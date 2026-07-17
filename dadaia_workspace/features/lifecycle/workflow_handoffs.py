"""The run-scoped workflow-step handoff resolver/service (v0.1.30 Item 5 / T-30-D-03).

This is the queue-semantics engine that makes prompt-to-prompt communication
**addressable by (run id, producer step, attempt)** instead of the slop "latest handoff
by agent filename" (SPEC A25). There is no SQLite, no queue server — the queue lives in
this Python resolver over two planes:

- **Control plane** — :class:`~dadaia_workspace.core.models.workflow_handoff.WorkflowStepLedger`
  carried on :class:`~dadaia_workspace.core.models.lifecycle.LifecycleRun.workflow_steps`,
  persisted atomically through the run store.
- **Data plane** — immutable step payload envelopes written atomically under a
  **release-aware zone inside the Spec Context's specs directory** (operator mandate:
  "handoffs must be registered in the release folder, not in an aleatory path on
  .dadaia"): ``<specs_dir>/releases/<release_id>/handoffs/<run_id>/steps/`` for a run
  with a real release context, or ``<specs_dir>/backlog/handoffs/<run_id>/steps/`` for a
  run with no release context (currently only the ``backlog_definition`` workflow — see
  :func:`_zone_release_id`). This resolver computes *which* zone a run belongs to
  (:class:`ReleaseAwareWorkflowStepPayloadWriter`); the injected writer resolves the
  concrete ``specs_dir`` from the run's ``context`` and performs the confined atomic I/O.
  A writer that has not yet implemented the extension is used through the legacy,
  narrower :class:`WorkflowStepPayloadWriter` contract unchanged — the WORKSPACE-ROOT
  ``.dadaia/runs/lifecycle/<run_id>/steps/`` zone — so this resolver stays wired against
  every existing adapter with no breaking change (the concrete
  ``FilesystemRuntimeFileAdapter`` — ``dadaia_workspace/infrastructure/runtime_files.py``
  — implements :class:`ReleaseAwareWorkflowStepPayloadWriter`, so production writes land
  in the release-aware zone). ``.dadaia/handoff/`` stays reserved
  for durable external evidence (agent report handoffs) — workflow-step payloads never go
  there, in either zone.

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

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.lifecycle import AgentRunResult, LifecycleRun
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

    def purge_step_payloads(
        self, run_id: str, producer_steps: frozenset[str] | set[str] | None = None
    ) -> int:
        """Reclaim the run's orphaned step-payload zone on RESTART; return files removed.

        *producer_steps* narrows the reclaim to the named steps (resume-from-step)."""
        ...

    def purge_worker_outputs(self, refs: tuple[str, ...]) -> int:
        """Remove exact temporary worker outputs owned by restarted steps."""
        ...


@runtime_checkable
class ReleaseAwareWorkflowStepPayloadWriter(WorkflowStepPayloadWriter, Protocol):
    """Optional writer capability: route the step-payload zone under the Spec Context.

    Probed via ``isinstance`` (``runtime_checkable``, like the base contract it extends)
    so the resolver stays wired against every adapter that only satisfies
    :class:`WorkflowStepPayloadWriter` — no breaking change for an adapter that has not
    yet implemented this extension. An adapter that implements it (production:
    ``FilesystemRuntimeFileAdapter``) routes payloads under:

    - ``<specs_dir>/releases/<release_id>/handoffs/<run_id>/steps/`` — a run with a real
      release context (``release_id`` given).
    - ``<specs_dir>/backlog/handoffs/<run_id>/steps/`` — a run with no release context
      (``release_id is None``).

    ``specs_dir`` is resolved by the adapter from ``context`` (the Spec Context Project
    name), mirroring the ``repos/<context>/specs`` / self-hosting ``specs`` fallback
    already used by ``container.py``'s workflow builders.
    """

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
        """Write the immutable envelope under the release-aware zone; return its ref."""
        ...

    def purge_release_scoped_step_payloads(
        self,
        run_id: str,
        producer_steps: frozenset[str] | set[str] | None,
        *,
        context: str,
        release_id: str | None,
    ) -> int:
        """Reclaim the run's release-aware step-payload zone for a RESTART."""
        ...


