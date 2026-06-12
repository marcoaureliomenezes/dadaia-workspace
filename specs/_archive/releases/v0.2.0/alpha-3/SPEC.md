# SPEC: v0.1.8 — Coordinator + Sub-Agent Architecture, Roster 15→9, Persona Tailoring

**Status:** Aprovado
**Release ID:** v0.1.8 (milestone of v0.2.0)
**Owner:** product-engineer
**Created:** 2026-06-06
**Depends on:** v0.1.7 committed + operator-validated (constitution frozen)

> **Design of record:** v0.2.0 umbrella SPEC §4 (coordinator + sub-agent architecture),
> grill report `.dadaia/reports/dadaia-workspace/project-manager/2026-06-06T035141Z-refine-specs.html`,
> backlog `specs/backlog/dadaia-agent-specialization.md` (§2.1–§2.6, §6), v0.2.0 TASKS.md T-018-*.

---

## 1. Why this milestone exists

v0.1.7 encoded the lifecycle law and the activity-class/lock contract as constitutional
text. v0.1.8 **implements** that law: it authors all 9 surviving core personas with the
precise vocabulary the law requires, reduces the public agent surface from 15 to 9, and
moves out-of-scope capabilities to plugin stubs. The coordinator personas (project-manager,
product-engineer, project-auditor, ai-engineer) receive the deepest treatment because they
are the agents that run the full lifecycle — a thin coordinator forces the operator to
re-explain the protocol every session.

Three live failure modes that this milestone fixes:
- PM dispatches without grill-me when demand is ambiguous; does not enforce the review gate.
- PE creates specs without a clear reference to PM-created backlog; the boundary is ambiguous.
- project-auditor is thin: no dispatch authority, no scoring model, no constitution anchor.
- 15 agents on the public surface: 4 implementer personas encode language idiom the base
  model already knows; persona slop fills context windows and drifts with the workflow.

---

## 2. Scope

### 2.1 Roster reduction: 15 → 9 core agents

**Core roster after this milestone (9 agents):**

| Agent | Role | Activity class | Lease relationship |
|---|---|---|---|
| project-manager | Coordinator / lease holder | MUTATING (release span) | Holds the release lease; never sub-leases |
| project-auditor | Peer coordinator / drift anchor | ADDITIVE | No lease — concurrent |
| product-engineer | Spec author / memory guardian | MUTATING (under PM coordination) | PM sub-agent; no independent acquire |
| ai-engineer | AI-entity surface owner | MUTATING (under PM coordination) | PM sub-agent during releases; own short MUTATING session ad-hoc |
| software-engineer | Generic implementer | MUTATING (under PM coordination) | PM sub-agent; no independent acquire |
| qa-engineer | Gate: pre-commit | ADDITIVE | No lease — concurrent |
| security-reviewer | Gate: pre-push | ADDITIVE | No lease — concurrent |
| code-reviewer | Gate: pre-PR | ADDITIVE | No lease — concurrent |
| software-architect | Architecture review / onboarding | ADDITIVE | No lease — concurrent |

**Deletions from `public/agents/`:**
- `software-engineer-python.md` — merged into `software-engineer`
- `software-engineer-node.md` — merged into `software-engineer`
- `backend-engineer.md` — merged into `software-engineer`
- `researcher.md` — removed from core (PM dispatches read-only exploration inline)

**Plugin stubs (remain in `public/agents/` as thin stubs only, not full personas):**
- `frontend-engineer.md` — plugin; contains only a plugin header + install pointer
- `design-specialist.md` — plugin; contains only a plugin header + install pointer
- `devops-engineer.md` — plugin; contains only a plugin header + install pointer

The plugin stub is not a persona. It declares `[PLUGIN REQUIRED]` and points to the
install command. No behavior is encoded.

### 2.2 New generic implementer: `software-engineer`

A single `software-engineer` absorbs the three deleted implementers. Scope:
- Language coverage: Python (`dadaia_workspace/**/*.py`), Node (`*.js`, `*.ts`, `*.mjs`
  server-side), and any language in scope for the active context's implementation tasks.
- Does NOT cover: browser frontend (`*.tsx`, browser `*.ts`, `*.css`), Go services, CI
  YAML, AI-entity surface (`dadaia_workspace/public/**`).
- Key disciplines: SDD task-marker protocol (task-manager skill), TDD-first, conventional
  commits, no-architecture-drift discipline, slop-test discipline (no fabricated tests
  to pass coverage, no real venvs in test), quality/security gate awareness.
