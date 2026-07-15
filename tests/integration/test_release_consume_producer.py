"""End-to-end producer post-step on ``lifecycle release define`` (v0.1.27, SPEC §3.2/§3.4).

* A1 (``test_define_writes_ledger``) — a real ``release define`` run over a temp workspace
  whose release SPEC carries ``**Consumes:** <slug>`` writes
  ``specs/_archive/<release-id>/consumed_backlog.json`` keyed on the verified shipped-anchor
  set, under ``_archive/`` (not the live release dir).
* A2 (``test_define_close_loop``) — a real define→close cycle removes the fully-consumed
  item from the live SET (archive copy precedes unlink) and leaves ``backlog doctor`` with
  zero BL-STALE.
* A4 boundary (``test_bad_consumes_fails_loud``) — a ``**Consumes:**`` slug that does not
  resolve surfaces as the verb's ``post_step_error`` and writes no ledger.

The release-definition runtime factory is monkeypatched to a kind-reporting fake (mirrors
``tests/integration/cli/test_release_definition_workflow.py``) so the §6.1 sequence walks
deterministically with no live worker; the producer post-step is the unit under test.
All roots live under ``tmp_path`` — the CLI resolves them via ``resolve_workspace_root`` /
``_backlog_context_roots`` after ``monkeypatch.chdir``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

import dadaia_workspace.container as container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_RELEASE = "v0.1.27-test"
_CONTEXT = "dadaia-workspace"
_SLUG = "shipped-feature"
_REF = "pkg/ship.py#shipped"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


@dataclass
class _KindReportingFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        # The structural gate verifies declared refs EXIST and that a create step
        # delivers INSIDE its declared zone (bugs gate-accepts-phantom-artifact-evidence
        # / create-step-gate-accepts-refusal-handoff-as-success): be step-aware and
        # materialize like the production driving fake.
        parts = (request.task_id or "").split(":")
        label = parts[-2] if parts and parts[-1].startswith("attempt-") else parts[-1]
        deliverable = {
            "spec_create": "SPEC.md",
            "plan_create": "PLAN.md",
            "tasks_create": "TASKS.md",
            "close": "CLOSURE.md",
        }.get(label)
        refs = list(self.result.artifact_refs)
        if deliverable is not None:
            zone = Path.cwd() / "repos" / _CONTEXT / "specs"
            prefix = f"repos/{_CONTEXT}/specs" if zone.is_dir() else "specs"
            refs.append(f"{prefix}/releases/{_RELEASE}/{deliverable}")
        for ref in refs:
            target = Path.cwd() / ref
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                content = '{"fake": true}\n'
                if target.name == "PLAN.md":
                    content = (
                        "# PLAN\n\n**Status:** Aprovado\n\n"
                        "## Validation Dependency Table\n\n"
                        "| Workstream | Produces by end | Direct validation | "
                        "Validation dependencies | Deferred integration evidence |\n"
                        "|---|---|---|---|---|\n"
                        "| WS-1 | fixture | focused pytest | None | None |\n"
                    )
                elif target.name == "TASKS.md":
                    content = "# TASKS\n\n**Status:** Aprovado\n\n### [ ] T1 - Verify fixture\n"
                elif target.name == "CLOSURE.md":
                    content = "# CLOSURE\n\n**Status:** Aprovado\n"
                target.write_text(content, encoding="utf-8")
        return replace(self.result, artifact_refs=tuple(refs))


def _install_fake_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake worker: APPROVED",
        artifact_refs=(
            f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/release-definition.step-output.json",
        ),
        structured_output={"verdict": "APPROVED"},
    )

    def fake_factory(
        *,
        context: str,  # noqa: ARG001
        run_cwd: Path,  # noqa: ARG001
        release_id: str | None = None,  # noqa: ARG001
    ) -> object:
        def factory(kind: AgentRuntimeKind) -> _KindReportingFake:
            return _KindReportingFake(kind, approving)

        return factory

    monkeypatch.setattr(container, "_release_definition_runtime_factory", fake_factory)


def _install_approving_phase_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the single-step phase workflow (used by ``close``) accept on ``--harness fake``.

    The default ``build_agent_runtime(FAKE)`` returns a verdict-less no-op result, so a phase
    step BLOCKS (no APPROVED verdict) and the ``close`` post-step never runs. Patch the
    factory to a kind-reporting fake that returns an APPROVED handoff so the closure phase
    step is accepted and ``_apply_closure_removal`` fires — exactly the production loop.
    """
    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake phase worker: APPROVED",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/phase.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )

    def fake_build_agent_runtime(
        kind: AgentRuntimeKind,
        *,
        cwd: Path | None = None,  # noqa: ARG001
        model: object | None = None,  # noqa: ARG001
    ) -> _KindReportingFake:
        return _KindReportingFake(kind, approving)

    monkeypatch.setattr(container, "build_agent_runtime", fake_build_agent_runtime)


