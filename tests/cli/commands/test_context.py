import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import context as context_cmd
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fakes import NoWorktreeContainer, seed_dead_context
from tests.helpers.oslib import make_executable, run, write_text
from tests.helpers.oslib import run as os_run

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES)
    monkeypatch.chdir(tmp_path)
    # Hermetic identity: each test sets exactly the id sources it needs.
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
        "DADAIA_CONTEXT",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _register_alive_ctx(workspace: Path, name: str = "myctx") -> None:
    """An ALIVE v2 context written straight into the state file — no real clone."""
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    write_text(
        states / "spec_contexts.json",
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"https://example.com/{name}.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            }
        ),
    )


def _record(workspace: Path) -> dict:
    from dadaia_workspace.core import session_store

    record = session_store.read_session(workspace, "sess_t1")
    assert record is not None, "session record sess_t1 not persisted"
    return dict(record)


def test_context_create_show_list_happy_lifecycle(workspace: Path) -> None:
    seed_dead_context(workspace, "alpha", "alpha", "https://x.test/alpha.git")

    show = _runner.invoke(app, ["context", "show", "alpha", "--json"])
    assert show.exit_code == 0, show.output
    data = json.loads(show.stdout)
    assert data["name"] == "alpha"
    assert data["state"] == "dead"
    # v2: no is_primary field
    assert "is_primary" not in data
    assert "alive_since" in data
    assert "dead_since" in data
    # v2: session sub-object present (null when no binding)
    assert "session" in data
    assert data["session"] is None

    list_out = _runner.invoke(app, ["context", "list"])
    assert list_out.exit_code == 0, list_out.output
    assert "alpha" in list_out.output
    assert "dead" in list_out.output

    list_json = _runner.invoke(app, ["context", "list", "--json"])
    assert list_json.exit_code == 0, list_json.output
    # `list --json` also carries `associated_repos` (full list).
    assert json.loads(list_json.stdout) == [
        {
            "alive_since": None,
            "associated_repos": [],
            "created_at": json.loads(show.stdout)["created_at"],
            "current_branch": None,
            "dead_since": None,
            "name": "alpha",
            "main_repo": "alpha",
            "repo_url": "https://x.test/alpha.git",
            "state": "dead",
            "gitflow": None,
        }
    ]


def test_context_list_json_empty_is_stable_array(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == []


@pytest.mark.parametrize(
    "invoke_args",
    [
        pytest.param(["context", "show", "ghost", "--json"], id="show-unknown-json"),
        pytest.param(["context", "delete", "ghost"], id="delete-nonexistent"),
        pytest.param(["context", "alive", "ghost"], id="alive-requires-existing"),
        pytest.param(["context", "dead", "ghost"], id="dead-requires-existing"),
    ],
)
def test_context_error_matrix(workspace: Path, invoke_args: list[str]) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, invoke_args)
    assert result.exit_code != 0


