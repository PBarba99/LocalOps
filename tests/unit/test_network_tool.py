"""Tests for the read-only network status tool."""

from unittest.mock import MagicMock, call

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError
from localops.tools.network import get_network_status
from localops.tools.registry import CommandID


def test_get_network_status_returns_labeled_command_output() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult(
            "lo UNKNOWN 127.0.0.1/8 ::1/128\n"
            "eth0 UP 192.0.2.10/24\n",
            "",
            0,
        ),
        CommandResult("default via 192.0.2.1 dev eth0\n", "", 0),
    ]

    output = get_network_status(ssh)

    assert output == (
        "Network interfaces:\n"
        "lo UNKNOWN 127.0.0.1/8 ::1/128\n"
        "eth0 UP 192.0.2.10/24\n\n"
        "Default route:\n"
        "default via 192.0.2.1 dev eth0"
    )
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.NETWORK_INTERFACES),
        call(CommandID.DEFAULT_ROUTE),
    ]


def test_get_network_status_labels_an_absent_default_route_as_none() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult("eth0 DOWN\n", "", 0),
        CommandResult("\n", "", 0),
    ]

    output = get_network_status(ssh)

    assert output.endswith("Default route:\nNone")


def test_get_network_status_stops_when_interface_query_fails() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "ip: command failed\n", 1)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_network_status(ssh)

    assert raised.value.command_id is CommandID.NETWORK_INTERFACES
    assert raised.value.result is failed
    ssh.run_approved_command.assert_called_once_with(CommandID.NETWORK_INTERFACES)


def test_get_network_status_stops_when_default_route_query_fails() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "route query failed\n", 1)
    ssh.run_approved_command.side_effect = [
        CommandResult("eth0 UP 192.0.2.10/24\n", "", 0),
        failed,
    ]

    with pytest.raises(ToolCommandError) as raised:
        get_network_status(ssh)

    assert raised.value.command_id is CommandID.DEFAULT_ROUTE
    assert raised.value.result is failed
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.NETWORK_INTERFACES),
        call(CommandID.DEFAULT_ROUTE),
    ]
