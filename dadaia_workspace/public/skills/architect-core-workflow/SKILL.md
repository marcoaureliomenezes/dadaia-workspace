---
name: architect-core-workflow
description: >
  The software-architect's structured method, run BEFORE forming any recommendation
  or verdict. Two steps: (1) Understand the Problem, (2) Research Existing Solutions.
  PRIMARY CALLER: software-architect, in every DRAFT/REVIEW/ONBOARD mode and before
  any spec/release review verdict. Use when the architect must propose, choose, or
  judge an approach. Keeps recommendations strictly evidence-based.
tldr: "Understand the problem, then survey prior art on 5 axes, before any recommendation or verdict."
applyTo: "**"
---

# architect-core-workflow

## 1. When

- Before forming any recommendation or verdict.
- Every DRAFT/REVIEW/ONBOARD mode, and before any spec/release review verdict.
- Skipping a step is slop — a recommendation with no understood problem or no surveyed prior art is a guess.

## 2. Steps

1. Extract the core problem: one sentence describing what must actually be solved.
2. Extract constraints: time, budget, team skills, existing systems it must live inside.
3. Extract success criteria: how you will know the solution worked, in testable terms.
4. Extract assumptions: make every implicit assumption explicit — an unstated one is a future incident.
5. Ask clarifying questions when any of the above is unclear — never invent the missing context.
6. Call the Skill tool with `dd-grill-me` for operator-facing clarification; never ask what `Read`/`Glob`/`Grep` can answer.
7. Use `WebSearch` to find existing tools/libraries, established patterns, known pitfalls, honest comparisons.
8. Score each candidate on: maturity, fit (80%+ of the problem without contortion), integration, cost, risk.
9. Prefer the simplest candidate that clears all five axes.
10. Build new only when no mature option fits — state why explicitly.
11. Record both steps' output in the report you emit: core problem, constraints, candidates surveyed, chosen direction, trade-off.

## 3. Done when

- The core problem, constraints, success criteria, and assumptions are written down.
- Prior art was searched and at least one candidate was scored on all five axes.
- The report states the trade-off behind the chosen direction — a recommendation with no trail is rejected as unfounded.

## 4. References

- `dd-grill-me` — operator-facing clarification protocol.
- `WebSearch` — prior-art discovery.
