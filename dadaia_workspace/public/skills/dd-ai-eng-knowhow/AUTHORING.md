# AUTHORING.md — The Writing-for-Agents Contract

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth).
House authoring contract for every AI-entity file `ai-engineer` writes: personas, skills, rules, hooks-facing instructions.

- Derived from, and provenance-anchored to, the read-only clone at
  `.dadaia/references/skills-examples/skills/productivity/writing-for-agents/` (`mattpocock/skills`).
- Consult that clone for the full worked prose; this file states house rules in our own vocabulary, never a copy (A11.5).

---

## 1. Context pointers

- Every skill description, every `AGENTS.md` doc reference, every "see X" in a persona is a context pointer.
- The pointer's wording, not its target, decides whether an agent reaches the material.
- A must-have target behind a weak pointer is a variance bug, not a content bug.
- Fix rule: sharpen the wording first; inline only if sharpening fails.
- House rule: front-load the trigger word — the description's first clause is where matching happens.
- House rule: one trigger per branch — never two names for the same situation.
- House rule: never restate identity the body already carries — a pointer names the condition, not a summary.

---

## 2. The two loads

- Every document/pointer spends one of two budgets; authoring routes correctly between them.

| Load | Who pays | What it buys |
|---|---|---|
| Context load | The agent, every turn | Speed/reliability of reaching material without a human in the loop |
| Cognitive load | The operator/reviewer | Zero context tax, but the human must remember the document exists |

- This is `dd-ai-eng-knowhow`'s own shape in miniature: Part 1 is context-loaded for every agent, every session.
- Siblings are reached only by pointer — free until `ai-engineer` needs them (the FR11 fleet-scale trade).

---

## 3. Information hierarchy and disclosure

- Every AI-entity document is built from steps (ordered actions) and reference (facts consulted on demand).
- Ranked on a ladder: in-file step, in-file reference, disclosed reference.
- In-file step: what the agent does, in order — the primary tier of a workflow skill.
- In-file reference: consulted on demand, often a legitimate flat peer-set (OWASP table, decision table).
- Disclosed reference: pushed to a sibling file or a fully external doc, reached only by its pointer.
- Progressive disclosure: inline what every branch needs, disclose what only some branches reach.
- `dd-ai-eng-knowhow` applies this at the top level — every agent needs Part 1, only `ai-engineer` reaches Part 2.
- Co-location: keep a concept's definition, rule, and caveat under one heading, not scattered.
- Sprawl is the failure this consolidation cures: four skills, 1,372 lines, real duplication across them.
- The cure was disclosure — one context-loaded top layer, four disclosed-reference siblings.

---

## 4. Completion criteria

- Every step in a skill's ordered arc ends on a completion criterion — the condition telling the agent it is done.
- A criterion is a lever only when clear: the agent can tell done from not-done without judgment calls.
- A vague bound invites premature completion — attention slipping to "being done" before the work actually is.
- Sharpen the bound first (cheap, local); split across a real context boundary only if irreducibly fuzzy.
- A criterion is a lever only when exhaustive: "every finding disposed", not "produce a summary."
- Demand drives legwork; a flat reference document carries the same exhaustiveness bar as a sequence.
- Every "Done when:" line in `dd-release-implement`'s arc is this house rule applied.

---

## 5. Positive leading words, not negation

- A leading word is a compact, already-pretrained concept the agent thinks with (this workspace's own: tight, root cause, green).
- Reach for an existing word before coining one — a made-up term recruits no priors and costs definition tokens.
- Negation is the failure mode beside this lever: prohibition drags the forbidden behavior into context.
- "Don't restate the constitution" half-reads as an instruction about restating the constitution.
- Prompt the positive: state the target ("link to the canonical source") so the banned behavior is never spoken.
- A prohibition earns its place only as a hard guardrail that cannot be phrased positively.
- Even a hard guardrail (a `[SCOPE ERROR]` refusal, a security "never" rule) should pair with the positive target.
- Audit test: count "never"/"don't"/"do not" instructions that could be rephrased positively — each is a rewrite.

---

## 6. Pruning

Four checks, applied at authoring time and at review time:

1. Single source of truth — one meaning, one authoritative place; a duplicated paragraph across personas violates this.
2. Cache discipline — the environment is a source of truth too (`--help`, a schema, the directory layout).
3. Cache only what the agent cannot find by looking: the unwritten convention, the reason behind a choice, the gotcha.
4. Relevance sweep — does each line still bear on what the document does?
5. A line that never bears on the task, or went stale, is sediment — the default fate of an unpruned document.
6. No-op hunt — does removing the sentence change what the model does? If not, delete the whole sentence.

---

## 7. Applying this contract

When authoring or reviewing any persona, skill, rule, or hook-facing instruction:

1. Walk §1-§3 while drafting: is every pointer sharp, is the load routed right, is the ladder respected?
2. Walk §4-§5 on every step/rule you write: checkable and exhaustive criterion, phrased positively?
3. Walk §6 before calling the draft done, and again on every later review pass — pruning is a standing discipline.
