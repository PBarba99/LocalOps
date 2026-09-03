"""Tests for safe model-to-tool orchestration."""

import json
import logging
from unittest.mock import MagicMock

import pytest

from localops.agent import ServerAssistant, ToolExecution
from localops.ollama_client import ModelMetrics, ModelResponse
from localops.prompts import SYSTEM_PROMPT
from localops.request_policy import ControlActionID, lookup_control_response
from localops.tools.registry import InvalidToolRequest, ToolRegistry


def test_run_requested_tool_selects_and_invokes_one_fixed_tool() -> None:
    model = MagicMock()
    tools = MagicMock()
    definitions = [{"type": "function", "function": {"name": "get_disk_usage"}}]
    tools.definitions.return_value = definitions
    model.chat.return_value = ModelResponse(
        content="",
        tool_calls=({"name": "get_disk_usage", "arguments": {}},),
    )
    tools.invoke.return_value = "Disk usage:\n/dev/sda2 78%"
    assistant = ServerAssistant(model=model, tools=tools)

    execution = assistant.run_requested_tool("How much storage is left?")

    model.chat.assert_called_once_with(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "How much storage is left?"},
        ],
        tools=definitions,
    )
    tools.invoke.assert_called_once_with("get_disk_usage", {})
    assert execution == ToolExecution(
        name="get_disk_usage",
        output="Disk usage:\n/dev/sda2 78%",
    )


@pytest.mark.parametrize(
    "tool_calls",
    [
        (),
        (
            {"name": "get_memory_usage", "arguments": {}},
            {"name": "get_disk_usage", "arguments": {}},
        ),
    ],
)
def test_run_requested_tool_requires_exactly_one_request(
    tool_calls: tuple[dict[str, object], ...]
) -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.return_value = ModelResponse(content="", tool_calls=tool_calls)
    assistant = ServerAssistant(model=model, tools=tools)

    with pytest.raises(ValueError, match="exactly one tool"):
        assistant.run_requested_tool("Inspect the server")

    tools.invoke.assert_not_called()


def test_run_requested_tool_does_not_bypass_registry_validation() -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.return_value = ModelResponse(
        content="",
        tool_calls=(
            {"name": "get_disk_usage", "arguments": {"path": "/etc"}},
        ),
    )
    tools.invoke.side_effect = ValueError("accepts no arguments")
    assistant = ServerAssistant(model=model, tools=tools)

    with pytest.raises(ValueError, match="accepts no arguments"):
        assistant.run_requested_tool("Inspect /etc")

    tools.invoke.assert_called_once_with("get_disk_usage", {"path": "/etc"})


def test_answer_sends_tool_output_back_and_returns_final_text() -> None:
    model = MagicMock()
    tools = MagicMock()
    definitions = [{"type": "function", "function": {"name": "get_disk_usage"}}]
    tools.definitions.return_value = definitions
    model.chat.side_effect = [
        ModelResponse(
            content="",
            tool_calls=({"name": "get_disk_usage", "arguments": {}},),
        ),
        ModelResponse(content="The main filesystem has 192 GiB available."),
    ]
    tools.invoke.return_value = "Disk usage:\n/dev/sda2 915G 677G 192G 78% /"
    assistant = ServerAssistant(model=model, tools=tools)

    answer = assistant.answer("How much storage is left?")

    assert answer == "The main filesystem has 192 GiB available."
    tools.invoke.assert_called_once_with("get_disk_usage", {})
    assert model.chat.call_args_list[1].args[0] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "How much storage is left?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_disk_usage",
                        "arguments": {},
                    }
                }
            ],
        },
        {
            "role": "tool",
            "tool_name": "get_disk_usage",
            "content": "Disk usage:\n/dev/sda2 915G 677G 192G 78% /",
        },
    ]
    assert model.chat.call_args_list[1].kwargs == {"tools": definitions}


def test_answer_returns_fixed_decline_without_ssh_or_second_model_call() -> None:
    model = MagicMock()
    model.chat.return_value = ModelResponse(
        content="",
        tool_calls=(
            {"name": "decline_unsupported_request", "arguments": {}},
        ),
    )
    assistant = ServerAssistant(model=model, tools=ToolRegistry())

    answer = assistant.answer("What day is it?")

    assert answer == lookup_control_response(
        ControlActionID.DECLINE_UNSUPPORTED_REQUEST
    )
    model.chat.assert_called_once()


@pytest.mark.parametrize(
    "final_response",
    [
        ModelResponse(
            content="",
            tool_calls=({"name": "get_memory_usage", "arguments": {}},),
        ),
        ModelResponse(content="   "),
    ],
)
def test_answer_rejects_missing_final_text(final_response: ModelResponse) -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.side_effect = [
        ModelResponse(
            content="",
            tool_calls=({"name": "get_system_info", "arguments": {}},),
        ),
        final_response,
    ]
    tools.invoke.return_value = "Hostname:\ntest-server"
    assistant = ServerAssistant(model=model, tools=tools)

    with pytest.raises(ValueError, match="another tool|empty final answer"):
        assistant.answer("What is the hostname?")


