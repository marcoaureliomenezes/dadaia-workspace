"""Intent: CONTRACT — `specs upgrade` rewrites the retired Portuguese status tokens in the
live release trio (0.4.7 FR4 / T-047-58), and never inside published history. Size: SMALL."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.upgrade import (
    plan_status_token_rewrites,
    rewrite_status_tokens,
)

pytestmark = pytest.mark.unit


def _trio(root: Path, status: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (root / name).write_text(f"# doc\n\n> **Status:** {status}\n", encoding="utf-8")


def test_live_release_root_and_rc_folders_are_rewritten_to_english(tmp_path: Path) -> None:
    live = tmp_path / "releases" / "0.4.7"
    _trio(live, "Aprovado")
    _trio(live / "rc-1", "Em revisão")
    _trio(live / "rc-2", "Rascunho")

    planned = plan_status_token_rewrites(tmp_path)
    assert set(planned) == {live / name for name in ("SPEC.md", "PLAN.md", "TASKS.md")} | {
        live / f"rc-{n}" / name for n in (1, 2) for name in ("SPEC.md", "PLAN.md", "TASKS.md")
    }

    assert set(rewrite_status_tokens(tmp_path)) == set(planned)
    assert (live / "SPEC.md").read_text(encoding="utf-8").splitlines()[2] == (
        "> **Status:** Approved"
    )
    assert "In review" in (live / "rc-1" / "PLAN.md").read_text(encoding="utf-8")
    assert "Draft" in (live / "rc-2" / "TASKS.md").read_text(encoding="utf-8")


def test_the_accent_stripped_worker_spelling_is_rewritten_too(tmp_path: Path) -> None:
    live = tmp_path / "releases" / "0.9.9"
    _trio(live, "Em revisao")
    assert plan_status_token_rewrites(tmp_path) == sorted(live.glob("*.md"))
    rewrite_status_tokens(tmp_path)
    assert "In review" in (live / "SPEC.md").read_text(encoding="utf-8")


def test_published_history_under_archive_is_never_rewritten(tmp_path: Path) -> None:
    archived = tmp_path / "releases" / "_archive" / "0.4.6"
    _trio(archived, "Aprovado")
    _trio(archived / "rc-1", "Aprovado")

    assert plan_status_token_rewrites(tmp_path) == []
    assert rewrite_status_tokens(tmp_path) == []
    assert "Aprovado" in (archived / "SPEC.md").read_text(encoding="utf-8")


def test_an_already_english_tree_is_a_no_op(tmp_path: Path) -> None:
    _trio(tmp_path / "releases" / "0.4.7", "Approved")
    assert plan_status_token_rewrites(tmp_path) == []
    assert rewrite_status_tokens(tmp_path) == []
