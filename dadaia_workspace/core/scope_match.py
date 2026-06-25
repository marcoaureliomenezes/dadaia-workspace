"""Shared write-scope matching for lifecycle worker boundaries.

One classifier, two boundaries: the runner's Ring-2 post-flight detective check
(`LifecycleAgentRunner`) and the Claude adapter's Ring-1 pre-disk `can_use_tool`
decider both call these pure functions, so an in-scope/out-of-scope decision is
identical wherever it is enforced.
"""

from __future__ import annotations

from collections.abc import Iterable


def matches_path(path: str, pattern: str) -> bool:
    """Return whether ``path`` is covered by a scope ``pattern``.

    ``foo/**`` matches ``foo`` and anything under it; ``foo/*`` matches direct
    children only; a bare ``foo`` matches ``foo`` and its subtree.
    """
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    if pattern.endswith("/*"):
        prefix = pattern[:-1]
        return path.startswith(prefix) and "/" not in path[len(prefix) :]
    return path == pattern or path.startswith(f"{pattern}/")


def is_in_scope(path: str, *, allowed: Iterable[str], forbidden: Iterable[str]) -> bool:
    """A path is in scope when it matches no forbidden pattern and (if any allowed
    patterns are declared) matches at least one allowed pattern."""
    if any(matches_path(path, pattern) for pattern in forbidden):
        return False
    allowed_patterns = tuple(allowed)
    return not allowed_patterns or any(matches_path(path, pattern) for pattern in allowed_patterns)


def out_of_scope_paths(
    paths: Iterable[str],
    *,
    allowed: Iterable[str],
    forbidden: Iterable[str],
) -> tuple[str, ...]:
    """Return the subset of ``paths`` that fall outside the declared write scope."""
    allowed_patterns = tuple(allowed)
    forbidden_patterns = tuple(forbidden)
    return tuple(
        path
        for path in paths
        if not is_in_scope(path, allowed=allowed_patterns, forbidden=forbidden_patterns)
    )
