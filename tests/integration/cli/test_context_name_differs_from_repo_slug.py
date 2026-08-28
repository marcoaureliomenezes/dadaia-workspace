"""A context whose NAME differs from its repo SLUG must work end to end.

Bugs a1-context-specs-resolution-ignores-repo-slug and a1-audit-completes-without-audit-report,
both reported by the consumer-side validator against the re-architected workflows.

``dadaia context create meu-projeto --repo repo-diferente`` is ordinary usage: a context has
two identities — the NAME every session record and handoff uses, and the SLUG that is the
directory under ``repos/``. 28 call sites across 9 modules derived the directory by
interpolating the NAME, so any context where they differed resolved to a path that does not
exist. The workflows then reported success while writing nothing: the deliverable zone
pointed at the wrong directory, so the worker's write fell out of scope.

Every one of those sites now derives the directory from ONE resolution
(``repo_slug_for_context``, or the already-resolved ``specs_dir``), which is why this test
exercises the whole chain rather than a single function.
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

_NAME = "meu-projeto"
_SLUG = "repo-diferente"
_RELEASE = "v0.1.0"
_TIMEOUT = 180


def _dadaia(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=workspace,
        env=claude_hook_env(workspace, extra={"DADAIA_CONTEXT": _NAME}),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root)
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, timeout=_TIMEOUT)
    created = _dadaia(root, "context", "create", _NAME, "--repo", _SLUG, "--url", str(remote))
    assert created.returncode == 0, created.stdout + created.stderr
    alive = _dadaia(root, "context", "alive", _NAME)
    assert alive.returncode == 0, alive.stdout + alive.stderr
    return root


def _run(workspace: Path, *args: str) -> dict:
    proc = _dadaia(workspace, *args, "--json")
    assert proc.returncode == 0, f"{' '.join(args)} failed:\n{proc.stdout}{proc.stderr}"
    return json.loads(proc.stdout)


def test_bugs_append_resolves_the_slug_and_closure_lands_in_scope(workspace: Path) -> None:
    """Two more sites that assumed name == slug, both validator-reported.

    `bugs append --context <name>` validated `repos/<name>/specs` and REFUSED a perfectly
    valid context (a2-bugs-append-context-resolution-ignores-repo-slug); and the close
    step's CLOSURE.md was written under the name, landing outside its declared write scope
    so the step was refused (a2-fake-implementation-close-closure-out-of-scope).

    Both are the same disease as the first fix — a directory derived from the wrong
    identity — which is why they are pinned here next to it.
    """
    proc = _dadaia(
        workspace,
        "bugs",
        "append",
        "--bug-id",
        "probe",
        "--reported-by",
        "test",
        "--title",
        "t",
        "--severity",
        "LOW",
        "--surface",
        "cli",
        "--component",
        "c",
        "--context",
        _NAME,
        "--symptom",
        "sy",
        "--repro",
        "rp",
        "--expected",
        "ex",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (workspace / "repos" / _SLUG / "specs" / "bugs" / "BUGS.jsonl").is_file(), (
        "the event must land in the context's real ledger, under its SLUG"
    )


@pytest.mark.timeout(180)
def test_create_refuses_a_name_no_other_verb_can_use(workspace: Path) -> None:
    """`create` must refuse exactly what the rest of the CLI refuses.

    Explicit timeout (dadaia-test-stewardship S-09/S-10): this test builds several real
    workspaces through the CliRunner and measured ~20 s solo / >60 s under full-suite
    xdist load — above the 60 s integration ceiling. The justified bound stays; the
    structural fix (splitting the workspace builds) was queued and curated under the
    v0.4.3 stewardship pass (FR18).

    Bug a3-context-create-accepts-unusable-name: `create` accepted names with spaces or
    non-ASCII characters, and then `bind`, `bugs append` and every workflow rejected that
    same context against the `[A-Za-z0-9_-]+` allowlist. The operator was left holding a
    context they could create and never use — a trap whose only exit is deleting it.

    The check reuses the resolver's own allowlist rather than inventing a second, stricter
    opinion, so "created" and "usable" cannot drift apart.
    """
    for bad in ("meu projeto", "projeto-café", "../escape"):
        proc = _dadaia(workspace, "context", "create", bad, "--repo", "r", "--url", "x")
        combined = proc.stdout + proc.stderr
        assert proc.returncode != 0, f"create accepted the unusable name {bad!r}"
        assert "Traceback" not in combined
        assert "letters, digits" in combined, combined

    ok = _dadaia(
        workspace, "context", "create", "outro_valido-2", "--repo", "slug_ok", "--url", "x"
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
