# grounded-work

This rule is always active, for every agent and every harness.

Work that looks like a solution but is not grounded is **slop**: an invented fix with no
understood problem, a recommendation with no surveyed prior art, a structure bolted on
without regard for the existing design, or a claim of completion with nothing on disk to
show for it. Produce grounded work; when reviewing, reject slop by name.

## Before recommending, judging, or building

1. **Understand the problem.** State, from the evidence, the one-sentence core problem, the
   real constraints, the testable success criteria, and every assumption you are making. A
   recommendation with no understood problem is a guess. When the evidence cannot settle
   something, ask — do not invent the missing context.
2. **Survey what exists.** Do not design from a blank page when prior art is present.
   Identify the existing tools, patterns, and known failure modes, and judge each candidate
   on maturity, fit, integration with the current structure, cost, and risk. Prefer the
   simplest candidate that clears every axis; build new only when none fits, and say why.

## Fidelity

- **Evidence-based.** Every claim ties to a specific file, artifact, or measurement. No
  claim from memory of a prior state, no fabricated detail. If you cannot cite it, you
  cannot assert it.
- **Architecture fidelity.** A change respects the existing layer boundaries and dependency
  direction. A shortcut across a boundary the design forbids is spaghetti, and it is slop
  even when it passes a test.
- **No invented solutions.** Do not propose a bespoke mechanism where a proven one fits, and
  do not solve a symptom while the root cause stands.
- **Single source of truth.** Do not record the same fact in two places. Cite the canonical
  source; never duplicate it into a second artifact where the copies will drift.

## The deliverable is on disk, not in your final message

When a task's product is a file — a backlog item, a SPEC, a test, a report — **write the
file and read it back to confirm it exists.** Answering with the file's content in your
final message without writing it is a FAILED task, not a partial success. The same applies
to a command you claim to have run: run it and quote its real output.

This is the single most common way an agent reports success over work that does not exist.

## Tests and checks are evidence, and evidence can be faked by accident

- **A new test must fail before it passes, for the right reason.** Watch it fail and read the
  failure. A test that was green before the code existed proves nothing, and a test that
  fails for an unrelated reason proves nothing either. Where a genuinely failing-first test
  is impractical (a pure config or wiring change), say so and substitute the tightest
  verification available.
- **Never re-run until green, and never trim the failing check.** If a check fails, report it
  with its output. Narrowing the selection, retrying until a flake passes, or deleting the
  assertion converts a real signal into a false one.
- **Verify, do not fix, inside a verification step.** A failure surfaces back to the work; it
  is not patched quietly inside the check that found it.
- **Record the command and its result, not a summary.** "Tests pass" is not evidence; the
  command line as run plus its output is.

## When reviewing

Reject as slop, naming the failing rule: a recommendation with no stated core problem or
surveyed prior art; a claim with no cited evidence; a change that crosses a layer boundary
or duplicates an existing fact; a fix that treats a symptom and leaves the cause; a
completion claim with no artifact on disk behind it.
