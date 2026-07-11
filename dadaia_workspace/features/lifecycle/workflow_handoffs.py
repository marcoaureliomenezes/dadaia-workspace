"""The run-scoped workflow-step handoff resolver/service (v0.1.30 Item 5 / T-30-D-03).

This is the queue-semantics engine that makes prompt-to-prompt communication
**addressable by (run id, producer step, attempt)** instead of the slop "latest handoff
by agent filename" (SPEC A25). There is no SQLite, no queue server — the queue lives in
this Python resolver over two planes:

- **Control plane** — :class:`~dadaia_workspace.core.models.workflow_handoff.WorkflowStepLedger`
  carried on :class:`~dadaia_workspace.core.models.lifecycle.LifecycleRun.workflow_steps`,
  persisted atomically through the run store.
- **Data plane** — immutable step payload envelopes written atomically under the
  WORKSPACE-ROOT ``.dadaia/runs/lifecycle/<run_id>/steps/`` zone via an injected writer
  port. ``.dadaia/handoff/`` stays reserved for durable external evidence — workflow-step
  payloads never go there.

Resolver surface:

- :meth:`produce` — a producing step writes an immutable payload envelope atomically,
  validates it against the envelope schema + the named payload schema, and records a
  :class:`WorkflowStepRecord` in the run's ledger through the run store. (A18/A21.)
- :meth:`resolve_required` — a consuming step resolves the EXACT upstream payload it
  declared a ``consumes`` edge on, by ``(run_id, producer_step, attempt)``. A missing or
  malformed required payload raises :class:`RequiredHandoffMissingError` /
  :class:`MalformedHandoffError` — the workflow BLOCKS before the next prompt runs.
  (A19/A20/A25.)
- :meth:`record_consumption` — record that ``(consumer_step, consumer_attempt)`` consumed
  a producer payload, atomically through the run store. Drives the
  ``produced → consumed_partial → consumed_all`` transitions. (A22.)
- :meth:`render_digest` — render a COMPACT digest (verdict / summary / findings / refs)
  of a resolved payload for injection into the next prompt — never the raw JSON.

Layering: ``features/`` importing ``core/`` + sibling ``features/`` + the run-store
protocol only. The payload writer and the schema source are injected / resolved from the
packaged ``public/schemas/`` root — no ``infrastructure`` import.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.lifecycle import LifecycleRun
from dadaia_workspace.core.models.workflow_handoff import (
    RetentionMode,
    WorkflowStepConsumerRecord,
    WorkflowStepRecord,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.core.protocols.runtime_files import StepPayloadRef

_ENVELOPE_SCHEMA_ID = "workflow-step-payload-v1"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class WorkflowHandoffError(DadaiaError):
    """Base error for the workflow-step handoff resolver."""


class RequiredHandoffMissingError(WorkflowHandoffError):
    """A required upstream payload is absent from the ledger / data plane (A20)."""


class MalformedHandoffError(WorkflowHandoffError):
    """A required upstream payload exists but fails envelope / named-schema validation (A20)."""


class PayloadSchemaUnknownError(WorkflowHandoffError):
    """A produced payload names an output_schema with no registered validator."""


# ---------------------------------------------------------------------------
# Injected writer port (concrete adapter: FilesystemRuntimeFileAdapter — T-30-D-04)
# ---------------------------------------------------------------------------


@runtime_checkable
class WorkflowStepPayloadWriter(Protocol):
    """Write/read immutable step payload envelopes under the run-scoped steps zone.

    The concrete adapter (``FilesystemRuntimeFileAdapter`` — T-30-D-04) writes under the
    WORKSPACE-ROOT ``.dadaia/runs/lifecycle/<run_id>/steps/`` canonical zone with
    atomic temp+rename. The resolver depends only on this narrow port — no infrastructure
    import — so it is unit-testable with an in-memory fake.
    """

    def write_step_payload(
        self,
        *,
        run_id: str,
        producer_step: str,
        attempt: int,
        content: str,
    ) -> StepPayloadRef:
        """Write the payload envelope JSON immutably; return its ref + content hash."""
        ...

    def read_step_payload(self, payload_ref: str) -> str | None:
        """Return the raw envelope JSON at ``payload_ref``, or ``None`` if absent."""
        ...


# ---------------------------------------------------------------------------
# Named payload validators (A21 — per output_schema Python validators this release)
# ---------------------------------------------------------------------------

#: A named-payload validator returns a list of human-readable reasons; empty ⇒ valid.
PayloadValidator = Callable[[dict[str, object]], list[str]]


def _require_keys(payload: dict[str, object], keys: tuple[str, ...]) -> list[str]:
    return [f"missing required field '{key}'" for key in keys if key not in payload]


def _validate_release_scope_handoff(payload: dict[str, object]) -> list[str]:
    """Minimal validator for the release_scope step's payload (release-scope-handoff-v1)."""
    return _require_keys(payload, ("summary",))


