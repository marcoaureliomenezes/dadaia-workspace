"""`verdict.py` is the reviewer's one writer of a verdict handoff, bound to the
sha and diff hash it judged; every refusal writes nothing. Size: MEDIUM (real git, tmp workspace)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jsonschema
import pytest

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import command, read_text, write_text
from tests.helpers.oslib import run as os_run
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import commit, fixes, git, make_workspace, patch_cli, run

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
    """A workspace whose skill scripts sit where an install puts them; a backlog lane at HEAD."""
    assert (PKG / "public/skills" / SKILL / "scripts/verdict.py").is_file(), "verdict.py is absent"
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    for skill in (SKILL, "dd-gitflow-default", "dd-bug-resolution", "dd-release-implementation"):
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "0.5.0/wt-backlog-notes").returncode == 0
    tree = root / "worktrees/r/0.5.0/wt-backlog-notes"
    return root, tree, commit(tree, "specs/notes", "")


def _verdict(
    root: Path,
    tree: Path | str,
    *,
    sha: str,
    stdin: str | None = None,
    slug: str = "s",
    cwd: Path | None = None,
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
    return os_run(cmd, cwd=cwd or root, env=env, input=json.dumps(BODY) if stdin is None else stdin)


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
    body = json.loads(read_text(path))
    assert (
        body["reviewed_sha"] == head
        and body["agent"] == "dd-code-reviewer"
        and body["verdict"] == "APPROVED"
    )
    assert done.stdout.strip() == str(path)
    schema = json.loads(read_text(PKG / "public/schemas/handoff-v1.schema.json"))
    jsonschema.validate(body, schema)
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr


def test_a_verdict_for_a_sha_a_later_commit_left_behind_is_refused_by_the_merge(
    tmp_path: Path,
) -> None:
    root, tree, old = _workspace(tmp_path)
    assert _verdict(root, tree, sha=old).returncode == 0
    head = commit(tree, "specs/later", "x\n")
    refused = run(root, "merge", str(tree))
    assert refused.returncode != 0
    assert (
        f"fix: Agent action: dispatch dd-code-reviewer on {tree} at HEAD {head}; " in refused.stderr
    )


_OWNED = "stdin sets keys verdict.py owns: "
_CASES = [(f'{{"{k}": "x"}}', k, f"{_OWNED}{k}") for k in RESERVED] + [
    ("", "empty", "stdin is not JSON"),
    ("not json", "non-json", "stdin is not JSON"),
    ("[1]", "array", "stdin is not a JSON object"),
]  # fmt: skip


@pytest.mark.parametrize(("stdin", "why", "message"), _CASES, ids=[w for _, w, _ in _CASES])
def test_a_bad_stdin_is_refused_and_writes_nothing(
    tmp_path: Path, stdin: str, why: str, message: str
) -> None:
    root, tree, head = _workspace(tmp_path)
    refused = _verdict(root, tree, sha=head, stdin=stdin)
    assert refused.returncode == 1, why
    assert refused.stderr == (
        f"[error] {message}\nfix: Agent action: pipe one JSON object without the keys"
        " verdict.py owns, then rerun verdict.py\n"
    ), why
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
    own = os_run(
        hash_cmd,
        cwd=root,
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


_CLIMBING = ["../../evil", "a/b", "a\\b", ""]


@pytest.mark.parametrize(
    ("name", "bad"),
    [("--context", b) for b in _CLIMBING] + [("--slug", b) for b in [*_CLIMBING, "_x", "A"]],
)
def test_a_bad_context_or_slug_is_refused_by_name_and_writes_nothing_anywhere(
    tmp_path: Path, name: str, bad: str
) -> None:
    root, tree, head = _workspace(tmp_path)
    before = _tree_files(tmp_path)
    refused = _verdict(root, tree, sha=head, **{name: bad})
    assert refused.returncode == 1
    assert refused.stderr.startswith(f"[error] {name} must match ")
    assert refused.stderr.endswith(
        f"\nfix: Agent action: pass a {name[2:]} matching that pattern, then rerun verdict.py\n"
    )
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
    assert refused.stderr == (
        "[error] stdin is not a JSON object\nfix: Agent action: pipe one JSON object"
        " without the keys verdict.py owns, then rerun verdict.py\n"
    )
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
        write_text(path, "first")
    refused = _verdict(root, tree, sha=head)
    assert refused.returncode == 1
    assert refused.stderr.startswith("[error] ") and refused.stderr.endswith(
        "exists; rerun in a second\nfix: Agent action: rerun verdict.py in a second\n"
    )
    assert [read_text(p) for p in taken] == ["first"] * len(taken)
    assert set(_written(root)) == set(taken)


def test_the_file_name_stamp_and_produced_at_are_one_instant(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    assert _verdict(root, tree, sha=head).returncode == 0
    (path,) = _written(root)
    stamp = path.name.removesuffix("-dd-code-reviewer-s.handoff.json")
    produced = json.loads(read_text(path))["produced_at"]
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
    minute: str = "2026-10-12T10:00",
    context: str = "c",
) -> None:
    """A verdict handoff with the keys `verdict.py` writes (schema-validated), at *at* seconds."""
    produced = f"{minute}:{at}Z"
    body = {
        "schema_version": "handoff-v1.2",
        "agent": agent,
        "context": context,
        "produced_at": produced,
        "verdict": verdict,
        "verdict_reason": "r",
        "scope": scope,
        "reviewed_sha": "a" * 40,
        "diff_sha256": "b" * 64,
        **BODY,
    }
    schema = json.loads(read_text(PKG / "public/schemas/handoff-v1.schema.json"))
    jsonschema.validate(body, schema)
    base = root / (
        f".dadaia/reaped/x/.dadaia/handoff/{context}" if hold else f".dadaia/handoff/{context}"
    )
    base.mkdir(parents=True, exist_ok=True)
    name = f"{produced.replace(':', '')}-{agent}-{verdict}-{scope.replace('/', '_')}.handoff.json"
    write_text(base / name, json.dumps(body, indent=2) + "\n")


def _stats_workspace(tmp_path: Path) -> Path:
    """A workspace with the skill scripts where an install puts them."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    for skill in (SKILL, "dd-bug-resolution", "dd-release-implementation"):
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    patch_cli(root, '"main_repo": "r"', '"name": "c", "main_repo": "r"')
    return root


