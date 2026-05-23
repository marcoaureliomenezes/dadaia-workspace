#!/usr/bin/env python3
"""check_agent_topology.py — drift guard for the 20-agent canonical topology.

Authored for release agents-r3-v1 task R3-22. Asserts the invariants that the
SDD agent layer relies on. Run from the repo root:

    .dadaia/.venv/bin/python scripts/check_agent_topology.py

Exit codes:
    0  All invariants hold.
    1  At least one invariant violated; report printed to stdout, details
       to stderr.

Invariants (per SPEC agents-r3-v1):
    I1  Exactly 20 persona files under dadaia_workspace/public/agents/.
    I2  Each persona has frontmatter with: name, description, tier, model,
        tools, paths.write_allowlist (non-empty).
    I3  project-manager.md AND project-auditor.md each name every one of the
        17 leaf agents in their body.
    I4  The Decision Authority Matrix in public/skills/project-orchestration/
        SKILL.md contains rows for: "Python implementation",
        "Node implementation", "Data engineering", "BI / dashboards",
        "AI entities".
    I5  No bare `software-engineer` references (i.e. not followed by `-python`
        or `-node`) anywhere in
        dadaia_workspace/public/{agents,workflows,skills,commands,rules,data}/.

ASCII output only — no colors. Stdlib + PyYAML (already a repo dependency).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError as exc:  # pragma: no cover - env-dependent
    print(f"FATAL: PyYAML required ({exc}). Install via .dadaia/.venv/bin/pip.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC = REPO_ROOT / "dadaia_workspace" / "public"
AGENTS_DIR = PUBLIC / "agents"
SKILLS_DIR = PUBLIC / "skills"
DAM_SKILL = SKILLS_DIR / "project-orchestration" / "SKILL.md"

EXPECTED_AGENT_COUNT = 20

# Tier 1 dispatchers and tier 2 curator are stripped before assembling the
# 17 T3 leaf-agent roster. Order does not matter for any check.
T1 = {"project-manager", "project-auditor"}
T2 = {"product-engineer"}

REQUIRED_FRONTMATTER_KEYS = ("name", "description", "tier", "model", "tools")

REQUIRED_DAM_ROWS = (
    "Python implementation",
    "Node implementation",
    "Data engineering",
    "BI / dashboards",
    "AI entities",
)

SCAN_DIRS_FOR_BARE_SE = (
    PUBLIC / "agents",
    PUBLIC / "workflows",
    PUBLIC / "skills",
    PUBLIC / "commands",
    PUBLIC / "rules",
    PUBLIC / "data",
)

# A bare reference is `software-engineer` NOT followed by `-python` or `-node`.
# Word boundary preceding to avoid matching e.g. `python-software-engineer`.
BARE_SE_RE = re.compile(r"\bsoftware-engineer\b(?!-(?:python|node))")

# Lines that intentionally mention the legacy `software-engineer` agent to
# explain the split (in software-engineer-python.md / software-engineer-node.md
# persona bodies) are allowlisted. The marker is the word "legacy" followed
# by an optional backtick and then "software-engineer".
LEGACY_SE_RE = re.compile(r"legacy\s+`?software-engineer`?")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter dict from a markdown file. None on failure."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].lstrip("\n")
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _list_agent_files() -> list[Path]:
    return sorted(p for p in AGENTS_DIR.glob("*.md") if p.is_file())


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------


def check_i1_agent_count(errors: list[str]) -> list[Path]:
    """I1: Exactly EXPECTED_AGENT_COUNT persona files."""
    files = _list_agent_files()
    if len(files) != EXPECTED_AGENT_COUNT:
        errors.append(
            f"I1 FAIL: expected {EXPECTED_AGENT_COUNT} agent files under "
            f"{AGENTS_DIR.relative_to(REPO_ROOT)}, found {len(files)}: "
            f"{[p.name for p in files]}"
        )
    return files


def check_i2_frontmatter(files: list[Path], errors: list[str]) -> dict[str, dict]:
    """I2: Each persona has required frontmatter keys + non-empty
    paths.write_allowlist. Returns dict mapping stem -> frontmatter."""
    by_stem: dict[str, dict] = {}
    for path in files:
        stem = path.stem
        fm = _parse_frontmatter(_read_text(path))
        if fm is None:
            errors.append(f"I2 FAIL: {stem}: malformed or missing frontmatter")
            continue
        by_stem[stem] = fm

        for key in REQUIRED_FRONTMATTER_KEYS:
            if key not in fm or fm[key] in (None, "", []):
                errors.append(f"I2 FAIL: {stem}: required frontmatter key {key!r} missing or empty")

        paths_block = fm.get("paths")
        if not isinstance(paths_block, dict):
            errors.append(f"I2 FAIL: {stem}: 'paths' block missing or not a dict")
            continue
        wl = paths_block.get("write_allowlist")
        if not isinstance(wl, list) or not wl:
            errors.append(f"I2 FAIL: {stem}: 'paths.write_allowlist' missing or empty")
    return by_stem


def check_i3_dispatchers_name_leaves(
    by_stem: dict[str, dict],
    errors: list[str],
) -> None:
    """I3: PM + auditor each mention every T3 leaf agent in their body."""
    leaves = sorted(set(by_stem.keys()) - T1 - T2)
    if not leaves:
        errors.append("I3 FAIL: no T3 leaf agents discovered (T1+T2 set ate the roster)")
        return

    for dispatcher in ("project-manager", "project-auditor"):
        dpath = AGENTS_DIR / f"{dispatcher}.md"
        if not dpath.exists():
            errors.append(f"I3 FAIL: {dispatcher}.md missing")
            continue
        body = _read_text(dpath)
        missing = [leaf for leaf in leaves if leaf not in body]
        if missing:
            errors.append(f"I3 FAIL: {dispatcher}.md does not mention these leaf agents: {missing}")


def check_i4_dam_rows(errors: list[str]) -> None:
    """I4: DAM SKILL.md contains rows for all 5 required scopes."""
    if not DAM_SKILL.exists():
        errors.append(f"I4 FAIL: {DAM_SKILL.relative_to(REPO_ROOT)} missing")
        return
    text = _read_text(DAM_SKILL)
    for row_label in REQUIRED_DAM_ROWS:
        if row_label not in text:
            errors.append(f"I4 FAIL: DAM is missing row labelled {row_label!r}")


def check_i5_no_bare_se(errors: list[str]) -> None:
    """I5: no `software-engineer` (without -python/-node suffix) in public scan dirs."""
    hits: list[str] = []
    for root in SCAN_DIRS_FOR_BARE_SE:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in (".md", ".yaml", ".yml", ".txt", ".sh"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if BARE_SE_RE.search(line) and not LEGACY_SE_RE.search(line):
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    if hits:
        errors.append(
            "I5 FAIL: bare `software-engineer` references found "
            "(must be -python or -node suffixed):\n  " + "\n  ".join(hits)
        )


def check_i6_skill_links(agents: dict[str, dict], errors: list[str]) -> None:
    """I6: Every skill name in each agent's frontmatter skills: list must
    resolve to an existing directory under dadaia_workspace/public/skills/.
    """
    for stem, fm in agents.items():
        skills = fm.get("skills", [])
        if not isinstance(skills, list):
            errors.append(f"I6 FAIL: {stem}: 'skills' frontmatter is not a list")
            continue
        for skill_name in skills:
            skill_dir = SKILLS_DIR / skill_name
            if not skill_dir.is_dir():
                errors.append(
                    f"I6 FAIL: {stem}: skill ref {skill_name!r} not found (expected {skill_dir})"
                )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    errors: list[str] = []

    files = check_i1_agent_count(errors)
    by_stem = check_i2_frontmatter(files, errors)
    check_i3_dispatchers_name_leaves(by_stem, errors)
    check_i4_dam_rows(errors)
    check_i5_no_bare_se(errors)
    check_i6_skill_links(by_stem, errors)

    if errors:
        print("AGENT TOPOLOGY DRIFT DETECTED")
        print("=" * 60)
        for err in errors:
            print(err)
        print("=" * 60)
        print(f"{len(errors)} invariant violation(s).")
        return 1

    print("AGENT TOPOLOGY OK")
    print(f"  I1: {len(files)} persona files (expected {EXPECTED_AGENT_COUNT})")
    print("  I2: all frontmatter blocks valid")
    print(f"  I3: PM + auditor reference {len(by_stem) - len(T1) - len(T2)} T3 leaves")
    print(f"  I4: DAM contains {len(REQUIRED_DAM_ROWS)} required rows")
    print("  I5: no bare software-engineer references")
    print(f"  I6: {len(by_stem)} agents x skill refs validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
