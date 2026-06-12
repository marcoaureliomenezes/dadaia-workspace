# SPEC: v0.1.7 — Constitution v2 + Development Lifecycle Law + Memory Canon (THE FREEZE)

**Status:** Aprovado
**Release ID:** v0.1.7
**Parent program:** v0.2.0 — Agentic Development Lifecycle
**Owner:** product-engineer
**Created:** 2026-06-06
**Type:** Milestone SPEC — Milestone 2 of 4 under the v0.2.0 program. Document-only: no Python code.

> **Source of record:** v0.2.0/SPEC.md §v0.1.7, v0.2.0/PLAN.md §Milestone v0.1.7,
> v0.2.0/TASKS.md T-017-*.
> The consolidated roadmap `…/project-manager/2026-06-06T045436Z-consolidated-roadmap.md`
> (§1 matrix, §2 lease flow, §3 roster, §4 constitution additions) is supporting context —
> it is the genesis document, not the acceptance gate. Once §7 is committed in the
> constitution, the constitution §7 matrix is the normative source. The roadmap is not
> re-checked after that point.
> This SPEC does not repeat what is already ratified in the program umbrella. It states only
> the milestone delta that product-engineer will implement.

---

## 1. Why this milestone exists

v0.1.6 delivers the TTL-lease lock model. Without encoding it as law, every subsequent
session must re-derive the contracts from scratch — exactly the thrash that caused three
rewrites. v0.1.7 is THE FREEZE: it encodes the canonical agentic development lifecycle,
the coordinator+sub-agent architecture, the anti-slop law, the review-gate sequence, and
the memory canon into `specs/constitution.md` before a single persona is authored in
v0.1.8. Personas in v0.1.8 will be written once, against a committed constitution, and
never rewritten because the law changed underneath them.

This milestone is also the point where the operators demands are satisfied at the legal
level: the steps in the development lifecycle, how agents work in it, the process of
backlog definition, and the role of each agent are encoded as binding law derivable from
the constitution without operator narration.

**Activity class:** document-only. No Python code, no shell script changes. The entire
milestone is two write targets: `specs/constitution.md` (major revision) and
`specs/memory/product/quality-assurance.md` (new atom), plus the `index.md` catalog
entry. Gate write permission for `specs/memory/**` in DEFINITION phase is established
by the v0.1.6 gate (OD-5 resolution, ratified in v0.2.0/SPEC.md §5).

---

## 2. Objective

Produce a `specs/constitution.md` v2 that is a complete, standalone source of truth for:

1. The canonical eight-phase development lifecycle (§7 matrix, normative source once
   committed; roadmap §1 is the genesis context) — owner, write-target, activity class,
   and lease behavior per phase, including the self-host path generalization for phase 6.
2. The concurrency model — ADDITIVE phases run concurrently; MUTATING phases serialize
   under one lease held by the PM coordinator.
3. The coordinator + sub-agent architecture — project-manager holds the single lease;
   product-engineer and software-engineer run as PM sub-agents under it.
4. The backlog-definition process — PM owns; grill is mandatory before SPEC.
5. The review-gate sequence — qa→commit, security→push, code-review→PR; PE updates
   memory only after code-review gate.
6. The anti-slop law — no agent/skill/rule/workflow without a phase it owns or gates;
   no store without GC; no fact in two sources.
7. The memory canon — `architecture.md`, `product/**` folder, `tech-stack.md`, and the
   new `quality-assurance.md`.
8. The agent roster — 9 named core agents, each declared with its phase ownership, activity
   class, and lease relationship.
9. Cross-harness honesty — updated to reflect the v0.1.6 gate model exactly.

The test of completeness: a new operator can read the constitution and derive the full
lifecycle, all agent roles, the lock contract, and the gate sequence without any
additional narration.

Additionally, create `specs/memory/product/quality-assurance.md` as the single source of
truth for the test architecture design (absorbing `test-suite-architecture.md`), and
update `specs/memory/product/index.md` with the catalog entry.

---

## 3. Product deltas

### 3.1 `specs/constitution.md` — major revision

The current constitution (6 laws) states foundational rules (SDD is binding, public
defaults generic, memory is truth, runtime parity, source repo clean, layering) but
omits the development lifecycle, the agent roster, the lock model, the gate sequence,
the anti-slop law, and the memory canon. Every session re-derives these from
scattered skills and rules.

v2 adds the following named sections — each a new law:

