"""sdd_gate's ALLOW/BLOCK verdict, driven as a real PreToolUse subprocess.

Intent: CONTRACT — the install ledger decides PROTECTED (sa-gate-path-classes-diverge-from-the-law);
scope is path-first and repos/<r>/ is merge-only (T-050-97, AC1.1); the gate never blocks on
concurrency (NO-LOCKS doctrine, v0.1.76); a fenced root stays protected (AC1.3); a repo's own AGENTS.md is never law (v0.4.5 FR1).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core import session_store
from dadaia_workspace.core.workspace_resolver import FENCE_ENV
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _mk_workspace(tmp_path: Path, *slugs: str) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"name": s, "repo_slug": s, "state": "alive"} for s in slugs]}),
        encoding="utf-8",
    )
    for s in slugs:
        (tmp_path / "repos" / s / "specs").mkdir(parents=True, exist_ok=True)
    return tmp_path


_LEDGERED = (
    ".claude/settings.json", ".codex/hooks.json", ".dadaia/hooks/codex-pre-gate",
    ".agents/skills/dd-x/SKILL.md", "AGENTS.md", ".dadaia/AGENTS.md", ".dadaia/tmp/AGENTS.md",
)  # fmt: skip
_BLOCK = ""  # any block, whatever its reason
_PATCH = "*** Begin Patch\n*** Update File: README.md\n+ok\n*** Update File: {}\n+x\n*** End Patch"
_WT_A = "worktrees/a/0.5.0a-impl/"
_BOUND_A = {"s": {"context": "a"}}


def _row(id: str, target: Any, want: str | None = None, **opts: Any) -> Any:
    return pytest.param(target, want, opts, id=id)


@pytest.mark.parametrize(
    ("target", "want", "opts"),
    [
        _row("non-write-tool", "x", tool="Read"),
        _row("unparseable-target", None),
        _row("F3-non-grammar-slug-is-no-repo", "repos/a.b/x.py"),
        _row("protected-sessions-fails-closed", ".dadaia/sessions/runtime/a.ptr", "SEC-01"),
        _row("AC1.3-a-fenced-root-stays-protected", ".dadaia/sessions/runtime/a.ptr",
             "SEC-01", fence=True),
        _row("worktree-agents-md-is-never-law-A1.1", _WT_A + "AGENTS.md", records=_BOUND_A),
        _row("AC1.1-bound-repos-write-names-the-worktree", "repos/a/src/x.py",
             "worktree.py new a --kind impl", records=_BOUND_A),
        _row("apply-patch-a-later-protected-header-blocks-T-014-02",
             _PATCH.format(".dadaia/sessions/runtime/a.ptr"), "SEC-01", tool="apply_patch"),
        _row("apply-patch-all-headers-allowed", _PATCH.format("docs/notes.md"), tool="apply_patch"),
        _row("path-first-a-write-under-b-is-b-never-first-alive-a",
             "worktrees/b/0.5.0a-impl/src/x.py", "context bind b"),
        _row("no-repo-no-context-fails-open", "specs/releases/x/TASKS.md"),
        _row("sa-bind-has-two-stores#S1-dadaia-context-is-ignored-for-an-unbound-native-id",
             "worktrees/b/0.5.0a-impl/src/x.py", "context bind b", env={"DADAIA_CONTEXT": "b"}),
        _row("F3-bound-audit-write-allowed", "repos/a/specs/audits/20260101-x/index.md",
             records=_BOUND_A),
        _row("no-repo-write-resolves-via-rung3-cwd-repo", "specs/releases/r/TASKS.md",
             cwd="repos/a"),
        _row("two-live-sessions-both-write-no-lock", _WT_A + "specs/releases/rel-1/TASKS.md",
             records={**_BOUND_A, "peer": {"context": "a"}}),
        _row("a-foreign-read-bind-never-imposes-read-on-my-write", _WT_A + "src/x.py",
             records={**_BOUND_A, "peer": {"mode": "READ"}}),
        *(_row(f"sa-gate-path-classes-diverge-from-the-law#B39-1-hook-wiring-{r}", r,
               "public install", ledger=True)
          for r in (".claude/settings.json", ".codex/hooks.json", ".dadaia/hooks/codex-pre-gate")),
        *(_row(f"sa-gate-path-classes-diverge-from-the-law#B39-2-{r}", r, _BLOCK, ledger=True)
          for r in (".agents/skills/dd-x/SKILL.md", ".dadaia/states/install_ledger.json")),
        *(_row(f"sa-gate-path-classes-diverge-from-the-law#B39-7-ledgered-law-{r}", r, _BLOCK,
               ledger=True) for r in ("AGENTS.md", ".dadaia/AGENTS.md", ".dadaia/tmp/AGENTS.md")),
        *(_row(f"B39-7-unledgered-law-is-an-ordinary-write-{r}", r)
          for r in ("AGENTS.md", ".dadaia/AGENTS.md", ".dadaia/tmp/AGENTS.md")),
        _row("sa-gate-path-classes-diverge-from-the-law#B39-3-a-tmp-probe-agents-md",
             ".dadaia/tmp/probe/20260927/AGENTS.md", ledger=True),
        _row("sa-gate-path-classes-diverge-from-the-law#B39-4-root-histo",
             "specs/releases/_archive/releases_histo.jsonl"),
    ],
)  # fmt: skip
def test_gate_verdict(tmp_path: Path, target: Any, want: str | None, opts: dict[str, Any]) -> None:
    """The hook blocks the PROTECTED/ledgered paths and the out-of-scope or merge-only ones
    (``want`` names the reason), never on a peer session, the env or the cwd."""
    ws = _mk_workspace(tmp_path, "a", "b")
    if opts.get("ledger"):
        entries = [
            {"relpath": p, "sha256": "0" * 64, "family": "x", "kind": "file"} for p in _LEDGERED
        ]
        (ws / ".dadaia" / "states" / "install_ledger.json").write_text(
            json.dumps({"schema_version": "1", "entries": entries}), encoding="utf-8"
        )
    now = datetime.now(tz=UTC).isoformat()
    for sid, record in opts.get("records", {}).items():
        session_store.write_session(ws, sid, {"session_id": sid, "last_seen_at": now, **record})
    tool = opts.get("tool", "Write")
    if tool == "apply_patch":
        tool_input: dict[str, Any] = {"command": target}
    elif target is None:
        tool_input = {}
    else:
        tool_input = {"file_path": str(ws / target)}
    env = claude_hook_env(ws, session_id="s")
    env.pop("DADAIA_CONTEXT", None)  # never inherit the operator's shell
    env.update(opts.get("env", {}))
    if opts.get("fence"):  # the fence says "never act on", never "nothing protects"
        env[FENCE_ENV] = os.pathsep.join(filter(None, (env.get(FENCE_ENV), str(ws))))
    payload = {"tool_name": tool, "tool_input": tool_input, "session_id": "s"}
    result = run_hook_subprocess("sdd_gate", payload, env, cwd=ws / opts.get("cwd", ""))
    assert result.returncode == 0, result.stderr
    block = result.block_envelope()
    if want is None:
        assert block is None, block
    else:
        assert block is not None and want in block["reason"], block


def test_a_truncated_registry_is_no_context_at_the_gate_and_in_context_show(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-context-repo-mapping-falls-back-to-the-name#B4 (the gate and `context show
    --json` legs; alive_context_names is test_invocation's): with a truncated
    spec_contexts.json and DADAIA_CONTEXT naming a context, the real hook neither crashes
    nor scope-blocks an id-less worktree write (no context is registered, ADR 0116), and
    `context show --json` answers
    `{"context": null}`, exit 0."""
    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    ws = _mk_workspace(tmp_path, "proj", "other")
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": [{"na')
    env = claude_hook_env(ws, session_id="s")
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env["DADAIA_CONTEXT"] = "proj"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(ws / "worktrees/other/0.5.0a-impl/x.py")},
    }

    gate = run_hook_subprocess("sdd_gate", payload, env)

    assert gate.returncode == 0, gate.stderr
    assert gate.block_envelope() is None

    monkeypatch.chdir(ws)
    monkeypatch.setenv("DADAIA_CONTEXT", "proj")
    for var in (
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
        "DADAIA_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    shown = CliRunner().invoke(app, ["context", "show", "--json"])

    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output) == {"context": None}
