"""The one module that owns handoff discovery, version routing and artifact resolution.

release 0.5.1 candidate K6. Before this module, ten independent readers each re-decided
how to find a ``*.handoff.json`` file, which schema version it carried, and where its
``artifact.path`` pointed on disk — ``cli/commands/reports.py``, the three services of the
since-deleted ``features/reports/`` package, ``features/panel/{reports_doctor.py,views/api_reports.py}``,
``features/chokepoints/service.py``, ``features/specs/doctor_release.py``, plus the stdlib
schema validator itself. A fix landing in one reader did not reach the next (7 bug-ledger
records, one open — see the module-level docstring on :meth:`Handoff.validate` for the fix
this module carries).

Placement (core, not a features/* package): resolving "which handoff, what version, which
artifact" needs the SAME answer in ``features.chokepoints``, ``features.specs``,
``features.panel`` — three *different* feature packages under the
P-07 mutual-independence contract. A features/* home would need a new suppressed
``features-no-cross-feature`` ignore edge per consumer (the cap must never rise). ``core`` is
outside that contract and already hosts the same shape of cross-cutting filesystem resolver
(``core/specs_resolver.py``, ``core/workspace_resolver.py``) — this module joins that
precedent rather than inventing a new one. The K6 candidate also sketched a thin
``features/handoff.py`` facade; it was never created (F016, 20260830 audit) — every
consumer, CLI and tests included, imports ``core.handoff_index`` directly, and the
import-linter ``ignore_imports`` edge count is unchanged either way (P-10).

File I/O here is intentionally authorized (P-11: ``core`` file I/O is pure outside a named
set) — ``Handoff.load``/``HandoffIndex.scan`` walk the filesystem exactly like
``specs_resolver``/``workspace_resolver`` already do; joining that authorized set is the
same trade this module's whole existence already makes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dadaia_workspace.core.exceptions import HandoffSchemaError, HandoffValidationError
from dadaia_workspace.core.role_atom_map import ROLE_ATOM_MAP

__all__ = [
    "Finding",
    "Handoff",
    "HandoffIndex",
    "ValidationResult",
    "discover_handoff_paths",
    "load_schema",
    "path_timestamp",
    "scan_handoffs",
    "validate_schema_shape",
]

_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{6}Z)")
_SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
_SELF_PULL_REQUIRED_FROM = "handoff-v1.2"

# ---------------------------------------------------------------------------
# stdlib-only JSON-schema walker (folded from the former
# infrastructure/stdlib_handoff_validator.py + core/protocols/handoff_validator.py
# ValidatorPort — there is exactly one validation path now, internal to this module).
# ---------------------------------------------------------------------------

_SUPPORTED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema",
        "$id",
        "type",
        "required",
        "enum",
        "pattern",
        "properties",
        "items",
        "additionalProperties",
        "format",
        "minimum",
        "minItems",
        "title",
        "description",
    }
)

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "object": dict,
    "array": list,
    "boolean": bool,
    "null": type(None),
}


def _walk_schema(schema: Any, path: str = "") -> None:
    """Reject any schema keyword outside ``_SUPPORTED_KEYWORDS`` — fail loudly."""
    if not isinstance(schema, dict):
        return
    for key in schema:
        if key not in _SUPPORTED_KEYWORDS:
            raise HandoffSchemaError(f"Unsupported schema keyword: {key}")
    for prop_schema in schema.get("properties", {}).values():
        _walk_schema(prop_schema, path)
    items_schema = schema.get("items")
    if isinstance(items_schema, dict):
        _walk_schema(items_schema, path)
    elif isinstance(items_schema, list):
        for sub in items_schema:
            _walk_schema(sub, path)


def _validate_node(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[HandoffValidationError],
) -> None:
    """Validate ``value`` against ``schema``, appending violations to ``errors``.

    The version-routing fix (bug ``reports-sidecar-version-detection-misroutes-future-tokens``)
    lives HERE, structurally, not as a second special-cased function: ``schema_version``
    already carries an ``enum`` in the real schema, so any token outside
    ``{handoff-v1, handoff-v1.1, handoff-v1.2}`` — including a future ``handoff-v1.3`` —
    fails this ordinary enum check with an explicit, actionable message. There is no
    catch-all fallback path to silently downgrade into.
    """
    type_name = schema.get("type")
    if type_name is not None:
        expected_py = _TYPE_MAP.get(str(type_name))
        if expected_py is not None:
            if type_name == "boolean":
                if not isinstance(value, bool):
                    errors.append(
                        HandoffValidationError(
                            path, f"expected boolean, got {type(value).__name__}"
                        )
                    )
                    return
            elif type_name in ("integer", "number"):
                if isinstance(value, bool) or not isinstance(value, expected_py):
                    errors.append(
                        HandoffValidationError(
                            path, f"expected {type_name}, got {type(value).__name__}"
                        )
                    )
                    return
            else:
                if isinstance(value, bool) and type_name == "integer":
                    errors.append(HandoffValidationError(path, f"expected {type_name}, got bool"))
                    return
                if not isinstance(value, expected_py):
                    errors.append(
                        HandoffValidationError(
                            path, f"expected {type_name}, got {type(value).__name__}"
                        )
                    )
                    return

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        errors.append(HandoffValidationError(path, f"{value!r} is not one of {enum_values!r}"))
        return

    pattern = schema.get("pattern")
    if pattern is not None and isinstance(value, str) and not re.fullmatch(pattern, value):
        errors.append(HandoffValidationError(path, f"{value!r} does not match pattern {pattern!r}"))

    fmt = schema.get("format")
    if fmt == "date-time" and isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized)
        except ValueError:
            errors.append(HandoffValidationError(path, f"{value!r} is not a valid date-time"))

    minimum = schema.get("minimum")
    if minimum is not None and isinstance(value, int | float) and value < minimum:
        errors.append(HandoffValidationError(path, f"{value} is less than minimum {minimum}"))

    min_items = schema.get("minItems")
    if min_items is not None and isinstance(value, list) and len(value) < min_items:
        errors.append(
            HandoffValidationError(path, f"array has {len(value)} items, minimum is {min_items}")
        )

    if isinstance(value, dict):
        required_fields: list[str] = schema.get("required", [])
        for req_field in required_fields:
            if req_field not in value:
                child_path = f"{path}.{req_field}" if path else req_field
                errors.append(HandoffValidationError(child_path, "required field missing"))

        if schema.get("additionalProperties") is False:
            allowed_keys = set(schema.get("properties", {}).keys())
            for extra_key in value:
                if extra_key not in allowed_keys:
                    child_path = f"{path}.{extra_key}" if path else extra_key
                    errors.append(
                        HandoffValidationError(
                            child_path, f"additional property '{extra_key}' is not allowed"
                        )
                    )

        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if prop_name in value:
                child_path = f"{path}.{prop_name}" if path else prop_name
                _validate_node(value[prop_name], prop_schema, child_path, errors)

    elif isinstance(value, list):
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for idx, element in enumerate(value):
                child_path = f"{path}[{idx}]"
                _validate_node(element, items_schema, child_path, errors)


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load + structurally validate a JSON-schema file. Raises ``HandoffSchemaError``.

    Public: this is the same loader ``HandoffIndex`` uses internally (lazily, cached),
    exposed standalone for schema-file contract tests that need to prove the schema
    itself is well-formed and usable, without constructing a full ``HandoffIndex``.
    """
    if not schema_path.exists():
        raise HandoffSchemaError(f"Schema file not found: {schema_path}")
    try:
        raw = schema_path.read_text(encoding="utf-8")
        schema: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HandoffSchemaError(f"Schema is not valid JSON: {exc}") from exc
    _walk_schema(schema)
    return schema


