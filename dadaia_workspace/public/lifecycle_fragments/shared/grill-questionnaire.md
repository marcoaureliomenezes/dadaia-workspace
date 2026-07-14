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

# Grill questionnaire — evidence-first readiness checklist

You run headless. There is no operator on the other end of this turn, so an interview
posture that waits for an answer is a dead end — resolve everything the evidence can answer,
and record everything it cannot as `open_questions` for the next step to see. This is a
checklist you run against `grill_subject`, not a conversation.

## What must be known before the subject is ready

For each row, check `available_evidence` first; resolve silently when it answers, record how.

| Check | Evidence-answerable when |
|---|---|
| Internal consistency | Two artifacts describing the same thing agree, or the conflict is resolved by the newer/authoritative one. |
| Artifact vs reality | What an artifact claims matches the actual current state. |
| Already-answered questions | A "decision needed" whose answer already exists in `available_evidence`. |
| Naming | One canonical name is used, not two synonyms for the same concept. |
| Acceptance | Every requirement has a testable "how do we know it is done". |
| Dependencies | Anything this subject needs finished first is declared, not assumed. |
| Category / staleness | The subject is filed under the right concept and reflects the current truth, not an invalidated prior state. |

## Procedure

1. **Resolve from evidence.** Work the checklist above against `available_evidence`. Every row
   the evidence settles is resolved here, with the resolution recorded — never surfaced as a
   question.
2. **List what evidence cannot settle.** Anything left open after step 1 becomes one entry in
   `open_questions`: a precise, evidence-anchored statement of what is unknown and why the
   evidence does not settle it, each carrying your recommended resolution. Never a vague "it
   depends" — state the actual fork and your recommendation.
3. **Synthesize.** State the core problem resolved, the post-grill readiness, the required
   changes, any newly declared dependencies, and the decisions recorded.

## Output

A refinement result: every checklist row and how it was resolved (by evidence), the
`open_questions` list for anything evidence could not settle, the pending edits, and a
readiness verdict for the subject. The output is refinement, never an implementation
proposal.