- Activity class: MUTATING. Lease relationship: PM sub-agent — does not independently
  acquire a release lease; the lease belongs to PM's coordinator session throughout.
- Gate role: implementer. Advances to `[x]` only after qa-engineer + security-reviewer +
  code-reviewer all APPROVE.

### 2.3 Coordinator deepening: project-manager

The heart of this milestone. PM is the lease coordinator and the single entry point for
all non-trivial work. The persona must carry the dispatch logic without operator narration.

**Model:** `claude-opus-4-8` (already in current persona frontmatter; confirm and keep).

**Required persona content:**
- Opening statement: PM holds the release lease from first MUTATING write through
  CLOSURE. PM never releases the lease mid-release and never acquires a second one.
- Sub-agent dispatch model (architecture A-2): PE and software-engineer run as PM
  sub-agents under the single lease. They do not call `context bind` independently.
  The lease's `session_id` is always PM's coordinator session. PM dispatches the next
  sub-agent by invoking the Agent tool; the lease does not change hands.
  **Enforcement note:** A-2 is a dispatch-topology convention, not a session primitive.
  The gate does not distinguish sub-agents within one session; correctness rests on
  (a) PM being the only agent with dispatch authority for this flow and (b) the single
  lease keyed to PM's session. The lease is a file, not a session primitive. The gate
  does NOT block a sub-agent's independent bind mid-flow — that correctness rests on
  the convention that sub-agents do not call `context bind` independently.
- Grill-mandatory: `dadaia-grill-me` is invoked before dispatching when demand is
  ambiguous, scope is unconfirmed, or the bug/backlog set is under question. Not
  optional. A release-from-backlog does not advance to SPEC without a grill report.
- Review gate (hard rule, non-negotiable): PM lets no agent mark `[x]`, push, open PR,
  deploy, or write CLOSURE until qa-engineer + code-reviewer + security-reviewer all
  return APPROVE for the same commit. Any REQUEST_CHANGES keeps the task `[-]` and
  routes back to the implementer.
- Dispatch table updated: all references to `software-engineer-python`, `-node`,
  `backend-engineer` replaced with `software-engineer`. References to `researcher`
  removed (PM explores inline or dispatches a scoped read from any agent).
- Workflow references: In the v0.1.8→v0.1.9 interim, PM carries NO workflow-file rows
  in its persona. Orchestration is dispatch logic, expressed as Tier-2 playbook prose.
  The 2 new workflows (`release-ship`, `audit-fanout`) will be added to PM's reference
  in v0.1.9 (T-019-02). Stale Tier-1 workflow names are removed from the dispatch
  table in this milestone; Tier-2 playbook prose is PM's sole guidance until then.
- §1 lifecycle position declared: PM owns the MUTATING lease for the full release span
  (DISCOVERY → IMPLEMENTATION → REVIEW-CLOSURE). PM never enters the ADDITIVE lanes.

**Stale content to remove:**
- Per-language dispatch routing table (python/node/backend-engineer references).
- Researcher as dispatched leaf specialist.
- All Tier-1 workflow names (v0.1.9 T-019-02 will re-add only `release-ship` and
  `audit-fanout`; removing them here is not a gap, it prevents stale pointers).

### 2.4 Coordinator deepening: product-engineer

PE is a PM sub-agent during definition and closure phases. The persona must be explicit
about its subagent status and its memory write permission scope.

**Required persona content:**
- §1 position declared: PE is MUTATING, under PM coordination. PE does not independently
  bind a context session. When PM dispatches PE, PM's lease covers PE's writes.
- Memory write permission: DEFINITION phase (writing the spec set) + CLOSURE phase
  (updating memory atoms). Both are permitted, not CLOSURE-only. The v0.1.6 gate
  encodes this as a path-classifier rule.
- Backlog-consumer explicit: PE reads PM-created backlog to author specs; PE never
  creates or edits backlog entries. This is a hard-gated rule (`backlog-ownership`).
- Spec lifecycle table: the phase-to-action map must reference the §1 matrix explicitly
  — each phase maps to an activity class (MUTATING during SPEC/PLAN/TASKS/CLOSURE,
  quiescent during IMPLEMENTATION).
- Implementer list updated: "implementer agents" in Phase 7 description updated from the
  list of old implementers to `software-engineer` only (plus plugin-installed agents for
  frontend/devops work).
- Write-permissions table updated: "software-engineer-python or software-engineer-node"
  references replaced with `software-engineer`.

**Stale content to remove:**
- References to `software-engineer-python`, `software-engineer-node`, `backend-engineer`
  in the "What this agent does NOT do" table and Phase 7 description.

