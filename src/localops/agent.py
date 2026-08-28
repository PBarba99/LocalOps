"""Orchestration loop joining the model to predefined tools."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from .ollama_client import ModelResponse, OllamaClient
from .prompts import SYSTEM_PROMPT
from .tools.registry import InvalidToolRequest, ToolRegistry

logger = logging.getLogger(__name__)


def _log_tool_event(event: str, **fields: Any) -> None:
    """Emit a machine-readable event without command output or configuration."""

    logger.info(json.dumps({"event": event, **fields}, sort_keys=True))


@dataclass(frozen=True)
class ToolExecution:
    """One validated model tool request and its resulting output."""

    name: str
    output: str


@dataclass
class ServerAssistant:
    model: OllamaClient
    tools: ToolRegistry

    @staticmethod
    def _initial_messages(question: str) -> list[dict[str, object]]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

    def _execute_tool_response(self, response: ModelResponse) -> ToolExecution:
        """Validate and execute exactly one requested tool."""

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

    def _select_and_execute(
        self,
        messages: list[dict[str, object]],
        definitions: list[dict[str, object]],
    ) -> tuple[ModelResponse, ToolExecution]:
        """Allow one correction retry for an invalid model tool request."""

        for attempt in range(2):
            response = self.model.chat(messages, tools=definitions)
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
                execution = self._execute_tool_response(response)
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
                            "Choose exactly one available tool and pass an empty "
                            "argument object {}."
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
                _log_tool_event(
                    "tool_execution_succeeded",
                    attempt=attempt + 1,
                    tool_name=execution.name,
                )
                return response, execution

        raise AssertionError("unreachable")

    def run_requested_tool(self, question: str) -> ToolExecution:
        """Ask the model to select and execute exactly one predefined tool."""

        messages = self._initial_messages(question)
        response, execution = self._select_and_execute(
            messages,
            self.tools.definitions(),
        )
        return execution

    def answer(self, question: str) -> str:
        """Run one approved tool and ask the model to explain its result."""

        messages = self._initial_messages(question)
        definitions = self.tools.definitions()
        selection, execution = self._select_and_execute(messages, definitions)
        tool_call = selection.tool_calls[0]
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
                    ],
                },
                {
                    "role": "tool",
                    "tool_name": execution.name,
                    "content": execution.output,
                },
            ]
        )
        final_response = self.model.chat(messages, tools=definitions)
        if final_response.tool_calls:
            raise ValueError("Model requested another tool instead of answering")
        if not final_response.content.strip():
            raise ValueError("Model returned an empty final answer")
        return final_response.content
