"""Privacy allowlist for Claude Code telemetry events (T1 CRITICAL).

This module is the security boundary that prevents any conversation content
from leaking into the telemetry SQLite database.  It uses an ALLOWLIST
(not a denylist) approach: only explicitly declared keys survive filtering.

Decision references:
    D-AM-03   — Transcripts NEVER exposed. Allowlist in reader (not denylist).
    D-AM-13   — usage in event.message.usage.*; model in event.message.model
    D-AM-19   — Mark suspect events (don't drop); suspect=1 flag in output.
    T1 (CRITICAL) — Threat matrix T1: zero leakage of message content.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Approved top-level keys (applies to ALL event types)
# ---------------------------------------------------------------------------

ALLOWED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "sessionId",
        "timestamp",
        "cwd",
        "entrypoint",
        "gitBranch",
        "isSidechain",
        "slug",
        "uuid",
        "type",
        "agentName",
        "aiTitle",
    }
)

# Additional nested keys allowed for type=assistant events.
# These live under event.message.usage.* and event.message.model.
_ALLOWED_USAGE_KEYS: frozenset[str] = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    }
)

# ---------------------------------------------------------------------------
# Forbidden key set — used by is_forbidden_field_present() in tests and
# assertions.  Presence of any of these in output constitutes a T1 violation.
# ---------------------------------------------------------------------------

FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "content",
        "text",
        "messages",
        "snapshot",
        "thinking",
        "prompt",
        "response",
    }
)

# ---------------------------------------------------------------------------
# Token bound constant (D-AM-19 / devops T7)
# ---------------------------------------------------------------------------

MAX_TOKEN_COUNT_PER_EVENT: int = 2_000_000

# ---------------------------------------------------------------------------
# Required keys — events missing any of these are rejected (return None)
# ---------------------------------------------------------------------------

_REQUIRED_KEYS: frozenset[str] = frozenset({"sessionId", "timestamp", "type"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def allowlist_event(raw: object) -> dict | None:
    """Filter *raw* to only allowlisted keys, returning a new dict.

    Returns ``None`` when:
    - *raw* is not a dict.
    - Any required key (sessionId, timestamp, type) is absent.

    For ``type == "assistant"`` events:
    - ``message.usage.{input_tokens, output_tokens,
      cache_creation_input_tokens, cache_read_input_tokens}`` and
      ``message.model`` are extracted into the output dict.
    - All other ``message.*`` keys are stripped.

    For other event types only top-level allowlisted keys survive.

    If any token count field exceeds ``MAX_TOKEN_COUNT_PER_EVENT`` or is
    negative, the returned dict includes ``_suspect: True`` (D-AM-19 —
    mark, do not drop).

    The input dict is NEVER mutated.
    """
    if not isinstance(raw, dict):
        return None

    if not _REQUIRED_KEYS.issubset(raw.keys()):
        return None

    # Start with a shallow copy restricted to the allowed top-level keys.
    output: dict = {k: v for k, v in raw.items() if k in ALLOWED_TOP_LEVEL_KEYS}

    suspect = False

    if raw.get("type") == "assistant":
        message = raw.get("message")
        if isinstance(message, dict):
            # Extract usage fields
            usage = message.get("usage")
            if isinstance(usage, dict):
                extracted_usage: dict[str, object] = {}
                for key in _ALLOWED_USAGE_KEYS:
                    if key in usage:
                        val = usage[key]
                        extracted_usage[key] = val
                        # Validate token bounds (D-AM-19)
                        if isinstance(val, int) and (
                            val > MAX_TOKEN_COUNT_PER_EVENT or val < 0
                        ):
                            suspect = True
                if extracted_usage:
                    output["usage"] = extracted_usage

            # Extract model
            model_val = message.get("model")
            if model_val is not None:
                output["model"] = model_val

    if suspect:
        output["_suspect"] = True

    return output


def is_forbidden_field_present(d: object) -> bool:
    """Recursively check *d* (dict or list) for any key in FORBIDDEN_KEYS.

    Returns ``True`` if any forbidden key is found anywhere in the nested
    structure.  Used in tests to assert zero content leakage.
    """
    if isinstance(d, dict):
        for key, value in d.items():
            if key in FORBIDDEN_KEYS:
                return True
            if is_forbidden_field_present(value):
                return True
    elif isinstance(d, list):
        for item in d:
            if is_forbidden_field_present(item):
                return True
    return False
