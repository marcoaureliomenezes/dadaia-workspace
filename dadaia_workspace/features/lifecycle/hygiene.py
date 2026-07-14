"""Lifecycle hygiene status service driven by the canonical SlopPolicy."""

from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any

from dadaia_workspace.core.models.hygiene import (
    HygieneCandidate,
    HygieneCandidateKind,
    HygieneCounters,
    HygieneProtectionKind,
    HygieneZone,
    SlopPolicy,
)

if TYPE_CHECKING:
    from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore


#: Zone doc filenames that are canonical (scoped-rules / zone documentation), never
#: reclaimable (v0.1.74).
_CANONICAL_ZONE_DOC_NAMES = frozenset({"AGENTS.md", "README.md", ".gitkeep"})


@dataclass(frozen=True)
class WorkflowStepPayloadCounts:
    """Workflow-step payload state counters (v0.1.30 Item 5 / T-30-D-07).

    Separate from the generic handoff orphan/malformed counters — these count the
    run-scoped workflow-step data plane (``.dadaia/runs/lifecycle/<run>/steps/``) against
    the ``LifecycleRun.workflow_steps`` ledger.
    """

    produced: int = 0
    consumed_all: int = 0
    orphan: int = 0
    malformed: int = 0
    undeclared: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "produced": self.produced,
            "consumed_all": self.consumed_all,
            "orphan": self.orphan,
            "malformed": self.malformed,
            "undeclared": self.undeclared,
        }


@dataclass(frozen=True)
class HygieneCleanupResult:
    """Outcome of a lifecycle hygiene cleanup pass."""

    dry_run: bool
    candidates: tuple[HygieneCandidate, ...]
    deleted_paths: tuple[Path, ...] = field(default_factory=tuple)
    skipped_paths: tuple[Path, ...] = field(default_factory=tuple)
    pruned_dirs: tuple[Path, ...] = field(default_factory=tuple)