def test_context_bind_is_one_verb_with_one_argument(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`bind <ctx>` exits 0, persists the record, prints a human
    confirmation — never a shell export line. No --mode, no --release, no --force,
    no --reason, no --print-env; the record carries neither `mode` nor `release`."""
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess_t1")
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output
    assert "myctx" in result.output
    assert "sess_" in result.output
    record = _record(workspace)
    assert record["context"] == "myctx"
    assert "mode" not in record
    assert "release" not in record

    for flag in ("--mode", "--release", "--force", "--reason", "--print-env"):
        refused = _runner.invoke(app, ["context", "bind", "myctx", flag])
        assert refused.exit_code != 0, f"{flag} must not exist any more"


@pytest.mark.parametrize(
    ("env", "session_id"),
    [
        # One stable harness-native id, never a minted sess_*
        pytest.param({"CLAUDE_CODE_SESSION_ID": "claude-stable-abc123"}, "claude-stable-abc123", id="claude-native-id"),
        pytest.param({"CODEX_THREAD_ID": "harness-session"}, "harness-session", id="codex-native-id"),
        # the eval-flow contract: an explicit DADAIA_SESSION_ID is reused, never re-minted
        pytest.param({"DADAIA_SESSION_ID": "sess_stable01"}, "sess_stable01", id="dadaia-session-id"),
        # env id AND harness id -> the env id owns the ONE record
        pytest.param({"DADAIA_SESSION_ID": "sess_envfixed", "CLAUDE_CODE_SESSION_ID": "claude-native-xyz"}, "sess_envfixed", id="env-id-wins-one-record"),
    ],
)  # fmt: skip
def test_bind_resolves_one_session_identity(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    session_id: str,
) -> None:
    """Two binds both exit 0 (peer presence is advisory) and persist the record under the one
    resolved identity — no global pointer, no second record, no minted stray."""
    from dadaia_workspace.core import clock, session_store

    for name, value in env.items():
        monkeypatch.setenv(name, value)
    _register_alive_ctx(workspace)
    session_store.touch_last_seen_at(
        workspace, session_id, now=clock.now_iso()
    )  # the hook heartbeat
    outputs = [_runner.invoke(app, ["context", "bind", "myctx"]) for _ in range(2)]
    assert [r.exit_code for r in outputs] == [0, 0], outputs[0].output
    sessions = workspace / ".dadaia" / "sessions"
    assert not (sessions / "runtime").exists()
    assert all(
        session_id in r.output and "sess_" not in r.output.replace(session_id, "") for r in outputs
    )
    assert sorted(p.name for p in sessions.glob("*.json")) == [f"{session_id}.json"]
    record = session_store.read_session(workspace, session_id)
    assert (
        record is not None and record["session_id"] == session_id and record["context"] == "myctx"
    )


def test_bind_records_dadaia_runtime_env(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess_t1")
    _register_alive_ctx(workspace)

    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output
    record = _record(workspace)
    assert record["runtime"] == "unknown"

    env_real = {"DADAIA_RUNTIME": "kimi-code"}
    result2 = _runner.invoke(app, ["context", "bind", "myctx"], env=env_real)
    assert result2.exit_code == 0, result2.output
    record2 = _record(workspace)
    assert record2["runtime"] == "kimi-code"


def test_context_show_json_session_null_then_populated_when_bound(workspace: Path) -> None:
    """show --json has session=null when no session binding, and a
    populated session sub-object when DADAIA_SESSION_ID is set and the session file
    is fresh."""
    _register_alive_ctx(workspace)

    result = _runner.invoke(app, ["context", "show", "myctx", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert "session" in data
    assert data["session"] is None

    session_id = "sess_t1"
    env = {"DADAIA_SESSION_ID": session_id}
    bind_result = _runner.invoke(app, ["context", "bind", "myctx"], env=env)
    assert bind_result.exit_code == 0, bind_result.output
    show_result = _runner.invoke(app, ["context", "show", "--json"], env=env)
    assert show_result.exit_code == 0, show_result.output
    data = json.loads(show_result.stdout)
    # Name and session come from the one bind.
    assert data["name"] == "myctx" == data["session"]["context"]
    assert data["session"]["session_id"] == session_id


def test_push_uses_set_upstream_when_no_tracking(tmp_path: Path) -> None:
    """Smoke test: GitSubprocessClient.push() uses -u on a repo with no upstream."""
    # Create a bare remote
    bare = tmp_path / "bare.git"
    bare.mkdir()
    os_run(["git", "init", "--bare", str(bare)], check=True)

    # Create a local repo with at least one commit
    local = tmp_path / "local"
    local.mkdir()
    os_run(["git", "init", str(local)], check=True)
    os_run(["git", "config", "user.email", "test@example.com"], cwd=local, check=True)
    os_run(["git", "config", "user.name", "Test"], cwd=local, check=True)
    write_text(local / "README.md", "hello")
    os_run(["git", "add", "README.md"], cwd=local, check=True)
    os_run(["git", "commit", "-m", "init"], cwd=local, check=True)
    os_run(["git", "remote", "add", "origin", str(bare)], cwd=local, check=True)

    # Pre-condition: no upstream tracking branch
    no_upstream = run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=local)
    assert no_upstream.returncode != 0, "pre-condition: upstream must NOT be set"

    # Exercise the fix
    client = GitSubprocessClient()
    client.push(local)  # must not raise

    # Post-condition: upstream tracking branch is now set
    has_upstream = run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=local)
    assert has_upstream.returncode == 0, (
        "upstream tracking must be set after git push -u; "
        f"got stderr: {has_upstream.stderr.strip()!r}"
    )


def _remote_heads(bare: Path) -> dict[str, str]:
    out = run(["git", "-C", str(bare), "for-each-ref", "--format=%(refname) %(objectname)"], check=True).stdout  # fmt: skip
    return dict(line.split() for line in out.splitlines())


def test_context_baseline_is_consent_by_invocation(workspace: Path, tmp_path: Path) -> None:
    """No --yes/--push; one invocation publishes, a re-run is a no-op."""
    bare = tmp_path / "baseline.git"
    os_run(["git", "init", "--bare", str(bare)], check=True)
    repo = workspace / "repos" / "baseline"
    os_run(["git", "clone", str(bare), str(repo)], check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "T")):
        os_run(["git", "config", key, value], cwd=repo, check=True)
    (repo / "specs").mkdir()
    write_text(repo / "specs" / "constitution.md", "---\nspecs_pattern_version: 6\n---\n")
    _register_alive_ctx(workspace, "baseline")

    assert _runner.invoke(app, ["context", "baseline", "baseline", "--yes"]).exit_code != 0
    result = _runner.invoke(app, ["context", "baseline", "baseline"])
    assert result.exit_code == 0, result.output
    published = _remote_heads(bare)
    assert "refs/heads/feature/0.1.0" in published, published
    again = _runner.invoke(app, ["context", "baseline", "baseline"])
    assert again.exit_code == 0 and _remote_heads(bare) == published, again.output


def test_context_dead_surfaces_the_refused_push_with_its_fix_line(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A push the pre-push hook refuses reaches the operator verbatim — its
    one ``fix:`` line included — instead of a bare "resolve the issue and retry"."""
    bare = tmp_path / "refused.git"
    os_run(["git", "init", "--bare", str(bare)], check=True)
    repo = workspace / "repos" / "refused"
    os_run(["git", "clone", str(bare), str(repo)], check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "T")):
        os_run(["git", "config", key, value], cwd=repo, check=True)
    write_text(repo / "README.md", "x\n")
    os_run(["git", "add", "README.md"], cwd=repo, check=True)
    os_run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    os_run(["git", "checkout", "-qb", "feature/0.1.0"], cwd=repo, check=True)
    hook = repo / ".git" / "hooks" / "pre-push"
    write_text(hook, "#!/bin/sh\necho 'fix: git checkout -b feature/0.1.0' >&2\nexit 1\n")
    make_executable(hook)
    _register_alive_ctx(workspace, "refused")
    monkeypatch.setattr(context_cmd, "container", NoWorktreeContainer())

    result = _runner.invoke(app, ["context", "dead", "refused"])

    assert result.exit_code != 0
    assert "fix: git checkout -b feature/0.1.0" in " ".join(result.output.split())
    assert result.output.count("fix: ") == 1  # the gate's fix is the one fix
    assert repo.is_dir()