**§7 Canonical Development Lifecycle**
Once committed, this section IS the normative source. The consolidated roadmap §1 is
the genesis context; it is referenced for traceability only, not as an ongoing gate.
The eight-phase table:

| # | Phase | Owner | Writes to | Activity class | Lease behavior |
|---|-------|-------|-----------|----------------|----------------|
| 1 | Backlog definition | project-manager | `specs/backlog/**` | ADDITIVE | no lease — parallel |
| 2 | Bug filing | any agent / auto | `specs/bugs/**` | ADDITIVE | no lease — parallel |
| 3 | Research | researcher / PM-dispatched | `.dadaia/reports/**` | ADDITIVE | no lease — parallel |
| 4 | Audit | project-auditor | `.dadaia/reports/**` | ADDITIVE | no lease — parallel |
| 5 | Release definition (SPEC/PLAN/TASKS) | product-engineer | `specs/releases/<id>/**` | MUTATING | acquires the release lease |
| 6 | Implementation | software-engineer | `repos/<ctx>/` prod + tests (or `dadaia_workspace/**` when dadaia-workspace is the bound context) | MUTATING | holds the release lease |
| 7 | Review gates (qa→commit · security→push · code-review→PR) | qa-engineer · security-reviewer · code-reviewer | `.dadaia/handoff/**` · `.dadaia/reports/**` | ADDITIVE evidence; gates transitions | no lease — they vote |
| 8 | Closure (memory + ACTIVE) | product-engineer | `specs/memory/**`, `CLOSURE.md`, `ACTIVE.md` | MUTATING | holds until release; then releases |

The section states the single governing rule: exactly one MUTATING actor per context at
a time (phases 5/6/8), serialized by one lease that project-manager coordinates.
ADDITIVE actors (1/2/3/4/7) run in parallel and never touch the lease.

The 4-row summary table in the v0.2.0 umbrella (SPEC.md §3) maps to this normative
matrix as follows: umbrella row 1 = phases {1, 2}; row 2 = phases {3, 4}; row 3 =
phases {5, 6, 8}; row 4 = phase {7}. The umbrella is the summary; constitution §7 is
normative.

**§8 Concurrency Model**
Two activity classes partition every action in the workspace. The partition is
simultaneously the lock model, the agent-coordination model, and the lifecycle.

- ADDITIVE phases (1/2/3/4/7): `specs/backlog/**`, `specs/bugs/**`,
  `.dadaia/reports/**`, `.dadaia/handoff/**` — no lease required, concurrent sessions
  allowed, gate allows unconditionally.
- MUTATING phases (5/6/8): `specs/releases/<id>/**`, the active context's production tree (`repos/<ctx>/` for a consumer repo, or `dadaia_workspace/**` when dadaia-workspace is the bound context), `specs/memory/**` — exactly one active lease per context; gate blocks on live-lease conflict; the lease is acquired via `O_EXCL` CAS (as implemented in v0.1.6).

The lease record schema (as implemented in v0.1.6): `{context, release, session_id,
mode, acquired_at, heartbeat, ttl}`. No PID field. Liveness = `now − heartbeat ≤
LEASE_TTL_SECONDS` where `LEASE_TTL_SECONDS = 120` (short heartbeat — OQ-1 operator
decision 2026-06-06, superseding the earlier 1800s value). Stable session identity via
`.dadaia/sessions/runtime/<id>.ptr` makes a relaunched/continuing session resolve to the
same identity (RENEW, never self-block). Heartbeat renewed on every PreToolUse event by
the actively-working holder. A fully-idle holder is reclaimable after ~120s. Fail-safe:
the gate never blocks on an expired or absent lease — it heals and allows; a live foreign
lease yields informatively and never instructs the operator to rebind, relaunch, or steal.

**§9 Coordinator + Sub-Agent Architecture**
project-manager is the lease coordinator for a release. When a release enters its
MUTATING span (phase 5), PM acquires ONE lease keyed to PM's coordinator session and
holds it through phase 5 → 6 → 8. product-engineer and software-engineer run as PM
sub-agents under that single lease. They never independently bind a session, so there
is no session handoff and no second lock. This is how deadlocks between sessions in
different lifecycle phases are structurally impossible. The writer role moves between
sub-agents by PM dispatching the next one; the lease never changes hands.

