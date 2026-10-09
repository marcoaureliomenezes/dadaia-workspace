---
name: dd-grill-me
description: >
  Interview the operator to shared understanding on a demand, spec, or backlog item,
  resolving by inspection everything the repo/CLI/a subagent can answer first. Use
  for ambiguous intake, the mandatory pre-SPEC session of a release candidate, a
  focused spec question, or when the operator says "grill". It asks and records; the backlog document is dd-backlog-definition's and the SPEC dd-release-definition's.
compatibility: Standalone Agent Skill. Inside a dadaia-workspace (pip install dadaia-workspace) it also drives the SDD lifecycle — specs, backlog, bugs, releases.
---

# dd-grill-me — SDD Spec Refinement

Reach shared understanding by mapping every open branch of the demand as a design tree, then asking one frontier question at a time until the tree is fully visited.

## 1. When

- The operator's demand is ambiguous and needs intake refinement (the main thread).
- A release is being defined and needs its mandatory pre-SPEC session (the main thread, `dd-release-definition` §3).
- A single spec or feature question needs a focused leaf answer.

## 2. Steps

1. Search the repo (`Read`/`Glob`/`Grep`) and run the read verbs (`.dadaia/.venv/bin/dadaia context show --json`, `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --specs <specs-dir>`) before framing a single question — finding facts is your job.
2. Dispatch a subagent for deeper exploration when needed.
3. Read `PROBLEM-TAXONOMY.md` and classify each gap against it before deciding inspection vs promotion to the tree.
4. Map every remaining open question as a node; a dependent question hangs beneath its prerequisite as a child.
5. Identify the frontier: every question whose prerequisites are already settled.
6. Ask one question per `AskUserQuestion` call: 3 closed options, each with its trade-off, one marked recommended, plain-text options; the open answer is the tool's own. Without that tool, ask in numbered text, still one at a time. The handoff (step 15) is the session's one record.
7. Wait for the operator's answer, recompute the frontier from it (settled nodes unblock their children), and ask the next question.
8. Skip aesthetic preference, an already-working implementation choice, and anything answerable "whatever is reasonable."
9. Stop when the frontier is empty — every branch visited, nothing silently assumed.
10. The grill settles new-scope and design questions before launch; a launched candidate carries
    those decisions to closure. Workflow-required operator confirmations and escalations follow
    `specs/bugs/AGENTS.md` §1 and `dd-manager-orchestration` §3.
11. Sharpen terminology as decisions land: resolve a fuzzy or colliding term to the one name the repo's specs already use before it enters the record.
12. State the resulting shared understanding back to the operator in one summary.
13. In the handoff's `findings`, record each inspection-resolved item as `answered via inspection: <value>`.
14. In the same `findings`, record each operator decision as `<decision> — reason: <justification>`.
15. Emit the session through `dd-handoff-emitter`.
16. A report, when that skill's report mode applies, takes `EMISSION-FORMAT.md`'s sections.

## 3. Done when

- Every gap findable by inspection is resolved or promoted, not asked of the operator.
- The frontier is empty and the operator has confirmed the shared understanding.
- The handoff's `findings` hold one `answered via inspection:` line per inspected gap and one decision line per operator answer, and its `decisions_required` is empty.
- The handoff is emitted; inside a dadaia workspace it passes `.dadaia/.venv/bin/dadaia reports validate`.

## 4. References

- [`PROBLEM-TAXONOMY.md`](PROBLEM-TAXONOMY.md) — the problem shapes, step 3.
- [`EMISSION-FORMAT.md`](EMISSION-FORMAT.md) — the report sections, report mode only.
