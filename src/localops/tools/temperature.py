"""Read-only kernel thermal-zone temperature inspection."""

import re

from ..ssh_client import SSHClient
from .errors import require_success
from .registry import CommandID


def _format_temperature(raw: str) -> str:
    """Convert integer millidegrees exactly, without floating-point rounding."""

    if raw == "Unavailable":
        return "Unavailable"
    if re.fullmatch(r"-?[0-9]+", raw) is None:
        return "Unavailable (invalid reading)"
    try:
        millidegrees = int(raw)
    except ValueError:
        return "Unavailable (invalid reading)"

    whole, fraction = divmod(abs(millidegrees), 1000)
    sign = "-" if millidegrees < 0 else ""
    decimals = f"{fraction:03d}".rstrip("0")
    number = f"{sign}{whole}"
    if decimals:
        number += f".{decimals}"
    return f"{number}°C"


def get_temperature_readings(ssh: SSHClient) -> str:
    """Return labeled thermal readings, preserving unavailable zones."""

    result = ssh.run_approved_command(CommandID.THERMAL_READINGS)
    stdout = require_success(CommandID.THERMAL_READINGS, result)
    readings: list[str] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 3 or not fields[0].strip() or not fields[1].strip():
            readings.append("Unavailable (malformed thermal-zone record)")
            continue
        zone, zone_type, raw = fields
        readings.append(f"{zone} ({zone_type}): {_format_temperature(raw)}")

    display = "\n".join(readings) or "No thermal zones reported"
    return f"Thermal zone readings:\n{display}"
