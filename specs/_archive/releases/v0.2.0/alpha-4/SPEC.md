# SPEC: v0.1.9 — Skills cleanup + workflow redesign + memory tree + surface cleanup

**Status:** Aprovado
**Release ID:** v0.1.9
**Owner:** product-engineer
**Created:** 2026-06-06
**Parent program:** v0.2.0 — Agentic Development Lifecycle
**Type:** Milestone SPEC — fourth sequenced milestone of the v0.2.0 program.

> **DEPENDS ON:** v0.1.8 must be committed and operator-validated. The v0.1.8 roster
> (9 core agents) must be final before any workflow or skill reference-strip can be
> verified clean. No task in this milestone may begin until T-018-09 is DONE.

---

## 1. Objective

Eliminate slop from the public agentic surface that is now justified by the frozen v0.1.7
constitution and the v0.1.8 roster. Concretely:

1. **Skills 22 → 17**: move the 5 frontend/design skills out of core (already removed from
   personas in v0.1.8; this milestone removes the source files and cleans the manifest).
   For each of the 17 remaining skills: a text-review pass that trims slop, removes dead
   references to deleted agents/workflows, and verifies the skill maps to a lifecycle phase
   or coordinator need defined in the v0.1.7 constitution.
2. **Workflow redesign**: delete all 7 stale pre-coordinator workflows. Author a new minimal
   set (`release-ship`, `audit-fanout`) that covers only deterministic sequences where a
   scripted file beats PM dispatch logic. Concurrently strip all references to the 7 deleted
   workflows from the 9 surviving personas and from `project-orchestration`.
3. **`product/` memory tree**: restructure the 26-file flat catalog into thematic
   subdirectories. Update `index.md` with wikilinks. project-auditor refines exact placement
   during this milestone's execution.
4. **Manifest + doctor reconcile**: after skills and workflows change, re-run
   `dadaia public stage && install --force --target all` and confirm `dadaia public doctor`
   exits 0 on all four runtimes (`.claude/`, `.agents/`, `.opencode/`, `.codex/`).

---

## 2. Skill surface delta

### 2.1 Skills moved to plugin (22 → 17)

The following 5 skills are removed from `dadaia_workspace/public/skills/` in this
milestone (their personas were already stripped in v0.1.8 — T-018-03):

| Skill slug | Reason for removal |
|---|---|
| `frontend-design` | Plugin-scoped per D2 (grill report). Core does not ship frontend. |
| `frontend-implementation-quality` | Same — frontend capability lives in the plugin. |
| `design-reference-research` | Same. |
| `design-report-quality-gate` | Same. |
| `ux-ui-review` | Same. |

These are not deleted from the product — they belong to the frontend/design plugin.
The core `public/skills/` directory must not contain them after this milestone.

### 2.2 Remaining 17 skills — text-review pass

Every remaining skill undergoes a **text-review pass** by `ai-engineer`. The review
enforces these criteria for each skill:

| Criterion | What to check |
|---|---|
| **Phase mapping** | The skill's `description` field or opening section must map it to one or more lifecycle phases from the v0.1.7 constitution §1 matrix (Backlog/Research/Definition/Implementation/Push/PR/Closure) or to a named coordinator need. No skill without a phase. |
| **Dead agent refs** | No reference to `software-engineer-python`, `software-engineer-node`, `backend-engineer`, `frontend-engineer` (as core), `design-specialist` (as core), `devops-engineer` (as core), or `researcher` outside an explicit plugin-scope note. |
| **Dead workflow refs** | No reference to `audit-cycle`, `code-review-fan-out`, `cross-cutting-feature`, `design-first-implementation`, `hotfix-release`, `spec-refinement`, `onboarding-new-repo`. |
| **Evidence store** | No reference to `specs/releases/<id>/evidence/` as a landing path. Evidence always lands in `.dadaia/handoff/` and `.dadaia/reports/` (A-1 from v0.1.7 constitution). |
| **Slop prose** | Remove paragraphs that re-state general knowledge the base model already has. Each prose block must carry workspace-specific instruction or workspace-specific data. |
| **Stale schema refs** | No reference to handoff schema versions prior to `handoff-v1.1`. No reference to `spec_contexts.json` v1 fields (`standby`, `is_selected`, `select`). |

