"""Local Ollama model boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ollama

from .config import Settings


@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: tuple[dict[str, Any], ...] = ()
    metrics: ModelMetrics | None = None


@dataclass(frozen=True)
class ModelMetrics:
    """Non-sensitive performance metrics reported by Ollama."""

    total_ms: float | None = None
    load_ms: float | None = None
    prompt_eval_ms: float | None = None
    generation_ms: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None


def _duration_ms(value: object) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(value / 1_000_000, 3)


def _token_count(value: object) -> int | None:
    return value if isinstance(value, int) else None


@dataclass(frozen=True)
class OllamaClient:
    """Boundary around the local Ollama SDK."""

    settings: Settings

    def warm_up(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> None:
        """Load the model and prime the repeated chat prompt prefix."""

        self._create_client().chat(
            model=self.settings.ollama_model,
            messages=messages,
            tools=tools,
            stream=False,
            keep_alive=-1,
            options={"num_predict": 1},
        )

    def unload(self) -> None:
        """Unload the configured model after the CLI session ends."""

        self._create_client().generate(
            model=self.settings.ollama_model,
            stream=False,
            keep_alive=0,
        )

    def _create_client(self) -> ollama.Client:
        """Create an SDK client for the validated Ollama endpoint."""

        return ollama.Client(
            host=str(self.settings.ollama_base_url),
            timeout=self.settings.ollama_timeout_seconds,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ModelResponse:
        """Send a non-streaming chat request and normalize requested tools."""

        request: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": False,
            "keep_alive": -1,
        }
        if tools is not None:
            request["tools"] = tools
        if options is not None:
            request["options"] = options

        response = self._create_client().chat(**request)
        tool_calls = tuple(
            {
                "name": tool_call.function.name,
                "arguments": dict(tool_call.function.arguments),
            }
            for tool_call in (response.message.tool_calls or ())
        )
        metrics = ModelMetrics(
            total_ms=_duration_ms(response.total_duration),
            load_ms=_duration_ms(response.load_duration),
            prompt_eval_ms=_duration_ms(response.prompt_eval_duration),
            generation_ms=_duration_ms(response.eval_duration),
            prompt_tokens=_token_count(response.prompt_eval_count),
            output_tokens=_token_count(response.eval_count),
        )
        if all(value is None for value in metrics.__dict__.values()):
            metrics = None
        return ModelResponse(
            content=response.message.content or "",
            tool_calls=tool_calls,
            metrics=metrics,
        )
