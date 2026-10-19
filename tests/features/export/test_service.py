"""Size: SMALL — fakes at the store and git seams; the expected records are the documented
example, never derived from the service.
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
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.stores import context_store
from tests.helpers.oslib import read_text

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


def _service(root: Path) -> tuple[ExportService, JsonContextStore]:
    store = context_store(root / ".dadaia" / "states")
    git = GitSubprocessClient()
    return ExportService(context_store=store, git_client=git, workspace_root=root), store


def test_export_writes_fr13_records(tmp_path: Path) -> None:
    svc, store = _service(tmp_path)
    store.save(_ctx("alpha", ContextState.ALIVE, associated_repos=(_INFRA,)))
    (tmp_path / "repos" / "alpha").mkdir(parents=True)
    (tmp_path / "repos" / "beta").mkdir(parents=True)
    store.save(_ctx("beta", ContextState.DEAD, dead_since="2026-08-01T00:00:00+00:00"))

    result = svc.run()

    dist = tmp_path / ".dadaia" / "dist"
    assert result.path == dist / "spec-contexts.json"
    assert sorted(p.name for p in dist.iterdir()) == ["spec-contexts.json"]
    dist_zone = next(zone for zone in zones_with_canon() if zone.name == "dist")
    assert dist_zone.canon == frozenset({result.path.name, "workspace-export.tar.gz"})

    payload = json.loads(read_text(result.path))
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
                "associated_repos": [{"slug": "infra", "url": "https://example.com/infra.git"}],
                "last_sync_at": exported_at,
            },
            {
                "slug": "beta",
                "name": "beta",
                "state": "DEAD",
                "repo_url": "https://example.com/beta.git",
                "associated_repos": [],
                "last_sync_at": "2026-08-01T00:00:00+00:00",
            },
        ],
    }
    assert isinstance(payload["dadaia_version"], str) and payload["dadaia_version"]
    assert result.contexts == 2

    alpha = store.get("alpha")
    assert alpha is not None and alpha.associated_repos == (_INFRA,)


def test_export_overwrites_the_single_artifact(tmp_path: Path) -> None:
    svc, store = _service(tmp_path)
    store.save(_ctx("alpha", ContextState.ALIVE))
    store.save(_ctx("beta", ContextState.DEAD))
    first = svc.run()

    store.delete("beta")
    second = svc.run()

    assert first.path == second.path
    assert sorted(p.name for p in second.path.parent.iterdir()) == ["spec-contexts.json"]
    names = [c["name"] for c in json.loads(read_text(second.path))["contexts"]]
    assert names == ["alpha"]
