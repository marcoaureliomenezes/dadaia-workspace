"""Real assertions for `_install_workspace_guardrail_pair`.

Tests for `_install_workspace_guardrail_pair` and `_doctor_guardrail_pair` in
`dadaia_workspace.infrastructure.public_assets`, plus the Option C absence
invariant for `dadaia_workspace/public/data/CLAUDE.md`.

Seven cases covering:
1. 4-target projection write (byte-identical, single SHA-256).
2. Skip when consumer has no `.dadaia/` marker.
3. Skip when consumer has `.dadaia/` but no `.dadaia/agentic/` marker.
4. Self-slug skip via `package_version` match (R14).
5. Nested-pair non-interference: `services/CLAUDE.md` + `services/AGENTS.md` untouched (FR10).
6. Doctor produces exactly 4 parity labels per source.
7. Option C invariant: `data/CLAUDE.md` MUST NOT exist as a source file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
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


# ---------------------------------------------------------------------------
# Case 1 — 4-target projection write
# ---------------------------------------------------------------------------


def test_four_target_projection_write(tmp_path: Path) -> None:
    """Single source `data/AGENTS.md` fans out to 4 destinations.

    Given:
      - A source file at `<agentic_dir>/data/AGENTS.md` with known content.
      - A workspace root directory.
      - One consumer repo registered in `spec_contexts.json` (v0.1.58 FR4
        registry-based detection — INVERT of the dead in-repo marker, Ruling G),
        marker-less on disk (so it is NOT self-skipped).

    When:
      - `_install_workspace_guardrail_pair` is called with force=True.

    Then:
      - All 4 destination files are written:
          * workspace-root / AGENTS.md
          * workspace-root / CLAUDE.md
          * workspace-root / repos/<slug> / AGENTS.md
          * workspace-root / repos/<slug> / CLAUDE.md
      - AGENTS.md files are byte-identical to the source (full canonical content).
      - CLAUDE.md files contain the 1-line stub only (T-41: delegates to AGENTS.md).
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

    # AGENTS.md destinations must be byte-identical to source.
    agents_destinations = [
        workspace_root / "AGENTS.md",
        consumer / "AGENTS.md",
    ]
    for dest in agents_destinations:
        assert dest.exists(), f"Expected AGENTS.md destination missing: {dest}"
        assert sha256(dest) == expected_agents_sha, (
            f"AGENTS.md at {dest} is not byte-identical to source.\n"
            f"  source sha256: {expected_agents_sha}\n"
            f"  dest   sha256: {sha256(dest)}"
        )

    # CLAUDE.md destinations must be the 1-line stub (T-41).
    claude_destinations = [
        workspace_root / "CLAUDE.md",
        consumer / "CLAUDE.md",
    ]
    for dest in claude_destinations:
        assert dest.exists(), f"Expected CLAUDE.md destination missing: {dest}"
        assert dest.read_text(encoding="utf-8") == _CLAUDE_MD_STUB, (
            f"CLAUDE.md at {dest} must contain only the 1-line stub (T-41).\n"
            f"  Expected: {_CLAUDE_MD_STUB!r}\n"
            f"  Got:      {dest.read_text(encoding='utf-8')!r}"
        )

    ok_entries = [e for e in installed if e.startswith("[ok]")]
    assert len(ok_entries) == 4, (
        f"Expected exactly 4 '[ok]' entries in installed list, got {len(ok_entries)}.\n"
        f"  installed: {installed}"
    )


# ---------------------------------------------------------------------------
# Case 2 — INVERT: an unregistered on-disk repo is not written (registry detection)
# ---------------------------------------------------------------------------
# (Case 3 — "no .dadaia/agentic/ marker" — DELETED at v0.1.58 W4: the in-repo
#  marker distinction it exercised no longer exists; detection is registry-based,
#  so it has no invertible assertion distinct from this inverted Case 2.)


def test_unregistered_repo_not_written(tmp_path: Path) -> None:
    """A repo present on disk under `repos/` but NOT registered in
    `spec_contexts.json` is not written to (v0.1.58 FR4 registry-based
    detection, Ruling G — INVERT of the old marker-skip). The old
    `[skip] ... (no .dadaia/ marker)` stderr line no longer exists.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # On-disk but NOT registered → invisible to the fan-out.
    consumer = workspace_root / "repos" / "unregistered-repo"
    consumer.mkdir(parents=True)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    assert not (consumer / "AGENTS.md").exists(), (
        "Installer must NOT write to a repo that is not registered in spec_contexts.json."
    )
    assert not (consumer / "CLAUDE.md").exists()


# ---------------------------------------------------------------------------
# Case 4 — Skip variant: self-slug (R14, package_version match) — RETAINED
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

    # Registry-listed self repo whose manifest package_version matches the
    # installed version — detected via the registry (v0.1.58 FR4) then self-skipped
    # via the RETAINED _is_self_repo package_version match (R14).
    consumer = workspace_root / "repos" / "dadaia-workspace"
    consumer.mkdir(parents=True)
    (consumer / ".dadaia" / "agentic").mkdir(parents=True)
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        f'{{"package_version": "{own_version}"}}\n', encoding="utf-8"
    )
    _register_context(workspace_root, "dadaia-workspace")

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
      - The returned list contains exactly 4 lines with the 4 labels
        (`root:AGENTS.md`, `root:CLAUDE.md`, `repos/<slug>:AGENTS.md`, `repos/<slug>:CLAUDE.md`).
      - v0.1.60 FR9 amendment (doctor-`[ok]`-parity flip, NOT an `[updated]`-on-divergent case
        — QA-1 misattribution correction): the source here is BANNERLESS, so the consumer pair
        classifies `[foreign]` (repo-owned) while the lib-owned root pair keeps `[ok]`.
    """
    source = tmp_path / "data" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"# AGENTS\n")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    slug = "some-consumer"
    # Registry-listed, marker-less consumer (v0.1.58 FR4).
    consumer = workspace_root / "repos" / slug
    consumer.mkdir(parents=True)
    _register_context(workspace_root, slug)

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    lines = _doctor_guardrail_pair(source, workspace_root)

    expected_labels = {
        "root:AGENTS.md",
        "root:CLAUDE.md",
        f"repos/{slug}:AGENTS.md",
        f"repos/{slug}:CLAUDE.md",
    }
    status = {ln.split(" ", 1)[1]: ln.split(" ", 1)[0] for ln in lines if " " in ln}

    assert set(status) == expected_labels, (
        f"Doctor labels mismatch.\n  Expected: {expected_labels}\n  Got: {set(status)}"
    )
    assert len(lines) == 4, (
        f"Expected exactly 4 parity lines, found {len(lines)}.\n  Lines: {lines}"
    )
    # Root pair (lib-owned) is [ok]; the consumer pair (bannerless source) is [foreign].
    assert status["root:AGENTS.md"] == "[ok]", lines
    assert status["root:CLAUDE.md"] == "[ok]", lines
    assert status[f"repos/{slug}:AGENTS.md"] == "[foreign]", lines
    assert status[f"repos/{slug}:CLAUDE.md"] == "[foreign]", lines


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
