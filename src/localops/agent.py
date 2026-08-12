"""Orchestration loop joining the model to predefined tools."""

from dataclasses import dataclass
from .ollama_client import OllamaClient
from .tools.registry import ToolRegistry


@dataclass
class ServerAssistant:
    model: OllamaClient
    tools: ToolRegistry

    def answer(self, question: str) -> str:
        raise NotImplementedError("The agent loop is not implemented")

