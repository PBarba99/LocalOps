"""Explicit registries for model-visible tools and approved commands."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from ..request_policy import (
    ControlActionID,
    lookup_control_response,
)

if TYPE_CHECKING:
    from ..ssh_client import SSHClient


class InvalidToolRequest(ValueError):
    """The model requested a tool outside the fixed invocation contract."""


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


@dataclass(frozen=True)
class ToolRegistry:
    """Fixed model-visible tools and their strict invocation boundary."""

    ssh: SSHClient | None = None

    def definitions(self) -> list[dict[str, Any]]:
        """Return the fixed zero-argument actions visible to the model."""

        descriptions = (
            (
                "get_system_info",
                "Get the server hostname, operating system, kernel, and uptime.",
            ),
            (
                "get_memory_usage",
                "Get the server's current memory and swap usage.",
            ),
            (
                "get_disk_usage",
                "Get current disk usage for the server's mounted filesystems.",
            ),
            (
                ControlActionID.DECLINE_UNSUPPORTED_REQUEST.value,
                "Decline a request that cannot be answered using the available "
                "read-only server inspection tools.",
            ),
        )
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            }
            for name, description in descriptions
        ]

    def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke one fixed zero-argument action after strict validation."""

        from .disk import get_disk_usage
        from .memory import get_memory_usage
        from .system import get_system_info

        tools = {
            "get_system_info": get_system_info,
            "get_memory_usage": get_memory_usage,
            "get_disk_usage": get_disk_usage,
        }
        control_name = ControlActionID.DECLINE_UNSUPPORTED_REQUEST.value
        if not isinstance(name, str) or (
            name not in tools and name != control_name
        ):
            raise InvalidToolRequest(f"Unknown tool: {name!r}")
        if not isinstance(arguments, dict) or arguments:
            raise InvalidToolRequest(f"Tool {name!r} accepts no arguments")
        if name == control_name:
            return lookup_control_response(
                ControlActionID.DECLINE_UNSUPPORTED_REQUEST
            )
        if self.ssh is None:
            raise RuntimeError("Tool registry has no SSH client")

        return tools[name](self.ssh)
