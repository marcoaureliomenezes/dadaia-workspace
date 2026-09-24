"""`dadaia context create` is one transactional step (0.4.8 FR3, T-048-03).

Intent: CONTRACT — AC3.1, AC3.2, AC3.3, AC3.4, AC3.5, AC3.6, AC3.8.

MEDIUM tier: real `git` against local bare remotes — the clone, the rollback and the
adoption are the behaviour under test, so no fake stands in for git.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from typer.testing import CliRunner  # noqa: E402

from dadaia_workspace.cli.main import app  # noqa: E402
from dadaia_workspace.core import session_store  # noqa: E402
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES  # noqa: E402
from dadaia_workspace.features.spec_context.service import slug_from_url  # noqa: E402
from dadaia_workspace.features.workspace.service import WorkspaceService  # noqa: E402
from dadaia_workspace.infrastructure.public_assets import (  # noqa: E402
    FileSystemPublicAssetManager,
)
from dadaia_workspace.infrastructure.python_env import (  # noqa: E402
    VenvPythonEnvironmentManager,
)

_runner = CliRunner()
_SID = "sess_create01"
_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@e",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@e",
}


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV},
    ).stdout.strip()


def _remote(parent: Path, name: str) -> Path:
    """A bare remote at *parent/name* carrying one commit on `main`."""
    bare = parent / name
    _git("init", "-q", "--bare", "-b", "main", str(bare))
    seed = parent / f"seed-{name}"
    _git("clone", "-q", str(bare), str(seed))
    (seed / "README.md").write_text("hi\n", encoding="utf-8")
    _git("add", "README.md", cwd=seed)
    _git("commit", "-qm", "init", cwd=seed)
    _git("push", "-q", "origin", "HEAD:main", cwd=seed)
    return bare


def _names(ws: Path) -> list[str]:
    path = ws / ".dadaia" / "states" / "spec_contexts.json"
    if not path.exists():
        return []
    contexts = json.loads(path.read_text(encoding="utf-8")).get("contexts", {})
    return [c["name"] for c in contexts] if isinstance(contexts, list) else list(contexts)


@pytest.fixture()
def ws(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root, harnesses=L1_ENTRY_HARNESSES)
    monkeypatch.chdir(root)
    monkeypatch.setenv("DADAIA_SESSION_ID", _SID)
    return root


def _create(*args: str) -> tuple[int, str]:
    result = _runner.invoke(app, ["context", "create", *args])
    return result.exit_code, result.output


@pytest.mark.parametrize(
    ("url", "slug"),
    [
        ("https://h.test/org/my.repo.git", "my-repo"),
        ("git@h.test:org/app.git", "app"),
        ("/srv/git/tools/", "tools"),
        ("https://h.test/a b+c", "a-b-c"),
    ],
)
def test_one_slug_rule(url: str, slug: str) -> None:
    """AC3.2 — every char outside [A-Za-z0-9_-] becomes '-'."""
    assert slug_from_url(url) == slug


def test_create_clones_hooks_alives_binds_and_leaves_the_repo_untouched(
    ws: Path, tmp_path: Path
) -> None:
    """AC3.1 + AC3.6: name defaults to the slug; porcelain clean; HEAD equals the
    remote's. Doctor's 0 errors needs a real venv — the onboarding journey pins it."""
    main = _remote(tmp_path, "my.app.git")
    assoc = _remote(tmp_path, "lib.git")

    code, out = _create("--main-repo", str(main), "--associated-repo", str(assoc))

    assert code == 0, out
    repo = ws / "repos" / "my-app"
    record = json.loads(_runner.invoke(app, ["context", "show", "my-app", "--json"]).stdout)
    assert record["state"] == "alive"
    assert [r["slug"] for r in record["associated_repos"]] == ["lib"]
    assert (session_store.read_session(ws, _SID) or {}).get("context") == "my-app"
    for checkout in (repo, ws / "repos" / "lib"):
        assert (checkout / ".git" / "hooks" / "pre-push").is_file()
        assert _git("status", "--porcelain", cwd=checkout) == ""
    assert _git("rev-parse", "HEAD", cwd=repo) == _git("rev-parse", "main", cwd=main)


def test_a_failed_clone_leaves_nothing_and_the_same_command_then_succeeds(
    ws: Path, tmp_path: Path
) -> None:
    """AC3.4 + AC3.5 (RV1): rollback of every created dir, no record, a fix line that
    carries every --associated-repo (the failed one a placeholder), and a clean retry (R3)."""
    main = _remote(tmp_path, "core.git")
    ok_assoc = _remote(tmp_path, "one.git")
    missing = tmp_path / "two.git"
    argv = ["proj", "--main-repo", str(main)]
    argv += ["--associated-repo", str(ok_assoc), "--associated-repo", str(missing)]

    code, out = _create(*argv)

    assert code == 1
    assert (
        f"context create proj --main-repo {main} --associated-repo {ok_assoc} "
        "--associated-repo <clone-url>"
    ) in out.replace("\n", "")
    assert "proj" not in _names(ws)
    assert sorted(p.name for p in (ws / "repos").iterdir()) == []

    _remote(tmp_path, "two.git")
    code, out = _create(*argv)
    assert code == 0, out
    assert sorted(p.name for p in (ws / "repos").iterdir()) == ["core", "one", "two"]


def test_an_existing_checkout_of_the_url_is_adopted_any_other_occupant_refused(
    ws: Path, tmp_path: Path
) -> None:
    """AC3.3."""
    main = _remote(tmp_path, "adopt.git")
    _git("clone", "-q", str(main), str(ws / "repos" / "adopt"))
    (ws / "repos" / "squat").mkdir()
    squat = _remote(tmp_path, "squat.git")

    code, out = _create("--main-repo", str(squat))
    assert code == 1
    assert "squat" not in _names(ws)
    assert (ws / "repos" / "squat").is_dir(), "a dir this call did not create survives"

    code, out = _create("--main-repo", str(main))
    assert code == 0, out
    assert (ws / "repos" / "adopt" / ".git" / "hooks" / "pre-push").is_file()


@pytest.mark.parametrize("flag", ["--url", "--associated-repos"])
def test_retired_flags_exit_2(ws: Path, flag: str) -> None:
    """AC3.8."""
    code, _ = _create("x", "--main-repo", "https://h.test/x.git", flag, "y")
    assert code == 2


def test_refusal_fix_lines_never_repeat_the_failing_command(ws: Path, tmp_path: Path) -> None:
    """Live audit G3/G4: a bad URL points at a clone-URL placeholder, an owned slug at
    the list that names its owner — neither echoes the command that just failed (G6: the
    empty list names the runnable create)."""
    listed = _runner.invoke(app, ["context", "list"]).output
    assert "context create <name> --main-repo <clone-url>" in listed
    code, out = _create("bad", "--main-repo", str(tmp_path / "nothere.git"))
    assert code == 1
    assert out.splitlines()[-1].endswith("context create bad --main-repo <clone-url>")

    second = _remote(tmp_path, "second.git")
    assert _create("--main-repo", str(second))[0] == 0
    code, out = _create("bad", "--main-repo", str(second))
    assert code == 1
    assert out.splitlines()[-1].endswith("context list")


def test_the_created_line_is_one_line_and_the_next_step_is_the_new_contexts(
    ws: Path, tmp_path: Path
) -> None:
    """Live audit G1 + G5: the new context's own next step, not another context's; the
    success line never wraps at 80 columns."""
    assert _create("--main-repo", str(_remote(tmp_path, "second.git")))[0] == 0
    code, out = _create("--main-repo", str(_remote(tmp_path, "a-rather-long-repo-name.git")))
    assert code == 0, out
    assert any(ln.endswith("(main repo: repos/a-rather-long-repo-name)") for ln in out.splitlines())
    assert "specs init --context a-rather-long-repo-name" in out
    assert "'second'" not in out
