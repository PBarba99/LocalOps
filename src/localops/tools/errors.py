"""Failures raised by predefined read-only tools."""

from ..ssh_client import CommandResult
from .registry import CommandID


class ToolCommandError(RuntimeError):
    """An approved remote command completed with a non-zero exit code."""

    def __init__(self, command_id: CommandID, result: CommandResult) -> None:
        self.command_id = command_id
        self.result = result
        super().__init__(
            f"{command_id.name} failed with exit code {result.exit_code}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}"
        )


def require_success(command_id: CommandID, result: CommandResult) -> str:
    """Return stdout or raise with the complete failed command result."""

    if result.exit_code != 0:
        raise ToolCommandError(command_id, result)
    return result.stdout
