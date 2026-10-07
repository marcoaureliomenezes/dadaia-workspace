"""Slop checks: the package's slop ratchets (V32, V33, V37-V40), the doctor section subset,
the suppressed layering-edge cap (ARCHITECTURE P-10) and no file-size pin (ADR 0143).

``ALLOWANCES`` (V37-V39) is data each check reads from the tree's own copy of this file, so
a plant edits it like any tracked file. A row is ``<check>[*] <key> <value>``: ``*`` marks a
key there at birth (the allowance only shrinks); a value is ``parity:<test file>``, an open
bug id, ``report-only`` (v39) or ``-`` (a birth key no longer allowed).
"""

from __future__ import annotations

import ast
import configparser
import io
import re
import shutil
import sys
import tokenize
import warnings
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dadaia_workspace.infrastructure.ledger_scripts import load_owner  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Callable

    from run import Check, Plant, Session, Tree

SELF, PKG, SWEEP = "scripts/guards/slop.py", "dadaia_workspace", "features/spec_context/sweep.py"
_LEDGER = load_owner("dd-bug-resolution", "_ledger")

# Ceilings measured on this tree; ratchet DOWN ONLY, target 0: lower one in the commit that
# removes a hit, never raise one.
V32_COMMENTS, V32_DOCSTRINGS, V33_ORPHANS, IGNORE_EDGES = 109, 215, 31, 2

# v37: the candidate-folder pair (ADR 0150): the stdlib scripts cannot import the package, so
# each side keeps its twin and one test pins them equal. v38: each deleter outside sweep,
# keyed to the test pinning its delete (a stdlib skill script cannot import the sweep, so its
# row is unstarred when its value is parity:<test>). v39: a doctor code with no fix-clears plant.
ALLOWANCES = """
v37* core/gitflow.py:candidate_dir parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* core/gitflow.py:candidate_number parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* core/gitflow.py:next_candidate parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* core/release_state.py:CANDIDATE_RE parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* public/skills/dd-release-implementation/scripts/_release_schema.py:CANDIDATE_RE parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* public/skills/dd-release-implementation/scripts/_release_schema.py:candidate_dir parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* public/skills/dd-release-implementation/scripts/_release_schema.py:candidate_number parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v37* public/skills/dd-release-implementation/scripts/_release_schema.py:next_candidate parity:tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py
v38* core/atomic_write.py:atomic_write parity:tests/core/test_atomic_write.py
v38* public/skills/dd-bug-resolution/scripts/_ledger.py:replace parity:tests/public/skills/dd_bug_resolution/scripts/test__ledger.py
v38* features/certification/service.py:certify parity:tests/features/certification/test_service.py
v38* features/migrate/state_v2.py:execute_migration parity:tests/features/migrate/test_state_v2.py
v38* features/reconcile/service.py:_restore_state parity:tests/features/reconcile/test_service.py
v38* features/specs/doctor_memory.py:fix_placeholder_atom parity:tests/features/specs/test_canon__scaffold_placeholder_repair.py
v38* infrastructure/projection.py:_clear parity:tests/infrastructure/test_public_assets__install_ledger_reconciliation.py
v38* infrastructure/public_assets.py:_prune_empty_dirs parity:tests/infrastructure/test_public_assets__install_ledger_reconciliation.py
v38* infrastructure/public_assets.py:_reconcile_install_ledger parity:tests/infrastructure/test_public_assets__install_ledger_reconciliation.py
v38* infrastructure/public_assets.py:stage parity:tests/infrastructure/test_public_assets__staged_assets_have_consumers.py
v38 public/skills/dd-gitflow-default/scripts/_worktree_end.py:_rmdir parity:tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py
v38* public/skills/dd-release-implementation/scripts/_release_new.py:new_release parity:tests/public/skills/dd_release_implementation/scripts/test_release.py
v39* ONBOARDING parity:tests/features/workspace/test_onboarding__onboarding_steps_property.py
v39* WS-INVARIANT parity:tests/features/spec_context/test_doctor__unfixable_findings_carry_their_own_fix.py
v39* RELEASE-TREE-ARCHIVED -
v39* RELEASE-TREE-MEMORY -
v39* RELEASE-TREE-PARSE -
v39* RELEASE-TREE-PHASE -
v39* RELEASE-TREE-SCHEMA -
v39* RELEASE-TREE-STATE-MISSING -
v39* RELEASE-TREE-TRIO -
v39* RELEASE-TREE-TS-ORDER -
v39* SPEC-DOC-002L -
v39* SPEC-DOC-035 -
v39* TREE-7 -
"""

