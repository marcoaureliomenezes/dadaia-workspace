"""The memory-atom lint (LINT-1) — the ONE canonical implementation (v0.4.3 T-043-20/FR16).

Inverts the pre-v0.4.3 architecture: ``doctor_memory.MemoryValidator.check_lint1_memory_atoms``
used to shell out to the PROJECTED copy at ``dadaia_workspace/public/scripts/lint-memory-atoms.py``
via a subprocess — the package depended on its own distributed asset at runtime, backwards from
every other in-package check. This module IS the logic now; ``doctor_memory`` imports it
directly (no subprocess, no ``ProcessRunner``, no dependency on the projected copy existing or
being byte-identical). The projected ``public/scripts/lint-memory-atoms.py`` becomes a thin
wrapper that execs the workspace venv's ``python -m dadaia_workspace.features.specs.memory_lint``
entry point (ai-engineer's half of T-043-20 — see the task's handoff note for the exact contract).

Ported faithfully from the pre-v0.4.3 script (same frontmatter schema, same CLI
shape/exit codes) — the DEPENDENCY DIRECTION inverts (A16.1). The heading-vocabulary
check (a curated allowlist of "known" ## headings, plus an optional per-workspace
``.heading-allowlist`` extension file) is RETIRED: a heading vocabulary is prose
policy, not a lint. This module keeps only what a lint can mechanically decide —
frontmatter schema conformance, forbidden (changelog/history) headings, duplicate
headings, and wikilink resolution.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from dadaia_workspace.core import frontmatter as _fm
from dadaia_workspace.features.specs import memory_canon

__all__ = [
    "AtomResult",
    "lint_atom",
    "lint_directory",
    "load_frontmatter_schema",
    "main",
]


# ---------------------------------------------------------------------------
# Frontmatter schema resolution — packaged data, same technique as
# cli/commands/bugs.py's _schema_root() (public/ ships as package data in the
# installed wheel; importing FROM it is not the inversion FR16 fixes — the
# inversion was the LOGIC living only in the projected copy, requiring a subprocess).
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # dadaia_workspace/
_SCHEMA_REL = Path("public") / "schemas" / "memory" / "memory-frontmatter-v1.schema.json"


def load_frontmatter_schema() -> dict[str, Any]:
    """Load the packaged frontmatter JSON schema."""
    schema_path = _PACKAGE_ROOT / _SCHEMA_REL
    if not schema_path.exists():
        raise FileNotFoundError(
            f"memory-frontmatter-v1.schema.json not found at {schema_path} "
            "— the installed dadaia-workspace package is incomplete."
        )
    return cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = memory_canon.WIKILINK_RE

# v6 canon top-level singles (FR1/A1.5/A1.6, T-050-06): these three atoms' on-disk
# filenames were renamed (ARCHITECTURE.md, TECHSTACK.md, QUALITY.md) while their
# frontmatter `slug:` — the stable identity every `[[wikilink]]` across the memory
# corpus already references — stays unchanged (architecture / tech-stack /
# quality-assurance). This is the ONE named exception to "slug == filename stem" and
# to "wikilink target == <slug>.md": both checks below consult it instead of adding a
# second slug-resolution mechanism.
_CANON_SINGLE_FILENAMES: dict[str, str] = memory_canon.MEMORY_SINGLE_FILE_SLUGS


def _extract_h2_headings(body: str) -> list[str]:
    """Return list of ## heading texts in order of appearance."""
    return [m.group(1).strip() for m in _H2_RE.finditer(body)]


def _extract_wikilinks(body: str) -> list[str]:
    """Return list of slug strings from [[slug]] wikilinks."""
    return _WIKILINK_RE.findall(body)


# ---------------------------------------------------------------------------
# Per-atom lint
# ---------------------------------------------------------------------------


