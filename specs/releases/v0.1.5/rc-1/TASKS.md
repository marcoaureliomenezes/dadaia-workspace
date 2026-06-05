# TASKS: v0.1.5 rc-1 — session-semaphore + agent-specialization

**Status:** Aprovado
**Release ID:** v0.1.5
**Segment:** rc-1
**Owner:** product-engineer
**Created:** 2026-06-05

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Group G1 — R1: Session semaphore + env-free binding + 3 lock fixes

### T-R1-01 — Design and implement runtime→session pointer (env-free resolution)

- **Status:** [x]
- **Owner:** software-engineer-python
- **Write set:**
  - `dadaia_workspace/public/scripts/ctx-inject.sh`
  - `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (RULE E update)
  - `.dadaia/sessions/runtime/` directory (new runtime pointer storage)
- **Acceptance:**
  - `ctx-inject.sh` writes a `.dadaia/sessions/runtime/<session_id>.ptr` file at session start and cleans up on end.
  - RULE E resolves session via: env var → runtime ptr file → deny (no rebind required).
  - Gate functions without `DADAIA_SESSION_ID` being manually exported.
  - Unit tests: env path, ptr-file path, deny path all covered.
- **Dependencies:** none (first task)

### T-R1-02 — Implement per-context semaphore (ctx_locks)

- **Status:** [x]
- **Owner:** software-engineer-python
- **Write set:**
  - `dadaia_workspace/features/specs/` — lock acquire/renew/release logic
  - `dadaia_workspace/core/models/spec_context.py` — lock model fields
  - `.dadaia/states/ctx_locks/<context>.lock` schema
- **Acceptance:**
  - Per-context lock file `<context>.lock` with fields: `owner`, `phase`, `release`, `write_set`, `acquired_at`, `ttl`, `heartbeat`.
  - At most one active implement+review holder per context; a second bind attempt is denied/queued with the holder identified.
  - read/spec phases are never blocked by the semaphore.
  - Unit tests: acquire, renew, release, deny-second-holder, read-not-blocked.
- **Dependencies:** T-R1-01

### T-R1-03 — Fix heartbeat renewal (Bug C — both session file and lock)

- **Status:** [x]
- **Owner:** software-engineer-python
- **Write set:** `dadaia_workspace/public/scripts/sdd-post-gate.sh`
- **Acceptance:**
  - `sdd-post-gate.sh` heartbeat renews both the session file (`last_seen_at`) and the context lock (`heartbeat`).
  - Unit test: after heartbeat call, both files show updated timestamp.
- **Dependencies:** T-R1-02

### T-R1-04 — Fix multi-lock non-determinism (narrow glob) and CONTEXT_SLUG sanitization

- **Status:** [x]
- **Owner:** software-engineer-python
- **Write set:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (RULE E lock lookup)
- **Acceptance:**
  - Glob narrowed from `${CONTEXT_SLUG}__*.json` to `${CONTEXT_SLUG}__${ACTIVE_RELEASE}.json`.
  - `CONTEXT_SLUG` sanitized (strip non-alphanumeric except `-_`) before any path construction.
  - Unit tests: multi-lock scenario resolves deterministically; slug with path chars is sanitized.
- **Dependencies:** T-R1-01

### T-R1-05 — Update `dadaia context bind` CLI for semaphore + runtime pointer

- **Status:** [x]
- **Owner:** software-engineer-python
- **Write set:** `dadaia_workspace/cli/context.py` (bind command)
- **Acceptance:**
  - `dadaia context bind` registers the runtime→session pointer on bind.
  - Phase progression does not require a new bind; bind acquires the context semaphore.
  - CLI help text updated.
- **Dependencies:** T-R1-02

### T-R1-06 — Doctor invariants for orphan/stale/duplicate locks

- **Status:** [x]
- **Owner:** software-engineer-python + devops-engineer
- **Write set:**
  - `dadaia_workspace/features/specs/` — doctor check implementations
  - `dadaia_workspace/public/scripts/` — hook wiring if needed
- **Acceptance:**
  - `dadaia doctor` detects orphan locks (no live session), stale locks (TTL expired), duplicate locks (two locks for same context).
  - Each detected issue gets a named code (e.g. `LOCK-1`, `LOCK-2`, `LOCK-3`).
  - `dadaia doctor --fix` can reclaim stale/orphan locks with audit trail.
  - Unit tests for each invariant (clean, orphan, stale, duplicate).
- **Dependencies:** T-R1-02, T-R1-05

### T-R1-07 — E2E concurrent-session test

- **Status:** [x]
- **Owner:** software-engineer-python
- **Write set:** `tests/` — new E2E test for concurrent writers
- **Acceptance:**
  - Test spawns two sessions on the same context in implement mode; second is denied.
  - Test verifies first session can write; second cannot until first releases.
  - Test passes locally (not CI-only).
- **Dependencies:** T-R1-01 through T-R1-06

---

## Group G2 — D5: Backlog-ownership rule + hard gate

### T-D5-01 — New rule: backlog-ownership (always-on)

- **Status:** [x]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/rules/backlog-ownership.md`
- **Acceptance:**
  - Rule is always-on; declares: only `project-manager` creates `specs/backlog/**` entries; PE and specialists are readers; PE consumes PM-created backlog to create specs.
  - Rule is concise (no over-explanation).
  - `dadaia public doctor` exit 0 after `dadaia public stage && dadaia public install --target all`.
