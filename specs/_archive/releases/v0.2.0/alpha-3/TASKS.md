# TASKS: v0.1.8 — Coordinator + Sub-Agent Architecture, Roster 15→9, Persona Tailoring

**Status:** Aprovado
**Release ID:** v0.1.8 (milestone of v0.2.0)
**Owner:** product-engineer
**Created:** 2026-06-06

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Maximum one `[-]` per owner at a time unless disjoint write sets are declared.
All tasks start `[ ]` OPEN. Precondition for ALL tasks: v0.1.7 committed and
operator-validated (constitution frozen — personas cite frozen constitution).

---

## T-018-01 — Author `software-engineer.md` generic implementer

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:** `dadaia_workspace/public/agents/software-engineer.md` (NEW)
- **Preconditions:** v0.1.7 operator sign-off DONE. No other v0.1.8 task required.
- **Done criteria:**
  - File exists at `dadaia_workspace/public/agents/software-engineer.md`
  - YAML frontmatter valid; includes `activity_class: MUTATING`,
    `lease_relationship: "PM sub-agent — no independent acquire"`,
    `gate_role: implementer`
  - Model: `claude-sonnet-4-6`
  - Body covers, without restating referenced skills inline:
    - §1 lifecycle position: MUTATING, PM sub-agent, dispatched by PM via Agent tool
    - SDD task-lifecycle: reserves `[ ]` → `[-]` before writing; closes `[x]` only after
      qa + security + code-reviewer APPROVE; no `[x]` without trio APPROVE
    - Language coverage: Python (`dadaia_workspace/**/*.py`), Node (server-side `*.js`,
      `*.ts`, `*.mjs`), any language in active context's implementation tasks
    - TDD-first: red test before implementation code; never fabricate tests for coverage
    - No-architecture-drift: no new dependency without an approved release task; no
      layer violations; no `subprocess` outside `infrastructure/`
    - Slop-test discipline: no real venvs in tests; no `time.sleep` in tests; no
      `threading.Barrier` in unit tests; pytest `-p no:cacheprovider` for all runs
    - Conventional commits with task-id suffix
    - Does NOT cover: browser frontend, AI-entity surface, `specs/`, CI YAML
  - Does NOT reference any deleted agent name (python/node/backend/researcher)
  - Does NOT reference any of the 7 stale workflow names
  - References only skills present in `public/skills/` after T-018-03
  - `dadaia public stage` succeeds (new file staged without error)
- **Commit convention:** `feat(agents): software-engineer generic implementer (T-018-01)`

---

## T-018-02 — Delete 4 persona files (python/node/backend/researcher)

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/agents/software-engineer-python.md` (DELETE)
  - `dadaia_workspace/public/agents/software-engineer-node.md` (DELETE)
  - `dadaia_workspace/public/agents/backend-engineer.md` (DELETE)
  - `dadaia_workspace/public/agents/researcher.md` (DELETE)
- **Preconditions:** T-018-01 DONE (`software-engineer.md` must exist before old personas deleted)
- **Done criteria:**
  - All 4 files absent from `dadaia_workspace/public/agents/`
  - No surviving persona or skill file in `public/` references any of the 4 deleted
    persona names by slug (`software-engineer-python`, `software-engineer-node`,
    `backend-engineer`, `researcher`)
  - `dadaia public stage` succeeds (manifest does not error on deleted files)
- **Commit convention:** `refactor(agents): delete python/node/backend/researcher personas (T-018-02)`

---

## T-018-03 — Plugin stubs + skill removals + plugin-scope rule update

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/agents/frontend-engineer.md` (REWRITE to plugin stub)
  - `dadaia_workspace/public/agents/design-specialist.md` (REWRITE to plugin stub)
  - `dadaia_workspace/public/agents/devops-engineer.md` (REWRITE to plugin stub)
  - `dadaia_workspace/public/rules/plugin-scope.md` (UPDATE)
  - `dadaia_workspace/public/skills/frontend-design/` (DELETE — confirm exact slug)
  - `dadaia_workspace/public/skills/frontend-implementation-quality/` (DELETE)
  - `dadaia_workspace/public/skills/design-reference-research/` (DELETE)
  - `dadaia_workspace/public/skills/design-report-quality-gate/` (DELETE)
  - `dadaia_workspace/public/skills/ux-ui-review/` (DELETE)

