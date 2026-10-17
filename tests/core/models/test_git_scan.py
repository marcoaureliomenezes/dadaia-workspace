"""``git_scan.is_zero_sha``: the one decider of git's absent-object sentinel, SHA-1 or SHA-256."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.git_scan import is_zero_sha


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0" * 40, True),
        ("0" * 64, True),
        ("0" * 39 + "1", False),
        ("0" * 63 + "a", False),
        ("0" * 41, False),
        ("0" * 63, False),
        ("", False),
    ],
)
def test_is_zero_sha_holds_only_for_an_all_zero_object_id(value: str, expected: bool) -> None:
    assert is_zero_sha(value) is expected
