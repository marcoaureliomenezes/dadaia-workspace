# T-045-28 — FR13 persona line-ceiling trim: coverage table

Release v0.4.5, `S4`. AS-1: relocate justified overflow only into sibling mechanisms
that **already exist** — no new skill, no new sibling file. A13.2: every
removed/relocated block names its surviving home; a fact with no home stays, with its
overflow justification.

## Scope-definition drift found and corrected (report to CLOSURE)

TASKS.md's T-045-28 write set names four personas
(`product-engineer`, `qa-engineer`, `ai-engineer`, `software-architect`). SPEC.md FR13
(line 483) and the re-run baseline (`.dadaia/tmp/ai-engineer/20260826/T-045-27-v6-v7-v9-raw.md`)
both measure **five** personas above the 220-line ceiling — `software-engineer` (245/247
lines, source/projected) is over-ceiling too and was omitted from both TASKS.md's write
set and SPEC's own FR13 prose ("The four over-ceiling personas"). Per the dispatching
agent's explicit instruction, `software-engineer.md` is included in this pass and the
drift is recorded here rather than silently worked around — TASKS.md itself is untouched
(out of this task's write set); the operator/PM should reconcile the "four" wording at
CLOSURE.

## Per-persona line counts (A13.1 — projected, `.claude/agents/*.md`)

| Persona | Before | After | Δ lines | Before tokens | After tokens | Δ tokens |
|---|---:|---:|---:|---:|---:|---:|
| `product-engineer` | 336 | 279 | **−57** | 2658.7 | 2077.5 | −581.2 |
| `qa-engineer` | 276 | 269 | **−7** | 1939.1 | 1879.3 | −59.8 |
| `ai-engineer` | 275 | 252 | **−23** | 2173.2 | 1907.2 | −266.0 |
| `software-architect` | 253 | 250 | **−3** | 1989.7 | 1933.8 | −55.9 |
| `software-engineer` | 245 | 245 | **−2*** | 1750.3 | 1703.7 | −46.6 |
| **Fleet (5 personas)** | **1385** | **1295** | **−90** | 10511.0 | 9501.5 | **−1009.5** |

`*` software-engineer's projected-line delta reads 247→245 (−2) in the raw capture
(2-line frontmatter/harness padding above the source's 245); source-line delta is also
245→243 (−2). Fleet net across all 9 personas (line count, projected):
2187 → 2095 = **−92, negative (A13.1 satisfied)**.

## Relocated blocks — surviving home (A13.2)

| # | From persona | Removed/relocated block | Class | Surviving home |
|---|---|---|---|---|
| 1 | `product-engineer` | "SDD file hierarchy" ASCII directory tree + `Draft`/`Em revisão`/`Aprovado` status-lifecycle line | (b) role-adjacent fact, useful to every navigator | `dadaia-workspace-spec-navigator/SKILL.md`, new "## Directory reference" section (verbatim tree) + pointer to `DADAIA.md` §6 for the status tokens |
| 2 | `product-engineer` | "Memory atomicity contract" bullet 1 (write-phase gating) | (a) internal duplicate — the same fact is already stated in this file's own §1 Lifecycle position (lines 82-85) | Deleted outright, no pointer needed (same file, same session's attention) |
| 3 | `product-engineer` | "Memory atomicity contract" bullets 2-3 (Markdown/Mermaid/screenshot format, forbidden-sections rule) | (a) restatement of a skill PE already invokes | `dd-release-implement`'s `CLOSURE-CHECKS.md` §1 (already stated there, items 4-5) — pointer only, no merge needed (pure duplicate) |
| 4 | `product-engineer` | "Product memory content contract" (folder-catalog shape: `index.md` sections, feature-atom sections, templates, closure-update rule) | (b) role-specific procedure, no home existed yet | `dd-release-implement`'s `CLOSURE-CHECKS.md` §1, new item 7 (merged verbatim into the memory-update protocol PE already follows at closure) |
| 5 | `product-engineer` | "Release definition from bugs/backlog" restated step list (pick/sanitize/bug-always-solved/mandatory grill) | (a) restatement of `dd-release-definition`'s own protocol — **and a drift**: PE's copy listed "sanitize" as its own step 1, but `dd-release-definition`'s SKILL.md explicitly assigns sanitizing to `dd-backlog-definition`/PM, never PE | `dd-release-definition` (already-existing skill, already invoked by name) — pointer replaces the stale restatement, fixing the drift at the same time |
| 6 | `product-engineer` | Phase-8 "Closure" procedural bullet list (Summary/Tasks/Validations/Drifts/Memory updates/Intake candidates/Archive decision + `git mv` block) | (a) restatement of `CLOSURE-TEMPLATE.md`'s own section shape + `dd-release-implement` step 12's archive instruction | `dd-release-implement`'s `CLOSURE-TEMPLATE.md` (shape) + `SKILL.md` step 12 (archive mechanics) — pointer only |
| 7 | `qa-engineer`, `software-architect` | "Bug-surface axis (FR24, required)" paragraph — identical wording in both files | (a) verbatim cross-persona duplicate (CONTEXT-ENGINEERING.md §1 smell: "same paragraph in 2+ files") | `dd-bug-registration/SKILL.md`, new "## 5. Review-verdict bug-surface axis (FR24)" section (merged, generalized subject line covering any reviewer verdict) — both personas already grant `dd-bug-registration` |
| 8 | `qa-engineer` | "Workspace protocol" section's spec-loading list + "Legacy compat" blockquote | (a) restatement of `dadaia-workspace-spec-navigator`'s own steps 2/4/5/6 | `dadaia-workspace-spec-navigator` (already invoked by name) — pointer replaces the restated list; the `[-]`-before-writing rule (QA-specific) stays inline |
| 9 | `software-architect` | ONBOARD/DRAFT/REVIEW modes' 3x-repeated spec-loading file list (`constitution.md`, `memory/architecture.md`, `memory/product/index.md`, `memory/tech-stack.md`) | (a) internal triple restatement + restatement of `dadaia-workspace-spec-navigator` | `dadaia-workspace-spec-navigator` (already invoked by name in this persona's skills list) — each of the 3 modes keeps only its own delta (`foundation/SPEC.md`, canonical order) |
| 10 | `ai-engineer` | "Harness mastery" sibling table (`CLAUDE-CODE.md`/`CODEX.md`/`CONTEXT-ENGINEERING.md`/`AUTHORING.md` purposes) | (a) verbatim-in-substance duplicate of `dd-ai-eng-knowhow/SKILL.md`'s own Part 2 sibling table | `dd-ai-eng-knowhow/SKILL.md` Part 2 (already the canonical table) — pointer only, no merge needed |
| 11 | `ai-engineer` | Model-tier registry decision table + bump/downgrade prose | (a) verbatim-in-substance duplicate of `CONTEXT-ENGINEERING.md` §4's own decision table | `dd-ai-eng-knowhow`'s `CONTEXT-ENGINEERING.md` §4 (already the canonical rubric) — pointer only |
| 12 | `ai-engineer`, `software-engineer` | Report-section closing paragraph ("Your completed implementation is a handoff, not task completion: the task stays `[-]` until <trio> approve...") — near-identical wording in both files | (a) verbatim cross-persona duplicate of a section `dd-release-implement/SKILL.md` itself labels **"canonical home"** ("## Review/QA gate cadence (canonical home)") | `dd-release-implement/SKILL.md`'s "Review/QA gate cadence" section (already the designated canonical home; both personas already grant this skill) — pointer replaces the restatement in both files |