**Parallel note:** T-018-03 and T-018-01/02 have disjoint write sets (different agent files
and skills). T-018-03 may start after T-018-01 DONE; it does not need to wait for T-018-02
to finish, but T-018-02 must complete before T-018-04 begins.

- **Preconditions:** T-018-01 DONE
- **Done criteria:**
  - `frontend-engineer.md` contains ONLY: YAML frontmatter (name, `plugin: true`), a
    `[PLUGIN REQUIRED]` header, and one sentence pointing to the plugin install command.
    No behavior encoded. No skill references.
  - `design-specialist.md` same as above.
  - `devops-engineer.md` same as above; all skill references to `devops-deploy-strategies`,
    `github-actions-pipelines`, `devops-gitflow-governance` are absent (they were in the
    old persona; the stub has none).
  - `plugin-scope.md` names all 3 plugin agents explicitly: `frontend-engineer`,
    `design-specialist`, `devops-engineer`. Rule text declares: dispatching any of these
    requires the plugin to be installed; core agents receiving a task in those domains
    respond with `[PLUGIN REQUIRED] <agent-name> plugin is not installed in this
    workspace. Install with: dadaia plugin install <name>`.
  - All 5 frontend/design skills deleted from `public/skills/` (exact slugs confirmed
    by ai-engineer via `ls dadaia_workspace/public/skills/` before deletion)
  - No surviving CORE persona (the 9 listed in SPEC §2.1) references any of the 5
    deleted skill slugs
  - `dadaia public stage` succeeds
- **Commit convention:** `refactor(agents): frontend/design/devops→plugin stubs + strip 5 skills (T-018-03)`

---

