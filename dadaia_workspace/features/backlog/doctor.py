"""``backlog doctor`` — the ENFORCED backstop (SPEC v0.12.0 FR2, ADR-D, ADR D8; v0.5.0
FR5, A5.2).

Three checks, run by **one parameterized check engine** (SPEC §3.8 #8 — no copy-paste
fan-out): each check is a ``BacklogCheck`` (a code + a callable over the shared
:class:`DoctorContext`), and the engine maps the same loop over all of them.

* **BL-SCHEMA** — every non-``idea`` item has bound ``intents[]`` (every subject resolves
  in the registry) + a valid status; a structurally invalid ``intents:``/``**Intents:**``
  block is also BL-SCHEMA; a located :class:`~dadaia_workspace.features.backlog.document.DocumentError`
  (a missing required key) is one BL-SCHEMA per error.
* **BL-CONFLICT** — two items share an anchor with incompatible change → ERROR (the divergent
  twin, caught even when hand-written; classifier ``DIVERGENT_CONFLICT``).
* **BL-STALE** (re-defined, ADR D8; v0.5.0 A5.2) — an ACTIVE item already
  consumed/dispositioned: its slug is recorded in the relocated consumed-backlog histo
  ledger (``ledger.read_consumed``, T-050-13A/A5.5 — reads
  ``consumed_backlog_histo.jsonl`` through an injected
  ``RecordStore[ConsumedBacklogHistoRecord]``, the relocation target for the 18
  per-release ``consumed_backlog.json`` sidecars FR6 deletes), OR it already has an
  exit record in ``backlog_histo.jsonl`` (the retired in-document ``## LEDGER``
  condition's replacement — v0.5.0 FR5), OR its own ``Status`` is one of the six
  canonical terminal disposition tokens.

**BL-DUP is DELETED, not disabled (v0.5.0 A5.2).** With ``BACKLOG.md`` holding only
``## ACTIVE`` and every exit landing as one append-only ``backlog_histo.jsonl`` record
keyed by slug, a duplicate EXIT is structurally impossible — there is no second place a
slug's closure could be hand-duplicated into. `BL check codes 4 -> 3`; the classifier's
``DUPLICATE`` verdict (same anchor-set + change on two live items) and the
same-slug-twice-in-``ACTIVE`` check retire with it — both existed to police the
dual-section document's duplicate-closure failure mode this task's SPEC (FR5) names as
its bug-history evidence, not an independent invariant.

Pure module: all roots are **injected** (SPEC §3.8 #6); no I/O outside the supplied paths and
no subprocess (``histo_store``/``consumed_histo_store``, when supplied, are each an
already-built :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` — DI
via ``core.protocols``, never a direct ``infrastructure`` import). The CLI
(``cli/commands/newartifacts.py``) and the pre-commit/CI chokepoint
(``cli/commands/ci.py`` + ``public/scripts/``) are thin wirings over :func:`run_backlog_doctor`,
which reads the single source ``specs/backlog/BACKLOG.md`` through
:func:`~dadaia_workspace.features.backlog.document.load_document` (SPEC v0.12.0 FR1, ADR #14)
— the T-120-08 cutover; there is no per-entry fallback.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.models.backlog import (
    INTENTS_EXEMPT_STATUS,
    BacklogHistoRecord,
    ConsumedBacklogHistoRecord,
    is_intents_exempt,
    is_terminal_disposition,
)
from dadaia_workspace.core.protocols.record_store import RecordStore
from dadaia_workspace.features.backlog.classifier import BoundItem, Verdict, classify
from dadaia_workspace.features.backlog.document import ActiveItem, DocumentError, load_document
from dadaia_workspace.features.backlog.ledger import read_consumed
from dadaia_workspace.features.backlog.preview import bound_anchor_changes
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
    consumed: dict[str, set[str]]
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
    ACTIVE item already consumed/dispositioned fires on ANY of three ORed conditions —
    (a) its slug is recorded in the relocated consumed-backlog histo ledger
    (``ledger.read_consumed``, T-050-13A/A5.5 — empty/no-op when no
    ``consumed_histo_store`` was supplied), (b) it already has an exit record
    in ``backlog_histo.jsonl`` (the retired in-document ``## LEDGER`` condition's
    replacement — ``ctx.histo_slugs``, empty/no-op when no ``histo_store`` was
    supplied), or (c) its own ``Status`` is itself one of the six canonical terminal
    disposition tokens."""
    findings: list[Finding] = []
    for item in ctx.items:
        reasons: list[str] = []
        if item.slug in ctx.consumed:
            reasons.append("recorded as consumed in an archived release's consumed_backlog ledger")
        if item.slug in ctx.histo_slugs:
            reasons.append("already has an exit record in backlog_histo.jsonl")
        if item.status is not None and is_terminal_disposition(item.status):
            reasons.append(f"its own Status {item.status!r} is a terminal disposition token")
        if reasons:
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_STALE,
                    Severity.ERROR,
                    "ACTIVE item is already consumed/dispositioned (" + "; ".join(reasons) + ") "
                    "— it should have exited to backlog_histo.jsonl, not stayed an ACTIVE "
                    "subsection",
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
    _BacklogCheck(BacklogDoctorCode.BL_CONFLICT, _check_conflict),
    _BacklogCheck(BacklogDoctorCode.BL_STALE, _check_stale),
)


