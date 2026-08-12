"""System information tool placeholder."""

from ..ssh_client import SSHClient


def get_system_info(ssh: SSHClient) -> str:
    """Return OS, kernel, hostname, and uptime information."""
    raise NotImplementedError("get_system_info is not implemented")

