"""Tests for the read-only memory usage tool."""

from unittest.mock import MagicMock

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError
from localops.tools.memory import get_memory_usage
from localops.tools.registry import CommandID


def test_get_memory_usage_returns_labeled_output() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.return_value = CommandResult(
        "Mem: 15Gi 4Gi 6Gi\n",
        "",
        0,
    )

    output = get_memory_usage(ssh)

    assert output == "Memory usage:\nMem: 15Gi 4Gi 6Gi"
    ssh.run_approved_command.assert_called_once_with(CommandID.MEMORY_USAGE)


def test_get_memory_usage_raises_with_failed_command_details() -> None:
    ssh = MagicMock()
    failed = CommandResult("", "free: command failed\n", 1)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_memory_usage(ssh)

    assert raised.value.command_id is CommandID.MEMORY_USAGE
    assert raised.value.result is failed
