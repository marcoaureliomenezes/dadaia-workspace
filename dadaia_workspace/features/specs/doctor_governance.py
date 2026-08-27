"""Governance validator: backlog single-source invariants, bug status/JSONL.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the bug/backlog governance
invariants: consumed-but-unsanitized ACTIVE backlog item (SPEC-DOC-031, SPEC v0.4.2 FR14),
bug-status canon (SPEC-DOC-032), the bug-ledger invariant (SPEC-DOC-033), the immutable-core
drift detector (SPEC-DOC-040, v0.5.0 A2.7) and the archive-overdue signal (SPEC-DOC-041,
v0.5.0 A2.8), and the single-source loose-file invariant (SPEC-DOC-035, SPEC v0.12.0 FR5).
Leaf-only: imports the shared leaves + core, plus one documented cross-feature leaf edge
(``features.backlog.document`` — SPEC v0.12.0 PLAN §6, ``setup.cfg``'s
``features-no-cross-feature`` ``ignore_imports``), never a sibling validator.

**v0.5.0 T-050-08 (FR2/AR-1 finding "the doctor's bug lane is a second hand-kept
reader").** ``check_bugs_jsonl_invariant`` used to hand-parse each line's ``bug_id``/
``event`` fields directly and split the file with ``str.splitlines()`` — the EXACT
defect class fixed at the store's OWN reader by T-045-20
(``bug-event-field-with-unicode-line-separator-silently-drops-the-event``), left live
here (bug ``specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators``, closed by
this rewrite). This validator now reads through ``core.models.bugs``'s OWN parsers
(``BugEvent.from_dict``/``BugRecord.from_dict``) and splits on a literal ``"\\n"``
only — one parser, not a second hand-kept mirror of it. The legacy hourly-file rotation
reader (``_BUGS_JSONL_ROW_CEILING``, ``_BUGS_JSONL_NAME_RE``, the ``*.jsonl`` glob) is
DEAD under canon v6 (AR-1 (a)4) and is deleted, not carried forward: only the single
canonical ``bugs/bugs.jsonl`` is read.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    TERMINAL_EVENTS,
    BugCoherenceRecord,
    BugEvent,
    BugRecord,
    diagnose_bug_coherence_history,
    governance_completeness_gaps,
    immutable_core_drift,
)
from dadaia_workspace.features.backlog.document import load_document
from dadaia_workspace.features.specs.doctor_common import iter_archive_release_dirs
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

# ADR-11 single-source status-token vocabulary.
#
# Backlog (case-insensitive prefix match on the Status line value):
#   non-terminal = {OPEN, PICKED, CANDIDATE}; terminal = {DELIVERED, SUPERSEDED,
#   RESOLVED, CONSUMED, DEFERRED, REJECTED} (+ free suffixes like ``— vX.Y.Z``).
# Only the NON-TERMINAL set drives SPEC-DOC-031: a non-terminal backlog entry whose
# slug is referenced by an archived release is the consumed-but-unsanitized drift.
_BACKLOG_NONTERMINAL_PREFIXES: tuple[str, ...] = ("open", "picked", "candidate")

# Bugs (ADR-11): the canon is exactly {Open, Closed} (case-insensitive). SPEC-DOC-032
# WARNs on anything else (legacy Fixed/resolved/Rejected tokens, etc.).
_BUG_STATUS_CANON: frozenset[str] = frozenset({"open", "closed"})

# Match a bug frontmatter ``status:`` line (frontmatter is leading YAML-like lines).
_BUG_STATUS_RE = re.compile(r"^status\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)

# SPEC-DOC-035 (SPEC v0.12.0 FR5, ADR D5/D9): the single-source invariant — the only two
# filenames permitted loose directly under ``specs/backlog/``. Anything else (a per-entry
# item that survived the v0.12.0 consolidation, or was hand-authored outside `dadaia
# backlog new`) is drift.
_BACKLOG_SINGLE_SOURCE_FILES: frozenset[str] = frozenset({"BACKLOG.md", "README.md"})

# SPEC-DOC-031 evidence surface (SPEC v0.4.2 FR14/GRILL D6): a mention counts as
# consumption evidence only when it ASSERTS consumption, never on free-text prose —
# "non-goal", "inheritance", "provenance", "Backlog returns" and every other prose
# mention are ignored by construction, with no per-section exclusion list to maintain
# (D6 deletes the ``## Backlog returns`` special case as subsumed: a returns section is
# not a ``**Consumes:**`` declaration, so it was never actually evidence).
#
# An archived SPEC's own ``**Consumes:**`` declaration (P19: its value continues onto
# subsequent lines until a blank line or the next ``**Key:**`` line — 27 archived
# SPEC/CLOSURE files carry this line, several wrapped across two lines).
_CONSUMES_LINE_RE = re.compile(r"^[ \t]*\*\*Consumes:\*\*[ \t]*(?P<rest>.*)$")

# Any other bold-key line (``**Key:** value``) — the continuation-stop boundary. Matches
# the SPEC frontmatter shape (``**Status:**``, ``**Picked set:**``, ``**Branch:**``, …).
_BOLD_KEY_LINE_RE = re.compile(r"^[ \t]*\*\*[^*\n]+:\*\*")

# An archived CLOSURE's ``## Dispositions`` section — only its table ROWS (lines starting
# with ``|``, a Markdown table cell boundary) are evidence; the surrounding prose
# (rationale paragraphs, "Explicit non-flips" notes) is never scanned.
_DISPOSITIONS_HEADING_RE = re.compile(r"^##[ \t]+Dispositions\b")

# Slug-shaped tokens (P19): backlog slugs are always ``^[a-z][a-z0-9-]+$`` — splitting
# consumption-evidence text on anything OUTSIDE that charset isolates candidate tokens
# (from backtick-quoted, comma-separated, or path-shaped mentions alike) without matching
# a slug that is merely a SUBSTRING of a longer word or a different slug (D6).
_SLUG_TOKEN_RE = re.compile(r"[a-z0-9-]+")


def _consumes_tokens(spec_text: str) -> frozenset[str]:
    """Whole-token slug candidates from every ``**Consumes:**`` declaration in an
    archived SPEC.md, continuation lines included (P19)."""
    lines = spec_text.splitlines()
    span: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        m = _CONSUMES_LINE_RE.match(lines[i])
        if m is None:
            i += 1
            continue
        span.append(m.group("rest"))
        i += 1
        while i < n and lines[i].strip() != "" and not _BOLD_KEY_LINE_RE.match(lines[i]):
            span.append(lines[i])
            i += 1
    return frozenset(_SLUG_TOKEN_RE.findall(" ".join(span)))


def _dispositions_tokens(closure_text: str) -> frozenset[str]:
    """Whole-token slug candidates from every table row under an archived CLOSURE's
    ``## Dispositions`` heading — never its rationale prose, never any other section."""
    tokens: list[str] = []
    in_section = False
    for line in closure_text.splitlines():
        if line.startswith("## "):
            in_section = bool(_DISPOSITIONS_HEADING_RE.match(line))
            continue
        if in_section and line.lstrip().startswith("|"):
            tokens.extend(_SLUG_TOKEN_RE.findall(line))
    return frozenset(tokens)


