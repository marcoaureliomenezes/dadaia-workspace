"""The chain an operator actually runs: demand → backlog → approved release → closure.

This is the journey the product exists for, and until now NOTHING covered it end to end.
``test_backlog_define_e2e`` stops after ``backlog-definition`` exits 0 and a file appears.
``test_lifecycle_journey_e2e``, despite its name, covers create/alive/bind/inject/gate and
never touches a workflow. So every handoff BETWEEN the workflows — the release consuming
the authored pick, the approval statuses, the bind that implementation requires, reaching
closure — was unproven by the suite while being exactly what the consumer-side validator
kept breaking on.

Deterministic ``--harness fake``, on purpose: this pins the PYTHON contract — step order,
gate transitions, the artifacts that land on disk, and the data flowing across workflow
boundaries. What a live model writes is not something a test can pin, and pretending
otherwise is how a green suite coexists with a broken product; that half belongs to the
consumer-side validator. What this test guarantees is that when the model behaves, the
machinery around it carries the work all the way through.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_runner = CliRunner()

_CTX = "chainctx"
_REPO = "chainrepo"
_RELEASE = "v0.1.0"


def _cli(*args: str):
    result = _runner.invoke(app, list(args))
    return result


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    repo = tmp_path / "repos" / _REPO
    repo.mkdir(parents=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "e2e@test"],
        ["config", "user.name", "e2e"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    # One stable session identity for the whole chain: `context bind` records the mode
    # against the CALLER's session, and implementation refuses an unbound one. Without
    # pinning it, each in-process invocation would resolve a different identity and the
    # bind would never be seen by the next step.
    monkeypatch.setenv("DADAIA_SESSION_ID", "e2e-chain-session")

    created = _cli("context", "create", _CTX, "--repo", _REPO, "--url", str(repo))
    assert created.exit_code == 0, created.output
    alive = _cli("context", "alive", _CTX)
    assert alive.exit_code == 0, alive.output
    return tmp_path


def _specs(workspace: Path) -> Path:
    return workspace / "repos" / _REPO / "specs"


def test_a_demand_travels_all_the_way_to_closure(workspace: Path) -> None:
    """Every handoff between the four workflows, asserted on real on-disk artifacts."""
    # 1 ── backlog-definition materialises a real item.
    backlog = _cli(
        "lifecycle", "backlog-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "bd1",
        "--harness", "fake", "--demand", "add an example verb",
    )  # fmt: skip
    assert backlog.exit_code == 0, backlog.output
    items = [p for p in (_specs(workspace) / "backlog").glob("*.md") if p.stem != "README"]
    assert items, "backlog-definition completed without leaving an item on disk"
    authored = items[0].stem

    # 2 ── release-definition must CONSUME that exact pick, not merely run.
    release = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd1",
        "--harness", "fake", "--backlog-run-id", "bd1",
    )  # fmt: skip
    assert release.exit_code == 0, release.output
    assert authored in release.output, (
        f"the release did not consume the authored pick {authored!r} — the handoff "
        f"between the two workflows is the thing that keeps breaking. Output:\n{release.output}"
    )

    ledger = _specs(workspace) / "_archive" / _RELEASE / "consumed_backlog.json"
    assert ledger.is_file(), "the consumed-backlog ledger is the durable proof of the handoff"
    recorded = json.loads(ledger.read_text(encoding="utf-8"))
    assert recorded["release"] == _RELEASE
    assert authored in [entry["slug"] for entry in recorded["consumed"]], recorded

    # 3 ── the definition artifacts exist AND carry the canonical approval token.
    for name in ("SPEC", "PLAN", "TASKS"):
        artifact = _specs(workspace) / "releases" / _RELEASE / f"{name}.md"
        assert artifact.is_file(), f"{name}.md was never written"
        assert "**Status:** Aprovado" in artifact.read_text(encoding="utf-8"), (
            f"{name}.md exists but was never approved — an unapproved artifact blocks "
            "implementation, so 'the workflow ran' is not the same as 'the release is usable'"
        )

    # 4 ── implementation REFUSES without a bind, and says so. Pinned because a silent
    #      or cryptic refusal here is what stalls a live run mid-chain.
    unbound = _cli(
        "lifecycle", "implementation-reviews",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "ir0", "--harness", "fake",
    )  # fmt: skip
    assert unbound.exit_code != 0
    assert "not bound" in unbound.output.lower(), unbound.output

    # 5 ── bound, the same command carries the release to closure.
    bound = _cli("context", "bind", _CTX, "--mode", "implementation", "--release", _RELEASE)
    assert bound.exit_code == 0, bound.output
    implement = _cli(
        "lifecycle", "implementation-reviews",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "ir1", "--harness", "fake",
    )  # fmt: skip
    assert implement.exit_code == 0, implement.output
    assert "phase=closure" in implement.output, (
        f"the chain stopped before closure; output was:\n{implement.output}"
    )


def test_the_release_refuses_a_pick_that_was_never_authored(workspace: Path) -> None:
    """The negative half: consuming is a real check, not a label copied forward.

    Without this, the assertion above passes for a release-definition that ignores its
    input entirely and writes the same artifacts regardless.
    """
    result = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd-ghost",
        "--harness", "fake", "--backlog-run-id", "never-ran",
    )  # fmt: skip
    assert result.exit_code != 0, result.output
    assert "never-ran" in result.output
