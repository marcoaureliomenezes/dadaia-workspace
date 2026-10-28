"""The project gitflow value — roles fixed, names free."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.gitflow import (
    DEFAULT,
    Gitflow,
    SeveralWorkBranches,
    from_mapping,
    live_release_id,
    resolve_live_candidate,
    work_branch,
)
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import read_text, write_text


def test_the_default_names_live_only_in_default_and_work_is_cut_from_integration() -> None:
    """Only DEFAULT spells the principal name; the skill cuts work from integration."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    literal = re.compile(r'principal: main|"--principal", "main"|else "main"')
    assert [p.name for p in pkg.rglob("*.py") if literal.search(read_text(p))] == []
    skill = read_text(pkg / "public/skills/dd-gitflow-default/SKILL.md")
    work_row = next(r for r in skill.splitlines() if r.startswith("| work `"))
    assert work_row.split("|")[3].strip() == "integration"


def test_one_live_release_reader_and_no_verb_mints_a_version() -> None:
    """One reader of the live id, no tag+1; release-please owns the version.
    No module lists or bumps tags."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    src = {p.name: read_text(p) for p in pkg.rglob("*.py") if "public" not in p.parts}
    assert [n for n, t in src.items() if "def live_ids" in t] == []
    assert [n for n, t in src.items() if re.search(r'"tag", "--sort|\]\) \+ 1\}', t)] == []
    assert "release-please owns the version" in read_text(pkg.parent / "AGENTS.md")


def test_the_sole_live_release_is_the_kernels_and_several_refuse_there(tmp_path: Path) -> None:
    """None live: None; one: its id; several: the kernel refuses, the doctor-facing reader says None."""
    grammar, refusal = (load_owner("dd-bug-resolution", m) for m in ("_grammar", "_refusal"))
    assert (grammar.sole_live(tmp_path), live_release_id(tmp_path)) == (None, None)
    for rid in ("0.5.0", "0.6.0"):
        (tmp_path / "releases" / rid).mkdir(parents=True)
        write_text(tmp_path / "releases" / rid / "_RELEASE.json", "{}")
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


def test_resolve_live_candidate_names_the_candidate_release_py_names(tmp_path: Path) -> None:
    """A milestone makes the first candidate the live one; the empty folder after it is not."""
    release = tmp_path / "releases" / "0.5.0"
    (release / "rc-1").mkdir(parents=True)
    (release / "rc-2").mkdir()
    milestone = {"ts": "2026-09-21T10:00:00Z", "agent": "release.py", "kind": "milestone",
                 "candidate": "rc-1", "milestone": "implemented", "sha": "0000002", "text": "rc-1 implemented."}  # fmt: skip
    state = {"schema": "release-state-v1", "release": "0.5.0", "phase": "IMPLEMENTATION",
             "defined": None, "implemented": None, "shipped": None, "log": [milestone]}  # fmt: skip
    write_text(release / "_RELEASE.json", json.dumps(state))
    release_py = load_owner("dd-release-implementation", "_release_store").live_release(tmp_path)
    assert release_py.candidate == release / "rc-1"
    assert resolve_live_candidate(tmp_path) == release_py.candidate


def test_an_unreadable_state_names_no_live_candidate(tmp_path: Path) -> None:
    """The doctor's rule: a state it cannot read names no candidate; `release.py check` reports it."""
    release = tmp_path / "releases" / "0.5.0"
    (release / "rc-1").mkdir(parents=True)
    write_text(release / "_RELEASE.json", "{not json")
    assert resolve_live_candidate(tmp_path) is None


def test_a_log_the_schema_refuses_names_no_live_candidate(tmp_path: Path) -> None:
    release = tmp_path / "releases" / "0.5.0"
    (release / "rc-1").mkdir(parents=True)
    write_text(release / "_RELEASE.json", json.dumps({"phase": "IMPLEMENTATION", "log": [1]}))
    assert resolve_live_candidate(tmp_path) is None


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


def test_the_history_rewrite_rule_covers_only_the_branches_that_advance_by_merge() -> None:
    """A wt/* branch is rebased by its owner; the rule must not reach it,
    and both of its verbs (rewrite, force-push) take the same scope."""
    skill = read_text(
        Path(__file__).resolve().parents[2]
        / "dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md"
    )
    rows = [ln.split("|")[1:5] for ln in skill.splitlines() if re.match(r"\| [a-z]+( `|\s+\|)", ln)]
    covered = {r[0].split()[0] for r in rows if "wt/" not in r[0]}
    assert covered == {"work", "integration", "principal"}
    rule = next(ln for ln in skill.splitlines() if "pushed history" in ln)
    verbs, scope = rule.split("force-pushing,", 1)
    assert "pushed history of," in verbs
    assert "work, integration or principal branch" in scope
    assert "advances only by PR" not in scope
    pushable = {r[0].split()[0]: r[1].strip() for r in rows if "wt/" not in r[0]}
    assert pushable["integration"].startswith("Yes")
    assert pushable["principal"].startswith("Yes")
    assert not {"job", "backlog", "task", "plain"} & set(re.findall(r"\w+", scope))


