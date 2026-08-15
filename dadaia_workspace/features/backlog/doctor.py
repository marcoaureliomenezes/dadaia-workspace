"""``backlog doctor`` — the ENFORCED backstop (SPEC v0.12.0 FR2, ADR-D, ADR D8).

Four checks, run by **one parameterized check engine** (SPEC §3.8 #8 — no copy-paste
fan-out): each check is a ``BacklogCheck`` (a code + a callable over the shared
:class:`DoctorContext`), and the engine maps the same loop over all of them.

* **BL-SCHEMA** — every non-``idea`` item has bound ``intents[]`` (every subject resolves
  in the registry) + a valid status; a structurally invalid ``intents:``/``**Intents:**``
  block is also BL-SCHEMA; a located :class:`~dadaia_workspace.features.backlog.document.DocumentError`
  (a missing required key, an off-grammar LEDGER line) is one BL-SCHEMA per error.
* **BL-DUP** — two items share anchor-set + change → ERROR (via the classifier
  ``DUPLICATE``); a slug repeated in ``ACTIVE`` or in ``LEDGER`` → ERROR.
* **BL-CONFLICT** — two items share an anchor with incompatible change → ERROR (the divergent
  twin, caught even when hand-written; classifier ``DIVERGENT_CONFLICT``).
* **BL-STALE** (re-defined, ADR D8) — an ACTIVE item already consumed/dispositioned: its slug
  is recorded in an archived ``consumed_backlog.json`` (``ledger.read_consumed``, unchanged),
  OR it also carries a ``LEDGER`` line in the same document, OR its own ``Status`` is one of
  the six canonical terminal disposition tokens.

Pure module: all roots are **injected** (SPEC §3.8 #6); no I/O outside the supplied paths and
no subprocess. The CLI (``cli/commands/newartifacts.py``) and the pre-commit/CI chokepoint
(``cli/commands/ci.py`` + ``public/scripts/``) are thin wirings over :func:`run_backlog_doctor`.

**T-120-05 transition note.** The check engine (``_CHECKS``, ``DoctorContext`` and every
``_check_*`` body below) is generic over :class:`_SchemaItem` — a structural
:class:`~typing.Protocol` (``slug``/``status``/``intents``/``intents_error``) satisfied by
BOTH the legacy per-entry :class:`~dadaia_workspace.features.backlog.preview.BacklogItem`
and the new single-source :class:`~dadaia_workspace.features.backlog.document.ActiveItem` —
so the SAME engine serves the still-live legacy reading path today and the new document
model once T-120-08 wires it in, with no duplicated check logic and no dual-shape reader
(SPEC §3 standing green rule). :func:`run_backlog_doctor`, the CLI-facing live entry point,
is **unchanged in its reading behaviour** by this task: it still calls
:func:`~dadaia_workspace.features.backlog.preview.load_backlog_items` over
``specs/backlog/*.md`` and feeds an empty ``ledger`` (the old shape has no LEDGER section) —
only the cutover commit (T-120-08) repoints it at
:func:`~dadaia_workspace.features.backlog.document.load_document`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.backlog import (
    INTENTS_EXEMPT_STATUS,
    Intent,
    is_intents_exempt,
    is_terminal_disposition,
)
from dadaia_workspace.features.backlog.classifier import BoundItem, Verdict, classify
from dadaia_workspace.features.backlog.document import DocumentError, LedgerRow
from dadaia_workspace.features.backlog.ledger import read_consumed
from dadaia_workspace.features.backlog.preview import (
    BacklogItem,
    bound_anchor_changes,
    load_backlog_items,
)
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry

__all__ = [
    "BacklogDoctorCode",
    "Finding",
    "Severity",
    "run_backlog_doctor",
]

#: A located document-level error whose own message already IS the intents diagnostic
#: surfaced (once, deduplicated) via the item's own ``intents_error`` in the per-item
#: loop below — skipped here so a malformed ``**Intents:**``/``intents:`` block never
#: produces two findings for the same item.
_INTENTS_DOCUMENT_ERROR_PREFIXES = (
    "malformed intents[] YAML:",
    "malformed intents[] frontmatter:",
    "**Intents:** key present",
)

#: The one status EXEMPT from the resolvable-typed-intents requirement (v0.1.55 FR5, bug
#: ``backlog-new-stub-readme-lag-intents-schema``). An ``idea`` is an unbound brainstorm: it
#: carries no bound ``intents[]`` yet, so the "no intents[] declared" and unresolved-subject
#: BL-SCHEMA errors are held until the item matures to ``candidate`` and beyond. This is a
#: STATUS gate, NOT a blanket exemption — a malformed ``intents:`` frontmatter and an invalid
#: status still fire at ANY status.
_INTENTS_EXEMPT_STATUS = INTENTS_EXEMPT_STATUS

#: Statuses accepted as valid in BL-SCHEMA (kept permissive; the backlog status vocabulary is
#: informal — see ``DADAIA.md`` §5, Backlog). ``None``/empty is the only invalid case here.
_KNOWN_STATUSES = frozenset(
    {
        "idea",
        "candidate",
        "picked",
        "in-progress",
        "delivered",
        "rejected",
        "deferred",
        "done",
        "closed",
        "open",
    }
)


class BacklogDoctorCode(StrEnum):
    """The four backlog-consistency check codes (SPEC §3.4)."""

    BL_SCHEMA = "BL-SCHEMA"
    BL_DUP = "BL-DUP"
    BL_CONFLICT = "BL-CONFLICT"
    BL_STALE = "BL-STALE"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """One backlog-doctor finding."""

    code: BacklogDoctorCode
    severity: Severity
    message: str
    slug: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "slug": self.slug,
        }


class _SchemaItem(Protocol):
    """Structural shape the four checks need — satisfied by both the legacy per-entry
    :class:`~dadaia_workspace.features.backlog.preview.BacklogItem` (until T-120-08) and
    the new single-source :class:`~dadaia_workspace.features.backlog.document.ActiveItem`
    (fixture-tested from T-120-05, unwired until T-120-08).

    Declared as read-only ``@property`` members (not plain annotated attributes):
    both concrete types are FROZEN dataclasses, and mypy treats a frozen dataclass
    field as read-only — a plain Protocol attribute annotation demands read+write.
    """

    @property
    def slug(self) -> str: ...
    @property
    def status(self) -> str | None: ...
    @property
    def intents(self) -> tuple[Intent, ...]: ...
    @property
    def intents_error(self) -> str | None: ...


@dataclass
class DoctorContext:
    """Everything the check engine needs, computed once and shared across all checks."""

    items: Sequence[_SchemaItem]
    registry: Registry
    consumed: dict[str, set[str]]
    #: ``## LEDGER`` rows of the document model (ADR D8's BL-STALE condition (b) and
    #: BL-DUP's cross-LEDGER duplicate-slug condition). Always empty for the legacy
    #: per-entry reading path, which has no LEDGER section.
    ledger: tuple[LedgerRow, ...] = ()
    #: Located :class:`~dadaia_workspace.features.backlog.document.DocumentError`
    #: diagnostics from the document parser (a missing required key, an off-grammar
    #: LEDGER line). Always empty for the legacy per-entry reading path.
    document_errors: tuple[DocumentError, ...] = ()
    #: slug -> (anchor_changes, unresolved-messages), bound once.
    bound: dict[str, tuple[dict[str, str], list[str]]] = field(default_factory=dict)

    def bound_item(self, slug: str) -> BoundItem:
        anchor_changes, _ = self.bound[slug]
        return BoundItem(slug=slug, anchor_changes=anchor_changes)


# ── the four checks (each a pure function over the shared context) ───────────────


def _check_schema(ctx: DoctorContext) -> list[Finding]:
    findings: list[Finding] = []
    # Items whose own intents_error already covers the diagnostic (below) — skip the
    # matching DocumentError so a malformed **Intents:**/intents: block never produces
    # two findings for the same item.
    intents_error_slugs = {item.slug for item in ctx.items if item.intents_error is not None}
    malformed_slugs: set[str] = set()
    for error in ctx.document_errors:
        if error.message.startswith(_INTENTS_DOCUMENT_ERROR_PREFIXES) and (
            error.slug is None or error.slug in intents_error_slugs
        ):
            continue
        findings.append(
            Finding(BacklogDoctorCode.BL_SCHEMA, Severity.ERROR, error.message, slug=error.slug)
        )
        if error.slug is not None:
            malformed_slugs.add(error.slug)

    for item in ctx.items:
        if item.slug in malformed_slugs:
            # A located document-level error (e.g. a missing required key) already
            # covers this item — downstream schema noise for it is suppressed, exactly
            # as a frontmatter/intents parse failure suppresses it below (FR10).
            continue
        # A malformed ``intents:``/``**Intents:**`` block is always BL-SCHEMA, at ANY
        # status (FR10, v0.1.65 — preserved bit for bit over the new shape).
        if item.intents_error is not None:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_SCHEMA,
                    Severity.ERROR,
                    f"malformed intents[] frontmatter: {item.intents_error}",
                    slug=item.slug,
                )
            )
            continue
        exempt = is_intents_exempt(item.status)
        # FR5 status gate: the no-intents and unresolved-subject errors are held for an
        # ``idea`` (unbound brainstorm) and become mandatory at ``candidate`` and beyond.
        if not item.intents and not exempt:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_SCHEMA,
                    Severity.ERROR,
                    "no intents[] declared (every backlog item at status 'candidate' or "
                    "beyond must carry bound intents; 'idea' entries are exempt)",
                    slug=item.slug,
                )
            )
        # An invalid status token is always BL-SCHEMA, at ANY status.
        if item.status is not None and item.status.lower() not in _KNOWN_STATUSES:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_SCHEMA,
                    Severity.ERROR,
                    f"invalid status {item.status!r}",
                    slug=item.slug,
                )
            )
        if not exempt:
            _, unresolved = ctx.bound[item.slug]
            for message in unresolved:
                findings.append(
                    Finding(BacklogDoctorCode.BL_SCHEMA, Severity.ERROR, message, slug=item.slug)
                )
    return findings


def _pairwise(
    ctx: DoctorContext, want: Verdict, code: BacklogDoctorCode, label: str
) -> list[Finding]:
    """Shared pairwise body for BL-DUP and BL-CONFLICT (classifier-driven)."""
    findings: list[Finding] = []
    bound_items = [ctx.bound_item(item.slug) for item in ctx.items if not ctx.bound[item.slug][1]]
    seen: set[frozenset[str]] = set()
    for i, new in enumerate(bound_items):
        existing = bound_items[:i]
        for result in classify(new, existing):
            if result.verdict is want:
                pair = frozenset({new.slug, result.other_slug})
                if pair in seen:
                    continue
                seen.add(pair)
                findings.append(
                    Finding(
                        code,
                        Severity.ERROR,
                        f"{label} with backlog item {result.other_slug!r} "
                        f"(shared anchors: {', '.join(result.shared_anchors)})",
                        slug=new.slug,
                    )
                )
    return findings


def _check_duplicate_slugs(ctx: DoctorContext) -> list[Finding]:
    """BL-DUP's second condition (SPEC FR2): the same slug appearing twice in ``ACTIVE``
    or twice in ``LEDGER``. Never fires over the legacy per-entry model — the filesystem
    (one file per slug) already guarantees ACTIVE-slug uniqueness there, and it has no
    LEDGER section at all."""
    findings: list[Finding] = []
    seen_active: set[str] = set()
    for item in ctx.items:
        if item.slug in seen_active:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_DUP,
                    Severity.ERROR,
                    f"slug {item.slug!r} appears more than once in ACTIVE",
                    slug=item.slug,
                )
            )
        else:
            seen_active.add(item.slug)
    seen_ledger: set[str] = set()
    for row in ctx.ledger:
        if row.slug in seen_ledger:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_DUP,
                    Severity.ERROR,
                    f"slug {row.slug!r} appears more than once in LEDGER",
                    slug=row.slug,
                )
            )
        else:
            seen_ledger.add(row.slug)
    return findings


def _check_dup(ctx: DoctorContext) -> list[Finding]:
    return _pairwise(
        ctx, Verdict.DUPLICATE, BacklogDoctorCode.BL_DUP, "duplicate"
    ) + _check_duplicate_slugs(ctx)


def _check_conflict(ctx: DoctorContext) -> list[Finding]:
    return _pairwise(
        ctx, Verdict.DIVERGENT_CONFLICT, BacklogDoctorCode.BL_CONFLICT, "divergent conflict"
    )


def _check_stale(ctx: DoctorContext) -> list[Finding]:
    """BL-STALE, re-defined over the document model (ADR D8): an ACTIVE item already
    consumed/dispositioned fires on ANY of three ORed conditions — (a) its slug is
    recorded in an archived ``consumed_backlog.json`` (``ledger.read_consumed``,
    unchanged, FR4-kept), (b) it also carries a ``LEDGER`` line in the same document, or
    (c) its own ``Status`` is itself one of the six canonical terminal disposition
    tokens. Condition (b)/(c) are inert over the legacy per-entry model (empty
    ``ctx.ledger``; no live per-entry item carries a terminal-token ``Status`` today)."""
    findings: list[Finding] = []
    ledger_slugs = {row.slug for row in ctx.ledger}
    for item in ctx.items:
        reasons: list[str] = []
        if item.slug in ctx.consumed:
            reasons.append("recorded as consumed in an archived release's consumed_backlog ledger")
        if item.slug in ledger_slugs:
            reasons.append("also carries a LEDGER line in the same document")
        if item.status is not None and is_terminal_disposition(item.status):
            reasons.append(f"its own Status {item.status!r} is a terminal disposition token")
        if reasons:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_STALE,
                    Severity.ERROR,
                    "ACTIVE item is already consumed/dispositioned (" + "; ".join(reasons) + ") "
                    "— it should be a LEDGER line, not an ACTIVE subsection",
                    slug=item.slug,
                )
            )
    return findings


#: A single parameterized registry of checks (SPEC §3.8 #8 — no copy-paste fan-out).
@dataclass(frozen=True)
class _BacklogCheck:
    code: BacklogDoctorCode
    run: Callable[[DoctorContext], list[Finding]]


_CHECKS: tuple[_BacklogCheck, ...] = (
    _BacklogCheck(BacklogDoctorCode.BL_SCHEMA, _check_schema),
    _BacklogCheck(BacklogDoctorCode.BL_DUP, _check_dup),
    _BacklogCheck(BacklogDoctorCode.BL_CONFLICT, _check_conflict),
    _BacklogCheck(BacklogDoctorCode.BL_STALE, _check_stale),
)


def run_checks(ctx: DoctorContext) -> list[Finding]:
    """Run the four parameterized checks over an already-built :class:`DoctorContext`.

    The shared engine both :func:`run_backlog_doctor` (the legacy-reading live path) and
    the document-model fixture tests drive — never copy-pasted, never duplicated per
    model. Findings are returned in check order then item order; an empty list ⇒ clean.
    """
    findings: list[Finding] = []
    for check in _CHECKS:
        findings.extend(check.run(ctx))
    return findings


def _split_legacy_frontmatter_errors(
    items: Sequence[BacklogItem],
) -> tuple[list[Finding], list[BacklogItem]]:
    """FR10 (v0.1.65), legacy per-entry model only: an item whose frontmatter failed to
    parse as YAML is its own loud BL-SCHEMA ERROR, with every downstream diagnostic
    (no-intents, unresolved subjects, status) suppressed for it — they would all be
    artifacts of the parse failure, not independent findings. ``document.ActiveItem``
    has no equivalent concept (there is no single YAML frontmatter blob to fail parsing
    in the new shape — a malformed ``**Intents:**`` block is captured as ``intents_error``
    instead, handled generically by :func:`_check_schema`), so this legacy-only split
    stays here rather than in the shared, model-agnostic check engine.
    """
    findings: list[Finding] = []
    clean: list[BacklogItem] = []
    for item in items:
        if item.frontmatter_error is not None:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_SCHEMA,
                    Severity.ERROR,
                    f"frontmatter YAML parse error: {item.frontmatter_error}",
                    slug=item.slug,
                )
            )
            continue
        clean.append(item)
    return findings, clean


def run_backlog_doctor(
    *,
    specs_dir: Path,
    source_root: Path,
    catalog_path: Path,
    alias_map_path: Path,
    archive_root: Path,
    cli_anchors: frozenset[str],
) -> list[Finding]:
    """Run BL-SCHEMA/DUP/CONFLICT/STALE over the live backlog and return all findings.

    All roots are injected (SPEC §3.8 #6), including ``cli_anchors`` — the pre-derived
    ``cli``-kind anchor set threaded in from the CLI composition boundary (FR1b), so this
    feature never imports ``cli.main``. The registry is recomputed from live truth; the ledger
    read is a no-op when absent.

    **Unchanged reading behaviour (T-120-05).** Still reads the legacy per-entry model via
    :func:`~dadaia_workspace.features.backlog.preview.load_backlog_items` over
    ``specs/backlog/*.md`` — the T-120-08 cutover is the only commit that repoints this at
    :func:`~dadaia_workspace.features.backlog.document.load_document` (SPEC §3 standing
    green rule: the old shape stays validated by tooling reading the old shape until then).
    Findings are returned in check order then item order; an empty list ⇒ a clean backlog.
    """
    registry = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=specs_dir,
        cli_anchors=cli_anchors,
    )
    raw_items = load_backlog_items(specs_dir / "backlog")
    consumed = read_consumed(archive_root)

    frontmatter_findings, items = _split_legacy_frontmatter_errors(raw_items)

    ctx = DoctorContext(items=items, registry=registry, consumed=consumed, ledger=())
    for item in items:
        ctx.bound[item.slug] = bound_anchor_changes(item, registry)

    return frontmatter_findings + run_checks(ctx)
