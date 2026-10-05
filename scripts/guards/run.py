"""The guard runner: every sibling module's ``CHECKS`` over the tree, or over its plants.

``python scripts/guards/run.py`` runs each check on the checkout and exits 1 on any red;
``--planted`` runs each check over its module's ``CONTROL`` (a healthy tree whose only
violations sit in an untracked, gitignored file), where green is required, and over every
planted violation in a temp git tree, where red on the row's own sub-rule is required.
A check is ``(fn, plants)``: ``fn(tree)`` returns violation messages, each opening with
the sub-rule it names; a plant writes its violation under a root and may return the
session report the check reads instead of the live probe.
"""

from __future__ import annotations

import importlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TIERS = ("unit", "contract", "integration", "e2e")

Session = dict[str, Any]
Plant = Callable[[Path], Session | None]
Check = tuple[Callable[["Tree"], list[str]], dict[str, Plant]]

_CI = "scripts/ci.py"  # the Linux CI jobs (T-050-190)


def tracked(root: Path, *spec: str) -> list[str]:
    """Every git-tracked path under *spec*: the one enumerator. A scratch file another
    process writes under ``tests/tmp/`` is never in it (bugs 465, 467)."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *spec], cwd=root, capture_output=True, check=True
    ).stdout.decode()
    return sorted(p for p in out.split("\0") if p)


# The probe plugin: records what the repo conftest did to real items of every tier and to
# a planted explicit timeout, catches a collection refusal, then runs only the probe file.
_PLUGIN = """
import json, os
from pathlib import Path
import pytest

ROOT, PROBE = Path(os.environ["GUARD_ROOT"]), os.environ["GUARD_PROBE"]
REPORT = {"tiers": {}, "explicit": None, "refusal": None, "props": {}, "failed": []}


def _timeout(item):
    m = item.get_closest_marker("timeout")
    return m.args[0] if m and m.args else None


@pytest.hookimpl(wrapper=True)
def pytest_collection_modifyitems(config, items):
    planted = next(i for i in items if "/tests/contract/" in i.path.as_posix())
    own = {id(i) for i in items if i.get_closest_marker("timeout")}
    planted.add_marker(pytest.mark.timeout(45))
    try:
        yield
    except pytest.UsageError as exc:
        REPORT["refusal"] = str(exc)
    REPORT["explicit"] = _timeout(planted)
    for item in items:
        if item is not planted and id(item) not in own:
            REPORT["tiers"].setdefault(item.path.relative_to(ROOT).parts[1], _timeout(item))
    config.hook.pytest_deselected(items=[i for i in items if str(i.path) != PROBE])
    items[:] = [i for i in items if str(i.path) == PROBE]


def pytest_runtest_logreport(report):
    REPORT["props"].update(dict(report.user_properties))
    if report.failed:
        REPORT["failed"].append(report.nodeid)


def pytest_sessionfinish(session):
    Path(os.environ["GUARD_REPORT"]).write_text(json.dumps(REPORT), encoding="utf-8")
"""


def probe(root: Path, modules: list[Any]) -> Session:
    """ONE pytest session under the repo conftest: the first tracked test file of each tier
    plus a generated probe of every module's ``PROBE`` tests. Its report, plus the
    session's stderr and seconds, is what every session check reads."""
    firsts: dict[str, str] = {}
    for path in tracked(root, *(f"tests/{t}" for t in TIERS)):
        if Path(path).name.startswith("test_"):
            firsts.setdefault(Path(path).parts[1], path)
    probe_file = root / "tests" / "tmp" / f"_guard_probe_{os.getpid()}.py"
    probe_file.write_text("\n\n".join(m.PROBE for m in modules if hasattr(m, "PROBE")), "utf-8")
    with tempfile.TemporaryDirectory(prefix="guard-probe-") as tmp:
        (Path(tmp) / "_guard_probe.py").write_text(_PLUGIN, encoding="utf-8")
        report = Path(tmp) / "report.json"
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([tmp, str(root)]),
            "GUARD_ROOT": str(root),
            "GUARD_PROBE": str(probe_file),
            "GUARD_REPORT": str(report),
        }
        argv = [sys.executable, "-m", "pytest", "-q", "-s", "-p", "no:xdist", "-p", "_guard_probe"]
        start = time.monotonic()
        try:
            result = subprocess.run(
                [*argv, *firsts.values(), str(probe_file)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )
        finally:
            probe_file.unlink(missing_ok=True)
        seconds = time.monotonic() - start
        session: Session = json.loads(report.read_text("utf-8")) if report.is_file() else {}
    session.update(stderr=result.stderr, seconds=seconds, output=result.stdout[-3000:])
    return session


class Tree:
    """What a check reads: a root, its tracked paths, and the probe session (lazy, once)."""

    def __init__(self, root: Path, modules: list[Any], session: Session | None = None) -> None:
        self.root, self._modules, self._session = root, modules, session

    def tracked(self, *spec: str) -> list[str]:
        return tracked(self.root, *spec)

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def ci_jobs(self) -> dict[str, list[Any]]:
        """``scripts/ci.py``'s ``JOBS`` (stdlib-only, loads without running); none untracked."""
        return runpy.run_path(str(self.root / _CI))["JOBS"] if self.tracked(_CI) else {}

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = probe(self.root, self._modules)
            print(f"probe session: {self._session['seconds']:.1f}s")
            if "tiers" not in self._session or self._session.get("failed"):
                print(self._session["output"], self._session["stderr"][-3000:])
        return self._session


def modules() -> list[Any]:
    """Every sibling module that declares ``CHECKS``."""
    sys.path.insert(0, str(HERE))
    found = (
        importlib.import_module(p.stem) for p in sorted(HERE.glob("*.py")) if p != HERE / "run.py"
    )
    return [m for m in found if hasattr(m, "CHECKS")]


def checks(mods: list[Any]) -> Iterator[tuple[str, Check]]:
    for mod in mods:
        yield from mod.CHECKS.items()


def run_tree(mods: list[Any]) -> int:
    tree, red = Tree(ROOT, mods), 0
    for cid, (fn, _) in checks(mods):
        violations = fn(tree)
        red += bool(violations)
        print(f"{'FAIL' if violations else 'PASS'} {cid}")
        for v in violations:
            print(f"  {cid}: {v}")
    return 1 if red else 0


def _judge(mods: list[Any], fn: Callable[[Tree], list[str]], plant: Plant) -> list[str]:
    """*fn* over a temp git tree holding *plant*'s files, everything but ignores staged."""
    with tempfile.TemporaryDirectory(prefix="guard-plant-") as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        session = plant(root)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        return fn(Tree(root, mods, session or {}))


def run_planted(mods: list[Any]) -> int:
    """Each module's ``CONTROL`` must leave every check green; each plant must turn its
    check red on the sub-rule the row names."""
    missed = 0
    for mod in mods:
        for cid, (fn, plants) in mod.CHECKS.items():
            noise = _judge(mods, fn, mod.CONTROL)
            missed += bool(noise)
            print(f"{'NOISY' if noise else 'GREEN'} {cid} [control]: {(noise or [''])[0]}")
            for row, plant in plants.items():
                hit = [v for v in _judge(mods, fn, plant) if v.startswith(f"{row}:")]
                missed += not hit
                print(f"{'RED' if hit else 'MISSED'} {cid} [{row}]: {(hit or [''])[0]}")
    return 1 if missed else 0


def main(argv: list[str]) -> int:
    mods = modules()
    return run_planted(mods) if "--planted" in argv else run_tree(mods)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
