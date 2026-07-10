"""Real assertions for `_install_workspace_guardrail_pair`.

Tests for `_install_workspace_guardrail_pair` and `_doctor_guardrail_pair` in
`dadaia_workspace.infrastructure.public_assets`, plus the Option C absence
invariant for `dadaia_workspace/public/data/CLAUDE.md`.

Covers:
1. 4-target projection write (byte-identical, single SHA-256).
2. Skip-variant matrix: unregistered on-disk repo not written, self-slug skip
   (package_version match), and the doctor 4-line parity output.
3. Nested-pair non-interference: `services/CLAUDE.md` + `services/AGENTS.md`
   untouched (FR10) — the regression detector for a real HIGH bug (install once
   clobbered a repo's AGENTS.md).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
    _CLAUDE_MD_STUB,
    _doctor_guardrail_pair,
    _install_workspace_guardrail_pair,
    _package_version,
)

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


def _register_context(workspace_root: Path, slug: str, state: str = "alive") -> None:
    """Register a consumer repo in ``spec_contexts.json`` (v0.1.58 FR4 registry detection).

    Detection moved off the dead in-repo ``.dadaia/agentic/`` marker onto the
    workspace registry (Ruling G); this appends a schema-v2 context row so
    ``_consumer_repos_for_root`` derives ``repos/<slug>/`` on disk.
    """
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    registry = states_dir / "spec_contexts.json"
    data: dict[str, Any] = (
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


def test_four_target_projection_write(tmp_path: Path) -> None:
    """Single source `data/AGENTS.md` fans out to 4 destinations.

    AGENTS.md destinations are byte-identical to the source; CLAUDE.md
    destinations contain only the 1-line stub (T-41: delegates to AGENTS.md).
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n\nGuardrail content.\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Registry-listed, marker-less consumer (v0.1.58 FR4).
    consumer = workspace_root / "repos" / "some-consumer"
    consumer.mkdir(parents=True)
    _register_context(workspace_root, "some-consumer")

    installed: list[str] = []
    _install_workspace_guardrail_pair(source, workspace_root, force=True, installed=installed)

    def sha256(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    expected_agents_sha = sha256(source)

    agents_destinations = [workspace_root / "AGENTS.md", consumer / "AGENTS.md"]
    for dest in agents_destinations:
        assert dest.exists(), f"Expected AGENTS.md destination missing: {dest}"
        assert sha256(dest) == expected_agents_sha, (
            f"AGENTS.md at {dest} is not byte-identical to source."
        )

    claude_destinations = [workspace_root / "CLAUDE.md", consumer / "CLAUDE.md"]
    for dest in claude_destinations:
        assert dest.exists(), f"Expected CLAUDE.md destination missing: {dest}"
        assert dest.read_text(encoding="utf-8") == _CLAUDE_MD_STUB, (
            f"CLAUDE.md at {dest} must contain only the 1-line stub (T-41)."
        )

    ok_entries = [e for e in installed if e.startswith("[ok]")]
    assert len(ok_entries) == 4, f"Expected exactly 4 '[ok]' entries, got {len(ok_entries)}."


def test_skip_and_doctor_matrix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skip variants (unregistered repo, self-slug) + the doctor 4-line parity output."""
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    # (a) unregistered on-disk repo is invisible to the fan-out (registry-based
    #     detection, v0.1.58 FR4, Ruling G — INVERT of the old marker-skip).
    ws_a = tmp_path / "ws-unregistered"
    ws_a.mkdir()
    consumer_a = ws_a / "repos" / "unregistered-repo"
    consumer_a.mkdir(parents=True)
    _install_workspace_guardrail_pair(source, ws_a, force=True)
    assert not (consumer_a / "AGENTS.md").exists(), (
        "Installer must NOT write to a repo not registered in spec_contexts.json."
    )
    assert not (consumer_a / "CLAUDE.md").exists()

    # (b) self-slug skip via package_version match (R14).
    ws_b = tmp_path / "ws-self"
    ws_b.mkdir()
    own_version = _package_version()
    consumer_b = ws_b / "repos" / "dadaia-workspace"
    consumer_b.mkdir(parents=True)
    (consumer_b / ".dadaia" / "agentic").mkdir(parents=True)
    (consumer_b / ".dadaia" / "agentic" / "manifest.json").write_text(
        f'{{"package_version": "{own_version}"}}\n', encoding="utf-8"
    )
    _register_context(ws_b, "dadaia-workspace")
    _install_workspace_guardrail_pair(source, ws_b, force=True)
    assert not (consumer_b / "AGENTS.md").exists()
    assert not (consumer_b / "CLAUDE.md").exists()
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "[skip]" in combined and "self-projection" in combined

    # (c) doctor emits exactly 4 parity lines; bannerless source classifies the
    #     consumer pair [foreign] while the lib-owned root pair stays [ok]
    #     (v0.1.60 FR9 amendment).
    ws_c = tmp_path / "ws-doctor"
    ws_c.mkdir()
    slug = "some-consumer"
    consumer_c = ws_c / "repos" / slug
    consumer_c.mkdir(parents=True)
    _register_context(ws_c, slug)
    _install_workspace_guardrail_pair(source, ws_c, force=True)
    lines = _doctor_guardrail_pair(source, ws_c)
    expected_labels = {
        "root:AGENTS.md",
        "root:CLAUDE.md",
        f"repos/{slug}:AGENTS.md",
        f"repos/{slug}:CLAUDE.md",
    }
    status = {ln.split(" ", 1)[1]: ln.split(" ", 1)[0] for ln in lines if " " in ln}
    assert set(status) == expected_labels
    assert len(lines) == 4
    assert status["root:AGENTS.md"] == "[ok]", lines
    assert status["root:CLAUDE.md"] == "[ok]", lines
    assert status[f"repos/{slug}:AGENTS.md"] == "[foreign]", lines
    assert status[f"repos/{slug}:CLAUDE.md"] == "[foreign]", lines


def test_nested_pair_non_interference(tmp_path: Path) -> None:
    """Operator-authored services/CLAUDE.md + services/AGENTS.md are NOT touched.

    FR10: files at `services/CLAUDE.md` and `services/AGENTS.md` are operator-authored
    (not lib-originated). The guardrail installer only writes to workspace-root and
    consumer-repo roots — this is the regression detector for the real HIGH bug where
    `install` once clobbered a repo's AGENTS.md.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS guardrail\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    services_dir = workspace_root / "services"
    services_dir.mkdir()

    services_agents = services_dir / "AGENTS.md"
    services_claude = services_dir / "CLAUDE.md"

    operator_agents_content = b"# Operator-authored AGENTS for services\n"
    operator_claude_content = b"# Operator-authored CLAUDE for services\n"

    services_agents.write_bytes(operator_agents_content)
    services_claude.write_bytes(operator_claude_content)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    assert services_agents.read_bytes() == operator_agents_content, (
        "services/AGENTS.md was modified by the installer — must remain untouched (FR10)."
    )
    assert services_claude.read_bytes() == operator_claude_content, (
        "services/CLAUDE.md was modified by the installer — must remain untouched (FR10)."
    )
