"""Integration tests for guardrail-pair doctor parity (AGT-r2-26).

K3 (v0.5.1): the root law is a ``ProjectionRule`` entry (``root:AGENTS.md``); 0.4.7
FR3 retired its ``CLAUDE.md`` twin. The standalone
``_doctor_guardrail_pair`` helper — a duplicate of what ``manager.doctor()`` already
computed inline — is retired. Every assertion below goes through the REAL production
path (``manager.stage()`` / ``manager.install()`` / ``manager.doctor()``), which is a
strictly more faithful test than calling a bespoke doctor helper directly.

Verifies that ``FileSystemPublicAssetManager.doctor()`` emits:
  - ``root:AGENTS.md`` — always present, drift-detecting.
"""

from __future__ import annotations

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


def _make_minimal_public(tmp_path: Path) -> Path:
    """Create a minimal ``public/`` directory tree for stage()/install()/doctor()."""
    public_dir = tmp_path / "public"
    public_dir.mkdir(parents=True)
    data_dir = public_dir / "data"
    data_dir.mkdir()
    (data_dir / "AGENTS.md").write_bytes(_SOURCE_CONTENT)
    return public_dir


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
    manager.install(ws, force=True)
    lines = _rendered(manager.doctor(ws))
    assert "[ok] root:AGENTS.md" in lines, lines


def test_root_agents_md_detects_drift_when_tampered(tmp_path: Path) -> None:
    public_dir = _make_minimal_public(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    manager = _mgr(public_dir)
    manager.stage(ws)
    manager.install(ws, force=True)
    (ws / "AGENTS.md").write_bytes(b"# Tampered AGENTS\n")
    lines = _rendered(manager.doctor(ws))
    assert "[drift] root:AGENTS.md" in lines, lines
    assert not any("CLAUDE.md" in ln for ln in lines), lines