The 17 skills to review:

| # | Skill slug | Primary lifecycle phase / coordinator need |
|---|---|---|
| 1 | `dadaia-step0-memory-bootstrap` | All phases — grounding before any work |
| 2 | `dadaia-workspace-doctor` | Platform / operational — invoked by any agent on workspace state |
| 3 | `dev-server-registry` | Implementation / platform — invoked when a dev server must be started |
| 4 | `ai-harness-claude-code` | ai-engineer / harness literacy (restricted scope) |
| 5 | `dadaia-handoff-emitter` | All phases — emitting evidence after any report |
| 6 | `ai-context-engineering` | ai-engineer / harness literacy (restricted scope) |
| 7 | `dadaia-workspace-manager` | Platform / context lifecycle — invoked for workspace state management |
| 8 | `ai-harness-codex` | ai-engineer / harness literacy (restricted scope) |
| 9 | `drift-detection` | Research/Audit — project-auditor memory↔implementation drift audit |
| 10 | `harness-primitives` | All-agent literacy — shared mental model of harness primitives |
| 11 | `dadaia-release-definition` | Definition phase — PE picks bugs+backlog set, grill, SPEC |
| 12 | `project-orchestration` | Coordinator — PM dispatch reference, agent inventory, playbooks |
| 13 | `dadaia-grill-me` | Definition phase — mandatory pre-SPEC refinement interview |
| 14 | `dadaia-workspace-spec-navigator` | All phases — resolving active context + release + spec order |
| 15 | `dadaia-release-closure` | Closure phase — CLOSURE.md template + memory update protocol |
| 16 | `dadaia-task-manager` | Implementation phase — task marker protocol |
| 17 | `dadaia-workspace-spec-reviewer` | Definition/Review — consistency review of spec artifacts |

**Key high-priority reviews:**
- `project-orchestration` (SKILL.md): currently lists the 15-agent topology (stale),
  all 7 stale workflows in the inventory table, and references `software-engineer-python`,
  `backend-engineer`, `design-specialist` as peers in the Decision Authority table.
  These are the most critical dead-ref concentrations. This skill must be updated to
  the 9-agent topology and the new 2-workflow set, with the Decision Authority table
  trimmed to match.
- `dadaia-workspace-manager`: references lock primitives from before v0.1.6 (semaphore
  acquisition on `context bind`); must be verified clean after v0.1.6 ships.
- `dadaia-workspace-doctor`: references `product-auditor-agent` (non-existent; should
  be `project-auditor`). Must be corrected.
- `drift-detection`: references `memory/*.md` as "atomic HTML files" — must be updated
  to Markdown atoms (memory-markdown-source-v1).
- `dadaia-release-definition`: mentions `dadaia backlog list` and `dadaia bug list` CLI
  commands. **These commands do NOT exist** — the CLI only ships `dadaia backlog new` and
  `dadaia bug new` (see `dadaia_workspace/cli/commands/newartifacts.py`). T-019-05 item 5
  must replace both commands with "read `specs/bugs/*.md` directly" and "read
  `specs/backlog/*.md` directly" (direct file reads, no CLI command).

---

## 3. Workflow redesign

### 3.1 Delete 7 stale workflows

All 7 files below are deleted from `dadaia_workspace/public/workflows/`:

| File | Reason |
|---|---|
| `audit-cycle.workflow.md` | Predates coordinator strategy. Orchestration lives in PM dispatch logic. |
| `code-review-fan-out.workflow.md` | Predates segment-based review cadence (ADR-3). |
| `cross-cutting-feature.workflow.md` | Subsumed by single `software-engineer` under PM dispatch. |
| `design-first-implementation.workflow.md` | Frontend/design is plugin-scoped; not core. |
| `hotfix-release.workflow.md` | Flow is in the PE persona and SPEC §8. A scripted file is redundant. |
| `spec-refinement.workflow.md` | Subsumed by `dadaia-grill-me` skill. |
| `onboarding-new-repo.workflow.md` | Ad-hoc; not a deterministic sequence that benefits from a scripted file. |

**Precondition gate (D-OC-1):** before any deletion, `ai-engineer` audits every
surviving v0.1.8 persona and the `project-orchestration` skill for any remaining
reference to these 7 filenames or their workflow slugs. All references must be stripped
first (see §2.2 — `project-orchestration` is the biggest offender).

### 3.2 Author 2 new lifecycle-aligned workflows

Two new workflows are created (OD-1 resolution from v0.2.0 SPEC §5):

**`release-ship.workflow.md`** — covers the MUTATING deploy gate sequence:
- Scope: the deterministic portion of a release ship (post-RC approval through deploy).
- Steps: merge `feature/<version>` → `main`; verify pre-push CI gate passes (`dadaia ci
  preflight`); create tag `v<M>.<m>.<p>`; PyPI publish (`poetry publish`); post-publish
  smoke test (`pip install dadaia==<version>` in clean venv).
- This is a deterministic, no-judgment sequence. PM dispatches it; it does **not** replace
  PM's decision to ship (that decision lives in PM's persona — the workflow delegates
  the ship decision back to PM on any precondition failure or judgment fork).
- Cites §1 matrix: MUTATING class, release-closure phase.
- **Honesty note:** this is a dispatch-reference document. Claude Code and Codex do NOT
  auto-load `.claude/workflows/` files at runtime (per constitution §4). A workflow file
  is read by an agent when PM explicitly loads it as context. This note must appear in
  the workflow file itself so consumers are not misled.

**`audit-fanout.workflow.md`** — covers deterministic audit dispatch:
- Scope: the ordered sequence when `project-auditor` runs a full-workspace audit.
- Steps: bootstrap memory → run `dadaia public doctor` + `dadaia specs doctor` → project-auditor
  drift-detection (per feature scope) → findings handoff to PM → PM decides backlog or
  immediate release.
- This is deterministic and benefits from a scripted file because the step order is fixed
  and the output format (handoffs) is contractual.
- Cites §1 matrix: ADDITIVE class, Research/Audit phase.
- **Anti-duplication:** `audit-fanout.workflow.md` CITES the `drift-detection` skill for
  the drift protocol; it does NOT restate the drift-detection procedure inline (doing so
  would duplicate the skill and create a maintenance hazard).
- **Honesty note:** same as `release-ship` — this is a dispatch-reference document, not
  a Claude Code runtime primitive. The note must appear in the workflow file itself.

### 3.3 Reference strip from personas and `project-orchestration`

All 9 v0.1.8-authored core personas and `project-orchestration` must have every
reference to the 7 deleted workflows removed. This includes:
- Inventory tables listing the workflow by filename or slug.
- "Use the `<workflow>` workflow" instructions.
- Fallback references ("if the workflow is not available, ...").

After stripping and before deletion, `dadaia public doctor` D-OC-1 check must pass
(zero dangling workflow references in any persona or skill).

---

## 4. `product/` memory tree restructure

### 4.1 Current state

**Atom arithmetic (ground truth):**
- Today (`specs/memory/product/`): 24 product atoms + `index.md` (25 files total). The
  24 atoms include `test-suite-architecture.md` (physically present, superseded).
- v0.1.7 (T-017-02) adds `quality-assurance.md` → 25 product atoms + `index.md`.
- `test-suite-architecture.md` is excluded from placement (see §4.2 and §4.3 handling
  rule). The remaining **24 atoms are placed into the 6 thematic subdirectories**.
