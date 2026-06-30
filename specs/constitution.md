---
specs_pattern_version: 1
---

<!--
CONSTITUTION VERSION: 2.0.0  (ratified 2026-06-30, release v0.1.42)
Amendment history is NOT kept inline in the articles below. It lives in this header
block and in each release's CLOSURE.md. v2.0.0 = the truth-realignment rewrite:
the obsolete fourth-harness references (deleted from the product in v0.1.24) were removed
from the law; the harness/runtime roster single-sourced to memory ([[tech-stack]]); §8 mechanism moved to
memory ([[sdd-gate-v3]], [[context-management]]); §0 vision/layout moved to
[[product-vision]] / [[architecture]]; embedded dated amendments removed. See
specs/audits/20260630T021228Z-251bb5f3/ for the audit that motivated it.
-->

# Constitution — dadaia-workspace

This document is the permanent product law for `dadaia-workspace`: a small set of
durable, normative principles. It is **principle, not mechanism** — when a statement
would change because the *code* changed, it belongs in memory, not here. Agents and
contributors read it before changing architecture, public agentic assets, SDD behavior,
memory, or distribution rules. The human-readable vision is `[[product-vision]]`; the
current architecture is `[[architecture]]`; the approved toolchain and the canonical
harness/runtime roster are `[[tech-stack]]`.

## 0. Core Definitions

This article is **declarative**: it names the concepts the normative articles (§1–§14)
encode. It imposes no constraint of its own.

- **dadaia-workspace** is a multi-AI-harness × multi-project × SDD-oriented × multi-agent
  development workspace. Its product is not any one project's code: it is the
  workspace-level **context-engineering** that orients a generic agent fleet so those
  agents build many projects safely, in parallel, without re-deriving how to work.
- **Spec Context Project** (the keystone): one canonical `specs/` folder
  (`backlog/ bugs/ memory/ releases/` + `constitution.md` + `AGENTS.md`) bound to one
  repository. It is **bindable to a session**, and that chain is the whole product:
  **bind → inject → enforce → parallel-multi-project**. Binding injects the context's
  constitution + memory; the SDD lifecycle (§7) is enforced for every production write;
  and because each context carries exactly one MUTATING lease (§8), many contexts advance
  concurrently without collision.
- **The two agentic layers** (naming them is load-bearing; enforcement differs per layer):
  - **Layer 1 — the entry harness** a human launches in a terminal (Claude Code, Codex,
    or PI). It reads the workspace `AGENTS.md` + its projected assets and may call the
    `dadaia` CLI. Its deterministic enforcement is the per-harness PreToolUse + git-chokepoint
    posture of §8.
  - **Layer 2 — the worker harness** a `dadaia lifecycle` Python workflow drives behind the
    `AgentRuntimePort` seam (selectable per step via `--harness` / `--step-harness`). The
    **canonical set of Layer-2 worker runtimes and Layer-1 entry harnesses lives in
    `[[tech-stack]]` (§ Agent runtimes)** — the constitution does not enumerate them, so the
    law cannot drift from the code. Per-runtime enforcement posture is §8 + `[[sdd-gate-v3]]`.
- **Development phases**: work flows through the eight phases of §7, partitioned into
  **ADDITIVE** (parallel, never leased) and **MUTATING** (serialized under one lease)
  activity classes — the partition that is simultaneously the lock model and the
  coordination model.
- **Agent philosophy**: every agent is a generic AI implementation specialized **only** in
  its dadaia-workspace SDD role (which phase it owns or gates, how it interconnects, a
  minimal role skill-set). Agents hold **no project-domain knowledge** — that lives in the
  bound context's `specs/`. The same fleet works any project; only the injected context
  changes.

The workspace root, its allowed entries, and the `.dadaia/` operational layout are
described in `[[architecture]]`; root cleanliness is law under §5.

## 1. SDD Is Binding

`dadaia-workspace` is developed through release-lifecycle SDD. A production change requires
an approved release gate (`SPEC.md`, `PLAN.md`, `TASKS.md` with `**Status:** Aprovado`) and
a reserved task before implementation. Bypass language does not override the gate.

