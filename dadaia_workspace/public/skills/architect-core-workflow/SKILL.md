---
name: architect-core-workflow
description: >
  The software-architect's structured method, run BEFORE forming any recommendation
  or verdict. Two steps: (1) Understand the Problem, (2) Research Existing Solutions.
  PRIMARY CALLER: software-architect, in every DRAFT/REVIEW/ONBOARD mode and before
  any spec/release review verdict. Use when the architect must propose, choose, or
  judge an approach. Keeps recommendations evidence-based, not invented.
applyTo: "**"
---

# architect-core-workflow

Run both steps before recommending, choosing, or judging an approach. Skipping a step
is itself slop: a recommendation with no understood problem or no surveyed prior art is
a guess. Record the output of each step in the report you emit.

## Step 1 — Understand the Problem

Before any solution, extract and write down:

- **Core problem** — the one sentence describing what must actually be solved.
- **Constraints** — time, budget, team skills, existing systems it must live inside.
- **Success criteria** — how you will know the solution worked, in testable terms.
- **Assumptions** — make every implicit assumption explicit; an unstated assumption is a
  future incident.

When any of these is unclear, ask clarifying questions before proposing — do not invent
the missing context:

- What problem does this solve, for whom?
- What must it integrate with?
- Expected scale (now, and at growth)?
- Must-haves vs nice-to-haves?

Use `dadaia-grill-me` for operator-facing clarification. Never ask what `Read`/`Glob`/`Grep`
can answer.

## Step 2 — Research Existing Solutions

Do not design from a blank page when prior art exists. Use `WebSearch` to find:

- Existing tools / libraries that already solve this.
- Established implementation patterns.
- Known pitfalls and failure modes.
- Honest comparisons between candidates.

Evaluate each candidate on five axes:

| Axis | Question |
|---|---|
| Maturity | Is it proven in production, maintained, documented? |
| Fit | Does it solve **80%+** of the actual problem without contortion? |
| Integration | Does it fit the current stack and layer boundaries cleanly? |
| Cost | Build/run/maintenance cost vs. building it ourselves? |
| Risk | Lock-in, learning curve, abandonment, hidden complexity? |

Prefer the simplest candidate that clears all five axes. Build new only when no mature
option fits — and state why explicitly.

## Output

Both steps feed the architecture report. State the core problem, the constraints, the
candidates surveyed, and the chosen direction with its trade-off. A recommendation
without this trail is rejected as unfounded.
