"""Intent: CONTRACT — sa-unfixable-doctor-findings-say-doctor-fix (the non-specs codes).

The real CLI doctor runs on a tmp tree with one planted finding; the printed ``fix:``
runs from ``repos/alpha`` and the re-run doctor no longer emits it. The suite fence
(``DADAIA_FENCED_ROOTS``, inherited) keeps every child off the live instance.

size: MEDIUM — the CLI and the ledger scripts run as real subprocesses.
"""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_REPO = Path(__file__).resolve().parents[2]
_UNSET = ("DADAIA_CONTEXT", "DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID")
_ENV = {k: v for k, v in os.environ.items() if k not in _UNSET} | {"PYTHONPATH": str(_REPO)}
_GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


def _findings(root: Path, *scope: str) -> list[dict[str, str]]:
    """The real CLI's ``doctor --json`` — the run judging a fix."""
    argv = [sys.executable, "-m", "dadaia_workspace", "doctor", *scope, "--json"]
    run = subprocess.run(argv, cwd=root, env=_ENV, capture_output=True, text=True, check=False)  # noqa: S603
    return _parse(run.stdout, scope)


def _findings_before(root: Path, *scope: str) -> list[dict[str, str]]:
    """The same ``doctor --json`` in-process — the planted finding and its printed fix,
    before any child runs; the fix and the re-run doctor stay real processes."""
    env = {**_ENV, **dict.fromkeys(_UNSET)}
    with contextlib.chdir(root):
        run = CliRunner().invoke(app, ["doctor", *scope, "--json"], env=env)
    return _parse(run.stdout, scope)


def _parse(stdout: str, scope: tuple[str, ...]) -> list[dict[str, str]]:
    sections = json.loads(stdout)["sections"]
    if scope:  # a bare specs tree: the fenced child judges no workspace at all
        assert sections.get("workspace", {}).get("findings", []) == [], "unfenced"
    return [f for s in sections.values() for f in s["findings"]]


def _run_from_elsewhere(root: Path, fix: str) -> None:
    elsewhere = root / "repos" / "alpha"  # WP-17 #S2: a fix runs from any cwd
    elsewhere.mkdir(parents=True, exist_ok=True)
    ran = subprocess.run(
        ["bash", "-c", fix], cwd=elsewhere, env=_ENV, capture_output=True, text=True
    )  # noqa: S603, S607
    assert ran.returncode == 0, ran.stdout + ran.stderr


def _plant_memory(root: Path) -> dict[str, str]:
    atom = root / "specs/memory/product/core/feature-a.md"
    atom.parent.mkdir(parents=True)
    atom.write_text("---\ntitle: feature-a\ntldr: One line.\n---\n\n# feature-a\n", "utf-8")
    return {}


_SPECS_PLANTS = {"LEDGER-MEMORY-SCHEMA": _plant_memory}


@pytest.mark.parametrize("code", sorted(_SPECS_PLANTS))
def test_the_printed_fix_clears_its_finding(tmp_path: Path, code: str) -> None:
    """Intent: sa-unfixable-doctor-findings-say-doctor-fix#S2 — run the printed fix, re-run
    the whole doctor: the finding is gone and no new error finding appears."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    (tmp_path / "specs").mkdir()
    fills = _SPECS_PLANTS[code](tmp_path)
    before = _findings_before(tmp_path, "--specs-dir", "specs")
    fix = next(f["fix"] for f in before if f["code"] == code)
    for placeholder, value in fills.items():
        fix = fix.replace(placeholder, value)
    _run_from_elsewhere(tmp_path, fix)
    after = _findings(tmp_path, "--specs-dir", "specs")
    old = {(f["code"], f["message"]) for f in before}
    assert code not in {f["code"] for f in after}, fix
    assert [
        f for f in after if f["verdict"] == "error" and (f["code"], f["message"]) not in old
    ] == []


_LEDGER_ROWS = [
    ("LEDGER-BUGS-SCHEMA", "specs/bugs/BUGS.jsonl", "", '{"id": "broken"}\n'),  # the bug's repro
    ("LEDGER-BUGS-SCHEMA", "specs/bugs/BUGS.jsonl", "{not json\n", "{not json\n"),  # invalid at HEAD too
    ("LEDGER-BACKLOG-SCHEMA", "specs/backlog/BACKLOG.json", '{"schema": "backlog-v1", "active": []}', "{not json\n"),
    ("LEDGER-FINDINGS-SCHEMA", "specs/audits/20260101-x/FINDINGS.jsonl", "", "{not json\n"),
    ("LEDGER-RELEASE-SCHEMA", "specs/releases/1.0.0/_RELEASE.json", "{}\n", "{not json\n"),
]  # fmt: skip


@pytest.mark.parametrize(("code", "rel", "committed", "bad"), _LEDGER_ROWS)
def test_an_invalid_ledger_line_names_its_scripts_verb(
    tmp_path: Path, code: str, rel: str, committed: str, bad: str
) -> None:
    """Intent: CONTRACT — ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids (AC4.5):
    an invalid line carries ONE fix, which runs its ledger script's own verb, never a
    hand edit the law forbids; run, it names that line."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    ledger = tmp_path / rel
    ledger.parent.mkdir(parents=True)
    (ledger.parent / "AUDIT.md").write_text("# Audit\n") if "audits" in rel else None
    ledger.write_text(committed)
    subprocess.run([*_GIT, "-C", str(tmp_path), "add", rel], check=True)  # noqa: S603
    subprocess.run([*_GIT, "-C", str(tmp_path), "commit", "-qm", "l"], check=True)  # noqa: S603
    ledger.write_text(bad)
    found = _findings_before(tmp_path, "--specs-dir", "specs")
    (fix,) = {f["fix"] for f in found if f["code"] == code}
    assert "Operator action" not in fix and " check --specs " in fix, fix
    ran = subprocess.run(
        ["bash", "-c", fix], cwd=tmp_path, env=_ENV, capture_output=True, text=True
    )  # noqa: S603, S607
    assert ran.returncode == 1 and f"{rel.removeprefix('specs/')}:1 " in ran.stdout, ran.stdout


