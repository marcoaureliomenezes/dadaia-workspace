"""The one handoff reader: schema validation (``jsonschema``), the ``self_pull`` rule and
artifact resolution for ``*.handoff.json`` files.

Placement: ``core``, beside ``specs_resolver``/``workspace_resolver`` — filesystem
resolvers several layers need (P-11 authorized file I/O). No ``features/handoff.py``
facade exists; every consumer imports this module directly.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from dadaia_workspace.core.exceptions import HandoffSchemaError, HandoffValidationError
from dadaia_workspace.core.invocation import repo_slug_for_context

__all__ = ["Handoff", "HandoffIndex", "ValidationResult"]


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a single handoff file."""

    path: Path
    valid: bool
    errors: tuple[HandoffValidationError, ...] = field(default_factory=tuple)
    hash_status: str | None = None


@dataclass(frozen=True)
class Handoff:
    """One ``*.handoff.json`` file; unparseable JSON is recorded in ``malformed_error``."""

    path: Path
    raw: dict[str, Any] = field(default_factory=dict)
    malformed_error: str | None = None

    @classmethod
    def load(cls, path: Path) -> Handoff:
        """Read + parse ``path``. Never raises — malformed JSON is recorded, not thrown."""
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return cls(path=path, malformed_error=f"malformed JSON: {exc}")
        if not isinstance(doc, dict):
            return cls(path=path, malformed_error="handoff document is not a JSON object")
        return cls(path=path, raw=doc)

    def _artifact(self, key: str) -> str | None:
        artifact = self.raw.get("artifact")
        value = artifact.get(key) if isinstance(artifact, dict) else None
        return value if isinstance(value, str) and value else None

    def artifact_path(self, workspace_root: Path) -> Path | None:
        """Resolve ``artifact.path`` to an in-workspace file, or ``None``.

        An absolute path resolves as-is; a relative one resolves workspace-rooted when
        that file exists, else handoff-dir-relative. Every branch is guarded against
        ``..``/symlink escape (CWE-22).
        """
        ref = self._artifact("path")
        if not ref:
            return None
        candidate = Path(ref)
        if candidate.is_absolute():
            return _within_root(candidate, workspace_root)
        workspace_rooted = _within_root(workspace_root / candidate, workspace_root)
        if workspace_rooted is not None and workspace_rooted.exists():
            return workspace_rooted
        return _within_root(self.path.parent / candidate, workspace_root)

    def artifact_hash_status(self, workspace_root: Path) -> str:
        """``"match"``/``"mismatch"``/``"missing_artifact"`` for the declared ``content_hash``."""
        resolved = self.artifact_path(workspace_root)
        if resolved is None or not resolved.is_file():
            return "missing_artifact"
        actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return "match" if actual == (self._artifact("content_hash") or "") else "mismatch"

    def validate(
        self,
        *,
        workspace_root: Path,
        schema: dict[str, Any],
        reviewed_root: Path | None = None,
    ) -> ValidationResult:
        """Schema shape (version routing is the schema's ``schema_version`` enum), then
        every ``self_pull`` ref's existence, then the artifact hash.

        ``reviewed_root`` (the CLI's ``--reviewed-root``) is tried first for each ref —
        the tree the handoff was reviewed against — before ``repos/<context>/<ref>`` and
        ``<workspace>/<ref>``.
        """
        if self.malformed_error is not None:
            error = HandoffValidationError("$root", self.malformed_error)
            return ValidationResult(path=self.path, valid=False, errors=(error,))
        errors = [
            HandoffValidationError(e.json_path, e.message)
            for e in sorted(Draft202012Validator(schema).iter_errors(self.raw), key=str)
        ]
        if not errors:
            refs = self.raw["self_pull"]["refs"]
            errors = [
                HandoffValidationError(
                    f"self_pull.refs[{idx}]",
                    f"ref does not exist: {ref!r} (checked reviewed_root, "
                    "repos/<context>/<ref> and <workspace>/<ref>)",
                )
                for idx, ref in enumerate(refs)
                if not self._ref_exists(ref, workspace_root, reviewed_root)
            ]
        hash_status: str | None = None
        if not errors and self._artifact("path"):
            hash_status = self.artifact_hash_status(workspace_root)
            if hash_status != "match":
                errors.append(
                    HandoffValidationError(
                        "artifact.content_hash", f"artifact hash check failed: {hash_status}"
                    )
                )
        return ValidationResult(
            path=self.path, valid=not errors, errors=tuple(errors), hash_status=hash_status
        )

    def _ref_exists(self, ref: str, workspace_root: Path, reviewed_root: Path | None) -> bool:
        candidates: list[tuple[Path, Path]] = []  # (candidate, boundary root)
        if reviewed_root is not None:
            candidates.append((reviewed_root / ref, reviewed_root))
        slug = repo_slug_for_context(workspace_root, self.raw["context"])
        if slug:  # refs are relative to the context's main repo, found via the registry
            candidates.append((workspace_root / "repos" / slug / ref, workspace_root))
        candidates.append((workspace_root / ref, workspace_root))
        return any(
            (resolved := _within_root(candidate, boundary)) is not None and resolved.is_file()
            for candidate, boundary in candidates
        )


def _within_root(path: Path, root: Path) -> Path | None:
    """Resolve ``path``, rejecting anything outside ``root`` (CWE-22 guard)."""
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return resolved


class HandoffIndex:
    """Validates handoffs against the workspace's projected schema, loaded once, lazily."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._schema: dict[str, Any] | None = None

    def _schema_dict(self) -> dict[str, Any]:
        if self._schema is None:
            path = self._workspace_root / ".dadaia/agentic/schemas/handoff-v1.schema.json"
            try:
                self._schema = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise HandoffSchemaError(f"Schema unreadable: {path}: {exc}") from exc
        return self._schema

    def validate_file(self, path: Path, *, reviewed_root: Path | None = None) -> ValidationResult:
        """Validate a single handoff JSON file (loads it fresh)."""
        return Handoff.load(path).validate(
            workspace_root=self._workspace_root,
            schema=self._schema_dict(),
            reviewed_root=reviewed_root,
        )
