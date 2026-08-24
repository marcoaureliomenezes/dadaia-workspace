"""FR19 (v0.4.4, T-044-30) A19.2 — one place of control: ``specs doctor``, ``backlog
doctor`` and the SDD gate see exactly ONE ``specs/`` tree per context — the main repo's.

Intent: CONTRACT — A19.2

G13 (v0.4.4 grill ADR, ratified): a Spec Context's associated repos are cloned clean and
their OWN ``specs/`` (if any) are **ignored** by the spec context. This suite builds the
adversarial fixture the acceptance criterion calls for: the associated repo carries its
OWN, git-committed ``specs/`` tree, DELIBERATELY diverging from the main repo's (a
different release name, a different phase, and a backlog schema violation under a
distinctive slug) — so a leak is unambiguous the moment any of the three consumers
below reads so much as one byte of it.

Extends T-044-27's A16.4 resolution-walk coverage
(``tests/unit/core/test_specs_resolver_associated_repo_walk.py`` — which already proves
``core.specs_resolver.resolve_specs_dir`` lands on the main repo's ``specs/`` from a cwd
inside the associated repo) up to the three real consumers that sit on top of that
resolver: the ``specs doctor`` / ``backlog doctor`` CLI verbs (via the real Typer app,
the same convention as
``tests/integration/cli/test_bind_resolution_seam_executed_path.py``) and the
``sdd_gate`` PreToolUse hook (via ``run_hook_subprocess``, the same convention as
``tests/unit/hooks/test_sdd_gate.py``). Fixture SHAPE (git-committed repos, same
slug/name identifiers) is reused from T-044-27's suite locally, not shared as a fixture
module — the established convention for this feature.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = [pytest.mark.integration]

_runner = CliRunner()

_MAIN_SLUG = "main-repo"
_MAIN_NAME = "proj"
_ASSOC_SLUG = "assoc-repo"

#: Content unique to the associated repo's OWN specs tree — must never surface in any
#: of the three consumers' output when they operate on the MAIN-resolved tree.
_ASSOC_RELEASE = "assoc-fake-release"
_ASSOC_PHASE = "DEFINITION"
_ASSOC_BACKLOG_SLUG = "assoc-only-broken-item"
_ASSOC_MEMORY_MARKER = "ASSOC-ONLY-MARKER"

_MAIN_RELEASE = "v9.9.9"
_MAIN_PHASE = "IMPLEMENTATION"


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=t@test", "-c", "user.name=t", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr or proc.stdout}"


def _seed_main_repo(repo: Path) -> None:
    """A minimal, clean SDD tree for the MAIN repo — a real release + empty backlog."""
    release_dir = repo / "specs" / "releases" / _MAIN_RELEASE
    release_dir.mkdir(parents=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (release_dir / name).write_text(f"# {name}\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (repo / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {_MAIN_RELEASE}\nphase: {_MAIN_PHASE}\n", encoding="utf-8"
    )
    mem = repo / "specs" / "memory" / "product"
    mem.mkdir(parents=True)
    (repo / "specs" / "memory" / "tech-stack.md").write_text("# tech\nmain\n", encoding="utf-8")
    (mem / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    # A2.8 (backlog doctor): an empty backlog/ dir with NO BACKLOG.md is a clean no-op.
    (repo / "specs" / "backlog").mkdir(parents=True)
    _git(repo, "-c", "init.defaultBranch=main", "init")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed: main repo's specs tree")


def _seed_associated_repo(repo: Path) -> None:
    """The associated repo's OWN, DELIBERATELY DIVERGENT specs/ tree — committed to its
    own git history, exactly as A16.3 proves a real ``alive()`` clone would leave it."""
    (repo / "specs" / "releases").mkdir(parents=True)
    (repo / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {_ASSOC_RELEASE}\nphase: {_ASSOC_PHASE}\n", encoding="utf-8"
    )
    (repo / "specs" / "memory").mkdir(parents=True)
    (repo / "specs" / "memory" / "tech-stack.md").write_text(
        f"# the associated repo's OWN tech stack\n{_ASSOC_MEMORY_MARKER}\n", encoding="utf-8"
    )
    (repo / "specs" / "backlog").mkdir(parents=True)
    (repo / "specs" / "backlog" / "BACKLOG.md").write_text(
        "## ACTIVE\n\n"
        f"### {_ASSOC_BACKLOG_SLUG}\n"
        "- **Title:** Broken on purpose\n"
        "- **Opened:** 2026-08-23\n"
        "- **Description:** missing Status and Provenance — a BL-SCHEMA violation.\n\n"
        "## LEDGER\n",
        encoding="utf-8",
    )
    _git(repo, "-c", "init.defaultBranch=main", "init")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed: the associated repo's own (divergent) specs tree")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "3",
                "contexts": [
                    {
                        "name": _MAIN_NAME,
                        "repo_slug": _MAIN_SLUG,
                        "state": "alive",
                        "repo_url": "https://example.invalid/main-repo.git",
                        "created_at": "2026-08-23T00:00:00+00:00",
                        "alive_since": "2026-08-23T00:00:00+00:00",
                        "associated_repos": [
                            {"slug": _ASSOC_SLUG, "url": "https://example.invalid/assoc.git"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _seed_main_repo(ws / "repos" / _MAIN_SLUG)
    _seed_associated_repo(ws / "repos" / _ASSOC_SLUG)
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


# --------------------------------------------------------------------------- #
# `specs doctor` — resolves the main repo's specs/ tree from inside the associated repo
# --------------------------------------------------------------------------- #


def test_specs_doctor_from_inside_associated_repo_resolves_main_specs_tree(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(workspace / "repos" / _ASSOC_SLUG)

    result = _runner.invoke(app, ["specs", "doctor", "--json"])

    assert result.exit_code in (0, 1), result.output
    payload = json.loads(result.output)
    assert Path(payload["specs_dir"]) == (workspace / "repos" / _MAIN_SLUG / "specs").resolve()
    # Never a byte of the associated repo's own content in the doctor's own output.
    assert _ASSOC_RELEASE not in result.output
    assert _ASSOC_MEMORY_MARKER not in result.output


# --------------------------------------------------------------------------- #
# `backlog doctor` — same seam, same resolution; the assoc repo's BL-SCHEMA violation
# must never be evaluated, let alone reported.
# --------------------------------------------------------------------------- #


def test_backlog_doctor_from_inside_associated_repo_never_sees_the_associated_backlog(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(workspace / "repos" / _ASSOC_SLUG)

    result = _runner.invoke(app, ["backlog", "doctor"])

    # The MAIN repo's backlog/ has no BACKLOG.md at all (A2.8: absent -> clean, exit 0).
    # If this had instead resolved to the associated repo's own (broken) BACKLOG.md, the
    # BL-SCHEMA violation would fail the command (exit 1) and name the broken slug.
    assert result.exit_code == 0, result.output
    assert "clean" in result.output
    assert _ASSOC_BACKLOG_SLUG not in result.output


# --------------------------------------------------------------------------- #
# SDD gate — the phase decision for a write INSIDE the associated repo's own
# specs/memory/ still reads the MAIN repo's ACTIVE.md phase, never the associated
# repo's own (divergent) one.
# --------------------------------------------------------------------------- #


def _run_gate(
    ws: Path, payload: dict[str, object], *, session_id: str = "gate-sess"
) -> dict[str, object] | None:
    env = claude_hook_env(ws, session_id=session_id)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    full_payload = {**payload, "session_id": session_id}
    result = run_hook_subprocess("sdd_gate", full_payload, env, cwd=ws / "repos" / _ASSOC_SLUG)
    assert result.returncode == 0, result.stderr
    return result.block_envelope()


def test_gate_memory_write_inside_associated_repo_is_governed_by_the_main_repos_phase(
    workspace: Path,
) -> None:
    """The associated repo's own ``specs/releases/ACTIVE.md`` claims phase DEFINITION
    (which would ALLOW a memory write); the MAIN repo's real phase is IMPLEMENTATION
    (which BLOCKs one). A write physically inside ``repos/assoc-repo/specs/memory/``
    must be BLOCKed on the MAIN's phase — proving the gate never reads the associated
    repo's own ACTIVE.md."""
    target = workspace / "repos" / _ASSOC_SLUG / "specs" / "memory" / "leak-probe.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    block = _run_gate(workspace, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})

    assert block is not None, (
        "expected RULE A to block — the assoc repo's own DEFINITION phase must never leak in"
    )
    assert "RULE A" in block["reason"]
    assert f"current phase={_MAIN_PHASE}" in block["reason"]
    # The RULE A message text always NAMES "DEFINITION" (the phases memory writes ARE
    # allowed in) — the leak this test guards against is the *observed* phase, not that
    # substring, hence the exact "current phase=<value>" check above and this one.
    assert f"current phase={_ASSOC_PHASE}" not in block["reason"]


def test_gate_mutating_write_inside_associated_repo_attributes_presence_to_the_owning_context(
    workspace: Path,
) -> None:
    """A19.2 for the gate's presence side: a MUTATING write physically inside the
    associated repo's directory records presence under the OWNING context's NAME
    (``proj``) — never under a fictitious second context keyed by the associated repo's
    own slug (the exact failure A16.4 fixed at the resolver seam, proven here end to
    end through the real gate)."""
    target = workspace / "repos" / _ASSOC_SLUG / "some_file.py"

    block = _run_gate(
        workspace,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="mut-sess",
    )

    assert block is None  # never blocks — NO-LOCKS doctrine
    presence_root = workspace / ".dadaia" / "states" / "presence"
    assert (presence_root / _MAIN_NAME / "mut-sess.json").exists()
    assert not (presence_root / _ASSOC_SLUG).exists()
