"""A finding the doctor cannot repair carries its own fix — never `doctor --fix`.

Intent: CONTRACT — sa-unfixable-doctor-findings-say-doctor-fix#S1..#S6 (listed per test).
Size: MEDIUM (real git repo, the doctor's own section assembly, the CLI in-process).
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.doctor_rules import run_section
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import (
    SECTION,
    DoctorService,
    workspace_rules,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store


def _ctx(name: str, slug: str, *, url: str = "", alive: bool = True) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE if alive else ContextState.DEAD,
        repo_slug=slug,
        repo_url=url,
        created_at="2026-01-01T00:00:00",
        alive_since="2026-06-01T00:00:00Z" if alive else None,
        current_branch="main" if alive else None,
    )


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    repo = ws / "repos" / "demo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.invalid/demo.git"],
        cwd=repo,
        check=True,
    )
    store = context_store(ws / ".dadaia" / "states")
    store.save(_ctx("demo", "demo"))  # alive, empty repo_url -> CTX-URL-1
    store.save(_ctx("a", "x", url="https://example.invalid/x", alive=False))
    store.save(_ctx("b", "x", url="https://example.invalid/x", alive=False))  # INV-6
    return ws  # no .dadaia/.venv -> VENV-1


def _findings(ws: Path) -> dict[str, list[tuple[str, str]]]:
    service = DoctorService(context_store(ws / ".dadaia" / "states"), GitSubprocessClient(), ws)
    report = run_section(SECTION, workspace_rules(), service, lambda _r, f: f, ws)
    out: dict[str, list[tuple[str, str]]] = {}
    for finding in report.findings:
        out.setdefault(finding.code, []).append((finding.message, finding.fix))
    return out


def test_no_unfixable_finding_says_doctor_fix(tmp_path: Path) -> None:
    """sa-unfixable-doctor-findings-say-doctor-fix#S1, sa-unfixable-doctor-findings-say-doctor-fix#S5,
    sa-unfixable-doctor-findings-say-doctor-fix#S6, sa-unfixable-doctor-findings-say-doctor-fix#S4:
    CTX-URL-1, INV-6 and VENV-1 are unfixable; each carries its own command, none the
    doctor's own repair, none restated in the prose; a missing install ledger is no finding."""
    found = _findings(_workspace(tmp_path))
    for code in ("CTX-URL-1", "INV-6", "VENV-1"):
        ((message, fix),) = found[code]
        assert fix and "doctor --fix" not in fix and "dadaia " not in message, (code, fix)
    assert not [m for items in found.values() for m, _ in items if "states/install_ledger" in m]


def test_the_printed_ctx_url_fix_clears_ctx_url_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-unfixable-doctor-findings-say-doctor-fix#S2, sa-unfixable-doctor-findings-say-doctor-fix#S3: run the printed fix (its argv
    after the workspace CLI path), re-run the doctor: CTX-URL-1 is gone and nothing new
    appears for that context."""
    ws = _workspace(tmp_path)
    ((_message, fix),) = _findings(ws)["CTX-URL-1"]
    argv = shlex.split(fix)
    assert argv[0] == (ws / ".dadaia" / ".venv" / "bin" / "dadaia").as_posix() or os.name == "nt"
    monkeypatch.chdir(ws)
    result = CliRunner().invoke(app, argv[1:])

    after = _findings(ws)
    assert "CTX-URL-1" not in after, result.output
    assert not [m for code, items in after.items() for m, _ in items if "'demo'" in m]
