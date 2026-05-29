# PLAN: orchestration-consolidation-v1

**Status:** Aprovado
**Release ID:** orchestration-consolidation-v1
**Owner:** product-engineer
**Created:** 2026-05-29
**Amended:** 2026-05-29 — ownership fixes + ai-engineer recommendations folded in.
**Approved:** 2026-05-29 (operador).

---

## Strategy

Three contradictory registries and one halt bug — all caused by a half-completed
migration. The repair is surgical text editing of two public asset files and one
workflow file, plus a new drift-gate invariant with a unit test. No engine code
changes.

**Execution order:** Phase 1 (PM router fix) → Phase 2 (SKILL.md inventory) →
Phase 3 (add playbooks with mandatory schema) → Phase 4 (workflow contradiction; can
overlap Phase 1–3 at the file level but ai-engineer is serial) → Phase 5 (backlog
cleanup + D-OC-1 design note by ai-engineer → Python implementation + unit test by
SE-python; backlog markdown runs in parallel with D-OC-1 Python — disjoint write sets)
→ Phase 6 (propagation) → Phase 7 (acceptance validation).

**Owners:**
- `ai-engineer` — Phases 1–4 asset edits + D-OC-1 design note (Phase 5a)
- `product-engineer` — backlog update T-OCV-05 (Phase 5b)
- `software-engineer-python` — D-OC-1 invariant implementation + unit test (Phase 5c–d)
- `devops-engineer` — propagation and health checks (Phase 6)
- `project-manager` — drives acceptance round-trips (Phase 7)
- `qa-engineer` — independently validates acceptance evidence (Phase 7)
- `product-engineer` — CLOSURE + memory update

**Parallelism note:** T-OCV-05 (markdown, `specs/backlog/candidates.md`) and the
D-OC-1 Python work (T-OCV-06a, T-OCV-06b, T-OCV-07) have disjoint write sets and may
run concurrently once Phase 4 (T-OCV-04) is complete. Maximum one `[-]` per owner at
a time still applies per-owner.

---

## Layers Affected

| Layer | Files touched |
|---|---|
| Public agent asset | `dadaia_workspace/public/agents/project-manager.md` |
| Public skill asset | `dadaia_workspace/public/skills/project-orchestration/SKILL.md` |
| Public workflow asset | `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md` |
| Specs backlog | `specs/backlog/candidates.md` |
| Library tests | `tests/test_orchestration_registry.py` (new) |
| Doctor invariants | `dadaia_workspace/features/doctor/` or equivalent doctor-check location |

---

## Execution Order

### Phase 1 — Fix PM Halt Bug (`project-manager.md`)

**Owner:** ai-engineer
**SPEC ACs:** AC-OC-01, AC-OC-02
**Target:** `dadaia_workspace/public/agents/project-manager.md`

Replace Step-3 flat routing table with a two-tier router:

- **Tier-1:** "Engine-backed workflows (call `dadaia orchestrate run`)" — 7 rows:
  `cross-cutting-feature`, `hotfix-release`, `audit-cycle`, `code-review-fan-out`,
  `spec-refinement`, `game-dev-cycle`, `onboarding-new-repo`.
- **Tier-2:** "PM Playbooks (compose inline from `project-orchestration` skill)" — rows
  for all patterns without workflow files, including the 3 new playbooks.

Replace Step-4 to stop-and-escalate only on missing **agent** (not missing file).

Add operator UX contract note: operator supplies plain-language demand only; PM derives
tier and pattern; PM auto-reserves task_ids; PM emits intake report naming pattern + agents.

### Phase 2 — Reconcile SKILL.md Workflow Inventory

**Owner:** ai-engineer
**SPEC ACs:** AC-OC-03, AC-OC-04
**Target:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`

- Update inventory count to 7; remove `dashboard-publication` and
  `design-first-implementation` rows.
- Add cross-reference note to each surviving row pointing to its `*.workflow.md` file.
- Remove duplicate `spec-refinement` playbook entry. The `scope=game` sub-section in
  the removed duplicate MUST be preserved — retain it in the surviving entry or
  cross-reference it into `spec-refinement.workflow.md`. Content loss is a failure.
- Add cross-reference to workflow file in the surviving spec-refinement playbook entry.

### Phase 3 — Add PM Playbooks with Mandatory Schema

**Owner:** ai-engineer
**SPEC ACs:** AC-OC-05, AC-OC-06, AC-OC-14, AC-OC-15
**Target:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`

