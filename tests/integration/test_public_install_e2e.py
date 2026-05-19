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


def _add_marker_consumer(workspace_root: Path, slug: str) -> Path:
    """Create a marker-bearing consumer repo under `workspace_root/repos/`."""
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    manifest = {"schema_version": "1", "package_version": _CONSUMER_VERSION}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return consumer


# ---------------------------------------------------------------------------
# Test 1 — services/ pair untouched; root + consumer pairs written
# ---------------------------------------------------------------------------


def test_nested_services_pair_untouched_after_install(tmp_path: Path) -> None:
    """services/AGENTS.md and services/CLAUDE.md are not overwritten by install.

    FR10 end-to-end: the installer writes ONLY to workspace-root and marker-bearing
    consumer-repo roots.  Operator-authored files in subdirectories (e.g. `services/`)
    must remain byte-identical to their pre-install content.

    Setup:
      - `services/AGENTS.md` and `services/CLAUDE.md` present with operator content.
      - `data/AGENTS.md` source has different content.
      - One marker-bearing consumer repo under `repos/`.

    After `_install_workspace_guardrail_pair` (force=True):
      - services/{AGENTS,CLAUDE}.md unchanged.
      - workspace-root/{AGENTS,CLAUDE}.md byte-identical to source.
      - consumer/{AGENTS,CLAUDE}.md byte-identical to source (single SHA-256).
    """
    source = _make_source(tmp_path)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # --- Operator-authored files in services/ (must NOT be touched) ---
    services_dir = workspace_root / "services"
    services_dir.mkdir()
    services_agents = services_dir / "AGENTS.md"
    services_claude = services_dir / "CLAUDE.md"
    services_agents.write_bytes(_OPERATOR_AGENTS_CONTENT)
    services_claude.write_bytes(_OPERATOR_CLAUDE_CONTENT)

    # --- Marker-bearing consumer repo ---
    slug = "dadaia-bots"
    consumer = _add_marker_consumer(workspace_root, slug)

    # --- Run install ---
    installed: list[str] = []
    _install_workspace_guardrail_pair(source, workspace_root, force=True, installed=installed)

    # --- Assert: services/ files unchanged ---
    assert services_agents.read_bytes() == _OPERATOR_AGENTS_CONTENT, (
        "services/AGENTS.md was overwritten by install — it must remain untouched (FR10)."
    )
    assert services_claude.read_bytes() == _OPERATOR_CLAUDE_CONTENT, (
        "services/CLAUDE.md was overwritten by install — it must remain untouched (FR10)."
    )

    # --- Assert: workspace-root pair byte-identical to source (single SHA-256) ---
    source_sha = hashlib.sha256(_SOURCE_GUARDRAIL_CONTENT).hexdigest()

    root_agents = workspace_root / "AGENTS.md"
    root_claude = workspace_root / "CLAUDE.md"
    assert root_agents.exists(), "workspace-root/AGENTS.md must be written by install."
    assert root_claude.exists(), "workspace-root/CLAUDE.md must be written by install."
    assert _sha256(root_agents) == source_sha, (
        f"workspace-root/AGENTS.md is not byte-identical to source.\n"
        f"  source sha256: {source_sha}\n"
        f"  dest   sha256: {_sha256(root_agents)}"
    )
    assert _sha256(root_claude) == source_sha, (
        f"workspace-root/CLAUDE.md is not byte-identical to source.\n"
        f"  source sha256: {source_sha}\n"
        f"  dest   sha256: {_sha256(root_claude)}"
    )

    # --- Assert: consumer pair byte-identical to source (same single SHA-256) ---
    consumer_agents = consumer / "AGENTS.md"
    consumer_claude = consumer / "CLAUDE.md"
    assert consumer_agents.exists(), f"repos/{slug}/AGENTS.md must be written by install."
    assert consumer_claude.exists(), f"repos/{slug}/CLAUDE.md must be written by install."
    assert _sha256(consumer_agents) == source_sha, (
        f"repos/{slug}/AGENTS.md is not byte-identical to source.\n"
        f"  source sha256: {source_sha}\n"
        f"  dest   sha256: {_sha256(consumer_agents)}"
    )
    assert _sha256(consumer_claude) == source_sha, (
        f"repos/{slug}/CLAUDE.md is not byte-identical to source.\n"
        f"  source sha256: {source_sha}\n"
        f"  dest   sha256: {_sha256(consumer_claude)}"
    )


