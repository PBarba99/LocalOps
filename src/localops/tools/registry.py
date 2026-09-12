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
    CPU_COUNT = "cpu_count"
    LOAD_AVERAGE = "load_average"
    RUNNING_SERVICES = "running_services"
    FAILED_SERVICES = "failed_services"
    NETWORK_INTERFACES = "network_interfaces"
    DEFAULT_ROUTE = "default_route"
    AVAILABLE_UPDATES = "available_updates"
    APT_REFRESH_TIMESTAMP = "apt_refresh_timestamp"
    THERMAL_READINGS = "thermal_readings"


# Construct the proxy inline so no mutable backing dictionary is retained.
COMMAND_ALLOWLIST = MappingProxyType(
    {
        CommandID.HOSTNAME: "hostname",
        CommandID.OS_RELEASE: "cat /etc/os-release",
        CommandID.KERNEL_INFO: "uname -a",
        CommandID.UPTIME: "uptime",
        CommandID.MEMORY_USAGE: "free -h",
        CommandID.DISK_USAGE: "df -h",
        CommandID.CPU_COUNT: "nproc",
        CommandID.LOAD_AVERAGE: "cat /proc/loadavg",
        CommandID.RUNNING_SERVICES: (
            "systemctl list-units --type=service --state=running "
            "--no-pager --no-legend --plain"
        ),
        CommandID.FAILED_SERVICES: (
            "systemctl list-units --type=service --state=failed "
            "--no-pager --no-legend --plain"
        ),
        CommandID.NETWORK_INTERFACES: "ip -brief address show",
        CommandID.DEFAULT_ROUTE: "ip route show default",
        CommandID.AVAILABLE_UPDATES: "LC_ALL=C apt list --upgradable",
        CommandID.APT_REFRESH_TIMESTAMP: (
            "if [ -f /var/lib/apt/periodic/update-stamp ]; then "
            "stat -c '%y' /var/lib/apt/periodic/update-stamp; "
            "else printf '%s\\n' 'Unknown (APT periodic refresh stamp missing)'; fi"
        ),
        # Tab-separated zone ID, kernel type, and raw millidegrees Celsius.
        # Missing/unreadable readings remain visible without failing other zones.
        CommandID.THERMAL_READINGS: (
            "for thermal_zone in /sys/class/thermal/thermal_zone*; do "
            '[ -d "$thermal_zone" ] || continue; '
            'thermal_type=$(cat "$thermal_zone/type" 2>/dev/null) '
            "|| thermal_type=Unknown; "
            'thermal_temp=$(cat "$thermal_zone/temp" 2>/dev/null) '
            "|| thermal_temp=Unavailable; "
            "printf '%s\\t%s\\t%s\\n' "
            '"${thermal_zone##*/}" "$thermal_type" "$thermal_temp"; done'
        ),
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

    def validate_invocation(
        self, name: str, arguments: dict[str, Any]
    ) -> None:
        """Validate one fixed action without executing it."""

        available_names = {
            definition["function"]["name"] for definition in self.definitions()
        }
        if not isinstance(name, str) or name not in available_names:
            raise InvalidToolRequest(f"Unknown tool: {name!r}")
        if not isinstance(arguments, dict) or arguments:
            raise InvalidToolRequest(f"Tool {name!r} accepts no arguments")

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
                "get_cpu_load",
                "Get the server's CPU count and current load averages.",
            ),
            (
                "get_service_status",
                "Get the server's running and failed systemd services.",
            ),
            (
                "get_network_status",
                "Get the server's network interfaces, assigned addresses, "
                "and default route.",
            ),
            (
                "get_package_updates",
                "List available package upgrades from cached APT metadata and "
                "the last recorded periodic refresh. Does not refresh metadata "
                "or install updates.",
            ),
            (
                "get_temperature_readings",
                "Get kernel thermal-zone temperatures in Celsius, including "
                "CPU package readings when available. Preserve zone labels "
                "and unavailable readings; do not infer hardware health.",
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

        from .cpu import get_cpu_load
        from .disk import get_disk_usage
        from .memory import get_memory_usage
        from .network import get_network_status
        from .services import get_service_status
        from .system import get_system_info
        from .temperature import get_temperature_readings
        from .updates import get_package_updates

        tools = {
            "get_system_info": get_system_info,
            "get_memory_usage": get_memory_usage,
            "get_disk_usage": get_disk_usage,
            "get_cpu_load": get_cpu_load,
            "get_service_status": get_service_status,
            "get_network_status": get_network_status,
            "get_package_updates": get_package_updates,
            "get_temperature_readings": get_temperature_readings,
        }
        control_name = ControlActionID.DECLINE_UNSUPPORTED_REQUEST.value
        self.validate_invocation(name, arguments)
        if name == control_name:
            return lookup_control_response(
                ControlActionID.DECLINE_UNSUPPORTED_REQUEST
            )

        if self.ssh is None:
            raise RuntimeError("Tool registry has no SSH client")
        return tools[name](self.ssh)
