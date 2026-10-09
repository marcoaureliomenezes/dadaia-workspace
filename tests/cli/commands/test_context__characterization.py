"""Characterization net for the four context registry write seams owned by CP4."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.fakes import FakePythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES[:1])
    monkeypatch.chdir(tmp_path)
    for name in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _row(*, state: str, associated_repos: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "name": "catalog",
        "state": state,
        "repo_slug": "catalog-main",
        "repo_url": "https://example.test/catalog-main.git",
        "created_at": "2026-01-01T00:00:00Z",
        "alive_since": "2026-01-02T00:00:00Z" if state == "alive" else None,
        "dead_since": "2026-01-03T00:00:00Z" if state == "dead" else None,
        "current_branch": "feature/1.2.3",
        "associated_repos": associated_repos or [],
    }


def _write_registry(workspace: Path, row: dict[str, object]) -> Path:
    path = workspace / ".dadaia" / "states" / "spec_contexts.json"
    path.write_text(
        json.dumps({"schema_version": "3", "contexts": [row]}, indent=2),
        encoding="utf-8",
    )
    return path


def test_context_bind_persists_the_callers_session_record(workspace: Path) -> None:
    _write_registry(workspace, _row(state="alive"))

    result = _runner.invoke(
        app,
        ["context", "bind", "catalog"],
        env={"DADAIA_SESSION_ID": "session-char", "DADAIA_RUNTIME": "codex"},
        terminal_width=200,
    )

    assert result.exit_code == 0
    assert result.output == "✓ Bound to 'catalog' (session id: session-char)\n"
    record = json.loads(
        (workspace / ".dadaia" / "sessions" / "session-char.json").read_text("utf-8")
    )
    assert {key: record[key] for key in ("session_id", "context", "runtime")} == {
        "session_id": "session-char",
        "context": "catalog",
        "runtime": "codex",
    }
    assert record["pid"] == os.getpid()
    assert record["bound_at"] == record["last_seen_at"]
    assert datetime.fromisoformat(record["bound_at"]).tzinfo is not None


def test_context_delete_removes_one_dead_registry_record(workspace: Path) -> None:
    registry = _write_registry(workspace, _row(state="dead"))

    result = _runner.invoke(app, ["context", "delete", "catalog"], terminal_width=200)

    assert result.exit_code == 0
    assert result.output == "✓ Context 'catalog' deleted\n"
    assert registry.read_bytes() == b'{\n  "schema_version": "3",\n  "contexts": []\n}'


def test_context_repo_add_appends_one_literal_registry_entry(workspace: Path) -> None:
    registry = _write_registry(workspace, _row(state="dead"))

    result = _runner.invoke(
        app,
        [
            "context",
            "repo",
            "add",
            "catalog",
            "catalog-events",
            "--url",
            "https://example.test/catalog-events.git",
        ],
        terminal_width=200,
    )

    assert result.exit_code == 0
    assert result.output == (
        "✓ Associated repo 'catalog-events' added to context 'catalog' "
        "(1 associated \nrepo(s) total).\n"
    )
    assert json.loads(registry.read_text("utf-8")) == {
        "schema_version": "3",
        "contexts": [
            {
                **_row(state="dead"),
                "associated_repos": [
                    {
                        "slug": "catalog-events",
                        "url": "https://example.test/catalog-events.git",
                    }
                ],
            }
        ],
    }


def test_context_repo_remove_keeps_the_checkout_and_rewrites_only_registry(
    workspace: Path,
) -> None:
    registry = _write_registry(
        workspace,
        _row(
            state="dead",
            associated_repos=[
                {
                    "slug": "catalog-events",
                    "url": "https://example.test/catalog-events.git",
                }
            ],
        ),
    )
    marker = workspace / "repos" / "catalog-events" / "event.txt"
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b"event-1\n")

    result = _runner.invoke(
        app,
        ["context", "repo", "remove", "catalog", "catalog-events"],
        terminal_width=200,
    )

    assert result.exit_code == 0
    expected_output = (
        (
            "✓ Associated repo 'catalog-events' removed from context 'catalog' registry "
            "(0 \nassociated repo(s) remain).\n"
            "! The on-disk checkout at 'repos/catalog-events' was left untouched — this only\n"
            "removes the registry entry, it never deletes files. Remove it yourself if it is\n"
            "no longer needed.\n"
        )
        if PLATFORM.windows
        else (
            "✓ Associated repo 'catalog-events' removed from context 'catalog' registry "
            "(0 \nassociated repo(s) remain).\n"
            "! The on-disk checkout at 'repos/catalog-events' was left untouched — this only "
            "\nremoves the registry entry, it never deletes files. Remove it yourself if it is "
            "\nno longer needed.\n"
        )
    )
    assert result.output == expected_output
    assert marker.read_bytes() == b"event-1\n"
    assert json.loads(registry.read_text("utf-8")) == {
        "schema_version": "3",
        "contexts": [{**_row(state="dead"), "associated_repos": []}],
    }
