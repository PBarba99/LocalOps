"""Tests for model-visible tool definitions and strict invocation."""

from unittest.mock import MagicMock, patch

import pytest

from localops.request_policy import ControlActionID, lookup_control_response
from localops.tools.registry import ToolRegistry


def test_definitions_expose_only_five_zero_argument_actions() -> None:
    definitions = ToolRegistry().definitions()

    assert [definition["function"]["name"] for definition in definitions] == [
        "get_system_info",
        "get_memory_usage",
        "get_disk_usage",
        "get_cpu_load",
        "decline_unsupported_request",
    ]
    for definition in definitions:
        assert definition["type"] == "function"
        assert definition["function"]["parameters"] == {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        serialized = repr(definition).lower()
        assert "command_id" not in serialized
        assert "shell" not in serialized
        assert "ssh" not in serialized


def test_mutating_returned_definitions_does_not_change_registry() -> None:
    registry = ToolRegistry()
    definitions = registry.definitions()
    definitions[0]["function"]["name"] = "run_arbitrary_command"
    definitions.append({"type": "function", "function": {"name": "injected"}})

    fresh_definitions = registry.definitions()

    assert [definition["function"]["name"] for definition in fresh_definitions] == [
        "get_system_info",
        "get_memory_usage",
        "get_disk_usage",
        "get_cpu_load",
        "decline_unsupported_request",
    ]


@pytest.mark.parametrize(
    ("name", "module", "function_name", "expected"),
    [
        ("get_system_info", "system", "get_system_info", "system output"),
        ("get_memory_usage", "memory", "get_memory_usage", "memory output"),
        ("get_disk_usage", "disk", "get_disk_usage", "disk output"),
        ("get_cpu_load", "cpu", "get_cpu_load", "CPU output"),
    ],
)
def test_invoke_routes_only_fixed_tool_names(
    name: str, module: str, function_name: str, expected: str
) -> None:
    ssh = MagicMock()
    registry = ToolRegistry(ssh=ssh)

    with patch(
        f"localops.tools.{module}.{function_name}", return_value=expected
    ) as tool:
        result = registry.invoke(name, {})

    tool.assert_called_once_with(ssh)
    assert result == expected


@pytest.mark.parametrize(
    "unknown_name",
    ["run_command", "get_disk_usage; whoami", "GET_SYSTEM_INFO", "", None],
)
def test_invoke_rejects_unknown_and_injected_names(unknown_name: object) -> None:
    ssh = MagicMock()
    registry = ToolRegistry(ssh=ssh)

    with pytest.raises(ValueError, match="Unknown tool"):
        registry.invoke(unknown_name, {})  # type: ignore[arg-type]

    ssh.assert_not_called()


@pytest.mark.parametrize(
    "arguments",
    [{"command": "whoami"}, {"path": "/"}, {"unexpected": True}, None, []],
)
def test_invoke_rejects_all_arguments(arguments: object) -> None:
    ssh = MagicMock()
    registry = ToolRegistry(ssh=ssh)

    with pytest.raises(ValueError, match="accepts no arguments"):
        registry.invoke("get_disk_usage", arguments)  # type: ignore[arg-type]

    ssh.assert_not_called()


def test_invoke_requires_an_ssh_client() -> None:
    with pytest.raises(RuntimeError, match="no SSH client"):
        ToolRegistry().invoke("get_system_info", {})


def test_decline_returns_fixed_response_without_an_ssh_client() -> None:
    result = ToolRegistry().invoke("decline_unsupported_request", {})

    assert result == lookup_control_response(
        ControlActionID.DECLINE_UNSUPPORTED_REQUEST
    )


@pytest.mark.parametrize(
    "arguments",
    [{"question": "What day is it?"}, {"command": "whoami"}, None, []],
)
def test_decline_rejects_all_arguments(arguments: object) -> None:
    with pytest.raises(ValueError, match="accepts no arguments"):
        ToolRegistry().invoke(
            "decline_unsupported_request", arguments  # type: ignore[arg-type]
        )
