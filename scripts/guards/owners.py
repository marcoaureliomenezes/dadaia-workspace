"""Owner checks: each question the package answers in one module is asked of the whole package.

One check per question; each violation opens with the sub-rule it names. Every check reads
the tracked ``dadaia_workspace`` sources as ASTs or text, never the live import graph.
"""

from __future__ import annotations

import ast
import re
import shutil
from typing import TYPE_CHECKING

from run import ROOT, tracked

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from run import Check, Tree

PKG = "dadaia_workspace"

# core/ modules whose file I/O is authorized; new I/O enters core/ only by joining this set.
CORE_IO_STEMS = frozenset(
    {"workspace_resolver", "context_registry", "session_store", "handoff_index",
     "template_history", "gitflow", "workspace_layout"}
)  # fmt: skip
_PATH_IO_ATTRS = frozenset(
    {"read_text", "write_text", "mkdir", "exists", "glob", "iterdir", "rglob"}
)
_PATH_CLASS_OWNERS = {"features/spec_context/gate_policy.py", "core/workspace_layout.py"}
_RMTREE_ALLOWED = {"service.py:create", "sweep.py:remove"}
_LAYOUT_SETS = {
    "ROOT_ALLOWED_DIRS", "ROOT_ALLOWED_FILES", "DADAIA_ROOT_FILES", "STATES_CANON", "zone_names",
}  # fmt: skip
_VERDICT_READERS = ("hooks/root_whitelist.py", "features/spec_context/doctor.py")


def _sources(tree: Tree, *globs: str) -> Iterator[tuple[str, str, ast.Module]]:
    """(path under the package, text, AST) of each tracked package source matching a glob."""
    from fnmatch import fnmatchcase

    for path in tree.tracked(PKG):
        rel = path.removeprefix(f"{PKG}/")
        if path.endswith(".py") and (not globs or any(fnmatchcase(rel, g) for g in globs)):
            text = tree.read(path)
            yield rel, text, ast.parse(text)


def _called(node: ast.Call) -> str:
    return getattr(node.func, "attr", getattr(node.func, "id", ""))


def _functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    yield from (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef))


def core_file_io(tree: Tree) -> list[str]:
    hits, stems = [], set()
    for rel, _, mod in _sources(tree, "core/*.py", "core/**/*.py"):
        stem = rel.rsplit("/", 1)[-1].removesuffix(".py")
        stems.add(stem)
        if stem in CORE_IO_STEMS:
            continue
        for n in (c for c in ast.walk(mod) if isinstance(c, ast.Call)):
            f = n.func
            if (
                (isinstance(f, ast.Name) and f.id == "open")
                or (isinstance(f, ast.Attribute) and f.attr in _PATH_IO_ATTRS)
                or (
                    isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "shutil"
                    and (f.attr.startswith("copy") or f.attr == "move")
                )
            ):
                hits.append(f"io-outside-authorized: {rel}:{n.lineno}")
    return hits + [f"stale-stem: {s}" for s in sorted(CORE_IO_STEMS - stems)]


def session_paths(tree: Tree) -> list[str]:
    pointer = ('"sessions" / "runtime"', '"runtime" / f"{')
    record = ('"sessions" / f"{', '".dadaia" / "sessions"')
    return [
        f"session-path-idiom: {rel}: {i}"
        for rel, text, _ in _sources(tree)
        for i in pointer + (() if rel == "core/session_store.py" else record)
        if i in text
    ]


def orphan_factories(tree: Tree) -> list[str]:
    source = tree.read(f"{PKG}/container.py")
    defs = re.findall(r"^(?:def|class) ([A-Za-z_][A-Za-z0-9_]*)", source, re.M)
    others = "\n".join(t for rel, t, _ in _sources(tree) if rel != "container.py")

    def used(text: str, name: str) -> bool:
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text) is not None

    return [
        f"orphan-factory: {n}"
        for n in defs
        if not used(others, n)
        and not used(re.sub(rf"^(?:def|class) {n}\b", "", source, flags=re.M), n)
    ]


