#!/usr/bin/env python3
"""Lint memory atom .md files for the memory-markdown-source-v1 release.

Usage:
    lint-memory-atoms.py [--memory-dir <path>]

    Default --memory-dir resolves to specs/memory relative to the workspace root
    found by walking up from CWD until a directory containing specs/memory is found.

Exit codes:
    0  — all atoms valid (no ERRORs, no WARNINGs)
    1  — at least one ERROR found
    2  — warnings only (no ERRORs, at least one WARNING)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import ValidationError, validate

# Public-source hygiene (T-011-15 / FR-W5-01): never write a __pycache__/*.pyc under
# dadaia_workspace/public/. This guard fires no matter how the script is invoked
# (direct `python <script>`, subprocess, or import), complementing the `-B` flag at
# the subprocess call site in features/specs/doctor.py.
sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# Heading allowlist (union of Groups A + B + C from W0 decisions report)
# Exact strings, case-sensitive.  See T-MMS-W0-01 for the enumeration.
# ---------------------------------------------------------------------------

# Group A — Standard product atom sections (used 14× each)
_HEADING_GROUP_A: frozenset[str] = frozenset(
    [
        "Propósito",
        "Fluxo de uso",
        "Trigger típico",
        "Diferencial",
        "Estado runtime tocado",
        "Dependências",
    ]
)

# Group B — Extended product atom sections (one-offs in divergent atoms)
_HEADING_GROUP_B: frozenset[str] = frozenset(
    [
        "Fora de escopo (deferido a backlog)",
        "Fora de escopo (drifts conhecidos)",
        "Próximos passos",
        "O que é",
        "Schema location",
        "CLI",
        "Skill: dadaia-handoff-emitter",
        "Adoção (15 de 15 agentes)",
        "Referência",
        "Brand identity",
        "Decision Authority Matrix — domínios novos (r3)",
        "Handoff-first emission contract (ADR-X5)",
        "Dispatch-to-researcher pattern (ADR-X6)",
        "Plugin-scope enforcement (ADR-X7)",
        "Codex Dispatcher Capability Matrix (ADR-3)",
    ]
)

# Group C — Core and index atom sections (architecture, tech-stack, index only)
_HEADING_GROUP_C: frozenset[str] = frozenset(
    [
        "Visão atômica",
        "Usuários",
        "Catálogo de features",
        "Mapa de capacidades",
        "Limites conhecidos",
        "Evidências visuais",
        "Visão geral",
        "Camadas",
        "Regras de dependência",
        "Fluxo de dados — pipeline asset chain",
        "Fluxo de dados — gate v3 SDD (com RULE E e PostToolUse)",
        "Contratos entre módulos",
        "Estado runtime",
        "Memory injection subsystem",
        "Structured-memory-source subsystem",
        "Linguagens",
        "Runtimes e ferramentas",
        "Agent runtimes",
        "Model assignments (20 agentes)",
        "Plugin inventory",
        "Schema handoff-v1.1",
        "Dependências aprovadas",
        "Restrições e proibições",
        "Comandos canônicos",
    ]
)

HEADING_ALLOWLIST: frozenset[str] = _HEADING_GROUP_A | _HEADING_GROUP_B | _HEADING_GROUP_C

# Forbidden headings — belt-and-suspenders, checked independently of the allowlist.
# Case-insensitive match (strip/lower comparison).
_FORBIDDEN_HEADING_LOWER: frozenset[str] = frozenset(
    ["changelog", "histórico", "history", "versions"]
)

# ---------------------------------------------------------------------------
# Frontmatter schema path (relative to this script at install time)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_SCHEMA_PATH = _SCRIPT_DIR.parent / "schemas" / "memory" / "memory-frontmatter-v1.schema.json"


def _load_schema() -> dict[str, Any]:
    """Load the frontmatter JSON schema from the canonical path."""
    if not _SCHEMA_PATH.exists():
        # Fallback: search relative to the repo root (dev/editable install)
        for parent in _SCRIPT_DIR.parents:
            candidate = (
                parent
                / "dadaia_workspace"
                / "public"
                / "schemas"
                / "memory"
                / "memory-frontmatter-v1.schema.json"
            )
            if candidate.exists():
                return cast(dict[str, Any], json.loads(candidate.read_text(encoding="utf-8")))
        raise FileNotFoundError(
            f"memory-frontmatter-v1.schema.json not found at {_SCHEMA_PATH} "
            "or any parent dadaia_workspace/public/schemas/memory/"
        )
    return cast(dict[str, Any], json.loads(_SCHEMA_PATH.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _parse_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Return (frontmatter_dict, body_text) or (None, full_content) if no frontmatter."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return None, content
    raw_yaml = m.group(1)
    body = content[m.end() :]
    try:
        fm = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return None, content
    if not isinstance(fm, dict):
        return None, content
    return fm, body


def _extract_h2_headings(body: str) -> list[str]:
    """Return list of ## heading texts in order of appearance."""
    return [m.group(1).strip() for m in _H2_RE.finditer(body)]


def _extract_wikilinks(body: str) -> list[str]:
    """Return list of slug strings from [[slug]] wikilinks."""
    return _WIKILINK_RE.findall(body)


