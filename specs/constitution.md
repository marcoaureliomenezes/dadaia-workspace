---
specs_pattern_version: 4
constitution_version: 2.1.0
---

# Constitution — dadaia-workspace

Permanent product law. Agents and contributors read it before changing architecture,
public agentic assets, SDD behavior, memory, or distribution rules. Each article is a
binding, verifiable principle; mechanism and inventory live in the memory canon (§13)
and are cited, never duplicated (§12.3).

## 0. Identity & Definitions

`dadaia-workspace` is a multi-AI-harness, multi-project, SDD-oriented, multi-agent
development workspace. Its product is workspace-level context-engineering: it orients a
generic agent fleet so the fleet can build many projects safely, in parallel, without
re-deriving how to work and without colliding. The normative vision lives in
[[product-vision]]; the operational layout and module map live in [[architecture]].

Definitions used by this law:

- **Spec Context Project** — one canonical specs folder bound to one repository;
  session-bindable. The bind → inject → enforce → parallel chain is the value spine
  (see [[spec-context-project]]).
- **Layer 1 (entry harness)** — the coding harness a human launches in a terminal.
  Governed by AGENTS.md read up-tree plus the projected per-harness asset trees.
- **Layer 2 (worker harness)** — the bounded workers a `dadaia lifecycle` verb
  (a dadaia-workflow: a Python body assembling fragment + persona + dynamic context
  per step) drives behind `AgentRuntimePort`, one harness/model selectable per step.
- **Harness roster invariant** — the concrete Layer-1 harness set, the Layer-2 worker
  set, and the `AgentRuntimeKind` members are enumerated in exactly ONE memory atom —
  `[[tech-stack]]` §Agent runtimes — which must stay set-equal to the code enum. This
  constitution never enumerates the rosters or the runtime-kind enum members;
  individual harness names (claude, codex, pi) may appear in prose where a law is
  harness-specific. **Claude Code is Layer-1-only**: a `claude-*`
  model id is never a Layer-2 worker (cost bound). Layer-2 model ids are
  allowlist-governed.
- **Persona / fragment** — a persona is a harness-universal role mandate injected into
  every Layer-2 step prompt (the Layer-2 equivalent of a Claude sub-agent persona);
  a fragment is the single-step instruction (inputs, task, output contract) injected
  into exactly one step prompt. Every model-driven step prompt carries both.
- **Harness isolation** — a workspace may be installed for any subset of the entry
  harnesses (`dadaia public install --target <t>`); scaffolding follows the choice.
  In a Codex or PI entry session, dadaia-workflows are the preferred execution path,
  defaulting the Layer-2 harness to the entry harness unless the operator overrides.
  Per-harness capability and scaffold truth lives in the `memory/product/harness/`
  atoms.

## 1. SDD Is Binding

Production changes require an approved release gate (`SPEC.md`, `PLAN.md`, `TASKS.md`,
each `**Status:** Aprovado`) and a reserved task before implementation. Bypass language
does not override the gate. (`Aprovado`, `Em revisão`, `Draft` are canonical status
tokens — never translated.)

**Operational-change lane (the only sanctioned `release: none` lane).** With
`ACTIVE.md` at `release: none`, ONLY these change classes may land: package version
metadata bumps, README/documentation-only changes, CI-infrastructure fixes, and
dependency bumps — each still requiring an explicit operator order, the sha-keyed
security-APPROVE push gate, and green CI. **Never release-less:** any change that
alters agent or product behavior, or that would require a `specs/memory/**` edit for
memory to stay true — **the memory-bearing test**. The PR #115 agent retier is the
named counter-example: it changed agent model assignments, so memory had to change,
so it required a release. An ungated span that nonetheless creates memory drift
obligates the NEXT release to carry a memory-truth pass. This lane is
judgment-enforced (human PR review + the reactive memory-truth obligation) — no
doctor invariant or hook can decide "memory-bearing" mechanically. Ratification
pointer: PRs #112/#113/#115 (landed release-less before this lane existed) are
ratified post-hoc by release v0.1.61 (see its SPEC §9 ADR-1 and CLOSURE).

## 2. Public Defaults Must Be Generic

Publicly distributed agents, skills, rules, workflows, hooks, templates, personas,
fragments, and AGENTS.md files must be safe for any user: no private project names,
hostnames, IPs, credentials, personal paths, or non-generic domain packs. Domain
knowledge belongs in optional packs or private overlays.

## 3. Memory Is Repository Truth

