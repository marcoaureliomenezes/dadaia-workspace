---
specs_pattern_version: 1
---

# Constitution — dadaia-workspace

This document is the permanent product law for `dadaia-workspace`. Agents and
contributors must read it before changing architecture, public agentic assets,
SDD behavior, memory, or distribution rules.

## 0. Identity & Core Concepts

This section defines what `dadaia-workspace` is and the vocabulary the rest of
this law uses. It is **declarative, not normative**: it imposes no new constraint;
it names the concepts that §1–§14 encode. The lifecycle (§7), the roster (§14),
the concurrency/lock contract (§8–§9), and the gate sequence (§11) are all
derivable from the definitions stated here.

The normative human-readable Product Vision is `docs/01_medium_codex.md`. It
describes the intended shape of the workspace — what it must be, its pillars, its
scaffold, its agent model, and its operating philosophy. This constitution
operationalizes that vision into binding law. When a detail is unclear in these
sections, agents and contributors must read `docs/01_medium_codex.md` first.

### What dadaia-workspace is

`dadaia-workspace` is a **multi-AI-harness × multi-project × SDD-oriented ×
multi-agent** development workspace. It runs the same agent fleet across more than
one AI coding harness (Claude Code, Codex, and — when installed — OpenCode), over
more than one software project at once, under Spec-Driven Development, coordinated
by a roster of specialized agents. Its product is not any single project's code: it
is the **workspace-level context-engineering** that orients an otherwise generic
agent fleet so those agents can build many projects safely, in an organized way,
and in parallel — without re-deriving how to work each time and without colliding
with one another.

### The Spec Context Project (the keystone concept)

The **Spec Context Project** is the central concept of dadaia-workspace, and the
unit through which all of the above is delivered. A Spec Context Project is **one
canonical specs folder bound to one repository**. The specs folder is a fixed
pattern — `backlog/`, `bugs/`, `memory/`, `releases/`, plus `constitution.md` and
`AGENTS.md` — and the repository is the code the specs govern.

A Spec Context Project is **bindable to a terminal session**. Binding is the value
chain that makes the workspace work:

1. **Bind** — a session attaches to one Spec Context Project (the active context).
2. **Inject** — binding injects that context's `constitution.md` and its `memory/`
   into the session, by **lazy product-feature consumption** (the constitution and
   the memory index load up front; individual feature atoms are pulled on demand,
   so a session is grounded without paying for the whole product catalog at once).
3. **Enforce** — the SDD lifecycle (§7) is enforced for every production write under
   that context: no production change without an approved release and a reserved task.
4. **Parallel multi-project** — because each context carries exactly one MUTATING
   lease (§8), multiple Spec Context Projects can be worked concurrently in different
   sessions, and ADDITIVE work within any context runs in parallel — safely, because
   the lock contract makes exactly-one-mutating-writer-per-context structural.

This bind → inject → enforce → parallel-multi-project chain is what lets a generic
agent fleet build real projects safely and in an organized way. Everything else in
this constitution is machinery in service of it.

### Development lifecycle phases

Work in a Spec Context Project flows through eight phases, partitioned into two
activity classes that determine concurrency:

- **ADDITIVE** phases run in parallel and never take a lease: backlog definition,
  bug filing, research, audit, and the review checkpoints. Their writes append
  evidence or candidates; they never mutate the product's source of truth.
- **MUTATING** phases serialize under exactly one lease per context: release
  definition (SPEC/PLAN/TASKS), implementation, and closure (memory + ACTIVE).

The full eight-phase matrix — owner, write target, activity class, and lease
behavior per phase — is the normative §7. The concurrency contract that partitions
them is §8; the coordinator model that holds the single lease across the MUTATING
span is §9.

### Agent philosophy

dadaia-workspace agents are **generic AI implementations specialized only in their
dadaia-workspace SDD role.** An agent's expertise is: how it fits the lifecycle,
which phases it owns or gates, how it interconnects with the other agents, and a
minimal set of role-tailored skills carried by a context-engineered system prompt.
Agents hold **no project-domain knowledge** — that lives entirely in the bound Spec
Context's `specs/` (constitution + memory). The same fleet therefore works any
project; only the injected context changes.