def _workspace(tmp_path: Path) -> Path:
    """A real ``init`` in tmp, its venv stubbed onto this interpreter (never a real venv)."""
    from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
    from dadaia_workspace.core.platform import PLATFORM
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager as A
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager as E

    ws = tmp_path / "ws"
    ws.mkdir()
    WorkspaceService(public_assets=A(), python_env=E()).init(ws, harnesses=L1_ENTRY_HARNESSES[:1])
    bin_dir = ws / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "dadaia").write_text(
        f'#!/bin/sh\nexec "{sys.executable}" -m dadaia_workspace "$@"\n'
    )
    (bin_dir / "dadaia").chmod(0o755)
    return ws


def _plant_root_slop(ws: Path) -> str:
    (ws / "junk.txt").write_text("x\n")
    return "WS-root-slop"


def _plant_drifted_hook(ws: Path) -> str:
    from dadaia_workspace.core import workspace_layout

    repo = ws / "repos" / "beta"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)  # noqa: S603, S607
    for target, _ in workspace_layout.INSTALLED_GIT_HOOKS:
        (repo / ".git" / "hooks" / target).write_text("#!/bin/sh\nexit 0\n")
    ctx = {"name": "beta", "state": "alive", "repo_slug": "beta", "repo_url": "file:///x.git",
           "created_at": "2026-01-01T00:00:00Z", "alive_since": "2026-01-01T00:00:00Z",
           "dead_since": None, "current_branch": None}  # fmt: skip
    states = ws / ".dadaia/states/spec_contexts.json"
    states.write_text(json.dumps({"schema_version": "2", "contexts": [ctx]}))
    return "HOOKS-DRIFT-1"


def _plant_disarmed_gate(ws: Path) -> str:
    (ws / ".claude" / "settings.json").unlink()
    return "PROJECTION"


#: Every code this module proves: cleared by its printed fix, or an operator action (V39).
WORKSPACE_PLANTS = {
    **_SPECS_PLANTS,
    **dict.fromkeys(code for code, *_ in _LEDGER_ROWS),
    "WS-ENTRY": _plant_root_slop,  # the fixable sub-rule (S5)
    "HOOKS-DRIFT-1": _plant_drifted_hook,
    "PROJECTION": _plant_disarmed_gate,
}


@pytest.mark.skipif(sys.platform == "win32", reason="the stub CLI is a POSIX shell script")
@pytest.mark.parametrize("plant", [_plant_root_slop, _plant_drifted_hook, _plant_disarmed_gate])
def test_a_workspace_finding_is_cleared_by_its_printed_fix(tmp_path: Path, plant: object) -> None:
    """Intent: sa-unfixable-doctor-findings-say-doctor-fix#S2 — in an initialized tmp
    workspace the printed fix, run from repos/alpha, clears the workspace finding."""
    ws = _workspace(tmp_path)
    code = plant(ws)  # type: ignore[operator]
    fix = next(f["fix"] for f in _findings_before(ws) if f["code"] == code)
    _run_from_elsewhere(ws, shlex.join(shlex.split(fix)))
    assert code not in {f["code"] for f in _findings(ws)}
