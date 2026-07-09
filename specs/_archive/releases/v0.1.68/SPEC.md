# SPEC — Release v0.1.68 — Lifecycle Evidence/Handoff Engine Correctness

> **Status:** Aprovado
> **Release ID:** v0.1.68
> **Owner:** product-engineer
> **Picked set:** 3 open HIGH bugs — the lifecycle *engine* layer

## Objective

Fix three engine-layer defects that make `dadaia lifecycle pipeline` /
`implement-review` unusable or misleading for a real release, and add the
**full-pipeline end-to-end test that never existed** — one that drives a real
release through the actual pipeline against a throwaway spec-context, the test
whose absence let all of these ship. No workarounds: each fix removes the cause,
each proven by a RED→GREEN executed-path test.

## Why these escaped (feeds the post-mortem)

Every one of these bugs is live on `main` at HEAD `54e9be0e` — the exact commit
the reporter runs. v0.1.66/67 validated the pi/codex **adapter** (does the binary
get invoked, does a non-zero exit surface) with fake harnesses and adapter-level
unit tests, and **never once drove the operator's real workflow** — a full
`lifecycle pipeline` run selecting evidence, consuming payloads, and deriving
scope. The engine above the adapter was untested end-to-end. FR4 closes that gap
permanently.

## Picked bugs

| Bug id | Severity | Disposition |
|---|---|---|
| `lifecycle-pipeline-selects-stale-unrelated-handoff` | HIGH | Fixed (FR1) |
| `implement-review-completed-run-leaves-unconsumed-required-payload` | HIGH | Fixed (FR2) |
| `pipeline-does-not-derive-write-scope-from-tasks` | HIGH | Fixed (FR3) |

None superseded; all fixed directly. `pipeline-does-not-derive-write-scope-from-tasks`
is the **unmet half** of the v0.1.66-"resolved" `lifecycle-implement-step-write-scope-too-narrow`:
v0.1.66 shipped only the manual `--write-scope` escape hatch and marked the bug
resolved; the operator's actual need — automatic derivation from the reserved
task's `Write set:` — was never delivered. FR3 delivers it. (A CLOSURE note will
record this partial-fix lesson; the prior disposition is not reversed, it is
completed.)

## Reproduction & TDD mandate — no workarounds

This release operates under the reproduce→root-cause→validate law
(`feedback-reproduce-rootcause-no-workaround`). Every FR carries an
`AC-N(repro)` criterion: a **failing executed-path test on current code that
passes after the root-cause fix**. No config band-aids, no error-swallowing, no
test-only shims. The RED proof is committed first, the fix second.

---

## Root causes (verified by inspection — see grill report)

### FR1 — Run-unscoped block-evidence enrichment (`lifecycle-pipeline-selects-stale-unrelated-handoff`)

`dadaia_workspace/container.py:509-560` `_build_handoff_lookup._lookup(context, agent)`
globs `context_dir.glob(f"*-{agent}-*.handoff.json")` sorted `reverse=True` and
returns the newest independently-validating file. It is keyed **only on
`(context, role)`** — it has no `run_id` or `step` — so when a create/implement
worker returns SUCCEEDED with empty `artifact_refs`
(`features/lifecycle/agent_runner.py:210-221`), the block detail's
`validated_handoff_path` is enriched with an **arbitrary historical handoff by
that role from a previous task/run**. The lookup callable's signature is
`Callable[[str, str], str | None]` (`container.py:509`) and
`_lookup_validated_handoff` (`agent_runner.py:235-248`) passes only
`(lifecycle_run.context, data.request.role)`. This enrichment is
observability-only (it never converts the block to a pass — FR2/v0.1.66's no-op
invariant is intact) but it actively **misdirects** the operator to an unrelated
task's handoff, and any real harness that writes a handoff file without
populating `artifact_refs` gets a false "evidence found" pointer.