Exactly-one-lease invariant: at most one MUTATING holder per context at any time.
Carve-out: outside a release span, ai-engineer (only) may take its own short MUTATING
lease for surface fixes (`dadaia_workspace/public/**`). This never overlaps a
PM-held release lease because a release in flight holds the only lease for the context;
ai-engineer's ad-hoc lease is blocked by the gate if a PM lease is live. The
exclusivity invariant is preserved: the gate enforces at most one holder regardless of
whether the holder is PM or ai-engineer.

**§10 Backlog-Definition Process**
project-manager is the sole owner of `specs/backlog/**`. The process:
1. PM consults `specs/bugs/` (status: open) + `specs/backlog/` (status: candidate/idea).
2. PM dispatches product-engineer to pick and define the release (never self-initiated).
3. product-engineer sanitizes stale/invalid items (deferred/rejected with reason; never
   deletes).
4. product-engineer picks the bug + backlog set; every picked bug is solved in the
   release unless a picked backlog item supersedes it (record `superseded_by:` in bug
   frontmatter; TASKS must cover the bug acceptance).
5. A `dadaia-grill-me` session on the picked set is MANDATORY before the SPEC is
   written. PM will not advance a release to SPEC without it.
6. product-engineer writes the SPEC.md Draft; PM does not unblock the release until
   SPEC has `**Status:** Aprovado`.

**§11 Review-Gate Sequence**
Gate sequence for every rc-N (ship) segment:
1. qa-engineer reviews → APPROVE verdict → commit allowed.
2. security-reviewer reviews → APPROVE verdict → push to feature branch allowed.
3. code-reviewer reviews → APPROVE verdict → PR merge allowed.
4. product-engineer updates `specs/memory/**` → only after code-review gate.

Reviewer evidence lands in `.dadaia/handoff/<context>/` and `.dadaia/reports/<context>/`
exclusively. No `specs/releases/<id>/evidence/` subtree exists (A-1 resolution). Each
gate requires a handoff JSON with `"verdict": "APPROVED"`. A REJECT blocks the
transition and reopens the relevant implementation task.

For alpha-N segments: qa-engineer gate only → commit. No push, no PR, no other reviewers.

**§12 Anti-Slop Law**
No agent, skill, rule, or workflow ships without a phase in the §7 matrix that it owns
or gates. No store is created without a GC mechanism. No fact is recorded in two
sources (constitution is the single source; skills and personas cite it, never
duplicate it). Evidence paths are `.dadaia/handoff/` and `.dadaia/reports/` only.

**§13 Memory Canon**
The four authoritative memory areas that define the current state of the product:
- `specs/memory/architecture.md` — layer rules, module map, dependency contracts,
  ADRs, and agent topology.
- `specs/memory/product/**` — folder catalog: `index.md` (entry point with vision,
  users, catalog, capability-map, limits) + one `.md` atom per production feature.
- `specs/memory/tech-stack.md` — approved technologies, constraints, canonical commands.
- `specs/memory/quality-assurance.md` (NEW, this milestone) — test pyramid, proportions,
  the design-of-record for quality; single source absorbing `test-suite-architecture.md`.

Memory files are the atomic snapshot of the current product. They are NOT changelogs.
product-engineer is the sole author of memory files, permitted in DEFINITION phase
(writing quality-assurance.md in this milestone) and CLOSURE phase (updating atoms
after a release).

**§14 Agent Roster**
9 core agents, each with phase ownership, activity class, and lease relationship. This
section is the canonical roster. Agents not listed here are plugins, not core:

| Agent | Phase | Activity class | Lease relationship |
|-------|-------|----------------|--------------------|
| project-manager | 1–2, coordinates all | ADDITIVE (backlog); MUTATING coordinator (lease) | holds + hands + releases the release lease |
| project-auditor | 4 (audit) | ADDITIVE | no lease |
| product-engineer | 5 + 8 (definition, closure) | MUTATING | PM sub-agent, no independent acquire |
| software-engineer | 6 (implementation) | MUTATING | PM sub-agent, no independent acquire |
| qa-engineer | 7 gate → commit | ADDITIVE evidence, votes | no lease |
| security-reviewer | 7 gate → push | ADDITIVE evidence, votes | no lease |
| code-reviewer | 7 gate → PR | ADDITIVE evidence, votes | no lease |
| ai-engineer | surface owner (owns `dadaia_workspace/public/**`) | MUTATING under PM lease during releases | PM sub-agent when part of a release; own short lease for ad-hoc surface fixes |
| software-architect | feeds findings into phases 4/5 | ADDITIVE | no lease |

