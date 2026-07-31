"""A block's reason must be a diagnosis, not a transcript.

Round 25 R-23 evidence: a blocked ``backlog_author`` carried a ~6000-character reason —
the whole Codex prompt envelope (persona, every injected fragment, the anchor list), then
the model banner, then eight repetitions of a websocket retry. The cause, ``401
Unauthorized``, was one line buried near the end.

The recipe already calls this class F-22: a raw dump where a clean operator-facing line
belongs. It travels into the persisted run record, the printed block and the handoff, so
the operator meets it at the exact moment something has gone wrong.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.worker_failure import summarize_worker_failure

pytestmark = pytest.mark.unit

_REAL_DUMP = (
    "OpenAI Codex v0.144.1\n--------\nworkdir: /opt/data/state/round25/f24\n"
    + (
        '{"persona": "OPERATIVE DIRECTIVE — act per the following role mandate '
        + "x" * 400
        + '"}\n'
    )
    + "warning: Model metadata for `gpt-5.3-codex-spark` not found.\n"
    + "ERROR codex_api: failed to connect to websocket: HTTP error: 401 Unauthorized, "
    "url: wss://api.openai.com/v1/responses\n"
    + "ERROR: Reconnecting... 2/5\n" * 5
    + "ERROR: unexpected status 401 Unauthorized: Missing bearer or basic authentication\n"
)


def test_the_cause_leads_instead_of_hiding_at_the_end() -> None:
    summary = summarize_worker_failure(_REAL_DUMP)

    assert summary.startswith("provider rejected the credential"), summary
    assert "401 Unauthorized" in summary
    assert len(summary) < 500, f"still a transcript at {len(summary)} chars"
    assert "OPERATIVE DIRECTIVE" not in summary, (
        "the prompt envelope must not travel in the reason — it is not a diagnosis, and "
        "it is the bulk of what made the original unreadable"
    )


def test_a_short_clean_failure_is_left_exactly_as_it_is() -> None:
    """A worker that already failed with one precise line must not be made vaguer."""
    original = "agent result missing APPROVED verdict"
    assert summarize_worker_failure(original) == original


@pytest.mark.parametrize(
    "needle, expected",
    [
        ("HTTP error: 403 Forbidden", "provider refused the request"),
        ("status 429 Too Many Requests", "provider rate-limited the request"),
        ("codex: command not found", "the worker binary is missing"),
        ("Traceback (most recent call last):", "the worker crashed"),
    ],
)
def test_each_recognised_failure_is_named(needle: str, expected: str) -> None:
    noise = "context line\n" * 80
    assert summarize_worker_failure(noise + needle + "\n" + noise).startswith(expected)


def test_an_unrecognised_failure_still_stops_being_a_transcript() -> None:
    """The fallback matters most: an unknown failure is exactly when nobody reads 6000 chars."""
    summary = summarize_worker_failure("some unfamiliar failure\n" + "noise " * 3000)

    assert len(summary) < 900, len(summary)
    assert "diagnostic_ref" in summary, "the operator must be told where the full text went"
