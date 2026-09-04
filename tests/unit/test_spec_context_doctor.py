"""Unit tests for DoctorService — spec context invariant checker."""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import stat  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.platform import PLATFORM  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402


def _make_healthy_venv(root: Path) -> None:
    """Create a SYNTHETIC healthy venv tree so the FR-W3-02 VENV-1 invariant is satisfied.

    Synthetic only (mkdir/touch/chmod) — never a real venv build (QA memory law).
    """
    bindir = root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    bindir.mkdir(parents=True, exist_ok=True)
    entry = bindir / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(entry.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _ctx(
    name: str,
    state: ContextState = ContextState.DEAD,
    repo_slug: str | None = None,
) -> SpecContextProject:
    slug = repo_slug or name
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=slug,
        repo_url=f"https://github.com/org/{slug}",
        created_at="2026-01-01T00:00:00",
        alive_since="2026-06-01T00:00:00Z" if state == ContextState.ALIVE else None,
        dead_since=None,
        current_branch="main" if state == ContextState.ALIVE else None,
    )


def _make_doctor(
    workspace_root: Path,
    contexts: list[SpecContextProject] | None = None,
) -> tuple[DoctorService, FakeContextStore]:
    ctx_store = FakeContextStore()
    for c in contexts or []:
        ctx_store.save(c)
    git_client = FakeGitClient()
    svc = DoctorService(ctx_store, git_client, workspace_root)
    return svc, ctx_store


def test_check_clean_state_no_issues(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ALIVE)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    _make_healthy_venv(tmp_path)  # FR-W3-02: a clean workspace has a healthy venv.
    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    assert issues == []


# ---------------------------------------------------------------------------
# INV-4: ALIVE context must have repo on disk — reported, not fixable
# ---------------------------------------------------------------------------


def test_inv4_alive_repo_missing_detected_and_not_fixable(tmp_path: Path) -> None:
    ctx = _ctx("missing", state=ContextState.ALIVE)
    # do NOT create the repo dir
    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}
    assert "INV-4" in codes
    inv4 = next(i for i in issues if i.code == "INV-4")
    assert inv4.fixable is False


# ---------------------------------------------------------------------------
# CTX-URL-1: ALIVE context must not have an empty repo_url (T-011-08 / FR-W2-03 d)
# ---------------------------------------------------------------------------


def _ctx_empty_url(name: str, state: ContextState = ContextState.ALIVE) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=name,
        repo_url="",
        created_at="2026-01-01T00:00:00",
        alive_since="2026-06-01T00:00:00Z" if state == ContextState.ALIVE else None,
        dead_since=None,
        current_branch="main" if state == ContextState.ALIVE else None,
    )


@pytest.mark.parametrize(
    ("name", "ctx_fn", "make_repo", "expect_code"),
    [
        ("alive_empty_url_flagged", lambda: _ctx_empty_url("foo", ContextState.ALIVE), True, True),
        ("url_present_silent", lambda: _ctx("foo", ContextState.ALIVE), True, False),
        (
            # A DEAD context with an empty URL is not flagged (only ALIVE is
            # un-portable now).
            "dead_empty_url_silent",
            lambda: _ctx_empty_url("foo", ContextState.DEAD),
            False,
            False,
        ),
    ],
)
def test_ctx_url_1_table(
    tmp_path: Path, name: str, ctx_fn: object, make_repo: bool, expect_code: bool
) -> None:
    ctx = ctx_fn()  # type: ignore[operator]
    if make_repo:
        (tmp_path / "repos" / "foo").mkdir(parents=True)
    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}
    if expect_code:
        assert "CTX-URL-1" in codes
        ctx_url = next(i for i in issues if i.code == "CTX-URL-1")
        assert ctx_url.fixable is False
        assert "context update" in ctx_url.description
    else:
        assert "CTX-URL-1" not in codes


