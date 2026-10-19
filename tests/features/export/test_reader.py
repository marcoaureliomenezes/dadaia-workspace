"""`ExportService.read` is the one reader of an `export-v1` artifact: a null clone URL reads as
`""` (never the text `None`), so `SpecContextService.register`, the one decider, refuses it.

Size: SMALL — the real service over a tmp dir, the real registry; the scanner is a fake.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core.exceptions import DadaiaError, RepoUrlMissingError
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store
from tests.helpers.oslib import write_text

_ALPHA = SpecContextProject(
    name="alpha",
    state=ContextState.ALIVE,
    repo_slug="alpha",
    repo_url="https://example.com/alpha.git",
    created_at="2026-01-01T00:00:00+00:00",
    alive_since="2026-01-02T00:00:00+00:00",
)


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


def _artifact(
    tmp_path: Path, *records: dict[str, object], schema_version: object = "export-v1"
) -> Path:
    file = tmp_path / "spec-contexts.json"
    write_text(
        file,
        json.dumps(
            {
                "schema_version": schema_version,
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


@pytest.mark.parametrize("version", ["export-v0", "export-v2", "workspace-export-v0", 1, None])
def test_any_other_schema_version_refuses_with_the_one_re_export_fix(
    tmp_path: Path, version: object
) -> None:
    reader, registry = _reader(tmp_path)

    with pytest.raises(DadaiaError) as refused:
        reader.read(_artifact(tmp_path, _record("solo"), schema_version=version))

    assert (
        refused.value.fix
        == "Agent action: re-export the artifact with the current dadaia-workspace"
    )
    assert str(refused.value).count("fix:") == 1
    assert registry.list_all() == []


def test_read_returns_every_record_as_a_dead_context_and_names_the_alive_ones(
    tmp_path: Path,
) -> None:
    reader, _ = _reader(tmp_path)
    infra = {"slug": "infra", "url": "https://example.com/infra.git"}

    artifact = reader.read(
        _artifact(
            tmp_path,
            _record("alpha", state="alive", branch="feature/0.4.6", last_sync_at="2026-09-03"),
            _record("beta", slug="beta-repo", associated_repos=[infra]),
        )
    )

    alpha, beta = artifact.contexts
    assert (alpha.state, alpha.alive_since, alpha.dead_since) == (
        ContextState.DEAD,
        None,
        alpha.created_at,
    )
    assert beta == SpecContextProject(
        name="beta",
        state=ContextState.DEAD,
        repo_slug="beta-repo",
        repo_url="https://example.com/beta.git",
        created_at=beta.created_at,
        alive_since=None,
        dead_since=beta.created_at,
        associated_repos=(AssociatedRepo(slug="infra", url="https://example.com/infra.git"),),
    )
    assert (artifact.alive, artifact.harnesses) == (("alpha",), ("claude",))


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (_record("escape", slug=".."), "letters, digits"),
        (_record("meu projeto", slug="ok-slug"), "letters, digits"),
        (_record("ok-name", slug="../../etc"), "letters, digits"),
        (_record("thief", slug="alpha"), "owned by context 'alpha'"),
        (
            _record(
                "sneaky",
                slug="own-slug",
                associated_repos=[{"slug": "alpha", "url": "https://example.com/x.git"}],
            ),
            "owned by context 'alpha'",
        ),
        (
            _record(
                "sneaky2",
                slug="own-slug",
                associated_repos=[{"slug": "../..", "url": "https://example.com/x.git"}],
            ),
            "letters, digits",
        ),
        (_record("no-url", repo_url=""), "no clone URL"),
    ],
)
def test_register_refuses_and_never_writes_a_record_read_from_an_artifact(
    tmp_path: Path, record: dict[str, object], reason: str
) -> None:
    reader, registry = _reader(tmp_path)
    registry.register(_ALPHA)
    [ctx] = reader.read(_artifact(tmp_path, record)).contexts

    with pytest.raises(DadaiaError, match=reason):
        registry.register(ctx)

    assert [c.name for c in registry.list_all()] == ["alpha"]


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (None, "not found"),
        ("{not json", "not valid JSON"),
        (json.dumps({"schema_version": "export-v1"}), "contexts"),
    ],
)
def test_read_refuses_a_file_outside_the_contract_with_one_fix(
    tmp_path: Path, content: str | None, reason: str
) -> None:
    file = tmp_path / "spec-contexts.json"
    if content is not None:
        write_text(file, content)

    with pytest.raises(DadaiaError, match=reason) as refused:
        _reader(tmp_path)[0].read(file)

    assert refused.value.fix
    assert str(refused.value).count("fix:") == 1


def test_a_missing_file_fix_names_the_export_verb(
    tmp_path: Path, sentence: Callable[..., str]
) -> None:
    with pytest.raises(DadaiaError) as refused:
        _reader(tmp_path)[0].read(tmp_path / "spec-contexts.json")

    assert sentence(None, "export") in refused.value.fix


@pytest.mark.parametrize(
    ("record", "missing"),
    [
        (lambda: {k: v for k, v in _record("x").items() if k != "name"}, "name"),
        (lambda: {k: v for k, v in _record("x").items() if k != "repo_url"}, "repo_url"),
        (lambda: _record("x", associated_repos=[{"slug": "side"}]), "url"),
    ],
    ids=["name", "repo_url", "associated-url"],
)
def test_read_refuses_a_record_missing_a_field_naming_it(
    tmp_path: Path, record: Callable[[], dict[str, object]], missing: str
) -> None:
    with pytest.raises(DadaiaError) as refused:
        _reader(tmp_path)[0].read(_artifact(tmp_path, record()))

    assert missing in str(refused.value)
    assert str(refused.value).count("fix:") == 1