PROBE = """
def test_guard_doctor_codes(record_property):
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.rules import RULES as SPECS
    from dadaia_workspace.features.workspace import onboarding
    from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS
    from tests.cli.commands.test_doctor import OPERATOR_ACTION, PLANTS, REPORT_ONLY
    from tests.cli.commands.test_doctor__workspace_fix_lines_clear_their_finding import WORKSPACE_PLANTS

    rules = [*SPECS, *BACKLOG, *workspace_rules(expired_only=False, context=None)]
    codes = {c for r in rules for c in r.codes} | {s.code for s in LEDGER_SCRIPTS} | {onboarding.CODE}
    covered = {*PLANTS, *REPORT_ONLY, *OPERATOR_ACTION, *WORKSPACE_PLANTS}
    record_property("doctor", {"codes": sorted(codes), "covered": sorted(covered)})
"""


def _files(tree: Tree, *spec: str, py: bool = False) -> dict[str, str]:
    """Tracked text files under *spec*, ``_archive`` and undecodable files skipped."""
    out = {}
    for p in tree.tracked(*spec):
        if "_archive" not in Path(p).parts and (p.endswith(".py") or not py):
            try:
                out[p] = tree.read(p)
            except UnicodeDecodeError:
                continue
    return out


def _table(text: str) -> list[list[str]]:
    """The rows of ``ALLOWANCES`` as assigned in *text*."""
    body = text.split('ALLOWANCES = """', 1)[1].split('"""', 1)[0]
    return [row.split() for row in body.splitlines() if row]


def _skill_script(key: str) -> bool:
    return key.startswith("public/skills/") and "/scripts/" in key


def _allowance(tree: Tree, hits: dict[str, str], check: str, also: str = "") -> list[str]:
    """*hits* (key -> its sub-rule) against the tree's allowance rows of *check*."""
    rows = [r for r in _table(tree.read(SELF)) if r[0].rstrip("*") == check]
    allow = {key: value for _, key, value in rows if value != "-"}
    ledger = _LEDGER.records(tree.root / "specs/bugs/BUGS.jsonl")
    valid = {r["id"] for r in ledger if r.get("status") == "open"} | {also}
    out = [f"{r}: {k} has no allowance key" for k, r in sorted(hits.items()) if k not in allow]
    out += [f"stale-key: {k} matches nothing" for k in sorted(allow.keys() - hits.keys())]
    for key, value in sorted(allow.items()):
        if not value.startswith("parity:") and value not in valid:
            out.append(f"bad-value: {key} -> {value!r} is no open bug id")
        elif value.startswith("parity:") and not (tree.root / value[7:]).is_file():
            out.append(f"no-test-file: {key} -> {value}")
    born = {key for check_, key, _ in rows if check_.endswith("*")}
    skill = {k: v for k, v in allow.items() if check == "v38" and _skill_script(k)}
    out += [
        f"skill-row-no-test: {k} -> {v!r}" for k, v in sorted(skill.items()) if v[:7] != "parity:"
    ]
    born |= skill.keys()
    return out + [f"absent-at-birth: {k} (only shrinks)" for k in sorted(allow.keys() - born)]


_GOV_ID = re.compile(r"\b(FR[0-9]+|T-[0-9]{2,3}(-[0-9]+)?|ADR[ -]?[0-9]+|v0\.[0-9]+(\.[0-9]+)?)\b")
_DOC_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def v32(tree: Tree) -> list[str]:
    """Governance ids in package comment tokens and docstring lines (tests excluded)."""
    comments = docs = 0
    for text in _files(tree, PKG, py=True).values():
        for t in tokenize.generate_tokens(io.StringIO(text).readline):
            comments += t.type == tokenize.COMMENT and bool(_GOV_ID.search(t.string))
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, _DOC_OWNERS):
                doc = ast.get_docstring(node, clean=False) or ""
                docs += sum(bool(_GOV_ID.search(line)) for line in doc.splitlines())
    out = [f"comment-ids: {comments} comments > {V32_COMMENTS}"] if comments > V32_COMMENTS else []
    return out + (
        [f"docstring-ids: {docs} lines > {V32_DOCSTRINGS}"] if docs > V32_DOCSTRINGS else []
    )


