"""Policy checks: pytest tests behaviour only, so no test reads a tracked repo file.

A test, its helpers and its tables must not read a path rooted at ``__file__`` outside
``tests/fixtures/`` and ``tmp_path``, nor run ``git ls-files`` or ``git grep`` on the checkout.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from run import Check, Session, Tree


_READS = {"read_text", "read_bytes", "open", "exists", "is_file", "is_dir", "stat"}
_TREE = {"glob", "rglob", "iterdir", "scandir", "listdir"}
_GIT = {"ls-files", "grep"}
_EXEMPT = {"tmp_path", "tmp_path_factory"}
_SKIP = ("tests/fixtures/", "tests/helpers/", "tests/tmp/")


class _Scope:
    def __init__(self, node: ast.AST, parent: _Scope | None) -> None:
        self.node, self.parent = node, parent
        self.binds: dict[str, list[ast.expr]] = {}
        self.calls: list[ast.Call] = []
        self.returns: list[ast.expr] = []

    def bind(self, target: ast.AST, value: ast.expr | None) -> None:
        for n in ast.walk(target):
            if isinstance(n, ast.Name):
                self.binds.setdefault(n.id, [])
                if value is not None:
                    self.binds[n.id].append(value)

    def note(self, n: ast.AST) -> None:
        if isinstance(n, ast.Call):
            self.calls.append(n)
        elif isinstance(n, ast.Return) and n.value:
            self.returns.append(n.value)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                self.bind(t, n.value)
        elif isinstance(n, ast.AnnAssign) and n.value:
            self.bind(n.target, n.value)
        elif isinstance(n, ast.For | ast.AsyncFor | ast.comprehension):
            self.bind(n.target, n.iter)
        elif isinstance(n, ast.withitem) and n.optional_vars:
            self.bind(n.optional_vars, n.context_expr)


def _scopes(module: ast.Module) -> list[_Scope]:
    scopes = [top := _Scope(module, None)]

    def visit(n: ast.AST, sc: _Scope) -> None:
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
            sc.bind(ast.Name(n.name), None)
            for d in n.decorator_list:
                visit(d, sc)
            scopes.append(inner := _Scope(n, sc))
            for a in n.args.args + n.args.kwonlyargs:
                inner.binds.setdefault(a.arg, [])
            for stmt in n.body:
                visit(stmt, inner)
            return
        sc.note(n)
        for child in ast.iter_child_nodes(n):
            visit(child, sc)

    visit(module, top)
    return scopes


class _Taint:
    """Names rooted at ``__file__``, each with the route that reached it, to a fixpoint."""

    def __init__(self, module: ast.Module) -> None:
        self.scopes = _scopes(module)
        self.defs = {s.node.name: s for s in self.scopes if isinstance(s.node, ast.FunctionDef)}
        self.route: dict[tuple[int, str], str] = {}
        grew = True
        while grew:
            before = len(self.route)
            for sc in self.scopes:
                self._scan(sc)
            grew = len(self.route) > before

    def _set(self, sc: _Scope, name: str, route: str) -> None:
        self.route.setdefault((id(sc), name), route)

    def label(self, e: ast.AST, sc: _Scope) -> str | None:
        """The route of the first repo-rooted name in *e*; ``None`` when *e* is not repo-rooted."""
        nodes = list(ast.walk(e))
        if any(isinstance(n, ast.Constant) and n.value == "fixtures" for n in nodes):
            return None
        if any(isinstance(n, ast.Name) and n.id in _EXEMPT for n in nodes):
            return None
        for n in nodes:
            if isinstance(n, ast.Attribute) and n.attr == "__file__":
                return "module-file"
            if isinstance(n, ast.Name):
                if n.id == "__file__":
                    return ""
                at: _Scope | None = sc
                while at and n.id not in at.binds:
                    at = at.parent
                if at and (id(at), n.id) in self.route:
                    return self.route[id(at), n.id]
        return None

    def _scan(self, sc: _Scope) -> None:
        for name, values in sc.binds.items():
            for v in values:
                if (r := self.label(v, sc)) is not None:
                    self._set(sc, name, r)
        fn = sc.node
        if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef) and sc.parent:
            if any(self.label(r, sc) is not None for r in sc.returns):
                self._set(sc.parent, fn.name, "return")
            for d in fn.decorator_list:
                if (
                    isinstance(d, ast.Call)
                    and getattr(d.func, "attr", "") == "parametrize"
                    and len(d.args) > 1
                    and isinstance(d.args[0], ast.Constant)
                    and self.label(d.args[1], sc.parent) is not None
                ):
                    for name in str(d.args[0].value).split(","):
                        self._set(sc, name.strip(), "table")
        for call in sc.calls:
            if isinstance(call.func, ast.Name) and (callee := self.defs.get(call.func.id)):
                fn = callee.node
                assert isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
                pairs = list(zip([a.arg for a in fn.args.args], call.args, strict=False))
                pairs += [(k.arg, k.value) for k in call.keywords if k.arg]
                for param, arg in pairs:
                    if self.label(arg, sc) is not None:
                        self._set(callee, param, "helper")


def _hits(source: str) -> list[tuple[str, int, str]]:
    """``(sub-rule, line, expression)`` of every read of a repo-rooted path in *source*."""
    taint = _Taint(ast.parse(source))
    out = []
    for sc in taint.scopes:
        for call in sc.calls:
            f = call.func
            parts = [*call.args, *(k.value for k in call.keywords)]
            labels: list[str]
            if _git(call):
                cwd = next((k.value for k in call.keywords if k.arg == "cwd"), None)
                kind = "git"
                labels = (
                    [""] if cwd is None else [x for x in [taint.label(cwd, sc)] if x is not None]
                )
                if cwd is None and any(
                    isinstance(n, ast.Name) and n.id in _EXEMPT for n in ast.walk(call)
                ):
                    labels = []
            elif isinstance(f, ast.Attribute) and (
                f.attr in _READS | _TREE or ast.unparse(f) == "os.walk"
            ):
                kind = "tree" if f.attr in _TREE else ""
                labels = [x for p in [*parts, f.value] if (x := taint.label(p, sc)) is not None]
            elif isinstance(f, ast.Name) and f.id == "open":
                kind = ""
                labels = [x for p in parts if (x := taint.label(p, sc)) is not None]
            else:
                continue
            if not labels:
                continue
            tag = "constant" if sc.parent is None else (labels[0] if labels else "") or kind
            out.append(
                (f"repo-file-read{'-' + tag if tag else ''}", call.lineno, ast.unparse(call)[:60])
            )
    return out


def _git(call: ast.Call) -> bool:
    words = {
        e.value
        for a in call.args
        if isinstance(a, ast.List | ast.Tuple)
        for e in a.elts
        if isinstance(e, ast.Constant)
    }
    return "git" in words and bool(words & _GIT)


def policy_in_pytest(tree: Tree) -> list[str]:
    return [
        f"{row}: {p}:{line} reads {expr}"
        for p in tree.tracked("tests")
        if p.endswith(".py") and Path(p).name.startswith("test_") and not p.startswith(_SKIP)
        for row, line, expr in _hits(tree.read(p))
    ]


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


_ROOT = "from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[2]\n\n\n"

_CONTROL_TESTS = {
    "fixture": _ROOT
    + 'FIX = ROOT / "tests" / "fixtures"\n\n\n'
    + 'def test_fixture():\n    assert (FIX / "data.md").read_text()\n',
    "tmp_path": 'def test_tmp(tmp_path):\n    (tmp_path / "a.md").write_text("a")\n'
    + '    assert (tmp_path / "a.md").read_text()\n',
    "copy_and_run": "import shutil\nimport subprocess\nimport sys\n\n"
    + _ROOT
    + 'def test_copy(tmp_path):\n    shutil.copy(ROOT / "scripts" / "x.py", tmp_path / "x.py")\n'
    + '    subprocess.run([sys.executable, str(tmp_path / "x.py")], check=True)\n',
    "run_by_path": "import subprocess\nimport sys\n\n"
    + _ROOT
    + 'def test_run():\n    subprocess.run([sys.executable, str(ROOT / "scripts" / "x.py")], check=True)\n',
    "argument": _ROOT
    + "def test_argument():\n    from x import check\n\n"
    + '    assert check(ROOT / "scripts" / "x.py") == []\n',
    "git_in_tmp": "import subprocess\n\n\n"
    + 'def test_git(tmp_path):\n    subprocess.run(["git", "ls-files"], cwd=tmp_path, check=True)\n',
}


def CONTROL(root: Path) -> Session:
    """Every check green: tests that read only fixtures and ``tmp_path``, run scripts or
    pass a repo path as an argument, with violations only in an untracked, gitignored file."""
    _write(root, ".gitignore", "scratch/\n")
    _write(
        root, "scratch/tests/unit/test_x.py", _CONTROL_TESTS["fixture"].replace("FIX /", "ROOT /")
    )
    _write(root, "tests/fixtures/data.md", "data\n")
    for name, body in _CONTROL_TESTS.items():
        _write(root, f"tests/unit/test_{name}.py", body)
    return {}


def _plant(body: str) -> Callable[[Path], Session | None]:
    def plant(root: Path) -> None:
        CONTROL(root)
        _write(root, "tests/unit/test_planted.py", body)

    return plant


_PLANTS = {
    "repo-file-read": _ROOT
    + 'def test_law():\n    assert "x" in (ROOT / "AGENTS.md").read_text()\n',
    "repo-file-read-helper": _ROOT
    + "def _read(p):\n    return p.read_text()\n\n\n"
    + 'def test_law():\n    assert _read(ROOT / "AGENTS.md")\n',
    "repo-file-read-table": "import pytest\n\n"
    + _ROOT
    + 'DOCS = [ROOT / "AGENTS.md"]\n\n\n'
    + '@pytest.mark.parametrize("p", DOCS)\ndef test_law(p):\n    assert p.read_text()\n',
    "repo-file-read-git": "import subprocess\n\n\n"
    + "def test_files():\n"
    + '    out = subprocess.run(["git", "ls-files"], capture_output=True, check=True).stdout\n'
    + "    assert out\n",
    "repo-file-read-tree": "import ast\n\n"
    + _ROOT
    + 'def test_parse():\n    for p in ROOT.rglob("*.py"):\n        ast.parse(p.read_text())\n',
    "repo-file-read-module-file": "from pathlib import Path\n\nimport pkg\n\n\n"
    + 'def test_pkg():\n    assert (Path(pkg.__file__).parent / "AGENTS.md").read_text()\n',
    "repo-file-read-return": _ROOT
    + 'def _doc():\n    return ROOT / "AGENTS.md"\n\n\n'
    + "def test_law():\n    assert _doc().read_text()\n",
    "repo-file-read-constant": _ROOT
    + 'LAW = (ROOT / "AGENTS.md").read_text()\n\n\ndef test_law():\n    assert "x" in LAW\n',
}

CHECKS: dict[str, Check] = {
    "policy-in-pytest": (policy_in_pytest, {row: _plant(body) for row, body in _PLANTS.items()}),
}
