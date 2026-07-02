"""Canonical-subject registry — the linchpin (SPEC §3.2, ADR-A).

**Auto-derived, recomputed from live truth on every ``build_registry`` call.** It is derived,
never a stored file that can itself go stale (the meta-version of the bug we are fixing).

R1 auto-derives exactly **five** anchor kinds, each backed by a real registry of truth in the
live tree:

1. ``code`` — module-relative ``path#symbol``, validated via ``ast`` (grep fallback) of the
   injected source root;
2. ``cli`` — Typer command ids (the ``dadaia <group> <verb>`` surface walked from the app tree);
3. ``catalog`` — ``catalog.json`` slugs (and product-atom ids);
4. ``doc`` — spec-doc ids (``SPEC-DOC-NNN``) + memory heading anchors (``file.md#heading``);
5. ``invariant`` — named invariants (``INV-*``).

``panel``/``api`` ids are NOT auto-derivable in R1 (no route registry exists) — they bind via
the **operator alias map only**. The alias map path is injected, never a cwd lookup
(SPEC §3.8 #6).

**Binding contract:** the model *proposes* a subject string; Python *normalizes + binds* it to
a single registry anchor, and **HALTs (rejects, not silent NEW)** any subject that resolves to
no known anchor or to an ambiguous set. The HALT message names the unresolved ref so it is
actionable (acceptance §3.7.1).
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from dadaia_workspace.core.models.backlog import SubjectKind

if TYPE_CHECKING:
    import typer

__all__ = [
    "Anchor",
    "BindResult",
    "BindStatus",
    "Registry",
    "build_registry",
    "load_alias_map",
]


class BindStatus(StrEnum):
    """Outcome of resolving a proposed subject ref to a canonical anchor."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Anchor:
    """One canonical subject anchor derived from live truth (or an alias target).

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


# ── alias map ────────────────────────────────────────────────────────────────────

_ALIAS_RE = re.compile(r"^(?P<synonym>.+?)\s*->\s*(?P<anchor>.+?)\s*$")


def load_alias_map(alias_map_path: Path) -> dict[str, str]:
    """Read ``synonym -> canonical-anchor`` lines from the injected alias-map path.

    Blank lines and ``#`` comments are skipped. Tolerates an absent file (returns ``{}``) —
    the alias map is optional. Synonyms are matched case-insensitively (normalized to lower).
    """
    aliases: dict[str, str] = {}
    try:
        text = alias_map_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return aliases
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ALIAS_RE.match(line)
        if match is None:
            continue
        synonym = match.group("synonym").strip().lower()
        anchor = match.group("anchor").strip()
        if synonym and anchor:
            aliases[synonym] = anchor
    return aliases


# ── code anchors (AST + grep fallback) ──────────────────────────────────────────

_PY_SYMBOL_RE = re.compile(r"^\s*(?:class|def|async\s+def)\s+(?P<name>[A-Za-z_]\w*)")
_PY_ASSIGN_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)\s*(?::[^=]+)?=")


def _module_top_level_symbols(source: str) -> set[str]:
    """Top-level symbol names in ``source`` via ``ast`` (grep fallback on SyntaxError)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _grep_top_level_symbols(source)
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _grep_top_level_symbols(source: str) -> set[str]:
    """Line-oriented fallback when a file does not parse (SPEC §6 grep fallback)."""
    names: set[str] = set()
    for line in source.splitlines():
        sym = _PY_SYMBOL_RE.match(line)
        if sym:
            names.add(sym.group("name"))
            continue
        if line and not line[0].isspace():
            assign = _PY_ASSIGN_RE.match(line)
            if assign:
                names.add(assign.group("name"))
    return names


def _derive_code_anchors(source_root: Path) -> set[str]:
    """Derive ``path#symbol`` anchor ids for every top-level symbol under ``source_root``."""
    anchors: set[str] = set()
    if not source_root.is_dir():
        return anchors
    for py in sorted(source_root.rglob("*.py")):
        try:
            source = py.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        rel = py.relative_to(source_root).as_posix()
        for symbol in _module_top_level_symbols(source):
            anchors.add(f"{rel}#{symbol}")
    return anchors


# ── cli anchors (Typer app tree walk) ───────────────────────────────────────────


def _derive_cli_anchors(app: typer.Typer | None) -> set[str]:
    """Walk the Typer app tree for ``<group> <verb>`` (and nested) command ids.

    A registered command's id is the space-joined path of group names + the command name,
    e.g. ``backlog doctor``. Top-level commands (no group) are their own bare name.
    """
    anchors: set[str] = set()
    if app is None:
        return anchors
    _walk_typer(app, (), anchors, depth=0)
    return anchors


