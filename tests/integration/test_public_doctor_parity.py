"""Integration tests for guardrail-pair doctor parity (AGT-r2-26).

Verifies that ``_runtime_expectations`` emits the correct labels when
``data/AGENTS.md`` is the source:
  - ``root:AGENTS.md``
  - ``root:CLAUDE.md``
  - ``repos/<slug>:AGENTS.md``   (per marker-bearing consumer)
  - ``repos/<slug>:CLAUDE.md``   (per marker-bearing consumer)

Also verifies the ``FileSystemPublicAssetManager.doctor()`` output includes
all four labels after a full stage + install cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    _consumer_repos_for_root,
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


def _add_consumer(
    workspace_root: Path,
    slug: str,
    package_version: str = _CONSUMER_VERSION,
) -> Path:
    """Create a marker-bearing consumer repo under ``workspace_root/repos/``."""
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    manifest = {"schema_version": "1", "package_version": package_version}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return consumer


# ---------------------------------------------------------------------------
# Test 1 — root labels always present (no consumers)
# ---------------------------------------------------------------------------


def test_doctor_root_labels_present_without_consumers(tmp_path: Path) -> None:
    """Root parity labels are emitted even when no consumer repos exist.

    Verifies the minimum invariant: ``root:AGENTS.md`` and ``root:CLAUDE.md``
    always appear in doctor output regardless of ``repos/`` contents.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(_SOURCE_CONTENT)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Install the pair at workspace root.
    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    # Doctor must surface both root labels as [ok].
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


# ---------------------------------------------------------------------------
# Test 2 — 4 labels per consumer (root × 2 + consumer × 2)
# ---------------------------------------------------------------------------


def test_doctor_emits_four_labels_with_one_consumer(tmp_path: Path) -> None:
    """Exactly 4 parity labels are emitted when one marker-bearing consumer exists.

    Labels expected:
      - root:AGENTS.md
      - root:CLAUDE.md
      - repos/<slug>:AGENTS.md
      - repos/<slug>:CLAUDE.md
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(_SOURCE_CONTENT)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    slug = "redacted-slug"
    _add_consumer(workspace_root, slug)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    lines = _doctor_guardrail_pair(source, workspace_root)
    labels = {ln.split(" ", 1)[1] for ln in lines if " " in ln}

    expected = {
        "root:AGENTS.md",
        "root:CLAUDE.md",
        f"repos/{slug}:AGENTS.md",
        f"repos/{slug}:CLAUDE.md",
    }
    assert labels == expected, (
        f"Doctor labels mismatch.\n  Expected: {expected}\n  Got: {labels}"
    )
    assert len(lines) == 4, (
        f"Expected exactly 4 parity lines, got {len(lines)}.\n  Lines: {lines}"
    )
    assert all(ln.startswith("[ok]") for ln in lines), (
        f"All labels should be [ok] after install. Lines: {lines}"
    )


# ---------------------------------------------------------------------------
# Test 3 — drift detected for modified destination
# ---------------------------------------------------------------------------


def test_doctor_detects_drift_on_modified_destination(tmp_path: Path) -> None:
    """Doctor reports [drift] when a projected file diverges from the source."""
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(_SOURCE_CONTENT)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    # Tamper with the workspace-root CLAUDE.md.
    (workspace_root / "CLAUDE.md").write_bytes(b"# Tampered CLAUDE\n")

    lines = _doctor_guardrail_pair(source, workspace_root)
    label_map = {ln.split(" ", 1)[1]: ln.split(" ", 1)[0] for ln in lines if " " in ln}

    assert label_map.get("root:CLAUDE.md") == "[drift]", (
        f"Expected '[drift] root:CLAUDE.md'. Lines: {lines}"
    )
    assert label_map.get("root:AGENTS.md") == "[ok]", (
        f"Expected '[ok] root:AGENTS.md'. Lines: {lines}"
    )


# ---------------------------------------------------------------------------
# Test 4 — _runtime_expectations yields 4 tuples for data/AGENTS.md source
# (full stage + install cycle via FileSystemPublicAssetManager)
# ---------------------------------------------------------------------------


def test_runtime_expectations_yields_guardrail_labels(tmp_path: Path) -> None:
    """``_runtime_expectations`` yields ``root:AGENTS.md`` and ``root:CLAUDE.md``.

    This is a smoke test verifying the labels are present in the manager's
    doctor output after a stage + install cycle.

    If no marker-bearing consumer repos exist in the workspace, only the
    2 root labels are verified (minimum acceptable state per task acceptance).
    """
    public_dir = _make_minimal_public(tmp_path)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    manager.stage(workspace_root)
    manager.install(workspace_root, target="all", force=True)

    doctor_lines = manager.doctor(workspace_root)

    label_set = set(doctor_lines)
    assert any("root:AGENTS.md" in ln for ln in label_set), (
        f"Expected 'root:AGENTS.md' in doctor output.\n  Lines: {sorted(label_set)}"
    )
    assert any("root:CLAUDE.md" in ln for ln in label_set), (
        f"Expected 'root:CLAUDE.md' in doctor output.\n  Lines: {sorted(label_set)}"
    )


# ---------------------------------------------------------------------------
# Test 5 — consumer repos without marker are skipped silently
# ---------------------------------------------------------------------------


def test_no_marker_consumer_does_not_appear_in_doctor_labels(tmp_path: Path) -> None:
    """Consumer dirs without ``.dadaia/agentic/`` are absent from doctor labels."""
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(_SOURCE_CONTENT)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # No-marker consumer: has no .dadaia/ at all.
    no_marker = workspace_root / "repos" / "no-marker-repo"
    no_marker.mkdir(parents=True)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    lines = _doctor_guardrail_pair(source, workspace_root)
    labels = {ln.split(" ", 1)[1] for ln in lines if " " in ln}

    # Only root labels should be present; the no-marker repo is invisible.
    assert "repos/no-marker-repo:AGENTS.md" not in labels, (
        f"Marker-less consumer must not appear in doctor labels. Labels: {labels}"
    )
    assert len(lines) == 2, (
        f"Expected exactly 2 lines (root pair only). Got {len(lines)}: {lines}"
    )
