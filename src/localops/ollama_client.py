"""Local Ollama model boundary."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: tuple[dict[str, Any], ...] = ()


class OllamaClient:
    def chat(self, messages: list[dict[str, str]]) -> ModelResponse:
        raise NotImplementedError("Ollama integration is not implemented")