## T-018-04 — Deepen 4 coordinator personas

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/agents/project-manager.md`
  - `dadaia_workspace/public/agents/product-engineer.md`
  - `dadaia_workspace/public/agents/project-auditor.md`
  - `dadaia_workspace/public/agents/ai-engineer.md`
- **Preconditions:** T-018-02 DONE and T-018-03 DONE (deleted/stubbed agents absent; cannot
  write coordinator personas that might reference them until those are cleaned)
- **Done criteria:**

  **project-manager.md:**
  - `model: claude-opus-4-8` confirmed in frontmatter (already set; verify and retain)
  - Frontmatter or opening section includes `activity_class: MUTATING`,
    `lease_relationship: "holds release lease — coordinator"`,
    `gate_role: coordinator`
  - `## §1 Lifecycle position` section (or equivalent label) states:
    PM holds the single release lease from first MUTATING write through CLOSURE;
    PE and software-engineer are PM sub-agents (A-2) — their writes are covered by PM's
    lease; the lease's `session_id` is always PM's coordinator session.
  - Grill-mandatory hard rule explicitly stated as non-optional (not just recommended).
  - Review gate hard rule: no `[x]`, no push, no PR, no deploy, no CLOSURE until
    qa-engineer + code-reviewer + security-reviewer all return APPROVE for the same
    commit. REQUEST_CHANGES → task back to `[-]`.
  - Dispatch table updated: `software-engineer-python`, `software-engineer-node`,
    `backend-engineer` → `software-engineer`; `researcher` removed; Tier-1 stale
    workflow names (the 7 to be deleted in v0.1.9) replaced with Tier-2 playbook
    equivalents or removed; per-language routing table removed or replaced with
    a single `software-engineer` row for non-frontend/non-devops implementation.
  - No reference to deleted agent names anywhere in the body.

  **product-engineer.md:**
  - Frontmatter or opening section includes `activity_class: MUTATING`,
    `lease_relationship: "PM sub-agent — no independent acquire"`,
    `gate_role: spec-author / memory-guardian`
  - `## §1 Lifecycle position` section states: PE runs under PM coordination;
    memory writes permitted in DEFINITION (spec authoring) + CLOSURE phases, not
    CLOSURE-only; no independent session bind during active PM-coordinated release.
  - Phase 7 "Implementation" paragraph: implementer agents listed as `software-engineer`
    (not the three deleted names).
  - "What this agent does NOT do" table: entries for `software-engineer-python`,
    `software-engineer-node`, `backend-engineer`, `backend-engineer`, `frontend-engineer`
    updated to `software-engineer` (for Python/Node) and `[plugin]` for frontend.
  - No reference to deleted agent names anywhere in the body.

  **project-auditor.md:**
  - Frontmatter or opening section includes `activity_class: ADDITIVE`,
    `lease_relationship: "no lease — concurrent"`,
    `gate_role: none (peer coordinator / drift anchor)`
  - `## §1 Lifecycle position` section states: ADDITIVE, peer to PM, operator-triggered,
    NOT dispatched by PM as a leaf in normal flow.
  - Dispatch authority explicit: PA spawns evidence agents (code-reviewer,
    security-reviewer, software-architect, qa-engineer, ai-engineer) via Agent tool;
    PA does not implement and does not write specs or memory.
  - Scoring model declared inline (not just referenced): six scorecard dimensions
    (architecture, product, tech-stack, security, tests, agent-surface), criticality
    scale (CRITICAL/HIGH/MEDIUM/LOW/INFO), 1–10 per-dimension rubric semantics.
  - Constitution + memory as primary audit anchors explicitly stated.
  - Evidence harvest rule header (researcher dispatch) removed.
  - Dispatch list (in workflow step 3 and scope section) updated: `software-engineer-python`,
    `software-engineer-node`, `backend-engineer`, `frontend-engineer` (core), `researcher`
    removed; `software-engineer` added; `frontend-engineer` marked as plugin-conditional.
  - No reference to deleted agent names.

  **ai-engineer.md:**
  - Frontmatter or opening section includes `activity_class: MUTATING`,
    `lease_relationship: "PM sub-agent during releases; own short session for ad-hoc surface fixes"`,
    `gate_role: AI-entity implementer`
  - `## §1 Lifecycle position` section states: MUTATING during release tasks (runs as PM
    sub-agent); MUTATING for short ad-hoc surface fixes (own session, no release in
    flight). Never ADDITIVE — always a MUTATING actor when writing AI-entity files.
  - Scope section "You do NOT write" updated: `software-engineer-python` → `software-engineer`;
    `software-engineer-node` → `software-engineer`; `frontend-engineer` removed (plugin);
    `backend-engineer` → `software-engineer`.
  - Collaboration section: remove references to `software-engineer-python`,
    `software-engineer-node`, `backend-engineer`, `frontend-engineer` as collaborators.
  - Write-permissions table: update agent names in "Never (X)" cells to reflect new roster.
  - No reference to deleted agent names.

  **All 4 personas:**
  - The 3 machine fields (`activity_class`, `lease_relationship`, `gate_role`) are in
    YAML frontmatter (not body-only). dadaia-doctor validates frontmatter presence;
    Claude Code runtime ignores non-native frontmatter keys (these are tooling-only).
  - Anti-slop: no section restates a constitution §/skill protocol for >3 lines — cite
    by reference (A-2 → cite `project-orchestration`; grill → cite `dadaia-grill-me`;
    gate sequence → cite constitution §11). Every instruction is directly actionable.
  - PM persona body (Markdown body, excluding frontmatter) ≤ 120 lines.
  - No reference to any of the 7 stale workflow names.
  - A-2 enforcement stated honestly: the gate does NOT distinguish sub-agents within one
    session and does NOT block an independent bind as a technical primitive; correctness
    rests on PM being the sole dispatch authority and the convention that sub-agents do
    not call `context bind` independently.

