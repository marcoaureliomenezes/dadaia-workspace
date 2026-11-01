"""The shipped `export-v1` schema validates the JSON of both artifacts and refuses a wrong
`state` casing and a missing `schema_version`. Size: SMALL — the real service over a tmp
workspace, the real validator.
"""

import copy
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.stores import context_store
from tests.helpers.oslib import read_text, write_text
from tests.helpers.worktree_ws import make_workspace

_ledger = load_owner("dd-bug-resolution", "_ledger")


def _findings(document: object) -> list[str]:
    schema = _ledger.load_schema("export-v1")
    return list(_ledger.validate(document, schema, schema, "export"))


@pytest.fixture
def artifacts(tmp_path: Path) -> dict[str, dict[str, Any]]:
    """The soft JSON and the hard archive's JSON member of one registry: a context with a
    remote and one associated repo, a second with none."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    write_text(root / ".dadaia/states/spec_contexts.json", '{"contexts": []}')
    store = context_store(root / ".dadaia" / "states")
    stamp = "2026-01-01T00:00:00+00:00"
    store.save(
        SpecContextProject(
            "r",
            ContextState.ALIVE,
            "r",
            "https://example.com/r.git",
            stamp,
            associated_repos=(AssociatedRepo("a", "https://example.com/a.git"),),
        )  # fmt: skip
    )
    store.save(SpecContextProject("solo", ContextState.DEAD, "solo", "", stamp))
    service = container.build_export_service(root)
    soft = json.loads(read_text(service.run().path))
    with tarfile.open(service.run(hard=True).path) as tar:
        member = tar.extractfile("spec-contexts.json")
        assert member is not None
        hard = json.loads(member.read())
    return {"soft": soft, "hard": hard}


@pytest.mark.parametrize("kind", ["soft", "hard"])
def test_the_schema_validates_both_artifacts(
    artifacts: dict[str, dict[str, Any]], kind: str
) -> None:
    assert _findings(artifacts[kind]) == []
    assert artifacts[kind]["contexts"][1]["repo_url"] is None


def test_the_schema_refuses_an_uppercase_state(artifacts: dict[str, dict[str, Any]]) -> None:
    broken = copy.deepcopy(artifacts["soft"])
    broken["contexts"][0]["state"] = "ALIVE"

    assert _findings(broken) != []


def test_the_schema_refuses_a_missing_schema_version(
    artifacts: dict[str, dict[str, Any]],
) -> None:
    broken = copy.deepcopy(artifacts["soft"])
    del broken["schema_version"]

    assert _findings(broken) != []
