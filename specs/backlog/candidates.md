# Backlog candidates

Surfaced issues awaiting triage into a release. Newest first.

## FEAT-LIFECYCLE-WORKFLOW-BODIES-01 — Python workflow bodies over lifecycle foundation (HIGH)

**Reported:** 2026-06-20 at v0.1.15 CLOSURE.

The v0.1.15 release shipped the deterministic lifecycle foundation: state machine, run
store, hygiene policy, report workflow proof, semantic gates, blocked/resume, prompt
scope builder, and Codex exec adapter. The next step is to implement the actual
workflow bodies as reusable Python routines: backlog definition, release definition and
review, implementation + QA/security/code-review gates, closure/archive, report writing,
handoff emission, and memory updates. These routines should call bounded agent runtimes
through `AgentRuntimePort` and advance only through Python validation.

**Status:** CANDIDATE — not picked. Requires operator pick and mandatory grill.

---

## FEAT-GOVERNANCE-V2-REMAINDER-01 — Remaining SDD governance-v2 scope (HIGH)

**Reported:** 2026-06-20 at v0.1.15 CLOSURE.

`specs/backlog/sdd-governance-v2-agents-lifecycle.md` was consumed by v0.1.15 only for
the Codex deterministic lifecycle foundation slice. The broader governance-v2 scope
remains open for a future release: roster/taxonomy updates, researcher relay,
JSONL/event-sourced bug telemetry, archive-class gate changes, and associated public
asset/persona/rule projection parity.

**Status:** CANDIDATE — not picked. Requires operator pick and mandatory grill.

---

> **Curated 2026-06-09 under release v0.1.9 (audit remediation).** The stale
> "Priority index (2026-06-06)" and the dead per-release lock-glob / semaphore /
> agent-specialization / panel-reports tracking entries were removed: they
> referenced shipped or archived releases (v0.1.5, 0.1.6, 0.1.8, v0.2.0, v0.2.1,
> v0.2.2 are all archived/done) and removed architecture (RULE-E, the per-release
> implementation lock, the per-context semaphore — all retired in v0.1.6). Only
> genuinely-open candidates remain below. Current active release: **v0.1.9**.

## FEAT-LIFECYCLE-ENGINE-ANTISLOP-01 — SDK-Driven Multi-Harness SDD Lifecycle Engine + Anti-Slop Subsystem (HIGH)

**Reported:** 2026-06-18 (operator deep-analysis session). **Full source:**
`specs/backlog/sdk-lifecycle-engine-multiharness-antislop.md`.

A deterministic, SDK-driven, multi-harness (Codex/Claude/OpenCode) SDD **lifecycle engine**
— the dadaia Python CLI owns lifecycle state/transitions/typed-gates; harnesses are bounded
workers behind one `AgentRuntimePort` — with **anti-slop as a first-class subsystem**. The
operator's two demands (SDK-driven workflows AND ending the slop war) are ONE fix: cleanup is
the same "no deterministic transition owner" defect. One-shot release IN scope = single TTL home
+ directory-aware slop metric + liveness-gated transition-owned `RetentionSweep` (reclaims the
live 12 GB) + `allocate_tmp` + `AgentRuntimePort` + rings 2/3 write-boundary diff-inspection +
one typed handoff-gate (Codex adapter first). DEFERRED = ClaudeAdapter/OpenCodeAdapter, full
state machines, transition shadow→enforce, AI-surface reduction. **Builds on**
`deterministic-lifecycle-kernel-v0114`; **narrows** `harness-agentic-entities-and-determinism-parity`;
cross-refs `sdd-governance-v2-agents-lifecycle` (the LAW; sequence engine after v0.1.15) and
`model-tier-efficiency-and-fast-tier-utilization`.

**Status:** CANDIDATE — NOT yet picked. Needs operator pick + MANDATORY `dadaia-grill-me` before
product-engineer authors SPEC. QA BLOCKER: zero archived handoffs → shadow corpus must be
synthesized + co-archived (see full source §7).

---

## BACKLOG-V0111-AUDIT-RESIDUALS — v0.1.10 re-audit residual list (MEDIUM, ranked)

**Reported:** 2026-06-10 at v0.1.10 CLOSURE. **Full source:** `specs/backlog/v0.1.11-audit-residuals.md`.

The 10 ranked residuals from the final v0.1.10 re-audit (`specs/audits/2026-06-10T052944Z/index.md` §5, verdict SHIP 9.0/10): probe-less CLI side doors (`lock steal`/`lease._main`), lifecycle-asymmetry mechanical enforcement, bind-record GC decay, session-path ownership residue, panel `?token=` launch URL, ctx-inject bootstrap bloat, public-source hygiene, doc nits, venv tooling bumps, time-earned WARN cleanups. **Status:** DELIVERED — v0.1.11 (picked 2026-06-10; shipped + archived; R9 partially DEFERRED to an operator command, R10 escape axis out of scope per ADR-3 — see `specs/_archive/releases/v0.1.11/CLOSURE.md` and the full-source file).

---

## BACKLOG-LEASE-SHELL-GAP — Lease does not mediate shell/CLI writes (MEDIUM)

**Reported:** 2026-06-09 (grill ADR-3, deferred from 0.1.7 rc-4). **Full source:** `specs/backlog/lease-shell-write-coverage-gap.md`.

The single-session lease is enforced only on agent Write/Edit tools; `Bash`/CLI writes bypass it. Closing it needs its own design+grill (must not break legitimate git/shell use). **Status:** OPEN — candidate.

---

## FEAT-XPLAT-OS-COMPAT-01 — Cross-Platform OS Compatibility (Linux/Windows/macOS) (HIGH)

