"""Suite checks: what the test suite and its conftest must hold (QUALITY P-21, P-22, P-23).

The session checks read the runner's one probe session, never this process; ``PROBE`` is
this module's share of the probe file, run there under the repo conftest.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from run import _CI

if TYPE_CHECKING:
    from collections.abc import Callable

    from run import Check, Session, Tree

# P-23 ceilings, measured on this tree; ratchet DOWN ONLY, target 0. Lower them in the
# commit that removes an import; raising one is never a ratchet move.
PRIVATE_IMPORT_STATEMENTS = 37
PRIVATE_IMPORT_FILES = 34
_ALLOW = "# allow-private-import:"

# P-21: the tier table on Linux and macOS; the conftest calibrates once for Windows.
TIER_SECONDS = {"small": 10, "medium": 60, "e2e": 120}
CALIBRATION = {
    "small linux False": 10,
    "small win32 False": 30,
    "medium darwin False": 60,
    "e2e win32 False": 360,
    "slow win32 False": None,
    "small linux True": 20,
    "small win32 True": 60,
}

_CITATION = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)+#[A-Za-z]*\d+(?:[.-]\d+)?")
_RUN_PYTEST = re.compile(r"^\s*(?:-\s*)?run:\s*(.*\bpytest\s.*)$", re.M)
_SELECTOR = re.compile(r"""-m\s+(["'])(.*?)\1""")
_REAL_CI = Path(__file__).resolve().parents[2] / _CI

PROBE = (
    f"KEYS = {list(CALIBRATION)!r}\n"
    + """
import pytest


@pytest.mark.quarantine(bug="guard-probe")
def test_guard_quarantine_with_bug():
    pass


@pytest.mark.quarantine
def test_guard_quarantine_naked():
    pass


def test_guard_calibration(record_property):
    from tests import conftest

    record_property("calibration", {
        key: conftest.tier_timeout_seconds(key.split()[0], platform=key.split()[1], coverage=key.split()[2] == "True")
        for key in KEYS
    })


@pytest.mark.medium
def test_guard_push_starts_no_gc(tmp_path, record_property):
    import os, re, subprocess

    def git(*args, env=None):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, env=env)

    trace = tmp_path / "trace.json"
    git("init", "-q", "--bare", "b.git")
    git("init", "-q", "s")
    (tmp_path / "s" / "f").write_text("f\\n", encoding="utf-8")
    git("-C", "s", "add", "f")
    git("-C", "s", "commit", "-qm", "f")
    git("-C", "s", "push", "-q", (tmp_path / "b.git").as_uri(), "HEAD:refs/heads/m",
        env={**os.environ, "GIT_TRACE2_EVENT": str(trace)})
    record_property("push_gc", re.findall(r'"argv":\\[[^\\]]*"(?:gc|maintenance)"', trace.read_text()))
"""
)


def _private_imports(source: str) -> int:
    """``from dadaia_workspace... import _name`` statements without the allow marker."""
    lines, count = source.splitlines(), 0
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.ImportFrom) and (node.module or "").startswith("dadaia_workspace")
        ):
            continue
        if not any(a.name.startswith("_") and not a.name.startswith("__") for a in node.names):
            continue
        span = lines[node.lineno - 1 : node.end_lineno or node.lineno]
        count += not any(_ALLOW in line for line in span)
    return count


def private_import_ratchet(tree: Tree) -> list[str]:
    counts = [
        n
        for p in tree.tracked("tests")
        if p.endswith(".py")
        if (n := _private_imports(tree.read(p)))
    ]
    out = []
    if sum(counts) > PRIVATE_IMPORT_STATEMENTS:
        out.append(
            f"statement-ceiling: {sum(counts)} private-symbol imports > {PRIVATE_IMPORT_STATEMENTS}"
        )
    if len(counts) > PRIVATE_IMPORT_FILES:
        out.append(
            f"file-ceiling: {len(counts)} files with private-symbol imports > {PRIVATE_IMPORT_FILES}"
        )
    return out


