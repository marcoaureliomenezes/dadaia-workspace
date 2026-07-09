"""T-69-06 (FR3, bug ``lifecycle-preflight-unusable-resolved-runtime-inputs``, MEDIUM).

``LifecyclePreflightInput`` (``service.py:119-134``) has ZERO production producers — only
``test_preflight_service.py`` hand-feeds its state classes. RED: the container builder
``build_lifecycle_preflight_input`` does not exist yet, so every test here fails with
``AttributeError`` (no such attribute on ``container``) / ``ImportError``.

Each test below drives ONE producer's real behavior against a hand-assembled ``tmp_path``
workspace (no fakes-of-the-thing-under-test): active-release from a real ACTIVE.md, git
state from a real git repo, specs-doctor from a real specs tree, lease/mode from real
session-identity + lease records, hygiene from the real ``LifecycleHygieneService``, and
the composed ``expected_phase``/``required_mode`` policy from ACTIVE.md's phase.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


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
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
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
    (repo / "specs" / "releases" / "v0.1.99" / "SPEC.md").write_text(
        "# SPEC\n\n> **Status:** Aprovado\n", encoding="utf-8"
    )
    (repo / "specs" / "releases" / "v0.1.99" / "PLAN.md").write_text(
        "# PLAN\n\n> **Status:** Aprovado\n", encoding="utf-8"
    )
    (repo / "specs" / "releases" / "v0.1.99" / "TASKS.md").write_text(
        "# TASKS\n\n> **Status:** Aprovado\n", encoding="utf-8"
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


def test_build_lifecycle_preflight_input_exists_and_returns_typed_input(
    tmp_path: Path,
) -> None:
    from dadaia_workspace import container

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    assert data.context == "proj"
    assert data.release_id == "v0.1.99"


def test_active_release_producer_reads_real_active_md(tmp_path: Path) -> None:
    from dadaia_workspace import container

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    assert data.active_release.release_id == "v0.1.99"
    assert data.active_release.phase is not None
    assert data.active_release.phase.strip().upper() == "IMPLEMENTATION"


def test_git_producer_reads_real_dirty_state(tmp_path: Path) -> None:
    from dadaia_workspace import container

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    # A freshly-committed repo is clean.
    assert data.git.dirty_paths == ()

    # Dirty it and re-build: the producer must reflect the REAL git status.
    (ws / "repos" / "proj" / "dirty.txt").write_text("x", encoding="utf-8")
    dirty_data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")
    assert dirty_data.git.dirty_paths != ()


def test_specs_doctor_producer_runs_real_doctor(tmp_path: Path) -> None:
    from dadaia_workspace import container

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    assert isinstance(data.specs_doctor.ok, bool)


def test_lease_mode_producer_reads_real_session_identity(tmp_path: Path) -> None:
    from dadaia_workspace import container

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    # No bind yet ⇒ no live foreign holder, mode resolves to the unbound default.
    assert data.lease.live_foreign_holder is False


def test_hygiene_producer_reads_real_lifecycle_hygiene_service(tmp_path: Path) -> None:
    from dadaia_workspace import container

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    assert data.hygiene.cleanup_candidate_count == 0


def test_binding_producer_reads_incumbent_pointer_when_bound(tmp_path: Path) -> None:
    from dadaia_workspace import container
    from dadaia_workspace.features.spec_context import session_identity

    ws = _mk_workspace(tmp_path)
    session_identity.write_session(
        ws,
        "sess-bound-1",
        {
            "session_id": "sess-bound-1",
            "context": "proj",
            "mode": "BOUND_IMPLEMENTATION",
            "release": "v0.1.99",
        },
    )
    session_identity.set_incumbent(ws, "proj", "sess-bound-1")

    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    assert data.binding is not None
    assert data.binding.context == "proj"
    assert data.binding.release_id == "v0.1.99"
    assert data.binding.mode.upper() == "BOUND_IMPLEMENTATION"


def test_expected_phase_and_required_mode_policy_derived_from_active_md(
    tmp_path: Path,
) -> None:
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase

    ws = _mk_workspace(tmp_path)
    data = container.build_lifecycle_preflight_input(ws, context="proj", release_id="v0.1.99")

    assert data.expected_phase == LifecyclePhase.IMPLEMENTATION
    assert data.required_mode.strip().lower() == "implementation"
