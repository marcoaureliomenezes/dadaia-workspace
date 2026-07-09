# PLAN: Release v0.1.71

**Status:** Aprovado
**Release ID:** v0.1.71
**Owner:** product-engineer

## Approach

Four independent, low-blast-radius fixes. Each is RED-first against a fixture derived
**verbatim from the real dd-chain-capture artifacts** (the axis the arc missed), then
proven GREEN, then replayed on the operator's remote against the live consumer.

### FR1 — `features/lifecycle/tasks_write_scope.py`
Generalize the grammar. Reserved-task resolution accepts either an inline-marked heading
(`### … `[-]``) or a bold `**T-x.y —**` heading paired with a fenced `[-] T-x.y` marker
block. The block spans from the resolved heading to the next task heading of EITHER shape.
Write-set bullet matches bold or plain key. `_extract_globs` iterates all backtick spans
and keeps the path-shaped ones, stripping parentheticals per span (no first-`(` cut).
Fixture: `tests/fixtures/tasks/ddcc_v0_2_0_TASKS.md` (real file, verbatim).

### FR2 — `cli/commands/lifecycle.py` (+ hygiene/doctor services accept a run filter)
Add `--context`/`--release-id` to `status` and `handoffs_doctor`. Thread an optional
`(context, release_id)` filter into `build_lifecycle_hygiene_service`/`build_workflow_handoff_doctor`
run enumeration (filter `LifecycleRun.context`/`release_id`). Absent filter = current behavior.

### FR3 — `cli/commands/context.py`
Extract a `_resolve_default_context(svc, workspace_root)` helper: among ALIVE contexts,
pick the one with a live incumbent session (newest `last_seen_at`), else first ALIVE.

### FR4 — `features/lifecycle/workflow_handoff_doctor.py`
Add `record.retention_mode is not RetentionMode.PROMOTE_TO_EVIDENCE` to the
`unconsumed_required` predicate. Import `RetentionMode` (already used in the module).

## Pinned substrate versions (bound at approval)
None — no dependency or substrate changes.

## Test strategy
- Unit RED-first per FR with real-artifact fixtures.
- Executed-path CLI tests (Typer runner) for FR2/FR3 asserting the parsed contract.
- Mutation-sanity: revert each fix → its targeted test goes RED.
- Remote replay of all four reporter commands against dd-chain-capture v0.2.0.
