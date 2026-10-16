"""The project gitflow value — roles fixed, names free."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.gitflow import (
    DEFAULT,
    Gitflow,
    from_mapping,
    live_release_id,
    work_branch,
)
from dadaia_workspace.core.skill_owner import load_owner


def test_the_default_names_live_only_in_default_and_work_is_cut_from_integration() -> None:
    """Only DEFAULT spells the principal name; the skill cuts work from integration."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    literal = re.compile(r'principal: main|"--principal", "main"|else "main"')
    assert [p.name for p in pkg.rglob("*.py") if literal.search(p.read_text("utf-8"))] == []
    skill = (pkg / "public/skills/dd-gitflow-default/SKILL.md").read_text("utf-8")
    work_row = next(r for r in skill.splitlines() if r.startswith("| work `"))
    assert work_row.split("|")[3].strip() == "integration"


def test_one_live_release_reader_and_no_verb_mints_a_version() -> None:
    """One reader of the live id, no tag+1; release-please owns the version.
    No module lists or bumps tags."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    src = {p.name: p.read_text("utf-8") for p in pkg.rglob("*.py") if "public" not in p.parts}
    assert [n for n, t in src.items() if "def live_ids" in t] == []
    assert [n for n, t in src.items() if re.search(r'"tag", "--sort|\]\) \+ 1\}', t)] == []
    assert "release-please owns the version" in (pkg.parent / "AGENTS.md").read_text("utf-8")


def test_the_sole_live_release_is_the_kernels_and_several_refuse_there(tmp_path: Path) -> None:
    """None live: None; one: its id; several: the kernel refuses, the doctor-facing reader says None."""
    grammar, refusal = (load_owner("dd-bug-resolution", m) for m in ("_grammar", "_refusal"))
    assert (grammar.sole_live(tmp_path), live_release_id(tmp_path)) == (None, None)
    for rid in ("0.5.0", "0.6.0"):
        (tmp_path / "releases" / rid).mkdir(parents=True)
        (tmp_path / "releases" / rid / "_RELEASE.json").write_text("{}")
        if rid == "0.5.0":
            assert (grammar.sole_live(tmp_path), live_release_id(tmp_path)) == ("0.5.0",) * 2
    with pytest.raises(refusal.Refusal) as caught:
        grammar.sole_live(tmp_path)
    assert str(caught.value) == (
        "multiple live release directories carry _RELEASE.json: 0.5.0, 0.6.0 — exactly one is allowed"
    )
    assert caught.value.fix == (
        f"Agent action: keep one of 0.5.0, 0.6.0 live under {tmp_path / 'releases'};"
        " ship or move out the others"
    )
    assert live_release_id(tmp_path) is None


@pytest.mark.parametrize(
    ("branch", "role"),
    [
        ("main", "principal"),
        ("develop", "integration"),
        ("feature/0.5.0", "work"),
        ("feature/v0.5.0", None),
        ("feature/0.5", None),
        ("feature/0.5.0-rc", None),
        ("hotfix/1.0.0", None),
        ("trunk", None),
    ],
)
def test_role_of_default(branch: str, role: str | None) -> None:
    assert DEFAULT.role_of(branch) == role


def test_from_mapping_reads_the_block_keys_and_maps_their_roles() -> None:
    flow = from_mapping({"principal": "trunk", "integration": "next", "work": "work/"})
    roles = [flow.role_of(b) for b in ("trunk", "next", "work/1.2.3", "main", "feature/1.2.3")]
    assert roles == ["principal", "integration", "work", None, None]


@pytest.mark.parametrize(
    "mapping",
    [
        {"principal": "main", "integration": "main", "work": "feature/"},  # same name twice
        {"principal": "main", "integration": "develop", "work": ""},  # empty prefix
        {"principal": "main", "integration": "develop"},  # key missing
        {"principal": "ma in", "integration": "develop", "work": "feature/"},
        {"principal": "main", "integration": "dev..x", "work": "feature/"},
        {"principal": "main", "integration": "develop", "work": "/feature/"},
        {"principal": "a.lock", "integration": "develop", "work": "feature/"},
        {"principal": 7, "integration": "develop", "work": "feature/"},
        {"principal": "release", "integration": "develop", "work": "release/"},  # nests
        {"principal": "main", "integration": "rel", "work": "rel/v"},  # nests
        "main",
    ],
)
def test_from_mapping_refuses_invalid(mapping: object) -> None:
    with pytest.raises(ValueError):
        from_mapping(mapping)


def test_the_history_rewrite_rule_covers_only_the_branches_that_advance_by_merge_or_pr() -> None:
    """A wt/* branch is rebased by its owner; the rule must not reach it,
    and both of its verbs (rewrite, force-push) take the same scope."""
    skill = (
        Path(__file__).resolve().parents[2]
        / "dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md"
    ).read_text("utf-8")
    rows = [ln.split("|")[1:5] for ln in skill.splitlines() if re.match(r"\| [a-z]+( `|\s+\|)", ln)]
    covered = {r[0].split()[0] for r in rows if "wt/" not in r[0]}
    assert covered == {"work", "integration", "principal"}
    rule = next(ln for ln in skill.splitlines() if "pushed history" in ln)
    verbs, scope = rule.split("force-pushing,", 1)
    assert "pushed history of," in verbs
    assert "work branch" in scope
    assert "advances only by PR" in scope
    assert not {"job", "backlog", "task", "plain"} & set(re.findall(r"\w+", scope))


def test_the_history_rewrite_rule_scopes_to_the_branches_that_never_rebase() -> None:
    """A wt/* branch is rebased by its owner."""
    skill = (
        Path(__file__).resolve().parents[2]
        / "dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md"
    ).read_text("utf-8")
    rule = next(ln for ln in skill.splitlines() if "pushed history" in ln)
    rows = [
        ln.split("|")[1].split()[0]
        for ln in skill.splitlines()
        if re.match(r"\| (work|integration|principal|job|backlog|task|plain) ", ln)
    ]
    assert [r for r in rows if re.search(rf"\b{r}\b", rule)] == ["work"]
    assert "advances only by PR" in rule


def _repo(tmp_path: Path, heads: list[str], live: str | None) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    git = load_owner("dd-gitflow-default", "_worktree_git").git
    git(repo, "init", "-q")
    git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "i",
    )
    for head in heads:
        git(repo, "branch", head)
    if live:
        (repo / "specs/releases" / live).mkdir(parents=True)
        (repo / "specs/releases" / live / "_RELEASE.json").write_text("{}")
    return repo


@pytest.mark.medium
@pytest.mark.parametrize(
    ("heads", "live", "name"),
    [
        (["feature/0.6.0"], "0.5.0", "feature/0.6.0"),
        (["feature/0.6.0"], None, "feature/0.6.0"),
        ([], "0.5.0", "feature/0.5.0"),
    ],
    ids=["window", "after-ship", "to-create"],
)
def test_the_work_branch_is_the_one_local_branch_else_the_name_to_create(
    tmp_path: Path, heads: list[str], live: str | None, name: str
) -> None:
    repo = _repo(tmp_path, heads, live)
    assert work_branch(repo, Gitflow("main", "dev", "feature/"), "r") == name


@pytest.mark.medium
def test_several_work_branches_refuse_with_the_skills_fix_line(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["feature/0.5.0", "feature/0.6.0"], "0.5.0")
    git = load_owner("dd-gitflow-default", "_worktree_git").git
    git(repo, "switch", "-q", "feature/0.5.0")
    git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "lower",
    )
    with pytest.raises(load_owner("dd-gitflow-default", "_worktree_names").Refusal) as refused:
        work_branch(repo, Gitflow("main", "dev", "feature/"), "r")
    assert refused.value.fix == (
        f"Agent action: run `{git_line(repo, 'switch', 'feature/0.6.0')}`, then merge feature/0.5.0 into feature/0.6.0, then run `{git_line(repo, 'branch', '-d', 'feature/0.5.0')}`"
    )


@pytest.mark.medium
def test_several_work_branches_refuse_as_the_one_error_type_that_carries_its_fix(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, ["feature/0.5.0", "feature/0.6.0"], None)
    with pytest.raises(DadaiaError) as refused:
        work_branch(repo, Gitflow("main", "dev", "feature/"), "r")
    assert refused.value.message == "2 work branches"
    fix = f"Agent action: run `{git_line(repo, 'switch', 'feature/0.6.0')}`, then run `{git_line(repo, 'branch', '-d', 'feature/0.5.0')}`"
    assert refused.value.fix == fix
    assert str(refused.value) == f"2 work branches\nfix: {fix}"