_RELAUNCH = "fix: Operator action: relaunch the session at the workspace root"
_NO_ROLE = "This session was started outside the workspace root, so it stands in for no role."
_UNREAD = "This session's record does not read."


@pytest.mark.parametrize(
    ("session", "recorded", "exit_code"),
    [
        pytest.param(None, False, 0, id="no-session"),
        pytest.param("sess_live", True, 0, id="live-record"),
        pytest.param("sess_ghost", False, 1, id="no-record"),
    ],
)
def test_session_check_passes_a_governed_session_and_refuses_the_rest(
    workspace: Path, session: str | None, recorded: bool, exit_code: int
) -> None:
    from dadaia_workspace.core import clock, session_store

    if recorded and session:
        session_store.write_session(
            workspace, session, {"session_id": session, "last_seen_at": clock.now_iso()}
        )
    env = {"CLAUDE_CODE_SESSION_ID": session} if session else {}

    result = _runner.invoke(app, ["context", "session-check"], env=env)

    assert result.exit_code == exit_code, result.output
    if exit_code:
        assert " ".join(result.output.split()).count("fix: ") == 1
        assert _RELAUNCH in " ".join(result.output.split())
        assert _NO_ROLE in " ".join(result.output.split())


@pytest.mark.parametrize(
    ("env", "session_id", "heartbeat", "exit_code"),
    [
        pytest.param({"CLAUDE_CODE_SESSION_ID": "sess_nohook"}, "sess_nohook", False, 1, id="claude-no-record-refused"),
        pytest.param({"CLAUDE_CODE_SESSION_ID": "sess_hooked"}, "sess_hooked", True, 0, id="claude-after-heartbeat-binds"),
        pytest.param({"DADAIA_SESSION_ID": "sess_operator"}, "sess_operator", False, 0, id="operator-terminal-binds"),
        pytest.param({"CODEX_THREAD_ID": "codex-thread"}, "codex-thread", True, 0, id="codex-binds"),
        pytest.param({"CODEX_SESSION_ID": "codex-nohook"}, "codex-nohook", False, 1, id="codex-no-record-refused"),
        pytest.param({"CODEX_SESSION_ID": "codex-hooked"}, "codex-hooked", True, 0, id="codex-after-heartbeat-binds"),
    ],
)  # fmt: skip
def test_bind_needs_a_hook_heartbeat_for_a_judged_harness_session(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    session_id: str,
    heartbeat: bool,
    exit_code: int,
) -> None:
    """A Claude Code session id binds only after its hook heartbeat created the record; a
    refused bind writes nothing and prints the one relaunch fix line."""
    from dadaia_workspace.core import clock, session_store

    for name, value in env.items():
        monkeypatch.setenv(name, value)
    _register_alive_ctx(workspace)
    if heartbeat:
        session_store.touch_last_seen_at(workspace, session_id, now=clock.now_iso())

    result = _runner.invoke(app, ["context", "bind", "myctx"])

    assert result.exit_code == exit_code, result.output
    record = session_store.read_session(workspace, session_id)
    if exit_code:
        assert " ".join(result.output.split()).count("fix: ") == 1
        assert _RELAUNCH in " ".join(result.output.split())
        assert _NO_ROLE in " ".join(result.output.split())
        assert record is None
        assert not (workspace / ".dadaia" / "sessions" / f"{session_id}.json").exists()
    else:
        assert record is not None and record["context"] == "myctx"


