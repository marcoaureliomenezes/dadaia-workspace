"""Default CLI output is byte-for-byte unchanged by the addition of ``--redact``.

Intent: CONTRACT — v0.9.0 A8.2.

SPEC v0.9.0 FR8a requires ``--redact`` to be strictly opt-in: `dadaia doctor`,
`dadaia context list` and `dadaia context show` (table and ``--json``) must render
IDENTICAL output to their pre-FR8a behavior when the flag is absent. Every string below
was captured from the verb's actual output before the ``--redact`` flag existed, so a
byte-for-byte regression here means the new flag's plumbing leaked into the default
path — not a decision this task is free to re-litigate.

Byte-for-byte golden literals are inherently platform-specific wherever they embed a
``rich.table.Table`` rendering: Rich substitutes its default HEAVY_HEAD box-drawing
characters for the ASCII-safe SQUARE box whenever ``Console.legacy_windows`` resolves
True (no Windows Virtual Terminal support detected — the case for CI runners without an
attached VT-capable console), independent of ``sys.platform`` alone
(`rich.console.detect_legacy_windows`, `rich.box.Box.substitute`). Plain-text and
``--json`` output never goes through box substitution, so those golden literals hold on
every platform. Only ``dadaia context list``'s default table output embeds box-drawing
characters in this module (`dadaia doctor` and `dadaia context show` render plain
``console.print(f"...")`` lines with no ``Table``); its byte-for-byte pin is therefore
scoped to Linux (where it was captured), paired with a platform-independent assertion
that runs everywhere and pins the semantic half of A8.2: the default table still carries
the true, unredacted context name and never leaks a ``[REDACTED-CONTEXT-`` placeholder.
"""

from __future__ import annotations

import json
import platform
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.contract

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    from dadaia_workspace.core.platform import PLATFORM

    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
        "DADAIA_CONTEXT",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _register_alive_ctx(workspace: Path, name: str = "caller-ctx") -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"https://example.com/{name}.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            }
        )
    )
    (workspace / "repos" / name).mkdir(parents=True, exist_ok=True)


def _register_dead_ctx_with_repo_on_disk(workspace: Path, name: str = "stale-ctx") -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "dead",
                        "repo_slug": name,
                        "repo_url": "",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": None,
                        "dead_since": "2026-05-01T00:00:00Z",
                        "current_branch": None,
                    }
                ],
            }
        )
    )
    (workspace / "repos" / name).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# dadaia doctor — healthy, issue-present, and --fix paths
# ---------------------------------------------------------------------------


def test_doctor_default_output_healthy_workspace_unchanged(workspace: Path) -> None:
    result = _runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert result.output == "All invariants OK — workspace is healthy.\n"


def test_doctor_default_output_with_issue_unchanged(workspace: Path) -> None:
    _register_dead_ctx_with_repo_on_disk(workspace)
    result = _runner.invoke(app, ["doctor"])
    assert result.exit_code == 1, result.output
    assert result.output == (
        "Found 1 issue(s):\n"
        "  INV-5 [fixable] — Context 'stale-ctx' is dead but repo 'stale-ctx' is on disk\n"
        "\n"
        "Run 'dadaia doctor --fix' to apply automatic repairs.\n"
    )


def test_doctor_default_fix_output_unchanged(workspace: Path) -> None:
    _register_dead_ctx_with_repo_on_disk(workspace)
    result = _runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        "Found 1 issue(s):\n"
        "  INV-5 [fixable] — Context 'stale-ctx' is dead but repo 'stale-ctx' is on disk\n"
        "\n"
        "Applied 1 repair(s):\n"
        "  - Removed stale repo 'stale-ctx' for dead context 'stale-ctx'\n"
    )


# ---------------------------------------------------------------------------
# dadaia context list — table and --json
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    platform.system() != "Linux",
    reason="golden output pinned on Linux Rich rendering; Windows renders ASCII-safe boxes",
)
def test_context_list_default_table_output_unchanged(workspace: Path) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    # FR18 (T-044-29): the table gains an "Associated" column (repo count) — the
    # deliberate golden change. Regenerated with the same fixture, unrelated bytes
    # unchanged.
    assert result.output == (
        "             Spec Context Projects              \n"
        "┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓\n"
        "┃ Name       ┃ State ┃ Repo       ┃ Associated ┃\n"
        "┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩\n"
        "│ caller-ctx │ alive │ caller-ctx │ 0          │\n"
        "└────────────┴───────┴────────────┴────────────┘\n"
    )


