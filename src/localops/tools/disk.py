"""Disk usage tool placeholder."""

from ..ssh_client import SSHClient


def get_disk_usage(ssh: SSHClient) -> str:
    """Return current filesystem capacity and free space."""
    raise NotImplementedError("get_disk_usage is not implemented")
