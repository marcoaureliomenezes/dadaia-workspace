"""Unit tests for shared write-scope matching (Ring-1 + Ring-2 single classifier).

CRITICAL: the ONE scope classifier both rings use — sibling-prefix non-match must stay a
case.
"""

from __future__ import annotations

from dadaia_workspace.core.scope_match import (
    is_in_scope,
    matches_path,
    out_of_scope_paths,
)


def test_matches_path_glob_forms_and_scope_allowed_rules() -> None:
    assert matches_path("foo/bar/baz.txt", "foo/**") is True
    assert matches_path("foo", "foo/**") is True
    assert matches_path("foo/bar.txt", "foo/*") is True
    assert matches_path("foo/bar/baz.txt", "foo/*") is False  # not a direct child
    assert matches_path("foo/bar", "foo") is True
    assert matches_path("other/x", "foo/**") is False  # sibling-prefix non-match

    assert is_in_scope("a/b", allowed=("a/**",), forbidden=()) is True
    assert is_in_scope("z/b", allowed=("a/**",), forbidden=()) is False
    # No allowed patterns declared → only forbidden constrains.
    assert is_in_scope("z/b", allowed=(), forbidden=("q/**",)) is True


def test_forbidden_wins_and_out_of_scope_paths_filter() -> None:
    assert (
        is_in_scope(
            "repos/x/secrets.py", allowed=("repos/x/**",), forbidden=("repos/x/secrets.py",)
        )
        is False
    )

    result = out_of_scope_paths(
        ("a/ok.txt", "z/bad.txt", "a/secrets"),
        allowed=("a/**",),
        forbidden=("a/secrets",),
    )
    assert result == ("z/bad.txt", "a/secrets")