#: Workflow ``command`` values whose runs have no release context — their durable step
#: payloads route to the shared ``<specs_dir>/backlog/handoffs/`` zone instead of a
#: specific release's zone (operator mandate: handoffs live in the release folder, not
#: an "aleatory path" under ``.dadaia``). ``backlog_definition`` is the only such
#: workflow today; a future no-release workflow joins this set.
_NO_RELEASE_CONTEXT_COMMANDS = frozenset({"backlog_definition"})


def _zone_release_id(run: LifecycleRun) -> str | None:
    """Return the release id for *run*'s durable handoff zone, or ``None`` for backlog runs.

    ``None`` routes :class:`ReleaseAwareWorkflowStepPayloadWriter` to the shared
    ``<specs_dir>/backlog/handoffs/`` zone; any other value routes to
    ``<specs_dir>/releases/<that_id>/handoffs/``. Both ``context`` and ``release_id`` are
    already carried on every :class:`LifecycleRun` — no new field, no caller change.
    """
    if run.command in _NO_RELEASE_CONTEXT_COMMANDS:
        return None
    return run.release_id


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


def _require_non_empty_string(
    payload: dict[str, object], field: str, reasons: list[str]
) -> str | None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        reasons.append(f"{field} must be a non-empty string")
        return None
    return value.strip()


def _validate_audit_scope_handoff(payload: dict[str, object]) -> list[str]:
    """Require a bounded, executable audit scope rather than a fallback summary."""
    reasons: list[str] = []
    _require_non_empty_string(payload, "summary", reasons)
    _require_non_empty_string(payload, "audit_question", reasons)

    lenses = payload.get("lenses")
    lens_names: list[str] = []
    if not isinstance(lenses, list) or not lenses:
        reasons.append("lenses must be a non-empty list")
    else:
        for index, lens in enumerate(lenses):
            if not isinstance(lens, dict):
                reasons.append(f"lenses[{index}] must be an object")
                continue
            name = _require_non_empty_string(lens, "name", reasons)
            _require_non_empty_string(lens, "rationale", reasons)
            if name is not None:
                lens_names.append(name)
        if len(lens_names) != len(set(lens_names)):
            reasons.append("lens names must be unique")

    surfaces = payload.get("surfaces")
    if (
        not isinstance(surfaces, list)
        or not surfaces
        or any(not isinstance(item, str) or not item.strip() for item in surfaces)
    ):
        reasons.append("surfaces must be a non-empty list of non-empty strings")

    criteria = payload.get("acceptance_criteria")
    criterion_lenses: list[str] = []
    if not isinstance(criteria, list) or not criteria:
        reasons.append("acceptance_criteria must be a non-empty list")
    else:
        for index, criterion in enumerate(criteria):
            if not isinstance(criterion, dict):
                reasons.append(f"acceptance_criteria[{index}] must be an object")
                continue
            lens = _require_non_empty_string(criterion, "lens", reasons)
            _require_non_empty_string(criterion, "pass_condition", reasons)
            if lens is not None:
                criterion_lenses.append(lens)
        if lens_names:
            uncovered = _uncovered_lens_names(lens_names, criterion_lenses)
            if uncovered:
                reasons.append(
                    "acceptance_criteria must cover every declared lens (no criterion "
                    f"matches: {', '.join(uncovered)})"
                )
        if len(criterion_lenses) != len(set(criterion_lenses)):
            reasons.append("acceptance_criteria lens names must be unique")
    return reasons


def _normalize_lens_name(value: str) -> str:
    """Fold a lens name to a hyphen/case/whitespace-insensitive comparison key."""
    return re.sub(r"[-_\s]+", "", value).lower()


