"""``backlog doctor`` — the ENFORCED backstop (SPEC v0.12.0 FR2, ADR-D, ADR D8; v0.5.0
FR5, A5.2; operator ruling 2026-08-28 — ``BACKLOG.md`` -> ``BACKLOG.json``).

Three checks, run by **one parameterized check engine** (SPEC §3.8 #8 — no copy-paste
fan-out): each check is a ``BacklogCheck`` (a code + a callable over the shared
:class:`DoctorContext`), and the engine maps the same loop over all of them.

* **BL-SCHEMA** — every non-``idea`` item has bound ``intents[]`` (every subject resolves
  in the registry) + a valid status; a structurally invalid ``intents`` value is also
  BL-SCHEMA; a located :class:`~dadaia_workspace.features.backlog.document.DocumentError`
  (a missing required key, or a duplicate ``id`` in ``active[]``) is one BL-SCHEMA per
  error.
* **BL-CONFLICT** — two items share an anchor with incompatible change → ERROR (the divergent
  twin, caught even when hand-written; classifier ``DIVERGENT_CONFLICT``).
* **BL-STALE** (re-defined, ADR D8; v0.5.0 A5.2) — an ACTIVE item already
  dispositioned: it already has an exit record in ``backlog_histo.jsonl`` (the retired
  in-document ``## LEDGER`` condition's replacement — v0.5.0 FR5), OR its own
  ``Status`` is one of the five canonical terminal disposition tokens.

**BL-DUP is DELETED, not disabled (v0.5.0 A5.2) — still true under the JSON document.**
With ``BACKLOG.json`` holding only the live ``active[]`` array and every exit landing as
one append-only ``backlog_histo.jsonl`` record keyed by slug, a duplicate EXIT is
structurally impossible — there is no second place a slug's closure could be
hand-duplicated into (the migration to JSON does not reopen this: ``backlog_histo.jsonl``
stays the one, append-only exit ledger; it is not folded back into ``BACKLOG.json``). `BL
check codes 4 -> 3`; the classifier's ``DUPLICATE`` verdict (same anchor-set + change on
two live items) and the same-id-twice-in-``active`` check (now a plain
:class:`~dadaia_workspace.features.backlog.document.DocumentError`, surfaced as
BL-SCHEMA rather than a dedicated code) retire with BL-DUP — both existed to police the
dual-section document's duplicate-closure failure mode this task's SPEC (FR5) names as
its bug-history evidence, not an independent invariant.

Pure module: all roots are **injected** (SPEC §3.8 #6); no I/O outside the supplied paths and
no subprocess — ``histo_store``, when supplied, is an already-built
:class:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore` (DI: the
CLI composition boundary builds it, this module only ever calls the instance it is
handed, never constructs one itself — ADR-0001 retired the single-adapter
``RecordStore`` Protocol this used to type against). The CLI
(``cli/commands/newartifacts.py``) and the pre-commit/CI chokepoint
(``cli/commands/ci.py`` + ``public/scripts/``) are thin wirings over :func:`run_backlog_doctor`,
which reads the single source ``specs/backlog/BACKLOG.json`` through
:func:`~dadaia_workspace.features.backlog.document.load_document` (SPEC v0.12.0 FR1, ADR #14;
operator ruling 2026-08-28) — there is no per-entry fallback and no Markdown dual path.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.doctor_rules import Rule
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.models.backlog import (
    INTENTS_EXEMPT_STATUS,
    is_intents_exempt,
)
from dadaia_workspace.core.models.histo import HistoRecord, is_terminal_disposition
from dadaia_workspace.features.backlog.classifier import BoundItem, Verdict, classify
from dadaia_workspace.features.backlog.document import ActiveItem, DocumentError, load_document
from dadaia_workspace.features.backlog.preview import bound_anchor_changes
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

__all__ = [
    "RULES",
    "BacklogDoctorCode",
    "Finding",
    "LedgerRule",
    "Severity",
    "build_context",
    "run_backlog_doctor",
]

#: A located document-level error whose own message already IS the intents diagnostic
#: surfaced (once, deduplicated) via the item's own ``intents_error`` in the per-item
#: loop below — skipped here so a malformed ``intents`` value never produces two
#: findings for the same item.
_INTENTS_DOCUMENT_ERROR_PREFIXES = ("malformed intents[] frontmatter:",)

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
    """The three backlog-consistency check codes (SPEC §3.4; v0.5.0 A5.2 — BL-DUP
    deleted, structurally impossible under the single-section + histo shape)."""

    BL_SCHEMA = "BL-SCHEMA"
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


@dataclass
class DoctorContext:
    """Everything the check engine needs, computed once and shared across all checks."""

    items: Sequence[ActiveItem]
    registry: Registry
    #: Slugs already carrying an exit record in ``backlog_histo.jsonl`` (v0.5.0 FR5) —
    #: ADR D8's BL-STALE condition (b)'s replacement for the retired in-document
    #: ``## LEDGER`` check. Empty when no ``histo_store`` was supplied (A2.8-style
    #: no-op, never a false ERROR) or a fixture-built context that supplies none.
    histo_slugs: frozenset[str] = frozenset()
    #: Located :class:`~dadaia_workspace.features.backlog.document.DocumentError`
    #: diagnostics from the document parser (a missing required key). Empty when the
    #: document parsed with no located errors.
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
    # matching DocumentError so a malformed 'intents' value never produces two findings
    # for the same item.
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
        # A malformed 'intents' value is always BL-SCHEMA, at ANY status (FR10, v0.1.65
        # — preserved bit for bit over the JSON-native shape).
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


def _check_conflict(ctx: DoctorContext) -> list[Finding]:
    """BL-CONFLICT (classifier-driven): two items share an anchor with an incompatible
    change (the divergent twin). BL-DUP's sibling pairwise verdict (``DUPLICATE`` — same
    anchor-set + change) is no longer consumed here: it retired with BL-DUP (v0.5.0
    A5.2) — the classifier still computes it (unchanged, ``classifier.py`` is out of
    this task's write set), this check simply never asks for it."""
    findings: list[Finding] = []
    bound_items = [ctx.bound_item(item.slug) for item in ctx.items if not ctx.bound[item.slug][1]]
    seen: set[frozenset[str]] = set()
    for i, new in enumerate(bound_items):
        existing = bound_items[:i]
        for result in classify(new, existing):
            if result.verdict is Verdict.DIVERGENT_CONFLICT:
                pair = frozenset({new.slug, result.other_slug})
                if pair in seen:
                    continue
                seen.add(pair)
                findings.append(
                    Finding(
                        BacklogDoctorCode.BL_CONFLICT,
                        Severity.ERROR,
                        f"divergent conflict with backlog item {result.other_slug!r} "
                        f"(shared anchors: {', '.join(result.shared_anchors)})",
                        slug=new.slug,
                    )
                )
    return findings


def _check_stale(ctx: DoctorContext) -> list[Finding]:
    """BL-STALE, re-defined over the single-section document (ADR D8; v0.5.0 A5.2): an
    ACTIVE item already dispositioned fires on either ORed condition — (a) it already
    has an exit record in ``backlog_histo.jsonl`` (the retired in-document ``## LEDGER``
    condition's replacement — ``ctx.histo_slugs``, empty/no-op when no ``histo_store``
    was supplied), or (b) its own ``Status`` is itself one of the canonical terminal
    dispositions (``core.models.histo.TERMINAL_DISPOSITIONS``).

    A picked item stays ``picked`` in ``active[]`` and exits ONCE, at closure (0.4.7
    FR7, T-047-05): the pick-time provisional exit this check's deleted third condition
    policed no longer exists."""
    findings: list[Finding] = []
    for item in ctx.items:
        reasons: list[str] = []
        if item.slug in ctx.histo_slugs:
            reasons.append("already has an exit record in backlog_histo.jsonl")
        if item.status is not None and is_terminal_disposition(item.status):
            reasons.append(f"its own Status {item.status!r} is a terminal disposition token")
        if reasons:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_STALE,
                    Severity.ERROR,
                    "ACTIVE item is already dispositioned (" + "; ".join(reasons) + ") "
                    "— it should have exited to backlog_histo.jsonl, not stayed an ACTIVE "
                    "subsection",
                    slug=item.slug,
                )
            )
    return findings