def test_answer_corrects_one_invalid_tool_request() -> None:
    model = MagicMock()
    tools = MagicMock()
    definitions = [{"type": "function", "function": {"name": "get_memory_usage"}}]
    tools.definitions.return_value = definitions
    model.chat.side_effect = [
        ModelResponse(content="I need current data."),
        ModelResponse(
            content="",
            tool_calls=({"name": "get_memory_usage", "arguments": {}},),
        ),
        ModelResponse(content="The server has 6.6 GiB available."),
    ]
    tools.invoke.return_value = "Memory usage:\navailable 6.6Gi"
    assistant = ServerAssistant(model=model, tools=tools)

    answer = assistant.answer("How much memory is available?")

    assert answer == "The server has 6.6 GiB available."
    correction_messages = model.chat.call_args_list[1].args[0]
    correction = next(
        message["content"]
        for message in correction_messages
        if "previous tool request was invalid" in message.get("content", "")
    )
    assert "empty argument object {}" in correction
    tools.invoke.assert_called_once_with("get_memory_usage", {})


def test_answer_stops_after_invalid_correction_retry() -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.side_effect = [
        ModelResponse(content="No tool needed."),
        ModelResponse(
            content="",
            tool_calls=(
                {"name": "get_disk_usage", "arguments": {"path": "/"}},
            ),
        ),
    ]
    tools.invoke.side_effect = InvalidToolRequest(
        "Tool 'get_disk_usage' accepts no arguments"
    )
    assistant = ServerAssistant(model=model, tools=tools)

    with pytest.raises(InvalidToolRequest, match="after one correction"):
        assistant.answer("Check the server")

    assert model.chat.call_count == 2
    assert tools.invoke.call_count == 1


def test_answer_does_not_retry_operational_failure() -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.return_value = ModelResponse(
        content="",
        tool_calls=({"name": "get_system_info", "arguments": {}},),
    )
    tools.invoke.side_effect = TimeoutError("VPN unavailable")
    assistant = ServerAssistant(model=model, tools=tools)

    with pytest.raises(TimeoutError, match="VPN unavailable"):
        assistant.answer("What OS is the server running?")

    model.chat.assert_called_once()


def test_tool_logs_are_structured_and_omit_sensitive_output(caplog: pytest.LogCaptureFixture) -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.side_effect = [
        ModelResponse(
            content="",
            tool_calls=({"name": "get_disk_usage", "arguments": {}},),
        ),
        ModelResponse(content="There is enough disk space."),
    ]
    sensitive_output = "PRIVATE SERVER OUTPUT / secret mount"
    tools.invoke.return_value = sensitive_output
    assistant = ServerAssistant(model=model, tools=tools)

    with caplog.at_level(logging.INFO, logger="localops.agent"):
        assistant.answer("This question is not logged")

    events = [json.loads(record.message) for record in caplog.records]
    assert events == [
        {
            "attempt": 1,
            "event": "tool_request_received",
            "tool_call_count": 1,
            "tool_name": "get_disk_usage",
        },
        {
            "attempt": 1,
            "event": "tool_execution_succeeded",
            "tool_name": "get_disk_usage",
        },
    ]
    combined_logs = "\n".join(record.message for record in caplog.records)
    assert sensitive_output not in combined_logs
    assert "This question is not logged" not in combined_logs


def test_operational_failure_log_uses_exception_type_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.return_value = ModelResponse(
        content="",
        tool_calls=({"name": "get_system_info", "arguments": {}},),
    )
    tools.invoke.side_effect = TimeoutError("sensitive connection details")
    assistant = ServerAssistant(model=model, tools=tools)

    with caplog.at_level(logging.INFO, logger="localops.agent"):
        with pytest.raises(TimeoutError):
            assistant.answer("Inspect the server")

    failure = json.loads(caplog.records[-1].message)
    assert failure == {
        "attempt": 1,
        "error_type": "TimeoutError",
        "event": "tool_execution_failed",
        "tool_name": "get_system_info",
    }
    assert "sensitive connection details" not in caplog.records[-1].message


def test_answer_logs_separate_selection_and_final_model_metrics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    model = MagicMock()
    tools = MagicMock()
    model.chat.side_effect = [
        ModelResponse(
            content="",
            tool_calls=({"name": "get_memory_usage", "arguments": {}},),
            metrics=ModelMetrics(
                total_ms=1200.0,
                load_ms=800.0,
                prompt_eval_ms=100.0,
                generation_ms=300.0,
                prompt_tokens=90,
                output_tokens=8,
            ),
        ),
        ModelResponse(
            content="6.6 GiB is available.",
            metrics=ModelMetrics(
                total_ms=600.0,
                load_ms=0.0,
                prompt_eval_ms=200.0,
                generation_ms=400.0,
                prompt_tokens=160,
                output_tokens=12,
            ),
        ),
    ]
    tools.invoke.return_value = "Memory usage:\navailable 6.6Gi"

    with caplog.at_level(logging.INFO, logger="localops.agent"):
        ServerAssistant(model=model, tools=tools).answer("Memory?")

    metrics = [
        json.loads(record.message)
        for record in caplog.records
        if json.loads(record.message)["event"] == "model_response_metrics"
    ]
    assert metrics[0]["phase"] == "tool_selection"
    assert metrics[0]["attempt"] == 1
    assert metrics[0]["load_ms"] == 800.0
    assert metrics[1]["phase"] == "final_answer"
    assert "attempt" not in metrics[1]
    assert metrics[1]["generation_ms"] == 400.0
