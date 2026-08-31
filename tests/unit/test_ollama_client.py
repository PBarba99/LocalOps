"""Tests for the local Ollama model boundary."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from localops.config import Settings
from localops.ollama_client import ModelMetrics, ModelResponse, OllamaClient


def test_ollama_client_uses_validated_settings() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen3:4b",
        _env_file=None,
    )

    client = OllamaClient(settings=settings)

    assert client.settings is settings


def test_sdk_client_uses_configured_ollama_endpoint() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        ollama_base_url="http://ollama.internal:11434",
        _env_file=None,
    )

    with patch("localops.ollama_client.ollama.Client") as client_class:
        sdk_client = OllamaClient(settings)._create_client()

    client_class.assert_called_once_with(host="http://ollama.internal:11434/")
    assert sdk_client is client_class.return_value


def test_chat_uses_configured_model_and_returns_normalized_response() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        ollama_model="qwen3:4b",
        _env_file=None,
    )
    messages = [{"role": "user", "content": "Reply with pong."}]
    sdk_client = MagicMock()
    sdk_client.chat.return_value.message.content = "pong"

    with patch.object(
        OllamaClient, "_create_client", return_value=sdk_client
    ):
        response = OllamaClient(settings).chat(messages)

    sdk_client.chat.assert_called_once_with(
        model="qwen3:4b",
        messages=messages,
        stream=False,
    )
    assert response == ModelResponse(content="pong")


def test_chat_sends_tools_and_normalizes_requested_tool_calls() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        ollama_model="qwen3:4b",
        _env_file=None,
    )
    messages = [{"role": "user", "content": "How much memory is available?"}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_memory_usage",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    tool_call = MagicMock()
    tool_call.function.name = "get_memory_usage"
    tool_call.function.arguments = {}
    sdk_client = MagicMock()
    sdk_client.chat.return_value.message.content = ""
    sdk_client.chat.return_value.message.tool_calls = [tool_call]

    with patch.object(
        OllamaClient, "_create_client", return_value=sdk_client
    ):
        response = OllamaClient(settings).chat(messages, tools=tools)

    sdk_client.chat.assert_called_once_with(
        model="qwen3:4b",
        messages=messages,
        stream=False,
        tools=tools,
    )
    assert response == ModelResponse(
        content="",
        tool_calls=({"name": "get_memory_usage", "arguments": {}},),
    )


def test_chat_normalizes_ollama_performance_metrics() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )
    sdk_client = MagicMock()
    raw_response = sdk_client.chat.return_value
    raw_response.message.content = "done"
    raw_response.message.tool_calls = None
    raw_response.total_duration = 2_500_000_000
    raw_response.load_duration = 1_200_000_000
    raw_response.prompt_eval_duration = 300_000_000
    raw_response.eval_duration = 900_000_000
    raw_response.prompt_eval_count = 120
    raw_response.eval_count = 24

    with patch.object(
        OllamaClient, "_create_client", return_value=sdk_client
    ):
        response = OllamaClient(settings).chat(
            [{"role": "user", "content": "test"}]
        )

    assert response.metrics == ModelMetrics(
        total_ms=2500.0,
        load_ms=1200.0,
        prompt_eval_ms=300.0,
        generation_ms=900.0,
        prompt_tokens=120,
        output_tokens=24,
    )
