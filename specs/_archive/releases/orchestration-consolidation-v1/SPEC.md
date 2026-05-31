# SPEC: orchestration-consolidation-v1

**Status:** Aprovado
**Release ID:** orchestration-consolidation-v1
**Owner:** product-engineer
**Created:** 2026-05-29
**Amended:** 2026-05-29 — ownership fixes + ai-engineer review recommendations (items 1–7) folded in.
**Approved:** 2026-05-29 (operador).

---

## Objective

Eliminate the three-registry inconsistency and the PM halt bug introduced by the
unfinished migration in `agents-r2-v1`. After this release, the project-manager agent
routes every demand unambiguously: engine-backed workflows for patterns that meet the
`file-iff-X` rule; PM Playbooks for everything else. No missing-file stop condition
for playbook routes. The operator interface remains plain-language demand only.

---

## Problem Statement

Release `agents-r2-v1` deleted 8 workflow files and described replacement PM Playbooks
in `project-orchestration/SKILL.md`. It did not complete the cutover on the PM agent
side. The consequences are:

**Halt Bug (critical):** `project-manager.md` Step-3 maps 13 categories to workflow
names. Six of those names (`game-spec-definition`, `bug-fix-fastlane`,
`architecture-review`, `security-patch`, `design-validation`, `deploy-validation-only`,
`game-bugfix`) have no `*.workflow.md` file on disk — they are PM Playbooks. Step-4
then says "Read `public/workflows/<workflow>.workflow.md` … if missing, stop and
escalate." The orchestrator is wired to dead-end on its most common routes.

**Three contradictory registries:**
1. `project-manager.md` Step-3 table (~L134–152) — lists 13 route names.
2. `project-orchestration/SKILL.md` Workflow Inventory (~L46) — says "7 canonical
   workflows" but 9 `*.workflow.md` files exist (`dashboard-publication`,
   `design-first-implementation` added post-inventory).
3. `project-orchestration/SKILL.md` PM Playbooks section — `spec-refinement` playbook
   entry (~L382) names `product-engineer` as entry; `spec-refinement.workflow.md` L33
   names `project-manager`. Additionally, `cross-cutting-feature.workflow.md` YAML L37
   sets `agent: project-manager` for the discovery stage while the prose section (~L224)
   names `product-engineer`.

**Stale backlog:** `specs/backlog/candidates.md` carries a `dashboard-publication-workflow-v1`
bullet — the file already exists on disk, making this bullet stale.

---

## The File-iff-X Rule (core principle this release encodes)

A coordination pattern earns an engine-backed `*.workflow.md` file **only if** it has
at least one of:

- **(a)** a multi-party `parallel_group` topology
- **(b)** a non-optional operator-approval gate sequence
- **(c)** enforced cross-surface named input contracts

Patterns that do not meet any criterion become PM Playbooks (prose in
`project-orchestration/SKILL.md`). The operator never names a playbook; PM derives
the pattern from intent.

**Tier-2 promotion path:** A PM Playbook that later acquires file-iff-X characteristics
(multi-party parallel topology, operator-approval gate, or enforced cross-surface input
contract) is a candidate for promotion to a Tier-1 engine workflow in a future release.
This prevents silent complexity accumulation in Tier-2.

---

## Product Deltas

### PM agent (`project-manager.md`)

- Replace Step-3 flat table with a **two-tier router**:
  - **Tier-1** (engine-backed): the 7 surviving `*.workflow.md` files → PM calls
    `dadaia orchestrate run <workflow> --input ...`.
  - **Tier-2** (PM Playbooks): all other patterns → PM composes inline from the
    playbook steps in `project-orchestration/SKILL.md`.
- Replace Step-4's "if file missing, stop and escalate" with: stop-and-escalate only
  when a **required agent** is missing; missing file on a Tier-2 route is normal.
- Encode the operator UX contract: operator supplies plain-language demand only; PM
  derives the tier and workflow/playbook; PM auto-reserves task_ids in TASKS.md on
  the operator's behalf; PM emits an intake report naming the chosen pattern + agents.

### SKILL.md (`project-orchestration/SKILL.md`)

