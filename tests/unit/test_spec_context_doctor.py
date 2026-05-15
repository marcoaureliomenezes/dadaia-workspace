"""Unit tests for DoctorService — spec context invariant checker."""

from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient, FakePrimaryContextStore


def _ctx(
    name: str,
    state: ContextState = ContextState.INATIVO,
    is_primary: bool = False,
    repo_slug: str | None = None,
) -> SpecContextProject:
    slug = repo_slug or name
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=slug,
        repo_url=f"https://github.com/org/{slug}",
        is_primary=is_primary,
        created_at="2026-01-01T00:00:00",
        activated_at="2026-06-01T00:00:00" if state == ContextState.ATIVO else None,
        current_branch="main" if state == ContextState.ATIVO else None,
    )


def _make_doctor(
    workspace_root: Path,
    contexts: list[SpecContextProject] | None = None,
    primary_name: str | None = None,
    primary_slug: str | None = None,
) -> tuple[DoctorService, FakeContextStore, FakePrimaryContextStore]:
    ctx_store = FakeContextStore()
    for c in contexts or []:
        ctx_store.save(c)
    primary_store = FakePrimaryContextStore()
    if primary_name and primary_slug:
        primary_store.write(
            primary_name, primary_slug, workspace_root / "repos" / primary_slug / "specs"
        )
    git_client = FakeGitClient()
    svc = DoctorService(ctx_store, primary_store, git_client, workspace_root)
    return svc, ctx_store, primary_store


def test_check_clean_state_no_issues(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ATIVO, is_primary=True)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx], primary_name="alpha", primary_slug="alpha")
    issues = svc.check()
    assert issues == []


def test_check_detects_inv1_multiple_primaries(tmp_path: Path) -> None:
    a = _ctx("a", state=ContextState.ATIVO, is_primary=True)
    b = _ctx("b", state=ContextState.ATIVO, is_primary=True)
    (tmp_path / "repos" / "a").mkdir(parents=True)
    (tmp_path / "repos" / "b").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [a, b])
    codes = {i.code for i in svc.check()}
    assert "INV-1" in codes


def test_check_detects_inv2_primary_on_inativo(tmp_path: Path) -> None:
    c = _ctx("ghost", state=ContextState.INATIVO, is_primary=True)
    svc, _, _ = _make_doctor(tmp_path, [c])
    codes = {i.code for i in svc.check()}
    assert "INV-2" in codes


def test_check_detects_inv3_primary_json_mismatch(tmp_path: Path) -> None:
    ctx = _ctx("real", state=ContextState.ATIVO, is_primary=True)
    (tmp_path / "repos" / "real").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx], primary_name="other", primary_slug="other")
    codes = {i.code for i in svc.check()}
    assert "INV-3" in codes


def test_check_detects_inv3_primary_json_missing_but_primary_exists(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ATIVO, is_primary=True)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])  # no primary_context.json
    codes = {i.code for i in svc.check()}
    assert "INV-3" in codes


def test_check_detects_inv4_ativo_repo_missing(tmp_path: Path) -> None:
    ctx = _ctx("missing", state=ContextState.ATIVO, is_primary=True)
    # do NOT create the repo dir
    svc, _, _ = _make_doctor(tmp_path, [ctx], primary_name="missing", primary_slug="missing")
    codes = {i.code for i in svc.check()}
    assert "INV-4" in codes


def test_check_detects_inv5_inativo_with_repo_on_disk(tmp_path: Path) -> None:
    ctx = _ctx("stale", state=ContextState.INATIVO)
    (tmp_path / "repos" / "stale").mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    codes = {i.code for i in svc.check()}
    assert "INV-5" in codes


def test_check_detects_inv6_primary_json_without_is_primary_context(tmp_path: Path) -> None:
    ctx = _ctx("plain", state=ContextState.INATIVO)
    svc, _, _ = _make_doctor(tmp_path, [ctx], primary_name="plain", primary_slug="plain")
    codes = {i.code for i in svc.check()}
    assert "INV-6" in codes


def test_fix_demotes_extra_primaries(tmp_path: Path) -> None:
    a = _ctx("a", state=ContextState.ATIVO, is_primary=True)
    b = _ctx("b", state=ContextState.ATIVO, is_primary=True)
    (tmp_path / "repos" / "a").mkdir(parents=True)
    (tmp_path / "repos" / "b").mkdir(parents=True)
    svc, ctx_store, _ = _make_doctor(tmp_path, [a, b])
    actions = svc.fix()
    primaries = [c for c in ctx_store.list_all() if c.is_primary]
    assert len(primaries) == 1
    assert any("Demoted" in a for a in actions)


def test_fix_clears_primary_on_inativo_context(tmp_path: Path) -> None:
    c = _ctx("ghost", state=ContextState.INATIVO, is_primary=True)
    svc, ctx_store, _ = _make_doctor(tmp_path, [c])
    actions = svc.fix()
    fixed = ctx_store.get("ghost")
    assert fixed is not None
    assert fixed.is_primary is False
    assert any("Cleared is_primary" in a for a in actions)


def test_fix_writes_primary_json_for_single_primary(tmp_path: Path) -> None:
    ctx = _ctx("alpha", state=ContextState.ATIVO, is_primary=True)
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    svc, _, primary_store = _make_doctor(tmp_path, [ctx])
    actions = svc.fix()
    data = primary_store.read()
    assert data is not None
    assert data["name"] == "alpha"
    assert any("primary_context.json" in a for a in actions)


def test_fix_clears_stale_primary_json_when_no_primary(tmp_path: Path) -> None:
    ctx = _ctx("plain", state=ContextState.INATIVO)
    svc, _, primary_store = _make_doctor(
        tmp_path, [ctx], primary_name="plain", primary_slug="plain"
    )
    actions = svc.fix()
    assert primary_store.read() is None
    assert any("Cleared stale" in a for a in actions)


def test_fix_removes_stale_repo_for_inativo_context(tmp_path: Path) -> None:
    ctx = _ctx("stale", state=ContextState.INATIVO)
    repo_dir = tmp_path / "repos" / "stale"
    repo_dir.mkdir(parents=True)
    svc, _, _ = _make_doctor(tmp_path, [ctx])
    actions = svc.fix()
    assert not repo_dir.exists()
    assert any("Removed stale repo" in a for a in actions)