**The enrichment cannot be run-scoped — it must be removed (architect F1).** The
enrichment fires exactly when `result.artifact_refs` is empty, i.e. the worker
produced **no** in-result handoff path. The `.dadaia/handoff/<ctx>/*.handoff.json`
files the glob matches carry **no `run_id`/`step`** in their name or emitter
contract, and the per-run step-payload ledger (`workflow_handoffs.py`,
`.dadaia/runs/lifecycle/<run_id>/steps/*.step-payload.json`) is a **different data
plane** that holds no `.handoff.json` path. So "thread run_id into the lookup"
would degrade to a fragile slug substring-match heuristic (the v0.1.66 FR8 test
only passes because its slug coincidentally equals the run-id) — a new defect, not
a fix. Because a no-op create worker wrote nothing for the current step, **there
is no current-run handoff to surface by construction.** The correct fix is to
**remove** the role-keyed disk-glob as a block-evidence source (the FR8 v0.1.66
enrichment that was never run-scopable) and replace it with an honest
`no_current_artifact` detail naming the run and step.

**Invariant to restore:** the block enrichment must never surface a handoff not
produced by the current run's current step; since none exists when `artifact_refs`
is empty, the enrichment surfaces nothing (no `validated_handoff_path`) and MAY
carry a `no_current_artifact` detail (run+step). The role-wide glob and its
`_build_handoff_lookup` closure + `handoff_lookup` injection are retired.

### FR2 — Terminal APPROVED review declares a consumer that can never run (`implement-review-completed-run-leaves-unconsumed-required-payload`)

`dadaia_workspace/features/lifecycle/pipeline.py:404-422`
(`run_implement_review_loop`): on every review round it calls `resolver.produce(...)`
with `declared_consumers=(implement_step.label,)` **and**
`retention_mode=RetentionMode.PROMOTE_TO_EVIDENCE`, then — when
`verdict == "APPROVED"` (already known at line 403, before the produce) — sets
`status=COMPLETED` and returns (lines 417-422). The declared `implement` consumer
for that final verdict **can never run** after terminal completion, so the
payload's `consumption_state()` stays `PRODUCED`. The doctor's unconsumed-required
gate (`features/lifecycle/workflow_handoff_doctor.py:126-129`) fires on any
terminal-run record with **non-empty** `declared_consumers` and state ≠
`CONSUMED_ALL` — so a promote-to-evidence terminal verdict is *structurally
guaranteed* to be flagged. Net: a successful `implement-review` leaves state its
own `handoffs doctor` calls invalid.

**Invariant to restore:** a terminal APPROVED review payload (which survives on
its `PROMOTE_TO_EVIDENCE` retention, not on downstream consumption) must not
declare a consumer that can never run. The producer already knows the verdict at
produce time (line 403), so it declares `()` consumers on the APPROVED/terminal
round and `(implement_step.label,)` only on a REJECTED round (where the next
`implement#N` genuinely consumes the rejection digest). The doctor gate at
line 126 is correct and unchanged — the producer over-declaration is the cause.

### FR3 — Implement write-scope not derived from TASKS.md (`pipeline-does-not-derive-write-scope-from-tasks`)

`dadaia_workspace/features/lifecycle/pipeline.py:517-537` `_scope` assembles the
implement step's `allowed_paths` as `(handoff_glob, *step.extra_allowed_paths)`
for non-review steps, and `PipelineStep.extra_allowed_paths` is populated **only**
from the CLI `--write-scope` flag. There is **no** code path that resolves the
reserved `[-]` task from `<specs_dir>/releases/<release>/TASKS.md` and parses its
`Write set:` line. The SDD task file declares the legal implementation surface
once; the pipeline ignores it, forcing the operator to hand-copy every task's
write set on every invocation (and risking under-scoped implement workers that
emit no-op handoffs).

**Invariant to restore:** for a release implementation pipeline, the engine
resolves the active `[-]` task in `TASKS.md`, parses its declared `Write set:`
globs, and unions them into the implement (non-review) step's `allowed_paths`
automatically. `--write-scope` remains an additive escape hatch, never a
requirement. `specs_dir` is already wired to the pipeline container
(`build_lifecycle_pipeline`), so no new resolution mechanism is invented.

---

## Functional requirements

