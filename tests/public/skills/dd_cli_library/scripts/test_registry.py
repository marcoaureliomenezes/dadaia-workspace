"""dd-cli-library/scripts/registry.py owns the port registry JSON (one stdlib script).
Size: SMALL."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.platform import quote
from tests.helpers.oslib import popen, read_text, run, write_text

_SCRIPT = (
    Path(__file__).resolve().parents[5]
    / "dadaia_workspace"
    / "public"
    / "skills"
    / "dd-cli-library"
    / "scripts"
    / "registry.py"
)


def _run(registry: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(_SCRIPT), "--registry", str(registry), *argv], check=False)


def _entries(registry: Path) -> list[dict[str, object]]:
    return json.loads(read_text(registry))["entries"]


def test_register_list_release_round_trip(tmp_path: Path) -> None:
    reg = tmp_path / ".dadaia" / "states" / "server_registry.json"
    assert _run(reg, "register", "--port", "3100", "--project", "demo").returncode == 0
    doc = json.loads(read_text(reg))
    assert doc["version"] == "1" and doc["range"] == {"min_port": 3000, "max_port": 3999}
    assert [e["port"] for e in doc["entries"]] == [3100]

    listed = json.loads(_run(reg, "list", "--json").stdout)
    assert listed[0]["project"] == "demo" and listed[0]["status"] == "active"

    assert _run(reg, "release", "--port", "3100").returncode == 0
    assert _entries(reg) == []


def test_same_project_reregister_is_idempotent_and_other_project_is_refused(
    tmp_path: Path,
) -> None:
    reg = tmp_path / "r.json"
    _run(reg, "register", "--port", "3100", "--project", "demo")
    again = _run(reg, "register", "--port", "3100", "--project", "demo")
    assert again.returncode == 0 and len(_entries(reg)) == 1
    other = _run(reg, "register", "--port", "3100", "--project", "other")
    assert other.returncode == 1 and "'demo'" in other.stderr


def test_next_is_deterministic_and_skips_occupied_base(tmp_path: Path) -> None:
    reg = tmp_path / "r.json"
    first = json.loads(_run(reg, "next", "--project", "demo", "--json").stdout)
    second = json.loads(_run(reg, "next", "--project", "demo", "--json").stdout)
    assert first == second and 3000 <= first["port"] <= 3999 and first["is_base_port"]
    _run(reg, "register", "--port", str(first["port"]), "--project", "holder")
    moved = json.loads(_run(reg, "next", "--project", "demo", "--json").stdout)
    assert moved["port"] != first["port"] and moved["is_base_port"] is False


def test_clean_removes_expired_entries_only(tmp_path: Path) -> None:
    reg = tmp_path / "r.json"
    _run(reg, "register", "--port", "3200", "--project", "fresh")
    doc = json.loads(read_text(reg))
    past = (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat()
    doc["entries"].append(
        {
            "port": 3201,
            "project": "old",
            "url": "http://localhost:3201",
            "status": "active",
            "pid": None,
            "reserved_at": past,
            "expires_at": past,
            "description": None,
        }
    )
    write_text(reg, json.dumps(doc))
    dry = _run(reg, "clean", "--dry-run")
    assert "would remove: port 3201" in dry.stdout and len(_entries(reg)) == 2
    assert _run(reg, "clean").returncode == 0
    assert [e["port"] for e in _entries(reg)] == [3200]


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("registry", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_without_selector_is_refused(tmp_path: Path) -> None:
    result = _run(tmp_path / "r.json", "release")
    assert result.returncode == 1 and "--port" in result.stderr


def test_scan_skips_registered_privileged_and_pidless_listeners() -> None:
    module = _load_module()
    listener = module._platform.Listener
    found = [
        listener(4999, "127.0.0.1", os.getpid(), "dadaia", "/w"),
        listener(22, "0.0.0.0", 1, "sshd", "/"),
        listener(8080, "0.0.0.0", os.getpid(), "node", "/app"),
        listener(9000, "127.0.0.1", None, "", ""),
    ]
    doc = {"entries": [{"port": 4999}]}
    findings = module.scan(doc, found)
    assert [f["port"] for f in findings] == [8080]
    assert findings[0]["lan_exposed"] is True and findings[0]["bind"] == "0.0.0.0"
    assert findings[0]["cmdline"] == "node" and findings[0]["cwd"] == "/app"
    assert module.scan(doc, None) == []


def _run_in(cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(_SCRIPT), *argv], check=False, cwd=cwd)


def test_registry_resolves_the_workspace_sentinel_never_a_partial_dadaia(tmp_path: Path) -> None:
    """From repos/<slug> holding a partial .dadaia/ (no
    sentinel), the registry lands in the workspace owning the sentinel."""
    workspace = tmp_path / "ws"
    repo = workspace / "repos" / "yb"
    (repo / ".dadaia").mkdir(parents=True)
    (workspace / ".dadaia" / "states").mkdir(parents=True)
    write_text(workspace / ".dadaia" / "states" / "spec_contexts.json", "{}")
    assert _run_in(repo, "register", "--port", "3100", "--project", "demo").returncode == 0
    reg = workspace / ".dadaia" / "states" / "server_registry.json"
    assert [e["port"] for e in _entries(reg)] == [3100]
    assert not (repo / ".dadaia" / "states").exists()


def test_registry_refuses_when_no_dadaia_dir_is_above_the_cwd(tmp_path: Path) -> None:
    """No workspace sentinel above (a bare .dadaia/ is
    not one) → exit non-zero, no registry written."""
    lonely = tmp_path / "lonely"
    (lonely / ".dadaia").mkdir(parents=True)
    result = _run_in(lonely, "list")
    assert result.returncode != 0
    assert "no workspace sentinel above the cwd" in result.stderr
    assert not any(tmp_path.rglob("server_registry.json"))


def test_entry_with_a_dead_pid_is_stale_before_its_ttl(tmp_path: Path) -> None:
    reg = tmp_path / "r.json"
    probe = popen([sys.executable, "-c", "pass"])
    probe.wait()
    dead_pid = probe.pid
    _run(reg, "register", "--port", "3100", "--project", "demo", "--pid", str(dead_pid))
    listed = json.loads(_run(reg, "list", "--json", "--status", "all").stdout)
    assert listed[0]["status"] == "stale"
    alive = _run(reg, "register", "--port", "3200", "--project", "live", "--pid", str(os.getpid()))
    assert alive.returncode == 0
    listed = json.loads(_run(reg, "list", "--json", "--status", "all").stdout)
    assert {e["port"]: e["status"] for e in listed} == {3200: "active"}


def test_a_concurrent_load_never_reads_a_half_written_registry(tmp_path: Path) -> None:
    """Interleaved save and load never raise JSONDecodeError (a load raising it fails the reader
    thread)."""
    import threading

    module = _load_module()
    registry = tmp_path / "server_registry.json"
    doc = json.dumps({"entries": [{"port": p} for p in range(2000)]}) + "\n"
    module.replace(registry, doc)
    reader = threading.Thread(target=lambda: [module.load(registry) for _ in range(300)])
    reader.start()
    for _ in range(300):
        module.replace(registry, doc)
    reader.join()


def test_staleness_asks_the_kernel_whether_the_pid_lives(monkeypatch: pytest.MonkeyPatch) -> None:
    """The registry holds no liveness probe of its own: on any host a pid the kernel reports
    gone makes its entry stale, and one it reports alive keeps it active."""
    module = _load_module()
    asked: list[int] = []
    verdicts = {4242: False, 4343: True}

    def alive(pid: int, caps: object = None) -> bool:
        asked.append(pid)
        return verdicts[pid]

    monkeypatch.setattr(module._platform, "pid_alive", alive)
    monkeypatch.setattr(sys, "platform", "win32")
    stamp = "2999-01-01T00:00:00+00:00"
    assert module.is_stale({"expires_at": stamp, "pid": 4242}) is True
    assert module.is_stale({"expires_at": stamp, "pid": 4343}) is False
    assert asked == [4242, 4343]


def test_register_stamps_through_the_kernel_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`register` takes its instant from `_clock.now_iso()` (called through the module,
    so a test freezes it) and writes both stamps in that clock's `YYYY-MM-DDTHH:MM:SSZ` form;
    `expires_at` is the default 8-hour TTL later."""
    module = _load_module()
    import _clock  # on sys.path once registry.py is loaded

    monkeypatch.setattr(_clock, "now_iso", lambda: "2026-01-02T03:04:05Z")
    reg = tmp_path / "r.json"
    assert (
        module.main(["--registry", str(reg), "register", "--port", "3100", "--project", "d"]) == 0
    )
    (entry,) = _entries(reg)
    assert (entry["reserved_at"], entry["expires_at"]) == (
        "2026-01-02T03:04:05Z",
        "2026-01-02T11:04:05Z",
    )


