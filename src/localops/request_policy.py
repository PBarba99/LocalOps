"""Application-owned decisions that never execute a server command."""

from enum import Enum, unique
from types import MappingProxyType


@unique
class ControlActionID(str, Enum):
    """Stable identifiers for non-command actions available to the agent."""

    DECLINE_UNSUPPORTED_REQUEST = "decline_unsupported_request"


# Construct the proxy inline so no mutable backing dictionary is retained.
CONTROL_RESPONSES = MappingProxyType(
    {
        ControlActionID.DECLINE_UNSUPPORTED_REQUEST: (
            "I can only help with questions that can be answered using the "
            "available read-only server inspection tools."
        ),
    }
)


def lookup_control_response(action_id: ControlActionID) -> str:
    """Return fixed application text for a recognized control action."""

    if not isinstance(action_id, ControlActionID):
        raise ValueError(f"Unknown control action ID: {action_id!r}")

    try:
        return CONTROL_RESPONSES[action_id]
    except KeyError as exc:
        raise ValueError(f"Unknown control action ID: {action_id!r}") from exc
