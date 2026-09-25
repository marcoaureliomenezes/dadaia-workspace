"""Intent: CONTRACT — T-048-05 (SPEC 0.4.8 FR4 AC4.1, AC4.3–AC4.5): ``specs init --context``
on the three tree kinds — absent scaffolds, dadaia upgrades, foreign moves to ``specs-bkp/``
only when confirmed — never committing. Size: MEDIUM (real git repo on disk)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli._specs_resolution import HARNESS_SESSION_ID_ENV_VARS
from dadaia_workspace.cli.main import app
from dadaia_workspace.core import specs_version
from dadaia_workspace.features.specs import SpecsDoctor, canon

pytestmark = pytest.mark.integration

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_runner = CliRunner()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Workspace with context ``c`` whose main repo ``repos/c`` has one commit."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"name": "c", "repo_slug": "c", "state": "alive"}]}),
        encoding="utf-8",
    )
    main = tmp_path / "repos" / "c"
    main.mkdir(parents=True)
    _git(main, "init", "-q")
    (main / "README.md").write_text("hi\n", encoding="utf-8")
    _git(main, "add", "README.md")
    _git(main, "commit", "-q", "-m", "init")
    for var in (*HARNESS_SESSION_ID_ENV_VARS, "DADAIA_CONTEXT", "WORKSPACE_ROOT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    return main


def _doctor_errors(specs: Path) -> list[dict[str, object]]:
    issues = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates").check()
    return [i.to_dict() for i in issues if i.severity.value == "error"]


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _foreign(repo: Path) -> dict[str, bytes]:
    specs = repo / "specs"
    (specs / "features").mkdir(parents=True)
    (specs / "README.md").write_text("# our specs\n", encoding="utf-8")
    (specs / "features" / "login.md").write_text("login\n", encoding="utf-8")
    _git(repo, "add", "specs")
    _git(repo, "commit", "-q", "-m", "foreign specs")
    (specs / "features" / "draft.md").write_text("untracked draft\n", encoding="utf-8")
    return _snapshot(specs)


def test_absent_specs_scaffolds_lists_paths_and_commits_nothing(repo: Path) -> None:
    head = _git(repo, "rev-parse", "HEAD")

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    assert "constitution.md" in result.output and "memory/ARCHITECTURE.md" in result.output
    assert _doctor_errors(repo / "specs") == []
    assert _git(repo, "rev-parse", "HEAD") == head
    template = _PUBLIC / "templates"
    law = (template / "repo-AGENTS.md").read_text(encoding="utf-8")
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == law.replace("<repo-name>", repo.name)
    # T-048-11: the tests law governs an existing test tree; init never invents one
    # (a manufactured tests/AGENTS.md is born with AGENTS-PLACEHOLDER-1 on a clean repo).
    assert not (repo / "tests").exists()
    assert f"[created] {repo / 'AGENTS.md'}" in result.output


def test_an_existing_scoped_law_is_never_overwritten(repo: Path) -> None:
    (repo / "AGENTS.md").write_text("# ours\n", encoding="utf-8")
    (repo / "tests").mkdir()

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# ours\n"
    assert (repo / "tests" / "AGENTS.md").is_file()


def test_a_v6_tree_ends_v7_with_a_clean_doctor(repo: Path) -> None:
    assert _runner.invoke(app, ["specs", "init", "--context", "c"]).exit_code == 0
    specs = repo / "specs"
    constitution = specs / "constitution.md"
    constitution.write_text(
        constitution.read_text(encoding="utf-8").split("<!-- dadaia:fixed")[0], encoding="utf-8"
    )
    specs_version.merge_frontmatter(specs, specs_pattern_version=6)

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    assert specs_version.read_pattern_version(specs) == 7
    assert _doctor_errors(specs) == []
    assert not (repo / "specs-bkp").exists()


def test_foreign_tree_non_tty_refusal_leaves_the_tree_byte_identical(repo: Path) -> None:
    _foreign(repo)
    before = _snapshot(repo)

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 2, result.output
    assert _snapshot(repo) == before


def test_replace_foreign_moves_to_specs_bkp_staged_then_scaffolds(repo: Path) -> None:
    old = _foreign(repo)
    head = _git(repo, "rev-parse", "HEAD")

    result = _runner.invoke(app, ["specs", "init", "--context", "c", "--replace-foreign"])

    assert result.exit_code == 0, result.output
    assert _snapshot(repo / "specs-bkp") == old
    assert _git(repo, "rev-parse", "HEAD") == head
    staged = _git(repo, "diff", "--cached", "--name-status").splitlines()
    assert "R100\tspecs/README.md\tspecs-bkp/README.md" in staged
    assert "R100\tspecs/features/login.md\tspecs-bkp/features/login.md" in staged
    assert _doctor_errors(repo / "specs") == []


def test_an_existing_specs_bkp_exits_1_and_writes_nothing(repo: Path) -> None:
    _foreign(repo)
    (repo / "specs-bkp").mkdir()
    before = _snapshot(repo)

    result = _runner.invoke(app, ["specs", "init", "--context", "c", "--replace-foreign"])

    assert result.exit_code == 1, result.output
    assert "fix:" in result.output
    assert _snapshot(repo) == before


def test_no_context_resolved_exits_2_with_a_fix_line(repo: Path) -> None:
    result = _runner.invoke(app, ["specs", "init"])

    assert result.exit_code == 2, result.output
    assert ".dadaia/.venv/bin/dadaia specs init --context '<name>'" in result.output


def test_existing_specs_bkp_fix_line_is_non_destructive_and_clears_the_refusal(
    repo: Path,
) -> None:
    """Review finding 8: the fix line keeps the prior backup instead of deleting it."""
    _foreign(repo)
    (repo / "specs-bkp").mkdir()
    (repo / "specs-bkp" / "old.md").write_text("previous backup\n", encoding="utf-8")
    refused = _runner.invoke(app, ["specs", "init", "--context", "c", "--replace-foreign"])
    fix = next(ln for ln in refused.output.splitlines() if ln.startswith("fix: "))[5:]
    assert " rm " not in fix

    subprocess.run(fix, shell=True, check=True, cwd=repo.parent.parent)
    result = _runner.invoke(app, ["specs", "init", "--context", "c", "--replace-foreign"])

    assert result.exit_code == 0, result.output
    kept = [p for p in repo.glob("specs-bkp-*/old.md")]
    assert [p.read_text(encoding="utf-8") for p in kept] == ["previous backup\n"]


def test_a_symlinked_context_specs_root_is_refused_and_nothing_written(
    repo: Path, tmp_path: Path
) -> None:
    """Review finding 7: ``--context`` routes through the one symlink-refusal seam."""
    real = tmp_path / "elsewhere-specs"
    canon.scaffold(real)
    specs_version.merge_frontmatter(real, specs_pattern_version=6)
    (repo / "specs").symlink_to(real, target_is_directory=True)
    before, before_real = _snapshot(repo), _snapshot(real)

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code != 0, result.output
    assert "symlink" in result.output.lower()
    assert (_snapshot(repo), _snapshot(real)) == (before, before_real)


# ── T-050-13 (AC6.3): the gitflow flags ──────────────────────────────────────────────


def test_fresh_tree_writes_the_detected_gitflow_and_names_it(repo: Path) -> None:
    from dadaia_workspace.core.gitflow import Gitflow

    remote = repo.parent / "origin.git"
    _git(repo.parent, "init", "-q", "--bare", "-b", "trunk", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    flow, warning = specs_version.read_gitflow(repo / "specs")
    assert (flow, warning) == (Gitflow("trunk", "develop", "feature/"), None)
    assert "[gitflow] principal trunk, integration develop, work feature/<M.m.p>" in result.output


def test_flags_merge_into_an_existing_tree_and_rerun_is_a_no_op(repo: Path) -> None:
    from dadaia_workspace.core.gitflow import Gitflow

    assert _runner.invoke(app, ["specs", "init", "--context", "c"]).exit_code == 0
    constitution = repo / "specs" / "constitution.md"
    constitution.write_text(
        constitution.read_text(encoding="utf-8").replace("---\n#", "owner: me\n---\n#", 1),
        encoding="utf-8",
    )
    flags = ["--principal", "trunk", "--integration", "next", "--work-prefix", "work/"]

    first = _runner.invoke(app, ["specs", "init", "--context", "c", *flags])
    snapshot = _snapshot(repo / "specs")
    second = _runner.invoke(app, ["specs", "init", "--context", "c", *flags])

    assert first.exit_code == 0 and second.exit_code == 0, first.output + second.output
    assert specs_version.read_gitflow(repo / "specs")[0] == Gitflow("trunk", "next", "work/")
    assert "owner: me" in constitution.read_text(encoding="utf-8")
    assert _snapshot(repo / "specs") == snapshot


def test_an_invalid_flag_refuses_with_a_fix_and_writes_nothing(repo: Path) -> None:
    result = _runner.invoke(app, ["specs", "init", "--context", "c", "--integration", "main"])
    assert result.exit_code == 2
    assert "fix: " in result.output
    assert not (repo / "specs").exists()
