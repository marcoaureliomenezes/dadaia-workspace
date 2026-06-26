---
id: shared.grill_questionnaire
role: shared
workflow: shared
step: grill_questionnaire
static_inputs: []
dynamic_inputs: [grill_subject, available_evidence]
output_schema: grill-refinement-v1
max_context_policy: summary
---

# Grill questionnaire — interrogate until shared understanding

Before a scope, SPEC, or demand is accepted, interrogate it. The goal is to surface
and resolve the defects that quietly destroy specs — inconsistencies, scope gaps,
ambiguous acceptance, undeclared dependencies, divergent naming, and assumptions
that turn out to be answered already. Resolve everything that the evidence can
resolve; bring to the operator only what evidence cannot.

## Defect taxonomy to hunt for

| Defect | Signature |
|---|---|
| Inconsistency between artifacts | Two artifacts describe the same thing in conflicting terms. |
| Artifact vs reality drift | What an artifact claims diverges from the actual current state. |
| Already-answered open question | A "decision needed" whose answer is present in the available evidence. |
| Divergent naming | One concept carried under two different names. |
| Ambiguous acceptance | A requirement with no testable "how do we know it is done". |
| Undeclared dependency | This work needs another item finished first, and nobody said so. |
| Wrong category / stale truth | An item filed under the wrong concept, or a "current truth" that a later change already invalidated. |

## Protocol

1. **Inspect before asking.** Never ask what the `available_evidence` can answer.
   Build an internal findings list, classify each by the taxonomy above, and resolve
   every evidence-answerable finding yourself — recording how you resolved it.
2. **Interview only on the unanswerable.** One question per turn, each anchored to a
   specific artifact and the exact conflicting or missing text, each carrying your
   recommended resolution. Never bundle two questions. Prioritize defects that would
   block or cause rework first; never ask about cosmetics or already-settled choices.
3. **Synthesize.** For the subject, state the core problem resolved, the post-grill
   readiness, the required changes, any newly declared dependencies, and the
   decisions recorded.

## Output

A refinement result listing every defect found, how each was resolved (by evidence
or by operator answer), the pending edits, and a readiness verdict for the subject.
Do not accept "it depends" as an answer — drive the decision tree to an actionable
resolution. The output is refinement, never an implementation proposal.