_FAMILY, _UPPER = re.compile(r"\b[A-Z]{1,4}-?[0-9]{2,3}\b"), re.compile(r"[A-Z]+")
_WORD = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def _joined(text: str, i: int) -> bool:
    """``text[i]`` is a witness char: a `_WORD` char, or a `.` between two (a dotted id)."""
    return text[i] in _WORD or (
        text[i] == "." and 0 < i < len(text) - 1 and {text[i - 1], text[i + 1]} <= _WORD
    )


def _constants(source: str) -> list[str]:
    """Every non-empty string constant of *source* that is not a bare docstring statement."""
    nodes = list(ast.walk(ast.parse(source)))
    bare = {id(n.value) for n in nodes if isinstance(n, ast.Expr)}
    strs = [n for n in nodes if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return [str(n.value) for n in strs if n.value and id(n) not in bare]


def _reads(constant: str, prefix: str, witnesses: set[tuple[str, int]]) -> bool:
    """*constant* (a regex, else a literal) matches a witness through its prefix and beyond."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            pattern = re.compile(constant)
    except re.error:
        pattern = re.compile(re.escape(constant))
    return any(
        (m := pattern.search(word)) is not None and m.start() <= at and m.end() > at + len(prefix)
        for word, at in witnesses
    )


def v33(tree: Tree) -> list[str]:
    """PREFIX-NN families in specs/, the package and tests/ that no string constant reads."""
    families: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for text in _files(tree, "specs", PKG, "tests").values():
        for m in _FAMILY.finditer(text):
            left, right = m.start(), m.end()
            while left > 0 and _joined(text, left - 1):
                left -= 1
            while right < len(text) and _joined(text, right):
                right += 1
            prefix = _UPPER.match(m.group(0)).group(0)  # type: ignore[union-attr]
            families[prefix].add((text[left:right], m.start() - left))
    readers: dict[str, list[str]] = defaultdict(list)
    for source in _files(tree, PKG, "tests", py=True).values():
        for constant in _constants(source):
            for run in set(_UPPER.findall(constant)):
                readers[run].append(constant)
    unread = [
        p for p, w in sorted(families.items()) if not any(_reads(c, p, w) for c in readers[p])
    ]
    orphans = [p for p in unread if p not in {"FR", "AC", "T"}]
    if len(orphans) > V33_ORPHANS:
        return [f"orphan-families: {len(orphans)} > {V33_ORPHANS}: {orphans}"]
    return []


def _definition(node: ast.stmt) -> tuple[str, str, str] | None:
    """``(name, shape, sub-rule)`` of a top-level function (docstring dropped) or an UPPER
    constant whose value is not a bare scalar literal."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        body = node.body[1:] if ast.get_docstring(node) is not None else node.body
        shape = ast.dump(node.args) + ast.dump(ast.Module(body=body, type_ignores=[]))
        return node.name, shape, "function-twin"
    one = isinstance(node, ast.Assign) and len(node.targets) == 1
    target = node.targets[0] if one else getattr(node, "target", None)  # type: ignore[attr-defined]
    value = getattr(node, "value", None)
    if isinstance(target, ast.Name) and target.id.lstrip("_").isupper() and value is not None:
        twin = (target.id, ast.dump(value), "constant-twin")
        return None if isinstance(value, ast.Constant) else twin
    return None


def v37(tree: Tree) -> list[str]:
    """A definition AST-identical in two package modules, skill scripts or hooks."""
    homes: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for rel, text in _files(tree, PKG, py=True).items():
        for node in ast.parse(text).body:
            if (found := _definition(node)) is not None:
                homes[found].add(rel[len(PKG) + 1 :])
    hits = {f"{rel}:{d[0]}": d[2] for d, rels in homes.items() if len(rels) > 1 for rel in rels}
    return _allowance(tree, hits, "v37")


_DELETES, _OS_DELETES = {"rmtree", "unlink", "rmdir", "removedirs"}, {"remove", "move"}


def v38(tree: Tree) -> list[str]:
    """A delete call outside ``features/spec_context/sweep.py``, the one deleter."""
    hits: dict[str, str] = {}
    for rel, text in _files(tree, PKG, py=True).items():
        rel, module, owner = rel[len(PKG) + 1 :], ast.parse(text), {}
        functions = [
            n for n in ast.walk(module) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        ]
        for function in sorted(functions, key=lambda f: f.lineno):
            owner.update({id(n): function.name for n in ast.walk(function)})
        for node in ast.walk(module):
            if rel == SWEEP or not isinstance(getattr(node, "func", None), ast.Attribute):
                continue
            base, attr = ast.unparse(node.func.value), node.func.attr  # type: ignore[attr-defined]
            key = f"{rel}:{owner.get(id(node), '<module>')}"
            if attr in _DELETES and base != "sweep":
                hits[key] = "path-delete"
            elif attr in _OS_DELETES and base in {"os", "shutil"}:
                hits[key] = "os-delete"
    return _allowance(tree, hits, "v38")


def v39(tree: Tree) -> list[str]:
    """Every doctor code has a fix-clears plant, or an allowance key."""
    doctor = tree.session.get("props", {}).get("doctor")
    if doctor is None:
        return ["probe-broke: the probe session recorded no doctor codes"]
    codes, covered = set(doctor["codes"]), set(doctor["covered"])
    out = [f"undeclared-code: {c} has a plant but no rule table" for c in sorted(covered - codes)]
    return out + _allowance(tree, dict.fromkeys(codes - covered, "uncovered"), "v39", "report-only")


def _attr(node: ast.AST) -> str:
    return str(getattr(getattr(node, "func", None), "attr", ""))


_ASSIGNS = ast.Assign | ast.AnnAssign


def v40(tree: Tree) -> list[str]:
    """``json.loads`` fed from ``.splitlines()``, directly or through one assigned name:
    U+2028 splits a record; JSONL goes through ``_ledger.parse``."""
    out = []
    for rel, text in _files(tree, PKG, "tests", py=True).items():
        nodes, tainted = list(ast.walk(ast.parse(text))), dict[str, str]()
        for a in nodes:
            if isinstance(a, _ASSIGNS) and "splitlines" in map(_attr, ast.walk(a)):
                hop = "annotated-hop" if isinstance(a, ast.AnnAssign) else "hop"
                targets = a.targets if isinstance(a, ast.Assign) else [a.target]
                tainted |= {getattr(t, "id", ""): hop for t in targets}
        for node in nodes:
            loops = getattr(node, "generators", None) or (
                [node] if isinstance(node, ast.For) else []
            )
            args = node.args if isinstance(node, ast.Call) else []
            first = getattr(args[0], "attr", "") if args else ""
            if loops and "loads" in map(_attr, ast.walk(node)):
                kind = "for-loop" if loops == [node] else "comprehension"
                fed = [g.iter for g in loops]
            elif _attr(node) == "loads" or (_callee(node) == "map" and first == "loads"):
                fed, kind = args, ("argument" if _attr(node) == "loads" else "map")
            else:
                continue
            seen = [c for x in fed for c in ast.walk(x)]
            via = [tainted[c.id] for c in seen if isinstance(c, ast.Name) and c.id in tainted]
            if via or "splitlines" in map(_attr, seen):
                out.append(f"{via[0] if via else kind}: {rel}:{node.lineno}")  # type: ignore[attr-defined]
    return out


def doctor_section_subset(tree: Tree) -> list[str]:
    """No code selects a subset of doctor sections, named by each module's ``SECTION``."""
    modules = {rel: ast.parse(text) for rel, text in _files(tree, PKG, py=True).items()}
    found = [n for m in modules.values() for n in m.body if isinstance(n, ast.Assign)]
    found = [n for n in found if getattr(n.targets[0], "id", "") == "SECTION"]
    sections = {v for n in found if isinstance(v := getattr(n.value, "value", None), str)}
    out = [] if len(sections) >= 2 else [f"no-sections: {len(sections)} SECTION constants, < 2"]
    for rel, module in modules.items():
        for n in ast.walk(module):
            named = {getattr(e, "value", "") for e in getattr(n, "elts", [])}
            if isinstance(n, ast.Subscript) and ast.unparse(n.slice) == "'sections'":
                out.append(f"sections-read: {rel}:{n.lineno} reads a report's sections")
            elif isinstance(n, ast.Tuple | ast.List | ast.Set) and len(sections & named) >= 2:
                out.append(f"section-literal: {rel}:{n.lineno} names two doctor sections")
    return out


_CROSS = "importlinter:contract:features-no-cross-feature"


def _edges(text: str) -> list[tuple[str, str]]:
    """``(contract, edge)`` for every ignored import; configparser drops comment lines."""
    cfg = configparser.ConfigParser()
    cfg.read_string(text)
    edges = [(s, cfg[s].get("ignore_imports", "").splitlines()) for s in cfg.sections()]
    return [(s, e.strip()) for s, lines in edges for e in lines if "->" in e]


def ignore_cap(tree: Tree) -> list[str]:
    """P-10: the suppressed edges equal the cap, under the cross-feature contract, from features."""
    edges = _edges(tree.read("setup.cfg"))
    out = (
        [f"edge-cap: {len(edges)} ignored edges != {IGNORE_EDGES}"]
        if len(edges) != IGNORE_EDGES
        else []
    )
    out += [f"off-family: {e} sits under {s}" for s, e in edges if s != _CROSS]
    return out + [
        f"non-feature-source: {e}" for _, e in edges if not e.startswith(f"{PKG}.features")
    ]


_READS = {"read_text", "read_bytes", "read", "readlines"}
_EXEMPT = {"skill_md_line_soft", "skill_md_line_ceiling"}  # ADR 0170's two keys


def _callee(n: ast.AST | None) -> str:
    return (
        str(getattr(n.func, "attr", None) or getattr(n.func, "id", ""))
        if isinstance(n, ast.Call)
        else ""
    )


def _hop(e: ast.expr, names: dict[str, ast.expr]) -> ast.expr:
    e = e.value if isinstance(e, ast.NamedExpr) else e
    return names.get(e.id, e) if isinstance(e, ast.Name) else e


def _measure(e: ast.expr, names: dict[str, ast.expr]) -> str | None:
    """The sub-rule naming how *e* measures a file read, or None."""
    e = _hop(e, names)
    if isinstance(e, ast.Attribute) and e.attr == "st_size":
        return "st_size"
    if not isinstance(e, ast.Call) or not e.args:
        return None
    if _callee(e) == "count" and getattr(e.args[0], "value", None) in ("\n", b"\n"):
        return "count" if _callee(_hop(e.func.value, names)) in _READS else None  # type: ignore[attr-defined]
    arg = _hop(e.args[0], names) if _callee(e) == "len" else None
    if _callee(arg) == "splitlines" and _callee(_hop(arg.func.value, names)) in _READS:  # type: ignore[union-attr]
        return "splitlines"
    return _callee(arg) if _callee(arg) in _READS else None


def _bound(e: ast.expr, names: dict[str, ast.expr]) -> str | None:
    """*e* as a constant (int literal, UPPER name, a data key other than 0170's), else None."""
    if not (isinstance(e, ast.Name) and e.id.lstrip("_").isupper()):
        e = _hop(e, names)
    if isinstance(e, ast.Constant) and type(e.value) is int:
        return str(e.value)
    if isinstance(e, ast.Name) and e.id.lstrip("_").isupper():
        return e.id
    key = getattr(getattr(e, "slice", None), "value", None)
    return (
        f"[{key!r}]"
        if isinstance(e, ast.Subscript) and isinstance(key, str) and key not in _EXEMPT
        else None
    )


def no_size_pin(tree: Tree) -> list[str]:
    """ADR 0143: no test or script compares a file's line or byte count against a constant."""
    out = []
    for rel, text in _files(tree, py=True).items():
        module, names = ast.parse(text), {}
        for n in ast.walk(module):
            t = n.targets[0] if isinstance(n, ast.Assign) else getattr(n, "target", None)
            if (
                type(n) is not ast.AugAssign
                and isinstance(t, ast.Name)
                and getattr(n, "value", None)
            ):
                names[t.id] = n.value  # type: ignore[attr-defined]
        for n in ast.walk(module):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                for a, b in ((n.left, n.comparators[0]), (n.comparators[0], n.left)):
                    if (m := _measure(a, names)) and (k := _bound(b, names)):
                        out.append(f"{m}: {rel}:{n.lineno} compares a file's size against {k}")
    return out


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    with (root / rel).open("a", encoding="utf-8") as f:
        f.write(text)


def _ids(comments: int, docs: int) -> str:
    """A module with *comments* id comments and *docs* id docstring lines over all four owners."""
    q, r = divmod(docs, 4)
    doc = ['"""' + "\n".join(["FR1"] * n) + '"""' for n in (q + r, q)]
    body = "".join(
        f"x = 1  {('# FR1', '# T-050', '# ADR 1', '# v0.5.1')[i % 4]}\n" for i in range(comments)
    )
    return f"{doc[0]}\n{body}class C:\n    {doc[1]}\ndef f():\n    {doc[1]}\nasync def g():\n    {doc[1]}\n"


_NEAR = '''"""A near miss for every matcher; no governance id here."""
import json, os
SECTION = "workspace"
KIND = "a"
def load(p):
    """Load."""
    return p
def near(p, q, t, r, cfg, limit):
    sweep.unlink(p); os.replace(p, q); r.move(p); r["section"]; x = ("workspace", "x")  # a why
    rows = [json.loads(x) for x in t.split("\\n")]; n = len(t.splitlines()); lines = t.splitlines()
    y = map(str, t.splitlines()); z = sorted(json.loads, t.splitlines())
    ok = len(p.read_text().splitlines()) > cfg["skill_md_line_soft"]; ok = len(t.splitlines()) <= 12
    ok = p.read_text().count("x") > 3; ok = len(p.read_bytes()) > limit; bad = "("
'''
_DELETERS = [
    "p.rmtree()",
    "p.unlink()",
    "p.rmdir()",
    "p.removedirs()",
    "os.remove(p)",
    "shutil.move(p)",
]


def CONTROL(root: Path) -> Session:
    """Every check green: synthetic twins and deleters for each allowance key, the ceilings
    met exactly, a near miss per matcher; violations only in an untracked, gitignored dir."""
    (root / SELF).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / SELF, root / SELF)
    shutil.copyfile(ROOT / "setup.cfg", root / "setup.cfg")
    rows = _table((ROOT / SELF).read_text("utf-8"))
    for i, (check, key, value) in enumerate(rows):
        rel, _, sym = key.partition(":")
        if check == "v37*":
            _write(
                root,
                f"{PKG}/{rel}",
                f"{sym} = compile('x')\n" if sym.isupper() else f"def {sym}(p):\n    return p\n",
            )
        if check.rstrip("*") == "v38":
            _write(root, f"{PKG}/{rel}", f"def {sym}(p, q):\n    {_DELETERS[i % 6]}\n")
        if value.startswith("parity:"):
            _write(root, value[7:], "")
    _edit_row(root, "v38", lambda r: f"{r[0]} {r[1]} zz-open-bug", -2)
    _edit_row(root, "v39", lambda r: f"{r[0]} {r[1]} report-only", -1)
    _write(
        root,
        "specs/bugs/BUGS.jsonl",
        '{"id": "zz-open-bug", "status": "open"}\n{"id": "zz-shut", "status": "resolved"}\n',
    )
    _write(root, f"{PKG}/{SWEEP}", "def sweep(p):\n    p.unlink()\n")
    _write(root, f"{PKG}/ids.py", _ids(V32_COMMENTS, V32_DOCSTRINGS) + 'x = "FR1 ADR 1"\n')
    _write(root, f"{PKG}/zz/near.py", _NEAR)
    _write(
        root,
        f"{PKG}/zz/near2.py",
        'SECTION = "ledgers"\nKIND = "a"\ndef load(p):\n    """Load."""\n    return 1\n',
    )
    orphans = " ".join(f"Q{chr(65 + i // 26)}{chr(65 + i % 26)}-01" for i in range(V33_ORPHANS - 3))
    _write(
        root, "specs/x.md", f"{orphans} OFF-11 DIG-22 RDA-12 RDB-12 EF-12-XY FR-12 AC-03 T-050\n"
    )
    _write(root, "specs/y.md", "XB-CD-12\n")
    readers = '"OFF", "(?<=DIG)-22", r"RDA-\\d+", r"RDB-\\d+", r"^XB-CD-\\d+$", r"^EF-\\d+-XY$"'
    _write(root, "tests/unit/test_r.py", f'"""DOC-11"""\nreaders = ({readers})\n')
    _write(root, "specs/_archive/x.md", "ARC-01\n")
    (root / "specs/bin.dat").write_bytes(b"\xff ZZZ-01\n")
    _write(root, ".gitignore", f"{PKG}/zz_ignored/\n")
    _write(
        root,
        f"{PKG}/zz_ignored/x.py",
        'def f(p):\n    p.unlink(); r["sections"]\nok = p.stat().st_size > 9\n',
    )
    allowed = [r[1] for r in rows if r[0] == "v39*" and r[2] != "-"]
    return {"props": {"doctor": {"codes": ["ZZ-COVERED", *allowed], "covered": ["ZZ-COVERED"]}}}


