"""Placeholder test suite — AGT-r2-23.

Tests for `_install_workspace_guardrail_pair` in
`dadaia_workspace.infrastructure.public_assets`.

The installer function does NOT yet exist (it is authored in P9 — AGT-r2-25).
All 6 cases below are marked xfail or skipped with the reason
"implemented in P9: AGT-r2-27", where real assertions will land once the
installer is built and the integration test phase (AGT-r2-27) executes.

When P9 lands:
1. Remove the xfail / skip decorators from each case.
2. Fill in the assertion bodies following the scenario descriptions.
3. Confirm all 6 cases go green under pytest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module-level import guard
# ---------------------------------------------------------------------------
# The target function does not exist yet; importing it here would crash the
# entire module at collection time.  We defer the import into each test body
# so pytest can still collect all 6 cases and report them as xfail / skip.
# ---------------------------------------------------------------------------

_REASON = "implemented in P9: AGT-r2-27"

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


# ---------------------------------------------------------------------------
# Case 1 — 4-target projection write
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason=_REASON, strict=False, raises=(ImportError, NotImplementedError))
def test_four_target_projection_write(tmp_path: Path) -> None:
    """Single source `data/AGENTS.md` fans out to 4 destinations.

    Given:
      - A source file at `<agentic_dir>/data/AGENTS.md` with known content.
      - A workspace root directory.
      - One consumer repo directory under `repos/`.

    When:
      - `_install_workspace_guardrail_pair` is called.

    Then:
      - All 4 destination files are written:
          * workspace-root / AGENTS.md
          * workspace-root / CLAUDE.md
          * workspace-root / repos/<slug> / AGENTS.md
          * workspace-root / repos/<slug> / CLAUDE.md
      - All 4 files are byte-identical to the source (verified via SHA-256).
    """
    from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
        _install_workspace_guardrail_pair,
    )

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

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    import hashlib

    def sha256(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    expected = sha256(source)
    destinations = [
        workspace_root / "AGENTS.md",
        workspace_root / "CLAUDE.md",
        consumer / "AGENTS.md",
        consumer / "CLAUDE.md",
    ]
    for dest in destinations:
        assert dest.exists(), f"Expected destination missing: {dest}"
        assert sha256(dest) == expected, (
            f"Destination {dest} is not byte-identical to source.\n"
            f"  source sha256: {expected}\n"
            f"  dest   sha256: {sha256(dest)}"
        )


# ---------------------------------------------------------------------------
# Case 2 — Skip variant: no `.dadaia/` marker
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason=_REASON, strict=False, raises=(ImportError, NotImplementedError))
def test_skip_no_dadaia_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Consumer dir without `.dadaia/` is silently skipped.

    Given:
      - A consumer repo directory that has NO `.dadaia/` subdirectory.

    When:
      - `_install_workspace_guardrail_pair` processes that consumer.

    Then:
      - The consumer directory is not written to.
      - The installer logs: `[skip] <path> (no .dadaia/ marker)`.
    """
    from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
        _install_workspace_guardrail_pair,
    )

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


@pytest.mark.xfail(reason=_REASON, strict=False, raises=(ImportError, NotImplementedError))
def test_skip_no_agentic_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Consumer dir with `.dadaia/` but no `.dadaia/agentic/` is silently skipped.

    Given:
      - A consumer repo directory that has `.dadaia/` but NOT `.dadaia/agentic/`.

    When:
      - `_install_workspace_guardrail_pair` processes that consumer.

    Then:
      - The consumer directory is not written to.
      - The installer logs: `[skip] <path> (no .dadaia/ marker)`.
    """
    from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
        _install_workspace_guardrail_pair,
    )

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


@pytest.mark.xfail(reason=_REASON, strict=False, raises=(ImportError, NotImplementedError))
def test_skip_self_slug_package_version_match(tmp_path: Path) -> None:
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
      - The consumer directory is not written to.
      - The installer does NOT raise; it silently self-skips.
    """
    from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
        _install_workspace_guardrail_pair,
        _package_version,
    )

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

    agents_before = (consumer / "AGENTS.md").exists()

    _install_workspace_guardrail_pair(source, workspace_root, force=True)

    agents_after = (consumer / "AGENTS.md").exists()
    assert agents_before == agents_after, (
        "Installer must NOT write to the self-slug consumer (package_version match).\n"
        f"  AGENTS.md existed before: {agents_before}, after: {agents_after}"
    )


# ---------------------------------------------------------------------------
# Case 5 — Nested-pair non-interference
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason=_REASON, strict=False, raises=(ImportError, NotImplementedError))
def test_nested_pair_non_interference(tmp_path: Path) -> None:
    """Operator-authored services/CLAUDE.md + services/AGENTS.md are NOT touched.

    FR10: Files at `services/CLAUDE.md` and `services/AGENTS.md` are
    operator-authored (not lib-originated). The guardrail installer must not
    modify them.

    Given:
      - `services/CLAUDE.md` and `services/AGENTS.md` exist with known content.

    When:
      - `_install_workspace_guardrail_pair` is called.

    Then:
      - `services/CLAUDE.md` and `services/AGENTS.md` remain byte-identical to
        their pre-call content.
    """
    from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
        _install_workspace_guardrail_pair,
    )

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


@pytest.mark.xfail(reason=_REASON, strict=False, raises=(ImportError, NotImplementedError))
def test_doctor_four_line_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`dadaia public doctor` emits exactly 4 parity lines per source.

    Given:
      - A fully installed guardrail pair (4 destinations written).
      - One consumer repo slug (e.g., `some-consumer`).

    When:
      - The doctor parity check runs (exercised here via the public_assets API).

    Then:
      - The output contains exactly 4 lines of the form:
          `root:AGENTS.md`
          `root:CLAUDE.md`
          `repos/<slug>:AGENTS.md`
          `repos/<slug>:CLAUDE.md`
      - No extra parity lines appear; no lines are missing.
    """
    from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
        _install_workspace_guardrail_pair,
        _doctor_guardrail_pair,
    )

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

    _doctor_guardrail_pair(source, workspace_root)

    captured = capsys.readouterr()
    combined = captured.out + captured.err

    expected_lines = {
        "root:AGENTS.md",
        "root:CLAUDE.md",
        f"repos/{slug}:AGENTS.md",
        f"repos/{slug}:CLAUDE.md",
    }
    for line_key in expected_lines:
        assert line_key in combined, (
            f"Doctor output missing expected parity line: {line_key!r}\n"
            f"  Full output: {combined!r}"
        )

    parity_lines = [
        ln for ln in combined.splitlines()
        if any(k in ln for k in expected_lines)
    ]
    assert len(parity_lines) == 4, (
        f"Expected exactly 4 parity lines, found {len(parity_lines)}.\n"
        f"  Parity lines: {parity_lines}\n"
        f"  Full output: {combined!r}"
    )
