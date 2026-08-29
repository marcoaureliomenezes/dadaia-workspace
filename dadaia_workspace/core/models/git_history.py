"""Pure data types for the FR3 bug-provenance commit-history walk.

Zero I/O (core ring rule): only the commit-tuple shape and the typed failure live
here. The sole adapter (``GitSubprocessClient.log_added_lines``, ADR-0001: one
adapter, no port) lives in ``infrastructure/git_subprocess.py``; the pure consumer
(``core/bug_provenance.py``'s ``derive_commit_provenance``) imports only
:class:`HistoryCommit` from here — never the adapter itself.
"""

from __future__ import annotations

from dataclasses import dataclass


class GitHistoryReadError(Exception):
    """Raised when walking the ledger's commit history, or reading one commit's
    added-line diff / whole-commit touched-path list, fails — a non-zero git exit or a
    missing ``git`` executable. A history-derivation caller never falls through to a
    silent empty/partial result on a git failure; it raises and the caller decides."""


@dataclass(frozen=True)
class HistoryCommit:
    """One commit in the chronological, all-refs walk over a pathspec (FR3 steps 1-2).

    ``sha`` / ``parents`` / ``date`` describe the commit itself — ``parents`` is every
    parent sha (empty for a root commit; ``--no-merges`` means at most one in practice,
    but the field stays a tuple rather than assuming exactly one, and is reserved for a
    future topological tie-break / migration-report use — the pure derivation in
    ``core/bug_provenance.py`` does not consume it today, trusting the reader's own
    chronological ordering instead (see that module's docstring)). ``date`` is the git
    ``%aI`` (strict ISO-8601, author date) string, kept as text rather than parsed here
    — this is a zero-I/O DATA shape, not a place to import ``datetime`` parsing rules
    the derivation does not need.

    ``touched_paths`` is the commit's **whole, unrestricted** changed-path set — every
    path the commit touches, not just the ones inside *pathspec* (AR-1 ruling (c)4: the
    ``exact`` granularity marker requires "touches a file outside ``specs/``", which
    ``git log -p -- specs/bugs/`` alone can never answer, because both ``-p`` and
    ``--name-only`` restrict to the pathspec).

    ``added_lines`` is the **pathspec-restricted** set of lines this commit ADDED (never
    removed/context lines) to *pathspec* — one raw line of text per entry, in diff
    order, with the leading ``+`` diff marker already stripped and no trailing newline.
    Each is fed to a caller-supplied classifier (``core.bug_provenance.LineClassifier``)
    that decodes the v5/v6 boundary shape — this dataclass carries the raw text only, no
    JSON parsing, no bug-domain knowledge (A2.5: that decoding is
    ``features/bugs/migrate_v5.py``'s job alone).
    """

    sha: str
    parents: tuple[str, ...]
    date: str
    touched_paths: tuple[str, ...]
    added_lines: tuple[str, ...]


__all__ = ["GitHistoryReadError", "HistoryCommit"]
