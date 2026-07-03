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
from dataclasses import dataclass
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

    def run(self, request: AgentRunRequest) -> AgentRunResult:  # noqa: ARG002
        return self.result


def _install_fake_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake worker: APPROVED",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/release-definition-step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )

    def fake_factory(
        *,
        context: str,  # noqa: ARG001
        run_cwd: Path,  # noqa: ARG001
        model_by_kind: dict[AgentRuntimeKind, object],  # noqa: ARG001
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
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/phase-step.handoff.json",),
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
        ["lifecycle", "release", "define", "--release-id", _RELEASE, "--json", *args],
    )


def _close(args: list[str]) -> Result:
    return _runner.invoke(
        app,
        ["lifecycle", "close", "--release-id", _RELEASE, "--json", *args],
    )


def _payload(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


# ── A1 — define writes the ledger end-to-end ────────────────────────────────────────


def test_define_writes_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)
    _plant_specs(workspace, consumes=_SLUG)

    result = _define(["--harness", "fake"])
    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    assert payload["completed"] is True

    ledger = workspace / "specs" / "_archive" / _RELEASE / "consumed_backlog.json"
    assert ledger.exists(), f"ledger not written; output={result.output}"
    # The ledger lives under _archive/, NOT the live release dir.
    assert (workspace / "specs" / "releases" / _RELEASE / "consumed_backlog.json").exists() is False

    data = json.loads(ledger.read_text(encoding="utf-8"))
    # The recorded entry is keyed on the verified shipped-anchor set (the item's own anchor).
    serialized = json.dumps(data)
    assert _SLUG in serialized
    assert _REF in serialized

    # The verb surfaces the consumed slug + ledger path in its post-step payload.
    post_step = payload.get("post_step")
    assert isinstance(post_step, dict), payload
    assert _SLUG in json.dumps(post_step)
    assert payload.get("post_step_error") is None


# ── A2 — define -> close removes the item + zero BL-STALE ────────────────────────────


def test_define_close_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)
    _plant_specs(workspace, consumes=_SLUG)

    define_result = _define(["--harness", "fake"])
    assert define_result.exit_code == 0, define_result.output

    _install_approving_phase_runtime(monkeypatch)
    close_result = _close(["--harness", "fake"])
    assert close_result.exit_code == 0, close_result.output

    backlog = workspace / "specs" / "backlog"
    archive = workspace / "specs" / "_archive"
    # The fully-consumed item is gone from the live SET; the archive copy is the survivor.
    assert not (backlog / f"{_SLUG}.md").exists()
    assert (archive / _RELEASE / "consumed-backlog" / f"{_SLUG}.md").exists()

    # backlog doctor reports zero BL-STALE over the post-removal tree (run over the same
    # injected roots the CLI resolves, so no live workspace state leaks into the assertion).
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


# ── A4 boundary — a bad **Consumes:** surfaces as post_step_error ───────────────────


def test_bad_consumes_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)
    # Declare a slug that has no live backlog item file.
    _plant_specs(workspace, consumes="ghost-slug", with_item=True)

    result = _define(["--harness", "fake"])
    payload = _payload(result.output)
    # The definition itself completed; the producer post-step failed loud (no silent skip).
    assert payload["completed"] is True
    error = payload.get("post_step_error")
    assert isinstance(error, str) and "ghost-slug" in error, payload
    # No ledger was written from the failed declaration.
    assert not (workspace / "specs" / "_archive" / _RELEASE / "consumed_backlog.json").exists()