Add 5 PM Playbook sections. Each MUST follow the mandatory schema (SPEC AC-OC-14):
`**Trigger:**`, `**Entry:**`, `**Input contract:**`, `**Steps:**`, `**Gate:**`
(conditional), `**Stop conditions:**`, `**Done when:**`.

Where cheap, retrofit existing playbooks with the same schema. The two most critical
missing fields are `**Input contract:**` and `**Done when:**` — these are what prevent
sessions running forever or closing too early.

**`### Playbook — data-pipeline-cycle`**
- Trigger: new data pipeline (Spark, Airflow, Kafka, Delta/Iceberg) or ETL/ELT change.
- Entry: `data-engineer`.
- Input contract: `context`, `pipeline_spec` (scope + sources + sinks).
- Steps: PM dispatches data-engineer → implements + unit tests → qa-engineer validates
  → data-analyst consumes if dashboard affected.
- Stop conditions: pipeline feeds Go backend → route backend-engineer for integration;
  schema diverges from dashboard spec → route product-engineer.
- Done when: qa-engineer green validation report at `.dadaia/reports/`.

**`### Playbook — ai-entity-refinement`**
- Trigger: audit of AI entities (skills, rules, workflows, commands, agents, hooks);
  refinement of existing persona surface without new workflow authorship.
- Entry: `ai-engineer`.
- Input contract: `context`, `scope` (list of entity files or glob).
- Steps: PM dispatches ai-engineer with audit scope → ai-engineer emits refinement
  report → PM routes findings to product-engineer for SPEC integration if scope changes
  needed → ai-engineer applies approved edits → devops-engineer propagates.
- Stop conditions: scope requires SPEC change → product-engineer authors it first.
- Done when: devops-engineer `public doctor` exit 0 + ai-engineer `.handoff.json`.

**`### Playbook — ai-engineer-recursive-bootstrap`**
- Trigger: first real dispatch of `ai-engineer` on its own surface in a restricted scope.
- Entry: `ai-engineer`.
- Gate: operator must type the recognition token
  `APPROVED: ai-engineer-recursive-bootstrap scope=[<explicit named-file list>]`.
  Approved scope is an enumerated named-file list, not a domain. Gate stays active
  until one proven restricted-scope success is recorded and the operator explicitly
  removes it via SPEC amendment.
- Input contract: `scope` (named file list from the APPROVED token).
- Steps: PM presents proposed scope to operator → operator types recognition token →
  PM dispatches ai-engineer within the approved scope → ai-engineer acts → devops-engineer
  propagates → PM verifies no unintended drift.
- Stop conditions: any edit outside the approved file list → pause immediately, list the
  edit, escalate to operator (do not proceed).
- Done when: devops-engineer `public doctor` exit 0 + PM drift-verification report showing
  no unintended files changed.

**`### Playbook — dashboard-publication`** (folded from workflow file)
- Trigger: completed dashboard needs visual review and publish.
- Entry: `data-analyst`.
- Input contract: `context`, `dashboard_id`.
- Steps: data-analyst builds dashboard → PM dispatches design-specialist for visual
  review → data-analyst publishes via DABs → PM confirms publication.
- Stop conditions: design-specialist blocks → route product-engineer for arbitration.
- Done when: DABs publication URL confirmed by data-analyst + design-specialist sign-off.

**`### Playbook — design-first-implementation`** (folded from workflow file)
- Trigger: new UI surface where design must precede implementation.
- Entry: `design-specialist`.
- Input contract: `context`, `scope` (UI surface description).
- Steps: PM dispatches design-specialist with brief → specialist emits design spec →
  PM dispatches frontend-engineer with design report as input → FE implements.
- Stop conditions: design spec conflicts with memory semantics → route product-engineer.
- Done when: frontend-engineer `.handoff.json` exit 0 referencing the design report.

### Phase 4 — Fix `cross-cutting-feature.workflow.md` Contradiction

**Owner:** ai-engineer
**SPEC AC:** AC-OC-07
**Target:** `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md`

Change YAML `discovery.agent: project-manager` → `agent: product-engineer`. Confirm
prose step-1 matches. Both must agree on `product-engineer`.

