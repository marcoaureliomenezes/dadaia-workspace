# SPEC — Release: v0.1.31 — make the dadaia-workflows actually run on a real Layer-2 worker

**Status:** Aprovado
**Release ID:** v0.1.31
**Owner:** product-engineer
**Opened:** 2026-06-27

> No `**Consumes:**` line. This is a **bug-driven** release (GRILL "Backlog"): no existing
> backlog item maps 1:1 to its real-worker-validation intent. `specs/backlog/` was scanned —
> nothing carries a consumable real-worker validation intent — so per the GRILL the SPEC
> declares no consumed backlog (do not invent one).

---

## 1. Problem and context

The two-layer architecture (Layer-1 entry harnesses; Layer-2 bounded workers behind
`AgentRuntimePort`) and the procedural dadaia-workflow engine have shipped incrementally
across v0.1.16–v0.1.30. The first real `dadaia lifecycle release define --harness pi` run
(operator demo, 2026-06-27) proved the engine **governs and dispatches** a real Layer-2 (PI)
worker correctly — but **no real worker run has ever advanced past step 1**. Every
lifecycle-workflow test to date runs the **fake** runtime, which returns a canned
`{"verdict":"APPROVED"}` regardless of prompt; the fake masked two HIGH worker-contract gaps
end-to-end:

1. **bug `pi-headless-command-trailing-dash-breaks-layer2` (HIGH).** `PiHeadlessAdapter._command`
   built `pi … -p -`; the installed `pi` rejects the trailing `-` ("Unknown option: -"), so PI
   was non-functional headless and every `--harness pi` step BLOCKed at step 1 with
   `reason: "Error: Unknown option: -"`. The unit test froze the broken argv against a **fake**
   runner, so the malformed real command shipped. **The fix already landed on this branch**
   (commit `c8513fa5`, `-p -` → `-p`).
