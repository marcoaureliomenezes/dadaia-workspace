"""Workspace checks: the zone registry, the law tables, the single homes and the specs-tree
rules the package source must keep.

Checks read tracked files as text, JSON, TOML or an AST. Where only the package's own decider
can answer (the canonical sets, the template renderer, the shipped-history reader, the specs
doctor, the harness registry), the check imports that decider and runs it over the tree.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
import typing
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from run import ROOT

sys.path.insert(0, str(ROOT))

from dadaia_workspace.cli.main import app  # noqa: E402
from dadaia_workspace.core.gitflow import Role  # noqa: E402
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES  # noqa: E402
from dadaia_workspace.core.template_history import was_shipped  # noqa: E402
from dadaia_workspace.core.workspace_layout import (  # noqa: E402
    CANON_ROOT_MEMBERS,
    DADAIA_ZONES,
    ROOT_ALLOWED_DIRS,
    ROOT_ALLOWED_FILES,
    STATES_CANON,
    render_registry_tables,
    root_entries_display,
    specs_canon_table_rows,
    zone_names,
)
from dadaia_workspace.features.specs.doctor import SpecsDoctor  # noqa: E402
from dadaia_workspace.features.specs.doctor_common import RELEASE_ARTIFACTS  # noqa: E402

if TYPE_CHECKING:
    from run import Check, Plant, Tree

_PKG = "dadaia_workspace"
_PUBLIC = f"{_PKG}/public"
_SKILLS = f"{_PUBLIC}/skills"
_PHASE_SCHEMA = f"{_SKILLS}/dd-release-implementation/scripts/schemas/release-state-v1.schema.json"
_DISPOSITION_SCHEMA = f"{_SKILLS}/dd-backlog-definition/scripts/schemas/histo-record-v1.schema.json"
_RELEASE_SCRIPT = ROOT / _SKILLS / "dd-release-implementation/scripts/release.py"
_LAYOUT = f"{_PKG}/core/workspace_layout.py"
_COMMANDS = f"{_PKG}/cli/commands"
_PRIVACY = f"{_SKILLS}/dd-bug-resolution/scripts/_privacy.py"
_REDACT = f"{_PKG}/cli/redact.py"
_WITNESS = "tests/public/skills/dd_bug_resolution/scripts/test__ledger.py"
_BACKLOG_SCHEMA = f"{_SKILLS}/dd-backlog-definition/scripts/_backlog_schema.py"
_QUICKSTART = ("docs/quickstart.md", "tests/fixtures/quickstart.md")
_SECOND_LISTS = {_BACKLOG_SCHEMA: f"parity:{_WITNESS}"}
_RETIRED_ZONES = ("academy", "logs", "runs", "scripts", "dev-report", "runtime")
_SET_HOME = {
    "phase": f"{_SKILLS}/dd-release-implementation/scripts/_release_schema.py",
    "ledger-disposition": _DISPOSITION_SCHEMA,
    "trio": f"{_PKG}/features/specs/doctor_common.py",
    "gitflow-role": f"{_PKG}/core/gitflow.py",
}
_SCAFFOLD_LAW = ("audits/AGENTS.md", "memory/AGENTS.md", "memory/QUALITY.md")
_SCAFFOLD_AREAS = ("memory", "releases", "backlog", "bugs", "audits", "ADRs")
_PUBLISH_FILES = (
    f"{_PKG}/features/spec_context/service.py",
    f"{_PKG}/features/chokepoints/branch_policy.py",
)
_REWRITE_VERBS = ("-f", "reset", "rebase", "--force", "--delete")
_HARNESS_FILES = (
    f"{_PKG}/infrastructure/projection_rules.py",
    f"{_PKG}/infrastructure/agent_transcodes.py",
    f"{_PKG}/features/workspace/service.py",
    f"{_COMMANDS}/init.py",
)
_OS_CLASSIFIERS = (
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
)
_SEAM = frozenset(
    {"resolve_specs_dir_for_cli", "resolve_context_for_cli", "resolve_context_specs_dir_for_cli"}
)
_FILTER_ONLY = frozenset({"container.build_workflow_handoff_doctor"})
_RESOLVER_PARAMS = ("context", "specs_dir")


def _python(tree: Tree) -> list[str]:
    return [p for p in tree.tracked(_PKG) if p.endswith(".py")]


def _ast(tree: Tree, rel: str) -> ast.Module:
    return ast.parse(tree.read(rel))


def _enum(tree: Tree, schema: str, field: str) -> frozenset[str]:
    return frozenset(json.loads(tree.read(schema))["properties"][field]["enum"])


def _canonical_sets(tree: Tree) -> dict[str, frozenset[str]]:
    return {
        "zone": zone_names(),
        "root": ROOT_ALLOWED_DIRS | ROOT_ALLOWED_FILES,
        "specs-canon": CANON_ROOT_MEMBERS,
        "phase": _enum(tree, _PHASE_SCHEMA, "phase"),
        "ledger-disposition": _enum(tree, _DISPOSITION_SCHEMA, "disposition"),
        "trio": frozenset(RELEASE_ARTIFACTS),
        "gitflow-role": frozenset(typing.get_args(Role)),
    }


def _second_list_hits(
    module: ast.Module, sets: dict[str, frozenset[str]], home: frozenset[str]
) -> list[str]:
    retired = {f".dadaia/{name}" for name in _RETIRED_ZONES}
    hits = []
    for node in ast.walk(module):
        if isinstance(node, ast.Set | ast.Tuple | ast.List):
            for label, canonical in sets.items():
                found = [
                    e.value
                    for e in node.elts
                    if isinstance(e, ast.Constant)
                    and isinstance(e.value, str)
                    and e.value.rstrip("/") in canonical
                ]
                if label not in home and len(found) >= 3:
                    hits.append(f"second-list: {node.lineno}: literal holds {label} names {found}")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.rstrip("/") in retired
        ):
            hits.append(f"retired-zone: {node.lineno}: path {node.value!r}")
    return hits


def zone_registry_only_list(tree: Tree) -> list[str]:
    """No package literal restates a canonical set or names a retired zone, outside the registry,
    each set's home and the allowance whose witness test file exists and whose literal remains."""
    sets, out, listed = _canonical_sets(tree), [], set()
    for rel in _python(tree):
        if rel == _LAYOUT:
            continue
        home = frozenset(label for label, module in _SET_HOME.items() if module == rel)
        hits = _second_list_hits(_ast(tree, rel), sets, home)
        if hits and rel in _SECOND_LISTS:
            listed.add(rel)
        else:
            out += [f"{hit.split(': ', 1)[0]}: {rel}:{hit.split(': ', 1)[1]}" for hit in hits]
    out += [f"stale-allowance: {rel} holds no second list" for rel in _SECOND_LISTS.keys() - listed]
    return out + [
        f"witness: {rel} -> {value!r} names no test file"
        for rel, value in _SECOND_LISTS.items()
        if not tree.tracked(value.removeprefix("parity:"))
    ]


