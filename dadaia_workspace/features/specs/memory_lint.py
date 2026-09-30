"""The memory-atom lint (LINT-1): frontmatter schema, ``sources`` globs, history narrative,
forbidden and duplicate headings, wikilink resolution."""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from dadaia_workspace.features.specs import memory_canon
from dadaia_workspace.features.specs.schemas import load_schema

__all__ = [
    "AtomResult",
    "glob_matches_a_file",
    "lint_atom",
    "lint_directory",
    "load_frontmatter_schema",
    "main",
]


def load_frontmatter_schema() -> dict[str, Any]:
    return load_schema("memory/memory-frontmatter-v1")


_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = memory_canon.WIKILINK_RE
_WILDCARD_RE = re.compile(r"[*?\[]")


def glob_matches_a_file(root: Path, pattern: str) -> bool:
    """True when *pattern* (``fnmatch`` over repo-relative POSIX paths, ``*`` crossing ``/``
    — the ``memory.py drift`` matcher) matches a file under *root*. The walk is anchored at
    the literal prefix, which fnmatch requires anyway: exact, not an approximation."""
    wildcard = _WILDCARD_RE.search(pattern)
    if wildcard is None:
        return (root / pattern).is_file()
    base = root / PurePosixPath(pattern[: wildcard.start()]).parent
    if not base.is_dir():
        return False
    return any(
        path.is_file() and fnmatch.fnmatch(path.relative_to(root).as_posix(), pattern)
        for path in base.rglob("*")
    )


def _check_sources(result: AtomResult, fm: dict[str, Any], repo_root: Path) -> None:
    """A product atom declares the code it describes, and every glob names real code."""
    sources = fm.get("sources")
    if not isinstance(sources, list) or not sources:
        result.error(
            "Missing 'sources': every product atom names the repo-relative path globs of "
            "the code it describes (memory-frontmatter-v1; the closure drift worklist "
            "joins a commit window to its atoms through this field)."
        )
        return
    for source in sources:
        if not isinstance(source, str):
            continue
        if source.startswith("/") or ".." in PurePosixPath(source).parts:
            result.error(f"'sources' glob '{source}' escapes the repo root.")
        elif not glob_matches_a_file(repo_root, source):
            result.error(f"'sources' glob '{source}' matches no file under {repo_root}.")