## 2. Public Defaults Must Be Generic

Publicly distributed agents, skills, rules, workflows, hooks, templates, and `AGENTS.md`
files must be safe for any user: no private project names, hostnames, IP addresses,
credentials, personal repo paths, or domain packs that are not general workspace behavior.
Domain-specific knowledge belongs in optional packs or private overlays.

## 3. Memory Is Repository Truth

`specs/memory/**` is committed product memory describing the **current** product state, not
a changelog. Historical detail belongs in release `CLOSURE.md` and archived release files.
Memory source is Markdown; `*.html`/`*.yaml`/`*.yml` are not committed as product memory.

## 4. Runtime Parity Must Be Honest

Every runtime projection (and `dadaia doctor` output, and `AGENTS.md` instructions) must
describe what that runtime **actually** enforces — never claim behavior a runtime does not
perform. This honesty clause binds both agentic layers. The concrete per-harness Layer-1
enforcement matrix and the Layer-2 worker-runtime ring posture are **mechanism**: they live
in `[[sdd-gate-v3]]`, governed by the invariants of §8. Harness-specific behavior is
expressed in that harness's native terms.

## 5. Source Repo Must Stay Clean

The workspace root and every repo working tree stay free of generated runtime projections,
harness artefacts, caches, and state directories (the projection dirs at root, `Makefile`,
coverage/cache/`test-results/`/`playwright-report/` anywhere, and `.dadaia/` **inside** any
repo). The root holds only its nine canonical entries (see `[[architecture]]`); the
`tmp-file-guardrail` rule governs temp output. Tooling runs with caches disabled or
redirected outside the repo.

## 6. Layering

Business behavior lives in `dadaia_workspace/features/**`, runtime and I/O adapters in
`dadaia_workspace/infrastructure/**`, CLI wiring in `dadaia_workspace/cli/**`, shared pure
models/protocols in `dadaia_workspace/core/**`. `core` imports from no other layer; feature
modules do not import CLI; cross-feature composition goes through the container or explicit
service contracts. The enforced import-contract set lives in `[[architecture]]`.

## 7. Canonical Development Lifecycle

Every action belongs to one of eight phases. This table is normative.

| # | Phase | Owner | Writes to | Activity class | Lease behavior |
|---|-------|-------|-----------|----------------|----------------|
| 1 | Backlog definition | project-manager | `specs/backlog/**` | ADDITIVE | no lease — parallel |
| 2 | Bug filing | any agent / auto | `specs/bugs/**` | ADDITIVE | no lease — parallel |
| 3 | Research | PM-dispatched | `.dadaia/reports/**` | ADDITIVE | no lease — parallel |
| 4 | Audit | project-auditor | `specs/audits/<ts>-<sid8>/` | ADDITIVE | no lease — parallel |
| 5 | Release definition (SPEC/PLAN/TASKS) | product-engineer | `specs/releases/<id>/**` | MUTATING | acquires the release lease |
| 6 | Implementation | software-engineer | production tree + tests | MUTATING | holds the release lease |
| 7 | Review gates (qa→commit · security→push · code-review→PR) | qa · security · code reviewers | `.dadaia/handoff/**` · `.dadaia/reports/**` | ADDITIVE evidence; gate transitions | no lease — they vote |
| 8 | Closure (memory + ACTIVE) | product-engineer | `specs/memory/**`, `CLOSURE.md`, `ACTIVE.md` | MUTATING | holds until release; then releases |

Exactly one MUTATING actor per context at a time (phases 5/6/8), serialized by one lease
project-manager coordinates. ADDITIVE actors (1/2/3/4/7) run in parallel and never touch
the lease. Audit output is committed Markdown in `specs/audits/` (channel 3 of §11), not
HTML and not `.dadaia/reports/`.

## 8. Concurrency Model — binding invariants

Two activity classes partition every action; the partition is simultaneously the lock
model, the coordination model, and the lifecycle. The **invariants** below are law; their
**mechanism** (the lease record schema, the O_EXCL CAS, the mode-resolution chain, TTL
tunables, the chokepoint probe chains, and the per-harness enforcement matrices) lives in
`[[sdd-gate-v3]]` (gate + git chokepoints) and `[[context-management]]` (lease + session
mode), and must not be restated here.