### 2.5 Coordinator deepening: project-auditor

PA is a peer to PM — Tier-1, operator-triggered. The persona must be explicit about its
dispatch authority and its scoring model without requiring operator narration.

**Required persona content:**
- §1 position declared: PA is ADDITIVE. It runs concurrently with PM. It is NOT
  dispatched by PM as a leaf specialist in normal flow; both are Tier-1.
- Dispatch authority: PA uses the Agent tool to spawn evidence-gathering agents
  (code-reviewer, security-reviewer, software-architect, qa-engineer, ai-engineer) to
  gather positions. PA does not implement and does not change specs or memory.
- Scoring model: dimensions + criticality scale explicitly declared inline (six
  scorecard dimensions: architecture, product, tech-stack, security, tests, agent-surface;
  criticality: CRITICAL/HIGH/MEDIUM/LOW/INFO; 1–10 per-dimension rubric).
- Constitution + memory anchor: PA's primary audit anchors are `specs/constitution.md`
  and `specs/memory/` (catalog.json + architecture.md + product atoms). Every drift
  finding is measured against them.
- Agent references updated: dispatched evidence agents list updated to reflect the 9-agent
  roster. References to `software-engineer-python`, `-node`, `backend-engineer`,
  `frontend-engineer` (core), `researcher` removed; `software-engineer` added.

**Stale content to remove:**
- Researcher dispatch instruction ("Evidence harvest rule" from header).
- References to deleted persona names in dispatch list and scope section.

### 2.6 Coordinator deepening: ai-engineer

AI-engineer is the AI-entity surface owner. It runs as a PM sub-agent during releases
and may hold a short MUTATING session for ad-hoc surface fixes.

**Required persona content:**
- §1 position declared: MUTATING during release tasks (PM sub-agent, same lease as PM);
  MUTATING for short ad-hoc surface fixes (own session, no release in flight).
- Activity class + lease relationship explicit in frontmatter or opening section.
- Write-permissions table updated: stale agent references removed
  (`software-engineer-python`, `-node`, `backend-engineer`, `frontend-engineer`
  references in the "You do NOT write" section replaced with `software-engineer`).
- Scope section updated: Python/Node/Go scope references updated to `software-engineer`.
- Collaboration section updated: references to deleted personas removed.

### 2.7 Gate persona sharpening: qa-engineer, security-reviewer, code-reviewer

Each gate persona must declare its §1 lifecycle position. The personas are already
correct in scope; the gaps are the missing declarations.

**qa-engineer additions:**
- §1 position: gate pre-commit; ADDITIVE evidence only; no lease; concurrent.
- Activity class: ADDITIVE. Gate role: approves → commit allowed.
- Scope updated: qa does not run evidence for project-auditor's deleted sub-agents list.

**security-reviewer additions:**
- §1 position: gate pre-push; ADDITIVE evidence only; no lease; concurrent.
- Activity class: ADDITIVE. Gate role: approves → push to `feature/0.2.0` allowed.

**code-reviewer additions:**
- §1 position: gate pre-PR; ADDITIVE evidence only; no lease; concurrent.
- Activity class: ADDITIVE. Gate role: approves → PR allowed.

### 2.8 Software-architect §1 alignment

software-architect is ADDITIVE — it feeds architecture findings into the
SPEC/PLAN phases (Phase 4/5 inputs) and the REVIEW phases (post-implementation).
No persona rewrite needed; targeted additions only:
- §1 position declared.
- Stale skill references stripped (`architect-code-audit`, `architect-design-patterns`
  are absent from `public/skills/`; remove references).
- Evidence harvest rule (researcher reference) stripped — researcher is removed from core.

### 2.9 Plugin scope rule update

`dadaia_workspace/public/rules/plugin-scope.md` updated to name the three plugin agents:
`frontend-engineer`, `design-specialist`, `devops-engineer`. The rule must declare that
dispatching any of these requires the plugin to be installed, and that core agents who
receive a task in those domains respond with `[PLUGIN REQUIRED]`.

### 2.10 Skills: remove 5 frontend/design skills from public/skills/

Five skills leave the core surface:
- `frontend-design` (or equivalent skill slug)
- `frontend-implementation-quality`
- `design-reference-research`
- `design-report-quality-gate`
- `ux-ui-review`

No surviving core persona references any of these after T-018-03.

### 2.11 Bug annotations

- `specs/bugs/agent-skill-surface-slop.md`: frontmatter `adopted: v0.2.0`
- `specs/bugs/semaphore-no-liveness-reclaim.md`: frontmatter `superseded_by: v0.2.0/v0.1.6`
Neither file is deleted.

