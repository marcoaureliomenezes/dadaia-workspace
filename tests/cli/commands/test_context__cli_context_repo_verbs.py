"""v0.4.4 FR17 A17.1-A17.3 (T-044-28): `context repo add/remove` are
idempotent, refuse loudly (unknown context or slug, a conflicting URL, the main repo's own
slug) leaving the record unchanged, and `remove` never deletes an on-disk checkout — it
says what it leaves behind.
"""

from __future__ import annotations

import json
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
from tests.fakes import seed_dead_context

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


_A = [{"slug": "assoc-a", "url": "https://x.test/a.git"}]
_ADD_A = ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]


@pytest.fixture()
def foo(workspace: Path) -> Path:
    """DEAD `foo` (main repo `foo-repo`) with `assoc-a` registered once."""
    seed_dead_context(workspace, "foo", "foo-repo", "https://x.test/foo.git")
    assert _runner.invoke(app, _ADD_A).exit_code == 0
    assert _record(workspace, "foo")["associated_repos"] == _A
    return workspace


def test_repo_add_is_idempotent(foo: Path) -> None:
    again = _runner.invoke(app, _ADD_A)
    assert again.exit_code == 0 and "no change" in again.output.lower(), again.output
    assert _record(foo, "foo")["associated_repos"] == _A


@pytest.mark.parametrize(
    ("argv", "text"),
    [
        pytest.param(["add", "foo", "assoc-a", "--url", "https://x.test/b.git"], "remove", id="conflicting-url-names-remove"),
        pytest.param(["add", "foo", "foo-repo"], "main repo", id="A17.3-main-repo-slug"),
        pytest.param(["add", "nope", "assoc-b"], "not found", id="add-unknown-context"),
        pytest.param(["add", "foo", "not a valid slug"], "", id="add-invalid-slug"),
        pytest.param(["remove", "foo", "never-added"], "never-added", id="remove-unknown-slug"),
        pytest.param(["remove", "nope", "assoc-a"], "not found", id="remove-unknown-context"),
    ],
)  # fmt: skip
def test_a_refused_repo_verb_exits_1_and_changes_nothing(
    foo: Path, argv: list[str], text: str
) -> None:
    result = _runner.invoke(app, ["context", "repo", *argv])
    assert result.exit_code == 1 and text in result.output.lower(), result.output
    assert _record(foo, "foo")["associated_repos"] == _A


@pytest.mark.parametrize(
    ("checkout", "text"), [(True, "untouched"), (False, "no on-disk checkout")]
)
def test_repo_remove_never_deletes_a_checkout_and_says_so(
    foo: Path, checkout: bool, text: str
) -> None:
    """A17.2; A17.1: a second remove of the same slug is a loud failure."""
    on_disk = foo / "repos" / "assoc-a"
    if checkout:
        on_disk.mkdir(parents=True)
        (on_disk / "marker.txt").write_text("still here\n", encoding="utf-8")

    result = _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"])

    assert result.exit_code == 0 and text in result.output.lower(), result.output
    assert _record(foo, "foo")["associated_repos"] == []
    assert (on_disk / "marker.txt").exists() is checkout
    assert _runner.invoke(app, ["context", "repo", "remove", "foo", "assoc-a"]).exit_code == 1