## Not moved — fact with no home, overflow justification stays inline (A13.2/A13.4)

Per-persona identity content with no shared sibling to carry it: `product-engineer`'s
Spec-lifecycle phase→action map and phases-4-8 authoring steps (PE is the sole owner of
SPEC/PLAN/TASKS/CLOSURE authorship — no other agent or skill performs this); `qa-engineer`'s
E2E toolchain table, test-pyramid/zero-tolerance list, and hotfix-candidate filing
procedure (QA-only procedures, no existing sibling covers them); `software-architect`'s
mode-specific checklists and finding-format template (unique to architecture review);
`software-engineer`'s stack-expertise and OWASP self-check sections (implementer-specific,
already cross-referenced to `security-reviewer`'s fuller methodology rather than
duplicating it). None of these were touched.

## Protected — never removed (A13.3)

Every `[SCOPE ERROR]` block, every "Scope"/"You do NOT write" table, every
"Write permissions" table (mirroring each persona's frontmatter `paths.write_allowlist`),
and the `[SDD HARD STOP]` block (`product-engineer`) are byte-identical before and after
this pass — verified by diff during authoring (no write-allowlist row, scope boundary, or
hard-stop block appears in any relocated/removed block above).

## Residual side-effect on V7 (negations) — noted, not this task's target

T-045-27 (already `[x]`) owns the negation count; T-045-28's target is line count
(A13.1/V9). This pass's pointer phrasing ("referenced, not restated" — repeated 9x
across the touched files) trips the V7 negation regex on "not", moving the 5-persona
negation subtotal from 223→226 (+3) and the fleet V7 total from 254→257 (Claude Code).
Flagged here rather than hidden; a future pass can reword the pointer idiom
positively (e.g. "canonical home:" instead of "referenced, not restated") without
reopening T-045-28's line-count scope.

## Skill-sibling growth (on-demand, not always-on — does not count toward V6)

Content relocated INTO a skill sibling makes that sibling's on-demand body longer, not
the always-on set: `dadaia-workspace-spec-navigator/SKILL.md` (+27 lines, directory
tree), `dd-release-implement/CLOSURE-CHECKS.md` (+19 lines, memory folder-catalog shape),
`dd-bug-registration/SKILL.md` (+6 lines, FR24 axis). These three files are loaded only
when the skill is invoked (per-invocation, not per-turn) — QA's own close should read
this as relocation, not growth of the always-on budget T-045-27 measured.
