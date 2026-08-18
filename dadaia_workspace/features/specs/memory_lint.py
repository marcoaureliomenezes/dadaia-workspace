"""The memory-atom lint (LINT-1) — the ONE canonical implementation (v0.4.3 T-043-20/FR16).

Inverts the pre-v0.4.3 architecture: ``doctor_memory.MemoryValidator.check_lint1_memory_atoms``
used to shell out to the PROJECTED copy at ``dadaia_workspace/public/scripts/lint-memory-atoms.py``
via a subprocess — the package depended on its own distributed asset at runtime, backwards from
every other in-package check. This module IS the logic now; ``doctor_memory`` imports it
directly (no subprocess, no ``ProcessRunner``, no dependency on the projected copy existing or
being byte-identical). The projected ``public/scripts/lint-memory-atoms.py`` becomes a thin
wrapper that execs the workspace venv's ``python -m dadaia_workspace.features.specs.memory_lint``
entry point (ai-engineer's half of T-043-20 — see the task's handoff note for the exact contract).

Ported faithfully from the pre-v0.4.3 script (same heading-allowlist groups, same frontmatter
schema, same per-atom checks, same CLI shape/exit codes) — behavior is unchanged, only the
DEPENDENCY DIRECTION inverts (A16.1).
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

__all__ = [
    "HEADING_ALLOWLIST",
    "AtomResult",
    "lint_atom",
    "lint_directory",
    "load_frontmatter_schema",
    "load_workspace_allowlist",
    "main",
]

# ---------------------------------------------------------------------------
# Heading allowlist (union of Groups A + B + C from the W0 decisions report,
# extended by Groups D-S over subsequent releases). Exact strings, case-sensitive.
# ---------------------------------------------------------------------------

# Group A — Standard product atom sections.
# PT legacy entries are KEPT (G2, v0.1.48): consumer workspaces carry PT atoms and
# must keep linting clean without any atom edit.
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

# Group A (EN) — the ENGLISH canonical Group-A set (F-79 / v0.1.48 English canon).
# 1:1 translations of the PT Group-A sections above; new/renamed atoms use these.
_HEADING_GROUP_A_EN: frozenset[str] = frozenset(
    [
        "Purpose",
        "Usage flow",
        "Typical trigger",
        "Differentiator",
        "Runtime state touched",
        "Dependencies",
        # Canonical headings emitted by the `dadaia memory product add` template
        # (public/templates/memory-feature.md). A supported "add a feature" atom must
        # lint clean out of the box (test_memory_feature_template_headings_are_allowlisted).
        "Current behavior",
        "Boundaries",
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
        # "Adoção (15 de 15 agentes)" pruned in v0.1.48 (F-79): 0 usages in specs/memory/.
        "Referência",
        "Brand identity",
        "Decision Authority Matrix — domínios novos (r3)",
        "Handoff-first emission contract (ADR-X5)",
        "Dispatch-to-researcher pattern (ADR-X6)",
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
        # "Model assignments (20 agentes)" pruned in v0.1.48 (F-79): 0 usages in specs/memory/.
        "Schema handoff-v1.1",
        "Dependências aprovadas",
        "Restrições e proibições",
        "Comandos canônicos",
    ]
)

# Group D — Legitimate current-atom canon headings (F9 / T-PIO-09).
_HEADING_GROUP_D: frozenset[str] = frozenset(
    [
        "Acquire do lease (O_EXCL CAS + stable-session-identity)",
        "Adoção (9 agentes core)",
        "Agent roster and phase ownership (constitution §14 + §7)",
        "Blocking and resume",
        "CI matrix 3-OS (graduated — hard-gated)",
        "Contrato de resiliência — 3 tiers",
        "Core services",
        "Current limits",
        "Dispatcher purity (constitution §9)",
        "Fluxo de dados — gate v3 SDD (v0.1.14: entrypoint merged pre_gate)",
        "Gating note (current behavior)",
        "Harness runtime boundary",
        "Hygiene and anti-slop behavior",
        "Model assignments (9 core agents)",
        "Modelo de concorrência e lease (v0.1.14)",
        "Multi-harness runtime parity (constitution §4)",
        "Os 3 canais de reporte/comunicação (constitution §11)",
        "O Spec Context Project (conceito central)",
        "Plataforma seam — `core/platform.py`",
        "Portos e adapters (4 + 9)",
        "Public surface counts (v0.2.0)",
        "Python governance hooks package",
        "Structured-memory-source subsystem (memory-markdown-source-v1)",
        "Sub-agent model (constitution §9)",
        "Topologia de agentes (9 core)",
    ]
)

# Group E — Workflow / backlog subsystem canon headings (v0.1.25–v0.1.45).
_HEADING_GROUP_E: frozenset[str] = frozenset(
    [
        "Backlog-consistency subsystem (`features/backlog/`, v0.1.25)",
        "Workflow control plane subsystem (v0.1.28 + v0.1.29)",
        "Workflow-step handoff data plane (v0.1.30)",
        "Workflows control plane (v0.1.28, redesenhado em v0.1.45)",
        "Workflow model governance (control plane, v0.1.28)",
        "Harness as a governed dimension (v0.1.29)",
        "Gating note (review-only typed gate + coherent worker-output contract)",
    ]
)

# Group F — v0.1.48 architecture.md canon (F-79).
_HEADING_GROUP_F: frozenset[str] = frozenset(
    [
        "Modelo de concorrência e lease",
        "Backlog-consistency subsystem (`features/backlog/`)",
        "Workflow control plane subsystem",
        "Workflow-step handoff data plane",
        "Concurrency and lease model",
    ]
)

_HEADING_GROUP_G: frozenset[str] = frozenset(
    [
        "Adoption (9 core agents)",
        "Agent topology (9 core)",
        "Approved dependencies",
        "Canonical commands",
        "Capability map",
        "Contracts between modules",
        "Data flow — asset chain pipeline",
        "Dependency rules",
        "Known limits",
        "Languages",
        "Layers",
        "Lease acquire (O_EXCL CAS + stable-session-identity)",
        "Overview",
        "Platform seam — `core/platform.py`",
        "Ports and adapters (4 + 9)",
        "Resilience contract — 3 tiers",
        "Restrictions and prohibitions",
        "Runtimes and tools",
        "Runtime state",
        "The 3 report/communication channels (constitution §11)",
        "The Spec Context Project (central concept)",
        "Users",
        "Visual evidence",
        "What it is",
        "Workflows control plane (v0.1.28, redesigned in v0.1.45)",
    ]
)

# Group S — scaffold template sections (v0.1.49 FR3).
_HEADING_GROUP_S: frozenset[str] = frozenset(
    [
        "Padrões de qualidade",
        "Disciplina de testes",
    ]
)

HEADING_ALLOWLIST: frozenset[str] = (
    _HEADING_GROUP_A
    | _HEADING_GROUP_A_EN
    | _HEADING_GROUP_B
    | _HEADING_GROUP_C
    | _HEADING_GROUP_D
    | _HEADING_GROUP_E
    | _HEADING_GROUP_F
    | _HEADING_GROUP_G
    | _HEADING_GROUP_S
)

# Workspace extension file (v0.1.49 FR3): optional `<memory-dir>/.heading-allowlist`
# — UTF-8, one exact heading per line; blank lines and `#` comments ignored. Merged
# (union) with the curated allowlist at lint time so consumers extend the canon
# without editing this module. The file sits in the MEMORY path class: consumers
# edit it via file tools in DEFINITION/CLOSURE phase (gate law, v0.4.3 FR13 ratifies
# this classification explicitly — no dotfile carve-out).
_WORKSPACE_ALLOWLIST_NAME = ".heading-allowlist"


def load_workspace_allowlist(memory_dir: Path) -> frozenset[str]:
    """Load the optional workspace heading allowlist from ``memory_dir``."""
    path = memory_dir / _WORKSPACE_ALLOWLIST_NAME
    if not path.is_file():
        return frozenset()
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return frozenset()
    headings: set[str] = set()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        headings.add(stripped)
    return frozenset(headings)


# Forbidden headings — belt-and-suspenders, checked independently of the allowlist.
# Case-insensitive match (strip/lower comparison).
_FORBIDDEN_HEADING_LOWER: frozenset[str] = frozenset(
    ["changelog", "histórico", "history", "versions"]
)

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
    allowlist: frozenset[str] = HEADING_ALLOWLIST,
) -> AtomResult:
    """Lint a single memory atom .md file. Returns an AtomResult."""
    result = AtomResult(md_path)
    stem = md_path.stem  # filename without extension

    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error(f"Cannot read file: {exc}")
        return result

    fm, body = _parse_frontmatter(content)

    if fm is None:
        result.error("No valid YAML frontmatter found (expected --- delimited block).")
        return result

    try:
        validate(instance=fm, schema=schema)
    except ValidationError as exc:
        result.error(f"Frontmatter schema violation: {exc.message}")
        # Do not return early — continue with remaining checks.

    slug = fm.get("slug")
    if isinstance(slug, str) and slug != stem:
        result.error(f"'slug' frontmatter value '{slug}' does not match filename stem '{stem}'.")

    headings = _extract_h2_headings(body)
    seen: set[str] = set()

    for heading in headings:
        heading_lower = heading.strip().lower()

        if heading_lower in _FORBIDDEN_HEADING_LOWER:
            result.error(
                f"Forbidden heading '## {heading}' — changelog/history sections "
                "violate the atomicity contract (specs/memory/AGENTS.md §3)."
            )
            continue

        if heading not in allowlist:
            result.warn(
                f"'## {heading}' is not in the curated allowlist — consider "
                "normalising, adding it to the allowlist in memory_lint.py, "
                f"or listing it in <memory-dir>/{_WORKSPACE_ALLOWLIST_NAME}."
            )

        if heading in seen:
            result.error(f"Duplicate '## {heading}' heading found.")
        else:
            seen.add(heading)

    wikilinks = _extract_wikilinks(body)
    for wikilink_slug in wikilinks:
        if not any(memory_dir.rglob(f"{wikilink_slug}.md")):
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

    allowlist = HEADING_ALLOWLIST | load_workspace_allowlist(memory_dir)
    results: list[AtomResult] = []
    for md_path in atom_files:
        results.append(lint_atom(md_path, memory_dir, schema, allowlist))
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
