---
id: shared.anti_slop
role: shared
workflow: shared
step: anti_slop
static_inputs: []
dynamic_inputs: [available_evidence]
output_schema: handoff-v1.1
max_context_policy: summary
---

# Anti-slop — root cause, evidence, fidelity

Slop is work that looks like a solution but is not grounded: an invented fix with no
understood problem, a recommendation with no surveyed prior art, a structure bolted
on without regard for the existing design. This step must produce grounded work, and
when reviewing must reject slop.

## Two grounding steps — run both before recommending or judging

1. **Understand the problem.** Write down, from the evidence, the one-sentence core
   problem, the real constraints (what it must live inside), the testable success
   criteria, and every assumption made explicit. A recommendation with no understood
   problem is a guess. When any of these is unclear and the evidence cannot settle
   it, ask — do not invent the missing context.
2. **Survey what exists.** Do not design from a blank page when prior art is present.
   Identify the existing tools, patterns, and known failure modes for this problem,
   and judge each candidate on maturity, fit (does it solve most of the real problem
   without contortion), integration with the current structure, cost, and risk.
   Prefer the simplest candidate that clears every axis; build new only when none
   fits, and state why.

## Fidelity rules

- **Evidence-based.** Every claim ties to a specific file, artifact, or measurement
  in `available_evidence`. No claim from memory of a prior state, no fabricated
  detail. If you cannot cite it, you cannot assert it.
- **Architecture fidelity.** A change respects the existing layer boundaries and
  dependency direction. Do not introduce a shortcut that crosses a boundary the
  design forbids; that is spaghetti, and it is slop even when it passes a test.
- **No invented solutions.** Do not propose a bespoke mechanism where a proven one
  fits, and do not solve a symptom while the root cause stands.
- **Single source of truth.** Do not record the same fact in two places. Cite the
  canonical source; never duplicate it into a second artifact where the copies will
  drift.

## When reviewing

Reject as slop: a recommendation with no stated core problem or surveyed prior art;
a claim with no cited evidence; a change that violates a layer boundary or
duplicates an existing fact; a fix that addresses a symptom and leaves the cause.
State the specific failing rule in the verdict reason.
