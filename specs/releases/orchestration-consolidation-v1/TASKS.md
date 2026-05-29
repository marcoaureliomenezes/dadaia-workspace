# TASKS: orchestration-consolidation-v1

**Status:** Aprovado
**Release ID:** orchestration-consolidation-v1
**Owner:** product-engineer
**Created:** 2026-05-29
**Amended:** 2026-05-29 — ownership fixes + ai-engineer recommendations (items 1–7) folded in.
**Approved:** 2026-05-29 (operador).

---

## Agent Roster

| Agent | Role in this release |
|---|---|
| `ai-engineer` | Asset edits (Phases 1–4) + D-OC-1 design note (Phase 5a) |
| `product-engineer` | Backlog update (Phase 5b) + CLOSURE |
| `software-engineer-python` | D-OC-1 invariant implementation + unit test (Phases 5c–5d) |
| `devops-engineer` | Propagation + health checks (Phase 6) |
| `project-manager` | Drives acceptance round-trips (Phase 7) |
| `qa-engineer` | Owns acceptance criteria + independently validates evidence (Phase 7) |

---

## Task List

### Phase 1 — Fix PM Halt Bug

- [x] **T-OCV-01** | owner: ai-engineer | phase: 1 | AC: AC-OC-01, AC-OC-02
  - **Description:** Rewrite `project-manager.md` Step-3 and Step-4 — replace flat routing table with two-tier router (Tier-1: 7 engine-backed workflow names; Tier-2: PM Playbook pattern names). Replace Step-4 stop-and-escalate condition to trigger on missing agent only (not missing file). Add operator UX contract note (plain-language demand; PM auto-reserves task_ids; PM emits intake report naming pattern + agents). Add one-liner note that a PM Playbook acquiring file-iff-X characteristics is a candidate for Tier-1 promotion in a future release.
  - **Target:** `dadaia_workspace/public/agents/project-manager.md`
  - **Preconditions:** SPEC + PLAN approved. TASKS.md marked `[-]` for this task before edit.
  - **Done criterion:** Step-3 table has exactly 2 tiers; Tier-1 lists 7 workflow names each mapping to a real file; Tier-2 lists playbook names. Step-4 stops only on missing agent. Operator UX contract note present.
  - **Parallelism:** None — must complete before T-OCV-02.

### Phase 2 — Reconcile SKILL.md Inventory

- [x] **T-OCV-02** | owner: ai-engineer | phase: 2 | AC: AC-OC-03, AC-OC-04
  - **Description:** Reconcile `project-orchestration/SKILL.md` Workflow Inventory: update count to 7; remove `dashboard-publication` and `design-first-implementation` rows; add cross-reference note to each row pointing to its `*.workflow.md` file. Remove duplicate `spec-refinement` playbook entry — the `scope=game` sub-section in the removed duplicate MUST be preserved (retained in the surviving entry or cross-referenced into `spec-refinement.workflow.md`; content loss is a failure). Add cross-reference to workflow file in surviving spec-refinement playbook entry.
  - **Target:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`
  - **Preconditions:** T-OCV-01 done (confirms Tier-1 set).
  - **Done criterion:** Inventory table has exactly 7 rows with cross-references; `dashboard-publication` and `design-first-implementation` absent; no duplicate spec-refinement playbook entry; `scope=game` content preserved.
  - **Parallelism:** Sequential after T-OCV-01.

### Phase 3 — Add PM Playbooks (mandatory schema)

- [x] **T-OCV-03** | owner: ai-engineer | phase: 3 | AC: AC-OC-05, AC-OC-06, AC-OC-14, AC-OC-15
  - **Description:** Add 5 PM Playbook sections to `project-orchestration/SKILL.md`: `data-pipeline-cycle`, `ai-entity-refinement`, `ai-engineer-recursive-bootstrap`, `dashboard-publication` (folded), `design-first-implementation` (folded). Each section MUST follow the mandatory 7-field schema: `**Trigger:**`, `**Entry:**`, `**Input contract:**`, `**Steps:**`, `**Gate:**` (conditional), `**Stop conditions:**`, `**Done when:**`. Where cheap, retrofit existing playbooks with the same schema. The `ai-engineer-recursive-bootstrap` playbook's `**Gate:**` must require the recognition token `APPROVED: ai-engineer-recursive-bootstrap scope=[<explicit named-file list>]`. `**Stop conditions:**` must include: "any edit outside the approved file list → pause immediately, list the edit, escalate to operator."
  - **Target:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`
  - **Preconditions:** T-OCV-02 done.
  - **Done criterion:** 5 new `### Playbook —` headings present with all 7 schema fields. `ai-engineer-recursive-bootstrap` gate specifies the recognition token and file-list scope. `**Input contract:**` and `**Done when:**` fields non-empty in all new playbooks.
  - **Parallelism:** Sequential after T-OCV-02.