Each agent is specialized along one axis:

- **ai-engineer** — the multi-harness AI-entity surface: agent personas, skills,
  rules, workflows, hooks, and the context-engineering that drives them.
- **product-engineer** — specs and memory: SPEC/PLAN/TASKS/CLOSURE, the memory
  canon, and anti-slop guardianship of the single-source-of-truth law.
- **project-manager** — the full lifecycle as coordinator: it knows every agent's
  attributions and acts as the delegator that holds and routes the release lease.
- **software-engineer** — production code under TDD and SDD task discipline.

The remaining core agents (project-auditor, qa-engineer, security-reviewer,
code-reviewer, software-architect) are each specialized to the phase they own or
gate in §7. The canonical roster is §14; the dispatcher-purity rule (only
project-manager and project-auditor dispatch sub-agents) is §9.

### Value proposition

An operator chooses dadaia-workspace because it turns a generic agent fleet into a
disciplined, parallel, multi-project software team: bind a context, and the
constitution and memory orient the agents, the SDD gate keeps them honest, and the
single-lease concurrency model lets several projects advance at once without
collision or re-derivation.

### Workspace root & operational layout

The workspace root is not a git repo. The nine allowed root entries are:

1. `.agents/` — universal agent assets and shared skills.
2. `.claude/` — Claude Code projection.
3. `.codex/` — Codex projection.
4. `.dadaia/` — operational data for the workspace.
5. `.opencode/` — OpenCode projection.
6. `repos/` — alive repos associated with Spec Context Projects.
7. `AGENTS.md` — root workspace rules (the primary agent instruction file).
8. `CLAUDE.md` — required Claude Code bridge. Claude Code does not read `AGENTS.md`
   natively (per official Claude Code documentation); a root `CLAUDE.md` containing
   `@AGENTS.md` is the correct import bridge. This entry is therefore mandatory
   for Claude Code users and is authorized as a permanent root entry.
9. `prompt.md` — optional human-created long prompt file for operator use.

Agents must not create extra root files or directories. Human-created exceptions are
allowed, but default agent behavior must preserve root cleanliness. This list
supersedes any prior "under investigation" or "T-SANI-02 pending" stance on
`CLAUDE.md` or `prompt.md`.

`.dadaia/` is the operational home for the workspace runtime. Authorized
sub-directories:

- `.dadaia/.venv/` — workspace Python environment and CLI dependencies.
- `.dadaia/handoff/` — machine-readable agent-to-agent communication (JSON).
- `.dadaia/reports/` — human-readable HTML reports served by the panel.
- `.dadaia/states/` — JSON state for workspace features (read via CLI, not direct edit).
- `.dadaia/tmp/` — temporary output and short-lived agent artifacts.
- `.dadaia/mcps/` — working areas for MCP-style tooling when needed (reserved).

## 1. SDD Is Binding

`dadaia-workspace` is developed through release-lifecycle SDD. Production
changes require an approved release gate (`SPEC.md`, `PLAN.md`, `TASKS.md`) and
task ownership before implementation. Bypass language does not override the
gate.

## 2. Public Defaults Must Be Generic

Publicly distributed agents, skills, rules, workflows, hooks, templates, and
AGENTS.md files must be safe for any user. They must not contain private
project names, hostnames, IP addresses, credentials, personal repo paths, or
domain packs that are not general workspace behavior.

Domain-specific knowledge belongs in optional packs or private overlays. The
default public install ships only generic workspace, SDD, engineering, review,
security, design, frontend, backend, QA, DevOps, research, and orchestration
capabilities.

## 3. Memory Is Repository Truth

`specs/memory/**` is committed product memory. It describes the current product
state, not a changelog. Historical detail belongs in release `CLOSURE.md` and
archived release files.

Memory source is Markdown. `specs/memory/**/*.html`, `*.yaml`, and `*.yml` are
legacy or generated formats and must not be committed as product memory.

## 4. Runtime Parity Must Be Honest

