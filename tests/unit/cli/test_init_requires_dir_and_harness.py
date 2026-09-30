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
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.infrastructure import python_env as pe

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


def _foreign(tmp: Path, mp: pytest.MonkeyPatch) -> Path:
    (tmp / "demo").mkdir()
    (tmp / "demo" / "somebody-elses-file.txt").write_text("keep me", encoding="utf-8")
    return tmp


def _foreign_cwd(tmp: Path, mp: pytest.MonkeyPatch) -> Path:
    (tmp / "proj").mkdir()
    (tmp / "proj" / "README.md").write_text("mine", encoding="utf-8")
    return tmp / "proj"


def _bootstrap_fails(tmp: Path, mp: pytest.MonkeyPatch) -> Path:
    def _raise(self: object, root: str) -> None:
        raise pe.WorkspaceVenvBootstrapError(
            "point DADAIA_BOOTSTRAP_PACKAGE at the local wheel file and retry"
        )

    mp.setattr(pe.VenvPythonEnvironmentManager, "ensure_workspace_venv", _raise)
    return tmp


# fmt: off
@pytest.mark.parametrize(("argv", "setup", "code", "fix", "in_output"), [
    pytest.param(["init", "demo"], None, 1, "uvx dadaia-workspace init demo --harness ", [], id="AC2.1-no-harness-default"),
    pytest.param(["init", "--harness", "claude"], None, 1, None, [], id="no-dir-never-targets-cwd"),
    *[pytest.param(["init", "demo", "--harness", v], None, 2, None, ["claude", v], id=f"meta-or-unknown-{v}") for v in ("all", "claude,codex", "zzz")],
    pytest.param(["init", "demo", "--harness", "claude"], _foreign, 1, None, [], id="foreign-tree-never-scaffolded-over"),
    pytest.param(["init", ".", "--harness", "claude"], _foreign_cwd, 1, "uvx dadaia-workspace init {tmp}/proj-workspace --harness claude", [],
                 id="init-foreign-tree-fix-line-unrunnable-sibling-from-the-resolved-path"),
    pytest.param(["init", "/", "--harness", "claude"], None, 1, "uvx dadaia-workspace init {root}dadaia-workspace --harness claude", [],
                 id="init-root-dir-crashes-deriving-sibling-fix"),
    pytest.param(["init", "demo", "--harness", "claude"], _bootstrap_fails, 1, None, ["DADAIA_BOOTSTRAP_PACKAGE"], id="validation-028-bootstrap-error-clean-exit"),
])
# fmt: on
def test_init_refuses_meta_and_unknown_harness_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str], setup: Callable[[Path, pytest.MonkeyPatch], Path] | None,
    code: int, fix: str | None, in_output: list[str],
) -> None:  # fmt: skip
    """Each refusal exits non-zero, scaffolds nothing, never tracebacks; a usage error (exit 2) lists the
    registered harnesses on stderr with an empty stdout; a fixable one prints exactly ONE `fix:` line."""
    monkeypatch.chdir(setup(tmp_path, monkeypatch) if setup else tmp_path)

    result = _runner.invoke(app, argv)

    assert result.exit_code == code, result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "demo" / ".dadaia").exists() and not (tmp_path / ".dadaia").exists()
    assert all(part in result.output for part in in_output)
    if code == 2:
        assert result.stdout == ""
    if fix:
        expected = fix.format(tmp=tmp_path.as_posix(), root=Path("/").resolve().as_posix().rstrip("/") + "/")
        assert _the_fix(result.output).replace("\\", "/").startswith(expected)
    if setup is _foreign:
        assert (tmp_path / "demo" / "somebody-elses-file.txt").read_text(encoding="utf-8") == "keep me"


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
