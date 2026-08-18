#!/usr/bin/env python3
"""Derive the `dadaia-cli` skill grant from each agent's `Bash` tool and fail loud on drift.

FR5 (v0.4.3, entry `dadaia-cli-skill-agent-grant` #36). The rule is mechanical: an
agent whose `tools:` frontmatter includes `Bash` is shell-capable and must carry the
`dadaia-cli` skill grant; an agent with no `Bash` (`product-engineer`,
`software-architect`) would find the grant inert and must NOT carry it. This mirrors
`public/skills/dadaia-cli/SKILL.md`'s "Reachability" table — keep both in sync.

Usage:
    lint-dadaia-cli-reachability.py [--agents-dir <path>] [--self-test]

Exit codes:
    0 — every agent's grant matches its Bash-capability (or --self-test passed)
    1 — at least one agent's grant disagrees with its Bash-capability
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_TOOLS_BLOCK_RE = re.compile(r"^tools:\n((?:  - .+\n)+)", re.MULTILINE)
_SKILLS_BLOCK_RE = re.compile(r"^skills:\n((?:  - .+\n)+)", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^  - (.+)$", re.MULTILINE)


def _parse_agent(md_path: Path) -> tuple[str, bool, bool] | None:
    """Return (name, has_bash, has_dadaia_cli_grant) or None if unparseable."""
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    fm_match = _FRONTMATTER_RE.match(content)
    if not fm_match:
        return None
    raw = fm_match.group(1)
    name_m = _NAME_RE.search(raw)
    if not name_m:
        return None
    tools_m = _TOOLS_BLOCK_RE.search(raw)
    tools = _LIST_ITEM_RE.findall(tools_m.group(1)) if tools_m else []
    skills_m = _SKILLS_BLOCK_RE.search(raw)
    skills = _LIST_ITEM_RE.findall(skills_m.group(1)) if skills_m else []
    return name_m.group(1), "Bash" in tools, "dadaia-cli" in skills


def find_drift(agents: list[tuple[str, bool, bool]]) -> list[tuple[str, bool, bool]]:
    """Return (name, has_bash, has_grant) triples where grant disagrees with Bash-capability."""
    return [
        (name, has_bash, has_grant) for name, has_bash, has_grant in agents if has_bash != has_grant
    ]


def _resolve_default_agents_dir() -> Path:
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "dadaia_workspace" / "public" / "agents"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not auto-resolve dadaia_workspace/public/agents. "
        "Run from inside the dadaia-workspace repo or pass --agents-dir explicitly."
    )


def _self_test() -> int:
    """In-memory fixture proof — never reads or writes tests/**."""
    ok = True

    # (a) Bash-capable agent WITHOUT the grant must fire.
    missing_grant = [("fixture-shell-agent", True, False)]
    findings_a = find_drift(missing_grant)
    if not findings_a:
        print("SELF-TEST FAIL (a): expected a missing-grant finding, got none.", file=sys.stderr)
        ok = False
    else:
        print(f"SELF-TEST PASS (a): missing grant on a Bash-capable agent fired: {findings_a}")

    # (b) shell-less agent WITHOUT the grant is correct — no finding.
    correct_exclusion = [("fixture-shell-less-agent", False, False)]
    findings_b = find_drift(correct_exclusion)
    if findings_b:
        print(f"SELF-TEST FAIL (b): expected silence, got {findings_b}", file=sys.stderr)
        ok = False
    else:
        print("SELF-TEST PASS (b): shell-less agent with no grant produces no finding.")

    # (c) shell-less agent WITH an inert grant must also fire (over-grant is drift too).
    inert_grant = [("fixture-shell-less-agent-overgranted", False, True)]
    findings_c = find_drift(inert_grant)
    if not findings_c:
        print("SELF-TEST FAIL (c): expected an inert-grant finding, got none.", file=sys.stderr)
        ok = False
    else:
        print(f"SELF-TEST PASS (c): inert grant on a shell-less agent fired: {findings_c}")

    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the dadaia-cli skill grant from each agent's Bash tool; fail loud on drift."
    )
    parser.add_argument("--agents-dir", type=Path, default=None)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run the in-memory fixture proof instead of scanning the real tree.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    agents_dir: Path
    if args.agents_dir is not None:
        agents_dir = args.agents_dir.resolve()
    else:
        try:
            agents_dir = _resolve_default_agents_dir()
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    agents: list[tuple[str, bool, bool]] = []
    for agent_md in sorted(agents_dir.glob("*.md")):
        parsed = _parse_agent(agent_md)
        if parsed is not None:
            agents.append(parsed)

    findings = find_drift(agents)

    print(f"lint-dadaia-cli-reachability: scanned {len(agents)} agent(s) in {agents_dir}")
    if not findings:
        print("Every agent's dadaia-cli grant agrees with its Bash-capability.")
        return 0

    for name, has_bash, has_grant in findings:
        if has_bash and not has_grant:
            print(f"  [ERROR] '{name}' has Bash but no dadaia-cli grant.", file=sys.stderr)
        else:
            print(
                f"  [ERROR] '{name}' has no Bash but carries an inert dadaia-cli grant.",
                file=sys.stderr,
            )
    print(
        f"\n{len(findings)} drift finding(s) — reconcile the grant with the Bash tool.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