def run_checks(ctx: DoctorContext) -> list[Finding]:
    """Run the four parameterized checks over an already-built :class:`DoctorContext`.

    The shared engine both :func:`run_backlog_doctor` (the live CLI-facing path) and the
    document-model fixture tests drive — never copy-pasted, never duplicated. Findings
    are returned in check order then item order; an empty list ⇒ clean.
    """
    findings: list[Finding] = []
    for check in _CHECKS:
        findings.extend(check.run(ctx))
    return findings


def run_backlog_doctor(
    *,
    specs_dir: Path,
    source_root: Path,
    catalog_path: Path,
    alias_map_path: Path,
    cli_anchors: frozenset[str],
    histo_store: RecordStore[BacklogHistoRecord] | None = None,
    consumed_histo_store: RecordStore[ConsumedBacklogHistoRecord] | None = None,
) -> list[Finding]:
    """Run BL-SCHEMA/CONFLICT/STALE over the single-source ``BACKLOG.md`` and return
    all findings.

    All roots are injected (SPEC §3.8 #6), including ``cli_anchors`` — the pre-derived
    ``cli``-kind anchor set threaded in from the CLI composition boundary (FR1b), so this
    feature never imports ``cli.main``. The registry is recomputed from live truth.

    ``histo_store`` (v0.5.0 FR5/A13.4) and ``consumed_histo_store`` (v0.5.0 T-050-13A/
    A5.5) are each an already-built
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` — DI via
    ``core.protocols`` (composed at ``container.build_backlog_histo_store`` and
    ``container.build_consumed_backlog_histo_store`` respectively), never a direct
    ``infrastructure`` import from this pure module. ``None`` (the default for both) is
    a no-op for the corresponding BL-STALE condition, never a false ERROR — this is the
    seam :func:`run_backlog_doctor` resolves the generic backlog-histo stores through:
    ``histo_store``'s second real caller is
    :func:`~dadaia_workspace.features.backlog.document.backlog_exit`;
    ``consumed_histo_store`` replaces the pre-relocation ``archive_root``
    directory-glob parameter (T-050-13A relocated the 18 per-release
    ``consumed_backlog.json`` sidecars into one ``consumed_histo_store``-backed file
    before FR6/T-050-14 deletes the tree they lived under).

    Reads ``specs/backlog/BACKLOG.md`` through
    :func:`~dadaia_workspace.features.backlog.document.load_document` (SPEC v0.12.0 FR1/FR2,
    ADR #14 — T-120-08 cutover): an absent document yields an empty model, so a context with
    no backlog is a clean no-op (A2.8). Findings are returned in check order then item order;
    an empty list ⇒ a clean backlog.
    """
    registry = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=specs_dir,
        cli_anchors=cli_anchors,
    )
    document = load_document(specs_dir / "backlog")
    consumed = read_consumed(consumed_histo_store)
    histo_slugs: frozenset[str] = (
        frozenset(record.id for record in histo_store.iter_records())
        if histo_store is not None
        else frozenset()
    )

    ctx = DoctorContext(
        items=list(document.active),
        registry=registry,
        consumed=consumed,
        histo_slugs=histo_slugs,
        document_errors=document.errors,
    )
    for item in document.active:
        ctx.bound[item.slug] = bound_anchor_changes(item, registry)

    return run_checks(ctx)
