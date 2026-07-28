"""Read-only resolve/preview surface (SPEC §3.4a).

Breaks the chicken-and-egg of the backfill (§3.5): the author cannot write bound ``intents[]``
without *seeing* how a proposed subject resolves against the registry first. This surface is
strictly read-only — it never writes a backlog file or the alias map.

* :func:`list_anchors` — the live auto-derived anchor set (optionally filtered by kind).
* :func:`resolve_one` — given a proposed subject, show its bound canonical anchor, or
  ``UNRESOLVED``/``AMBIGUOUS`` with the candidate set + an actionable alias-map suggestion.

It also hosts the shared **backlog-item loader** (:func:`load_backlog_items`,
:func:`bound_anchor_changes`) that both the preview surface and the doctor consume to read
``intents[]`` frontmatter from ``specs/backlog/*.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from dadaia_workspace.core.models.backlog import Intent, SubjectKind, parse_intents
from dadaia_workspace.features.backlog.subject_registry import (
    Anchor,
    BindStatus,
    Registry,
)

__all__ = [
    "BacklogItem",
    "PreviewResult",
    "bound_anchor_changes",
    "list_anchors",
    "load_backlog_items",
    "resolve_one",
]

#: Files under ``specs/backlog/`` that are NOT item files (no ``intents[]`` expected).
_NON_ITEM_STEMS = frozenset({"ideas", "candidates", "README"})

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class PreviewResult:
    """How one proposed subject resolves (read-only)."""

    ref: str
    status: BindStatus
    anchor_id: str | None = None
    message: str = ""
    candidates: tuple[str, ...] = ()
    alias_suggestion: str | None = None


def resolve_one(registry: Registry, ref: str, kind: SubjectKind) -> PreviewResult:
    """Resolve ``ref`` of ``kind`` through the registry; never mutates anything.

    On an UNRESOLVED/AMBIGUOUS result, attach an actionable alias-map suggestion line
    (``'<ref>' -> <canonical-anchor>``) the author can paste into the alias map.
    """
    result = registry.bind(ref, kind)
    if result.status is BindStatus.RESOLVED and result.anchor is not None:
        return PreviewResult(ref=ref, status=result.status, anchor_id=result.anchor.id)
    suggestion = f"{ref} -> <canonical-anchor-for-{kind.value}>"
    return PreviewResult(
        ref=ref,
        status=result.status,
        message=result.message,
        candidates=result.candidates,
        alias_suggestion=suggestion,
    )


def list_anchors(registry: Registry, kind: SubjectKind | None = None) -> list[Anchor]:
    """List the live anchor set, optionally filtered to one ``kind``. Read-only."""
    return registry.list_anchors(kind)


# ── shared backlog-item loader (consumed by preview + doctor) ────────────────────


@dataclass(frozen=True)
class BacklogItem:
    """A backlog item file reduced to its slug + parsed ``intents[]`` + status.

    ``intents_error`` is non-``None`` when the ``intents:`` frontmatter was structurally
    invalid (BL-SCHEMA fodder); ``intents`` is then empty.

    ``frontmatter_error`` (FR10, v0.1.65) is non-``None`` when the frontmatter block
    itself failed to parse as YAML (e.g. an unquoted ``source: text (note: more text)``
    value). The whole frontmatter is then unavailable — ``status`` is ``None`` and
    ``intents`` is empty — so downstream no-intents/unresolved diagnostics are noise;
    the doctor reports the parse error instead.
    """

    slug: str
    path: Path
    status: str | None
    intents: tuple[Intent, ...]
    intents_error: str | None = None
    frontmatter_error: str | None = None


def _format_yaml_error(exc: yaml.YAMLError, *, line_offset: int = 0) -> str:
    """Render a YAMLError as ``<msg> (line <L>, column <C>)`` when a mark is available.

    Prefers the short ``problem`` message over ``str(exc)`` (which embeds the mark in a
    multi-line snippet). Line/column are 1-based; ``line_offset`` shifts the mark's
    block-relative line to the FILE line the human will open (the frontmatter block
    starts after the opening ``---`` line).
    """
    problem = getattr(exc, "problem", None)
    message = str(problem) if problem else str(exc)
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        return f"{message} (line {mark.line + 1 + line_offset}, column {mark.column + 1})"
    return message


def _parse_frontmatter(content: str) -> tuple[dict[str, object] | None, str | None]:
    """Parse the frontmatter block; return ``(data, frontmatter_error)``.

    A YAML parse failure is CAPTURED, not swallowed (FR10): the second element carries
    the formatted YAMLError (message + problem-mark line/column when available) so the
    doctor can emit a loud parse-error finding instead of misdiagnosing the item as
    having no ``intents[]``.
    """
    match = _FRONTMATTER_RE.match(content)
    if match is None:
        # Bug r9-f26-author-accepts-unterminated-frontmatter: the regex needs BOTH
        # delimiters, so a block that opens and never closes used to be indistinguishable
        # from a file with no frontmatter — both returned (None, None). The item was then
        # promoted with status=None and the failure resurfaced far downstream as
        # "status missing", a diagnosis that names the wrong thing and never mentions the
        # truncation a live worker actually produced. A file that OPENS a block has
        # declared frontmatter; failing to close it is malformed, not absent.
        if content.startswith("---\n") or content.startswith("---\r\n"):
            return None, (
                "unterminated frontmatter block: the file opens with '---' but never "
                "closes it — add the closing '---' line"
            )
        return None, None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        # +1: the frontmatter block starts on file line 2 (after the opening ``---``).
        return None, _format_yaml_error(exc, line_offset=1)
    return (data if isinstance(data, dict) else None), None


def load_backlog_items(backlog_dir: Path) -> list[BacklogItem]:
    """Load every backlog *item* file under ``backlog_dir`` (``specs/backlog/``).

    Skips ``ideas.md``, ``candidates.md``, ``README.md``, and the epic file is NOT special-
    cased here (it is an item with its own residual ``intents[]``). Returns an empty list when
    the directory is absent. Each item's ``intents[]`` frontmatter is parsed; a structurally
    invalid ``intents:`` value is captured as ``intents_error`` rather than raised, so the
    doctor can report BL-SCHEMA instead of crashing.
    """
    items: list[BacklogItem] = []
    if not backlog_dir.is_dir():
        return items
    for md in sorted(backlog_dir.glob("*.md")):
        if md.stem in _NON_ITEM_STEMS:
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        parsed, frontmatter_error = _parse_frontmatter(content)
        fm = parsed or {}
        status_raw = fm.get("status")
        status = status_raw if isinstance(status_raw, str) else None
        intents: tuple[Intent, ...] = ()
        error: str | None = None
        if frontmatter_error is None:
            try:
                intents = tuple(parse_intents(fm.get("intents")))
            except ValueError as exc:
                error = str(exc)
        items.append(
            BacklogItem(
                slug=md.stem,
                path=md,
                status=status,
                intents=intents,
                intents_error=error,
                frontmatter_error=frontmatter_error,
            )
        )
    return items


def bound_anchor_changes(item: BacklogItem, registry: Registry) -> tuple[dict[str, str], list[str]]:
    """Bind each of ``item``'s intents to a canonical anchor.

    Returns ``(anchor_changes, unresolved)``: a map of anchor-id → change for every intent
    that resolved, plus the list of HALT messages for intents that did not (BL-SCHEMA fodder).
    When two intents bind to the same anchor with differing changes, the first wins for the
    map (the intra-item duplicate is an authoring error the doctor surfaces separately).
    A ``surface: new`` subject binds by declared identity (``new:<kind>:<ref>``) instead of
    registry resolution, so items introducing disjoint new surfaces classify UNRELATED.
    """
    anchor_changes: dict[str, str] = {}
    unresolved: list[str] = []
    for intent in item.intents:
        if intent.subject.surface == "new":
            # Bugs backlog-independent-cli-items-false-conflict-044 +
            # backlog-cli-intent-hallucinated-anchor-045: a declared NEW surface binds
            # by its own identity — never forced onto an existing anchor (false
            # conflicts) and never unresolved (dead-end blocks). Guard the dual error:
            # a "new" surface the registry already resolves is an authoring mistake.
            result = registry.bind(intent.subject.ref, intent.subject.kind)
            if result.status is BindStatus.RESOLVED and result.anchor is not None:
                unresolved.append(
                    f"subject ref {intent.subject.ref!r} (kind="
                    f"{intent.subject.kind.value}) is declared 'surface: new' but "
                    f"already resolves to existing anchor {result.anchor.id!r}; bind "
                    "it as existing (drop 'surface: new') or choose a new name."
                )
                continue
            declared = f"new:{intent.subject.kind.value}:{intent.subject.ref}"
            anchor_changes.setdefault(declared, intent.change)
            continue
        result = registry.bind(intent.subject.ref, intent.subject.kind)
        if result.status is BindStatus.RESOLVED and result.anchor is not None:
            anchor_changes.setdefault(result.anchor.id, intent.change)
        else:
            unresolved.append(result.message or f"unresolved: {intent.subject.ref}")
    return anchor_changes, unresolved
