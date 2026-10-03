"""Isolation checks: no test reaches a real workspace, ages a fixture by the real clock
against a frozen one, or fakes the harness env a hook receives.

``no-real-workspace`` and ``no-instance-reach`` read the runner's one probe session, never
this process; ``PROBE`` is this module's share of the probe file. The fixture's
``ALLOWLISTED_DADAIA_ENV`` and ``HOOK_MODULES`` are read from their ``frozenset({...})``
literals with ``ast``, never imported.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from run import Check, Session, Tree

FIXTURE = "tests/fixtures/harness_env.py"
_SETS = ("ALLOWLISTED_DADAIA_ENV", "HOOK_MODULES")
_NO_WORKSPACE = "WorkspaceNotInitializedError"

PROBE = """
def test_guard_no_real_workspace(record_property):
    from pathlib import Path
    from typer.testing import CliRunner
    from dadaia_workspace.cli.main import app
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    try:
        walk = str(resolve_workspace_root())
    except Exception as exc:
        walk = type(exc).__name__
    doctor = CliRunner().invoke(app, ["doctor"])
    record_property("workspace", {
        "walk": walk,
        "cwd": str(Path.cwd().resolve()),
        "doctor": [doctor.exit_code, "No initialized workspace found" in doctor.output],
    })


def test_guard_no_instance_reach(tmp_path, record_property):
    import os, subprocess, sys
    from pathlib import Path

    sentinel = Path(".dadaia") / "states" / "spec_contexts.json"
    ws = tmp_path / "instance"
    (ws / sentinel).parent.mkdir(parents=True)
    (ws / sentinel).write_text("{}", encoding="utf-8")
    (ws / "repos" / "x").mkdir(parents=True)
    own = os.environ.get("DADAIA_FENCED_ROOTS", "")

    def child(code, cwd, fence):
        env = {**os.environ, "DADAIA_FENCED_ROOTS": os.pathsep.join(filter(None, (own, fence)))}
        r = subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env,
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return r.stdout.strip()
        return "refused" if "No initialized workspace" in r.stderr else r.stderr[-300:]

    walk = "from dadaia_workspace.core.workspace_resolver import resolve_workspace_root as r; print(r())"
    named = ("from dadaia_workspace.core.workspace_resolver import resolve_cli_workspace_root as r;"
             f"import pathlib; print(r(pathlib.Path({str(ws)!r})))")
    acting = ("import os, pathlib as p; from dadaia_workspace.core.invocation import resolve as r;"
              "print(r(env=os.environ, cwd=p.Path.cwd(), target_path=p.Path('f')).workspace_root)")
    inner = ws / "repos" / "x"
    checkout = Path(__file__).resolve().parents[2]
    record_property("instance", {
        "ws": str(ws.resolve()),
        "open": child(walk, inner, ""),
        "fenced": child(walk, inner, str(ws)),
        "named": child(named, tmp_path, str(ws)),
        "acting": child(acting, inner, str(ws)),
        "enclosing": sorted(str(p) for p in checkout.parents if (p / sentinel).is_file()),
        "fenced_roots": sorted(filter(None, own.split(os.pathsep))),
    })