Plugins (not in core roster): frontend-engineer, design-specialist, devops-engineer.
Every surviving persona must reference a phase from the §7 matrix that it owns or gates.
Personas for deleted agents must not exist in `dadaia_workspace/public/agents/`.

**Updates to existing sections:**
- §4 Runtime Parity Must Be Honest — update to reflect v0.1.6 gate model:
  Claude Code = real block (gate is enforced shell hook); Codex = guardrail
  (trusted-workspace; gate is advisory on untrusted Codex); opencode = advisory only.
- §6 Layering — no change.
- §1–§5 — no change (they remain the foundational laws).

### 3.2 `specs/memory/product/quality-assurance.md` — new memory atom

A new memory atom that becomes the single source of truth for the test architecture of
dadaia-workspace. Content absorbs `test-suite-architecture.md` and is the design-of-record
for implementers and qa-engineer. Required sections (all 6 mandatory per memory atom
contract):

- `## Propósito` — five-layer pytest architecture purpose; no-slop policy; CI-only coverage.
- `## Fluxo de uso` — 5-step sequence: write test → pick layer → mark with marker → run
  local fast path → CI runs 7 jobs.
- `## Trigger típico` — used when implementing a new feature, refactoring a public
  contract, or debugging a CI failure.
- `## Diferencial` — without the taxonomy, the suite has no boundary between fast and slow
  tests; coverage inflation hides weak contracts; release-history tests accumulate.
- `## Estado runtime tocado` — `pyproject.toml`, `tests/unit/**`, `tests/contract/**`,
  `tests/integration/**`, `tests/e2e/**`, `tests/tmp/**`, `.github/workflows/ci.yml`,
  `tests/conftest.py`.
- `## Dependências` — `[[specs-doctor]]`, `[[public-asset-distribution]]`, `[[agent-comms]]`,
  `[[sdd-gate-v3]]`.

Frontmatter: slug `quality-assurance`, category `product`, tags `testing/pytest/ci/quality`,
`agent_tier: self-pull`.

### 3.3 `specs/memory/product/index.md` — catalog entry

Add `quality-assurance` to the catalog in daily-relevance order, with a link to
`quality-assurance.md`. The entry must appear with `slug`, `title`, `tldr` consistent
with the atom frontmatter.

### 3.4 `test-suite-architecture.md` — staged for archive

`specs/memory/product/test-suite-architecture.md` is NOT deleted in this milestone (the
gate blocks deletion from memory before CLOSURE). It is annotated in the file header with
a note: `SUPERSEDED — content absorbed into quality-assurance.md (v0.1.7). This file will
be moved to specs/_archive/legacy-memory/ at release CLOSURE.` The actual `git mv` happens
at v0.2.0 CLOSURE (T-020-05).

### 3.5 Memory doctor-error fixes

The following atoms have known doctor errors that block `dadaia specs doctor` from
passing. Fixing them is a precondition for T-017-03 (qa gate) acceptance. All fixes
are mechanical frontmatter/link repairs — no content meaning changes, no gate conflict.

1. **`sdd-gate-v3.md`** — two violations, both mechanical:
   - Frontmatter `description` field (the `summary:` block) is too long for the
     `memory-frontmatter-v1` schema. Shorten the `summary:` to ≤ 3 sentences /
     ≤ 280 characters while preserving its meaning.
   - Body contains a broken wikilink `[[semaphore-no-liveness-reclaim]]` (line 60,
     in the "Context semaphore" paragraph). `semaphore-no-liveness-reclaim` is a bug
     file in `specs/bugs/`, not a memory atom — no corresponding `.md` exists under
     `specs/memory/`. Fix: **remove the wikilink entirely** and replace the phrase
     `— ver [[semaphore-no-liveness-reclaim]] em specs/bugs/` with the plain-text
     equivalent `— tracked in specs/bugs/`.

2. **`sdd-bug-backlog-governance.md`** — one violation:
   - Frontmatter `summary:` block is too long for the `memory-frontmatter-v1` schema.
     Shorten to ≤ 3 sentences / ≤ 280 characters while preserving its meaning.