def _restated(text: str, sets: dict[str, frozenset[str]]) -> list[str]:
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        tokens = set(re.findall(r"[A-Za-z0-9_.\-]+", line))
        for label, canonical in sets.items():
            found = len(tokens & canonical)
            if found == len(canonical) if len(canonical) <= 4 else found * 2 >= len(canonical):
                hits.append(f"{number}:{label}")
    return hits


def law_restates_no_set(tree: Tree) -> list[str]:
    """No ``public`` law markdown line spells a whole small canonical set, or half a larger one."""
    sets = _canonical_sets(tree)
    return [
        f"restated: {p}:{hit}"
        for p in tree.tracked(_PUBLIC)
        if p.endswith(".md") and "_archive" not in Path(p).parts
        for hit in _restated(tree.read(p), sets)
    ]


def _tables(text: str, columns: set[str]) -> list[list[dict[str, str]]]:
    """Every pipe table of *text* whose header holds *columns*, as header-keyed rows."""
    tables: list[list[dict[str, str]]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            tables.append([])
        elif not all(set(c) <= set("-: ") for c in cells):
            tables[-1].append(dict(zip(header, cells, strict=False)))
    return [t for t in tables if t and columns <= set(t[0])]


def _bare(cell: str) -> str:
    return cell.strip("`").rstrip("/")


def law_tables_equal_registry(tree: Tree) -> list[str]:
    """The rendered law sources hold the registry's zone, states, specs-canon tables and root line."""

    def rendered(rel: str) -> str:
        return render_registry_tables(tree.read(f"{_PUBLIC}/{rel}"))

    out = []
    zone = _tables(rendered("data/dadaia-AGENTS.md"), {"class", "ttl", "creator"})
    expected_zones = [
        (
            z.name,
            z.cls.value,
            "never" if z.ttl_seconds is None else str(z.ttl_seconds),
            z.creator.value,
        )
        for z in DADAIA_ZONES
    ]
    if len(zone) != 1:
        out.append("zones: no single rendered zone table")
    else:
        name = next(k for k in zone[0][0] if k in {"zone", "folder"})
        got = [(_bare(r[name]), r["class"], r["ttl"], r["creator"]) for r in zone[0]]
        out += [] if got == expected_zones else ["zones: the rendered table is not the registry"]
    states = [t for t in _tables(rendered("data/states-AGENTS.md"), set())]
    if STATES_CANON not in [{_bare(next(iter(r.values()))) for r in t} for t in states]:
        out.append("states: no rendered table is the states canon")
    canon = _tables(rendered("templates/specs-AGENTS.md"), {"area", "members"})
    rows = [("root" if p == "" else p, m) for p, m in specs_canon_table_rows()]
    if len(canon) != 1 or [(_bare(r["area"]), r["members"].strip("`")) for r in canon[0]] != rows:
        out.append("specs-canon: the rendered table is not the registry")
    if f"- Root holds only: `{root_entries_display()}`" not in rendered("data/AGENTS.md"):
        out.append("root: the rendered root line is not the registry")
    return out


def shipped_history_records_law(tree: Tree) -> list[str]:
    """The specs law template and every scaffold area law match a version recorded as shipped."""
    templates = tree.root / _PUBLIC / "templates"
    law = {"specs-AGENTS.md": templates / "specs-AGENTS.md"} | {
        f"scaffold/{a}/AGENTS.md": tree.root / _PUBLIC / "scaffold" / a / "AGENTS.md"
        for a in _SCAFFOLD_AREAS
    }
    return [
        f"unrecorded: {name} matches no shipped version"
        for name, path in law.items()
        if not was_shipped(path.read_text(encoding="utf-8"), name, templates)
    ]


def scaffold_area_law(tree: Tree) -> list[str]:
    """The source scaffold carries the area law files a specs tree needs."""
    return [
        f"missing: scaffold/{rel}"
        for rel in _SCAFFOLD_LAW
        if not tree.tracked(f"{_PUBLIC}/scaffold/{rel}")
    ]


def specs_law_canonical(tree: Tree) -> list[str]:
    """``specs/AGENTS.md`` is tracked and the specs doctor finds no drift in it."""
    if not tree.tracked("specs/AGENTS.md"):
        return ["untracked: specs/AGENTS.md is not tracked"]
    issues = SpecsDoctor(tree.root / "specs", public_dir=tree.root / _PUBLIC).check()
    return [
        f"drift: {i.code} {i.message}"
        for i in issues
        if i.code in ("TREE-5", "MEM-DRIFT-2") and "specs/AGENTS.md" in i.message
    ]


def release_tree_checks_clean(tree: Tree) -> list[str]:
    """``release.py check`` exits 0 over the tree's own ``specs/``."""
    done = subprocess.run(
        [sys.executable, str(_RELEASE_SCRIPT), "check", "--specs", str(tree.root / "specs")],
        capture_output=True,
        encoding="utf-8",
        text=True,
        check=False,
    )
    return [f"red: release.py check exit {done.returncode}: {done.stdout[:200]}"] * bool(
        done.returncode
    )


def single_homes(tree: Tree) -> list[str]:
    """One mask, one redactor builder, no ``gc_check`` and no ``WORKSPACE_ROOT`` read in the package."""
    sources = {p: tree.read(p) for p in _python(tree)}
    masks = sorted(p for p, t in sources.items() if "[0]}…{" in t)
    builders = sorted(p for p, t in sources.items() if "ContextRedactor(" in t)
    out = [f"mask: {p} is a mask definition outside {_PRIVACY}" for p in masks if p != _PRIVACY]
    out += [] if _PRIVACY in masks else [f"mask-home: {_PRIVACY} defines no mask"]
    out += [f"redactor: {p} builds a ContextRedactor" for p in builders if p != _REDACT]
    out += [] if _REDACT in builders else [f"redactor-home: {_REDACT} builds no ContextRedactor"]
    out += [f"gc-check: {p} names gc_check" for p, t in sources.items() if "gc_check" in t]
    return out + [
        f"root-env: {p}:{n.lineno}"
        for p in sources
        for n in ast.walk(_ast(tree, p))
        if isinstance(n, ast.Constant) and n.value == "WORKSPACE_ROOT"
    ]


def publish_never_rewrites(tree: Tree) -> list[str]:
    """The publish and branch-policy code holds no rewrite, force or delete string."""
    return [
        f"rewrite: {rel} carries {n.value!r}"
        for rel in _PUBLISH_FILES
        for n in ast.walk(_ast(tree, rel))
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and (n.value in _REWRITE_VERBS or "--republish" in n.value)
    ]


def harness_names_in_registry_only(tree: Tree) -> list[str]:
    """The projection table, transcodes, workspace service and ``init`` spell no harness name."""
    return [
        f"harness-literal: {rel} names {name!r}"
        for rel in _HARNESS_FILES
        for name in L1_ENTRY_HARNESSES
        if f'"{name}"' in tree.read(rel) or f"'{name}'" in tree.read(rel)
    ]


def os_classifiers(tree: Tree) -> list[str]:
    """``pyproject.toml`` declares Linux, macOS and Windows, never ``OS Independent``."""
    found = tomllib.loads(tree.read("pyproject.toml"))["tool"]["poetry"].get("classifiers", [])
    out = [f"missing: classifier {c!r}" for c in _OS_CLASSIFIERS if c not in found]
    return out + (
        ["over-broad: OS Independent"] if "Operating System :: OS Independent" in found else []
    )


def quickstart_fixture_is_the_doc(tree: Tree) -> list[str]:
    """The e2e's quickstart fixture is byte-equal to ``docs/quickstart.md``."""
    doc, fixture = _QUICKSTART
    return [] if tree.read(doc) == tree.read(fixture) else [f"stale: {fixture} differs from {doc}"]


def _taint(fn: ast.FunctionDef, seed: str) -> set[str]:
    """Local names transitively assigned from *seed* inside *fn*."""
    tainted, grown = {seed}, True
    while grown:
        before = len(tainted)
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Assign | ast.AnnAssign)
                and node.value is not None
                and {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)} & tainted
            ):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                tainted |= {t.id for t in targets if isinstance(t, ast.Name)}
        grown = len(tainted) > before
    return tainted


