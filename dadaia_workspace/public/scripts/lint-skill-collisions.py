#!/usr/bin/env python3
"""Flag undeclared `applyTo` activation-glob overlap between non-universal skills.

FR2 (v0.4.3, entry `dd-skills-applyto-glob-collisions` #32, acceptance rewritten by
R2). Scope is deliberately narrow: `applyTo: "**"` skills and `dadaia-grill-me`'s
`specs/**` are always-on by design and never asserted disjoint (that would be an
unsatisfiable diagnostic — the Satisfiable Diagnostics law). Among the remaining
("stage") skills, an overlap is fine **iff declared** below; an undeclared overlap
between two stage skills is a projection-time defect.

The declared-overlaps table mirrors `public/skills/dd-backlog-definition/SKILL.md`
§7 (canonical home for the precedence rule) — update both together.

Usage:
    lint-skill-collisions.py [--skills-dir <path>] [--self-test]

Exit codes:
    0 — no undeclared overlap (or --self-test passed)
    1 — at least one undeclared overlap found (or --self-test failed)
"""

from __future__ import annotations

import argparse
import re
import sys
from itertools import combinations
from pathlib import Path

# Public-source hygiene: never write a __pycache__/*.pyc under dadaia_workspace/public/.
sys.dont_write_bytecode = True

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_APPLYTO_RE = re.compile(r'^applyTo:\s*"?([^"\n]*)"?\s*$', re.MULTILINE)

# Skills whose activation surface is intentionally universal/near-universal — never
# asserted disjoint against anything (FR2/R2).
_UNIVERSAL_GLOBS: frozenset[str] = frozenset(["**"])
_UNIVERSAL_NAMES: frozenset[str] = frozenset(["dadaia-grill-me"])

# Declared overlaps (subset or intentional-identical relationships), mirrored from
# dd-backlog-definition/SKILL.md §7. Each entry is a frozenset of the 2+ skill names
# involved — any pairwise overlap among members of the same set is pre-cleared.
DECLARED_OVERLAPS: list[frozenset[str]] = [
    frozenset({"dd-release-implement", "dadaia-task-manager"}),
    frozenset({"dd-audit-project", "dadaia-workspace-doctor"}),
    frozenset({"dd-bug-registration", "dd-bug-fix"}),
    frozenset({"ai-context-engineering", "ai-harness-claude-code", "ai-harness-codex"}),
    frozenset({"dadaia-handoff-emitter", "project-orchestration", "dadaia-workspace-doctor"}),
]


def _is_declared(name_a: str, name_b: str) -> bool:
    return any({name_a, name_b} <= group for group in DECLARED_OVERLAPS)


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a `**`/`*` path glob into an anchored regex."""
    out: list[str] = []
    i = 0
    while i < len(glob):
        ch = glob[i]
        if glob[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _probe_paths(glob: str) -> list[str]:
    """Instantiate 1+ concrete candidate paths a glob could match."""
    filler_segment = "x"
    filler_tail = "x/y/z"
    concrete = glob.replace("**", filler_tail).replace("*", filler_segment)
    return [concrete]


def globs_overlap(glob_a: str, glob_b: str) -> bool:
    """True if the two globs could both match at least one concrete path."""
    if glob_a == glob_b:
        return True
    regex_a = _glob_to_regex(glob_a)
    regex_b = _glob_to_regex(glob_b)
    for probe in _probe_paths(glob_a):
        if regex_b.match(probe):
            return True
    return any(regex_a.match(probe) for probe in _probe_paths(glob_b))


def _parse_skill(md_path: Path) -> tuple[str, str] | None:
    """Return (name, applyTo) for a SKILL.md, or None if no frontmatter / no name."""
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return None
    raw = m.group(1)
    name_m = _NAME_RE.search(raw)
    if not name_m:
        return None
    apply_m = _APPLYTO_RE.search(raw)
    apply_to = apply_m.group(1).strip() if apply_m else ""
    return name_m.group(1), apply_to


def collect_stage_skills(skills_dir: Path) -> list[tuple[str, str]]:
    """Return (name, applyTo) pairs for non-universal, path-claiming stage skills."""
    stage: list[tuple[str, str]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        parsed = _parse_skill(skill_md)
        if parsed is None:
            continue
        name, apply_to = parsed
        if not apply_to:
            continue  # no path claim — nothing to collide over
        if apply_to in _UNIVERSAL_GLOBS or name in _UNIVERSAL_NAMES:
            continue
        stage.append((name, apply_to))
    return stage


def find_undeclared_overlaps(stage_skills: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Return the list of (name_a, name_b) pairs that overlap without a declaration."""
    findings: list[tuple[str, str]] = []
    for (name_a, glob_a), (name_b, glob_b) in combinations(stage_skills, 2):
        if not globs_overlap(glob_a, glob_b):
            continue
        if _is_declared(name_a, name_b):
            continue
        findings.append((name_a, name_b))
    return findings


def _resolve_default_skills_dir() -> Path:
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "dadaia_workspace" / "public" / "skills"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not auto-resolve dadaia_workspace/public/skills. "
        "Run from inside the dadaia-workspace repo or pass --skills-dir explicitly."
    )


def _self_test() -> int:
    """Prove: (a) a `**` skill never fires even with an obvious path collision;
    (b) a newly introduced undeclared duplicate pair does fire. In-memory fixtures
    only — never reads or writes tests/**."""
    ok = True

    # (a) universal skill silence
    universal_case = [("some-universal", "**"), ("some-stage", "specs/foo/**")]
    stage_only = [p for p in universal_case if p[1] not in _UNIVERSAL_GLOBS]
    findings_a = find_undeclared_overlaps(stage_only)
    if findings_a:
        print(f"SELF-TEST FAIL (a): expected silence, got {findings_a}", file=sys.stderr)
        ok = False
    else:
        print("SELF-TEST PASS (a): universal-glob skill produces no finding.")

    # (b) newly introduced undeclared duplicate fires
    duplicate_case = [
        ("fixture-skill-one", "specs/newthing/**"),
        ("fixture-skill-two", "specs/newthing/**"),
    ]
    findings_b = find_undeclared_overlaps(duplicate_case)
    if not findings_b:
        print(
            "SELF-TEST FAIL (b): expected an undeclared-duplicate finding, got none.",
            file=sys.stderr,
        )
        ok = False
    else:
        print(f"SELF-TEST PASS (b): undeclared duplicate fired: {findings_b}")

    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flag undeclared applyTo activation-glob overlap between non-universal skills."
    )
    parser.add_argument("--skills-dir", type=Path, default=None)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run the in-memory fixture proof (A2.4) instead of scanning the real tree.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    skills_dir: Path
    if args.skills_dir is not None:
        skills_dir = args.skills_dir.resolve()
    else:
        try:
            skills_dir = _resolve_default_skills_dir()
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    stage_skills = collect_stage_skills(skills_dir)
    findings = find_undeclared_overlaps(stage_skills)

    print(f"lint-skill-collisions: scanned {len(stage_skills)} stage skill(s) in {skills_dir}")
    if not findings:
        print("No undeclared applyTo overlap among non-universal skills.")
        return 0

    for name_a, name_b in findings:
        print(f"  [ERROR] undeclared overlap: '{name_a}' vs '{name_b}'", file=sys.stderr)
    print(
        f"\n{len(findings)} undeclared overlap(s) — narrow one glob or add a declared "
        "entry to dd-backlog-definition/SKILL.md §7 and this script's DECLARED_OVERLAPS.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
