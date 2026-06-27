---
release: v0.1.31
kind: grill-record
date: 2026-06-27
status: Aprovado
---

# Grill record — v0.1.31 (make the dadaia-workflows actually run on a real Layer-2 worker)

Operator demand 2026-06-27: *"make the dadaia-workflows actually run on a real Layer-2
worker. Define a full release."* This release is **bug-driven**, born from the first real
`dadaia lifecycle release define --harness pi` run (operator demo, 2026-06-27), which proved
the engine **governs and dispatches** Layer-2 correctly but **no real worker run has ever
advanced past step 1**. The mandatory grill below was run by the Layer-1 coordinator on the
picked set before SPEC authorship. Outcomes are BINDING scope.

## Theme
Close the gap between "the workflow engine dispatches a real Layer-2 worker" and "a real
Layer-2 worker completes a workflow step under the typed gate." Make a real `pi`/`codex`
worker run a workflow end-to-end, and add an **anti-fake** test law so the fake runtime can
never again mask a worker-contract gap.

## Picked set
1. **bug `pi-headless-command-trailing-dash-breaks-layer2`** (HIGH) — `PiHeadlessAdapter._command`
   built `pi … -p -`; the installed `pi` rejects the trailing `-` ("Unknown option: -"), so PI
   was non-functional headless. **Fix already landed on this branch** (commit `c8513fa5`,
   `-p -` → `-p`). The release adopts it as a tracked deliverable: re-verify + **harden with a
   real `pi` smoke** (the unit test froze the broken command against a fake runner — that is
   why it shipped).
2. **bug `lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate`** (HIGH, OPEN) — after
   the command fix, a real worker runs but BLOCKs at the first step (`release_scope`) with
   `"agent result missing APPROVED verdict"`. `agent_runner._blocked_result` requires
   `structured_output["verdict"] == "APPROVED"` from **every** model step, but `release_scope`
   is a *create* step bundling only `shared.grill_questionnaire` — the worker is never told to
   emit a verdict. The fake runtime returns a canned `APPROVED`, masking the gap.
3. **NEW — anti-fake real-worker e2e** — at least one e2e that runs a workflow step end-to-end
   against a **real** (non-fake) Layer-2 worker, so a fake can never again hide a
   worker-contract break.

## Adversarial grill → decisions (binding)

### D-1 — Verdict gate is a REVIEW concept; scope it to review steps (Option 2, not Option 1)
The bug offered two directions: (1) bundle `shared.output_handoff` into every create step so the
worker self-reports `verdict: APPROVED`; or (2) scope the verdict gate to `is_review` steps only.

**Decision: Option 2.** Grounds:
- `release_definition.py`'s own module docstring already states the design: *"Each **review
  step's** structured verdict (APPROVED / REJECTED) is read by Python via the typed gate …"* —
  the gate was specified as review-only; `_blocked_result` **drifted** to apply it to all model
  steps.
- `pi_runtime._verdict_payload` docstring: the fenced verdict block is *"the in-band channel for
  **review verdicts ONLY**."*
- A create step (`release_scope`, `spec_create`) **produces an artifact**; it does not *approve*
  anything. Requiring a create-step worker to self-emit `APPROVED` is a category error and
  cheapens the review gate (a worker "approving" its own draft).

Option 1 is **rejected** for those reasons.

### D-2 — Create-step success contract (minimal surface)
Scoping the verdict off create steps must not make them gate-free. A create step PASSES iff it:
(a) succeeds, (b) emits a structured payload matching its declared `produces` schema (→
populates `artifact_refs` / structured evidence), (c) writes only in-scope paths. It does **not**
require `verdict == APPROVED`.

**Decision:** reuse the single `shared.output_handoff` contract (do **not** fork a parallel
`create_handoff` fragment); the gate simply **ignores `verdict` for non-review steps**. Create-step
fragments that the gate requires evidence from (starting with `release_scope`) MUST bundle the
handoff-emission instruction so a real worker is told to end with its schema'd payload + artifact
refs. (`release_scope` currently bundles only `shared.grill_questionnaire`.) The
`is_review` signal already exists on `ReleaseStep` — thread it into `_blocked_result`. PLAN to
confirm every model step's bundle includes a handoff-emission instruction.

