---
name: lifecycle-prompt-names-two-schemas-confusing-real-workers
status: Open
severity: MEDIUM
reported: 2026-06-27
surface: features/lifecycle/prompt_builder.py (envelope + PromptScope.expected_schema), public/lifecycle_fragments/shared/output-handoff.md
session_id: null
---

> **Origin:** recorded as the C-02 residual of release v0.1.31 (make the dadaia-workflows run
> on a real Layer-2 worker). The real-worker e2e is GREEN via an extractor hardening
> (`pi_runtime._verdict_payload` now accepts bare JSON + structural acceptance); this bug is
> the *prompt-side* root cause that the hardening tolerates rather than fixes.

**Symptom:** A real `pi`/Codex Layer-2 worker is told to emit its step result against **two
different schema names** and labels the result inconsistently across runs, so a strict
`schema`-field equality check drops a correct payload. Observed live on `release_scope`
(gpt-5.5), two consecutive runs:
- run 1: top-level `"schema": "agent-run-result-v1"` (the transport schema — matched);
- run 2: NO top-level `schema`; instead `"output_schema": "release-scope-handoff-v1"` nested
  inside `structured_output` (the fragment's domain schema — did NOT match).

Both payloads were otherwise correct (non-empty `artifact_refs`, `status`, `verdict`).

**Root cause:** the prompt presents two schema identifiers:
- `prompt_builder.PromptScope.expected_schema` defaults to `"agent-run-result-v1"` (the
  transport/result-object schema the extractor checks); and
- the per-step fragment declares its own `output_schema` (e.g. `release-scope-handoff-v1`),
  which the envelope text also surfaces to the worker
  (`prompt_builder.py:~72` "conforms to the output schema `{bundle.output_schema}`").
The worker sees both and can't reliably decide which to put in the `schema` field. The
extractor (`_verdict_payload`) historically required `payload["schema"] == expected_schema`
exactly, so a domain-schema-labelled (or unlabelled) result was silently dropped → the step
BLOCKed with "agent result missing artifact evidence".

**Repro:** run the v0.1.31 real-worker e2e against the strict (pre-hardening) extractor:
```
DADAIA_E2E_REAL_WORKER=1 PI_BIN="$(command -v pi)" \
  .dadaia/.venv/bin/pytest -q tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py
# pre-hardening: BLOCKED release_scope "agent result missing artifact evidence"
```

**Expected / fix direction:** disambiguate the prompt so the worker is told exactly ONE
`schema` value to emit, and make `expected_schema` per-step consistent with what the envelope
instructs. Either (a) thread the fragment's `output_schema` through as the single
`expected_schema` and instruct the worker to put *that* in the `schema` field; or (b) keep
`agent-run-result-v1` as the transport and stop surfacing the fragment `output_schema` as a
second "schema" to emit (carry it only as an internal field). Then the strict equality check
can be restored and the structural-tolerance fallback in `_verdict_payload` becomes
defence-in-depth rather than the primary path.

**Notes:** No secrets/operator-local paths. The v0.1.31 extractor hardening
(`_verdict_payload` accepts fenced OR bare JSON, and accepts a structurally-valid result
object regardless of the `schema` label) keeps the real-worker chain green today; this bug
tracks fixing the prompt so worker compliance no longer *depends* on that tolerance. Apply
the same disambiguation to the Codex extractor for parity.
