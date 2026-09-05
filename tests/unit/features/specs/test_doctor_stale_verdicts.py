"""SPEC-DOC-044: stale verdict files under specs/releases/<id>/verdicts/ (v0.5.0
specs-canon closure, operator ruling 2026-08-28).

A verdict under ``releases/<id>/verdicts/`` whose 40-hex name is not one of the LIVE
shas — the branch HEAD, HEAD's first parent, or the integration branch tip (the ship
shape, DADAIA.md §4.2) — is stale — ERROR, ``--fix`` deletes. Uses the SAME
``features.specs.canon.verdict_violations`` predicate the pre-push gate uses, over the
SAME ``features.chokepoints.verdict.live_verdict_shas`` set — never a second rule.

Intent: CONTRACT — v0.5.0 specs-canon closure
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor

_HEAD = "a" * 40
_PARENT = "b" * 40
_STALE = "c" * 40
_DEVELOP_TIP = "d" * 40
_LIVE = (_HEAD, _PARENT, _DEVELOP_TIP)


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
    issues = SpecsDoctor(specs, live_shas=_LIVE).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_verdict_matching_head_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _make_release_with_verdict(specs, _HEAD)
    issues = SpecsDoctor(specs, live_shas=_LIVE).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_verdict_matching_first_parent_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _make_release_with_verdict(specs, _PARENT)
    issues = SpecsDoctor(specs, live_shas=_LIVE).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_stale_verdict_is_an_error_and_fixable(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    stale_path = _make_release_with_verdict(specs, _STALE)
    doctor = SpecsDoctor(specs, live_shas=_LIVE)
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

    doctor = SpecsDoctor(specs, live_shas=_LIVE)
    issues = doctor.check()
    doctor.fix(issues)

    assert not stale_path.exists()
    assert fresh_path.exists()
    residual = [i for i in doctor.check() if i.code == "SPEC-DOC-044"]
    assert residual == []


def test_absent_live_shas_is_silent_never_guesses(tmp_path: Path) -> None:
    """No repo_root/git context resolved (live_shas=None) — this check genuinely
    cannot evaluate without a resolved head, so it stays silent rather than
    guessing (mirrors the constitution file-ref check's own optional-repo_root
    shape)."""
    specs = tmp_path / "specs"
    _make_release_with_verdict(specs, _STALE)
    issues = SpecsDoctor(specs).check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []


def test_the_ship_shape_pr_head_verdict_plus_develop_tip_verdict_is_silent(
    tmp_path: Path,
) -> None:
    """DADAIA.md §4.2 / dd-gitflow-default §3b: the ship verdict names develop's tip and
    is staged on the feature branch next to the PR-head verdict. Both are live; the
    doctor must neither flag nor ``--fix``-delete the ship evidence (bug
    verdict-staleness-rule-refuses-the-ship-verdict-the-gitflow-law-mandates)."""
    specs = tmp_path / "specs"
    parent_path = _make_release_with_verdict(specs, _PARENT)
    ship_path = parent_path.parent / f"{_DEVELOP_TIP}.handoff.json"
    ship_path.write_text(
        '{"agent": "security-reviewer", "verdict": "APPROVED"}\n', encoding="utf-8"
    )

    doctor = SpecsDoctor(specs, live_shas=_LIVE)
    issues = doctor.check()
    assert [i for i in issues if i.code == "SPEC-DOC-044"] == []
    doctor.fix(issues)
    assert ship_path.exists() and parent_path.exists()


def test_a_second_file_naming_the_same_live_sha_is_the_excess(tmp_path: Path) -> None:
    """One file per live sha: a duplicate for the SAME sha (here across two release
    directories) is the excess, and only the excess."""
    specs = tmp_path / "specs"
    first = _make_release_with_verdict(specs, _HEAD, release_id="1.2.3")
    second = _make_release_with_verdict(specs, _HEAD, release_id="1.2.4")

    issues = SpecsDoctor(specs, live_shas=_LIVE).check()
    stale_issues = [i for i in issues if i.code == "SPEC-DOC-044"]
    assert [i.path for i in stale_issues] == [str(second)]
    assert first.exists()


def test_cli_resolver_is_silent_when_the_integration_tip_is_unresolvable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live set depends on environment state (an unfetched ``origin/develop``);
    without it the doctor cannot tell a live ship verdict from a stale one, so the CLI
    hands SpecsDoctor ``None`` (silent) instead of a partial set whose ``--fix`` would
    delete staged ship evidence. The pre-push gate keeps failing closed on its own."""
    from dadaia_workspace import container
    from dadaia_workspace.cli.commands import specs as specs_cli
    from dadaia_workspace.features.chokepoints.verdict import INTEGRATION_TIP_REF

    class _Reader:
        def __init__(self, refs: dict[str, str]) -> None:
            self._refs = refs

        def resolve_ref(self, repo: Path, ref: str) -> str | None:
            return self._refs.get(ref)

        def first_parent(self, repo: Path, sha: str) -> str | None:
            return _PARENT

    monkeypatch.setattr(container, "build_git_object_reader", lambda: _Reader({"HEAD": _HEAD}))
    assert specs_cli._resolve_live_shas(tmp_path / "specs") is None

    full = _Reader({"HEAD": _HEAD, INTEGRATION_TIP_REF: _DEVELOP_TIP})
    monkeypatch.setattr(container, "build_git_object_reader", lambda: full)
    assert specs_cli._resolve_live_shas(tmp_path / "specs") == _LIVE
