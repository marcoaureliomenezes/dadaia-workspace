"""``is_zero_sha`` and the kernel ``is_zero_object_id``: one decider of git's absent-object sentinel, SHA-1 or SHA-256."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.git_scan import is_zero_sha
from dadaia_workspace.core.skill_owner import load_owner

_ROWS = [
    ("0" * 40, True),
    ("0" * 64, True),
    ("0" * 39 + "1", False),
    ("0" * 63 + "a", False),
    ("0" * 41, False),
    ("0" * 63, False),
    ("0" * 40 + "\n", False),
    ("", False),
    ("000", False),
    ("0000000", False),
]


@pytest.mark.parametrize(("value", "expected"), _ROWS)
def test_is_zero_sha_holds_only_for_an_all_zero_object_id(value: str, expected: bool) -> None:
    assert is_zero_sha(value) is expected


@pytest.mark.parametrize(("value", "expected"), _ROWS)
def test_the_kernel_predicate_holds_only_for_a_full_length_all_zero_object_id(
    value: str, expected: bool
) -> None:
    is_zero_object_id = load_owner("dd-bug-resolution", "_grammar").is_zero_object_id
    assert is_zero_object_id(value) is expected
    assert is_zero_object_id(value.encode()) is expected