def _uncovered_lens_names(lens_names: list[str], criterion_lenses: list[str]) -> list[str]:
    """Return every declared lens with no acceptance-criterion match.

    A criterion "covers" a lens when either name contains the other after
    hyphen/case/whitespace-insensitive normalization (a spelling variant — e.g.
    ``architecture`` vs ``architecture-drift`` — must not fail a multi-session audit
    run). Set-equality of the raw strings is deliberately NOT required.
    """
    normalized_criteria = [_normalize_lens_name(lens) for lens in criterion_lenses]
    return [
        name
        for name in lens_names
        if not any(
            _normalize_lens_name(name) in candidate or candidate in _normalize_lens_name(name)
            for candidate in normalized_criteria
        )
    ]


def _validate_audit_findings_handoff(payload: dict[str, object]) -> list[str]:
    """Require measured lens results and structured, addressable findings.

    ``verdict`` and ``findings``/``lens_results`` are independently valid: a scan may
    reach an overall ``APPROVED`` verdict while still carrying LOW/INFO findings, and a
    ``REJECTED`` verdict does not require a specific failed lens or a non-empty findings
    list (e.g. a process-level rejection). Only each field's own shape is enforced here —
    the coupled "APPROVED requires zero findings / REJECTED requires >=1 failed lens"
    invariant was removed; it provably bought nothing over the independent shape checks.
    """
    reasons = _validate_review_verdict(payload)
    _require_non_empty_string(payload, "summary", reasons)
    _require_non_empty_string(payload, "verdict_reason", reasons)

    lens_results = payload.get("lens_results")
    if not isinstance(lens_results, list) or not lens_results:
        reasons.append("lens_results must be a non-empty list")
    else:
        names: list[str] = []
        for index, result in enumerate(lens_results):
            if not isinstance(result, dict):
                reasons.append(f"lens_results[{index}] must be an object")
                continue
            name = _require_non_empty_string(result, "lens", reasons)
            if result.get("status") not in {"PASS", "FAIL"}:
                reasons.append(f"lens_results[{index}].status must be PASS or FAIL")
            evidence = result.get("evidence")
            if (
                not isinstance(evidence, list)
                or not evidence
                or any(not isinstance(item, str) or not item.strip() for item in evidence)
            ):
                reasons.append(
                    f"lens_results[{index}].evidence must be a non-empty list of strings"
                )
            if name is not None:
                names.append(name)
        if len(names) != len(set(names)):
            reasons.append("lens_results lens names must be unique")

    findings = payload.get("findings")
    finding_ids: list[str] = []
    if not isinstance(findings, list):
        reasons.append("findings must be a list")
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            reasons.append(f"findings[{index}] must be an object")
            continue
        finding_id = _require_non_empty_string(finding, "id", reasons)
        severity = finding.get("severity")
        if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}:
            reasons.append(f"findings[{index}].severity is invalid")
        _require_non_empty_string(finding, "message", reasons)
        _require_non_empty_string(finding, "surface", reasons)
        _require_non_empty_string(finding, "evidence", reasons)
        if finding_id is not None:
            finding_ids.append(finding_id)
    if len(finding_ids) != len(set(finding_ids)):
        reasons.append("finding ids must be unique")

    return reasons


def _validate_audit_disposition_handoff(payload: dict[str, object]) -> list[str]:
    """Require an explicit routing decision for each upstream finding."""
    reasons: list[str] = []
    _require_non_empty_string(payload, "summary", reasons)
    if payload.get("source_verdict") not in {"APPROVED", "REJECTED"}:
        reasons.append("source_verdict must be APPROVED or REJECTED")
    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, list):
        reasons.append("dispositions must be a list")
        return reasons
    finding_ids: list[str] = []
    for index, disposition in enumerate(dispositions):
        if not isinstance(disposition, dict):
            reasons.append(f"dispositions[{index}] must be an object")
            continue
        finding_id = _require_non_empty_string(disposition, "finding_id", reasons)
        if disposition.get("disposition") not in {
            "bug",
            "backlog",
            "accepted-risk",
            "resolved",
        }:
            reasons.append(f"dispositions[{index}].disposition is invalid")
        _require_non_empty_string(disposition, "route", reasons)
        if disposition.get("severity") not in {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
            "INFO",
        }:
            reasons.append(f"dispositions[{index}].severity is invalid")
        _require_non_empty_string(disposition, "evidence", reasons)
        if finding_id is not None:
            finding_ids.append(finding_id)
    if len(finding_ids) != len(set(finding_ids)):
        reasons.append("disposition finding_ids must be unique")
    return reasons


