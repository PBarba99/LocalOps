"""Tests for the read-only system information tool."""

from unittest.mock import MagicMock, call

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID
from localops.tools.system import get_system_info


def test_get_system_info_returns_labeled_command_output() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.side_effect = [
        CommandResult("test-server\n", "", 0),
        CommandResult('PRETTY_NAME="Debian GNU/Linux 12"\n', "", 0),
        CommandResult("Linux test-server 6.1.0 x86_64 GNU/Linux\n", "", 0),
        CommandResult("up 12 days, 3 hours\n", "", 0),
    ]

    output = get_system_info(ssh)

    assert output == (
        "Hostname:\ntest-server\n\n"
        'OS release:\nPRETTY_NAME="Debian GNU/Linux 12"\n\n'
        "Kernel:\nLinux test-server 6.1.0 x86_64 GNU/Linux\n\n"
        "Uptime:\nup 12 days, 3 hours"
    )
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.HOSTNAME),
        call(CommandID.OS_RELEASE),
        call(CommandID.KERNEL_INFO),
        call(CommandID.UPTIME),
    ]


def test_get_system_info_stops_after_first_failed_command() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "os-release unavailable\n", 1)
    ssh.run_approved_command.side_effect = [
        CommandResult("test-server\n", "", 0),
        failed,
    ]

    with pytest.raises(ToolCommandError) as raised:
        get_system_info(ssh)

    assert raised.value.command_id is CommandID.OS_RELEASE
    assert raised.value.result is failed
    assert ssh.run_approved_command.call_args_list == [
        call(CommandID.HOSTNAME),
        call(CommandID.OS_RELEASE),
    ]
