---
name: dd-grill-me
description: >
  Interview the operator to shared understanding on a demand, spec, ADR or plan,
  resolving by inspection everything the repo/CLI/a subagent can answer first. Use
  for ambiguous intake, the mandatory pre-SPEC session of a release candidate, an
  ADR decision, a focused spec question, or when the operator says "grill". It asks and records; the backlog document is dd-backlog-definition's and the SPEC dd-release-definition's.
compatibility: Standalone Agent Skill. Inside a dadaia-workspace (pip install dadaia-workspace) it also drives the SDD lifecycle — specs, backlog, bugs, releases.
---

# dd-grill-me — SDD Spec Refinement

Reach shared understanding by mapping every open branch of the demand as a design tree, then asking one question at a time until the tree is fully visited.

## 1. When

Each stage reads its reference before the first question:

- Before a backlog entry is created: [`references/backlog.md`](references/backlog.md).
- Before a release candidate's SPEC: [`references/release.md`](references/release.md).
- When a decision may be an ADR: [`references/adr.md`](references/adr.md).
- After the PLAN: [`references/plan.md`](references/plan.md).

## 2. Steps

1. Search the repo (`Read`/`Glob`/`Grep`) and run the read verbs (`.dadaia/.venv/bin/dadaia context show --json`, `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --specs <specs-dir>`) before framing a question — finding facts is your job; dispatch a subagent for deeper exploration.
2. Read `PROBLEM-TAXONOMY.md` and classify each gap against it: inspect, or promote to the tree.
3. Map every remaining open question as a node; a dependent question hangs beneath its prerequisite. Ask next a question whose prerequisites are settled.
4. Ask one question per `AskUserQuestion` call: 3 closed options, each with its trade-off, one marked recommended; free text is the tool's open answer. Without that tool, ask in numbered text, still one at a time.
5. Skip aesthetic preference, an already-working implementation choice, and anything answerable "whatever is reasonable." A contract break, a de-dup, dead code or lying text is decided in scope and stated in one line, never asked.
6. Sharpen terminology as decisions land: resolve a fuzzy or colliding term to the one name the repo's specs already use.
7. Land every answer in its durable record in the same turn: the backlog entry description, the ADR `options` and `ruling.words`, or the SPEC. The handoff is ephemeral, never the record. A default you choose is labelled "agent default, unruled"; Recommended never marks an option that reverses a ruling, and a permission denial is not a ruling.
8. Stop when nothing is left to ask — every branch visited, nothing silently assumed — and state the shared understanding back in one summary.
9. Present the result as the harness artifact when it has one; otherwise as an HTML report styled by `scripts/report.css`.
10. Emit the session through `dd-handoff-emitter`, with `answered via inspection: <value>` and `<decision> — reason: <justification>` findings.

## 3. Done when

- Every gap findable by inspection is resolved or promoted, not asked of the operator.
- Every operator answer sits in its durable record and the operator confirmed the summary.
- The handoff is emitted; inside a dadaia workspace it passes `.dadaia/.venv/bin/dadaia reports validate`.

## 4. References

- [`PROBLEM-TAXONOMY.md`](PROBLEM-TAXONOMY.md) — the problem shapes, step 2.
- `references/` — one file per stage, §1.
- `scripts/report.css` — the HTML report style, step 9.