#: This section's binding of the ONE doctor rule record (0.4.7 FR5): the `ledgers`
#: section's rules run over the shared :class:`DoctorContext` and emit :class:`Finding`.
type LedgerRule = Rule[DoctorContext, Finding]

SECTION = "ledgers"

#: The `ledgers` section's rules — the same record `features/specs/rules.py` fills, so
#: `dadaia doctor` collects, renders and scores all three sections through one engine
#: (T-047-03 widens this tuple to every ledger without touching the collector).
RULES: tuple[LedgerRule, ...] = (
    Rule(
        (BacklogDoctorCode.BL_SCHEMA.value,),
        SECTION,
        _check_schema,
        fix_help="sed -i '<line>s|.*|<the corrected entry line>|' specs/backlog/BACKLOG.json",
    ),
    Rule(
        (BacklogDoctorCode.BL_CONFLICT.value,),
        SECTION,
        _check_conflict,
        fix_help=f"{DADAIA_BIN} backlog exit <slug> --disposition superseded --reason <the-twin-slug>",
    ),
    Rule(
        (BacklogDoctorCode.BL_STALE.value,),
        SECTION,
        _check_stale,
        fix_help=(
            f"{DADAIA_BIN} backlog exit <slug> --disposition <disposition> "
            "<--release id|--reason why>"
        ),
    ),
)