def validate_schema_shape(
    doc: dict[str, Any], schema: dict[str, Any]
) -> list[HandoffValidationError]:
    """Structural JSON-schema validation only — no version routing, self_pull or hash
    checks (those need a workspace root; see ``Handoff.validate``). Public for the same
    reason as :func:`load_schema`."""
    errors: list[HandoffValidationError] = []
    _validate_node(doc, schema, "", errors)
    return errors


# ---------------------------------------------------------------------------
# Result + finding shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One finding entry from a handoff's ``findings[]`` array."""

    severity: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a single handoff file."""

    path: Path
    valid: bool
    errors: tuple[HandoffValidationError, ...] = field(default_factory=tuple)
    hash_status: str | None = None


# ---------------------------------------------------------------------------
# Handoff — the one model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Handoff:
    """One discovered ``*.handoff.json`` file, parsed leniently.

    Every field-accessing property is tolerant of a missing/malformed shape (returns
    ``None``/an empty tuple rather than raising) — a handoff whose JSON parsed but whose
    shape is wrong is still a ``Handoff``; :meth:`validate` is what turns shape problems
    into reported errors. A handoff whose JSON did NOT parse at all is also still a
    ``Handoff`` (``raw == {}``, ``malformed_error`` set) — every property degrades to
    ``None`` for it too, so a caller that only reads fields (never calls ``validate``)
    naturally skips a malformed sibling exactly like today's readers already do.
    """

    path: Path
    raw: dict[str, Any] = field(default_factory=dict)
    malformed_error: str | None = None

    # -- classmethod loader -------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> Handoff:
        """Read + parse ``path``. Never raises — malformed JSON is recorded, not thrown."""
        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return cls(path=path, raw={}, malformed_error=f"unreadable: {exc}")
        try:
            doc = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return cls(path=path, raw={}, malformed_error=f"malformed JSON: {exc}")
        if not isinstance(doc, dict):
            return cls(path=path, raw={}, malformed_error="handoff document is not a JSON object")
        return cls(path=path, raw=doc)

    # -- tolerant field readers ----------------------------------------------

    @property
    def schema_version(self) -> str | None:
        value = self.raw.get("schema_version")
        return value if isinstance(value, str) else None

    @property
    def agent(self) -> str | None:
        value = self.raw.get("agent")
        return value if isinstance(value, str) else None

    @property
    def context(self) -> str | None:
        value = self.raw.get("context")
        return value if isinstance(value, str) else None

    @property
    def release_id(self) -> str | None:
        value = self.raw.get("release_id")
        return value if isinstance(value, str) else None

    @property
    def produced_at(self) -> str | None:
        value = self.raw.get("produced_at")
        return value if isinstance(value, str) else None

    @property
    def verdict(self) -> str | None:
        value = self.raw.get("verdict")
        return value if isinstance(value, str) else None

    @property
    def metrics(self) -> dict[str, Any]:
        value = self.raw.get("metrics")
        return value if isinstance(value, dict) else {}

    @property
    def commit_sha(self) -> str | None:
        value = self.metrics.get("commit_sha")
        return value if isinstance(value, str) and value else None

    @property
    def artifact(self) -> dict[str, Any]:
        value = self.raw.get("artifact")
        return value if isinstance(value, dict) else {}

    @property
    def artifact_type(self) -> str | None:
        value = self.artifact.get("type")
        return value if isinstance(value, str) else None

    @property
    def artifact_path_raw(self) -> str | None:
        """The declared ``artifact.path`` string, unresolved — ``None`` if absent/empty."""
        value = self.artifact.get("path")
        return value if isinstance(value, str) and value else None

    @property
    def artifact_content_hash(self) -> str | None:
        value = self.artifact.get("content_hash")
        return value if isinstance(value, str) and value else None

    @property
    def findings(self) -> tuple[Finding, ...]:
        raw_findings = self.raw.get("findings")
        if not isinstance(raw_findings, list):
            return ()
        result: list[Finding] = []
        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            severity = item.get("severity")
            message = item.get("message")
            if isinstance(severity, str) and isinstance(message, str):
                result.append(Finding(severity=severity, message=message))
        return tuple(result)

    @property
    def self_pull_refs(self) -> tuple[str, ...]:
        self_pull = self.raw.get("self_pull")
        if not isinstance(self_pull, dict):
            return ()
        refs = self_pull.get("refs")
        if not isinstance(refs, list):
            return ()
        return tuple(ref for ref in refs if isinstance(ref, str))

    # -- derived helpers -------------------------------------------------

    def findings_summary(self) -> dict[str, int]:
        """Severity counts (``CRITICAL``/``HIGH``/``MEDIUM``/``LOW``) — ``INFO`` excluded,
        matching every existing panel/reports reader's four-bucket shape."""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for finding in self.findings:
            sev = finding.severity.upper()
            if sev in counts:
                counts[sev] += 1
        return counts

    def severity_max(self) -> str | None:
        """The highest-ranked severity present, or ``None`` when there are no findings."""
        present = {finding.severity.upper() for finding in self.findings}
        for sev in _SEVERITY_ORDER:
            if sev in present:
                return sev
        return None

    def effective_timestamp(self) -> datetime:
        """``produced_at`` if parseable, else :func:`path_timestamp` of the file itself."""
        produced_at = self.produced_at
        if produced_at:
            parsed = _parse_datetime(produced_at)
            if parsed is not None:
                return parsed
        return path_timestamp(self.path)

    def expires_at(self, ttl: timedelta) -> datetime:
        """``effective_timestamp() + ttl`` — the one TTL-expiry rule."""
        return self.effective_timestamp() + ttl

    # -- the one artifact-path resolution rule -------------------------------

    def artifact_path(self, workspace_root: Path) -> Path | None:
        """Resolve ``artifact.path`` to an in-workspace file, or ``None`` if unresolvable.

        Resolution order (bugs ``handoff-artifact-path-cannot-reference-specs-audits`` /
        ``handoff-artifact-path-resolver-ignores-workspace-root-contract``):

        1. No ``artifact.path`` declared -> ``None``.
        2. An absolute path resolves as-is (still boundary-guarded).
        3. ANY relative path that exists workspace-rooted resolves workspace-rooted —
           workspace-root wins over the handoff-dir fallback when both exist (this is what
           makes ``repos/<slug>/specs/audits/<UTC>/audit.md`` resolvable — it is not
           ``.dadaia/reports/``-prefixed, and the old per-reader rule only special-cased
           that one prefix).
        4. Otherwise falls back to the legacy handoff-dir-relative location (kept for
           artifacts that only ever existed there).

        Every branch is boundary-guarded against ``..``-traversal and symlink escape
        (``resolve()`` + ``relative_to()``, CWE-22).
        """
        ref = self.artifact_path_raw
        if not ref:
            return None
        candidate = Path(ref)
        if candidate.is_absolute():
            return _within_root(candidate, workspace_root)
        workspace_rooted = _within_root(workspace_root / candidate, workspace_root)
        if workspace_rooted is not None and workspace_rooted.exists():
            return workspace_rooted
        handoff_relative = self.path.parent / candidate
        return _within_root(handoff_relative, workspace_root)

    def artifact_hash_status(self, workspace_root: Path) -> str:
        """``"match"``/``"mismatch"``/``"missing_artifact"`` for the declared ``content_hash``."""
        if not self.artifact_path_raw:
            return "missing_artifact"
        resolved = self.artifact_path(workspace_root)
        if resolved is None or not resolved.is_file():
            return "missing_artifact"
        actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        expected = self.artifact_content_hash or ""
        return "match" if actual == expected else "mismatch"

    # -- validation: schema shape + version routing + self_pull + hash -------

    def validate(
        self,
        *,
        workspace_root: Path,
        schema: dict[str, Any],
        reviewed_root: Path | None = None,
    ) -> ValidationResult:
        """Full validation: schema shape (incl. version routing via the schema's own
        ``schema_version`` enum), the v1.2 ``self_pull`` conditional, and the artifact hash.

        ``reviewed_root`` (bug ``reports-validate-resolves-self-pull-refs-against-the-
        checked-out-branch-not-the-reviewed-tree``, FIX): when given, ``self_pull.refs``
        resolve against THIS filesystem root FIRST — the tree the handoff was actually
        authored/reviewed against (e.g. a linked worktree checked out at the reviewed
        commit) — falling back to the ordinary ``<workspace_root>/repos/<context>/<ref>``
        and ``<workspace_root>/<ref>`` candidates when a ref is not found there, or when
        ``reviewed_root`` is not supplied at all. Root cause: the old resolver had exactly
        two candidates, BOTH anchored to whatever ``repos/<context>`` happens to have
        checked out on disk right now — a Spec Context repo used through multiple git
        worktrees (this very session runs from one) has no way to express "resolve against
        the OTHER worktree, not this one". The fix does not guess which worktree that is —
        it accepts the caller's answer (the CLI's ``--reviewed-root``, mirroring the
        existing ``--workspace`` precedent) rather than adding a git-history read to a
        module whose whole point is to stay filesystem-only.
        """
        if self.malformed_error is not None:
            return ValidationResult(
                path=self.path,
                valid=False,
                errors=(HandoffValidationError("$root", self.malformed_error),),
            )
        errors = validate_schema_shape(self.raw, schema)
        if not errors:
            errors.extend(
                self._check_self_pull(workspace_root=workspace_root, reviewed_root=reviewed_root)
            )
        hash_status: str | None = None
        if not errors and self.artifact_path_raw:
            hash_status = self.artifact_hash_status(workspace_root)
            if hash_status != "match":
                errors.append(
                    HandoffValidationError(
                        "artifact.content_hash",
                        f"artifact hash check failed: {hash_status}",
                    )
                )
        return ValidationResult(
            path=self.path,
            valid=len(errors) == 0,
            errors=tuple(errors),
            hash_status=hash_status,
        )

    def _check_self_pull(
        self, *, workspace_root: Path, reviewed_root: Path | None
    ) -> list[HandoffValidationError]:
        if self.schema_version != _SELF_PULL_REQUIRED_FROM:
            return []
        errors: list[HandoffValidationError] = []
        refs = self.self_pull_refs
        if not refs:
            errors.append(
                HandoffValidationError(
                    "self_pull",
                    "handoff-v1.2 requires self_pull with a non-empty refs array "
                    "(the Layer-1 self-pull audit line)",
                )
            )
            return errors

        context = self.context
        for idx, ref in enumerate(refs):
            if not self._self_pull_ref_exists(
                ref, context, workspace_root=workspace_root, reviewed_root=reviewed_root
            ):
                errors.append(
                    HandoffValidationError(
                        f"self_pull.refs[{idx}]",
                        f"ref does not exist: {ref!r} (checked reviewed_root, "
                        "repos/<context>/<ref> and <workspace>/<ref>)",
                    )
                )

        agent = self.agent
        if agent is not None:
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

    def _self_pull_ref_exists(
        self,
        ref: str,
        context: str | None,
        *,
        workspace_root: Path,
        reviewed_root: Path | None,
    ) -> bool:
        candidates: list[tuple[Path, Path]] = []  # (candidate, boundary root)
        if reviewed_root is not None:
            candidates.append((reviewed_root / ref, reviewed_root))
        if context:
            candidates.append((workspace_root / "repos" / context / ref, workspace_root))
        candidates.append((workspace_root / ref, workspace_root))
        for candidate, boundary in candidates:
            resolved = _within_root(candidate, boundary)
            if resolved is not None and resolved.is_file():
                return True
        return False


