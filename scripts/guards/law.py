"""Law checks: what the shipped law, scaffold and persona files say about the code and each other.

Checks read tracked files as text, JSON, INI or an AST. Where the package owns the answer (the
fixed-sections canon, the frontmatter grammar), the check imports that owner.
"""

from __future__ import annotations

import ast
import configparser
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from run import ROOT

sys.path.insert(0, str(ROOT))

from dadaia_workspace.core.fixed_sections import (  # noqa: E402
    FIXED_SECTIONS,
    extract_fixed_section,
)
from dadaia_workspace.core.frontmatter import FrontmatterError, parse  # noqa: E402

if TYPE_CHECKING:
    from run import Check, Plant, Tree

_PKG = "dadaia_workspace"
_PUBLIC = f"{_PKG}/public"
_SKILLS = f"{_PUBLIC}/skills"
_FRAGMENTS = f"{_PUBLIC}/data/fixed"
_BUG_SCHEMA = f"{_SKILLS}/dd-bug-resolution/scripts/schemas/bug-record-v1.schema.json"
_BIND_CONTRACT = "importlinter:contract:bind-resolution-seam-is-a-single-home"
_COMMANDS = f"{_PKG}/cli/commands"
_MAX_BULLET_CHARS = 150
_PERSONAS = 5
_DEFAULT_LITERAL = re.compile(r'principal: main|"--principal", "main"|else "main"')
_VERSION_MINT = re.compile(r'"tag", "--sort|\]\) \+ 1\}')
_FORBIDDEN_PHRASES = (
    ("phrase", "dd-bug-resolution/SKILL.md", "rewriting an old assert"),
    ("phrase", "dd-audit-project/PILLAR-BUGS.md", "governance_events"),
    ("phrase", "dd-backlog-definition/SKILL.md", "merge a near-duplicate"),
    ("dispatch", "dd-manager-orchestration/SKILL.md", "unit of dispatch is a job"),
)


def _package_py(tree: Tree) -> list[str]:
    return [p for p in tree.tracked(_PKG) if p.endswith(".py") and "public" not in Path(p).parts]


def _fragments(tree: Tree) -> list[str]:
    return [p for p in tree.tracked(_FRAGMENTS) if p.endswith(".md")]


def fragment_shape(tree: Tree) -> list[str]:
    """Each fixed fragment: one heading, short ``- `` bullets, one trailing newline."""
    paths, out = _fragments(tree), []
    if not paths:
        return ["shape: no fixed fragment is tracked"]
    for p in paths:
        text = tree.read(p)
        heading, *bullets = text.splitlines() or [""]
        level = "## " if Path(p).stem == "slop-law" else "### "
        if not text.endswith("\n") or text.endswith("\n\n"):
            out.append(f"shape: {p} does not end with exactly one newline")
        if not (heading.startswith(level + "Slop — ") and heading.endswith("(fixed)")):
            out.append(f"shape: {p} heading is not '{level}Slop — … (fixed)'")
        if not bullets:
            out.append(f"shape: {p} has no bullet")
        out += [
            f"shape: {p} bullet is not a '- ' line of at most {_MAX_BULLET_CHARS} chars: {b[:40]}"
            for b in bullets
            if not b.startswith("- ") or len(b) > _MAX_BULLET_CHARS
        ]
    return out


def scaffold_marker_pair(tree: Tree) -> list[str]:
    """Each memory scaffold template ends with the empty marker pair of its fixed section."""
    out = []
    for rel, sid in FIXED_SECTIONS:
        if rel == "constitution.md":
            continue
        p = f"{_PUBLIC}/scaffold/{rel}"
        if not tree.tracked(p):
            out.append(f"absent: {p} is not tracked")
            continue
        text, body = tree.read(p), extract_fixed_section(tree.read(p), sid)
        if body is None:
            out.append(f"absent: {p} carries no {sid} marker pair")
        elif body or not text.endswith(f"<!-- /dadaia:fixed {sid} -->\n"):
            out.append(f"marker: {p} does not end with the empty {sid} marker pair")
    return out


def fragment_bullet_not_restated(tree: Tree) -> list[str]:
    """No scaffold, data or template markdown outside the fragments repeats a fragment bullet."""
    bullets = {ln for p in _fragments(tree) for ln in tree.read(p).splitlines()[1:]}
    return [
        f"restated: {p}: {ln[:60]}"
        for folder in ("scaffold", "data", "templates")
        for p in tree.tracked(f"{_PUBLIC}/{folder}")
        if p.endswith(".md") and "fixed" not in Path(p).parts
        for ln in tree.read(p).splitlines()
        if ln in bullets
    ]


