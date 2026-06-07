# SPEC: v0.1.5 rc-1 — session-semaphore + agent-specialization

**Status:** Aprovado
**Release ID:** v0.1.5
**Segment:** rc-1
**Owner:** product-engineer
**Created:** 2026-06-05
**Grill report:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-06-05T050955Z-refine-specs.html` (D1–D5 all resolved; mandatory grill gate satisfied)

---

## 1. Objective

Deliver five locked work-streams in a single `rc-1` segment of v0.1.5 to close the
deploy-blocker and deepen the workspace's agentic quality:

1. **R1** — Per-context implement+review semaphore + env-free runtime→session
   resolution + 3 deferred lock/TOCTOU fixes. Deploy-blocker. Lands first.
2. **D5** — Backlog-ownership enforcement: rule (PM authors backlog, PE consumes)
   + hard PreToolUse gate blocking non-PM writes to `specs/backlog/**`.
3. **R3** — Specialize the four dadaia-native agents (ai-engineer, product-engineer,
   project-manager, project-auditor). AI-entity surface only (craft, not engine).
   ai-engineer leads with a strategy document before any persona is touched.
4. **R4** — Audit + right-fit the remaining generic agents for over/under-fitting
   (audit-only; trims are a follow-on work-stream R4b if needed).
5. **D4** — Set `project-manager` model to `claude-opus-4-8` (alongside the R3 PM
   persona edit; no global default change).

This segment dogfoods the alpha/rc engine (T-ENG-03) that v0.1.5 itself delivered.

## 2. Context and background

v0.1.5 shipped the governance layer (bug/backlog→release rules, ADR-1..5, pre-push
CI gate, segment engine) and reached CLOSURE with all 20 tasks done. Deploy was held
because R1 (session semaphore) — the deploy-blocker — was deferred.

Operator decision 2026-06-05: reopen v0.1.5, absorb R1 + R3 + R4 + D4 + D5 into
an `rc-1` segment, ship once under a single v0.1.5 tag. The stacked 0.1.6/0.1.7
bundle plan (memory D1/D2) is superseded by this decision. v0.1.4.6
(harness-mastery) is delivered and archived — it is NOT a dependency of rc-1.

The "phantom backlog" `r2-lock-toctou-hardening-v1` never had a file; the 3 lock
races it described exist only as deferred items in `specs/backlog/candidates.md`
and are folded into R1 here. Nothing to retire.

## 3. Scope (in this segment)

### R1 — Session semaphore + env-free binding + 3 lock fixes (CRITICAL / deploy-blocker)

**Source:** `specs/backlog/session-orchestration-semaphore.md` + 3 items in
`specs/backlog/candidates.md`.

**Problem:** The SDD gate resolves session identity from `DADAIA_SESSION_ID` env var,
which a running agent process cannot self-inject or update mid-session. Phase changes
require a new bind → effective relaunch. This is an undeployable stop-the-flow
failure (reproduced on v0.1.4.6, 2026-06-04).

**Required changes:**

- **sdd-spec-gate.sh RULE E** — replace env-var-only session resolution with a
  runtime→session pointer lookup (e.g. a per-pid or per-session "current binding"
  file in `.dadaia/sessions/runtime/`). Gate must function without operator env export.
- **sdd-post-gate.sh** — align heartbeat renewal to renew both session file and lock
  (fixes candidates.md Bug C: heartbeat-doesn't-renew).
- **ctx-inject.sh** — register a runtime→session pointer at session start; clean up
  on session end.
- **Session model** (`.dadaia/sessions/*.json`, `.dadaia/states/ctx_locks/`) — add a
  per-context semaphore file `.dadaia/states/ctx_locks/<context>.lock` with fields:
  `owner`, `phase`, `release`, `write_set`, `acquired_at`, `ttl`, `heartbeat`.
  At most one active implement+review holder per context.
- **`dadaia context bind` CLI** — update bind to register the runtime→session pointer;
  phase progression does not require a new bind.
- **Lock glob (candidates.md multi-lock edge)** — narrow the glob in RULE E from
  `${CONTEXT_SLUG}__*.json` to `${CONTEXT_SLUG}__${ACTIVE_RELEASE}.json` (exact
  match on active release) to eliminate non-deterministic multi-lock adoption.
- **CONTEXT_SLUG sanitization (candidates.md CWE-22)** — strip non-alphanumeric
  except `-_` from `CONTEXT_SLUG` before use in path construction.
- **Doctor invariants** — `dadaia doctor` detects orphan/stale/duplicate context
  locks and runtime→session pointers; stale-reclaim with audit trail.
- **PM orchestration** — project-manager is the coordinator that acquires/holds/
  renews/releases the context semaphore; specialist agents run under the held lock.
  PM drives phase transitions without requiring rebind.

**Implementers:** `software-engineer-python` (CLI + session model + gate scripts),
`devops-engineer` (hook wiring + doctor invariants).

**Acceptance:**
- A single bind/launch carries a session through read → spec → implementation →
  review → closure with no relaunch and no manual re-export.
- Concurrent implement+review on the same spec context is impossible (semaphore);
  a second attempt is cleanly denied/queued with the holder identified.
- Gate functions with no operator env export; `dadaia doctor` detects stale/orphan
  locks; documented recovery for a crashed holder.
- E2E: two concurrent sessions on one context cannot both write production files.
- Heartbeat renews both session file and lock on every renewal point.
- CONTEXT_SLUG is sanitized before lock path construction.
- Multi-lock non-determinism is eliminated.

### D5 — Backlog-ownership enforcement

**Problem:** No enforcement prevents non-PM agents from creating backlog entries,
causing workflow drift (PM owns backlog creation; PE and specialists consume it).

**Required changes:**

- **New rule `backlog-ownership.md`** (always-on, `dadaia_workspace/public/rules/`)
  — declares: only `project-manager` creates entries in `specs/backlog/**`; all
  other agents are readers; `product-engineer` consumes PM-created backlog to create
  release specs but does not author backlog.
- **Hard PreToolUse gate** — extends existing gate infrastructure (mirroring the
  memory-atomicity gate pattern) to block writes to `specs/backlog/**` from any agent
  that is not `project-manager`. Block is enforced at the hook/gate layer, not just
  by convention.

**Implementer:** `ai-engineer` (rule craft + gate hook).

**Acceptance:**
- Any write attempt to `specs/backlog/**` by a non-PM agent is blocked at the gate
  with a clear error message naming the violating agent.
- `project-manager` can write to `specs/backlog/**` without restriction.
- Rule is projected and verified by `dadaia public doctor`.

### R3 — Four dadaia-native agent specialization (AI-entity craft)

**Source:** `specs/backlog/dadaia-agent-specialization.md` (FEAT-DADAIA-AGENTS-01).

**Scope:** AI-entity surface only (personas, skills, rules). No Python code changes.
v0.1.4.6 (R2 in the original train table) is DONE+archived — not a dependency.

**Required first step:** `ai-engineer` must produce a **strategy document** answering:
- Which skills are thin vs. need new dedicated skills?
- What goes in each persona vs. referenced skill vs. rule?
- Which process rules (backlog ownership, release-definition flow, review gate) are
  best as always-on rules vs. skill content vs. persona inline?
- Minimum edit to each persona that achieves acceptance without adding noise.
- How the four personas + skills cross-reference each other and existing skills.

PM reviews and accepts the strategy before any persona is touched.

**Agent-specific scope:**

**product-engineer:**
- Explicitly states "consumes PM-created backlog; does not author backlog."
- Embeds the spec lifecycle (DISCOVERY→SPEC→PLAN→TASKS→IMPLEMENTATION→CLOSURE→
  ARCHIVED) with a phase-to-action mapping.
- References `dadaia-step0-memory-bootstrap`, `dadaia-workspace-spec-navigator`,
  `dadaia-release-closure` as governing skills.
- Embeds a clear mental model of the memory system (constitution + memory as project
  soul; `catalog.json` + per-feature atoms as tailing mechanism).

**project-manager:**
- Opens with explicit "Owner of backlog creation" statement.
- States grill-me as mandatory before dispatching when demand is ambiguous or scope
  unconfirmed.
- Encodes the review-gate protocol (no `[x]`, no PR, no push, no deploy, no CLOSURE
  without qa-engineer + code-reviewer + security-reviewer approval) as a hard rule.
- (D4) `model: claude-opus-4-8` in frontmatter — only project-manager; others unchanged.

**project-auditor:**
- Peer to PM, operator-triggered, NOT dispatched by PM as a leaf specialist in
  normal flow.
- Dispatch authority: can spawn (code-reviewer, security-reviewer, software-architect,
  qa-engineer, researcher) to gather positions; does not implement or change specs.
- Scoring model defined: dimensions + criticality scale.
- Constitution + memory catalog as primary audit anchors.
- Emits a scored report with improvement aspects and criticality levels.

**ai-engineer:**
- Sharpened around AI-entity surface ownership (agents, skills, rules, workflows,
  commands, hooks).
- Carries the harness-mastery synthesis workload (per v0.1.4.6 delivery).
- Clear boundary: does not author backlog, does not write product specs.

**Anti-slop constraint (hard):** No giant prompts. Direct, objective instructions.
Smart cross-references (cite skill/rule names, not re-explain their content).
Every persona edit reviewed for (a) no redundancy with referenced skills/rules,
(b) no over-explanation of things that belong in referenced docs,
(c) every instruction actionable and necessary.

**Implementer:** `ai-engineer` (strategy first, then persona/skill edits).

**Acceptance:**
- Strategy document produced and PM-accepted before any persona edit.
- All four personas and any new skills/rules pass `dadaia public doctor` exit 0.
- Persona projections verified manually in `.claude/agents/` + `.codex/agents/`.
- No redundancy with referenced skills/rules in any persona.

### R4 — Generic-agent audit (audit-only)

**Source:** `specs/backlog/dadaia-agent-specialization.md` §6 (FEAT-OTHER-AGENTS-AUDIT-01).

**Scope:** Audit pass only. Every agent OTHER than the four dadaia-specific ones is
audited for over/under-fitting to dadaia internals. Trims (if needed) are a
follow-on work-stream (R4b) scoped after R4 audit is reviewed and accepted.

**Audit output:** scored report — which agents have non-generic content, what to
trim, what to generalize, with file:line citations.

**Implementer:** `ai-engineer` (audit read-only; no persona edits in R4).

**Acceptance:**
- Audit report covers all non-dadaia-specific agents.
- Findings are filed by severity with citations.
- No persona or skill file is modified in R4 (audit-only).

### D4 — project-manager model upgrade

**Decision (operator-confirmed):** `project-manager` persona → `model: claude-opus-4-8`.
No other agent's model changes. Add `MODEL_MAP` entry in projection code if missing.

**Implementer:** `ai-engineer` (alongside R3 PM persona edit — same file touch).

**Acceptance:**
- `project-manager.md` source has `model: claude-opus-4-8`.
- Projection in `.claude/agents/project-manager.md` reflects the model.
- Codex projection in `.codex/agents/project-manager.toml` reflects the model.
- No other agent model changes.

## 4. Out of scope for rc-1

- Python implementation changes beyond R1 session model / gate scripts (no feature
  surface changes unrelated to R1).
- R4b (generic-agent trims) — depends on R4 audit results; separate work-stream.
- Memory atom updates — CLOSURE phase only (per workspace-protocol §5).
- BUG-PANEL-REPORTS-01 (reports tab regression) — backlog; separate release.
- ai-harness-opencode skill — backlog (deferred from v0.1.4.6).
- Any changes to the `dadaia public` asset chain beyond what R1/D5/R3/R4/D4 require.

## 5. Acceptance (segment-level)

- **R1:** Single-launch, env-free phase-through implemented and verified E2E.
- **D5:** Hard backlog write-gate enforced and verified (non-PM write blocked).
- **R3:** Four dadaia agents specialized; `dadaia public doctor` exit 0; projections
  verified; no anti-slop violations; strategy document PM-accepted.
- **R4:** Audit report complete with cited findings; no persona edits in R4.
- **D4:** PM model is `claude-opus-4-8` in source + both projections.
- **Pre-push CI gate:** `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`
  all green locally before any push on this segment.
- **End of rc-1 ship gate:** `qa-engineer` + `code-reviewer` + `security-reviewer` all
  APPROVE → push `feature/0.1.5` → PR → merge → CLOSURE → tag v0.1.5 → publish.

## 6. Decisions inherited from grill session (ADRs)

| ADR | Decision | Source |
|---|---|---|
| rc-1-scope | Reopen v0.1.5, rc-1 absorbs R1+R3+R4+D4+D5; one tag | Operator (2026-06-05) |
| r2-delivered | v0.1.4.6 is DONE+archived, not a dependency of rc-1 | Inspection |
| d4-narrow | Only project-manager → opus-4-8; global default unchanged | Operator |
| d5-hard-gate | Block non-PM writes to specs/backlog/** at gate layer | Operator |
| d3-fold | 3 lock candidates fold into R1; no phantom backlog file to retire | Inspection |