# ---------------------------------------------------------------------------
# Test 2 — services/ pair untouched even without consumer repos
# ---------------------------------------------------------------------------


def test_nested_services_pair_untouched_no_consumers(tmp_path: Path) -> None:
    """services/ files untouched even when there are no consumer repos.

    This is the minimal variant: workspace-root only, no repos/ directory.
    Confirms the FR10 invariant is upheld regardless of whether consumers exist.
    """
    source = _make_source(tmp_path)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Operator-authored files — services/ (no marker-bearing repos in this test)
    services_dir = workspace_root / "services"
    services_dir.mkdir()
    services_agents = services_dir / "AGENTS.md"
    services_claude = services_dir / "CLAUDE.md"
    services_agents.write_bytes(_OPERATOR_AGENTS_CONTENT)
    services_claude.write_bytes(_OPERATOR_CLAUDE_CONTENT)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    assert services_agents.read_bytes() == _OPERATOR_AGENTS_CONTENT, (
        "services/AGENTS.md was overwritten by install (no consumers) — FR10 violated."
    )
    assert services_claude.read_bytes() == _OPERATOR_CLAUDE_CONTENT, (
        "services/CLAUDE.md was overwritten by install (no consumers) — FR10 violated."
    )

    source_sha = hashlib.sha256(_SOURCE_GUARDRAIL_CONTENT).hexdigest()
    assert _sha256(workspace_root / "AGENTS.md") == source_sha, (
        "workspace-root/AGENTS.md must be byte-identical to source after install."
    )
    assert _sha256(workspace_root / "CLAUDE.md") == source_sha, (
        "workspace-root/CLAUDE.md must be byte-identical to source after install."
    )


# ---------------------------------------------------------------------------
# Test 3 — all projected pairs share a single SHA-256 (Option C invariant)
# ---------------------------------------------------------------------------


def test_all_projected_pairs_share_single_sha256(tmp_path: Path) -> None:
    """All projected {AGENTS,CLAUDE}.md files share exactly one unique SHA-256.

    Option C (ADR): a single source file fans out to N projections.  All N
    destinations must be byte-identical to each other (verified by SHA-256 set
    cardinality = 1).

    Fixture: 2 marker-bearing consumer repos.
    """
    source = _make_source(tmp_path)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    slug_a = "dadaia-bots"
    slug_b = "workflow-tools"
    consumer_a = _add_marker_consumer(workspace_root, slug_a)
    consumer_b = _add_marker_consumer(workspace_root, slug_b)

    installed: list[str] = []
    _install_workspace_guardrail_pair(source, workspace_root, force=True, installed=installed)

    projected_files = [
        workspace_root / "AGENTS.md",
        workspace_root / "CLAUDE.md",
        consumer_a / "AGENTS.md",
        consumer_a / "CLAUDE.md",
        consumer_b / "AGENTS.md",
        consumer_b / "CLAUDE.md",
    ]

    for path in projected_files:
        assert path.exists(), f"Expected projected file missing: {path}"

    sha_set = {_sha256(p) for p in projected_files}
    source_sha = hashlib.sha256(_SOURCE_GUARDRAIL_CONTENT).hexdigest()

    assert sha_set == {source_sha}, (
        f"All projected files must share a single SHA-256 (Option C invariant).\n"
        f"  Expected: {{{source_sha!r}}}\n"
        f"  Got: {sha_set}"
    )

    # Also confirm the installed list records all 6 as [ok]
    ok_entries = [e for e in installed if e.startswith("[ok]")]
    assert len(ok_entries) == 6, (
        f"Expected 6 '[ok]' entries in installed list (2 root + 4 consumer), "
        f"got {len(ok_entries)}.\n  installed: {installed}"
    )