### 2.12 Propagation and validation

After all persona and skill edits:
- `dadaia public stage` — re-stages with updated SHA256
- `dadaia public install --force --target all` — projects to all runtimes
- `dadaia public doctor` — exits 0; 9 core agents enumerable on all runtimes
- All runtimes (`.claude/agents/`, `.agents/`, `.opencode/agents/`, `.codex/agents/`)
  reflect the 9-agent / updated-skill surface

---

## 3. Architecture delta

No new Python modules. The v0.1.6 gate already classifies paths; this milestone edits
the AI-entity surface that the gate consumes via `agents.index.json`. The file lives at
`.dadaia/agentic/agents.index.json` and is generated by `dadaia public stage` from
persona frontmatter — it is NOT hand-authored. After this milestone `dadaia public stage`
must regenerate it to reflect the updated persona roster. The index maps EVERY agent
(all 12 files including plugin stubs) to its write_allowlist as declared in its
frontmatter — it is not a "mutating-only names" subset. The gate uses it for path
classification, not for enumerating who is MUTATING (that is answered by constitution §7).

**Plugin stubs and the core roster:** plugin stubs (`frontend-engineer.md`,
`design-specialist.md`, `devops-engineer.md`) contain `plugin: true` in frontmatter.
They are NOT personas; they carry no behavior and no write_allowlist. They are permitted
to exist in `public/agents/` as install pointers and are excluded from the 9-agent core
roster count and from any mutating set. This carve-out is explicit: v0.1.7 §14
("deleted personas must not exist") applies to full personas, not plugin stubs.
A `plugin: true` stub is architecturally distinct from a persona.

---

## 4. Tech-stack delta

No new dependencies. Model assignment changes:
- No change: project-manager already uses `claude-opus-4-8`.
- No change: all other surviving core agents keep `claude-sonnet-4-6`.
- Removed from model assignment table: `software-engineer-python`, `-node`,
  `backend-engineer`, `researcher`, `frontend-engineer`, `design-specialist`,
  `devops-engineer` (last three become plugin stubs with no model assignment in core).

`specs/memory/tech-stack.md` model assignment table to be updated at CLOSURE to reflect
the 9-agent roster.

---

## 5. Sub-agent lease model (A-2) — explicit statement

This is the central architectural decision this milestone materializes in the personas.

The release lease (a single `ctx_locks/<ctx>.lock.json` record, introduced in v0.1.6)
is held by the PM coordinator session from the first MUTATING write through CLOSURE.
PE and software-engineer execute their MUTATING work (writing specs, writing code) as
sub-agents dispatched by PM via the Agent tool. They do not call `dadaia context bind`
to acquire an independent session; they operate within PM's coordinator session.

Consequence: there is no "session handoff" between PM and PE, and no second lock
acquisition between PE and software-engineer. The lock record's `session_id` is always
PM's. Sub-agents may perform MUTATING writes (the gate checks the path classifier and
the lease mode, not which agent within the session performed the write). When PM
concludes the release, PM calls release on the lease.

This means:
- A deadlock between a PM session and a PE session is structurally impossible — PE is
  always inside PM's session.
- Concurrent ADDITIVE work (auditor, reviewers, backlog) is always allowed — they never
  contend for the lease.
- The graveyard (188 stale session records) cannot accumulate — there is one lease per
  context, not one per agent per phase.

**Enforcement honest statement:** A-2 is a dispatch-topology convention. The gate does
NOT distinguish sub-agents within one session and does NOT block a sub-agent's
independent bind mid-flow as a technical primitive. Correctness rests on (a) PM being
the only agent with dispatch authority for this flow and (b) the single lease keyed to
PM's session. The lease is a file, not a session primitive. The gate simply checks the
lease owner before MUTATING writes; if a sub-agent independently called `context bind`
and acquired the lease, the gate would not object on A-2 grounds — the convention is
what prevents this, not a harness primitive.

Every coordinator persona must state this model in its §1 lifecycle position section.
Every sub-agent persona must state "PM sub-agent — no independent acquire" in its
`lease_relationship` **frontmatter field** (not in the body). The 3 machine fields
(`activity_class`, `lease_relationship`, `gate_role`) are mandated in YAML frontmatter
for all surviving personas — dadaia-doctor validates their presence; Claude Code runtime
ignores non-native frontmatter keys, so these are for tooling only.

---

## 6. Acceptance criteria

