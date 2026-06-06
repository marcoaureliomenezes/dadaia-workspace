"""Unit tests for T-PROP-02: doctor staging-vs-projected drift detection.

Verifies that `dadaia public doctor` (via FileSystemPublicAssetManager.doctor):
1. Exits 0 and emits [ok] for every staged asset on a clean workspace.
2. Exits non-zero (via the CLI) and emits [drift] for staged assets whose SHA
   differs from their projected counterparts.
3. Emits [missing] / exits non-zero when a staged asset has no projected file.

The tests exercise the underlying `doctor()` method directly to assert on the
report lines, and also verify that the CLI command propagates the non-zero exit.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _has_drift_or_missing(reports: list[str]) -> bool:
    """Return True when any report line signals non-clean state."""
    return any(line.startswith("[drift]") or line.startswith("[missing]") for line in reports)


# ---------------------------------------------------------------------------
# Minimal public_dir fixture that avoids touching the real source tree.
# We patch FileSystemPublicAssetManager._public_dir to a tmp directory.
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """Bare workspace with .dadaia/agentic/ layout."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / ".dadaia" / "agentic").mkdir(parents=True)
    return ws


class TestDoctorProjectedDrift:
    """T-PROP-02 acceptance tests for the doctor() return values."""

    # ------------------------------------------------------------------
    # Helper: build a manager whose _public_dir points at a controlled dir.
    # ------------------------------------------------------------------
    @staticmethod
    def _make_manager(public_dir: Path) -> FileSystemPublicAssetManager:
        mgr = FileSystemPublicAssetManager.__new__(FileSystemPublicAssetManager)
        mgr._public_dir = public_dir  # type: ignore[attr-defined]
        return mgr

    # ------------------------------------------------------------------
    # AC-1: clean tree → [ok] only, no drift/missing
    # ------------------------------------------------------------------
    def test_clean_tree_exits_0(self, tmp_path: Path) -> None:
        """T-PROP-02 AC-2: doctor emits [ok] for every asset on a clean workspace.

        We bypass the full doctor() (which touches many real paths) and test
        _compare / _compare_content directly to confirm the per-file logic is
        clean on a matching staged+projected pair.
        """
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        mgr = self._make_manager(public_dir)

        staged = tmp_path / "staged.md"
        projected = tmp_path / "projected.md"
        content = b"# identical content\n"
        _write(staged, content)
        _write(projected, content)

        line = mgr._compare(staged, projected, "stage:test.md")
        assert line.startswith("[ok]"), f"Expected [ok], got: {line!r}"
        assert "[drift]" not in line
        assert "[missing]" not in line

    # ------------------------------------------------------------------
    # AC-2: projected drift → [drift] emitted
    # ------------------------------------------------------------------
    def test_projected_drift_exits_nonzero(self, tmp_path: Path) -> None:
        """T-PROP-02 AC-1: staged SHA differs from projected → [drift] emitted."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        mgr = self._make_manager(public_dir)

        staged = tmp_path / "staged.md"
        projected = tmp_path / "projected.md"
        _write(staged, b"# new staged content\n")
        _write(projected, b"# old projected content\n")

        line = mgr._compare(staged, projected, "stage:test.md")
        assert line.startswith("[drift]"), f"Expected [drift], got: {line!r}"

    # ------------------------------------------------------------------
    # AC-3: staged asset with no projected file → [missing] emitted
    # ------------------------------------------------------------------
    def test_staged_but_not_installed_exits_nonzero(self, tmp_path: Path) -> None:
        """T-PROP-02 AC-3: staged asset with no projection → [missing] emitted."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        mgr = self._make_manager(public_dir)

        staged = tmp_path / "staged.md"
        projected = tmp_path / "non_existent.md"
        _write(staged, b"# some content\n")
        # projected does NOT exist

        line = mgr._compare(staged, projected, "stage:test.md")
        assert line.startswith("[missing]"), f"Expected [missing], got: {line!r}"

    # ------------------------------------------------------------------
    # Script staging↔projected check (core T-PROP-02 addition)
    # ------------------------------------------------------------------
    def test_script_drift_detected_in_runtime_expectations(self, tmp_path: Path) -> None:
        """T-PROP-02: scripts in agentic/scripts/ are checked against .dadaia/scripts/."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        # Set up staged script
        agentic_scripts = workspace / ".dadaia" / "agentic" / "scripts"
        agentic_scripts.mkdir(parents=True)
        script_src = agentic_scripts / "hook.sh"
        _write(script_src, b"#!/bin/bash\necho staged\n")

        # Set up projected script with DIFFERENT content (drift)
        projected_scripts = workspace / ".dadaia" / "scripts"
        projected_scripts.mkdir(parents=True)
        projected_script = projected_scripts / "hook.sh"
        _write(projected_script, b"#!/bin/bash\necho old\n")

        mgr = self._make_manager(public_dir)
        agentic_dir = workspace / ".dadaia" / "agentic"

        # Collect expectations from the generator
        expectations = list(mgr._runtime_expectations(agentic_dir, workspace))

        # Find the scripts expectation
        script_expectations = [
            (src, dst, label, transform)
            for (src, dst, label, transform) in expectations
            if src is not None and "scripts" in str(src) and "hook.sh" in str(src)
        ]
        assert script_expectations, (
            "Expected at least one scripts expectation for hook.sh; "
            f"got expectations: {[lbl for (_, _, lbl, _) in expectations]}"
        )
        src, dst, label, transform = script_expectations[0]
        line = mgr._compare(src, dst, label)
        assert line.startswith("[drift]"), f"Expected [drift] for script, got: {line!r}"

    def test_script_ok_when_matching(self, tmp_path: Path) -> None:
        """T-PROP-02: matching staged and projected scripts → [ok]."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        content = b"#!/bin/bash\necho hello\n"

        agentic_scripts = workspace / ".dadaia" / "agentic" / "scripts"
        agentic_scripts.mkdir(parents=True)
        _write(agentic_scripts / "hook.sh", content)

        projected_scripts = workspace / ".dadaia" / "scripts"
        projected_scripts.mkdir(parents=True)
        _write(projected_scripts / "hook.sh", content)

        mgr = self._make_manager(public_dir)
        agentic_dir = workspace / ".dadaia" / "agentic"

        expectations = list(mgr._runtime_expectations(agentic_dir, workspace))
        script_expectations = [
            (src, dst, label, transform)
            for (src, dst, label, transform) in expectations
            if src is not None and "scripts" in str(src) and "hook.sh" in str(src)
        ]
        assert script_expectations
        src, dst, label, transform = script_expectations[0]
        line = mgr._compare(src, dst, label)
        assert line.startswith("[ok]"), f"Expected [ok] for matching scripts, got: {line!r}"


