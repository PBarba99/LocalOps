"""Read-only network status tool."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_network_status(ssh: SSHClient) -> str:
    """Return network interfaces, addresses, and the default route."""

    sections = (
        ("Network interfaces", CommandID.NETWORK_INTERFACES),
        ("Default route", CommandID.DEFAULT_ROUTE),
    )
    output: list[str] = []

    for label, command_id in sections:
        result = ssh.run_approved_command(command_id)
        stdout = require_success(command_id, result).rstrip()
        display = stdout if stdout.strip() else "None"
        output.append(f"{label}:\n{display}")

    return "\n\n".join(output)