def run_checks(ctx: DoctorContext) -> list[Finding]:
    """Run every rule of the `ledgers` section over an already-built context.

    The shared engine both :func:`run_backlog_doctor` (the live CLI-facing path) and the
    document-model fixture tests drive — never copy-pasted, never duplicated. Findings
    are returned in check order then item order; an empty list ⇒ clean.
    """
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule.run(ctx))
    return findings


def build_context(
    *,
    specs_dir: Path,
    source_root: Path,
    catalog_path: Path,
    alias_map_path: Path,
    cli_anchors: frozenset[str],
    histo_store: JsonlRecordStore[HistoRecord] | None = None,
) -> DoctorContext:
    """Build the shared :class:`DoctorContext` over the single-source ``BACKLOG.json``.

    All roots are injected (SPEC §3.8 #6), including ``cli_anchors`` — the pre-derived
    ``cli``-kind anchor set threaded in from the CLI composition boundary (FR1b), so this
    feature never imports ``cli.main``. The registry is recomputed from live truth.

    ``histo_store`` (v0.5.0 FR5/A13.4) is an already-built
    :class:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore` — DI
    (built directly by the one real CLI callsite, ``cli.commands.newartifacts``'s
    ``backlog_doctor_cmd``, per ADR-0001: a single-consumer store builder has no reason
    to be a container seam), never constructed by this pure module. ``None`` (the
    default) is a no-op for BL-STALE condition (a), never a false ERROR — this is the
    seam :func:`run_backlog_doctor` resolves the generic backlog-histo store through;
    ``histo_store``'s second real caller is
    :func:`~dadaia_workspace.features.backlog.document.backlog_exit`.

    Reads ``specs/backlog/BACKLOG.json`` through
    :func:`~dadaia_workspace.features.backlog.document.load_document` (SPEC v0.12.0 FR1/FR2,
    ADR #14; operator ruling 2026-08-28 — BACKLOG.md is DELETED, not kept as a fallback):
    an absent document yields an empty model, so a context with no backlog is a clean
    no-op (A2.8). Findings are returned in check order then item order; an empty list ⇒
    a clean backlog.
    """
    registry = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=specs_dir,
        cli_anchors=cli_anchors,
    )
    document = load_document(specs_dir / "backlog")
    histo_slugs: frozenset[str] = (
        frozenset(record.id for record in histo_store.iter_records())
        if histo_store is not None
        else frozenset()
    )

    ctx = DoctorContext(
        items=list(document.active),
        registry=registry,
        histo_slugs=histo_slugs,
        document_errors=document.errors,
    )
    for item in document.active:
        ctx.bound[item.slug] = bound_anchor_changes(item, registry)

    return ctx


def run_backlog_doctor(
    *,
    specs_dir: Path,
    source_root: Path,
    catalog_path: Path,
    alias_map_path: Path,
    cli_anchors: frozenset[str],
    histo_store: JsonlRecordStore[HistoRecord] | None = None,
) -> list[Finding]:
    """Build the context and run every `ledgers` rule over it — the one-shot path."""
    return run_checks(
        build_context(
            specs_dir=specs_dir,
            source_root=source_root,
            catalog_path=catalog_path,
            alias_map_path=alias_map_path,
            cli_anchors=cli_anchors,
            histo_store=histo_store,
        )
    )
