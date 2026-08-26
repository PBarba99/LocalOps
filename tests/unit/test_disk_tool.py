"""Tests for the read-only disk usage tool."""

from unittest.mock import MagicMock

import pytest

from localops.ssh_client import CommandResult
from localops.tools.disk import get_disk_usage
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID


def test_get_disk_usage_returns_labeled_output() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.return_value = CommandResult(
        "Filesystem Size Used Avail Use% Mounted on\n/dev/sda1 100G 40G 60G 40% /\n",
        "",
        0,
    )

    output = get_disk_usage(ssh)

    assert output == (
        "Disk usage:\n"
        "Filesystem Size Used Avail Use% Mounted on\n"
        "/dev/sda1 100G 40G 60G 40% /"
    )
    ssh.run_approved_command.assert_called_once_with(CommandID.DISK_USAGE)


def test_get_disk_usage_raises_with_failed_command_details() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "df: command failed\n", 1)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_disk_usage(ssh)

    assert raised.value.command_id is CommandID.DISK_USAGE
    assert raised.value.result is failed
