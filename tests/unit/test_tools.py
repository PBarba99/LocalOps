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


def test_allowlist_entries_cannot_be_replaced_or_deleted() -> None:
    with pytest.raises(TypeError):
        COMMAND_ALLOWLIST[CommandID.HOSTNAME] = "hostname; id"  # type: ignore[index]

    with pytest.raises(TypeError):
        del COMMAND_ALLOWLIST[CommandID.HOSTNAME]  # type: ignore[attr-defined]

    assert lookup_command(CommandID.HOSTNAME) == "hostname"


@pytest.mark.parametrize(
    "untrusted_id",
    [
        "hostname",
        "HOSTNAME",
        "hostname; id",
        "$(id)",
        "disk_usage && whoami",
        "",
        None,
    ],
)
def test_lookup_rejects_unknown_and_injected_ids(untrusted_id: object) -> None:
    with pytest.raises(ValueError, match="Unknown command ID"):
        lookup_command(untrusted_id)  # type: ignore[arg-type]
