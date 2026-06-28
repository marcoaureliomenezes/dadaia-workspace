---
name: lifecycle-review-blocked-json-drops-rejected-verdict-detail
status: Closed
severity: MEDIUM
reported: 2026-06-28
resolved_in: v0.1.34
surface: dadaia lifecycle review security --json / LifecycleAgentRunner
session_id: null
---

**Resolution (v0.1.34):** Review-step blocked states now distinguish a missing verdict
from an explicit non-approved verdict. When a worker emits `verdict: REJECTED`, the
blocked JSON reason is `agent result verdict REJECTED (expected APPROVED)` and
`blocked.detail` includes `actual_verdict` plus `verdict_reason` when present.

**Symptom:** A Codex-driven security review produced a valid security-reviewer handoff
with `verdict: REJECTED` and concrete findings, but the lifecycle command returned JSON
with reason `agent result missing APPROVED verdict` and empty detail. The operator-facing
workflow response looked like the verdict was absent even though the worker had made a
clear rejection decision.

**Repro:**
1. Run a review-phase lifecycle command whose worker emits a structured result with
   `verdict: REJECTED`.
2. Use `--json`.
3. Observe a blocked response that says `agent result missing APPROVED verdict` and omits
   the actual verdict/reason.

**Expected:** A rejected review must block, but the blocked state must preserve the actual
verdict and the worker's rejection reason so the operator can act without opening raw
handoff files.

**Root Cause:** `LifecycleAgentRunner._blocked_result` had one branch for every
non-`APPROVED` review result. It compared `structured_output["verdict"]` to `APPROVED`
and emitted the same generic "missing APPROVED verdict" block for both missing verdicts
and explicit `REJECTED` verdicts, with no detail extraction.

**Evidence:** Regression coverage:
`tests/integration/cli/test_lifecycle_pipeline_full.py::test_review_block_reports_rejected_verdict_detail`.

