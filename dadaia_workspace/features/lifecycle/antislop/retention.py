"""Directory-aware retention SWEEP (D5) — the consolidated, guarded deleter.

WS-6 shipped the directory-aware *metric* (``slop_scan``). This module is the *deleter*
layered on that metric: it actually reclaims past-TTL / non-canonical entries from the
recognised swept ``.dadaia/`` zones — whole directory trees via ``rmtree`` (the 12 GB
stray-venv case the file-only cleanup could never see) and files via ``unlink``.

**This code deletes files. Safety is the whole job.** Every reclaim is gated by a fixed
ladder of refusals, evaluated *before* any destructive call. In order:

1. **Dry-run by default.** ``sweep()`` previews; it deletes only when ``apply=True`` is
   passed explicitly. The CLI default is dry-run.
2. **Zone confinement.** Only the recognised swept zones are ever considered
   (``.dadaia/{tmp,reports,handoff,runs}``). Nothing else under ``.dadaia/`` — and
   nothing outside it — is even discovered.
3. **Escape refusal.** An entry whose *resolved* path escapes the workspace ``.dadaia/``
   (a symlink pointing out, ``..`` traversal) is refused, never followed. Following it
   would delete an arbitrary external tree.
4. **Liveness gate (HARD, EPIC D6).** An entry claimed by a LIVE lifecycle run — or
   nested under such a claim — is never reclaimed, even past-TTL. Reclaiming a live
   worker's tmp mid-flight is a worse incident than the slop.
5. **Important protection.** An operator-marked-important (or current-release-evidence)
   ref is never reclaimed.
6. **TTL.** Only entries past their zone TTL are reclaimable; canonical-within-TTL
   entries survive.

The sweep is **idempotent** and uses an **injected clock**: a first apply removes exactly
the reclaimable, non-live, non-important set; a second apply removes nothing and leaves
survivors byte-identical.

Layering: this lives in ``features/`` and imports only ``core/`` + sibling ``features/``
(it reuses ``antislop.slop_scan`` recursive-size + zone helpers). The run-store-derived
live-claim set and the important-ref set are **injected callables**, wired by the
container — no direct ``infrastructure`` import.
"""

from __future__ import annotations

import datetime as dt
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.features.lifecycle.antislop.slop_scan import (
    _recursive_size,
    _swept_zones,
)


class RetentionSkipReason(StrEnum):
    """Why a discovered swept-zone entry was NOT reclaimed."""

    #: Claimed by (or nested under) a live lifecycle run — never reclaimed mid-flight.
    LIVE = "live"
    #: Operator-marked important / current-release evidence.
    IMPORTANT = "important"
    #: Resolved path escapes the workspace ``.dadaia/`` (symlink-out, ``..``). Refused.
    ESCAPE = "escape"


@dataclass(frozen=True)
class RetentionResult:
    """Typed outcome of one retention sweep.

    ``reclaimed_paths`` / ``reclaimed_bytes`` describe what was (or, in dry-run, would be)
    removed. ``skipped`` records every entry that was a TTL/zone candidate but spared, with
    the guard that spared it — the audit trail for the destructive decision.
    """

    applied: bool
    reclaimed_paths: tuple[str, ...]
    reclaimed_bytes: int
    skipped: tuple[tuple[str, RetentionSkipReason], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "reclaimed_paths": list(self.reclaimed_paths),
            "reclaimed_bytes": self.reclaimed_bytes,
            "skipped": [{"path": path, "reason": reason.value} for path, reason in self.skipped],
        }


@dataclass(frozen=True)
class _Candidate:
    """A past-TTL swept-zone reporting unit considered for reclaim."""

    rel: str
    node: Path
    size_bytes: int
    is_dir: bool


