"""The package's door to the one privacy owner, ``dd-bug-resolution/scripts/_privacy.py``."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING, Any

from dadaia_workspace.core.skill_owner import load_owner

__all__ = [
    "PUBLISHED",
    "UNSAFE_FORMAT_CHARS_RE",
    "BaselinePattern",
    "Redactor",
    "compile_candidates",
    "fresh_matches",
    "load_baseline",
    "mask",
    "privacy_matches",
    "publication_boundaries",
    "published_matches",
]

_owner = load_owner("dd-bug-resolution", "_privacy")

PUBLISHED: str = _owner.PUBLISHED
UNSAFE_FORMAT_CHARS_RE: re.Pattern[str] = _owner.UNSAFE_FORMAT_CHARS_RE
mask: Callable[[str], str] = _owner.mask
compile_candidates: Callable[[Iterable[str]], re.Pattern[str] | None] = _owner.compile_candidates
privacy_matches: Callable[
    [str, Iterable[tuple[str, str]], Iterable[Any]], Iterator[tuple[str, str, str]]
] = _owner.privacy_matches
publication_boundaries: Callable[..., tuple[str, ...]] = _owner.publication_boundaries
published_matches: Callable[
    [str | None, Iterable[tuple[str, str]], Iterable[Any]], set[tuple[str, str]] | None
] = _owner.published_matches
fresh_matches: Callable[
    [str, set[tuple[str, str]] | None, Iterable[tuple[str, str]], Iterable[Any]],
    Iterator[tuple[str, str, str]],
] = _owner.fresh_matches
load_baseline: Callable[[], tuple[BaselinePattern, ...]] = _owner.load_baseline

if TYPE_CHECKING:

    class Redactor:
        active: bool

        def __init__(self, candidates: Iterable[str], *, placeholder_fmt: str) -> None: ...
        def mask(self, value: str) -> str: ...

    class BaselinePattern:
        id: str
        regex: re.Pattern[str]
        reason: str
        exclude: re.Pattern[str] | None
        exclude_rationale: str | None

        def __init__(
            self,
            id: str,  # noqa: A002
            regex: re.Pattern[str],
            reason: str,
            exclude: re.Pattern[str] | None,
            exclude_rationale: str | None = ...,
        ) -> None: ...
else:
    Redactor = _owner.Redactor
    BaselinePattern = _owner.BaselinePattern