def _log(root: Path, log: list[dict[str, str]]) -> None:
    state = root / "repos/r/specs/releases/0.5.0/_RELEASE.json"
    write_text(state, json.dumps({**json.loads(read_text(state)), "log": log}))
    # a state `release.py check` passes holds the folder of each candidate its log names
    for rc in {e["candidate"] for e in log if "candidate" in e and e["candidate"][:3] == "rc-"}:
        if not (state.parent / rc).exists():
            shutil.copytree(state.parent / "rc-1", state.parent / rc)


_CHECK_OK = 'if sys.argv[1] == "check":\n    sys.exit(0)\n'


def _stub(root: Path, skill: str, script: str, body: str) -> None:
    write_text(root / ".agents/skills" / skill / "scripts" / script, f"import sys\n{body}\n")


def _stats(
    root: Path, rc: str = "0.5.0-rc99", specs: str = "repos/r/specs"
) -> subprocess.CompletedProcess[str]:
    script = root / ".agents/skills" / SKILL / "scripts/verdict.py"
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"PATH": os.environ["PATH"], "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    argv = [sys.executable, str(script), "stats", rc, "--specs", specs]
    return os_run(argv, cwd=root, env=env)


def _entry(ts: str, kind: str, text: str, **more: str) -> dict[str, str]:
    agent = "release.py new" if " born" in text else "release.py"
    return {"ts": ts, "agent": agent, "kind": kind, "text": text, **more}


def _born(ts: str) -> dict[str, str]:
    return _entry(ts, "note", "Candidate born on 0.5.0 (prior candidate closed at x)")


def _milestone(ts: str, rc: str, milestone: str, sha: str) -> dict[str, str]:
    return _entry(
        ts, "milestone", f"{milestone} at {sha}", candidate=rc, milestone=milestone, sha=sha
    )


