"""Reports validation feature service.

This module is intentionally free of any infrastructure imports (constitution
L67).  It only knows about ``core/`` protocols, models, and exceptions, plus
the Python standard library.

The concrete ``StdlibHandoffValidator`` adapter is wired in by
``dadaia_workspace.container.build_reports_validation_service`` — never here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dadaia_workspace.core.exceptions import HandoffValidationError
from dadaia_workspace.core.protocols.handoff_validator import ValidatorPort

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Outcome of validating a single handoff file.

    Attributes:
        path: Absolute path to the ``.handoff.json`` file.
        valid: ``True`` if the document passed all checks.
        errors: Tuple of ``HandoffValidationError`` instances (empty when valid).
        hash_status: One of ``"match"``, ``"mismatch"``, ``"missing_artifact"``,
            or ``None`` when hash was not checked.
    """

    path: Path
    valid: bool
    errors: tuple[HandoffValidationError, ...] = field(default_factory=tuple)
    hash_status: str | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ReportsValidationService:
    """Validates agent handoff documents using a pluggable ``ValidatorPort``.

    This service discovers, reads, and validates ``.handoff.json`` files under
    ``handoff_root``.  It does **not** couple itself to any concrete validator
    implementation — callers inject the adapter via ``validator``.

    Args:
        validator: Any object implementing ``ValidatorPort``.
        reports_root: Root directory where agent handoff files are stored
            (typically ``<workspace>/.dadaia/handoff``). The argument name is
            kept for API compatibility.
    """

    def __init__(self, validator: ValidatorPort, reports_root: Path) -> None:
        self._validator = validator
        self._reports_root = reports_root
        self._workspace_root = self._infer_workspace_root(reports_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_file(self, path: Path) -> ValidationResult:
        """Validate a single handoff JSON file.

        Reads the JSON, calls the validator, and returns a ``ValidationResult``.
        Malformed JSON is treated as a structural violation — the validator is
        NOT called for such documents.

        Args:
            path: Absolute (or relative) path to the ``.handoff.json`` file.

        Returns:
            A ``ValidationResult`` capturing validity and any errors.
        """
        try:
            raw = path.read_text(encoding="utf-8")
            doc: dict[str, object] = json.loads(raw)
        except json.JSONDecodeError as exc:
            malformed_error = HandoffValidationError("$root", f"malformed JSON: {exc}")
            return ValidationResult(path=path, valid=False, errors=(malformed_error,))

        errors = list(self._validator.validate(doc))
        hash_status = None
        if not errors and self._artifact_path(doc):
            hash_status = self.check_hash(path)
            if hash_status != "match":
                errors.append(
                    HandoffValidationError(
                        "artifact.content_hash",
                        f"artifact hash check failed: {hash_status}",
                    )
                )
        return ValidationResult(
            path=path,
            valid=len(errors) == 0,
            errors=tuple(errors),
            hash_status=hash_status,
        )

    def validate_all(self, context: str | None = None) -> list[ValidationResult]:
        """Discover and validate all ``*.handoff.json`` files under ``handoff_root``.

        Args:
            context: If provided, only files under ``handoff_root/<context>/``
                are included.

        Returns:
            A list of ``ValidationResult`` — one per discovered file.
        """
        search_root = self._reports_root / context if context else self._reports_root
        results: list[ValidationResult] = []
        for handoff_path in sorted(search_root.rglob("*.handoff.json")):
            results.append(self.validate_file(handoff_path))
        return results

    def check_hash(self, handoff_path: Path) -> str:
        """Compare the artifact's actual sha256 against the handoff's ``content_hash``.

        Workspace-relative artifact paths such as ``.dadaia/reports/...`` are
        resolved from the workspace root. Other relative paths keep the legacy
        behavior and resolve from the handoff file directory.

        Args:
            handoff_path: Path to the ``.handoff.json`` file.

        Returns:
            - ``"match"`` — hashes are identical.
            - ``"mismatch"`` — hashes differ.
            - ``"missing_artifact"`` — the artifact file referenced in the handoff
              does not exist on disk or is outside the workspace boundary.
        """
        raw = handoff_path.read_text(encoding="utf-8")
        doc: dict[str, object] = json.loads(raw)
        artifact_info = doc.get("artifact", {})
        assert isinstance(artifact_info, dict)
        artifact_rel = str(artifact_info.get("path", ""))
        if not artifact_rel:
            return "missing_artifact"
        expected_hash = str(artifact_info.get("content_hash", ""))

        artifact_path = self._resolve_artifact_path(handoff_path, artifact_rel)
        if artifact_path is None:
            return "missing_artifact"

        if not artifact_path.exists():
            return "missing_artifact"

        actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        return "match" if actual_hash == expected_hash else "mismatch"

    def _resolve_artifact_path(self, handoff_path: Path, artifact_ref: str) -> Path | None:
        artifact_path = Path(artifact_ref)
        if artifact_path.is_absolute():
            return self._within_workspace(artifact_path)
        if artifact_ref.startswith(".dadaia/") and self._workspace_root is not None:
            return self._within_workspace(self._workspace_root / artifact_path)
        candidate = handoff_path.parent / artifact_path
        return self._within_workspace(candidate) if self._workspace_root is not None else candidate

    def _within_workspace(self, path: Path) -> Path | None:
        if self._workspace_root is None:
            return path
        try:
            resolved = path.resolve()
            resolved.relative_to(self._workspace_root.resolve())
        except (OSError, ValueError):
            return None
        return resolved

    @staticmethod
    def _infer_workspace_root(handoff_root: Path) -> Path | None:
        parts = handoff_root.parts
        if len(parts) >= 2 and parts[-2:] == (".dadaia", "handoff"):
            return handoff_root.parent.parent
        return None

    @staticmethod
    def _artifact_path(doc: dict[str, object]) -> str | None:
        artifact = doc.get("artifact", {})
        if not isinstance(artifact, dict):
            return None
        path = artifact.get("path")
        return path if isinstance(path, str) and path else None