_SHIPPED_NAMES = f"{_SKILLS}/dd-gitflow-default/scripts/_worktree_names.py"


def gitflow_names(tree: Tree) -> list[str]:
    """Only ``core/gitflow`` spells the default branch names; the skill cuts work from integration."""
    out = [
        f"default-literal: {p}: spells a default branch name"
        for p in tree.tracked(_PKG)
        if p.endswith(".py") and _DEFAULT_LITERAL.search(tree.read(p))
    ]
    skill = tree.read(f"{_SKILLS}/dd-gitflow-default/SKILL.md")
    row = next((r for r in skill.splitlines() if r.startswith("| work `")), "").split("|")
    if len(row) < 4 or row[3].strip() != "integration":
        out.append("work-cut: the skill's work row is not cut from integration")
    return out


def live_release_reader(tree: Tree) -> list[str]:
    """One reader of the live release id; no module mints a version; the repo law names its owner."""
    out = []
    for p in _package_py(tree):
        text = tree.read(p)
        if "def live_ids" in text:
            out.append(f"live-ids: {p} defines a second live-release reader")
        if _VERSION_MINT.search(text):
            out.append(f"tag-mint: {p} lists or bumps tags")
    if "release-please owns the version" not in tree.read("AGENTS.md"):
        out.append("version-law: AGENTS.md does not say release-please owns the version")
    return out


def persona_files(tree: Tree) -> list[str]:
    """Five persona files, each ``dd-`` named, declaring its name and a numeric band, pinning no model."""
    paths = [p for p in tree.tracked(f"{_PUBLIC}/agents") if p.endswith(".md")]
    out = (
        [] if len(paths) == _PERSONAS else [f"roster: {len(paths)} persona files, not {_PERSONAS}"]
    )
    for p in paths:
        stem, parsed = Path(p).stem, parse(tree.read(p))
        if isinstance(parsed, FrontmatterError):
            out.append(f"frontmatter: {p} has no YAML mapping frontmatter")
            continue
        fm = parsed.data
        if not stem.startswith("dd-") or fm.get("name") != stem:
            out.append(f"name: {p} is not dd- named and declaring its own name")
        band = fm.get("dispatch_band")
        if not isinstance(band, int) or isinstance(band, bool):
            out.append(f"band: {p} dispatch_band is {band!r}, not numeric")
        out += [f"pinned: {p} pins {k}" for k in ("model", "effort") if k in fm]
        if stem == "dd-researcher" and fm.get("skills"):
            out.append(f"researcher-skills: {p} declares skills")
    return out


def release_validity_in_script(tree: Tree) -> list[str]:
    """No package module decides release-state validity; the release script does."""
    return [
        f"outside-script: {p}"
        for p in _package_py(tree)
        if '"releases/release-state-v1"' in (t := tree.read(p)) or "parse_release_state" in t
    ]


def bind_contract_covers_verbs(tree: Tree) -> list[str]:
    """Every verb module is a source module of the bind-resolution import-linter contract."""
    cfg = configparser.ConfigParser()
    cfg.read_string(tree.read("setup.cfg"))
    modules = cfg.get(_BIND_CONTRACT, "source_modules", fallback="").split()
    verbs = [
        Path(p).stem
        for p in tree.tracked(_COMMANDS)
        if p.endswith(".py")
        and Path(p).parent.as_posix() == _COMMANDS
        and p[len(_COMMANDS) + 1] != "_"
    ]
    out = [
        f"uncovered: verb {v} is no source of the bind-resolution contract"
        for v in verbs
        if not any(f"{_PKG}.cli.commands.{v}".startswith(m) for m in modules)
    ]
    return out or ([] if verbs else ["uncovered: no verb module is tracked"])


def os_name_via_platform(tree: Tree) -> list[str]:
    """No package module reads ``os.name``."""
    return [
        f"os-name: {p}:{node.lineno}"
        for p in _package_py(tree)
        for node in ast.walk(ast.parse(tree.read(p)))
        if isinstance(node, ast.Attribute)
        and node.attr == "name"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    ]


def skill_forbidden_phrases(tree: Tree) -> list[str]:
    """A skill prescribes no act its laws forbid, and dispatches a task never a job."""
    return [
        f"{rule}: {skill} says {phrase!r}"
        for rule, skill, phrase in _FORBIDDEN_PHRASES
        if phrase in tree.read(f"{_SKILLS}/{skill}")
    ]


