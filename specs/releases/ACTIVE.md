---
release: v0.1.30
phase: CLOSURE
---

# Active release: v0.1.30 — super release: PI/Codex Layer-2 + workflow system maturation

Operator `/goal` 2026-06-27: a super release taking 6 correlated open backlog items
(new architecture / PI / Codex / 2nd agentic layer / workflows).

**Phase:** IMPLEMENTATION — operator `/goal` 2026-06-27 authorized "implement, test and review
in sequence waves A, B, C, D and E" (D-4 define-only checkpoint released). SPEC/PLAN/TASKS
Aprovado (30 tasks, waves A→E); `specs doctor` 0 errors. DEFINITION review APPROVED:
software-architect (0 crit/high; 5 MEDIUM impl-time advisories) + qa-engineer (0 crit; 1 HIGH
= WS-PI-6 real-shape fixture obligation, verified `~/.pi/agent/sessions/<dir-slug>/*.jsonl`
exists). Review handoffs under `.dadaia/handoff/dadaia-workspace/`.

**Cadence:** one software-engineer per wave (sequential — snapshot-guard forbids repo-writes
concurrent with pytest), each wave green-checkpointed (ruff/mypy/pytest/import-linter) then
reviewed (qa-engineer + code-reviewer) before the next wave starts.

**STATUS 2026-06-27 — ALL 5 WAVES IMPLEMENTED + TESTED + REVIEWED (30/30 tasks `[x]`).**
Full suite 4047 passed / 14 skipped; `mypy --strict` clean (288 files); ruff format+check
green; `public doctor` exit 0 (`[ok] public-privacy`, `[ok] ai-surface`, `[ok]
codex:rule-corpus-reachable`); `specs doctor` 0 errors; panel Playwright e2e 69/69 green
locally (A12 PI surface + handler route changes). Per-wave reviews ALL APPROVE:
A (security+code), B (security+code), C (security+code), D (security+qa+code), E
(security+qa+code). Substantive review findings fixed inline (Wave-A dead import; Wave-B A12
panel wiring + CSP hash + PI styling; Wave-C overlay to_dict 3-map-union bug; Wave-D
is_cleanup_eligible retention-mode data-loss path + real-provider retention test; Wave-E
graph-completeness gate test + fragment READMEs). Bugs filed:
import-linter-contracts-red-but-not-ci-enforced (Open), backlog-doctor-blocks-consumed-item-refactor-commit
(Open), overlay-todict-drops-harness-only-workflow (Closed, fixed in C). NOT pushed (operator
ship decision pending). NOT yet run: CLOSURE (T-30-Z-01) — memory atoms, disposition sweep
(flip the 5 `**Consumes:**` items to terminal tokens — see specs doctor SPEC-DOC-031 warns),
archive, PR/merge. Deferred review LOWs (research second-hop test, doctor symlink-rglob
robustness, doctor UNCONSUMED_REQUIRED FAILED-scoping) recorded in review handoffs for the
closure nit-sweep.

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