def _refused(refused: subprocess.CompletedProcess[str], error: str, fix: str) -> None:
    assert refused.returncode == 1
    assert refused.stderr == f"[error] {error}\nfix: {fix}\n"


def test_the_delete_fix_quotes_a_path_holding_a_blank(tmp_path: Path) -> None:
    reg = tmp_path / "a dir" / "r.json"
    reg.parent.mkdir()
    reg.write_bytes(b"\xff")
    _refused(
        _run(reg, "list"),
        f"{reg} is not valid UTF-8",
        f"Operator action: delete {quote(str(reg))} — the next registry.py run starts an empty registry",
    )


def test_every_registry_refusal_prints_one_error_line_and_one_fix_line(tmp_path: Path) -> None:
    reg = tmp_path / "r.json"
    _run(reg, "register", "--port", "3100", "--project", "demo")
    _refused(
        _run(reg, "register", "--port", "3100", "--project", "other"),
        "port 3100 is registered by project 'demo' (http://localhost:3100)",
        "Agent action: pick another port with registry.py next, then rerun",
    )
    _refused(
        _run(reg, "release"),
        "provide --port and/or --project",
        "Agent action: pass --port and/or --project, then rerun",
    )
    _refused(
        _run(reg, "release", "--port", "3999"),
        "port 3999 is not registered",
        "Agent action: run registry.py list to see the registered ports, then rerun",
    )
    _refused(
        _run(reg, "next", "--project", "z", "--min-port", "3100", "--max-port", "3100"),
        "no free ports in [3100, 3100]",
        "Agent action: run registry.py clean, then rerun",
    )
    (lonely := tmp_path / "lonely").mkdir()
    _refused(
        _run_in(lonely, "list"),
        "no workspace sentinel above the cwd",
        "Agent action: rerun with --registry and a registry file path, or from inside a workspace",
    )
    reg.write_bytes(b"\xff")
    _refused(
        _run(reg, "list"),
        f"{reg} is not valid UTF-8",
        f"Operator action: delete {quote(str(reg))} — the next registry.py run starts an empty registry",
    )


def test_a_planted_kernel_module_on_the_path_never_loads(tmp_path: Path) -> None:
    """The kernel's `_clock` wins over any same-named module an earlier path entry holds."""
    planted = tmp_path / "planted"
    planted.mkdir()
    marker = tmp_path / "loaded"
    write_text(planted / "_clock.py", f"open({str(marker)!r}, 'w').close()\nraise SystemExit(97)\n")
    reg = tmp_path / ".dadaia" / "states" / "server_registry.json"
    env = {**os.environ, "PYTHONPATH": str(planted)}
    done = run([sys.executable, str(_SCRIPT), "--registry", str(reg), "list"], check=False, env=env)

    assert (done.returncode, marker.exists()) == (0, False), done.stderr