def _iter_native_bug_records(ledger_path: Path) -> list[BugRecord]:
    """Every line of *ledger_path* that parses as a native v6 :class:`BugRecord` (no
    ``"event"`` key) — a v5 line, malformed JSON, or a non-object line is silently
    skipped (SPEC-DOC-033's own line-validity check already reports those). Splits on
    a literal ``"\\n"`` only. Shared by A2.7's and A2.8's checks, both of which only
    ever act on already-native lines (module docstring)."""
    if not ledger_path.is_file():
        return []
    records: list[BugRecord] = []
    for raw_line in ledger_path.read_text(encoding="utf-8").split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or "event" in obj:
            continue
        try:
            records.append(BugRecord.from_dict(obj))
        except (ValueError, TypeError):
            continue
    return records


def _parse_bug_record_ts(value: str) -> datetime | None:
    """Parse a ``BugRecord.ts`` ISO-8601 UTC value; ``None`` on anything unparseable
    (an unparseable timestamp is never treated as overdue — A2.8's own no-guess rule)."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class GovernanceValidator:
    """Bug/backlog governance: single-source backlog invariants, bug status/JSONL."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        *,
        bug_first_add_baselines: Mapping[str, BugRecord] | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        # v0.5.0 A2.7 — the TODO-free seam FR3/T-050-09's core.bug_provenance
        # derivation plugs a real git-derived first-add snapshot into: this release
        # (T-050-08) has no git access here (a "pure module, no I/O outside
        # specs_dir/public_dir" leaf) and no derivation exists yet, so every current
        # caller passes ``None`` — the check is a genuine production no-op (nothing to
        # compare against) until T-050-09 threads a real mapping through this same
        # constructor param.
        self._bug_first_add_baselines = bug_first_add_baselines or {}

    def _archive_consumption_hits(self, slug: str) -> list[str]:
        """Release ids of archived releases that ASSERT ``slug`` was consumed (SPEC
        v0.4.2 FR14/GRILL D6) — never a raw line-substring scan of the whole document.

        A mention counts as consumption evidence in exactly two shapes:

        - an archived SPEC's ``**Consumes:**`` declaration (its value plus continuation
          lines, P19), tokenized on non-slug characters and matched as a WHOLE token; or
        - an archived CLOSURE's ``## Dispositions`` table ROWS, tokenized the same way.

        Everything else in either document — prose, non-goals, provenance notes, a
        ``## Backlog returns`` section — is never read here; it never asserted
        consumption in the first place, so there is no special case to carve it out
        (D6 deletes the old ``## Backlog returns`` exclusion as subsumed). Returns the
        sorted, de-duplicated set of archived release ids with matching evidence.
        """
        arch = self.specs_dir / "_archive" / "releases"
        if not arch.is_dir():
            return []
        hits: set[str] = set()
        for release_dir in iter_archive_release_dirs(arch):
            spec_doc = release_dir / "SPEC.md"
            if spec_doc.is_file() and slug in _consumes_tokens(
                spec_doc.read_text(encoding="utf-8")
            ):
                hits.add(release_dir.name)
                continue
            closure_doc = release_dir / "CLOSURE.md"
            if closure_doc.is_file() and slug in _dispositions_tokens(
                closure_doc.read_text(encoding="utf-8")
            ):
                hits.add(release_dir.name)
        return sorted(hits)

    def check_consumed_backlog_disposition(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-031 (re-targeted, SPEC v0.4.2 FR14/GRILL D6): WARN on a consumed-but-
        unsanitized ``## ACTIVE`` item in ``specs/backlog/BACKLOG.md``.

        Iterates the document's ACTIVE subsections (:func:`~dadaia_workspace.features.
        backlog.document.load_document`) instead of globbing per-entry files. An ACTIVE
        item whose ``**Status:**`` is an ADR-11 NON-TERMINAL token ({OPEN, PICKED,
        CANDIDATE}, case-insensitive prefix match) AND whose slug is a whole-token match
        inside an archived release's CONSUMPTION-ASSERTING evidence — an archived SPEC's
        ``**Consumes:**`` declaration or an archived CLOSURE's ``## Dispositions`` table
        rows (:func:`_archive_consumption_hits`, FR14) — ⇒ **WARNING**. The lifecycle
        contract is that an item consumed into a shipped+archived release must move
        ``ACTIVE`` → ``LEDGER`` at CLOSURE; a non-terminal ACTIVE item whose slug is
        consumption-asserted is the drift.

        Severity is WARN, never ERR (ADR-6, R3): the evidence surface is narrower than
        before FR14 (conversation no longer counts, only consumption), but it is still
        necessary-but-not-sufficient — a genuinely consumed slug whose SPEC never
        declared it in ``**Consumes:**`` is an accepted false NEGATIVE (R3), not a false
        positive; the twelve documented false positives free-text matching produced are
        gone by construction, with no per-section exclusion list to maintain (D6 deletes
        the old ``## Backlog returns`` special case as subsumed — a returns section was
        never a ``**Consumes:**`` declaration, so it was never actually evidence). Never
        fires on the document itself (A5.2): the slug universe is the parsed ``###
        <slug>`` subsections, never the literal ``BACKLOG`` filename/slug.
        """
        backlog_dir = self.specs_dir / "backlog"
        document = load_document(backlog_dir)
        if not document.active:
            return []
        backlog_md_path = backlog_dir / "BACKLOG.md"
        issues: list[SpecsDoctorIssue] = []
        for item in document.active:
            if item.status is None:
                continue
            status_lower = item.status.lower()
            if not status_lower.startswith(_BACKLOG_NONTERMINAL_PREFIXES):
                continue
            hits = self._archive_consumption_hits(item.slug)
            if not hits:
                continue
            releases = ", ".join(hits)
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-031",
                    severity=Severity.WARNING,
                    description=(
                        f"backlog ACTIVE item {item.slug!r} has non-terminal status "
                        f"'{item.status}' but its slug is referenced by archived "
                        f"release(s) {releases} (outside 'Backlog returns' sections). "
                        "If it was consumed/shipped, add a LEDGER line ('<slug> · "
                        "DELIVERED · vX.Y.Z · <date>'; also SUPERSEDED/RESOLVED/"
                        "CONSUMED/DEFERRED/REJECTED) and remove this ACTIVE subsection "
                        "in the same edit — an item moves ACTIVE -> LEDGER, it is never "
                        "left recorded in both (BL-STALE would then fire). Do NOT leave "
                        "the item ACTIVE with a terminal-looking status suffix instead "
                        "— BL-SCHEMA/BL-STALE key off the bare Status token and the "
                        "LEDGER line, not free text. WARNING only — a slug mention is "
                        "not proof of consumption (ADR-6 false-positive class)."
                    ),
                    path=str(backlog_md_path),
                )
            )
        return issues

    def check_bug_status_canon(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-032 (T-011-10, bug B1, ADR-11): WARN on non-canonical bug status tokens.

        Every ``specs/bugs/<slug>.md`` frontmatter ``status:`` must be in the ADR-11 bug
        canon {``Open``, ``Closed``} (case-insensitive). Anything else (legacy ``Fixed`` /
        ``resolved`` / ``Rejected`` etc.) ⇒ **WARNING**. A duplicate/rejected bug should be
        ``Closed`` with a ``superseded_by:`` frontmatter field, not a ``Rejected`` token.
        ``README.md`` is skipped; an absent ``bugs/`` dir is a no-op.
        """
        bugs_dir = self.specs_dir / "bugs"
        if not bugs_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for bug_file in sorted(bugs_dir.glob("*.md")):
            if bug_file.name in ("README.md",):
                continue
            m = _BUG_STATUS_RE.search(bug_file.read_text(encoding="utf-8"))
            if m is None:
                # Missing status is a separate concern (TREE-7 governs session_id); a bug
                # with no status line at all is not flagged by this status-canon check.
                continue
            status = m.group(1).strip()
            if status.lower() in _BUG_STATUS_CANON:
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-032",
                    severity=Severity.WARNING,
                    description=(
                        f"bugs/{bug_file.name} has status '{status}' outside the ADR-11 bug "
                        "canon {Open, Closed}. Normalize it: a fixed bug ⇒ 'Closed'; a "
                        "duplicate/rejected bug ⇒ 'Closed' with a 'superseded_by: <slug>' "
                        "frontmatter field (SPEC-DOC-032, WARNING)."
                    ),
                    path=str(bug_file),
                )
            )
        return issues

    def check_bugs_jsonl_invariant(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-033 (v0.1.46 AC-1; rewritten v0.5.0 T-050-08, FR2/A2.3): the single
        canonical ``specs/bugs/bugs.jsonl`` ledger invariant.

        Three sub-checks over the ONE canonical file (the legacy hourly-file rotation
        reader is dead under canon v6 and is not carried forward — module docstring):

        1. **Line validity** (ERROR) — each non-blank line must parse as EITHER a v5
           :class:`~dadaia_workspace.core.models.bugs.BugEvent` (an ``"event"`` key
           present) or a native v6
           :class:`~dadaia_workspace.core.models.bugs.BugRecord` (no ``"event"`` key),
           through THEIR OWN ``from_dict`` parsers — never a hand-rolled field check.
        2. **Event-stream coherence** (WARNING, demoted from ERROR — A2.3/D15: never a
           block) over the v5 portion's whole history — see
           :func:`~dadaia_workspace.core.models.bugs.diagnose_bug_coherence_history`'s
           own docstring for why this is now a diagnostic-only survivor.
        3. **Governance completeness** (WARNING — A2.3) — every native v6
           :class:`BugRecord` line whose
           :func:`~dadaia_workspace.core.models.bugs.governance_completeness_gaps` is
           non-empty.

        Splits on a literal ``"\\n"`` only, never ``str.splitlines()`` (closes
        ``specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators`` — the
        module docstring's AR-1 finding). Absent ``bugs/`` dir -> no-op.
        """
        ledger_path = self.specs_dir / "bugs" / "bugs.jsonl"
        if not ledger_path.is_file():
            return []

        issues: list[SpecsDoctorIssue] = []
        # v0.5.0 FR2: coherence is a WHOLE-HISTORY diagnosis (the healing rule needs to
        # see events that come later than a violation), so this loop only COLLECTS one
        # (bug_id, event, position) record per valid v5 line; the fold itself runs
        # once, after every line has been read, in `_fold_bug_coherence`.
        coherence_records: list[BugCoherenceRecord[int]] = []

        for lineno, raw_line in enumerate(ledger_path.read_text(encoding="utf-8").split("\n"), 1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-033",
                        severity=Severity.ERROR,
                        description=(
                            f"bugs/bugs.jsonl line {lineno}: not valid JSON ({exc.msg}) — "
                            "every JSONL row must be one bug-event or bug-record object "
                            "(SPEC-DOC-033, ERROR)."
                        ),
                        path=str(ledger_path),
                    )
                )
                continue
            if not isinstance(obj, dict):
                continue
            if "event" in obj:
                try:
                    event = BugEvent.from_dict(obj)
                except (ValueError, TypeError) as exc:
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-033",
                            severity=Severity.ERROR,
                            description=(
                                f"bugs/bugs.jsonl line {lineno}: not a valid bug-event "
                                f"object ({exc}) (SPEC-DOC-033, ERROR)."
                            ),
                            path=str(ledger_path),
                        )
                    )
                    continue
                coherence_records.append(
                    BugCoherenceRecord(bug_id=event.bug_id, event=event.event, position=lineno)
                )
                continue
            try:
                record = BugRecord.from_dict(obj)
            except (ValueError, TypeError) as exc:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-033",
                        severity=Severity.ERROR,
                        description=(
                            f"bugs/bugs.jsonl line {lineno}: not a valid bug-record "
                            f"object ({exc}) (SPEC-DOC-033, ERROR)."
                        ),
                        path=str(ledger_path),
                    )
                )
                continue
            gaps = governance_completeness_gaps(record)
            if gaps:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-033",
                        severity=Severity.WARNING,
                        description=(
                            f"bugs/bugs.jsonl record {record.id!r}: status "
                            f"{record.status!r} is missing {', '.join(gaps)} "
                            "(SPEC-DOC-033, WARNING — never a block, D15)."
                        ),
                        path=str(ledger_path),
                    )
                )
        issues.extend(self._fold_bug_coherence(ledger_path, coherence_records))
        return issues

    @staticmethod
    def _fold_bug_coherence(
        ledger_path: Path, records: list[BugCoherenceRecord[int]]
    ) -> list[SpecsDoctorIssue]:
        """Format the WHOLE-HISTORY v5 coherence diagnosis as ``SpecsDoctorIssue``
        lines, at WARNING severity (A2.3/D15 — demoted from the pre-T-050-08 ERROR: a
        diagnosis over RETIRED-write-path history is detection, not a live gate)."""
        issues: list[SpecsDoctorIssue] = []
        for violation in diagnose_bug_coherence_history(records):
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-033",
                    severity=Severity.WARNING,
                    description=(
                        f"bugs/bugs.jsonl line {violation.position}: {violation.clause} "
                        "(SPEC-DOC-033, WARNING — never a block, D15)."
                    ),
                    path=str(ledger_path),
                )
            )
        return issues

    def check_bug_record_immutable_core(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-040 (v0.5.0 A2.7) — WARN when a native v6 :class:`BugRecord`'s
        immutable-core fields differ from its injected first-add baseline.

        Detects, never prevents (A2.2a already refuses a core-field CHANGE made
        through the record-store update seam — this is the residual-gap detector for
        a file tool that bypassed it entirely). ``self._bug_first_add_baselines``
        defaults to ``{}`` (constructor docstring) — a genuine production no-op until
        FR3/T-050-09 threads a real git-derived mapping through the same seam. Absent
        ``bugs/`` dir or no baselines configured -> no-op.
        """
        if not self._bug_first_add_baselines:
            return []
        ledger_path = self.specs_dir / "bugs" / "bugs.jsonl"
        if not ledger_path.is_file():
            return []
        issues: list[SpecsDoctorIssue] = []
        for record in _iter_native_bug_records(ledger_path):
            baseline = self._bug_first_add_baselines.get(record.id)
            if baseline is None:
                continue
            drifted = immutable_core_drift(record, baseline)
            if drifted:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-040",
                        severity=Severity.WARNING,
                        description=(
                            f"bugs/bugs.jsonl record {record.id!r}: immutable-core "
                            f"field(s) {', '.join(drifted)} differ from the first-add "
                            "snapshot — a file tool bypassed the record-store update "
                            "seam (SPEC-DOC-040, WARNING — detected, never prevented, "
                            "A2.7)."
                        ),
                        path=str(ledger_path),
                    )
                )
        return issues

    def check_bug_archive_overdue(self, *, now: datetime | None = None) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-041 (v0.5.0 A2.8) — WARN when a native v6 terminal
        :class:`BugRecord` is older than
        :data:`~dadaia_workspace.core.models.bugs.BUG_ARCHIVE_THRESHOLD_DAYS` and is
        still live (not yet moved by ``dadaia bugs archive``). Never a block (D15);
        the exit code is unchanged. Absent ``bugs/`` dir -> no-op.
        """
        ledger_path = self.specs_dir / "bugs" / "bugs.jsonl"
        if not ledger_path.is_file():
            return []
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=BUG_ARCHIVE_THRESHOLD_DAYS)
        issues: list[SpecsDoctorIssue] = []
        for record in _iter_native_bug_records(ledger_path):
            if record.status not in TERMINAL_EVENTS:
                continue
            record_ts = _parse_bug_record_ts(record.ts)
            if record_ts is not None and record_ts < cutoff:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-041",
                        severity=Severity.WARNING,
                        description=(
                            f"bugs/bugs.jsonl record {record.id!r} has been terminal "
                            f"({record.status!r}) since {record.ts} — past the "
                            f"{BUG_ARCHIVE_THRESHOLD_DAYS}-day archive threshold; run "
                            "'dadaia bugs archive' (SPEC-DOC-041, WARNING — never a "
                            "block, D15)."
                        ),
                        path=str(ledger_path),
                    )
                )
        return issues

    def check_unarchived_terminal_backlog(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-035 (re-targeted, SPEC v0.12.0 FR5/ADR D5/D9): the single-source
        invariant — any ``*.md`` loose directly under ``specs/backlog/`` other than
        ``BACKLOG.md`` and ``README.md`` is drift → WARN.

        The physical model changed from "one file per backlog item" to "one document,
        ``BACKLOG.md``, with ``## ACTIVE`` + ``## LEDGER``" (ADR #14); a loose per-entry
        file is now itself the drift signal, regardless of any status text it carries —
        either a stray survivor of the v0.12.0 consolidation, or a file hand-authored
        outside ``dadaia backlog new``. ``specs/backlog/_archive/`` and
        ``specs/backlog/remote-bugs/`` are excluded (non-recursive glob already skips
        both — they are subdirectories, not ``*.md`` siblings).
        """
        backlog_dir = self.specs_dir / "backlog"
        if not backlog_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for entry in sorted(backlog_dir.glob("*.md")):
            if entry.name in _BACKLOG_SINGLE_SOURCE_FILES:
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-035",
                    severity=Severity.WARNING,
                    description=(
                        f"backlog/{entry.name} is a loose per-entry file directly under "
                        "specs/backlog/ — the single source is BACKLOG.md (## ACTIVE + "
                        "## LEDGER); fold it into BACKLOG.md and move the superseded "
                        "file into specs/backlog/_archive/ (SPEC-DOC-035, WARNING)."
                    ),
                    path=str(entry),
                )
            )
        return issues
