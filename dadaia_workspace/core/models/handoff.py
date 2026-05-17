"""Pure-domain dataclasses for agent handoff documents.

These classes mirror the structure of handoff-v1.schema.json.
No I/O — only data structure. Testable in total isolation.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class ArtifactType(enum.Enum):
    """Enumeration of valid artifact types."""

    report = "report"
    spec = "spec"
    plan = "plan"
    tasks = "tasks"
    closure = "closure"
    memory = "memory"
    other = "other"


class Severity(enum.Enum):
    """Enumeration of finding severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to the artifact produced by the agent."""

    type: ArtifactType
    path: str
    content_hash: str  # sha256 hex of the artifact file


@dataclass(frozen=True)
class Finding:
    """A key finding from the agent's work session."""

    severity: Severity
    message: str


@dataclass(frozen=True)
class NextHandoff:
    """Pointer to the expected next handoff in the pipeline."""

    agent: str
    context: str
    expected_artifact_type: ArtifactType


@dataclass(frozen=True)
class HandoffDocument:
    """Immutable domain model mirroring handoff-v1.schema.json.

    The ``from_dict`` classmethod parses a raw dict (e.g. from JSON) into this
    structure. It raises ``ValueError`` only on invalid enum values. Field-level
    validation against the schema is the responsibility of ``ValidatorPort``
    implementations — not this class.
    """

    schema_version: str
    agent: str
    context: str
    produced_at: str  # ISO 8601 wire format kept as string
    artifact: ArtifactRef
    release_id: str | None = None
    findings: tuple[Finding, ...] = ()
    decisions_required: tuple[str, ...] = ()
    next_handoff: NextHandoff | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> HandoffDocument:
        """Parse a raw dictionary into a ``HandoffDocument``.

        Args:
            data: The raw dict, typically deserialized from JSON.

        Returns:
            A frozen ``HandoffDocument`` instance.

        Raises:
            ValueError: If an enum value (ArtifactType or Severity) is invalid.
        """
        artifact_raw = data["artifact"]
        assert isinstance(artifact_raw, dict)
        artifact = ArtifactRef(
            type=ArtifactType(artifact_raw["type"]),
            path=str(artifact_raw["path"]),
            content_hash=str(artifact_raw["content_hash"]),
        )

        findings_raw = data.get("findings", [])
        assert isinstance(findings_raw, list)
        findings = tuple(
            Finding(
                severity=Severity(f["severity"]),
                message=str(f["message"]),
            )
            for f in findings_raw
        )

        decisions_raw = data.get("decisions_required", [])
        assert isinstance(decisions_raw, list)
        decisions_required = tuple(str(d) for d in decisions_raw)

        next_handoff: NextHandoff | None = None
        next_raw = data.get("next_handoff")
        if next_raw is not None:
            assert isinstance(next_raw, dict)
            next_handoff = NextHandoff(
                agent=str(next_raw["agent"]),
                context=str(next_raw["context"]),
                expected_artifact_type=ArtifactType(next_raw["expected_artifact_type"]),
            )

        return cls(
            schema_version=str(data["schema_version"]),
            agent=str(data["agent"]),
            context=str(data["context"]),
            produced_at=str(data["produced_at"]),
            artifact=artifact,
            release_id=str(data["release_id"]) if data.get("release_id") is not None else None,
            findings=findings,
            decisions_required=decisions_required,
            next_handoff=next_handoff,
        )
