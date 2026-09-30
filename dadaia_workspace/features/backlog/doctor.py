"""The backlog's anchor rules in the doctor's `ledgers` section.

* **BL-SCHEMA** — a subject a live entry past ``idea`` binds resolves to a live anchor.
* **BL-CONFLICT** — two live entries change one anchor differently.

Entry validation (fields, status, ids, the exit ledger) is ``backlog.py check``'s alone:
the section runs that script beside these rules and holds no second vocabulary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from dadaia_workspace.core.doctor_rules import Rule, SectionFinding
from dadaia_workspace.core.models.backlog import INTENTS_EXEMPT_STATUS, Intent
from dadaia_workspace.features.backlog.subject_registry import BindStatus, Registry, build_registry

__all__ = ["RULES", "DoctorContext", "build_context"]


@dataclass(frozen=True)
class DoctorContext:
    """Each live entry past ``idea``: slug -> (anchor -> change, unresolved messages)."""

    bound: dict[str, tuple[dict[str, str], list[str]]]


def _finding(code: str, message: str, slug: str) -> SectionFinding:
    """One backlog-doctor finding, always an error."""
    return SectionFinding(code, "error", f"[{slug}] {message}", False, True)


def _check_schema(ctx: DoctorContext) -> list[SectionFinding]:
    return [
        _finding("BL-SCHEMA", message, slug)
        for slug, (_, unresolved) in ctx.bound.items()
        for message in unresolved
    ]


def _check_conflict(ctx: DoctorContext) -> list[SectionFinding]:
    items = [(slug, changes) for slug, (changes, unresolved) in ctx.bound.items() if not unresolved]
    findings: list[SectionFinding] = []
    for i, (slug, changes) in enumerate(items):
        for other, theirs in items[:i]:
            shared = sorted(changes.keys() & theirs.keys())
            if any(changes[a] != theirs[a] for a in shared):
                message = f"divergent conflict with backlog item {other!r} (shared anchors: {', '.join(shared)})"  # fmt: skip
                findings.append(_finding("BL-CONFLICT", message, slug))
    return findings


type LedgerRule = Rule[DoctorContext]

SECTION = "ledgers"

RULES: tuple[LedgerRule, ...] = (
    Rule(
        ("BL-SCHEMA",),
        SECTION,
        _check_schema,
        fix_help="Operator action: correct the entry this finding names in <specs>/backlog/BACKLOG.json, then commit.",
    ),
    Rule(
        ("BL-CONFLICT",),
        SECTION,
        _check_conflict,
        fix_help="Operator action: exit one of the twins this finding names from <specs>/backlog/BACKLOG.json, then commit.",
    ),
)


_SCHEMA = Path(__file__).resolve().parents[2] / "public" / "schemas" / "backlog" / "backlog-v1.schema.json"  # fmt: skip
_ITEM = Draft202012Validator({"$defs": json.loads(_SCHEMA.read_text(encoding="utf-8"))["$defs"], "$ref": "#/$defs/activeItem"})  # fmt: skip


def _live_intents(specs_dir: Path) -> dict[str, list[Intent]]:
    """Each live entry past ``idea`` the backlog-v1 schema accepts, and its intents; every
    other entry is `backlog.py check`'s finding and binds nothing here."""
    try:
        active = json.loads((specs_dir / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))["active"]  # fmt: skip
        return {
            e["id"]: [Intent.of(i) for i in e.get("intents", [])]
            for e in active
            if _ITEM.is_valid(e) and e["status"] != INTENTS_EXEMPT_STATUS
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def build_context(
    *,
    specs_dir: Path,
    source_root: Path,
    catalog_path: Path,
    alias_map_path: Path,
    cli_anchors: frozenset[str],
) -> DoctorContext:
    """Bind every live entry's intents against the registry, recomputed from live truth."""
    registry = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=specs_dir,
        cli_anchors=cli_anchors,
    )
    return DoctorContext(
        {slug: _bind(intents, registry) for slug, intents in _live_intents(specs_dir).items()}
    )


def _bind(intents: list[Intent], registry: Registry) -> tuple[dict[str, str], list[str]]:
    """``(anchor -> change, unresolved)``; a ``surface: new`` subject binds by its declared
    identity, and is an error when an anchor of that name already exists."""
    anchor_changes: dict[str, str] = {}
    unresolved: list[str] = []
    for intent in intents:
        subject = intent.subject
        result = registry.bind(subject.ref, subject.kind)
        anchor = result.anchor if result.status is BindStatus.RESOLVED else None
        if subject.surface == "new" and anchor is not None:
            unresolved.append(
                f"subject ref {subject.ref!r} (kind={subject.kind.value}) is declared "
                f"'surface: new' but already resolves to existing anchor {anchor.id!r}; "
                "bind it as existing (drop 'surface: new') or choose a new name."
            )
        elif subject.surface == "new":
            anchor_changes.setdefault(f"new:{subject.kind.value}:{subject.ref}", intent.change)
        elif anchor is not None:
            anchor_changes.setdefault(anchor.id, intent.change)
        else:
            unresolved.append(result.message or f"unresolved: {subject.ref}")
    return anchor_changes, unresolved
