"""Intent: CONTRACT — `specs upgrade` rewrites the retired Portuguese status tokens in the
live candidate's trio (0.4.7 FR4 / T-047-58), never in a closed rc-<N>/ or published
history (ADR 0150 (1)). Size: SMALL."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.upgrade import (
    fold_flat_trio,
    plan_status_token_rewrites,
    rewrite_status_tokens,
)

pytestmark = pytest.mark.unit


def _trio(root: Path, status: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root.parent / "_RELEASE.json").write_text("{}", encoding="utf-8")
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (root / name).write_text(f"# doc\n\n> **Status:** {status}\n", encoding="utf-8")


# fmt: off
@pytest.mark.parametrize(("dirs", "expected"), [
    pytest.param({"0.4.7/rc-1": "Em revisão", "0.4.7/rc-2": "Rascunho"},
                 {"0.4.7/rc-2": "Draft"}, id="live-candidate-only-closed-rc-kept"),
    pytest.param({"0.9.9/rc-1": "Em revisao"}, {"0.9.9/rc-1": "In review"}, id="accent-stripped-worker-spelling"),
    pytest.param({"_archive/0.4.6/rc-1": "Aprovado"}, {}, id="published-archive-never-rewritten"),
    pytest.param({"0.4.7/rc-1": "Approved"}, {}, id="already-english-no-op"),
])
# fmt: on
def test_upgrade_rewrites_retired_status_tokens_only_in_the_live_trio(tmp_path: Path, dirs: dict[str, str], expected: dict[str, str]) -> None:
    for rel, status in dirs.items():
        _trio(tmp_path / "releases" / rel, status)
    touched = {tmp_path / "releases" / rel / n for rel in expected for n in ("SPEC.md", "PLAN.md", "TASKS.md")}

    assert set(plan_status_token_rewrites(tmp_path)) == touched
    assert set(rewrite_status_tokens(tmp_path)) == touched
    for rel, status in dirs.items():
        text = (tmp_path / "releases" / rel / "PLAN.md").read_text(encoding="utf-8")
        assert text.splitlines()[2] == f"> **Status:** {expected.get(rel, status)}"


def test_the_8_to_9_hop_folds_a_flat_live_trio_into_the_next_candidate(tmp_path: Path) -> None:
    """ADR 0150, 0151 M5: a v8 tree's flat live trio moves into `rc-<N+1>/`; a closed
    `rc-<N>/` is untouched; a second run folds nothing."""
    _trio(tmp_path / "releases" / "0.4.7" / "rc-1", "Approved")
    _trio(tmp_path / "releases" / "0.4.7", "Draft")
    folded = fold_flat_trio(tmp_path)
    release = tmp_path / "releases" / "0.4.7"
    assert folded == [release / n for n in ("PLAN.md", "SPEC.md", "TASKS.md")]
    assert sorted(p.name for p in release.iterdir()) == ["_RELEASE.json", "rc-1", "rc-2"]
    assert "Draft" in (release / "rc-2" / "PLAN.md").read_text(encoding="utf-8")
    assert "Approved" in (release / "rc-1" / "PLAN.md").read_text(encoding="utf-8")
    assert fold_flat_trio(tmp_path) == []