def _validate_review_verdict(payload: dict[str, object]) -> list[str]:
    """Validator for a review-verdict payload — the gate keys on a verdict (A24)."""
    reasons = _require_keys(payload, ("verdict",))
    verdict = payload.get("verdict")
    if verdict is not None and verdict not in {"APPROVED", "REJECTED"}:
        reasons.append("verdict must be APPROVED or REJECTED")
    return reasons


def _validate_generic_handoff(payload: dict[str, object]) -> list[str]:
    """Fallback validator for a generic step payload — requires a non-empty summary."""
    reasons = _require_keys(payload, ("summary",))
    summary = payload.get("summary")
    if summary is not None and (not isinstance(summary, str) or not summary.strip()):
        reasons.append("summary must be a non-empty string")
    return reasons


#: Registry of named payload schemas → Python validators (A21). New named schemas are
#: registered here AT MODULE-IMPORT time (never mutated at runtime — Wave-E test-isolation
#: nit). Per-schema JSON Schema files follow incrementally (Slice D). The Wave-E
#: ``audit``/``research``/``bug_report`` workflow bodies (T-30-E-01..03) seed their
#: output-schema validators here so a test never has to register them at runtime:
#:
#: - audit:      scope → ``audit-scope-handoff-v1`` (summary), drift-scan review →
#:               ``audit-findings-handoff-v1`` (verdict), triage →
#:               ``audit-disposition-handoff-v1`` (summary — disposition-ready output).
#: - research:   scope → ``research-scope-handoff-v1`` (summary), synthesis →
#:               ``research-findings-handoff-v1`` (summary).
#: - bug_report: intake → ``bug-intake-handoff-v1`` (summary), dedupe review →
#:               ``bug-dedupe-handoff-v1`` (verdict), bug_write →
#:               ``bug-record-handoff-v1`` (summary — the ADDITIVE bug record).
#: - pipeline (v0.1.78 T-B / FR-B): the full IMPLEMENTATION→QA→SECURITY→CODE ladder
#:               (``LifecyclePipeline.run``) produces one payload per step through the
#:               (additive-optional) wired ``handoff_resolver`` — ``implement`` (create) →
#:               ``generic-step-handoff-v1`` (summary), ``review_qa`` → the existing
#:               ``qa-review-handoff-v1`` (verdict), ``review_security`` →
#:               ``security-review-handoff-v1`` (verdict), ``review_code`` →
#:               ``code-review-handoff-v1`` (verdict).
_PAYLOAD_VALIDATORS: dict[str, PayloadValidator] = {
    "release-scope-handoff-v1": _validate_release_scope_handoff,
    "spec-review-handoff-v1": _validate_review_verdict,
    "plan-review-handoff-v1": _validate_review_verdict,
    "tasks-review-handoff-v1": _validate_review_verdict,
    "qa-review-handoff-v1": _validate_review_verdict,
    "implementation-handoff-v1": _validate_generic_handoff,
    "generic-step-handoff-v1": _validate_generic_handoff,
    # Wave E — audit workflow body (T-30-E-01).
    "audit-scope-handoff-v1": _validate_generic_handoff,
    "audit-findings-handoff-v1": _validate_review_verdict,
    "audit-disposition-handoff-v1": _validate_generic_handoff,
    # Wave E — research workflow body (T-30-E-02).
    "research-scope-handoff-v1": _validate_generic_handoff,
    "research-findings-handoff-v1": _validate_generic_handoff,
    # Wave E — bug_report workflow body (T-30-E-03).
    "bug-intake-handoff-v1": _validate_generic_handoff,
    "bug-dedupe-handoff-v1": _validate_review_verdict,
    "bug-record-handoff-v1": _validate_generic_handoff,
    # v0.1.78 T-B / FR-B — full-pipeline (``LifecyclePipeline.run``) step payloads.
    "security-review-handoff-v1": _validate_review_verdict,
    "code-review-handoff-v1": _validate_review_verdict,
}


def register_payload_validator(output_schema: str, validator: PayloadValidator) -> None:
    """Register a named-payload validator (extension seam for Wave E workflow bodies)."""
    _PAYLOAD_VALIDATORS[output_schema] = validator


def known_payload_schemas() -> tuple[str, ...]:
    """Return every output_schema with a registered named-payload validator."""
    return tuple(sorted(_PAYLOAD_VALIDATORS))


# ---------------------------------------------------------------------------
# Envelope schema (packaged JSON Schema)
# ---------------------------------------------------------------------------


def _default_schema_root() -> Path:
    """Resolve the packaged ``public/schemas/`` root inside the wheel/source tree.

    Mirrors :func:`FragmentLoader._default_root` — the package root is three levels up
    from this module; the schema source lives at ``public/schemas/``.
    """
    package_root = Path(__file__).resolve().parents[2]
    return package_root / "public" / "schemas"


