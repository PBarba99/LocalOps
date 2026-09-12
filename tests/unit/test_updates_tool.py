"""Tests for read-only cached package-update inspection."""

from unittest.mock import MagicMock, call

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID
from localops.tools.updates import get_package_updates


def test_get_package_updates_returns_packages_and_refresh_timestamp() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult(
            "Listing...\nexample/stable 2.0 amd64 [upgradable from: 1.0]\n",
            "WARNING: apt does not have a stable CLI interface.\n",
            0,
        ),
        CommandResult("2026-09-12 07:10:11.000000000 +0200\n", "", 0),
    ]

    output = get_package_updates(ssh)

    assert output == (
        "Available package updates (cached APT metadata):\n"
        "example/stable 2.0 amd64 [upgradable from: 1.0]\n\n"
        "Last recorded periodic APT refresh:\n"
        "2026-09-12 07:10:11.000000000 +0200\n\n"
        "No metadata refresh or package installation was performed. "
        "The refresh timestamp does not guarantee all repositories are current."
    )
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.AVAILABLE_UPDATES),
        call(CommandID.APT_REFRESH_TIMESTAMP),
    ]


@pytest.mark.parametrize("updates", ["", " \n", "Listing...\n", "Listing... Done\n"])
def test_get_package_updates_reports_no_cached_upgrades(updates: str) -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult(updates, "", 0),
        CommandResult("Unknown (APT periodic refresh stamp missing)\n", "", 0),
    ]

    output = get_package_updates(ssh)

    assert "None reported by cached APT metadata" in output
    assert "Unknown (APT periodic refresh stamp missing)" in output
    assert "does not guarantee all repositories are current" in output


def test_get_package_updates_labels_empty_refresh_output_as_unknown() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult("Listing...\nexample/stable 2.0 amd64\n", "", 0),
        CommandResult(" \n", "", 0),
    ]

    output = get_package_updates(ssh)

    assert "Last recorded periodic APT refresh:\nUnknown" in output
    assert "example/stable 2.0 amd64" in output


def test_get_package_updates_stops_when_package_query_fails() -> None:
    ssh = MagicMock()
    failed = CommandResult("partial output", "APT query failed\n", 100)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_package_updates(ssh)

    assert raised.value.command_id is CommandID.AVAILABLE_UPDATES
    assert raised.value.result is failed
    ssh.run_approved_command.assert_called_once_with(CommandID.AVAILABLE_UPDATES)


def test_get_package_updates_preserves_refresh_query_failure() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "stat: permission denied\n", 1)
    ssh.run_approved_command.side_effect = [
        CommandResult("Listing...\n", "", 0),
        failed,
    ]

    with pytest.raises(ToolCommandError) as raised:
        get_package_updates(ssh)

    assert raised.value.command_id is CommandID.APT_REFRESH_TIMESTAMP
    assert raised.value.result is failed
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.AVAILABLE_UPDATES),
        call(CommandID.APT_REFRESH_TIMESTAMP),
    ]
