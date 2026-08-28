"""Tests for the local Ollama model boundary."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from localops.config import Settings
from localops.ollama_client import ModelResponse, OllamaClient


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