Claude Code, Codex, and OpenCode projections must describe what each runtime
actually supports. Runtime adapters may differ, but doctor output and AGENTS.md
instructions must not claim behavior that the runtime does not enforce.

Claude Code = real block (enforced shell hook); Codex = guardrail in
trusted-workspace mode (advisory on untrusted Codex); opencode = advisory only.

Codex-specific behavior must be expressed in Codex-native terms: `AGENTS.md`
context, `.codex/config.toml`, `.codex/skills`, hooks where supported, and
deferred tool discovery for multi-agent capability.

## 5. Source Repo Must Stay Clean

The `dadaia-workspace` source repository must not track generated local runtime
projections or harness artefacts at its root, including `.dadaia/`, `.agents/`,
`.claude/`, `.codex/`, `.opencode/`, `CLAUDE.md`, `opencode.json`, `Makefile`,
root `playwright.config.ts`, `playwright-report/`, and `test-results/`.

Temporary files belong under `.dadaia/tmp/` in a consumer workspace or external
system temp directories, never as source-root artefacts.

## 6. Layering

Business behavior lives in `dadaia_workspace/features/**`, runtime and I/O
adapters in `dadaia_workspace/infrastructure/**`, CLI wiring in
`dadaia_workspace/cli/**`, and shared pure models/protocols in
`dadaia_workspace/core/**`.

`core` does not import from features, infrastructure, or CLI. Feature modules do
not import CLI modules. Cross-feature composition goes through the container or
explicit service contracts.

## 7. Canonical Development Lifecycle

Every action in this workspace belongs to one of eight phases. This table is the
normative source once committed. The consolidated roadmap §1 is supporting context
(genesis traceability) only — it is not an ongoing gate.

| # | Phase | Owner | Writes to | Activity class | Lease behavior |
|---|-------|-------|-----------|----------------|----------------|
| 1 | Backlog definition | project-manager | `specs/backlog/**` | ADDITIVE | no lease — parallel |
| 2 | Bug filing | any agent / auto | `specs/bugs/**` | ADDITIVE | no lease — parallel |
| 3 | Research | researcher / PM-dispatched | `.dadaia/reports/**` | ADDITIVE | no lease — parallel |
| 4 | Audit | project-auditor | `specs/audits/<ts>-<session_id_8chars>/` | ADDITIVE | no lease — parallel |
| 5 | Release definition (SPEC/PLAN/TASKS) | product-engineer | `specs/releases/<id>/**` | MUTATING | acquires the release lease |
| 6 | Implementation | software-engineer | `repos/<ctx>/` prod + tests (or `dadaia_workspace/**` when dadaia-workspace is the bound context) | MUTATING | holds the release lease |
| 7 | Review gates (qa→commit · security→push · code-review→PR) | qa-engineer · security-reviewer · code-reviewer | `.dadaia/handoff/**` · `.dadaia/reports/**` | ADDITIVE evidence; gates transitions | no lease — they vote |
| 8 | Closure (memory + ACTIVE) | product-engineer | `specs/memory/**`, `CLOSURE.md`, `ACTIVE.md` | MUTATING | holds until release; then releases |

Exactly one MUTATING actor per context at a time (phases 5/6/8), serialized by one
lease that project-manager coordinates. ADDITIVE actors (1/2/3/4/7) run in parallel
and never touch the lease.

The 4-row summary in v0.2.0/SPEC.md §3 maps to phases {1,2}/{3,4}/{5,6,8}/{7};
constitution §7 is normative.

Audit output (phase 4) is **committed Markdown** in the Spec Context's
`specs/audits/` tree — not HTML, not `.dadaia/reports/`. This is channel 3 of the
report/comms model (§11): the project-auditor's findings are versioned alongside the
specs they audit.

## 8. Concurrency Model

Two activity classes partition every action in the workspace. The partition is
simultaneously the lock model, the agent-coordination model, and the lifecycle.

**ADDITIVE phases (1/2/3/4/7):** write targets are `specs/backlog/**`,
`specs/bugs/**`, `specs/audits/**`, `.dadaia/reports/**`, `.dadaia/handoff/**`. No
lease required. Concurrent sessions allowed. Gate allows unconditionally for these
paths.

