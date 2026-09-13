"""Citation finders — dead `specs/` paths, dead `dadaia <verb>`s, dead skill pointers.

Relocated out of ``tests/contract/test_behavior_map.py`` (0.4.7 FR2): the same three
finders that keep every ``public/**`` asset honest now measure ``specs/memory/**``
through the doctor's ``MEM-DRIFT-2`` and the derived documents through FR3 — one
implementation, three consumers, no test-local copy.

Pure over text plus plain data: a command-path set (walked ONCE by
``cli.help_digest.command_paths``; ``features`` never imports ``cli``) and the file
roots a citation may resolve against. The tree wrappers are thin ``glob`` loops over
the text finders.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from pathlib import Path, PurePath

__all__ = [
    "CITABLE_PATH_PREFIXES",
    "dead_body_pointers",
    "dead_body_pointers_in_tree",
    "dead_citations",
    "dead_path_citations",
    "dead_path_citations_in_tree",
    "dead_verb_citations",
    "dead_verb_citations_in_tree",
    "memory_citation_violations",
    "posix_relpath",
]

_CITATION_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER_CHARS = frozenset("<>{}*|")
_ELLIPSIS_MARKERS = ("...", "…")
_WORKSPACE_RUNTIME_PREFIX = ".dadaia/"
#: The three path prefixes a citation is held to — everything else is prose.
CITABLE_PATH_PREFIXES = ("specs/", "dadaia_workspace/", ".github/")
_SIBLING_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:md|json|rules|txt)$")
_SIBLING_MARKER_RE = re.compile(r"^\(?\s*sibling\b")
_BLOCKQUOTE_PREFIX_RE = re.compile(r"^>\s*")

_DADAIA_VERB_RE = re.compile(
    r"(?<![\w./-])dadaia(?!\w)(?:\s+([a-z][a-z0-9-]*))?(?:\s+([a-z][a-z0-9-]*))?"
)

_DD_SKILL_TOKEN_RE = re.compile(r"^dd-[a-z0-9-]+$")
_DD_SECTION_PAIR_RE = re.compile(r"`(dd-[a-z0-9-]+)`[^`§\n]{0,40}§(\d+)")
_SCOPED_AGENTS_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*-AGENTS\.md$")


def posix_relpath(path: PurePath, root: PurePath) -> str:
    """Render *path* relative to *root* in POSIX form — separator-agnostic, so a
    violation's ``file:line`` citation is byte-identical on Windows and POSIX (bug
    ``citation-mutation-fixtures-never-turn-red-on-windows``). Pure path arithmetic
    (no I/O), so it takes any ``PurePath``."""
    return path.relative_to(root).as_posix()


def _is_placeholder_or_ellipsis(token: str) -> bool:
    if any(ch in _PLACEHOLDER_CHARS for ch in token):
        return True
    return any(marker in token for marker in _ELLIPSIS_MARKERS)


def _sibling_marked(same_line_remainder: str, next_line: str) -> bool:
    """True if a ``(sibling)``/``sibling`` annotation follows the citation, on the same
    line or on the very next one — a blockquote continuation, whose leading ``>`` marker
    is stripped first."""
    if _SIBLING_MARKER_RE.match(same_line_remainder.lstrip()):
        return True
    stripped_next = _BLOCKQUOTE_PREFIX_RE.sub("", next_line).lstrip()
    return bool(_SIBLING_MARKER_RE.match(stripped_next))


def dead_path_citations(
    text: str,
    *,
    rel: str,
    repo_root: Path,
    exempt: Collection[str] = (),
    sibling_dir: Path | None = None,
    sibling_roots: Collection[Path] = (),
) -> list[str]:
    """Failure mode (a) — every ``specs/``/``dadaia_workspace/``/``.github/``-prefixed
    or ``(sibling)``-annotated bare-filename citation in *text* must resolve on disk.

    *exempt* holds tokens proven to be projected INSTANCE realities absent from any
    checkout (bug ``citation-enforcer-resolves-projected-instance-paths-against-the-
    checkout``) — plain data, decided by the caller, never a second allowlist here.
    Sibling citations resolve next to the document (*sibling_dir*) or anywhere under
    *sibling_roots*; with neither supplied they are not checked.
    """
    violations: list[str] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        for m in _CITATION_BACKTICK_RE.finditer(line):
            token = m.group(1).strip()
            if not token or _is_placeholder_or_ellipsis(token):
                continue
            if token.startswith(_WORKSPACE_RUNTIME_PREFIX):
                continue
            if token.startswith(CITABLE_PATH_PREFIXES):
                if token in exempt:
                    continue
                if not (repo_root / token).exists():
                    violations.append(f"{rel}:{idx + 1}: dead path `{token}`")
                continue
            if sibling_dir is None and not sibling_roots:
                continue
            if "/" in token or not _SIBLING_FILENAME_RE.match(token):
                continue
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            if not _sibling_marked(line[m.end() :], next_line):
                continue
            if sibling_dir is not None and (sibling_dir / token).exists():
                continue
            if any(root.glob(f"**/{token}") for root in sibling_roots):
                continue
            violations.append(f"{rel}:{idx + 1}: dead sibling citation `{token}`")
    return violations


def dead_verb_citations(
    text: str, *, rel: str, command_paths: Collection[tuple[str, ...]]
) -> list[str]:
    """Failure mode (b) — every ``dadaia <verb> [<sub>]`` citation in *text* must resolve
    in *command_paths* (``cli.help_digest.command_paths()``, passed in as plain data)."""
    violations: list[str] = []
    for idx, line in enumerate(text.splitlines()):
        for m in _CITATION_BACKTICK_RE.finditer(line):
            token = m.group(1)
            for cm in _DADAIA_VERB_RE.finditer(token):
                v1, v2 = cm.group(1), cm.group(2)
                if v1 is None:
                    verb_path: tuple[str, ...] = ()
                elif v2 is None:
                    verb_path = (v1,)
                else:
                    verb_path = (v1, v2)
                if not verb_path or verb_path in command_paths:
                    continue
                violations.append(
                    f"{rel}:{idx + 1}: dead verb `dadaia {' '.join(verb_path)}` "
                    f"(cited as `{token.strip()}`)"
                )
    return violations


def dead_citations(
    text: str,
    *,
    command_paths: Collection[tuple[str, ...]],
    repo_root: Path,
    rel: str = "",
    exempt: Collection[str] = (),
) -> list[str]:
    """Both citation failure modes over one document — the entry the doctor's
    ``MEM-DRIFT-2`` and the derived-docs contract test share."""
    return dead_path_citations(text, rel=rel, repo_root=repo_root, exempt=exempt) + (
        dead_verb_citations(text, rel=rel, command_paths=command_paths)
    )


def _numbered_headings(skill_md: Path) -> set[str]:
    """The `N` of every `## N.`/`## Na.` heading of *skill_md* — `## 3a.` answers §3."""
    return {
        m.group(1)
        for m in re.finditer(r"^## (\d+)[a-z]?\.", skill_md.read_text(encoding="utf-8"), re.M)
    }


def dead_body_pointers(text: str, *, rel: str, public_dir: Path) -> list[str]:
    """Every backticked ``dd-<name>`` token names a skill directory under *public_dir*;
    every `` `dd-x` §N `` pair names a ``## N.`` section of that skill's ``SKILL.md``;
    every backticked ``*-AGENTS.md`` filename resolves to an asset under *public_dir*.
    Returns ``file:line: …`` strings naming what to re-read."""
    skills = {d.name for d in (public_dir / "skills").iterdir() if d.is_dir()}
    violations: list[str] = []
    for idx, line in enumerate(text.splitlines()):
        for m in _CITATION_BACKTICK_RE.finditer(line):
            token = m.group(1).strip()
            if _DD_SKILL_TOKEN_RE.match(token) and token not in skills:
                violations.append(f"{rel}:{idx + 1}: dead skill pointer `{token}`")
            elif _SCOPED_AGENTS_TOKEN_RE.match(token) and not any(public_dir.glob(f"**/{token}")):
                violations.append(f"{rel}:{idx + 1}: dead scoped-rule pointer `{token}`")
        for m in _DD_SECTION_PAIR_RE.finditer(line):
            skill, number = m.group(1), m.group(2)
            target = public_dir / "skills" / skill / "SKILL.md"
            if not target.exists() or number not in _numbered_headings(target):
                violations.append(
                    f"{rel}:{idx + 1}: dead section pointer `{skill}` §{number} "
                    f"— re-read {skill}/SKILL.md's numbered headings"
                )
    return violations


def memory_citation_violations(
    memory_dir: Path,
    *,
    repo_root: Path | None,
    command_paths: Collection[tuple[str, ...]] | None,
) -> list[tuple[Path, str]]:
    """`dead_citations` over every ``*.md`` under *memory_dir* — the doctor's
    MEM-DRIFT-2 input, as ``(atom, violation)`` pairs.

    Silent (``[]``) with no command tree, no *repo_root* or no memory tree: a consumer
    whose CLI tree could not be resolved is not a consumer with drift, exactly as
    ``live_shas=None`` keeps SPEC-DOC-044 silent.
    """
    if repo_root is None or command_paths is None or not memory_dir.is_dir():
        return []
    return [
        (path, violation)
        for path in _markdown_files(memory_dir)
        for violation in dead_citations(
            path.read_text(encoding="utf-8"),
            command_paths=command_paths,
            repo_root=repo_root,
            rel=posix_relpath(path, repo_root),
        )
    ]


def _markdown_files(root: Path) -> list[Path]:
    return sorted(root.glob("**/*.md"))


def dead_path_citations_in_tree(
    public_dir: Path, repo_root: Path, *, exempt: Collection[str] = ()
) -> list[str]:
    """`dead_path_citations` over every ``*.md`` under *public_dir*."""
    violations: list[str] = []
    for md_path in _markdown_files(public_dir):
        violations += dead_path_citations(
            md_path.read_text(encoding="utf-8"),
            rel=posix_relpath(md_path, repo_root),
            repo_root=repo_root,
            exempt=exempt,
            sibling_dir=md_path.parent,
            sibling_roots=(public_dir,),
        )
    return violations


def dead_verb_citations_in_tree(
    public_dir: Path, repo_root: Path, command_paths: Collection[tuple[str, ...]]
) -> list[str]:
    """`dead_verb_citations` over every ``*.md`` under *public_dir*."""
    violations: list[str] = []
    for md_path in _markdown_files(public_dir):
        violations += dead_verb_citations(
            md_path.read_text(encoding="utf-8"),
            rel=posix_relpath(md_path, repo_root),
            command_paths=command_paths,
        )
    return violations


def dead_body_pointers_in_tree(
    roots: Iterable[Path], public_dir: Path, repo_root: Path
) -> list[str]:
    """`dead_body_pointers` over every ``*.md`` under each of *roots*."""
    violations: list[str] = []
    for root in roots:
        for md_path in _markdown_files(root):
            violations += dead_body_pointers(
                md_path.read_text(encoding="utf-8"),
                rel=posix_relpath(md_path, repo_root),
                public_dir=public_dir,
            )
    return violations
