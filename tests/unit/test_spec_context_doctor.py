"""Unit tests for DoctorService — spec context invariant checker."""

from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore


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
) -> tuple[DoctorService, FakeContextStore, FakePrimaryContextStore]:
    ctx_store = FakeContextStore()
    for c in contexts or []:
        ctx_store.save(c)
    primary_store = FakePrimaryContextStore()
    git_client = FakeGitClient()
    svc = DoctorService(ctx_store, primary_store, git_client, workspace_root)
    return svc, ctx_store, primary_store


# ---------------------------------------------------------------------------
# INV-4: ALIVE context must have repo on disk
# ---------------------------------------------------------------------------


def test_check_clean_state_no_issues(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ALIVE)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    assert issues == []


def test_check_detects_inv4_alive_repo_missing(tmp_path: Path) -> None:
    ctx = _ctx("missing", state=ContextState.ALIVE)
    # do NOT create the repo dir
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    codes = {i.code for i in svc.check()}
    assert "INV-4" in codes


def test_inv4_issue_not_fixable(tmp_path: Path) -> None:
    ctx = _ctx("missing", state=ContextState.ALIVE)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    inv4 = next(i for i in issues if i.code == "INV-4")
    assert inv4.fixable is False


# ---------------------------------------------------------------------------
# INV-5: DEAD context must not have repo on disk
# ---------------------------------------------------------------------------


def test_check_detects_inv5_dead_with_repo_on_disk(tmp_path: Path) -> None:
    ctx = _ctx("stale", state=ContextState.DEAD)
    (tmp_path / "repos" / "stale").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    codes = {i.code for i in svc.check()}
    assert "INV-5" in codes


def test_inv5_issue_is_fixable(tmp_path: Path) -> None:
    ctx = _ctx("stale", state=ContextState.DEAD)
    (tmp_path / "repos" / "stale").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    issues = svc.check()
    inv5 = next(i for i in issues if i.code == "INV-5")
    assert inv5.fixable is True


# ---------------------------------------------------------------------------
# Fix INV-5: remove stale repos for DEAD contexts
# ---------------------------------------------------------------------------


def test_fix_removes_stale_repo_for_dead_context(tmp_path: Path) -> None:
    ctx = _ctx("stale", state=ContextState.DEAD)
    repo_dir = tmp_path / "repos" / "stale"
    repo_dir.mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    actions = svc.fix()
    assert not repo_dir.exists()
    assert any("stale" in a for a in actions)


def test_fix_no_issues_returns_empty(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ALIVE)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    actions = svc.fix()
    assert actions == []
