"""Intent: CONTRACT — AC11 (FR13, T-046-31): `dadaia export` writes one `spec-contexts.json`.

Size: SMALL — fakes at the store and git seams; the expected records are the SPEC FR13
worked example, never derived from the service.
"""

import json
from pathlib import Path

from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.workspace_layout import zones_with_canon
from dadaia_workspace.features.export.service import ExportService
from tests.fakes import FakeContextStore, FakeGitClient

_INFRA = AssociatedRepo(slug="infra", url="https://example.com/infra.git")


def _ctx(name: str, state: ContextState, **fields: object) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=name,
        repo_url=f"https://example.com/{name}.git",
        created_at="2026-01-01T00:00:00+00:00",
        **fields,  # type: ignore[arg-type]
    )


def _service(root: Path) -> tuple[ExportService, FakeContextStore, FakeGitClient]:
    store = FakeContextStore()
    git = FakeGitClient()
    return ExportService(context_store=store, git_client=git, workspace_root=root), store, git


def test_export_writes_fr13_records_and_refreshes_alive_branches_only(tmp_path: Path) -> None:
    svc, store, git = _service(tmp_path)
    store.save(_ctx("alpha", ContextState.ALIVE, current_branch="main", associated_repos=(_INFRA,)))
    store.save(
        _ctx(
            "beta", ContextState.DEAD, current_branch="main", dead_since="2026-08-01T00:00:00+00:00"
        )
    )
    for name, branch in (("alpha", "feature/0.4.6"), ("beta", "stale-checkout")):
        (tmp_path / "repos" / name).mkdir(parents=True)
        git.checkout(tmp_path / "repos" / name, branch)

    result = svc.run()

    dist = tmp_path / ".dadaia" / "dist"
    assert result.path == dist / "spec-contexts.json"
    assert sorted(p.name for p in dist.iterdir()) == ["spec-contexts.json"]
    dist_zone = next(zone for zone in zones_with_canon() if zone.name == "dist")
    assert dist_zone.canon == frozenset({result.path.name})

    payload = json.loads(result.path.read_text("utf-8"))
    exported_at = payload["exported_at"]
    assert payload == {
        "schema_version": "spec-contexts-export-v1",
        "exported_at": exported_at,
        "dadaia_version": payload["dadaia_version"],
        "contexts": [
            {
                "slug": "alpha",
                "name": "alpha",
                "state": "ALIVE",
                "repo_url": "https://example.com/alpha.git",
                "branch": "feature/0.4.6",
                "associated_repos": [{"slug": "infra", "url": "https://example.com/infra.git"}],
                "last_sync_at": exported_at,
            },
            {
                "slug": "beta",
                "name": "beta",
                "state": "DEAD",
                "repo_url": "https://example.com/beta.git",
                "branch": "main",
                "associated_repos": [],
                "last_sync_at": "2026-08-01T00:00:00+00:00",
            },
        ],
    }
    assert isinstance(payload["dadaia_version"], str) and payload["dadaia_version"]
    assert result.contexts == 2

    alpha = store.get("alpha")
    assert alpha is not None
    assert (alpha.current_branch, alpha.associated_repos) == ("feature/0.4.6", (_INFRA,))
    beta = store.get("beta")
    assert beta is not None and beta.current_branch == "main"


def test_export_overwrites_the_single_artifact(tmp_path: Path) -> None:
    svc, store, _ = _service(tmp_path)
    store.save(_ctx("alpha", ContextState.ALIVE))
    store.save(_ctx("beta", ContextState.DEAD))
    first = svc.run()

    store.delete("beta")
    second = svc.run()

    assert first.path == second.path
    assert sorted(p.name for p in second.path.parent.iterdir()) == ["spec-contexts.json"]
    names = [c["name"] for c in json.loads(second.path.read_text("utf-8"))["contexts"]]
    assert names == ["alpha"]