- **Commit convention:** `feat(agents): deepen 4 coordinator personas (T-018-04)`

---

## T-018-05 — Sharpen 3 gate personas + software-architect §1

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/agents/qa-engineer.md`
  - `dadaia_workspace/public/agents/security-reviewer.md`
  - `dadaia_workspace/public/agents/code-reviewer.md`
  - `dadaia_workspace/public/agents/software-architect.md`
- **Preconditions:** T-018-04 DONE (coordinators define the gate sequence these personas gate into)
- **Done criteria:**

  **All 4 files (qa-engineer, security-reviewer, code-reviewer, software-architect):**
  - The 3 machine fields (`activity_class`, `lease_relationship`, `gate_role`) are in
    YAML frontmatter (not body-only). dadaia-doctor validates frontmatter presence.

  **qa-engineer.md:**
  - YAML frontmatter includes `activity_class: ADDITIVE`,
    `lease_relationship: "no lease — concurrent"`, `gate_role: gate-pre-commit`
  - Body addition (or update): "Gate pre-commit. ADDITIVE evidence only — qa-engineer
    approves → commit allowed. Does not hold or compete for the release lease."
  - No reference to deleted agent names.

  **security-reviewer.md:**
  - YAML frontmatter includes `activity_class: ADDITIVE`,
    `lease_relationship: "no lease — concurrent"`, `gate_role: gate-pre-push`
  - Body addition: "Gate pre-push. ADDITIVE evidence only — security-reviewer approves
    → push to feature branch allowed."
  - No reference to deleted agent names.

  **code-reviewer.md:**
  - YAML frontmatter includes `activity_class: ADDITIVE`,
    `lease_relationship: "no lease — concurrent"`, `gate_role: gate-pre-PR`
  - Body addition: "Gate pre-PR. ADDITIVE evidence only — code-reviewer approves
    → PR allowed. Consumes qa + security evidence + architecture adherence on the diff."
  - No reference to deleted agent names.

  **software-architect.md:**
  - YAML frontmatter includes `activity_class: ADDITIVE`,
    `lease_relationship: "no lease — concurrent"`,
    `gate_role: architecture-feed (SPEC/PLAN phases)`
  - Body: `## §1 Lifecycle position` added — ADDITIVE; feeds architecture findings to PM
    and PE during SPEC/PLAN phases; also dispatched by project-auditor for evidence.
  - All references to absent skills `architect-code-audit` and `architect-design-patterns`
    stripped from body and skills list.
  - Evidence harvest rule (researcher reference) stripped from header.

- **Commit convention:** `feat(agents): sharpen gate personas + software-architect §1 (T-018-05)`

---

## T-018-06 — Bug file annotations

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `specs/bugs/agent-skill-surface-slop.md`
  - `specs/bugs/semaphore-no-liveness-reclaim.md`
- **Preconditions:** T-018-05 DONE (surface work complete; annotating bugs as absorbed is
  the last content step before propagation)
- **Done criteria:**
  - `specs/bugs/agent-skill-surface-slop.md` frontmatter has `adopted: v0.2.0`
  - `specs/bugs/semaphore-no-liveness-reclaim.md` frontmatter has
    `superseded_by: v0.2.0/v0.1.6`
  - Neither file is deleted
  - Neither file has content changed beyond the frontmatter additions
- **Commit convention:** `chore(bugs): annotate slop + semaphore bugs as absorbed (T-018-06)`

---

## T-018-07 — Propagation: stage → install --force --target all → doctor exit 0

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `.dadaia/agentic/manifest.json` (manifest update via `dadaia public stage`)
  - `.dadaia/agentic/agents.index.json` (regenerated by `dadaia public stage` from persona frontmatter — NOT hand-authored)
  - `.claude/agents/` (all 4 runtimes via `dadaia public install`)
  - `.agents/`
  - `.opencode/agents/`
  - `.codex/agents/`
