"""v0.1.71 FR2 — ``lifecycle status`` run-scoped summary (bug
``lifecycle-status-handoffs-doctor-missing-context``).

Hygiene counters are workspace-global, so ``--context``/``--release-id`` on ``status``
must do REAL work, not be accepted-but-ignored (the v0.1.69 anti-pattern). They add a
run-scoped summary filtered over ``LifecycleRun.context``/``release_id``. Proven
hermetically against a tmp_path workspace (no ambient workspace on CI).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.cli.commands.lifecycle import _runs_summary
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    return tmp_path


def _save(tmp_path: Path, run_id: str, context: str, release_id: str) -> None:
    JsonLifecycleRunStore(tmp_path).save(
        LifecycleRun(
            run_id=run_id,
            context=context,
            release_id=release_id,
            command="release_definition",
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.COMPLETED,
            current_step="release_scope",
            idempotency_key=run_id,
        )
    )


def test_runs_summary_filters_by_context_and_release(tmp_path: Path) -> None:
    _workspace(tmp_path)
    _save(tmp_path, "r1", "dd-chain-capture", "v0.2.0")
    _save(tmp_path, "r2", "dd-chain-capture", "v0.2.0")
    _save(tmp_path, "r3", "dd-chain-capture", "v0.3.0")
    _save(tmp_path, "r4", "some-other-context", "v0.2.0")

    scoped = _runs_summary(tmp_path, context="dd-chain-capture", release_id="v0.2.0")
    assert scoped["matched"] == 2
    assert scoped["context"] == "dd-chain-capture"
    assert scoped["release_id"] == "v0.2.0"
    assert scoped["by_status"] == {"completed": 2}


def test_runs_summary_no_filter_counts_all(tmp_path: Path) -> None:
    _workspace(tmp_path)
    _save(tmp_path, "r1", "dd-chain-capture", "v0.2.0")
    _save(tmp_path, "r2", "some-other-context", "v0.9.9")
    summary = _runs_summary(tmp_path, context=None, release_id=None)
    assert summary["matched"] == 2


def test_runs_summary_context_only_filter(tmp_path: Path) -> None:
    _workspace(tmp_path)
    _save(tmp_path, "r1", "dd-chain-capture", "v0.2.0")
    _save(tmp_path, "r2", "dd-chain-capture", "v0.3.0")
    _save(tmp_path, "r3", "other", "v0.2.0")
    summary = _runs_summary(tmp_path, context="dd-chain-capture", release_id=None)
    assert summary["matched"] == 2
