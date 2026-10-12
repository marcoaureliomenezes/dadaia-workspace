"""Pure data types for the push-range git object scan.

Zero I/O (core ring rule): only the result shape, the typed failure, and the branch-
deletion sentinel live here. The sole adapter (subprocess-backed: one
adapter, no port) lives in ``infrastructure/git_objects.py``. Kept in ``core/models/``
rather than the adapter module itself so ``features/chokepoints/**`` — a
security-sensitive push-gate surface that must NEVER gain subprocess reach, even
transitively through a type import — can import these pure value types without also
importing ``subprocess`` (``infrastructure/git_objects.py`` does).
"""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.skill_owner import load_owner

#: A zero sha marks a branch deletion — never scanned, always an empty
#: range. Shared here (rather than re-derived per module) so the adapter and its
#: consumers agree on the sentinel without either importing the other's internals.
ZERO_SHA = "0" * 40
#: A git object sha: 40 (SHA-1) or 64 (SHA-256) hex characters; ZERO_SHA matches it.
SHA_SHAPE_RE = load_owner("dd-bug-resolution", "_grammar").OBJECT_ID_RE


@dataclass(frozen=True)
class ScannedObject:
    """One blob or message body newly reachable in a pushed range.

    ``decodable`` is False for a binary blob, or an oversized blob whose scanned prefix
    failed to decode; ``text`` is then the empty string, and the matcher skips and counts
    the object instead of raising.

    ``oversized`` is True when the git-reported size exceeds the adapter's per-object cap.
    The adapter reads at most the cap's worth of bytes and closes the stream early. When
    that prefix is valid UTF-8, ``decodable`` is True and ``text`` is the decoded prefix,
    so a match inside the first cap bytes still produces a hit. ``size_bytes`` and
    ``scanned_bytes`` are populated only when ``oversized`` is True; both default to 0.

    ``prior_text`` is the full prior text of this same path at the resolvable base, never
    truncated. ``None`` is an explicit absence: no single published base, the path did not
    exist at the base, the prior blob exceeds the size cap, or it is not valid UTF-8. It
    is always ``None`` for an oversized current object.

    ``kind`` is ``"blob"`` (the default: a real blob at a repo-relative ``path``),
    ``"commit"`` (one commit's message body, never its author or committer headers, with a
    synthetic non-path ``path`` label) or ``"tag"`` (an annotated tag's body, yielded only
    for a tag-ref push). A ``"commit"`` or ``"tag"`` object never carries a real path, so
    its ``prior_text`` is always ``None``.
    """

    path: str
    sha: str
    text: str
    decodable: bool
    oversized: bool = False
    size_bytes: int = 0
    scanned_bytes: int = 0
    prior_text: str | None = None
    kind: str = "blob"


class GitObjectReadError(Exception):
    """Listing or reading the pushed-range git objects failed; the gate refuses, never a
    silent "no objects" scan. ``path`` carries the offending blob's path as a STRUCTURED
    field (never in the message), masked at the one render boundary (``push_gate``)."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path


class GitRunError(GitObjectReadError):
    """git itself could not run (missing, timed out): the object store is not at fault."""


__all__ = ["ZERO_SHA", "GitObjectReadError", "GitRunError", "ScannedObject"]