def tracked_suite_only(tree: Tree) -> list[str]:
    scratch = [p for p in tree.tracked("tests/tmp") if p != "tests/tmp/README.md"]
    return [f"tracked-scratch: {p} is tracked under tests/tmp/" for p in scratch]


def tier_timeout(tree: Tree) -> list[str]:
    s, factor = tree.session, 3 if sys.platform == "win32" else 1
    tiers = s.get("tiers")
    if not tiers:
        return ["probe-broke: the probe session reported no tier timeouts"]
    out = []
    if s.get("explicit") != 45:
        out.append(f"explicit-kept: a planted timeout(45) became {s.get('explicit')}")
    wrong = {t: tiers.get(t) for t in TIER_SECONDS if tiers.get(t) != TIER_SECONDS[t] * factor}
    if wrong:
        out.append(f"four-tiers: {wrong} differ from {TIER_SECONDS} (x{factor})")
    if s.get("props", {}).get("calibration") != CALIBRATION:
        out.append(
            f"calibrated-ceiling: tier_timeout_seconds gives {s.get('props', {}).get('calibration')}"
        )
    return out


def quarantine_needs_bug(tree: Tree) -> list[str]:
    s, out = tree.session, []
    if "refusal" not in s:
        out.append("probe-broke: the probe session reported no collection outcome")
    refusal = s.get("refusal") or ""
    if "test_guard_quarantine_with_bug" in refusal:
        out.append("collected-with-bug: quarantine(bug=...) refused collection")
    if (
        "test_guard_quarantine_naked" not in refusal
        or "requires a registered bug id" not in refusal
    ):
        out.append(f"refused-without-bug: a bare quarantine mark was collected ({refusal!r})")
    if "[quarantine-discipline]" not in s.get("stderr", ""):
        out.append("actionable-on-stderr: the refusal is not printed to stderr before it raises")
    for wf in tree.tracked(".github/workflows"):
        for cmd in _RUN_PYTEST.findall(tree.read(wf)):
            selector = _SELECTOR.search(cmd)
            if not selector or "not quarantine" not in selector.group(2):
                out.append(f"selector-lacks-not-quarantine: {wf} runs `{cmd.strip()}`")
    # scripts/ci.py's pytest steps, [python, -m, pytest, ...]: the selector is the next -m's
    # (no step at all: onboarding-journey-uv's e2e-runs-journey is red)
    steps = [s for job in tree.ci_jobs().values() for s in job if "pytest" in s[1]]
    for name, cmd, _ in steps:
        if "not quarantine" not in (cmd[cmd.index("-m", 3) + 1] if "-m" in cmd[3:] else ""):
            out.append(f"selector-lacks-not-quarantine: {_CI} step {name}")
    return out


def statement_id_cited(tree: Tree) -> list[str]:
    ids = json.loads(tree.read("tests/fixtures/statement_ids.json"))
    known = {f"{bug}#{sid}" for bug, sids in ids.items() for sid in sids}
    known |= set(_CITATION.findall(tree.read("specs/memory/QUALITY.md")))
    return [
        f"unknown-id: {p} cites {cid}"
        for p in tree.tracked("tests")
        if p.endswith(".py")
        for cid in sorted(set(_CITATION.findall(tree.read(p))) - known)
    ]


def push_starts_no_gc(tree: Tree) -> list[str]:
    spawned = tree.session.get("props", {}).get("push_gc")
    if spawned is None:
        return ["probe-broke: the push probe recorded nothing"]
    return [f"gc-spawned: a local push under the suite env started {spawned}"] if spawned else []


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def _healthy() -> Session:
    return {
        "tiers": dict(TIER_SECONDS),
        "explicit": 45,
        "refusal": "tests/tmp/p.py::test_guard_quarantine_naked: ... requires a registered bug id",
        "stderr": "[quarantine-discipline]",
        "props": {"calibration": dict(CALIBRATION), "push_gc": []},
    }