#: Canonical audit disposition routes — the same enum the triage step always used
#: (audit-disposition law: route, never delete).
_AUDIT_REPORT_DISPOSITION_ROUTES = frozenset({"bug", "backlog", "accepted-risk", "resolved"})


def _validate_audit_report_handoff(payload: dict[str, object]) -> list[str]:
    """Validator for the collapsed single-step audit report (``audit-report-v1``).

    The audit workflow's scope -> drift-scan -> triage ladder collapses to one model
    step producing ``{question, lenses[], findings[], dispositions[]}``. Findings carry
    their own ``id``/``severity``/``lens``/``summary``; dispositions route each
    ``finding_id`` to one of ``bug``/``backlog``/``accepted-risk``/``resolved``.
    Dispositions do NOT need to byte-copy a finding's severity or an overall verdict —
    Python stamps those onto the disposition record downstream; only the routing
    decision is required here.
    """
    reasons: list[str] = []
    _require_non_empty_string(payload, "question", reasons)

    lenses = payload.get("lenses")
    if (
        not isinstance(lenses, list)
        or not lenses
        or any(not isinstance(item, str) or not item.strip() for item in lenses)
    ):
        reasons.append("lenses must be a non-empty list of non-empty strings")

    findings = payload.get("findings")
    finding_ids: list[str] = []
    if not isinstance(findings, list):
        reasons.append("findings must be a list")
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            reasons.append(f"findings[{index}] must be an object")
            continue
        finding_id = _require_non_empty_string(finding, "id", reasons)
        if finding.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}:
            reasons.append(f"findings[{index}].severity is invalid")
        _require_non_empty_string(finding, "lens", reasons)
        _require_non_empty_string(finding, "summary", reasons)
        if finding_id is not None:
            finding_ids.append(finding_id)
    if len(finding_ids) != len(set(finding_ids)):
        reasons.append("finding ids must be unique")

    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, list):
        reasons.append("dispositions must be a list")
        dispositions = []
    disposition_finding_ids: list[str] = []
    for index, disposition in enumerate(dispositions):
        if not isinstance(disposition, dict):
            reasons.append(f"dispositions[{index}] must be an object")
            continue
        disposition_finding_id = _require_non_empty_string(disposition, "finding_id", reasons)
        if disposition.get("route") not in _AUDIT_REPORT_DISPOSITION_ROUTES:
            reasons.append(f"dispositions[{index}].route is invalid")
        if disposition_finding_id is not None:
            disposition_finding_ids.append(disposition_finding_id)
    if len(disposition_finding_ids) != len(set(disposition_finding_ids)):
        reasons.append("disposition finding_ids must be unique")

    return reasons