| # | Criterion | Verification |
|---|---|---|
| AC-01 | 9 core agent persona files present in `public/agents/`; 4 deleted persona files absent; 3 `plugin: true` stubs present (plugin stubs are NOT personas and are excluded from the 9-count) | `ls public/agents/ \| wc -l` = 12 (9 core + 3 plugin stubs) |
| AC-02 | Each of the 9 core personas declares `activity_class`, `lease_relationship`, `gate_role` in YAML frontmatter (not body only) — dadaia-doctor validates presence | qa-engineer T-018-08 confirms |
| AC-03 | No surviving PERSONA (the 9 core agent files) references a deleted agent name; the `project-orchestration` SKILL is knowingly stale until v0.1.9 T-019-02 (out of scope for this AC) | doctor D-OC-1 check on personas only |
| AC-04 | `public/skills/` no longer contains any of the 5 frontend/design skill slugs | `ls public/skills/` |
| AC-05 | `dadaia public doctor` exits 0; 9 agents enumerable on all 4 runtimes | doctor output |
| AC-06 | PM persona: model=`claude-opus-4-8`; lease-coordinator role explicit; A-2 stated with honest enforcement note; grill-mandatory stated; stale workflow refs removed; body ≤ 120 lines | qa review |
| AC-07 | PE persona: backlog-consumer explicit; memory write DEFINITION+CLOSURE stated; §1 position; old implementer refs removed | qa review |
| AC-08 | project-auditor persona: ADDITIVE; peer-to-PM; dispatch authority explicit; scoring model inline; no researcher dispatch ref | qa review |
| AC-09 | ai-engineer persona: MUTATING/PM-sub-agent stated; scope refs to deleted personas removed; §1 position | qa review |
| AC-10 | software-engineer persona: new file; MUTATING/PM-sub-agent; TDD+SDD; no arch drift; no slop-test; conventional commits | qa review |
| AC-11 | plugin-scope rule names all 3 plugin agents; `[PLUGIN REQUIRED]` response documented | qa review |
| AC-12 | Bug files annotated (adopted/superseded_by) | direct read |
| AC-13 | Anti-slop gate (checked in T-018-08): no deepened persona body restates a constitution §/skill protocol for >3 lines — cite by reference; PM body ≤ 120 lines; 'cite the constitution, never duplicate it' is a gate-checked criterion in T-018-08, not advisory prose | qa-engineer count check |
| AC-14 | `agents.index.json` regenerated by `dadaia public stage` from updated persona frontmatter (not hand-authored); reflects updated roster; location `.dadaia/agentic/agents.index.json` | doctor + path check |
| AC-15 | Operator runs a small end-to-end demand through PM (grill → backlog → SPEC → implement → review gates); no lock friction; 9 agents enumerable | operator sign-off |

---

## 7. Out of scope

- Python source code changes (all gate + lock work is v0.1.6).
- Constitution changes (v0.1.7).
- Workflow files (v0.1.9 deletes stale workflows and authors new ones).
- `product/` memory tree restructure (v0.1.9).
- Skills count reduction beyond the 5 frontend/design skills (v0.1.9 confirms 22→17).
- PyPI publish (v0.2.0 only).

---

## 8. Dependencies and risks

| Item | Type | Detail |
|---|---|---|
| v0.1.7 committed + operator-validated | Hard dependency | Personas cite the frozen constitution; authoring before the freeze creates rewrite risk |
| `agents.index.json` regenerated index | Risk: gate blind spot | `.dadaia/agentic/agents.index.json` is generated by `dadaia public stage` from persona frontmatter — do NOT hand-author. T-018-07 depends on v0.1.6 T-016-00 (the agents.index.json generator). T-018-07's job is to re-run `dadaia public stage` and VERIFY the regenerated index reflects the updated roster (deleted names absent, `software-engineer` present). |
| Plugin stubs in core surface | Risk: init confusion | A fresh `dadaia init` must not emit full frontend/design/devops personas. Stubs should either be absent from the init projection or clearly identified as install-required. Confirm projection behavior in T-018-07 |
| PM persona workflow table | Risk: stale Tier-1 refs | Removing stale Tier-1 workflow names from PM's dispatch table before v0.1.9 authors new workflows leaves PM with Tier-2-only for those patterns. This is acceptable (documented behavior), not a gate block |
| Sub-agent model confusion | Risk: AI runtime misinterpretation | A-2 is a dispatch-topology convention, not a session primitive. The gate does NOT block a sub-agent's independent bind — correctness rests on PM being the sole dispatch authority and sub-agents not calling `context bind` independently. The risk is an agent ignoring the convention; mitigation is the persona text + the single lease file record. |