def _edit_row(root: Path, check: str, edit: Callable[[list[str]], str], index: int = 0) -> None:
    """The tree copy's *index*-th allowed row of *check* rewritten by *edit*."""
    text = (root / SELF).read_text("utf-8")
    row = [r for r in _table(text) if r[0] == f"{check}*" and r[2] != "-"][index]
    (root / SELF).write_text(text.replace(" ".join(row), edit(row), 1), "utf-8")


def _plant(edit: Callable[[Path], object]) -> Plant:
    def plant(root: Path) -> Session:
        session = CONTROL(root)
        edit(root)
        return session

    return plant


def _edit(rel: str, old: str, new: str) -> Plant:
    return _plant(lambda r: (r / rel).write_text((r / rel).read_text("utf-8").replace(old, new)))


def _add(rel: str, text: str | Callable[[], str]) -> Plant:
    return _plant(lambda root: _write(root, rel, text if isinstance(text, str) else text()))


def _rows(check: str, bad: str) -> dict[str, Plant]:
    """One plant per allowance sub-rule, each editing the first allowed row of *check*."""
    rules: dict[str, Callable[[list[str]], str]] = {
        "stale-key": lambda r: f"{' '.join(r)}\n{r[0]} zz.py:x {r[2]}",
        "no-test-file": lambda r: f"{r[0]} {r[1]} parity:tests/none.py",
        "bad-value": lambda r: f"{r[0]} {r[1]} {bad}",
        "absent-at-birth": lambda r: f"{check} {r[1]} {r[2]}",
    }

    def bind(f: Callable[[list[str]], str]) -> Plant:
        return _plant(lambda root: _edit_row(root, check, f))

    return {rule: bind(f) for rule, f in rules.items()}


