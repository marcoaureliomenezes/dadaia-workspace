"""THE full development lifecycle, chained: N backlog items → ONE release → implementation.

This is the flow the workspace exists for, and until now nothing asserted it end to end.
Three defects in series made it impossible to drive at all, each invisible to the tests
that covered the steps in isolation because each step reported success:

* ``fake-backlog-canary-fixed-slug-blocks-multi-item-release-flow`` — three authoring runs
  left ONE item, runs 2 and 3 silently overwriting their predecessors.
* ``release-definition-refuses-multiple-backlog-producers`` — with three producers the
  release refused to define at all unless two of the three items were discarded.
* ``release-definition-consumes-nothing-while-scope-declares-items`` — the release then
  completed with an EMPTY ledger while its own scope directive declared three items
  mandatory.

Every one of them is the same class: the run reports success, the effect never happens.
Per-step tests cannot catch that class, because per-step is exactly where it hides. So
this test asserts the COMPOSITION, and asserts it on DISK — never from a run's own
summary, which is the thing that was lying.

``--harness fake`` keeps it deterministic and spends no operator credits. The recipe
statement this mirrors for the consumer-side validator is R-19.

Every verb runs as a real subprocess with :func:`claude_hook_env`, not through the
in-process ``CliRunner``: implementation preflight requires a bound context, and binding
resolves a HARNESS-NATIVE session id that the suite's autouse envelope deliberately
scrubs. In-process the chain would stop at "context is not bound" — a property of the test
envelope, not of the product — so proving this composition needs a session identity a real
harness supplies.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fixtures.harness_env import claude_hook_env

pytestmark = pytest.mark.integration

_RELEASE = "v0.1.0"
_RUN_IDS = ("bl-one", "bl-two", "bl-three")
_CONTEXT = "journey-ctx"
_TIMEOUT = 180


def _dadaia(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a dadaia verb the way a real Claude Code session does."""
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=workspace,
        env=claude_hook_env(workspace, extra={"DADAIA_CONTEXT": _CONTEXT}),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A real workspace with a REAL registered context, cloned from a local bare remote.

    The context is registered rather than faked through ``DADAIA_CONTEXT`` alone because
    ``context bind`` — which implementation preflight requires — resolves the registry, and
    a fixture that skipped it would prove the flow works only in a shape production never
    reaches.
    """
    root = tmp_path / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root)

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, timeout=_TIMEOUT)
    created = _dadaia(root, "context", "create", _CONTEXT, "--repo", _CONTEXT, "--url", str(remote))
    assert created.returncode == 0, created.stdout + created.stderr
    alive = _dadaia(root, "context", "alive", _CONTEXT)
    assert alive.returncode == 0, alive.stdout + alive.stderr
    return root


def _run(workspace: Path, *args: str) -> dict:
    proc = _dadaia(workspace, *args, "--json")
    assert proc.returncode == 0, f"{' '.join(args)} failed:\n{proc.stdout}{proc.stderr}"
    return json.loads(proc.stdout)


def _specs(workspace: Path) -> Path:
    return workspace / "repos" / _CONTEXT / "specs"


def _items(workspace: Path) -> list[Path]:
    return sorted(p for p in (_specs(workspace) / "backlog").glob("*.md") if p.name != "README.md")


def test_three_backlog_items_are_consumed_by_one_release_and_implemented(
    workspace: Path,
) -> None:
    # 1. Three authoring runs → THREE items, each claiming its own anchor. Same anchor on
    #    two items is a fail-closed DIVERGENT_CONFLICT, so one release could never take
    #    the set — the count alone is not enough to prove the flow is open.
    for run_id in _RUN_IDS:
        payload = _run(
            workspace,
            "lifecycle",
            "backlog-definition",
            "--release-id",
            _RELEASE,
            "--run-id",
            run_id,
            "--harness",
            "fake",
            "--demand",
            f"capability from {run_id}",
        )
        assert payload["completed"] is True, payload

    items = _items(workspace)
    assert len(items) == 3, [p.name for p in items]
    anchors = [
        line.split("ref:", 1)[1].strip()
        for item in items
        for line in item.read_text(encoding="utf-8").splitlines()
        if "ref:" in line
    ]
    assert len(set(anchors)) == 3, anchors

    # 2. ONE release, no --backlog-run-id: every completed producer is the scope, and the
    #    release must consume ALL of it. An empty consumed_slugs here is the silent
    #    failure this whole file exists to make impossible.
    release = _run(
        workspace,
        "lifecycle",
        "release-definition",
        "--release-id",
        _RELEASE,
        "--run-id",
        "rel-one",
        "--harness",
        "fake",
    )
    assert release["completed"] is True, release
    assert release["post_step_error"] is None, release["post_step_error"]
    consumed = release["post_step"]["consumed_slugs"]
    assert sorted(consumed) == sorted(p.stem for p in items), consumed
    assert sorted(release["post_step"]["shipped_anchors"]) == sorted(anchors)

    # On disk, not in the summary.
    ledger = workspace / release["post_step"]["ledger"]
    assert ledger.is_file(), f"consumed_backlog ledger missing at {ledger}"

    spec = _specs(workspace) / "releases" / _RELEASE / "SPEC.md"
    spec_text = spec.read_text(encoding="utf-8")
    for slug in consumed:
        assert slug in spec_text, f"{slug} consumed but absent from the SPEC's Consumes line"

    # 3. Implementation reaches closure and its gate removes exactly the consumed set.
    bind = _dadaia(
        workspace, "context", "bind", _CONTEXT, "--mode", "implementation", "--release", _RELEASE
    )
    assert bind.returncode == 0, bind.stdout + bind.stderr

    impl = _run(
        workspace,
        "lifecycle",
        "implementation-reviews",
        "--release-id",
        _RELEASE,
        "--run-id",
        "impl-one",
        "--harness",
        "fake",
    )
    assert impl["completed"] is True, impl
    assert impl["final_phase"] == "closure", impl["final_phase"]
    assert sorted(impl["closure_gate"]["removed"]) == sorted(consumed), impl["closure_gate"]

    # The items left the backlog by being ARCHIVED, never deleted (never-delete law).
    assert _items(workspace) == []
    archived = sorted((_specs(workspace) / "_archive" / _RELEASE / "consumed-backlog").glob("*.md"))
    assert sorted(p.stem for p in archived) == sorted(consumed), [p.name for p in archived]

    # 4. The state the gates ACCEPTED must satisfy the validators (R-13: a gate is a
    #    validator too, and the two must not disagree about the same tree).
    doctor = _dadaia(workspace, "specs", "doctor")
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