_NARRATIVE_TOKENS = (
    ("date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("release id", re.compile(r"(?<![\d.=])\d+\.\d+\.\d+(?!\.?\d)")),
    ("candidate id", re.compile(r"\b(?:c|rc-)\d+\b")),
    ("task id", re.compile(r"\bT-\d+-\d+\b")),
    ("FR id", re.compile(r"\bFR\d+\b")),
)
_HISTORY_PHRASE_RE = re.compile(
    r"\b(?:operator (?:doctrine|decision|ruling)|closed as|died|was deleted|retired"
    r"|no longer|formerly|previously)\b",
    re.IGNORECASE,
)
_ADR_LINE_RE = re.compile(r"^\s*ADR:\s*\d{4}\b")
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")


def _check_narrative(result: AtomResult, content: str, body: str, product: bool) -> None:
    """One ERROR per body line carrying a history token (any memory file) or a history
    phrase (product atoms only); fenced code and a principle's ``ADR:`` line are exempt."""
    offset = len(content.splitlines()) - len(body.splitlines())
    fenced = False
    for number, line in enumerate(body.splitlines(), start=offset + 1):
        if _FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced or _ADR_LINE_RE.match(line):
            continue
        hits = [(kind, m.group(0)) for kind, rx in _NARRATIVE_TOKENS for m in rx.finditer(line)]
        if product:
            hits += [("phrase", m.group(0)) for m in _HISTORY_PHRASE_RE.finditer(line)]
        if hits:
            named = ", ".join(f"{kind} '{text}'" for kind, text in hits)
            result.error(
                f"MEM-NARRATIVE-1 line {number}: history in memory ({named}) — state what "
                "the product does, never when it started."
            )


class AtomResult:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def _is_product_atom(md_path: Path, memory_dir: Path) -> bool:
    """True for ``product/<area>/<slug>.md`` — the atoms that describe code."""
    try:
        parts = md_path.resolve().relative_to(memory_dir.resolve()).parts
    except ValueError:
        return False
    return len(parts) == 3 and parts[0] == "product"


def lint_atom(md_path: Path, memory_dir: Path, schema: dict[str, Any]) -> AtomResult:
    result = AtomResult(md_path)
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error(f"Cannot read file: {exc}")
        return result

    fm, body, problem = memory_canon.parse_atom(content)
    if fm is None:
        result.error(f"Frontmatter is outside the atom grammar: {problem}")
        return result
    # Every schema error in one pass: validate() stops at the first.
    for schema_error in sorted(Draft202012Validator(schema).iter_errors(fm), key=str):
        result.error(f"Frontmatter schema violation: {schema_error.message}")

    product = _is_product_atom(md_path, memory_dir)
    if product:
        _check_sources(result, fm, memory_dir.parent.parent)
    _check_narrative(result, content, body, product)

    slug = fm.get("slug")
    if isinstance(slug, str) and slug != md_path.stem:
        result.error(
            f"'slug' frontmatter value '{slug}' does not match filename stem '{md_path.stem}'."
        )
    seen: set[str] = set()
    for heading in (m.group(1).strip() for m in _H2_RE.finditer(body)):
        if memory_canon.is_forbidden_memory_heading(heading):
            result.error(
                f"Forbidden heading '## {heading}' — changelog/history sections "
                "violate the atomicity contract (specs/memory/AGENTS.md §3)."
            )
            continue
        if heading in seen:
            result.error(f"Duplicate '## {heading}' heading found.")
        else:
            seen.add(heading)

    for wikilink_slug in _WIKILINK_RE.findall(body):
        if not any(memory_dir.rglob(f"{wikilink_slug}.md")):
            result.error(
                f"Wikilink [[{wikilink_slug}]] does not resolve to any .md file under {memory_dir}."
            )

    return result


def lint_directory(memory_dir: Path, schema: dict[str, Any]) -> list[AtomResult]:
    """Lint the atoms of *memory_dir* and ``product/**`` — never AGENTS.md (a directory
    contract) nor ``product/index.md`` (a generated TOC)."""
    product_dir = memory_dir / "product"
    atom_files = sorted(p for p in memory_dir.glob("*.md") if p.name != "AGENTS.md")
    if product_dir.is_dir():
        atom_files += sorted(p for p in product_dir.glob("**/*.md") if p.name != "index.md")
    if not atom_files:
        print(f"WARNING: no .md atoms found in {memory_dir}", file=sys.stderr)
    return [lint_atom(md_path, memory_dir, schema) for md_path in atom_files]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint memory atom .md files for frontmatter + heading conformance."
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        required=True,
        help="Path to the specs/memory directory to lint.",
    )
    memory_dir: Path = parser.parse_args(argv).memory_dir.resolve()
    if not memory_dir.is_dir():
        print(f"ERROR: --memory-dir '{memory_dir}' is not a directory.", file=sys.stderr)
        return 1

    try:
        schema = load_frontmatter_schema()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    results = lint_directory(memory_dir, schema)
    errors = sum(1 for r in results if r.has_errors)
    print(f"lint-memory-atoms: scanned {len(results)} atom(s) in {memory_dir}")
    for result in results:
        print(f"  [{'ERROR' if result.has_errors else 'OK':5s}] {result.path}")
        for err in result.errors:
            print(f"          ERROR: {err}")
    print(f"\nSummary: {len(results) - errors} OK, {errors} ERROR")
    if errors:
        print(f"{errors} atom(s) have errors — fix before proceeding.", file=sys.stderr)
        return 1
    print("All atoms passed lint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
