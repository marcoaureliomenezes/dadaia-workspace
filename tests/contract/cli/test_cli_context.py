"""Intent: CONTRACT — dadaia context CLI (P-09 one Invocation; DADAIA §3.3 context resolution)

Public CLI contracts for `dadaia context`.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fakes import seed_dead_context
from tests.fixtures.stores import workspace_cli

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES)
    monkeypatch.chdir(workspace_cli(tmp_path))
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
    (states / "spec_contexts.json").write_text(
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
        )
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
    # FR18 (T-044-29): `list --json` also carries `stored_branch` (the stored
    # snapshot, distinct from the live-resolved `current_branch`, A18.1) and
    # `associated_repos` (full list, A18.4/A18.5).
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
            "stored_branch": None,
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
    """0.4.7 FR4: `bind <ctx>` exits 0, persists the record, prints a human
    confirmation — never a shell export line. No --mode, no --release, no --force,
    no --reason; the record carries neither `mode` nor `release`."""
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess_t1")
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT" not in result.output
    assert "myctx" in result.output
    assert "sess_" in result.output
    record = _record(workspace)
    assert record["context"] == "myctx"
    assert "mode" not in record
    assert "release" not in record

    for flag in ("--mode", "--release", "--force", "--reason"):
        refused = _runner.invoke(app, ["context", "bind", "myctx", flag, "x"])
        assert refused.exit_code != 0, f"{flag} must not exist any more"


@pytest.mark.parametrize(
    ("env", "session_id"),
    [
        # bug bind-session-id-divergence: one stable harness-native id, never a minted sess_*
        pytest.param({"CLAUDE_CODE_SESSION_ID": "claude-stable-abc123"}, "claude-stable-abc123", id="claude-native-id"),
        pytest.param({"CODEX_THREAD_ID": "harness-session"}, "harness-session", id="codex-native-id"),
        # the eval-flow contract: an explicit DADAIA_SESSION_ID is reused, never re-minted
        pytest.param({"DADAIA_SESSION_ID": "sess_stable01"}, "sess_stable01", id="dadaia-session-id"),
        # bug validation-027-f-07: env id AND harness id -> the env id owns the ONE record
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
    from dadaia_workspace.core import session_store

    for name, value in env.items():
        monkeypatch.setenv(name, value)
    _register_alive_ctx(workspace)
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

    env_real = {**os.environ, "DADAIA_RUNTIME": "kimi-code"}
    result2 = _runner.invoke(app, ["context", "bind", "myctx"], env=env_real)
    assert result2.exit_code == 0, result2.output
    record2 = _record(workspace)
    assert record2["runtime"] == "kimi-code"


def test_context_show_json_session_null_then_populated_when_bound(workspace: Path) -> None:
    """AC-T10d-6: show --json has session=null when no session binding, and a
    populated session sub-object when DADAIA_SESSION_ID is set and the session file
    is fresh."""
    _register_alive_ctx(workspace)

    env_no_session = {k: v for k, v in os.environ.items() if k != "DADAIA_SESSION_ID"}
    result = _runner.invoke(app, ["context", "show", "myctx", "--json"], env=env_no_session)
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert "session" in data
    assert data["session"] is None

    session_id = "sess_t1"
    env = {**os.environ, "DADAIA_SESSION_ID": session_id}
    bind_result = _runner.invoke(app, ["context", "bind", "myctx"], env=env)
    assert bind_result.exit_code == 0, bind_result.output
    show_result = _runner.invoke(app, ["context", "show", "--json"], env=env)
    assert show_result.exit_code == 0, show_result.output
    data = json.loads(show_result.stdout)
    # sa-bind-has-two-stores#S8: name and session come from the one Bind.
    assert data["name"] == "myctx" == data["session"]["context"]
    assert data["session"]["session_id"] == session_id


def test_push_uses_set_upstream_when_no_tracking(tmp_path: Path) -> None:
    """Smoke test: GitSubprocessClient.push() uses -u on a repo with no upstream."""
    # Create a bare remote
    bare = tmp_path / "bare.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)

    # Create a local repo with at least one commit
    local = tmp_path / "local"
    local.mkdir()
    subprocess.run(["git", "init", str(local)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    (local / "README.md").write_text("hello")
    subprocess.run(["git", "add", "README.md"], cwd=local, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)],
        cwd=local,
        capture_output=True,
        check=True,
    )

    # Pre-condition: no upstream tracking branch
    no_upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert no_upstream.returncode != 0, "pre-condition: upstream must NOT be set"

    # Exercise the fix
    client = GitSubprocessClient()
    client.push(local)  # must not raise

    # Post-condition: upstream tracking branch is now set
    has_upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert has_upstream.returncode == 0, (
        "upstream tracking must be set after git push -u; "
        f"got stderr: {has_upstream.stderr.strip()!r}"
    )


def test_context_baseline_is_consent_by_invocation(workspace: Path, tmp_path: Path) -> None:
    """AC4.2/AC4.7: no --yes/--push; one invocation publishes, a re-run is a no-op."""
    bare = tmp_path / "baseline.git"
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)
    repo = workspace / "repos" / "baseline"
    subprocess.run(["git", "clone", str(bare), str(repo)], capture_output=True, check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "T")):
        subprocess.run(["git", "config", key, value], cwd=repo, check=True)
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(
        "---\nspecs_pattern_version: 6\n---\n", encoding="utf-8"
    )
    _register_alive_ctx(workspace, "baseline")

    assert _runner.invoke(app, ["context", "baseline", "baseline", "--yes"]).exit_code != 0
    result = _runner.invoke(app, ["context", "baseline", "baseline"])
    assert result.exit_code == 0, result.output
    assert "published on feature/0.1.0" in result.output
    again = _runner.invoke(app, ["context", "baseline", "baseline"])
    assert again.exit_code == 0 and "already published" in again.output


def test_context_dead_surfaces_the_refused_push_with_its_fix_line(
    workspace: Path, tmp_path: Path
) -> None:
    """T-048-11: a push the pre-push hook refuses reaches the operator verbatim — its
    one ``fix:`` line included — instead of a bare "resolve the issue and retry"."""
    bare = tmp_path / "refused.git"
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)
    repo = workspace / "repos" / "refused"
    subprocess.run(["git", "clone", str(bare), str(repo)], capture_output=True, check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "T")):
        subprocess.run(["git", "config", key, value], cwd=repo, check=True)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-qb", "feature/0.1.0"], cwd=repo, check=True)
    hook = repo / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\necho 'fix: git checkout -b feature/0.1.0' >&2\nexit 1\n")
    hook.chmod(0o755)
    _register_alive_ctx(workspace, "refused")

    result = _runner.invoke(app, ["context", "dead", "refused"])

    assert result.exit_code != 0
    assert "fix: git checkout -b feature/0.1.0" in " ".join(result.output.split())
    assert result.output.count("fix: ") == 1  # the gate's fix is the one fix
    assert repo.is_dir()


def test_show_unbound_is_calm_in_both_modes(workspace: Path) -> None:
    """Bug context-show-json-traceback-unbound: with no bind, `show --json` answers
    {"context": null} and human `show` prints a calm line — both exit 0, no traceback."""
    as_json = _runner.invoke(app, ["context", "show", "--json"])
    human = _runner.invoke(app, ["context", "show"])
    assert as_json.exit_code == human.exit_code == 0, as_json.output + human.output
    assert json.loads(as_json.output) == {"context": None}
    assert "No active context" in human.output
    assert "Traceback" not in as_json.output + human.output


def test_bind_with_no_live_release_exits_zero_and_the_next_write_is_allowed(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug ``context-bind-implementation-requires-release-id-stall-when-none-live``.

    The repro: a workspace with no ``specs/releases/<id>/`` on disk. Bind used to refuse
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

    # sa-bind-has-two-stores#S4: the record the bind wrote is the bind — no env by hand.
    target = workspace / "worktrees/myctx/0.0.1a-release/specs/releases/0.0.1/SPEC.md"
    block = pre_gate.evaluate_payload(
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    )
    assert block is None, block


def test_context_create_help_names_main_repo_and_associated_repos(workspace: Path) -> None:
    """Intent: CONTRACT — AC5.1, AC3.8. The option surface names the paradigm's parts;
    the retired `--repo`/`--associated`/`--url`/`--associated-repos` spellings are gone."""
    result = _runner.invoke(
        app, ["context", "create", "--help"], env={"TERMINAL_WIDTH": "200", "NO_COLOR": "1"}
    )
    assert result.exit_code == 0, result.output
    # Rich styles the option token inline on a colour-forcing runner (CI): assert on the
    # plain text, never on the escaped stream.
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--main-repo" in plain
    assert "--associated-repo " in plain
    assert "--associated-repos" not in plain
    assert "--url" not in plain
    assert "--repo " not in plain
    assert "--associated " not in plain


def test_context_show_and_list_json_emit_main_repo_key(workspace: Path) -> None:
    """Intent: CONTRACT — AC5.1. `show --json` / `list --json` carry `main_repo`;
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