- Placement total: `agents`:8 + `sdd`:5 + `panel`:2 + `platform`:6 + `distribution`:2 +
  `philosophy`:1 = **24**. Every AC and task count references this same number.

`specs/memory/product/` today is a flat directory navigated by file name only; a human
or agent trying to understand the product must read all entries or guess slugs. The v0.2.0
SPEC OD-3 resolution mandates a thematic tree.

### 4.2 Target tree

```
specs/memory/product/
├── index.md                  ← entry point (catalog, vision, users, capability-map, limits)
├── agents/                   ← AI-entity surface: personas, skills, rules, workflows, harness (8 atoms)
│   ├── agent-sdd-alignment.md  ← placed here; NOT in philosophy/ (see §4.3)
│   ├── agent-orchestration.md
│   ├── agent-monitoring.md
│   ├── agent-comms.md
│   ├── harness-primitives.md
│   ├── ai-harness-claude-code.md
│   ├── ai-harness-codex.md
│   └── ai-context-engineering.md
├── sdd/                      ← Spec-Driven Development system (5 atoms)
│   ├── sdd-gate-v3.md
│   ├── sdd-bug-backlog-governance.md
│   ├── sdd-hotfix-track.md
│   ├── specs-doctor.md
│   └── quality-assurance.md  ← new in v0.1.7; absorbs test-suite-architecture.md
├── panel/                    ← control surface UI (2 atoms)
│   ├── panel.md
│   └── brand-identity.md
├── platform/                 ← runtime infrastructure features (6 atoms)
│   ├── context-management.md
│   ├── workspace-init.md
│   ├── workspace-doctor.md
│   ├── workspace-portability.md
│   ├── server-registry.md
│   └── multi-platform-parity.md
├── distribution/             ← how the product ships and is distributed (2 atoms)
│   ├── public-asset-distribution.md
│   └── academy.md
└── philosophy/               ← foundational reference (1 atom)
    └── repos-catalog.md
```

**`agent-sdd-alignment.md` placement (authoritative):** placed in `agents/` — it
describes an AI-entity capability (how agents relate to SDD lifecycle). project-auditor
may confirm or move it during T-019-06, but it appears in the tree ONCE only. The
`philosophy/` group in §4.2 does NOT list it (double-listing removed).

**`philosophy/` single-atom note:** one atom (`repos-catalog.md`) is justified here
because it is a pure reference lookup with no natural fit in the 5 other groups.
project-auditor applies the criterion during T-019-06: "no orphan single-file thematic
group unless justified; if unjustified, merge into the nearest group." An explicit
justification must appear in the auditor handoff.

**`test-suite-architecture.md` handling:** this atom is physically present until its
`git mv` to `specs/_archive/legacy-memory/<timestamp>/` is executed as part of v0.1.9
(AC-9 handling rule below). Its superseded status makes placement ambiguous. Rule: it is
placed in `sdd/` with a `SUPERSEDED` banner in its frontmatter, then archived via
`git mv` in the same T-019-06 commit. It does NOT appear as a regular atom in the
catalog. AC-9 "nothing flat but index.md" is satisfied when this atom is either archived
or placed in a subdir (either treatment is acceptable; archiving is preferred).

**`quality-assurance.md` dependency:** this atom must exist before T-019-06 begins
(created by T-017-02). If it does not exist, T-019-06 is blocked. PE confirms this as
part of the T-019-06 precondition check.

### 4.3 Placement review by project-auditor

During T-019-06, project-auditor reads each of the 24 placed atoms and proposes
adjustments where the placement is ambiguous. The criteria:
- Place by primary concern, not by implementation dependency.
- An atom about an AI-entity capability belongs in `agents/`.
- An atom about an SDD process or governance belongs in `sdd/`.
- An atom about a UI control surface belongs in `panel/`.
- An atom about a runtime platform service belongs in `platform/`.
- An atom about how the product is distributed or installed belongs in `distribution/`.
- Philosophy / foundational reference belongs in `philosophy/`.
- If an atom genuinely spans two groups, it belongs in its primary group and links to
  the secondary via a wikilink.