def rmtree_sites(tree: Tree) -> list[str]:
    sites = {
        f"{rel.rsplit('/', 1)[-1]}:{fn.name}"
        for rel, _, mod in _sources(tree, "features/spec_context/*.py")
        for fn in _functions(mod)
        if fn.name != "rmtree"
        and any(isinstance(c, ast.Call) and _called(c) == "rmtree" for c in ast.walk(fn))
    }
    return [f"rmtree-site: {s}" for s in sorted(sites ^ _RMTREE_ALLOWED)]


def ttl_clocks(tree: Tree) -> list[str]:
    return [
        f"ttl-constant: {rel}:{t.id}"
        for rel, _, mod in _sources(tree)
        if not rel.startswith("public/") and not rel.endswith("workspace_layout.py")
        for n in ast.walk(mod)
        for t in (
            n.targets
            if isinstance(n, ast.Assign)
            else [n.target]
            if isinstance(n, ast.AnnAssign)
            else []
        )
        if isinstance(t, ast.Name) and "_TTL" in t.id and t.id != "SESSION_GC_TTL_SECONDS"
    ]


def path_class_readers(tree: Tree) -> list[str]:
    return [
        f"table-reader: {rel}"
        for rel, _, mod in _sources(tree)
        if rel not in _PATH_CLASS_OWNERS
        and "additive_prefixes"
        in (
            {n.attr for n in ast.walk(mod) if isinstance(n, ast.Attribute)}
            | {n.id for n in ast.walk(mod) if isinstance(n, ast.Name)}
            | {a.name for n in ast.walk(mod) if isinstance(n, ast.ImportFrom) for a in n.names}
        )
    ]


def path_class_producers(tree: Tree) -> list[str]:
    return [
        f"producer: {rel}:{n.lineno}"
        for rel, _, mod in _sources(tree)
        if rel not in _PATH_CLASS_OWNERS
        for n in ast.walk(mod)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Attribute)
        and "PathClass" in ast.unparse(n.value)
    ]


def release_state_io(tree: Tree) -> list[str]:
    text = tree.read(f"{PKG}/core/release_state.py")
    writers = {"write_text", "write_bytes", "mkdir", "unlink", "rmdir", "atomic_write", "open"}
    hits = [
        f"release-state-io: {n.lineno}:{_called(n)}"
        for n in ast.walk(ast.parse(text))
        if isinstance(n, ast.Call) and _called(n) in writers
    ]
    return hits + (["release-state-io: read_text("] if "read_text(" in text else [])


def repos_from_context_name(tree: Tree) -> list[str]:
    return [
        f"repos-from-context-name: {rel}:{n.lineno}"
        for rel, _, mod in _sources(tree)
        for n in ast.walk(mod)
        if isinstance(n, ast.BinOp)
        and isinstance(n.op, ast.Div)
        and isinstance(n.left, ast.BinOp)
        and isinstance(n.left.right, ast.Constant)
        and n.left.right.value == "repos"
        and "context" in (text := ast.unparse(n.right))
        and "slug" not in text
    ]


def raw_specs_writes(tree: Tree) -> list[str]:
    hits = []
    for rel, _, mod in _sources(tree, "features/migrate/*.py", "features/specs/*.py"):
        for n in ast.walk(mod):
            if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
                continue
            name, owner = n.func.attr, n.func.value
            is_os = isinstance(owner, ast.Name) and owner.id == "os"
            opens_for_write = name == "open" and any(
                isinstance(a, ast.Constant) and str(a.value)[:1] in {"w", "a", "x"} for a in n.args
            )
            if (
                name in {"write_text", "write_bytes"}
                or (is_os and name in {"replace", "open"})
                or opens_for_write
            ):
                hits.append(f"raw-write: {rel}:{n.lineno}:{name}")
    return hits


def reaped_deleters(tree: Tree) -> list[str]:
    return [
        f"reaped-deleter: {rel}:{fn.name}"
        for rel, _, mod in _sources(tree)
        for fn in _functions(mod)
        if any(
            (isinstance(n, ast.Constant) and n.value == "reaped")
            or (isinstance(n, ast.Name) and n.id == "REAPED_ZONE")
            for n in ast.walk(fn)
        )
        and any(
            isinstance(n, ast.Call) and _called(n) in {"remove", "rmtree", "unlink", "rmdir"}
            for n in ast.walk(fn)
        )
    ]


