# AUTHORING.md — The Writing-for-Agents Contract

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth).
House authoring contract for every AI-entity file `ai-engineer` writes: personas, skills, rules, hooks-facing instructions.

- Derived from the public reference corpus `mattpocock/skills` (`writing-for-agents`,
  `SKILL-MECHANICS.md`, and its promoted skills as worked examples); this file states
  house rules in our own vocabulary, never a copy.

## The 15-rule checklist (audit 2026-08-31, operator-ratified)

Every library skill must satisfy all fifteen; each rule's detail lives in the section named.

| # | Rule | Detail |
|---|---|---|
| 1 | One skill, one job — and it knows whether it is steps, reference, or a conscious mix | §3, §7 |
| 2 | The description is a context pointer carrying trigger branches, nothing else | §1 |
| 3 | Invocation is a deliberate choice: model-invoked only when the agent or another skill must reach it | §7 |
| 4 | Progressive disclosure: short SKILL.md, disclosed siblings behind condition-naming pointers | §3 |
| 5 | Single source of truth; the environment is a source; cache only expensive lookups | §6 |
| 6 | Every step ends on a checkable, demanding completion criterion | §4 |
| 7 | Leading words over prose; a vocabulary skill says "use these terms exactly" with an Avoid list | §5 |
| 8 | Positive instruction; prohibition only as a hard guardrail paired with the positive | §5 |
| 9 | Prune no-ops, sediment, duplication — provenance and history live in git, never in the skill | §6 |
| 10 | Right altitude: intent over mechanics that go stale (paths, snippets), with the prototype exception | §6 |
| 11 | Steps are actions in execution order, one idea each; the branch decision comes first; templates are fenced blocks | §8 |
| 12 | The set is curated and composed: overlap resolves by merge or by one skill calling the other | §7 |
| 13 | Determinism goes to a script/template sibling; the skill authors stages, never re-derives the library | §3 |
| 14 | Human gates are explicit: facts are the agent's job, decisions are the operator's | §8 |
| 15 | The ecosystem stays equalized: behavior-map, grants, law citations and projections move with the skill | §9 |

---

## 1. Context pointers

- Every skill description, every `AGENTS.md` doc reference, every "see X" in a persona is a context pointer.
- The pointer's wording, not its target, decides whether an agent reaches the material.
- A must-have target behind a weak pointer is a variance bug, not a content bug.
- Fix rule: sharpen the wording first; inline only if sharpening fails.
- House rule: front-load the trigger word — the description's first clause is where matching happens.
- House rule: one trigger per branch — never two names for the same situation.
- House rule: never restate identity the body already carries — a pointer names the condition, not a summary.
- House rule: a description carries no grant lists, no rename/absorb history, no governance ids — triggers only.

---

## 2. The two loads

- Every document/pointer spends one of two budgets; authoring routes correctly between them.

| Load | Who pays | What it buys |
|---|---|---|
| Context load | The agent, every turn | Speed/reliability of reaching material without a human in the loop |
| Cognitive load | The operator/reviewer | Zero context tax, but the human must remember the document exists |

- This is `dd-ai-eng-knowhow`'s own shape in miniature: Part 1 is context-loaded for every agent, every session.
- Siblings are reached only by pointer — free until `ai-engineer` needs them.

---

## 3. Information hierarchy and disclosure

- Every AI-entity document is built from steps (ordered actions) and reference (facts consulted on demand).
- Ranked on a ladder: in-file step, in-file reference, disclosed reference.
- In-file step: what the agent does, in order — the primary tier of a workflow skill.
- In-file reference: consulted on demand, often a legitimate flat peer-set (OWASP table, decision table).
- Disclosed reference: pushed to a sibling file or a fully external doc, reached only by its pointer.
- Progressive disclosure: inline what every branch needs, disclose what only some branches reach.
- A sibling is one ALL-CAPS.md per topic, pointed at with its reaching condition ("deepening a cluster → `DEEPENING.md`").
- A deterministic procedure ships as a script/template sibling; the skill's job reduces to authoring its variable parts.
- Co-location: keep a concept's definition, rule, and caveat under one heading, not scattered.
- Sprawl is the failure disclosure cures; the reference corpus keeps every SKILL.md between 7 and ~140 lines.

---

## 4. Completion criteria

- Every step in a skill's ordered arc ends on a completion criterion — the condition telling the agent it is done.
- A criterion is a lever only when clear: the agent can tell done from not-done without judgment calls.
- A vague bound invites premature completion — attention slipping to "being done" before the work actually is.
- Sharpen the bound first (cheap, local); split across a real context boundary only if irreducibly fuzzy.
- A criterion is a lever only when exhaustive: "every finding disposed", not "produce a summary."
- Demand drives legwork; a flat reference document carries the same exhaustiveness bar as a sequence.
- A phase may gate the next explicitly ("no red-capable command, no phase 2") — the strongest completion shape.