- No orphan single-file thematic group unless explicitly justified in the auditor
  handoff (criterion: "merge into nearest group" unless the atom's primary concern
  is genuinely orthogonal to all 5 other groups).

### 4.4 `index.md` update requirements

The updated `index.md` must contain:
- `## Vision` — 2–3 sentence atomic vision (no changelog).
- `## Users` — who operates this workspace.
- `## Catalog` — ordered list of all production features, grouped by thematic
  subdirectory, each linking to its Markdown atom via relative path
  (e.g. `[context-management](platform/context-management.md)`).
- `## Capability map` — fenced Mermaid flowchart of the feature surface, grouped by theme.
- `## Limits` — explicit non-goals (what the product is not).

Wikilinks between related atoms are encouraged where a reader of atom A is likely to
need atom B next. Format: `[[slug]]` or explicit relative link.

---

## 5. Manifest + `dadaia public doctor` reconcile

After all skill and workflow changes are committed, a final propagation step ensures:
- `dadaia public stage` succeeds (manifest rebuilt; no reference to deleted files).
- `dadaia public install --force --target all` propagates changes to all four runtimes.
- `dadaia public doctor` exits 0: exactly 17 skills enumerable, exactly 2 workflows
  enumerable, 9 agents on all runtimes. No orphan skills, workflows, or agents.
- `dadaia specs doctor` exits 0: memory tree valid, no broken wikilinks, no broken
  image references, `index.md` has all required sections, all atoms have required
  feature sections.

### Fresh-init parity check

After propagation, the operator runs `dadaia init` on a temporary empty directory and
confirms:
- The default projection emits exactly the 9 core agents.
- No plugin stubs (`frontend-engineer.md`, `design-specialist.md`, `devops-engineer.md`)
  appear in the core projection.
- Exactly 17 skills are projected.
- Exactly 2 workflows are projected.

---

## 6. Architecture and tech-stack deltas

No new Python code is written in this milestone. All changes are to Markdown files
under `dadaia_workspace/public/` and `specs/memory/product/`.

**Architecture delta:** none. The memory tree restructure does not change any runtime
behavior. `specs/memory/architecture.md` requires no update from this milestone.

**Tech-stack delta:** none.

---

## 7. Acceptance criteria

| ID | Criterion |
|---|---|
| AC-1 | Exactly 5 skill files are absent from `public/skills/` compared to v0.1.8 start: `frontend-design`, `frontend-implementation-quality`, `design-reference-research`, `design-report-quality-gate`, `ux-ui-review`. |
| AC-2 | Each of the 17 remaining skills has completed the text-review pass: no dead agent refs, no dead workflow refs, no evidence-subtree refs, phase mapped. |
| AC-3 | `project-orchestration` Agent Inventory table lists exactly 9 agents matching the v0.1.7 constitution roster. Decision Authority table cites only those 9. Workflow Inventory table lists exactly 2 workflows: `release-ship` and `audit-fanout`. |
| AC-4 | All 7 stale workflow files are absent from `public/workflows/`. |
| AC-5 | `release-ship.workflow.md` and `audit-fanout.workflow.md` exist and each cites the §1 matrix activity class. |
| AC-6 | `dadaia public doctor` D-OC-1 confirms zero dangling references to the 7 deleted workflows across all personas and skills. |
| AC-7 | `specs/memory/product/` is structured into 6 thematic subdirectories per §4.2. |
| AC-8 | `specs/memory/product/index.md` contains all 4 required sections: Vision, Users, Catalog (with links), Capability map (fenced Mermaid), Limits. |
| AC-9 | Exactly 24 atoms (per §4.1 arithmetic) reside in the 6 thematic subdirectories — `agents`:8 / `sdd`:5 / `panel`:2 / `platform`:6 / `distribution`:2 / `philosophy`:1. No file remains at the flat `product/` root other than `index.md`. `test-suite-architecture.md` is either archived via `git mv` or placed in `sdd/` with a SUPERSEDED banner; in neither case does it appear as a regular catalog entry. |
| AC-10 | `dadaia public doctor` exits 0: 9 agents / 17 skills / 2 workflows on all four runtimes. No orphan agents, skills, or rules. |
| AC-11 | `dadaia specs doctor` exits 0: no broken image refs, no broken wikilinks in `product/` (including subdirs), all 24 placed atoms have the 6 required sections. |
| AC-12 | Fresh-init parity check: `dadaia init` on empty dir emits 9 core agents, 17 skills, 2 workflows; no plugin stubs in core projection. |

