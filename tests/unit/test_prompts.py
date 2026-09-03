"""Regression tests for the model's safety instructions."""

from localops.prompts import SYSTEM_PROMPT


def test_system_prompt_requires_exact_reported_units() -> None:
    assert "exactly as written in the tool output" in SYSTEM_PROMPT
    assert "183G, never 183 GB" in SYSTEM_PROMPT
    assert "6.6Gi, never 6.6 GiB" in SYSTEM_PROMPT


def test_system_prompt_requires_read_only_refusal() -> None:
    assert "cannot modify the server in any way" in SYSTEM_PROMPT
    assert "If the user requests a change" in SYSTEM_PROMPT
    assert SYSTEM_PROMPT.count("choose decline_unsupported_request") == 2
    assert "Never claim that you performed or will perform" in SYSTEM_PROMPT
    assert "Never print, suggest, or imitate shell commands" in SYSTEM_PROMPT


def test_system_prompt_declines_requests_outside_inspection_tools() -> None:
    assert "cannot be answered using the available read-only server" in SYSTEM_PROMPT
    assert "inspection tools, choose decline_unsupported_request" in SYSTEM_PROMPT