#: Registry of named payload schemas → Python validators (A21). New named schemas are
#: registered here AT MODULE-IMPORT time (never mutated at runtime — Wave-E test-isolation
#: nit). Per-schema JSON Schema files follow incrementally (Slice D). The Wave-E
#: ``audit`` workflow body seeds its
#: output-schema validators here so a test never has to register them at runtime:
#:
#: - audit:      scope → ``audit-scope-handoff-v1`` (summary), drift-scan review →
#:               ``audit-findings-handoff-v1`` (verdict), triage →
#:               ``audit-disposition-handoff-v1`` (summary — disposition-ready output).
#:               ``audit-report-v1`` is the collapsed single-step replacement (companion
#:               release): one payload carries ``{question, lenses[], findings[],
#:               dispositions[]}``; the three-step validators above stay registered for
#:               back-compat with any run still on the three-step sequence.
#: - implementation_reviews: the full implementation→review→closure ladder
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
    "generic-step-handoff-v1": _validate_generic_handoff,
    # Wave E — audit workflow body (T-30-E-01).
    "audit-scope-handoff-v1": _validate_audit_scope_handoff,
    "audit-findings-handoff-v1": _validate_audit_findings_handoff,
    "audit-disposition-handoff-v1": _validate_audit_disposition_handoff,
    # Companion release — collapsed single-step audit report.
    "audit-report-v1": _validate_audit_report_handoff,
    # v0.1.78 T-B / FR-B — full-pipeline (``LifecyclePipeline.run``) step payloads.
    "security-review-handoff-v1": _validate_review_verdict,
    "code-review-handoff-v1": _validate_review_verdict,
    # Combined single-review ladder (v0.2.x simplification): one tri-angle verdict.
    "combined-review-handoff-v1": _validate_review_verdict,
    "closure-handoff-v1": _validate_generic_handoff,
    "backlog-demand-v1": _validate_generic_handoff,
    "backlog-item-v1": _validate_generic_handoff,
}


_TRANSPORT_ONLY_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "agent",
        "context",
        "task_id",
        "release_id",
        "produced_at",
        "scope",
        "self_pull",
        "structured_output",
        "artifact",
        "artifact_refs",
        "handoff",
        "details",
    }
)
_WORKER_OUTPUT_PREFIX = ".dadaia/tmp/lifecycle-worker/"


