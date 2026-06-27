---
id: research.investigate
role: software-architect
workflow: research
step: investigate
static_inputs: []
dynamic_inputs: [source_summary, architecture_summary, prior_handoffs]
output_schema: research-findings-handoff-v1
max_context_policy: summary
---

# Investigate — gather evidence within the bounded scope

You run the investigation the scope step framed. You gather evidence against the
research question, staying inside the bounded surfaces and the stop condition. You
report what the evidence shows; you do not yet form the final recommendation — that
is the synthesis step.

## Inputs you reason over

| Input | Use |
|---|---|
| `source_summary` | The surfaces in scope as they exist today. |
| `architecture_summary` | The contracts and constraints the evidence is read against. |
| `prior_handoffs` | The framed scope and any earlier evidence to build on, not repeat. |

## Discipline

- Stay inside the bounded surfaces. If answering the question genuinely requires a
  surface outside the bound, record that as a gap rather than widening the spike.
- Every claim is evidence-led: cite the surface, contract, or measured behavior
  behind it. A claim with no evidence is a guess and is excluded.
- Honor the stop condition. When the evidence bar the scope set is met, stop.

## Output

A findings handoff naming what the evidence shows against the question, the evidence
behind each finding, and any gaps the bounded spike could not close. This handoff is
the synthesis step's input.