def _session(**change: object) -> Callable[[Path], Session]:
    return lambda root: {**_healthy(), **change}


def CONTROL(root: Path) -> Session:
    """Every check green: a healthy session, and violations only in an untracked,
    gitignored ``tests/tmp/x.py`` (bugs 465, 467: untracked stays out)."""
    _write(root, ".gitignore", "tests/tmp/*\n")
    _write(root, "tests/tmp/x.py", _IMPORT * 99 + "# sa-no-such-bug#S99\n")
    _write(root, "tests/fixtures/statement_ids.json", '{"sa-known-bug": ["S1"]}')
    _write(root, "specs/memory/QUALITY.md", "cites sa-quality-bug#Q1\n")
    _write(root, "tests/unit/test_c.py", "# sa-known-bug#S1 sa-quality-bug#Q1\n" + _ALLOWED * 99)
    _write(root, ".github/workflows/ci.yml", 'run: pytest -m "unit and not quarantine"\n')
    _write(root, _CI, _REAL_CI.read_text("utf-8"))
    return _healthy()


def _plant_imports(files: int, per_file: int) -> Callable[[Path], Session]:
    def plant(root: Path) -> Session:
        for i in range(files):
            _write(root, f"tests/unit/test_p{i}.py", _IMPORT * per_file)
        return CONTROL(root)

    return plant


def _plant_scratch(root: Path) -> None:
    _write(root, "tests/tmp/x.py", "x = 1\n")  # no .gitignore: the scratch file is tracked


def _plant_selector(root: Path) -> Session:
    session = CONTROL(root)
    _write(root, _CI, _REAL_CI.read_text("utf-8").replace("slow and not quarantine", "slow"))
    return session


def _plant_citation(root: Path) -> None:
    CONTROL(root)
    _write(root, "tests/unit/test_c.py", "# sa-no-such-bug#S99\n")


_IMPORT = "from dadaia_workspace.core import _x\n"
_ALLOWED = "from dadaia_workspace.core import _x  # allow-private-import: documented\n"

CHECKS: dict[str, Check] = {
    "private-import-ratchet": (
        private_import_ratchet,
        {
            "statement-ceiling": _plant_imports(1, PRIVATE_IMPORT_STATEMENTS + 1),
            "file-ceiling": _plant_imports(PRIVATE_IMPORT_FILES + 1, 1),
        },
    ),
    "tracked-suite-only": (tracked_suite_only, {"tracked-scratch": _plant_scratch}),
    "tier-timeout": (
        tier_timeout,
        {
            "explicit-kept": _session(explicit=30),
            "four-tiers": _session(tiers={**TIER_SECONDS, "e2e": None}),
            "calibrated-ceiling": _session(
                props={"calibration": {**CALIBRATION, "small win32 False": 10}, "push_gc": []}
            ),
            "probe-broke": lambda root: {},
        },
    ),
    "quarantine-needs-bug": (
        quarantine_needs_bug,
        {
            "refused-without-bug": _session(
                refusal="tests/tmp/p.py::test_guard_quarantine_naked: refused"
            ),
            "collected-with-bug": _session(
                refusal="tests/tmp/p.py::test_guard_quarantine_with_bug: requires a registered bug id"
            ),
            "actionable-on-stderr": _session(stderr=""),
            "selector-lacks-not-quarantine": _plant_selector,
            "probe-broke": lambda root: {},
        },
    ),
    "statement-id-cited": (statement_id_cited, {"unknown-id": _plant_citation}),
    "push-starts-no-gc": (
        push_starts_no_gc,
        {
            "gc-spawned": _session(props={"push_gc": ['"argv":["git","gc"']}),
            "probe-broke": lambda root: {},
        },
    ),
}