`specs/memory/**` is committed product memory describing the CURRENT product — never a
changelog (history belongs in release `CLOSURE.md` and `_archive/`). Memory source is
Markdown with frontmatter; generated formats are never committed as memory. A claim in
memory that the product does not honor is a defect of the same severity as failing
code.

## 4. Runtime Parity Must Be Honest

Projections and doctor output must describe only what each runtime actually enforces,
at both layers. Enforcement postures (which harness has pre-disk hooks, which relies on
git chokepoints, ring boundaries per worker runtime) are documented in
[[architecture]] and the `memory/product/harness/` atoms; no projection or doctor line
may claim enforcement a runtime does not perform. Harness-specific behavior is
expressed in that harness's native terms.

## 5. Source Repo Must Stay Clean

The source repository never tracks generated runtime projections, harness artefacts, or
tool caches at its root. Temporary files belong under the consumer workspace's
`.dadaia/tmp/` or system temp. Repos never contain `.dadaia/` or cache/state dirs.

## 6. Layering

Business behavior in `features/**`; runtime/I-O adapters in `infrastructure/**`; CLI
wiring in `cli/**`; pure models/protocols in `core/**`. `core` imports nothing from the
other layers and performs no I/O (authorized exceptions are named in [[architecture]]);
features import neither CLI nor infrastructure directly (ports + container injection);
cross-feature composition goes through the container. `container.py` is the sole
composition root.

## 7. Canonical Development Lifecycle

Every action belongs to one of eight phases. This table is normative.

| # | Phase | Owner | Writes to | Class | Concurrency |
|---|-------|-------|-----------|-------|-------------|
| 1 | Backlog definition | project-manager | `specs/backlog/**` | ADDITIVE | concurrent |
| 2 | Bug filing | any agent | `specs/bugs/**` (JSONL events) | ADDITIVE | concurrent |
| 3 | Research | PM-dispatched | `.dadaia/reports/**` | ADDITIVE | concurrent |
| 4 | Audit | project-auditor | `specs/audits/<ts>-<sid8>/` | ADDITIVE | concurrent |
| 5 | Release definition | product-engineer | `specs/releases/<id>/**` | MUTATING | advisory presence |
| 6 | Implementation | software-engineer | context production tree | MUTATING | advisory presence |
| 7 | Review gates | qa / security / code reviewers | handoffs + reports | ADDITIVE; gates transitions | concurrent |
| 8 | Closure | product-engineer | `specs/memory/**`, CLOSURE, ACTIVE | MUTATING | advisory presence |

MUTATING actors coordinate through workflow scope and task ownership. The workspace
does not serialize them: concurrent writes are allowed and surfaced through advisory
presence. Audit output is committed Markdown in
`specs/audits/` (channel 3, §11) named with the `<ts>-<session_id_8chars>` collision
convention; every audit generates exactly one remediation release that dispositions
every finding (fixed / superseded / deferred-with-reason) — no finding is silently
dropped, and an audit archives only when fully dispositioned by an approved release.

## 8. Concurrency Invariants

- No workspace lock, lease, acquisition, adoption, or steal operation exists.
- Races are accepted and surfaced, never prevented. MUTATING writes upsert caller-owned
  presence and may emit one throttled warning when another live session is present.
- Presence I/O is fail-open and can never block a write, commit, or workflow.
- ADDITIVE writes are always concurrency-independent, with collision-safe naming where
  trees are parallel-writable.
- READ mode is caller-local self-protection: it blocks only that caller's MUTATING file
  writes. Another session's bind or presence can never change the caller's mode.
- Pre-commit may warn about peer presence but always allows concurrency. Pre-push may
  block on missing CI or security-review evidence; this is a quality gate, not a lock.
- Context memory injection follows the session's own bind, never another session's.
- Mechanism (presence record, TTL cleanup, caller mode, classifier, hook order, tunables)
  lives in [[sdd-gate-v3]], [[context-management]], and `core/kernel_tunables.py`.

## 9. Coordinator + Sub-Agent Architecture

project-manager coordinates a release's MUTATING span through workflow state, task
ownership, and explicit write scopes. product-engineer and software-engineer run as PM
sub-agents with caller-scoped binds; peer presence is advisory only. Outside a release
span, ai-engineer may perform authorized surface fixes under the same no-lock model.
**Dispatcher purity:** only project-manager and project-auditor
dispatch sub-agents; every other persona is a worker that surfaces needs to its
dispatcher and never spawns agents.

## 10. Backlog → Release

