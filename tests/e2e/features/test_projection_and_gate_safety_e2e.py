"""E2E cover for three behaviours a mutation campaign proved the suite did NOT catch.

Breaking each of these left ``tests/e2e`` fully green:

* pruning scoped by the projection ledger — reverting it deletes operator-authored files
  on a routine ``public install`` (a data-loss bug that shipped once already);
* the backlog gate blocking an item with no ``intents[]`` — reverting it lets
  ``backlog-definition`` complete on a tree ``backlog doctor`` rejects;
* doctor naming unmanaged files in ``.claude/`` — reverting it makes an
  instruction-injection surface invisible again.

Unit tests covered all three. That was not enough: the operator does not run unit tests,
they run the CLI, and every one of these failures reached them through the CLI. A suite
that only proves the pieces work is how "all green" coexists with a broken product.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_runner = CliRunner()


@pytest.fixture
def installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_SESSION_ID", "e2e-projection-session")
    assert _runner.invoke(app, ["public", "stage"]).exit_code == 0
    assert _runner.invoke(app, ["public", "install", "--target", "claude"]).exit_code == 0
    return tmp_path


def test_install_never_deletes_an_operator_authored_rule(installed: Path) -> None:
    """The data-loss case, through the CLI the operator actually types."""
    mine = installed / ".claude" / "rules" / "minha-regra.md"
    mine.write_text("# minha regra\n\nOperator law.\n", encoding="utf-8")

    result = _runner.invoke(app, ["public", "install", "--target", "claude"])

    assert result.exit_code == 0, result.output
    assert mine.is_file(), "a routine install deleted an operator-authored rule"
    assert mine.read_text(encoding="utf-8") == "# minha regra\n\nOperator law.\n"


def test_install_still_prunes_a_stale_lib_projection(installed: Path) -> None:
    """The other direction — scoping the prune must not disable it.

    Without this, 'never delete anything' would pass the test above while letting the
    projection rot.
    """
    projected = sorted((installed / ".claude" / "rules").glob("*.md"))
    assert projected, "no rules were projected"
    orphan = projected[0]
    staged = installed / ".dadaia" / "agentic" / "rules" / orphan.name
    assert staged.is_file()
    staged.unlink()  # the library stopped shipping this rule

    assert _runner.invoke(app, ["public", "install", "--target", "claude"]).exit_code == 0
    assert not orphan.exists(), "a lib-originated projection whose source is gone must be pruned"


def test_doctor_names_an_unmanaged_file_in_the_rules_corpus(installed: Path) -> None:
    """An unmanaged file in .claude/rules is loaded into every session's context."""
    (installed / ".claude" / "rules" / "smuggled.md").write_text("x\n", encoding="utf-8")

    result = _runner.invoke(app, ["public", "doctor"])

    # The EXACT line, not "the word appears somewhere": doctor output is long and other
    # checks mention the same file (the dead-law warn names 'smuggled' too), so a loose
    # substring pair passes even when this check is deleted. Found by mutation.
    named = [
        line
        for line in result.output.splitlines()
        if line.startswith("[warn] claude:rules/smuggled.md unmanaged")
    ]
    assert named, (
        f"doctor did not name .claude/rules/smuggled.md as unmanaged; output was:\n{result.output}"
    )


def test_doctor_is_quiet_about_unmanaged_files_on_a_clean_tree(installed: Path) -> None:
    """A check that fires on a healthy workspace is noise the operator learns to skip."""
    result = _runner.invoke(app, ["public", "doctor"])
    assert "unmanaged" not in result.output, result.output


def test_backlog_definition_refuses_to_leave_a_tree_the_doctor_rejects(
    installed: Path,
) -> None:
    """The producer and the validator must not disagree about the same backlog."""
    repo = installed / "repos" / "gaterepo"
    repo.mkdir(parents=True)
    import subprocess

    for args in (
        ["init", "-q"],
        ["config", "user.email", "e2e@test"],
        ["config", "user.name", "e2e"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    assert (
        _runner.invoke(
            app, ["context", "create", "gatectx", "--repo", "gaterepo", "--url", str(repo)]
        ).exit_code
        == 0
    )
    assert _runner.invoke(app, ["context", "alive", "gatectx"]).exit_code == 0

    specs = repo / "specs"
    (specs / "backlog" / "no-intents.md").write_text(
        "---\nname: no-intents\nstatus: candidate\nintents: []\n---\n\n# BACKLOG\n",
        encoding="utf-8",
    )

    doctor = _runner.invoke(app, ["backlog", "doctor", "--specs-dir", str(specs)])
    assert doctor.exit_code != 0, "the validator accepted an item with no intents[]"

    workflow = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--context",
            "gatectx",
            "--release-id",
            "v0.1.0",
            "--run-id",
            "gate1",
            "--harness",
            "fake",
            "--demand",
            "x",
        ],  # fmt: skip
    )
    assert workflow.exit_code != 0, (
        "backlog-definition completed and left a backlog that `backlog doctor` rejects — "
        "producer and validator must never disagree about the same tree"
    )
    assert "no-intents" in workflow.output, workflow.output
