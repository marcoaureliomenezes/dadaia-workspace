"""`verdict.py` is the reviewer's one writer of a verdict handoff, bound to the
sha and diff hash it judged; every refusal writes nothing. Size: MEDIUM (real git, tmp workspace)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jsonschema
import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.harness_env import suite_env
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import commit, git, make_workspace, run

PKG = Path(__file__).resolve().parents[5] / "dadaia_workspace"
SKILL = "dd-handoff-emitter"
BODY = {
    "self_pull": {"refs": ["specs/memory/ARCHITECTURE.md"]},
    "metrics": {},
    "artifact": {"type": "other"},
}
RESERVED = (
    "agent",
    "verdict",
    "verdict_reason",
    "reviewed_sha",
    "diff_sha256",
    "scope",
    "produced_at",
    "context",
    "schema_version",
)
RED = "reviewer-emits-own-verdict (ADR 0218)"


def _workspace(tmp_path: Path) -> tuple[Path, Path, str]:
    """A workspace whose skill scripts sit where an install puts them; a `define` tree at HEAD."""
    assert (PKG / "public/skills" / SKILL / "scripts/verdict.py").is_file(), "verdict.py is absent"
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    for skill in (SKILL, "dd-gitflow-default", "dd-bug-resolution", "dd-release-implementation"):
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "0.5.0-rc1/define").returncode == 0
    tree = root / "worktrees/r/0.5.0-rc1/define"
    return root, tree, commit(tree, "specs/notes", "")


def _verdict(
    root: Path,
    tree: Path | str,
    *,
    sha: str,
    stdin: str | None = None,
    slug: str = "s",
    **over: str,
) -> subprocess.CompletedProcess[str]:
    script = root / ".agents/skills" / SKILL / "scripts/verdict.py"
    args = {"--context": "c", "--slug": slug, "--verdict": "APPROVED", "--reason": "r", **over}
    cmd = [
        sys.executable,
        str(script),
        str(tree),
        "--sha",
        sha,
        *(a for kv in args.items() for a in kv),
    ]
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"PATH": os.environ["PATH"], "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    return subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        input=json.dumps(BODY) if stdin is None else stdin,
    )


def _written(root: Path) -> list[Path]:
    return sorted((root / ".dadaia/handoff").glob("**/*.handoff.json"))


def test_a_verdict_binds_the_head_it_judged_and_the_merge_lands_on_it(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    done = _verdict(root, tree, sha=head)
    assert done.returncode == 0, done.stderr
    (path,) = _written(root)
    assert path.parent == root / ".dadaia/handoff/c" and path.name.endswith(
        "-dd-code-reviewer-s.handoff.json"
    )
    body = json.loads(path.read_text())
    assert (
        body["reviewed_sha"] == head
        and body["agent"] == "dd-code-reviewer"
        and body["verdict"] == "APPROVED"
    )
    assert done.stdout.strip() == str(path)
    schema = json.loads((PKG / "public/schemas/handoff-v1.schema.json").read_text())
    jsonschema.validate(body, schema)
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr


def test_a_verdict_for_a_sha_a_later_commit_left_behind_is_refused_by_the_merge(
    tmp_path: Path,
) -> None:
    root, tree, old = _workspace(tmp_path)
    assert _verdict(root, tree, sha=old).returncode == 0
    commit(tree, "specs/later", "x\n")
    refused = run(root, "merge", str(tree))
    assert refused.returncode != 0 and "reports validate" in refused.stderr


_CASES = [(f'{{"{k}": "x"}}', k) for k in RESERVED] + [
    ("", "empty"), ("not json", "non-json"), ("[1]", "array"),
]  # fmt: skip


@pytest.mark.parametrize(("stdin", "why"), _CASES, ids=[w for _, w in _CASES])
def test_a_bad_stdin_is_refused_and_writes_nothing(tmp_path: Path, stdin: str, why: str) -> None:
    root, tree, head = _workspace(tmp_path)
    refused = _verdict(root, tree, sha=head, stdin=stdin)
    assert refused.returncode != 0 and refused.stderr, why
    assert _written(root) == []


def test_a_path_that_is_no_worktree_is_refused_with_the_hash_verbs_own_words(
    tmp_path: Path,
) -> None:
    root, tree, head = _workspace(tmp_path)
    (plain := tmp_path / "plain").mkdir()
    staged = (
        root / ".agents/skills/dd-gitflow-default/scripts/worktree.py"
    )  # its fix line names itself
    hash_cmd = [sys.executable, str(staged), "hash", str(plain), "--sha", head]
    own = subprocess.run(
        hash_cmd,
        cwd=root,
        capture_output=True,
        text=True,
        env=suite_env(
            os.environ, Path.home(), overrides={"PATH": os.environ["PATH"], "HOME": str(root)}
        ),
    )
    assert own.returncode != 0 and own.stderr
    refused = _verdict(root, plain, sha=head)
    assert refused.returncode == own.returncode and refused.stderr == own.stderr
    assert _written(root) == []


def test_an_unknown_sha_is_refused_with_the_hash_verbs_own_words(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    own = run(root, "hash", str(tree), "--sha", "0" * 40)
    assert own.returncode != 0 and own.stderr
    refused = _verdict(root, tree, sha="0" * 40)
    assert refused.returncode == own.returncode and refused.stderr == own.stderr
    assert _written(root) == []


def test_a_slug_that_climbs_out_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    refused = _verdict(root, tree, sha=head, slug="../x")
    assert refused.returncode != 0 and refused.stderr
    assert _written(root) == [] and not (root / ".dadaia/handoff/x").exists()


def _tree_files(top: Path) -> set[Path]:
    return {p for p in top.rglob("*") if p.is_file() and ".git" not in p.parts}


@pytest.mark.parametrize("name", ["--context", "--slug"])
@pytest.mark.parametrize("bad", ["../../evil", "a/b", "a\\b", "_x", "A", ""])
def test_a_bad_context_or_slug_is_refused_by_name_and_writes_nothing_anywhere(
    tmp_path: Path, name: str, bad: str
) -> None:
    root, tree, head = _workspace(tmp_path)
    before = _tree_files(tmp_path)
    refused = _verdict(root, tree, sha=head, **{name: bad})
    assert refused.returncode == 1
    assert refused.stderr.startswith(f"[error] {name} must match ")
    assert "Traceback" not in refused.stderr
    assert _tree_files(tmp_path) == before


@pytest.mark.parametrize("ctx", ["My_Ctx", "A", "_x"])
def test_a_context_the_core_grammar_accepts_receives_its_verdict(tmp_path: Path, ctx: str) -> None:
    root, tree, head = _workspace(tmp_path)
    done = _verdict(root, tree, sha=head, **{"--context": ctx})
    assert done.returncode == 0, done.stderr
    (path,) = _written(root)
    assert path.parent == root / ".dadaia/handoff" / ctx


@pytest.mark.parametrize("stdin", ["[1]", "3", "null", '"s"'])
def test_a_non_object_json_is_refused_with_text_and_no_traceback(
    tmp_path: Path, stdin: str
) -> None:
    root, tree, head = _workspace(tmp_path)
    refused = _verdict(root, tree, sha=head, stdin=stdin)
    assert refused.returncode == 1
    assert refused.stderr == "[error] stdin is not a JSON object\n"
    assert _written(root) == []


def test_a_verdict_in_a_second_already_taken_never_overwrites_the_first(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    out = root / ".dadaia/handoff/c"
    out.mkdir(parents=True)
    now = datetime.now(UTC)
    taken = [
        out / f"{now + timedelta(seconds=i):%Y-%m-%dT%H%M%SZ}-dd-code-reviewer-s.handoff.json"
        for i in range(-2, 8)  # every second the run can stamp
    ]
    for path in taken:
        path.write_text("first")
    refused = _verdict(root, tree, sha=head)
    assert refused.returncode == 1
    assert refused.stderr.startswith("[error] ") and refused.stderr.endswith(
        "exists; rerun in a second\n"
    )
    assert [p.read_text() for p in taken] == ["first"] * len(taken)
    assert set(_written(root)) == set(taken)


def test_the_file_name_stamp_and_produced_at_are_one_instant(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    assert _verdict(root, tree, sha=head).returncode == 0
    (path,) = _written(root)
    stamp = path.name.removesuffix("-dd-code-reviewer-s.handoff.json")
    produced = json.loads(path.read_text())["produced_at"]
    assert datetime.strptime(stamp, "%Y-%m-%dT%H%M%SZ") == datetime.strptime(
        produced, "%Y-%m-%dT%H:%M:%SZ"
    )


@pytest.mark.parametrize("slug", ["a--b", "1a", "a-", "-a", "a_b", "A", "a-b", "a1", "a", "a-1-b"])
def test_a_slug_is_accepted_exactly_as_the_backlog_slug_pattern_says(
    tmp_path: Path, slug: str
) -> None:
    """The verdict slug and the backlog slug are one grammar, read from `backlog-v1`
    (`$defs.slug`) — never restated here. `a--b` is the worktree job/task separator: refused;
    today the verdict's own looser pattern lets `a--b`, `1a` and `a-` through."""
    schema = load_owner("dd-bug-resolution", "_ledger").load_schema("backlog-v1")
    legal = re.fullmatch(schema["$defs"]["slug"]["pattern"], slug) is not None
    root, tree, head = _workspace(tmp_path)
    done = _verdict(root, tree, sha=head, slug=slug)
    assert (done.returncode == 0) is legal, done.stderr
    assert len(_written(root)) == int(legal)


