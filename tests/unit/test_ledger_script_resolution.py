"""Intent: CONTRACT — 0.4.7 review fold (T-047-70): a ledger script is executed only
from the workspace this process was launched from.

`script_findings` runs whatever `resolve_script` hands it. Resolution used to walk up
from the caller-supplied `--specs-dir` and take the FIRST `.agents/skills/` it found, so
pointing the doctor at any tree that carried one executed that tree's Python (CWE-427,
untrusted search path). Resolution now asks one question: is this specs tree inside the
workspace whose `.dadaia/.venv/` holds my interpreter? Yes — the operator's installed
tree. No — the packaged copy that shipped with this distribution.

size: SMALL.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure import ledger_scripts

_PACKAGE_SKILLS = Path(ledger_scripts.__file__).resolve().parents[1] / "public" / "skills"
_SCRIPT = ledger_scripts.LEDGER_SCRIPTS[0]


def _tree_with_skills(root: Path) -> Path:
    """A workspace-shaped tree carrying an installed script at the expected path."""
    (root / "specs").mkdir(parents=True, exist_ok=True)
    scripts = root / ".agents" / "skills" / _SCRIPT.skill / "scripts"
    scripts.mkdir(parents=True)
    (scripts / _SCRIPT.filename).write_text("", encoding="utf-8")
    return scripts / _SCRIPT.filename


def _launch_from(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend this process's interpreter is *root*'s venv Python."""
    interpreter = root / ".dadaia" / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(interpreter))


def test_the_running_workspaces_installed_tree_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = _tree_with_skills(tmp_path)
    _launch_from(tmp_path, monkeypatch)

    assert ledger_scripts.resolve_script(_SCRIPT, tmp_path / "specs") == installed


def test_a_foreign_trees_installed_tree_is_never_executed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The attack: a tree the operator merely pointed the doctor at carries its own
    `.agents/skills/bugs.py`. It must not be the file that runs."""
    foreign = tmp_path / "foreign"
    planted = _tree_with_skills(foreign)
    _launch_from(tmp_path / "mine", monkeypatch)

    resolved = ledger_scripts.resolve_script(_SCRIPT, foreign / "specs")

    assert resolved != planted
    assert resolved == _PACKAGE_SKILLS / _SCRIPT.skill / "scripts" / _SCRIPT.filename
