"""One definition of the rules for a release's on-disk layout, proven once.

These cases are the union of what three separate modules each got wrong on their own
copy of this knowledge. They live here so the next caller inherits the fixes instead of
rediscovering the bugs.

The module is deliberately PURE — `core` is file-I/O-free by ratchet, and the boundary is
worth more than the convenience of an `iterdir` here. Listing a directory is one line at
the call site that cannot drift in meaning; the RULES are what drifted.
"""

from __future__ import annotations

from dadaia_workspace.core.release_layout import (
    CLOSURE_ARTIFACT,
    next_segment_name,
    ordered_segments,
    segment_sort_key,
)


def test_segments_order_numerically_not_lexicographically() -> None:
    """`alpha-10` matures AFTER `alpha-2`; string ordering says the opposite."""
    assert ordered_segments(["alpha-10", "alpha-2", "rc-1", "alpha-1"]) == [
        "alpha-1",
        "alpha-2",
        "alpha-10",
        "rc-1",
    ]


def test_the_last_ordered_segment_is_the_current_one() -> None:
    assert ordered_segments(["alpha-1", "rc-1"])[-1] == "rc-1"


def test_an_unknown_segment_shape_sorts_last_without_crashing() -> None:
    """A hand-made directory must not break resolution for the real segments."""
    assert ordered_segments(["rc-1", "scratch", "alpha-1"]) == ["alpha-1", "rc-1", "scratch"]


def test_the_next_segment_advances_the_current_kind() -> None:
    assert next_segment_name([]) == "alpha-1"
    assert next_segment_name(["alpha-1"]) == "alpha-2"
    assert next_segment_name(["alpha-1", "alpha-2"]) == "alpha-3"
    assert next_segment_name(["alpha-1", "rc-1"]) == "rc-2", "reached rc ⇒ advance rc"


def test_the_closure_artifact_has_one_name() -> None:
    """Four modules each decided independently what 'closed' looks like."""
    assert CLOSURE_ARTIFACT == "CLOSURE.md"


def test_the_sort_key_is_total_over_junk() -> None:
    for name in ("", "-", "alpha-", "alpha-x", "12"):
        assert isinstance(segment_sort_key(name), tuple)
