"""T-048-05 (SPEC 0.4.8 FR4 AC4.1, AC4.3–AC4.5): ``specs init --context``
on the three tree kinds — absent scaffolds, dadaia upgrades, foreign moves to ``specs-bkp/``
only when confirmed — never committing. Size: MEDIUM (real git repo on disk)."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path, PurePath

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli._specs_resolution import HARNESS_SESSION_ID_ENV_VARS
from dadaia_workspace.cli.main import app
from dadaia_workspace.core import gitflow, specs_version
from dadaia_workspace.features.specs import SpecsDoctor, canon

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
    for var in (*HARNESS_SESSION_ID_ENV_VARS, "DADAIA_CONTEXT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    return main


def _doctor_errors(specs: Path) -> list[dict[str, object]]:
    issues = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates").check()
    return [i for i in issues if i.verdict == "error"]


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
    created = {
        PurePath(ln.removeprefix("[created] ")).parts[-2:] for ln in result.output.splitlines()
    }
    assert {("specs", "constitution.md"), ("memory", "ARCHITECTURE.md")} <= created
    # sa-placement-rules-contradict-tree8#B5: a fresh scaffold is doctor-clean — no issue at all.
    assert [i.to_dict() for i in SpecsDoctor(repo / "specs").check()] == []
    assert _git(repo, "rev-parse", "HEAD") == head
    assert repo.name in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert f"[created] {repo / 'AGENTS.md'}" in result.output


def test_the_catalog_pair_is_written_by_its_one_generator(repo: Path) -> None:
    """sa-package-defines-a-fact-twice: the scaffold writes no catalog; `specs init` runs
    `memory.py catalog generate`, so the pair it leaves passes `memory.py check`."""
    assert "memory/product/catalog.json" not in canon.TEMPLATES

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    assert "[created] [ledgers] LEDGER-MEMORY-SCHEMA: catalog generate" in result.output
    memory = _PUBLIC / "skills" / "dd-spec-navigator" / "scripts" / "memory.py"
    check = [sys.executable, str(memory), "check", "--specs", str(repo / "specs")]
    assert subprocess.run(check, capture_output=True, text=True).returncode == 0


def test_an_existing_scoped_law_is_never_overwritten(repo: Path) -> None:
    (repo / "AGENTS.md").write_text("# ours\n", encoding="utf-8")

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# ours\n"


def test_a_v6_tree_ends_v7_with_a_clean_doctor(repo: Path) -> None:
    assert _runner.invoke(app, ["specs", "init", "--context", "c"]).exit_code == 0
    specs = repo / "specs"
    constitution = specs / "constitution.md"
    constitution.write_text(
        constitution.read_text(encoding="utf-8").split("<!-- dadaia:fixed")[0], encoding="utf-8"
    )
    gitflow.merge_frontmatter(specs, specs_pattern_version=6)

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    assert specs_version.state(specs)[0] == "canonical"
    assert _doctor_errors(specs) == []
    assert not (repo / "specs-bkp").exists()


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


def test_an_existing_specs_bkp_is_kept_and_the_tree_moves_to_a_stamped_child(
    repo: Path,
) -> None:
    """Review finding 8: a prior backup is never overwritten nor deleted. Review H1: the
    new one lands INSIDE specs-bkp/ — the one onboarding path baseline publishes."""
    _foreign(repo)
    (repo / "specs-bkp").mkdir()
    (repo / "specs-bkp" / "old.md").write_text("previous backup\n", encoding="utf-8")

    result = _runner.invoke(app, ["specs", "init", "--context", "c", "--replace-foreign"])

    assert result.exit_code == 0, result.output
    assert (repo / "specs-bkp" / "old.md").read_text(encoding="utf-8") == "previous backup\n"
    assert [p.name for p in repo.glob("specs-bkp/*/features/login.md")] == ["login.md"]
    assert list(repo.glob("specs-bkp-*")) == []


# ── T-050-13 (AC6.3): the gitflow flags ──────────────────────────────────────────────


@pytest.mark.parametrize(("head", "principal"), [("trunk", "trunk"), ("develop", "master")])
def test_fresh_tree_writes_the_detected_gitflow_and_names_it(
    repo: Path, head: str, principal: str
) -> None:
    """sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-2 origin/HEAD=trunk: trunk.
    sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-1 HEAD=develop, master present: master."""
    for ref in {head, "master"}:
        _git(repo, "update-ref", f"refs/remotes/origin/{ref}", "HEAD")
    _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{head}")

    result = _runner.invoke(app, ["specs", "init", "--context", "c"])

    assert result.exit_code == 0, result.output
    flow, warning = gitflow.read_gitflow(repo / "specs")
    assert (flow, warning) == (gitflow.Gitflow(principal, "develop", "feature/"), None)
    assert f"[gitflow] principal {principal}, integration develop, work" in result.output


def test_flags_merge_into_an_existing_tree_and_rerun_is_a_no_op(repo: Path) -> None:
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
    assert gitflow.read_gitflow(repo / "specs")[0] == gitflow.Gitflow("trunk", "next", "work/")
    assert "owner: me" in constitution.read_text(encoding="utf-8")
    assert _snapshot(repo / "specs") == snapshot


def test_an_invalid_flag_refuses_with_a_fix_that_clears_it(repo: Path) -> None:
    """sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-3: the fix names
    the detected values and clears the refusal."""
    _git(repo, "update-ref", "refs/remotes/origin/master", "HEAD")
    result = _runner.invoke(app, ["specs", "init", "--context", "c", "--integration", "master"])
    assert result.exit_code == 1 and not (repo / "specs").exists()
    fix = "--principal master --integration develop --work-prefix feature/"
    assert result.output.rstrip().endswith(f"specs init --context c {fix}"), result.output
    assert _runner.invoke(app, ["specs", "init", "--context", "c", *fix.split()]).exit_code == 0


#: The registry placeholders a shipped law template carries (literal, the law's own).
_PLACEHOLDERS = (
    "<!-- zones -->",
    "<!-- canon -->",
    "<!-- root -->",
    "<!-- specs-canon -->",
)


def _symlinked(repo: Path) -> None:
    real = repo.parents[1] / "elsewhere-specs"
    canon.scaffold(real)
    gitflow.merge_frontmatter(real, specs_pattern_version=6)
    (real / "memory" / "atom.md").write_text("---\nslug: x\nagent_tier: self-pull\n---\n")
    (repo / "specs").symlink_to(real, target_is_directory=True)


_SPECS = "repos/c/specs"
_REFUSALS = [
    pytest.param(_foreign, ["specs", "init", "--context", "c"], "--replace-foreign", id="AC4.4-foreign-tree-non-tty"),
    pytest.param(_symlinked, ["specs", "init", "--context", "c"], "symlink", id="finding-7-symlinked-context-root"),
    # bug symlinked-specs-root-is-followed-by-migration-and-repair (T-044-40, CWE-59),
    # sa-specs-upgrade-writes-through-symlinks#B5: every verb refuses at the one seam.
    pytest.param(_symlinked, ["specs", "upgrade", "--specs-dir", _SPECS], "symlink", id="B5-upgrade-symlinked-root"),
    pytest.param(_symlinked, ["doctor", "--specs-dir", _SPECS, "--fix"], "symlink", id="B5-doctor-fix-symlinked-root"),
    # sa-context-repo-mapping-falls-back-to-the-name#B2: a typo never becomes repos/alpah/.
    pytest.param(lambda r: None, ["specs", "init", "--context", "alpah"], "context list", id="B2-unregistered-context"),
    pytest.param(lambda r: None, ["specs", "init"], "specs init --context` with it", id="ADR-0045-no-context-resolved"),
]  # fmt: skip


@pytest.mark.parametrize(("plant", "argv", "text"), _REFUSALS)
def test_a_refusal_names_its_fix_and_writes_nothing(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    plant: Callable[[Path], object],
    argv: list[str],
    text: str,
) -> None:
    monkeypatch.setattr(sys, "prefix", str(repo.parent / "host-venv"))  # no workspace CLI
    plant(repo)
    workspace = repo.parents[1]
    before = _snapshot(workspace)

    result = _runner.invoke(app, argv)

    assert result.exit_code != 0 and text in result.output, result.output
    assert _snapshot(workspace) == before


def test_specs_init_writes_every_law_rendered(repo: Path) -> None:
    """sa-specs-init-writes-unrendered-law#B38-1: specs/AGENTS.md carries the canon
    table; sa-specs-init-writes-unrendered-law#B38-2: no law file `specs init` writes
    (specs tree and repo law) keeps a registry placeholder."""
    assert _runner.invoke(app, ["specs", "init", "--context", "c"]).exit_code == 0

    assert "| Area | Members |" in (repo / "specs" / "AGENTS.md").read_text(encoding="utf-8")
    raw = [
        f"{path.relative_to(repo)}: {marker}"
        for path in sorted(repo.rglob("*.md"))
        if ".git" not in path.parts
        for marker in _PLACEHOLDERS
        if marker in path.read_text(encoding="utf-8")
    ]
    assert raw == []
