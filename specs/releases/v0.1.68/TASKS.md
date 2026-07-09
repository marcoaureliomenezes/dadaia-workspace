# TASKS — Release v0.1.68 — Lifecycle Evidence/Handoff Engine Correctness

> **Status:** Aprovado
> **Release ID:** v0.1.68
> **Owner:** product-engineer

Marker contract: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]`
per owner unless disjoint write sets are declared. RED-first: every fix task
starts by committing the failing proof, confirming it fails on current code,
THEN implementing the fix.

---

## Wave A — FR1: run-scoped block evidence

### T-68-01 — RED: block evidence must not surface a stale role handoff `[x]`
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_block_evidence_run_scoped.py` (new, additive — co-located with lifecycle siblings, architect F4)
- **Task:** Executed-path test: seed `.dadaia/handoff/<ctx>/<old-UTC>-software-engineer-<slug>.handoff.json`
  (a valid handoff) in a `tmp_path` workspace, drive a fresh fake-harness
  pipeline whose implement worker returns SUCCEEDED + empty `artifact_refs`, and
  assert the block detail has **no** `validated_handoff_path` referencing the
  seeded stale file. CONFIRM RED (current code surfaces the stale path).
- **AC:** SPEC AC1(repro) RED half.

### T-68-02 — GREEN: remove the run-unscopable disk-glob enrichment `[x]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `dadaia_workspace/features/lifecycle/agent_runner.py`,
  `tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py` (FR1.5 — invert FR8 assertion)
- **Preconditions:** T-68-01 `[x]`
- **Task (architect F1+F2):** Remove `_build_handoff_lookup` (`container.py:509-560`)
  and its `handoff_lookup` injection through
  `build_lifecycle_pipeline`/`build_lifecycle_phase_workflow`/`LifecycleAgentRunner`;
  drop `_lookup_validated_handoff`'s disk call. When `artifact_refs` is empty, the
  block detail carries no `validated_handoff_path` and MAY carry a
  `no_current_artifact` detail (run+step). Preserve the no-op BLOCK invariant.
  **Invert** `test_lifecycle_pipeline_v0166_repro.py::test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty`
  to assert the stale file is NOT surfaced, with a documented reason (FR8→FR1).
  Re-run T-68-01 → GREEN; full lifecycle suite green.
- **AC:** SPEC AC1.1, AC1.2, AC1(repro) GREEN half.

## Wave B — FR2: terminal payload declares no phantom consumer

### T-68-03 — RED: terminal implement-review leaves no unconsumed_required `[x]`
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_implement_review_terminal_consumption.py` (new)
- **Task:** Executed-path test: run `implement-review` to APPROVED on the fake
  harness, then run `WorkflowHandoffDoctor.run()` over the same run store; assert
  `report.ok is True` (no `unconsumed_required`). CONFIRM RED.
- **AC:** SPEC AC2(repro) RED half.

### T-68-04 — GREEN: declare () consumers on APPROVED terminal round `[x]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/pipeline.py` (`run_implement_review_loop` only)
- **Preconditions:** T-68-03 `[x]`
- **Task:** In `run_implement_review_loop`, set
  `declared_consumers=() if verdict == "APPROVED" else (implement_step.label,)`
  at the `resolver.produce(...)` call (pipeline.py:404-415); retention unchanged.
  Re-run T-68-03 → GREEN. Add/confirm AC2.2: a REJECTED→APPROVED sequence still
  declares the implement consumer on rejected rounds. Full suite green.
- **AC:** SPEC AC2.1, AC2.2, AC2(repro) GREEN half.

## Wave C — FR3: derive implement write-scope from TASKS.md

### T-68-05 — RED: implement scope derived from TASKS write set `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/unit/features/lifecycle/test_tasks_write_scope.py` (new — resolver grammar unit tests),
  `tests/integration/cli/test_implement_scope_from_tasks.py` (new — executed-path)
- **Task:** Executed-path test: fixture `TASKS.md` with a `[-]` task whose
  `Write set:` lists `` `foo/bar.py` ``; drive a pipeline implement step (no
  `--write-scope`) and assert the built request `allowed_paths` contains
  `foo/bar.py`. PLUS grammar unit tests for AC3.3: (i) comma-multi-glob both
  captured, (ii) annotation-with-backticks — inner token NOT captured, (iii)
  `Write set: none` → `()`, (iv) not-exactly-one `[-]` → `()`. CONFIRM RED.
- **AC:** SPEC AC3(repro) RED half, AC3.3.

### T-68-06 — GREEN: TASKS write-scope resolver (grammar F3) + pipeline union `[ ]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/tasks_write_scope.py` (new),
  `dadaia_workspace/features/lifecycle/pipeline.py` (`_scope`/step assembly),
  `dadaia_workspace/cli/commands/lifecycle.py` (wire resolver into pipeline verb)
- **Preconditions:** T-68-05 `[x]`
- **Task:** Add `write_scope_from_tasks(specs_dir, release_id) -> tuple[str, ...]`
  implementing the SPEC FR3.1 deterministic grammar exactly (exactly-one `[-]`;
  Write-set line to next bullet/blank; path-shaped backtick spans before first
  `(`; strip trailing parenthetical; `none`→`()`; absent→`()`). Union into the
  implement (non-review) step's `extra_allowed_paths` before `--write-scope`
  extras. Re-run T-68-05 → GREEN; full suite green.
- **AC:** SPEC AC3.1, AC3.2, AC3.3, AC3(repro) GREEN half.

## Wave D — FR4 + FR5: full-pipeline E2E + validation

### T-68-07 — Full-pipeline E2E on a throwaway context (the missing test) `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/e2e/features/test_pipeline_end_to_end_throwaway_context.py` (new — co-located with `test_lifecycle_journey_e2e.py`, architect F4)
- **Preconditions:** T-68-02, T-68-04, T-68-06 `[x]`
- **Task:** Provision a real `tmp_path` `repos/<slug>/specs/` with an `Aprovado`
  SPEC/PLAN/TASKS and a reserved `[-]` task carrying a `Write set:`; drive
  `dadaia lifecycle pipeline` + `implement-review` on the fake harness end to end;
  assert (a) run-scoped evidence (FR1), (b) terminal run passes `handoffs doctor`
  (FR2), (c) implement scope includes the TASKS write set (FR3). Hermetic,
  `-p no:cacheprovider`, no real binaries.
- **AC:** SPEC AC4.1.

### T-68-08 — QA validation + gate green `[ ]`
- **Owner:** qa-engineer
- **Write set:** none (ADDITIVE evidence handoff only)
- **Preconditions:** T-68-07 `[x]`
- **Task:** Full `pytest -p no:cacheprovider`, `ruff format --check`,
  `ruff check --no-cache`, `mypy --strict`, `lint-imports` (9). Confirm no
  pre-existing test weakened; confirm each FR's RED→GREEN transition at its parent
  commit. Emit QA handoff.
- **AC:** SPEC AC-FR5.1, FR5.2.
