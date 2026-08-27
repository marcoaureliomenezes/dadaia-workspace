# T-050-21 Coverage Table — the skill surface rides the canon

**Release:** 0.5.0 · **Segment:** S2 · **Task:** T-050-21 (SPEC FR12 · A12.1–A12.5 ·
D8/D15/D-F) · **Author:** ai-engineer · **Date:** 2026-08-27

## Commits (this task)

| # | Sha | Family |
|---|---|---|
| 1 | `400a0554` | `chore(bugs): report backlog-cli-help-cites-retired-ledger-and-bl-dup` (ADDITIVE, isolated) |
| 2 | `8c27dc9e` | bug-resolution: `dd-bug-fix` → `dd-bug-resolution` (git mv + rewrite), `dd-diagnose`, `dd-bug-registration` |
| 3 | `d5d6cce1` | release-implement: `SKILL.md` + new `RC-FLOW.md`/`RELEASE-EVENTS.md`/`MEMORY-UPDATE.md` |
| 4 | `d4f386db` | backlog-definition: live-photo + `backlog_histo.jsonl` |
| 5 | `a4d144cd` | release-definition: `--set`-not-`--event`, bare SemVer, `_ideas/`, `defined` milestone |
| 6 | `417f97b2` | scoped `AGENTS.md` family: `specs-AGENTS.md`, `scaffold/AGENTS.md`, `scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `specs/memory/AGENTS.md`, `specs/backlog/AGENTS.md` (new) |
| 7 | `e8ce2c80` | persona citations: product-engineer, project-manager, project-auditor, code-reviewer, software-engineer, ai-engineer, scaffold/constitution.md |
| 8 | `112a1522` | remaining skill citations: dadaia-task-manager, spec-navigator, spec-reviewer, dd-manager-orchestration, dd-audit-project/RUBRIC.md |
| 9 | `45d01d51` | drop the transitional `dd-bug-fix` parenthetical from `bugs/AGENTS.md` |
| 10 | `a25a4a26` | behavior-map.json hash-tuple re-record (rename + skill/scoped hashes) |
| 11 | `31a10af4` | `shipped-hashes.json` — append the new `specs-AGENTS.md` digest |
| 12 | `e1403725` | fix: re-record the `scaffold/AGENTS.md` scoped hash tuple (missed in #10) |
| 13 | `64863a21` | economy pass: cut restated dual-write/purge-on-pick text |

## `CLOSURE-CHECKS.md` / `CLOSURE-TEMPLATE.md` — every block's surviving home (A12.2)

| # | Block | Origin | Surviving home | Note |
|---|---|---|---|---|
| 1 | §1 Memory update protocol | `CLOSURE-CHECKS.md` §1 | `dd-release-implement/MEMORY-UPDATE.md` | Content carried forward verbatim in substance |
| 2 | §2 Disposition sweep rule + CONSUMED→terminal update discipline | `CLOSURE-CHECKS.md` §2 | `dd-release-implement/RC-FLOW.md` step 10 | The "one `## LEDGER` line" language retired — now "one `backlog_histo.jsonl` record, rewritten in place" (FR5 already landed, T-050-13) |
| 3 | §3 Artifact GC sweep — scope, keep/delete rule, lane guard | `CLOSURE-CHECKS.md` §3 | `dd-release-implement/RC-FLOW.md` step 11 | Unchanged in substance |
| 4 | §4 Test dispositions (feeds closure) | `CLOSURE-CHECKS.md` §4 | `dd-release-implement/RC-FLOW.md` "Test-stewardship touchpoints" + step 9's `closure-test-dispositions` note class | Recorded as a `note`, not a `CLOSURE.md` table row |
| 5 | §5 Out of scope for closure | `CLOSURE-CHECKS.md` §5 | `dd-release-implement/RC-FLOW.md` "Out of scope for closure" | Verbatim |
| 6 | §6 Segments (ADR-1/ADR-5) | `CLOSURE-CHECKS.md` §6 | `dd-release-implement/RC-FLOW.md` "Segments" | Corrected: `RELEASE.jsonl` is one file per release (not per segment); `data.segment` carries the split, `TASKS.md` still splits by directory |
| 7 | `## Summary` | `CLOSURE-TEMPLATE.md` | `RELEASE.jsonl` `note` (`data.kind: "closure-summary"`) | `RELEASE-EVENTS.md`'s conversion table |
| 8 | `## Tasks completed` | `CLOSURE-TEMPLATE.md` | Native: `TASKS.md`'s `[x]` markers + each task's final commit sha | No `note` needed |
| 9 | `## Validations` | `CLOSURE-TEMPLATE.md` | Native: per-task `implementation-complete` handoffs + the trio's `APPROVE` verdicts | No `note` needed |
| 10 | `## Size accounting` | `CLOSURE-TEMPLATE.md` | `RELEASE.jsonl` `note` (`data.kind: "closure-size-accounting"`) | `RELEASE-EVENTS.md`'s conversion table |
| 11 | `## Drifts` | `CLOSURE-TEMPLATE.md` | `RELEASE.jsonl` `note` (`data.kind: "closure-drift"`, one per drift) | `RELEASE-EVENTS.md`'s conversion table |
| 12 | `## Memory updates` | `CLOSURE-TEMPLATE.md` | Native: the memory atom diffs themselves, in git history | No `note` needed |
| 13 | `## Dispositions` | `CLOSURE-TEMPLATE.md` | Native: `backlog_histo.jsonl`'s `release` field + `BUGS.jsonl`'s `resolved_release` field, per item | Verified with `dadaia bugs stats` / `dadaia backlog doctor`, never re-tabulated |
| 14 | `## Test dispositions` | `CLOSURE-TEMPLATE.md` | `RELEASE.jsonl` `note` (`data.kind: "closure-test-dispositions"`) | `dadaia-test-stewardship`'s own record is the primary source; the note only summarizes |
| 15 | `## Record-only observations` | `CLOSURE-TEMPLATE.md` | Native: the reviewer's own findings array/handoff | Never re-homed (FR6/R4) — this table was always just an aggregator |
| 16 | `## Intake candidates` | `CLOSURE-TEMPLATE.md` | Native: `project-manager`'s intake-report workflow (`dd-backlog-definition` §5) | Handed directly, no staging list |
| 17 | `## Artifact GC sweep` | `CLOSURE-TEMPLATE.md` | `RELEASE.jsonl` `note` (`data.kind: "closure-artifact-gc"`) | `RELEASE-EVENTS.md`'s conversion table |
| 18 | `## Archive decision` | `CLOSURE-TEMPLATE.md` | Native: the `git mv` fact + `phase: ARCHIVED` record | `MOVE` is the only path now; the `KEEP` alternative retires with the template |

