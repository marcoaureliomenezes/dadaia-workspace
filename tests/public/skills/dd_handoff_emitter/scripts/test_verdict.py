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
from tests.helpers.oslib import read_text, write_text
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
    commit(tree, "specs/later", "x\n")
    refused = run(root, "merge", str(tree))
    assert refused.returncode != 0 and "reports validate" in refused.stderr


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
) -> None:
    """A verdict handoff with the keys `verdict.py` writes (schema-validated), at *at* seconds."""
    produced = f"{minute}:{at}Z"
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
    schema = json.loads(read_text(PKG / "public/schemas/handoff-v1.schema.json"))
    jsonschema.validate(body, schema)
    base = root / (".dadaia/reaped/x/.dadaia/handoff/c" if hold else ".dadaia/handoff/c")
    base.mkdir(parents=True, exist_ok=True)
    name = f"{produced.replace(':', '')}-{agent}-{verdict}-{scope.replace('/', '_')}.handoff.json"
    write_text(base / name, json.dumps(body, indent=2) + "\n")


def _stats_workspace(tmp_path: Path) -> Path:
    """A workspace with the skill scripts where an install puts them."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    for skill in (SKILL, "dd-bug-resolution", "dd-release-implementation"):
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    return root


def _log(root: Path, log: list[dict[str, str]]) -> None:
    state = root / "repos/r/specs/releases/0.5.0/_RELEASE.json"
    write_text(state, json.dumps({**json.loads(read_text(state)), "log": log}))


def _stub(root: Path, skill: str, script: str, body: str) -> None:
    write_text(root / ".agents/skills" / skill / "scripts" / script, f"import sys\n{body}\n")


def _stats(root: Path) -> subprocess.CompletedProcess[str]:
    script = root / ".agents/skills" / SKILL / "scripts/verdict.py"
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"PATH": os.environ["PATH"], "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    argv = [sys.executable, str(script), "stats", "0.5.0-rc99", "--specs", "repos/r/specs"]
    return os_run(argv, cwd=root, env=env)


def _entry(ts: str, kind: str, text: str, **more: str) -> dict[str, str]:
    agent = "release.py new" if text.startswith("Candidate born") else "release.py"
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
    for message in (
        "fix(bugs): a - cause\n\nblock: item",
        "refactor(J1.T1): REBUILD x",
        "docs(memory): reconcile",
        "feat(J1.T2): y",
    ):
        git(repo, "commit", "-q", "--allow-empty", "-m", message)
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
    _stub(root, "dd-bug-resolution", "bugs.py",
          'assert sys.argv[1] == "stats"\nprint("total\\t9")\nprint("rebuild-due:a.py\\tx,y")\nprint("rebuild-due:b.py\\tz,w")')  # fmt: skip
    _stub(root, "dd-release-implementation", "release.py",
          'assert sys.argv[1:3] == ["drift", "--json"]\nprint(\'{"since": "s", "atoms": ["a", "b", "c"], "uncovered": []}\')')  # fmt: skip
    done = _stats(root)
    assert (done.returncode, done.stdout) == (
        0,
        "metric\tvalue\ttarget\n"
        "1 fix-induced bugs\t1/4 (25%)\t<= 20%\n"
        "2 first-pass approval\t2/4 (50%)\t>= 70%\n"
        "4 closure duration\t3.5 h\t<= 4 h\n"
        "6 non-block commits after closure\t2\t0\n"
        "7 memory drift\t3\t0\n"
        "9 rebuild-due patches\t2\t0\n"
        "oldest record\t2026-10-09T10:00:01Z\n",
    ), done.stderr


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
    _stub(root, "dd-release-implementation", "release.py", "sys.exit(1)")
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
