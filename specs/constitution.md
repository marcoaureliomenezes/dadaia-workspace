# Constitution — dadaia-workspace

This document is the permanent product law for `dadaia-workspace`. Agents and
contributors must read it before changing architecture, public agentic assets,
SDD behavior, memory, or distribution rules.

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
| 4 | Audit | project-auditor | `.dadaia/reports/**` | ADDITIVE | no lease — parallel |
| 5 | Release definition (SPEC/PLAN/TASKS) | product-engineer | `specs/releases/<id>/**` | MUTATING | acquires the release lease |
| 6 | Implementation | software-engineer | `repos/<ctx>/` prod + tests (or `dadaia_workspace/**` when dadaia-workspace is the bound context) | MUTATING | holds the release lease |
| 7 | Review gates (qa→commit · security→push · code-review→PR) | qa-engineer · security-reviewer · code-reviewer | `.dadaia/handoff/**` · `.dadaia/reports/**` | ADDITIVE evidence; gates transitions | no lease — they vote |
| 8 | Closure (memory + ACTIVE) | product-engineer | `specs/memory/**`, `CLOSURE.md`, `ACTIVE.md` | MUTATING | holds until release; then releases |

Exactly one MUTATING actor per context at a time (phases 5/6/8), serialized by one
lease that project-manager coordinates. ADDITIVE actors (1/2/3/4/7) run in parallel
and never touch the lease.

The 4-row summary in v0.2.0/SPEC.md §3 maps to phases {1,2}/{3,4}/{5,6,8}/{7};
constitution §7 is normative.

## 8. Concurrency Model

Two activity classes partition every action in the workspace. The partition is
simultaneously the lock model, the agent-coordination model, and the lifecycle.

**ADDITIVE phases (1/2/3/4/7):** write targets are `specs/backlog/**`,
`specs/bugs/**`, `.dadaia/reports/**`, `.dadaia/handoff/**`. No lease required.
Concurrent sessions allowed. Gate allows unconditionally for these paths.

**MUTATING phases (5/6/8):** write targets are `specs/releases/<id>/**`, the
active context's production tree (`repos/<ctx>/` for a consumer repo, or
`dadaia_workspace/**` when dadaia-workspace is the bound context), and
`specs/memory/**`. Exactly one active lease per context. Gate blocks on
live-lease conflict.

The lease record schema (as implemented in v0.1.6):
`{context, release, session_id, mode, acquired_at, heartbeat, ttl}`. No PID
field. Liveness = `now − heartbeat ≤ ttl` (TTL = 1800s). Heartbeat renewed on
every PreToolUse event by the actively-working holder. A fully-idle holder is
reclaimable after TTL. Fail-safe: the gate never blocks on an expired or absent
lease — it heals and allows. Acquire mechanism: `O_EXCL` CAS (atomic file
creation; second caller gets EEXIST and is blocked).

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

## 11. Review-Gate Sequence

Gate sequence for every rc-N (ship) segment:

1. qa-engineer reviews → APPROVE verdict → commit to feature branch allowed.
2. security-reviewer reviews → APPROVE verdict → push to feature branch allowed.
3. code-reviewer reviews → APPROVE verdict → PR merge allowed.
4. product-engineer updates `specs/memory/**` → only after code-reviewer gate.

For alpha-N segments: qa-engineer gate only → commit. No push, no PR, no other
reviewers.

Each gate requires a handoff JSON with `"verdict": "APPROVED"`. A REJECT verdict
blocks the transition and re-opens the relevant implementation task (marker flipped
back to `[ ]`). The failing task stays `[ ]` until the fix is committed and the
gate is re-run.

Reviewer evidence lands exclusively in `.dadaia/handoff/<context>/` and
`.dadaia/reports/<context>/`. No `specs/releases/<id>/evidence/` subtree exists or
is authorized.

## 12. Anti-Slop Law

Three hard rules that apply to every artifact shipped in this workspace:

1. No agent, skill, rule, or workflow ships without a phase in the §7 matrix that
   it owns or gates. An artifact with no phase ownership is slop and must be
   removed.
2. No store is created without a GC mechanism. Every state file, lock, session
   record, or cache must have a defined expiry and a cleanup path.
3. No fact is recorded in two sources. The constitution is the single source of
   truth for lifecycle law; skills and personas cite it, never duplicate it.
   Evidence paths are `.dadaia/handoff/` and `.dadaia/reports/` only.

## 13. Memory Canon

The four authoritative memory areas that define the current state of the product:

- `specs/memory/architecture.md` — layer rules, module map, dependency contracts,
  ADRs, and agent topology.
- `specs/memory/product/**` — folder catalog: `index.md` (entry point with vision,
  users, catalog, capability-map, limits) + one `.md` atom per production feature.
- `specs/memory/tech-stack.md` — approved technologies, constraints, canonical
  commands.
- `specs/memory/product/quality-assurance.md` — test pyramid, layer taxonomy,
  CI job split, no-slop policy; single source of truth for quality architecture,
  absorbing `test-suite-architecture.md`.

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

Persona-existence rule: every surviving persona in `dadaia_workspace/public/agents/`
must reference a phase from the §7 matrix that it owns or gates. Personas for
removed agents must not exist in the public agents directory.
