"""Governance validator: backlog single-source invariants, bug status/JSONL.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the bug/backlog governance
invariants: consumed-but-unsanitized ACTIVE backlog item (SPEC-DOC-031, SPEC v0.4.2 FR14),
the bug-ledger invariant (SPEC-DOC-033), the archive-overdue signal (SPEC-DOC-041, v0.5.0
A2.8), and the single-source loose-file invariant (SPEC-DOC-035, SPEC v0.12.0 FR5).
Leaf-only: imports the shared leaves + core, plus one documented cross-feature leaf edge
(``features.backlog.document`` — SPEC v0.12.0 PLAN §6, ``setup.cfg``'s
``features-no-cross-feature`` ``ignore_imports``), never a sibling validator.

**v0.5.1 K5 deepening — the doctor reads through the ONE store, not a second hand-kept
parser.** Two prior rewrites of ``check_bugs_jsonl_invariant`` (v0.5.0 T-050-08, then
the 08-27 fix for bug ``specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators``)
each re-implemented the SAME classification the record store's own ``iter_records``
already had — the unicode-line-split defect class (T-045-20) was fixed at the store
08-24, then reproduced and fixed a SECOND time at this doctor 08-27, because there were
two parsers. This deepening deletes the second one: ``check_bugs_jsonl_invariant`` now
reads through an injected ``bug_store_factory`` (mirrors
``ClosureAuditValidator``'s ``findings_store_factory`` seam) calling
``RecordStore.iter_records(strict=True)`` — the ONE malformed-line diagnosis
(``core.protocols.record_store.MalformedLine``), yielded by
``infrastructure.jsonl_record_store.JsonlRecordStore`` in production, by a
zero-dependency fallback reader here when no factory is injected (this module holds no
``features -> infrastructure`` edge, mirroring ``ClosureAuditValidator``'s own
``_default_iter_findings``) — either way, the record-level parsing is
``BugRecord.from_dict`` (now enum-validating ``status`` too), never a second,
hand-rolled field check.

**Governance completeness is no longer diagnosed here at all.** The former WARNING
branch (``governance_completeness_gaps``, "record X is missing field Y for its status")
is DELETED along with that function — v0.5.1 K5 moves completeness to the WRITE seam
(``core.models.bugs.BugRecord.resolve``/``supersede``/``defer``/``reject``: status is
unreachable without its own required fields), never re-diagnosed against history. A
historical record that reached an incomplete terminal status before this seam existed
(the "488 live warnings nobody acts on" the K5 card names) is simply never re-checked —
completeness is enforced prospectively, not retroactively.

**``check_bug_status_canon`` (SPEC-DOC-032) is DELETED.** It regex-matched a
``status:`` frontmatter line in ``specs/bugs/<slug>.md`` files — a per-bug Markdown
file shape retired two migrations before this one (the v0.5.0 FR2 single-JSONL-ledger
cutover); the check has had nothing to find since, dead code behind a dead artifact.

**S1 FR23 firing amendments A3/A5
(`specs/releases/0.5.0/reviews/S1-FR23-firing.md`).** A3: the v5 event fold and its
coherence state machine are deleted from ``core/models/bugs.py`` — the live ledger
carries zero v5 lines, so a surviving ``"event"``-keyed (or otherwise v5-shaped) line
now fails ``BugRecord.from_dict`` and surfaces as a plain ``MalformedLine`` — one ERROR,
never a folded WARNING diagnosis. A5: SPEC-DOC-040 (the immutable-core drift WARN) is
deleted along with the ``bug_first_add_baselines`` plumbing — it never fired in
production (its input was always the empty default); A2.7's detector moves to FR14
pillar 1, which owns the git walk this check would have needed.

**v0.5.0 T-050-25A (FR15 extended scope, A4.4).** ``_archive_consumption_hits``'s
CLOSURE.md-side evidence (an archived CLOSURE's ``## Dispositions`` table) is deleted —
FR4/T-050-21A retired ``CLOSURE.md`` as a going-forward artifact, so a checker that
parses it is dead code behind a dead artifact. SPEC-DOC-031's evidence surface narrows
to ONLY an archived SPEC's own ``**Consumes:**`` declaration; the disposition sweep this
lost half used to also (imperfectly) catch is already native elsewhere —
``specs/backlog/_archive/backlog_histo.jsonl``'s ``release`` field and ``BUGS.jsonl``'s
``resolved_release`` field (`dd-release-implement`'s ``RELEASE-EVENTS.md``) — so nothing
is left unrecorded, only unread by THIS check. The narrowing is an accepted false
NEGATIVE (R3, already documented below): a genuinely consumed slug whose SPEC never
declared it in ``**Consumes:**`` was already a false negative before this task; it
simply loses its second (smaller) evidence source too.

**Backlog "non-terminal status" vocabulary (v0.5.1 K5).** SPEC-DOC-031's own
prefix-matched non-terminal set is DELETED; it now calls
``core.models.backlog.is_nonterminal_active_status`` — the SAME vocabulary
``features.backlog.doctor``'s BL-SCHEMA/BL-STALE checks already share (K5's "same shape
applies to backlog" note) — rather than a THIRD, independently-maintained status
classification.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, overload

from dadaia_workspace.core.models.backlog import is_nonterminal_active_status
from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    TERMINAL_EVENTS,
    BugRecord,
)
from dadaia_workspace.core.protocols.record_store import MalformedLine, RecordStore
from dadaia_workspace.features.backlog.document import load_document
from dadaia_workspace.features.specs.doctor_common import iter_archive_release_dirs
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

# ADR-11 single-source status-token vocabulary.
#
# Backlog: non-terminal/terminal classification lives in
#   core.models.backlog.is_nonterminal_active_status (v0.5.1 K5 — was a private
#   prefix-matched tuple here, now the shared source `features.backlog.doctor` also
#   reads).
# Bugs: terminal = {DELIVERED, SUPERSEDED, RESOLVED, CONSUMED, DEFERRED, REJECTED}
#   (+ free suffixes like ``— vX.Y.Z``).
# Only the NON-TERMINAL predicate drives SPEC-DOC-031: a non-terminal backlog entry
# whose slug is referenced by an archived release is the consumed-but-unsanitized
# drift — is_nonterminal_active_status is imported above (v0.5.1 K5).

# SPEC-DOC-035 (SPEC v0.12.0 FR5, ADR D5/D9): the single-source invariant — the only two
# filenames permitted loose directly under ``specs/backlog/``. Anything else (a per-entry
# item that survived the v0.12.0 consolidation, or was hand-authored outside `dadaia
# backlog new`) is drift.
_BACKLOG_SINGLE_SOURCE_FILES: frozenset[str] = frozenset({"BACKLOG.json", "AGENTS.md"})

# SPEC-DOC-031 evidence surface (SPEC v0.4.2 FR14/GRILL D6): a mention counts as
# consumption evidence only when it ASSERTS consumption, never on free-text prose —
# "non-goal", "inheritance", "provenance", "Backlog returns" and every other prose
# mention are ignored by construction, with no per-section exclusion list to maintain
# (D6 deletes the ``## Backlog returns`` special case as subsumed: a returns section is
# not a ``**Consumes:**`` declaration, so it was never actually evidence).
#
# An archived SPEC's own ``**Consumes:**`` declaration (P19: its value continues onto
# subsequent lines until a blank line or the next ``**Key:**`` line — 27 archived
# SPEC files carry this line, several wrapped across two lines). The surviving evidence
# source (v0.5.0 T-050-25A, A4.4 — the CLOSURE.md-side ``## Dispositions`` table was
# the other one, deleted; module docstring).
_CONSUMES_LINE_RE = re.compile(r"^[ \t]*\*\*Consumes:\*\*[ \t]*(?P<rest>.*)$")

# Any other bold-key line (``**Key:** value``) — the continuation-stop boundary. Matches
# the SPEC frontmatter shape (``**Status:**``, ``**Picked set:**``, ``**Branch:**``, …).
_BOLD_KEY_LINE_RE = re.compile(r"^[ \t]*\*\*[^*\n]+:\*\*")

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


@overload
def _default_iter_bug_records(
    ledger_path: Path, *, strict: Literal[False] = False
) -> Iterator[BugRecord]: ...
@overload
def _default_iter_bug_records(
    ledger_path: Path, *, strict: Literal[True]
) -> Iterator[BugRecord | MalformedLine]: ...
def _default_iter_bug_records(
    ledger_path: Path, *, strict: bool = False
) -> Iterator[BugRecord | MalformedLine]:
    """Zero-dependency fallback reader — mirrors ``doctor_closure_audit``'s own
    ``_default_iter_findings`` shape (this module holds no ``features ->
    infrastructure`` edge) and ``JsonlRecordStore.iter_records``'s own
    ``strict`` split (v0.5.1 K5 deepening): ``strict=False`` (default) silently
    skips a malformed line; ``strict=True`` yields a
    :class:`~dadaia_workspace.core.protocols.record_store.MalformedLine` instead —
    the ONE malformed-line diagnosis, never a second classification of what
    "malformed" means. Splits on a literal ``"\\n"`` only (never
    ``str.splitlines()`` — the T-045-20/AR-1 fix); every line parses through
    :meth:`~dadaia_workspace.core.models.bugs.BugRecord.from_dict`, the model's OWN
    parser, never a second hand-rolled field check."""
    if not ledger_path.is_file():
        return
    for lineno, raw_line in enumerate(ledger_path.read_text(encoding="utf-8").split("\n"), 1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            if strict:
                yield MalformedLine(
                    lineno=lineno, raw=stripped, reason=f"not valid JSON: {exc.msg}"
                )
            continue
        if not isinstance(obj, dict):
            if strict:
                yield MalformedLine(lineno=lineno, raw=stripped, reason="not a JSON object")
            continue
        try:
            yield BugRecord.from_dict(obj)
        except (ValueError, TypeError) as exc:
            if strict:
                yield MalformedLine(lineno=lineno, raw=stripped, reason=str(exc))


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
        bug_store_factory: Callable[[Path], RecordStore[BugRecord]] | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        # DI seam (v0.5.1 K5, mirrors ClosureAuditValidator's findings_store_factory,
        # A13.4): injected by a composition root that wires
        # container.build_bug_record_store; None keeps the zero-dependency default
        # reader (_default_iter_bug_records/_strict) so this leaf module never
        # imports infrastructure.
        self._bug_store_factory = bug_store_factory

    @overload
    def _iter_bug_records(
        self, ledger_path: Path, *, strict: Literal[False] = False
    ) -> Iterator[BugRecord]: ...
    @overload
    def _iter_bug_records(
        self, ledger_path: Path, *, strict: Literal[True]
    ) -> Iterator[BugRecord | MalformedLine]: ...
    def _iter_bug_records(
        self, ledger_path: Path, *, strict: bool = False
    ) -> Iterator[BugRecord | MalformedLine]:
        # container.build_bug_record_store(specs_dir) — takes specs_dir, not the
        # ledger file path (unlike findings_store_factory, which takes the file path
        # directly): a BugService has exactly ONE ledger per specs_dir, so this
        # mirrors the SAME factory `cli.commands.bugs` already calls, never a
        # second bug-store composition function with a different Path semantic.
        # Each branch below passes a LITERAL True/False (never the *strict* variable
        # itself) so the callee's own @overload resolves precisely — the same
        # explicit-branch shape ``JsonlRecordStore.iter_records`` itself is called
        # with everywhere else in this codebase.
        if self._bug_store_factory is not None:
            store = self._bug_store_factory(self.specs_dir)
            if strict:
                yield from store.iter_records(strict=True)
            else:
                yield from store.iter_records()
            return
        if strict:
            yield from _default_iter_bug_records(ledger_path, strict=True)
        else:
            yield from _default_iter_bug_records(ledger_path, strict=False)

    def _archive_consumption_hits(self, slug: str) -> list[str]:
        """Release ids of archived releases that ASSERT ``slug`` was consumed (SPEC
        v0.4.2 FR14/GRILL D6) — never a raw line-substring scan of the whole document.

        A mention counts as consumption evidence in exactly one shape: an archived
        SPEC's ``**Consumes:**`` declaration (its value plus continuation lines, P19),
        tokenized on non-slug characters and matched as a WHOLE token. The other former
        evidence source — an archived CLOSURE's ``## Dispositions`` table rows — is
        deleted (v0.5.0 T-050-25A, A4.4: CLOSURE.md retired as a going-forward artifact;
        module docstring). Narrower evidence is an accepted false NEGATIVE (R3), never a
        false positive: a genuinely consumed slug whose SPEC never declared it in
        ``**Consumes:**`` was already missed before this task.

        Everything else in the document — prose, non-goals, provenance notes, a
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
        return sorted(hits)

    def check_consumed_backlog_disposition(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-031 (re-targeted, SPEC v0.4.2 FR14/GRILL D6): WARN on a consumed-but-
        unsanitized ``## ACTIVE`` item in ``specs/backlog/BACKLOG.json``.

        Iterates the document's ACTIVE subsections (:func:`~dadaia_workspace.features.
        backlog.document.load_document`) instead of globbing per-entry files. An ACTIVE
        item whose ``**Status:**`` is an ADR-11 NON-TERMINAL token ({OPEN, PICKED,
        CANDIDATE}, case-insensitive prefix match) AND whose slug is a whole-token match
        inside an archived release's CONSUMPTION-ASSERTING evidence — an archived SPEC's
        ``**Consumes:**`` declaration (:func:`_archive_consumption_hits`, FR14; narrowed
        at v0.5.0 T-050-25A, A4.4) — ⇒ **WARNING**. The lifecycle
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
        backlog_md_path = backlog_dir / "BACKLOG.json"
        issues: list[SpecsDoctorIssue] = []
        for item in document.active:
            if item.status is None:
                continue
            if not is_nonterminal_active_status(item.status):
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

    def check_bugs_jsonl_invariant(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-033 (v0.1.46 AC-1; rewritten v0.5.0 T-050-08, FR2/A2.3; the v5
        coherence fold retired at the S1 FR23 firing, A3; v0.5.1 K5 deepening: reads
        through the injected/default ``RecordStore``, not a second hand-kept parser):
        the single canonical ``specs/bugs/BUGS.jsonl`` ledger invariant.

        ONE sub-check over the ONE canonical file (the legacy hourly-file rotation
        reader is dead under canon v6 and is not carried forward — module docstring):
        **line validity** (ERROR) — each non-blank line must parse as a
        :class:`~dadaia_workspace.core.models.bugs.BugRecord` through
        :meth:`~dadaia_workspace.core.models.bugs.BugRecord.from_dict`, the model's
        OWN parser (now enum-validating ``status`` too) — never a hand-rolled field
        check. Every line the store's ``iter_records(strict=True)`` cannot parse (not
        valid JSON, not an object, a v5-shaped line, an invalid enum value) surfaces
        as exactly ONE :class:`~dadaia_workspace.core.protocols.record_store
        .MalformedLine` -> ONE ERROR here — the ONE malformed-line diagnosis, never a
        second classification of what "v5" or "invalid" means.

        **Governance completeness is no longer diagnosed here (v0.5.1 K5).** A
        well-formed record — however incomplete for its own status — is not
        re-checked: completeness is enforced prospectively, at the
        :meth:`~dadaia_workspace.core.models.bugs.BugRecord.resolve`/``supersede``/
        ``defer``/``reject`` write seam, never retroactively against history.

        Splits on a literal ``"\n"`` only, never ``str.splitlines()`` (the
        T-045-20/AR-1 fix, now owned by the ONE reader — module docstring). Absent
        ``bugs/`` dir -> no-op.
        """
        ledger_path = self.specs_dir / "bugs" / "BUGS.jsonl"
        if not ledger_path.is_file():
            return []

        issues: list[SpecsDoctorIssue] = []
        for parsed in self._iter_bug_records(ledger_path, strict=True):
            if not isinstance(parsed, MalformedLine):
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-033",
                    severity=Severity.ERROR,
                    description=(
                        f"bugs/BUGS.jsonl line {parsed.lineno}: {parsed.reason} — "
                        "every JSONL row must be one bug-record object "
                        "(SPEC-DOC-033, ERROR)."
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
        ledger_path = self.specs_dir / "bugs" / "BUGS.jsonl"
        if not ledger_path.is_file():
            return []
        cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=BUG_ARCHIVE_THRESHOLD_DAYS)
        issues: list[SpecsDoctorIssue] = []
        for record in self._iter_bug_records(ledger_path):
            if record.status not in TERMINAL_EVENTS:
                continue
            record_ts = _parse_bug_record_ts(record.ts)
            if record_ts is not None and record_ts < cutoff:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-041",
                        severity=Severity.WARNING,
                        description=(
                            f"bugs/BUGS.jsonl record {record.id!r} has been terminal "
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
        outside ``dadaia backlog new``. ``specs/backlog/_archive/`` is excluded
        (non-recursive glob already skips it — it is a subdirectory, not a
        ``*.md`` sibling).
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
                        "specs/backlog/ — the single source is BACKLOG.json (## ACTIVE + "
                        "## LEDGER); fold it into BACKLOG.json and move the superseded "
                        "file into specs/backlog/_archive/ (SPEC-DOC-035, WARNING)."
                    ),
                    path=str(entry),
                )
            )
        return issues
