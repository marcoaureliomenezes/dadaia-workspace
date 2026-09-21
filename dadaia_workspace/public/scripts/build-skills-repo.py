#!/usr/bin/env python3
"""Render the standalone Agent Skills repository (`build-skills-repo.py <out-dir>`).

A skill's bytes exist in one place — `dadaia_workspace/public/skills/` — and the prose
in another: `specs/memory/`. Everything written here derives from those two, so the
published repository cannot drift from the library that owns it; an installed wheel,
carrying no `specs/`, refuses to build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "dadaia_workspace" / "public" / "skills"
MEMORY = REPO_ROOT / "specs" / "memory"
DISTRIBUTION_ATOM = MEMORY / "product" / "distribution" / "public-asset-distribution.md"
ENTITIES_ATOM = MEMORY / "product" / "agents" / "agentic-entities.md"
OWNER = "marcoaureliomenezes"
REPO_URL = f"https://github.com/{OWNER}/dadaia-skills"
DESCRIPTION = "The dadaia agent skills: spec-driven development, bug resolution, review, design."

README = """# dadaia-skills

{description}

## Install

```
# the skills CLI
npx skills add {owner}/dadaia-skills

# Claude Code, as a plugin marketplace
/plugin marketplace add {owner}/dadaia-skills
/plugin install dadaia-skills@dadaia-skills

# Codex — clone, and let .agents/skills be read natively
git clone {repo}.git .agents/dadaia-skills && ln -s dadaia-skills/skills .agents/skills
```

## Skills

<!-- derived-from: agentic-entities sha256:{entities} -->
<!-- derived-from: public-asset-distribution sha256:{distribution} -->

| Skill | What it does |
| --- | --- |
{table}

These skills are standalone. Inside a workspace created by `dadaia-workspace` they also
drive the spec-driven lifecycle — specs, backlog, bugs, releases — with the ledger
scripts, the projection chain and the governance hooks that ship with it:
<https://github.com/{owner}/dadaia-workspace>.

MIT licensed — see `LICENSE`.
"""


def atom_hash(path: Path) -> str:
    """An atom's hash over LF bytes, so a CRLF checkout pins the same twelve chars."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def summary(skill_md: Path) -> str:
    """The first sentence of a skill's `description`, read without a YAML dependency —
    the folded form is the run of indented lines under the key."""
    block = re.search(r"^description:(.*(?:\n  +.*)*)", skill_md.read_text(encoding="utf-8"), re.M)
    text = " ".join(block.group(1).lstrip().lstrip(">|").split()) if block else ""
    return text.split(". ")[0].rstrip(".") + "." if text else ""


def readme(skills: list[str]) -> str:
    return README.format(
        description=DESCRIPTION,
        owner=OWNER,
        repo=REPO_URL,
        entities=atom_hash(ENTITIES_ATOM),
        distribution=atom_hash(DISTRIBUTION_ATOM),
        table="\n".join(f"| `{n}` | {summary(SKILLS_DIR / n / 'SKILL.md')} |" for n in skills),
    )


def manifests() -> dict[str, object]:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    if match is None:
        raise SystemExit('fix: pyproject.toml carries no `version = "…"` line to render')
    release = match.group(1)
    plugin = {
        "name": "dadaia-skills",
        "source": "./",
        "description": DESCRIPTION,
        "version": release,
        "license": "MIT",
        "repository": REPO_URL,
        "skills": ["./skills/"],
    }
    return {
        ".claude-plugin/marketplace.json": {
            "name": "dadaia-skills",
            "owner": {"name": OWNER},
            "description": DESCRIPTION,
            "plugins": [plugin],
        },
        ".claude-plugin/plugin.json": {
            "name": "dadaia-skills",
            "description": DESCRIPTION,
            "version": release,
            "author": {"name": "Marco Menezes"},
        },
    }


def build(out: Path) -> None:
    """Render into *out*; the renderer owns every managed subtree, so a re-run converges."""
    roster: list[str] = json.loads(
        (SKILLS_DIR.parent / "entities" / "behavior-map.json").read_text(encoding="utf-8")
    )["standalone_skills"]
    for managed in ("skills", ".claude-plugin"):
        shutil.rmtree(out / managed, ignore_errors=True)
        (out / managed).mkdir(parents=True, exist_ok=True)
    for name in roster:
        shutil.copytree(SKILLS_DIR / name, out / "skills" / name)
    shutil.copyfile(REPO_ROOT / "LICENSE", out / "LICENSE")
    (out / "README.md").write_text(readme(roster), encoding="utf-8")
    for relative, payload in manifests().items():
        (out / relative).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the standalone skills repository.")
    parser.add_argument("out", type=Path, help="directory to render into (created if absent)")
    args = parser.parse_args(argv)
    if not SKILLS_DIR.is_dir() or not MEMORY.is_dir():
        print(f"fix: run this from a dadaia-workspace checkout — {REPO_ROOT} carries no sources")
        return 1
    build(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