"""


def _props(tree: Tree, key: str) -> dict[str, Any] | None:
    props: dict[str, dict[str, Any]] = tree.session.get("props", {})
    return props.get(key)


def no_real_workspace(tree: Tree) -> list[str]:
    p = _props(tree, "workspace")
    if p is None:
        return ["probe-broke: the workspace probe recorded nothing"]
    out = []
    if p["walk"] != _NO_WORKSPACE:
        out.append(f"cwd-walk: a test's cwd walk resolved {p['walk']}")
    if Path(str(p["cwd"])).is_relative_to(tree.root.resolve()):
        out.append(f"outside-checkout: a test starts in {p['cwd']}, inside the checkout")
    exit_code, refused = p["doctor"]
    if not refused:
        out.append("bare-doctor: a bare doctor did not refuse with no workspace found")
    if exit_code != 1:
        out.append(f"doctor-exit: a bare doctor exited {exit_code}, not 1")
    return out


def no_instance_reach(tree: Tree) -> list[str]:
    p = _props(tree, "instance")
    if p is None:
        return ["probe-broke: the instance probe recorded nothing"]
    out = []
    if p["open"] != p["ws"]:
        out.append(f"open-child: an unfenced child resolved {p['open']!r}, not {p['ws']}")
    for row, key, refused in (
        ("fenced-child", "fenced", "refused"),
        ("named-root", "named", "refused"),
        ("acting-root", "acting", "None"),
    ):
        if p[key] != refused:
            out.append(f"{row}: a child under a fenced instance gave {p[key]!r}")
    unfenced = sorted(set(p["enclosing"]) - set(p["fenced_roots"]))
    if unfenced:
        out.append(f"every-instance-fenced: the suite leaves {unfenced} unfenced")
    return out


# --- frozen-clock -------------------------------------------------------------------------

_CONSTANT = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
_CLOCK_MARKERS = ("NOW", "FROZEN", "EPOCH", "TIMESTAMP")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _tail(node: ast.expr) -> str | None:
    return node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)


def _frozen_kind(name: str, value: ast.expr) -> str | None:
    """A constructed ``datetime``/``date`` is frozen whatever its name; a number or an ISO
    string only under a clock-marked name (``_TIMEOUT_S = 60`` is no clock)."""
    if isinstance(value, ast.Call):
        callee = _tail(value.func)
        return f"{callee}-call" if callee in ("datetime", "date") else None
    v = value.value if isinstance(value, ast.Constant) else None
    number = isinstance(v, (int, float)) and not isinstance(v, bool)
    if not (number or (isinstance(v, str) and _ISO_DATE.match(v))):
        return None
    return next((f"{m.lower()}-name" for m in _CLOCK_MARKERS if m in name), None)


def _frozen(module: ast.Module) -> list[tuple[str, str, int]]:
    """``(kind, name, line)`` per module-level frozen-clock constant."""
    found = []
    for node in module.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        for t in targets:
            if (
                isinstance(t, ast.Name)
                and _CONSTANT.match(t.id)
                and (kind := _frozen_kind(t.id, value))
            ):
                found.append((kind, t.id, node.lineno))
    return found


def _real_clock(module: ast.Module) -> list[int]:
    """Lines of ``<name>.time()`` and ``….datetime.now()`` calls: call sites, never prose."""
    return sorted(
        n.lineno
        for n in ast.walk(module)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and (
            (n.func.attr == "time" and isinstance(n.func.value, ast.Name))
            or (n.func.attr == "now" and _tail(n.func.value) == "datetime")
        )
    )


def frozen_clock(tree: Tree) -> list[str]:
    """No test file freezes a clock constant AND reads the real clock: the two drift apart
    at wall-clock rate until an assertion margin erodes (the tmp_gc midnight failure)."""
    out = []
    for p in tree.tracked("tests"):
        if not p.endswith(".py"):
            continue
        module = ast.parse(tree.read(p))
        if clock := _real_clock(module):
            out += [
                f"{kind}: {p} freezes {name}:{line} and reads the real clock at {clock}"
                for kind, name, line in _frozen(module)
            ]
    return out


# --- the harness-env fixture --------------------------------------------------------------


def _str(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _fixture_sets(tree: Tree) -> tuple[dict[str, set[str]], list[str]]:
    """The fixture's two sets, from each ``NAME = frozenset({...})`` set-literal argument."""
    source = tree.read(FIXTURE) if tree.tracked(FIXTURE) else ""
    sets: dict[str, set[str]] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.AnnAssign):
            continue
        target, value = node.target, node.value
        if (
            isinstance(target, ast.Name)
            and target.id in _SETS
            and isinstance(value, ast.Call)
            and _tail(value.func) == "frozenset"
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Set)
        ):
            sets[target.id] = {s for e in value.args[0].elts if (s := _str(e))}
    return sets, [
        f"fixture-unreadable: {FIXTURE} has no {n}: … = frozenset({{...}})"
        for n in _SETS
        if not sets.get(n)
    ]


