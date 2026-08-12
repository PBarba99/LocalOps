"""Explicit registries for model-visible tools and approved commands."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, unique
from types import MappingProxyType
from typing import Any

Tool = Callable[..., str]


@unique
class CommandID(str, Enum):
    """Stable identifiers for commands approved by LocalOps."""

    HOSTNAME = "hostname"
    OS_RELEASE = "os_release"
    KERNEL_INFO = "kernel_info"
    UPTIME = "uptime"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"


# Construct the proxy inline so no mutable backing dictionary is retained.
COMMAND_ALLOWLIST = MappingProxyType(
    {
        CommandID.HOSTNAME: "hostname",
        CommandID.OS_RELEASE: "cat /etc/os-release",
        CommandID.KERNEL_INFO: "uname -a",
        CommandID.UPTIME: "uptime",
        CommandID.MEMORY_USAGE: "free -h",
        CommandID.DISK_USAGE: "df -h",
    }
)


def lookup_command(command_id: CommandID) -> str:
    """Return a fixed command, rejecting everything except a known enum member."""

    if not isinstance(command_id, CommandID):
        raise ValueError(f"Unknown command ID: {command_id!r}")

    try:
        return COMMAND_ALLOWLIST[command_id]
    except KeyError as exc:
        raise ValueError(f"Unknown command ID: {command_id!r}") from exc


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, name: str, tool: Tool) -> None:
        self._tools[name] = tool

    def definitions(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Tool definitions are not implemented")

    def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        raise NotImplementedError(f"Invocation for {name!r} is not implemented")
