"""The tests-mirror guard's refusals: each fix names the real path and owner, no placeholder."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest


class _Tree:
    def tracked(self, *_spec: str) -> list[str]:
        return ["tests/e2e/test_journey.py", "tests/test_loose.py"]

    def read(self, _rel: str) -> str:
        return '"""A journey."""\n'


@pytest.mark.medium
def test_each_mirror_refusal_names_its_file_and_a_real_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts" / "guards"))
    repo = importlib.import_module("repo")
    assert repo.tests_mirror_the_package(_Tree()) == [  # type: ignore[arg-type]
        "no-owner: tests/e2e/test_journey.py names no `Owner:`. "
        "Agent action: add an `Owner: dd-sw-engineer-sr` docstring line to tests/e2e/test_journey.py",
        "loose-test: tests/test_loose.py mirrors no module. "
        "Agent action: git mv tests/test_loose.py under the tests/ folder that mirrors the module "
        "it tests, or under tests/fixtures/ when it tests the suite itself",
    ]


def _guards(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts" / "guards"))
    return importlib.import_module("run"), importlib.import_module("repo")


@pytest.mark.medium
@pytest.mark.parametrize(
    "line",
    [
        'CMD = "uv pip install -U dadaia-workspace"\n',
        'CMD = "pip install dadaia_workspace==0.4.7"\n',
        "CMD = 'pip install \"dadaia-workspace>0.4\"'\n",
    ],
    ids=["flag-between-verb-and-name", "underscore-spelling", "bare-greater-than"],
)
def test_the_published_install_rule_catches_every_spelling_of_the_name(
    monkeypatch: pytest.MonkeyPatch, line: str
) -> None:
    run, repo = _guards(monkeypatch)
    found = run._judge([], repo.release_workflow_canon, repo._file("tests/helpers/pin.py", line))
    assert [v for v in found if v.startswith("published-dadaia-workspace-install:")]


@pytest.mark.medium
def test_the_published_install_rule_leaves_the_import_name_and_a_local_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, repo = _guards(monkeypatch)
    text = "import dadaia_workspace\nCMD = 'python -m dadaia_workspace.cli'\nW = 'uvx --from ./dist/x.whl dadaia'\n"
    found = run._judge([], repo.release_workflow_canon, repo._file("tests/helpers/pin.py", text))
    assert [v for v in found if v.startswith("published-dadaia-workspace-install:")] == []


@pytest.mark.medium
def test_the_memory_shape_rule_flags_the_headings_the_doctor_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, repo = _guards(monkeypatch)
    plant = repo._edit(repo._A, "\n## Tech Stack", "\n### Version notes\n\n## Tech Stack")
    found = run._judge([], repo.memory_canonical_shape, plant)
    assert [v for v in found if v.startswith("history-heading:")]