def _born_package_row(root: Path) -> None:
    _write(root, f"{PKG}/zz/tidy.py", "def tidy(p):\n    p.unlink()\n")
    _edit_row(root, "v38", lambda r: f"{' '.join(r)}\nv38 zz/tidy.py:tidy {r[2]}")


def _first(constant: bool) -> str:
    """The first v37 key's symbol of the real table that is (or is not) a constant."""
    syms = [r[1].split(":")[1] for r in _table((ROOT / SELF).read_text("utf-8")) if r[0] == "v37*"]
    return min(s for s in syms if s.isupper() == constant)


def _doctor(codes: list[str], covered: list[str]) -> Plant:
    def plant(root: Path) -> Session:
        session = CONTROL(root)
        session["props"]["doctor"]["codes"] += codes
        session["props"]["doctor"]["covered"] += covered
        return session

    return plant


def _cfg(edit: Callable[[str, str], str]) -> Plant:
    """CONTROL's setup.cfg rewritten by *edit* given its first ignored edge, read at plant time."""

    def rewrite(root: Path) -> None:
        text = (root / "setup.cfg").read_text("utf-8")
        (root / "setup.cfg").write_text(edit(text, _edges(text)[0][1]), "utf-8")

    return _plant(rewrite)


def _ids_plant(comments: int, docs: int) -> Plant:
    return _plant(lambda root: (root / PKG / "ids.py").write_text(_ids(comments, docs), "utf-8"))


