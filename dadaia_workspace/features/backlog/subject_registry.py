"""Canonical-subject registry — the linchpin (SPEC §3.2, ADR-A).

**Auto-derived, recomputed from live truth on every ``build_registry`` call.** It is derived,
never a stored file that can itself go stale (the meta-version of the bug we are fixing).

Four anchor kinds, each backed by a real registry of truth in the live tree:

1. ``code`` — a tracked repo path, any language, ``#word`` optional: the word must occur in
   that file (a word grep, no parser);
2. ``catalog`` — ``catalog.json`` slugs (and product-atom ids);
3. ``doc`` — spec-doc ids (``SPEC-DOC-NNN``) + memory heading anchors (``file.md#heading``);
4. ``invariant`` — named invariants (``INV-*``).

**Binding contract:** the model *proposes* a subject string; Python *normalizes + binds* it to
a single registry anchor, and **HALTs (rejects, not silent NEW)** any subject that resolves to
no known anchor or to an ambiguous set. The HALT message names the unresolved ref so it is
actionable (acceptance §3.7.1).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.models.backlog import SubjectKind

__all__ = [
    "Anchor",
    "BindResult",
    "BindStatus",
    "Registry",
    "build_registry",
]


class BindStatus(StrEnum):
    """Outcome of resolving a proposed subject ref to a canonical anchor."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Anchor:
    """One canonical subject anchor derived from live truth.

    ``id`` is the canonical, stable identity used for set-intersection in the classifier.
    """

    kind: SubjectKind
    id: str


@dataclass(frozen=True)
class BindResult:
    """The result of :meth:`Registry.bind`.

    ``status is RESOLVED`` ⇒ ``anchor`` is set. ``UNRESOLVED``/``AMBIGUOUS`` ⇒ ``anchor`` is
    ``None`` and ``message`` carries an actionable explanation naming the ref;
    ``candidates`` lists the ambiguous anchor ids when applicable.
    """

    status: BindStatus
    anchor: Anchor | None = None
    message: str = ""
    candidates: tuple[str, ...] = ()


# ── catalog anchors ──────────────────────────────────────────────────────────────


def _derive_catalog_anchors(catalog_path: Path) -> set[str]:
    """Derive feature slugs (and product-atom ids) from ``catalog.json``."""
    anchors: set[str] = set()
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return anchors
    if not isinstance(data, dict):
        return anchors
    features = data.get("features")
    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, dict):
                slug = feature.get("slug")
                if isinstance(slug, str) and slug:
                    anchors.add(slug)
    return anchors


# ── doc anchors (SPEC-DOC ids + memory heading anchors) ─────────────────────────

_SPECDOC_RE = re.compile(r"\bSPEC-DOC-\d+[A-Za-z]?\b")
_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<text>.+?)\s*$", re.MULTILINE)
_INVARIANT_RE = re.compile(r"\bINV-[A-Za-z0-9][A-Za-z0-9-]*\b")


def _slug_heading(text: str) -> str:
    """Normalize a heading to its anchor slug (best-effort GitHub-style)."""
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def _derive_doc_anchors(specs_dir: Path) -> set[str]:
    """Derive ``SPEC-DOC-NNN`` ids + ``memory/<file>.md#<heading-slug>`` anchors."""
    anchors: set[str] = set()
    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        return anchors
    for md in sorted(memory_dir.rglob("*.md")):
        try:
            content = md.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        for match in _SPECDOC_RE.finditer(content):
            anchors.add(match.group(0))
        rel = md.relative_to(specs_dir).as_posix()
        for heading in _HEADING_RE.finditer(content):
            text = heading.group("text")
            # Preserve a raw INV-/SPEC-DOC- heading verbatim as an anchor suffix; also add
            # the slugged form so both "memory/architecture.md#INV-x" and the slug resolve.
            anchors.add(f"{rel}#{text.strip()}")
            anchors.add(f"{rel}#{_slug_heading(text)}")
    return anchors


