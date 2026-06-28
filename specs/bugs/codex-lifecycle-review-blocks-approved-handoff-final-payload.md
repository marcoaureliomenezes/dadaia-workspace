---
name: codex-lifecycle-review-blocks-approved-handoff-final-payload
status: Closed
severity: HIGH
reported: 2026-06-28
resolved_in: v0.1.34
surface: dadaia lifecycle review security --harness codex / CodexExecAdapter result extraction
session_id: null
---

**Resolution (v0.1.34):** The shared headless result extractor now accepts a current
`handoff-v1.1` document as structural review evidence when it carries a top-level
`verdict` and a metrics/artifact path. Codex result flattening now forwards top-level
handoff `verdict`, `verdict_reason`, and `metrics.commit_sha` into
`AgentRunResult.structured_output`. Codex also recovers the newest matching handoff
written under `.dadaia/handoff/<context>/` during the run when the final assistant
message is prose instead of the result wrapper/handoff JSON.

**Symptom:** `dadaia lifecycle review security --harness codex --json` returned
`BLOCKED` with `agent result missing APPROVED verdict`, while the same run wrote a valid
security-reviewer handoff with top-level `verdict: APPROVED` and
`metrics.commit_sha` equal to the reviewed commit.

**Repro:**
1. Run a Codex Layer-2 security review where the worker writes a valid
   `.dadaia/handoff/<context>/*.handoff.json` and makes that handoff document the final
   assistant payload.
2. Observe the handoff top-level `verdict: APPROVED`.
3. Observe the lifecycle command still blocks as if the verdict were missing.

**Expected:** A review worker that emits a valid approving handoff document as its final
payload should satisfy the review gate. The runner must not require a duplicate
`agent-run-result-v1` wrapper when the handoff itself contains the verdict and artifact
reference.

**Root Cause:** `extract_result_payload` accepted only strict `agent-run-result-v1` or
structural payloads with top-level `artifact_refs`. A valid `handoff-v1.1` document has
top-level `verdict` but stores its artifact path under `metrics.artifact_ref` or
`artifact.path`, so the extractor rejected it. Codex then degraded to a successful result
with no `structured_output.verdict`, and the lifecycle review gate blocked.

**Evidence:** Regression coverage:
`tests/contract/test_headless_runtime_security.py::test_result_payload_extraction_accepts_only_current_result_contract`,
`tests/contract/test_headless_runtime_security.py::test_codex_handoff_final_payload_surfaces_review_verdict`,
and
`tests/contract/test_headless_runtime_security.py::test_codex_recovers_written_handoff_when_final_message_is_prose`.