def one_verdict_readers(tree: Tree) -> list[str]:
    out = []
    for rel in _VERDICT_READERS:
        mod = ast.parse(tree.read(f"{PKG}/{rel}"))
        attrs = {n.attr for n in ast.walk(mod) if isinstance(n, ast.Attribute)}
        names = {n.id for n in ast.walk(mod) if isinstance(n, ast.Name)}
        out += [f"layout-set-read: {rel}: {s}" for s in sorted((attrs | names) & _LAYOUT_SETS)]
        out += [] if "verdict" in attrs else [f"no-verdict-call: {rel}"]
    return out


# --- plants: the control is a copy of the tracked package; each plant adds one violation -----


def _write(root: Path, rel: str, text: str, *, append: bool = False) -> None:
    path = root / PKG / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = path.read_text(encoding="utf-8") if append else ""
    path.write_text(prior + text, encoding="utf-8")


def CONTROL(root: Path) -> None:
    """Every check green on a copy of the tracked package; an untracked, gitignored module
    carrying violations stays unread."""
    for rel in tracked(ROOT, PKG):
        if rel.endswith(".py"):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, root / rel)
    (root / ".gitignore").write_text("scratch/\n", encoding="utf-8")
    _write(root, "../scratch/zz.py", "FOO_TTL = 1\nopen('x')\n")


def _plant(rel: str, text: str, *, append: bool = False) -> Callable[[Path], None]:
    def plant(root: Path) -> None:
        CONTROL(root)
        _write(root, rel, text, append=append)

    return plant


def _plant_stale_stem(root: Path) -> None:
    CONTROL(root)
    (root / PKG / "core" / "gitflow.py").unlink()


CHECKS: dict[str, Check] = {
    "core-file-io-purity": (
        core_file_io,
        {
            "io-outside-authorized": _plant("core/zz.py", "open('x')\n"),
            "stale-stem": _plant_stale_stem,
        },
    ),
    "session-store-owns-session-paths": (
        session_paths,
        {"session-path-idiom": _plant("features/zz.py", 'p = "sessions" / f"{x}"\n')},
    ),
    "every-container-def-has-a-production-consumer": (
        orphan_factories,
        {"orphan-factory": _plant("container.py", "\ndef zz_orphan(): ...\n", append=True)},
    ),
    "no-rmtree-outside-the-create-rollback": (
        rmtree_sites,
        {"rmtree-site": _plant("features/spec_context/zz.py", "def f(p):\n    rmtree(p)\n")},
    ),
    "one-expiry-clock": (ttl_clocks, {"ttl-constant": _plant("core/zz.py", "FOO_TTL = 1\n")}),
    "path-class-tables-have-one-reader": (
        path_class_readers,
        {"table-reader": _plant("core/zz.py", "x = additive_prefixes\n")},
    ),
    "path-class-has-one-producer": (
        path_class_producers,
        {"producer": _plant("core/zz.py", "def f():\n    return PathClass.X\n")},
    ),
    "release-state-module-never-writes": (
        release_state_io,
        {"release-state-io": _plant("core/release_state.py", "\nopen('x')\n", append=True)},
    ),
    "repos-path-comes-from-the-registry": (
        repos_from_context_name,
        {"repos-from-context-name": _plant("core/zz.py", "x = root / 'repos' / context_name\n")},
    ),
    "specs-writes-go-through-atomic-write": (
        raw_specs_writes,
        {"raw-write": _plant("features/specs/zz.py", "p.write_text('x')\n")},
    ),
    "no-function-naming-the-reaped-zone-deletes": (
        reaped_deleters,
        {
            "reaped-deleter": _plant(
                "features/zz.py", "def f(p):\n    REAPED_ZONE\n    p.unlink()\n"
            )
        },
    ),
    "root-whitelist-and-doctor-ask-the-one-verdict": (
        one_verdict_readers,
        {
            "layout-set-read": _plant(
                "hooks/root_whitelist.py", "\nx = STATES_CANON\n", append=True
            ),
            "no-verdict-call": _plant("features/spec_context/doctor.py", "x = 1\n"),
        },
    ),
}