### FR1 — Remove the run-unscopable block-evidence disk-glob (architect F1)
- **FR1.1** Remove the role-keyed disk-glob
  (`context_dir.glob('*-{agent}-*.handoff.json')`) as a block-evidence source.
  The block enrichment must not derive `validated_handoff_path` from any
  cross-run/role-wide filename match. Retire `_build_handoff_lookup`
  (`container.py:509-560`), its `handoff_lookup` injection through
  `build_lifecycle_pipeline`/`build_lifecycle_phase_workflow`/`LifecycleAgentRunner`,
  and `_lookup_validated_handoff`'s disk call.
- **FR1.2** When a create/implement worker returns empty `artifact_refs`, the
  block detail carries **no** `validated_handoff_path` and MAY carry an explicit
  `no_current_artifact` detail naming the run and step (observability).
- **FR1.3** No cross-run/cross-task handoff is ever surfaced by the block.
- **FR1.4** The no-op-create BLOCK invariant is untouched: empty `artifact_refs`
  still BLOCKs. Enrichment never converts a block to a pass.
- **FR1.5 (architect F2)** Reconcile the pre-existing v0.1.66 FR8 test
  `tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py::test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty`,
  which asserts the OLD behavior (seeded role handoff surfaced). Under FR1 it must
  invert: assert **no** `validated_handoff_path` for the seeded file (or the
  `no_current_artifact` detail), with a documented reason referencing the FR8→FR1
  correction. This test file is in the FR1 write set.

**AC1.1** A fresh pipeline run whose implement worker returns empty
`artifact_refs`, with an unrelated older `*-software-engineer-*.handoff.json`
present in the context handoff dir, blocks with `validated_handoff_path` **absent**
(never the stale file).
**AC1.2** The v0.1.66 FR8 test is corrected to expect no stale surfacing; full
suite green under both the new and corrected tests (no contradiction).
**AC1(repro)** executed-path test `test_block_evidence_is_run_scoped` (in
`tests/integration/cli/`) seeds a stale handoff + drives a fresh fake-harness
pipeline run; FAILS on current code (stale path surfaced), PASSES after FR1.

### FR2 — Terminal review payload declares no phantom consumer
- **FR2.1** In `run_implement_review_loop`, the `review_qa` payload declares
  `declared_consumers=()` when `verdict == "APPROVED"` (terminal) and
  `(implement_step.label,)` only when `verdict != "APPROVED"`.
- **FR2.2** No change to the doctor gate (`workflow_handoff_doctor.py:126`) or to
  `retention_mode` — the promote-to-evidence retention is preserved.

**AC2.1** After an `implement-review` run reaches APPROVED (fake harness),
`WorkflowHandoffDoctor.run()` over the same run store returns `ok=True` with no
`unconsumed_required` finding.
**AC2.2** A REJECTED-then-APPROVED sequence still declares the `implement`
consumer on the rejected round(s) (the digest is genuinely consumed next round)
and `()` on the terminal approved round.
**AC2(repro)** executed-path test `test_terminal_implement_review_leaves_no_unconsumed_required`;
FAILS on current code, PASSES after FR2.

### FR3 — Derive implement write-scope from TASKS.md
- **FR3.1** Add a resolver `write_scope_from_tasks(specs_dir, release_id) ->
  tuple[str, ...]` that reads `<specs_dir>/releases/<release>/TASKS.md`, locates
  the reserved task, and parses its `Write set:` entry. **Deterministic grammar
  (architect F3):**
  - **Reserved task:** the task whose marker is `[-]`. If **not exactly one** `[-]`
    exists (zero, or multiple), return `()` — never guess.
  - **Write set line:** the `Write set:` bullet within that task's block, up to the
    next `- **`/`###` bullet or a blank line (multi-line continuation joined).
  - **Glob extraction:** take backtick-delimited spans that are **path-shaped**
    (contain `/` or a filename extension) and appear **before the first `(`** on
    the line. A trailing parenthetical annotation (e.g. `(new, additive)`,
    `` (`run_implement_review_loop` only) ``) is stripped and its inner backticks
    are **not** captured as paths.
  - **`none`:** a `Write set:` of the literal `none` (case-insensitive) ⇒ `()`.
  - Absent TASKS.md / no releases dir ⇒ `()` (no crash).
