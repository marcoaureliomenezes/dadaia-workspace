"""Unit tests for features/telemetry/reader/allowlist.py (T-AM-05).

T1 CRITICAL: zero leakage of content/text/messages/snapshot/thinking/
prompt/response into telemetry output.  The test_no_forbidden_in_output
test is the critical gate — kept verbatim (paired with the reader_claude
no-forbidden-in-db executed-path guarantee).
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.reader.allowlist import (
    FORBIDDEN_KEYS,
    MAX_TOKEN_COUNT_PER_EVENT,
    allowlist_event,
    is_forbidden_field_present,
)

_BASE_ASSISTANT: dict[str, Any] = {
    "sessionId": "test-session-001",
    "timestamp": "2026-05-17T10:00:00.000Z",
    "type": "assistant",
    "uuid": "aaaa-bbbb-cccc-dddd",
    "cwd": "/home/operator/workspace",
    "gitBranch": "main",
    "isSidechain": False,
    "slug": "",
    "entrypoint": "cli",
    "agentName": None,
    "aiTitle": None,
    "message": {
        "model": "claude-opus-4-7",
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 400,
            "cache_creation_input_tokens": 300,
            "cache_read_input_tokens": 150,
        },
    },
}


def _make_agent_name_event(session_id: str = "test-session-001") -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "timestamp": "2026-05-17T10:00:00.000Z",
        "type": "agent-name",
        "uuid": "uuid-agent-1",
        "agentName": "software-engineer",
        "cwd": "/home/operator/workspace",
        "gitBranch": "main",
        "isSidechain": False,
        "slug": "",
        "entrypoint": "cli",
        "aiTitle": None,
    }


# ---------------------------------------------------------------------------
# Kept: the sanitizer contract — no-mutation-of-input + strips-forbidden (both
# top-level and message-nested), merged into one test.
# ---------------------------------------------------------------------------


def test_sanitizer_contract_strips_forbidden_and_never_mutates_input() -> None:
    raw = copy.deepcopy(_BASE_ASSISTANT)
    raw["content"] = "LEAK: top-level content"
    raw["text"] = "raw text"
    raw["messages"] = ["msg1", "msg2"]
    raw["message"]["content"] = "This should be stripped"
    raw["message"]["thinking"] = "Internal chain of thought — strip this"
    original_keys = set(raw.keys())

    result = allowlist_event(raw)

    assert result is not None
    assert "content" not in result
    assert "text" not in result
    assert "messages" not in result
    assert is_forbidden_field_present(result) is False
    assert result["sessionId"] == "test-session-001"
    assert result["type"] == "assistant"
    assert "usage" in result
    assert result["model"] == "claude-opus-4-7"

    # The original dict is untouched — no mutation.
    assert set(raw.keys()) == original_keys
    assert raw["content"] == "LEAK: top-level content"


# ---------------------------------------------------------------------------
# Required-key rejections + usage extraction + event-type variants — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expect_none", "assert_fn"),
    [
        pytest.param(
            {"timestamp": "2026-05-17T10:00:00.000Z", "type": "assistant"},
            True,
            None,
            id="missing-session-id-none",
        ),
        pytest.param(
            {"sessionId": "s1", "type": "assistant"}, True, None, id="missing-timestamp-none"
        ),
        pytest.param(
            {"sessionId": "s1", "timestamp": "2026-05-17T10:00:00.000Z"},
            True,
            None,
            id="missing-type-none",
        ),
        pytest.param("string", True, None, id="non-dict-string-none"),
        pytest.param(None, True, None, id="non-dict-none-value-none"),
        pytest.param([1, 2, 3], True, None, id="non-dict-list-none"),
        pytest.param(
            _BASE_ASSISTANT,
            False,
            lambda r: (
                r["usage"]["input_tokens"] == 1200
                and r["usage"]["output_tokens"] == 400
                and r["usage"]["cache_creation_input_tokens"] == 300
                and r["usage"]["cache_read_input_tokens"] == 150
                and r["model"] == "claude-opus-4-7"
            ),
            id="assistant-full-usage-extraction",
        ),
        pytest.param(
            {
                "sessionId": "s1",
                "timestamp": "2026-05-17T10:00:00.000Z",
                "type": "assistant",
                "uuid": "u1",
            },
            False,
            lambda r: "usage" not in r and "model" not in r,
            id="assistant-no-message-no-usage",
        ),
        pytest.param(
            _make_agent_name_event(),
            False,
            lambda r: (
                r["type"] == "agent-name"
                and r["agentName"] == "software-engineer"
                and "usage" not in r
            ),
            id="non-assistant-agent-name-no-usage-required",
        ),
        pytest.param(
            {
                "sessionId": "s1",
                "timestamp": "2026-05-17T10:00:00.000Z",
                "type": "ai-title",
                "uuid": "u1",
                "aiTitle": "Implement telemetry reader",
            },
            False,
            lambda r: r["aiTitle"] == "Implement telemetry reader",
            id="ai-title-event-passes",
        ),
    ],
)
def test_required_keys_and_event_type_matrix(raw, expect_none: bool, assert_fn) -> None:  # type: ignore[no-untyped-def]
    result = allowlist_event(raw)
    if expect_none:
        assert result is None
    else:
        assert result is not None
        assert assert_fn(result)


# ---------------------------------------------------------------------------
# Suspect-bounds boundary rows: over-max / negative / zero / exact-max — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens", "expect_suspect"),
    [
        pytest.param(3_000_000, 400, True, id="over-max-input-suspect"),
        pytest.param(500, -1, True, id="negative-output-suspect"),
        pytest.param(0, 0, False, id="zero-tokens-not-suspect"),
        pytest.param(MAX_TOKEN_COUNT_PER_EVENT, 0, False, id="exactly-max-not-suspect"),
    ],
)
def test_token_bounds_matrix(input_tokens: int, output_tokens: int, expect_suspect: bool) -> None:
    raw = dict(_BASE_ASSISTANT)
    raw["message"] = {
        "model": "claude-opus-4-7",
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
    result = allowlist_event(raw)
    assert result is not None, "Event must NOT be dropped even when suspect"
    if expect_suspect:
        assert result.get("_suspect") is True
    else:
        assert "_suspect" not in result


# ---------------------------------------------------------------------------
# T1 CRITICAL gate — zero forbidden fields anywhere in an adversarial payload.
# Kept verbatim.
# ---------------------------------------------------------------------------


def test_no_forbidden_in_output() -> None:
    """Construct a maximally adversarial raw input that contains ALL forbidden
    keys at multiple nesting levels, then assert the allowlist produces zero
    forbidden keys in its output."""
    adversarial_raw: dict[str, Any] = {
        "sessionId": "adversarial-session-001",
        "timestamp": "2026-05-17T12:00:00.000Z",
        "type": "assistant",
        "uuid": "ffff-eeee-dddd-cccc",
        "cwd": "/home/operator",
        "gitBranch": "main",
        "isSidechain": False,
        "slug": "",
        "entrypoint": "cli",
        "agentName": None,
        "aiTitle": None,
        "content": "LEAK: top-level content",
        "text": "LEAK: top-level text",
        "messages": ["LEAK: message 1", "LEAK: message 2"],
        "snapshot": {"state": "LEAK: snapshot data"},
        "thinking": "LEAK: chain of thought",
        "prompt": "LEAK: system prompt",
        "response": "LEAK: raw response",
        "message": {
            "model": "claude-opus-4-7",
            "content": "LEAK: message.content",
            "text": "LEAK: message.text",
            "thinking": "LEAK: message.thinking",
            "snapshot": "LEAK: message.snapshot",
            "prompt": "LEAK: message.prompt",
            "response": "LEAK: message.response",
            "messages": ["LEAK: nested messages"],
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_creation_input_tokens": 100,
                "cache_read_input_tokens": 50,
                "content": "LEAK: usage.content",
                "thinking": "LEAK: usage.thinking",
            },
        },
    }

    result = allowlist_event(adversarial_raw)
    assert result is not None, "Valid event must not return None"

    assert is_forbidden_field_present(result) is False, (
        f"Forbidden field found in output: {result!r}"
    )
    assert "usage" in result
    assert result["model"] == "claude-opus-4-7"
    assert result["sessionId"] == "adversarial-session-001"

    # Sanity: every key in FORBIDDEN_KEYS is actually caught by the detector.
    for key in FORBIDDEN_KEYS:
        assert is_forbidden_field_present({key: "value"}) is True, f"Key {key!r} not detected"
