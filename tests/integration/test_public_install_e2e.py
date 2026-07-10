"""End-to-end integration tests for guardrail-pair nested non-interference — AGT-r2-28.

Verifies that `_install_workspace_guardrail_pair` (the Option C installer):

1. Does NOT overwrite operator-authored `services/CLAUDE.md` and `services/AGENTS.md`.
2. DOES write workspace-root `AGENTS.md` and `CLAUDE.md` byte-identical to the source.
3. DOES write consumer-repo pair byte-identical to the source when a marker-bearing
   consumer repo exists in `repos/`.

This covers ADR item 5 (nested-pair non-interference) end-to-end, exercising the
installer function directly against a realistic workspace layout.

Note (AGT-r2-35 pending): `FileSystemPublicAssetManager.install()` will dispatch
to `_install_workspace_guardrail_pair` once AGT-r2-35 wires the call site.  These
tests use the function directly so they pass at the current phase (P9).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    _CLAUDE_MD_STUB,
    _install_workspace_guardrail_pair,
)

# Distinct content strings to ensure byte-identity checks are meaningful.
_SOURCE_GUARDRAIL_CONTENT = b"# AGENTS\n\nLib-general guardrail content for E2E test.\n"
_OPERATOR_AGENTS_CONTENT = b"# Operator-authored AGENTS.md for services/\n"
_OPERATOR_CLAUDE_CONTENT = b"# Operator-authored CLAUDE.md for services/\n"
_CONSUMER_VERSION = "0.0.0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_source(tmp_path: Path) -> Path:
    """Write the guardrail source file and return its path."""
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(_SOURCE_GUARDRAIL_CONTENT)
    return source


def _register_context(workspace_root: Path, slug: str, state: str = "alive") -> None:
    """Register a consumer repo in ``spec_contexts.json`` (v0.1.58 FR4 registry detection)."""
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    registry = states_dir / "spec_contexts.json"
    data = (
        json.loads(registry.read_text(encoding="utf-8"))
        if registry.exists()
        else {"schema_version": "2", "contexts": []}
    )
    data["contexts"].append(
        {
            "name": slug,
            "state": state,
            "repo_slug": slug,
            "repo_url": f"https://example.test/{slug}.git",
            "created_at": "2026-07-04T00:00:00Z",
            "alive_since": "2026-07-04T00:00:00Z" if state == "alive" else None,
            "dead_since": None if state == "alive" else "2026-07-04T00:00:00Z",
            "current_branch": "main",
        }
    )
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _add_marker_consumer(workspace_root: Path, slug: str) -> Path:
    """Register a consumer repo under `workspace_root/repos/` (v0.1.58 FR4).

    Detection is registry-based (Ruling G): the slug is registered in
    ``spec_contexts.json``. The manifest is kept for the retained
    ``_is_self_repo`` self-skip check, not for detection.
    """
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    manifest = {"schema_version": "1", "package_version": _CONSUMER_VERSION}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _register_context(workspace_root, slug)
    return consumer


# ---------------------------------------------------------------------------
# Merged: nested operator services/ pair untouched (with and without consumers) +
# all projected root/consumer pairs byte-identical to source (single SHA-256, Option C).
# ---------------------------------------------------------------------------


def test_nested_operator_pair_untouched_and_all_projections_share_single_sha(
    tmp_path: Path,
) -> None:
    """FR10 end-to-end: the installer writes ONLY to workspace-root and marker-bearing
    consumer-repo roots — operator-authored files in ``services/`` remain byte-identical
    to their pre-install content, both with and without consumer repos present. Option C
    (ADR): a single source file fans out to N projections, and all N destinations share
    exactly one SHA-256 per file kind (AGENTS.md vs the T-41 CLAUDE.md stub)."""
    source = _make_source(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Operator-authored files in services/ (must NOT be touched).
    services_dir = workspace_root / "services"
    services_dir.mkdir()
    services_agents = services_dir / "AGENTS.md"
    services_claude = services_dir / "CLAUDE.md"
    services_agents.write_bytes(_OPERATOR_AGENTS_CONTENT)
    services_claude.write_bytes(_OPERATOR_CLAUDE_CONTENT)

    # Two marker-bearing consumer repos.
    slug_a = "sample-consumer"
    slug_b = "workflow-tools"
    consumer_a = _add_marker_consumer(workspace_root, slug_a)
    consumer_b = _add_marker_consumer(workspace_root, slug_b)

    installed: list[str] = []
    _install_workspace_guardrail_pair(source, workspace_root, force=True, installed=installed)

    # services/ files unchanged.
    assert services_agents.read_bytes() == _OPERATOR_AGENTS_CONTENT, (
        "services/AGENTS.md was overwritten by install — it must remain untouched (FR10)."
    )
    assert services_claude.read_bytes() == _OPERATOR_CLAUDE_CONTENT, (
        "services/CLAUDE.md was overwritten by install — it must remain untouched (FR10)."
    )

    source_sha = hashlib.sha256(_SOURCE_GUARDRAIL_CONTENT).hexdigest()
    stub_sha = hashlib.sha256(_CLAUDE_MD_STUB.encode()).hexdigest()

    agents_files = [
        workspace_root / "AGENTS.md",
        consumer_a / "AGENTS.md",
        consumer_b / "AGENTS.md",
    ]
    claude_files = [
        workspace_root / "CLAUDE.md",
        consumer_a / "CLAUDE.md",
        consumer_b / "CLAUDE.md",
    ]
    for path in agents_files + claude_files:
        assert path.exists(), f"Expected projected file missing: {path}"

    agents_sha_set = {_sha256(p) for p in agents_files}
    assert agents_sha_set == {source_sha}, (
        f"All AGENTS.md projections must share a single SHA-256 (Option C invariant).\n"
        f"  Expected: {{{source_sha!r}}}\n"
        f"  Got: {agents_sha_set}"
    )
    claude_sha_set = {_sha256(p) for p in claude_files}
    assert claude_sha_set == {stub_sha}, (
        f"All CLAUDE.md projections must be the T-41 stub (single SHA-256).\n"
        f"  Expected: {{{stub_sha!r}}}\n"
        f"  Got: {claude_sha_set}"
    )

    ok_entries = [e for e in installed if e.startswith("[ok]")]
    assert len(ok_entries) == 6, (
        f"Expected 6 '[ok]' entries in installed list (2 root + 4 consumer), "
        f"got {len(ok_entries)}.\n  installed: {installed}"
    )

    # Minimal variant: workspace-root only, no repos/ directory — services/ still untouched.
    no_consumer_root = tmp_path / "no-consumer-case"
    no_consumer_root.mkdir()
    no_consumer_source = _make_source(no_consumer_root)
    no_consumer_ws = no_consumer_root / "workspace"
    no_consumer_ws.mkdir()
    nc_services_dir = no_consumer_ws / "services"
    nc_services_dir.mkdir()
    nc_services_agents = nc_services_dir / "AGENTS.md"
    nc_services_claude = nc_services_dir / "CLAUDE.md"
    nc_services_agents.write_bytes(_OPERATOR_AGENTS_CONTENT)
    nc_services_claude.write_bytes(_OPERATOR_CLAUDE_CONTENT)

    _install_workspace_guardrail_pair(no_consumer_source, no_consumer_ws, force=True)

    assert nc_services_agents.read_bytes() == _OPERATOR_AGENTS_CONTENT, (
        "services/AGENTS.md was overwritten by install (no consumers) — FR10 violated."
    )
    assert nc_services_claude.read_bytes() == _OPERATOR_CLAUDE_CONTENT, (
        "services/CLAUDE.md was overwritten by install (no consumers) — FR10 violated."
    )
    assert _sha256(no_consumer_ws / "AGENTS.md") == source_sha, (
        "workspace-root/AGENTS.md must be byte-identical to source after install."
    )
    assert _sha256(no_consumer_ws / "CLAUDE.md") == stub_sha, (
        "workspace-root/CLAUDE.md must be the T-41 stub after install."
    )
