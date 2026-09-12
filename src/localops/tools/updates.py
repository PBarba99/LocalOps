"""Read-only package-update inspection using cached APT metadata."""

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def get_package_updates(ssh: SSHClient) -> str:
    """Return available upgrades and the last recorded periodic APT refresh."""

    updates_result = ssh.run_approved_command(CommandID.AVAILABLE_UPDATES)
    updates = require_success(CommandID.AVAILABLE_UPDATES, updates_result)
    lines = updates.splitlines()
    if lines and lines[0].strip() in {"Listing...", "Listing... Done"}:
        lines = lines[1:]
    updates_display = "\n".join(lines).strip()
    if not updates_display:
        updates_display = "None reported by cached APT metadata"

    refresh_result = ssh.run_approved_command(CommandID.APT_REFRESH_TIMESTAMP)
    refresh = require_success(CommandID.APT_REFRESH_TIMESTAMP, refresh_result)
    refresh_display = refresh.strip() or "Unknown"

    return (
        f"Available package updates (cached APT metadata):\n{updates_display}\n\n"
        f"Last recorded periodic APT refresh:\n{refresh_display}\n\n"
        "No metadata refresh or package installation was performed. "
        "The refresh timestamp does not guarantee all repositories are current."
    )
