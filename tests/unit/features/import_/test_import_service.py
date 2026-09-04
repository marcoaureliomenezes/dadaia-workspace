"""Intent: CONTRACT — AC11 (FR13 / D15, T-046-31): `dadaia import` registers unknown names DEAD;
bug import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees: every imported record goes
through `SpecContextService.register`, the ONE guarded registry seam — a name or slug failing the
allowlist, or a slug another context owns, is skipped with its reason and never written.

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
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.specs.canon import scaffold as canon_scaffold
from tests.fakes import FakeContextStore, FakeGitClient

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


def _importer(tmp_path: Path, store: FakeContextStore) -> ImportService:
    (tmp_path / "repos").mkdir(exist_ok=True)
    contexts = SpecContextService(
        context_store=store,
        git_client=FakeGitClient(),
        workspace_root=tmp_path,
        scaffold_specs=canon_scaffold,
    )
    return ImportService(contexts)


def _export_file(tmp_path: Path, *records: dict[str, object]) -> Path:
    file = tmp_path / "spec-contexts.json"
    file.write_text(json.dumps({**_EXPORT, "contexts": list(records)}), encoding="utf-8")
    return file


def _record(name: str, slug: str, **overrides: object) -> dict[str, object]:
    return {
        "slug": slug,
        "name": name,
        "state": "DEAD",
        "repo_url": f"https://example.com/{name}.git",
        "branch": None,
        "associated_repos": [],
        "last_sync_at": None,
        **overrides,
    }


def test_import_saves_unknown_names_dead_and_skips_known_names(tmp_path: Path) -> None:
    file = tmp_path / "spec-contexts.json"
    file.write_text(json.dumps(_EXPORT), encoding="utf-8")
    store = FakeContextStore()
    store.save(_ALPHA)

    result = _importer(tmp_path, store).run(file)

    assert (result.registered, result.skipped) == (("beta",), (("alpha", "exists"),))
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
    ("record", "reason"),
    [
        (_record("escape", ".."), "letters, digits"),
        (_record("meu projeto", "ok-slug"), "letters, digits"),
        (_record("ok-name", "../../etc"), "letters, digits"),
        (_record("thief", "alpha"), "owned by context 'alpha'"),
        (
            _record(
                "sneaky",
                "own-slug",
                associated_repos=[{"slug": "alpha", "url": "https://example.com/x.git"}],
            ),
            "owned by context 'alpha'",
        ),
        (
            _record(
                "sneaky2",
                "own-slug",
                associated_repos=[{"slug": "../..", "url": "https://example.com/x.git"}],
            ),
            "letters, digits",
        ),
    ],
)
def test_import_skips_and_never_writes_a_record_the_registry_guard_refuses(
    tmp_path: Path, record: dict[str, object], reason: str
) -> None:
    """The record is refused by the same seam `context create` uses — nothing is saved,
    and the action line names the reason instead of `registered (dead)`."""
    store = FakeContextStore()
    store.save(_ALPHA)
    file = _export_file(tmp_path, record)

    result = _importer(tmp_path, store).run(file)

    assert result.registered == ()
    ((skipped_name, skipped_reason),) = result.skipped
    assert skipped_name == record["name"]
    assert reason in skipped_reason
    assert [c.name for c in store.list_all()] == ["alpha"]


def test_import_refusal_of_one_record_does_not_stop_the_others(tmp_path: Path) -> None:
    store = FakeContextStore()
    file = _export_file(tmp_path, _record("bad", ".."), _record("good", "good-repo"))

    result = _importer(tmp_path, store).run(file)

    assert result.registered == ("good",)
    assert [name for name, _ in result.skipped] == ["bad"]
    assert [c.name for c in store.list_all()] == ["good"]


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
        _importer(tmp_path, store).run(file)

    assert store.list_all() == []
