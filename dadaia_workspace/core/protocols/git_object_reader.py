"""GitObjectReader Protocol — read-only git object-listing port for the push-range scan.

Zero I/O (per the core ring rule): only the Protocol, the result shape, and the typed
failure live here. The concrete adapter (subprocess-backed) lives in
``infrastructure/git_objects.py``; the CLI (``cli/commands/ci.py``) wires it into
``push_gate_decision`` (SPEC v0.9.0 FR1/FR7) — ``features/chokepoints/**`` itself NEVER
imports ``infrastructure`` and NEVER spawns a subprocess.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

#: A zero sha marks a branch deletion (SPEC FR1 row 3) — never scanned, always an empty
#: range. Shared here (rather than re-derived per module) so the port and its adapter
#: agree on the sentinel without either importing ``features.chokepoints``.
ZERO_SHA = "0" * 40


@dataclass(frozen=True)
class ScannedObject:
    """One blob newly reachable in a pushed range (SPEC v0.9.0 FR1).

    ``decodable`` is False for a binary blob (FR6 row 3) or a blob over the adapter's
    size guard (SPEC R3 — a blob that large is never even fetched) — ``text`` is then
    the empty string; undecodable/oversized bytes cannot be usefully matched by a text
    denylist, so the matcher skips and counts it instead of raising.
    """

    path: str
    sha: str
    text: str
    decodable: bool


class GitObjectReadError(Exception):
    """Raised when listing or reading the pushed-range git objects fails.

    Covers a non-zero ``git rev-list``/``git cat-file`` exit and a missing ``git``
    executable (SPEC v0.9.0 FR6 row 2: a policy gate never skips what it cannot
    evaluate). The pure decision function catches this and refuses, naming the failure
    — it never falls through to a silent "no objects" scan.
    """


class GitObjectReader(Protocol):
    """Read-only port over the new objects one pushed ref would publish.

    Implementors resolve the FR1 range table from ``local_sha``/``remote_sha`` alone:

    * ``local_sha`` zero (deletion) -> empty range, no objects.
    * ``remote_sha`` non-zero and resolvable locally -> ``git rev-list --objects
      local_sha --not remote_sha``.
    * ``remote_sha`` zero (new ref) or unresolvable locally -> ``git rev-list --objects
      local_sha --not --remotes``.

    Only blob objects are yielded (commits and trees are never returned), deduplicated
    by object sha within one call. Any git failure raises :class:`GitObjectReadError`
    rather than returning a partial/empty result.
    """

    def new_objects(
        self, repo: Path, local_sha: str, remote_sha: str
    ) -> Iterable[ScannedObject]: ...