def _estimate_tokens(body: str) -> int:
    """Approximate body token count: word_count * 1.35 (stdlib only, no tiktoken)."""
    return round(len(body.split()) * 1.35)


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
    """Lint a single memory atom .md file.  Returns an AtomResult."""
    result = AtomResult(md_path)
    stem = md_path.stem  # filename without extension

    # --- Read file ---
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error(f"Cannot read file: {exc}")
        return result

    # --- Parse frontmatter ---
    fm, body = _parse_frontmatter(content)

    if fm is None:
        result.error("No valid YAML frontmatter found (expected --- delimited block).")
        # Cannot proceed with further checks.
        return result

    # --- (a+b+c) Schema validation (required fields + additionalProperties) ---
    try:
        validate(instance=fm, schema=schema)
    except ValidationError as exc:
        result.error(f"Frontmatter schema violation: {exc.message}")
        # Do not return early — continue with remaining checks.

    # --- slug == filename stem ---
    slug = fm.get("slug")
    if isinstance(slug, str) and slug != stem:
        result.error(f"'slug' frontmatter value '{slug}' does not match filename stem '{stem}'.")

    # --- (d+e+h) Heading checks ---
    headings = _extract_h2_headings(body)
    seen: set[str] = set()

    for heading in headings:
        heading_lower = heading.strip().lower()

        # Belt-and-suspenders forbidden check (case-insensitive)
        if heading_lower in _FORBIDDEN_HEADING_LOWER:
            result.error(
                f"Forbidden heading '## {heading}' — changelog/history sections "
                "violate the atomicity contract (specs/memory/AGENTS.md §3)."
            )
            continue

        # Allowlist check
        if heading not in HEADING_ALLOWLIST:
            result.warn(
                f"'## {heading}' is not in the curated allowlist — consider "
                "normalising or adding it to the allowlist in lint-memory-atoms.py."
            )

        # Duplicate check
        if heading in seen:
            result.error(f"Duplicate '## {heading}' heading found.")
        else:
            seen.add(heading)

    # --- (f) Wikilink resolution ---
    wikilinks = _extract_wikilinks(body)
    for wikilink_slug in wikilinks:
        # Slugs may refer to a top-level atom or any atom nested anywhere under
        # product/ (v0.1.9 thematic-subdir tree). Resolve by slug at any depth.
        if not any(memory_dir.rglob(f"{wikilink_slug}.md")):
            result.error(
                f"Wikilink [[{wikilink_slug}]] does not resolve to any .md file under {memory_dir}."
            )

    # --- (g) token_estimate drift warning ---
    token_estimate = fm.get("token_estimate")
    if isinstance(token_estimate, int) and token_estimate > 0:
        actual = _estimate_tokens(body)
        if actual > 0:
            drift = abs(actual - token_estimate) / token_estimate
            if drift > 0.20:
                result.warn(
                    f"'token_estimate' drift: frontmatter says {token_estimate}, "
                    f"computed ≈{actual} (drift {drift:.0%} > 20%). "
                    "Update the frontmatter value."
                )

    return result


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------


def lint_directory(memory_dir: Path, schema: dict[str, Any]) -> list[AtomResult]:
    """Lint all .md atoms found in memory_dir and memory_dir/product/."""
    # Files that live in specs/memory/ but are NOT memory atoms.
    # AGENTS.md is a directory contract (not an atom); it has no frontmatter.
    _NON_ATOM_FILES: frozenset[str] = frozenset(["AGENTS.md"])

    atom_files: list[Path] = []

    # Top-level atoms (e.g. architecture.md, tech-stack.md)
    atom_files.extend(sorted(p for p in memory_dir.glob("*.md") if p.name not in _NON_ATOM_FILES))

    # Product atoms (product/*.md). index.md is a GENERATED TOC (no frontmatter),
    # not a memory atom — exclude it like AGENTS.md.
    product_dir = memory_dir / "product"
    if product_dir.is_dir():
        # Recurse into thematic subdirs (v0.1.9 tree). index.md is the catalog TOC.
        atom_files.extend(sorted(p for p in product_dir.glob("**/*.md") if p.name != "index.md"))

    if not atom_files:
        print(f"WARNING: no .md atoms found in {memory_dir}", file=sys.stderr)
        return []

    results: list[AtomResult] = []
    for md_path in atom_files:
        results.append(lint_atom(md_path, memory_dir, schema))
    return results


# ---------------------------------------------------------------------------
# Output / reporting
# ---------------------------------------------------------------------------


def _print_results(results: list[AtomResult]) -> None:
    """Print a per-atom summary to stdout."""
    for result in results:
        rel = result.path.name
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
        _ = rel  # used implicitly via result.path above


def _exit_code(results: list[AtomResult]) -> int:
    """Compute the exit code based on aggregated results."""
    if any(r.has_errors for r in results):
        return 1
    if any(r.has_warnings for r in results):
        return 2
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _resolve_default_memory_dir() -> Path:
    """Walk up from CWD to find specs/memory under a workspace root."""
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "specs" / "memory"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not auto-resolve specs/memory directory.  "
        "Run from inside a dadaia workspace or pass --memory-dir explicitly."
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns exit code."""
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
        schema = _load_schema()
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
        print(
            f"{warns} atom(s) have warnings (token_estimate drift or unknown headings).",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