def test_stats_prints_the_local_metric_table_over_the_candidate_window(tmp_path: Path) -> None:
    """A lane tree and a free-named tree count, a tree outside birth-to-CLOSURE does not, a record
    held by the reaper is read, and the oldest record read is printed whatever its window."""
    root = _stats_workspace(tmp_path)
    repo = root / "repos/r"
    closure = git(repo, "rev-parse", "HEAD").strip()
    _log(
        root,
        [
            _born("2026-10-10T08:00:00Z"),
            _milestone("2026-10-11T08:00:00Z", "rc-98", "implemented", "0" * 40),
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T09:30:00Z", "rc-99", "defined", "1" * 40),
            _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", closure),
            _born("2026-10-12T14:30:00Z"),
        ],
    )
    git(repo, "branch", "dev")
    git(repo, "checkout", "-q", "-b", "topic")
    for message in (
        "fix(bugs): a - cause\n\nblock: item",
        "refactor(J1.T1): REBUILD x",
        "docs(memory): reconcile",
        "feat(J1.T2): y",
        "docs(law): z",
        "chore(release): w",
    ):
        git(repo, "commit", "-q", "--allow-empty", "-m", message)
    git(repo, "checkout", "-q", "dev")
    merged = suite_env(
        os.environ,
        Path.home(),
        overrides={
            "HOME": str(repo),
            "PATH": os.environ["PATH"],
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_COMMITTER_DATE": "2026-10-12T14:30:00Z",
        },
    )
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    landed = os_run(["git", *ident, "merge", "-q", "--no-ff", "-m", "Merge candidate", "topic"], cwd=repo, env=merged)  # fmt: skip
    assert landed.returncode == 0, landed.stderr
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J9.T9): a later candidate's work")
    ledger = repo / "specs/bugs"
    for name, rows in (
        ("BUGS.jsonl", (("a", "none", "10:30"), ("b", "a", "10:31"))),
        (
            "_archive/bugs_histo.jsonl",
            (("c", "none", "10:32"), ("d", "none", "10:33"), ("e", "x", "09:59")),
        ),
    ):
        (ledger / name).parent.mkdir(parents=True, exist_ok=True)
        day = lambda hhmm, n=name: "2026-10-10" if hhmm == "09:59" else "2026-10-12"  # noqa: E731
        write_text(
            ledger / name,
            "".join(
                json.dumps({"id": i, "status": "resolved", "caused_by": by,
                            "closed_at": f"{day(at)}T{at}:00Z"}) + "\n"
                for i, by, at in rows
            ),
        )  # fmt: skip
    histo = ledger / "_archive/bugs_histo.jsonl"
    event = {"ts": "2026-08-28T12:45:33Z", "event": "archived", "agent": "claude-code", "data": {"id": "g", "status": "Closed"}}  # fmt: skip
    write_text(histo, json.dumps(event) + "\n" + read_text(histo))
    write_text(ledger / "BUGS.jsonl", read_text(ledger / "BUGS.jsonl") + json.dumps({"id": "f", "status": "open", "caused_by": "none"}) + "\n")  # fmt: skip
    sha = "@" + "a" * 40
    # written out of time order: the first verdict of a tree is read by `produced_at`
    _record(root, f"wt/0.5.0/rc-99/job-3/wt-main{sha}", "APPROVED", "03")
    _record(root, f"wt/0.5.0/rc-99/job-3/wt-main{sha}", "REJECTED", "01")
    _record(root, f"wt/0.5.0/rc-99/job-1/wt-main{sha}", "APPROVED", "01")
    _record(root, f"wt/0.5.0/wt-backlog-notes{sha}", "APPROVED", "01", hold=True)
    _record(root, f"wt/0.5.0/free-tree{sha}", "REJECTED", "01")
    _record(root, f"wt/0.5.0/wt-hotfix-old{sha}", "REJECTED", "01", minute="2026-10-09T10:00")
    _record(root, f"wt/0.5.0/rc-99/job-4/wt-main{sha}", "REJECTED", "01", agent="dd-sw-engineer-sr")
    _record(root, f"wt/0.5.0/rc-99/job-9/wt-main{sha}", "APPROVED", "01", context="other")
    _stub(root, "dd-bug-resolution", "bugs.py",
          'assert sys.argv[1] == "stats"\nprint("total\\t9")\nprint("closed\\t4\\nfix-induced\\t1\\nrebuild-due\\t1")\nprint("rebuild-due:a.py\\ta,z")\nprint("rebuild-due:b.py\\te,w")')  # fmt: skip
    _stub(root, "dd-release-implementation", "release.py",
          _CHECK_OK + 'assert sys.argv[1:3] == ["drift", "--json"]\nprint(\'{"since": "s", "atoms": ["a", "b", "c"], "uncovered": []}\')\nsys.exit(1)')  # fmt: skip
    done = _stats(root)
    assert (done.returncode, done.stdout) == (
        0,
        "metric\tvalue\ttarget\n"
        "1 fix-induced bugs\t1/4 (25%)\t<= 20%\n"
        "2 first-pass approval\t2/4 (50%)\t>= 70%\n"
        "4 closure duration\t3.5 h\t<= 4 h\n"
        "6 non-block commits after closure\t3\t0\n"
        "7 memory drift\t3\t0\n"
        "9 rebuild-due patches\t1\t0\n"
        "oldest record\t2026-10-09T10:00:01Z\n",
    ), done.stderr