def _record(
    root: Path,
    scope: str,
    verdict: str,
    at: str,
    *,
    hold: bool = False,
    agent: str = "dd-code-reviewer",
) -> None:
    """A verdict handoff with the keys `verdict.py` writes (schema-validated), at *at* seconds."""
    produced = f"2026-10-12T10:00:{at}Z"
    body = {
        "schema_version": "handoff-v1.2",
        "agent": agent,
        "context": "c",
        "produced_at": produced,
        "verdict": verdict,
        "verdict_reason": "r",
        "scope": scope,
        "reviewed_sha": "a" * 40,
        "diff_sha256": "b" * 64,
        **BODY,
    }
    schema = json.loads((PKG / "public/schemas/handoff-v1.schema.json").read_text())
    jsonschema.validate(body, schema)
    base = root / (".dadaia/reaped/x/.dadaia/handoff/c" if hold else ".dadaia/handoff/c")
    base.mkdir(parents=True, exist_ok=True)
    name = f"{produced.replace(':', '')}-{agent}-{verdict}-{scope.replace('/', '_')}.handoff.json"
    (base / name).write_text(json.dumps(body, indent=2) + "\n")


def test_stats_counts_the_rc_verdict_sequences_in_produced_at_order(tmp_path: Path) -> None:
    root, _tree, _head = _workspace(tmp_path)
    rc99, sha = "wt/0.5.0-rc99", "@" + "a" * 40
    # written out of time order: the count reads `produced_at`, not the file listing
    _record(root, f"{rc99}/job1{sha}", "REJECTED", "03")
    _record(root, f"{rc99}/job1{sha}", "REJECTED", "01")
    _record(root, f"{rc99}/job1{sha}", "APPROVED", "02")
    _record(root, f"{rc99}/job2{sha}", "APPROVED", "01", hold=True)
    _record(root, f"{rc99}/job3{sha}", "REJECTED", "01")
    _record(root, f"{rc99}/job3{sha}", "REJECTED", "02")
    _record(root, f"{rc99}/job3{sha}", "APPROVED", "03")
    _record(root, f"wt/0.5.0-rc98/job1{sha}", "REJECTED", "01")
    _record(root, f"{rc99}/job4{sha}", "REJECTED", "01", agent="dd-sw-engineer-sr")
    script = root / ".agents/skills" / SKILL / "scripts/verdict.py"
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"PATH": os.environ["PATH"], "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    done = subprocess.run(
        [sys.executable, str(script), "stats", "0.5.0-rc99"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert (done.returncode, done.stdout) == (
        0,
        "sequences 4\nverdicts 7\nrejected 4\nfirst_pass_rejected 3/4\n",
    ), done.stderr
