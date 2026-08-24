# AUTHORING.md — The Writing-for-Agents Contract

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth). This
is the house authoring contract for every AI-entity file `ai-engineer` writes: personas,
skills, rules, hooks-facing instructions. It is derived from, and provenance-anchored
to, the pattern cloned read-only at
`.dadaia/references/skills-examples/skills/productivity/writing-for-agents/` (`SKILL.md`
+ `SKILL-MECHANICS.md`, `mattpocock/skills`) — consult that clone for the full worked
prose; this file states the house rules in our own vocabulary, never a copy of the
source text (A11.5).

---

## 1. Context pointers

Every skill description, every `AGENTS.md` line naming a doc, every "see X" reference in
a persona is a **context pointer**: material named in-context with the condition for
reaching it. The pointer's wording, not its target, decides whether an agent reaches the
material — a must-have target behind a weak pointer is a variance bug, not a content
bug. Fix rule: sharpen the wording first; inline only if sharpening fails.

House rules for every pointer we write:
- **Front-load the trigger word.** The description's first clause is where the matching
  actually happens.
- **One trigger per branch.** A skill/rule description lists genuinely distinct
  situations, never two names for the same one.
- **Never restate identity the body already carries.** A pointer names the *condition*
  for reaching the material, not a summary of it.

---

## 2. The two loads

Every document and pointer we add spends one of two budgets, and authoring is the
discipline of routing correctly between them:

| Load | Who pays | What it buys |
|---|---|---|
| **Context load** | The agent, every turn | Speed and reliability of reaching the material without a human in the loop |
| **Cognitive load** | The operator/reviewer | Zero context tax, but the human must remember the document exists and when to reach for it |

This is `dd-ai-eng-knowhow`'s own two-part shape in miniature: [`SKILL.md`](SKILL.md)'s
Part 1 is universally context-loaded (every agent, every session); this sibling and its
neighbors are reached only by a pointer, so they cost nothing until `ai-engineer` needs
them — the deliberate trade this consolidation (FR11) exists to make, at fleet scale.

---

## 3. Information hierarchy and disclosure

Every AI-entity document is built from **steps** (ordered actions) and **reference**
(facts consulted on demand), ranked on a ladder:

1. **In-file step** — what the agent does, in order. The primary tier of a workflow
   skill (`dd-release-implement`'s numbered arc).
2. **In-file reference** — consulted on demand, often a legitimate flat peer-set (an
   OWASP-style table, a decision table). Not a smell by itself.
3. **Disclosed reference** — pushed to a sibling file (this folder's pattern) or a fully
   external doc, reached only by its pointer.

**Progressive disclosure** is the move down this ladder to keep the top legible; the
branching test decides it — inline what every branch needs, disclose what only some
branches reach. `dd-ai-eng-knowhow` applies this at the top level: every agent needs Part
1 (inline in `SKILL.md`); only `ai-engineer` reaches Part 2's siblings (disclosed).

**Co-location**, the within-file companion: keep a concept's definition, rule, and
caveat under one heading (this is why each `[SCOPE ERROR]` block, each write-permissions
table, stays a single contiguous section rather than scattered across a persona).

**Sprawl** is the failure mode this consolidation exists to cure: four skills, each
individually reasonable, summed to 1,372 lines of standing context tax with real
duplication across them (harness deltas restated three ways, the same "model decides,
harness enforces" framing repeated). The cure was never "trim each file" — it was
disclosure: one context-loaded top layer, four disclosed-reference siblings.

---

## 4. Completion criteria

Every step in a skill's ordered arc (`dd-release-implement`, `dd-gitflow-default`, `dd-
bug-fix`) ends on a **completion criterion** — the condition that tells the agent the
step is done. A criterion is a lever only when it is:

- **Clear** — the agent can tell done from not-done without judgment calls. A vague
  bound invites **premature completion**: attention slipping to "being done" before the
  work actually is. Sharpen the bound first (cheap, local); only split the sequence
  across a real context boundary (a hand-off, a subagent dispatch) if the bound is
  irreducibly fuzzy and premature completion is actually observed.
- **Exhaustive** — "every finding disposed", "every mapped skill exists on disk", not
  "produce a summary". Demand drives legwork; it is not step-bound — a flat reference
  document (an audit protocol) carries an exhaustiveness bar exactly the way a sequence
  does ("every persona checked" binds a review the same way "every step done" binds a
  workflow).

Every "Done when:" line in `dd-release-implement`'s arc is this house rule applied.

---

## 5. Positive leading words, not negation

A **leading word** is a compact, already-pretrained concept the agent thinks with while
running the document (this workspace's own: *tight*, *root cause*, *green*). Reach for
an existing word before coining one — a made-up term recruits no priors and costs
definition tokens a pretrained word gets for free.

**Negation is the failure mode beside this lever.** Steering by prohibition drags the
forbidden behavior into context and makes it *more* available, not less — "don't restate
the constitution" half-reads as an instruction about restating the constitution. Prompt
the **positive**: state the target ("link to the canonical source") so the banned
behavior is never spoken. A prohibition earns its place only as a hard guardrail that
cannot be phrased positively (a `[SCOPE ERROR]` refusal, a security "never" rule) — and
even then, pair it with the positive target.

Audit test for any AI-entity file under review: count "never"/"don't"/"do not"
instructions that could be rephrased as a positive instruction instead. Each one found is
a rewrite, not a keep.

---

## 6. Pruning

Four checks, applied to every AI-entity file at authoring time and at review time:

- **Single source of truth.** One meaning, one authoritative place. The workspace-
  constitution link pattern (`CONTEXT-ENGINEERING.md` §1) is this rule applied to shared
  protocol; a duplicated paragraph across two personas is this rule violated.
- **Cache discipline.** The environment is a source of truth too (`--help` output, a
  schema file, the directory layout). A document that restates a one-command lookup is a
  cache earning no load — cache only what the agent cannot find by looking: the
  unwritten convention, the reason behind a choice, the gotcha no config confesses.
- **Relevance sweep.** Does each line still bear on what the document does? A line that
  never bears on the task, or has gone stale as the described behavior changed, is
  **sediment** — the default fate of any document without an active pruning discipline.
  This consolidation (FR11) is a sediment-clearing event by design: the F1-F8-style
  private audit-history labels in the retired `ai-harness-claude-code` did not survive
  (A11.7) precisely because they were sediment — true once, illegible now, and
  reachable-but-dead weight on every future read.
- **No-op hunt.** An instruction the model already obeys by default pays load to say
  nothing. The test is behavioral, not stylistic: does removing the sentence change what
  the model does? If not, delete the whole sentence — trimming words from a no-op still
  leaves a no-op.

---

## 7. Applying this contract

When authoring or reviewing any persona, skill, rule, or hook-facing instruction:

1. Walk §1-§3 while drafting: is every pointer sharp, is the load routed to the right
   budget, is the ladder respected (inline what every reader needs, disclose the rest)?
2. Walk §4-§5 on every step/rule you write: does it end on a checkable, exhaustive
   criterion; is it phrased positively?
3. Walk §6 before calling the draft done, and again on every later review pass — pruning
   is never a one-time step, it is the standing discipline that keeps the fleet legible.