- **Preconditions:** T-018-03 DONE, T-018-05 DONE, T-018-06 DONE.
  **T-018-07 depends on v0.1.6 T-016-00 (agents.index.json generator)** — confirm the
  generator is in place before running `dadaia public stage`.

**Parallel note:** T-018-07 has a disjoint write set from all preceding tasks (it writes
to runtime projection trees, not to `public/agents/*.md`). It begins only after all
persona edits and bug annotations are committed.

- **Done criteria:**
  - `dadaia public stage` re-run; exits 0; regenerates `.dadaia/agentic/agents.index.json`
    from persona frontmatter (do NOT hand-edit this file)
  - VERIFY regenerated `agents.index.json`: deleted agent names absent; `software-engineer`
    present; plugin stubs reflected with `plugin: true`; index maps agents to their
    write_allowlist as declared in frontmatter (it is NOT a "mutating-only" subset)
  - `dadaia public install --force --target all` exits 0
  - `dadaia public doctor` exits 0
  - Runtime verification:
    - `.claude/agents/` contains exactly 12 files (9 core + 3 plugin stubs)
    - `.codex/agents/` contains exactly 12 files
    - `.agents/` contains exactly 12 files
    - `.opencode/agents/` contains exactly 12 files (or equivalent count for that runtime)
  - No orphan agents, skills, or rules flagged by doctor (D-OC-1 passes)
  - The 5 deleted frontend/design skills absent from all runtime projection trees
- **Commit convention:** `chore(public): propagate v0.1.8 roster to all runtimes (T-018-07)`

---

## T-018-08 — qa-engineer gate (pre-commit)

- **Status:** [x]
- **Owner:** qa-engineer
- **Write-set:** `.dadaia/handoff/dadaia-workspace/` (ADDITIVE — evidence only)
- **Preconditions:** T-018-07 DONE

- **Done criteria:**
  - qa-engineer confirms all 9 core personas present and each has `activity_class`,
    `lease_relationship`, `gate_role` declared in YAML frontmatter (not body-only)
  - Confirms: no surviving PERSONA (the 9 core agent files) references a deleted agent
    name or absent skill. NOTE: the `project-orchestration` SKILL is knowingly stale
    until v0.1.9 T-019-02; do not flag it as a persona violation.
  - Confirms: PM persona has model=`claude-opus-4-8`; lease-coordinator role explicit;
    A-2 dispatch model stated with honest enforcement note (gate does not distinguish
    sub-agents, correctness rests on convention); review-gate hard rule present; stale
    agent dispatch refs absent
  - **Anti-slop gate-check (hard, measurable):** PM persona body ≤ 120 lines (count
    excluding frontmatter); no deepened persona body restates a constitution §/skill
    protocol for >3 lines — every such section must cite by reference (cite
    `project-orchestration`, `dadaia-grill-me`, constitution §11, etc.); flag any
    section that copies protocol text inline instead of citing. This criterion is
    gate-checked, not advisory.
  - Confirms: PE persona has PM-sub-agent declared; DEFINITION+CLOSURE memory write
    permission stated; old implementer refs absent
  - Confirms: project-auditor has ADDITIVE/peer-to-PM stated; dispatch authority
    explicit; scoring model inline; researcher refs absent
  - Confirms: ai-engineer has §1 position; scope section updated; write-permissions
    table consistent with 9-agent roster
  - Confirms: `software-engineer.md` covers TDD + SDD lifecycle + no-slop-test +
    conventional commits; no deleted agent refs
  - Confirms: 3 gate personas have §1 fields in YAML frontmatter; software-architect
    has §1 frontmatter fields + stripped refs
  - Confirms: 3 plugin stubs are thin (no behavior encoded); each has `plugin: true`
    in frontmatter
  - Confirms: 5 frontend/design skills absent; no core PERSONA refs them
  - Confirms: `dadaia public doctor` exit 0; 9 agents enumerable all runtimes
  - Confirms: bug annotations correct
  - Confirms: `agents.index.json` at `.dadaia/agentic/agents.index.json` was regenerated
    by `dadaia public stage` (not hand-authored); deleted agent names absent;
    `software-engineer` present; maps agents to write_allowlist (not a mutating-only
    subset — constitution §7 answers who is MUTATING)
  - Handoff JSON emitted to `.dadaia/handoff/dadaia-workspace/` as
    `T-018-08-qa-gate.handoff.json` with `verdict: APPROVE` or `verdict: REJECTED`
  - If REJECTED: findings detail specific failing criteria; relevant implementation
    task re-opened `[ ]`; qa re-runs after fix
  - APPROVE → commit allowed
