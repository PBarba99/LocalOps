"""Tests for application-owned non-command decisions."""

from types import MappingProxyType

import pytest

from localops.request_policy import (
    CONTROL_RESPONSES,
    ControlActionID,
    lookup_control_response,
)


EXPECTED_RESPONSE = (
    "I can only help with questions that can be answered using the available "
    "read-only server inspection tools."
)


def test_control_responses_contain_only_the_unsupported_request_decision() -> None:
    assert isinstance(CONTROL_RESPONSES, MappingProxyType)
    assert dict(CONTROL_RESPONSES) == {
        ControlActionID.DECLINE_UNSUPPORTED_REQUEST: EXPECTED_RESPONSE
    }
    assert set(ControlActionID) == {ControlActionID.DECLINE_UNSUPPORTED_REQUEST}


def test_lookup_returns_fixed_unsupported_request_response() -> None:
    assert (
        lookup_control_response(ControlActionID.DECLINE_UNSUPPORTED_REQUEST)
        == EXPECTED_RESPONSE
    )


def test_control_response_cannot_be_replaced_or_deleted() -> None:
    with pytest.raises(TypeError):
        CONTROL_RESPONSES[ControlActionID.DECLINE_UNSUPPORTED_REQUEST] = (  # type: ignore[index]
            "Injected"
        )

    with pytest.raises(TypeError):
        del CONTROL_RESPONSES[ControlActionID.DECLINE_UNSUPPORTED_REQUEST]  # type: ignore[attr-defined]

    assert (
        lookup_control_response(ControlActionID.DECLINE_UNSUPPORTED_REQUEST)
        == EXPECTED_RESPONSE
    )


@pytest.mark.parametrize(
    "untrusted_id",
    [
        "decline_unsupported_request",
        "DECLINE_UNSUPPORTED_REQUEST",
        "decline_unsupported_request; get_disk_usage",
        "$(get_disk_usage)",
        "",
        None,
    ],
)
def test_lookup_rejects_unknown_and_injected_action_ids(
    untrusted_id: object,
) -> None:
    with pytest.raises(ValueError, match="Unknown control action ID"):
        lookup_control_response(untrusted_id)  # type: ignore[arg-type]
