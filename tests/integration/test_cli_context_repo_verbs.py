"""CLI integration tests for `dadaia context repo add/remove/list` and
`context create --associated` (v0.4.4 FR17, T-044-28).

Covers:
- A17.1 each verb is idempotent and fails loudly on an unknown context or slug.
- A17.2 `remove` never deletes an on-disk repo silently — it states what it leaves
  behind.
- A17.3 adding the main repo's own slug as associated is refused.
- `create --associated SLUG[=URL]`, repeatable, both bare-slug and slug=url forms.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from typer.testing import CliRunner  # noqa: E402

from dadaia_workspace.cli.main import app  # noqa: E402
from dadaia_workspace.features.workspace.service import WorkspaceService  # noqa: E402
from dadaia_workspace.infrastructure.public_assets import (  # noqa: E402
    FileSystemPublicAssetManager,
)
from dadaia_workspace.infrastructure.python_env import (  # noqa: E402
    VenvPythonEnvironmentManager,
)

_runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch) -> Path:  # type: ignore[no-untyped-def]
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    for var in ("DADAIA_SESSION_ID", "DADAIA_CONTEXT"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _record(workspace: Path, name: str) -> dict:  # type: ignore[type-arg]
    data = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    contexts = data.get("contexts", data)
    if isinstance(contexts, dict):
        return contexts[name]
    return next(c for c in contexts if c["name"] == name)


# --------------------------------------------------------------------- repo add


def test_repo_add_registers_and_is_idempotent(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])

    result = _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )
    assert result.exit_code == 0, result.output
    rec = _record(workspace, "foo")
    assert rec["associated_repos"] == [{"slug": "assoc-a", "url": "https://x.test/a.git"}]

    # Idempotent: same slug + same url again -> success, no-op, no duplicate entry.
    result2 = _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )
    assert result2.exit_code == 0, result2.output
    assert "no change" in result2.output.lower() or "already" in result2.output.lower()
    rec2 = _record(workspace, "foo")
    assert rec2["associated_repos"] == [{"slug": "assoc-a", "url": "https://x.test/a.git"}]


def test_repo_add_refuses_conflicting_url(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )

    result = _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a-renamed.git"]
    )
    assert result.exit_code == 1
    assert "remove" in result.output.lower()  # tells the operator the one path forward
    rec = _record(workspace, "foo")
    assert rec["associated_repos"] == [{"slug": "assoc-a", "url": "https://x.test/a.git"}]


def test_repo_add_refuses_main_repo_slug(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])

    result = _runner.invoke(app, ["context", "repo", "add", "foo", "foo-repo"])
    assert result.exit_code == 1
    assert "main repo" in result.output.lower()
    rec = _record(workspace, "foo")
    assert rec["associated_repos"] == []


def test_repo_add_unknown_context_exits_1(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "repo", "add", "nope", "assoc-a"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_repo_add_invalid_slug_exits_1(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    result = _runner.invoke(app, ["context", "repo", "add", "foo", "not a valid slug"])
    assert result.exit_code == 1


# --------------------------------------------------------------------- repo remove


def test_repo_remove_states_on_disk_checkout_left_untouched(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )
    on_disk = workspace / "repos" / "assoc-a"
    on_disk.mkdir(parents=True)
    (on_disk / "marker.txt").write_text("still here\n", encoding="utf-8")

    result = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert result.exit_code == 0, result.output
    assert "untouched" in result.output.lower()
    assert "assoc-a" in result.output

    # Registry entry gone.
    rec = _record(workspace, "foo")
    assert rec["associated_repos"] == []
    # On-disk checkout genuinely left alone (A17.2 — never deletes silently, or at all).
    assert on_disk.exists()
    assert (on_disk / "marker.txt").exists()


def test_repo_remove_states_no_on_disk_checkout_found(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    _runner.invoke(app, ["context", "repo", "add", "foo", "assoc-a"])

    result = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert result.exit_code == 0, result.output
    assert "no on-disk checkout" in result.output.lower()


def test_repo_remove_unknown_slug_exits_1(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    result = _runner.invoke(app, ["context", "repo", "remove", "foo", "never-added"])
    assert result.exit_code == 1
    assert "never-added" in result.output


def test_repo_remove_unknown_context_exits_1(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "repo", "remove", "nope", "assoc-a"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_repo_remove_second_call_fails_loudly(workspace: Path) -> None:
    """A17.1: remove converges to "not registered" — a second call on the same slug
    is a loud failure, not a silent no-op."""
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    _runner.invoke(app, ["context", "repo", "add", "foo", "assoc-a"])
    first = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert first.exit_code == 0

    second = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert second.exit_code == 1


# --------------------------------------------------------------------- repo list


def test_repo_list_json(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )
    _runner.invoke(app, ["context", "repo", "add", "foo", "assoc-b"])

    result = _runner.invoke(app, ["context", "repo", "list", "foo", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == [
        {"slug": "assoc-a", "url": "https://x.test/a.git"},
        {"slug": "assoc-b", "url": ""},
    ]


def test_repo_list_table_empty(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "foo", "--repo", "foo-repo"])
    result = _runner.invoke(app, ["context", "repo", "list", "foo"])
    assert result.exit_code == 0, result.output
    assert "no associated repos" in result.output.lower()


def test_repo_list_unknown_context_exits_1(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "repo", "list", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


# --------------------------------------------------------------------- create --associated


def test_create_associated_repeatable_bare_slug_and_slug_equals_url(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "context",
            "create",
            "foo",
            "--repo",
            "foo-repo",
            "--associated",
            "assoc-a",
            "--associated",
            "assoc-b=https://x.test/b.git",
        ],
    )
    assert result.exit_code == 0, result.output
    rec = _record(workspace, "foo")
    assert rec["associated_repos"] == [
        {"slug": "assoc-a", "url": ""},
        {"slug": "assoc-b", "url": "https://x.test/b.git"},
    ]


def test_create_associated_refuses_when_slug_equals_main_repo(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        ["context", "create", "foo", "--repo", "foo-repo", "--associated", "foo-repo"],
    )
    assert result.exit_code == 1
    assert "main repo" in result.output.lower()
    # No context left behind by a refused create.
    data = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    contexts = data.get("contexts", data)
    names = [c["name"] for c in contexts] if isinstance(contexts, list) else list(contexts)
    assert "foo" not in names


def test_create_associated_refuses_duplicate_slug_in_same_call(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "context",
            "create",
            "foo",
            "--repo",
            "foo-repo",
            "--associated",
            "assoc-a",
            "--associated",
            "assoc-a=https://x.test/a.git",
        ],
    )
    assert result.exit_code == 1
    assert "more than once" in result.output.lower()