def test_the_history_rewrite_rule_names_the_branches_that_never_rebase() -> None:
    """A wt/* branch is rebased by its owner."""
    skill = read_text(
        Path(__file__).resolve().parents[2]
        / "dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md"
    )
    rule = next(ln for ln in skill.splitlines() if "pushed history" in ln)
    rows = [
        ln.split("|")[1].split()[0]
        for ln in skill.splitlines()
        if re.match(r"\| (work|integration|principal|job|backlog|task|plain) ", ln)
    ]
    assert [r for r in rows if re.search(rf"\b{r}\b", rule)] == ["work", "integration", "principal"]
    assert "advances only by PR" not in rule


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
        write_text(repo / "specs/releases" / live / "_RELEASE.json", "{}")
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
def test_several_work_branches_refuse_as_the_one_error_type_that_carries_its_fix(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, ["feature/0.5.0", "feature/0.6.0"], None)
    with pytest.raises(DadaiaError) as refused:
        work_branch(repo, Gitflow("main", "dev", "feature/"), "r")
    assert refused.value.message == "2 work branches"
    assert refused.value.fix.startswith("Agent action: run `")
    assert str(refused.value) == f"2 work branches\nfix: {refused.value.fix}"


def test_several_work_branches_is_one_dadaia_error_built_from_message_text_and_keep() -> None:
    several = SeveralWorkBranches("2 work branches", "run `x`, then run `y`", "0.2.0")
    skill_class = load_owner("dd-gitflow-default", "_worktree_git").SeveralWork
    assert not isinstance(several, skill_class)
    assert isinstance(several, DadaiaError)
    assert (several.message, several.keep) == ("2 work branches", "0.2.0")
    assert several.fix == "Agent action: run `x`, then run `y`"
    assert str(several) == "2 work branches\nfix: Agent action: run `x`, then run `y`"


@pytest.mark.medium
def test_work_branch_with_several_raises_the_one_class_and_never_the_skills(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, ["feature/0.5.0", "feature/0.6.0"], None)
    with pytest.raises(SeveralWorkBranches) as refused:
        work_branch(repo, Gitflow("main", "dev", "feature/"), "r")
    skill_class = load_owner("dd-gitflow-default", "_worktree_git").SeveralWork
    assert type(refused.value) is SeveralWorkBranches
    assert not isinstance(refused.value, skill_class)
    assert refused.value.keep == "0.6.0"


def _constitution(tmp_path: Path, text: str) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    write_text(specs / "constitution.md", text)
    return specs


@pytest.mark.parametrize("eol", ["\n", "\r\n"])
@pytest.mark.parametrize("prefix", ["", "﻿"])
def test_merge_frontmatter_replaces_a_block_value_whole_and_keeps_the_rest(
    tmp_path: Path, prefix: str, eol: str
) -> None:
    from dadaia_workspace.core.gitflow import merge_frontmatter

    text = (
        "---\nconstitution_version: 7.0.0\nspecs_pattern_version:\n- 1\n- 2\n"
        "gitflow:\n  principal: x\n  work: y\nkeep:\n  - a\n---\n\n# body\n"
    )
    specs = _constitution(tmp_path, prefix + text.replace("\n", eol))

    merge_frontmatter(specs, specs_pattern_version=7, gitflow=Gitflow("main", "dev", "feature/"))

    assert read_text(specs / "constitution.md") == (
        "---\nconstitution_version: 7.0.0\nspecs_pattern_version: 7\n"
        'gitflow: {"principal": "main", "integration": "dev", "work": "feature/"}\n'
        "keep:\n  - a\n---\n\n# body\n"
    )


def test_merge_frontmatter_appends_an_absent_key_after_a_trailing_block_list(
    tmp_path: Path,
) -> None:
    from dadaia_workspace.core.gitflow import merge_frontmatter

    specs = _constitution(tmp_path, "---\nkeep:\n  - a\n---\nbody\n")

    merge_frontmatter(specs, specs_pattern_version=7)

    assert read_text(specs / "constitution.md") == (
        "---\nkeep:\n  - a\nspecs_pattern_version: 7\n---\nbody\n"
    )
