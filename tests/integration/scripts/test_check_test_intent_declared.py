"""Integration self-test AND real-repo wiring for tests/scripts/check_test_intent_declared.py.

FR19 (v0.4.3 T-043-27): the mechanical check that refuses an e2e (LARGE) test file with
no declared ``Intent:`` line. Scoped to ``tests/e2e/**`` (Python + Playwright TS) — the
tier T-043-24..26 fully backfilled, so A19.1 ("green at HEAD the moment it lands") is
satisfiable by construction; the wider suite (unit/contract/integration) carries no such
mechanical gate yet and is out of this task's write set (D-3: FR19 is unsatisfiable
before FR18's curation, which was itself scoped to the LARGE census).

Four fake-tree cases (A19.2):
  1. Undeclared Python e2e file -> script exits 1, names the offending file.
  2. Undeclared Playwright spec file -> script exits 1, names the offending file.
  3. Both declared -> script exits 0, silent.
  4. Non-test support modules (__init__.py, rendezvous.py) never require a declaration —
     they carry zero collected test items (mirrors the exclusion the T-043-26 census
     itself applied).

Plus the real-repo WIRING case: run the script with no override against this repo's own
``tests/e2e/**`` tree (T-043-26's V5 census confirms 15/15 pytest e2e files and 11/11
Playwright spec files already declare `Intent:`) — the check is part of the normal
gating pytest run (this file lives under tests/integration/**, collected on every
gating run) and regresses on any NEW undeclared e2e test file, mirroring the
`check_skill_orphans.py` wiring pattern (T-043-25 Verdict 3).

Intent: CONTRACT — v0.4.3 A19.1, A19.2, A19.3 (T-043-27, FR19)
Owner: software-engineer
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "check_test_intent_declared.py"
)
_REPO_ROOT = _SCRIPT.parent.parent.parent


def _run_script(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
        env={"DADAIA_WORKSPACE_ROOT": str(root), "PATH": str(Path(sys.executable).parent)},
    )


def _seed(tmp_path: Path, *, py_declared: bool, ts_declared: bool) -> None:
    """Lay out a minimal fake ``tests/e2e/**`` tree under *tmp_path*."""
    e2e = tmp_path / "tests" / "e2e"
    (e2e / "features").mkdir(parents=True)
    (e2e / "panel").mkdir(parents=True)
    (e2e / "__init__.py").write_text("")
    (e2e / "features" / "__init__.py").write_text("")
    (e2e / "rendezvous.py").write_text('"""Support module, not a test — no Intent needed."""\n')

    py_header = (
        '"""Fake e2e journey.\n\nIntent: CONTRACT — fake-ref\n"""\n'
        if py_declared
        else '"""Fake e2e journey, no intent line."""\n'
    )
    (e2e / "features" / "test_fake_journey.py").write_text(
        py_header + "\n\ndef test_fake() -> None:\n    pass\n"
    )

    ts_header = (
        "/**\n * Fake spec.\n * Intent: CONTRACT — fake-ref\n */\n"
        if ts_declared
        else "/**\n * Fake spec, no intent line.\n */\n"
    )
    (e2e / "panel" / "fake.spec.ts").write_text(ts_header + "\ntest('fake', () => {});\n")


def test_undeclared_python_e2e_file_refused(tmp_path: Path) -> None:
    root = tmp_path / "undeclared-py"
    _seed(root, py_declared=False, ts_declared=True)
    result = _run_script(root)
    assert result.returncode == 1, (
        f"Expected exit 1 (undeclared Python e2e file), got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "test_fake_journey.py" in result.stderr
    assert "fake.spec.ts" not in result.stderr


def test_undeclared_ts_e2e_file_refused(tmp_path: Path) -> None:
    root = tmp_path / "undeclared-ts"
    _seed(root, py_declared=True, ts_declared=False)
    result = _run_script(root)
    assert result.returncode == 1, (
        f"Expected exit 1 (undeclared Playwright spec file), got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "fake.spec.ts" in result.stderr
    assert "test_fake_journey.py" not in result.stderr


def test_fully_declared_tree_passes_clean(tmp_path: Path) -> None:
    root = tmp_path / "declared"
    _seed(root, py_declared=True, ts_declared=True)
    result = _run_script(root)
    assert result.returncode == 0, (
        f"Expected exit 0 (both files declared), got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert result.stderr.strip() == ""
    assert result.stdout.strip() == ""


def test_support_modules_excluded_from_the_check(tmp_path: Path) -> None:
    """``__init__.py``/``rendezvous.py`` carry zero collected items — never gated."""
    root = tmp_path / "support-only"
    e2e = root / "tests" / "e2e"
    (e2e / "features").mkdir(parents=True)
    (e2e / "__init__.py").write_text("")
    (e2e / "features" / "__init__.py").write_text("")
    (e2e / "rendezvous.py").write_text('"""Support module."""\n')
    result = _run_script(root)
    assert result.returncode == 0, (
        f"Expected exit 0 (no test files present), got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert result.stderr.strip() == ""


def test_real_repo_e2e_tier_is_fully_declared() -> None:
    """WIRE (T-043-27/FR19, A19.1): run against the REAL repo tree.

    T-043-26's V5 census (`.dadaia/tmp/qa-engineer/20260817/v0.4.3-T-043-26-v5-census-
    remeasure.md`) confirms 15/15 pytest e2e files and 11/11 Playwright spec files
    already carry `Intent:` — the check must be green at HEAD the moment it lands
    (A19.1). Any future NEW e2e test file without a declared Intent regresses this.
    """
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        env={"PATH": str(Path(sys.executable).parent)},
    )
    assert result.returncode == 0, (
        f"undeclared e2e test file(s) found: {result.stderr!r}. Add a module-docstring/"
        "header `Intent: <KIND> — <ref>` line (dadaia-test-stewardship §A, tests/AGENTS.md)."
    )
    assert result.stderr.strip() == ""
