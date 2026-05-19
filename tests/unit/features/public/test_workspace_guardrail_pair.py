"""Real assertions for `_install_workspace_guardrail_pair` — AGT-r2-27 + AGT-r2-34 + AGT-r2-35.

Tests for `_install_workspace_guardrail_pair` and `_doctor_guardrail_pair` in
`dadaia_workspace.infrastructure.public_assets`, plus the Option C absence
invariant for `dadaia_workspace/public/data/CLAUDE.md` (AGT-r2-34), and the
install call-site dispatch to `_install_workspace_guardrail_pair` (AGT-r2-35).

Eight cases covering:
1. 4-target projection write (byte-identical, single SHA-256).
2. Skip when consumer has no `.dadaia/` marker.
3. Skip when consumer has `.dadaia/` but no `.dadaia/agentic/` marker.
4. Self-slug skip via `package_version` match (R14).
5. Nested-pair non-interference: `services/CLAUDE.md` + `services/AGENTS.md` untouched (FR10).
6. Doctor produces exactly 4 parity labels per source.
7. Option C invariant: `data/CLAUDE.md` MUST NOT exist as a source file.
8. Install call site dispatch: `FileSystemPublicAssetManager.install()` writes 4 guardrail
   files when `data/AGENTS.md` is present in the staged agentic dir (AGT-r2-35).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    _doctor_guardrail_pair,
    _install_workspace_guardrail_pair,
    _package_version,
)

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


# ---------------------------------------------------------------------------
# Case 1 — 4-target projection write
# ---------------------------------------------------------------------------


def test_four_target_projection_write(tmp_path: Path) -> None:
    """Single source `data/AGENTS.md` fans out to 4 destinations.

    Given:
      - A source file at `<agentic_dir>/data/AGENTS.md` with known content.
      - A workspace root directory.
      - One consumer repo directory under `repos/` with `.dadaia/agentic/` markers
        and a distinct `package_version` (so it is NOT self-skipped).

    When:
      - `_install_workspace_guardrail_pair` is called with force=True.

    Then:
      - All 4 destination files are written:
          * workspace-root / AGENTS.md
          * workspace-root / CLAUDE.md
          * workspace-root / repos/<slug> / AGENTS.md
          * workspace-root / repos/<slug> / CLAUDE.md
      - All 4 files are byte-identical to the source (verified via SHA-256).
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n\nGuardrail content.\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    consumer = workspace_root / "repos" / "some-consumer"
    consumer.mkdir(parents=True)
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        '{"package_version": "0.0.0"}\n', encoding="utf-8"
    )

    installed: list[str] = []
    _install_workspace_guardrail_pair(source, workspace_root, force=True, installed=installed)

    def sha256(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    expected = sha256(source)
    destinations = [
        workspace_root / "AGENTS.md",
        workspace_root / "CLAUDE.md",
        consumer / "AGENTS.md",
        consumer / "CLAUDE.md",
    ]
    assert len(destinations) == 4, "Fixture must define exactly 4 destination paths."
    for dest in destinations:
        assert dest.exists(), f"Expected destination missing: {dest}"
        assert sha256(dest) == expected, (
            f"Destination {dest} is not byte-identical to source.\n"
            f"  source sha256: {expected}\n"
            f"  dest   sha256: {sha256(dest)}"
        )

    ok_entries = [e for e in installed if e.startswith("[ok]")]
    assert len(ok_entries) == 4, (
        f"Expected exactly 4 '[ok]' entries in installed list, got {len(ok_entries)}.\n"
        f"  installed: {installed}"
    )


# ---------------------------------------------------------------------------
# Case 2 — Skip variant: no `.dadaia/` marker
# ---------------------------------------------------------------------------


def test_skip_no_dadaia_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Consumer dir without `.dadaia/` is silently skipped.

    Given:
      - A consumer repo directory that has NO `.dadaia/` subdirectory.

    When:
      - `_install_workspace_guardrail_pair` processes that consumer.

    Then:
      - The consumer directory is not written to.
      - The installer logs: `[skip] <path> (no .dadaia/ marker)` to stderr.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Consumer has NO .dadaia/ directory — must be skipped
    consumer = workspace_root / "repos" / "no-marker-repo"
    consumer.mkdir(parents=True)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    assert not (consumer / "AGENTS.md").exists(), (
        "Installer must NOT write to a consumer lacking a .dadaia/ marker."
    )

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "[skip]" in combined and "no .dadaia/ marker" in combined, (
        f"Expected skip log line not found in output.\n  Output: {combined!r}"
    )


# ---------------------------------------------------------------------------
# Case 3 — Skip variant: no `.dadaia/agentic/` marker
# ---------------------------------------------------------------------------


def test_skip_no_agentic_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Consumer dir with `.dadaia/` but no `.dadaia/agentic/` is silently skipped.

    Given:
      - A consumer repo directory that has `.dadaia/` but NOT `.dadaia/agentic/`.

    When:
      - `_install_workspace_guardrail_pair` processes that consumer.

    Then:
      - The consumer directory is not written to.
      - The installer logs: `[skip] <path> (no .dadaia/ marker)` to stderr.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Consumer has .dadaia/ but NO .dadaia/agentic/ subdirectory
    consumer = workspace_root / "repos" / "no-agentic-repo"
    consumer.mkdir(parents=True)
    (consumer / ".dadaia").mkdir()

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    assert not (consumer / "AGENTS.md").exists(), (
        "Installer must NOT write to a consumer lacking a .dadaia/agentic/ marker."
    )

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "[skip]" in combined and "no .dadaia/ marker" in combined, (
        f"Expected skip log line not found in output.\n  Output: {combined!r}"
    )


# ---------------------------------------------------------------------------
# Case 4 — Skip variant: self-slug (R14, package_version match)
# ---------------------------------------------------------------------------


def test_skip_self_slug_package_version_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """dadaia-workspace's own repo is self-skipped via package_version match.

    R14: When the `package_version` in `<repo>/.dadaia/agentic/manifest.json`
    matches the source's own package version, the installer recognises the repo
    as itself (or a mirror at the same version) and skips it — it must NEVER
    overwrite its own source files.

    Given:
      - A consumer repo whose manifest.json `package_version` equals the
        currently installed dadaia-workspace package version.

    When:
      - `_install_workspace_guardrail_pair` processes that consumer.

    Then:
      - The consumer directory is not written to (no AGENTS.md or CLAUDE.md created).
      - The installer does NOT raise; it silently self-skips with a log line.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    own_version = _package_version()

    # Consumer manifests the same package_version — this is the "self" repo
    consumer = workspace_root / "repos" / "dadaia-workspace"
    consumer.mkdir(parents=True)
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        f'{{"package_version": "{own_version}"}}\n', encoding="utf-8"
    )

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    assert not (consumer / "AGENTS.md").exists(), (
        "Installer must NOT write AGENTS.md to the self-slug consumer (package_version match).\n"
        f"  own_version: {own_version}"
    )
    assert not (consumer / "CLAUDE.md").exists(), (
        "Installer must NOT write CLAUDE.md to the self-slug consumer (package_version match).\n"
        f"  own_version: {own_version}"
    )

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "[skip]" in combined and "self-projection" in combined, (
        f"Expected self-projection skip log line not found in output.\n  Output: {combined!r}"
    )


# ---------------------------------------------------------------------------
# Case 5 — Nested-pair non-interference
# ---------------------------------------------------------------------------


def test_nested_pair_non_interference(tmp_path: Path) -> None:
    """Operator-authored services/CLAUDE.md + services/AGENTS.md are NOT touched.

    FR10: Files at `services/CLAUDE.md` and `services/AGENTS.md` are
    operator-authored (not lib-originated). The guardrail installer must not
    modify them — it only writes to workspace-root and consumer-repo roots.

    Given:
      - `services/CLAUDE.md` and `services/AGENTS.md` exist with known content
        BEFORE `_install_workspace_guardrail_pair` is called.

    When:
      - `_install_workspace_guardrail_pair` is called with force=True.

    Then:
      - `services/CLAUDE.md` and `services/AGENTS.md` remain byte-identical to
        their pre-call content.
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
        "services/AGENTS.md was modified by the installer — it must remain untouched (FR10)."
    )
    assert services_claude.read_bytes() == operator_claude_content, (
        "services/CLAUDE.md was modified by the installer — it must remain untouched (FR10)."
    )


