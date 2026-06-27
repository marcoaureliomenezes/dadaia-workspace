---
release: v0.1.30
phase: DEFINITION
---

# Active release: v0.1.30 — super release: PI/Codex Layer-2 + workflow system maturation

Operator `/goal` 2026-06-27: a super release taking 6 correlated open backlog items
(new architecture / PI / Codex / 2nd agentic layer / workflows).

**Phase:** DEFINITION — **COMPLETE, awaiting operator go-ahead before IMPLEMENTATION** (D-4
define-only). SPEC/PLAN/TASKS Aprovado (30 tasks, waves A→E); `specs doctor` 0 errors.
DEFINITION review APPROVED: software-architect (0 crit/high; 5 MEDIUM impl-time advisories)
+ qa-engineer (0 crit; 1 HIGH = WS-PI-6 real-shape fixture obligation, verified
`~/.pi/agent/sessions/<dir-slug>/*.jsonl` exists). Review handoffs under
`.dadaia/handoff/dadaia-workspace/`.

Binding impl-time obligations (carry into the waves when implementation is authorized):
- Wave A: characterization baseline of all 3 adapter suites green BEFORE refactor; redaction
  parity parametrized across pi/codex/claude_sdk; security-reviewer pass on the hoisted
  secret-scrub + Ring-2 git-diff base before any Wave-B task consumes it.
- Wave B / WS-PI-6: fixture byte-faithful to a REAL `~/.pi/agent/sessions/<dir-slug>/*.jsonl`
  + recorded one-shot real-dir ingest (no invented shape); else close not-applicable w/ evidence.
- Wave D: write back-compat (old LifecycleRun loads) + retention live-run-safety
  (`preserves_live_run_step_payloads`, `reclaims_consumed_all_past_ttl`) FIRST, before producer code.
- Wave E: per-body fake-runtime e2e (role→fragments→selector→schema→gate, consuming D's ledger);
  ctx-inject dehydration prompt-composition test.
- Closure: pin the GH Actions `e2e-panel` job green (not run by `ci preflight`).
- Verify `lifecycle-prompt-fragments` frontmatter intents == {WS-A audit, WS-A research, WS-C}
  before the Consumes hook binds (drop WS-B if it's an open frontmatter intent).

Picked Core 6: shared-headless-adapter-base (foundation) · codex-runtime-fidelity ·
pi-agent-fourth-harness (WS-PI-6 only) · workflow-model-governance-operator-profiles-and-context-overlays ·
workflow-step-handoff-data-plane-cleanup (CRITICAL) · lifecycle-prompt-fragments-ai-surface-dehydration (CRITICAL).

Branch: `feature/v0.1.30` (off main @ ccb8885). Cadence: stop at approved SPEC/PLAN/TASKS +
DEFINITION review (architect + qa); do NOT implement until the operator approves the plan.
