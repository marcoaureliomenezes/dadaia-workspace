"""0.4.6 AC2, AC4 (`dadaia doctor` workspace section: finding lines, exit code,
`--json`, `--fix --expired-only --quiet`, holds in reaped/, expiry); size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import (
    LEVEL1_SEEDS,
    provisioned_zones,
)
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dadaia = tmp_path / ".dadaia"
    for zone in provisioned_zones():
        (dadaia / zone.name).mkdir(parents=True, exist_ok=True)
    (dadaia / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    (dadaia / "states" / "harness_profile.json").write_text(
        json.dumps({"schema_version": "1", "harnesses": list(L1_ENTRY_HARNESSES)}),
        encoding="utf-8",
    )
    (dadaia / "states" / "install_ledger.json").write_text(
        json.dumps({"schema_version": "1", "entries": []}), encoding="utf-8"
    )
    (tmp_path / "repos").mkdir()
    (tmp_path / "AGENTS.md").write_text("# agents", encoding="utf-8")
    for name in LEVEL1_SEEDS:  # init writes them (ADR 0095)
        (tmp_path / name).write_text("", encoding="utf-8")
    venv_bin = dadaia / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n", encoding="utf-8")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        container,
        "build_doctor_service",
        lambda root: DoctorService(
            context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root
        ),
    )
    return tmp_path


def test_healthy_workspace_exits_0_and_prints_only_the_next_step(workspace: Path) -> None:
    """Zero contexts prints the one ONBOARDING info finding and its fix line, exit 0."""
    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert [line.split(" ", 2)[:2] for line in lines[:1]] == [["ONBOARDING", "info"]], lines
    assert len(lines) == 2 and lines[1].startswith("fix: "), lines


@pytest.mark.parametrize("ledger_state", ["absent", "corrupt"])
def test_fix_changes_nothing_in_a_harness_dir_without_a_readable_ledger(
    workspace: Path, ledger_state: str
) -> None:
    """sa-doctor-reaps-harness-owned-entries#H5: with no readable ledger ``--fix`` touches no harness file."""
    ledger = workspace / ".dadaia" / "states" / "install_ledger.json"
    if ledger_state == "corrupt":
        ledger.write_text("{not json", encoding="utf-8")
    else:
        ledger.unlink()
    projected = workspace / ".claude" / "agents" / "pm.md"
    projected.parent.mkdir(parents=True)
    projected.write_text("projected", encoding="utf-8")

    CliRunner().invoke(app, ["doctor", "--fix"])

    assert projected.read_text(encoding="utf-8") == "projected"
    assert sorted(p.name for p in (workspace / ".claude").rglob("*")) == ["agents", "pm.md"]


def test_a_context_run_neither_reports_nor_reaps_another_contexts_repo(workspace: Path) -> None:
    """AC10.4: slop only in repos/beta; `--context alpha` judges and repairs alpha alone."""
    store = context_store(workspace / ".dadaia" / "states")
    for name in ("alpha", "beta"):
        store.save(
            SpecContextProject(
                name=name,
                state=ContextState.ALIVE,
                repo_slug=name,
                repo_url=f"https://example.test/{name}",
                created_at="2026-01-01T00:00:00",
                alive_since="2026-06-01T00:00:00Z",
                dead_since=None,
                current_branch="main",
            )
        )
        (workspace / "repos" / name).mkdir()
    (workspace / "repos" / "beta" / ".dadaia").mkdir()

    report = CliRunner().invoke(app, ["doctor", "--context", "alpha"])
    assert report.exit_code == 0, report.output
    CliRunner().invoke(app, ["doctor", "--fix", "--context", "alpha"])
    assert (workspace / "repos" / "beta" / ".dadaia").is_dir()
