"""CLI integration tests for `dadaia context repo add/remove/list` and
`context create --associated` (v0.4.4 FR17, T-044-28).

Intent: CONTRACT — A17.1, A17.2, A17.3.

Covers:
- A17.1 each verb is idempotent and fails loudly on an unknown context or slug.
- A17.2 `remove` never deletes an on-disk repo silently — it states what it leaves
  behind.
- A17.3 adding the main repo's own slug as associated is refused.
- `create --associated-repos SLUG[=URL]`, repeatable, both bare-slug and slug=url forms.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from typer.testing import CliRunner  # noqa: E402

from dadaia_workspace.cli.main import app  # noqa: E402
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
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
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES)
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
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )

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
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )
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
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )

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
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )
    result = _runner.invoke(app, ["context", "repo", "add", "foo", "not a valid slug"])
    assert result.exit_code == 1


# --------------------------------------------------------------------- repo remove


def test_repo_remove_states_on_disk_checkout_left_untouched(workspace: Path) -> None:
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )
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
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )
    _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )

    result = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert result.exit_code == 0, result.output
    assert "no on-disk checkout" in result.output.lower()


def test_repo_remove_unknown_slug_exits_1(workspace: Path) -> None:
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )
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
    _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/foo.git"],
    )
    _runner.invoke(
        app, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]
    )
    first = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert first.exit_code == 0

    second = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])
    assert second.exit_code == 1


# --------------------------------------------------------------------- create --associated


def test_create_associated_repeatable_bare_slug_and_slug_equals_url(workspace: Path) -> None:
    """A bare slug adopts an existing ``repos/<slug>`` git checkout (bugs
    context-create-admits-uncloneable-empty-url, context-dead-destroys-associated-repo-
    without-url: a bare or non-git directory is refused)."""
    subprocess.run(
        ["git", "init", str(workspace / "repos" / "assoc-a")], capture_output=True, check=True
    )
    result = _runner.invoke(
        app,
        [
            "context",
            "create",
            "foo",
            "--main-repo",
            "foo-repo",
            "--url",
            "https://x.test/foo.git",
            "--associated-repos",
            "assoc-a",
            "--associated-repos",
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
        [
            "context",
            "create",
            "foo",
            "--main-repo",
            "foo-repo",
            "--url",
            "https://x.test/foo.git",
            "--associated-repos",
            "foo-repo",
        ],
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


def test_create_associated_refuses_slug_owned_by_another_context(workspace: Path) -> None:
    """T-044-45 F-1 / bug context-repo-add-accepts-foreign-context-slug: `create
    --associated` (`cli/commands/context.py`) reuses `SpecContextService.add_repo`
    verbatim for each `--associated` entry, so it must inherit the cross-context
    guard with no second code path. Pins that inheritance at the CLI seam, not a
    re-derivation of the rule (unit-level coverage: `test_repo_verbs.py`)."""
    _runner.invoke(
        app,
        ["context", "create", "bar", "--main-repo", "bar-repo", "--url", "https://x.test/bar.git"],
    )

    result = _runner.invoke(
        app,
        [
            "context",
            "create",
            "foo",
            "--main-repo",
            "foo-repo",
            "--url",
            "https://x.test/foo.git",
            "--associated-repos",
            "bar-repo",
        ],
    )
    assert result.exit_code == 1
    assert "bar" in result.output.lower()


def test_create_refuses_main_repo_slug_owned_by_another_context(workspace: Path) -> None:
    """context-create-accepts-slug-owned-by-another-context (S5-FR23 Firing 5
    finding, mirror of F-1): `create`'s own `--repo` (main) slug checked only
    context-name collision, never slug ownership — `context create foo --repo
    <bar's main slug>` sailed through and armed `dead()` of either context
    against the other's checkout. Pins the CLI seam for the MAIN slug, the
    counterpart of `test_create_associated_refuses_slug_owned_by_another_context`
    above (unit-level coverage: `test_repo_verbs.py`)."""
    _runner.invoke(
        app,
        ["context", "create", "bar", "--main-repo", "bar-repo", "--url", "https://x.test/bar.git"],
    )

    result = _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "bar-repo", "--url", "https://x.test/bar.git"],
    )
    assert result.exit_code == 1
    assert "bar" in result.output.lower()
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
            "--main-repo",
            "foo-repo",
            "--url",
            "https://x.test/foo.git",
            "--associated-repos",
            "assoc-a=https://x.test/a.git",
            "--associated-repos",
            "assoc-a=https://x.test/a.git",
        ],
    )
    assert result.exit_code == 1
    assert "more than once" in result.output.lower()


def test_create_refuses_a_bare_slug_over_a_non_git_directory(workspace: Path) -> None:
    """A non-git ``repos/<slug>`` is no checkout: ``dead`` would delete it with no URL to
    clone it back (bug context-dead-destroys-associated-repo-without-url)."""
    (workspace / "repos" / "assoc-a").mkdir(parents=True)
    result = _runner.invoke(
        app,
        ["context", "create", "foo", "--main-repo", "foo-repo", "--url", "https://x.test/f.git"]
        + ["--associated-repos", "assoc-a"],
    )
    assert result.exit_code == 1
    assert "fix:" in result.output