def test_stats_of_a_worktree_reads_the_same_table_as_the_repo_checkout(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    repo = root / "repos/r"
    _log(root, [_born("2026-10-12T09:00:00Z"),
                _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", git(repo, "rev-parse", "HEAD").strip())])  # fmt: skip
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "state")
    tree = root / "worktrees/r/wt-rc"
    git(repo, "worktree", "add", "-q", "-b", "wt-rc", str(tree))
    _record(root, "wt/0.5.0/rc-99/job-1/wt-main@" + "a" * 40, "APPROVED", "01")
    main, moved = _stats(root), _stats(root, specs="worktrees/r/wt-rc/specs")
    assert main.returncode == moved.returncode == 0, moved.stderr
    assert "2 first-pass approval\t1/1 (100%)\t>= 70%\n" in moved.stdout
    assert moved.stdout == main.stdout


def test_stats_reads_closure_duration_as_n_a_before_the_integration_merge(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    repo = root / "repos/r"
    closure = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "branch", "dev")
    _log(
        root,
        [
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T09:30:00Z", "rc-99", "defined", "1" * 40),
            _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", closure),
        ],
    )
    done = _stats(root)
    assert done.returncode == 0, done.stderr
    assert "4 closure duration\tn/a\t<= 4 h" in done.stdout.splitlines()


def test_stats_reads_memory_drift_only_for_the_newest_candidate(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    _log(
        root,
        [
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T09:30:00Z", "rc-99", "defined", "1" * 40),
            _born("2026-10-12T14:30:00Z"),
            _milestone("2026-10-12T15:00:00Z", "rc-100", "defined", "2" * 40),
        ],
    )
    _stub(root, "dd-release-implementation", "release.py",
          _CHECK_OK + 'print(\'{"since": "s", "atoms": ["a"], "uncovered": []}\')\nsys.exit(1)')  # fmt: skip
    older, newest = _stats(root), _stats(root, "0.5.0-rc100")
    assert "7 memory drift\tn/a\t0" in older.stdout.splitlines(), older.stderr
    assert "7 memory drift\t1\t0" in newest.stdout.splitlines(), newest.stderr


def test_stats_window_of_a_first_candidate_opens_at_its_release_born_note(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    _log(
        root,
        [
            _entry("2026-10-12T09:00:00Z", "note", "Release 0.5.0 born"),
            _milestone("2026-10-12T09:30:00Z", "rc-1", "defined", "1" * 40),
            _milestone("2026-10-12T11:00:00Z", "rc-1", "implemented", "2" * 40),
            _born("2026-10-12T14:30:00Z"),
        ],
    )
    _record(root, f"wt/0.5.0/rc-1/job-1/wt-main@{'a' * 40}", "APPROVED", "01")
    done = _stats(root, "0.5.0-rc1")
    assert "2 first-pass approval\t1/1 (100%)\t>= 70%" in done.stdout.splitlines(), done.stderr


def test_stats_reads_absent_data_as_n_a_and_exits_zero(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    _log(
        root,
        [
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T09:30:00Z", "rc-99", "defined", "1" * 40),
        ],
    )
    _stub(root, "dd-bug-resolution", "bugs.py", "sys.exit(1)")
    _stub(root, "dd-release-implementation", "release.py", _CHECK_OK + "sys.exit(1)")
    done = _stats(root)
    assert (done.returncode, done.stdout) == (
        0,
        "metric\tvalue\ttarget\n"
        "1 fix-induced bugs\tn/a\t<= 20%\n"
        "2 first-pass approval\tn/a\t>= 70%\n"
        "4 closure duration\tn/a\t<= 4 h\n"
        "6 non-block commits after closure\tn/a\t0\n"
        "7 memory drift\tn/a\t0\n"
        "9 rebuild-due patches\tn/a\t0\n"
        "oldest record\tn/a\n",
    ), done.stderr


def _closed(root: Path, *rows: tuple[str, str, str]) -> None:
    """Resolved bugs `(id, caused_by, closed_at)` in the repo's ledger."""
    (ledger := root / "repos/r/specs/bugs/BUGS.jsonl").parent.mkdir(parents=True, exist_ok=True)
    write_text(
        ledger,
        "".join(
            json.dumps({"id": i, "status": "resolved", "caused_by": by, "closed_at": at}) + "\n"
            for i, by, at in rows
        ),
    )


def _metric1(done: subprocess.CompletedProcess[str]) -> str:
    assert done.returncode == 0, done.stderr
    return next(x for x in done.stdout.splitlines() if x.startswith("1 "))


def test_stats_of_a_candidate_the_log_never_names_reads_n_a_for_every_metric(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    _log(
        root,
        [
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T11:00:00Z", "rc-98", "implemented", "1" * 40),
        ],
    )
    _closed(root, ("a", "x", "2026-10-12T12:00:00Z"))
    done = _stats(root, "0.5.0-rc99")
    assert (done.returncode, done.stdout) == (
        0,
        "metric\tvalue\ttarget\n"
        "1 fix-induced bugs\tn/a\t<= 20%\n"
        "2 first-pass approval\tn/a\t>= 70%\n"
        "4 closure duration\tn/a\t<= 4 h\n"
        "6 non-block commits after closure\tn/a\t0\n"
        "7 memory drift\tn/a\t0\n"
        "9 rebuild-due patches\tn/a\t0\n"
        "oldest record\tn/a\n",
    ), done.stderr


def test_stats_counts_a_bug_closed_between_two_candidates_in_exactly_one_window(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    _log(
        root,
        [
            _born("2026-10-10T08:00:00Z"),
            _milestone("2026-10-11T08:00:00Z", "rc-98", "implemented", "1" * 40),
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", "2" * 40),
        ],
    )
    _closed(
        root,
        ("x", "none", "2026-10-11T08:00:00Z"),
        ("y", "x", "2026-10-11T20:00:00Z"),
        ("z", "none", "2026-10-12T11:00:00Z"),
        ("w", "none", "2026-10-12T11:00:01Z"),
    )
    assert _metric1(_stats(root, "0.5.0-rc98")) == "1 fix-induced bugs\t0/1 (0%)\t<= 20%"
    assert _metric1(_stats(root, "0.5.0-rc99")) == "1 fix-induced bugs\t1/2 (50%)\t<= 20%"


def test_stats_window_of_the_first_candidate_has_no_lower_bound(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    _log(
        root,
        [
            _entry("2026-10-12T09:00:00Z", "note", "Release 0.5.0 born"),
            _milestone("2026-10-12T11:00:00Z", "rc-1", "implemented", "2" * 40),
        ],
    )
    _closed(root, ("a", "x", "2026-10-05T10:00:00Z"), ("b", "none", "2026-10-12T10:00:00Z"))
    assert _metric1(_stats(root, "0.5.0-rc1")) == "1 fix-induced bugs\t1/2 (50%)\t<= 20%"


def test_stats_reads_the_closed_counts_by_running_the_bug_script_without_its_internals(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    scripts = root / ".agents/skills/dd-bug-resolution/scripts"
    (scripts / "_bugs_store.py").unlink()
    _log(
        root,
        [
            _born("2026-10-10T08:00:00Z"),
            _milestone("2026-10-11T08:00:00Z", "rc-98", "implemented", "1" * 40),
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", "2" * 40),
        ],
    )
    _stub(
        root,
        "dd-bug-resolution",
        "bugs.py",
        'a = sys.argv\nassert a[1] == "stats"\n'
        'assert a[a.index("--closed-after") + 1] == "2026-10-11T08:00:00Z"\n'
        'assert a[a.index("--closed-until") + 1] == "2026-10-12T11:00:00Z"\n'
        'print("closed\\t3\\nfix-induced\\t1\\nrebuild-due\\t2")',
    )
    done = _stats(root)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert "1 fix-induced bugs\t1/3 (33%)\t<= 20%" in lines
    assert "9 rebuild-due patches\t2\t0" in lines


def _merge_at(repo: Path, into: str, other: str, at: str) -> None:
    git(repo, "checkout", "-q", into)
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={
            "HOME": str(repo),
            "PATH": os.environ["PATH"],
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_COMMITTER_DATE": at,
        },  # fmt: skip
    )
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    landed = os_run(["git", *ident, "merge", "-q", "--no-ff", "-m", f"Merge {other}", other], cwd=repo, env=env)  # fmt: skip
    assert landed.returncode == 0, landed.stderr


def _dev_side_merge(repo: Path, at: str) -> str:
    """Cut `dev` from the current HEAD, merge a side branch into it at *at*, return to the first branch."""
    work = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    git(repo, "checkout", "-q", "-b", "dev")
    git(repo, "checkout", "-q", "-b", "side")
    git(repo, "commit", "-q", "--allow-empty", "-m", "docs(memory): side work")
    git(repo, "checkout", "-q", "dev")
    git(repo, "commit", "-q", "--allow-empty", "-m", "docs(memory): integration side")
    _merge_at(repo, "dev", "side", at)
    git(repo, "checkout", "-q", work)
    return work


def test_stats_counts_the_integration_line_merge_not_a_back_merge_into_the_work_branch(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    repo = root / "repos/r"
    work = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    _dev_side_merge(repo, "2026-10-12T08:00:00Z")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T0): the closure")
    closure = git(repo, "rev-parse", "HEAD").strip()
    _log(
        root,
        [
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", closure),
        ],
    )
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T1): before the back-merge")
    _merge_at(repo, work, "dev", "2026-10-12T12:00:00Z")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T2): after the back-merge")
    _merge_at(repo, "dev", work, "2026-10-12T14:30:00Z")
    done = _stats(root)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert "4 closure duration\t3.5 h\t<= 4 h" in lines
    assert "6 non-block commits after closure\t2\t0" in lines


def test_stats_names_the_context_that_owns_the_repo_among_several(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    decoy = '{"name": "x", "main_repo": "z", "associated_repos": [], "gitflow": {"integration": "main"}}, '  # fmt: skip
    patch_cli(root, '[{"name": "c"', f"[{decoy}" + '{"name": "c"')
    repo = root / "repos/r"
    work = _dev_side_merge(repo, "2026-10-12T08:00:00Z")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T0): the closure")
    closure = git(repo, "rev-parse", "HEAD").strip()
    _log(root, [_born("2026-10-12T09:00:00Z"), _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", closure)])  # fmt: skip
    _merge_at(repo, "dev", work, "2026-10-12T14:30:00Z")
    done = _stats(root)
    assert done.returncode == 0, done.stderr
    assert "4 closure duration\t3.5 h\t<= 4 h" in done.stdout.splitlines()


def test_stats_reads_closure_duration_as_n_a_when_no_integration_merge_holds_the_closure(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    repo = root / "repos/r"
    _dev_side_merge(repo, "2026-10-12T08:00:00Z")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T0): the closure")
    closure = git(repo, "rev-parse", "HEAD").strip()
    _log(
        root,
        [
            _born("2026-10-12T09:00:00Z"),
            _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", closure),
        ],
    )
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T1): after the closure")
    git(repo, "commit", "-q", "--allow-empty", "-m", "feat(J1.T2): after the closure too")
    done = _stats(root)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert "4 closure duration\tn/a\t<= 4 h" in lines
    assert "6 non-block commits after closure\t2\t0" in lines


def test_stats_of_a_malformed_candidate_name_reads_n_a_for_every_metric(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    done = _stats(root, "0.5.0-rcX")
    assert (done.returncode, done.stdout) == (
        0,
        "metric\tvalue\ttarget\n"
        "1 fix-induced bugs\tn/a\t<= 20%\n"
        "2 first-pass approval\tn/a\t>= 70%\n"
        "4 closure duration\tn/a\t<= 4 h\n"
        "6 non-block commits after closure\tn/a\t0\n"
        "7 memory drift\tn/a\t0\n"
        "9 rebuild-due patches\tn/a\t0\n"
        "oldest record\tn/a\n",
    ), done.stderr
    assert "Traceback" not in done.stderr


def test_stats_with_the_root_found_and_the_cli_missing_refuses_with_the_install_fix(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    _log(root, [_born("2026-10-12T09:00:00Z"), _milestone("2026-10-12T11:00:00Z", "rc-99", "implemented", "2" * 40)])  # fmt: skip
    shutil.rmtree(root / ".dadaia/.venv")
    refused = _stats(root)
    assert refused.returncode == 1
    assert refused.stderr.startswith("[error] no workspace CLI\nfix: uvx dadaia-workspace init ")
    assert refused.stderr.count("fix:") == 1 and refused.stdout == ""


def test_stats_of_a_candidate_without_a_release_folder_reads_every_metric_as_n_a(
    tmp_path: Path,
) -> None:
    root = _stats_workspace(tmp_path)
    done = _stats(root, "9.9.9-rc1")
    assert (done.returncode, done.stdout) == (
        0,
        "metric\tvalue\ttarget\n"
        "1 fix-induced bugs\tn/a\t<= 20%\n"
        "2 first-pass approval\tn/a\t>= 70%\n"
        "4 closure duration\tn/a\t<= 4 h\n"
        "6 non-block commits after closure\tn/a\t0\n"
        "7 memory drift\tn/a\t0\n"
        "9 rebuild-due patches\tn/a\t0\n"
        "oldest record\tn/a\n",
    ), done.stderr


_CHECK_FIX = (
    "fix: Agent action: {state} fails at the keys this finding names (specs/releases/AGENTS.md: "
    "release.py writes every _RELEASE.json field and ledger line) \u2014 revert the commit that "
    "introduced it (`{finder}` lists them), or delete the "
    "line if you wrote it and it is still uncommitted, then redo the change through `release.py`"
)


_REL = "releases/0.5.0/_RELEASE.json:1"


def _format_fix(fix: str, state: Path) -> str:
    """*fix* with its `{state}` and the repo-spelled `{finder}` command filled in."""
    finder = load_owner("dd-bug-resolution", "_platform").git_inline(
        state.parent, "log", "-p", "--", "_RELEASE.json"
    )
    return fix.format(state=state, finder=finder)


@pytest.mark.parametrize(
    ("body", "finding", "fix"),
    [
        (
            b"{bad",
            "document is not valid JSON: Expecting property name enclosed in double quotes",
            "fix: Agent action: {state} fails at its JSON syntax (line 1) (specs/releases/AGENTS.md: "
            "release.py writes every _RELEASE.json field and ledger line) \u2014 revert the commit "
            "that introduced it (`{finder}` lists them), or "
            "delete the line if you wrote it and it is still uncommitted, then redo the change "
            "through `release.py`",
        ),
        (b"[]", "state must be of type object", _CHECK_FIX),
        (
            b"{\xff}",
            "the file is not valid UTF-8",
            "fix: Agent action: re-encode line 1 of {state} as UTF-8 in place; every other line stays",
        ),
    ],
)
def test_stats_of_an_unreadable_release_state_is_refused_with_one_fix_line(
    tmp_path: Path, body: bytes, finding: str, fix: str
) -> None:
    root = _stats_workspace(tmp_path)
    state = root / "repos/r/specs/releases/0.5.0/_RELEASE.json"
    state.write_bytes(body)
    done = _stats(root)
    lines = done.stderr.splitlines()
    assert (done.returncode, done.stdout, len(lines)) == (1, "", 2), done.stderr
    assert lines[0] == f"[error] {_REL} {finding}", done.stderr
    assert lines[1] == _format_fix(fix, state), done.stderr


@pytest.mark.parametrize(
    ("entry", "finding"),
    [
        (
            {"agent": "a", "kind": "note", "text": "t"},
            "state.log[0] is missing required field 'ts'",
        ),
        (
            _entry("2026-10-12T10:00:00Z", "note", "x", candidate="foo"),
            "state.log[0].candidate value 'foo' does not match ^rc-[1-9][0-9]*$",
        ),
        ("x", "state.log[0] must be of type object"),
    ],
    ids=["no-ts", "bad-candidate", "not-an-object"],
)
def test_stats_of_a_log_entry_that_breaks_the_schema_is_refused_with_checks_finding(
    tmp_path: Path, entry: object, finding: str
) -> None:
    root = _stats_workspace(tmp_path)
    _log(root, [entry])  # type: ignore[list-item]
    state = root / "repos/r/specs/releases/0.5.0/_RELEASE.json"
    done = _stats(root, "0.5.0-rc18")
    lines = done.stderr.splitlines()
    assert (done.returncode, done.stdout, len(lines)) == (1, "", 2), done.stdout + done.stderr
    assert lines[0] == f"[error] {_REL} {finding}", done.stderr
    assert lines[1] == _format_fix(_CHECK_FIX, state), done.stderr


def test_stats_refuses_a_release_check_that_exits_non_zero_with_no_finding(tmp_path: Path) -> None:
    """The exit status decides: a crashed `release.py check` is a refusal, never a pass."""
    root = _stats_workspace(tmp_path)
    _log(
        root, [{"agent": "a", "kind": "note", "text": "t", "candidate": "rc-18"}]
    )  # no ts: _window KeyErrors
    _stub(root, "dd-release-implementation", "release.py",
          'print("Traceback (most recent call last):", file=sys.stderr)\nsys.exit(1)')  # fmt: skip
    done = _stats(root, "0.5.0-rc18")
    assert (done.returncode, done.stdout) == (1, ""), done.stderr
    specs = (root / "repos/r/specs").resolve()
    lines = done.stderr.splitlines()
    assert lines[0] == "[error] release.py check exited 1", done.stderr
    release = (root / ".agents/skills/dd-release-implementation/scripts/release.py").resolve()
    check = command(sys.executable, str(release), "check", "--specs", str(specs))
    assert lines[1:] == [f"fix: {check}"], done.stderr


def test_stats_of_a_milestone_without_sha_reads_n_a(tmp_path: Path) -> None:
    root = _stats_workspace(tmp_path)
    no_sha = {k: v for k, v in _milestone("2026-10-12T09:30:00Z", "rc-1", "defined", "x").items() if k != "sha"}  # fmt: skip
    _log(root, [_born("2026-10-12T09:00:00Z"), no_sha])
    done = _stats(root, "0.5.0-rc1")
    assert (done.returncode, done.stderr) == (0, ""), done.stdout
    assert "4 closure duration\tn/a\t<= 4 h\n" in done.stdout


_STUB_VALIDATE = '    sys.exit(0 if "schema_version" in json.load(open(args[2])) else 1)'
_REAL_VALIDATE = """    open({log!r}, "a").write(json.dumps(args) + chr(10))
    sys.path.insert(0, {kernel!r})
    from _platform import run
    done = run([{py!r}, "-m", "dadaia_workspace", *args])
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    sys.exit(done.returncode)"""


def _real_validator(root: Path, tmp_path: Path) -> Path:
    """Route the stub's `reports validate` to the real validator; returns the argv log."""
    log = tmp_path / "validate.argv"
    schemas = root / ".dadaia/agentic/schemas"
    schemas.mkdir(parents=True)
    write_text(root / ".dadaia/states/spec_contexts.json", '{"contexts": []}')
    shutil.copy(PKG / "public/schemas/handoff-v1.schema.json", schemas)
    patch_cli(
        root,
        _STUB_VALIDATE,
        _REAL_VALIDATE.format(
            log=str(log),
            py=sys.executable,
            kernel=str(PKG / "public/skills/dd-bug-resolution/scripts"),
        ),
    )
    return log


_FINDING = {"severity": "LOW", "message": "m", "detail_md": "d", "fix_recommendation": "f"}
_FIX = "fix: Agent action: correct {} in the stdin body ({}), then rerun verdict.py"
_REFUSED = [
    pytest.param(
        {"findings": [{"severity": "LOW", "message": "m", "detail_md": "d"}]},
        "$.findings[0]",
        "'fix_recommendation' is a required property",
        id="required-property",
    ),
    pytest.param(
        {"findings": [{**_FINDING, "severity": "BAD"}]},
        "$.findings[0].severity",
        "'BAD' is not one of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']",
        id="enum-value",
    ),
    pytest.param(
        {"self_pull": {"refs": ["specs/absent.md"]}},
        "self_pull.refs[0]",
        "ref does not exist: 'specs/absent.md' (checked reviewed_root, "
        "repos/<context>/<ref> and <workspace>/<ref>)",
        id="missing-ref",
    ),
]


@pytest.mark.parametrize(("over", "where", "message"), _REFUSED)
def test_a_body_the_schema_rejects_is_refused_by_field_and_leaves_no_handoff(
    tmp_path: Path, over: dict[str, object], where: str, message: str
) -> None:
    root, tree, head = _workspace(tmp_path)
    _real_validator(root, tmp_path)
    refused = _verdict(root, tree, sha=head, stdin=json.dumps({**BODY, **over}))
    assert refused.returncode == 1
    assert refused.stderr == f"[error] {where}: {message}\n{_FIX.format(where, message)}\n"
    assert _written(root) == []


def test_an_unreadable_schema_passes_the_cli_fix_line_through(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    log = _real_validator(root, tmp_path)
    (root / ".dadaia/agentic/schemas/handoff-v1.schema.json").unlink()
    refused = _verdict(root, tree, sha=head, stdin=json.dumps(BODY))
    assert refused.returncode == 1
    assert fixes(refused) == ["fix: " + fix_line(root, "public", "install")]
    assert _written(root) == [] and log.exists()


def test_a_verdict_citing_a_file_only_the_reviewed_tree_holds_is_written_and_validated_there(
    tmp_path: Path,
) -> None:
    root, tree, _ = _workspace(tmp_path)
    head = commit(tree, "specs/only-here.md", "x\n")
    log = _real_validator(root, tmp_path)
    body = {**BODY, "self_pull": {"refs": ["specs/only-here.md"]}}
    done = _verdict(root, tree, sha=head, stdin=json.dumps(body))
    assert done.returncode == 0, done.stderr
    (path,) = _written(root)
    assert done.stdout.strip() == str(path)
    assert read_text(log) == (
        json.dumps(["reports", "validate", str(path), "--reviewed-root", str(tree), "--json"])
        + "\n"
    )


def test_a_relative_tree_path_is_validated_as_the_resolved_tree(tmp_path: Path) -> None:
    root, tree, _ = _workspace(tmp_path)
    head = commit(tree, "specs/only-here.md", "x\n")
    log = _real_validator(root, tmp_path)
    body = {**BODY, "self_pull": {"refs": ["specs/only-here.md"]}}
    done = _verdict(root, ".", sha=head, stdin=json.dumps(body), cwd=tree)
    assert done.returncode == 0, done.stderr
    (path,) = _written(root)
    assert read_text(log) == (
        json.dumps(["reports", "validate", str(path), "--reviewed-root", str(tree), "--json"])
        + "\n"
    )


def test_a_cli_crash_without_json_or_fix_line_is_refused_with_one_agent_action(
    tmp_path: Path,
) -> None:
    root, tree, head = _workspace(tmp_path)
    patch_cli(root, _STUB_VALIDATE, '    sys.stderr.write("boom")\n    sys.exit(1)')
    refused = _verdict(root, tree, sha=head)
    assert refused.returncode == 1
    assert refused.stderr == (
        "[error] boom\nfix: Agent action: resolve the workspace CLI error above,"
        " then rerun verdict.py\n"
    )
    assert _written(root) == []


def test_stats_outside_a_workspace_is_refused_with_one_fix_line(tmp_path: Path) -> None:
    root, _tree, _head = _workspace(tmp_path)
    (away := tmp_path / "away").mkdir()
    script = root / ".agents/skills" / SKILL / "scripts/verdict.py"
    refused = os_run([sys.executable, str(script), "stats", "0.5.0-rc1"], cwd=away)
    assert refused.returncode == 1
    assert refused.stderr == (
        "[error] no workspace above the current directory\nfix: Agent action: run"
        " verdict.py stats from inside the workspace, then rerun it\n"
    )


def test_a_workspace_without_its_cli_is_refused_with_the_install_fix_line(tmp_path: Path) -> None:
    root, tree, head = _workspace(tmp_path)
    shutil.rmtree(root / ".dadaia/.venv")
    refused = _verdict(root, tree, sha=head)
    assert refused.returncode == 1
    assert refused.stderr.startswith("[error] no workspace CLI\nfix: uvx dadaia-workspace init ")
    assert refused.stderr.count("fix:") == 1 and _written(root) == []
