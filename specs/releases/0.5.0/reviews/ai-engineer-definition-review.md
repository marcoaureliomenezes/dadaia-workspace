# ai-engineer definition review — release 0.5.0 (Draft)

**Reviewer:** ai-engineer · **Reviewed:** SPEC.md, PLAN.md, TASKS.md (`_ideas/0.5.0/`) ·
**Authority:** grill handoff `2026-08-26T120000Z-…-adr-grill.handoff.json` (D1–D15) ·
**Scope of this review:** FR7, FR8, FR9, FR10, FR11, FR12, FR14, FR17–FR21, and every
persona/skill/rule/hook edit named across S1–S4.

## Summary

The AI-surface design is sound in intent and unusually disciplined about D15 (no new
blocking CLI/hook — verified per-FR). Two findings are strong enough to block fold:
(1) FR10's "extend, don't replace" instruction never states that the **nine existing
`test_rules_skills_map.py` checks** (schema, 6 original modes, FR27 citation checks,
FR28 bidirectional model-invocation check) must survive the file's own retirement — as
written, `T-050-19`'s "which retires" line risks silently dropping hard-won regressions;
(2) four reviewer personas (`software-architect`, `qa-engineer`, `code-reviewer`,
`security-reviewer`) are given **write sets under `specs/releases/0.5.0/reviews/**`** by
TASKS.md, but only `project-auditor`'s allowlist widening is named anywhere in SPEC/PLAN
— the other four keep their current `.dadaia/reports/**`-only (or, for `qa-engineer`, a
single-filename) allowlist. No task in TASKS.md is `ai-engineer`-owned to fix this.

## 1. Map completeness (D14)

**GAP.** FR10's prose roster ("`specs/AGENTS.md`, `backlog/`, `bugs/`, `releases/`,
`memory/`, `audits/`, `ADRs/` … plus `.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`,
`tests/AGENTS.md`, the `repos/<slug>/AGENTS.md` template") **omits three existing
scoped-AGENTS.md sources already shipped in `dadaia_workspace/public/data/`**:
`dadaia-AGENTS.md` (`.dadaia/AGENTS.md`), `states-AGENTS.md` (`.dadaia/states/AGENTS.md`),
`tmp-AGENTS.md` (`.dadaia/tmp/AGENTS.md`). If A10.1's enforcer is implemented against the
SPEC's hand-listed roster rather than a glob over every `*-AGENTS.md`/`AGENTS.md`
generator under `public/data|scaffold|templates`, these three ship unmapped — the exact
defect D14 exists to catch. **Amendment:** state explicitly that the enforcer discovers
scoped-AGENTS.md *sources* structurally (glob the generators, not a hand list), the same
discipline A9.1/A9.2 already apply to skills.

**PASS (with a note) — the five RED directions.** They correctly extend rather than
duplicate `test_rules_skills_map.py`'s mechanism (T-050-19 explicitly names the file it
extends). But FR10/A10.2 describe only the five *new* completeness-check directions and
never say the **existing nine checks must be ported forward untouched** when the file
retires. Those nine checks carry two named regression histories
(`citation-enforcer-resolves-projected-instance-paths-against-the-checkout`,
`citation-mutation-fixtures-never-turn-red-on-windows`) plus the FR28 bidirectional
model-invocation grant check — losing any of them on a `git mv`-into-a-rewrite is exactly
the "law relocated into nothing" class PLAN §4/`S2` already names as R-4's risk.
**Amendment (blocking):** add an explicit acceptance id — "every test function present
in `test_rules_skills_map.py` at HEAD has a byte-for-byte-equivalent counterpart in
`test_behavior_map.py`, proven by a name-diff, zero-hit" — to FR10/A10, and require it
in T-050-19's Done criterion alongside V17.