# Plants appending one text under CONTROL: `<check> <row> <path> <text>`, the text's `\n` escaped.
_APPENDS = r"""
v33 orphan-families specs/x.md  NEW-01\n
v38 path-delete dadaia_workspace/zz/tidy.py def tidy(p):\n    p.unlink()\n
v38 os-delete dadaia_workspace/zz/tidy.py def outer():\n    def tidy(p):\n        os.remove(p)\n
v40 comprehension tests/unit/test_j.py rows = [json.loads(x) for x in t.splitlines()]\n
v40 for-loop tests/unit/test_j.py for n, x in enumerate(t.splitlines(), 1):\n    json.loads(x)\n
v40 argument tests/unit/test_j.py r = json.loads(t.splitlines()[0])\n
v40 map tests/unit/test_j.py rows = list(map(json.loads, t.splitlines()))\n
v40 hop tests/unit/test_j.py lines = t.splitlines()\nrows = [json.loads(x) for x in lines]\n
v40 annotated-hop tests/unit/test_j.py lines: list = t.splitlines()\nrows = [json.loads(x) for x in lines]\n
doctor-section-subset sections-read dadaia_workspace/zz/s.py x = report['sections']\n
doctor-section-subset section-literal dadaia_workspace/zz/s.py x = ['workspace', 'ledgers']\n
no-size-pin st_size tests/unit/test_pin.py assert p.stat().st_size <= 10240\n
no-size-pin count tests/unit/test_pin.py ok = (n := p.read_text().count("\x0a")) > _MAX_LINES\n
no-size-pin splitlines tests/unit/test_pin.py n_lines: int = len(p.read_text().splitlines())\nlimit = 300\nok = n_lines <= limit\n
no-size-pin read_bytes tests/unit/test_pin.py ok = len(p.read_bytes()) > cfg["readme_max_bytes"]\n
no-size-pin read_text tests/unit/test_pin.py ok = len(p.read_text()) > 4096\n
no-size-pin readlines tests/unit/test_pin.py ok = len(f.readlines()) < 9\n
no-size-pin read tests/unit/test_pin.py ok = len(f.read()) >= 9\n
"""
_TWIN, _EDGE = f"{PKG}/zz/twin.py", f"{PKG}.features.zz -> {PKG}.features.yy"
_PLANTS: dict[str, dict[str, Plant]] = {
    "v32": {
        "comment-ids": _ids_plant(V32_COMMENTS + 1, V32_DOCSTRINGS),
        "docstring-ids": _ids_plant(V32_COMMENTS, V32_DOCSTRINGS + 1),
    },
    "v33": {},
    "v37": {
        "function-twin": _add(_TWIN, lambda: f"def {_first(False)}(p):\n    return p\n"),
        "constant-twin": _add(_TWIN, lambda: f"{_first(True)}: object = compile('x')\n"),
        **_rows("v37", "report-only"),
    },
    "v38": {
        **_rows("v38", "zz-shut"),
        "absent-at-birth": _plant(_born_package_row),
        "skill-row-no-test": _edit(
            SELF,
            "_worktree_end.py:_rmdir parity:tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py",
            "_worktree_end.py:_rmdir zz-open-bug",
        ),
        "no-test-file": _edit(
            SELF,
            "_worktree_end.py:_rmdir parity:tests/public",
            "_worktree_end.py:_rmdir parity:tests/zz/public",
        ),
    },
    "v39": {
        "uncovered": _doctor(["ZZ-NEW"], []),
        "undeclared-code": _doctor([], ["ZZ-GHOST"]),
        "probe-broke": lambda root: {},
        **_rows("v39", "zz-unknown"),
    },
    "v40": {},
    "doctor-section-subset": {
        "no-sections": _edit(f"{PKG}/zz/near2.py", '"ledgers"', "Section.LEDGERS")
    },
    "ignore-cap": {
        "edge-cap": _cfg(lambda t, e: t.replace(e, f"{e}\n    {_EDGE}", 1)),
        "off-family": _cfg(
            lambda t, e: t.replace(e, "", 1) + f"\n[x:y]\nignore_imports =\n    {e}\n"
        ),
        "non-feature-source": _cfg(
            lambda t, e: t.replace(e, e.replace(".features", ".core", 1), 1)
        ),
    },
    "no-size-pin": {},
}
for _row in _APPENDS.strip().splitlines():
    _check, _name, _rel, _text = _row.split(" ", 3)
    _PLANTS[_check][_name] = _add(_rel, _text.replace("\\n", "\n"))
CHECKS: dict[str, Check] = {
    cid: (globals()[cid.replace("-", "_")], rows) for cid, rows in _PLANTS.items()
}