1. **ADDITIVE never leased.** Writes to `specs/backlog|bugs|audits/**`,
   `.dadaia/reports|handoff/**` require no lease and allow concurrent sessions. Path classes
   are computed context-relative (the same `specs/` taxonomy applies inside every
   `repos/<slug>/`).
2. **Exactly one MUTATING lease per context.** Writes to `specs/releases/<id>/**`, the
   active production tree, and `specs/memory/**` serialize under a single per-context lease.
3. **Reclaim-iff-stale, yield-iff-live-foreign.** The gate reclaims an absent lease or one
   whose holder is provably dead; it yields informatively on a live foreign holder. It
   **never** instructs the operator to rebind, relaunch, or steal a session.
4. **READ is non-acquiring.** A session whose resolved mode is READ never takes, renews, or
   steals a lease; its ADDITIVE writes still flow.
5. **Deterministic at the chokepoints.** PreToolUse enforcement is one merged, fail-open
   entrypoint (root-whitelist → venv-guard → SDD gate; PROTECTED `.dadaia/sessions/` is the
   sole fail-closed path). Because the gate does not parse shell strings, the lifecycle
   outcomes that matter are also gated at git-hook chokepoints (pre-commit lease gate;
   pre-push CI-preflight + security-verdict) that run regardless of any harness hook.
6. **The hook reads no SDD artifacts.** It enforces path-class × lease × memory-phase × mode
   only; `Aprovado` gates and `[-]` task reservations are agent/PM discipline (§1, §11).

## 9. Coordinator + Dispatcher Purity

project-manager is the lease coordinator. On entering a release's MUTATING span (phase 5) PM
acquires ONE lease keyed to its coordinator session and holds it through 5 → 6 → 8;
product-engineer and software-engineer run as PM sub-agents under that single lease and never
independently bind. The writer role moves between sub-agents by PM dispatch; the lease never
changes hands, so cross-phase deadlock is structurally impossible. Carve-out: outside a
release span, ai-engineer may take its own short MUTATING lease for surface fixes
(`dadaia_workspace/public/**`); the gate still enforces at most one holder per context.

**Dispatcher purity.** Only `project-manager` (lifecycle) and `project-auditor` (audit
fan-out) dispatch sub-agents. Every other persona is a worker that replies to its dispatcher
and never spawns another agent; a worker that needs another agent's work surfaces it to its
dispatcher.

## 10. Backlog & Release Definition

project-manager is the sole curator of `specs/backlog/**`. PM consults open bugs + candidate
backlog and dispatches product-engineer to pick and define a release (never self-initiated by
PE). product-engineer sanitizes stale items (`deferred`/`rejected` with a reason — never
deletes a bug or backlog file), and every picked bug is solved unless a picked backlog item
supersedes it (recorded as `superseded_by:` + covered in TASKS). A `dadaia-grill-me` session
on the picked set is **mandatory before the SPEC is written**. The full process lives in the
`release-governance` rule and `[[sdd-bug-backlog-governance]]`.

## 11. Review Checkpoints & Report Channels

