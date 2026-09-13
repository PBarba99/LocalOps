"""Tests for application construction."""

from pathlib import Path
from unittest.mock import MagicMock, call

import json
import logging
import httpx
import ollama
import paramiko
import pytest

from localops.agent import ServerAssistant
from localops.app import CLI_BANNER, build_assistant, configure_logging, run_cli
from localops.config import Settings
from localops.ollama_client import ModelResponse, OllamaClient
from localops.ssh_client import CommandResult, SSHClient
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID, InvalidToolRequest, ToolRegistry


def test_build_assistant_shares_one_validated_settings_object() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )

    assistant = build_assistant(settings)

    assert isinstance(assistant.model, OllamaClient)
    assert isinstance(assistant.tools, ToolRegistry)
    assert isinstance(assistant.tools.ssh, SSHClient)
    assert assistant.model.settings is settings
    assert assistant.tools.ssh.settings is settings


def test_configure_logging_writes_json_to_rotating_local_file(tmp_path: Path) -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        log_level="INFO",
        _env_file=None,
    )
    log_path = tmp_path / ".localops" / "localops.log"

    configured_path = configure_logging(settings, log_path)
    logging.getLogger("localops.agent").info(
        json.dumps({"event": "tool_execution_succeeded", "tool_name": "test"})
    )
    for handler in logging.getLogger("localops").handlers:
        handler.flush()

    assert configured_path == log_path
    assert json.loads(log_path.read_text(encoding="utf-8").strip()) == {
        "event": "tool_execution_succeeded",
        "tool_name": "test",
    }
    localops_logger = logging.getLogger("localops")
    for handler in tuple(localops_logger.handlers):
        if getattr(handler, "_localops_owned", False):
            localops_logger.removeHandler(handler)
            handler.close()


def test_run_cli_answers_questions_until_exit() -> None:
    assistant = MagicMock()
    assistant.answer.side_effect = ["6.6 GiB available", "183 GiB available"]
    inputs = iter(
        [
            "How much memory is available?",
            "How much storage is available?",
            " EXIT ",
        ]
    )
    output = MagicMock()

    run_cli(assistant, input_fn=lambda _: next(inputs), output_fn=output)

    assert assistant.answer.call_args_list == [
        call("How much memory is available?"),
        call("How much storage is available?"),
    ]
    assert [output_call.args[0] for output_call in output.call_args_list] == [
        CLI_BANNER,
        "Loading local model...",
        "Model ready.",
        "Type 'exit' or 'quit' to stop.",
        "LocalOps: 6.6 GiB available",
        "LocalOps: 183 GiB available",
        "Goodbye.",
    ]
    assistant.warm_up.assert_called_once_with()
    assistant.model.unload.assert_called_once_with()


def test_run_cli_ignores_blank_questions() -> None:
    assistant = MagicMock()
    inputs = iter(["   ", "quit"])
    output = MagicMock()

    run_cli(assistant, input_fn=lambda _: next(inputs), output_fn=output)

    assistant.answer.assert_not_called()
    assert "Please enter a question." in [
        output_call.args[0] for output_call in output.call_args_list
    ]


def test_run_cli_stops_before_prompt_when_model_warm_up_fails() -> None:
    assistant = MagicMock()
    assistant.warm_up.side_effect = ollama.ResponseError(
        "model unavailable", status_code=404
    )
    input_fn = MagicMock()
    output = MagicMock()

    run_cli(assistant, input_fn=input_fn, output_fn=output)

    input_fn.assert_not_called()
    assistant.answer.assert_not_called()
    assistant.model.unload.assert_not_called()
    assert [call.args[0] for call in output.call_args_list] == [
        CLI_BANNER,
        "Loading local model...",
        (
            "Error: the local model could not be loaded. Check that Ollama "
            "and the configured model are available."
        ),
    ]


@pytest.mark.parametrize(
    "failure", [ConnectionError("Ollama stopped"), httpx.ReadTimeout("timed out")]
)
def test_run_cli_ignores_unload_failure_during_clean_exit(failure: Exception) -> None:
    assistant = MagicMock()
    assistant.model.unload.side_effect = failure
    output = MagicMock()

    run_cli(assistant, input_fn=lambda _: "quit", output_fn=output)

    assistant.model.unload.assert_called_once_with()
    assert output.call_args_list[-1] == call("Goodbye.")