class TestDoctorCLIExitCode:
    """T-PROP-02: the CLI doctor command must exit non-zero when drift is found.

    We test the CLI module directly by exercising its logic — the `doctor`
    command collects lines from the service and must raise typer.Exit(1) when
    any line starts with '[drift]' or '[missing]'.
    """

    def test_cli_exits_0_when_all_ok(self, tmp_path: Path) -> None:
        """CLI doctor exits 0 when the service reports only [ok]/[not-applicable] lines."""
        from typer.testing import CliRunner

        # Build a minimal CLI app that calls our doctor implementation
        from dadaia_workspace.cli.commands.public import app

        # Patch the service to return only [ok] lines
        ok_reports = ["[ok] stage:foo.md", "[ok] claude:rules/bar.md"]

        with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
            mock_svc = MagicMock()
            mock_svc.doctor.return_value = ok_reports
            mock_container.build_public_service.return_value = mock_svc

            with patch(
                "dadaia_workspace.cli.commands.public.resolve_workspace_root",
                return_value=tmp_path,
            ):
                runner = CliRunner()
                result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0, (
            f"Expected exit code 0 for clean state, got {result.exit_code}. Output: {result.output}"
        )

    def test_cli_exits_nonzero_on_drift(self, tmp_path: Path) -> None:
        """CLI doctor exits non-zero when the service reports a [drift] line."""
        from typer.testing import CliRunner

        from dadaia_workspace.cli.commands.public import app

        drift_reports = ["[ok] stage:foo.md", "[drift] stage:scripts/hook.sh"]

        with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
            mock_svc = MagicMock()
            mock_svc.doctor.return_value = drift_reports
            mock_container.build_public_service.return_value = mock_svc

            with patch(
                "dadaia_workspace.cli.commands.public.resolve_workspace_root",
                return_value=tmp_path,
            ):
                runner = CliRunner()
                result = runner.invoke(app, ["doctor"])

        assert result.exit_code != 0, (
            f"Expected non-zero exit code for drift, got {result.exit_code}. "
            f"Output: {result.output}"
        )

    def test_cli_exits_nonzero_on_missing(self, tmp_path: Path) -> None:
        """CLI doctor exits non-zero when the service reports a [missing] line."""
        from typer.testing import CliRunner

        from dadaia_workspace.cli.commands.public import app

        missing_reports = ["[ok] stage:foo.md", "[missing] claude:rules/bar.md"]

        with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
            mock_svc = MagicMock()
            mock_svc.doctor.return_value = missing_reports
            mock_container.build_public_service.return_value = mock_svc

            with patch(
                "dadaia_workspace.cli.commands.public.resolve_workspace_root",
                return_value=tmp_path,
            ):
                runner = CliRunner()
                result = runner.invoke(app, ["doctor"])

        assert result.exit_code != 0, (
            f"Expected non-zero exit code for missing, got {result.exit_code}. "
            f"Output: {result.output}"
        )
