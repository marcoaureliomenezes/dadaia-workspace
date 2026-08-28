"""One control/format-character sanitation pass at the bug-record seam (SPEC v0.4.5 FR7,
T-045-20; narrowed by bug ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``, code
review T-045-33 F1). Rewritten at v0.5.0 T-050-08 against ``BugRecord``/``BugService``
(the event fold and ``JsonlBugStore`` it exercised are deleted).

Intent: CONTRACT — SPEC v0.4.5 FR7/A7.1-A7.3/A7.6, carried forward by v0.5.0 A2.6 (the
SAME redaction seam now covers ``BugRecord``'s write paths too).

Two symptoms, one root cause each, one fix:

1. ``JsonlRecordStore.append`` serializes with ``json.dumps(..., ensure_ascii=False)``,
   so a raw U+2028/U+2029 (or any other C0/C1 control byte) lands verbatim inside the
   JSON string; before the FR7 fix nothing ever stopped that byte reaching disk.
2. ``dadaia bugs status``/``bugs stats`` (or any future consumer of a folded
   :class:`BugRecord`) decode that same raw byte back out of the JSON — a raw ESC
   (CWE-117) can forge an ANSI escape sequence or a fake second output line in ANY
   consumer, present or future.

Fixed by construction, at the ONE write-time normalization seam every field already
passes through (``core.models.bugs.redact_text``, called once per field by
``BugRecord.redact()``, called once by ``BugService.register()``): a single strip of
the C0/C1/DEL control range MINUS TAB/LF/CR, plus the Unicode NEL/line/paragraph-
separator group, runs FIRST, before the IP/home/denylist masking passes (A7.6) — so a
value can never reach ``JsonlRecordStore`` (and from there, a fresh
``JsonlRecordStore.iter_records`` round trip) carrying one of these bytes.

Size: SMALL (directory-tiered ``unit`` — pure functions plus real ``tmp_path`` file I/O
only, no subprocess/network; sibling of ``test_write_time_denylist_redaction.py``).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord, redact_text
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

from ._bug_record_helpers import bug_record_store

_TS = "2026-08-26T10:00:00Z"
_ESC = "\x1b"
_LS = chr(0x2028)  # LINE SEPARATOR -- the bundled bug's exact reproduction character.
_NEL = "\x85"  # NEXT LINE -- the other splitlines()-only terminator json.dumps leaves raw.


def _register(
    store: JsonlRecordStore[BugRecord],
    bug_id: str,
    *,
    title: str = "t",
    symptom: str = "sy",
    repro: str = "re",
) -> None:
    service = BugService(store)
    service.register(
        bug_id=bug_id,
        ts=_TS,
        reported_by="software-engineer",
        title=title,
        severity="MEDIUM",
        surface="bugs",
        component="infrastructure/jsonl_record_store.py",
        context="dadaia-workspace",
        symptom=symptom,
        repro=repro,
        expected="ex",
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
# A7.1/A7.2 — THE RED test: a record carrying U+2028/ESC in a free-text field is
# registered and read back INTACT (present, not silently dropped/leaking a raw byte).
# ---------------------------------------------------------------------------


def test_bug_service_register_with_line_separator_in_symptom_is_readable_back(
    tmp_path: Path,
) -> None:
    """Before the fix: registering succeeds (the store's ``append`` never validates
    the byte it writes), but the SAME record would be absent from
    ``JsonlRecordStore.iter_records()`` if the reader still split on
    ``str.splitlines()`` — it fragments the physical line on the embedded U+2028."""
    store = bug_record_store(tmp_path)
    _register(store, "unicode-ls-record", symptom=f"before{_LS}after")

    ids = [r.id for r in store.iter_records()]
    assert "unicode-ls-record" in ids, (
        "record silently dropped on read-back — the embedded U+2028 fragmented the "
        "physical JSONL line"
    )
    persisted = next(r for r in store.iter_records() if r.id == "unicode-ls-record")
    assert _LS not in persisted.symptom


def test_bug_service_register_with_esc_in_title_is_readable_back_without_raw_esc(
    tmp_path: Path,
) -> None:
    """End-to-end round trip for A7.2: a record whose title carries ESC is registered,
    then read back through the real store — the persisted, folded title never carries
    a raw ESC, so nothing downstream can ever render one."""
    store = bug_record_store(tmp_path)
    _register(store, "esc-in-title-roundtrip", title=f"boom{_ESC}[2Khidden")

    persisted = next(r for r in store.iter_records() if r.id == "esc-in-title-roundtrip")
    assert _ESC not in persisted.title
    assert "boom" in persisted.title and "hidden" in persisted.title


# ---------------------------------------------------------------------------
# Bug `bug-event-sanitation-strips-tab-lf-cr-from-free-text` (code review T-045-33
# F1, HIGH): the strip class introduced above deleted TAB/LF/CR along with the real
# fragment/render hazards. json.dumps already escapes the whole C0 range, so a C0 byte
# can never fragment a JSONL line or reach a terminal raw -- only U+0085/U+2028/U+2029
# (splitlines()-only terminators) and ESC/C1 (CWE-117) need stripping.
# ---------------------------------------------------------------------------


def test_redact_text_preserves_tab_lf_cr_word_boundaries() -> None:
    """RED for F1: a multi-line value must keep its word boundaries -- TAB/LF/CR are
    not a fragment or render hazard (json.dumps escapes them; no reader splits on a
    literal char class that includes them since JsonlRecordStore.iter_records splits
    on the literal newline only), so ``redact_text`` must not delete them."""
    out = redact_text("step one\nstep two\ttabbed\r\n")
    assert out == "step one\nstep two\ttabbed\r\n"


def test_redact_text_still_strips_esc_and_c1_and_nel_and_line_separators() -> None:
    """The narrowed class still removes every real hazard: ESC/C1 (CWE-117 terminal
    injection) and the Unicode NEL/line/paragraph separators a naive ``splitlines()``
    reader would treat as terminators -- while a legitimate newline/tab right next to
    them survives untouched."""
    out = redact_text(f"before{_ESC}\nmid{_NEL}{_LS}after\tend")
    assert _ESC not in out
    assert _NEL not in out
    assert _LS not in out
    assert out == "before\nmidafter\tend"


def test_bug_service_register_with_multiline_repro_survives_write_time_redaction(
    tmp_path: Path,
) -> None:
    """End-to-end RED for F1: a multi-line ``repro`` must round-trip through
    ``BugService.register`` -> ``JsonlRecordStore.iter_records`` with its newlines and
    tabs intact, never word-joined, and the ledger stays exactly one physical line."""
    store = bug_record_store(tmp_path)
    multiline_repro = "step one\nstep two\ttabbed\nstep three"
    _register(store, "multiline-repro-record", repro=multiline_repro)

    persisted = next(r for r in store.iter_records() if r.id == "multiline-repro-record")
    assert persisted.repro == multiline_repro

    # The reader splits the file on a literal "\n" only (v0.4.5 FR7) -- prove the two
    # embedded newlines above never produced a second physical line: json.dumps has
    # escaped them to the two-character "\\n" sequence inside the JSON string.
    physical_lines = [
        line for line in store.path.read_text(encoding="utf-8").split("\n") if line.strip()
    ]
    assert len(physical_lines) == 1, (
        "embedded repro newline fragmented the JSONL file into more than one physical "
        "line -- json.dumps must escape it, the reader must never see a raw \\n inside "
        "a field value"
    )
