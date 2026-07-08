"""``backlog doctor`` — the ENFORCED backstop (SPEC §3.4, ADR-D).

Four checks, run by **one parameterized check engine** (SPEC §3.8 #8 — no copy-paste
fan-out): each check is a ``BacklogCheck`` (a code + a callable over the shared
:class:`DoctorContext`), and the engine maps the same loop over all of them.

* **BL-SCHEMA** — every item has bound ``intents[]`` (every subject resolves in the registry)
  + a valid status; a structurally invalid ``intents:`` frontmatter is also BL-SCHEMA.
* **BL-DUP** — two items share anchor-set + change → ERROR (via the classifier ``DUPLICATE``).
* **BL-CONFLICT** — two items share an anchor with incompatible change → ERROR (the divergent
  twin, caught even when hand-written; classifier ``DIVERGENT_CONFLICT``).
* **BL-STALE** — a slug listed in any archived release's ``consumed_backlog`` ledger
  (mechanical exact-membership, not NLP) that still exists in ``specs/backlog/`` → ERROR.

Pure module: all roots are **injected** (SPEC §3.8 #6); no I/O outside the supplied paths and
no subprocess. The CLI (``cli/commands/newartifacts.py``) and the pre-commit/CI chokepoint
(``cli/commands/ci.py`` + ``public/scripts/``) are thin wirings over :func:`run_backlog_doctor`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.features.backlog.classifier import BoundItem, Verdict, classify
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

#: Backlog statuses that are terminal — a stale check only flags non-terminal survivors.
_TERMINAL_STATUSES = frozenset({"delivered", "rejected", "done", "closed"})

#: The one status EXEMPT from the resolvable-typed-intents requirement (v0.1.55 FR5, bug
#: ``backlog-new-stub-readme-lag-intents-schema``). An ``idea`` is an unbound brainstorm: it
#: carries no bound ``intents[]`` yet, so the "no intents[] declared" and unresolved-subject
#: BL-SCHEMA errors are held until the item matures to ``candidate`` and beyond. This is a
#: STATUS gate, NOT a blanket exemption — a malformed ``intents:`` frontmatter and an invalid
#: status still fire at ANY status.
_INTENTS_EXEMPT_STATUS = "idea"

#: Statuses accepted as valid in BL-SCHEMA (kept permissive; the backlog status vocabulary is
#: informal — see ``release-governance``). ``None``/empty is the only invalid case here.
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


@dataclass
class DoctorContext:
    """Everything the check engine needs, computed once and shared across all checks."""

    items: list[BacklogItem]
    registry: Registry
    consumed: dict[str, set[str]]
    #: slug -> (anchor_changes, unresolved-messages), bound once.
    bound: dict[str, tuple[dict[str, str], list[str]]] = field(default_factory=dict)

    def bound_item(self, slug: str) -> BoundItem:
        anchor_changes, _ = self.bound[slug]
        return BoundItem(slug=slug, anchor_changes=anchor_changes)


# ── the four checks (each a pure function over the shared context) ───────────────


def _is_intents_exempt(status: str | None) -> bool:
    """True iff ``status`` is the intents-exempt ``idea`` stage (v0.1.55 FR5).

    An ``idea`` is an unbound brainstorm — exempt from the resolvable-typed-intents
    requirement. Every other status (candidate and beyond, or a missing status) must carry
    bound, resolvable intents.
    """
    return status is not None and status.strip().lower() == _INTENTS_EXEMPT_STATUS


def _check_schema(ctx: DoctorContext) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.items:
        # FR10 (v0.1.65): a frontmatter that failed to parse as YAML is its own loud
        # BL-SCHEMA ERROR, and every downstream diagnostic (no-intents, unresolved
        # subjects, status) is suppressed for that item — they are all artifacts of
        # the parse failure, not independent findings.
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
        # A malformed ``intents:`` frontmatter is always BL-SCHEMA, at ANY status.
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
        exempt = _is_intents_exempt(item.status)
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


def _check_dup(ctx: DoctorContext) -> list[Finding]:
    return _pairwise(ctx, Verdict.DUPLICATE, BacklogDoctorCode.BL_DUP, "duplicate")


def _check_conflict(ctx: DoctorContext) -> list[Finding]:
    return _pairwise(
        ctx, Verdict.DIVERGENT_CONFLICT, BacklogDoctorCode.BL_CONFLICT, "divergent conflict"
    )


def _check_stale(ctx: DoctorContext) -> list[Finding]:
    findings: list[Finding] = []
    if not ctx.consumed:  # no archived ledger → no-op (acceptance §3.7.6).
        return findings
    for item in ctx.items:
        if item.slug in ctx.consumed and (
            item.status is None or item.status.lower() not in _TERMINAL_STATUSES
        ):
            findings.append(
                Finding(
                    BacklogDoctorCode.BL_STALE,
                    Severity.ERROR,
                    "slug is recorded as consumed in an archived release's consumed_backlog "
                    "ledger but still exists in specs/backlog/ (stale — should be removed in R2)",
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
    read is a no-op when absent. The four checks are driven by one parameterized engine
    (``_CHECKS``) — the engine maps the same loop over each check, never copy-pasting bodies.
    Findings are returned in check order then file order; an empty list ⇒ a clean backlog.
    """
    registry = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=specs_dir,
        cli_anchors=cli_anchors,
    )
    items = load_backlog_items(specs_dir / "backlog")
    consumed = read_consumed(archive_root)

    ctx = DoctorContext(items=items, registry=registry, consumed=consumed)
    for item in items:
        ctx.bound[item.slug] = bound_anchor_changes(item, registry)

    findings: list[Finding] = []
    for check in _CHECKS:
        findings.extend(check.run(ctx))
    return findings