class AtomResult:
    """Collects errors and warnings for a single atom file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def lint_atom(
    md_path: Path,
    memory_dir: Path,
    schema: dict[str, Any],
) -> AtomResult:
    """Lint a single memory atom .md file. Returns an AtomResult."""
    result = AtomResult(md_path)
    stem = md_path.stem  # filename without extension

    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error(f"Cannot read file: {exc}")
        return result

    parsed = _fm.parse(content)

    if isinstance(parsed, _fm.FrontmatterError):
        # Bug memory-lint-blames-missing-delimiter-for-a-yaml-parse-error: name the
        # ACTUAL cause instead of always blaming a missing delimiter. `parsed.kind`
        # already distinguishes "no block" from "block present, YAML invalid at
        # line N" from "block present, not a mapping" — the fix IS not collapsing
        # them, so the message below is exactly `parsed.message`, unmodified.
        result.error(parsed.message)
        return result

    fm, body = parsed.data, parsed.body

    # Bug memory-trio-missing-required-frontmatter-fields (checker half):
    # ``jsonschema.validate()`` stops at the FIRST error `iter_errors` yields, so
    # a frontmatter block missing three required fields reports only one — an
    # author fixing it never sees the next two until they re-run. Iterating every
    # error reports each missing/violating field explicitly, in one pass.
    validator = Draft202012Validator(schema)
    for schema_error in sorted(validator.iter_errors(fm), key=str):
        result.error(f"Frontmatter schema violation: {schema_error.message}")
        # Do not return early — continue with remaining checks.

    slug = fm.get("slug")
    if isinstance(slug, str) and slug != stem:
        canon_name = _CANON_SINGLE_FILENAMES.get(slug)
        if canon_name is None or f"{stem}.md" != canon_name:
            result.error(
                f"'slug' frontmatter value '{slug}' does not match filename stem '{stem}'."
            )

    headings = _extract_h2_headings(body)
    seen: set[str] = set()

    for heading in headings:
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

    wikilinks = _extract_wikilinks(body)
    for wikilink_slug in wikilinks:
        target_name = _CANON_SINGLE_FILENAMES.get(wikilink_slug, f"{wikilink_slug}.md")
        if not any(memory_dir.rglob(target_name)):
            result.error(
                f"Wikilink [[{wikilink_slug}]] does not resolve to any .md file under {memory_dir}."
            )

    return result


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------


def lint_directory(memory_dir: Path, schema: dict[str, Any]) -> list[AtomResult]:
    """Lint all .md atoms found in memory_dir and memory_dir/product/."""
    # AGENTS.md is a directory contract (not an atom); it has no frontmatter.
    _non_atom_files: frozenset[str] = frozenset(["AGENTS.md"])

    atom_files: list[Path] = []

    atom_files.extend(sorted(p for p in memory_dir.glob("*.md") if p.name not in _non_atom_files))

    product_dir = memory_dir / "product"
    if product_dir.is_dir():
        # index.md is a GENERATED TOC (no frontmatter), not a memory atom.
        atom_files.extend(sorted(p for p in product_dir.glob("**/*.md") if p.name != "index.md"))

    if not atom_files:
        print(f"WARNING: no .md atoms found in {memory_dir}", file=sys.stderr)
        return []

    results: list[AtomResult] = []
    for md_path in atom_files:
        results.append(lint_atom(md_path, memory_dir, schema))
    return results


# ---------------------------------------------------------------------------
# Output / reporting / CLI entry point (kept for the thin-wrapper contract, ai-
# engineer's T-043-20 half: `python -m dadaia_workspace.features.specs.memory_lint`)
# ---------------------------------------------------------------------------


def _print_results(results: list[AtomResult]) -> None:
    """Print a per-atom summary to stdout."""
    for result in results:
        if result.has_errors:
            status = "ERROR"
        elif result.has_warnings:
            status = "WARN"
        else:
            status = "OK"

        print(f"  [{status:5s}] {result.path}")
        for err in result.errors:
            print(f"          ERROR: {err}")
        for warn in result.warnings:
            print(f"          WARN:  {warn}")


def _exit_code(results: list[AtomResult]) -> int:
    """Compute the exit code based on aggregated results."""
    if any(r.has_errors for r in results):
        return 1
    if any(r.has_warnings for r in results):
        return 2
    return 0


def _resolve_default_memory_dir() -> Path:
    """Walk up from CWD to find specs/memory under a workspace root."""
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "specs" / "memory"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not auto-resolve specs/memory directory. "
        "Run from inside a dadaia workspace or pass --memory-dir explicitly."
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — identical shape to the pre-v0.4.3 standalone script."""
    parser = argparse.ArgumentParser(
        description="Lint memory atom .md files for frontmatter + heading conformance."
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=None,
        help="Path to specs/memory directory. Defaults to auto-resolve from CWD.",
    )
    args = parser.parse_args(argv)

    memory_dir: Path
    if args.memory_dir is not None:
        memory_dir = args.memory_dir.resolve()
    else:
        try:
            memory_dir = _resolve_default_memory_dir()
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if not memory_dir.is_dir():
        print(f"ERROR: --memory-dir '{memory_dir}' is not a directory.", file=sys.stderr)
        return 1

    try:
        schema = load_frontmatter_schema()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    results = lint_directory(memory_dir, schema)

    total = len(results)
    errors = sum(1 for r in results if r.has_errors)
    warns = sum(1 for r in results if r.has_warnings and not r.has_errors)
    ok = total - errors - warns

    print(f"lint-memory-atoms: scanned {total} atom(s) in {memory_dir}")
    _print_results(results)
    print(f"\nSummary: {ok} OK, {warns} WARN-only, {errors} ERROR")

    code = _exit_code(results)
    if code == 0:
        print("All atoms passed lint.")
    elif code == 1:
        print(f"{errors} atom(s) have errors — fix before proceeding.", file=sys.stderr)
    else:
        print(f"{warns} atom(s) have warnings (unknown headings).", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