- Reconcile Workflow Inventory count to actual disk (9 → post-fold: 7 surviving,
  2 folded to playbooks).
- Remove the duplicate `spec-refinement` playbook entry (the file already exists;
  the playbook entry is redundant and contradictory).
- When removing the duplicate `spec-refinement` entry, the richer `scope=game`
  sub-section currently in that playbook entry MUST be preserved — either retained as a
  note in the surviving `spec-refinement.workflow.md` cross-reference or as a named
  sub-section within the Tier-1 entry. Do not lose this content in the dedup.
- Fold `design-first-implementation` and `dashboard-publication` into PM Playbooks
  (single-surface; do not justify engine overhead).
- Add 3 new PM Playbooks: `data-pipeline-cycle`, `ai-entity-refinement`,
  `ai-engineer-recursive-bootstrap` (gated, see below).
- Cross-reference surviving workflow files from within the inventory table.
- **Mandatory playbook structure schema:** Every PM Playbook section (the 3 new, the 2
  folded-in from workflow files, and retrofit existing playbooks where cheap) MUST
  contain the following sub-sections in order:
  - `**Trigger:**` — machine-matchable keywords for Step-3 classification (mandatory)
  - `**Entry:**` — agent name(s) only, no prose (mandatory)
  - `**Input contract:**` — named fields the PM must populate before dispatch (mandatory;
    may be `none` if nothing required)
  - `**Steps:**` — ordered, imperative; each step: agent + action + artifact produced (mandatory)
  - `**Gate:**` — only if per-run operator approval is required (conditional)
  - `**Stop conditions:**` — enumerated exit states → action for each (mandatory)
  - `**Done when:**` — single verifiable artifact/state signalling completion (mandatory)

### Workflow file (`cross-cutting-feature.workflow.md`)

- Fix self-contradiction: discovery stage owner → `product-engineer` (YAML L37 and
  prose L224 must agree; spec-author domain wins per Decision Authority Matrix).

### Backlog (`specs/backlog/candidates.md`)

- Delete stale `dashboard-publication-workflow-v1` bullet (file already exists).
- Re-file the other 3 backlog workflow candidates as PLAYBOOK tasks tied to this
  release (they become playbooks, not workflow files):
  - `data-pipeline-cycle-workflow-v1` → becomes Playbook `data-pipeline-cycle`
  - `ai-entity-refinement-workflow-v1` → becomes Playbook `ai-entity-refinement`
  - `ai-engineer-recursive-bootstrap-v1` → becomes Playbook `ai-engineer-recursive-bootstrap`

### Drift Gate (new invariant + unit test)

**Design authorship (ai-engineer):** Before implementation, ai-engineer writes a design
note specifying: (a) the exact parsing logic for extracting workflow/playbook names from
`project-manager.md` and `project-orchestration/SKILL.md`; (b) the precise rule
statement for D-OC-1; (c) the expected error message format. This design note travels
with T-OCV-06 as a precondition.

**Implementation (software-engineer-python):** Add invariant `D-OC-1` to `dadaia specs
doctor`:

> Every workflow name referenced in `project-manager.md` Step-3 table and in
> `project-orchestration/SKILL.md` Workflow Inventory maps **either** to a file under
> `public/workflows/` **or** to a `### Playbook —` heading in the skill.

The invariant is **bidirectional**:
- **Forward (router → artifact):** every Tier-1 name in the PM router maps to a real
  `*.workflow.md` file; every Tier-2 name maps to a `### Playbook — <name>` heading.
- **Reverse (artifact → router):** every `### Playbook — <name>` heading in SKILL.md
  must appear as a Tier-2 row in the PM router table, OR be explicitly annotated as
  `### Playbook — <name> [deprecated]`. This catches orphan/unreachable playbooks.

A dangling reference in either direction is a hard error.

Companion unit test in `tests/` that exercises this invariant.

---

## Architecture Deltas

None. The DAG execution engine (`features/orchestration/`, `cli/commands/orchestrate.py`,
`infrastructure/markdown_workflow_store.py`, agent dispatchers) is kept entirely intact.
This release is text-asset editing only.

---