def _walk_typer(app: typer.Typer, prefix: tuple[str, ...], out: set[str], *, depth: int) -> None:
    if depth > 16:  # defensive recursion guard
        return
    for info in app.registered_commands:
        name = info.name or (info.callback.__name__ if info.callback else None)
        if name:
            out.add(" ".join((*prefix, name)))
    for group in app.registered_groups:
        sub = group.typer_instance
        if sub is None or group.name is None:
            continue
        _walk_typer(sub, (*prefix, group.name), out, depth=depth + 1)


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
    """An immutable snapshot of the canonical-subject anchor set + the alias map.

    Built by :func:`build_registry`; every call recomputes from live truth (SPEC §3.2). The
    classifier and doctor consume :meth:`bind` and :meth:`list_anchors`.
    """

    def __init__(self, anchors: dict[SubjectKind, set[str]], aliases: dict[str, str]) -> None:
        self._anchors = anchors
        self._aliases = aliases
        # Reverse index: anchor-id -> kinds it belongs to (for alias-target classification).
        self._by_id: dict[str, set[SubjectKind]] = {}
        for kind, ids in anchors.items():
            for anchor_id in ids:
                self._by_id.setdefault(anchor_id, set()).add(kind)

    def list_anchors(self, kind: SubjectKind | None = None) -> list[Anchor]:
        """All anchors, optionally filtered to one ``kind``. Stable sort by id."""
        out: list[Anchor] = []
        for anchor_kind, ids in self._anchors.items():
            if kind is not None and anchor_kind is not kind:
                continue
            out.extend(Anchor(kind=anchor_kind, id=anchor_id) for anchor_id in ids)
        return sorted(out, key=lambda a: (a.kind.value, a.id))

    def _resolve_in_kind(self, raw_ref: str, kind: SubjectKind) -> BindResult:
        """Resolve ``raw_ref`` as a direct (non-alias) anchor of ``kind``."""
        ids = self._anchors.get(kind, set())
        if raw_ref in ids:
            return BindResult(status=BindStatus.RESOLVED, anchor=Anchor(kind=kind, id=raw_ref))
        return BindResult(
            status=BindStatus.UNRESOLVED,
            message=(
                f"subject ref {raw_ref!r} (kind={kind.value}) resolves to no known anchor; "
                f"add it as an alias in the operator alias map, or correct the ref."
            ),
        )

    def bind(self, raw_ref: str, kind: SubjectKind) -> BindResult:
        """Normalize + bind ``raw_ref`` of ``kind`` to a canonical anchor, or HALT.

        Resolution order:

        1. **alias map** — a ``synonym -> canonical-anchor`` entry collapses the proposed ref
           to its canonical anchor (case-insensitive). This is the **sole** binding path for
           ``panel``/``api`` in R1.
        2. **direct anchor** — the ref is itself a derived anchor of ``kind`` (auto-derived
           kinds only: code/cli/catalog/doc/invariant).

        Returns ``UNRESOLVED`` (HALT) when nothing matches; the message names the ref.
        """
        ref = raw_ref.strip()
        if not ref:
            return BindResult(
                status=BindStatus.UNRESOLVED, message="empty subject ref cannot be bound"
            )

        # (1) alias map — collapse a known synonym to its canonical anchor.
        alias_target = self._aliases.get(ref.lower())
        if alias_target is not None:
            target_kinds = self._by_id.get(alias_target)
            # An alias to an auto-derived anchor: classify it under that anchor's real kind.
            if target_kinds:
                resolved_kind = kind if kind in target_kinds else next(iter(sorted(target_kinds)))
                return BindResult(
                    status=BindStatus.RESOLVED,
                    anchor=Anchor(kind=resolved_kind, id=alias_target),
                )
            # An alias to an opaque target (e.g. a panel/api id with no auto-derivation):
            # bind to the requested kind. This is the R1 panel/api path.
            return BindResult(status=BindStatus.RESOLVED, anchor=Anchor(kind=kind, id=alias_target))

        # (2) panel/api are alias-ONLY in R1 — no direct/auto resolution.
        if kind in {SubjectKind.PANEL, SubjectKind.API}:
            return BindResult(
                status=BindStatus.UNRESOLVED,
                message=(
                    f"subject ref {ref!r} (kind={kind.value}) has no alias-map entry; "
                    f"panel/api subjects bind via the operator alias map only in R1 "
                    f"(no auto-derivation). Add a 'synonym -> canonical-anchor' alias."
                ),
            )

        # (2') direct auto-derived anchor.
        return self._resolve_in_kind(ref, kind)


def build_registry(
    *,
    source_root: Path,
    catalog_path: Path,
    alias_map_path: Path,
    specs_dir: Path,
    cli_app: typer.Typer | None = None,
) -> Registry:
    """Build the canonical-subject registry from live truth (SPEC §3.2).

    All roots are **injected** — never ``os.getcwd()`` (SPEC §3.8 #6). ``cli_app`` defaults to
    the live ``dadaia`` Typer app; tests pass a small fixture app. Every call recomputes the
    anchor set, so a symbol added/removed in source changes resolution with no stored file
    (acceptance §3.7.5).
    """
    if cli_app is None:
        from dadaia_workspace.cli.main import app as cli_app  # local import: avoid cycle

    anchors: dict[SubjectKind, set[str]] = {
        SubjectKind.CODE: _derive_code_anchors(source_root),
        SubjectKind.CLI: _derive_cli_anchors(cli_app),
        SubjectKind.CATALOG: _derive_catalog_anchors(catalog_path),
        SubjectKind.DOC: _derive_doc_anchors(specs_dir),
        SubjectKind.INVARIANT: _derive_invariant_anchors(specs_dir),
    }
    aliases = load_alias_map(alias_map_path)
    return Registry(anchors=anchors, aliases=aliases)
