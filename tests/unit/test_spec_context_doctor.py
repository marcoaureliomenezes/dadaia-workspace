"""Unit tests for DoctorService — spec context invariant checker."""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import stat  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject  # noqa: E402
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


def test_inv5_detected_fixable_and_fix_removes_stale_repo(tmp_path: Path) -> None:
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


def test_fix_no_issues_returns_empty(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ALIVE)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    svc, _ = _make_doctor(tmp_path, [ctx])
    actions = svc.fix()
    assert actions == []