## Tech-Stack Deltas

None.

---

## Security / Operations Deltas

None beyond the `ai-engineer-recursive-bootstrap` playbook gate (see below).

---

## Operator Decisions (authoritative — baked in)

These decisions were confirmed by the operator before this SPEC was written:

| Decision | Resolution |
|---|---|
| Execute via dedicated release | **Yes** — this release. |
| `design-first-implementation` fate | **Fold to PM Playbook.** |
| `dashboard-publication` fate | **Fold to PM Playbook.** |
| PM task_id reservation | **PM auto-reserves** — no confirmation prompt to operator. |
| Surviving engine-backed workflows | `cross-cutting-feature`, `hotfix-release`, `audit-cycle`, `code-review-fan-out`, `spec-refinement`, `game-dev-cycle`, `onboarding-new-repo`. |
| 4 backlog candidates as workflow files? | **No.** They become PM Playbooks. |
| `dashboard-publication` backlog bullet | **Delete** (stale — file exists). |

## Applied Defaults (operator may object at approval)

| Default | Encoding |
|---|---|
| `cross-cutting-feature` discovery owner | **product-engineer** (resolves YAML/prose self-contradiction; spec-author domain per Decision Authority Matrix). |
| `ai-engineer-recursive-bootstrap` gate | **Gated behind explicit per-run operator approval** until one proven restricted-scope success exists (per backlog requirement; self-referential DEV-workspace risk). |

---

## Memory Files Affected at Closure

- `specs/memory/architecture.html` — no structural change; update orchestration
  section to reflect two-tier routing model if description exists.
- `specs/memory/product/index.html` — no catalog change (orchestration is a
  cross-cutting concern, not a standalone product feature).
- No new product feature pages required.

---

## Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-OC-01 | `project-manager.md` Step-3 table contains exactly 2 tiers: Tier-1 (7 workflow names, each mapping to an existing `*.workflow.md` file) and Tier-2 (playbook route names, each mapping to a `### Playbook —` heading in `project-orchestration/SKILL.md`). |
| AC-OC-02 | `project-manager.md` Step-4 no longer contains "if file missing, stop and escalate" unconditionally. Stop-and-escalate applies only when a required **agent** is missing. |
| AC-OC-03 | `project-orchestration/SKILL.md` Workflow Inventory lists exactly 7 entries, each referencing a real file under `public/workflows/`. `dashboard-publication` and `design-first-implementation` are absent from this table. |
| AC-OC-04 | `project-orchestration/SKILL.md` PM Playbooks section contains no duplicate `spec-refinement` entry and cross-references `spec-refinement.workflow.md` for the engine-backed route. The richer `scope=game` sub-section from the removed duplicate is preserved: either retained as a note in the surviving entry or cross-referenced into `spec-refinement.workflow.md`. No content loss. |
| AC-OC-05 | `project-orchestration/SKILL.md` PM Playbooks section contains entries for `data-pipeline-cycle`, `ai-entity-refinement`, `ai-engineer-recursive-bootstrap` (with per-run operator gate noted). |
| AC-OC-06 | `project-orchestration/SKILL.md` PM Playbooks section contains entries for `dashboard-publication` and `design-first-implementation` (previously only workflow files, now also captured as playbooks). |
| AC-OC-07 | `cross-cutting-feature.workflow.md` discovery stage: YAML field `agent` and prose `## Stages` step-1 both name `product-engineer`. No self-contradiction. |
| AC-OC-08 | `specs/backlog/candidates.md` does not contain the `dashboard-publication-workflow-v1` bullet. The other 3 workflow-backlog candidates are annotated as "resolved to PM Playbook in `orchestration-consolidation-v1`" in the Histórico section. |
| AC-OC-09 | A new invariant `D-OC-1` exists in `dadaia specs doctor`. The check is **bidirectional**: (a) every Tier-1 name maps to an existing `*.workflow.md` file AND every Tier-2 name maps to a `### Playbook — <name>` heading; (b) every `### Playbook — <name>` heading in SKILL.md appears as a Tier-2 row in the PM router table OR carries a `[deprecated]` annotation. The invariant is documented alongside existing doctor invariants. |
| AC-OC-10 | A unit test exists and is green: `tests/test_orchestration_registry.py` (or equivalent), exercising the D-OC-1 invariant — both forward and reverse directions — by mocking the file tree and heading scanner. |
| AC-OC-11 | `poetry run pytest` exits 0. |
| AC-OC-12 | `dadaia public stage && dadaia public install --target all && dadaia public doctor` exits 0 with 0 drift / 0 missing. |
| AC-OC-13 | `git diff HEAD -- dadaia_workspace/public/` shows only intended edits (no unreviewed changes). |
| AC-OC-14 | Every PM Playbook section authored or updated in this release contains all 7 mandatory sub-sections in order: `**Trigger:**`, `**Entry:**`, `**Input contract:**`, `**Steps:**`, `**Gate:**` (conditional), `**Stop conditions:**`, `**Done when:**`. The `**Input contract:**` and `**Done when:**` fields are present and non-empty (or explicitly `none` for Input contract). |
| AC-OC-15 | The `ai-engineer-recursive-bootstrap` playbook's `**Gate:**` field requires the operator to type a specific recognition token in the form `APPROVED: ai-engineer-recursive-bootstrap scope=[<explicit file list>]`. The approved scope is an enumerated named-file list (not a domain). `**Stop conditions:**` explicitly states: "any edit outside the approved file list → pause immediately, list the edit, escalate to operator." |
| AC-OC-16 | **Playbook round-trip acceptance test:** operator supplies a raw plain-language demand with no workflow name and no task_id; PM grills → classifies to a Tier-2 playbook → auto-reserves the task in TASKS.md → dispatches the right specialist → emits intake report naming the chosen pattern + agents. Intake/dispatch reports exist at `.dadaia/reports/`; fields are correct; transcript shows NO operator-supplied workflow name or task_id. Validation: qa-engineer independently reviews the reports and confirms all fields correct and no operator-supplied workflow name or task_id appears in the transcript. |
| AC-OC-17 | **Engine-backed round-trip acceptance test:** operator supplies a demand that maps to a Tier-1 workflow; PM derives the workflow, populates `--input` contract itself (no operator prompt), calls `dadaia orchestrate run`, emits dispatch report. Validation: qa-engineer independently reviews the dispatch report and confirms the Tier-1 workflow name was PM-derived (not operator-supplied) and the `dadaia orchestrate run` call is present. |