- **Commit convention:** `chore(gate): v0.1.8 qa-engineer approval (T-018-08)`

---

## T-018-09 — Operator in-workspace validation + push

- **Status:** [x]
- **Owner:** project-manager (coordinates); operator signs off
- **Write-set:** `.dadaia/handoff/dadaia-workspace/` (ADDITIVE — operator sign-off record)
- **Preconditions:** T-018-08 DONE (qa APPROVE in handoff)

- **Done criteria:**
  - Operator runs a small end-to-end demand through PM on the live instance:
    1. State a plain-language demand to PM
    2. PM runs grill-me (confirms grill-mandatory)
    3. PM creates a backlog entry (confirms backlog-ownership)
    4. PM dispatches PE; PE authors a stub spec
    5. PM dispatches software-engineer for a stub implementation task
    6. software-engineer flips `[ ]` → `[-]`; performs stub work; flips `[-]` → `[x]`
       pending review
    7. PM routes through qa → security → code-reviewer gates
    8. No lock friction, no spurious MUTATING block, no deadlock observed
  - `dadaia public doctor` exits 0
  - 9 agents enumerable in all runtimes
  - Coordinators navigate the lifecycle from their personas without operator explaining
    the protocol
  - Operator sign-off recorded in handoff or TASKS comment
  - Push to `feature/0.2.0` allowed after sign-off
- **Commit convention:** `chore(gate): v0.1.8 operator sign-off + push (T-018-09)`

---

## Summary

| Task | Owner | Write-set summary | Preconditions |
|------|-------|-------------------|---------------|
| T-018-01 | ai-engineer | NEW software-engineer.md | v0.1.7 signed off |
| T-018-02 | ai-engineer | DELETE 4 persona files | T-018-01 DONE |
| T-018-03 | ai-engineer | Plugin stubs; 5 skill deletions; plugin-scope rule | T-018-01 DONE |
| T-018-04 | ai-engineer | Deepen 4 coordinator personas | T-018-02, T-018-03 DONE |
| T-018-05 | ai-engineer | §1 for 3 gates + software-architect | T-018-04 DONE |
| T-018-06 | ai-engineer | Bug annotations | T-018-05 DONE |
| T-018-07 | ai-engineer | Propagation; regenerate agents.index.json via `dadaia public stage` | T-018-03, T-018-05, T-018-06 DONE; depends on v0.1.6 T-016-00 |
| T-018-08 | qa-engineer | Gate review — pre-commit | T-018-07 DONE |
| T-018-09 | project-manager + operator | Operator E2E + push | T-018-08 APPROVE |

**Total: 9 tasks — 6 ai-engineer, 1 qa-engineer, 1 project-manager/operator, 1 combined**

**Critical path:** T-018-01 → T-018-02 → T-018-04 → T-018-05 → T-018-06 → T-018-07 → T-018-08 → T-018-09

**Parallel opportunity:** T-018-03 can proceed concurrently with T-018-02 (disjoint write sets) once T-018-01 is DONE.
