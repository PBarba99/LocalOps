"""Orchestration loop joining the model to predefined tools."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from .ollama_client import ModelResponse, OllamaClient
from .prompts import FINAL_ANSWER_PROMPT, SYSTEM_PROMPT
from .request_policy import ControlActionID
from .tools.registry import InvalidToolRequest, ToolRegistry

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 6


class InvalidFinalResponse(ValueError):
    """The model failed to return a usable text-only final answer."""


def _log_tool_event(event: str, **fields: Any) -> None:
    """Emit a machine-readable event without command output or configuration."""

    logger.info(json.dumps({"event": event, **fields}, sort_keys=True))


def _log_model_metrics(
    response: ModelResponse,
    phase: str,
    attempt: int | None = None,
) -> None:
    """Log Ollama timings and token counts without conversational content."""

    if response.metrics is None:
        return
    fields: dict[str, Any] = {
        "phase": phase,
        "total_ms": response.metrics.total_ms,
        "load_ms": response.metrics.load_ms,
        "prompt_eval_ms": response.metrics.prompt_eval_ms,
        "generation_ms": response.metrics.generation_ms,
        "prompt_tokens": response.metrics.prompt_tokens,
        "output_tokens": response.metrics.output_tokens,
    }
    if attempt is not None:
        fields["attempt"] = attempt
    _log_tool_event("model_response_metrics", **fields)


@dataclass(frozen=True)
class ToolExecution:
    """One validated model tool request and its resulting output."""

    name: str
    output: str


@dataclass
class ServerAssistant:
    model: OllamaClient
    tools: ToolRegistry

    def warm_up(self) -> None:
        """Load the model and prime its stable system-and-tool prompt prefix."""

        self.model.warm_up(
            [{"role": "system", "content": SYSTEM_PROMPT}],
            self.tools.definitions(),
        )

    @staticmethod
    def _initial_messages(question: str) -> list[dict[str, object]]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

    def _validate_tool_response(self, response: ModelResponse) -> None:
        """Validate a complete model tool batch before executing any call."""

        call_count = len(response.tool_calls)
        if call_count == 0:
            raise InvalidToolRequest("Model must request at least one tool")
        if call_count > MAX_TOOL_CALLS:
            raise InvalidToolRequest(
                f"Model may request at most {MAX_TOOL_CALLS} tools; "
                f"received {call_count}"
            )

        requested_names: set[str] = set()
        for tool_call in response.tool_calls:
            name = tool_call.get("name")
            arguments = tool_call.get("arguments")
            self.tools.validate_invocation(name, arguments)
            if name in requested_names:
                raise InvalidToolRequest(f"Duplicate tool request: {name!r}")
            requested_names.add(name)

        control_name = ControlActionID.DECLINE_UNSUPPORTED_REQUEST.value
        if control_name in requested_names and call_count != 1:
            raise InvalidToolRequest(
                f"Tool {control_name!r} cannot be combined with inspection tools"
            )

    def _execute_tool_response(self, response: ModelResponse) -> ToolExecution:
        """Validate and execute exactly one requested tool."""

        self._validate_tool_response(response)
        if len(response.tool_calls) != 1:
            raise InvalidToolRequest(
                "Model must request exactly one tool; "
                f"received {len(response.tool_calls)}"
            )

        tool_call = response.tool_calls[0]
        name = tool_call.get("name")
        arguments = tool_call.get("arguments")
        output = self.tools.invoke(name, arguments)
        return ToolExecution(name=name, output=output)

    def _execute_tool_batch(
        self, response: ModelResponse
    ) -> tuple[ToolExecution, ...]:
        """Validate a tool batch, then execute its calls sequentially."""

        self._validate_tool_response(response)
        executions = []
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            arguments = tool_call["arguments"]
            output = self.tools.invoke(name, arguments)
            executions.append(ToolExecution(name=name, output=output))
        return tuple(executions)

    def _select_and_execute(
        self,
        messages: list[dict[str, object]],
        definitions: list[dict[str, object]],
    ) -> tuple[ModelResponse, tuple[ToolExecution, ...]]:
        """Allow one correction retry for an invalid model tool request."""

        for attempt in range(2):
            response = self.model.chat(
                messages,
                tools=definitions,
                options={"temperature": 0},
            )
            _log_model_metrics(response, "tool_selection", attempt + 1)
            requested_name = (
                response.tool_calls[0].get("name")
                if len(response.tool_calls) == 1
                else None
            )
            _log_tool_event(
                "tool_request_received",
                attempt=attempt + 1,
                tool_name=requested_name,
                tool_call_count=len(response.tool_calls),
            )
            try:
                executions = self._execute_tool_batch(response)
            except InvalidToolRequest as exc:
                _log_tool_event(
                    "tool_request_rejected",
                    attempt=attempt + 1,
                    tool_name=requested_name,
                    reason=str(exc),
                )
                if attempt == 1:
                    raise InvalidToolRequest(
                        "Model produced an invalid tool request after one correction: "
                        f"{exc}"
                    ) from exc
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous tool request was invalid: {exc}. "
                            f"Choose between one and {MAX_TOOL_CALLS} distinct "
                            "available tools and pass an empty argument object "
                            "{} for each one."
                        ),
                    }
                )
            except Exception as exc:
                _log_tool_event(
                    "tool_execution_failed",
                    attempt=attempt + 1,
                    tool_name=requested_name,
                    error_type=type(exc).__name__,
                )
                raise
            else:
                success_fields: dict[str, Any]
                if len(executions) == 1:
                    success_fields = {"tool_name": executions[0].name}
                else:
                    success_fields = {
                        "tool_names": [execution.name for execution in executions]
                    }
                _log_tool_event(
                    "tool_execution_succeeded",
                    attempt=attempt + 1,
                    **success_fields,
                )
                return response, executions

        raise AssertionError("unreachable")

    def run_requested_tool(self, question: str) -> ToolExecution:
        """Ask the model to select and execute exactly one predefined tool."""

        messages = self._initial_messages(question)
        response, executions = self._select_and_execute(
            messages,
            self.tools.definitions(),
        )
        if len(executions) != 1:
            raise InvalidToolRequest(
                "run_requested_tool requires exactly one selected tool"
            )
        return executions[0]

    def answer(self, question: str) -> str:
        """Run approved tools and ask the model to explain their results."""

        messages = self._initial_messages(question)
        definitions = self.tools.definitions()
        selection, executions = self._select_and_execute(messages, definitions)
        if (
            executions[0].name
            == ControlActionID.DECLINE_UNSUPPORTED_REQUEST.value
        ):
            return executions[0].output
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": selection.content,
                    "tool_calls": [
                        {
                            "function": {
                                "name": tool_call["name"],
                                "arguments": tool_call["arguments"],
                            }
                        }
                        for tool_call in selection.tool_calls
                    ],
                },
                *[
                    {
                        "role": "tool",
                        "tool_name": execution.name,
                        "content": execution.output,
                    }
                    for execution in executions
                ],
                {"role": "user", "content": FINAL_ANSWER_PROMPT},
            ]
        )
        final_response = self.model.chat(messages)
        _log_model_metrics(final_response, "final_answer")
        if final_response.tool_calls:
            raise InvalidFinalResponse(
                "Model requested another tool instead of answering"
            )
        if not final_response.content.strip():
            raise InvalidFinalResponse("Model returned an empty final answer")
        return final_response.content