# ---------------------------------------------------------------------------
# Case 6 — Doctor 4-line output exactly
# ---------------------------------------------------------------------------


def test_doctor_four_line_output(tmp_path: Path) -> None:
    """`_doctor_guardrail_pair` emits exactly 4 parity lines for 1 consumer.

    Given:
      - A fully installed guardrail pair (4 destinations written).
      - One consumer repo slug (e.g., `some-consumer`).

    When:
      - `_doctor_guardrail_pair` is called against the same workspace.

    Then:
      - The returned list contains exactly 4 lines.
      - The 4 labels are exactly:
          `root:AGENTS.md`
          `root:CLAUDE.md`
          `repos/<slug>:AGENTS.md`
          `repos/<slug>:CLAUDE.md`
      - All 4 lines report `[ok]` (files are byte-identical to source).
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    slug = "some-consumer"
    consumer = workspace_root / "repos" / slug
    consumer.mkdir(parents=True)
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        '{"package_version": "0.0.0"}\n', encoding="utf-8"
    )

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    lines = _doctor_guardrail_pair(source, workspace_root)

    expected_labels = {
        "root:AGENTS.md",
        "root:CLAUDE.md",
        f"repos/{slug}:AGENTS.md",
        f"repos/{slug}:CLAUDE.md",
    }
    actual_labels = {ln.split(" ", 1)[1] for ln in lines if " " in ln}

    assert actual_labels == expected_labels, (
        f"Doctor labels mismatch.\n  Expected: {expected_labels}\n  Got: {actual_labels}"
    )
    assert len(lines) == 4, (
        f"Expected exactly 4 parity lines, found {len(lines)}.\n  Lines: {lines}"
    )
    assert all(ln.startswith("[ok]") for ln in lines), (
        f"All parity lines should be [ok] after install.\n  Lines: {lines}"
    )


# ---------------------------------------------------------------------------
# Case 7 — Option C invariant: data/CLAUDE.md MUST NOT exist as a source
# ---------------------------------------------------------------------------


def test_no_data_claude_md_source() -> None:
    """Option C invariant: ``data/CLAUDE.md`` MUST NOT EXIST in the lib.

    The architect ADR ``2026-05-19T003956Z-adr-claude-agents-parity`` resolved
    the lib pair to **Option C** — a single source file
    (``dadaia_workspace/public/data/AGENTS.md``) projected under two filenames
    (``AGENTS.md`` and ``CLAUDE.md``) at every target. The companion
    ``data/CLAUDE.md`` source file MUST NOT exist; if it did, two divergent
    sources of truth would race for the same projection targets.

    This test anchors the invariant at unit-test layer so future refactors
    cannot reintroduce ``data/CLAUDE.md`` silently.
    """
    repo_root = Path(__file__).resolve().parents[4]  # → dadaia-workspace repo root
    forbidden = repo_root / "dadaia_workspace" / "public" / "data" / "CLAUDE.md"
    assert not forbidden.exists(), (
        "Option C invariant violated: dadaia_workspace/public/data/CLAUDE.md "
        "MUST NOT EXIST. The single source of truth is data/AGENTS.md, "
        "projected under both filenames at install time.\n"
        f"  Unexpected path: {forbidden}"
    )


# ---------------------------------------------------------------------------
# Case 8 — Install call-site dispatch (AGT-r2-35)
# ---------------------------------------------------------------------------


def test_install_dispatches_to_workspace_guardrail_pair(tmp_path: Path) -> None:
    """FileSystemPublicAssetManager.install() calls _install_workspace_guardrail_pair
    once for data/AGENTS.md, producing 4 guardrail files per run.

    AGT-r2-35 acceptance: when `data/AGENTS.md` is present in the staged agentic dir,
    `install()` must write exactly 4 guardrail files:
      * workspace-root / AGENTS.md
      * workspace-root / CLAUDE.md
      * <consumer> / AGENTS.md
      * <consumer> / CLAUDE.md

    Setup:
      - A minimal pre-staged agentic dir (manifest.json + data/AGENTS.md).
      - One marker-bearing consumer repo under repos/ with a distinct package_version.
      - FileSystemPublicAssetManager._public_dir pointed at a minimal stub public dir
        containing only data/AGENTS.md (so stage() is a no-op and install() proceeds
        against the pre-staged agentic dir).

    After install(force=True):
      - All 4 destination paths exist and are byte-identical to the source.
    """
    guardrail_content = b"# AGENTS guardrail - install dispatch test\n"

    # Build a minimal workspace
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Pre-stage the agentic dir so install() skips stage()
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    (agentic_dir / "data").mkdir(parents=True)
    source = agentic_dir / "data" / "AGENTS.md"
    source.write_bytes(guardrail_content)

    # Minimal manifest so install() skips stage()
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0-test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [{"path": "data/AGENTS.md", "sha256": "aa", "type": "data"}],
    }
    (agentic_dir / "manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")

    # One marker-bearing consumer with a distinct (non-self) package_version
    consumer = workspace_root / "repos" / "dadaia-bots"
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    consumer_manifest = {"schema_version": "1", "package_version": "0.0.0"}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        __import__("json").dumps(consumer_manifest), encoding="utf-8"
    )

    # Instantiate the manager with a minimal public dir stub (only data/AGENTS.md)
    public_stub = tmp_path / "public"
    (public_stub / "data").mkdir(parents=True)
    (public_stub / "data" / "AGENTS.md").write_bytes(guardrail_content)

    manager = FileSystemPublicAssetManager()
    # Redirect _public_dir to the stub so runtime_expectations uses the stub
    manager._public_dir = public_stub  # type: ignore[assignment]

    installed = manager.install(workspace_root, target="all", force=True)

    # All 4 guardrail destinations must exist and be byte-identical to source
    import hashlib

    expected_sha = hashlib.sha256(guardrail_content).hexdigest()

    destinations = [
        workspace_root / "AGENTS.md",
        workspace_root / "CLAUDE.md",
        consumer / "AGENTS.md",
        consumer / "CLAUDE.md",
    ]

    for dest in destinations:
        assert dest.exists(), f"Expected guardrail destination missing: {dest}"
        actual_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, (
            f"Destination {dest.name} is not byte-identical to source.\n"
            f"  source sha256: {expected_sha}\n"
            f"  dest   sha256: {actual_sha}"
        )

    ok_guardrail = [e for e in installed if "AGENTS.md" in e or "CLAUDE.md" in e]
    assert len(ok_guardrail) >= 4, (
        f"Expected at least 4 guardrail entries in installed list, got {len(ok_guardrail)}.\n"
        f"  installed: {installed}"
    )
