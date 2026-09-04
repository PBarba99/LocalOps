"""Read-only CPU load tool."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_cpu_load(ssh: SSHClient) -> str:
    """Return the CPU count and current Linux load averages."""

    sections = (
        ("CPU count", CommandID.CPU_COUNT),
        ("Load average", CommandID.LOAD_AVERAGE),
    )
    output: list[str] = []

    for label, command_id in sections:
        result = ssh.run_approved_command(command_id)
        stdout = require_success(command_id, result).rstrip()
        output.append(f"{label}:\n{stdout}")

    return "\n\n".join(output)