- **Dependencies:** none (can run in parallel with G1)

### T-D5-02 — Hard PreToolUse gate for specs/backlog/**

- **Status:** [-]
- **Owner:** ai-engineer
- **Write set:**
  - Gate hook source (mirrors memory-atomicity gate pattern)
  - Hook wiring in `dadaia_workspace/public/scripts/` or equivalent
- **Acceptance:**
  - Any Write/Edit call targeting `specs/backlog/**` by a non-PM agent is blocked with a clear error naming the agent.
  - `project-manager` can write to `specs/backlog/**` without restriction.
  - Gate block is verified by a simulated non-PM write test.
- **Dependencies:** T-D5-01; T-R1-01 through T-R1-06 should be DONE (shared gate surface)

---

## Group G3 — R3: Four dadaia-agent specialization

### T-R3-01 — ai-engineer strategy document

- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `.dadaia/reports/dadaia-workspace/ai-engineer/` (strategy report only; no persona edits)
- **Acceptance:**
  - Strategy document answers all questions in SPEC §3/R3: skill thinness, placement (persona vs skill vs rule), process-rule enforcement surface, minimum-edit analysis, cross-reference map.
  - PM accepts the strategy before T-R3-02 is dispatched.
- **Dependencies:** G2 done (D5 rule encodes the ownership this strategy builds on)

### T-R3-02 — product-engineer persona specialization

- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/product-engineer.md` + any new skill files identified in T-R3-01
- **Acceptance:**
  - Persona explicitly states "consumes PM-created backlog; does not author backlog."
  - Spec lifecycle (DISCOVERY→SPEC→PLAN→TASKS→IMPLEMENTATION→CLOSURE→ARCHIVED) documented with phase-to-action mapping.
  - References `dadaia-step0-memory-bootstrap`, `dadaia-workspace-spec-navigator`, `dadaia-release-closure`.
  - Memory system mental model embedded (constitution + catalog + atoms).
  - Anti-slop: no redundancy with referenced skills/rules.
- **Dependencies:** T-R3-01 (strategy accepted by PM)

### T-R3-03 — project-manager persona specialization + D4 model bump

- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/project-manager.md` + any new skill files identified in T-R3-01
- **Acceptance:**
  - Opens with "Owner of backlog creation" statement.
  - grill-me stated as mandatory before dispatching when demand is ambiguous.
  - Review-gate protocol encoded as a hard rule (no `[x]`, no PR, no push, no deploy, no CLOSURE without trio approval).
  - `model: claude-opus-4-8` in frontmatter (D4).
  - `.claude/agents/project-manager.md` and `.codex/agents/project-manager.toml` projections reflect `claude-opus-4-8`.
  - Anti-slop: direct, objective, no over-explanation.
- **Dependencies:** T-R3-01

### T-R3-04 — project-auditor persona specialization

- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/project-auditor.md` + any new skill files identified in T-R3-01
- **Acceptance:**
  - Persona states: peer to PM, operator-triggered, NOT dispatched by PM as leaf specialist in normal flow.
  - Dispatch authority explicit: can spawn (code-reviewer, security-reviewer, software-architect, qa-engineer, researcher); does not implement or change specs.
  - Scoring model defined (dimensions + criticality scale).
  - Constitution + memory catalog as primary audit anchors.
  - Anti-slop: no redundancy with referenced skills.
- **Dependencies:** T-R3-01

### T-R3-05 — ai-engineer persona specialization

- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/ai-engineer.md` + any new skill files identified in T-R3-01
- **Acceptance:**
  - AI-entity surface ownership sharpened.
  - Harness-mastery synthesis workload (v0.1.4.6) reflected.
  - Clear boundary: does not author backlog, does not write product specs.
  - Anti-slop: no redundancy, no over-explanation.
