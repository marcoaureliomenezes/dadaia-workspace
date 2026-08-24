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

    Implementors resolve the range from ``local_sha``/``remote_sha`` with ONE formula,
    used identically for every push (bug
    new-branch-push-loses-prior-published-denylist-amnesty, v0.4.4 — supersedes the
    v0.9.0/v0.11.0-era two-shape "FR1 range table" this docstring used to describe):

    * ``local_sha`` zero (deletion) -> empty range, no objects.
    * Otherwise -> ``git rev-list --objects local_sha --not --remotes``, ADDITIONALLY
      excluding ``remote_sha`` itself when it happens to resolve to a real local
      commit (harmless when — as in the ordinary git-hook case — the local
      remote-tracking ref already covers it; load-bearing when no remote is
      configured at all, e.g. a synthetic test fixture).

    A brand-new ref's ``remote_sha`` (the git pre-push all-zero sentinel, e.g. a
    ``feature/{M.m.p}`` branch's FIRST push under the gitflow v2 model) therefore
    excludes exactly the same "everything already published to this remote" baseline
    as an ordinary continuing push — there is no separate, weaker fallback shape.

    **Limitation, stated honestly.** ``--remotes`` walks whatever
    ``refs/remotes/<remote>/*`` this repo ALREADY has locally at call time. The
    pre-push hook runs after git has resolved the push's own ref-update lines, but
    that says nothing about how recently this repo last ran ``git fetch`` — a local
    view that is stale relative to the true remote state can under-exclude (treating
    something the remote already has, that this repo has not fetched yet, as novel).
    This implementation deliberately does not fetch inside the hook (a network call
    on every push is its own cost/latency/failure-mode tradeoff); it trusts the
    caller's already-resolved local remote-tracking state, exactly as it always has.

    Blob objects are yielded exactly as before (trees are never returned), deduplicated
    by object sha within one call. As of v0.4.3 T-043-15/FR11, the range's commit
    objects are ALSO yielded — each commit's message BODY only, never its
    ``author``/``committer`` headers (the header/body boundary, A11.6) — through the
    SAME batched conversation and typed-error contract as the blob read; a tag-ref push
    additionally yields the annotated tag's own body (A11.3). These carry
    ``kind="commit"``/``kind="tag"`` (see :class:`ScannedObject`) and a synthetic,
    non-path ``path`` label rather than a real repo path. Any git failure raises
    :class:`GitObjectReadError` rather than returning a partial/empty result.

    **Base resolution for :attr:`ScannedObject.prior_text` (SPEC v0.11.0 FR2, ADR D7;
    widened by bug new-branch-push-loses-prior-published-denylist-amnesty).** The
    SAME exclusion set the range walk uses ALSO decides which commit(s) anchor prior
    content: every object's ``prior_text`` is resolved against the publication
    boundary/boundaries — the commit(s) where ``local_sha``'s own ancestry first
    re-joins that excluded, already-published history — which the adapter derives
    from the exclusion set itself, never from ``remote_sha``'s resolvability alone.
    ``prior_text`` stays an explicit absence (``None``) only when NO such boundary
    exists at all (a genuinely empty/unconfigured remote) — the one honest case with
    no published state to anchor against.
    """

    def new_objects(
        self, repo: Path, local_sha: str, remote_sha: str
    ) -> Iterable[ScannedObject]: ...
