"""Pre-commit advisory presence check across the real git-hook boundary.

Harness independence (regression for ``codex-exec-hooks-do-not-fire-headless``): the gate
fires from a real ``git commit`` through the installed ``.git/hooks/pre-commit`` script with
NO harness hook environment — no PreToolUse/PostToolUse payload, nothing but
``DADAIA_BIN``/``DADAIA_SESSION_ID``/``WORKSPACE_ROOT`` in the child env. That is the whole
point: the chokepoint protects runtimes whose in-process hooks never fire.

Scenarios (seed 1):

* No presence         → commit flows.
* Live sibling        → commit flows with an advisory naming the sibling.
* Self presence       → commit flows without a foreign warning.
* G6                  → holder commits with ZERO security handoffs on disk → still flows
                        (the pre-commit gate consults presence only, never a verdict).

The live sibling is a real long-lived child process. No fixed sleeps: it signals readiness
via a flag file with a bounded deadline.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.e2e.rendezvous import wait_for_file

pytestmark = pytest.mark.e2e

_SLUG = "demo-ctx"
_READY_DEADLINE = 30.0
_EXIT_DEADLINE = 30.0

#: A long-lived "foreign holder": just stay alive (pid genuinely running) until told to stop.
_HOLDER = textwrap.dedent(
    """
    import os, sys, time
    from pathlib import Path
    ready, stop, pidfile = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    pidfile.write_text(str(os.getpid()))
    ready.write_text("ready")
    deadline = time.monotonic() + 120.0
    while not stop.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    """
)


def _init_repo(workspace: Path, slug: str) -> Path:
    """A real git repo at ``<workspace>/repos/<slug>`` with the pre-commit hook installed."""
    (workspace / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = workspace / "repos" / slug
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.st"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    # Install a pre-commit hook that calls the CLI through THIS interpreter (harness-free).
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/usr/bin/env bash\nset -e\n"
        f'exec "{sys.executable}" -m dadaia_workspace.cli.main ci pre-commit-check\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    return repo


def _hook_env(workspace: Path, *, session_id: str | None) -> dict[str, str]:
    """A harness-FREE env: only WORKSPACE_ROOT + (optionally) DADAIA_SESSION_ID."""
    env = dict(os.environ)
    for bad in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "DADAIA_MODE"):
        env.pop(bad, None)
    env["WORKSPACE_ROOT"] = str(workspace)
    env.pop("DADAIA_SESSION_ID", None)
    if session_id is not None:
        env["DADAIA_SESSION_ID"] = session_id
    return env


def _write_presence(workspace: Path, slug: str, *, sid: str, pid: int) -> None:
    presence_dir = workspace / ".dadaia" / "states" / "presence" / slug
    presence_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    (presence_dir / f"{sid}.json").write_text(
        json.dumps(
            {
                "session_id": sid,
                "runtime": "test",
                "pid": pid,
                "started_at": now,
                "last_seen_at": now,
            }
        ),
        encoding="utf-8",
    )


def _commit(repo: Path, env: dict[str, str], message: str) -> subprocess.CompletedProcess[str]:
    target = repo / "file.py"
    target.write_text(f"# {message}\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.py"], cwd=repo, check=True, env=env)
    return subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=_EXIT_DEADLINE,
    )


def _start_holder(tmp_path: Path) -> tuple[subprocess.Popen[str], int, Path]:
    ready, stop, pidfile = tmp_path / "h.ready", tmp_path / "h.stop", tmp_path / "h.pid"
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(ready), str(stop), str(pidfile)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    wait_for_file(ready, deadline_s=_READY_DEADLINE, what="foreign holder to start")
    return proc, int(pidfile.read_text().strip()), stop


def _stop_holder(proc: subprocess.Popen[str], stop: Path) -> None:
    stop.write_text("stop")
    try:
        proc.wait(timeout=_EXIT_DEADLINE)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=_EXIT_DEADLINE)


@pytest.mark.parametrize(
    "variant",
    ["no-presence", "self-presence", "g6-zero-handoffs"],
    ids=["no-presence-flows", "self-presence-flows", "g6-zero-handoffs-flows"],
)
def test_allow_path_variants_flow(tmp_path: Path, variant: str) -> None:
    """No presence, self presence, and zero-handoff commits all flow."""
    workspace = tmp_path
    repo = _init_repo(workspace, _SLUG)

    if variant == "no-presence":
        result = _commit(repo, _hook_env(workspace, session_id=None), "no-presence")
        assert result.returncode == 0, result.stdout + result.stderr
        return

    holder_proc, holder_pid, stop = _start_holder(tmp_path)
    try:
        _write_presence(workspace, _SLUG, sid="holder-A", pid=holder_pid)
        if variant == "g6-zero-handoffs":
            assert not (workspace / ".dadaia" / "handoff").exists()
        result = _commit(repo, _hook_env(workspace, session_id="holder-A"), variant)
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        _stop_holder(holder_proc, stop)


def test_live_sibling_presence_allows_commit_with_advisory(tmp_path: Path) -> None:
    """A live sibling presence allows commit and names the sibling in an advisory."""
    workspace = tmp_path
    repo = _init_repo(workspace, _SLUG)
    holder_proc, holder_pid, stop = _start_holder(tmp_path)
    try:
        _write_presence(workspace, _SLUG, sid="foreign-holder", pid=holder_pid)
        # Committer is a different session (no env sid, not in the holder's ancestry).
        result = _commit(repo, _hook_env(workspace, session_id="committer-B"), "foreign-allowed")
        assert result.returncode == 0, result.stdout + result.stderr
        out = result.stdout + result.stderr
        assert "foreign-holder" in out, out
        for forbidden in ("rebind", "relaunch", "lock steal"):
            assert forbidden not in out.lower(), out
    finally:
        _stop_holder(holder_proc, stop)


def _dead_pid(tmp_path: Path) -> int:
    """Spawn a process, wait for it to exit, and return its now-DEAD pid.

    The pid is reaped (we ``wait``), so it represents stale process metadata.
    """
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(timeout=_EXIT_DEADLINE)
    return proc.pid


def test_relaunch_dead_recorded_pid_fresh_heartbeat_flows(tmp_path: Path) -> None:
    """ADR-G1 relaunch window across the REAL git boundary: dead recorded pid ⇒ commit flows.

    The qa-gate REJECT reproduced exactly this: ``renew_heartbeat`` keeps the heartbeat fresh
    but never refreshes ``pid``, so a same-sid relaunch (new pid, same ``.ptr``) leaves a DEAD
    recorded pid. The relaunched incumbent then runs ``git commit`` from a new process tree
    with no env sid. Before the fix this false-blocked; the dead-holder pid probe on the block
    branch now degrades to an advisory allow, so the commit must succeed.
    """
    workspace = tmp_path
    repo = _init_repo(workspace, _SLUG)
    # Fresh heartbeat (default), but the recorded holder pid is dead.
    _write_presence(workspace, _SLUG, sid="holder-A", pid=_dead_pid(tmp_path))
    # Relaunched incumbent: a brand-new process tree, no exported sid, not in the dead pid's tree.
    result = _commit(repo, _hook_env(workspace, session_id=None), "relaunch-flows")
    assert result.returncode == 0, result.stdout + result.stderr


#: Holder that runs `git commit` ITSELF, so the git→hook→python tree is a real descendant of
#: this process's pid — exercising the harness-real ANCESTOR allow path across the git boundary.
_HOLDER_COMMITS = textwrap.dedent(
    """
    import os, subprocess, sys, time
    from pathlib import Path
    repo, pidfile, gofile = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    pidfile.write_text(str(os.getpid()))
    # Wait until the parent has written the lease referencing THIS pid (bounded).
    deadline = time.monotonic() + 30.0
    while not gofile.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    env = dict(os.environ)
    target = Path(repo) / "anc.py"
    target.write_text("# ancestry-allow\\n")
    subprocess.run(["git", "add", "anc.py"], cwd=repo, check=True, env=env)
    r = subprocess.run(
        ["git", "commit", "-m", "ancestry-allow"],
        cwd=repo, capture_output=True, text=True, env=env, timeout=30.0,
    )
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    sys.exit(r.returncode)
    """
)


def test_holder_child_commit_flows_via_real_ancestry(tmp_path: Path) -> None:
    """The holder's OWN `git commit` flows via the REAL ancestry walk (no env sid).

    The lease records the holder's live pid. The holder then runs ``git commit`` itself with
    NO ``DADAIA_SESSION_ID`` exported — so the gate cannot use the env-sid fast path and must
    prove identity purely through ``ProcessAncestry``: the git→pre-commit→python(check)
    process is a genuine descendant of the holder pid. This is the ancestry-ANCESTOR allow
    path proven e2e across the real git-hook boundary (previously unit-faked only).
    """
    workspace = tmp_path
    repo = _init_repo(workspace, _SLUG)
    pidfile = tmp_path / "anc.pid"
    gofile = tmp_path / "anc.go"
    env = _hook_env(workspace, session_id=None)  # NO env sid — force the ancestry path.
    # The holder commits as a subprocess; we record ITS pid as the lease holder, then signal
    # "go" so the holder's own `git commit` fires only after the lease exists.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _HOLDER_COMMITS,
            str(repo),
            str(pidfile),
            str(gofile),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    wait_for_file(pidfile, deadline_s=_READY_DEADLINE, what="holder to report pid")
    holder_pid = int(pidfile.read_text().strip())
    _write_presence(workspace, _SLUG, sid="holder-A", pid=holder_pid)
    gofile.write_text("go")
    out, err = proc.communicate(timeout=_EXIT_DEADLINE)
    assert proc.returncode == 0, (
        f"holder's own commit must flow via real ancestry; rc={proc.returncode}\n{out}\n{err}"
    )
