"""Tests for the restricted command registry."""

from types import MappingProxyType

import pytest

from localops.tools.registry import COMMAND_ALLOWLIST, CommandID, lookup_command


EXPECTED_COMMANDS = {
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
}


def test_allowlist_contains_exactly_the_approved_commands() -> None:
    assert isinstance(COMMAND_ALLOWLIST, MappingProxyType)
    assert dict(COMMAND_ALLOWLIST) == EXPECTED_COMMANDS
    assert set(CommandID) == set(EXPECTED_COMMANDS)


@pytest.mark.parametrize(("command_id", "command"), EXPECTED_COMMANDS.items())
def test_lookup_returns_only_fixed_commands(
    command_id: CommandID, command: str
) -> None:
    assert lookup_command(command_id) == command


@pytest.mark.parametrize("command_id", EXPECTED_COMMANDS)
def test_allowlist_entries_cannot_be_replaced_or_deleted(
    command_id: CommandID,
) -> None:
    with pytest.raises(TypeError):
        COMMAND_ALLOWLIST[command_id] = "hostname; id"  # type: ignore[index]

    with pytest.raises(TypeError):
        del COMMAND_ALLOWLIST[command_id]  # type: ignore[attr-defined]

    assert lookup_command(command_id) == EXPECTED_COMMANDS[command_id]


@pytest.mark.parametrize(
    "untrusted_id",
    [
        "hostname",
        "HOSTNAME",
        "hostname; id",
        "$(id)",
        "disk_usage && whoami",
        "available_updates; apt upgrade",
        "apt_refresh_timestamp && apt update",
        "",
        None,
    ],
)
def test_lookup_rejects_unknown_and_injected_ids(untrusted_id: object) -> None:
    with pytest.raises(ValueError, match="Unknown command ID"):
        lookup_command(untrusted_id)  # type: ignore[arg-type]