# ---------------------------------------------------------------------------
# INV-5: DEAD context must not have repo on disk — detected, fixable, fix() removes
# ---------------------------------------------------------------------------


def test_inv5_detected_fixable_fix_removes_stale_repo_and_no_issues_returns_empty(
    tmp_path: Path,
) -> None:
    ctx = _ctx("stale", state=ContextState.DEAD)
    repo_dir = tmp_path / "repos" / "stale"
    repo_dir.mkdir(parents=True)
    svc, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    codes = {i.code for i in issues}
    assert "INV-5" in codes
    inv5 = next(i for i in issues if i.code == "INV-5")
    assert inv5.fixable is True

    actions = svc.fix()
    assert not repo_dir.exists()
    assert any("stale" in a for a in actions)

    # No issues left ⇒ a second fix() pass returns an empty action list.
    second_actions = svc.fix()
    assert second_actions == []


# ---------------------------------------------------------------------------
# INV-6 (T-045-22): registry-wide slug-ownership uniqueness — report-only.
# ---------------------------------------------------------------------------


def test_inv6_main_repo_slug_collision_reported_not_fixable(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-045-22 (S3-FR9-ruling.md), main/main collision."""
    a = _ctx("a", repo_slug="x")
    b = _ctx("b", repo_slug="x")
    svc, _ = _make_doctor(tmp_path, [a, b])
    inv6 = [i for i in svc.check() if i.code == "INV-6"]
    assert len(inv6) == 1
    assert inv6[0].fixable is False
    assert "a" in inv6[0].description and "b" in inv6[0].description


def test_inv6_main_vs_associated_slug_collision_reported(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-045-22 (S3-FR9-ruling.md), main-vs-associated collision."""
    a = _ctx("a", repo_slug="x")
    b = SpecContextProject(
        name="b",
        state=ContextState.DEAD,
        repo_slug="b",
        repo_url="https://github.com/org/b",
        created_at="2026-01-01T00:00:00",
        associated_repos=(AssociatedRepo(slug="x", url="https://github.com/org/x"),),
    )
    svc, _ = _make_doctor(tmp_path, [a, b])
    inv6 = [i for i in svc.check() if i.code == "INV-6"]
    assert len(inv6) == 1
    assert inv6[0].fixable is False
    assert "a" in inv6[0].description and "b" in inv6[0].description


def test_inv5_fix_refuses_a_dead_slug_that_resolves_outside_repos(tmp_path: Path) -> None:
    """Intent: CONTRACT — bug import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees.
    A DEAD record whose slug resolves outside ``<workspace>/repos/`` (``..`` is the workspace
    root itself) is never rmtree'd: the step reports a skipped action and every entry of
    the workspace survives."""
    (tmp_path / "repos" / "victim").mkdir(parents=True)
    (tmp_path / "repos" / "victim" / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    svc, _ = _make_doctor(tmp_path, [_ctx("escape", repo_slug=".."), _ctx("dot", repo_slug=".")])

    actions = svc.fix()

    assert (tmp_path / "repos" / "victim" / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert (tmp_path / ".dadaia" / "states").is_dir()
    inv5 = [a for a in actions if a.startswith("INV-5:")]
    assert len(inv5) == 2 and all("skipped" in a and "outside" in a for a in inv5), actions


def test_inv5_fix_never_follows_a_symlinked_repo_dir(tmp_path: Path) -> None:
    """Intent: CONTRACT — same bug, the CWE-59 shape: ``repos/<slug>`` is a symlink out of
    ``repos/``; the target is neither removed nor emptied."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    ws = tmp_path / "ws"
    (ws / "repos").mkdir(parents=True)
    (ws / "repos" / "stale").symlink_to(outside, target_is_directory=True)
    svc, _ = _make_doctor(ws, [_ctx("stale")])

    actions = svc.fix()

    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert [a for a in actions if a.startswith("INV-5:")] == [
        "INV-5: skipped 'repos/stale' (outside repos/)"
    ]
