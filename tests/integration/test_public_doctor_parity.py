"""Integration tests for guardrail-pair doctor parity (AGT-r2-26).

K3 (v0.5.1): the root ``AGENTS.md``/``CLAUDE.md`` pair is now 2 ``ProjectionRule``
entries (``root:AGENTS.md``, ``root:CLAUDE.md``); the standalone
``_doctor_guardrail_pair`` helper — a duplicate of what ``manager.doctor()`` already
computed inline — is retired. Every assertion below goes through the REAL production
path (``manager.stage()`` / ``manager.install()`` / ``manager.doctor()``), which is a
strictly more faithful test than calling a bespoke doctor helper directly.

Verifies that ``FileSystemPublicAssetManager.doctor()`` emits:
  - ``root:AGENTS.md`` / ``root:CLAUDE.md`` — always present, drift-detecting.
  - ``repos/<slug>:AGENTS.md`` / ``repos/<slug>:CLAUDE.md`` — per registry-listed
    consumer (v0.1.58 FR4), provenance-gated ``[foreign]`` for a bannerless/
    hand-authored source (Ruling 16).
  - Nothing at all for a consumer repo absent from the registry (Ruling G).
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


_SOURCE_CONTENT = b"# AGENTS\n\nLib-general guardrail content for testing.\n"
_CONSUMER_VERSION = "0.0.0"


def _make_minimal_public(tmp_path: Path) -> Path:
    """Create a minimal ``public/`` directory tree for stage()/install()/doctor()."""
    public_dir = tmp_path / "public"
    public_dir.mkdir(parents=True)
    data_dir = public_dir / "data"
    data_dir.mkdir()
    (data_dir / "AGENTS.md").write_bytes(_SOURCE_CONTENT)
    return public_dir


def _register_context(workspace_root: Path, slug: str) -> None:
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
            "state": "alive",
            "repo_slug": slug,
            "repo_url": f"https://example.test/{slug}.git",
            "created_at": "2026-07-04T00:00:00Z",
            "alive_since": "2026-07-04T00:00:00Z",
            "dead_since": None,
            "current_branch": "main",
        }
    )
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _add_consumer(workspace_root: Path, slug: str) -> Path:
    """Register a marker-less consumer repo via the workspace registry (v0.1.58 FR4)."""
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    manifest = {"schema_version": "1", "package_version": _CONSUMER_VERSION}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _register_context(workspace_root, slug)
    return consumer


def _mgr(public_dir: Path) -> FileSystemPublicAssetManager:
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    return manager


def test_root_pair_always_present_and_ok(tmp_path: Path) -> None:
    """Root labels are present, [ok], even with zero consumers registered."""
    public_dir = _make_minimal_public(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    manager = _mgr(public_dir)
    manager.stage(ws)
    manager.install(ws, target="all", force=True)
    lines = _rendered(manager.doctor(ws))
    assert "[ok] root:AGENTS.md" in lines, lines
    assert "[ok] root:CLAUDE.md" in lines, lines


def test_root_pair_detects_drift_on_tampered_claude_md(tmp_path: Path) -> None:
    public_dir = _make_minimal_public(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    manager = _mgr(public_dir)
    manager.stage(ws)
    manager.install(ws, target="all", force=True)
    (ws / "CLAUDE.md").write_bytes(b"# Tampered CLAUDE\n")
    lines = _rendered(manager.doctor(ws))
    assert "[drift] root:CLAUDE.md" in lines, lines
    assert "[ok] root:AGENTS.md" in lines, lines


def test_consumer_pair_foreign_for_bannerless_source(tmp_path: Path) -> None:
    """A staged AGENTS.md with no canonical banner classifies the CONSUMER pair
    [foreign] (never [drift]/[missing]) while the lib-owned root pair stays [ok]
    (Ruling 16, v0.1.60 FR9)."""
    public_dir = _make_minimal_public(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "sample-consumer"
    _add_consumer(ws, slug)
    manager = _mgr(public_dir)
    manager.stage(ws)
    manager.install(ws, target="all", force=True)
    lines = _rendered(manager.doctor(ws))
    assert "[ok] root:AGENTS.md" in lines, lines
    assert "[ok] root:CLAUDE.md" in lines, lines
    assert f"[foreign] repos/{slug}:AGENTS.md" in lines, lines
    assert f"[foreign] repos/{slug}:CLAUDE.md" in lines, lines


def test_consumer_pair_foreign_for_hand_authored_agents_md(tmp_path: Path) -> None:
    """The consumer pair is [foreign] only — no legacy [drift]/[missing] — and the
    hand-authored file survives byte-identical with no CLAUDE.md orphan."""
    public_dir = _make_minimal_public(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "game"
    consumer = _add_consumer(ws, slug)
    hand_authored = "# My Game Repo\n\nHand-authored, repo-owned rules. NOT lib-originated.\n"
    (consumer / "AGENTS.md").write_text(hand_authored, encoding="utf-8")

    manager = _mgr(public_dir)
    manager.stage(ws)
    manager.install(ws, target="all", force=True)

    assert (consumer / "AGENTS.md").read_text(encoding="utf-8") == hand_authored
    assert not (consumer / "CLAUDE.md").exists()

    lines = _rendered(manager.doctor(ws))
    assert f"[foreign] repos/{slug}:AGENTS.md" in lines, lines
    assert f"[foreign] repos/{slug}:CLAUDE.md" in lines, lines
    consumer_lines = [ln for ln in lines if f"repos/{slug}" in ln]
    assert consumer_lines and all(ln.startswith("[foreign]") for ln in consumer_lines), (
        f"the consumer pair must be [foreign] only — no legacy [drift]/[missing].\n  {consumer_lines}"
    )


def test_unregistered_consumer_is_invisible_to_doctor(tmp_path: Path) -> None:
    """A repo NOT registered in spec_contexts.json contributes zero doctor lines
    (registry-based detection, v0.1.58 FR4, Ruling G) — only the root pair remains."""
    public_dir = _make_minimal_public(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    no_marker = ws / "repos" / "no-marker-repo"
    no_marker.mkdir(parents=True)
    manager = _mgr(public_dir)
    manager.stage(ws)
    manager.install(ws, target="all", force=True)
    lines = _rendered(manager.doctor(ws))
    assert not any("no-marker-repo" in ln for ln in lines), lines
    assert "[ok] root:AGENTS.md" in lines, lines
    assert "[ok] root:CLAUDE.md" in lines, lines
