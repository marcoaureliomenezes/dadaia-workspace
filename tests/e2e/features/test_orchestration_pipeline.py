"""E2E: stage → install → list → run → status → resume → status (runtime=cli)."""

import json
from pathlib import Path

from dadaia_workspace import container
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


def _bootstrap(workspace: Path, ctx: str = "demo-ctx") -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(workspace)
    mgr = FileSystemPublicAssetManager()
    mgr.stage(workspace)
    mgr.install(workspace, target="all")
    (workspace / ".dadaia" / "states" / "primary_context.json").write_text(
        json.dumps({"name": ctx, "repo_slug": ctx, "specs_dir": str(workspace / "specs")})
    )


def test_full_pipeline_run_to_completion(tmp_path: Path) -> None:
    _bootstrap(tmp_path)

    service = container.build_orchestration_service(tmp_path, runtime="cli")

    workflows = service.list_workflows()
    names = {w.name for w in workflows}
    assert {"spec-refinement", "audit-cycle"}.issubset(names)

    manifest, invocations = service.start_run(
        "spec-refinement",
        context="demo-ctx",
        runtime="cli",
        inputs={"context": "demo-ctx", "topic": "smoke"},
    )
    assert len(invocations) == 1
    assert invocations[0].stage_id == "discovery"
    assert Path(invocations[0].invocation_path).exists()
    assert (tmp_path / ".dadaia" / "runs" / manifest.run_id / "manifest.json").exists()
    assert (tmp_path / ".dadaia" / "runs" / manifest.run_id / "events.jsonl").exists()

    # Simulate agent output for discovery (has must_include validation)
    disc_out = tmp_path / invocations[0].expected_output_path
    disc_out.parent.mkdir(parents=True, exist_ok=True)
    disc_out.write_text(
        "<!DOCTYPE html><html><body>"
        "<h2>Findings</h2><p>ok</p>"
        "<h2>Riscos</h2><p>ok</p>"
        "<h2>Decisões necessárias</h2><p>ok</p>"
        "</body></html>"
    )

    # discovery → 5 specialists in one parallel batch (multi-platform-parity-v1 expansion)
    _, parallel = service.resume_run(manifest.run_id)
    assert {inv.stage_id for inv in parallel} == {
        "arch_review",
        "devops_review",
        "qa_review",
        "frontend_review",
        "backend_review",
    }

    # specialists → synthesis (no must_include on specialists)
    _, synth = service.resume_run(manifest.run_id)
    assert {inv.stage_id for inv in synth} == {"synthesis"}

    # Simulate agent output for synthesis (has must_include validation)
    synth_out = tmp_path / synth[0].expected_output_path
    synth_out.parent.mkdir(parents=True, exist_ok=True)
    synth_out.write_text("# SPEC\n\n## Status\nDraft\n\n## Critérios de Aceite\n...\n")

    # synthesis → completed
    final, more = service.resume_run(manifest.run_id)
    assert final.status.value == "completed"
    assert more == ()

    # Re-resuming a completed run is a no-op
    _, none = service.resume_run(manifest.run_id)
    assert none == ()


def test_events_jsonl_records_full_lifecycle(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    service = container.build_orchestration_service(tmp_path, runtime="cli")
    manifest, _ = service.start_run(
        "audit-cycle",
        context="demo-ctx",
        runtime="cli",
        inputs={"context": "demo-ctx", "scope": "full"},
    )
    events_path = tmp_path / ".dadaia" / "runs" / manifest.run_id / "events.jsonl"
    lines = [ln for ln in events_path.read_text().splitlines() if ln.strip()]
    kinds = [json.loads(ln)["kind"] for ln in lines]
    assert kinds[0] == "run_started"
    assert "stage_started" in kinds
    assert "gate_pending" in kinds


def test_status_listing_and_lookup(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    service = container.build_orchestration_service(tmp_path, runtime="cli")
    m1, _ = service.start_run(
        "audit-cycle",
        context="demo-ctx",
        runtime="cli",
        inputs={"context": "demo-ctx", "scope": "full"},
    )
    m2, _ = service.start_run(
        "audit-cycle",
        context="demo-ctx",
        runtime="cli",
        inputs={"context": "demo-ctx", "scope": "partial"},
    )
    ids = {r.run_id for r in service.list_runs()}
    assert {m1.run_id, m2.run_id}.issubset(ids)

    loaded = service.get_run_status(m1.run_id)
    assert loaded.workflow_name == "audit-cycle"
    assert loaded.run_id == m1.run_id
