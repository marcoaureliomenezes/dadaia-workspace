"""The tests-mirror guard's refusals: each fix names the real path and owner, no placeholder."""

from __future__ import annotations

import importlib
from pathlib import Path

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
