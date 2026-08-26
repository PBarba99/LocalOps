"""Read-only system information tool."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_system_info(ssh: SSHClient) -> str:
    """Return OS, kernel, hostname, and uptime information."""

    sections = (
        ("Hostname", CommandID.HOSTNAME),
        ("OS release", CommandID.OS_RELEASE),
        ("Kernel", CommandID.KERNEL_INFO),
        ("Uptime", CommandID.UPTIME),
    )
    output: list[str] = []

    for label, command_id in sections:
        result = ssh.run_approved_command(command_id)
        stdout = require_success(command_id, result).rstrip()
        output.append(f"{label}:\n{stdout}")

    return "\n\n".join(output)
