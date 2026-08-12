"""Governance validator (v0.1.55 FR1): backlog schema, bug status/JSONL, consumed-backlog.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the bug/backlog governance
invariants: candidates.md bullet format (SPEC-DOC-012), consumed-but-unsanitized backlog
(SPEC-DOC-031), bug-status canon (SPEC-DOC-032), the event-sourced JSONL bug-telemetry invariant
(SPEC-DOC-033), and unarchived-terminal backlog (SPEC-DOC-035). Leaf-only: imports the shared
leaves + core, never a sibling validator.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugCoherenceRecord, diagnose_bug_coherence_history
from dadaia_workspace.features.specs.doctor_common import iter_archive_release_dirs
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

BACKLOG_BULLET_RE = re.compile(r"^- \S.*? — .+? \(owner: [a-z-]+, contexto: .+?\)\s*$")
# SPEC-DOC-022: format for ## Hotfixes pendentes bullets
# Pattern: - <YYYY-MM-DDTHHMMSSZ> <severity> <component> — <one-liner> (post-mortem: <link>)
BACKLOG_HOTFIX_RE = re.compile(
    r"^- (\d{4}-\d{2}-\d{2}T\d{6}Z) (LOW|MEDIUM|HIGH|CRITICAL) ([\w\-/]+) — .+ \(post-mortem: .+\)$"
)

# SPEC-DOC-023: hotfix bullets older than 72 hours in ## Hotfixes pendentes get WARNING
_HOTFIX_STALE_HOURS = 72

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

# SPEC-DOC-033 (v0.1.46 AC-1): the JSONL bug-telemetry rotation ceiling. A
# ``specs/bugs/<hour>Z-<n>.jsonl`` file with more than this many rows is a hard ERROR
# (the store rolls to ``-<n+1>`` at the boundary). Kept as a local doctor constant so the
# pure ``features.specs`` module never imports the infrastructure store (layering law).
_BUGS_JSONL_ROW_CEILING = 1000

# SPEC-DOC-033 canonical bug-log filename: ``<YYYYMMDDTHH>Z-<n>.jsonl``.
_BUGS_JSONL_NAME_RE = re.compile(r"^\d{8}T\d{2}Z-\d+\.jsonl$")

# SPEC-DOC-035 (v0.1.46 AC-4): terminal backlog status prefixes. A backlog entry whose
# Status is terminal but still loose in ``specs/backlog/`` (not under ``_archive/``) WARNs —
# a consumed/shipped item must be moved into ``specs/backlog/_archive/``.
_BACKLOG_TERMINAL_PREFIXES: tuple[str, ...] = (
    "delivered",
    "consumed",
    "superseded",
    "resolved",
)

# Match a Status line in a backlog entry: ``Status: ...`` or ``**Status:** ...``.
_BACKLOG_STATUS_RE = re.compile(r"^\s*(?:\*\*)?status\*?\*?\s*:?\*?\*?\s*(.+)$", re.IGNORECASE)

# Match a bug frontmatter ``status:`` line (frontmatter is leading YAML-like lines).
_BUG_STATUS_RE = re.compile(r"^status\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)

# Aggregate / free-form backlog files that are not per-slug backlog entries.
_BACKLOG_AGGREGATE_FILES: frozenset[str] = frozenset({"candidates.md", "ideas.md", "README.md"})

# ADR-6: matches inside a ``## Backlog returns`` section of an archived CLOSURE are a
# legitimate return (the slug is being ADDED for a future release, not consumed) and are
# the documented false-positive class. SPEC-DOC-031 stays WARN (never ERR) for this reason.
_BACKLOG_RETURNS_HEADING_RE = re.compile(r"^##\s+Backlog\s+returns\b", re.IGNORECASE)


class GovernanceValidator:
    """Bug/backlog governance: candidates schema, bug status/JSONL, consumed-backlog drift."""

    def __init__(self, specs_dir: Path, public_dir: Path | None = None) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir

    def check_backlog_schema(self) -> list[SpecsDoctorIssue]:
        """Validate bullet format in specs/backlog/candidates.md (SPEC-DOC-012).

        Validates two sections:
        - ``## Candidatas ativas`` — format: ``- <name> — <one-liner> (owner: <agent>, contexto: <link>)``
        - ``## Hotfixes pendentes`` — format (D22): ``- <ts> <severity> <component> — <one-liner> (post-mortem: <link>)``

        Also emits WARNING for bullets in ``## Hotfixes pendentes`` whose timestamp is
        older than 72 hours without being moved to ``## Histórico`` (D23).

        Sections starting with ``## Histórico`` are skipped. Backlog file absent → noop.
        Failures produce WARNING (not ERROR) during initial adoption period.

        Note: only ``candidates.md`` is validated; other files under
        ``specs/backlog/`` (e.g. ``dadaia-workspace-panel.md``) are free-form
        and are not touched by this check.
        """
        issues: list[SpecsDoctorIssue] = []
        candidates_path = self.specs_dir / "backlog" / "candidates.md"
        if not candidates_path.exists():
            return issues

        text = candidates_path.read_text(encoding="utf-8")
        in_candidatas_section = False
        in_hotfixes_section = False
        now_utc = datetime.now(tz=UTC)

        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.rstrip()
            if line.startswith("## "):
                in_candidatas_section = bool(re.match(r"^##\s+Candidatas", line))
                in_hotfixes_section = bool(re.match(r"^##\s+Hotfixes\s+pendentes", line))
                continue

            # --- ## Candidatas ativas section ---
            if in_candidatas_section:
                if not line.startswith("- "):
                    continue
                if not BACKLOG_BULLET_RE.match(line):
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-012",
                            severity=Severity.WARNING,
                            description=(
                                f"candidates.md line {lineno}: bullet does not match "
                                "expected format "
                                "'- <name> — <one-liner> (owner: <agent>, contexto: <link>)': "
                                f"{line!r}"
                            ),
                            path=str(candidates_path),
                        )
                    )
                continue

            # --- ## Hotfixes pendentes section ---
            if in_hotfixes_section:
                if not line.startswith("- "):
                    continue
                m = BACKLOG_HOTFIX_RE.match(line)
                if not m:
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-012",
                            severity=Severity.WARNING,
                            description=(
                                f"candidates.md line {lineno}: hotfix bullet does not match "
                                "expected format "
                                "'- <YYYY-MM-DDTHHMMSSZ> <LOW|MEDIUM|HIGH|CRITICAL> <component>"
                                " — <one-liner> (post-mortem: <link>)': "
                                f"{line!r}"
                            ),
                            path=str(candidates_path),
                        )
                    )
                else:
                    # Check staleness (D23): timestamp older than _HOTFIX_STALE_HOURS
                    ts_raw = m.group(1)  # e.g. 2026-05-14T120000Z
                    try:
                        ts = datetime.strptime(ts_raw, "%Y-%m-%dT%H%M%SZ").replace(tzinfo=UTC)
                        age_hours = (now_utc - ts).total_seconds() / 3600
                        if age_hours > _HOTFIX_STALE_HOURS:
                            issues.append(
                                SpecsDoctorIssue(
                                    code="SPEC-DOC-012",
                                    severity=Severity.WARNING,
                                    description=(
                                        f"candidates.md line {lineno}: hotfix bullet is stale "
                                        f"({age_hours:.0f}h > {_HOTFIX_STALE_HOURS}h). "
                                        "Consider promoting to a hotfix release or moving to "
                                        "## Histórico (D23)."
                                    ),
                                    path=str(candidates_path),
                                )
                            )
                    except ValueError:
                        pass  # timestamp parse failure already flagged above

        return issues

    def _backlog_status_value(self, text: str) -> str | None:
        """Extract the (first) Status line value from a backlog entry's body.

        Accepts both ``Status: <value>`` and ``**Status:** <value>``. Returns the
        stripped value, or ``None`` when no Status line is present.
        """
        for line in text.splitlines():
            m = _BACKLOG_STATUS_RE.match(line)
            if m:
                return m.group(1).strip()
        return None

    def _archive_consumption_hits(self, slug: str) -> list[str]:
        """Release ids of archived CLOSURE/SPEC that reference ``slug`` as consumed.

        Scans every ``specs/_archive/releases/*/CLOSURE.md`` and ``.../SPEC.md`` for a
        line containing ``slug``. Lines inside a ``## Backlog returns`` section are
        EXCLUDED (ADR-6: the slug is being ADDED for a future release, not consumed — the
        documented false-positive class). Returns the sorted, de-duplicated set of
        archived release ids that reference the slug outside Backlog-returns sections.
        """
        arch = self.specs_dir / "_archive" / "releases"
        if not arch.is_dir():
            return []
        hits: set[str] = set()
        for release_dir in iter_archive_release_dirs(arch):
            release_id = release_dir.name
            for doc_name in ("CLOSURE.md", "SPEC.md"):
                doc = release_dir / doc_name
                if not doc.is_file():
                    continue
                in_backlog_returns = False
                for raw_line in doc.read_text(encoding="utf-8").splitlines():
                    if raw_line.startswith("## "):
                        in_backlog_returns = bool(_BACKLOG_RETURNS_HEADING_RE.match(raw_line))
                    if in_backlog_returns:
                        continue
                    if slug in raw_line:
                        hits.add(release_id)
                        break
        return sorted(hits)

    def check_consumed_backlog_disposition(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-031 (T-011-10, bug B1, ADR-6): WARN on consumed-but-unsanitized backlog.

        A ``specs/backlog/<slug>.md`` entry whose Status line is an ADR-11 NON-TERMINAL
        token ({OPEN, PICKED, CANDIDATE}, case-insensitive prefix match) AND whose slug is
        referenced by an archived release CLOSURE/SPEC (outside ``## Backlog returns``
        sections) ⇒ **WARNING**. The lifecycle contract is that a backlog item consumed
        into a shipped+archived release must be flipped to a terminal disposition token
        during CLOSURE; a non-terminal status on a referenced slug is the drift.

        Severity is WARN, never ERR (ADR-6): a slug mention is necessary-but-not-sufficient
        evidence of consumption — the "Backlog returns" section (excluded here) and
        defer/supersede mentions in archived CLOSUREs are the known false-positive class.
        Aggregate files (``candidates.md``/``ideas.md``/``README.md``) are skipped.
        """
        backlog_dir = self.specs_dir / "backlog"
        if not backlog_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for entry in sorted(backlog_dir.glob("*.md")):
            if entry.name in _BACKLOG_AGGREGATE_FILES:
                continue
            slug = entry.stem
            status = self._backlog_status_value(entry.read_text(encoding="utf-8"))
            if status is None:
                continue
            status_lower = status.lower()
            if not status_lower.startswith(_BACKLOG_NONTERMINAL_PREFIXES):
                continue
            hits = self._archive_consumption_hits(slug)
            if not hits:
                continue
            releases = ", ".join(hits)
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-031",
                    severity=Severity.WARNING,
                    description=(
                        f"backlog/{entry.name} has non-terminal status '{status}' but its "
                        f"slug is referenced by archived release(s) {releases} (outside "
                        "'Backlog returns' sections). If it was consumed/shipped, set a BARE "
                        "terminal status token that BL-SCHEMA accepts (e.g. 'status: "
                        "delivered'; also 'superseded'/'resolved'/'consumed'/'rejected'), "
                        "record the release in an optional 'delivered_in: vX.Y.Z' field, and "
                        "move the entry into specs/backlog/_archive/ (SPEC-DOC-035). Do NOT "
                        "append '— vX.Y.Z' to the status token itself — BL-SCHEMA rejects a "
                        "'TOKEN — vX.Y.Z' status. WARNING only — a slug mention is not proof "
                        "of consumption (ADR-6 false-positive class)."
                    ),
                    path=str(entry),
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

    def _bug_event_schema_path(self) -> Path:
        """Resolve the packaged ``bug-event-v1`` JSON Schema.

        Prefers the injected ``public_dir`` (composition-root wiring); falls back to the
        package-relative source tree (``dadaia_workspace/public/schemas/bugs/``) so the
        pure module still validates without an injected public dir. Reading a bundled
        schema resource is not I/O outside the pattern's own package.
        """
        if self.public_dir is not None:
            return self.public_dir / "schemas" / "bugs" / "bug-event-v1.schema.json"
        package_root = Path(__file__).resolve().parents[2]
        return package_root / "public" / "schemas" / "bugs" / "bug-event-v1.schema.json"

    def check_bugs_jsonl_invariant(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-033 (v0.1.46 AC-1): event-sourced JSONL bug-telemetry invariant.

        Three sub-checks over every ``specs/bugs/<hour>Z-<n>.jsonl`` (``_archive/`` excluded
        — non-recursive glob):

        1. **Per-line schema validity** (ERROR) — each non-blank line must be a JSON object
           validating ``bug-event-v1``. A malformed-JSON line or a schema violation ERRORs.
        2. **Rotation ceiling** (ERROR) — a file with more than
           :data:`_BUGS_JSONL_ROW_CEILING` rows ERRORs (the store rolls at the boundary).
        3. **Event coherence** over the terminal set ``{resolved, superseded, deferred,
           rejected}`` (``archived`` is a NON-terminal annotation and is IGNORED): a
           terminal event for a ``bug_id`` with no prior ``reported`` ERRORs; a terminal
           after an existing terminal for the same ``bug_id`` ERRORs. A ``reported`` event
           (re)opens a ``bug_id`` — clearing any prior terminal so a legitimate reopen is
           not mis-flagged as a double-terminal.

        Pure module: reads only under ``specs_dir`` plus the packaged schema resource.
        Absent ``bugs/`` dir → no-op.
        """
        bugs_dir = self.specs_dir / "bugs"
        if not bugs_dir.is_dir():
            return []

        schema_path = self._bug_event_schema_path()
        validator = None
        if schema_path.is_file():
            from jsonschema import Draft202012Validator

            validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))

        issues: list[SpecsDoctorIssue] = []
        # v0.5.0 FR2: coherence is a WHOLE-HISTORY diagnosis (the healing rule needs to
        # see events that come later than a violation), so this loop only COLLECTS one
        # (bug_id, event, position) record per valid line; the fold itself runs once,
        # after every file has been read, in `_fold_bug_coherence`.
        coherence_records: list[BugCoherenceRecord[tuple[Path, int]]] = []

        for jsonl_path in sorted(bugs_dir.glob("*.jsonl")):
            # v0.1.73 FR1: the single canonical bugs.jsonl gets schema + coherence checks
            # but NO rotation ceiling (the one-file contract has no rotation); legacy
            # hourly files keep all three sub-checks.
            is_canonical = jsonl_path.name == "bugs.jsonl"
            if not is_canonical and not _BUGS_JSONL_NAME_RE.match(jsonl_path.name):
                continue
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
            row_count = sum(1 for line in lines if line.strip())
            if not is_canonical and row_count > _BUGS_JSONL_ROW_CEILING:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-033",
                        severity=Severity.ERROR,
                        description=(
                            f"bugs/{jsonl_path.name} has {row_count} rows, exceeding the "
                            f"{_BUGS_JSONL_ROW_CEILING}-row rotation ceiling — the store must "
                            "roll to the next '-<n+1>' counter (SPEC-DOC-033, ERROR)."
                        ),
                        path=str(jsonl_path),
                    )
                )
            for lineno, raw_line in enumerate(lines, start=1):
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
                                f"bugs/{jsonl_path.name} line {lineno}: not valid JSON "
                                f"({exc.msg}) — every JSONL row must be one bug-event object "
                                "(SPEC-DOC-033, ERROR)."
                            ),
                            path=str(jsonl_path),
                        )
                    )
                    continue
                if validator is not None:
                    error = next(iter(validator.iter_errors(obj)), None)
                    if error is not None:
                        issues.append(
                            SpecsDoctorIssue(
                                code="SPEC-DOC-033",
                                severity=Severity.ERROR,
                                description=(
                                    f"bugs/{jsonl_path.name} line {lineno}: fails "
                                    f"bug-event-v1 schema ({error.message}) "
                                    "(SPEC-DOC-033, ERROR)."
                                ),
                                path=str(jsonl_path),
                            )
                        )
                        continue
                if not isinstance(obj, dict):
                    continue
                bug_id = obj.get("bug_id")
                event = obj.get("event")
                if isinstance(bug_id, str) and isinstance(event, str):
                    coherence_records.append(
                        BugCoherenceRecord(
                            bug_id=bug_id, event=event, position=(jsonl_path, lineno)
                        )
                    )
        issues.extend(self._fold_bug_coherence(coherence_records))
        return issues

    @staticmethod
    def _fold_bug_coherence(
        records: list[BugCoherenceRecord[tuple[Path, int]]],
    ) -> list[SpecsDoctorIssue]:
        """Format the WHOLE-HISTORY coherence diagnosis as ``SpecsDoctorIssue`` lines.

        A thin caller: every coherence semantic — the per-event fold, the one-terminal
        invariant, and the v0.5.0 FR2 healing rule (a violation is reported only while
        no LATER ``reported`` event exists for the same ``bug_id``) — lives in
        :func:`dadaia_workspace.core.models.bugs.diagnose_bug_coherence_history`, the
        same authority ``BugService.append_event`` folds through (via
        :func:`advance_coherence`) to REFUSE an incoherent append, so the diagnostic
        gate and the enforced gate can never diverge (v0.1.72 law). This method only
        renders the message — byte-identical to the pre-FR2 format.
        """
        issues: list[SpecsDoctorIssue] = []
        for violation in diagnose_bug_coherence_history(records):
            jsonl_path, lineno = violation.position
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-033",
                    severity=Severity.ERROR,
                    description=(
                        f"bugs/{jsonl_path.name} line {lineno}: {violation.clause} "
                        "(SPEC-DOC-033, ERROR)."
                    ),
                    path=str(jsonl_path),
                )
            )
        return issues

    def check_unarchived_terminal_backlog(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-035 (v0.1.46 AC-4): terminal-status backlog entry still loose → WARN.

        A ``specs/backlog/<slug>.md`` whose Status line is a terminal token
        ({DELIVERED, CONSUMED, SUPERSEDED, RESOLVED}, case-insensitive prefix match) but
        which still lives directly in ``specs/backlog/`` (not under ``_archive/``) is
        consumed-but-unarchived drift → WARNING (move it to ``specs/backlog/_archive/``).
        An entry already under ``_archive/`` is clean (not scanned — non-recursive glob).
        Aggregate files are skipped.
        """
        backlog_dir = self.specs_dir / "backlog"
        if not backlog_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for entry in sorted(backlog_dir.glob("*.md")):
            if entry.name in _BACKLOG_AGGREGATE_FILES:
                continue
            status = self._backlog_status_value(entry.read_text(encoding="utf-8"))
            if status is None:
                continue
            if not status.lower().startswith(_BACKLOG_TERMINAL_PREFIXES):
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-035",
                    severity=Severity.WARNING,
                    description=(
                        f"backlog/{entry.name} has terminal status '{status}' but is still "
                        "loose in specs/backlog/ — move it into specs/backlog/_archive/ "
                        "(SPEC-DOC-035, WARNING)."
                    ),
                    path=str(entry),
                )
            )
        return issues