class RetentionSweep:
    """Directory-aware, liveness-gated, dry-run-by-default retention deleter.

    Args:
        workspace_root: Workspace root (the parent of ``.dadaia/``).
        now: Injected clock (UTC). Deterministic reclaim decisions in tests.
        policy: ``SlopPolicy`` carrying the per-zone TTLs.
        live_claims: Callable returning the set of workspace-relative posix paths claimed
            by LIVE lifecycle runs. An entry equal to, or nested under, any claim is spared
            (``RetentionSkipReason.LIVE``). Defaults to "no live claims".
        important_paths: Callable returning the set of workspace-relative posix paths that
            are operator-marked important / current-release evidence. Spared
            (``RetentionSkipReason.IMPORTANT``). Defaults to "none important".
    """

    def __init__(
        self,
        workspace_root: Path,
        *,
        now: dt.datetime,
        policy: SlopPolicy | None = None,
        live_claims: Callable[[], frozenset[str]] | None = None,
        important_paths: Callable[[], frozenset[str]] | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._dadaia_root = self._workspace_root / ".dadaia"
        self._now = now.astimezone(dt.UTC)
        self._policy = policy or SlopPolicy()
        self._live_claims = live_claims or (lambda: frozenset())
        self._important_paths = important_paths or (lambda: frozenset())

    @property
    def policy(self) -> SlopPolicy:
        return self._policy

    def sweep(self, *, apply: bool = False) -> RetentionResult:
        """Preview (default) or — only with ``apply=True`` — reclaim swept-zone slop.

        Discovery walks the recognised swept zones and collects past-TTL reporting units
        (a directory tree is ONE unit with its recursive byte size — the directory-aware
        reclaim WS-6's metric measured). Each unit then passes the guard ladder; survivors
        of the ladder are reclaimed (``rmtree`` for a dir, ``unlink`` for a file) only when
        ``apply`` is true.
        """
        live = self._live_claims()
        important = self._important_paths()

        reclaimed_paths: list[str] = []
        reclaimed_bytes = 0
        skipped: list[tuple[str, RetentionSkipReason]] = []

        for candidate in self._candidates():
            reason = self._skip_reason(candidate, live=live, important=important)
            if reason is not None:
                skipped.append((candidate.rel, reason))
                continue
            if apply:
                if not self._reclaim(candidate):
                    # Disappeared / vanished under us — not an error, just nothing to do.
                    continue
                self._prune_empty_parents(candidate.node)
            reclaimed_paths.append(candidate.rel)
            reclaimed_bytes += candidate.size_bytes

        return RetentionResult(
            applied=apply,
            reclaimed_paths=tuple(reclaimed_paths),
            reclaimed_bytes=reclaimed_bytes,
            skipped=tuple(skipped),
        )

    # -- discovery ------------------------------------------------------------------

    def _candidates(self) -> list[_Candidate]:
        """Past-TTL reporting units across every swept zone, directory-aware.

        Mirrors ``slop_scan``'s reporting granularity (a dir tree with direct files is ONE
        unit) but keeps the *un-resolved* node so the escape guard can inspect symlinks
        before any reclaim — ``slop_scan`` resolves paths for its metric, which is unsafe
        for a deleter.
        """
        if not self._dadaia_root.is_dir():
            return []
        out: list[_Candidate] = []
        for zone_name, ttl_seconds in _swept_zones(self._policy):
            zone_dir = self._dadaia_root / zone_name
            if not zone_dir.is_dir():
                continue
            cutoff = self._now - dt.timedelta(seconds=ttl_seconds)
            for child in sorted(zone_dir.iterdir()):
                self._collect(child, cutoff, out)
        return out

    def _collect(self, node: Path, cutoff: dt.datetime, out: list[_Candidate]) -> None:
        # A symlink is a leaf for the deleter — never descend through it. Its TTL/escape
        # checks happen at the unit level below.
        if node.is_symlink():
            self._collect_unit(node, cutoff, out)
            return
        if node.is_file():
            self._collect_unit(node, cutoff, out)
            return
        if not node.is_dir():
            return
        children = sorted(node.iterdir())
        has_direct_file = any(c.is_file() and not c.is_symlink() for c in children)
        if has_direct_file or not children:
            self._collect_unit(node, cutoff, out)
            return
        for child in children:
            self._collect(child, cutoff, out)

    def _collect_unit(self, node: Path, cutoff: dt.datetime, out: list[_Candidate]) -> None:
        rel = self._rel_unresolved(node)
        if rel is None:
            return
        # A symlink whose target escapes is reported (so the escape guard can record it),
        # with a zero recursive size — its size is irrelevant, it will never be deleted.
        if node.is_symlink():
            out.append(_Candidate(rel=rel, node=node, size_bytes=0, is_dir=node.is_dir()))
            return
        newest = self._newest_mtime(node)
        if newest is not None and newest >= cutoff:
            return  # within TTL — canonical, not reclaimable.
        size_bytes, _ = _recursive_size(node)
        out.append(_Candidate(rel=rel, node=node, size_bytes=size_bytes, is_dir=node.is_dir()))

    # -- guard ladder ---------------------------------------------------------------

    def _skip_reason(
        self,
        candidate: _Candidate,
        *,
        live: frozenset[str],
        important: frozenset[str],
    ) -> RetentionSkipReason | None:
        """Return the guard that spares this candidate, or ``None`` to allow reclaim.

        Order matters: ESCAPE first (never even resolve-confine a path that escapes),
        then LIVE (a live worker's tree is sacrosanct), then IMPORTANT.
        """
        if not self._is_confined(candidate.node):
            return RetentionSkipReason.ESCAPE
        if self._is_live(candidate.rel, live):
            return RetentionSkipReason.LIVE
        if self._touches_important(candidate.rel, important):
            return RetentionSkipReason.IMPORTANT
        return None

    def _is_confined(self, node: Path) -> bool:
        """True iff the *resolved* node stays inside the workspace ``.dadaia/``.

        Refuses symlink-out and ``..`` traversal: resolving the node and confirming it is
        still under ``.dadaia/`` is the single anti-escape invariant for the deleter.
        """
        try:
            resolved = node.resolve()
        except OSError:
            return False
        try:
            resolved.relative_to(self._dadaia_root)
        except ValueError:
            return False
        return True

    @staticmethod
    def _is_live(rel: str, live: frozenset[str]) -> bool:
        """True iff *rel* equals, or is nested under, any live-run claim."""
        return any(rel == claim or rel.startswith(claim.rstrip("/") + "/") for claim in live)

    @staticmethod
    def _touches_important(rel: str, important: frozenset[str]) -> bool:
        """True iff reclaiming *rel* would remove an important ref.

        A directory candidate is spared if it equals an important ref, is nested under
        one, OR *contains* one (an important file inside a stale dir tree must never be
        collaterally deleted by the directory-aware ``rmtree``).
        """
        prefix = rel.rstrip("/") + "/"
        return any(
            rel == ref or rel.startswith(ref.rstrip("/") + "/") or ref.startswith(prefix)
            for ref in important
        )

    # -- reclaim --------------------------------------------------------------------

    def _reclaim(self, candidate: _Candidate) -> bool:
        """Remove the candidate. Returns False if it vanished before the call.

        Re-confirms confinement immediately before the destructive call (TOCTOU defence):
        the guard ladder already checked it, but the node is re-resolved here so the actual
        ``rmtree``/``unlink`` can never operate on an escaped path. A directory is removed
        with ``shutil.rmtree``; a file (or symlink) with ``unlink``.
        """
        node = candidate.node
        if not node.exists() and not node.is_symlink():
            return False
        if not self._is_confined(node):
            return False
        # rmtree CALL SITE: gated by _is_confined (escape), the LIVE skip, the IMPORTANT
        # skip, and the past-TTL discovery filter — all evaluated in `sweep`/`_skip_reason`
        # before we get here, then re-confined immediately above.
        if node.is_dir() and not node.is_symlink():
            shutil.rmtree(node)
            return True
        node.unlink(missing_ok=True)
        return True

    def _prune_empty_parents(self, removed: Path) -> None:
        """Remove now-empty scaffolding dirs left above a reclaimed unit.

        After ``rmtree``-ing ``.dadaia/tmp/agent/stale`` the ``agent`` bucket may be empty;
        leaving it would make the next sweep rediscover it (an empty dir is reclaimable),
        breaking idempotency. We walk up to — but never including — the zone root, removing
        each dir only while it is genuinely empty and still confined under ``.dadaia/``.
        """
        zone_roots = {self._dadaia_root / zone_name for zone_name, _ in _swept_zones(self._policy)}
        parent = removed.parent
        while parent not in zone_roots and self._is_confined(parent):
            try:
                parent.rmdir()  # only succeeds when empty
            except OSError:
                return
            parent = parent.parent

    # -- helpers --------------------------------------------------------------------

    def _rel_unresolved(self, node: Path) -> str | None:
        """Workspace-relative posix ref using the *un-resolved* node.

        Unlike ``slop_scan``, the deleter must key its guards on the literal swept-zone
        path the operator sees (``.dadaia/tmp/...``), not on a symlink's resolved target —
        otherwise a symlink would be keyed by where it points, defeating the escape guard.
        """
        try:
            return node.relative_to(self._workspace_root).as_posix()
        except ValueError:
            return None

    @staticmethod
    def _newest_mtime(node: Path) -> dt.datetime | None:
        if node.is_file():
            return dt.datetime.fromtimestamp(node.stat().st_mtime, tz=dt.UTC)
        newest: dt.datetime | None = None
        for child in node.rglob("*"):
            if child.is_symlink() or not child.is_file():
                continue
            try:
                mtime = dt.datetime.fromtimestamp(child.stat().st_mtime, tz=dt.UTC)
            except OSError:
                continue
            if newest is None or mtime > newest:
                newest = mtime
        return newest
