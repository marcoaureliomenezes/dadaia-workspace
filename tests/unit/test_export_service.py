"""Unit tests for ExportService."""

from pathlib import Path

from dadaia_workspace.core.models.export import ExportOptions
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.export.service import ExportService
from tests.fakes import FakeContextStore, FakeGitClient


def _ctx(name: str = "demo", *, branch: str | None = None) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=name,
        repo_url=f"https://example.com/{name}.git",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-01-02T00:00:00Z",
        dead_since=None,
        current_branch=branch,
    )


def _service(workspace: Path) -> tuple[ExportService, FakeContextStore, FakeGitClient]:
    store = FakeContextStore()
    git = FakeGitClient()
    svc = ExportService(context_store=store, git_client=git, workspace_root=workspace)
    return svc, store, git


def test_resolve_includes_skips_missing_paths(tmp_path: Path) -> None:
    svc, _, _ = _service(tmp_path)
    includes = svc.resolve_includes(ExportOptions(exclude_mnt=True))
    assert includes == []


def test_resolve_includes_drops_dotenv_files(tmp_path: Path) -> None:
    svc, _, _ = _service(tmp_path)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}")
    (tmp_path / "CLAUDE.md").write_text("# claude")
    (tmp_path / "secrets.env").write_text("KEY=secret")
    arcs = {arc for _, arc in svc.resolve_includes(ExportOptions(exclude_mnt=True))}
    assert ".dadaia/states" in arcs
    assert "CLAUDE.md" in arcs
    assert all(not arc.endswith(".env") for arc in arcs)


def test_build_manifest_records_branch(tmp_path: Path) -> None:
    svc, store, _ = _service(tmp_path)
    store.save(_ctx("alpha", branch="main"))
    store.save(_ctx("beta", branch="dev"))

    manifest = svc.build_manifest([], ExportOptions(exclude_mnt=True))
    names = {c["name"] for c in manifest.contexts}
    assert {"alpha", "beta"}.issubset(names)
    alpha = next(c for c in manifest.contexts if c["name"] == "alpha")
    assert alpha["current_branch"] == "main"


def test_refresh_branches_updates_current_branch(tmp_path: Path) -> None:
    svc, store, git = _service(tmp_path)
    store.save(_ctx("alpha"))
    repo_path = tmp_path / "repos" / "alpha"
    repo_path.mkdir(parents=True)
    git.checkout(repo_path, "feature/test")

    svc._refresh_branches()  # noqa: SLF001

    updated = store.get("alpha")
    assert updated is not None
    assert updated.current_branch == "feature/test"


def test_create_archive_includes_manifest(tmp_path: Path) -> None:
    svc, store, _ = _service(tmp_path)
    store.save(_ctx("alpha"))
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}")
    out = tmp_path / "out"
    out.mkdir()

    options = ExportOptions(exclude_mnt=True)
    includes = svc.resolve_includes(options)
    manifest = svc.build_manifest(includes, options)
    archive = svc.create_archive(includes, manifest, out)

    import tarfile

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert "export-manifest.json" in names


def test_run_returns_archive_path(tmp_path: Path) -> None:
    svc, store, _ = _service(tmp_path)
    store.save(_ctx("alpha"))
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}")

    out = tmp_path / "dist"
    result = svc.run(ExportOptions(output=out, exclude_mnt=True))

    assert result.path is not None
    assert result.path.exists()
    assert result.path.suffix == ".gz"