**Collision-safe naming for parallel additive output.** Because additive phases
allow concurrent sessions, any Markdown written into a parallel-writable additive
tree (`specs/audits/`, and any future parallel additive tree) MUST carry a session
discriminator so two concurrent sessions never collide on a path:

- Directories: `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/`
- Files: `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>-<slug>.md`

(`specs/backlog/**` is exempt because `project-manager` is its sole writer; the rule
binds wherever multiple sessions may write the same tree.)

**MUTATING phases (5/6/8):** write targets are `specs/releases/<id>/**`, the
active context's production tree (`repos/<ctx>/` for a consumer repo, or
`dadaia_workspace/**` when dadaia-workspace is the bound context), and
`specs/memory/**`. Exactly one active lease per context. Gate blocks on
live-lease conflict.

The lease record schema (as implemented in v0.1.6):
`{context, release, session_id, mode, acquired_at, heartbeat, ttl}`. No PID
field. Liveness = `now − heartbeat ≤ LEASE_TTL_SECONDS` where
`LEASE_TTL_SECONDS = 120` (short-heartbeat liveness — OQ-1 operator decision
2026-06-06, superseding the earlier 1800s value). Heartbeat is renewed on every
PreToolUse event by the actively-working holder; a fully-idle holder is reclaimable
after ~120s. Stable session identity is carried by
`.dadaia/sessions/runtime/<id>.ptr`, so a relaunched or continuing session resolves
to the same identity and RENEWs its own lease rather than self-blocking. Acquire
mechanism: `O_EXCL` CAS (atomic file creation; the second caller gets EEXIST).

Lock resolution is **reclaim-iff-stale, yield-iff-live-foreign**: the gate reclaims
and heals on an absent or expired lease (it never blocks on a stale or missing
lease); on a live foreign lease it yields informatively. The gate **never** instructs
the operator to rebind, relaunch, or steal a session — that instruction is forbidden
law. Context resolves automatically from the registry; the flow is never halted to
ask the operator to bind.

## 9. Coordinator + Sub-Agent Architecture

project-manager is the lease coordinator for a release. When a release enters its
MUTATING span (phase 5), PM acquires ONE lease keyed to PM's coordinator session
and holds it through phases 5 → 6 → 8. product-engineer and software-engineer run
as PM sub-agents under that single lease. They never independently bind a session,
so there is no session handoff and no second lock. This is how deadlocks between
sessions in different lifecycle phases are structurally impossible — the writer
role moves between sub-agents by PM dispatching the next one; the lease never
changes hands.

Exactly-one-lease invariant: at most one MUTATING holder per context at any time.
The `session_id` always stays as PM's coordinator session throughout the release.

Carve-out: outside a release span, ai-engineer (only) may take its own short
MUTATING lease for surface fixes (`dadaia_workspace/public/**`). This never
overlaps a PM-held release lease because a release in flight holds the only lease
for the context; ai-engineer's ad-hoc lease is blocked by the gate if a PM lease
is live. The exclusivity invariant is preserved: the gate enforces at most one
holder regardless of whether the holder is PM or ai-engineer.

**Dispatcher purity.** Only `project-manager` (lifecycle coordination) and
`project-auditor` (audit fan-out) may dispatch sub-agents via the Agent tool. All
other personas are workers — they reply only to their dispatcher and never invoke
another agent. A worker that perceives a need for another agent's work surfaces it
to its dispatcher; it never spawns the agent itself. This closes worker→worker
dispatch as a structural impossibility and keeps the dispatch topology auditable.

## 10. Backlog-Definition Process

project-manager is the sole owner of `specs/backlog/**`. The process:

1. PM consults `specs/bugs/` (status: open) + `specs/backlog/` (status:
   candidate/idea).
2. PM dispatches product-engineer to pick and define the release (never
   self-initiated by PE).
3. product-engineer sanitizes stale/invalid items (marks `deferred` or `rejected`
   with a `reason:` field; never deletes bug or backlog files).
