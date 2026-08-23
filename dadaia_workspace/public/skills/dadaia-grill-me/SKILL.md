---
name: dadaia-grill-me
description: >
  Interview the operator to reach shared understanding on a demand, spec, or backlog
  item, resolving every question the repo/CLI/a subagent can already answer before it
  reaches the operator. Use when: the operator's demand is ambiguous and needs intake
  refinement (project-manager); a release is being defined and needs its mandatory
  pre-SPEC session (product-engineer, `dd-release-definition` §3); a single spec or
  feature question needs a focused leaf answer; or the operator says "grill", "refine
  specs", or "review backlog".
applyTo: "specs/**"
---

# dadaia-grill-me — SDD Spec Refinement

Reach shared understanding with the operator by mapping every open branch of the
demand as a **design tree**, then working it in **rounds** until the tree is fully
visited.

## 1. Inspect before asking

Finding facts is your job, never the operator's. Search the repo (`Read`/`Glob`/
`Grep`), run the CLI (e.g. `dadaia specs doctor`, `dadaia context show --json`), and
dispatch a subagent for deeper exploration — before framing a single question.
Classify each gap against `PROBLEM-TAXONOMY.md` (disclosed — read it here to name the
shape before deciding whether it resolves by inspection or promotes to the tree).
**Done when:** every gap findable by inspection is resolved ("answered via
inspection") or promoted to a design-tree question inspection genuinely cannot settle.

## 2. Build the design tree

Map every remaining open question as a node; a question that depends on another
question's answer hangs beneath it as its child. **Done when:** every gap that
survived step 1 has a place in the tree, including branches whose parent question is
still unanswered.

## 3. Work the frontier, one round at a time

The **frontier** is every question whose prerequisites are already settled — the ones
askable right now without guessing at an answer not yet heard. Ask the whole frontier
in one round, numbered, each carrying a recommended answer:

```
❓ **Q1** - **<question title>**: <question body — cite the exact spec, section, or
file that raised it>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body>

➡️ <your recommended answer>
```

Wait for the operator's answers before the next round. Each answer reshapes the tree:
settled nodes push the frontier outward and unblock their children. Recompute the
frontier and ask the next round — a question whose prerequisite is still open in the
same round belongs to a later round. Skip aesthetic preference, an implementation
choice already made and working, and anything the operator would answer "whatever is
reasonable" to. **Done when:** a round's answers are in hand and the frontier has been
recomputed from them.

## 4. Confirm shared understanding

The design tree is done when the frontier is empty — every branch visited, nothing
silently assumed. State the resulting shared understanding back to the operator in one
summary. **Done when:** the frontier is empty AND the operator has confirmed it.

## 5. Emit

Record every inspection-resolved item as "answered via inspection: <value>" and every
operator decision as an ADR line (`<decision> — reason: <justification>`). Emit the
session as a handoff via `dadaia-handoff-emitter` — handoff-only by default. Write the
HTML report (shape: `EMISSION-FORMAT.md`, disclosed — read it only in report mode)
when the operator asked for one or the next handoff target is human (`DADAIA.md` §4).
**Done when:** the handoff is emitted and passes `dadaia reports validate`.

---

Disclosed, not restated here: the mandatory pre-SPEC session rule
(`dd-release-definition` §3), the problem-shape reference (`PROBLEM-TAXONOMY.md`), the
optional report's shape (`EMISSION-FORMAT.md`).
