"""v0.1.77 T-1 (RED) — executed-path bind-visibility probe (SPEC FR1/FR3).

Companion to the structural dynamic walk in
``tests/contract/test_bind_resolution_seam_dynamic_walk.py``. That module proves the
STRUCTURE (no hardcoded default, every classified-resolver-driven param AST-reaches the
seam); this module proves the RUNTIME BEHAVIOR for a representative read-only verb per
command module, in a hermetic tmp workspace with TWO live contexts, using the REAL Typer
CLI (``CliRunner`` against ``cli.main.app`` — never calling the resolver functions
directly): after a bare ``dadaia context bind ctx-b`` (no ``DADAIA_SESSION_ID`` exported —
the normal harness-shell shape), every probed verb resolves ``ctx-b``, never ``ctx-a``
and never a hardcoded/no-op fallback.

Probed verbs (one per command module, matching the SPEC's example list):
  - ``context show`` (no positional name) — context.py
  - ``bugs status`` (no ``--specs-dir``) — bugs.py
  - ``specs doctor --json`` (no ``--specs-dir``/``--context``) — specs.py
  - ``lifecycle preflight`` (no ``--context``) — lifecycle.py (the read-only probe verb;
    ``lifecycle status``'s ``--context`` is a documented optional RUN FILTER, not a
    resolution input — see the dynamic-walk module's classifier docstring — so it is not
    a valid bind-visibility probe target).

RED at HEAD (T-1): ``bugs status`` and ``specs doctor`` already pass (they consume the
pre-existing partial seam, ``resolve_specs_dir_for_cli``); ``lifecycle preflight``
FAILS — its ``--context`` defaults to the hardcoded literal ``"dadaia-workspace"`` and is
passed as if explicit, so the bind is never consulted (this is the exact FR1 defect this
release fixes). ``context show`` no-arg already passes (v0.1.71/v0.1.76 fixed its private
incumbent-pointer algorithm) — kept here as a regression-guard once it, too, formally
folds into the seam in T-2.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = [pytest.mark.integration]

_runner = CliRunner()
_CTX_A = "seam-ctx-a"
_CTX_B = "seam-ctx-b"


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=t1@test", "-c", "user.name=t1", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr or proc.stdout}"


def _seed_specs_tree(repo: Path, release: str) -> None:
    (repo / "specs" / "releases" / release).mkdir(parents=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (repo / "specs" / "releases" / release / name).write_text(
            f"# {name}\n\n> **Status:** Aprovado\n", encoding="utf-8"
        )
    (repo / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {release}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "tech-stack.md").write_text("# tech\n", encoding="utf-8")
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "specs" / "backlog").mkdir(parents=True)


def _make_two_context_workspace(root: Path) -> Path:
    ws = root / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _CTX_A,
                        "state": "alive",
                        "repo_slug": _CTX_A,
                        "repo_url": "https://example.invalid/seam-ctx-a.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    },
                    {
                        "name": _CTX_B,
                        "state": "alive",
                        "repo_slug": _CTX_B,
                        "repo_url": "https://example.invalid/seam-ctx-b.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    for ctx in (_CTX_A, _CTX_B):
        repo = ws / "repos" / ctx
        _seed_specs_tree(repo, "v0.9.9")
        _git(repo, "-c", "init.defaultBranch=main", "init")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", f"seed: {ctx} specs tree")
    return ws


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def two_ctx_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = _make_two_context_workspace(tmp_path)
    monkeypatch.chdir(ws)
    bind_result = _runner.invoke(
        app,
        ["context", "bind", _CTX_B, "--mode", "implementation", "--release", "v0.9.9"],
    )
    assert bind_result.exit_code == 0, bind_result.output
    return ws


def test_context_show_noarg_resolves_bound_context(two_ctx_workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "show", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["name"] == _CTX_B, payload


def test_bugs_status_resolves_bound_context(two_ctx_workspace: Path) -> None:
    # Seed one bug per context via an explicit --specs-dir (setup only — never through the
    # seam), then assert the unset-`--specs-dir` `bugs status` call surfaces ONLY ctx-b's.
    specs_a = two_ctx_workspace / "repos" / _CTX_A / "specs"
    specs_b = two_ctx_workspace / "repos" / _CTX_B / "specs"
    for specs_dir, bug_id, meta_ctx in (
        (specs_a, "bug-in-ctx-a", _CTX_A),
        (specs_b, "bug-in-ctx-b", _CTX_B),
    ):
        append_result = _runner.invoke(
            app,
            [
                "bugs",
                "append",
                "--bug-id",
                bug_id,
                "--event",
                "reported",
                "--title",
                "seam probe bug",
                "--severity",
                "LOW",
                "--surface",
                "test",
                "--component",
                "test",
                "--context",
                meta_ctx,
                "--symptom",
                "n/a",
                "--repro",
                "n/a",
                "--expected",
                "n/a",
                "--notes",
                "n/a",
                "--specs-dir",
                str(specs_dir),
            ],
        )
        assert append_result.exit_code == 0, append_result.output

    status_result = _runner.invoke(app, ["bugs", "status"])
    assert status_result.exit_code == 0, status_result.output
    assert "bug-in-ctx-b" in status_result.output
    assert "bug-in-ctx-a" not in status_result.output


def test_specs_doctor_resolves_bound_context(two_ctx_workspace: Path) -> None:
    result = _runner.invoke(app, ["specs", "doctor", "--json"])
    assert result.exit_code in (0, 1), result.output
    payload = json.loads(result.output)
    resolved = Path(payload["specs_dir"])
    assert resolved == (two_ctx_workspace / "repos" / _CTX_B / "specs").resolve(), payload


def test_lifecycle_preflight_resolves_bound_context(two_ctx_workspace: Path) -> None:
    """RED at HEAD (T-1): ``--context`` defaults to the hardcoded literal
    ``"dadaia-workspace"`` (never ctx-b), so ``blocked.detail.context`` reports the wrong
    (nonexistent) context — the exact FR1 defect."""
    result = _runner.invoke(app, ["lifecycle", "preflight", "--json"])
    assert "No such option" not in result.output
    payload = json.loads(result.output)
    assert payload["status"] in ("OK", "BLOCKED")
    if payload["status"] == "BLOCKED":
        detail = payload["blocked"].get("detail", {})
        assert detail.get("context") == _CTX_B, (
            f"lifecycle preflight with no --context must resolve the BOUND context "
            f"({_CTX_B!r}) through the seam, not the hardcoded literal default; got: {payload}"
        )