### Phase 4 — Fix Workflow Contradiction

- [-] **T-OCV-04** | owner: ai-engineer | phase: 4 | AC: AC-OC-07
  - **Description:** Fix `cross-cutting-feature.workflow.md` self-contradiction. In the YAML front-matter, change `discovery.agent: project-manager` → `agent: product-engineer`. Verify the prose `## Stages` step-1 already names `product-engineer`; if not, update to match. Both must agree.
  - **Target:** `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md`
  - **Preconditions:** TASKS.md marker flipped to `[-]`. No dependency on T-OCV-01..03 (disjoint file); however ai-engineer must complete any in-progress task before starting this one (one `[-]` per owner at a time).
  - **Done criterion:** YAML `discovery.agent` = `product-engineer` AND prose step-1 = `product-engineer`.
  - **Parallelism:** Disjoint file from T-OCV-01..03; ai-engineer is serial — may run after completing any previous task.

### Phase 5a — D-OC-1 Design Note

- [ ] **T-OCV-05a** | owner: ai-engineer | phase: 5a | AC: (precondition for AC-OC-09)
  - **Description:** Write the D-OC-1 design note as a comment or addendum visible to software-engineer-python. Specify: (1) parsing logic for extracting Tier-1/Tier-2 names from `project-manager.md` Step-3; (2) parsing logic for extracting `### Playbook — <name>` headings from SKILL.md; (3) the precise D-OC-1 rule statement covering both directions (forward: router→artifact; reverse: artifact→router with `[deprecated]` escape); (4) the expected error message format. Deliver the design note in a comment block within T-OCV-06b's description update in this TASKS.md, or as an inline note in PLAN.md Phase 5a section.
  - **Target:** This TASKS.md (inline design note) or PLAN.md Phase 5a section.
  - **Preconditions:** T-OCV-03 done (playbook schema is final before parsing spec is written).
  - **Done criterion:** Design note is readable by software-engineer-python and covers all 4 items above.
  - **Parallelism:** Sequential after T-OCV-03. Unblocks T-OCV-06b.

### Phase 5b — Backlog Cleanup

- [ ] **T-OCV-05b** | owner: product-engineer | phase: 5b | AC: AC-OC-08
  - **Description:** Update `specs/backlog/candidates.md`: delete the `dashboard-publication-workflow-v1` bullet from `## Candidatas ativas`. Move `data-pipeline-cycle-workflow-v1`, `ai-entity-refinement-workflow-v1`, `ai-engineer-recursive-bootstrap-v1` from `## Candidatas ativas` to `## Histórico` with annotation: "resolved to PM Playbook in `orchestration-consolidation-v1` (2026-05-29)".
  - **Target:** `specs/backlog/candidates.md`
  - **Preconditions:** T-OCV-03 done (confirms playbook headings exist before backlog annotates them as resolved).
  - **Done criterion:** `dashboard-publication-workflow-v1` absent from candidates. The 3 workflow bullets present in Histórico with the `orchestration-consolidation-v1` annotation.
  - **Parallelism:** Runs in parallel with T-OCV-06b and T-OCV-07 (disjoint write sets: `specs/backlog/` vs `dadaia_workspace/features/` + `tests/`).

### Phase 5c — D-OC-1 Invariant Implementation