**Checkpoint vs gate.** Reviewer transitions are coordinator-enforced **checkpoints** (PM will
not advance without the reviewer's APPROVE handoff). "Gate" is reserved for the **mechanical**
enforcers — the merged PreToolUse gate and the git chokepoints. Do not conflate them.

- **Spec-review (phase 5):** qa-engineer reviews the SPEC first (mandatory; no SPEC advances
  without QA APPROVE); software-architect may review in parallel (optional); software-engineer
  reviews PLAN/TASKS last, after QA APPROVE.
- **Implementation:** qa APPROVE → commit; **push is a mechanical gate** — blocked unless an
  APPROVED `security-reviewer` handoff exists whose `metrics.commit_sha` equals each pushed
  sha; code-reviewer APPROVE → PR merge; product-engineer updates memory only after the
  code-review checkpoint. A REJECT re-opens the relevant task (`[-]`→`[ ]`). The mechanics live
  in the `release-governance` rule.

**The three report/comms channels** (exclusive, single canonical destination each):
1. **User reports** — HTML in `.dadaia/reports/<context>/<agent>/`; surfaced only by the panel.
2. **Agent↔agent** — JSON handoffs in `.dadaia/handoff/<context>/`; never served by the panel.
3. **Audit results** — committed Markdown in `specs/audits/<ts>-<sid8>/`.

No `specs/releases/<id>/evidence/` subtree exists or is authorized.

## 12. Anti-Slop Law

1. **No artifact without a phase.** No agent, skill, rule, or workflow ships without a §7 phase
   it owns or gates (the three plugin-agent stubs are exempt per §14 until their plugin ships).
2. **No store without a GC.** Every state file, lock, session record, or cache has a defined
   expiry and cleanup path.
3. **No fact in two sources, no fact in two channels.** The constitution is the single source
   for lifecycle law; memory is the single source for current product state (including the
   harness/runtime roster — see `[[tech-stack]]`); skills and personas cite, never duplicate.
   The three channels of §11 are exclusive. Parallel-written additive Markdown uses the
   collision-safe `<ts>-<sid8>` naming.

## 13. Memory Canon

The four authoritative memory areas defining current product state:

- `specs/memory/architecture.md` — layer rules, module map, dependency contracts, topology.
- `specs/memory/product/**` — `index.md` (the generated catalog TOC, kept in lockstep with
  `catalog.json`) + one atom per production feature; the product vision, users, and limits
  live in `[[product-vision]]`.
- `specs/memory/tech-stack.md` — approved technologies, the canonical harness/runtime roster,
  constraints, canonical commands.
- `specs/memory/quality-assurance.md` — test pyramid, layer taxonomy, CI split, no-slop policy.

Memory is the atomic snapshot of the present, not a changelog: the sections `Changelog`,
`History`, `Histórico`, `Versions` are forbidden in memory files. **product-engineer is the
sole author of all memory**, in the DEFINITION phase (for `quality-assurance.md` and new atoms,
with operator confirmation outside a release span) and the CLOSURE phase (updating atoms after
a release ships).

## 14. Agent Roster

Nine core agents define the lifecycle. This table is canonical; agents not listed are plugins.

| Agent | Phase | Activity class | Lease relationship |
|-------|-------|----------------|--------------------|
| project-manager | 1–2, coordinates all MUTATING phases | ADDITIVE (backlog/bugs); MUTATING coordinator | holds + coordinates + releases the release lease |
| project-auditor | 4 (audit) | ADDITIVE | no lease |
| product-engineer | 5 + 8 (definition, closure) | MUTATING | PM sub-agent; no independent acquire |
| software-engineer | 6 (implementation) | MUTATING | PM sub-agent; no independent acquire |
| qa-engineer | 7 gate → commit | ADDITIVE evidence; votes | no lease |
| security-reviewer | 7 gate → push | ADDITIVE evidence; votes | no lease |
| code-reviewer | 7 gate → PR | ADDITIVE evidence; votes | no lease |
| ai-engineer | surface owner (`dadaia_workspace/public/**`) | MUTATING under PM lease in releases; own short lease for ad-hoc surface fixes | gate blocks overlap with a PM lease |
| software-architect | feeds findings into phases 4/5 | ADDITIVE | no lease |

Plugins (not core, no §7 phase until their pack ships): frontend-engineer, design-specialist,
devops-engineer. Every surviving **core** persona in `dadaia_workspace/public/agents/` must
reference a §7 phase it owns or gates; personas for removed agents must not exist. The three
plugin stubs are exempt from the phase-ownership requirement (here and in §12.1) until installed.

## Governance

This constitution is versioned with semantic versioning in the header block above
(MAJOR = a redefinition or removal of a principle; MINOR = a new principle or materially
expanded guidance; PATCH = clarifications). Amendments are recorded **only** in that header and
in the amending release's `CLOSURE.md` — never as dated notes inside the articles. The
constitution is supreme over all other agent instructions; a more specific scoped rule may
tighten but never contradict it. Mechanism, schemas, enum values, and tunable constants are
never pinned here — they live in memory and code, which the law cites.