def _load_envelope_validator(schema_root: Path) -> Draft202012Validator:
    schema_path = schema_root / f"{_ENVELOPE_SCHEMA_ID}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:  # pragma: no cover — guards a corrupt packaged schema.
        raise WorkflowHandoffError(f"packaged envelope schema is invalid: {exc.message}") from exc
    return Draft202012Validator(schema)


# ---------------------------------------------------------------------------
# Resolver / service
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedHandoff:
    """A resolved upstream payload: the ledger record + the parsed payload body."""

    record: WorkflowStepRecord
    payload: dict[str, object]


class WorkflowHandoffResolver:
    """Run-scoped workflow-step handoff queue over the ledger + immutable payload plane."""

    def __init__(
        self,
        *,
        run_store: LifecycleRunStore,
        payload_writer: WorkflowStepPayloadWriter,
        clock: Callable[[], str],
        schema_root: Path | None = None,
    ) -> None:
        self._run_store = run_store
        self._writer = payload_writer
        self._clock = clock
        self._envelope_validator = _load_envelope_validator(schema_root or _default_schema_root())

    # -- produce (A18 / A21) -------------------------------------------------

    def produce(
        self,
        run: LifecycleRun,
        *,
        producer_step: str,
        attempt: int,
        output_schema: str,
        payload: dict[str, object],
        declared_consumers: tuple[str, ...] = (),
        retention_mode: RetentionMode = RetentionMode.DELETE_AFTER_CONSUMED,
    ) -> tuple[LifecycleRun, WorkflowStepRecord]:
        """Write the immutable payload envelope, validate it, and record it in the ledger.

        The envelope is validated against ``workflow-step-payload-v1`` AND the named
        ``output_schema`` validator before the ledger record is committed — a payload that
        fails either contract is never recorded. The run is persisted atomically through
        the run store; the returned run carries the new ledger entry.
        """
        self._require_known_schema(output_schema)
        produced_at = self._clock()
        envelope = {
            "schema_version": _ENVELOPE_SCHEMA_ID,
            "run_id": run.run_id,
            "producer_step": producer_step,
            "attempt": attempt,
            "output_schema": output_schema,
            "produced_at": produced_at,
            "retention_mode": retention_mode.value,
            "declared_consumers": list(declared_consumers),
            "payload": payload,
        }
        self._validate_envelope(envelope)
        self._validate_named_payload(output_schema, payload)

        content = json.dumps(envelope, indent=2, sort_keys=True) + "\n"
        ref = self._writer.write_step_payload(
            run_id=run.run_id,
            producer_step=producer_step,
            attempt=attempt,
            content=content,
        )
        record = WorkflowStepRecord(
            run_id=run.run_id,
            producer_step=producer_step,
            attempt=attempt,
            output_schema=output_schema,
            payload_ref=ref.payload_ref,
            content_hash=ref.content_hash,
            produced_at=produced_at,
            retention_mode=retention_mode,
            declared_consumers=declared_consumers,
        )
        updated = self._persist(run, run.workflow_steps.upsert(record))
        return updated, record

    # -- resolve a required upstream payload (A19 / A20 / A25) ----------------

    def resolve_required(
        self,
        run: LifecycleRun,
        *,
        producer_step: str,
        attempt: int,
    ) -> ResolvedHandoff:
        """Resolve the EXACT upstream payload by (run id, producer step, attempt).

        This is the A25 replacement for "latest handoff by agent filename": the lookup is
        the addressable ledger key, never a filename glob. A missing record raises
        :class:`RequiredHandoffMissingError`; a record whose on-disk payload is absent,
        unreadable, hash-mismatched, or schema-invalid raises
        :class:`MalformedHandoffError` — either way the workflow BLOCKS before the next
        prompt runs (A20).
        """
        record = run.workflow_steps.find(producer_step, attempt)
        if record is None:
            raise RequiredHandoffMissingError(
                f"required upstream payload not in ledger: run={run.run_id!r} "
                f"step={producer_step!r} attempt={attempt}"
            )
        raw = self._writer.read_step_payload(record.payload_ref)
        if raw is None:
            raise MalformedHandoffError(
                f"required upstream payload file missing: {record.payload_ref}"
            )
        payload = self._parse_and_verify(record, raw)
        return ResolvedHandoff(record=record, payload=payload)

    # -- record a consumption (A22) ------------------------------------------

    def record_consumption(
        self,
        run: LifecycleRun,
        *,
        producer_step: str,
        producer_attempt: int,
        consumer_step: str,
        consumer_attempt: int,
    ) -> LifecycleRun:
        """Record that (consumer_step, consumer_attempt) consumed a producer payload.

        Idempotent per (consumer step, attempt). Persisted atomically through the run
        store. Drives the ``produced → consumed_partial → consumed_all`` transitions and,
        once every declared consumer has acked, makes the payload cleanup-eligible (A22).
        """
        record = run.workflow_steps.find(producer_step, producer_attempt)
        if record is None:
            raise RequiredHandoffMissingError(
                f"cannot record consumption — producer payload not in ledger: "
                f"step={producer_step!r} attempt={producer_attempt}"
            )
        updated_record = record.with_consumption(
            WorkflowStepConsumerRecord(
                consumer_step=consumer_step,
                consumer_attempt=consumer_attempt,
                consumed_at=self._clock(),
            )
        )
        if updated_record is record:
            return run  # idempotent no-op — nothing to persist.
        return self._persist(run, run.workflow_steps.upsert(updated_record))

    # -- compact digest rendering (not raw JSON) -----------------------------

    @staticmethod
    def render_digest(resolved: ResolvedHandoff) -> str:
        """Render a COMPACT digest of a resolved payload for the next prompt.

        Emits the addressable ref, the verdict (if any), a one-line summary, the count and
        headline of any findings, and the artifact refs — never the raw JSON payload. The
        downstream prompt cites the payload by its ref; it does not paste the full body.
        """
        record = resolved.record
        payload = resolved.payload
        lines = [
            f"### handoff {record.producer_step}#{record.attempt} (schema {record.output_schema})",
            f"- ref: {record.payload_ref}",
        ]
        verdict = payload.get("verdict")
        if isinstance(verdict, str):
            lines.append(f"- verdict: {verdict}")
            reason = payload.get("verdict_reason")
            if isinstance(reason, str) and reason.strip():
                lines.append(f"- verdict_reason: {reason.strip()}")
        summary = payload.get("summary")
        if isinstance(summary, str) and summary.strip():
            lines.append(f"- summary: {summary.strip()}")
        findings = payload.get("findings")
        if isinstance(findings, list) and findings:
            lines.append(f"- findings: {len(findings)}")
            for finding in findings[:5]:
                if isinstance(finding, dict):
                    sev = finding.get("severity", "?")
                    msg = finding.get("message", "")
                    lines.append(f"  - [{sev}] {msg}")
        refs = payload.get("artifact_refs")
        if isinstance(refs, list) and refs:
            lines.append(f"- artifact_refs: {', '.join(str(r) for r in refs)}")
        return "\n".join(lines)

    # -- internals ----------------------------------------------------------

    def _persist(self, run: LifecycleRun, ledger: object) -> LifecycleRun:
        from dataclasses import replace

        updated = replace(run, workflow_steps=ledger)  # type: ignore[arg-type]
        self._run_store.save(updated)
        return updated

    def _require_known_schema(self, output_schema: str) -> None:
        if output_schema not in _PAYLOAD_VALIDATORS:
            valid = ", ".join(known_payload_schemas())
            raise PayloadSchemaUnknownError(
                f"no payload validator for output_schema '{output_schema}'; known: {valid}"
            )

    def _validate_envelope(self, envelope: dict[str, object]) -> None:
        try:
            self._envelope_validator.validate(envelope)
        except ValidationError as exc:
            raise MalformedHandoffError(
                f"step payload envelope failed {_ENVELOPE_SCHEMA_ID} validation: {exc.message}"
            ) from exc

    def _validate_named_payload(self, output_schema: str, payload: dict[str, object]) -> None:
        validator = _PAYLOAD_VALIDATORS[output_schema]
        reasons = validator(payload)
        if reasons:
            raise MalformedHandoffError(
                f"step payload failed '{output_schema}' validation: {'; '.join(reasons)}"
            )

    def _parse_and_verify(self, record: WorkflowStepRecord, raw: str) -> dict[str, object]:
        import hashlib

        actual_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if actual_hash != record.content_hash:
            raise MalformedHandoffError(
                f"step payload content hash mismatch for {record.payload_ref} "
                "(payload was mutated — immutability violated)"
            )
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MalformedHandoffError(
                f"step payload at {record.payload_ref} is not valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(envelope, dict):
            raise MalformedHandoffError(f"step payload at {record.payload_ref} is not an object")
        self._validate_envelope(envelope)
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise MalformedHandoffError(
                f"step payload at {record.payload_ref} has no payload object"
            )
        self._validate_named_payload(record.output_schema, payload)
        return payload


__all__ = [
    "MalformedHandoffError",
    "PayloadSchemaUnknownError",
    "RequiredHandoffMissingError",
    "ResolvedHandoff",
    "StepPayloadRef",
    "WorkflowHandoffError",
    "WorkflowHandoffResolver",
    "WorkflowStepPayloadWriter",
    "known_payload_schemas",
    "register_payload_validator",
]