Can be scheduled after T-OCV-01 completes (ai-engineer is serial; disjoint file allows
conceptual parallelism but one owner constraint applies).

### Phase 5 — Backlog Cleanup + D-OC-1 Design + Implementation

**Phase 5a — D-OC-1 design note (ai-engineer):**
Before software-engineer-python implements, ai-engineer writes a concise design note
(inline in T-OCV-06a or as a comment in TASKS.md) specifying:
1. Parsing logic: how to extract Tier-1/Tier-2 names from `project-manager.md` Step-3;
   how to extract `### Playbook — <name>` headings from SKILL.md.
2. The precise D-OC-1 rule statement (both directions: forward + reverse).
3. The expected error message format (e.g., `[error] D-OC-1: dangling reference '<name>' in PM router — no file or playbook heading found`).

---

### D-OC-1 Design Note (ai-engineer, T-OCV-05a)

**Target reader:** `software-engineer-python` implementing invariant D-OC-1 in
`dadaia specs doctor` (T-OCV-06b).

**Source files:**
- PM router: `dadaia_workspace/public/agents/project-manager.md`
- Skill: `dadaia_workspace/public/skills/project-orchestration/SKILL.md`
- Workflow files: `dadaia_workspace/public/workflows/*.workflow.md`

---

#### 1. Parsing Logic

**Extracting Tier-1 names from `project-manager.md` Step-3:**

The Tier-1 table appears under the heading:
```
#### Tier-1 — Engine-backed workflows (call `dadaia orchestrate run <name> --input ...`)
```

Parse it as a Markdown table. The workflow name is in the second column (`| Workflow name |`).
Use this regex on each table data row:
```python
import re

TIER1_TABLE_ROW = re.compile(
    r'^\|\s*`([^`]+)`\s*\|\s*`public/workflows/([^`]+)\.workflow\.md`',
    re.MULTILINE
)
```
This captures `(demand_label, workflow_name)` pairs. The workflow name (group 2) is
what maps to a `*.workflow.md` file.

Alternatively, a simpler single-column scan for the workflow name column:
```python
TIER1_NAME = re.compile(
    r'^\|\s+`([a-z][a-z0-9-]+)`\s+\|\s+`public/workflows/\1\.workflow\.md`',
    re.MULTILINE
)
```
Capture group 1 is the canonical Tier-1 workflow name.

**Extracting Tier-2 names from `project-manager.md` Step-3:**

The Tier-2 table appears under the heading:
```
#### Tier-2 — PM Playbooks (compose inline from `project-orchestration` skill)
```

Parse the second column (`| Playbook name |`) of this table:
```python
TIER2_NAME = re.compile(
    r'^\|\s+`([a-z][a-z0-9-]+)`\s*\|',
    re.MULTILINE
)
```
Apply only to lines between the Tier-2 heading and the next `###` or `---` boundary.
Capture group 1 is the canonical Tier-2 playbook name.

**Note:** The `spec-refinement` entry in Tier-2 includes a parenthetical note. Strip
everything after the first backtick-enclosed name. Example:
```
| `spec-refinement` (Tier-2 path; ...) | ...
```
Extract only `spec-refinement`.

**Extracting `### Playbook — <name>` headings from SKILL.md:**

```python
PLAYBOOK_HEADING = re.compile(
    r'^###\s+Playbook\s+—\s+([a-z][a-z0-9-]+)(\s+\[deprecated\])?',
    re.MULTILINE | re.IGNORECASE
)
```
Capture group 1 is the playbook name. Capture group 2 (if present and equals
`[deprecated]`) marks the playbook as deprecated — it is exempt from the reverse check.

**Note on the `spec-refinement` section heading:** The current SKILL.md uses:
```
### spec-refinement — Tier-1 engine-backed workflow
```
This does NOT match `### Playbook — spec-refinement` and MUST NOT be treated as a
Tier-2 playbook heading. The D-OC-1 reverse check only matches headings of the exact
form `### Playbook — <name>`. The `spec-refinement` Tier-1 section heading is
intentionally different.

---

#### 2. The Precise D-OC-1 Rule Statement

**Invariant D-OC-1 (bidirectional orchestration registry coherence):**

