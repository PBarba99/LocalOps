"""Restricted SSH transport boundary."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


class SSHClient:
    """Run internally selected commands; never accept model-generated shell text."""

    def run_approved_command(self, command_id: str) -> CommandResult:
        raise NotImplementedError(f"SSH command {command_id!r} is not implemented")