def _suite(tree: Tree) -> dict[str, ast.Module]:
    return {
        p: ast.parse(tree.read(p))
        for p in tree.tracked("tests")
        if p.endswith(".py") and p != FIXTURE
    }


def _is_env(node: ast.expr) -> bool:
    return _tail(node) == "environ"


def _env_writes(module: ast.Module) -> list[tuple[str, str | None]]:
    """``(form, name)`` per ``environ[k] =``, ``setenv``, ``environ.setdefault``,
    ``setitem(environ, k, …)`` and ``environ.update({...})``."""
    out: list[tuple[str, str | None]] = []
    for n in ast.walk(module):
        if isinstance(n, ast.Assign):
            out += [
                ("environ-item", _str(t.slice))
                for t in n.targets
                if isinstance(t, ast.Subscript) and _is_env(t.value)
            ]
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.args:
            attr, recv, args = n.func.attr, n.func.value, n.args
            if attr == "setenv":
                out.append(("setenv", _str(args[0])))
            elif attr == "setdefault" and _is_env(recv):
                out.append(("setdefault", _str(args[0])))
            elif attr == "setitem" and len(args) >= 2 and _is_env(args[0]):
                out.append(("setitem", _str(args[1])))
            elif attr == "update" and _is_env(recv) and isinstance(args[0], ast.Dict):
                out += [("update", _str(k)) for k in args[0].keys if k is not None]
    return out


def harness_env_allowlist(tree: Tree) -> list[str]:
    """A test writes only the ``DADAIA_*`` production reads by design (the fixture's
    allowlist); every ``HOOK_MODULES`` entry is a tracked hook module."""
    sets, out = _fixture_sets(tree)
    allowed = sets.get("ALLOWLISTED_DADAIA_ENV", set())
    out += [
        f"stale-hook-module: HOOK_MODULES names {m}, no dadaia_workspace/hooks/{m}.py"
        for m in sorted(sets.get("HOOK_MODULES", set()))
        if not tree.tracked(f"dadaia_workspace/hooks/{m}.py")
    ]
    for p, module in _suite(tree).items():
        out += [
            f"{form}: {p} writes {name}, outside ALLOWLISTED_DADAIA_ENV"
            for form, name in _env_writes(module)
            if name and name.startswith("DADAIA_") and name not in allowed
        ]
    return out


def _hook_imports(module: ast.Module, hooks: set[str]) -> str | None:
    for n in ast.walk(module):
        if (
            isinstance(n, ast.ImportFrom)
            and n.module == "dadaia_workspace.hooks"
            and {a.name for a in n.names} & hooks
        ):
            return "from-import"
        if isinstance(n, ast.Import) and any(
            a.name.startswith("dadaia_workspace.hooks.") and a.name.split(".")[2] in hooks
            for a in n.names
        ):
            return "module-import"
    return None


def _patches_stdin(module: ast.Module) -> bool:
    """``setattr("sys.stdin", …)`` or ``setattr(sys, "stdin", …)``."""
    for n in ast.walk(module):
        if isinstance(n, ast.Call) and _tail(n.func) == "setattr" and len(n.args) >= 2:
            a = n.args
            if _str(a[0]) == "sys.stdin" or (_tail(a[0]) == "sys" and _str(a[1]) == "stdin"):
                return True
    return False


def hook_stdin_not_in_process(tree: Tree) -> list[str]:
    """A hook's behaviour runs in a child (``run_hook_subprocess``), never by importing it
    and patching ``sys.stdin`` in-process."""
    sets, out = _fixture_sets(tree)
    hooks = sets.get("HOOK_MODULES", set())
    for p, module in _suite(tree).items():
        if (form := _hook_imports(module, hooks)) and _patches_stdin(module):
            out.append(f"{form}: {p} drives a hook through a patched sys.stdin")
    return out


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------

_ROOT = Path(__file__).resolve().parent.parent.parent


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def _healthy() -> Session:
    ws = "/elsewhere/instance"
    return {
        "props": {
            "workspace": {"walk": _NO_WORKSPACE, "cwd": "/elsewhere", "doctor": [1, True]},
            "instance": {
                "ws": ws,
                "open": ws,
                "fenced": "refused",
                "named": "refused",
                "acting": "None",
                "enclosing": ["/outer"],
                "fenced_roots": ["/outer", "/venv-instance"],
            },
        }
    }