> Every name referenced in the two-tier router in `project-manager.md` Step-3 AND in
> `project-orchestration/SKILL.md` must resolve unambiguously:
>
> **Forward (router → artifact):**
> - Every Tier-1 name in the PM router MUST have a corresponding file at
>   `dadaia_workspace/public/workflows/<name>.workflow.md`.
> - Every Tier-2 name in the PM router MUST have a corresponding
>   `### Playbook — <name>` heading in SKILL.md.
>
> **Reverse (artifact → router):**
> - Every `### Playbook — <name>` heading in SKILL.md MUST appear as a Tier-2 row in
>   the PM router table, OR carry the annotation `[deprecated]` in the heading itself
>   (`### Playbook — <name> [deprecated]`).
>
> A dangling reference in either direction is a **hard error** (non-zero exit, `[error]`
> line in `dadaia specs doctor` output).

---

#### 3. Parsing Boundary Details

To scope the Tier-2 regex to only the Tier-2 table (avoiding false matches in prose),
use a two-pass approach:

1. Split `project-manager.md` on `#### Tier-1` and `#### Tier-2` headings to isolate
   each tier's block.
2. Apply the respective regex only within that block.
3. Stop at the next `####` or `###` heading.

Python sketch:
```python
from pathlib import Path
import re

def _split_tier_blocks(text: str) -> tuple[str, str]:
    tier1_match = re.search(r'#### Tier-1[^\n]*\n', text)
    tier2_match = re.search(r'#### Tier-2[^\n]*\n', text)
    if not tier1_match or not tier2_match:
        return "", ""
    tier1_block = text[tier1_match.end():tier2_match.start()]
    # Tier-2 block ends at next `###` or end of file
    tier2_end = re.search(r'^###', text[tier2_match.end():], re.MULTILINE)
    tier2_block = (
        text[tier2_match.end(): tier2_match.end() + tier2_end.start()]
        if tier2_end else text[tier2_match.end():]
    )
    return tier1_block, tier2_block


def extract_tier1_names(pm_text: str) -> list[str]:
    tier1_block, _ = _split_tier_blocks(pm_text)
    return re.findall(
        r'^\|\s+`([a-z][a-z0-9-]+)`\s+\|\s+`public/workflows/',
        tier1_block, re.MULTILINE
    )


def extract_tier2_names(pm_text: str) -> list[str]:
    _, tier2_block = _split_tier_blocks(pm_text)
    return re.findall(r'^\|\s+`([a-z][a-z0-9-]+)`', tier2_block, re.MULTILINE)


def extract_playbook_headings(skill_text: str) -> dict[str, bool]:
    """Returns {name: is_deprecated}."""
    matches = re.findall(
        r'^###\s+Playbook\s+—\s+([a-z][a-z0-9-]+)(\s+\[deprecated\])?',
        skill_text, re.MULTILINE | re.IGNORECASE
    )
    return {name: bool(dep.strip()) for name, dep in matches}
```

---

#### 4. Expected Error Message Format

All D-OC-1 error lines must follow this format so they are parseable by the doctor
output scanner and the unit test assertions:

```
[error] D-OC-1: Tier-1 name '<name>' has no workflow file at public/workflows/<name>.workflow.md
[error] D-OC-1: Tier-2 name '<name>' has no playbook heading '### Playbook — <name>' in SKILL.md
[error] D-OC-1: Playbook heading '### Playbook — <name>' in SKILL.md has no Tier-2 router row in project-manager.md (add it or annotate [deprecated])
```

On success (no dangling references), emit:
```
[ok] D-OC-1: orchestration registry coherence — N Tier-1 workflows, M Tier-2 playbooks, K playbook headings — all references resolved
```

The doctor command must exit non-zero if any `[error] D-OC-1:` line is emitted.

---

#### 5. Implementation Location Hint

The doctor invariants live in `dadaia_workspace/features/doctor/` (inspect for the
existing invariant registration pattern — likely a list of check functions, each
returning a list of `DoctorFinding` objects or equivalent). The D-OC-1 check should
be registered at the same level as existing checks, with label `"D-OC-1"`.

The check receives the absolute path to the `dadaia_workspace/public/` directory and
reads the three relevant files from there. No network access; stdlib `re` + `pathlib`
only.

---

**Phase 5b — Backlog cleanup (product-engineer):**
**Target:** `specs/backlog/candidates.md`
- Delete `dashboard-publication-workflow-v1` from active candidates.
- Move the 3 workflow bullets to Histórico with annotation: "resolved to PM Playbook
  in `orchestration-consolidation-v1` (2026-05-29)".

Runs in parallel with Phase 5c/5d (disjoint write sets: `specs/backlog/` vs `tests/` +
`dadaia_workspace/features/`).

**Phase 5c — D-OC-1 invariant implementation (software-engineer-python):**
**Precondition:** ai-engineer's design note from Phase 5a complete.
**Target:** `dadaia_workspace/features/doctor/` (or equivalent)
**SPEC AC:** AC-OC-09

Implement bidirectional D-OC-1 from the design note:
- Forward: Tier-1 name → file exists; Tier-2 name → playbook heading exists.
- Reverse: every `### Playbook — <name>` heading → Tier-2 row present OR `[deprecated]`
  annotation present (catches orphan/unreachable playbooks).