project-manager curates `specs/backlog/**`. product-engineer, PM-dispatched (never
self-initiated), sanitizes stale items (`deferred`/`rejected` with reason — never
deleted), picks the bug + backlog set (open bugs and undispositioned audits outrank
plain backlog), and writes the SPEC. Every picked bug is solved unless a picked item
supersedes it (recorded, never silently dropped). A grill session on the picked set is
mandatory before the SPEC; PM does not unblock a release whose SPEC/PLAN/TASKS lack
`Aprovado`.

## 11. Checkpoints, Gates, and the Three Channels

A **checkpoint** is PM-mediated discipline (an APPROVE handoff required to advance); a
**gate** is a mechanical block (the merged PreToolUse gate and the git chokepoints).
Spec review: qa-engineer first (mandatory), software-architect parallel (optional),
software-engineer last. Implementation: qa APPROVE → commit; the push boundary is a
mechanical gate — every pushed sha requires an APPROVED security-reviewer handoff
sha-matched to that exact sha (stale approvals fail; deletions/tag-only exempt; the
carrying field is mechanism — [[sdd-gate-v3]], [[agent-comms]]);
code-review APPROVE → PR merge; memory updates only after the code-review checkpoint. A
REJECT re-opens the task (`[-]` → `[ ]`).

Exactly three report/comms channels: user reports (HTML) →
`.dadaia/reports/<ctx>/<agent>/`; agent↔agent handoffs (JSON) →
`.dadaia/handoff/<ctx>/`; audit results (committed Markdown) → `specs/audits/`. The
panel serves only channel 1. No `specs/releases/<id>/evidence/` subtree exists.

## 12. Anti-Slop Law

1. No agent, skill, rule, workflow, fragment, or persona ships without a §7 phase (or
   workflow step) it owns or gates; phase-less artifacts are removed. Plugin stubs are
   the named exemption (§14).
2. No store without a GC mechanism: every state file, lock, session record, or cache
   has a defined expiry and cleanup path.
3. No fact in two sources, no fact in two channels. The constitution states law once;
   memory states mechanism once; skills and personas cite, never duplicate. Injected
   context (fragments, personas, memory digests) carries no filler: text that does not
   change an agent's action is slop and is deleted.

## 13. Memory Canon

Authoritative memory: `specs/memory/architecture.md` (layers, module map,
topology) · `specs/memory/product/**` (one atom per production feature + `index.md`,
the **generated catalog TOC** — regenerated by `dadaia memory catalog generate`,
never hand-edited; vision/users/capability-map/limits live in
`product/philosophy/product-vision.md` + `harness/` carries per-harness truth) ·
`specs/memory/tech-stack.md` (approved tech; THE home of the harness/runtime roster) ·
`specs/memory/quality-assurance.md` (test architecture + CI split). Memory files are
snapshots, never changelogs; `Changelog`/`History`/`Histórico`/`Versions` sections are
forbidden. product-engineer is the sole memory author, writing in DEFINITION (new
atoms, with operator confirmation outside a release span) and CLOSURE (post-release
updates).

## 14. Agent Roster

Nine core agents; agents not listed are plugins.

| Agent | Phase | Class | Concurrency |
|-------|-------|-------|-------------|
| project-manager | 1–2 + coordinates MUTATING | ADDITIVE; coordinator | advisory presence |
| project-auditor | 4 | ADDITIVE | concurrent |
| product-engineer | 5 + 8 | MUTATING | caller-scoped bind |
| software-engineer | 6 | MUTATING | caller-scoped bind |
| qa-engineer | 7 → commit | ADDITIVE; votes | concurrent |
| security-reviewer | 7 → push | ADDITIVE; votes | concurrent |
| code-reviewer | 7 → PR | ADDITIVE; votes | concurrent |
| ai-engineer | AI-entity surface (`public/**`) | MUTATING | caller-scoped bind |
| software-architect | feeds 4/5 | ADDITIVE | concurrent |

Plugins (stubs, behavior-less until their pack installs; exempt from §12.1):
frontend-engineer, design-specialist, devops-engineer. Every core persona in
`public/agents/` must own or gate a §7 phase; personas for removed agents must not
exist. Agents are generic AI implementations specialized only in their SDD role; all
project-domain knowledge lives in the bound context's `specs/`.

## 15. Governance

This constitution is versioned (`constitution_version`, semver). An amendment is a
release-gated change: MAJOR for a changed/removed article, MINOR for a new article or
substantive clarification, PATCH for wording. Amendment history lives in the amending
releases' CLOSURE files and `_archive/` — never inline in the articles. The
`specs doctor` invariants (including the no-roster-enumeration check) guard this law's
consistency with code and memory.
