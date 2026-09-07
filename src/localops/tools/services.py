"""Read-only systemd service status tool."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_service_status(ssh: SSHClient) -> str:
    """Return running and failed systemd services."""

    sections = (
        ("Running services", CommandID.RUNNING_SERVICES),
        ("Failed services", CommandID.FAILED_SERVICES),
    )
    output: list[str] = []

    for label, command_id in sections:
        result = ssh.run_approved_command(command_id)
        stdout = require_success(command_id, result).rstrip()
        display = stdout if stdout.strip() else "None"
        output.append(f"{label}:\n{display}")

    return "\n\n".join(output)
