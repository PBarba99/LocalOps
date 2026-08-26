"""Read-only memory usage tool."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_memory_usage(ssh: SSHClient) -> str:
    """Return current memory totals and availability."""

    result = ssh.run_approved_command(CommandID.MEMORY_USAGE)
    stdout = require_success(CommandID.MEMORY_USAGE, result).rstrip()
    return f"Memory usage:\n{stdout}"
