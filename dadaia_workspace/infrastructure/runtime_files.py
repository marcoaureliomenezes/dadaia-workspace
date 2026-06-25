"""Filesystem adapter for canonical lifecycle runtime files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneSnapshot
from dadaia_workspace.core.protocols.runtime_files import RuntimeFileKind, RuntimeFileRef
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
        if payload["schema_version"] not in {"handoff-v1", "handoff-v1.1"}:
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
