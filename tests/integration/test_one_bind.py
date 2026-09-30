"""One bind: the gate, ctx_inject, onboarding and `context show` read the same Bind — the
session's own record when it has an id, else a registered DADAIA_CONTEXT.

Intent: CONTRACT — sa-bind-has-two-stores (WP-16); size: MEDIUM (hook and CLI subprocess
boundaries over a tmp workspace).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.cli.main import app
from dadaia_workspace.core import session_store
from dadaia_workspace.core.invocation import resolve
from dadaia_workspace.features.workspace.onboarding import next_step
from tests.fixtures.harness_env import (
    claude_hook_env,
    kimi_hook_env,
    run_hook_subprocess,
    scrub_context_resolution_env,
)

_NOW = "2999-01-01T00:00:00+00:00"
_CLAUDE = "CLAUDE_CODE_SESSION_ID"


def _workspace(root: Path, *names: str, dead: tuple[str, ...] = ()) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    rows = [
        {"name": n, "repo_slug": n, "repo_url": "u", "created_at": "2026-01-01T00:00:00Z",
         "state": "dead" if n in dead else "alive"}
        for n in names
    ]  # fmt: skip
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": rows})
    )
    for n in names:
        (root / "repos" / n).mkdir(parents=True)
    return root


def _record(root: Path, sid: str, context: str) -> None:
    session_store.write_session(
        root,
        sid,
        session_store.new_binding_record(
            session_id=sid, context=context, runtime="t", pid=1, now=_NOW
        ),
    )


@pytest.mark.parametrize(
    ("sid_var", "sid", "env_ctx", "record", "expected"),
    [
        pytest.param(_CLAUDE, "s1", "beta", "alpha", "alpha", id="native-id-record-wins-env-ignored"),
        pytest.param(_CLAUDE, "s1", "beta", None, None, id="native-id-no-record-unbound"),
        pytest.param(None, None, "beta", None, "beta", id="no-id-registered-env"),
        pytest.param(None, None, "ghost", None, None, id="no-id-ghost-env-unbound"),
        # bug codex-thread-id-bind-resolution-breaks-cli: CODEX_THREAD_ID alone is the id.
        pytest.param("CODEX_THREAD_ID", "thread-abc123", "beta", "alpha", "alpha", id="codex-thread-id-only"),
    ],
)  # fmt: skip
def test_the_readers_agree_on_the_bind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sid_var: str | None,
    sid: str | None,
    env_ctx: str,
    record: str | None,
    expected: str | None,
) -> None:
    """sa-bind-has-two-stores#S1, #S2, #S3: gate, ctx_inject, onboarding, the CLI specs
    resolver and `context show` ask one question and get one answer. The record is
    written by the real `context bind`; a workspace-root `specs/` is never a fallback
    (v0.1.50 FR4); an unbound no-arg `context show` answers `{"context": null}`
    (bug context-show-json-traceback-unbound)."""
    ws = _workspace(tmp_path, "alpha", "beta")
    for specs in ("repos/alpha/specs", "repos/beta/specs", "specs"):
        (ws / specs).mkdir()
    scrub_context_resolution_env(monkeypatch)
    monkeypatch.chdir(ws)
    if sid_var:
        monkeypatch.setenv(sid_var, sid)
    if record:
        assert CliRunner().invoke(app, ["context", "bind", record]).exit_code == 0
        assert (ws / ".dadaia" / "sessions" / f"{sid}.json").is_file()
    monkeypatch.setenv("DADAIA_CONTEXT", env_ctx)
    env = {"DADAIA_CONTEXT": env_ctx, **({sid_var: sid} if sid_var and sid else {})}
    inv = resolve(env=env, cwd=ws)
    assert inv.bind.context_name == expected  # the gate reads inv.bind

    hook_env = {**claude_hook_env(ws), **env}
    if not sid:
        hook_env = {**kimi_hook_env(ws), "DADAIA_CONTEXT": env_ctx}
    payload = {"session_id": sid} if sid else {}
    out = run_hook_subprocess("ctx_inject", payload, hook_env).stdout
    assert (f"[{expected}]" if expected else "[no bound context]") in out

    bound = None if not sid else inv.bind.context_name is not None
    step = next_step(ws, {"alpha": ws / "repos/alpha/specs"}, "alpha", bound)
    assert (step is not None and step.id == "bind") == (sid is not None and expected is None)

    shown = json.loads(CliRunner().invoke(app, ["context", "show", "--json"]).output)
    if expected is None:
        assert shown == {"context": None}
        with pytest.raises(typer.Exit):
            resolve_specs_dir_for_cli(None)
    else:
        assert shown["name"] == expected
        assert (shown["session"] or {}).get("context") == record
        assert resolve_specs_dir_for_cli(None) == (ws / "repos" / expected / "specs").resolve()


def test_a_ghost_env_never_denies_and_is_surfaced(tmp_path: Path) -> None:
    """sa-bind-has-two-stores#S3: a ghost DADAIA_CONTEXT is unbound (an id-less worktree
    write is the declared gap, ADR 0116) and ctx_inject emits a warning line."""
    ws = _workspace(tmp_path, "alpha")
    out = run_hook_subprocess("ctx_inject", {}, {**kimi_hook_env(ws), "DADAIA_CONTEXT": "ghost"})
    assert "! DADAIA_CONTEXT=ghost is not this session's bind" in out.stdout
    target = ws / "worktrees" / "alpha" / "0.5.0a-impl" / "x.py"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    gate = run_hook_subprocess(
        "sdd_gate", payload, {**kimi_hook_env(ws), "DADAIA_CONTEXT": "ghost"}
    )
    assert gate.block_envelope() is None


def test_running_the_printed_scope_fix_clears_the_deny(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-bind-has-two-stores#S4: a record-bound session denied a write runs the printed
    `context bind` fix and the retried write is ALLOWED — even with a stale env export."""
    ws = _workspace(tmp_path, "alpha", "beta")
    _record(ws, "s1", "alpha")
    env = {**claude_hook_env(ws, session_id="s1"), "DADAIA_CONTEXT": "alpha"}
    target = ws / "worktrees" / "beta" / "0.5.0a-impl" / "x.py"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s1"}
    denied = run_hook_subprocess("sdd_gate", payload, env).block_envelope()
    assert denied is not None and "context bind beta" in denied["reason"]

    monkeypatch.chdir(ws)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    assert CliRunner().invoke(app, ["context", "bind", "beta"]).exit_code == 0
    assert run_hook_subprocess("sdd_gate", payload, env).block_envelope() is None