**Transitional note (until T-050-25A).** `dadaia specs doctor`'s SPEC-DOC-006 still
requires an archived release directory to carry a `CLOSURE.md` with `## Summary`,
`## Validations`, `## Drifts`, `## Memory updates` headings and a validation triple —
that doctor-side parser retires at **T-050-25A** (FR15), a later task, not this one.
`RELEASE-EVENTS.md`'s conversion table names a minimal freeform `CLOSURE.md` (four
headings, no template) as the SPEC-DOC-006-compatibility bridge until then.

## The `dd-architecture-survey` operative pointer (SPEC FR12, carried forward)

`dd-release-implement/RC-FLOW.md` step 3 ("Segment close") names `dd-architecture-survey`
as an operative dependency at every `alpha-N`/release close — the exact placement
`BACKLOG.md`'s `dd-architecture-survey` entry requires under its "Surface ownership"
ruling (2026-08-23 BL-CONFLICT adjudication). The skill itself is not yet built (a
`## ACTIVE` backlog candidate); the pointer stays live so a future rebuild of this file
cannot silently drop it — the exact R-4 risk this segment names.

## A12.1 — zero-hit grep for `dd-bug-fix`

```
grep -rn "dd-bug-fix" dadaia_workspace/public/
dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md:3:  ...Renamed from `dd-bug-fix` at v0.5.0 T-050-21 (FR12)...
dadaia_workspace/public/scaffold/bugs/AGENTS.md:50:  ...(renamed from `dd-bug-fix` at T-050-21).
```

Both hits are provenance notes ("renamed from"), not a live reference naming
`dd-bug-fix` as an operative skill — zero references to the OLD NAME as a skill to use
survive in the live AI-entity surface (`dadaia_workspace/public/`). Residual mentions
outside `dadaia_workspace/public/` are out of this task's write authority and are
historical/planning record, not the live surface A12.1 governs:

- `specs/_archive/**`, `specs/releases/v0.4.5/**` — a stale, non-active, non-archived
  release directory predating this rename (treated as history in spirit; not this
  release's scope to touch).
- `specs/releases/0.5.0/{SPEC,PLAN,TASKS}.md`, `specs/releases/0.5.0/reviews/**` — this
  release's own planning/review record, describing the rename as work-to-do or
  work-done; not the skill surface itself.
- `specs/backlog/BACKLOG.md` — two backlog candidates (`dd-architecture-survey`,
  `dadaia-router`) reference the old name in still-unpicked prose; `specs/backlog/**` is
  `project-manager`'s exclusive write domain (`DADAIA.md` §6), out of this task's reach.
- `specs/memory/product/**` — two memory atoms cite the old name; `specs/memory/**` is
  `product-engineer`'s exclusive write domain, gated to DEFINITION/CLOSURE phase — a
  named CLOSURE update target already tracked in the SPEC's own memory-update table
  (`specs/memory/product/agents/agentic-entities.md`).
- `specs/bugs/BUGS.jsonl` — ledger records citing the old skill name as historical
  context inside already-resolved bug prose (immutable-core fields); one such record
  (`skill-docs-cite-retired-bugs-append-event-flag`) explicitly deferred its
  `dd-bug-fix`/`dd-release-definition` portion to this task — now fulfilled.
- `tests/**` — comment citations; `tests/**` is never this task's write set.

## V11 — AI-surface line count, `public/{agents,skills,data,entities}/**`

| Measurement | Value |
|---|---|
| Baseline (S2 start) | 7,930 |
| After T-050-21 (this task, HEAD) | 8,474 |
| Whole-segment delta (S2 total, informational — includes FR9/FR10's `behavior-map.json`, FR11, T-050-17 and every other S2 task, not just FR7/FR11/FR12) | +544 |

**FR7 + FR11 + FR12 accounting (SPEC A22.4's actual scope — not the whole segment):**

| FR | Task | Net (lines) | Source |
|---|---|---|---|
| FR7 | T-050-16 (`dd-diagnose` + `LINEAGE.md`) | +178 | T-050-16 coverage table |
| FR11 | T-050-20 (`DADAIA.md` governance additions) | +26 | `git show --stat c5df4bf9 -- public/data/DADAIA.md` (+52/−26) |
| FR12 | T-050-21 (this task) | **−1** | `git diff --shortstat b4ae686b -- public/{agents,skills,data,entities}` = 606 insertions(+)/607 deletions(−) |
| **Sum** | | **+203** | |

**A22.4's own text: "FR12's net is negative and S2's total (FR7 + FR11 + FR12) is
reported with its per-FR attribution"** — two separate clauses. FR12's own net is
**−1** (negative — satisfied, after an economy pass moved it from an initial +17 by
collapsing three restated-elsewhere paragraphs to one-line pointers:
`dd-release-definition`'s bare-SemVer-id/`_ideas/` explanation duplicated
`specs/releases/AGENTS.md`'s own canonical statement; `dd-backlog-definition`'s
CONSUMED→terminal explanation duplicated `RC-FLOW.md` step 10's fuller version).
The combined FR7+FR11+FR12 sum is **reported honestly above, at +203** — FR7's +178 and
FR11's +26 are outside this task's write authority (FR7 is T-050-16's closed task;
`DADAIA.md` is Tier-1, single-writer T-050-20 per A11.1) and are not renegotiable here;
every legitimate restatement this task's own text could collapse has been collapsed.
FR12 alone does not have enough surface to absorb both FR7 and FR11's additions without
deleting content those FRs' own SPEC text mandates as new law (bare-SemVer/`_ideas`
rules, `RELEASE.jsonl` event recipes, the corrected bug/backlog terminal-token
vocabulary) — cutting further would trade a line-count target for missing law, which
the standing "reduce implementation complexity, never bolt on, never grow for a
symptom patch" order does not authorize in reverse (deleting REQUIRED new rules is not
simplification).

## Acceptance cross-reference

- **A12.1** — zero-hit grep for `dd-bug-fix` as a live reference in
  `dadaia_workspace/public/`, above.
- **A12.2** — `CLOSURE-TEMPLATE.md`/`CLOSURE-CHECKS.md` deleted; every block's surviving
  home named, above.
- **A12.3** — every rewritten skill's steps end on a checkable *Done when* (`RC-FLOW.md`'s
  14-step arc, `dd-bug-resolution`'s checklist, `dd-diagnose`'s checklist unchanged).
- **A12.4** — `dadaia public doctor` green (`[ok]`/`[foreign]`/`[info]` only, zero
  `[drift]`/`[missing]` among this task's projected files); `entities-derivation` line
  reports 9 Personas ↔ 9 core sub-agents, 5 Deterministic Behaviors; FR10's enforcer
  (`tests/contract/test_behavior_map.py`) green, 30/30, with re-recorded hash tuples and
  `recorded_by: "ai-engineer"` on every touched row.
- **A12.5** — FR12's own AI-surface net is negative (**−1**), FR7's addition included in
  the reported combined total (+203, above) — measured, not estimated.