### D-3 — PI command fix: adopt, re-verify, HARDEN (don't re-fix)
The `c8513fa5` fix is correct. The release: keeps it; confirms `test_pi_runtime.py` asserts the
argv ends `-p` with no `-`; and adds a **real `pi` smoke** (env-gated, see D-4) so a unit test
freezing a fake can never again ship a malformed real command.

### D-4 — Anti-fake real-worker e2e (the core deliverable)
Add ≥1 e2e that exercises a **real** Layer-2 worker (pi and/or codex), NOT the fake runtime.
Constraints, binding:
- **Env-gated, opt-out of default CI/pytest.** CI has no pi/codex credentials and we must not
  burn the operator's Codex subscription on every run. Gate behind an explicit env flag (e.g.
  `DADAIA_E2E_REAL_WORKER=1`); `skip` by default; runnable locally on demand. Document the run
  command. (CI default stays fully faked + green.)
- **Must prove, end-to-end:** (a) the real `pi`/`codex` command actually executes (catches the
  D-3 class of bug); (b) the worker output parses to a structured result; (c) a *create* step
  passes the gate under D-1/D-2 with **no** self-`APPROVED`; (d) a minimal real chain advances
  past step 1 (target: `release_scope` → `spec_create`, or a single create + single review).
- **Worker-compliance risk (named):** a real `pi`/`codex` may not RELIABLY emit the fenced
  payload even when instructed. The e2e must PROVE it does for the chosen step(s), or the
  extraction must be hardened (and the residual recorded). This risk is the reason the e2e is
  mandatory, not optional.

### D-5 — Scope discipline (anti-slop)
Extend existing seams only: `agent_runner._blocked_result` (+ `AgentRunnerInput`/`ReleaseStep`
`is_review` threading), `release_definition._SEQUENCE` fragment bundles, the create-step fragment
bodies, and `pi_runtime`. **No** parallel gate subsystem, **no** new harness, **no** new fragment
family. software-architect enforces the root-cause + fidelity gates on the SPEC.

### D-6 — Branch / push / DEFINE-ONLY
`feature/v0.1.31` is branched off `feature/v0.1.30` (unmerged) + the `c8513fa5` PI fix. This is a
**DEFINE-ONLY** checkpoint: TASKS are authored but every marker stays `[ ]`; implementation begins
only after the operator approves at the DEFINITION checkpoint and `ACTIVE.md` advances to
IMPLEMENTATION. **No push** (standing operator constraint).

### D-7 — Version
Release id `v0.1.31`. `pyproject` version stays `0.1.7` (no PyPI — memory `project_v017_*`).

## Bug dispositions (release-governance: bugs are always solved)
- `pi-headless-command-trailing-dash-breaks-layer2` → solved by this release (D-3); status flips
  to `Closed` at CLOSURE with the real-`pi`-smoke evidence.
- `lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate` → solved by this release
  (D-1/D-2/D-4); status flips to `Closed` at CLOSURE with the real-worker e2e evidence.

## Backlog
No existing backlog item maps 1:1 to this bug-driven release. product-engineer to scan
`specs/backlog/` for any consumable real-worker-validation intent; if none, the SPEC carries **no
`**Consumes:**` line** (bug-driven release). Do not invent a backlog item.

## Open questions for DEFINITION (product-engineer + software-architect)
- OQ-1: D-2 mechanism — confirm gate ignores `verdict` for non-review steps **and** still requires
  schema-valid payload + artifact_refs for create steps (so a no-op worker still BLOCKs).
- OQ-2: Which real worker does the e2e target first — `pi` (operator's demo path) or `codex`
  (also credential-bearing)? Default `pi`; codex as a second case if cheap.
- OQ-3: Exact minimal real chain for D-4 (single create+review vs `release_scope`→`spec_create`).