def _first_domain_summary(value: object) -> str | None:
    """Return the first substantive summary-like string from a JSON domain object."""
    if not isinstance(value, dict):
        return None
    for key in ("summary", "core_problem", "verdict_reason"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    for candidate in value.values():
        nested = _first_domain_summary(candidate)
        if nested is not None:
            return nested
    return None


def durable_payload_from_result(
    result: AgentRunResult, *, fallback_summary: str, is_review: bool
) -> dict[str, object]:
    """Extract the substantive, durable domain handoff from one worker result.

    The transport document and its mandatory self-reference belong to the temporary
    worker-output plane. The immutable ledger receives the nested domain handoff (when
    present), or the transport document minus transport-only fields, plus only stable
    artifact references.
    """
    document = result.domain_payload
    nested = document.get("handoff")
    if not isinstance(nested, dict):
        nested = document.get("details")
    if not isinstance(nested, dict):
        nested = document.get("structured_output")
    # ONE unambiguous envelope (bug audit-fragment-schema-envelope-mismatch): the
    # fragments instruct workers to emit domain fields TOP-LEVEL in the result object,
    # so top-level non-transport fields are ALWAYS retained. A nested
    # handoff/details/structured_output dict keeps its historical authority — where BOTH
    # levels carry a key, the nested (structured-contract) value wins — but it never
    # ERASES a top-level field it does not itself carry, so a worker that obeyed the
    # fragment's top-level contract passes its gate.
    payload: dict[str, object] = {
        str(key): value for key, value in document.items() if key not in _TRANSPORT_ONLY_KEYS
    }
    if isinstance(nested, dict):
        payload.update({str(key): value for key, value in nested.items()})

    summary = _first_domain_summary(payload) or _first_domain_summary(document)
    if summary is None:
        summary = result.summary or fallback_summary
    payload["summary"] = summary

    if is_review:
        verdict = result.structured_output.get("verdict")
        if isinstance(verdict, str):
            payload["verdict"] = verdict
        reason = result.structured_output.get("verdict_reason")
        if isinstance(reason, str):
            payload["verdict_reason"] = reason
    findings_raw = result.structured_output.get("findings")
    if "findings" not in payload and isinstance(findings_raw, str) and findings_raw.strip():
        try:
            findings = json.loads(findings_raw)
        except json.JSONDecodeError:
            findings = None
        if isinstance(findings, list) and findings:
            payload["findings"] = findings

    stable_refs = [ref for ref in result.artifact_refs if not ref.startswith(_WORKER_OUTPUT_PREFIX)]
    artifact = document.get("artifact")
    artifact_path = artifact.get("path") if isinstance(artifact, dict) else None
    if (
        isinstance(artifact_path, str)
        and artifact_path
        and not artifact_path.startswith(_WORKER_OUTPUT_PREFIX)
    ):
        stable_refs.append(artifact_path)
    if stable_refs:
        payload["artifact_refs"] = list(dict.fromkeys(stable_refs))
    else:
        payload.pop("artifact_refs", None)
    return payload


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


def _compact_digest_text(value: str, *, limit: int = 320) -> str:
    """Collapse one domain value to a bounded single line for prompt injection."""
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


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
        # A validated-payload memo keyed by the addressable (run_id, producer_step,
        # attempt) — per-process, never persisted. ``produce()`` and the first
        # ``resolve_required()`` for a key populate it; every later ``resolve_required()``

    # -- restart (bug rerun-of-run-id-collides-with-immutable-payload-zone) ---

    def reset_run_zone(
        self,
        run_id: str,
        producer_steps: frozenset[str] | set[str] | None = None,
        *,
        worker_output_refs: tuple[str, ...] = (),
        context: str | None = None,
        release_id: str | None = None,
    ) -> int:
        """Reclaim a run's durable payloads and exact temporary worker outputs.

        Called by engines at run-creation time (fragment gate, pipeline, implement/review
        loop): the replaced run record discards the ledger that addressed these payloads,
        so the surviving files are unreferenced orphans that would block the new
        generation's ``attempt-0`` writes. In-run immutability is unchanged.
        *producer_steps* narrows the reclaim to the named steps (resume-from-step, bug
        blocked-definition-run-cannot-resume-from-step).

        *context* / *release_id* are optional (default ``None``) so every existing
        caller keeps working unchanged: when *context* is given AND the injected writer
        implements :class:`ReleaseAwareWorkflowStepPayloadWriter`, the release-aware zone
        is purged (``release_id=None`` means the backlog zone, matching
        :func:`_zone_release_id`); otherwise the legacy zone is purged exactly as before.
        """
        if context is not None and isinstance(self._writer, ReleaseAwareWorkflowStepPayloadWriter):
            removed = self._writer.purge_release_scoped_step_payloads(
                run_id, producer_steps, context=context, release_id=release_id
            )
        else:
            removed = self._writer.purge_step_payloads(run_id, producer_steps)
        return removed + self._writer.purge_worker_outputs(worker_output_refs)

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
        ref = self._write_payload(
            run, producer_step=producer_step, attempt=attempt, content=content
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
        audit_question = payload.get("audit_question")
        if isinstance(audit_question, str) and audit_question.strip():
            lines.append(f"- audit_question: {_compact_digest_text(audit_question)}")
        lenses = payload.get("lenses")
        if isinstance(lenses, list) and lenses:
            names = [
                item.get("name")
                for item in lenses
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            ]
            if names:
                lines.append(f"- lenses: {', '.join(str(name) for name in names)}")
        surfaces = payload.get("surfaces")
        if isinstance(surfaces, list) and surfaces:
            lines.append("- surfaces:")
            lines.extend(
                f"  - {_compact_digest_text(surface, limit=180)}"
                for surface in surfaces[:30]
                if isinstance(surface, str) and surface.strip()
            )
        criteria = payload.get("acceptance_criteria")
        if isinstance(criteria, list) and criteria:
            lines.append("- acceptance_criteria:")
            for criterion in criteria[:20]:
                if not isinstance(criterion, dict):
                    continue
                lens = criterion.get("lens")
                condition = criterion.get("pass_condition")
                if isinstance(lens, str) and isinstance(condition, str):
                    lines.append(f"  - {lens}: {_compact_digest_text(condition, limit=280)}")
        findings = payload.get("findings")
        if isinstance(findings, list) and findings:
            lines.append(f"- findings: {len(findings)}")
            for finding in findings[:20]:
                if isinstance(finding, dict):
                    sev = finding.get("severity", "?")
                    msg = finding.get("message", "")
                    finding_id = finding.get("id")
                    identity = (
                        f" (id: {finding_id})" if isinstance(finding_id, str) and finding_id else ""
                    )
                    lines.append(
                        f"  - [{sev}] {_compact_digest_text(str(msg), limit=240)}{identity}"
                    )
                    surface = finding.get("surface")
                    evidence = finding.get("evidence")
                    if isinstance(surface, str) and surface.strip():
                        lines.append(f"    surface: {_compact_digest_text(surface, limit=180)}")
                    if isinstance(evidence, str) and evidence.strip():
                        lines.append(f"    evidence: {_compact_digest_text(evidence, limit=300)}")
            if len(findings) > 20:
                lines.append("  - read the authoritative payload ref for all findings")
        refs = payload.get("artifact_refs")
        if isinstance(refs, list) and refs:
            lines.append(f"- artifact_refs: {', '.join(str(r) for r in refs)}")
        return "\n".join(lines)

    # -- internals ----------------------------------------------------------

    def recover_persisted_record(
        self, run: LifecycleRun, *, producer_step: str, attempt: int = 0
    ) -> tuple[LifecycleRun, WorkflowStepRecord] | None:
        """Re-admit a ledger record from its persisted immutable payload, if valid.

        Reconciliation for the interrupted-worker class (bug
        release-commit-gate-ignores-existing-plan-review-payload): a record lost from
        the in-memory ledger between resets/resumes is recovered from the durable
        payload file — Python-owned disk truth — after re-validating BOTH the envelope
        and the named payload schema. Returns ``None`` when the writer cannot look up
        by identity, no file exists, or validation fails (the gate then blocks as
        before).
        """
        reader = getattr(self._writer, "read_step_payload_by_identity", None)
        if reader is None:
            return None
        found = reader(
            run_id=run.run_id,
            producer_step=producer_step,
            attempt=attempt,
            context=run.context,
            release_id=_zone_release_id(run),
        )
        if found is None:
            return None
        payload_ref, content = found
        try:
            envelope = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(envelope, dict):
            return None
        try:
            self._validate_envelope(envelope)
            output_schema = str(envelope["output_schema"])
            self._require_known_schema(output_schema)
            payload = envelope["payload"]
            assert isinstance(payload, dict)
            self._validate_named_payload(output_schema, payload)
        except (MalformedHandoffError, KeyError, AssertionError):
            return None
        record = WorkflowStepRecord(
            run_id=run.run_id,
            producer_step=producer_step,
            attempt=attempt,
            output_schema=output_schema,
            payload_ref=payload_ref,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            produced_at=str(envelope.get("produced_at", "")),
            retention_mode=RetentionMode(
                str(envelope.get("retention_mode", "delete-after-consumed"))
            ),
            declared_consumers=tuple(str(c) for c in envelope.get("declared_consumers", [])),
        )
        updated = self._persist(run, run.workflow_steps.upsert(record))
        return updated, record

    def _write_payload(
        self, run: LifecycleRun, *, producer_step: str, attempt: int, content: str
    ) -> StepPayloadRef:
        """Write the envelope through the release-aware zone when the writer supports it.

        Probed via ``isinstance`` against :class:`ReleaseAwareWorkflowStepPayloadWriter`
        so every existing :class:`WorkflowStepPayloadWriter` adapter keeps writing to its
        current (legacy) zone unchanged until it implements the extension.
        """
        if isinstance(self._writer, ReleaseAwareWorkflowStepPayloadWriter):
            return self._writer.write_release_scoped_step_payload(
                run_id=run.run_id,
                producer_step=producer_step,
                attempt=attempt,
                content=content,
                context=run.context,
                release_id=_zone_release_id(run),
            )
        return self._writer.write_step_payload(
            run_id=run.run_id,
            producer_step=producer_step,
            attempt=attempt,
            content=content,
        )

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
    "ReleaseAwareWorkflowStepPayloadWriter",
    "WorkflowStepPayloadWriter",
    "durable_payload_from_result",
    "known_payload_schemas",
]