No other wikilinks in either atom reference non-existent memory slugs. The `[[sdd-hotfix-track]]`,
`[[context-management]]`, `[[agent-orchestration]]`, `[[public-asset-distribution]]`,
`[[specs-doctor]]`, and `[[agent-sdd-alignment]]` wikilinks in these two atoms all
resolve to real `.md` files in `specs/memory/product/` and require no change.

---

## 4. Architecture deltas

None. This milestone is document-only. No Python code changes, no shell script changes,
no new features, no CI/CD changes. The gate architecture cited (v0.1.6 lease model) is
implemented fact by the time this milestone begins.

---

## 5. Tech-stack deltas

None. No new dependencies, no runtime changes.

---

## 6. Security / operations deltas

None. The cross-harness honesty update in §4 is a documentation correction, not a
behavior change.

---

## 7. Memory files affected at closure

At v0.2.0 CLOSURE (T-020-05), not this milestone's own closure:

- `specs/memory/product/quality-assurance.md` — created this milestone; reflects the
  current test architecture state as of v0.2.0 ship.
- `specs/memory/product/index.md` — catalog entry added.
- `specs/memory/product/test-suite-architecture.md` → `git mv` to
  `specs/_archive/legacy-memory/<timestamp>/` (CLOSURE of v0.2.0).
- `specs/constitution.md` — updated in-place; the constitution is not a memory atom
  but is the product law. Updated as part of T-017-01; committed directly; no CLOSURE
  gate restriction (constitution writes are operator-confirmed, not memory-gate-locked).

Note: `specs/constitution.md` is not under `specs/memory/**` and is not subject to the
RULE A memory gate. T-017-01 writes it directly.

---

## 8. Acceptance criteria

The milestone is complete when all of the following are true:

1. **Lifecycle derivable.** An operator can read `specs/constitution.md` and list the 8
   phases, their owners, their write targets (including the self-host generalization for
   phase 6), their activity class, and their lease behavior without consulting any other
   document. The umbrella-reconciliation (4-row summary → 8-row normative) is also
   derivable from the constitution.
2. **Roster derivable.** The same read yields the 9-agent roster with each agent's phase
   ownership, activity class, and lease relationship.
3. **Lock contract derivable.** The same read yields: MUTATING serializes under one lease;
   ADDITIVE is always parallel; the coordinator model (PM holds, sub-agents run under it);
   and the ai-engineer carve-out (outside a release span, ai-engineer may hold a short
   MUTATING lease for surface fixes; gate enforces exclusivity).
4. **Gate sequence derivable.** The same read yields: qa→commit, security→push,
   code-review→PR; PE memory update after code-review gate; evidence in `.dadaia/handoff/`
   only.
5. **Backlog process derivable.** The same read yields: PM owns backlog; grill mandatory;
   every picked bug solved or superseded with trace.
6. **Anti-slop law encoded.** The constitution explicitly states: no agent/skill/workflow
   without a §7 phase; no store without GC; no fact in two sources.
7. **Memory canon stated.** The constitution names the 4 canon memory AREAS explicitly
   (`architecture.md`, `product/**` atom tree, `tech-stack.md`, `quality-assurance.md`).
8. **`quality-assurance.md` valid.** The atom has all 6 required sections, valid
   frontmatter, no forbidden headings, and `dadaia specs doctor` LINT-1 passes on it.
9. **`index.md` updated.** The catalog entry for `quality-assurance` is present and links
   correctly.
10. **No new lease mechanics.** The constitution cites only OQ-1..4 from the v0.1.6
    design proposal as implemented. Any new mechanics are a SPEC violation.
11. **Doctor passes.** `dadaia specs doctor` exits 0 after all tasks in this milestone are
    committed. This includes the 3 known LINT-1 atom fixes.
12. **qa-engineer APPROVE.** T-017-03 emits a handoff with `"verdict": "APPROVED"`.
13. **Operator confirms.** Operator reads `specs/constitution.md` §7 and confirms the
    lifecycle matrix is internally self-consistent and matches the lived workflow.
    Acceptance does not gate on a verbatim diff against the consolidated roadmap — the
    constitution §7 matrix is the normative source once committed; the roadmap is
    supporting context. Sign-off recorded.

**Soul-fold additions (D2/D3/D4/D5/D6-law/D10/D13):**

