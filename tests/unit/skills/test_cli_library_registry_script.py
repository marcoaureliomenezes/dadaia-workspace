"""Intent: CONTRACT — dd-cli-library/scripts/registry.py owns the port registry JSON (0.4.7
c5 T-047-45: the `dadaia server` group retired into one stdlib script). Size: SMALL."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "dadaia_workspace"
    / "public"
    / "skills"
    / "dd-cli-library"
    / "scripts"
    / "registry.py"
)


def _run(registry: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--registry", str(registry), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


def _entries(registry: Path) -> list[dict[str, object]]:
    return json.loads(registry.read_text(encoding="utf-8"))["entries"]


def test_register_list_release_round_trip(tmp_path: Path) -> None:
    reg = tmp_path / ".dadaia" / "states" / "server_registry.json"
    assert _run(reg, "register", "--port", "3100", "--project", "demo").returncode == 0
    doc = json.loads(reg.read_text(encoding="utf-8"))
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
    doc = json.loads(reg.read_text(encoding="utf-8"))
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
    reg.write_text(json.dumps(doc), encoding="utf-8")
    dry = _run(reg, "clean", "--dry-run")
    assert "would remove: port 3201" in dry.stdout and len(_entries(reg)) == 2
    assert _run(reg, "clean").returncode == 0
    assert [e["port"] for e in _entries(reg)] == [3200]


def test_release_without_selector_is_refused(tmp_path: Path) -> None:
    result = _run(tmp_path / "r.json", "release")
    assert result.returncode == 1 and "--port" in result.stderr


def test_scan_parses_ss_lines_and_skips_registered_and_privileged_ports() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("registry", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    raw = "\n".join(
        [
            "State Recv-Q Send-Q Local Address:Port Peer Address:Port Process",
            f'LISTEN 0 4096 127.0.0.1:4999 0.0.0.0:* users:(("dadaia",pid={os.getpid()},fd=4))',
            'LISTEN 0 4096 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))',
            f'LISTEN 0 4096 *:8080 0.0.0.0:* users:(("node",pid={os.getpid()},fd=5))',
            "LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*",
        ]
    )
    doc = {"entries": [{"port": 4999}]}
    findings = module.scan(doc, raw)
    assert [f["port"] for f in findings] == [8080]
    assert findings[0]["lan_exposed"] is True and findings[0]["bind"] == "0.0.0.0"
    assert module.scan(doc, None) == []


def _run_in(cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )


def test_registry_resolves_by_walking_up_to_the_nearest_dadaia_dir(tmp_path: Path) -> None:
    """The ancestor walk lands on the workspace that owns the cwd (review 0.4.7 c5 F4)."""
    workspace = tmp_path / "ws"
    nested = workspace / "repos" / "app" / "src"
    nested.mkdir(parents=True)
    (workspace / ".dadaia").mkdir()
    assert _run_in(nested, "register", "--port", "3100", "--project", "demo").returncode == 0
    reg = workspace / ".dadaia" / "states" / "server_registry.json"
    assert [e["port"] for e in _entries(reg)] == [3100]
    assert not (nested / ".dadaia").exists()


def test_registry_refuses_when_no_dadaia_dir_is_above_the_cwd(tmp_path: Path) -> None:
    """Never a silent registry in a foreign tree: no ``.dadaia/`` above → exit non-zero."""
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    result = _run_in(lonely, "list")
    assert result.returncode != 0
    assert "no .dadaia/ above the current directory" in result.stderr
    assert not any(tmp_path.rglob("server_registry.json"))


def test_entry_with_a_dead_pid_is_stale_before_its_ttl(tmp_path: Path) -> None:
    reg = tmp_path / "r.json"
    probe = subprocess.Popen([sys.executable, "-c", "pass"])
    probe.wait()
    dead_pid = probe.pid
    _run(reg, "register", "--port", "3100", "--project", "demo", "--pid", str(dead_pid))
    listed = json.loads(_run(reg, "list", "--json", "--status", "all").stdout)
    assert listed[0]["status"] == "stale"
    alive = _run(reg, "register", "--port", "3200", "--project", "live", "--pid", str(os.getpid()))
    assert alive.returncode == 0
    listed = json.loads(_run(reg, "list", "--json", "--status", "all").stdout)
    assert {e["port"]: e["status"] for e in listed} == {3200: "active"}