---

## 8. Out of scope

- Python code changes: none. (Lock/gate changes are in v0.1.6.)
- New features or new agents: none. (v0.1.7 encoded the roster; v0.1.8 authored personas.)
- PyPI publish: this is a workspace-internal milestone. Publish only at v0.2.0.
- Frontend/design plugin authoring: the plugin skills are moved out of core; their
  content is not revised in this milestone (plugin is a separate deliverable).
- Revising `specs/constitution.md`: frozen at v0.1.7. No edits in this milestone.
- New memory atoms: only the existing atoms are reorganized. The `quality-assurance.md`
  atom was created in v0.1.7; this milestone moves it into the tree.

---

## 9. Dependencies and risks

| Dependency / Risk | Detail | Mitigation |
|---|---|---|
| v0.1.8 must be committed (hard) | Personas define what the 9-agent surface is; without the final v0.1.8 personas, D-OC-1 cannot be accurate. | T-018-09 is a hard precondition gate; no v0.1.9 task starts before it. |
| `quality-assurance.md` from v0.1.7 must exist (hard) | It enters the `sdd/` group in the tree. | T-017-02 creates it; its existence is confirmed as part of T-019-05 preconditions. |
| `project-orchestration` is the largest dead-ref concentration (high risk) | The skill currently lists 15 agents, 7 workflows, and multiple now-deleted persona names. It is a PM-loaded skill (`project-orchestration`) that stays stale through v0.1.8; it is audited in T-019-01 and rebuilt in T-019-02 (this milestone). Missing a ref during the strip leaves a broken invariant. | ai-engineer audits the full skill line-by-line in T-019-01. D-OC-1 provides automated confirmation. |
| Memory tree restructure breaks wikilinks (medium risk) | Moving atoms into subdirs invalidates any relative wikilink in `index.md` or between atoms. | All wikilinks updated in T-019-05. `dadaia specs doctor` broken-link check is the acceptance gate. |
| `dadaia specs doctor` broken-link check must cover subdirs (medium risk) | If the doctor's glob only checks the flat `product/` level, it will not validate atoms inside subdirs. | This is a test of the doctor check itself; ai-engineer verifies coverage depth before T-019-06. |
| Skills text-review scope (low risk) | A partial review (fixing only the most visible dead refs) could leave subtler slop. | The review criteria in §2.2 are explicit and checklist-driven; ai-engineer attests to each criterion per skill. |

---

## 10. Memory files affected at closure

At the v0.2.0 CLOSURE phase (not this milestone's closure — this milestone has no
independent CLOSURE, it feeds the v0.2.0 CLOSURE), the following memory files will
reflect the v0.1.9 delta:

- `specs/memory/product/index.md` — rebuilt catalog in thematic tree structure.
- All 24 placed atoms — moved into subdirectories (paths change). `test-suite-architecture.md` is archived, not placed.
- `specs/memory/product/quality-assurance.md` — moved into `sdd/` subdir (created by T-017-02).
- `specs/memory/architecture.md` — no change from this milestone.
- `specs/memory/tech-stack.md` — no change from this milestone.

The memory write is gated on `ACTIVE.md` phase = CLOSURE (v0.2.0 umbrella CLOSURE).
