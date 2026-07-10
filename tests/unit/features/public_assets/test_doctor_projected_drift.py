"""Unit tests for T-PROP-02: doctor staging-vs-projected drift detection.

Verifies that `dadaia public doctor` (via FileSystemPublicAssetManager.doctor):
1. Exits 0 and emits [ok] for every staged asset on a clean workspace.
2. Exits non-zero (via the CLI) and emits [drift] for staged assets whose SHA
   differs from their projected counterparts.
3. Emits [missing] / exits non-zero when a staged asset has no projected file.

Doctor drift detection gates agent dispatch, so both failure modes ([drift] and
[missing]) are kept as named tests; the clean/[ok] path (incl. the scripts
staging↔projected facet) and the CLI exit-code propagation are each merged into
one parametrized test.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
)


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_manager(public_dir: Path) -> FileSystemPublicAssetManager:
    mgr = FileSystemPublicAssetManager.__new__(FileSystemPublicAssetManager)
    mgr._public_dir = public_dir
    return mgr


def test_projected_drift_exits_nonzero(tmp_path: Path) -> None:
    """T-PROP-02 AC-1: staged SHA differs from projected → [drift] emitted."""
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    mgr = _make_manager(public_dir)

    staged = tmp_path / "staged.md"
    projected = tmp_path / "projected.md"
    _write(staged, b"# new staged content\n")
    _write(projected, b"# old projected content\n")

    line = mgr._compare(staged, projected, "stage:test.md")
    assert line.startswith("[drift]"), f"Expected [drift], got: {line!r}"


def test_staged_but_not_installed_exits_nonzero(tmp_path: Path) -> None:
    """T-PROP-02 AC-3: staged asset with no projection → [missing] emitted."""
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    mgr = _make_manager(public_dir)

    staged = tmp_path / "staged.md"
    projected = tmp_path / "non_existent.md"
    _write(staged, b"# some content\n")
    # projected does NOT exist

    line = mgr._compare(staged, projected, "stage:test.md")
    assert line.startswith("[missing]"), f"Expected [missing], got: {line!r}"


def test_clean_ok_paths_incl_scripts(tmp_path: Path) -> None:
    """T-PROP-02 AC-2: identical staged/projected content is [ok], for both plain
    file pairs and the scripts staging↔projected expectation generator."""
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    mgr = _make_manager(public_dir)

    staged = tmp_path / "staged.md"
    projected = tmp_path / "projected.md"
    content = b"# identical content\n"
    _write(staged, content)
    _write(projected, content)
    line = mgr._compare(staged, projected, "stage:test.md")
    assert line.startswith("[ok]"), f"Expected [ok], got: {line!r}"
    assert "[drift]" not in line
    assert "[missing]" not in line

    # Scripts: matching staged/projected script content → [ok].
    workspace = tmp_path / "ws"
    workspace.mkdir()
    agentic_scripts = workspace / ".dadaia" / "agentic" / "scripts"
    agentic_scripts.mkdir(parents=True)
    script_content = b"#!/bin/bash\necho hello\n"
    _write(agentic_scripts / "hook.sh", script_content)
    projected_scripts = workspace / ".dadaia" / "scripts"
    projected_scripts.mkdir(parents=True)
    _write(projected_scripts / "hook.sh", script_content)

    agentic_dir = workspace / ".dadaia" / "agentic"
    expectations = list(mgr._runtime_expectations(agentic_dir, workspace))
    script_expectations = [
        (src, dst, label, transform)
        for (src, dst, label, transform) in expectations
        if src is not None and "scripts" in str(src) and "hook.sh" in str(src)
    ]
    assert script_expectations, (
        "Expected at least one scripts expectation for hook.sh; "
        f"got expectations: {[lbl for (_, _, lbl, _) in expectations]}"
    )
    src, dst, label, _transform = script_expectations[0]
    script_line = mgr._compare(src, dst, label)
    assert script_line.startswith("[ok]"), f"Expected [ok] for matching scripts, got: {script_line!r}"


@pytest.mark.parametrize(
    ("reports", "expect_zero"),
    [
        pytest.param(["[ok] stage:foo.md", "[ok] claude:rules/bar.md"], True, id="all-ok-exits-0"),
        pytest.param(
            ["[ok] stage:foo.md", "[drift] stage:scripts/hook.sh"],
            False,
            id="drift-exits-nonzero",
        ),
        pytest.param(
            ["[ok] stage:foo.md", "[missing] claude:rules/bar.md"],
            False,
            id="missing-exits-nonzero",
        ),
    ],
)
def test_cli_exit_code_propagation(tmp_path: Path, reports: list[str], expect_zero: bool) -> None:
    """The CLI doctor command must propagate [drift]/[missing] to a non-zero exit."""
    from typer.testing import CliRunner

    from dadaia_workspace.cli.commands.public import app

    with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
        mock_svc = MagicMock()
        mock_svc.doctor.return_value = reports
        mock_container.build_public_service.return_value = mock_svc

        with patch(
            "dadaia_workspace.cli.commands.public.resolve_workspace_root",
            return_value=tmp_path,
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor"])

    if expect_zero:
        assert result.exit_code == 0, (
            f"Expected exit code 0, got {result.exit_code}. Output: {result.output}"
        )
    else:
        assert result.exit_code != 0, (
            f"Expected non-zero exit code, got {result.exit_code}. Output: {result.output}"
        )