2. **bug `lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate` (HIGH, OPEN).** After
   the command fix, a real worker runs but BLOCKs at the first step (`release_scope`) with
   `reason: "agent result missing APPROVED verdict"`. The typed gate
   (`agent_runner._blocked_result`) requires `structured_output["verdict"] == "APPROVED"` from
   **every** model step (`release_definition.py:329` comment: "Every model step — create or
   review"). But `release_scope` is a *create* step bundling only `shared.grill_questionnaire`
   — the worker is never instructed to emit a verdict. This is a **drift**: the workflow's own
   module docstring states the design — *"Each **review step's** structured verdict
   (APPROVED / REJECTED) is read by Python via the typed gate"* — and the PI extractor docstring
   calls the fenced verdict "the in-band channel for **review verdicts ONLY**." The
   implementation drifted to apply the review-only gate to all model steps.

The theme is to **close the gap between "the workflow engine dispatches a real Layer-2 worker"
and "a real Layer-2 worker completes a workflow step under the typed gate"** — by restoring the
documented review-only gate design (root cause, not a workaround), instructing create steps to
emit their schema'd payload, re-verifying + hardening the PI command, and adding an **anti-fake**
real-worker e2e so a fake can never again mask a worker-contract break.

The mandatory `dadaia-grill-me` gate was run on the picked bug set before this SPEC (record:
`specs/releases/v0.1.31/GRILL.md`, `status: Aprovado`). Its decisions (D-1..D-7) and open
questions (OQ-1..3) are binding and are reflected below.

---

## 2. Objective

Make a real `pi`/`codex` Layer-2 worker run a dadaia-workflow step end-to-end under the typed
gate — by scoping the verdict gate to **review** steps, giving create steps a schema'd-payload
success contract, adopting + hardening the PI command fix, and proving it with an **anti-fake**
real-worker e2e — **by extending the existing runner/gate/fragment seams only, never building a
parallel subsystem** (D-5).

---

## 3. Scope

This release is **small and surgical** (D-5, anti-slop). The work maps to **four execution
waves** (A→D); see PLAN.md for the wave spine and sequencing. Acceptance criteria are numbered
`A1..An`, grouped by cluster.

### 3.0 Anti-slop framing (binding — D-5)

Every change EXTENDS an existing seam; none introduces a parallel system:

- The verdict-gate fix extends `agent_runner._blocked_result` + threads an `is_review` signal
  into the existing `AgentRunnerInput`. For the four named workflows the per-step signal already
  exists (`ReleaseStep.is_review` etc.); for the pipeline a new `is_review` field is **added to
  the existing `PipelineStep` dataclass** (an extension, not a new step model — see
  DEFINITION-review C1).
- The create-step payload contract reuses the **single existing** `shared.output_handoff`
  fragment — it does NOT fork a parallel `create_handoff` fragment (D-2).
- The PI command fix is the already-landed `c8513fa5`; this release adopts + re-verifies +
  hardens it — it does NOT re-fix it (D-3).
- The real-worker e2e extends the existing env-gated live-test pattern
  (`tests/integration/pi_live/`, `codex_live/`) — no new harness, no new fragment family.

### 3.1 Cluster 1 — Verdict gate is review-only (Wave A; D-1, D-2)

**Scope:** restore the documented review-only gate design. The verdict requirement
(`structured_output["verdict"] == "APPROVED"`) must apply to **review** steps only; create
steps pass on producing a schema-valid payload, never on a self-reported `APPROVED` verdict.

**Ships:**
- An `is_review: bool = False` field added to `AgentRunnerInput`, threaded from the step's review
  signal at **every** runner call site.
- `_blocked_result` branches on `data.is_review`:
  - **Review step** (`is_review=True`): unchanged — block unless `succeeded` **and**
    `verdict == "APPROVED"` **and** `artifact_refs` populated **and** all paths in scope.
  - **Create step** (`is_review=False`): block unless `succeeded` **and** the worker emitted a
    **schema-valid fenced payload** (the extractor `pi_runtime._verdict_payload` returns the
    parsed payload only when its fenced `schema` field equals the step's `expected_schema`; that
    is what populates `artifact_refs`) **and** all paths in scope. The `verdict` field is
    **ignored** for create steps (D-2). A no-op worker emits no schema-matching payload →
    `_verdict_payload` returns `None` → `artifact_refs` stays empty → the existing `artifact_refs`
    check still BLOCKs (OQ-1). **No field-level schema validation is added** — that is out of
    scope (D-5 anti-slop); "schema-valid" means the `schema`-field equality the extractor already
    enforces.
- **The fix lands once in the runner so all callers benefit (D-5 / DEFINITION-review C1).** There
  are **SEVEN** runner call sites total (verified by `grep AgentRunnerInput(`), each of which must
  thread the correct `is_review`:
  1. `release_definition.py:~339` (`evaluate_gate_with_result`) → `is_review=step.is_review`.
  2. `audit.py:~281` (`evaluate_gate_with_result`) → `is_review=step.is_review`.
  3. `bug_report.py:~276` (`evaluate_gate_with_result`) → `is_review=step.is_review`.
  4. `research.py:~265` (`evaluate_gate_with_result`) → `is_review=step.is_review`.
  5. `backlog_definition.py:~444` (`evaluate_gate`) → `is_review=False` (its single model step
     `backlog_author` is a *create* step; `BacklogStep` is kind-based, no `is_review` boolean —
     pass the literal `False`).
  6. `pipeline.py:~205` (`run`) → `is_review=step.is_review` — **REQUIRES adding an `is_review`
     field to `PipelineStep`** (it has none today). `pipeline` drives the
     `QA_REVIEW → SECURITY_REVIEW → CODE_REVIEW` phases; its `review_qa`/`review_security`/
     `review_code` steps (`pipeline.py:~495–519`) are **review** steps that gate a release toward
     push. Without this field they would default `is_review=False` and **silently lose the
     `verdict == APPROVED` requirement on the very review gates that protect the push boundary** —
     the C1 regression. The `implement` step (a create step) keeps `is_review=False`.
  7. `phase_workflow.py:~102` (`run`) → thread `is_review` so a phase step targeting a **review
     phase** (`QA_REVIEW`/`SECURITY_REVIEW`/`CODE_REVIEW`) runs as `is_review=True`. `phase_workflow`
     is a generic single-step runner parameterized by `target_phase`; derive `is_review` from
     whether `target_phase` (or `from_phase`) is a review phase, or accept it as a caller argument.
- The misleading inline comment at `release_definition.py:~329` ("Every model step — create or
  review — … reads its structured verdict") is corrected to describe the review-only gate.
- The `evaluate_gate` docstring (`agent_runner.py:~128`) is corrected so it no longer states the
  pass condition as "an APPROVED verdict" for all steps.

**Explicitly out:** any change to the review-step contract (review steps keep requiring
`verdict == APPROVED` + evidence + in-scope paths — unchanged); field-level schema validation of
create-step payloads (the extractor's existing `schema`-field equality is the mechanism — D-5);
any new gate subsystem.

**Acceptance:**
- A1. `AgentRunnerInput` carries `is_review: bool = False`; **all seven** runner call sites thread
  the correct `is_review` (the four review-capable workflows + `backlog_definition`=False +
  `pipeline` + `phase_workflow`); `PipelineStep` gains an `is_review` field.
- A2. `_blocked_result` requires `verdict == "APPROVED"` **only** when `data.is_review` is true.
- A3. A create step (`is_review=False`) PASSES iff: the worker succeeded, emitted a **fenced
  payload whose `schema` field equals the step's `expected_schema`** (which is what populates
  `artifact_refs` via `pi_runtime._verdict_payload`), and wrote only in-scope paths — **regardless
  of the `verdict` field's value** (REJECTED, absent, or APPROVED). Full field-level schema
  validation is explicitly NOT added (D-5).
- A4. A no-op create-step worker (no schema-matching payload → `_verdict_payload` returns `None` →
  empty `artifact_refs`) still BLOCKs at the existing `_blocked_result` `artifact_refs` check (the
  gate is not made permissive — OQ-1).
- A5. A review step (`is_review=True`) BLOCKs on a missing/`REJECTED` verdict exactly as before
  (review contract unchanged); a regression test pins this for **both** a release-definition review
  step **and** a pipeline review step (`review_qa`/`review_security`/`review_code`).
- A6. The behavior is consistent across all seven callers; the four review-capable workflows thread
  `step.is_review`; `backlog_definition`'s model create step threads `is_review=False`; `pipeline`
  and `phase_workflow` thread `is_review=True` on their review steps/phases.
- A7. The misleading inline comment + `evaluate_gate` docstring are corrected to state the
  review-only gate.
- A8. After the runner fix, the pipeline `review_qa`, `review_security`, and `review_code` steps
  **STILL gate on `verdict == APPROVED`** (a test drives each pipeline review step with a
  missing/`REJECTED` verdict and asserts it BLOCKs) — the C1 regression is closed, not introduced.

### 3.2 Cluster 2 — Create-step payload emission (Wave A; D-2)

**Scope:** **every** producing model create step the gate requires evidence from must instruct
the worker to end with its schema'd payload + `artifact_refs`. Today `release_scope` bundles only
`shared.grill_questionnaire`, and `plan_create` / `tasks_create` bundle **no** shared fragments at
all — so "where missing" is **all of them**: a real worker is never told to emit a structured
result.

**Ships:**
- Bundle the **single existing** `shared.output_handoff` contract into **every** producing model
  create step — `release_scope`, `spec_create` (already has it), `plan_create`, `tasks_create`,
  and `backlog_definition`'s `backlog_author`. The fragment is reused as-is; per D-2 the gate
  ignores its `verdict` field for non-review steps (the fragment already declares
  `verdict`/`findings` as *review-only* additions atop the always-present
  `schema_version`/`agent`/`scope`/`metrics`/`artifact.type` fields).
- No new `create_handoff` fragment is created (explicitly forbidden by D-2).

**Explicitly out:** forking a parallel create-handoff fragment family; changing
`shared.output_handoff`'s schema (`handoff-v1.1`) — it is reused unchanged.

**Acceptance:**
- A9. `release_scope` bundles `shared.output_handoff` (alongside its existing
  `shared.grill_questionnaire`); a test asserts the assembled create-step prompt carries the
  output-handoff emission instruction.
- A10. No new `create_handoff` fragment exists; `shared.output_handoff` is the single contract
  (grep-verifiable: one output-handoff fragment family).
- A11. **Unconditionally over the full producing-step set (C3 / R-B):** a test derives the
  producing-step set **programmatically from each workflow's `_SEQUENCE`** (not a hard-coded
  list) and asserts `release_scope`, `spec_create`, `plan_create`, `tasks_create`, **and**
  `backlog_author` each carry a handoff-emission instruction in their fragment bundle.

### 3.3 Cluster 3 — PI command fix: adopt, re-verify, harden (Wave B; D-3)

**Scope:** the `c8513fa5` `-p -` → `-p` fix is correct and already on this branch. This release
keeps it, re-verifies the unit assertion, and hardens with a real `pi` smoke so a fake-frozen
unit test can never again ship a malformed real command.

**Ships:**
- Confirm `tests/unit/infrastructure/test_pi_runtime.py::test_pi_adapter_builds_controlled_command_and_env`
  asserts the argv ends `-p` with **no** trailing `-` (it currently asserts `argv[-1] == "-p"`
  and `"-" not in argv` — re-verify, do not weaken).
- A **real `pi` smoke** (env-gated per D-4) that runs the real `pi` binary through
  `PiHeadlessAdapter` and proves the command actually executes (no "Unknown option: -"). This is
  the regression guard the frozen-fake unit test could not provide.

**Explicitly out:** re-fixing the command (already landed); any change to the PI argv beyond
re-verification; a separate reasoning-effort flag (PI exposes none).

**Acceptance:**
- A12. The unit test asserts the PI argv ends `-p` with no trailing `-` (re-verified, not
  weakened).
- A13. A real `pi` smoke (env-gated, skipped by default) proves the real command executes
  without the "Unknown option: -" failure and yields a typed `AgentRunResult` (this is folded
  into / shares the env gate of the Cluster-4 e2e per D-4).

### 3.4 Cluster 4 — Anti-fake real-worker e2e (Wave C; D-4 — the core deliverable)

**Scope:** ≥1 e2e that exercises a **real** (non-fake) Layer-2 worker, env-gated and skipped by
default so CI / default `pytest` stay fully faked + green. This is the law that prevents a fake
from ever again masking a worker-contract gap.

**Ships:**
- A real-worker e2e (under `tests/integration/` mirroring the `pi_live/` / `codex_live/` opt-in
  pattern) that drives a real `pi` worker (codex as an optional second case if cheap — OQ-2
  defaults to `pi`) through a **minimal real workflow chain**.
- The chain is **`release_scope` → `spec_create`** — the **exact shipped-failure path** the two
  bugs blocked (OQ-3, fixed by QA review). The e2e drives a real create step (`release_scope`) plus
  the next step that consumes it (`spec_create`), proving advancement past step 1.
- The e2e is gated behind an explicit env flag (e.g. `DADAIA_E2E_REAL_WORKER=1`, alongside the
  existing `DADAIA_PI_LIVE` / `PI_BIN` / `ANTHROPIC_API_KEY` preconditions); it auto-SKIPs when
  unset. CI has no pi/codex credentials and must not burn operator credit on every run — default
  CI/pytest stay fully faked + green.
- The run command is documented (in the test module docstring + PLAN) so the operator can run it
  on demand.

**Worker-compliance risk (named — D-4, the reason this e2e is mandatory):** a real `pi`/`codex`
may not RELIABLY emit the fenced structured payload even when instructed. The e2e must **PROVE**
the chosen create/review step(s) emit a parseable payload, **or** the extraction
(`pi_runtime._verdict_payload` / the structured-output read) must be hardened to degrade safely,
with the residual recorded at CLOSURE.

**Explicitly out:** running the e2e in default CI; a non-opt-in real-worker test; a full
all-steps real run (the minimal chain past step 1 is the proof, not the whole 9-step sequence).

**Acceptance:**
- A14. ≥1 e2e exercises a **real** (non-fake) Layer-2 worker (pi first; codex optional second),
  env-gated (`DADAIA_E2E_REAL_WORKER=1` + live preconditions), and **SKIPPED by default** — a
  default `pytest` / CI run collects it and skips, staying fully faked + green.
- A15. The e2e asserts **concrete post-step-1 state, not "no exception" (R-C):** for the
  `release_scope` → `spec_create` chain — (a) the real `pi`/`codex` command actually executed
  (catches the D-3 class of bug); (b) the `release_scope` step is **not blocked** and yields a
  parsed `SUCCEEDED` `AgentRunResult`; (c) the run carries **no** `"agent result missing APPROVED
  verdict"` `BlockedState` (the create step passed under D-1/D-2 with **no** self-`APPROVED`); (d)
  the run **advanced beyond `release_scope`** (reached / ran `spec_create`).
- A16. The e2e PROVES the chosen step(s) emit a parseable payload for the real worker, OR the
  extraction (`pi_runtime._verdict_payload` / the structured-output read) is hardened to degrade
  safely and the residual is recorded for CLOSURE.
- A17. The run command is documented (test docstring + PLAN); a default `pytest` run shows the
  e2e SKIPPED (not failed, not errored).

### 3.5 Cluster 5 — Bug dispositions (Wave D — CLOSURE only; recorded now)

**Scope:** record the disposition plan now; flip statuses at CLOSURE (do NOT close the bugs in
this DEFINITION cycle).

**Plan (release-governance: bugs are always solved):**
- `pi-headless-command-trailing-dash-breaks-layer2` → solved by this release (Cluster 3 / D-3);
  status flips to `Closed` at CLOSURE with the real-`pi`-smoke evidence (A13).
- `lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate` → solved by this release
  (Clusters 1+2+4 / D-1/D-2/D-4); status flips to `Closed` at CLOSURE with the real-worker e2e
  evidence (A15).

**Acceptance:**
- A18. At CLOSURE, both bugs carry `status: Closed` with an evidence pointer (CLOSURE section /
  commit SHA) in the disposition sweep; neither is deleted (never-delete law).

---

## 4. Out of scope

- **Implementation itself: this release is DEFINE-ONLY (D-6).** Deliverable now is approved
  SPEC/PLAN/TASKS + a DEFINITION review (architect + qa). Every TASKS marker stays `[ ]`.
  Implementation begins only after the operator approves at the DEFINITION checkpoint and
  `ACTIVE.md` advances to IMPLEMENTATION. **No push** (standing operator constraint — D-6).
- **Re-fixing the PI command** — `c8513fa5` already landed; this release adopts + re-verifies +
  hardens it only (D-3).
- **Bundling `shared.output_handoff` into every create step to make the worker self-APPROVE**
  (GRILL Option 1, rejected) — the verdict gate is review-only (D-1); create steps pass on a
  schema-valid payload, not a self-reported `APPROVED`.
- **A parallel `create_handoff` fragment family** — forbidden by D-2; reuse the single
  `shared.output_handoff`.
- **Running the real-worker e2e in default CI / on every push** — env-gated, opt-in only (D-4);
  default CI/pytest stay fully faked + green.
- **Any new harness, plugin pack, or new fragment family** (D-5).
- **A full all-steps real workflow run** — the minimal chain past step 1 is the proof (D-4 / OQ-3).
- **`pyproject` version bump** — version stays `0.1.7` (no PyPI — D-7).

---

## 5. Laws (binding — from GRILL D-1..D-7)

- **L1 — Verdict is a REVIEW concept (D-1).** `verdict == "APPROVED"` is required on **review**
  steps only. A create step never self-approves; requiring it to is a category error that
  cheapens the review gate.
- **L2 — Create steps are still gated (D-2 / OQ-1).** Scoping the verdict off create steps must
  not make them gate-free: a create step passes only on a schema-valid payload (the extractor's
  `schema`-field equality) + populated `artifact_refs` + in-scope paths. A no-op worker still
  BLOCKs. No field-level schema validation is added (D-5).
- **L3 — One handoff contract (D-2).** Reuse the single `shared.output_handoff`; the gate ignores
  its `verdict` for non-review steps. No parallel create-handoff fragment.
- **L4 — Fix once at the seam, thread ALL SEVEN callers (D-5 / C1).** The verdict-gate fix lands
  in `agent_runner._blocked_result` (branch on threaded `is_review`) so all callers benefit; each
  of the **seven** runner call sites threads the correct flag (`release_definition`, `audit`,
  `bug_report`, `research`, `backlog_definition`, `pipeline`, `phase_workflow`). Threading is NOT
  optional for the pipeline/phase-workflow review steps — missing them silently drops the
  `verdict == APPROVED` gate on the qa/security/code review phases that protect the push boundary.
- **L5 — Adopt, don't re-fix (D-3).** The `c8513fa5` PI command fix is kept and hardened, never
  re-implemented.
- **L6 — Anti-fake law (D-4).** At least one real-worker (non-fake) e2e exists so a fake runtime
  can never again mask a worker-contract gap; it is env-gated and skipped by default.
- **L7 — Never delete a bug file.** Both bugs are dispositioned `Closed` with evidence at CLOSURE,
  never removed (release-governance never-delete law).
- **L8 — Extend existing seams only (D-5).** No parallel gate subsystem, no new harness, no new
  fragment family; software-architect enforces the root-cause + fidelity gates on this SPEC.

---

## 6. Memory files affected at closure

(Updated at CLOSURE, not now — DEFINITION authorship defers memory to CLOSURE per the
constitution §13 / `dadaia-release-closure` skill.)

- `specs/memory/architecture.md` — the typed-gate contract is **review-only**: review steps gate
  on `verdict == APPROVED` + evidence; create steps gate on a schema-valid payload + evidence.
- `specs/memory/tech-stack.md` — record the pinned `pi` build verified by the real `pi` smoke /
  real-worker e2e (the live-verified `pi` version). No new locked dependency expected.
- `specs/memory/product/index.md` + the affected workflow/lifecycle feature atom(s) — the
  dadaia-workflows now run on a real Layer-2 worker end-to-end; create-vs-review gate distinction;
  the env-gated real-worker e2e as the anti-fake guard.

---

## 7. Dependencies and risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Scoping the verdict gate off create steps accidentally makes create steps gate-free (a no-op worker passes) | HIGH | A3/A4/L2: create steps still require a schema-valid payload (extractor `schema`-equality) + populated `artifact_refs` + in-scope paths; an explicit no-op-worker-still-BLOCKs test (OQ-1) |
| R2 | Review-step contract regresses while threading `is_review` (release-definition reviews) | HIGH | A5: review steps keep requiring `verdict == APPROVED` + evidence; a regression test pins both a release-definition review path and a pipeline review path before/after the change |
| R3 (C1) | **Pipeline qa/security/code review steps silently lose `verdict == APPROVED`** after the runner fix — `PipelineStep` has no `is_review` field, so they default `is_review=False`, dropping the gate on the very reviews that protect the push boundary | HIGH | A1/A6/A8/L4: add `is_review` to `PipelineStep`; thread it at `pipeline.py:~205` and `phase_workflow.py:~102`; A8 drives each pipeline review step with a missing/REJECTED verdict and asserts it STILL BLOCKs |
| R4 | A real `pi`/`codex` does not reliably emit the fenced payload (worker-compliance) | HIGH | A16 / D-4: the e2e must PROVE the chosen step(s) emit a parseable payload, OR harden `_verdict_payload`/structured read to degrade safely; residual recorded at CLOSURE |
| R5 | The real-worker e2e leaks into default CI and burns operator credit / fails on missing creds | MEDIUM | A14/A17 / D-4: env-gated (`DADAIA_E2E_REAL_WORKER=1` + live preconditions), auto-SKIP by default, mirrors the existing `pi_live`/`codex_live` opt-in pattern |
| R6 | A producing create step still has no output-handoff instruction, so a real worker emits no payload and BLOCKs | MEDIUM | A9/A11: bundle `shared.output_handoff` into EVERY producing create step; a test derives the producing-step set from `_SEQUENCE` and asserts the bundle |
| R7 | A runner caller is missed (seven total) and falsely gates / fails to gate | MEDIUM | A1/A6: all seven call sites threaded; `backlog_definition`'s create step threads `is_review=False`; the runner-level fix benefits all callers |
| R8 | Scope creep on a bug-driven release | LOW | D-5 anti-slop framing; D-6 DEFINE-ONLY checkpoint lets the operator prune before any wave runs; architect fidelity gate |

**Upstream/sequencing:** Wave A (the gate + payload contract) is the keystone — it is what makes
a real create step pass. Wave B (PI command re-verify + smoke) depends only on the landed
`c8513fa5` and the live preconditions. Wave C (the real-worker e2e) depends on Wave A (the gate
fix) **and** Wave B (the working PI command) — it cannot prove "advances past step 1" until both
land. Wave D (dispositions) is CLOSURE-only. See PLAN.md for the full spine and justification.

**Open questions — resolved at the DEFINITION review (architect + qa); recorded here:**
- OQ-1 (RESOLVED, architect+qa): the gate ignores `verdict` for non-review steps AND still
  requires a schema-valid payload for create steps so a no-op worker BLOCKs. The mechanism is the
  extractor's existing `schema`-field equality (`pi_runtime._verdict_payload` returns `None` unless
  the fenced `schema` == `expected_schema`, which is what populates `artifact_refs`); **no
  field-level schema validation is added** (avoids D-5 scope creep). Encoded as A3/A4.
- OQ-2 (RESOLVED): the e2e targets `pi` first (operator demo path); `codex` as an optional cheap
  second case — encoded as A14.
- OQ-3 (RESOLVED, qa): the minimal real chain is **`release_scope` → `spec_create`** — the exact
  shipped-failure path — encoded as A15.
- C1 (RESOLVED, architect): SEVEN runner callers, not five; `PipelineStep` gains an `is_review`
  field; pipeline/phase-workflow review steps thread `is_review=True` — encoded as A1/A6/A8 + R3.
