"""Intent: CONTRACT — AC11 (FR13 / D15, T-046-31): `dadaia import` registers unknown names DEAD.

Size: SMALL — the input file is the SPEC FR13 worked example; the store is a fake.
"""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.import_.service import ImportService
from tests.fakes import FakeContextStore

_EXPORT = {
    "schema_version": "spec-contexts-export-v1",
    "exported_at": "2026-09-03T15:00:00+00:00",
    "dadaia_version": "0.4.6",
    "contexts": [
        {
            "slug": "alpha",
            "name": "alpha",
            "state": "ALIVE",
            "repo_url": "https://example.com/alpha.git",
            "branch": "feature/0.4.6",
            "associated_repos": [],
            "last_sync_at": "2026-09-03T15:00:00+00:00",
        },
        {
            "slug": "beta-repo",
            "name": "beta",
            "state": "DEAD",
            "repo_url": "https://example.com/beta.git",
            "branch": "develop",
            "associated_repos": [{"slug": "infra", "url": "https://example.com/infra.git"}],
            "last_sync_at": None,
        },
    ],
}

_ALPHA = SpecContextProject(
    name="alpha",
    state=ContextState.ALIVE,
    repo_slug="alpha",
    repo_url="https://example.com/alpha.git",
    created_at="2026-01-01T00:00:00+00:00",
    alive_since="2026-01-02T00:00:00+00:00",
    current_branch="main",
)


def test_import_saves_unknown_names_dead_and_skips_known_names(tmp_path: Path) -> None:
    file = tmp_path / "spec-contexts.json"
    file.write_text(json.dumps(_EXPORT), encoding="utf-8")
    store = FakeContextStore()
    store.save(_ALPHA)

    result = ImportService(store).run(file)

    assert (result.registered, result.skipped) == (("beta",), ("alpha",))
    assert store.get("alpha") == _ALPHA
    beta = store.get("beta")
    assert beta is not None
    assert beta.created_at == beta.dead_since
    assert beta == SpecContextProject(
        name="beta",
        state=ContextState.DEAD,
        repo_slug="beta-repo",
        repo_url="https://example.com/beta.git",
        created_at=beta.created_at,
        alive_since=None,
        dead_since=beta.created_at,
        current_branch="develop",
        associated_repos=(AssociatedRepo(slug="infra", url="https://example.com/infra.git"),),
    )


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (None, "not found"),
        ("{not json", "not valid JSON"),
        (json.dumps({**_EXPORT, "schema_version": "workspace-export-v0"}), "schema_version"),
        (json.dumps({"schema_version": "spec-contexts-export-v1"}), "contexts"),
    ],
)
def test_import_rejects_files_outside_the_contract(
    tmp_path: Path, content: str | None, reason: str
) -> None:
    file = tmp_path / "spec-contexts.json"
    if content is not None:
        file.write_text(content, encoding="utf-8")
    store = FakeContextStore()

    with pytest.raises(ValueError, match=reason):
        ImportService(store).run(file)

    assert store.list_all() == []