def _callee(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if (
        isinstance(f, ast.Attribute)
        and isinstance(f.value, ast.Name)
        and f.value.id == "container"
        and f.attr.startswith(("build_", "resolve_"))
    ):
        return f"container.{f.attr}"
    return None


def _reaches_seam(defs: dict[str, ast.FunctionDef], func: str, param: str) -> bool:
    """*param* of *func* flows by name into a seam call, directly or via module-local helpers."""
    seen: set[tuple[str, str]] = set()

    def explore(name: str, seed: str) -> bool:
        if (name, seed) in seen or name not in defs:
            return False
        seen.add((name, seed))
        fn, tainted = defs[name], _taint(defs[name], seed)
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
            callee = _callee(call)
            if callee is None or callee in _FILTER_ONLY:
                continue
            passed = [*call.args, *(kw.value for kw in call.keywords)]
            if (callee in _SEAM or callee.startswith("container.")) and any(
                isinstance(a, ast.Name) and a.id in tainted for a in passed
            ):
                return True
            helper = defs.get(callee)
            if helper is None or callee == name:
                continue
            params = [a.arg for a in helper.args.args + helper.args.kwonlyargs]
            hops = [
                params[i]
                for i, a in enumerate(call.args)
                if i < len(params) and isinstance(a, ast.Name) and a.id in tainted
            ] + [
                kw.arg
                for kw in call.keywords
                if kw.arg in params and isinstance(kw.value, ast.Name) and kw.value.id in tainted
            ]
            if any(explore(callee, h) for h in hops):
                return True
        return False

    return explore(func, param)


def _verbs() -> set[tuple[str, str]]:
    """(module path, function name) of every leaf verb of the live Typer app, decorator or call form."""
    out: set[tuple[str, str]] = set()

    # Recurse on ``.commands``: Typer's vendored click shim fails isinstance(click.Group).
    def walk(cmd: Any) -> None:
        if getattr(cmd, "commands", None) is None:
            out.add((cmd.callback.__module__.replace(".", "/") + ".py", cmd.callback.__name__))
        else:
            for sub in cmd.commands.values():
                walk(sub)

    walk(typer.main.get_command(app))
    return out


def bind_seam_reached(tree: Tree) -> list[str]:
    """Each ``context``/``specs_dir`` parameter of a verb reaches the resolution seam, with no
    ``dadaia-workspace`` literal default."""
    out, seen = [], 0
    tracked = set(tree.tracked(_COMMANDS))
    for rel, name in sorted(v for v in _verbs() if v[0] in tracked):
        defs = {n.name: n for n in _ast(tree, rel).body if isinstance(n, ast.FunctionDef)}
        for fn in (defs[name],) if name in defs else ():
            args = fn.args.args + fn.args.kwonlyargs
            defaults = [None] * (len(fn.args.args) - len(fn.args.defaults)) + fn.args.defaults
            for arg, default in zip(args, [*defaults, *fn.args.kw_defaults], strict=False):
                if arg.arg not in _RESOLVER_PARAMS:
                    continue
                seen += 1
                label = f"{rel}:{fn.name} --{arg.arg.replace('_', '-')}"
                if default is not None and any(
                    isinstance(n, ast.Constant) and n.value == "dadaia-workspace"
                    for n in ast.walk(default)
                ):
                    out.append(f"hardcoded-default: {label}")
                if not _reaches_seam(defs, fn.name, arg.arg):
                    out.append(f"unreached: {label}")
    return out or ([] if seen else ["unreached: no verb carries a context or specs_dir parameter"])


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def _shipped(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


_SPECS_TEMPLATE = "# AGENTS\n\n<!-- specs-canon -->\n"
_SCAFFOLD_TEXT = "# area law\n"
_VERB = (
    "@app.command()\n"
    "def certify(context: str = typer.Option(None)) -> None:\n"
    "    ctx = context\n"
    "    resolve_context_for_cli(ctx)\n"
)
_PYPROJECT = (
    "[tool.poetry]\nclassifiers = [\n" + "".join(f'  "{c}",\n' for c in _OS_CLASSIFIERS) + "]\n"
)
_MASK = 'x = f"{v[0]}…{v[-1]}"\n'
_PYTHON_FILES = {
    "m.py": "import os\n",
    "features/spec_context/service.py": "run(['git', 'push'])\n",
    "features/chokepoints/branch_policy.py": "x = 1\n",
    "infrastructure/projection_rules.py": "x = 1\n",
    "infrastructure/agent_transcodes.py": "x = 1\n",
    "features/workspace/service.py": "x = 1\n",
    "cli/commands/init.py": "x = 1\n",
    "cli/commands/certify.py": _VERB,
    "cli/redact.py": "b = ContextRedactor(x)\n",
    "core/gitflow.py": "x = 1\n",
    "features/specs/doctor_common.py": "x = 1\n",
    "public/skills/dd-bug-resolution/scripts/_privacy.py": _MASK,
    "public/skills/dd-backlog-definition/scripts/_backlog_schema.py": (
        "T = ('SPEC.md', 'PLAN.md', 'TASKS.md')\n"
    ),
}


def CONTROL(root: Path) -> None:
    """Every check green on a minimal healthy tree; violations only in an ignored file."""
    files = {
        ".gitignore": "scratch/\n",
        "scratch/dadaia_workspace/m.py": "x = 'WORKSPACE_ROOT'\n",
        **{f"{_PKG}/{rel}": text for rel, text in _PYTHON_FILES.items()},
        _PHASE_SCHEMA: json.dumps({"properties": {"phase": {"enum": ["DEFINITION", "CLOSURE"]}}}),
        _DISPOSITION_SCHEMA: json.dumps(
            {"properties": {"disposition": {"enum": ["delivered", "resolved", "rejected"]}}}
        ),
        _WITNESS: "",
        f"{_PUBLIC}/data/AGENTS.md": "- Root holds only: `<!-- root -->`; the rest\n",
        f"{_PUBLIC}/data/dadaia-AGENTS.md": "# z\n\n<!-- zones -->\n",
        f"{_PUBLIC}/data/states-AGENTS.md": "# s\n\n<!-- canon -->\n",
        f"{_PUBLIC}/data/other.md": "- SPEC.md and PLAN.md only.\n",
        f"{_PUBLIC}/templates/specs-AGENTS.md": _SPECS_TEMPLATE,
        f"{_PUBLIC}/templates/shipped-hashes.json": json.dumps(
            {
                "specs-AGENTS.md": [_shipped(render_registry_tables(_SPECS_TEMPLATE))],
                **{f"scaffold/{a}/AGENTS.md": [_shipped(_SCAFFOLD_TEXT)] for a in _SCAFFOLD_AREAS},
            }
        ),
        **{f"{_PUBLIC}/scaffold/{a}/AGENTS.md": _SCAFFOLD_TEXT for a in _SCAFFOLD_AREAS},
        **{f"{_PUBLIC}/scaffold/{rel}": _SCAFFOLD_TEXT for rel in _SCAFFOLD_LAW},
        "specs/AGENTS.md": render_registry_tables(_SPECS_TEMPLATE),
        "specs/releases/.keep": "",
        "pyproject.toml": _PYPROJECT,
        _QUICKSTART[0]: "```bash\nuvx x\n```\n",
        _QUICKSTART[1]: "```bash\nuvx x\n```\n",
    }
    for rel, text in files.items():
        _write(root, rel, text)


def _plant(rel: str, text: str) -> Plant:
    """CONTROL with *rel* overwritten by *text*."""

    def plant(root: Path) -> None:
        CONTROL(root)
        _write(root, rel, text)

    return plant


def _py(rel: str, text: str) -> Plant:
    return _plant(f"{_PKG}/{rel}", text)


def _without(*rels: str) -> Plant:
    def plant(root: Path) -> None:
        CONTROL(root)
        for rel in rels:
            (root / rel).unlink()

    return plant


_PLANT_TABLE = "| Zone | Class | TTL | Creator |\n|---|---|---|---|\n| x | y | z | w |\n"
_SINGLE_HOMES = (
    ("mask", "m.py", _MASK),
    ("redactor", "m.py", "b = ContextRedactor(x)\n"),
    ("gc-check", "m.py", "gc_check = 1\n"),
    ("root-env", "m.py", "x = 'WORKSPACE_ROOT'\n"),
)

CHECKS: dict[str, Check] = {
    "workspace-zone-registry-only-list": (
        zone_registry_only_list,
        {
            "second-list": _py("m.py", "Z = ('SPEC.md', 'PLAN.md', 'TASKS.md')\n"),
            "retired-zone": _py("m.py", "p = '.dadaia/logs'\n"),
            "stale-allowance": _py(
                "public/skills/dd-backlog-definition/scripts/_backlog_schema.py", "x = 1\n"
            ),
            "witness": _without(_WITNESS),
        },
    ),
    "workspace-law-restates-no-set": (
        law_restates_no_set,
        {
            "restated": _plant(
                f"{_PUBLIC}/data/other.md", "- SPEC.md, PLAN.md and TASKS.md are the trio.\n"
            )
        },
    ),
    "workspace-law-tables-equal-registry": (
        law_tables_equal_registry,
        {
            "zones": _plant(f"{_PUBLIC}/data/dadaia-AGENTS.md", _PLANT_TABLE),
            "states": _plant(f"{_PUBLIC}/data/states-AGENTS.md", "| Name |\n|---|\n| x |\n"),
            "specs-canon": _plant(
                f"{_PUBLIC}/templates/specs-AGENTS.md", "| Area | Members |\n|---|---|\n| a | b |\n"
            ),
            "root": _plant(f"{_PUBLIC}/data/AGENTS.md", "- Root holds only: `x`\n"),
        },
    ),
    "workspace-shipped-history-records-law": (
        shipped_history_records_law,
        {"unrecorded": _plant(f"{_PUBLIC}/scaffold/bugs/AGENTS.md", "# edited, never shipped\n")},
    ),
    "workspace-scaffold-area-law": (
        scaffold_area_law,
        {"missing": _without(f"{_PUBLIC}/scaffold/audits/AGENTS.md")},
    ),
    "workspace-specs-law-canonical": (
        specs_law_canonical,
        {
            "untracked": _plant(".gitignore", "specs/AGENTS.md\n"),
            "drift": _plant("specs/AGENTS.md", "# AGENTS\n\nCustomised.\n"),
        },
    ),
    "workspace-release-tree-checks-clean": (
        release_tree_checks_clean,
        {"red": _plant("specs/releases/0.5.0/_RELEASE.json", "not json\n")},
    ),
    "workspace-single-homes": (
        single_homes,
        {rule: _py(rel, text) for rule, rel, text in _SINGLE_HOMES}
        | {
            "mask-home": _py(_PRIVACY.removeprefix(f"{_PKG}/"), "x = 1\n"),
            "redactor-home": _py(_REDACT.removeprefix(f"{_PKG}/"), "x = 1\n"),
        },
    ),
    "workspace-publish-never-rewrites": (
        publish_never_rewrites,
        {
            "rewrite": _py("features/spec_context/service.py", "run(['git', '--force'])\n"),
        },
    ),
    "workspace-harness-names-in-registry-only": (
        harness_names_in_registry_only,
        {"harness-literal": _py("cli/commands/init.py", f'h = "{L1_ENTRY_HARNESSES[0]}"\n')},
    ),
    "workspace-os-classifiers": (
        os_classifiers,
        {
            "missing": _plant("pyproject.toml", "[tool.poetry]\nclassifiers = []\n"),
            "over-broad": _plant(
                "pyproject.toml",
                _PYPROJECT[:-2] + '  "Operating System :: OS Independent",\n]\n',
            ),
        },
    ),
    "workspace-quickstart-fixture": (
        quickstart_fixture_is_the_doc,
        {"stale": _plant(_QUICKSTART[1], "```bash\nuvx y\n```\n")},
    ),
    "workspace-bind-seam-reached": (
        bind_seam_reached,
        {
            "hardcoded-default": _py(
                "cli/commands/certify.py", _VERB.replace("typer.Option(None)", '"dadaia-workspace"')
            ),
            "unreached": _py("cli/commands/certify.py", _VERB.replace("ctx)", "None)")),
        },
    ),
}
