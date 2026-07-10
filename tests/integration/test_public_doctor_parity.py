"""Integration tests for guardrail-pair doctor parity (AGT-r2-26).

Verifies that ``_runtime_expectations`` emits the correct labels when
``data/AGENTS.md`` is the source:
  - ``root:AGENTS.md``
  - ``root:CLAUDE.md``
  - ``repos/<slug>:AGENTS.md``   (per registry-listed consumer, v0.1.58 FR4)
  - ``repos/<slug>:CLAUDE.md``   (per registry-listed consumer, v0.1.58 FR4)

Also verifies the ``FileSystemPublicAssetManager.doctor()`` output includes
all four labels after a full stage + install cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    _doctor_guardrail_pair,
    _install_workspace_guardrail_pair,
)

_SOURCE_CONTENT = b"# AGENTS\n\nLib-general guardrail content for testing.\n"
_CONSUMER_VERSION = "0.0.0"
_OWN_VERSION_SENTINEL = "99.99.99-test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_public(tmp_path: Path) -> Path:
    """Create a minimal ``public/`` directory tree for stage() to process."""
    public_dir = tmp_path / "public"
    public_dir.mkdir(parents=True)
    data_dir = public_dir / "data"
    data_dir.mkdir()
    (data_dir / "AGENTS.md").write_bytes(_SOURCE_CONTENT)
    return public_dir


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


def _add_consumer(
    workspace_root: Path,
    slug: str,
    package_version: str = _CONSUMER_VERSION,
) -> Path:
    """Register a marker-less consumer repo via the workspace registry (v0.1.58 FR4).

    Detection is registry-based (Ruling G): the slug is registered in
    ``spec_contexts.json`` and the repo dir is created marker-less. The manifest
    is still written for the retained ``_is_self_repo`` self-skip check.
    """
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    manifest = {"schema_version": "1", "package_version": package_version}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _register_context(workspace_root, slug)
    return consumer


# ---------------------------------------------------------------------------
# Fn 1 — root+consumer label parity + `_runtime_expectations` labels.
# ---------------------------------------------------------------------------


def test_doctor_root_consumer_labels_runtime_expectations_foreign_and_unregistered(
    tmp_path: Path,
) -> None:
    """Root labels always present (no consumers); exactly 4 labels with one registry-listed
    consumer (root x2 + consumer x2, bannerless-source consumer classifies [foreign]);
    drift detected for a modified destination; and ``_runtime_expectations`` yields the
    root labels in the manager's doctor output after a stage+install cycle.

    Plus: the REAL ``manager.doctor()`` emits ``[foreign]`` on BOTH paired consumer lines
    for a hand-authored (no-banner) consumer AGENTS.md — never ``[drift]``/``[missing]``
    (Ruling 16; bug public-doctor-flags-hand-authored-consumer-agents-md); and a consumer
    repo NOT registered in ``spec_contexts.json`` is absent from doctor labels entirely
    (registry-based detection, v0.1.58 FR4, Ruling G)."""
    # Root labels present even without consumers.
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(_SOURCE_CONTENT)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    _install_workspace_guardrail_pair(source, workspace_root, force=True)
    lines = _doctor_guardrail_pair(source, workspace_root)
    labels = {ln.split(" ", 1)[1] for ln in lines if " " in ln}
    assert "root:AGENTS.md" in labels, (
        f"Expected 'root:AGENTS.md' in doctor output labels. Got: {labels}"
    )
    assert "root:CLAUDE.md" in labels, (
        f"Expected 'root:CLAUDE.md' in doctor output labels. Got: {labels}"
    )
    assert all(ln.startswith("[ok]") for ln in lines), (
        f"All root labels should be [ok] after install. Lines: {lines}"
    )

    # Exactly 4 parity labels with one registry-listed consumer (v0.1.58 FR4:
    # registry-based, not the dead in-repo marker). v0.1.60 FR9: bannerless source
    # classifies the consumer pair [foreign] (doctor-[ok]-parity flip) while the
    # lib-owned root pair keeps [ok].
    consumer_root = tmp_path / "consumer-case"
    consumer_root.mkdir()
    consumer_source = consumer_root / "data" / "AGENTS.md"
    consumer_source.parent.mkdir(parents=True)
    consumer_source.write_bytes(_SOURCE_CONTENT)
    consumer_ws = consumer_root / "workspace"
    consumer_ws.mkdir()
    slug = "sample-consumer"
    _add_consumer(consumer_ws, slug)
    _install_workspace_guardrail_pair(consumer_source, consumer_ws, force=True)
    lines2 = _doctor_guardrail_pair(consumer_source, consumer_ws)
    status = {ln.split(" ", 1)[1]: ln.split(" ", 1)[0] for ln in lines2 if " " in ln}
    expected = {
        "root:AGENTS.md",
        "root:CLAUDE.md",
        f"repos/{slug}:AGENTS.md",
        f"repos/{slug}:CLAUDE.md",
    }
    assert set(status) == expected, (
        f"Doctor labels mismatch.\n  Expected: {expected}\n  Got: {set(status)}"
    )
    assert len(lines2) == 4, (
        f"Expected exactly 4 parity lines, got {len(lines2)}.\n  Lines: {lines2}"
    )
    assert status["root:AGENTS.md"] == "[ok]", lines2
    assert status["root:CLAUDE.md"] == "[ok]", lines2
    assert status[f"repos/{slug}:AGENTS.md"] == "[foreign]", lines2
    assert status[f"repos/{slug}:CLAUDE.md"] == "[foreign]", lines2

    # Drift detected on a tampered destination.
    drift_root = tmp_path / "drift-case"
    drift_root.mkdir()
    drift_source = drift_root / "data" / "AGENTS.md"
    drift_source.parent.mkdir(parents=True)
    drift_source.write_bytes(_SOURCE_CONTENT)
    drift_ws = drift_root / "workspace"
    drift_ws.mkdir()
    _install_workspace_guardrail_pair(drift_source, drift_ws, force=True)
    (drift_ws / "CLAUDE.md").write_bytes(b"# Tampered CLAUDE\n")
    lines3 = _doctor_guardrail_pair(drift_source, drift_ws)
    label_map = {ln.split(" ", 1)[1]: ln.split(" ", 1)[0] for ln in lines3 if " " in ln}
    assert label_map.get("root:CLAUDE.md") == "[drift]", (
        f"Expected '[drift] root:CLAUDE.md'. Lines: {lines3}"
    )
    assert label_map.get("root:AGENTS.md") == "[ok]", (
        f"Expected '[ok] root:AGENTS.md'. Lines: {lines3}"
    )

    # _runtime_expectations smoke test via a full stage+install cycle.
    public_dir = _make_minimal_public(tmp_path)
    smoke_ws = tmp_path / "smoke-workspace"
    smoke_ws.mkdir()
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    manager.stage(smoke_ws)
    manager.install(smoke_ws, target="all", force=True)
    doctor_lines = manager.doctor(smoke_ws)
    label_set = set(doctor_lines)
    assert any("root:AGENTS.md" in ln for ln in label_set), (
        f"Expected 'root:AGENTS.md' in doctor output.\n  Lines: {sorted(label_set)}"
    )
    assert any("root:CLAUDE.md" in ln for ln in label_set), (
        f"Expected 'root:CLAUDE.md' in doctor output.\n  Lines: {sorted(label_set)}"
    )

    # Fn 2 — drift-detected + foreign-pair hand-authored + unregistered-consumer-excluded,
    # own workspace.
    foreign_public_dir = _make_minimal_public(tmp_path / "foreign-case")
    workspace_root2 = tmp_path / "foreign-case" / "workspace"
    workspace_root2.mkdir(parents=True)

    slug = "game"
    consumer = _add_consumer(workspace_root2, slug)
    hand_authored = "# My Game Repo\n\nHand-authored, repo-owned rules. NOT lib-originated.\n"
    (consumer / "AGENTS.md").write_text(hand_authored, encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = foreign_public_dir  # noqa: SLF001
    manager.stage(workspace_root2)
    manager.install(workspace_root2, target="all", force=True)

    # INSTALL side: the hand-authored file survives byte-identical, no CLAUDE.md orphan.
    assert (consumer / "AGENTS.md").read_text(encoding="utf-8") == hand_authored
    assert not (consumer / "CLAUDE.md").exists()

    # DOCTOR side via the REAL manager.doctor(): the consumer pair is [foreign] (Ruling 16).
    lines = manager.doctor(workspace_root2)
    assert "[foreign] repos/game:AGENTS.md" in lines, lines
    assert "[foreign] repos/game:CLAUDE.md" in lines, lines
    consumer_lines = [ln for ln in lines if f"repos/{slug}" in ln]
    assert consumer_lines and all(ln.startswith("[foreign]") for ln in consumer_lines), (
        f"the consumer pair must be [foreign] only — no legacy [drift]/[missing].\n  {consumer_lines}"
    )

    # A repo NOT registered in spec_contexts.json is invisible to doctor.
    unregistered_root = tmp_path / "unregistered-case"
    unregistered_root.mkdir()
    unregistered_source = unregistered_root / "data" / "AGENTS.md"
    unregistered_source.parent.mkdir(parents=True)
    unregistered_source.write_bytes(_SOURCE_CONTENT)
    unregistered_ws = unregistered_root / "workspace"
    unregistered_ws.mkdir()
    no_marker = unregistered_ws / "repos" / "no-marker-repo"
    no_marker.mkdir(parents=True)
    _install_workspace_guardrail_pair(unregistered_source, unregistered_ws, force=True)
    unreg_lines = _doctor_guardrail_pair(unregistered_source, unregistered_ws)
    unreg_labels = {ln.split(" ", 1)[1] for ln in unreg_lines if " " in ln}
    assert "repos/no-marker-repo:AGENTS.md" not in unreg_labels, (
        f"Marker-less consumer must not appear in doctor labels. Labels: {unreg_labels}"
    )
    assert len(unreg_lines) == 2, (
        f"Expected exactly 2 lines (root pair only). Got {len(unreg_lines)}: {unreg_lines}"
    )
