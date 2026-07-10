---
name: lifecycle-pipeline-correctness-and-diagnosability
status: candidate
opened: 2026-07-10
owner: project-manager (curates)
priority: P1
source: "2026-07-10 remote-user bug intake (4 HIGH lifecycle bugs) consolidated with the three open lifecycle backlog entries (`preflight-block-reasons-missing-operator-command`, `implement-review-write-scope-from-tasks-parity`, `tasks-write-scope-traversal-hardening` — operator-ratified fold 2026-07-10): one feature family, one entry"
absorbs:
  - bug: single-implement-verb-gated-as-review (HIGH, open)
  - bug: full-pipeline-success-persists-running-empty-ledger (HIGH, open)
  - bug: split-cleanup-engines-strand-stale-step-payloads (HIGH, open)
  - bug: worker-noncompliance-block-carries-no-diagnostic-evidence (HIGH, open)
  - backlog: preflight-block-reasons-missing-operator-command (superseded)
  - backlog: implement-review-write-scope-from-tasks-parity (superseded)
  - backlog: tasks-write-scope-traversal-hardening (superseded)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/cli/commands/lifecycle.py#implement" }
    change: "step kind becomes EXPLICIT, independent of transition target (bug `single-implement-verb-gated-as-review`): today the standalone `lifecycle implement` verb targets QA_REVIEW so is_review_phase(target_phase) (lifecycle.py:925, phase_workflow.py) classifies the CREATE step as review and the runner demands structured_output.verdict==APPROVED — a SUCCEEDED create result with artifact_refs and no self-verdict is blocked 'agent result missing APPROVED verdict'. Model an is_review/StepKind flag like PipelineStep.is_review already does (pipeline.py:102): implement/close are is_review=False, review verbs True. The existing test that ASSERTS the bug as the contract (test_lifecycle_command_skeletons) is flipped to the corrected truth, never ratified."
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/pipeline.py#LifecyclePipeline" }
    change: "CLI success and persisted terminal state become ATOMIC (bug `full-pipeline-success-persists-running-empty-ledger`): the full pipeline returns completed:true but never transitions the persisted LifecycleRun — status stays 'running' with empty workflow_steps (pipeline.py:234-304 has no terminal replace(status=COMPLETED)+save; implement-review has it at pipeline.py:418-419), and full-pipeline workers bypass WorkflowHandoffResolver so no per-step payloads exist for handoff doctor to verify. Fix: terminal COMPLETED save before returning (save failure fails the command); the full ladder produces run-scoped step payloads exactly like implement-review."
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/service.py#LifecyclePreflightService" }
    change: "ONE canonical cleanup contract (bug `split-cleanup-engines-strand-stale-step-payloads`) + actionable block reasons (absorbed backlog `preflight-block-reasons`): today `hygiene clean` scans only reports/handoff/tmp (SlopPolicy.safe_zones) while RetentionSweep owns .dadaia/runs step payloads — handoffs doctor flags a consumed payload past TTL but preflight's printed remediation is the engine that cannot see the file; the operator follows the official remediation, gets success, stays blocked. Fix: hygiene clean delegates to (or aliases) the retention sweep; status/preflight-remediation/doctor/dry-run/apply share one candidate classifier; safety gates preserved, doctor not weakened. Plus: the seven preflight block sites that default operator_command=None (wrong bound context :310, wrong bound release :312, active release mismatch :326, phase mismatch :328, lease mode mismatch :366, live foreign holder :368, required handoff gate failed :416 — re-verified 2026-07-10) each gain the exact remediation command, with an executed-path test asserting every blocked reason carries a non-null operator_command."
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/agent_runner.py#LifecycleAgentRunner" }
    change: "every real worker attempt persists ONE redacted run-scoped diagnostic (bug `worker-noncompliance-block-carries-no-diagnostic-evidence`): today a noncompliant worker (e.g. PI/kimi returning malformed prose, no agent-run-result-v1) collapses to the generic 'agent result missing artifact evidence' block with NOTHING persisted — the adapter maps zero-exit/no-result to SUCCEEDED+empty refs (pi_runtime.py:202-249) and the runner discards the summary (agent_runner.py:200-215); the operator cannot tell prompt vs model vs adapter vs config failure. Fix: persist a diagnostic (runtime, model, requested/actual reasoning, exit, parser classification, redacted output tail, session ref) referenced from BlockedState.detail; a no-op result still blocks. SECOND defect same family: PiHeadlessConfig.reasoning_effort is never forwarded — wire it to PI's --thinking flag (PI >= 0.80.3) and verify requested==actual in the run record."
  - subject: { kind: code, ref: "dadaia_workspace/cli/commands/lifecycle.py#implement_review" }
    change: "write-scope parity + parser hardening (absorbed backlog entries `implement-review-write-scope-from-tasks-parity` + `tasks-write-scope-traversal-hardening`): extend the v0.1.68 FR3 TASKS.md write-scope derivation to the `implement-review` verb (today write_scope_from_tasks is wired only at the pipeline verb, lifecycle.py:1896 — implement-review under-scopes its implement worker exactly as pipeline did pre-v0.1.68) plus a --write-scope escape hatch for parity; and harden tasks_write_scope.py#_extract_globs to reject at parse time any glob token that is absolute (leading /), contains a `..` segment, or begins with ~/$ (defense-in-depth — inert today because allowed_paths only feeds the advisory scope check, but the parser must not silently widen scope if matching ever gains real glob semantics). Executed-path tests: implement-review derives the reserved task's Write-set globs with no flag; each rejected token maps to no captured glob; frozen FR3 grammar tests stay green."
---

# BACKLOG — Lifecycle pipeline correctness & diagnosability (P1)

**Priority: P1.** One consolidated entry for the lifecycle feature family: the four HIGH
remote-user bugs (mis-gated `implement` verb; non-atomic pipeline terminal state; split
cleanup engines whose official remediation cannot fix what doctor demands; zero-evidence
worker-noncompliance blocks + PI `--thinking` unwired) plus the three lifecycle backlog
follow-ups they sit next to (seven null `operator_command` preflight sites,
`implement-review` write-scope parity, write-scope parser traversal hardening).

**Why one entry:** every anchor lives in `features/lifecycle/` +
`cli/commands/lifecycle.py`; the bugs and the backlog items share the same contract
theme — *the lifecycle engine must tell the truth (persisted state == reported state)
and every block must carry evidence + the exact next command*. One SPEC/review pass over
one surface beats four.

**Disposition note:** resolving this entry dispositions all four HIGH bugs
(`single-implement-verb-gated-as-review`,
`full-pipeline-success-persists-running-empty-ledger`,
`split-cleanup-engines-strand-stale-step-payloads`,
`worker-noncompliance-block-carries-no-diagnostic-evidence`) with
`--resolution-evidence`, per the never-silently-dropped law.
