---
name: dd-grill-me
description: >
  Interview the operator to shared understanding on a demand, spec, or backlog item,
  resolving by inspection everything the repo/CLI/a subagent can answer first. Use
  for ambiguous intake, the mandatory pre-SPEC session of a release candidate, a
  focused spec question, or when the operator says "grill", "refine specs", or
  "review backlog".
---

# dd-grill-me — SDD Spec Refinement

Reach shared understanding by mapping every open branch of the demand as a design tree, then working it in rounds until the tree is fully visited.

## 1. When

- The operator's demand is ambiguous and needs intake refinement (`project-manager`).
- A release is being defined and needs its mandatory pre-SPEC session (`product-engineer`, `dd-release-definition` §3).
- A single spec or feature question needs a focused leaf answer.
- The operator says "grill", "refine specs", or "review backlog".

## 2. Steps

1. Search the repo (`Read`/`Glob`/`Grep`) and run the CLI before framing a single question — finding facts is your job.
2. Dispatch a subagent for deeper exploration when needed.
3. Classify each gap against `PROBLEM-TAXONOMY.md` before deciding inspection vs promotion to the tree.
4. Map every remaining open question as a node; a dependent question hangs beneath its prerequisite as a child.
5. Identify the frontier: every question whose prerequisites are already settled.
6. Ask the whole frontier in one round, numbered, each carrying a recommended answer:

   ```
   ❓ **Q1** - **<question title>**: <question body — cite the exact spec/section/file>

   ➡️ <your recommended answer>
   ```
7. Wait for the operator's answers before the next round.
8. Recompute the frontier from the answers; settled nodes unblock their children.
9. Skip aesthetic preference, an already-working implementation choice, and anything answerable "whatever is reasonable."
10. Repeat rounds until the frontier is empty — every branch visited, nothing silently assumed.
11. Sharpen terminology as decisions land (`dd-domain-modeling`): resolve a fuzzy or colliding term into its canonical `CONTEXT.md` sense before it enters the record.
12. State the resulting shared understanding back to the operator in one summary.
13. Record every inspection-resolved item as "answered via inspection: <value>".
14. Record every operator decision as an ADR line (`<decision> — reason: <justification>`).
15. Emit the session as a handoff via `dd-handoff-emitter` — handoff-only by default.
16. Write the HTML report (`EMISSION-FORMAT.md`) only when the operator asked for one or the next hop is human.

## 3. Done when

- Every gap findable by inspection is resolved or promoted, not asked of the operator.
- The frontier is empty and the operator has confirmed the shared understanding.
- The handoff is emitted and passes `dadaia reports validate`.

## 4. References

- `PROBLEM-TAXONOMY.md` — the problem-shape reference used at step 3.
- `EMISSION-FORMAT.md` — the optional report's shape, report mode only.
- `dd-release-definition` §3 — the mandatory pre-SPEC session rule.
- `DADAIA.md` §5 — handoff-first emission law.