def test_run_cli_stops_before_input_when_model_loading_times_out() -> None:
    assistant = MagicMock()
    assistant.warm_up.side_effect = httpx.ReadTimeout("private endpoint details")
    input_fn = MagicMock()
    output = MagicMock()

    run_cli(assistant, input_fn=input_fn, output_fn=output)

    input_fn.assert_not_called()
    assistant.answer.assert_not_called()
    messages = [invocation.args[0] for invocation in output.call_args_list]
    assert messages[-1] == (
        "Error: loading the local model timed out. Check Ollama or increase "
        "OLLAMA_TIMEOUT_SECONDS."
    )
    assert not any("private endpoint details" in message for message in messages)


@pytest.mark.parametrize(
    "timeout_type",
    [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout],
)
def test_run_cli_recovers_after_ollama_timeout(
    timeout_type: type[httpx.TimeoutException],
) -> None:
    assistant = MagicMock()
    assistant.answer.side_effect = [
        timeout_type("private endpoint details"), "The hostname is test-server."
    ]
    inputs = iter(["Inspect the server", "Try again", "quit"])
    output = MagicMock()

    run_cli(assistant, input_fn=lambda _: next(inputs), output_fn=output)

    messages = [invocation.args[0] for invocation in output.call_args_list]
    assert (
        "Error: the local Ollama request timed out. Try again or increase "
        "OLLAMA_TIMEOUT_SECONDS."
    ) in messages
    assert "LocalOps: The hostname is test-server." in messages
    assert messages[-1] == "Goodbye."
    assert not any("private endpoint details" in message for message in messages)
    assert assistant.answer.call_count == 2
    assistant.model.unload.assert_called_once_with()


@pytest.mark.parametrize(
    ("failure", "expected_message"),
    [
        (
            InvalidToolRequest("invalid after retry"),
            "could not produce a valid tool request",
        ),
        (
            ToolCommandError(
                CommandID.DISK_USAGE,
                CommandResult("", "df failed", 1),
            ),
            "DISK_USAGE failed with exit code 1. Details: df failed",
        ),
        (
            paramiko.AuthenticationException("denied"),
            "SSH authentication failed",
        ),
        (
            TimeoutError("timed out"),
            "connection or command timed out",
        ),
        (
            ollama.ResponseError("model unavailable", status_code=404),
            "local Ollama request failed",
        ),
        (
            ConnectionError("VPN unavailable"),
            "a connection failed",
        ),
    ],
)
def test_run_cli_reports_expected_error_and_keeps_running(
    failure: Exception, expected_message: str
) -> None:
    assistant = MagicMock()
    assistant.answer.side_effect = failure
    inputs = iter(["Inspect the server", "quit"])
    output = MagicMock()

    run_cli(assistant, input_fn=lambda _: next(inputs), output_fn=output)

    messages = [output_call.args[0] for output_call in output.call_args_list]
    assert any(expected_message in message for message in messages)
    assert messages[-1] == "Goodbye."


@pytest.mark.parametrize(
    "invalid_response",
    [
        ModelResponse(content=""),
        ModelResponse(content=" \n"),
        ModelResponse(
            content="Another tool is needed.",
            tool_calls=({"name": "get_memory_usage", "arguments": {}},),
        ),
    ],
)
def test_run_cli_recovers_after_invalid_final_response(
    invalid_response: ModelResponse,
) -> None:
    model = MagicMock()
    tools = MagicMock()
    selection = ModelResponse(
        content="",
        tool_calls=({"name": "get_system_info", "arguments": {}},),
    )
    model.chat.side_effect = [
        selection,
        invalid_response,
        selection,
        ModelResponse(content="The hostname is test-server."),
    ]
    tools.invoke.return_value = "Hostname:\ntest-server"
    assistant = ServerAssistant(model=model, tools=tools)
    inputs = iter(["What is the hostname?", "What is the hostname?", "quit"])
    output = MagicMock()

    run_cli(assistant, input_fn=lambda _: next(inputs), output_fn=output)

    messages = [output_call.args[0] for output_call in output.call_args_list]
    assert messages.count(
        "Error: the local model returned an invalid final answer. Try asking again."
    ) == 1
    assert "LocalOps: The hostname is test-server." in messages
    assert messages[-1] == "Goodbye."
    assert model.chat.call_count == 4
    assert tools.invoke.call_count == 2
    model.unload.assert_called_once_with()


@pytest.mark.parametrize("terminal_signal", [EOFError(), KeyboardInterrupt()])
def test_run_cli_exits_cleanly_when_terminal_input_stops(
    terminal_signal: BaseException,
) -> None:
    assistant = MagicMock()
    output = MagicMock()

    def stop_input(_: str) -> str:
        raise terminal_signal

    run_cli(assistant, input_fn=stop_input, output_fn=output)

    assistant.answer.assert_not_called()
    assert output.call_args_list[-1] == call("Goodbye.")
