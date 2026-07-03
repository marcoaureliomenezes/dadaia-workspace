"""CLI ``dadaia context release`` — drops held lease(s) + clears by-session index.

T-014-08 / FR-W4-03 (closes ``context-release-leaves-lease-heartbeat-renewing``).

These are CLI-LEVEL tests: they drive ``context.release_cmd`` through the Typer runner
end-to-end against a minimal tmp workspace (NO real venv built — the workspace root is
just a ``tmp_path`` directory with the lock/session state seeded directly on disk, the
same fixture shape as ``test_lock_steal.py``). The predicate logic itself is covered at
the lease level in ``test_lease_release_predicates.py``; here we assert the CLI wires the
release into the command:

* **release WITH a held lease** → lock record gone AND by-session index entry gone,
  in both the eval flow (env sid == holder sid) and the default flow (CLI sid ≠ holder
  sid, holder pid resolved dead/owned).
* **release WITHOUT a lease** → a clean no-op (exit 0, nothing to drop).
* **a live foreign holder** is NEVER released by context name alone (default flow).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands import context as context_cmd
from dadaia_workspace.core.protocols.process_ancestry import Ancestry
from dadaia_workspace.features.spec_context import lease

runner = CliRunner()


# --------------------------------------------------------------------------- #
# Helpers — seed a minimal workspace on disk (no venv, no install)
# --------------------------------------------------------------------------- #


def _seed_lease(ws: Path, ctx: str, sid: str, *, pid: int) -> None:
    """Acquire a real lease record + by-session index entry directly via the API."""
    lease.acquire(ws, ctx, sid, "v0.1.14", "IMPLEMENTATION", pid=pid)


def _seed_session(ws: Path, sid: str, ctx: str) -> None:
    """Write a CLI session record naming the bound context (default-flow input)."""
    sessions_dir = context_cmd._sessions_dir(ws)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    (sessions_dir / f"{sid}.json").write_text(
        json.dumps({"session_id": sid, "context": ctx, "mode": "IMPLEMENTATION"}),
        encoding="utf-8",
    )


def _patch_workspace(monkeypatch: pytest.MonkeyPatch, ws: Path) -> None:
    monkeypatch.setattr(context_cmd, "resolve_workspace_root", lambda: ws)


def _patch_probes(monkeypatch: pytest.MonkeyPatch, *, alive: bool, ancestry: Ancestry) -> None:
    """Seam the default-flow ownership probes the CLI builds.

    v0.1.54 FR6: ``context release`` now calls the single public
    ``infrastructure.process_probe_adapter.build_pid_probe`` bound in the command module's
    namespace (``context_cmd.build_pid_probe``); the ancestry probe still comes from the
    container.
    """
    monkeypatch.setattr(context_cmd, "build_pid_probe", lambda: lambda _pid: alive)

    class _FakeAncestry:
        def is_ancestor(self, _holder: int, _caller: int) -> Ancestry:
            return ancestry

    monkeypatch.setattr(container, "build_process_ancestry", _FakeAncestry)


# --------------------------------------------------------------------------- #
# Eval flow (env sid == holder sid)
# --------------------------------------------------------------------------- #


def test_release_eval_flow_drops_lease_and_clears_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """env sid holds the lease ⇒ release drops the record AND the by-session index."""
    ws = tmp_path
    sid = "sess_env01"
    _seed_lease(ws, "ctxa", sid, pid=4242)
    _seed_session(ws, sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    monkeypatch.setenv("DADAIA_SESSION_ID", sid)

    # Precondition: lease + index present.
    assert lease.read_record(ws, "ctxa") is not None
    assert lease.contexts_for_session(ws, sid) == ["ctxa"]

    result = runner.invoke(context_cmd.app, ["release"])

    assert result.exit_code == 0, result.output
    assert "ctxa" in result.output  # the dropped lease is reported
    assert lease.read_record(ws, "ctxa") is None
    assert lease.contexts_for_session(ws, sid) == []
    # Session record unlinked too.
    assert not (context_cmd._sessions_dir(ws) / f"{sid}.json").exists()


# --------------------------------------------------------------------------- #
# Default flow (CLI sid ≠ holder sid)
# --------------------------------------------------------------------------- #


def test_release_default_flow_drops_lease_when_holder_dead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI sid ≠ holder sid, holder pid DEAD ⇒ bound-context lease released + index cleared."""
    ws = tmp_path
    holder_sid = "sess_harness"
    cli_sid = "sess_cli01"
    _seed_lease(ws, "ctxa", holder_sid, pid=9999)
    _seed_session(ws, cli_sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    _patch_probes(monkeypatch, alive=False, ancestry=Ancestry.NOT_ANCESTOR)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

    result = runner.invoke(context_cmd.app, ["release", "--session", cli_sid])

    assert result.exit_code == 0, result.output
    assert lease.read_record(ws, "ctxa") is None
    assert lease.contexts_for_session(ws, holder_sid) == []


def test_release_default_flow_keeps_live_foreign_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI sid ≠ holder sid, holder ALIVE + NOT in ancestry ⇒ lease NOT released."""
    ws = tmp_path
    holder_sid = "sess_foreign"
    cli_sid = "sess_cli02"
    _seed_lease(ws, "ctxa", holder_sid, pid=9999)
    _seed_session(ws, cli_sid, "ctxa")
    _patch_workspace(monkeypatch, ws)
    _patch_probes(monkeypatch, alive=True, ancestry=Ancestry.NOT_ANCESTOR)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

    result = runner.invoke(context_cmd.app, ["release", "--session", cli_sid])

    assert result.exit_code == 0, result.output
    # Live foreign holder's lease survives — only the CLI session record is unlinked.
    rec = lease.read_record(ws, "ctxa")
    assert rec is not None
    assert rec["session_id"] == holder_sid
    assert lease.contexts_for_session(ws, holder_sid) == ["ctxa"]
    assert not (context_cmd._sessions_dir(ws) / f"{cli_sid}.json").exists()


# --------------------------------------------------------------------------- #
# No-lease no-op
# --------------------------------------------------------------------------- #


def test_release_without_lease_is_clean_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """release with a session record but no held lease ⇒ exit 0, nothing dropped."""
    ws = tmp_path
    cli_sid = "sess_cli03"
    _seed_session(ws, cli_sid, "ctxa")  # bound, but no lease acquired
    _patch_workspace(monkeypatch, ws)
    _patch_probes(monkeypatch, alive=False, ancestry=Ancestry.NOT_ANCESTOR)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

    result = runner.invoke(context_cmd.app, ["release", "--session", cli_sid])

    assert result.exit_code == 0, result.output
    assert lease.read_record(ws, "ctxa") is None
    assert not (context_cmd._sessions_dir(ws) / f"{cli_sid}.json").exists()


def test_release_no_session_id_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither --session nor DADAIA_SESSION_ID ⇒ exit 1 with an actionable message."""
    _patch_workspace(monkeypatch, tmp_path)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

    result = runner.invoke(context_cmd.app, ["release"])

    assert result.exit_code == 1, result.output
    assert "session" in result.output.lower()
