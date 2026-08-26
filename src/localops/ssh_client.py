"""Restricted SSH transport boundary."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic, sleep
from typing import TYPE_CHECKING

import paramiko

from .config import Settings

if TYPE_CHECKING:
    from .tools.registry import CommandID


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


@dataclass(frozen=True)
class SSHClient:
    """Run internally selected commands; never accept model-generated shell text."""

    settings: Settings
    connection_timeout: float = 10.0
    command_timeout: float = 10.0

    def __post_init__(self) -> None:
        if self.connection_timeout <= 0:
            raise ValueError("Connection timeout must be greater than zero")
        if self.command_timeout <= 0:
            raise ValueError("Command timeout must be greater than zero")

    @staticmethod
    def _create_paramiko_client() -> paramiko.SSHClient:
        """Create a client that trusts only SSH hosts already known locally."""

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        return client

    def check_connection(self) -> None:
        """Connect to the configured server and close without running a command."""

        client = self._create_paramiko_client()
        try:
            client.connect(
                hostname=self.settings.server_host,
                port=self.settings.server_port,
                username=self.settings.server_username,
                key_filename=str(self.settings.server_ssh_key),
                timeout=self.connection_timeout,
                banner_timeout=self.connection_timeout,
                auth_timeout=self.connection_timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        finally:
            client.close()

    def resolve_command(self, command_id: CommandID) -> str:
        """Resolve an approved identifier without accepting arbitrary shell text."""

        # Local import avoids the tools package importing SSHClient while this
        # module is still being initialized.
        from .tools.registry import lookup_command

        return lookup_command(command_id)

    def run_approved_command(self, command_id: CommandID) -> CommandResult:
        """Execute one fixed allowlisted command over SSH."""

        command = self.resolve_command(command_id)
        client = self._create_paramiko_client()
        try:
            client.connect(
                hostname=self.settings.server_host,
                port=self.settings.server_port,
                username=self.settings.server_username,
                key_filename=str(self.settings.server_ssh_key),
                timeout=self.connection_timeout,
                banner_timeout=self.connection_timeout,
                auth_timeout=self.connection_timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            _, stdout, _ = client.exec_command(command, timeout=self.command_timeout)
            return self._collect_result(stdout.channel)
        finally:
            client.close()

    def _collect_result(self, channel: paramiko.Channel) -> CommandResult:
        """Drain a command channel within a total wall-clock deadline."""

        deadline = monotonic() + self.command_timeout
        stdout = bytearray()
        stderr = bytearray()

        while True:
            while channel.recv_ready():
                stdout.extend(channel.recv(65536))
            while channel.recv_stderr_ready():
                stderr.extend(channel.recv_stderr(65536))

            if channel.exit_status_ready():
                return CommandResult(
                    stdout.decode("utf-8", errors="replace"),
                    stderr.decode("utf-8", errors="replace"),
                    channel.recv_exit_status(),
                )

            if monotonic() >= deadline:
                channel.close()
                raise TimeoutError(
                    f"Approved command exceeded {self.command_timeout:g} seconds"
                )

            sleep(0.01)