def cli_fix_help_derived(tree: Tree) -> list[str]:
    """The doctor's ``--fix`` help is the registry's derived text, not a hand-written list."""
    src = tree.read(f"{_COMMANDS}/doctor.py")
    out = [] if "render_fix_help()" in src else ["derived: --fix help is not render_fix_help()"]
    if "TREE-3: render missing memory HTML" in src:
        out.append("hand-written: --fix help carries the stale TREE-3 line")
    return out


def bug_law_points_at_mutability(tree: Tree) -> list[str]:
    """The scaffold bugs law names ``x-mutability`` and lists no schema fields."""
    properties = set(json.loads(tree.read(_BUG_SCHEMA))["properties"])
    law = tree.read(f"{_PUBLIC}/scaffold/bugs/AGENTS.md")
    out = [] if "x-mutability" in law else ["pointer: the bugs law does not name x-mutability"]
    out += [
        f"field-list: {ln[:60]}"
        for ln in law.splitlines()
        if len(properties & set(ln.split("`"))) >= 3
    ]
    return out


def surface_names_no_library_fact(tree: Tree) -> list[str]:
    """The bug schema's ``surface`` is a free non-empty string naming no library package."""
    surface = json.loads(tree.read(_BUG_SCHEMA))["properties"]["surface"]
    out = []
    if "enum" in surface or "x-enum-append" in surface:
        out.append("enum: surface lists library values")
    if surface.get("type") != "string" or surface.get("minLength") != 1:
        out.append("type: surface is not a non-empty string")
    if "dadaia_workspace" in surface.get("description", ""):
        out.append("description: surface names the library package")
    return out


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def _pair(sid: str, body: str = "") -> str:
    return f"<!-- dadaia:fixed {sid} -->\n{body}<!-- /dadaia:fixed {sid} -->\n"


_PERSONA = "---\nname: {}\ndispatch_band: 2\n---\nbody\n"
_PERSONA_NAMES = ("dd-a", "dd-b", "dd-c", "dd-d", "dd-researcher")
_COMMAND_STEMS = ("a", "_x")
_BUG_SCHEMA_DOC = {
    "properties": {
        "surface": {"type": "string", "minLength": 1, "description": "a directory"},
        **{k: {} for k in ("a", "b", "c")},
    }
}


def CONTROL(root: Path) -> None:
    """Every check green on a minimal healthy tree; violations only in an ignored file."""
    files = {
        ".gitignore": "scratch/\n",
        "AGENTS.md": "release-please owns the version\n",
        "scratch/dadaia_workspace/m.py": "import os\nx = os.name\n",
        f"{_FRAGMENTS}/slop-law.md": "## Slop — law (fixed)\n- a law bullet\n",
        f"{_FRAGMENTS}/slop-code.md": "### Slop — code (fixed)\n- a code bullet\n",
        **{
            f"{_PUBLIC}/scaffold/{rel}": f"# T\n\n{_pair(sid)}"
            for rel, sid in FIXED_SECTIONS
            if rel != "constitution.md"
        },
        f"{_PUBLIC}/data/AGENTS.md": "- unrelated\n",
        f"{_PUBLIC}/templates/t.md": "- unrelated\n",
        f"{_PKG}/m.py": "import os\n",
        f"{_SKILLS}/dd-gitflow-default/SKILL.md": "| work `w` | Yes | integration | jobs |\n",
        **{f"{_SKILLS}/{s}": "ok\n" for _, s, _ in _FORBIDDEN_PHRASES},
        **{f"{_PUBLIC}/agents/{n}.md": _PERSONA.format(n) for n in _PERSONA_NAMES},
        "setup.cfg": f"[{_BIND_CONTRACT}]\nsource_modules =\n    {_PKG}.cli.commands.a\n    {_PKG}.cli.commands.doctor\n",
        **{f"{_COMMANDS}/{s}.py": "" for s in _COMMAND_STEMS},
        f"{_COMMANDS}/doctor.py": "help = render_fix_help()\n",
        _BUG_SCHEMA: json.dumps(_BUG_SCHEMA_DOC),
        f"{_PUBLIC}/scaffold/bugs/AGENTS.md": "Each class is its `x-mutability`.\n",
    }
    for rel, text in files.items():
        _write(root, rel, text)


def _plant(rel: str, text: str) -> Plant:
    """CONTROL with *rel* overwritten by *text*."""

    def plant(root: Path) -> None:
        CONTROL(root)
        _write(root, rel, text)

    return plant


def _skill(skill: str, text: str) -> Plant:
    return _plant(f"{_SKILLS}/{skill}", text)


def _persona(name: str, text: str) -> Plant:
    return _plant(f"{_PUBLIC}/agents/{name}.md", text)


