"""Size: SMALL — the real store and container wiring over a tmp workspace; expected artifacts are the documented example, never
derived from the service.
"""

import json
from pathlib import Path

from dadaia_workspace import container
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.workspace_layout import zones_with_canon
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
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


def _registry(root: Path, *contexts: SpecContextProject) -> JsonContextStore:
    store = context_store(root / ".dadaia" / "states")
    for ctx in contexts:
        store.save(ctx)
    return store


def _service(root: Path) -> ExportService:
    return container.build_export_service(root)


def test_export_writes_the_export_v1_artifact(tmp_path: Path) -> None:
    states = tmp_path / ".dadaia" / "states"
    _registry(
        tmp_path,
        _ctx("alpha", ContextState.ALIVE, associated_repos=(_INFRA,)),
        _ctx("beta", ContextState.DEAD, dead_since="2026-08-01T00:00:00+00:00"),
    )
    JsonHarnessProfileStore().write(states, HarnessProfile.of(("claude", "codex")))

    result = _service(tmp_path).run()

    dist = tmp_path / ".dadaia" / "dist"
    assert result.path == dist / "spec-contexts.json"
    assert sorted(p.name for p in dist.iterdir()) == ["spec-contexts.json"]
    dist_zone = next(zone for zone in zones_with_canon() if zone.name == "dist")
    assert dist_zone.canon == frozenset({result.path.name, "workspace-export.tar.gz"})
    payload = json.loads(read_text(result.path))
    assert payload == {
        "schema_version": "export-v1",
        "dadaia_version": payload["dadaia_version"],
        "harnesses": ["claude", "codex"],
        "contexts": [
            {
                "slug": "alpha",
                "name": "alpha",
                "state": "alive",
                "repo_url": "https://example.com/alpha.git",
                "associated_repos": [{"slug": "infra", "url": "https://example.com/infra.git"}],
            },
            {
                "slug": "beta",
                "name": "beta",
                "state": "dead",
                "repo_url": "https://example.com/beta.git",
                "associated_repos": [],
            },
        ],
    }
    assert isinstance(payload["dadaia_version"], str) and payload["dadaia_version"]
    assert result.contexts == 2


def test_export_leaves_the_registry_byte_identical(tmp_path: Path) -> None:
    _registry(tmp_path, _ctx("alpha", ContextState.ALIVE, associated_repos=(_INFRA,)))
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    before = registry.read_bytes()

    _service(tmp_path).run()

    assert registry.read_bytes() == before


def test_an_alive_context_whose_repo_is_not_on_disk_is_still_exported(tmp_path: Path) -> None:
    _registry(tmp_path, _ctx("alpha", ContextState.ALIVE), _ctx("beta", ContextState.ALIVE))
    (tmp_path / "repos" / "alpha").mkdir(parents=True)

    result = _service(tmp_path).run()

    contexts = json.loads(read_text(result.path))["contexts"]
    assert [(c["name"], sorted(c)) for c in contexts] == [
        ("alpha", ["associated_repos", "name", "repo_url", "slug", "state"]),
        ("beta", ["associated_repos", "name", "repo_url", "slug", "state"]),
    ]


def test_a_repo_with_no_remote_is_recorded_with_a_null_url(tmp_path: Path) -> None:
    quiet = AssociatedRepo(slug="infra", url="")
    _registry(
        tmp_path,
        SpecContextProject(
            name="solo",
            state=ContextState.ALIVE,
            repo_slug="solo",
            repo_url="",
            created_at="2026-01-01T00:00:00+00:00",
            associated_repos=(quiet, _INFRA),
        ),
    )

    result = _service(tmp_path).run()

    (record,) = json.loads(read_text(result.path))["contexts"]
    assert record["repo_url"] is None
    assert record["associated_repos"] == [
        {"slug": "infra", "url": None},
        {"slug": "infra", "url": "https://example.com/infra.git"},
    ]


def test_export_overwrites_the_single_artifact(tmp_path: Path) -> None:
    store = _registry(tmp_path, _ctx("alpha", ContextState.ALIVE), _ctx("beta", ContextState.DEAD))
    svc = _service(tmp_path)
    first = svc.run()

    store.delete("beta")
    second = svc.run()

    assert first.path == second.path
    assert sorted(p.name for p in second.path.parent.iterdir()) == ["spec-contexts.json"]
    names = [c["name"] for c in json.loads(read_text(second.path))["contexts"]]
    assert names == ["alpha"]
