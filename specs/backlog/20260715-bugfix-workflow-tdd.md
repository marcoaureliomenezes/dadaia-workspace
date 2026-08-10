---
name: bugfix-workflow-tdd
status: rejected
created: 2026-07-15
origin: operator demand 2026-07-15 (same session as the bug-hotfix doctrine decree)
owner: project-manager (curates)
intents:
  - subject: { kind: doc, ref: "memory/quality-assurance.md#Purpose" }
    change: "REJECTED (v0.3.0): the item asked for a bugfix workflow inside the dadaia-workflows engine; the engine was demolished in v0.3.0. The strict-TDD bug flow it wanted is law — constitution §1 bug-hotfix lane (register → root cause → RED → fix → GREEN → resolved + evidence). No mechanism needed."
---

# Backlog — `bugfix` dadaia-workflow: strict-TDD bug handling

## Demand (operator, verbatim intent)

A dedicated dadaia-workflow for bug handling with direct, strict prompts that do TDD:
get the problem registered in the bugs JSONL ledger, reproduce it, go for the root
cause, reproduce the root cause in different tests, review that the tests are reliable
(a review gate), then solve the root-cause problem until the created tests go green.
Well-dimensioned fragments; correct TDD structure for root-cause identification and
solution. This is the workflow-shaped codification of the **bug-hotfix doctrine**
(constitution §1 bug-hotfix lane; always-on `bug-hotfix-doctrine` rule): it must be
ceremony-free — no SPEC/PLAN/TASKS, no release.

## Architecture (proposed; grounded in the v0.2.x engine)

New workflow body `features/lifecycle/workflows/bugfix.py`, a thin
`FragmentGateWorkflow` subclass exactly like `audit.py` (step dataclass + module
`_SEQUENCE` + divergence hooks; terminal Python gate COMPLETEs with **no phase
transition and no release artifact**). CLI: `dadaia lifecycle bugfix --bug <bug-id>`
(alias `dadaia bugs fix <bug-id>`).

### Step sequence (fragments in `public/lifecycle_fragments/bugfix/`)

| # | step / fragment | role (persona) | kind | contract |
|---|---|---|---|---|
| 0 | `intake_register` (`intake-register.md`) | software-engineer | model | Normalize the report (symptom, exact repro command, expected contract, redaction per `bug-registration-guardrail`); append the `reported` event if absent. Output `bugfix-intake-handoff-v1`. |
| G0 | `ledger_gate` | — | python | Deterministic: the `reported` event for `bug_id` EXISTS on disk in `specs/bugs/bugs.jsonl` (existence gate — gates verify disk, never prose). |
| 1 | `reproduce` (`reproduce.md`) | software-engineer | model | Run the repro ON THE EXECUTED PATH (real CLI/tool, never a stub); capture commands, exit codes, output/traceback verbatim. Verdict REPRODUCED / NOT-REPRODUCIBLE. Output `bugfix-repro-handoff-v1`. |
| G1 | `repro_gate` | — | python | NOT-REPRODUCIBLE ⇒ BLOCK with disposition guidance (reject/needs-info); REPRODUCED ⇒ advance. |
| 2 | `root_cause` (`root-cause.md`) | software-engineer | model | Trace symptom → causal site (file:line + mechanism); state the violated contract; explicitly separate CAUSE from SYMPTOM; enumerate the **recurrence surface** (other call sites / inputs sharing the cause). Output `bugfix-rootcause-handoff-v1`. |
| 3 | `red_tests` (`red-tests.md`) | software-engineer | model | Write (a) one test reproducing the REPORTED symptom on the executed path and (b) tests pinning the ROOT CAUSE across its recurrence surface ("reproduce in different tests"). Run them; record RED failing-for-the-right-reason evidence per test. Output `bugfix-redtests-handoff-v1` (names every new test id + its run command). |
| G3 | `red_proof_gate` | — | python | Deterministic RED proof: the gate RE-RUNS the named tests itself and requires every one to FAIL pre-fix. A test that passes before the fix exists proves nothing and blocks. |
| 4 | `test_review` (`test-review.md`) | qa-engineer | model, **review** | Adversarial reliability review: fails for the right reason? executed-path (no fake harness — workflow-boundary law)? deterministic? would it re-fail if the fix were reverted? covers the recurrence surface? REJECTED ⇒ BLOCK (fix tests, resume). Output `bugfix-testreview-verdict-v1`. |
| 5 | `fix` (`fix-root-cause.md`) | software-engineer | model | Minimal fix at the CAUSAL SITE (no workaround, no symptom patch, no collateral refactor — cites `shared.anti-slop` + `shared.write-scope`); run the new tests and the surrounding suite; record commands/results. Output `bugfix-fix-handoff-v1`. |
| G5 | `green_proof_gate` | — | python | Deterministic GREEN proof: the gate RE-RUNS the named tests (all pass) + the full suite command (green). Trusts execution, not prose. |
| 6 | `fix_review` (`fix-review.md`) | code-reviewer | model, **review** | Does the diff remove the CAUSE (not mask the symptom)? Minimal? No behavior collateral? REJECTED ⇒ BLOCK. |
| G7 | `close_gate` | — | python | Appends the `resolved` event via the bugs store with the evidence triple (new test ids, fix commit sha, suite result) — `--release` anchor = package version, no release artifact; validates the terminal event landed; COMPLETEs the run. The completion handoff names the wheel obligation (`--build-wheel` flag optionally runs the build) for consumer-side validation. |

### Design principles applied

- **Gate-integrity law (v0.2.x stress-test lessons):** every Python gate verifies
  on-disk/executed reality (ledger events exist; tests actually re-run RED/GREEN by the
  gate itself) — never a model's claim.
- **Executed-path law (v0.1.68–70 post-mortem):** reproduce + red tests must exercise
  the real tool surface; fakes validate adapters, never the engine.
- **Recurrence-surface tests:** the ~40% need-unmet recurrence audit showed
  symptom-only fixes recur; pinning the cause across its other manifestations is what
  made structural fixes zero-recurrence.
- **Ceremony-free:** no SPEC/PLAN/TASKS, no grill, no task markers, no phase
  transition; the whole run is bug-scoped and resumable (`--resume-from`) after a
  review BLOCK.
- **Fragment dimensioning:** one narrow job per fragment (~1 screen each), reusing
  `shared/anti-slop.md`, `shared/write-scope.md`, `shared/output-handoff.md`; new
  output schemas `bugfix-*-v1` under `public/schemas/`.

### Deliverables when picked

Workflow body + 7 fragments + 6 schemas + CLI verb + panel Workflows-tab entry +
`workflow-policy` model mapping (software-engineer/qa-engineer/code-reviewer personas)
+ contract tests (one per gate, executed-path) + memory atom update
(`lifecycle-workflows` catalog).