def test_a_refused_bind_does_not_make_session_check_pass(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess_nohook")
    _register_alive_ctx(workspace)

    _runner.invoke(app, ["context", "bind", "myctx"])
    result = _runner.invoke(app, ["context", "session-check"])

    assert result.exit_code == 1, result.output
    assert _RELAUNCH in " ".join(result.output.split())


@pytest.mark.parametrize("argv", [["bind", "myctx"], ["session-check"]])
def test_a_refused_session_with_an_unreadable_record_names_doctors_fix(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    """The record that does not read is what refuses the session: both verbs name doctor's
    fix, the one act that clears it, never the relaunch."""
    from dadaia_workspace.core import session_store
    from dadaia_workspace.core.cli_line import fix_line

    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess_corrupt")
    _register_alive_ctx(workspace)
    write_text(
        session_store.session_record_path(workspace, "sess_corrupt", create=True), "{not json"
    )

    result = _runner.invoke(app, ["context", *argv])

    out = " ".join(result.output.split())
    assert result.exit_code == 1, result.output
    assert out.count("fix: ") == 1
    assert f"fix: {fix_line(workspace, 'doctor', '--fix')}" in out
    assert _UNREAD in out
    assert _NO_ROLE not in out
    assert _RELAUNCH not in out


def test_show_unbound_is_calm_in_both_modes(workspace: Path) -> None:
    """With no bind, `show --json` answers
    {"context": null} and human `show` prints a calm line — both exit 0, no traceback."""
    as_json = _runner.invoke(app, ["context", "show", "--json"])
    human = _runner.invoke(app, ["context", "show"])
    assert as_json.exit_code == human.exit_code == 0, as_json.output + human.output
    assert json.loads(as_json.output) == {"context": None}
    assert "Traceback" not in as_json.output + human.output


def test_bind_with_no_live_release_exits_zero_and_the_next_write_is_allowed(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workspace with no ``specs/releases/<id>/`` on disk. Bind used to refuse
    (``--release <id> is required``) and the only way to create the release was a
    MUTATING write the refused bind would not grant — a closed loop. `bind` no longer
    knows what a release is, so it exits 0 and the next in-scope MUTATING write ALLOWs.
    """
    from dadaia_workspace.hooks import pre_gate

    _register_alive_ctx(workspace)
    assert not (workspace / "repos" / "myctx" / "specs" / "releases").exists()

    monkeypatch.setenv("DADAIA_SESSION_ID", "sess_t1")
    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output

    # The record the bind wrote is the bind — no env by hand.
    target = workspace / "worktrees/myctx/0.0.1a-release/specs/releases/0.0.1/SPEC.md"
    block = pre_gate.evaluate_payload(
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    )
    assert block is None, block


def test_context_show_and_list_json_emit_main_repo_key(workspace: Path) -> None:
    """`show --json` / `list --json` carry `main_repo`;
    the retired output key `repo_slug` is absent (the state-file schema keeps it)."""
    from dadaia_workspace.core.models.spec_context import AssociatedRepo

    seed_dead_context(
        workspace,
        "alpha",
        "alpha",
        "https://x.test/alpha.git",
        associated_repos=(
            AssociatedRepo("beta", "https://x.test/beta.git"),
            AssociatedRepo("gamma", "https://x.test/gamma.git"),
        ),
    )

    show = json.loads(_runner.invoke(app, ["context", "show", "alpha", "--json"]).stdout)
    assert show["main_repo"] == "alpha"
    assert "repo_slug" not in show
    assert [r["slug"] for r in show["associated_repos"]] == ["beta", "gamma"]

    listed = json.loads(_runner.invoke(app, ["context", "list", "--json"]).stdout)
    assert listed[0]["main_repo"] == "alpha"
    assert "repo_slug" not in listed[0]
