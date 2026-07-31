"""Turn a failed worker's output into a diagnosis the operator can read.

Round 25, R-23 evidence: a blocked ``backlog_author`` carried a ``reason`` of roughly six
thousand characters — the entire Codex prompt envelope (persona, every injected fragment,
the anchor list) followed by the model banner and eight repetitions of a websocket retry.
The actual cause, ``401 Unauthorized``, was one line buried near the end.

That is the F-22 class the recipe already names: a raw dump where a clean line belongs. It
is not cosmetic. A reason nobody reads is a reason nobody acts on, and it travels into the
persisted run record, the printed block, and the handoff — so the operator is handed a wall
of text at the exact moment something has gone wrong.

The full transcript is not lost: the adapter's diagnostic is persisted separately and
referenced from ``BlockedState.detail["diagnostic_ref"]``. This module decides what leads.
Pure text in, text out — no filesystem, per the ``core`` purity ratchet.
"""

from __future__ import annotations

import re

#: Failure signatures worth leading with, most specific first. Each is a shape an operator
#: can act on: a credential, a rate limit, a missing binary, a crash.
_SIGNATURES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("provider rejected the credential", re.compile(r"\b401 Unauthorized\b", re.I)),
    ("provider refused the request", re.compile(r"\b403 Forbidden\b", re.I)),
    ("provider rate-limited the request", re.compile(r"\b429\b")),
    ("the worker binary is missing", re.compile(r"command not found|No such file or directory")),
    ("the worker crashed", re.compile(r"^Traceback \(most recent call last\)", re.M)),
    ("the worker timed out", re.compile(r"\btimed? ?out\b", re.I)),
)

#: How much raw output may ride along after the diagnosis. Enough to recognise the failure,
#: far short of a transcript.
_TAIL_BUDGET = 600


def _first_matching_line(text: str, pattern: re.Pattern[str]) -> str | None:
    for line in text.splitlines():
        if pattern.search(line):
            return " ".join(line.split())[:200]
    return None


def summarize_worker_failure(text: str) -> str:
    """Lead with the recognisable cause; keep a bounded tail; never emit a transcript.

    Short output is returned unchanged — a worker that already failed with one clean line
    must not be rewritten into something less precise.
    """
    stripped = text.strip()
    if len(stripped) <= _TAIL_BUDGET:
        return stripped

    for label, pattern in _SIGNATURES:
        line = _first_matching_line(stripped, pattern)
        if line is not None:
            return (
                f"{label}: {line} "
                f"(worker output truncated; the full transcript is in the persisted "
                f"diagnostic referenced by detail.diagnostic_ref)"
            )

    tail = " ".join(stripped[-_TAIL_BUDGET:].split())
    return (
        f"the worker failed without a recognised error signature; last {_TAIL_BUDGET} "
        f"characters: …{tail} (full transcript in detail.diagnostic_ref)"
    )