14. **Identity derivable (D10).** An operator reads `specs/constitution.md §0` and can state in one sentence what dadaia-workspace is and what the Spec Context Project keystone concept means (spec folder + repo + session-bindable + inject + enforce + parallel-multi-project).
15. **Agent philosophy present (D13).** Constitution §0 (or §14) contains the "Agent Philosophy" clause: agents are generic implementations specialized only in their SDD role; the per-agent specialization stance for at least ai-engineer, product-engineer, and project-manager is stated.
16. **3-channel model encoded (D2).** Constitution §7 Phase 4 (Audit) "Writes to" reads `specs/audits/<ts>/`. §11 evidence path explicitly names all three channels. §12 anti-slop law cites the three-channel separation rule.
17. **Dispatcher purity law (D3).** Constitution §9 contains an explicit clause: "Only `project-manager` and `project-auditor` may dispatch sub-agents. All other personas are workers — they reply only to their dispatcher and never invoke another agent."
18. **Spec-review sequence (D4).** Constitution §11 contains a sub-section on spec-review ordering: qa-first (mandatory) → arch parallel (optional) → SE last (after QA APPROVE). Distinct from the implementation checkpoint sequence.
19. **Checkpoint relabel (D5).** The word "gate" in §11 for the qa→commit/security→push/code-review→PR transitions is replaced by "coordinator-enforced checkpoint" or equivalent. No residual "gate" wording that implies a mechanical block for these reviewer transitions.
20. **Naming law (D6).** Constitution §8 (ADDITIVE section) and/or §12 state the collision-safe naming convention for `specs/audits/`: `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/` for directories; files follow the same prefix pattern.

---

## 9. Out of scope

- Any Python code change. If an implementation task appears to require Python, it is a
  scope violation and must be blocked.
- Any shell script change (including `sdd-spec-gate.sh`).
- v0.1.8 persona authoring. Personas cite the constitution; they are written in v0.1.8
  after this milestone is committed.
- v0.1.9 surface cleanup (workflow deletion, skills prune, product/ tree restructure).
- Deployment (PyPI, tag). Deployment is v0.2.0 only.
- Adding `quality-assurance.md` to `specs/memory/architecture.md`. The architecture atom
  is not updated in this milestone; it is updated at v0.2.0 CLOSURE (T-020-05).
- Persona-level CLOSURE-only deduplication (product-engineer.md "atomicity contract" + workspace-protocol.md §5 losing-duplicate deletion). These are persona-surface changes in the v0.1.8 scope (personas cite the frozen constitution; the constitution §13 DEFINITION+CLOSURE statement is the single source). This milestone encodes the canonical answer in the constitution; v0.1.8 removes the duplicates from the personas.

## 11. Soul-fold addendum (audit D2/D3/D4/D5/D6-law/D10/D13 — folded from audit)

This section records the soul-fold additions to this milestone, authorized by the v0.2.0 pre-deploy hold decision. These are constitution edits that fold into v0.1.7 (THE FREEZE) — the natural and only-correct moment to encode them. Deferring to a post-ship patch would require re-opening the same constitution sections currently being frozen. Source: `backlog/v0.2.0-soul-and-correctness-fold.md`.

**D10 — Constitution §0 Identity & Core Concepts + Spec Context Project (P0 soul):** Add `## 0. Identity & Core Concepts` as the first section of `specs/constitution.md`, before §1. This section declares: (a) what dadaia-workspace IS — a multi-AI-harness (Claude Code / Codex / opencode) × multi-project × SDD × multi-agent workspace, the keystone concept being the **Spec Context Project** (a spec folder pattern + one repo, session-bindable, injects constitution+memory into the session via lazy consumption, enforces SDD lifecycle, enables safe parallel multi-project work with one lease per context); (b) the value proposition: workspace-level context-engineering that orients a generic agent fleet to build projects safely in parallel; (c) the agent philosophy (see D13). The lifecycle, roster, lock contract, and gate (§7–§14) are derivable from §0's definitions. §0 is declarative, not normative — it does not impose new constraints; it defines what §1–§14 encode.

**D13 — Agent philosophy clause (§0 or §14):** Agents are generic AI implementations, specialized only in their dadaia-workspace SDD role: how they fit the lifecycle, which phases they own or gate, what skills and context-engineering they carry. They carry NO project-domain knowledge — that lives in the Spec Context's specs. Key per-agent specialization: ai-engineer = multi-harness surface + agent/skill/persona engineering; product-engineer = specs + memory + anti-slop guardianship; project-manager = full lifecycle coordinator + every agent's attributions as delegator; software-engineer = production code + TDD + SDD task discipline. This clause goes in §0 "Agent Philosophy" sub-section or as a §14 addendum.

