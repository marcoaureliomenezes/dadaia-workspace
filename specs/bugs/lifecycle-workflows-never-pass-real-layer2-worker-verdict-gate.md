---
name: lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate
status: Closed
severity: HIGH
reported: 2026-06-27
surface: features/lifecycle/workflows/release_definition.py (_SEQUENCE), features/lifecycle/agent_runner.py (_blocked_result), public/lifecycle_fragments/release_definition/release-scope.md
session_id: null
---

> **Closed in release v0.1.31 (2026-06-27).** Solved by scoping the verdict gate to **review**
> steps (Option 2, GRILL D-1): create steps now pass on a schema-valid/structural payload +
> `artifact_refs` + in-scope paths, with the `verdict` field ignored. Implemented at
> `agent_runner._blocked_result` (branch on a threaded `is_review`, all seven runner call sites +
> `PipelineStep.is_review`) and by bundling `shared.output_handoff` into every producing create
> step (`e87d54e7`); the PI extractor was hardened to accept bare/inconsistently-labelled real-worker
> payloads (`beba502c`). Evidence: live
> `tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py` PASSED — a real `pi` worker
> (gpt-5.5) drives `release_scope → spec_create` past step 1 with no `"agent result missing APPROVED
> verdict"` BlockedState. See `specs/_archive/releases/v0.1.31/CLOSURE.md` (Validations +
> Dispositions + Drifts).

**Symptom:** A `dadaia lifecycle release define --harness pi` (or codex) BLOCKs at the FIRST
step, `release_scope`, with `reason: "agent result missing APPROVED verdict"` — even after the
PI command bug (`pi-headless-command-trailing-dash-breaks-layer2`) is fixed and the worker
actually runs. No real Layer-2 worker run of the workflow has ever advanced past step 1.

**Root cause:** The typed gate (`agent_runner._blocked_result`) blocks any model step whose
worker output lacks `structured_output["verdict"] == "APPROVED"` — and per
`release_definition.py:329` this applies to **every** model step, "create or review". The
worker emits that verdict only as a fenced ```json block (PI: `_verdict_payload`; the contract
is documented in `shared/output-handoff.md`). BUT the first create step's fragment bundle does
NOT include that instruction:
```python
ReleaseStep(label="release_scope", ... fragment_id="release_definition.release_scope",
            shared_fragment_ids=("shared.grill_questionnaire",),   # <-- NOT shared.output_handoff
            produces="release-scope-handoff-v1")
```
`release-scope.md` carries no verdict instruction, and `grill_questionnaire` is not the
output-handoff contract — so a real worker is never told to end with `{"verdict":"APPROVED"}`.
`spec_create` DOES bundle `shared.output_handoff`, but the run never reaches it.

**Why it shipped:** every lifecycle-workflow test uses the FAKE runtime, which returns a canned
`{"verdict":"APPROVED"}` regardless of prompt. So the fake masks the gap: the workflows have
been validated ONLY against the fake worker, never end-to-end against a real pi/codex Layer-2
worker. This is the concrete reason "the dadaia-workflows working properly" has not actually
been demonstrable.

**Repro:**
```
dadaia release new v0.1.31
dadaia lifecycle release define --release-id v0.1.31 --harness pi --json
# -> blocked release_scope, reason "agent result missing APPROVED verdict"
```

**Expected / fix direction (needs a grill):** ONE of —
1. **Bundle the output-handoff contract into every model create step** (add `shared.output_handoff`
   to `release_scope` and any other create step that the gate requires a verdict from), so a real
   worker is instructed to emit the fenced APPROVED verdict; OR
2. **Scope the verdict gate to `is_review` steps only** — a create step passes on producing its
   declared payload (schema-valid) rather than on a self-reported APPROVED verdict (reserve the
   APPROVED/REJECTED verdict for the review steps, which is what `output-handoff.md` and the PI
   adapter comment already call "review verdicts ONLY").
Then add at least one **real-worker (non-fake) e2e** (pi and/or codex) that runs a workflow end
to end, so the fake can never again mask a worker-contract gap. NOTE a likely follow-on risk to
verify once step 1 is reached: real pi/codex may not RELIABLY emit the fenced verdict even when
instructed (worker-compliance) — the e2e must prove it does, or the extraction must be hardened.

**Notes:** No secrets/operator-local paths. Surfaced by the first real `--harness pi` workflow
run (operator demo, 2026-06-27). Directly blocks the operator's main goal (dadaia-workflows +
Layer-2 working properly). Pairs with `pi-headless-command-trailing-dash-breaks-layer2` (the PI
command fix that had to land first to even reach this gate).