def _session(key: str, **change: object) -> Callable[[Path], Session]:
    def plant(root: Path) -> Session:
        s = _healthy()
        s["props"][key] = {**s["props"][key], **change}
        return s

    return plant


def _fixture_copy(root: Path, old: str = "", new: str = "", tail: str = "") -> None:
    """The real fixture, one literal replaced: the reader is proven on the true shape."""
    text = (_ROOT / FIXTURE).read_text(encoding="utf-8")
    if old:
        assert old in text, f"{FIXTURE} lost {old!r}"
        text = text.replace(old, new, 1)
    _write(root, FIXTURE, text + tail)
    for hook in (_ROOT / "dadaia_workspace" / "hooks").glob("*.py"):
        _write(root, f"dadaia_workspace/hooks/{hook.name}", "")


_CONTROL_TEST = """
import os, sys, time
from datetime import datetime
from dadaia_workspace.hooks import _common, HOOK

_NOW = datetime(2026, 8, 18)

def age(monkeypatch, path):
    os.utime(path, (_NOW.timestamp(), _NOW.timestamp()))
    monkeypatch.setenv("DADAIA_CONTEXT", "c")
    os.environ["HOME"] = "/h"
    os.environ.update({"DADAIA_MODE": "read"})
    monkeypatch.setattr(sys, "argv", [])
    clock.now()
    datetime.fromtimestamp(0)
    monkeypatch.setitem(config, "DADAIA_X", 1)
    config.update({"DADAIA_X": 1})
"""

_CONTROL_CLOCK = """
import time
_TIMEOUT_S = 60
_NOW_ON = True
now = __import__("datetime").datetime(2026, 1, 1)

def deadline():
    _NOW = 0.0
    return time.time() + _TIMEOUT_S
"""

_CONTROL_STDIN = """
import sys
import dadaia_workspace.hooks._common
from dadaia_workspace.hooks import _common

def test(monkeypatch):
    monkeypatch.setattr(sys, "stdin", None)
"""

_VIOLATOR = """
import io, os, time
from datetime import datetime
from dadaia_workspace.hooks import HOOK
_NOW = datetime(2026, 1, 1)
os.environ["DADAIA_PERSONA"] = time.time()
def t(m):
    m.setattr("sys.stdin", io.StringIO())
"""


def CONTROL(root: Path) -> Session:
    """Every check green: a healthy session, near-miss shapes tracked, and every violation
    only in an untracked, gitignored ``tests/tmp/x.py`` (bugs 465, 467) or in the fixture
    itself, the one module that may write any ``DADAIA_*``."""
    _write(root, ".gitignore", "tests/tmp/*\n")
    _write(root, "tests/tmp/x.py", _VIOLATOR.replace("HOOK", _hook()))
    _fixture_copy(root, tail='\nos.environ["DADAIA_PERSONA"] = "x"\n')
    _write(root, "tests/unit/test_frozen_alone.py", _CONTROL_TEST.replace("HOOK", _hook()))
    _write(root, "tests/unit/test_clock_alone.py", _CONTROL_CLOCK)
    _write(root, "tests/unit/test_stdin_common.py", _CONTROL_STDIN)
    return _healthy()


def _plant(rel: str, text: str) -> Callable[[Path], Session]:
    def plant(root: Path) -> Session:
        session = CONTROL(root)
        _write(root, rel, text.replace("HOOK", _hook()) if "HOOK" in text else text)
        return session

    return plant


def _hooks_literal() -> tuple[str, ast.expr]:
    """The real fixture's text and its ``HOOK_MODULES`` set literal."""
    text = (_ROOT / FIXTURE).read_text(encoding="utf-8")
    return text, next(
        n.value.args[0]
        for n in ast.parse(text).body
        if isinstance(n, ast.AnnAssign)
        and _tail(n.target) == "HOOK_MODULES"
        and isinstance(n.value, ast.Call)
    )


