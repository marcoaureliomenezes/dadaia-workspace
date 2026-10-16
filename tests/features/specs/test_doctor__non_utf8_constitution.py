"""A constitution that is not UTF-8 is one `SPEC-DOC-002` finding with the act that re-encodes
it, whichever rule reads it first; `dadaia doctor` exits 1 and never raises."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.features.specs.test_doctor import _make_clean_specs_tree
from tests.features.specs.test_doctor__non_utf8_document import _reported

pytestmark = pytest.mark.medium


def test_a_non_utf8_constitution_is_one_finding_and_never_a_crash(tmp_path: Path) -> None:
    _make_clean_specs_tree(tmp_path)

    (found,) = _reported(tmp_path, "constitution.md")

    path = (tmp_path / "specs" / "constitution.md").resolve()
    assert (found["code"], found["fix"]) == (
        "SPEC-DOC-002",
        f"Agent action: re-encode line 1 of {path} as UTF-8 in place; every other line stays",
    )
