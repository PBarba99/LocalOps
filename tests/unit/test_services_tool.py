"""Tests for the read-only systemd service status tool."""

from unittest.mock import MagicMock, call

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID
from localops.tools.services import get_service_status


def test_get_service_status_returns_labeled_command_output() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult(
            "ssh.service loaded active running OpenSSH server\n",
            "",
            0,
        ),
        CommandResult(
            "example.service loaded failed failed Example service\n",
            "",
            0,
        ),
    ]

    output = get_service_status(ssh)

    assert output == (
        "Running services:\n"
        "ssh.service loaded active running OpenSSH server\n\n"
        "Failed services:\n"
        "example.service loaded failed failed Example service"
    )
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.RUNNING_SERVICES),
        call(CommandID.FAILED_SERVICES),
    ]


def test_get_service_status_labels_an_empty_failed_list_as_none() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult(
            "ssh.service loaded active running OpenSSH server\n",
            "",
            0,
        ),
        CommandResult("\n", "", 0),
    ]

    output = get_service_status(ssh)

    assert output.endswith("Failed services:\nNone")


def test_get_service_status_stops_when_running_services_fail() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "systemctl unavailable\n", 1)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_service_status(ssh)

    assert raised.value.command_id is CommandID.RUNNING_SERVICES
    assert raised.value.result is failed
    ssh.run_approved_command.assert_called_once_with(CommandID.RUNNING_SERVICES)


def test_get_service_status_stops_when_failed_services_query_fails() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "systemctl query failed\n", 1)
    ssh.run_approved_command.side_effect = [
        CommandResult(
            "ssh.service loaded active running OpenSSH server\n",
            "",
            0,
        ),
        failed,
    ]

    with pytest.raises(ToolCommandError) as raised:
        get_service_status(ssh)

    assert raised.value.command_id is CommandID.FAILED_SERVICES
    assert raised.value.result is failed
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.RUNNING_SERVICES),
        call(CommandID.FAILED_SERVICES),
    ]