def _plant_specs(workspace: Path, *, consumes: str, with_item: bool = True) -> None:
    """Plant a self-hosting specs tree: a release SPEC + (optionally) a live backlog item.

    The tmp workspace has no ``repos/<ctx>/specs``, so ``_backlog_context_roots`` resolves to
    ``workspace/specs`` + ``workspace`` (self-hosting fallback). Plant source for the anchor.
    """
    specs = workspace / "specs"
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    spec_text = f"""\
# SPEC — {_RELEASE}

**Status:** Aprovado
**Release ID:** {_RELEASE}
**Consumes:** {consumes}

body
"""
    (specs / "releases" / _RELEASE / "SPEC.md").write_text(spec_text, encoding="utf-8")
    backlog = specs / "backlog"
    backlog.mkdir(parents=True)
    if with_item:
        item = f"""\
---
name: {_SLUG}
status: candidate
intents:
  - subject: {{ kind: code, ref: "{_REF}" }}
    change: "fully shipped"
---

# {_SLUG}
Body that goes to the archive copy.
"""
        (backlog / f"{_SLUG}.md").write_text(item, encoding="utf-8")
    pkg = workspace / "pkg"
    pkg.mkdir()
    (pkg / "ship.py").write_text("def shipped() -> None:\n    pass\n", encoding="utf-8")


def _define(args: list[str]) -> Result:
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "release-definition",
            "--context",
            _CONTEXT,
            "--release-id",
            _RELEASE,
            "--json",
            *args,
        ],
    )


def _close(args: list[str]) -> Result:
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--context",
            _CONTEXT,
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--json",
            *args,
        ],
    )


def _payload(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


# ── A1+A2+A4 — define writes the ledger, then define -> close removes the item + zero
# BL-STALE (A1's ledger-write assertion folds in mid-loop, before close runs), plus the
# A4 boundary: a bad **Consumes:** surfaces as post_step_error (own workspace) ────────


def test_define_writes_ledger_close_removes_item_zero_stale_and_bad_consumes_fails_loud(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)
    _plant_specs(workspace, consumes=_SLUG)

    define_result = _define(["--harness", "fake"])
    assert define_result.exit_code == 0, define_result.output
    payload = _payload(define_result.output)
    assert payload["completed"] is True

    # A1 — the ledger is written end-to-end by `define`, under _archive/ (not the live
    # release dir), keyed on the verified shipped-anchor set.
    ledger = workspace / "specs" / "_archive" / _RELEASE / "consumed_backlog.json"
    assert ledger.exists(), f"ledger not written; output={define_result.output}"
    assert (workspace / "specs" / "releases" / _RELEASE / "consumed_backlog.json").exists() is False

    data = json.loads(ledger.read_text(encoding="utf-8"))
    serialized = json.dumps(data)
    assert _SLUG in serialized
    assert _REF in serialized

    post_step = payload.get("post_step")
    assert isinstance(post_step, dict), payload
    assert _SLUG in json.dumps(post_step)
    assert payload.get("post_step_error") is None

    # A2 — close then removes the fully-consumed item from the live SET.
    _install_approving_phase_runtime(monkeypatch)
    close_result = _close(["--harness", "fake"])
    assert close_result.exit_code == 0, close_result.output

    backlog = workspace / "specs" / "backlog"
    archive = workspace / "specs" / "_archive"
    assert not (backlog / f"{_SLUG}.md").exists()
    assert (archive / _RELEASE / "consumed-backlog" / f"{_SLUG}.md").exists()

    from dadaia_workspace.features.backlog.doctor import BacklogDoctorCode, run_backlog_doctor

    specs = workspace / "specs"
    findings = run_backlog_doctor(
        specs_dir=specs,
        source_root=workspace,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=workspace / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        archive_root=archive,
        cli_anchors=frozenset(),
    )
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert stale == [], f"unexpected BL-STALE: {[f.to_dict() for f in stale]}"

    # A4 boundary: a bad **Consumes:** surfaces as post_step_error, own workspace.
    bad_ws_root = tmp_path.parent / (tmp_path.name + "-bad-consumes")
    bad_workspace = _init_workspace(bad_ws_root)
    monkeypatch.chdir(bad_workspace)
    _install_fake_factory(monkeypatch)
    # Declare a slug that has no live backlog item file.
    _plant_specs(bad_workspace, consumes="ghost-slug", with_item=True)

    bad_result = _define(["--harness", "fake"])
    bad_payload = _payload(bad_result.output)
    # The definition itself completed; the producer post-step failed loud (no silent skip).
    assert bad_payload["completed"] is True
    error = bad_payload.get("post_step_error")
    assert isinstance(error, str) and "ghost-slug" in error, bad_payload
    # No ledger was written from the failed declaration.
    assert not (bad_workspace / "specs" / "_archive" / _RELEASE / "consumed_backlog.json").exists()