- **FR3.2** The pipeline unions the resolver output into the implement
  (non-review) step's `extra_allowed_paths`, before `--write-scope` extras.
  Review steps stay handoff-only (unchanged; the `is_review` gate at
  `pipeline.py:536` is preserved).
- **FR3.3** `--write-scope` remains an additive escape hatch; passing it is no
  longer required for a normal pipeline run.

**AC3.1** With a fixture `TASKS.md` carrying a `[-]` task whose `Write set:` lists
`` `foo/bar.py` ``, a pipeline implement step's built request `allowed_paths`
contains `foo/bar.py` **without** any `--write-scope` flag.
**AC3.2** No reserved `[-]` task (or not exactly one) ⇒ implement scope is exactly
the prior behavior (handoff glob + any `--write-scope`), no crash.
**AC3.3 (grammar, architect F3)** The resolver correctly handles: (i) a
comma-separated multi-glob line `` `a/b.py`, `c/d.py` `` → both captured; (ii) a
line whose annotation contains backticks `` `a/b.py` (`some_func` only) `` → only
`a/b.py` captured, `some_func` NOT captured; (iii) `Write set: none` → `()`.
**AC3(repro)** executed-path test `test_implement_scope_derived_from_tasks`;
FAILS on current code (allowed_paths lacks the task write set), PASSES after FR3.

### FR4 — Full-pipeline end-to-end acceptance test (the missing test)
- **FR4.1** Add an executed-path E2E that provisions a **throwaway spec-context**
  under `tmp_path` (a real `repos/<slug>/specs/` tree with an `Aprovado`
  SPEC/PLAN/TASKS and a reserved `[-]` task with a `Write set:`), then drives
  `dadaia lifecycle pipeline` (and `implement-review`) on the **fake** harness end
  to end, asserting: (a) evidence selected is run-scoped (FR1), (b) the terminal
  run passes `handoffs doctor` (FR2), (c) the implement scope includes the TASKS
  write set (FR3). This is the operator-workflow test that was missing.
- **FR4.2** The E2E runs hermetically (its own `tmp_path` workspace; no mutation
  of the live workspace, no real binaries, `-p no:cacheprovider`).

**AC4.1** `test_pipeline_end_to_end_on_throwaway_context` is green and, by
construction, would have been RED on pre-FR1/2/3 code (it asserts all three
invariants).

### FR5 — Regression & suite integrity
- **FR5.1** Full `pytest` (workspace repo) green; `ruff format --check`,
  `ruff check`, `mypy --strict`, `lint-imports` (9 contracts) all green.
- **FR5.2** No pre-existing test weakened to accommodate a fix; any test that
  encoded the buggy behavior is corrected with a documented reason.

---

## Non-goals
- Context/session resolution, CLI `--context` parity, preflight wiring — **Release B (v0.1.69)**.
- `agent_tier` doc/schema drift, gitignore intake — **Release C (v0.1.70)**.
- No PyPI publish.

## Out-of-scope paths (write allowlist for this release)
- `dadaia_workspace/container.py` (FR1 — retire `_build_handoff_lookup` + injection)
- `dadaia_workspace/features/lifecycle/agent_runner.py` (FR1 — drop disk lookup, add `no_current_artifact`)
- `dadaia_workspace/features/lifecycle/pipeline.py` (FR2 review-loop; FR3 `_scope`)
- `dadaia_workspace/features/lifecycle/tasks_write_scope.py` (FR3, new)
- `dadaia_workspace/cli/commands/lifecycle.py` (FR3 wiring)
- `tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py` (FR1.5 — invert FR8 assertion)
- `tests/integration/cli/**`, `tests/e2e/features/**`, `tests/unit/**` (RED-first proofs + FR4 E2E; co-located with siblings — architect F4)
- `specs/releases/v0.1.68/**`, `specs/bugs/**` (ADDITIVE), `specs/memory/**` (CLOSURE only)
