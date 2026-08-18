"""FR29 (v0.4.3 T-043-44) — ``dadaia tmp gc`` CLI wiring.

Intent: CONTRACT — A29.3, A29.4

Thin CLI-level proof that the Typer verb is wired correctly (workspace resolution,
``--dry-run`` flag plumbing, human-readable summary, and the A29.4 "documented as the
backstop" text). The exhaustive lane/AG.1 behavior is proven at the service level in
``tests/unit/features/tmp_gc/test_tmp_gc_service.py`` — this file does not re-derive it.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import tmp as tmp_cmd
from dadaia_workspace.cli.main import app as main_app

runner = CliRunner()

#: Typer collapses a SINGLE-command app's own subcommand name away when that Typer
#: instance is invoked standalone (``tmp_cmd.app`` has exactly one command, ``gc``) —
#: real dispatch only preserves ``tmp gc`` as two tokens when reached through the full
#: CLI's ``add_typer`` nesting, exactly as an operator actually runs it
#: (``dadaia tmp gc``). These fixtures therefore drive the full ``main.app``.


def _write_stale_cache(dadaia_root: Path) -> Path:
    path = dadaia_root / "tmp" / "software-engineer" / "mypy-cache" / "x.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    return path


def _patch_workspace(monkeypatch: pytest.MonkeyPatch, ws: Path) -> None:
    monkeypatch.setattr(tmp_cmd, "resolve_workspace_root", lambda: ws)


def test_dry_run_prints_candidates_and_deletes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_workspace(monkeypatch, tmp_path)
    cache_file = _write_stale_cache(tmp_path / ".dadaia")

    result = runner.invoke(main_app, ["tmp", "gc", "--dry-run"])

    assert result.exit_code == 0
    assert cache_file.exists()
    assert "mypy-cache" in result.stdout
    assert "--no-dry-run" not in result.stdout  # dry-run guidance uses the bare verb
    assert "would" in result.stdout.lower()


def test_no_dry_run_actually_deletes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_workspace(monkeypatch, tmp_path)
    cache_file = _write_stale_cache(tmp_path / ".dadaia")

    result = runner.invoke(main_app, ["tmp", "gc"])

    assert result.exit_code == 0
    assert not cache_file.exists()
    assert "reclaimed" in result.stdout.lower() or "mypy-cache" in result.stdout


def test_nothing_to_reclaim_prints_clean_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / ".dadaia" / "tmp").mkdir(parents=True)

    result = runner.invoke(main_app, ["tmp", "gc", "--dry-run"])

    assert result.exit_code == 0
    assert "nothing to reclaim" in result.stdout.lower()


def test_help_documents_the_backstop_and_event_driven_posture() -> None:
    """A29.4: documented as the backstop, with every other capability named as
    event-driven."""
    result = runner.invoke(main_app, ["tmp", "gc", "--help"])

    assert result.exit_code == 0
    lowered = result.stdout.lower()
    assert "backstop" in lowered
    assert "event-driven" in lowered
    assert "calendar" in lowered


def test_live_owned_marker_survives_the_cli_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end sanity through the CLI: a marker whose session record exists is never
    touched, even by the real (non-dry-run) invocation."""
    _patch_workspace(monkeypatch, tmp_path)
    dadaia_root = tmp_path / ".dadaia"
    (dadaia_root / "sessions").mkdir(parents=True)
    (dadaia_root / "sessions" / "owned.json").write_text("{}", encoding="utf-8")
    marker = dadaia_root / "tmp" / "reconciler-last-owned"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("marker", encoding="utf-8")
    import os

    old = time.time() - 30 * 86400
    os.utime(marker, (old, old))

    result = runner.invoke(main_app, ["tmp", "gc"])

    assert result.exit_code == 0
    assert marker.exists()
