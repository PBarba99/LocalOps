"""Local Ollama model boundary."""

from dataclasses import dataclass
from typing import Any

import ollama

from .config import Settings


@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class OllamaClient:
    """Boundary around the local Ollama SDK."""

    settings: Settings

    def _create_client(self) -> ollama.Client:
        """Create an SDK client for the validated Ollama endpoint."""

        return ollama.Client(host=str(self.settings.ollama_base_url))

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        """Send a non-streaming chat request and normalize requested tools."""

        request: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": False,
        }
        if tools is not None:
            request["tools"] = tools

        response = self._create_client().chat(**request)
        tool_calls = tuple(
            {
                "name": tool_call.function.name,
                "arguments": dict(tool_call.function.arguments),
            }
            for tool_call in (response.message.tool_calls or ())
        )
        return ModelResponse(
            content=response.message.content or "",
            tool_calls=tool_calls,
        )
