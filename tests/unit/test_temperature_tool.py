"""Tests for exact, read-only thermal-zone reporting."""

from unittest.mock import MagicMock

import pytest

from localops.ssh_client import CommandResult
from localops.tools.errors import ToolCommandError
from localops.tools.registry import CommandID
from localops.tools.temperature import get_temperature_readings


def test_temperature_tool_preserves_names_and_unavailable_zones() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.return_value = CommandResult(
        "thermal_zone0\tacpitz\t27800\n"
        "thermal_zone1\tINT3400 Thermal\t20000\n"
        "thermal_zone2\tx86_pkg_temp\t41000\n"
        "thermal_zone3\tiwlwifi_1\tUnavailable\n",
        "",
        0,
    )

    output = get_temperature_readings(ssh)

    assert output == (
        "Thermal zone readings:\n"
        "thermal_zone0 (acpitz): 27.8°C\n"
        "thermal_zone1 (INT3400 Thermal): 20°C\n"
        "thermal_zone2 (x86_pkg_temp): 41°C\n"
        "thermal_zone3 (iwlwifi_1): Unavailable"
    )
    ssh.run_approved_command.assert_called_once_with(CommandID.THERMAL_READINGS)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", "0°C"),
        ("41001", "41.001°C"),
        ("41010", "41.01°C"),
        ("-12345", "-12.345°C"),
        ("-1", "-0.001°C"),
        ("Unavailable", "Unavailable"),
        ("", "Unavailable (invalid reading)"),
        ("NaN", "Unavailable (invalid reading)"),
        ("41000.5", "Unavailable (invalid reading)"),
        ("41_000", "Unavailable (invalid reading)"),
    ],
)
def test_temperature_tool_converts_or_labels_readings(
    raw: str, expected: str
) -> None:
    ssh = MagicMock()
    ssh.run_approved_command.return_value = CommandResult(
        f"thermal_zone0\tUnknown\t{raw}\n", "", 0
    )

    output = get_temperature_readings(ssh)

    assert output == f"Thermal zone readings:\nthermal_zone0 (Unknown): {expected}"


@pytest.mark.parametrize("stdout", ["", " \n\t\n"])
def test_temperature_tool_reports_absent_zones(stdout: str) -> None:
    ssh = MagicMock()
    ssh.run_approved_command.return_value = CommandResult(stdout, "", 0)

    assert get_temperature_readings(ssh) == (
        "Thermal zone readings:\nNo thermal zones reported"
    )


def test_temperature_tool_keeps_valid_readings_after_malformed_records() -> None:
    ssh = MagicMock()
    ssh.run_approved_command.return_value = CommandResult(
        "incomplete record\nthermal_zone1\tx86_pkg_temp\t41000\n", "", 0
    )

    assert get_temperature_readings(ssh) == (
        "Thermal zone readings:\nUnavailable (malformed thermal-zone record)\n"
        "thermal_zone1 (x86_pkg_temp): 41°C"
    )


def test_temperature_tool_preserves_command_failure() -> None:
    ssh = MagicMock()
    failed = CommandResult("partial output", "command failed", 1)
    ssh.run_approved_command.return_value = failed

    with pytest.raises(ToolCommandError) as raised:
        get_temperature_readings(ssh)

    assert raised.value.command_id is CommandID.THERMAL_READINGS
    assert raised.value.result is failed
    ssh.run_approved_command.assert_called_once_with(CommandID.THERMAL_READINGS)