def test_context_list_default_table_output_unredacted_on_every_platform(
    workspace: Path,
) -> None:
    """Platform-free half of A8.2: regardless of which box-drawing style Rich picks
    for the current platform, the default (no ``--redact``) table must still carry the
    true context name and never a ``[REDACTED-CONTEXT-`` placeholder."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    assert "caller-ctx" in result.output
    assert "[REDACTED-CONTEXT-" not in result.output


def test_context_list_default_json_output_unchanged(workspace: Path) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "list", "--json"])
    assert result.exit_code == 0, result.output
    # FR18 (T-044-29): `list --json` gains `stored_branch` (the distinct name for the
    # cached snapshot, A18.1) and `associated_repos` (full list, A18.4/A18.5) —
    # `current_branch` is now the SAME live-resolved value `show --json` reports for
    # this context (A18.3), unchanged here since the repo is on disk with no `.git`
    # (the fixture never runs `git init`), so live resolution falls back to the
    # stored snapshot "main".
    assert json.loads(result.stdout) == [
        {
            "alive_since": "2026-01-01T00:00:00Z",
            "associated_repos": [],
            "created_at": "2026-01-01T00:00:00Z",
            "current_branch": "main",
            "dead_since": None,
            "name": "caller-ctx",
            "repo_slug": "caller-ctx",
            "repo_url": "https://example.com/caller-ctx.git",
            "state": "alive",
            "stored_branch": "main",
        }
    ]
    assert result.output == (
        '[{"alive_since": "2026-01-01T00:00:00Z", "associated_repos": [], '
        '"created_at": "2026-01-01T00:00:00Z", '
        '"current_branch": "main", "dead_since": null, "name": "caller-ctx", '
        '"repo_slug": "caller-ctx", "repo_url": "https://example.com/caller-ctx.git", '
        '"state": "alive", "stored_branch": "main"}]\n'
    )


# ---------------------------------------------------------------------------
# dadaia context show — table and --json
# ---------------------------------------------------------------------------


def test_context_show_default_table_output_unchanged(workspace: Path) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "show", "caller-ctx"])
    assert result.exit_code == 0, result.output
    # FR18 (T-044-29): `show` gains a "Branch:" line (previously the table rendered
    # NO branch at all — a real gap this task closes) — the deliberate golden
    # change; every other line is byte-identical.
    assert result.output == (
        "Name:       caller-ctx\n"
        "State:      alive\n"
        "Repo:       caller-ctx\n"
        "Repo URL:   https://example.com/caller-ctx.git\n"
        "Branch:     main\n"
        "Created:    2026-01-01T00:00:00Z\n"
        "Alive since:  2026-01-01T00:00:00Z\n"
        "Dead since:   —\n"
        "Presence:   —\n"
    )


def test_context_show_default_json_output_unchanged(workspace: Path) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "show", "caller-ctx", "--json"])
    assert result.exit_code == 0, result.output
    # FR18 (T-044-29): `show --json` gains `associated_repos` (A18.1/A18.4/A18.5) —
    # the deliberate golden change; every other field is byte-identical.
    assert result.output == (
        "{\n"
        '  "name": "caller-ctx",\n'
        '  "state": "alive",\n'
        '  "repo_slug": "caller-ctx",\n'
        '  "repo_url": "https://example.com/caller-ctx.git",\n'
        '  "created_at": "2026-01-01T00:00:00Z",\n'
        '  "alive_since": "2026-01-01T00:00:00Z",\n'
        '  "dead_since": null,\n'
        '  "current_branch": "main",\n'
        '  "stored_branch": "main",\n'
        '  "associated_repos": [],\n'
        '  "session": null,\n'
        '  "presence": []\n'
        "}\n"
    )