---

## Out of Scope

- Any change to the DAG engine or CLI commands (`dadaia orchestrate list/show/run`).
- New `*.workflow.md` files for the 3 backlog patterns (`data-pipeline-cycle`,
  `ai-entity-refinement`, `ai-engineer-recursive-bootstrap`).
- Changes to any workflow file other than `cross-cutting-feature.workflow.md`.
- Modifications to `dashboard-publication.workflow.md` or
  `design-first-implementation.workflow.md` beyond the inventory update
  (these files stay on disk as reference; they are simply demoted from the
  active routing table).
- Changes to agent persona files other than `project-manager.md`.
- Memory HTML rewrites beyond the minimal orchestration-section update.
- CI/CD pipeline changes.

---

## Dependencies and Risks

| Item | Detail |
|---|---|
| No active release in flight | ACTIVE.md shows `release: none` — clean slate. |
| agents-r2-v1 PM Playbooks already written | The SKILL.md Playbooks section exists and is the correct target. Edits are additive/corrective, not from scratch. |
| Engine stays intact | No Python changes to orchestration engine. Risk: near-zero. |
| `dashboard-publication` + `design-first-implementation` files stay on disk | Demoting them from routing table is the change; files are not deleted (used by engine-aware callers). |
| `ai-engineer-recursive-bootstrap` per-run gate | Operator gate with explicit recognition token ensures no accidental self-modification of the DEV workspace. |
| Drift gate unit test | Requires parsing `project-manager.md` and `SKILL.md` in test code. Scope is narrow (string search, not semantic analysis). |
| ai-engineer → software-engineer-python handoff for D-OC-1 | ai-engineer authors the design note (parsing logic + rule statement + error format); SE-python implements. Clear sequencing required. |