def _hook() -> str:
    """Any member of the real ``HOOK_MODULES``, read at plant time, never at import."""
    return str(min(ast.literal_eval(_hooks_literal()[1])))


def _plant_hooks(rewrite: Callable[[str], str]) -> Callable[[Path], Session]:
    """The real fixture with only ``HOOK_MODULES``'s set literal rewritten, wherever ruff
    lays it out: the guard names no hook member."""

    def plant(root: Path) -> Session:
        session = CONTROL(root)
        text, literal = _hooks_literal()
        segment = ast.get_source_segment(text, literal) or ""
        _fixture_copy(root, segment, rewrite(segment))
        return session

    return plant


def _clock(frozen: str, call: str = "time.time()") -> Callable[[Path], Session]:
    return _plant("tests/unit/test_p.py", f"import time\n{frozen}\ndef age():\n    return {call}\n")


def _env(write: str) -> Callable[[Path], Session]:
    return _plant("tests/unit/test_env.py", f"import os\ndef t(monkeypatch):\n    {write}\n")


_UNREADABLE = _plant_hooks(lambda s: f"[{s[1:-1]}]")

CHECKS: dict[str, Check] = {
    "no-real-workspace": (
        no_real_workspace,
        {
            "cwd-walk": _session("workspace", walk="/srv/op/instance"),
            "outside-checkout": lambda root: _session("workspace", cwd=str(root.resolve()))(root),
            "bare-doctor": _session("workspace", doctor=[1, False]),
            "doctor-exit": _session("workspace", doctor=[0, True]),
            "probe-broke": lambda root: {},
        },
    ),
    "no-instance-reach": (
        no_instance_reach,
        {
            "open-child": _session("instance", open="refused"),
            "fenced-child": _session("instance", fenced="/elsewhere/instance"),
            "named-root": _session("instance", named="/elsewhere/instance"),
            "acting-root": _session("instance", acting="/elsewhere/instance"),
            "every-instance-fenced": _session("instance", fenced_roots=["/venv-instance"]),
            "probe-broke": lambda root: {},
        },
    ),
    "frozen-clock": (
        frozen_clock,
        {
            "datetime-call": _clock(
                "import datetime as dt\n_X = dt.datetime(2026, 1, 1)", "dt.datetime.now()"
            ),
            "date-call": _clock("from datetime import date\n_X = date(2026, 1, 1)"),
            "now-name": _clock("_NOW = '2026-01-01T00:00Z'"),
            "frozen-name": _clock("_FROZEN_TS: float = 1.7e9"),
            "epoch-name": _clock("_EPOCH_S = 0"),
            "timestamp-name": _clock("_START_TIMESTAMP = '2026-01-01'"),
        },
    ),
    "harness-env-allowlist": (
        harness_env_allowlist,
        {
            "fixture-unreadable": _UNREADABLE,
            "stale-hook-module": _plant_hooks(lambda s: '{"gone_hook", ' + s[1:]),
            "environ-item": _env('os.environ["DADAIA_PERSONA"] = "x"'),
            "setenv": _env('monkeypatch.setenv("DADAIA_PERSONA", "x")'),
            "setdefault": _env('os.environ.setdefault("DADAIA_PERSONA", "x")'),
            "setitem": _env('monkeypatch.setitem(os.environ, "DADAIA_PERSONA", "x")'),
            "update": _env('os.environ.update({"DADAIA_PERSONA": "x"})'),
        },
    ),
    "hook-stdin-not-in-process": (
        hook_stdin_not_in_process,
        {
            "fixture-unreadable": _UNREADABLE,
            "from-import": _plant(
                "tests/unit/test_h.py",
                "import io\nfrom dadaia_workspace.hooks import HOOK\n"
                "def t(m):\n    m.setattr('sys.stdin', io.StringIO())\n",
            ),
            "module-import": _plant(
                "tests/unit/test_h.py",
                "import io, sys\nimport dadaia_workspace.hooks.HOOK\n"
                "def t(m):\n    m.setattr(sys, 'stdin', io.StringIO())\n",
            ),
        },
    ),
}