**D2 — 3-channel report model in constitution (§7/§11/§12):** The three channels are now encoded as law: (1) user-requested HTML reports → `.dadaia/reports/<ctx>/<agent>/`; (2) agent↔agent communication → `.dadaia/handoff/<ctx>/` JSON only; (3) project-auditor audit markdown → `specs/audits/<ts>-<session_id_8chars>/`. Phase 4 (Audit) in the §7 matrix row must be updated: "Writes to" changes from `.dadaia/reports/**` to `specs/audits/<ts>/`. §11 evidence path statement is updated to explicitly enumerate all three channels. §12 anti-slop law encodes: "No fact in two channels; evidence paths are `.dadaia/handoff/` (agent↔agent) and `.dadaia/reports/` (user reports); audit results land in `specs/audits/`."

**D3 — Dispatcher purity as law (§9):** Add an explicit clause to §9 (Coordinator + Sub-Agent Architecture): "Only `project-manager` and `project-auditor` may dispatch sub-agents via the Agent tool. All other personas are workers — they reply only to their dispatcher and never invoke another agent." This closes the residual ambiguity about worker→worker dispatch (implied but never stated as law).

**D4 — Spec-review sequence in §11:** Add a sub-section to §11 covering the SPEC review ordering (distinct from the implementation gate sequence already encoded): `qa-engineer` reviews the SPEC first (mandatory) for testability and quality-gate clarity; `software-architect` may review in parallel (optional); only after `qa-engineer` APPROVE does `software-engineer` review PLAN/TASKS to confirm implementability. PM-mediated throughout. Sequential qa→SE (SE gate is never before QA).

**D5 — Relabel "gate" → "coordinator-enforced checkpoint" in §11:** The review "gates" (qa→commit, security→push, code-review→PR) are not mechanical shell blocks — they are PM-coordinated checkpoints enforced by the coordinator's discipline (PM will not advance the transition without the APPROVE handoff). The word "gate" stops being used in §11 for these transitions; replaced with "coordinator-enforced checkpoint" or "PM-mediated checkpoint." The mechanical gate (`sdd-spec-gate.sh`) still exists and is still called "gate" in its own context (the PreToolUse block is a mechanical gate; the review checkpoint is coordinator-enforced). This distinction must be clear in §11 wording.

**D6-law — Naming convention law in §8/§12:** Encode the collision-safe naming rule as law: any markdown produced by parallel sessions in `specs/audits/` must use the format `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/` for directories and `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>-<slug>.md` for files. §8 states this in the ADDITIVE section. §12 cites it as an anti-collision anti-slop mechanism.

**Implementation note:** All D2/D3/D4/D5/D6-law/D10/D13 additions are ADDITIVE to the existing §0–§14 structure. Existing section text is preserved verbatim (except §11 wording for D4/D5 which amends the existing gate sequence text). The milestone guard (no new lease mechanics beyond OQ-1..4) is unaffected — these additions are governance, topology, and identity law, not lease mechanics. The existing acceptance criteria §8 items 1–13 are all still required; soul-fold adds items 14–20 (see new tasks T-017-04..06).

---

## 10. Dependencies and risks

**Hard dependency:** T-016-10 (v0.1.6 committed and operator-validated) must be DONE
before T-017-01 begins. The constitution §8 cites the v0.1.6 lease model as implemented
fact. If v0.1.6 deviates from the design (OQ-1..4), T-017-01 must reconcile before
committing.

**Risks:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Author adds speculative lease mechanics beyond OQ-1..4 in constitution | HIGH | qa-engineer T-017-03 confirms no new lease mechanics; any addition beyond OQ-1..4 is a reject |
| §7 matrix internally inconsistent (missing self-host path or umbrella reconciliation) | MEDIUM | qa-engineer T-017-03 checks internal consistency; operator confirms lived-workflow match; constitution §7 is normative once committed |
| LINT-1 violations in existing atoms not diagnosed before T-017-03 | MEDIUM | T-017-02 includes fixing the 3 known doctor-error atoms before qa gate |
| `quality-assurance.md` frontmatter or section structure invalid | LOW | Atom authoring follows the memory atom contract section-by-section; LINT-1 is the acceptance gate |
| Constitution writes conflict with the memory RULE A gate | NONE | `specs/constitution.md` is not under `specs/memory/**`; RULE A does not apply |
