"""One control/format-character sanitation pass at the bug-event seam (SPEC v0.4.5 FR7,
T-045-20).

Intent: CONTRACT — SPEC v0.4.5 FR7/A7.1-A7.3/A7.6. Bundles the open bug
``bug-event-field-with-unicode-line-separator-silently-drops-the-event`` (MEDIUM, D3).

Two symptoms, one root cause each, one fix:

1. ``JsonlBugStore.append_event`` serializes with ``json.dumps(..., ensure_ascii=False)``,
   so a raw U+2028/U+2029 (or any other C0 control byte) lands verbatim inside the JSON
   string; before this fix nothing ever stopped that byte reaching disk.
2. ``dadaia bugs status``/``bugs stats`` (or any future consumer of a folded
   :class:`BugEvent`) decode that same raw byte back out of the JSON — a raw ESC
   (CWE-117) can forge an ANSI escape sequence or a fake second output line in ANY
   consumer, present or future.

Fixed by construction, at the ONE write-time normalization seam every field already
passes through (``core.models.bugs.redact_text``, called once per field by
``BugEvent.redact()``, called once by ``BugService.append_event`` — SPEC v0.4.5 FR6/
T-045-19): a single strip of C0 controls + the Unicode NEL/line/paragraph-separator
group runs FIRST, before the IP/home/denylist masking passes (A7.6) — so a value can
never reach ``JsonlBugStore`` (and from there, a fresh ``JsonlBugStore.append_event``
round trip through ``iter_events``) carrying one of these bytes, and a denylisted term
an attacker split across an interrupting byte re-joins into a contiguous substring
before the masking regex runs over it.

Size: SMALL (directory-tiered ``unit`` — pure functions plus real ``tmp_path`` file I/O
only, no subprocess/network; sibling of ``test_write_time_denylist_redaction.py``).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.bugs import BugEvent, redact_text
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore

_TS = "2026-08-26T10:00:00Z"
_ESC = "\x1b"
_LS = "\u2028"  # LINE SEPARATOR -- the bundled bug's exact reproduction character (U+2028).


def _reported(bug_id: str, *, title: str = "t", notes: str = "n") -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="reported",
        ts=_TS,
        reported_by="software-engineer",
        title=title,
        severity="MEDIUM",
        surface="bugs ledger",
        component="infrastructure/jsonl_bug_store.py",
        context="dadaia-workspace",
        tags=(),
        symptom="sy",
        repro="re",
        expected="ex",
        notes=notes,
    )


# ---------------------------------------------------------------------------
# A7.3 — one pass, at redact_text, covering both hazard classes together.
# ---------------------------------------------------------------------------


def test_redact_text_strips_esc_and_line_separator_before_any_masking() -> None:
    """A7.3: a single ``redact_text`` call removes BOTH an embedded ESC (the CWE-117
    class) and an embedded U+2028 (the ``splitlines()``-over-split class) — not two
    independent guards, one pass over the same value."""
    out = redact_text(f"before{_ESC}mid{_LS}after")
    assert _ESC not in out
    assert _LS not in out
    assert "before" in out and "mid" in out and "after" in out


def test_redact_text_leaves_clean_text_byte_identical() -> None:
    """No-op on text carrying neither hazard — mirrors the existing pre-FR6/FR7
    byte-identical guarantee for every caller that never sees a control character."""
    raw = "deployment landed at ACME-Corp's staging box"
    assert redact_text(raw) == raw


# ---------------------------------------------------------------------------
# A7.6 — sanitation runs BEFORE redaction: a denylisted term interrupted by one of
# these characters still gets masked, proven by the two named fixtures.
# ---------------------------------------------------------------------------


def test_redact_text_masks_a_denylisted_term_interrupted_by_line_separator() -> None:
    """A7.6 fixture 1: ``acme-corp`` split by an embedded U+2028 must still be masked
    — impossible unless the separator is stripped BEFORE the substring scan runs."""
    out = redact_text(
        f"landed at acme{_LS}-corp today",
        denylist_terms=(("acme-corp", "private client name"),),
    )
    assert "acme-corp" not in out.lower()
    assert "[REDACTED-TERM]" in out
    assert _LS not in out


def test_redact_text_masks_a_denylisted_term_interrupted_by_esc() -> None:
    """A7.6 fixture 2: ``acme-corp`` split by an embedded ESC must still be masked —
    same ordering requirement, the other named hazard."""
    out = redact_text(
        f"landed at acme{_ESC}-corp today",
        denylist_terms=(("acme-corp", "private client name"),),
    )
    assert "acme-corp" not in out.lower()
    assert "[REDACTED-TERM]" in out
    assert _ESC not in out


# ---------------------------------------------------------------------------
# A7.2 — CWE-117: no consumer of a redacted BugEvent can ever observe a raw ESC.
# ---------------------------------------------------------------------------


def test_bug_event_redact_never_leaves_a_raw_esc_in_any_field() -> None:
    """A7.2: fixed by construction — every ``_OPTIONAL_STR_FIELDS`` value ``.redact()``
    touches is stripped of ESC, so no present or future renderer (``bugs status``,
    ``bugs stats``, or anything reading a folded :class:`BugEvent`) can ever print a
    raw control character it never received."""
    event = _reported("esc-in-title", title=f"urgent{_ESC}[31mFAKE ERROR{_ESC}[0m")
    redacted = event.redact()
    assert redacted.title is not None
    assert _ESC not in redacted.title


# ---------------------------------------------------------------------------
# A7.1 — THE RED test: an event carrying U+2028 in a free-text field is appended
# with [ok] and then read back INTACT (present, not silently dropped) by the store's
# own fold — before the fix it is absent because JsonlBugStore.iter_events's
# str.splitlines() call fragments the physical line on the raw U+2028 byte.
# ---------------------------------------------------------------------------


def test_bug_service_append_event_with_line_separator_in_notes_is_readable_back(
    tmp_path: Path,
) -> None:
    """Before the fix: appending this event succeeds (the store's ``append_event`` never
    validates the byte it writes), but the SAME event is absent from
    ``JsonlBugStore.iter_events()`` — ``str.splitlines()`` treats the embedded U+2028 as
    a second line terminator, so the one JSON record fragments into two unparseable
    halves and both are skipped with a logged WARN."""
    store = JsonlBugStore(tmp_path / "bugs")
    service = BugService(store)

    service.append_event(_reported("unicode-ls-event", notes=f"before{_LS}after"))

    ids = [e.bug_id for e in store.iter_events()]
    assert "unicode-ls-event" in ids, (
        "event silently dropped on read-back — the embedded U+2028 fragmented the "
        "physical JSONL line"
    )
    persisted = next(e for e in store.iter_events() if e.bug_id == "unicode-ls-event")
    assert persisted.notes is not None
    assert _LS not in persisted.notes


def test_bug_service_append_event_with_esc_in_title_is_readable_back_without_raw_esc(
    tmp_path: Path,
) -> None:
    """End-to-end round trip for A7.2: an event whose title carries ESC is appended,
    then read back through the real store — the persisted, folded title never carries
    a raw ESC, so nothing downstream can ever render one."""
    store = JsonlBugStore(tmp_path / "bugs")
    service = BugService(store)

    service.append_event(_reported("esc-in-title-roundtrip", title=f"boom{_ESC}[2Khidden"))

    persisted = next(e for e in store.iter_events() if e.bug_id == "esc-in-title-roundtrip")
    assert persisted.title is not None
    assert _ESC not in persisted.title
    assert "boom" in persisted.title and "hidden" in persisted.title