- [ ] **T-OCV-06b** | owner: software-engineer-python | phase: 5c | AC: AC-OC-09
  - **Description:** Implement bidirectional invariant `D-OC-1` in the dadaia specs doctor (locate extension point in `dadaia_workspace/features/doctor/` or `dadaia_workspace/cli/commands/doctor.py`). Implement per the design note from T-OCV-05a. Forward check: for each Tier-1 name in PM router, assert `public/workflows/<name>.workflow.md` exists; for each Tier-2 name, assert `### Playbook — <name>` heading exists in SKILL.md. Reverse check: for each `### Playbook — <name>` heading in SKILL.md, assert it appears as a Tier-2 row in the PM router OR carries `[deprecated]` annotation. Dangling reference in either direction = hard error.
  - **Target:** `dadaia_workspace/features/doctor/` (or equivalent)
  - **Preconditions:** T-OCV-05a done (design note present). T-OCV-01 and T-OCV-02 done (doctor checks final state of those files).
  - **Done criterion:** `dadaia specs doctor` output includes `D-OC-1` line. Running against updated files yields no errors. Running against a deliberately introduced dangling reference yields `[error]` / non-zero exit for D-OC-1 in both forward and reverse directions.
  - **Parallelism:** Runs in parallel with T-OCV-05b (disjoint write sets). Sequential after T-OCV-05a.

### Phase 5d — Unit Test

- [ ] **T-OCV-07** | owner: software-engineer-python | phase: 5d | AC: AC-OC-10
  - **Description:** Write unit test `tests/test_orchestration_registry.py`. Four test cases: (1) all correct → D-OC-1 passes; (2) remove a Tier-1 file entry → forward error; (3) remove a playbook heading → forward error; (4) add an orphan `### Playbook —` heading not in Tier-2 router → reverse error. Use stdlib `re` + `pathlib`; no new dependencies.
  - **Target:** `tests/test_orchestration_registry.py` (new file or existing orchestration tests)
  - **Preconditions:** T-OCV-06b done (D-OC-1 invariant must exist to test it).
  - **Done criterion:** `poetry run pytest tests/test_orchestration_registry.py` exits 0. All 4 test cases pass.
  - **Parallelism:** Sequential after T-OCV-06b.

### Phase 6 — Propagation

- [ ] **T-OCV-08** | owner: devops-engineer | phase: 6 | AC: AC-OC-11, AC-OC-12, AC-OC-13
  - **Description:** Run full propagation sequence: `cd repos/dadaia-workspace && poetry run pytest` (must exit 0); `dadaia public stage`; `dadaia public install --target all`; `dadaia public doctor` (must show 0 drift / 0 missing); `git diff HEAD -- dadaia_workspace/public/` (must show only the 3 intended file changes: `agents/project-manager.md`, `skills/project-orchestration/SKILL.md`, `workflows/cross-cutting-feature.workflow.md`).
  - **Target:** Propagation pipeline + workspace projections
  - **Preconditions:** T-OCV-01..T-OCV-07 all `[x]` DONE.
  - **Done criterion:** pytest exits 0; public doctor exits 0 with 0 drift/missing; git diff shows only 3 public asset files changed.
  - **Parallelism:** Sequential after all Phase 1–5 tasks.

### Phase 7 — Acceptance Validation

- [ ] **T-OCV-09** | owner: qa-engineer (validates) + project-manager (drives) | phase: 7 | AC: AC-OC-16
  - **Description:** Execute playbook round-trip. project-manager drives: operator supplies a plain-language demand with no workflow name and no task_id; PM grills → classifies to Tier-2 playbook → auto-reserves task in TASKS.md → dispatches specialist → emits intake report. qa-engineer independently validates: intake/dispatch reports exist at `.dadaia/reports/`; fields are correct; transcript shows NO operator-supplied workflow name or task_id.
  - **Target:** `.dadaia/reports/dadaia-workspace/project-manager/` (intake report as evidence)
  - **Preconditions:** T-OCV-08 done (propagation complete; updated PM agent live in projection).
  - **Done criterion:** qa-engineer confirms: report exists; fields correct; no operator-supplied pattern name or task_id in transcript.
  - **Parallelism:** T-OCV-09 and T-OCV-10 may run in parallel (disjoint write sets; each produces its own report).

