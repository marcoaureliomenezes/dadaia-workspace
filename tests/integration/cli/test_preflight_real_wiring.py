"""T-69-06/T-69-07 (FR3, bug ``lifecycle-preflight-unusable-resolved-runtime-inputs``, MEDIUM).

Pre-fix (T-69-06 RED): the ``preflight`` CLI command called
``service.unresolved_runtime_preflight()`` — the deterministic, always-BLOCKED stub — and
NEVER called ``service.preflight(data)``. The emitted reason was exactly the generic stub
string forbidden by AC3.1, and a spy on ``LifecyclePreflightService.preflight`` proved it
was unreached.

Post-fix (T-69-07 GREEN, this module's final form — the RED assertions are converted in
place, matching the T-69-04 pattern): the CLI wires the real
``build_lifecycle_preflight_input`` + ``service.preflight(data)`` path; the stub method
itself is DELETED from ``service.py`` (retired, not merely unreached — the only production
caller was ``lifecycle.py``). A dirty/unbound checkout correctly BLOCKS with a SPECIFIC
reason and a non-null ``operator_command`` (AC3.1) — never the generic stub string; a spy
on ``service.preflight`` confirms it IS the code path taken (AC3.2).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.lifecycle import service as service_module

_runner = CliRunner()


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=t@test", "-c", "user.name=t", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr or proc.stdout}"


def _mk_workspace(tmp_path: Path, *, ctx: str = "proj") -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": ctx,
                        "state": "alive",
                        "repo_slug": ctx,
                        "repo_url": "https://example.invalid/proj.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    repo = ws / "repos" / ctx
    (repo / "specs" / "releases" / "v0.1.99").mkdir(parents=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (repo / "specs" / "releases" / "v0.1.99" / name).write_text(
            f"# {name}\n\n> **Status:** Aprovado\n", encoding="utf-8"
        )
    (repo / "specs" / "releases" / "ACTIVE.md").write_text(
        "release: v0.1.99\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "tech-stack.md").write_text("# tech\n", encoding="utf-8")
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "specs" / "backlog").mkdir(parents=True)
    _git(repo, "-c", "init.defaultBranch=main", "init")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed")
    return ws


def test_preflight_never_emits_generic_unresolved_stub_reason_ac31(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3.1: an unbound checkout blocks with a SPECIFIC reason — never the generic stub."""
    ws = _mk_workspace(tmp_path)
    monkeypatch.chdir(ws)

    result = _runner.invoke(
        app,
        ["lifecycle", "preflight", "--context", "proj", "--release-id", "v0.1.99", "--json"],
    )

    payload = json.loads(result.output)
    assert payload["message"] != "lifecycle preflight requires resolved runtime inputs"
    assert payload["blocked"]["reason"] != "lifecycle preflight requires resolved runtime inputs"
    # AC3.1: a real blocked path carries a non-null operator_command for the common
    # (unbound) first-blocking case.
    assert payload["blocked"]["operator_command"] is not None


def test_preflight_calls_real_service_preflight_not_stub_ac32(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3.2: a spy on service.preflight confirms it IS invoked (the stub is retired)."""
    ws = _mk_workspace(tmp_path)
    monkeypatch.chdir(ws)

    calls: list[object] = []
    original = service_module.LifecyclePreflightService.preflight

    def _spy(self: object, data: object) -> object:
        calls.append(data)
        return original(self, data)  # type: ignore[arg-type]

    monkeypatch.setattr(service_module.LifecyclePreflightService, "preflight", _spy)

    _runner.invoke(
        app,
        ["lifecycle", "preflight", "--context", "proj", "--release-id", "v0.1.99", "--json"],
    )

    assert len(calls) == 1, "service.preflight(data) must be called exactly once"
    assert not hasattr(service_module.LifecyclePreflightService, "unresolved_runtime_preflight"), (
        "the unresolved_runtime_preflight stub must be RETIRED (deleted), not merely unused"
    )
