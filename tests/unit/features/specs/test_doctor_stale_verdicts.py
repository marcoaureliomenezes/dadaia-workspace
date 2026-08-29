"""SPEC-DOC-044: stale verdict files under specs/releases/<id>/verdicts/ (v0.5.0
specs-canon closure, operator ruling 2026-08-28).

A verdict under ``releases/<id>/verdicts/`` whose 40-hex name is neither the branch
HEAD nor HEAD's first parent is stale — ERROR, ``--fix`` deletes. Uses the SAME
``features.specs.canon.verdict_violations`` predicate the pre-push gate uses
(``features.chokepoints.service``) — never a second, hand-kept rule.

Intent: CONTRACT — v0.5.0 specs-canon closure
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor

_HEAD = "a" * 40
_PARENT = "b" * 40
_STALE = "c" * 40


def _make_release_with_verdict(specs_dir: Path, sha: str, release_id: str = "1.2.3") -> Path:
    verdicts_dir = specs_dir / "releases" / release_id / "verdicts"
    verdicts_dir.mkdir(parents=True)
    verdict_path = verdicts_dir / f"{sha}.handoff.json"
    verdict_path.write_text(
        '{"agent": "security-reviewer", "verdict": "APPROVED"}\n', encoding="utf-8"
    )
    return verdict_path


def test_no_verdicts_dir_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "releases" / "1.2.3").mkdir(parents=True)
    issues = SpecsDoctor(specs, head_sha=_HEAD, parent_sha=_PARENT).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_verdict_matching_head_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _make_release_with_verdict(specs, _HEAD)
    issues = SpecsDoctor(specs, head_sha=_HEAD, parent_sha=_PARENT).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_verdict_matching_first_parent_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _make_release_with_verdict(specs, _PARENT)
    issues = SpecsDoctor(specs, head_sha=_HEAD, parent_sha=_PARENT).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_stale_verdict_is_an_error_and_fixable(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    stale_path = _make_release_with_verdict(specs, _STALE)
    doctor = SpecsDoctor(specs, head_sha=_HEAD, parent_sha=_PARENT)
    issues = doctor.check()
    stale_issues = [i for i in issues if i.code == "SPEC-DOC-044"]
    assert len(stale_issues) == 1
    assert stale_issues[0].severity == Severity.ERROR
    assert stale_issues[0].fixable is True
    assert stale_issues[0].path == str(stale_path)


def test_fix_deletes_only_the_stale_verdict(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    stale_path = _make_release_with_verdict(specs, _STALE)
    fresh_path = stale_path.parent / f"{_HEAD}.handoff.json"
    fresh_path.write_text(
        '{"agent": "security-reviewer", "verdict": "APPROVED"}\n', encoding="utf-8"
    )

    doctor = SpecsDoctor(specs, head_sha=_HEAD, parent_sha=_PARENT)
    issues = doctor.check()
    doctor.fix(issues)

    assert not stale_path.exists()
    assert fresh_path.exists()
    residual = [i for i in doctor.check() if i.code == "SPEC-DOC-044"]
    assert residual == []


def test_absent_head_sha_is_silent_never_guesses(tmp_path: Path) -> None:
    """No repo_root/git context resolved (head_sha=None) — this check genuinely
    cannot evaluate without a resolved head, so it stays silent rather than
    guessing (mirrors the constitution file-ref check's own optional-repo_root
    shape)."""
    specs = tmp_path / "specs"
    _make_release_with_verdict(specs, _STALE)
    issues = SpecsDoctor(specs).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_two_verdicts_matching_head_and_parent_at_once_flags_the_excess(tmp_path: Path) -> None:
    """The verdict business rule (operator, 2026-08-28): at most ONE file may be
    named for head-or-parent at a time — a second, simultaneous one is also flagged
    (SPEC-DOC-044/verdict_violations "at most one" rule)."""
    specs = tmp_path / "specs"
    head_path = _make_release_with_verdict(specs, _HEAD)
    parent_path = head_path.parent / f"{_PARENT}.handoff.json"
    parent_path.write_text(
        '{"agent": "security-reviewer", "verdict": "APPROVED"}\n', encoding="utf-8"
    )

    issues = SpecsDoctor(specs, head_sha=_HEAD, parent_sha=_PARENT).check()
    stale_issues = [i for i in issues if i.code == "SPEC-DOC-044"]
    assert len(stale_issues) == 1
    assert stale_issues[0].path in (str(head_path), str(parent_path))