**Reported:** 2026-06-08 (operator-commissioned 4-lens architectural review:
software-architect + software-engineer + qa-engineer + security-reviewer); deepened 2026-06-09 by
an 18-agent foundation-first architecture blueprint (platform seam, layering law, 3-tier
resilience, full ADD/UPDATE/DELETE/MOVE ledger).

**Surface:** The Python implementation's OS-layer surfaces — file locking, file permissions,
process-liveness probe, signal handling, venv paths, `/proc` scan, bash governance hooks — plus
the PyPI classifier and the CI matrix.

**Core defect:** dadaia-workspace ships the PyPI classifier `Operating System :: OS Independent`
but is **not importable on Windows at all** (`import fcntl` unconditional at module top-level in
`features/spec_context/locking.py:21` and `features/telemetry/service.py:25` → `ModuleNotFoundError`
before any command runs). The codebase has **zero** platform guards across 400+ source files; the
security model (`chmod 0o600/0o700`) silently no-ops on Windows (CWE-732); the entire bash-only SDD
governance hook layer is dead on stock Windows; and CI is 100% `ubuntu-latest`, so none of it is
caught before a release. 14 findings (3 CRITICAL / 8 HIGH / 2 MEDIUM / 1 LOW), 9 ordered
workstreams, a 6-phase rollout (honest-labeling first → restore classifier last), a phased
three-OS CI matrix, and a port/adapter abstraction plan.

**Full source (self-contained):** `specs/backlog/cross-platform-os-compatibility.md` (+ companion `specs/backlog/cross-platform-os-compatibility-ledger.md` for the long-form ADD-39/UPDATE-62/DELETE-8/MOVE-4 ledger, 49-module rewrite map, and dead-code kill list).

**Status:** CANDIDATE — NOT yet picked. Needs operator pick + MANDATORY `dadaia-grill-me` before
`product-engineer` authors a release SPEC. All fixes are production edits requiring an approved SDD
gate; nothing is authorized by this candidate.

> **Curator note (2026-06-09):** the CRITICAL Windows-importability defect was
> substantially addressed by the now-archived **v0.1.8** cross-platform release
> (platform seam, port/adapters, 3-OS CI matrix, classifier broadened). Re-verify
> the remaining HIGH/MEDIUM findings against shipped v0.1.8 before any re-pick.

---

## EPIC-HARNESS-AGENTIC-PARITY — Harness Agentic Entities & Determinism Parity (HIGH)

**Reported:** 2026-06-09. **Full source:**
`specs/backlog/harness-agentic-entities-and-determinism-parity.md`.

Cross-harness agentic-entity model (identity / role / dispatch authority) + deterministic
enforcement parity + an end-to-end `project-manager`-coordinator flow on each harness with no
operator env manipulation. Preserves the 0.1.7 rc-3 law (no workflow lock; the single-session
lease is the only lock). Previously blocked by the persona gate; registered after rc-3 removed
that lock (its creation is the rc-3 end-to-end proof).

**Status:** OPEN — candidate; **narrowed 2026-06-18** — the active enforcement-parity + dispatch +
agentic-entity-model scope is concretized/superseded by `sdk-lifecycle-engine-multiharness-antislop.md`
(FEAT-LIFECYCLE-ENGINE-ANTISLOP-01). Remaining here: advisory identity telemetry + OpenCode shim.

---

## HOTFIX-CODEX-CTX-WORKFLOW-001 — Codex Context Hook and Workflow Enforcement Hotfix (CRITICAL)

**Reported:** 2026-06-07 (operator escalation during Codex session).

**Surface:** Codex `UserPromptSubmit` hooks, `ctx-inject.sh`, Claude/OpenCode hook parity,
context-engineering memory bootstrap, and deterministic dadaia workflow routing.

**Core defect:** Codex visibly prints the full workspace memory bootstrap on every prompt
because `ctx-inject.sh` falls back to a per-hook shell PID sentinel instead of a stable
Codex logical-session id. The same incident exposed a second workflow defect: Codex did not
deterministically route through the expected dadaia multi-agent workflow until the operator
challenged it.

**Full source:** `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md`.

**Source bugs:**
- `specs/bugs/repeated-visible-userpromptsubmit-memory-injection.md`
- `specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md`

**Status:** OPEN — urgent hotfix candidate. Should be picked before broader Codex parity
work if the operator wants to stop the per-prompt UX/token/attention damage immediately.

---

## FEAT-CODEX-COMPAT-100 — Full Codex Compatibility (CRITICAL)

**Reported:** 2026-06-07 (operator directive after Codex operability audit).

**Surface:** Codex runtime projection and compatibility across agents, hooks, skills,
rules, workflows, AGENTS.md, public doctor, and tests.

**Core defect:** dadaia-workspace has real Codex projection files, but they are not yet
100% first-class Codex-compatible. The audit found a critical generated-agent corruption
(`ai-harness-claude-code` → fake `ai-harness-gpt-5.3-codex`), Markdown protocol docs
projected under a path that looks like executable Codex Rules, stale Claude path references
inside generated Codex personas, stale subagent/orchestration memory, and no live Codex hook
smoke test.

**Full source:** `specs/backlog/full-codex-compatibility.md`.

**Evidence:** `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-07T152643Z-codex-operability-audit.html`
and `.dadaia/handoff/dadaia-workspace/2026-06-07T152643Z-ai-engineer-codex-operability-audit.handoff.json`.

**Status:** OPEN — should become a dedicated release after PM/product-engineer grill and
SPEC/PLAN/TASKS approval.

---

## ai-harness-opencode skill (deferred from v0.1.4.6)

ai-harness-opencode skill — compiled mental model + decision protocols for opencode runtime
(deferred from v0.1.4.6 pending opencode runtime stability).

**Status:** OPEN — deferred candidate, pending opencode runtime stability.
