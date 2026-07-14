"""Filesystem adapter for canonical lifecycle runtime files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneSnapshot
from dadaia_workspace.core.protocols.runtime_files import (
    RuntimeFileKind,
    RuntimeFileRef,
    StepPayloadRef,
)
from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text


class RuntimeFilePathError(ValueError):
    """Raised when a runtime artifact name would leave its canonical zone."""


class FilesystemRuntimeFileAdapter:
    """Write reports, handoffs, tmp files, and run artifacts under `.dadaia/`."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        if self._is_repo_tree_root(self._workspace_root):
            raise RuntimeFilePathError("runtime files require a workspace root, not a repo root")
        self._dadaia_root = self._workspace_root / ".dadaia"

    def write_report(
        self,
        *,
        context: str,
        agent: str,
        filename: str,
        html: str,
    ) -> RuntimeFileRef:
        self._require_suffix(filename, ".html")
        self._validate_html_report(html)
        path = self._canonical_path("reports", context, agent, filename)
        return self._write_text(RuntimeFileKind.REPORT, path, html)

    def write_handoff(
        self,
        *,
        context: str,
        filename: str,
        payload: dict[str, object],
    ) -> RuntimeFileRef:
        self._require_suffix(filename, ".handoff.json")
        self._validate_handoff_payload(context, payload)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        path = self._canonical_path("handoff", context, filename)
        return self._write_text(RuntimeFileKind.HANDOFF, path, text)

    def write_tmp(
        self,
        *,
        workflow: str,
        date_slug: str,
        filename: str,
        content: str,
        ttl_seconds: int,
    ) -> RuntimeFileRef:
        if ttl_seconds <= 0:
            raise RuntimeFilePathError("tmp ttl_seconds must be positive")
        path = self._canonical_path("tmp", workflow, date_slug, filename)
        return self._write_text(RuntimeFileKind.TMP, path, content, ttl_seconds=ttl_seconds)

    def write_run_artifact(
        self,
        *,
        run_id: str,
        filename: str,
        content: str,
    ) -> RuntimeFileRef:
        path = self._canonical_path("runs", "lifecycle", run_id, filename)
        return self._write_text(RuntimeFileKind.RUN_ARTIFACT, path, content)

    def write_step_payload(
        self,
        *,
        run_id: str,
        producer_step: str,
        attempt: int,
        content: str,
    ) -> StepPayloadRef:
        """Write an IMMUTABLE workflow-step payload envelope under the run-scoped steps zone.

        Path: WORKSPACE-ROOT
        ``.dadaia/runs/lifecycle/<run_id>/steps/<step>-attempt-<n>.step-payload.json``
        (v0.1.30 Item 5 — the workflow-step handoff data plane). The write is atomic
        (temp+rename via :func:`_atomic_write_text`) and **immutable**: a payload for an
        existing ``(run_id, producer_step, attempt)`` is never overwritten — re-producing
        the same key raises, preserving the addressable-key immutability the resolver's
        content-hash check depends on.

        ``run_id`` / ``producer_step`` are confined as single path segments (no traversal);
        ``attempt`` is rendered numerically — a run-id-derived path can never escape the
        ``.dadaia/runs/lifecycle`` canonical zone (``_canonical_path`` raises on escape).
        """
        if attempt < 0:
            raise RuntimeFilePathError("step payload attempt must be non-negative")
        filename = f"{producer_step}-attempt-{attempt}.step-payload.json"
        path = self._canonical_path("runs", "lifecycle", run_id, "steps", filename)
        if path.exists():
            raise RuntimeFilePathError(
                f"step payload already exists (immutable): {self._workspace_ref(path)}"
            )
        ref = self._write_text(RuntimeFileKind.RUN_ARTIFACT, path, content)
        assert ref.content_hash is not None
        return StepPayloadRef(payload_ref=ref.path, content_hash=ref.content_hash)

    def purge_step_payloads(
        self, run_id: str, producer_steps: frozenset[str] | set[str] | None = None
    ) -> int:
        """Reclaim the run's step-payload zone for a RESTART; return files removed.

        Restarting a run_id replaces the run record — and with it the ledger that
        addressed these payloads — so the zone's files are orphans that would otherwise
        block the new generation's ``attempt-0`` writes (bug
        rerun-of-run-id-collides-with-immutable-payload-zone). Confined to
        ``.dadaia/runs/lifecycle/<run_id>/steps`` via ``_canonical_path``; only
        ``*.step-payload.json`` files are removed. In-run immutability is untouched —
        ``write_step_payload`` still never overwrites a live key.

        *producer_steps* narrows the reclaim to the named steps' payloads (the
        resume-from-step case, bug blocked-definition-run-cannot-resume-from-step):
        upstream steps' payloads stay addressable for ``consumes`` resolution.
        """
        steps_dir = self._canonical_path("runs", "lifecycle", run_id, "steps")
        if not steps_dir.is_dir():
            return 0
        removed = 0
        for entry in steps_dir.glob("*.step-payload.json"):
            if producer_steps is not None:
                producer = entry.name.rsplit("-attempt-", 1)[0]
                if producer not in producer_steps:
                    continue
            entry.unlink()
            removed += 1
        return removed

    def read_step_payload(self, payload_ref: str) -> str | None:
        """Return the raw step payload envelope JSON at *payload_ref*, or ``None`` if absent.

        ``payload_ref`` is a workspace-relative path. It is resolved and confined to a
        canonical step-payload zone before any read — the legacy
        ``.dadaia/runs/lifecycle`` zone or a release-aware
        ``…/specs/releases/<id>/handoffs/…`` / ``…/specs/backlog/handoffs/…`` zone. A ref
        pointing outside every zone (traversal / absolute) returns ``None`` rather than
        reading an arbitrary file.
        """
        ref_path = Path(payload_ref)
        if ref_path.is_absolute() or ".." in ref_path.parts:
            return None
        resolved = (self._workspace_root / ref_path).resolve()
        try:
            resolved.relative_to(self._workspace_root)
        except ValueError:
            return None
        runs_root = (self._dadaia_root / "runs" / "lifecycle").resolve()
        in_legacy_zone = runs_root in resolved.parents
        if not in_legacy_zone and not self._in_release_zone(resolved):
            return None
        if not resolved.is_file():
            return None
        return resolved.read_text(encoding="utf-8")

    @staticmethod
    def _in_release_zone(resolved: Path) -> bool:
        """True when *resolved* sits in a release-aware step-payload zone.

        Zones (operator mandate — durable workflow handoffs live in the release folder):
        ``…/specs/releases/<release_id>/handoffs/<run_id>/steps/*.step-payload.json`` and
        ``…/specs/backlog/handoffs/<run_id>/steps/*.step-payload.json``.
        """
        if not resolved.name.endswith(".step-payload.json"):
            return False
        parts = resolved.parts
        for index, part in enumerate(parts):
            if part != "specs":
                continue
            tail = parts[index + 1 :]
            if len(tail) >= 5 and tail[0] == "releases" and tail[2] == "handoffs":
                return True
            if len(tail) >= 4 and tail[0] == "backlog" and tail[1] == "handoffs":
                return True
        return False

    def _specs_dir_for_context(self, context: str) -> Path:
        """Resolve *context*'s ``specs/`` tree (mirrors ``container._context_specs_dir``)."""
        specs_dir = self._workspace_root / "repos" / self._safe_segment(context) / "specs"
        if not specs_dir.is_dir():
            specs_dir = self._workspace_root / "specs"
        return specs_dir

    def _release_zone_dir(self, run_id: str, *, context: str, release_id: str | None) -> Path:
        """The release-aware steps zone for one run, confined under the context specs dir."""
        specs_dir = self._specs_dir_for_context(context)
        if release_id is None:
            zone = specs_dir / "backlog" / "handoffs" / self._safe_segment(run_id) / "steps"
        else:
            zone = (
                specs_dir
                / "releases"
                / self._safe_segment(release_id)
                / "handoffs"
                / self._safe_segment(run_id)
                / "steps"
            )
        resolved = zone.resolve()
        try:
            resolved.relative_to(self._workspace_root)
        except ValueError as exc:
            raise RuntimeFilePathError(f"release handoff zone escapes workspace: {zone}") from exc
        return resolved

    def write_release_scoped_step_payload(
        self,
        *,
        run_id: str,
        producer_step: str,
        attempt: int,
        content: str,
        context: str,
        release_id: str | None,
    ) -> StepPayloadRef:
        """Write the immutable envelope under the release-aware zone; return its ref.

        Same immutability contract as :meth:`write_step_payload` — a payload for an
        existing ``(run_id, producer_step, attempt)`` is never overwritten.
        """
        if attempt < 0:
            raise RuntimeFilePathError("step payload attempt must be non-negative")
        zone = self._release_zone_dir(run_id, context=context, release_id=release_id)
        filename = f"{self._safe_segment(producer_step)}-attempt-{attempt}.step-payload.json"
        path = zone / filename
        if path.exists():
            raise RuntimeFilePathError(
                f"step payload already exists (immutable): {self._workspace_ref(path)}"
            )
        ref = self._write_text(RuntimeFileKind.RUN_ARTIFACT, path, content)
        assert ref.content_hash is not None
        return StepPayloadRef(payload_ref=ref.path, content_hash=ref.content_hash)

    def purge_release_scoped_step_payloads(
        self,
        run_id: str,
        producer_steps: frozenset[str] | set[str] | None,
        *,
        context: str,
        release_id: str | None,
    ) -> int:
        """Reclaim the run's release-aware step-payload zone for a RESTART."""
        zone = self._release_zone_dir(run_id, context=context, release_id=release_id)
        if not zone.is_dir():
            return 0
        removed = 0
        for entry in zone.glob("*.step-payload.json"):
            if producer_steps is not None:
                producer = entry.name.rsplit("-attempt-", 1)[0]
                if producer not in producer_steps:
                    continue
            entry.unlink()
            removed += 1
        return removed

    def purge_worker_outputs(self, refs: tuple[str, ...]) -> int:
        """Remove only exact canonical ``.step-output.json`` refs for a restart.

        Callers derive each ref from workflow identity. This adapter performs no glob or
        prefix deletion: every ref is confined beneath
        ``.dadaia/tmp/lifecycle-worker`` and must name the canonical suffix.
        """
        worker_root = (self._dadaia_root / "tmp" / "lifecycle-worker").resolve()
        removed = 0
        for ref in dict.fromkeys(refs):
            ref_path = Path(ref)
            if ref_path.is_absolute() or ".." in ref_path.parts:
                raise RuntimeFilePathError(f"unsafe worker output ref: {ref}")
            target = (self._workspace_root / ref_path).resolve()
            try:
                target.relative_to(worker_root)
            except ValueError as exc:
                raise RuntimeFilePathError(
                    f"worker output ref leaves canonical zone: {ref}"
                ) from exc
            if not target.name.endswith(".step-output.json"):
                raise RuntimeFilePathError(f"worker output ref has invalid suffix: {ref}")
            if target.is_file():
                target.unlink()
                removed += 1
        return removed

    def write_hygiene_snapshot(self, snapshot: HygieneSnapshot) -> RuntimeFileRef:
        text = json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n"
        path = self._canonical_path("runs", "lifecycle", snapshot.run_id, "hygiene-snapshot.json")
        return self._write_text(RuntimeFileKind.HYGIENE_SNAPSHOT, path, text)

    def _canonical_path(self, top_level: str, *parts: str) -> Path:
        safe_parts = [self._safe_segment(part) for part in parts]
        path = (self._dadaia_root / top_level / Path(*safe_parts)).resolve()
        allowed_root = (self._dadaia_root / top_level).resolve()
        try:
            path.relative_to(allowed_root)
        except ValueError as exc:
            raise RuntimeFilePathError(f"path escapes .dadaia/{top_level}") from exc
        return path

    def _write_text(
        self,
        kind: RuntimeFileKind,
        path: Path,
        text: str,
        *,
        ttl_seconds: int | None = None,
    ) -> RuntimeFileRef:
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, text)
        return RuntimeFileRef(
            kind=kind,
            path=self._workspace_ref(path),
            content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            ttl_seconds=ttl_seconds,
        )

    def _workspace_ref(self, path: Path) -> str:
        return path.resolve().relative_to(self._workspace_root).as_posix()

    @staticmethod
    def _safe_segment(value: str) -> str:
        if not value or value in {".", ".."}:
            raise RuntimeFilePathError("runtime file path segment is empty or unsafe")
        path = Path(value)
        if path.is_absolute() or len(path.parts) != 1 or ".." in path.parts:
            raise RuntimeFilePathError(f"unsafe runtime file path segment: {value}")
        return value

    @staticmethod
    def _require_suffix(filename: str, suffix: str) -> None:
        if not filename.endswith(suffix):
            raise RuntimeFilePathError(f"filename must end with {suffix}")

    @staticmethod
    def _is_repo_tree_root(root: Path) -> bool:
        if root.parent.name == "repos":
            return True
        return (root / ".git").exists() and not (root / ".dadaia").exists()

    @staticmethod
    def _validate_html_report(html: str) -> None:
        lowered = html.lower()
        if "<html" not in lowered or "</html>" not in lowered:
            raise RuntimeFilePathError("report content must be an HTML document")

    def _validate_handoff_payload(self, context: str, payload: dict[str, object]) -> None:
        required = {
            "schema_version",
            "agent",
            "context",
            "produced_at",
            "artifact",
            "scope",
            "metrics",
        }
        missing = sorted(key for key in required if key not in payload)
        if missing:
            raise RuntimeFilePathError(f"handoff payload missing required fields: {missing}")
        # FR3 (v0.1.62): accept-set widened to include handoff-v1.2 (self_pull line).
        if payload["schema_version"] not in {"handoff-v1", "handoff-v1.1", "handoff-v1.2"}:
            raise RuntimeFilePathError("handoff payload has unsupported schema_version")
        if payload["context"] != context:
            raise RuntimeFilePathError("handoff payload context must match target context")
        if not isinstance(payload["agent"], str) or not payload["agent"]:
            raise RuntimeFilePathError("handoff payload agent must be a non-empty string")
        if not isinstance(payload["produced_at"], str) or "T" not in payload["produced_at"]:
            raise RuntimeFilePathError("handoff payload produced_at must be ISO-like text")
        if not isinstance(payload["scope"], str) or not payload["scope"]:
            raise RuntimeFilePathError("handoff payload scope must be a non-empty string")
        if not isinstance(payload["metrics"], dict):
            raise RuntimeFilePathError("handoff payload metrics must be an object")
        verdict = payload.get("verdict")
        if verdict is not None and verdict not in {"APPROVED", "REJECTED"}:
            raise RuntimeFilePathError("handoff payload verdict must be APPROVED or REJECTED")

        artifact = payload["artifact"]
        if not isinstance(artifact, dict):
            raise RuntimeFilePathError("handoff payload artifact must be an object")
        artifact_type = artifact.get("type")
        if artifact_type not in {"report", "spec", "plan", "tasks", "closure", "memory", "other"}:
            raise RuntimeFilePathError("handoff payload artifact.type is invalid")
        artifact_path = artifact.get("path")
        artifact_hash = artifact.get("content_hash")
        if artifact_path is not None and not isinstance(artifact_path, str):
            raise RuntimeFilePathError("handoff payload artifact.path must be a string")
        if artifact_path is not None and not artifact_hash:
            raise RuntimeFilePathError("handoff payload artifact.content_hash required with path")
        if artifact_hash is not None and (
            not isinstance(artifact_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", artifact_hash)
        ):
            raise RuntimeFilePathError("handoff payload artifact.content_hash must be sha256 hex")
        if artifact_path is not None:
            self._validate_artifact_ref_path(artifact_path, str(artifact_hash))

    def _validate_artifact_ref_path(self, artifact_path: str, expected_hash: str) -> None:
        path = Path(artifact_path)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeFilePathError("handoff payload artifact.path must be workspace-relative")
        parts = path.parts
        if len(parts) < 3 or parts[0] != ".dadaia":
            raise RuntimeFilePathError("handoff payload artifact.path must stay under .dadaia")
        is_report_artifact = parts[1] == "reports"
        is_run_artifact = parts[1] == "runs" and len(parts) >= 4 and parts[2] == "lifecycle"
        if not (is_report_artifact or is_run_artifact):
            raise RuntimeFilePathError(
                "handoff payload artifact.path must reference reports or lifecycle run artifacts"
            )
        resolved = (self._workspace_root / path).resolve()
        try:
            resolved.relative_to(self._dadaia_root.resolve())
        except ValueError as exc:
            raise RuntimeFilePathError("handoff payload artifact.path escapes .dadaia") from exc
        if not resolved.is_file():
            raise RuntimeFilePathError(
                "handoff payload artifact.path must reference an existing file"
            )
        actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeFilePathError("handoff payload artifact.content_hash does not match file")
