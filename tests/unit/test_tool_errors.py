"""Tests for failures reported by read-only tools."""

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError, require_success
from localops.tools.registry import CommandID


def test_require_success_returns_stdout() -> None:
    result = CommandResult(stdout="test-server\n", stderr="", exit_code=0)

    assert require_success(CommandID.HOSTNAME, result) == "test-server\n"


def test_failed_command_preserves_diagnostic_output() -> None:
    result = CommandResult(
        stdout="partial output\n",
        stderr="permission denied\n",
        exit_code=1,
    )

    with pytest.raises(ToolCommandError) as raised:
        require_success(CommandID.OS_RELEASE, result)

    error = raised.value
    assert error.command_id is CommandID.OS_RELEASE
    assert error.result is result
    assert "OS_RELEASE failed with exit code 1" in str(error)
    assert "partial output" in str(error)
    assert "permission denied" in str(error)