class LifecycleHygieneService:
    """Compute workspace hygiene counters without mutating the filesystem."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        policy: SlopPolicy | None = None,
        now: dt.datetime | None = None,
        active_release_id: str | None = None,
        run_store: LifecycleRunStore | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._dadaia_root = self._workspace_root / ".dadaia"
        self._policy = policy or SlopPolicy()
        self._now = now
        self._active_release_id = active_release_id
        # v0.1.78 T-C / FR-C: additive-optional. When wired, ``cleanup()`` ALSO reclaims
        # stale, cleanup-eligible workflow-step handoff-ledger payloads under
        # ``.dadaia/runs/lifecycle/`` — the ONE canonical cleanup contract that closes the
        # split-cleanup-engines hole (``dadaia reports workflow-hygiene-clean``, the command
        # preflight's remediation prints, used to be blind to that zone; only the
        # DIFFERENT top-level ``dadaia clean`` / RetentionSweep command covered it). When
        # absent (the pre-v0.1.78 default construction), behavior is byte-identical to
        # before — no step-payload candidates are discovered.
        self._run_store = run_store

    @property
    def policy(self) -> SlopPolicy:
        return self._policy

    def cleanup(self, *, dry_run: bool = True) -> HygieneCleanupResult:
        """Discover and optionally delete expired safe-zone runtime files.

        v0.1.78 T-C / FR-C: when a ``run_store`` is wired, the candidate set is UNIONED
        with stale, cleanup-eligible workflow-step payloads (the same TTL + liveness +
        consumption guard the doctor/retention-sweep already apply for that zone) — one
        candidate classifier, one reclaim pass, shared by status/preflight-remediation/
        doctor/dry-run/apply. Reclaiming a step payload ALSO drops its ledger record in the
        same operation (:meth:`WorkflowStepLedger.remove`) so the doctor never sees the
        physically-deleted file as a dangling ORPHAN record — a reclaim must never trade
        one finding for another.
        """
        protected_paths = self._protected_paths()
        candidates = tuple(self._cleanup_candidates(protected_paths))
        step_payload_candidates, ledger_keys = self._step_payload_candidates()
        all_candidates = candidates + tuple(step_payload_candidates)
        if dry_run:
            return HygieneCleanupResult(dry_run=True, candidates=all_candidates)

        deleted: list[Path] = []
        skipped: list[Path] = []
        for candidate in candidates:
            path = self._workspace_root / candidate.path
            if candidate.protected or not self._is_mutable_safe_zone_file(path):
                skipped.append(path)
                continue
            try:
                if path.is_file():
                    path.unlink()
                    deleted.append(path)
            except OSError:
                skipped.append(path)

        for candidate in step_payload_candidates:
            path = self._workspace_root / candidate.path
            if candidate.protected:
                skipped.append(path)
                continue
            try:
                if path.is_file():
                    path.unlink()
                    deleted.append(path)
                    self._prune_ledger_record(candidate.path, ledger_keys)
            except OSError:
                skipped.append(path)

        pruned = self._prune_empty_safe_dirs()
        return HygieneCleanupResult(
            dry_run=False,
            candidates=all_candidates,
            deleted_paths=tuple(deleted),
            skipped_paths=tuple(skipped),
            pruned_dirs=tuple(pruned),
        )

    def _step_payload_candidates(
        self,
    ) -> tuple[list[HygieneCandidate], dict[str, tuple[str, str, int]]]:
        """Stale, cleanup-eligible workflow-step payloads under ``.dadaia/runs/lifecycle/``.

        A payload is a reclaim candidate ONLY when ALL of:

        - its ledger record is ``is_cleanup_eligible()`` (``DELETE_AFTER_CONSUMED`` +
          every declared consumer has consumed it — mirrors the doctor's STALE check and
          the retention sweep's reclaim-allow set: one eligibility rule, never a second
          drifting definition);
        - the OWNING RUN is terminal (``COMPLETED``/``FAILED``) — a live run's payload is
          NEVER a candidate, matching the retention sweep's hard liveness gate;
        - the on-disk file's mtime is past the tmp-zone consumed TTL (the same TTL
          ``_swept_zones`` borrows for the ``runs`` zone, and the doctor's stale check
          uses).

        Returns ``(candidates, ledger_keys)`` where ``ledger_keys`` maps each candidate's
        workspace-relative ``path`` to its ``(run_id, producer_step, attempt)`` identity —
        the key :meth:`_prune_ledger_record` needs to drop the ledger record alongside the
        physical delete. Returns ``([], {})`` when no ``run_store`` is wired (back-compat:
        a default-constructed service behaves exactly as before this FR).
        """
        if self._run_store is None:
            return [], {}
        from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

        terminal = {LifecycleRunStatus.COMPLETED, LifecycleRunStatus.FAILED}
        cutoff = self._clock() - dt.timedelta(seconds=self._policy.tmp_ttl_seconds)
        candidates: list[HygieneCandidate] = []
        ledger_keys: dict[str, tuple[str, str, int]] = {}
        for run in self._run_store.list_runs():
            if run.status not in terminal:
                continue
            for record in run.workflow_steps:
                if not record.is_cleanup_eligible():
                    continue
                path = self._workspace_root / record.payload_ref
                if not path.is_file():
                    continue
                mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
                if mtime >= cutoff:
                    continue
                candidates.append(
                    HygieneCandidate(
                        path=record.payload_ref,
                        zone=HygieneZone.TMP,
                        kind=HygieneCandidateKind.EXPIRED_STEP_PAYLOAD,
                        reason=f"consumed workflow-step payload older than "
                        f"{self._policy.tmp_ttl_seconds} second TTL",
                        age_seconds=int((self._clock() - mtime).total_seconds()),
                        protected=False,
                    )
                )
                ledger_keys[record.payload_ref] = (run.run_id, record.producer_step, record.attempt)
        return candidates, ledger_keys

    def _prune_ledger_record(
        self, payload_ref: str, ledger_keys: dict[str, tuple[str, str, int]]
    ) -> None:
        """Drop the just-deleted payload's ledger record from its owning run (T-C).

        Reloads the run fresh (never trusts a stale in-memory copy across the reclaim
        pass — another record on the SAME run may have already been pruned earlier in
        this loop) and persists the pruned ledger. Fail-soft: a load/save error is
        swallowed — the physical file is already gone either way, and a subsequent
        ``handoffs doctor`` run would surface a genuine store problem on its own terms
        rather than this reclaim pass crashing mid-sweep.
        """
        assert self._run_store is not None
        key = ledger_keys.get(payload_ref)
        if key is None:
            return
        run_id, producer_step, attempt = key
        try:
            run = self._run_store.load(run_id)
            if run is None:
                return
            pruned_ledger = run.workflow_steps.remove(producer_step, attempt)
            if pruned_ledger is run.workflow_steps:
                return
            from dataclasses import replace

            self._run_store.save(replace(run, workflow_steps=pruned_ledger))
        except Exception:  # noqa: BLE001 — reclaim never crashes on a ledger-save hiccup.
            return

    def protected_refs(self) -> frozenset[str]:
        """Workspace-relative refs the hygiene service protects from deletion.

        Reused by the directory-aware retention SWEEP (D5) so the deleter inherits the
        same operator-marked-important + current-release-evidence + protected-handoff
        protection the file-only cleanup already enforces. Read-only; no mutation.
        """
        return frozenset(self._protected_paths())

    def workflow_step_payload_counts(
        self, run_store: LifecycleRunStore
    ) -> WorkflowStepPayloadCounts:
        """Count workflow-step payloads by ledger/disk state (v0.1.30 Item 5 / T-30-D-07).

        Reads every persisted run's ``workflow_steps`` ledger and reconciles it with the
        on-disk payloads under ``.dadaia/runs/lifecycle/<run>/steps/``:

        - ``produced`` — total ledger records;
        - ``consumed_all`` — records every declared consumer has consumed (cleanup-eligible);
        - ``orphan`` — a ledger record whose on-disk payload file is missing;
        - ``malformed`` — an on-disk ``*.step-payload.json`` that is not valid JSON;
        - ``undeclared`` — an on-disk payload with no matching ledger record.

        These are workflow-step counters kept separate from the generic handoff
        orphan/malformed counters (which count ``.dadaia/handoff/*.handoff.json``).
        """
        produced = consumed_all = orphan = malformed = undeclared = 0
        ledger_refs: set[str] = set()
        for run in run_store.list_runs():
            for record in run.workflow_steps:
                produced += 1
                ledger_refs.add(record.payload_ref)
                if record.is_cleanup_eligible():
                    consumed_all += 1
                if not (self._workspace_root / record.payload_ref).is_file():
                    orphan += 1
        steps_root = self._dadaia_root / "runs" / "lifecycle"
        if steps_root.is_dir():
            for payload in steps_root.rglob("*.step-payload.json"):
                if not payload.is_file():
                    continue
                rel = self._workspace_ref(payload)
                try:
                    json.loads(payload.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    malformed += 1
                    continue
                if rel not in ledger_refs:
                    undeclared += 1
        return WorkflowStepPayloadCounts(
            produced=produced,
            consumed_all=consumed_all,
            orphan=orphan,
            malformed=malformed,
            undeclared=undeclared,
        )

    def status(self) -> HygieneCounters:
        """Return metadata-only counters for canonical runtime zones."""
        started = self._clock()
        zone_totals: dict[HygieneZone, int] = {}
        expired_totals: dict[HygieneZone, int] = {}

        unreclaimable_total = 0
        for zone in self._policy.safe_zones:
            total, expired, unreclaimable = self._zone_counts(zone)
            zone_totals[zone] = total
            expired_totals[zone] = expired
            unreclaimable_total += unreclaimable

        orphan_handoffs, malformed_handoffs = self._handoff_semantic_counts()
        protected_paths = self._protected_paths()
        cleanup_candidates = sum(expired_totals.values())
        elapsed = int((self._clock() - started).total_seconds() * 1000)
        return HygieneCounters(
            zone_totals=zone_totals,
            expired_totals=expired_totals,
            orphan_handoff_count=orphan_handoffs,
            malformed_handoff_count=malformed_handoffs,
            unknown_top_level_dirs=self._unknown_top_level_dirs(),
            cleanup_candidate_count=cleanup_candidates,
            protected_residual_count=self._protected_residual_count(protected_paths),
            unreclaimable_count=unreclaimable_total,
            scan_elapsed_ms=elapsed,
        )

    def _cleanup_candidates(
        self, protected_paths: dict[str, HygieneProtectionKind]
    ) -> list[HygieneCandidate]:
        candidates: list[HygieneCandidate] = []
        operator_globs = self._operator_exception_globs()

        for zone in self._policy.safe_zones:
            zone_dir = self._dadaia_root / zone.value
            if not zone_dir.is_dir():
                continue
            zone_root = zone_dir.resolve()
            cutoff = self._clock() - dt.timedelta(seconds=self._policy.ttl_for(zone))
            for path in sorted(zone_dir.rglob("*")):
                if not path.is_file() or not self._is_under_resolved(path, zone_root):
                    continue
                mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
                if mtime >= cutoff:
                    continue
                rel = self._workspace_ref(path)
                protection = protected_paths.get(rel)
                if protection is None and self._is_operator_protected(rel, path, operator_globs):
                    protection = HygieneProtectionKind.OPERATOR_PROTECTED
                candidates.append(
                    HygieneCandidate(
                        path=rel,
                        zone=zone,
                        kind=self._expired_kind(zone),
                        reason=f"older than {self._policy.ttl_for(zone)} second TTL",
                        age_seconds=int((self._clock() - mtime).total_seconds()),
                        protected=protection is not None,
                        protection_kind=protection,
                    )
                )
        return candidates

    def _protected_paths(self) -> dict[str, HygieneProtectionKind]:
        protected: dict[str, HygieneProtectionKind] = {}
        for path in self._important_paths():
            protected[path] = HygieneProtectionKind.IMPORTANT_REPORT

        # v0.1.74 (bug public-install-restores-expired-zone-agents-reblocks-preflight):
        # zone doc files (AGENTS.md scoped rules, README.md, .gitkeep) are CANONICAL —
        # the documented zone-documentation mechanism, lib-projected with historical
        # mtimes. Classifying them by TTL made every `public install` re-block preflight
        # and created an install→clean→doctor-drift loop. One insertion point: cleanup,
        # the FR3 preflight arithmetic, and the retention sweep (protected_refs) all
        # inherit this protection.
        for zone in self._policy.safe_zones:
            zone_dir = self._dadaia_root / zone.value
            if not zone_dir.is_dir():
                continue
            zone_root = zone_dir.resolve()
            for doc in sorted(zone_dir.rglob("*")):
                if (
                    doc.is_file()
                    and doc.name in _CANONICAL_ZONE_DOC_NAMES
                    and self._is_under_resolved(doc, zone_root)
                ):
                    protected[self._workspace_ref(doc)] = HygieneProtectionKind.CANONICAL_ZONE_DOC

        handoff_dir = self._dadaia_root / HygieneZone.HANDOFF.value
        if not handoff_dir.is_dir():
            return protected
        handoff_root = handoff_dir.resolve()

        for handoff in sorted(handoff_dir.rglob("*.handoff.json")):
            if not handoff.is_file() or not self._is_under_resolved(handoff, handoff_root):
                continue
            handoff_ref = self._workspace_ref(handoff)
            if self._is_review_or_audit_ref(handoff_ref):
                protected[handoff_ref] = HygieneProtectionKind.CURRENT_RELEASE_EVIDENCE
            try:
                doc = json.loads(handoff.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(doc, dict):
                continue
            artifact_ref = self._artifact_report_ref(doc)
            if artifact_ref is not None:
                protected[artifact_ref] = HygieneProtectionKind.CURRENT_RELEASE_EVIDENCE
            if self._is_current_release_or_review_evidence(doc, handoff_ref):
                protected[handoff_ref] = HygieneProtectionKind.CURRENT_RELEASE_EVIDENCE
                if artifact_ref is not None:
                    protected[artifact_ref] = HygieneProtectionKind.CURRENT_RELEASE_EVIDENCE
        return protected

    def _protected_residual_count(self, protected_paths: dict[str, HygieneProtectionKind]) -> int:
        count = 0
        for rel in protected_paths:
            path = self._workspace_root / rel
            if not path.is_file():
                continue
            zone = self._zone_for_path(path)
            if zone is None:
                continue
            cutoff = self._clock() - dt.timedelta(seconds=self._policy.ttl_for(zone))
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
            if mtime < cutoff:
                count += 1
        return count

    def _important_paths(self) -> set[str]:
        state_path = self._dadaia_root / "states" / "report_retention.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return set()
        important = state.get("important") if isinstance(state, dict) else None
        if not isinstance(important, dict):
            return set()
        return {path for path in important if isinstance(path, str)}

    def _artifact_report_ref(self, doc: dict[object, object]) -> str | None:
        artifact = doc.get("artifact")
        if not isinstance(artifact, dict):
            return None
        artifact_path = artifact.get("path")
        if not isinstance(artifact_path, str):
            return None
        report_path = self._valid_report_artifact_path(artifact_path)
        if report_path is None or not report_path.is_file():
            return None
        return self._workspace_ref(report_path)

    def _is_current_release_or_review_evidence(
        self, doc: dict[object, object], handoff_ref: str
    ) -> bool:
        release = doc.get("release_id") or doc.get("release")
        if (
            self._active_release_id is not None
            and isinstance(release, str)
            and release == self._active_release_id
        ):
            return True
        if doc.get("verdict") is not None:
            return True
        return self._is_review_or_audit_ref(handoff_ref)

    @staticmethod
    def _is_review_or_audit_ref(handoff_ref: str) -> bool:
        lower_ref = handoff_ref.lower()
        return any(token in lower_ref for token in ("review", "audit"))

    def _prune_empty_safe_dirs(self) -> list[Path]:
        pruned: list[Path] = []
        for zone in self._policy.safe_zones:
            zone_dir = self._dadaia_root / zone.value
            if not zone_dir.is_dir():
                continue
            zone_root = zone_dir.resolve()
            dirs = sorted((path for path in zone_dir.rglob("*") if path.is_dir()), reverse=True)
            for directory in dirs:
                if not self._is_under_resolved(directory, zone_root):
                    continue
                try:
                    directory.rmdir()
                except OSError:
                    continue
                pruned.append(directory)
        return pruned

    def _zone_counts(self, zone: HygieneZone) -> tuple[int, int, int]:
        """Return ``(total, expired, unreclaimable)`` for the zone.

        ``unreclaimable`` counts expired files the cleaner cannot legally delete
        (parent directory not writable by this user — e.g. root-owned container
        artifacts). The preflight hygiene gate must not demand their deletion (bug
        preflight-hygiene-gate-demands-root-owned-deletions; v0.1.72 law).
        """
        zone_dir = self._dadaia_root / zone.value
        if not zone_dir.is_dir():
            return 0, 0, 0
        zone_root = zone_dir.resolve()
        cutoff = self._clock() - dt.timedelta(seconds=self._policy.ttl_for(zone))
        total = 0
        expired = 0
        unreclaimable = 0
        for path in zone_dir.rglob("*"):
            if not path.is_file() or not self._is_under_resolved(path, zone_root):
                continue
            total += 1
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
            if mtime < cutoff:
                expired += 1
                if not os.access(path.parent, os.W_OK):
                    unreclaimable += 1
        return total, expired, unreclaimable

    def _unknown_top_level_dirs(self) -> tuple[str, ...]:
        if not self._dadaia_root.is_dir():
            return ()
        durable = set(self._policy.durable_top_level_dirs)
        return tuple(
            sorted(
                child.name
                for child in self._dadaia_root.iterdir()
                if child.is_dir() and child.name not in durable
            )
        )

    def _handoff_semantic_counts(self) -> tuple[int, int]:
        handoff_dir = self._dadaia_root / HygieneZone.HANDOFF.value
        if not handoff_dir.is_dir():
            return 0, 0
        handoff_root = handoff_dir.resolve()
        orphan = 0
        malformed = 0
        for path in handoff_dir.rglob("*.handoff.json"):
            if not path.is_file() or not self._is_under_resolved(path, handoff_root):
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                malformed += 1
                continue
            if not isinstance(doc, dict):
                malformed += 1
                continue
            artifact = doc.get("artifact", {})
            if not isinstance(artifact, dict):
                malformed += 1
                continue
            artifact_path = artifact.get("path")
            if artifact_path is None:
                continue
            if not isinstance(artifact_path, str):
                malformed += 1
                continue
            # Bug malformed-handoff-classifier-rejects-non-report-artifacts: a
            # handoff-v1.2 artifact.path may name the REAL artifact (a SPEC.md, a
            # backlog item, an audit) anywhere workspace-relative — that is the
            # handoff-first contract, not malformation. Malformed = structurally
            # broken paths only (empty, absolute, traversal). The reports-zone
            # orphan check applies only to paths that claim the reports zone.
            stripped = artifact_path.strip()
            raw = Path(stripped) if stripped else None
            if (
                raw is None
                or PurePosixPath(stripped).is_absolute()
                or PureWindowsPath(stripped).is_absolute()
                or ".." in raw.parts
            ):
                malformed += 1
                continue
            if raw.parts[:2] != (".dadaia", "reports"):
                continue
            report_path = self._valid_report_artifact_path(stripped)
            if report_path is None:
                malformed += 1
                continue
            if not report_path.is_file():
                orphan += 1
        return orphan, malformed

    def _valid_report_artifact_path(self, artifact_path: str) -> Path | None:
        if (
            PurePosixPath(artifact_path).is_absolute()
            or PureWindowsPath(artifact_path).is_absolute()
        ):
            return None
        raw = Path(artifact_path)
        if ".." in raw.parts or raw.parts[:2] != (".dadaia", "reports"):
            return None
        resolved = (self._workspace_root / raw).resolve()
        reports_root = (self._dadaia_root / "reports").resolve()
        try:
            resolved.relative_to(reports_root)
        except ValueError:
            return None
        return resolved

    def _is_mutable_safe_zone_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        return any(
            self._is_under(path, self._dadaia_root / zone.value) for zone in self._policy.safe_zones
        )

    def _zone_for_path(self, path: Path) -> HygieneZone | None:
        for zone in self._policy.safe_zones:
            if self._is_under(path, self._dadaia_root / zone.value):
                return zone
        return None

    def _operator_exception_globs(self) -> list[str]:
        exc_file = self._dadaia_root / "states" / "root_exceptions.txt"
        try:
            lines = exc_file.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        globs: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                globs.append(stripped)
        return globs

    def _is_operator_protected(self, rel: str, path: Path, globs: list[str]) -> bool:
        return any(fnmatch.fnmatch(path.name, glob) or fnmatch.fnmatch(rel, glob) for glob in globs)

    def _workspace_ref(self, path: Path) -> str:
        return path.resolve().relative_to(self._workspace_root).as_posix()

    @staticmethod
    def _expired_kind(zone: HygieneZone) -> HygieneCandidateKind:
        if zone is HygieneZone.REPORTS:
            return HygieneCandidateKind.EXPIRED_REPORT
        if zone is HygieneZone.HANDOFF:
            return HygieneCandidateKind.EXPIRED_HANDOFF
        if zone is HygieneZone.TMP:
            return HygieneCandidateKind.EXPIRED_TMP
        raise ValueError(f"unsupported hygiene zone: {zone}")

    @staticmethod
    def _is_under(path: Path, root: Path) -> bool:
        return LifecycleHygieneService._is_under_resolved(path, root.resolve())

    @staticmethod
    def _is_under_resolved(path: Path, root_resolved: Path) -> bool:
        try:
            path.resolve().relative_to(root_resolved)
        except ValueError:
            return False
        return True

    def _clock(self) -> dt.datetime:
        return (self._now or dt.datetime.now(tz=dt.UTC)).astimezone(dt.UTC)
