"""Tests for the read-only CPU load tool."""

from unittest.mock import MagicMock, call

import pytest

from localops.ssh_client import CommandResult
from localops.tools.cpu import get_cpu_load
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID


def test_get_cpu_load_returns_labeled_command_output() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult("8\n", "", 0),
        CommandResult("0.24 0.18 0.12 1/842 2031\n", "", 0),
    ]

    output = get_cpu_load(ssh)

    assert output == (
        "CPU count:\n8\n\n"
        "Load average:\n0.24 0.18 0.12 1/842 2031"
    )
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.CPU_COUNT),
        call(CommandID.LOAD_AVERAGE),
    ]


def test_get_cpu_load_stops_when_cpu_count_fails() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "nproc: command failed\n", 1)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_cpu_load(ssh)

    assert raised.value.command_id is CommandID.CPU_COUNT
    assert raised.value.result is failed
    ssh.run_approved_command.assert_called_once_with(CommandID.CPU_COUNT)


def test_get_cpu_load_stops_when_load_average_fails() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "load average unavailable\n", 1)
    ssh.run_approved_command.side_effect = [
        CommandResult("8\n", "", 0),
        failed,
    ]

    with pytest.raises(ToolCommandError) as raised:
        get_cpu_load(ssh)

    assert raised.value.command_id is CommandID.LOAD_AVERAGE
    assert raised.value.result is failed
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.CPU_COUNT),
        call(CommandID.LOAD_AVERAGE),
    ]