def _schema(**surface: object) -> Plant:
    doc = {"properties": {**_BUG_SCHEMA_DOC["properties"], "surface": surface}}
    return _plant(_BUG_SCHEMA, json.dumps(doc))


_SURFACE = {"type": "string", "minLength": 1}
_MODULE = f"{_PKG}/m.py"

CHECKS: dict[str, Check] = {
    "law-fragment-shape": (
        fragment_shape,
        {
            "shape": _plant(
                f"{_FRAGMENTS}/slop-code.md", "### Slop — code (fixed)\n- " + "x" * 200 + "\n"
            )
        },
    ),
    "law-scaffold-marker-pair": (
        scaffold_marker_pair,
        {
            "marker": _plant(
                f"{_PUBLIC}/scaffold/memory/QUALITY.md", f"# Q\n\n{_pair('slop-tests', 'body\n')}"
            ),
            "absent": _plant(f"{_PUBLIC}/scaffold/memory/QUALITY.md", "# Q\n"),
        },
    ),
    "law-fragment-bullet-not-restated": (
        fragment_bullet_not_restated,
        {"restated": _plant(f"{_PUBLIC}/data/AGENTS.md", "- a code bullet\n")},
    ),
    "law-gitflow-names": (
        gitflow_names,
        {
            "default-literal": _plant(_MODULE, "x = 'principal: main'\n"),
            f"default-literal: {_SHIPPED_NAMES}": _plant(_SHIPPED_NAMES, "x = 'principal: main'\n"),
            "work-cut": _skill(
                "dd-gitflow-default/SKILL.md", "| work `w` | Yes | develop | jobs |\n"
            ),
        },
    ),
    "law-live-release-reader": (
        live_release_reader,
        {
            "live-ids": _plant(_MODULE, "def live_ids(): ...\n"),
            "tag-mint": _plant(_MODULE, 'run(["git", "tag", "--sort=-v:refname"])\n'),
            "version-law": _plant("AGENTS.md", "no owner\n"),
        },
    ),
    "law-persona-files": (
        persona_files,
        {
            "roster": _persona("dd-extra", _PERSONA.format("dd-extra")),
            "name": _persona("dd-a", _PERSONA.format("other")),
            "frontmatter": _persona("dd-a", "no frontmatter\n"),
            "band": _persona("dd-a", "---\nname: dd-a\ndispatch_band: high\n---\n"),
            "pinned": _persona("dd-a", "---\nname: dd-a\ndispatch_band: 2\nmodel: m\n---\n"),
            "researcher-skills": _persona(
                "dd-researcher", "---\nname: dd-researcher\ndispatch_band: 2\nskills: [x]\n---\n"
            ),
        },
    ),
    "law-release-validity-in-script": (
        release_validity_in_script,
        {"outside-script": _plant(_MODULE, "parse_release_state(doc)\n")},
    ),
    "law-bind-contract-covers-verbs": (
        bind_contract_covers_verbs,
        {"uncovered": _plant(f"{_COMMANDS}/b.py", "")},
    ),
    "law-os-name-via-platform": (
        os_name_via_platform,
        {"os-name": _plant(_MODULE, "import os\nx = os.name\n")},
    ),
    "law-skill-forbidden-phrases": (
        skill_forbidden_phrases,
        {
            "phrase": _skill("dd-backlog-definition/SKILL.md", "merge a near-duplicate\n"),
            "dispatch": _skill("dd-manager-orchestration/SKILL.md", "unit of dispatch is a job\n"),
        },
    ),
    "law-cli-fix-help-derived": (
        cli_fix_help_derived,
        {
            "derived": _plant(f"{_COMMANDS}/doctor.py", "help = 'x'\n"),
            "hand-written": _plant(
                f"{_COMMANDS}/doctor.py",
                "help = render_fix_help() + 'TREE-3: render missing memory HTML'\n",
            ),
        },
    ),
    "law-bug-law-points-at-mutability": (
        bug_law_points_at_mutability,
        {
            "pointer": _plant(f"{_PUBLIC}/scaffold/bugs/AGENTS.md", "no pointer\n"),
            "field-list": _plant(
                f"{_PUBLIC}/scaffold/bugs/AGENTS.md", "`x-mutability` lists `a` `b` `c`\n"
            ),
        },
    ),
    "law-surface-names-no-library-fact": (
        surface_names_no_library_fact,
        {
            "enum": _schema(**_SURFACE, enum=["core"]),
            "type": _schema(type="integer"),
            "description": _schema(**_SURFACE, description="a dadaia_workspace layer"),
        },
    ),
}
