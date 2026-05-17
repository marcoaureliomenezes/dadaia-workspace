"""Unit tests for features/telemetry/reader/allowlist.py (T-AM-05).

T1 CRITICAL: zero leakage of content/text/messages/snapshot/thinking/
prompt/response into telemetry output.  The test_no_forbidden_in_output
test is the critical gate.
"""
from __future__ import annotations

import pytest

from dadaia_workspace.features.telemetry.reader.allowlist import (
    FORBIDDEN_KEYS,
    MAX_TOKEN_COUNT_PER_EVENT,
    allowlist_event,
    is_forbidden_field_present,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_ASSISTANT: dict = {
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


def _make_agent_name_event(session_id: str = "test-session-001") -> dict:
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
# Tests
# ---------------------------------------------------------------------------


class TestStripsTopLevelForbiddenKeys:
    def test_strips_forbidden_top_level_keys(self) -> None:
        raw = {
            "sessionId": "test-session-001",
            "timestamp": "2026-05-17T10:00:00.000Z",
            "type": "user",
            "uuid": "uuid-1",
            # Forbidden — must be stripped
            "content": "Hello, do something dangerous",
            "text": "raw text",
            "messages": ["msg1", "msg2"],
        }
        result = allowlist_event(raw)
        assert result is not None
        assert "content" not in result
        assert "text" not in result
        assert "messages" not in result
        # Allowed keys survive
        assert result["sessionId"] == "test-session-001"
        assert result["type"] == "user"


class TestStripsMessageNestedForbidden:
    def test_strips_forbidden_in_message(self) -> None:
        """message.content and message.thinking must be stripped; usage/model kept."""
        raw = {
            "sessionId": "test-session-002",
            "timestamp": "2026-05-17T10:01:00.000Z",
            "type": "assistant",
            "uuid": "uuid-2",
            "message": {
                "model": "claude-opus-4-7",
                "content": "This should be stripped",
                "thinking": "Internal chain of thought — strip this",
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 100,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
        }
        result = allowlist_event(raw)
        assert result is not None
        # Forbidden nested keys must not appear
        assert is_forbidden_field_present(result) is False
        # usage and model should be present
        assert "usage" in result
        assert result["model"] == "claude-opus-4-7"


class TestMissingRequiredKeys:
    def test_missing_required_keys_returns_none(self) -> None:
        """Event missing sessionId must return None."""
        raw = {
            "timestamp": "2026-05-17T10:00:00.000Z",
            "type": "assistant",
        }
        assert allowlist_event(raw) is None

    def test_missing_timestamp_returns_none(self) -> None:
        raw = {
            "sessionId": "s1",
            "type": "assistant",
        }
        assert allowlist_event(raw) is None

    def test_missing_type_returns_none(self) -> None:
        raw = {
            "sessionId": "s1",
            "timestamp": "2026-05-17T10:00:00.000Z",
        }
        assert allowlist_event(raw) is None

    def test_non_dict_returns_none(self) -> None:
        assert allowlist_event("string") is None  # type: ignore[arg-type]
        assert allowlist_event(None) is None  # type: ignore[arg-type]
        assert allowlist_event([1, 2, 3]) is None  # type: ignore[arg-type]


class TestAssistantUsageExtraction:
    def test_assistant_extracts_usage(self) -> None:
        """Full assistant event: all 4 token counts + model must be in output."""
        result = allowlist_event(_BASE_ASSISTANT)
        assert result is not None
        assert "usage" in result
        usage = result["usage"]
        assert usage["input_tokens"] == 1200
        assert usage["output_tokens"] == 400
        assert usage["cache_creation_input_tokens"] == 300
        assert usage["cache_read_input_tokens"] == 150
        assert result["model"] == "claude-opus-4-7"

    def test_assistant_no_message_no_usage(self) -> None:
        """Assistant event without message field should still parse (no usage)."""
        raw = {
            "sessionId": "s1",
            "timestamp": "2026-05-17T10:00:00.000Z",
            "type": "assistant",
            "uuid": "u1",
        }
        result = allowlist_event(raw)
        assert result is not None
        assert "usage" not in result
        assert "model" not in result


class TestNonAssistantEvents:
    def test_non_assistant_no_usage_required(self) -> None:
        """agent-name event passes without usage fields."""
        raw = _make_agent_name_event()
        result = allowlist_event(raw)
        assert result is not None
        assert result["type"] == "agent-name"
        assert result["agentName"] == "software-engineer"
        # No usage in output for non-assistant
        assert "usage" not in result

    def test_ai_title_event_passes(self) -> None:
        raw = {
            "sessionId": "s1",
            "timestamp": "2026-05-17T10:00:00.000Z",
            "type": "ai-title",
            "uuid": "u1",
            "aiTitle": "Implement telemetry reader",
        }
        result = allowlist_event(raw)
        assert result is not None
        assert result["aiTitle"] == "Implement telemetry reader"


class TestTokenBounds:
    def test_token_bounds_marks_suspect(self) -> None:
        """input_tokens exceeding MAX → _suspect=True, event NOT dropped."""
        raw = dict(_BASE_ASSISTANT)
        raw["message"] = {
            "model": "claude-opus-4-7",
            "usage": {
                "input_tokens": 3_000_000,  # exceeds 2_000_000
                "output_tokens": 400,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }
        result = allowlist_event(raw)
        assert result is not None, "Event must NOT be dropped"
        assert result.get("_suspect") is True

    def test_token_negative_marks_suspect(self) -> None:
        """Negative output_tokens → _suspect=True, event NOT dropped."""
        raw = dict(_BASE_ASSISTANT)
        raw["message"] = {
            "model": "claude-opus-4-7",
            "usage": {
                "input_tokens": 500,
                "output_tokens": -1,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }
        result = allowlist_event(raw)
        assert result is not None, "Event must NOT be dropped"
        assert result.get("_suspect") is True

    def test_zero_tokens_not_suspect(self) -> None:
        """Zero counts are valid (not suspect)."""
        raw = dict(_BASE_ASSISTANT)
        raw["message"] = {
            "model": "claude-opus-4-7",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }
        result = allowlist_event(raw)
        assert result is not None
        assert "_suspect" not in result

    def test_exactly_max_not_suspect(self) -> None:
        """Exactly MAX_TOKEN_COUNT_PER_EVENT is acceptable."""
        raw = dict(_BASE_ASSISTANT)
        raw["message"] = {
            "model": "claude-opus-4-7",
            "usage": {
                "input_tokens": MAX_TOKEN_COUNT_PER_EVENT,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }
        result = allowlist_event(raw)
        assert result is not None
        assert "_suspect" not in result


class TestIsForbiddenFieldPresent:
    def test_is_forbidden_field_present_deep(self) -> None:
        """Nested dict 4 levels deep containing 'prompt' → True."""
        deep = {"level1": {"level2": {"level3": {"level4": {"prompt": "secret"}}}}}
        assert is_forbidden_field_present(deep) is True

    def test_not_forbidden_in_clean_dict(self) -> None:
        clean = {"sessionId": "s1", "type": "assistant", "model": "claude-opus-4-7"}
        assert is_forbidden_field_present(clean) is False

    def test_forbidden_in_list(self) -> None:
        data = {"items": [{"content": "leaked"}]}
        assert is_forbidden_field_present(data) is True

    def test_all_forbidden_keys_detected(self) -> None:
        for key in FORBIDDEN_KEYS:
            d = {key: "value"}
            assert is_forbidden_field_present(d) is True, f"Key {key!r} not detected"


class TestImmutability:
    def test_returns_new_dict_not_mutation(self) -> None:
        """The original input dict must not be mutated."""
        import copy

        raw = copy.deepcopy(_BASE_ASSISTANT)
        raw["content"] = "should not be touched in original"
        original_keys = set(raw.keys())
        result = allowlist_event(raw)
        assert result is not None
        # The original dict retains all its original keys
        assert set(raw.keys()) == original_keys
        assert raw["content"] == "should not be touched in original"
        # The output does not contain the forbidden key
        assert "content" not in result


class TestNoForbiddenInOutput:
    """T1 CRITICAL gate test.

    Construct a maximally adversarial raw input that contains ALL forbidden
    keys at multiple nesting levels, then assert the allowlist produces
    zero forbidden keys in its output.
    """

    def test_no_forbidden_in_output(self) -> None:
        adversarial_raw: dict = {
            # Required fields
            "sessionId": "adversarial-session-001",
            "timestamp": "2026-05-17T12:00:00.000Z",
            "type": "assistant",
            # Allowed top-level fields
            "uuid": "ffff-eeee-dddd-cccc",
            "cwd": "/home/operator",
            "gitBranch": "main",
            "isSidechain": False,
            "slug": "",
            "entrypoint": "cli",
            "agentName": None,
            "aiTitle": None,
            # ALL forbidden keys at top level
            "content": "LEAK: top-level content",
            "text": "LEAK: top-level text",
            "messages": ["LEAK: message 1", "LEAK: message 2"],
            "snapshot": {"state": "LEAK: snapshot data"},
            "thinking": "LEAK: chain of thought",
            "prompt": "LEAK: system prompt",
            "response": "LEAK: raw response",
            # message block with forbidden keys nested
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
                    # Forbidden keys inside usage too
                    "content": "LEAK: usage.content",
                    "thinking": "LEAK: usage.thinking",
                },
            },
        }

        result = allowlist_event(adversarial_raw)
        assert result is not None, "Valid event must not return None"

        # THE CRITICAL ASSERTION — zero forbidden fields anywhere in output
        assert is_forbidden_field_present(result) is False, (
            f"Forbidden field found in output: {result!r}"
        )

        # Verify useful data is still present
        assert "usage" in result
        assert result["model"] == "claude-opus-4-7"
        assert result["sessionId"] == "adversarial-session-001"