**Hash-tuple re-recording — PASS.** D-A-style provenance discipline: `recorded_by` +
`recorded_at` on each row (§3/FR10 JSON example) makes re-recording an ai-engineer act
with a named actor, and A10.4 ties it to "a named reviewer," matching T-050-21's
re-recording step. "Semantic equalization — no restatement, no contradiction" is
checkable only insofar as A8.1's duplicate-statement scan (a zero-hit grep-class check)
is re-run over every map member pair — the SPEC states this for FR11↔skills (A11.2) but
never explicitly for scoped-AGENTS.md↔skill pairs added by FR10 itself. **Amendment:**
extend A8.1's duplicate scan's stated scope to cover scoped-AGENTS.md files, not only
`DADAIA.md`/skills, since FR12 authors seven new/renamed scoped `AGENTS.md` files in the
same segment.

**No orphan skill/section found** in the six-entry corpus as authored: every skill in the
current 21 (soon `dd-bug-fix`→`dd-bug-resolution`, plus new `dd-diagnose`) traces to a
row, and every DADAIA.md `##` section that will exist post-FR11 has at least one intended
owner per §2.1's D-ruling table (D2–D15 → FR mapping) and PLAN §2's layer table.

## 2. Token economy (FR11)

**Measured baseline (this session, not the release's own capture):** the current
`dadaia_workspace/public/data/DADAIA.md` source is **330 lines / 2,589 words / 17,526
bytes** — a chars/4 heuristic puts it at **~4.3–4.4k tokens**, i.e. already above the
v0.4.4-era `≤3.5k` target the PLAN cites as historically missed. FR11 adds: stable
per-behavior anchors, the D15 posture paragraph (quoted verbatim, ~50 words), a short
bug-lineage/commit-shape section, a short audits section, a short memory-Part-1/ADR
section, and the preflight rule. By the density of the existing comparable subsections
(e.g. the current "Audits" paragraph in §6 is ~75 words), five additions in that range
put the raw delta at roughly **350–550 words (~450–700 tokens)**, a **~10–16%** growth on
an already-over-target base — plausible, not alarming, but not free either.

**PASS on discipline, GAP on one mechanism.** A11.3 correctly makes the delta a measured,
per-section-attributed fact (V12), not an estimate — good. The one place the SPEC is
silent: whether the "stable per-behavior anchors" are **zero-cost markup** (e.g. an inline
`<!-- behavior: bugs -->` HTML comment, invisible to a reading agent and near-free in
tokens) or a **titled subsection** that itself reads as prose. Six to eight anchors
authored as titled subsections instead of comments would materially change the V12
delta. **Amendment:** state in FR11/A11.1 that anchors are comment-form markers, not
additional headings, and that V12's per-section attribution table separates anchor cost
from section-body cost.

**What belongs in a skill instead of the always-on file:** none of the five additions
look misplaced — each is a pointer per A11.2, and the corresponding procedure body lives
in `dd-diagnose`, `dd-gitflow-default`, `dd-audit-project`, and the memory/`ADRs`
`AGENTS.md` files respectively, matching D15's posture exactly.

## 3. Instruction hierarchy & duplication

For the six behaviors this release touches, exactly one owner is named per §2.1/§3:

| Behavior | Skill | Scoped AGENTS.md | DADAIA.md |
|---|---|---|---|
| Bugs (lifecycle) | `dd-bug-resolution` | `specs/bugs/AGENTS.md` (new) | §7 (unchanged home) |
| Bug lineage (D8) | `dd-diagnose` (phase 0) | `specs/bugs/AGENTS.md` (summary only) | new short §7 subsection |
| Releases | `dd-release-definition` / `dd-release-implement` | `specs/releases/AGENTS.md` (new) | §4/§6 (unchanged) |
| Audits | `dd-audit-project` | `specs/audits/AGENTS.md` (new) | §6 (unchanged) |
| Memory/ADRs | none (no core skill, by design — D12) | `specs/memory/AGENTS.md`, `specs/ADRs/AGENTS.md` (new) | new short §6-adjacent section |
| Hooks posture (D9/D15) | `dd-gitflow-default` + `DADAIA.md` §7 | n/a | preflight rule sentence |

No duplication found between `dd-bug-registration`'s existing "reported" event procedure
and the new bugs section text as described — FR11 states each new section is a pointer
and A8.1's scan is explicitly re-run (A11.2). One risk flagged in §1 above (the scan's
scope over scoped-AGENTS.md pairs) applies here too.