4. product-engineer picks the bug + backlog set; every picked bug is solved in the
   release unless a picked backlog item supersedes it — in that case record
   `superseded_by: <backlog-slug>` in the bug's frontmatter, add a note in the
   SPEC, and ensure the backlog item's TASKS cover the bug's acceptance criteria.
   A bug is never silently dropped.
5. A `dadaia-grill-me` session on the picked set is mandatory before the SPEC is
   written. PM will not advance a release to SPEC without it.
6. product-engineer writes the SPEC.md Draft; PM does not unblock the release
   until SPEC has `**Status:** Aprovado`.

## 11. Review Checkpoints & Report Channels

### Terminology — checkpoint vs gate

The reviewer transitions below are **coordinator-enforced checkpoints**, not
mechanical blocks. They are enforced by `project-manager`'s discipline: PM will not
advance a transition without the reviewer's APPROVE handoff. The word "gate" is
reserved in this constitution for the genuinely **mechanical** enforcers — the SDD
path gate (`sdd-spec-gate.sh` PreToolUse block) and the pre-push CI gate
(`dadaia ci preflight`). A checkpoint is PM-mediated; a gate is a shell block. Do
not conflate them.

### Spec-review sequence (release-definition checkpoints)

During release definition (phase 5), the SPEC and its PLAN/TASKS pass a review
ordering distinct from the implementation checkpoints below:

1. **qa-engineer reviews the SPEC first (mandatory)** — for testability and
   quality-checkpoint clarity. No SPEC advances without QA APPROVE.
2. **software-architect may review in parallel (optional)** — for architectural
   soundness; runs alongside QA, never blocking it.
3. **software-engineer reviews LAST (after QA APPROVE)** — confirms PLAN/TASKS are
   implementable.

The ordering is sequential QA → SE (SE never reviews before QA APPROVE); the
architect review is parallel and optional. PM mediates throughout.

### Implementation checkpoints (rc-N ship segment)

1. qa-engineer reviews → APPROVE verdict → commit to feature branch allowed.
2. security-reviewer reviews → APPROVE verdict → push to feature branch allowed.
3. code-reviewer reviews → APPROVE verdict → PR merge allowed.
4. product-engineer updates `specs/memory/**` → only after the code-reviewer
   checkpoint.

For alpha-N segments: qa-engineer checkpoint only → commit. No push, no PR, no
other reviewers.

Each checkpoint requires a handoff JSON with `"verdict": "APPROVED"`. A REJECT
verdict blocks the transition and re-opens the relevant implementation task (marker
flipped back to `[ ]`). The failing task stays `[ ]` until the fix is committed and
the checkpoint is re-run.

### The three report/comms channels

dadaia-workspace has exactly three report/communication channels, each with a single
canonical destination:

1. **User reports** — HTML, written to `.dadaia/reports/<context>/<agent>/`. These
   are for human consumption and are surfaced exclusively by the panel. The panel
   serves **only** `.dadaia/reports/` HTML — it never surfaces `.dadaia/handoff/` JSON.
2. **Agent↔agent communication** — JSON handoffs, written to
   `.dadaia/handoff/<context>/` only. This is the machine-readable contract between
   agents. Handoff JSON is **never** served by the panel, never shown in the UI, and
   never written to `.dadaia/reports/`. Its sole purpose is agent-to-agent structured
   communication.
3. **Audit results** — committed Markdown, written to
   `specs/audits/<ts>-<session_id_8chars>/` (archive: `specs/audits/_archive/`).

The panel surfaces: contexts, user HTML reports, registered servers, sessions,
workflows, agents, and workspace state. It does not surface handoffs.

Reviewer checkpoint evidence lands in channels 1 and 2 only. No
`specs/releases/<id>/evidence/` subtree exists or is authorized.

## 12. Anti-Slop Law

Three hard rules that apply to every artifact shipped in this workspace:

1. No agent, skill, rule, or workflow ships without a phase in the §7 matrix that
   it owns or gates. An artifact with no phase ownership is slop and must be
   removed. (Exception: the three plugin-agent stubs are exempt per the §14
   plugin-stub exemption — they intentionally own no phase until their plugin is
   installed.)
