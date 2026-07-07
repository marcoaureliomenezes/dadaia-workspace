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
from dadaia_workspace.core.role_atom_map import ROLE_ATOM_MAP

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
        if not errors:
            errors.extend(self._check_self_pull(doc))
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

        Any relative artifact path that exists under the workspace root (e.g.
        ``.dadaia/reports/...`` or ``repos/<slug>/specs/audits/...``) is resolved
        workspace-rooted; workspace-root wins when a path is resolvable both ways.
        Paths that exist only beside the handoff file keep the legacy
        handoff-dir-relative behavior.

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

    def _check_self_pull(self, doc: dict[str, object]) -> list[HandoffValidationError]:
        """Version-conditional ``self_pull`` checks for ``handoff-v1.2`` documents (FR2).

        The stdlib validator cannot express "required only when schema_version ==
        handoff-v1.2" (no ``if``/``then`` — ADR-2), so the conditional lives here,
        evaluated only after a clean schema pass. ``handoff-v1``/``handoff-v1.1``
        documents are exempt (transition posture — the on-disk corpus keeps validating).

        Checks, in order:

        1. **Presence** — a v1.2 doc without a ``self_pull.refs`` non-empty array fails
           with a ``self_pull``-pathed error (shape errors are already the schema's job).
        2. **Existence** — each ref must resolve to an existing file, trying
           ``<workspace>/repos/<context>/<ref>`` then ``<workspace>/<ref>`` (self-hosting
           root), both guarded by ``_within_workspace``. Fail-soft: when
           ``_workspace_root`` is ``None`` (non-canonical handoff root) the existence
           check degrades to shape-only, mirroring the artifact-path posture.
        3. **Role-map coverage** — when the emitting ``agent`` has a role→atom mapping
           (``core.role_atom_map.ROLE_ATOM_MAP``), the mapped atom's ``specs/``-prefixed
           ref must appear in ``refs``. Unmapped agents carry no coverage requirement.
        """
        if doc.get("schema_version") != "handoff-v1.2":
            return []
        errors: list[HandoffValidationError] = []
        self_pull = doc.get("self_pull")
        refs: list[str] = []
        if isinstance(self_pull, dict):
            refs_obj = self_pull.get("refs")
            if isinstance(refs_obj, list):
                refs = [ref for ref in refs_obj if isinstance(ref, str)]
        if not refs:
            errors.append(
                HandoffValidationError(
                    "self_pull",
                    "handoff-v1.2 requires self_pull with a non-empty refs array "
                    "(the Layer-1 self-pull audit line)",
                )
            )
            return errors

        # Existence (fail-soft when the workspace root cannot be inferred).
        if self._workspace_root is not None:
            context = doc.get("context")
            for idx, ref in enumerate(refs):
                if not self._self_pull_ref_exists(ref, context):
                    errors.append(
                        HandoffValidationError(
                            f"self_pull.refs[{idx}]",
                            f"ref does not exist: {ref!r} (checked repos/<context>/<ref> "
                            "and <workspace>/<ref>)",
                        )
                    )

        # Role-map coverage (pure data — applies regardless of workspace root).
        agent = doc.get("agent")
        if isinstance(agent, str):
            mapped = ROLE_ATOM_MAP.get(agent)
            if mapped is not None:
                expected_ref = f"specs/{mapped}"
                if expected_ref not in refs:
                    errors.append(
                        HandoffValidationError(
                            "self_pull.refs",
                            f"agent {agent!r} is role-mapped to {expected_ref!r} "
                            "but self_pull.refs does not list it",
                        )
                    )
        return errors

    def _self_pull_ref_exists(self, ref: str, context: object) -> bool:
        """Resolve a ``self_pull`` ref inside the workspace boundary — existing file or not."""
        assert self._workspace_root is not None
        candidates: list[Path] = []
        if isinstance(context, str) and context:
            candidates.append(self._workspace_root / "repos" / context / ref)
        candidates.append(self._workspace_root / ref)
        for candidate in candidates:
            resolved = self._within_workspace(candidate)
            if resolved is not None and resolved.is_file():
                return True
        return False

    def _resolve_artifact_path(self, handoff_path: Path, artifact_ref: str) -> Path | None:
        """Resolve ``artifact_ref`` to an in-workspace path, or ``None`` if it escapes.

        Resolution order:
        1. Absolute paths resolve as-is (guarded against escaping the workspace).
        2. ANY relative path that exists workspace-rooted resolves workspace-rooted —
           workspace-root wins over the handoff-dir fallback when both exist (covers
           ``repos/<slug>/specs/audits/<UTC>/audit.md``).
        3. Otherwise fall back to the legacy handoff-dir-relative location.

        The ``_within_workspace`` guard (``resolve()`` + ``relative_to``, symlink-safe)
        is applied to every branch so ``..`` traversal and out-of-tree paths are
        rejected without a schema change.
        """
        artifact_path = Path(artifact_ref)
        if artifact_path.is_absolute():
            return self._within_workspace(artifact_path)
        if self._workspace_root is not None:
            workspace_rooted = self._within_workspace(self._workspace_root / artifact_path)
            if workspace_rooted is not None and workspace_rooted.exists():
                return workspace_rooted
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