`dd-release-implement`'s split into `RC-FLOW.md`/`RELEASE-EVENTS.md`/`MEMORY-UPDATE.md`
is a genuine disclosure-sibling pattern (matches `AUTHORING.md`'s "the two loads"), not a
second statement of the same procedure — `CLOSURE-CHECKS.md`/`CLOSURE-TEMPLATE.md` (298
combined lines) retire into it, and A12.5's net-negative claim is plausible given the new
siblings replace, not add to, that mass.

## 4. Persona changes

**FAIL — undeclared write-allowlist widenings.** Verified against the live
`dadaia_workspace/public/agents/*.md` frontmatter:

| Persona | Current `write_allowlist` (specs-relevant) | TASKS.md write set required | Widening task? |
|---|---|---|---|
| `project-auditor` | none under `specs/` | `specs/audits/**` | **Yes** — FR13/T-050-23, named explicitly in SPEC A13.2 and PLAN |
| `software-architect` | none under `specs/` | `specs/releases/0.5.0/reviews/S1-AR1-ruling.md` (T-050-04) | **No** |
| `qa-engineer` | `specs/releases/**/ALPHA-*-QA.md` only | `specs/releases/0.5.0/reviews/{S1,S2,S3,S4}-qa-close.md`, `RELEASE-VERDICT.md` (T-050-15/22/27/33/36) | **No** |
| `code-reviewer` | none under `specs/` | `specs/releases/0.5.0/reviews/T-050-35-code-review.md` (T-050-35) | **No** |
| `security-reviewer` | none under `specs/` | `specs/releases/0.5.0/reviews/RELEASE-VERDICT.md` (T-050-36) | **No** |

This is not a gate-blocked mechanism (write_allowlist is agent discipline, not
hook-enforced — `DADAIA.md` §2's "stay inside it" is a MUST with no `pre_gate` check
behind it), but it is exactly the class of drift `ai-engineer` exists to prevent, and the
release's own S1-close/S2-close/final-rc reviews depend on these four personas actually
writing those files. **Amendment (blocking):** add one `ai-engineer`-owned task —
sequenced before `S1` starts, since `T-050-04` needs it on day one — widening
`software-architect`, `qa-engineer`, `code-reviewer`, `security-reviewer` to
`specs/releases/**/reviews/**` (a pattern generic enough to survive future releases,
narrower than blanket `specs/**`), with a fixture proving each still refuses a write
elsewhere under `specs/` (mirroring A13.2's proof for `project-auditor`).

`product-engineer`'s existing `specs/**` allowlist already covers `specs/ADRs/**` and the
memory-trio renames — no frontmatter change needed there; consistent with TASKS.md never
naming one.

## 5. Per-harness projection

Every `ai-engineer`-owned task in `S2`/`S3` (T-050-16, T-050-17, T-050-18, T-050-19,
T-050-20, T-050-21, T-050-23, T-050-24) ends its write set with "then one projection
cycle" and a Done criterion citing `dadaia public doctor` green — correctly threading
`dadaia public stage && dadaia public install --target all` through the three harness
projections (`.claude/`, `.codex/`, `.agents/`/`.kimi-code/`) per `dd-ai-eng-knowhow`.
**PASS**, no gap found. One nit: T-050-23's write set is owned jointly by
`software-engineer` (schema/scaffold) and `ai-engineer` (persona/scoped law) but names a
single projection cycle at the end without stating which of the two runs it — harmless in
practice (idempotent), but worth a one-line clarification (owner = `ai-engineer`, since it
is the last write in that task's set).

## 6. Writing-for-agents quality (FR7, FR14 drafts)

**FR7 (`dd-diagnose`) — PASS, strong.** Seven phases, each with a stated *Done when*
(A7.1); phase 0 states the window once and is cited, not restated, by FR14 (A7.2, A14.2);
phase 0 explicitly instructs distrust of a non-`exact` sha instead of diffing it blind
(A7.3, directly operationalizes D-A). The coverage-table requirement (A7.4) is the right
mechanism for the "moved, not copied" claim to be checkable rather than asserted. No CLI
verb/hook named (A7.5) — matches D8/D15.

**FR14 (`dd-audit-project`) — PASS, with one precision gap.** Short SKILL.md + four
disclosed siblings mirrors `AUTHORING.md`'s pattern well; lifting
`disable-model-invocation` and listing the skill in `project-auditor.md`'s `skills:` is
correctly named as its own acceptance (A14.4) rather than assumed. Pillar 1's recurrence
and fix-induced definitions are stated as "operational, not adjectival" (A14.3) — good,
but the SPEC text itself (§3/FR14) never gives the operational definition inline; it is
deferred entirely to implementation. For a spec-level review this is acceptable *only*
because A14.3 makes it a checkable acceptance rather than a hope — flag as a watch item
for the `S3` QA close, not a blocker.

## 7. Ruling fidelity (D8/D14/D15)

No contradiction found. Explicit zero-CLI/zero-hook acceptance ids exist for every FR
that could plausibly grow the CLI or hooks: A7.5 (`dd-diagnose`), A8.3 (bug
append/resolve exit codes unchanged), A9.1–A9.3 (hooks net-deletion, executed-path
proof), A10.5 (behavior-map read by tests/agents only), A14.5 (`dd-audit-project`),
A19.4 (`ADRs/` — "zero CLI verbs, zero doctor rules beyond the folder shape"), A22.6 (the
release-wide invariant, contract-tested). D15's posture sentence is carried verbatim into
FR11's own text (§3/FR11), and TASKS.md restates the acceptance in its "Standing rules"
block rather than only in FR11's task — appropriately defensive against drift, not a
duplication of law (it is a task-level *reminder* of an owned rule, not a second
statement of the rule itself).

## Verdict

**REWORK** — not because of the design's shape, which is the strongest AI-surface
proposal this reviewer has seen from this workspace (measured claims, per-FR bug-surface
accounting, disclosed siblings, D15 discipline everywhere it is claimed) — but because two
findings are load-bearing and both land squarely in `ai-engineer`'s domain, meaning
`product-engineer` cannot close them without a task authored by this review:

1. **Blocking — Persona write-allowlist gap (§4).** Add an `ai-engineer` task widening
   `software-architect`, `qa-engineer`, `code-reviewer`, `security-reviewer` to
   `specs/releases/**/reviews/**`, sequenced before `T-050-04`.
2. **Blocking — Enforcer-retirement completeness (§1).** Add an explicit acceptance id to
   FR10 requiring every test in `test_rules_skills_map.py` at HEAD to have a proven
   counterpart in `test_behavior_map.py` before the old file is deleted.
3. **Non-blocking, requested before implementation.** Make FR10's scoped-AGENTS.md
   discovery structural (glob-derived), not a hand list, and name the three currently
   unlisted `.dadaia/*-AGENTS.md` sources explicitly so the roster in SPEC §3/FR10 does
   not read as authoritative when it is not.
4. **Non-blocking.** Specify anchor markup as zero-cost comment form in FR11/A11.1, and
   extend A8.1's duplicate-statement scan's stated scope to scoped-AGENTS.md pairs
   (§1, §3).

## AI-surface direction, stated plainly

**Net-additive in AI-surface lines, explicitly and honestly so** (PLAN's own framing,
A22.4): one new skill (`dd-diagnose`, two files), one renamed skill with a coverage
table, `dd-release-implement` restructured into three disclosed siblings, seven new/
retired scoped `AGENTS.md` files (`bugs/`, `releases/`, `audits/`, `ADRs/` new;
`backlog/`, `memory/`, root `specs/` retired READMEs folded in), and `DADAIA.md` growing
an estimated ~10–16% on an already-above-target base. Against that, two files retire
outright (`CLOSURE-TEMPLATE.md`, `CLOSURE-CHECKS.md`), `rules-skills-map.json` retires
into `behavior-map.json` rather than living beside it, and the hook surface loses two
blocking mechanisms with nothing replacing them in code. The always-on budget is the one
line item worth the operator's attention at approval time — it is measured, attributed,
and honestly reported rather than hidden, which is the right process even though the
number itself keeps climbing.