**Phase 5d — Unit test (software-engineer-python):**
**Precondition:** Phase 5c complete.
**Target:** `tests/test_orchestration_registry.py`
**SPEC AC:** AC-OC-10

Write unit test exercising D-OC-1 both directions:
1. All correct → no error.
2. Remove file entry → forward error.
3. Remove playbook heading → forward error.
4. Add orphan heading not in Tier-2 router → reverse error.
Use stdlib `re` + `pathlib`; no new dependencies.

### Phase 6 — Propagation

**Owner:** devops-engineer
**SPEC ACs:** AC-OC-11, AC-OC-12, AC-OC-13

```bash
cd repos/dadaia-workspace && poetry run pytest
dadaia public stage
dadaia public install --target all
dadaia public doctor
git diff HEAD -- dadaia_workspace/public/
```

All must exit 0. `public doctor` must show 0 drift / 0 missing. `git diff` must show
only the 3 intended public asset edits.

### Phase 7 — Acceptance Validation

**project-manager** drives the two round-trips; **qa-engineer** owns the acceptance
criteria and independently validates the evidence.

**AC-OC-16 — Playbook round-trip:**
Operator supplies a raw plain-language demand. PM grills → classifies Tier-2 → reserves
task in TASKS.md → dispatches specialist → emits intake report.
qa-engineer confirms: intake/dispatch reports exist; fields correct; transcript shows NO
operator-supplied workflow name or task_id.

**AC-OC-17 — Engine-backed round-trip:**
Operator supplies a demand mapping to Tier-1. PM derives workflow, populates `--input`
itself (no operator prompt), calls `dadaia orchestrate run`, emits dispatch report.
qa-engineer confirms: Tier-1 workflow name was PM-derived (not operator-supplied);
`dadaia orchestrate run` call present in report.

---

## Technical Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| SKILL.md spec-refinement `scope=game` content lost in dedup | Medium | AC-OC-04 explicitly requires it; ai-engineer reads both before editing. |
| `cross-cutting-feature.workflow.md` YAML parse breaks after agent change | Low | YAML is one field change; validate with `dadaia orchestrate show cross-cutting-feature`. |
| Doctor invariant location not obvious | Medium | SE-python inspects `features/doctor/` and `cli/commands/doctor.py` before writing; ai-engineer design note guides the implementation point. |
| D-OC-1 reverse check overly strict (deprecated playbooks) | Low | `[deprecated]` annotation escape hatch defined; SE-python implements the check. |
| PM testing own acceptance (conflict of interest) | Resolved | qa-engineer owns the AC validation gate; PM only drives the round-trip execution. |

---

## Validation Plan

| Validation | Command | Pass condition |
|---|---|---|
| pytest suite green | `poetry run pytest` | Exit 0, 0 failures |
| New unit test green (both directions) | `poetry run pytest tests/test_orchestration_registry.py` | Exit 0, all 4 cases pass |
| Public assets staged and projected | `dadaia public stage && dadaia public install --target all` | Exit 0 |
| No drift / no missing | `dadaia public doctor` | 0 drift, 0 missing |
| Only intended edits shipped | `git diff HEAD -- dadaia_workspace/public/` | 3 files changed |
| Playbook round-trip | qa-engineer reviews PM intake report | Fields correct, no operator-supplied pattern name |
| Engine-backed round-trip | qa-engineer reviews PM dispatch report | PM-derived Tier-1 name, `orchestrate run` present |
