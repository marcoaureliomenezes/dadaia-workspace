#!/usr/bin/env python3
"""Two mechanical, fail-loud reachability rules over the public surface.

1. The `dd-cli-library` grant is derived from each agent's `Bash` tool: shell-capable
   agents carry it, shell-less agents would find it inert and must not.
2. Every skill-script citation under `public/**/*.md` resolves — the script exists and
   the cited verb is a real subcommand, in the long
   `python3 .agents/skills/<skill>/scripts/<x>.py <verb>` form and in the `<ALIAS>_PY
   <verb>` short form a scoped `AGENTS.md` defines for itself.

Usage:
    lint-dadaia-cli-reachability.py [--agents-dir <path>] [--public-dir <path>] [--self-test]

Exit codes:
    0 — every grant matches its Bash-capability and every script citation resolves
        (or --self-test passed)
    1 — at least one grant disagrees, or at least one citation names a dead target
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

sys.dont_write_bytecode = True

# The delimiter block alone, reused from the one canonical parser (never a second
# frontmatter parser, K10) — zero third-party deps at import time (yaml is deferred
# inside `parse()`), so this stays safe for a bare-interpreter invocation.
from dadaia_workspace.core.frontmatter import FRONTMATTER_RE  # noqa: E402

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
    fm_match = FRONTMATTER_RE.match(content)
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
    return name_m.group(1), "Bash" in tools, "dd-cli-library" in skills


def find_drift(agents: list[tuple[str, bool, bool]]) -> list[tuple[str, bool, bool]]:
    """Return (name, has_bash, has_grant) triples where grant disagrees with Bash-capability."""
    return [
        (name, has_bash, has_grant) for name, has_bash, has_grant in agents if has_bash != has_grant
    ]


#: Citations are read inside a backticked span only, so the prose DEFINING an alias
#: ("`RELEASE_PY` below is `python3 …`") never reads as a citation of the next word.
_BACKTICK_SPAN_RE = re.compile(r"`([^`\n]+)`")
_SCRIPT_RE = r"\.agents/skills/([a-z0-9-]+)/scripts/([a-z_]+\.py)"
_ALIAS_DEF_RE = re.compile(rf"`([A-Z][A-Z0-9_]*_PY)`[^\n]*?`?python3 {_SCRIPT_RE}")
_CITATION_RE = re.compile(rf"^(?:python3 {_SCRIPT_RE}|([A-Z][A-Z0-9_]*_PY)) ([a-z][a-z-]*)\b")

Citations = dict[tuple[str, str, str], list[str]]


def script_citations(text: str) -> list[tuple[str, str, str]]:
    """Every (skill, script, verb) *text* cites; an alias resolves from that same file's
    own definition, never from a global vocabulary."""
    aliases = {name: (skill, script) for name, skill, script in _ALIAS_DEF_RE.findall(text)}
    found: list[tuple[str, str, str]] = []
    for span in _BACKTICK_SPAN_RE.findall(text):
        match = _CITATION_RE.match(span)
        if match is None:
            continue
        skill, script, alias, verb = match.groups()
        if alias is not None:
            if alias not in aliases:
                continue
            skill, script = aliases[alias]
        found.append((skill, script, verb))
    return found


def collect_citations(public_dir: Path) -> Citations:
    """Every citation under *public_dir*, mapped to the files making it."""
    citations: Citations = {}
    for md_path in sorted(public_dir.rglob("*.md")):
        rel = md_path.relative_to(public_dir).as_posix()
        for citation in script_citations(md_path.read_text(encoding="utf-8")):
            citations.setdefault(citation, []).append(rel)
    return citations


def _verb_is_reachable(script_path: Path, verb: str) -> bool:
    """True when ``<script> <verb> --help`` exits 0 — the script's own argparse is the
    one authority on its verb set."""
    argv = [sys.executable, str(script_path), verb, "--help"]
    return subprocess.run(argv, capture_output=True, text=True).returncode == 0  # noqa: S603


def find_dead_script_citations(
    citations: Citations, *, skills_dir: Path, reachable: Callable[[Path, str], bool]
) -> list[str]:
    """One finding per cited (skill, script, verb) that does not run — a missing script
    and an unknown verb are the same failure, so they are one rule."""
    return [
        f"{', '.join(sorted(set(sources)))}: `{skill}/scripts/{script} {verb}` does not run"
        for (skill, script, verb), sources in sorted(citations.items())
        if not reachable(skills_dir / skill / "scripts" / script, verb)
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

    # (d) both halves of a dead citation — a script that does not exist and a real
    # script cited with a verb it does not have — fire against the real reachability.
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    existing = next(skills_dir.glob("*/scripts/[a-z]*.py"), None)
    fixtures: Citations = {("dd-fixture", "fixture.py", "append"): ["fixture/AGENTS.md"]}
    if existing is not None:
        fixtures[(existing.parts[-3], existing.name, "nosuchverb")] = ["fixture/AGENTS.md"]
    dead = find_dead_script_citations(fixtures, skills_dir=skills_dir, reachable=_verb_is_reachable)
    if len(dead) != len(fixtures):
        print(
            f"SELF-TEST FAIL (d): expected {len(fixtures)} finding(s), got {dead}", file=sys.stderr
        )
        ok = False
    else:
        print(f"SELF-TEST PASS (d): every dead citation fired: {dead}")

    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the dd-cli-library skill grant from each agent's Bash tool; fail loud on drift."
    )
    parser.add_argument("--agents-dir", type=Path, default=None)
    parser.add_argument("--public-dir", type=Path, default=None)
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
    public_dir = args.public_dir.resolve() if args.public_dir is not None else agents_dir.parent
    citations = collect_citations(public_dir)
    dead_citations = find_dead_script_citations(
        citations, skills_dir=public_dir / "skills", reachable=_verb_is_reachable
    )

    print(
        f"lint-dadaia-cli-reachability: scanned {len(agents)} agent(s) in {agents_dir} "
        f"and {len(citations)} script citation(s) under {public_dir}"
    )
    for citation_finding in dead_citations:
        print(f"  [ERROR] {citation_finding}", file=sys.stderr)
    if not findings and not dead_citations:
        print(
            "Every agent's dd-cli-library grant agrees with its Bash-capability and "
            "every skill-script citation resolves."
        )
        return 0

    for name, has_bash, has_grant in findings:
        if has_bash and not has_grant:
            print(f"  [ERROR] '{name}' has Bash but no dd-cli-library grant.", file=sys.stderr)
        else:
            print(
                f"  [ERROR] '{name}' has no Bash but carries an inert dd-cli-library grant.",
                file=sys.stderr,
            )
    total = len(findings) + len(dead_citations)
    print(
        f"\n{total} finding(s) — reconcile each grant with its Bash tool and each "
        "citation with the script it names.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
