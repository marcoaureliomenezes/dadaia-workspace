# T-045-27 — FR11 always-on diet pass: coverage table

Release v0.4.5, `S4`. A11.2: every removed/compressed block names the surviving home. No
law is dropped — every edit below is either (a) wording compressed in place (fact still
stated in the same section, same file), or (b) a cross-persona restatement of DADAIA.md
§3's NO-LOCKS doctrine collapsed to a pointer at that section.

## Scope actually cut (A11.3 discipline)

Per dispatch: DADAIA.md source is fully in scope for wording compression and negation
rewrite (except the branch model §4, the gate-class table §3, and Credentials §9, left
byte-for-byte except where noted). Persona edits are restricted to (i) pure restatements
of DADAIA.md law, and (ii) negation-to-positive rewrites — never a T-045-28-scope line
reduction of persona-specific/justified content.

## DADAIA.md (source) — compressed in place, no relocation

| # | Section | Before (negation-bearing) | After | Surviving home |
|---|---|---|---|---|
| 1 | Header | "no second source" / "no fact is stated twice" | "one source" / "each fact is stated once" | Same paragraph, DADAIA.md header |
| 2 | §1 The flow | "Bugs are never release material and never wait for one. Features never skip the backlog." + a second, redundant "No workflow engine assembles prompts..." sentence restating "not engine-run" from the same paragraph | "A bug is fixed immediately, outside release material; a feature enters only through the backlog." The redundant engine-negation sentence is removed; the fact ("agent-dispatched") survives once, in the paragraph's own first sentence | DADAIA.md §1, same paragraph (fact retained, stated once instead of twice) |
| 3 | §3 gate doctrine (prose, NOT the path-class table) | "Races are surfaced, never prevented. There is no lock..." / "no other session is affected" / "there is no reason to defer" language patterns / "which the gate does not parse" / "do not depend on" / "reads no SDD artifacts...never how" | Positive-framed equivalents ("locks...are absent by design", "every other session is unaffected", "outside the gate's own parsing", "independent of any harness hook firing", "stays silent on **how**...reads zero SDD artifacts") | DADAIA.md §3, same location — path-class table (lines then 88-94) and the NO-LOCKS/mode/context/git-chokepoint doctrine untouched in substance |
| 4 | §5 Where things are written | "never auto-deleted" / "never `.dadaia/`, `.venv/`..." | "stays, permanently" / "excluding `.dadaia/`, `.venv/`..." | DADAIA.md §5, same location |
| 5 | §6 Backlog | "No agent materializes an entry" / "Nothing is deleted" / "never-delete law" | "An entry materializes only through the PM's...intake report" / "Every item is retained" / "retention law" | DADAIA.md §6, same location |
| 6 | §7 Quality | "are not acceptable outcomes" / "never an afterthought" / "The implementer never prunes..." / "are not product bugs" / "there is no reason to defer it" / "never enter an event field" / "never `-A`" / "Commits are never review-blocked" | Positive equivalents throughout (see diff) — meaning unchanged | DADAIA.md §7, same location |
| 7 | §8 Library surface | "No private repo names...ever enter" | "are excluded from `dadaia_workspace/public/` entirely" | DADAIA.md §8, same location |
| 8 | §10 Where to look next | "never listed ad hoc here" | "alone" | DADAIA.md §10, same location |

**Untouched by rule (task-mandated protection).** §4 Gitflow (the branch-contract table
and its surrounding rows), §3's ADDITIVE/MEMORY/MUTATING/FROZEN/PROTECTED path-class
table, and §9 Credentials are byte-identical to the pre-pass source except where a
negation appears in `## 3`'s *prose* outside the table itself (row 3 above) — the table
cells are untouched. The pending 0.5.0 enforcement-posture sentence has **no** home it
would need in this pass: §3 (deterministic enforcement) and §7 (quality) both remain
intact, stable anchors for it.

## Personas — restatement collapsed to a pointer

| # | Persona(s) | Removed restatement | Surviving home |
|---|---|---|---|
| 9 | `qa-engineer`, `security-reviewer`, `code-reviewer`, `software-architect`, `project-auditor` (5 files) | "No lock to hold: you run concurrently with everything else; your writes (X) are ADDITIVE." (near-verbatim restatement of DADAIA.md §3's NO-LOCKS doctrine + ADDITIVE-writability rule, repeated 5×) | Compressed to "No lock (`DADAIA.md` §3): concurrent by default; writes (X) are ADDITIVE." — the doctrine's full statement lives once, at `DADAIA.md` §3; each persona keeps only its own writes-are-ADDITIVE fact and a pointer |

## Personas — negation-to-positive rewrites (identical meaning, not a restatement cut)

| # | Persona | Before | After |
|---|---|---|---|
| 10 | `ai-engineer` (description) | "No code, specs, tests, frontend, CI." | "Scope: the AI-entity surface only — code, specs, tests, frontend and CI stay with other roles." |
| 11 | `project-auditor` (description) | "NEVER fixes drift." | "measure-and-report only; drift fixes route to the owning specialist." |
| 12 | `code-reviewer` (description) | "NEVER edits code or approves PRs." | "verdict-only — code edits and PR approval stay with the implementer/operator." |
| 13 | `project-manager` (description) | "NEVER writes code/specs/memory/tests/CI." | "dispatches all code/specs/memory/tests/CI work to its owning specialist rather than writing it." |
| 14 | `software-architect` (description) | "NEVER writes production code." | "reports-only — production code stays with software-engineer." |
| 15 | `security-reviewer` (description) | "NEVER writes fixes." | "findings-only — fixes stay with the implementing agent." |
| 16 | `software-engineer` (description) | "no architecture drift, no slop tests...No AI-entity/specs surfaces." | "architecture-conformant, tests assert real behavior...AI-entity/specs surfaces stay with ai-engineer/product-engineer." |
| 17 | `product-engineer` (description) | "NEVER dispatches or implements code." | "spec-authoring only — dispatch and implementation stay with PM/software-engineer." |

**Not touched (task-mandated protection — hard-stop/scope-boundary blocks).** Every
`[SCOPE ERROR]` block, every "Scope"/"You do NOT write" table, every write-allowlist
table, and the body-level identity sentences that assert a persona's hard boundary (e.g.
qa-engineer's "You never write application code, unit tests, or integration tests.",
security-reviewer's "You never write fixes and never run exploit code.") are unchanged —
these are the load-bearing scope statements T-045-28 (not this task) may relocate, and
this task never weakens their force by rewording.

## Skills — negation-to-positive rewrites (5 of 5 always-on skill-description negations)

| # | Skill | Before | After |
|---|---|---|---|
| 18 | `architect-core-workflow` | "Keeps recommendations evidence-based, not invented." | "Keeps recommendations strictly evidence-based." |
| 19 | `dadaia-handoff-emitter` | "the default emission carries no HTML report" | "the default emission is handoff-only" |
| 20 | `dd-cli-library` | "carry no grant" | "are ungranted" |
| 21 | `dadaia-step0-memory-bootstrap` | "(no strip pass needed)" | "read as plain text" |
| 22 | `dd-bug-registration` | "never the fix (that's `dd-bug-fix`)" | "the fix itself belongs to `dd-bug-fix`" |

## Net measured effect

See `.dadaia/tmp/ai-engineer/20260826/T-045-27-after.md` for the full V6/V7 before/after
table and the A11.4 miss statement.
