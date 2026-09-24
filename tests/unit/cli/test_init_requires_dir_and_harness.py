"""Intent: CONTRACT — 0.4.7 FR1/AC2.1 (T-047-73): `init <dir> --harness <name>`.

The bootstrap seam is argv: the workspace directory is a PARAMETER, never resolved from
cwd, and the harness is exactly ONE registered record. The three refusals asserted here
are the whole interface contract — a missing `<dir>`, a missing `--harness`, and the
retired meta-values (`all`, the comma subset) — each exiting 2 with exactly one
executable `fix:` line, plus the idempotence clause that makes a re-run a no-op.

size: SMALL.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()
_FIX_LINE_RE = re.compile(r"^fix: (\S.*)$", re.MULTILINE)


def _the_fix(output: str) -> str:
    """Return the ONE ``fix:`` command carried by *output* (fails the test otherwise)."""
    fixes = _FIX_LINE_RE.findall(output)
    assert len(fixes) == 1, f"expected exactly one 'fix:' line, got {fixes} in:\n{output}"
    return fixes[0]


def _tree(root: Path) -> dict[str, str]:
    """Every file under *root* as ``relative path -> sha256`` (symlinks by target)."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            snapshot[rel] = f"symlink:{path.readlink()}"
        elif path.is_file():
            snapshot[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            snapshot[rel] = "dir"
    return snapshot


def test_init_without_harness_exits_2_with_one_fix_line(tmp_path: Path, monkeypatch) -> None:
    """AC2.1 first clause: `--harness` has no default — `all` is not implied."""
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["init", "demo"])

    assert result.exit_code == 2, result.output
    assert _the_fix(result.output).startswith("uvx dadaia-workspace init demo --harness ")
    assert not (tmp_path / "demo" / ".dadaia").exists(), "a refused init scaffolds nothing"


def test_init_without_dir_exits_2(tmp_path: Path, monkeypatch) -> None:
    """The directory is a parameter: no positional means no cwd fallback, just a refusal."""
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["init", "--harness", "claude"])

    assert result.exit_code == 2, result.output
    assert not (tmp_path / ".dadaia").exists(), "a bare init never targets cwd"


@pytest.mark.parametrize("value", ["all", "claude,codex", "zzz"])
def test_init_refuses_meta_and_unknown_harness_values(
    value: str, tmp_path: Path, monkeypatch
) -> None:
    """`all` and the comma subset died with `parse_harness_set`; both are now unknown names."""
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["init", "demo", "--harness", value])

    assert result.exit_code == 2, result.output
    assert "claude" in result.output, "the refusal lists the registered harnesses"
    assert not (tmp_path / "demo" / ".dadaia").exists()


def test_init_refuses_a_directory_holding_a_foreign_tree(tmp_path: Path, monkeypatch) -> None:
    """A non-empty directory that is not already a workspace is never scaffolded over."""
    monkeypatch.chdir(tmp_path)
    foreign = tmp_path / "demo"
    foreign.mkdir()
    (foreign / "somebody-elses-file.txt").write_text("keep me", encoding="utf-8")

    result = _runner.invoke(app, ["init", "demo", "--harness", "claude"])

    assert result.exit_code == 2, result.output
    assert not (foreign / ".dadaia").exists()
    assert (foreign / "somebody-elses-file.txt").read_text(encoding="utf-8") == "keep me"


def test_init_creates_the_named_dir_and_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    """The dir is created if absent; a second identical `init` changes nothing (AC2.1)."""
    monkeypatch.chdir(tmp_path)

    first = _runner.invoke(app, ["init", "demo", "--harness", "claude", "--skip-assets"])
    assert first.exit_code == 0, first.output
    demo = tmp_path / "demo"
    assert (demo / ".dadaia" / "states" / "spec_contexts.json").exists()
    before = _tree(demo)

    second = _runner.invoke(app, ["init", "demo", "--harness", "claude", "--skip-assets"])
    assert second.exit_code == 0, second.output

    assert _tree(demo) == before, "a re-run of init on the same dir must change nothing"


def test_init_foreign_tree_fix_names_a_runnable_sibling(tmp_path: Path, monkeypatch) -> None:
    """Bug init-foreign-tree-fix-line-unrunnable: `init .` in a non-empty dir suggested
    `dadaia init .-workspace` — the fix is the uvx entry point and a sibling directory
    derived from the RESOLVED path, never the raw argument string-appended."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "README.md").write_text("mine", encoding="utf-8")
    monkeypatch.chdir(project)

    result = _runner.invoke(app, ["init", ".", "--harness", "claude"])

    assert result.exit_code == 2, result.output
    assert _the_fix(result.output) == (
        f"uvx dadaia-workspace init {tmp_path / 'proj-workspace'} --harness claude"
    )