def _within_root(path: Path, root: Path) -> Path | None:
    """Resolve ``path``, rejecting anything outside ``root`` (CWE-22 guard)."""
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_datetime_from_name(name: str) -> datetime | None:
    match = _TIMESTAMP_RE.match(name)
    if not match:
        return None
    raw = match.group(1)
    return _parse_datetime(f"{raw[:13]}:{raw[13:15]}:{raw[15:]}")


def path_timestamp(path: Path) -> datetime:
    """The filename's leading UTC stamp (``<YYYY-MM-DDTHHMMSSZ>-…``), else mtime, else now.

    The one age rule for a runtime artifact that carries no ``produced_at`` of its own —
    a report under ``.dadaia/reports/`` or a handoff whose document is unreadable.
    """
    parsed = _parse_datetime_from_name(path.name)
    if parsed is not None:
        return parsed
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Discovery primitives — module-level, workspace-agnostic (chokepoints/doctor_release
# use these directly; neither needs a HandoffIndex/schema/workspace_root).
# ---------------------------------------------------------------------------


def scan_handoffs(root: Path) -> Iterator[Handoff]:
    """Yield a :class:`Handoff` for every ``*.handoff.json`` file under ``root``.

    The one discovery primitive: every reader that needs "every handoff under this
    directory" — regardless of whether it also needs the workspace-rooted resolution
    ``HandoffIndex`` provides — calls this (or ``HandoffIndex.scan``, which is built on
    top of it). ``root`` need not be a workspace root or contain a schema — this is pure
    filesystem discovery, tolerant of a missing directory.
    """
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*.handoff.json")):
        if path.is_file():
            yield Handoff.load(path)


def discover_handoff_paths(root: Path, pattern: str = "**/*.handoff.json") -> list[Path]:
    """Sorted paths matching ``pattern`` under ``root`` — discovery without parsing.

    Used where only the PATH matters (e.g. ``specs/doctor_release.py``'s verdict-staleness
    check, which derives its answer from the 40-hex sha embedded in the filename, never
    from the document's content) — the same one discovery primitive, at the granularity
    that call site actually needs.
    """
    if not root.is_dir():
        return []
    return sorted(root.glob(pattern))


class HandoffIndex:
    """Workspace-rooted handoff discovery + validation.

    Args:
        workspace_root: Root directory of the initialized dadaia workspace. Used to
            resolve default scan roots, artifact paths and self_pull refs — never
            required to exist for construction itself (cheap to build; schema loading
            for :meth:`validate_file`/:meth:`validate_all` is lazy and cached).
    """

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._schema: dict[str, Any] | None = None

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    def default_roots(self) -> tuple[Path, ...]:
        return (self._workspace_root / ".dadaia" / "handoff",)

    def scan(self, roots: Iterable[Path] | None = None) -> Iterator[Handoff]:
        """Yield every discovered :class:`Handoff` under ``roots`` (default: the
        canonical ``.dadaia/handoff`` tree)."""
        for root in roots if roots is not None else self.default_roots():
            yield from scan_handoffs(root)

    def _schema_dict(self) -> dict[str, Any]:
        if self._schema is None:
            schema_path = (
                self._workspace_root / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
            )
            self._schema = load_schema(schema_path)
        return self._schema

    def validate_file(self, path: Path, *, reviewed_root: Path | None = None) -> ValidationResult:
        """Validate a single handoff JSON file (loads it fresh)."""
        handoff = Handoff.load(path)
        return handoff.validate(
            workspace_root=self._workspace_root,
            schema=self._schema_dict(),
            reviewed_root=reviewed_root,
        )

    def validate_all(
        self, context: str | None = None, *, reviewed_root: Path | None = None
    ) -> list[ValidationResult]:
        """Discover and validate all handoffs under the default root (optionally scoped
        to one ``context`` subdirectory)."""
        base = self.default_roots()[0]
        search_root = base / context if context else base
        return [
            self.validate_file(path, reviewed_root=reviewed_root)
            for path in discover_handoff_paths(search_root, "**/*.handoff.json")
        ]

    def check_hash(self, handoff_path: Path) -> str:
        """``"match"``/``"mismatch"``/``"missing_artifact"`` for ``handoff_path``'s artifact."""
        return Handoff.load(handoff_path).artifact_hash_status(self._workspace_root)