def _derive_invariant_anchors(specs_dir: Path) -> set[str]:
    """Derive named ``INV-*`` invariants from the memory docs ONLY.

    ``specs/memory/**`` Markdown is the sole invariant declaration surface
    (v0.1.49 FR2). Source code and tests are never scanned: docstring examples
    and test-fixture ids must not mint live anchors, or the fail-closed
    classifier can be satisfied by junk.
    """
    anchors: set[str] = set()
    root = specs_dir / "memory"
    if not root.is_dir():
        return anchors
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        for match in _INVARIANT_RE.finditer(content):
            anchors.add(match.group(0))
    return anchors


# ── the Registry ─────────────────────────────────────────────────────────────────


class Registry:
    """An immutable snapshot of the canonical-subject anchor set over one repo.

    Built by :func:`build_registry`; every call recomputes from live truth (SPEC §3.2). The
    classifier and doctor consume :meth:`bind` and :meth:`list_anchors`.
    """

    def __init__(self, anchors: dict[SubjectKind, set[str]], repo: Path) -> None:
        self._anchors = anchors
        self._repo = repo

    def _resolve_in_kind(self, raw_ref: str, kind: SubjectKind) -> BindResult:
        """Resolve ``raw_ref`` as a direct anchor of ``kind``.

        A ref that is not an exact anchor id still binds when it suffix-matches
        EXACTLY ONE known anchor of the kind on a path boundary (e.g. a worker
        writing ``snake.py`` for the canonical ``src/snake.py`` — the
        common weak-model slip of dropping the leading directories). Zero matches
        stay UNRESOLVED; more than one is AMBIGUOUS with the candidates named —
        the unique-suffix rule can never bind the wrong anchor silently.
        """
        ids = self._anchors.get(kind, set())
        if raw_ref in ids:
            return BindResult(status=BindStatus.RESOLVED, anchor=Anchor(kind=kind, id=raw_ref))
        suffix_matches = sorted(anchor_id for anchor_id in ids if anchor_id.endswith("/" + raw_ref))
        if len(suffix_matches) == 1:
            return BindResult(
                status=BindStatus.RESOLVED, anchor=Anchor(kind=kind, id=suffix_matches[0])
            )
        if len(suffix_matches) > 1:
            return BindResult(
                status=BindStatus.AMBIGUOUS,
                message=(
                    f"subject ref {raw_ref!r} (kind={kind.value}) suffix-matches multiple "
                    f"anchors; qualify the path."
                ),
                candidates=tuple(suffix_matches),
            )
        return BindResult(
            status=BindStatus.UNRESOLVED,
            message=(
                f"subject ref {raw_ref!r} (kind={kind.value}) resolves to no known anchor; "
                "correct the ref."
            ),
        )

    def bind(self, raw_ref: str, kind: SubjectKind) -> BindResult:
        """Bind ``raw_ref`` of ``kind`` to a canonical anchor, or HALT (``UNRESOLVED``,
        the message naming the ref). A ``code`` ref is ``path[#word]``: the path binds
        against the tracked paths, then the word must occur in that file."""
        ref = raw_ref.strip()
        if kind is not SubjectKind.CODE or not ref:
            return self._resolve_in_kind(ref, kind)
        path, _, word = ref.partition("#")
        result = self._resolve_in_kind(path, kind)
        if result.anchor is None or not word:
            return result
        try:
            text = (self._repo / result.anchor.id).read_text(encoding="utf-8")
        except (OSError, ValueError):
            text = ""
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) is None:
            return BindResult(
                status=BindStatus.UNRESOLVED,
                message=f"subject ref {ref!r} (kind=code): {word!r} does not occur in {result.anchor.id}; correct the ref.",
            )
        return BindResult(BindStatus.RESOLVED, Anchor(kind, f"{result.anchor.id}#{word}"))


def build_registry(*, specs_dir: Path, tracked: frozenset[str]) -> Registry:
    """Build the canonical-subject registry from live truth (SPEC §3.2): ``tracked`` is
    the repo's tracked paths (``specs_dir.parent``-relative), handed in by the caller."""
    anchors: dict[SubjectKind, set[str]] = {
        SubjectKind.CODE: set(tracked),
        SubjectKind.CATALOG: _derive_catalog_anchors(
            specs_dir / "memory" / "product" / "catalog.json"
        ),
        SubjectKind.DOC: _derive_doc_anchors(specs_dir),
        SubjectKind.INVARIANT: _derive_invariant_anchors(specs_dir),
    }
    return Registry(anchors, specs_dir.parent)