2. No store is created without a GC mechanism. Every state file, lock, session
   record, or cache must have a defined expiry and a cleanup path.
3. No fact is recorded in two sources, and no fact in two channels. The
   constitution is the single source of truth for lifecycle law; skills and personas
   cite it, never duplicate it. The three report/comms channels (§11) are exclusive:
   user reports → `.dadaia/reports/`; agent↔agent → `.dadaia/handoff/`; audit results
   → `specs/audits/`. Markdown written by parallel sessions into a parallel-writable
   additive tree (e.g. `specs/audits/`) MUST use the collision-safe
   `<ts>-<session_id_8chars>` naming convention of §8, so two concurrent sessions
   never overwrite each other.

## 13. Memory Canon

The four authoritative memory areas that define the current state of the product:

- `specs/memory/architecture.md` — layer rules, module map, dependency contracts,
  ADRs, and agent topology.
- `specs/memory/product/**` — folder catalog: `index.md` (entry point with vision,
  users, catalog, capability-map, limits) + one `.md` atom per production feature.
- `specs/memory/tech-stack.md` — approved technologies, constraints, canonical
  commands.
- `specs/memory/quality-assurance.md` — test pyramid, layer taxonomy,
  CI job split, no-slop policy; single source of truth for quality architecture,
  absorbing `test-suite-architecture.md`. This file lives at top level in `memory/`,
  not under `memory/product/`.

Memory files are the atomic snapshot of the current product. They are NOT
changelogs. Historical detail belongs in release `CLOSURE.md` and archived release
files. Forbidden sections in memory files: `Changelog`, `History`, `Histórico`,
`Versions`.

product-engineer is the sole author of all memory files. Write permission is
granted in DEFINITION phase (for quality-assurance.md and new atoms created outside
a release span with operator confirmation) and in CLOSURE phase (for updating atoms
after a release ships).

## 14. Agent Roster

Nine core agents define the agentic development lifecycle. This table is the
canonical roster. Agents not listed here are plugins, not core.

| Agent | Phase | Activity class | Lease relationship |
|-------|-------|----------------|--------------------|
| project-manager | 1–2, coordinates all MUTATING phases | ADDITIVE (backlog/bugs); MUTATING coordinator | holds + coordinates + releases the release lease |
| project-auditor | 4 (audit) | ADDITIVE | no lease |
| product-engineer | 5 + 8 (definition, closure) | MUTATING | PM sub-agent; no independent acquire |
| software-engineer | 6 (implementation) | MUTATING | PM sub-agent; no independent acquire |
| qa-engineer | 7 gate → commit | ADDITIVE evidence; votes | no lease |
| security-reviewer | 7 gate → push | ADDITIVE evidence; votes | no lease |
| code-reviewer | 7 gate → PR | ADDITIVE evidence; votes | no lease |
| ai-engineer | surface owner (`dadaia_workspace/public/**`) | MUTATING under PM lease during releases; own short lease for ad-hoc surface fixes | PM sub-agent when part of a release; own short MUTATING lease outside release spans (gate blocks overlap with PM lease) |
| software-architect | feeds findings into phases 4/5 | ADDITIVE | no lease |

Plugins (not in core roster): frontend-engineer, design-specialist, devops-engineer.
Plugin agents may be dispatched within a release but do not appear in the roster
table above.

Persona-existence rule: every surviving **core** persona in
`dadaia_workspace/public/agents/` must reference a phase from the §7 matrix that it
owns or gates. Personas for removed agents must not exist in the public agents
directory. **Plugin-stub exemption:** the three plugin agents (frontend-engineer,
design-specialist, devops-engineer) ship as thin behavior-less stubs in the core
install and are exempt from the phase-ownership requirement of this rule and of
§12.1 — they own no §7 phase by design and carry behavior only when their plugin is
installed.

Agent philosophy: every agent in this roster is a generic AI implementation
specialized only in its dadaia-workspace SDD role, carrying no project-domain
knowledge (that lives in the bound Spec Context's `specs/`). The per-agent
specialization axes and the value proposition are stated once in §0 "Agent
Philosophy"; this roster does not restate them.