- **Dependencies:** T-R3-01

### T-R3-06 — Propagate R3 + D4 to all runtimes and verify

- **Status:** [ ]
- **Owner:** ai-engineer + devops-engineer
- **Write set:** lib-originated projections only (via `dadaia public install`)
- **Acceptance:**
  - `dadaia public stage && dadaia public install --force --target all` exits 0.
  - `dadaia public doctor` exits 0.
  - Manual verification: `.claude/agents/` + `.codex/agents/` show updated personas.
  - `project-manager` model is `claude-opus-4-8` in `.claude/agents/project-manager.md`.
- **Dependencies:** T-R3-02 through T-R3-05

---

## Group G4 — R4: Generic-agent audit

### T-R4-01 — Audit generic agents for over/under-fitting

- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `.dadaia/reports/dadaia-workspace/ai-engineer/` (audit report only; no persona edits)
- **Acceptance:**
  - Every non-dadaia-specific agent audited (code-reviewer, security-reviewer, qa-engineer, devops-engineer, software-architect, software-engineer-python, software-engineer-node, backend-engineer, frontend-engineer, researcher, design-specialist).
  - Report covers: which agents have non-generic/over-fitted content, what to trim, what to generalize, cited file:line, severity.
  - No persona or skill file is modified in this task.
  - Handoff JSON emitted; PM receives findings before any R4b work is scoped.
- **Dependencies:** T-R3-06 (R3 patterns set; audit uses them as the reference)

---

## Ship gate tasks (end of rc-1)

### T-SHIP-01 — rc-1 pre-ship CI gate

- **Status:** [ ]
- **Owner:** software-engineer-python + devops-engineer
- **Write set:** none (verification only)
- **Acceptance:**
  - `ruff format --check` passes.
  - `ruff check` passes.
  - `mypy --strict dadaia_workspace` passes (zero errors).
  - `pytest -p no:cacheprovider` passes (all tests green).
  - Verification run locally on `feature/0.1.5` before any push.
- **Dependencies:** T-R1-07, T-D5-02, T-R3-06, T-R4-01

### T-SHIP-02 — QA review (qa-engineer)

- **Status:** [ ]
- **Owner:** qa-engineer
- **Write set:** `.dadaia/reports/dadaia-workspace/qa-engineer/` (review report only)
- **Acceptance:**
  - E2E/acceptance plan validated for all rc-1 work-streams (R1 E2E, D5 gate, R3 projection, D4 model, R4 audit).
  - Returns `APPROVE` or `REQUEST_CHANGES` in handoff JSON.
- **Dependencies:** T-SHIP-01

### T-SHIP-03 — Code review (code-reviewer)

- **Status:** [ ]
- **Owner:** code-reviewer
- **Write set:** `.dadaia/reports/dadaia-workspace/code-reviewer/` (review report only)
- **Acceptance:**
  - Architecture, maintainability, tests, regressions reviewed for all rc-1 changes.
  - Returns `APPROVE` or `REQUEST_CHANGES` in handoff JSON.
- **Dependencies:** T-SHIP-01

### T-SHIP-04 — Security review (security-reviewer)

- **Status:** [ ]
- **Owner:** security-reviewer
- **Write set:** `.dadaia/reports/dadaia-workspace/security-reviewer/` (review report only)
- **Acceptance:**
  - Security, privacy, secrets, dependency risk reviewed (especially R1 lock/session surface, D5 gate).
  - Returns `APPROVE` or `REQUEST_CHANGES` in handoff JSON.
- **Dependencies:** T-SHIP-01

### T-SHIP-05 — Push, PR, CLOSURE, tag, publish (on trio APPROVE)

- **Status:** [ ]
- **Owner:** devops-engineer (push/PR/merge) + product-engineer (CLOSURE + memory)
- **Write set:**
  - `feature/0.1.5` branch push + PR
  - `specs/releases/v0.1.5/rc-1/CLOSURE.md` (new)
  - `specs/memory/**` updates (CLOSURE phase only)
  - `specs/releases/ACTIVE.md` → phase CLOSURE → ARCHIVED
  - Tag `v0.1.5`, publish to PyPI
  - Live instance: `dadaia public stage && install --force --target all && doctor`
- **Acceptance:**
  - All three reviewers (T-SHIP-02, T-SHIP-03, T-SHIP-04) returned APPROVE.
  - CLOSURE.md authored with evidence references.
  - Memory atoms updated per CLOSURE protocol.
  - Live instance reflects rc-1 with zero drift.
- **Dependencies:** T-SHIP-02, T-SHIP-03, T-SHIP-04 all APPROVE
