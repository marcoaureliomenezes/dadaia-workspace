"""`ExportService.read` is the one reader of an `export-v1` artifact: a null clone URL reads as
`""` (never the text `None`), so `SpecContextService.register`, the one decider, refuses it.

Size: SMALL — the real service over a tmp dir, the real registry; the scanner is a fake.
"""

import json
from pathlib import Path

import pytest

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core.exceptions import RepoUrlMissingError
from dadaia_workspace.core.models.spec_context import AssociatedRepo
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store
from tests.helpers.oslib import write_text


def _reader(tmp_path: Path) -> tuple[ExportService, SpecContextService]:
    (tmp_path / "repos").mkdir(exist_ok=True)
    store = context_store(tmp_path / "states")
    registry = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=tmp_path,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )
    return ExportService(store, tmp_path, lambda _bundle, _repo: {}), registry


def _artifact(tmp_path: Path, *records: dict[str, object]) -> Path:
    file = tmp_path / "spec-contexts.json"
    write_text(
        file,
        json.dumps(
            {
                "schema_version": "export-v1",
                "dadaia_version": "0.5.0",
                "harnesses": ["claude"],
                "contexts": list(records),
            }
        ),
    )
    return file


def _record(name: str, **overrides: object) -> dict[str, object]:
    return {
        "slug": name,
        "name": name,
        "state": "dead",
        "repo_url": f"https://example.com/{name}.git",
        "associated_repos": [],
        **overrides,
    }


def test_a_null_main_url_reads_as_empty_and_a_null_associated_url_alike(tmp_path: Path) -> None:
    reader, _ = _reader(tmp_path)
    side = {"slug": "side", "url": None}

    artifact = reader.read(
        _artifact(tmp_path, _record("solo", repo_url=None, associated_repos=[side]))
    )

    [ctx] = artifact.contexts
    assert (ctx.repo_url, ctx.associated_repos) == ("", (AssociatedRepo("side", ""),))


@pytest.mark.parametrize(
    "record",
    [
        _record("solo", repo_url=None),
        _record("main", associated_repos=[{"slug": "side", "url": None}]),
    ],
    ids=["main-repo", "associated-repo"],
)
def test_a_context_with_a_null_url_is_refused_by_register_and_never_stored(
    tmp_path: Path, record: dict[str, object]
) -> None:
    reader, registry = _reader(tmp_path)
    [ctx] = reader.read(_artifact(tmp_path, record)).contexts

    with pytest.raises(RepoUrlMissingError):
        registry.register(ctx)

    assert registry.list_all() == []