def test_an_unbound_session_in_a_repo_injects_no_memory(tmp_path: Path) -> None:
    """sa-bind-has-two-stores#S6: cwd inside repos/alpha is not a bind."""
    ws = _workspace(tmp_path, "alpha")
    (ws / "repos" / "alpha" / "specs" / "memory").mkdir(parents=True)
    out = run_hook_subprocess(
        "ctx_inject", {"session_id": "s1"}, claude_hook_env(ws), cwd=ws / "repos" / "alpha"
    ).stdout
    assert "[alpha]" not in out and "memory bootstrap" not in out


def test_a_bound_context_without_specs_gets_its_next_step(tmp_path: Path) -> None:
    """sa-bind-has-two-stores#S7: header and next step, never "[no bound context]"."""
    ws = _workspace(tmp_path, "alpha")
    _record(ws, "s1", "alpha")
    out = run_hook_subprocess("ctx_inject", {"session_id": "s1"}, claude_hook_env(ws)).stdout
    assert "[alpha]" in out and "Next (" in out and "[no bound context]" not in out


@pytest.mark.parametrize(
    ("sid", "name", "fix"),
    [
        pytest.param("s1", "gamma", "context alive gamma", id="S9-dead-context"),
        pytest.param(None, "alpha", "export DADAIA_SESSION_ID=", id="ADR0116-no-id-never-mints"),
    ],
)
def test_bind_refuses_with_its_fix_and_writes_no_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sid: str | None, name: str, fix: str
) -> None:
    """sa-bind-has-two-stores#S9; AC1.2: with no native id and no DADAIA_SESSION_ID the
    bind exits non-zero with the export fix instead of minting an id no hook can see."""
    ws = _workspace(tmp_path, "gamma", "alpha", dead=("gamma",))
    scrub_context_resolution_env(monkeypatch)
    monkeypatch.chdir(ws)
    if sid:
        monkeypatch.setenv(_CLAUDE, sid)
    result = CliRunner().invoke(app, ["context", "bind", name])
    assert result.exit_code == 1 and fix in result.output
    assert not list((ws / ".dadaia").glob("sessions/*.json"))
