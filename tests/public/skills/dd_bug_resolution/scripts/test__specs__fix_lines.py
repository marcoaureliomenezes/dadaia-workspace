"""A fix travels as words and is spelled once: a refusal never nests an Agent action, and a path
with a blank or an unspellable character is one word of the line."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, inline

_K = load_owner("dd-bug-resolution", "_platform")
_S = load_owner("dd-bug-resolution", "_specs")
_L = load_owner("dd-bug-resolution", "_ledger")
_BAD = Path("C:/a!b/bugs.py")  # "!" has no safe spelling on Windows


@pytest.fixture
def win32(monkeypatch: pytest.MonkeyPatch) -> None:
    real = _K.detect
    monkeypatch.setattr(_K, "detect", lambda platform=None: real("win32"))


def _fix_line(capsys: pytest.CaptureFixture[str]) -> str:
    return next(ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("fix: "))


def test_a_choice_over_a_fix_with_an_unspellable_word_is_one_agent_action(
    win32: None, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", [str(_BAD)])
    fix = _S.script(_BAD)("append")
    _S.refuse(_S.choice(_S.Refusal("m", fix), "with a new --bug-id"), Path("specs"))
    line = _fix_line(capsys)
    assert line.count("Agent action:") == 1 and line.startswith("fix: Agent action: run `")
    assert line.endswith("with a new --bug-id")


def test_a_choice_rerun_with_an_unspellable_word_is_one_agent_action(
    win32: None, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", [str(_BAD), "append"])
    _S.refuse(_S.choice(_S.Refusal("m"), "with a new --bug-id"), Path("specs"))
    line = _fix_line(capsys)
    assert line.count("Agent action:") == 1 and line.startswith("fix: Agent action: run `")


def test_a_fix_with_an_unspellable_word_is_one_agent_action(win32: None) -> None:
    assert _S.script(_BAD)("check").count("Agent action:") == 1


def test_unwritten_names_its_git_command_inside_one_agent_action(win32: None) -> None:
    fix = _L.unwritten(Path("C:/a!b/specs/bugs/BUGS.jsonl"), 3, "bugs.py", "the law")
    assert fix.count("Agent action:") == 1 and fix.startswith("Agent action: ")


def test_a_script_path_with_a_blank_is_one_word_of_every_line(tmp_path: Path) -> None:
    path = tmp_path / "a b" / "x.py"
    path.parent.mkdir()
    this = _S.script(path)
    assert this("check", specs=tmp_path / "s p") == command(
        sys.executable, str(path.resolve()), "check", "--specs", str(tmp_path / "s p")
    )


def _check_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
) -> tuple[Exception | None, int]:
    """Runs `check_release` against a stub `release.py`; returns its refusal (or None) and the spawn count."""
    skills = tmp_path / "skills"
    release = skills / "dd-release-implementation/scripts/release.py"
    release.parent.mkdir(parents=True)
    release.write_text(f"import sys\nopen({str(tmp_path / 'spawns')!r}, 'a').write('x')\n{body}\n")
    monkeypatch.setattr(_S, "__file__", str(skills / "dd-bug-resolution/scripts/_specs.py"))
    try:
        _S.check_release(tmp_path / "specs")
    except _S.Refusal as refusal:
        return refusal, len((tmp_path / "spawns").read_text())
    return None, len((tmp_path / "spawns").read_text())


@pytest.mark.medium
def test_a_check_that_exits_one_with_no_fix_is_refused_with_the_check_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    refusal, spawns = _check_release(tmp_path, monkeypatch, "sys.exit(1)")
    assert isinstance(refusal, _S.Refusal) and spawns == 1
    release = tmp_path / "skills/dd-release-implementation/scripts/release.py"
    check = inline(sys.executable, str(release.resolve()), "check", "--specs", str(tmp_path / "specs"))  # fmt: skip
    assert refusal.fix == f"Agent action: run {check}"


@pytest.mark.medium
def test_a_check_that_prints_error_and_exits_zero_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    refusal, spawns = _check_release(tmp_path, monkeypatch, "print('[error] x y')")
    assert (refusal, spawns) == (None, 1)


@pytest.mark.medium
def test_a_check_with_findings_relays_its_own_first_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "print('[error] bad')\nprint('fix: Agent action: do A')\nprint('fix: Agent action: do B')\nsys.exit(1)"  # fmt: skip
    refusal, spawns = _check_release(tmp_path, monkeypatch, body)
    assert isinstance(refusal, _S.Refusal) and spawns == 1
    assert refusal.fix == "Agent action: do A"