---

## 5. Positive leading words, not negation

- A leading word is a compact, already-pretrained concept the agent thinks with (this workspace's own: tight, root cause, green, seam, frontier).
- Reach for an existing word before coining one — a made-up term recruits no priors and costs definition tokens.
- A vocabulary skill states "use these terms exactly", pairs each term with its _Avoid_ list, and every sibling skill speaks it.
- Negation is the failure mode beside this lever: prohibition drags the forbidden behavior into context.
- Prompt the positive: state the target ("link to the canonical source") so the banned behavior is never spoken.
- A prohibition earns its place only as a hard guardrail that cannot be phrased positively.
- Even a hard guardrail (a `[SCOPE ERROR]` refusal, a security "never" rule) should pair with the positive target.
- A negation of something retired ("no such flag exists") is sediment — delete it with the shape it mourns.
- Audit test: count "never"/"don't"/"do not" instructions that could be rephrased positively — each is a rewrite.

---

## 6. Pruning

Six checks, applied at authoring time and at review time:

1. Single source of truth — one meaning, one authoritative place; a duplicated paragraph across personas violates this.
2. Cache discipline — the environment is a source of truth too (`--help`, a schema, the directory layout).
3. Cache only what the agent cannot find by looking: the unwritten convention, the reason behind a choice, the gotcha.
4. Relevance sweep — does each line still bear on what the document does?
5. A line that never bears on the task, or went stale, is sediment — the default fate of an unpruned document.
   Governance provenance (FR ids, task ids, "renamed/absorbed from") is sediment by definition: git owns history.
6. No-op hunt — does removing the sentence change what the model does? If not, delete the whole sentence.

Altitude belongs here too: state intent, not mechanics that go stale (file paths, code snippets). The one exception:
a snippet that encodes a decision more precisely than prose (a schema, a state shape) may be inlined, trimmed to the
decision-rich part.

---

## 7. Skill mechanics: invocation, composition, the curated set

- Model-invoked: the description stays loaded every turn — pay that only when the agent, or another skill, must reach it autonomously.
- User/dispatch-invoked (`disable-model-invocation: true`): zero context load; the human or the calling skill is the index.
- In this workspace persona `skills:` allowlists already scope reach — but every granted description still costs its personas every turn, so the pointer-pruning bar (§1) stays maximal.
- Shared reference lives in exactly ONE skill; consumers call it ("call the Skill tool with X") — a two-line composing skill is a success, not a stub.
- Overlap between two skills resolves by merge or by one calling the other, never by both restating the material.
- A skill is one job: all steps, all reference, or a conscious mix — the form follows the content, never a fixed section template.
- When invocable skills multiply past what the index (human or dispatcher) holds, the cure is a router map — one place naming every skill and when to reach it — not more descriptions.

---

## 8. Steps, branches, human gates

- Steps are actions in execution order, one idea per step, each ending on its criterion (§4).
- When a skill branches, the branch decision is the FIRST step — picking the wrong branch wastes the whole run.
- Templates and formats are given as fenced blocks where they are used, never described in prose.
- Human gates are explicit: finding facts is the agent's job (inspect before asking); decisions are the operator's — put each one to them and wait.
- A round-based interview asks the whole frontier at once, numbered, each question carrying a recommended answer.

---

## 9. The ecosystem contract

A skill never moves alone. Any authoring act (create, merge, rename, delete, restructure) carries in the same change:

1. `entities/behavior-map.json` — the row (exactly one per skill), `declared_overlaps`, and the re-recorded hash tuple (a deliberate, reviewed act).
2. Persona `skills:` grants — the orphan checker requires every model-invoked skill granted somewhere; a `disable-model-invocation` skill is exempt.
3. Law citations — `DADAIA.md` and every scoped `AGENTS.md` SOURCE under `public/` that names the skill.
4. Cross-citations in sibling skills (the citation contract test checks every path-shaped token in `public/**`).
5. Reprojection — `dadaia public stage` → `install --target all` → `public doctor` `[ok]`; stale projected directories removed from every harness target.

---

## 10. Applying this contract

When authoring or reviewing any persona, skill, rule, or hook-facing instruction:

1. Walk the 15-rule checklist first — it is the review's finding taxonomy.
2. Walk §1-§3 while drafting: is every pointer sharp, is the load routed right, is the ladder respected?
3. Walk §4-§5 and §8 on every step/rule you write: checkable and exhaustive criterion, phrased positively, branch first?
4. Walk §6 before calling the draft done, and again on every later review pass — pruning is a standing discipline.
5. Walk §9 before committing — the skill and its ecosystem move in one change.
