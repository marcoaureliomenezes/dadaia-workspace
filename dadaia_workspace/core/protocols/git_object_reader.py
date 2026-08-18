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

    ``decodable`` is False for a binary blob (FR6 row 3) or an oversized blob whose
    scanned prefix failed to decode (SPEC v0.11.0 A4.6) — ``text`` is then the empty
    string; undecodable bytes cannot be usefully matched by a text denylist, so the
    matcher skips and counts it instead of raising.

    ``oversized`` (SPEC v0.11.0 FR4, supersedes the v0.9.0 total-blind-spot R3 guard)
    is True when the blob's GIT-REPORTED size exceeds the adapter's per-object cap. The
    adapter never fetches the whole such blob: it reads at most the cap's worth of
    bytes through a separate, bounded stream and closes it early, so the remainder is
    genuinely never fetched. When that prefix IS valid UTF-8, ``decodable`` is True and
    ``text`` carries the DECODED PREFIX (not the whole blob) — the matcher scans it like
    any other object, so a match inside the first cap bytes still produces a hit
    (partial coverage, not zero coverage). ``size_bytes`` (the blob's total size) and
    ``scanned_bytes`` (how many bytes were actually read) are populated only when
    ``oversized`` is True; both default to 0 for an ordinary, non-oversized object.

    ``prior_text`` (SPEC v0.11.0 FR2, ADR D7) is the published prior text of this SAME
    path, at the resolvable base — ``None`` is an EXPLICIT absence, never an empty
    string. Absence covers four situations the adapter never distinguishes further (the
    FR1 amnesty predicate treats all four identically): the range has no single
    published base (the ``--not --remotes`` fallback shape — no object anywhere carries
    prior content in that shape); the path did not exist at the base (a genuinely new
    file); the prior blob at the base exceeds the adapter's size cap; or the prior blob
    at the base is not valid UTF-8. A non-``None`` value is always the FULL prior
    content at that path (never truncated) — the resolvable-base lookup only ever
    fetches prior blobs already known to be under the cap. Not populated for an
    oversized CURRENT object (stays ``None``) — the prior-side lookup rides the FR9
    batched chunk loop only, never the oversized per-object path.

    ``kind`` (v0.4.3 T-043-15/FR11) discriminates what this object actually is:
    ``"blob"`` (the default — every pre-v0.4.3 object, unchanged) is a real blob at a
    real repo-relative ``path``; ``"commit"`` is one commit's message BODY (never its
    ``author``/``committer`` headers, A11.6) with a synthetic, non-path ``path`` label;
    ``"tag"`` is an annotated tag's own body, same shape, yielded only for a tag-ref
    push. A ``"commit"``/``"tag"`` object NEVER carries a real path — there is nothing
    to key a prior-text amnesty lookup on, so ``prior_text`` is always ``None`` for it,
    fail-closed by construction (A11.7).
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
    """Raised when listing or reading the pushed-range git objects fails.

    Covers a non-zero ``git rev-list``/``git cat-file`` exit and a missing ``git``
    executable (SPEC v0.9.0 FR6 row 2: a policy gate never skips what it cannot
    evaluate). The pure decision function catches this and refuses, naming the failure
    — it never falls through to a silent "no objects" scan.

    ``path`` (SPEC v0.4.2 FR4/GRILL P9) carries the offending blob's path as a
    STRUCTURED field, never embedded in the message string: a raise site that knows
    which path it failed on (e.g. the prior-content resolution desync in
    ``infrastructure.git_objects._resolve_prior_texts``) passes it here, and the single
    render boundary that catches this error (``features.chokepoints.service``) masks it
    through the SAME ``_PathMasker`` every other channel uses before it ever reaches an
    operator-facing string — the message itself never carries a raw path.
    """

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path


class GitObjectReader(Protocol):
    """Read-only port over the new objects one pushed ref would publish.

    Implementors resolve the FR1 range table from ``local_sha``/``remote_sha`` alone:

    * ``local_sha`` zero (deletion) -> empty range, no objects.
    * ``remote_sha`` non-zero and resolvable locally -> ``git rev-list --objects
      local_sha --not remote_sha``.
    * ``remote_sha`` zero (new ref) or unresolvable locally -> ``git rev-list --objects
      local_sha --not --remotes``.

    Blob objects are yielded exactly as before (trees are never returned), deduplicated
    by object sha within one call. As of v0.4.3 T-043-15/FR11, the range's commit
    objects are ALSO yielded — each commit's message BODY only, never its
    ``author``/``committer`` headers (the header/body boundary, A11.6) — through the
    SAME batched conversation and typed-error contract as the blob read; a tag-ref push
    additionally yields the annotated tag's own body (A11.3). These carry
    ``kind="commit"``/``kind="tag"`` (see :class:`ScannedObject`) and a synthetic,
    non-path ``path`` label rather than a real repo path. Any git failure raises
    :class:`GitObjectReadError` rather than returning a partial/empty result.

    **Base resolution for :attr:`ScannedObject.prior_text` (SPEC v0.11.0 FR2, ADR D7).**
    The SAME ``remote_sha`` resolvability check that decides the FR1 range shape ALSO
    decides whether any object in this call carries prior content: resolvable
    ``remote_sha`` -> that sha is the base every object's prior text is resolved
    against; unresolvable/zero ``remote_sha`` (the fallback shape) -> there is no
    single published base, so every object carries an explicit absence
    (``prior_text=None``) and behaviour is byte-identical to v0.9.0. This is a
    deliberate conservative boundary, not an oversight — widening it is a future
    decision, not a defect of this release.
    """

    def new_objects(
        self, repo: Path, local_sha: str, remote_sha: str
    ) -> Iterable[ScannedObject]: ...