- [ ] **T-OCV-10** | owner: qa-engineer (validates) + project-manager (drives) | phase: 7 | AC: AC-OC-17
  - **Description:** Execute engine-backed round-trip. project-manager drives: operator supplies a demand mapping to Tier-1; PM derives the workflow, populates `--input` itself (no operator prompt for workflow name), calls `dadaia orchestrate run <workflow> --input ...`, emits dispatch report. qa-engineer independently validates: dispatch report identifies Tier-1 workflow name as PM-derived (not operator-supplied); `dadaia orchestrate run` call is present in report.
  - **Target:** `.dadaia/reports/dadaia-workspace/project-manager/` (dispatch report as evidence)
  - **Preconditions:** T-OCV-08 done.
  - **Done criterion:** qa-engineer confirms: report exists; Tier-1 workflow name was PM-derived; `orchestrate run` call present.
  - **Parallelism:** Parallel with T-OCV-09.

---

## Summary

| Task ID | Phase | Owner | AC(s) | Status |
|---|---|---|---|---|
| T-OCV-01 | 1 — PM halt bug fix | ai-engineer | AC-OC-01, AC-OC-02 | `[x]` |
| T-OCV-02 | 2 — Inventory reconcile | ai-engineer | AC-OC-03, AC-OC-04 | `[x]` |
| T-OCV-03 | 3 — Add playbooks (schema) | ai-engineer | AC-OC-05, AC-OC-06, AC-OC-14, AC-OC-15 | `[x]` |
| T-OCV-04 | 4 — Cross-cutting fix | ai-engineer | AC-OC-07 | `[ ]` |
| T-OCV-05a | 5a — D-OC-1 design note | ai-engineer | (precondition for AC-OC-09) | `[ ]` |
| T-OCV-05b | 5b — Backlog cleanup | product-engineer | AC-OC-08 | `[ ]` |
| T-OCV-06b | 5c — D-OC-1 implementation | software-engineer-python | AC-OC-09 | `[ ]` |
| T-OCV-07 | 5d — Unit test | software-engineer-python | AC-OC-10 | `[ ]` |
| T-OCV-08 | 6 — Propagation | devops-engineer | AC-OC-11, AC-OC-12, AC-OC-13 | `[ ]` |
| T-OCV-09 | 7 — Playbook round-trip | qa-engineer + project-manager | AC-OC-16 | `[ ]` |
| T-OCV-10 | 7 — Engine round-trip | qa-engineer + project-manager | AC-OC-17 | `[ ]` |

**Total tasks:** 11
**Owners:** ai-engineer (5: T-OCV-01..04, T-OCV-05a), product-engineer (1: T-OCV-05b), software-engineer-python (2: T-OCV-06b, T-OCV-07), devops-engineer (1: T-OCV-08), qa-engineer + project-manager paired (2: T-OCV-09, T-OCV-10)

**Parallelism declared:**
- T-OCV-04 may run after T-OCV-01 completes (ai-engineer serial; disjoint file from T-OCV-02/03).
- T-OCV-05b (product-engineer) runs in parallel with T-OCV-06b + T-OCV-07 (software-engineer-python) — disjoint write sets: `specs/backlog/` vs `dadaia_workspace/features/` + `tests/`.
- T-OCV-09 and T-OCV-10 may run in parallel.

**Charter compliance confirmed:**
- ai-engineer owns NO Python source or test tasks. ai-engineer owns only asset edits (Phases 1–4) and the design note (T-OCV-05a).
- software-engineer-python owns all Python implementation: D-OC-1 invariant (T-OCV-06b) and unit test (T-OCV-07).
- product-engineer owns the backlog write (T-OCV-05b) — backlog is product-engineer's exclusive domain per workspace constitution.
- qa-engineer is in the roster and owns the acceptance-criteria validation gate for T-OCV-09 and T-OCV-10.
