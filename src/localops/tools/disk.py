"""Read-only disk usage tool."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_disk_usage(ssh: SSHClient) -> str:
    """Return current filesystem capacity and free space."""

    result = ssh.run_approved_command(CommandID.DISK_USAGE)
    stdout = require_success(CommandID.DISK_USAGE, result).rstrip()
    return f"Disk usage:\n{stdout}"
