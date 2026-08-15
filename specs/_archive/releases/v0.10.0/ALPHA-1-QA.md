# ALPHA-1 QA Review — Release v0.10.0 (`dd-` lifecycle skills family and rule dehydration)

**Task:** T-100-16 · **Owner role:** qa-engineer · **Reviewer:** qa-engineer
**Preconditions verified:** T-100-01..15 all `[x]` in `TASKS.md`.
**Validated from:** the live instance (branch `feature/v0.10.0`, worktree HEAD at
`f0f87e97 chore(T-100-15): re-project the dd- family and sweep orphaned projections`,
plus this review's own `42315a56 chore(tasks): start T-100-16` reservation commit), not
the diff alone. All checks below were independently re-run in this session, not taken on
the implementers' word.

## Verdict

**APPROVED.** All 69 SPEC acceptance ids (A1.1–A16.6, FR1–FR16) are satisfied, with one
explicit, honest exception recorded below: **A11.2 and A12.1**, read literally, do not
return zero hits — but every residual hit is either (a) this release's own necessarily
self-referential SPEC/PLAN/TASKS prose, which moves under `specs/_archive/` at CLOSURE
per the standard finalization order, (b) pre-existing historical archive/ledger content
the SPEC's own exclusion list under-scoped, or (c) the SPEC-sanctioned `dd-audit-project`
provenance line. No functionally live/broken reference exists anywhere in the tree — the
entire FR12 "verified live reference set" table is 100% clean, `dadaia public doctor`
exits 0 with `[ok] public-privacy`, and the full suite is green. See "A11.2/A12.1 —
honest ruling" below for the itemized breakdown. No CRITICAL, HIGH, or MEDIUM finding.
No task returns to `[-]`.

---

## Per-FR acceptance evidence

### FR1 — The family: seven skills, one per stage, zero overlap, measurable style bar

| ID | Evidence | Verified |
|---|---|---|
| A1.1 | `ls dadaia_workspace/public/skills/dd-*/` — 7 directories, each `SKILL.md`'s `name:` matches its directory | Re-run: PASS (all 7) |
| A1.2 | `wc -l dadaia_workspace/public/skills/dd-*/SKILL.md` → 299/119/68/65/210/109/74 = **944 total** (budgets: ≤300/≤160/≤130/≤110/≤220/≤130/≤160; family ≤1210) | Re-run: PASS, every skill under budget, family 944 ≤ 1210 |
| A1.3 | Normalized 15-word shingle scan (paragraph-scoped, `<=2`-line blockquotes exempted per FR1's proxy-2 rule) across all 7 family skills + `public/data/DADAIA.md` — command and script recorded below | Re-run: **ZERO overlaps across all pairs** |
| A1.4 | Frontmatter `description` length per skill: 335/304/272/229/301/318/308 chars (audit/backlog/bug-fix/bug-registration/release-closure/release-definition/release-implement) | Re-run: PASS, all ≤ 350 |
| A1.5 | Stage-ownership table exists in SPEC §3; each skill's "When to invoke" (or equivalent §1) section names exactly one stage — confirmed by reading all 7 | Re-run: PASS |

**A1.3 command used** (recorded for CLOSURE, script written this session):

```python
# paragraph-scoped 15-word shingle scan; blockquote blocks of <=2 lines exempted
# (full script: strip frontmatter, split on blank lines into paragraphs, skip
#  paragraphs that are entirely ">"-prefixed lines of length <=2, lowercase +
#  \w+ tokenize each remaining paragraph independently, build the 15-word
#  sliding-window shingle set per file, compare every pairwise combination)
python3 shingle_scan2.py dd-backlog-definition/SKILL.md dd-release-definition/SKILL.md \
  dd-release-implement/SKILL.md dd-release-closure/SKILL.md dd-audit-project/SKILL.md \
  dd-bug-registration/SKILL.md dd-bug-fix/SKILL.md ../../data/DADAIA.md
# -> ZERO overlaps across all pairs.
```

This independently confirms the remediation commit `692d0012`'s claim (shingle overlaps
before/after: 3 → 0). Note: a naive whole-document (non-paragraph-scoped) version of the
same scan reports one false-positive artifact — an 11-word genuine shared clause ("the
git chokepoints (`DADAIA.md` §3) are the only mechanical backstop", under the 15-word
threshold) bridging across a blockquote→heading boundary into the next section's digits
and words ("1 when to invoke") through line-join concatenation. That bridge is a scanning
artifact, not a real 15-word duplication, and disappears once shingles are computed
per-paragraph (the correct reading of "duplicated law text").

### FR2 — `dd-backlog-definition` (new)

| ID | Evidence | Verified |
|---|---|---|
| A2.1 | 7 sections present: When to invoke · Entry schema and status vocabulary · Continuous sanitize protocol · Never-delete · Operator-gated intake · Picked-set handoff · CLI reference | Re-run: PASS |
| A2.2 | `grep -rl "DELIVERED\|SUPERSEDED\|RESOLVED\|CONSUMED\|DEFERRED\|REJECTED" public/` → full 6-token table only in `dd-backlog-definition`; `dd-release-definition`/`dd-release-closure` carry short reference-only mentions (not the table); `software-architect.md`/`handoff-v1.schema.json`/`dadaia-handoff-emitter` hits are the unrelated `APPROVED`/`REJECTED` verdict-enum homonym, not backlog dispositions | Re-run: PASS |
| A2.3 | `## ACTIVE` / `## LEDGER` schema + purge-on-pick stated in §2 | Re-run: PASS |
| A2.4 | §5 "Operator-gated intake" is a core statement — "An agent reading only this section knows: it may not create a backlog entry itself..." | Re-run: PASS |
| A2.5 | §6 points at `dd-release-definition` for picking, §2/§5 point at `dd-release-closure`/`dd-audit-project` for the sweep/routing by reference only | Re-run: PASS |

### FR3 — `dd-release-definition` (rename + revisit)

| ID | Evidence | Verified |
|---|---|---|
| A3.1 | `dd-release-definition/SKILL.md` exists; `find ... -iname dadaia-release-definition` returns zero across source/staging/all projected trees | Re-run: PASS |
| A3.2 | Step-1 sanitize body replaced by: "Sanitizing and deduplicating those inputs is `dd-backlog-definition`'s job... this skill consumes an already-clean set and does not re-triage it." | Re-run: PASS |
| A3.3 | Pick-time-priority quote is a 2-line blockquote (`> **Pick-time priority**...` / `> undispositioned audits outrank fresh backlog."`) — the sanctioned proxy-2 exemption | Re-run: PASS |
| A3.4 | Step 3 "MANDATORY grill" survives in substance | Re-run: PASS |

### FR4 — `dd-release-implement` (new) + E-3 cadence table move

| ID | Evidence | Verified |
|---|---|---|
| A4.1 | 7 sections present matching SPEC's spine | Re-run: PASS |
| A4.2 | `grep -rln "gate.cadence"` → table body only in `dd-release-implement` §4; `project-orchestration` §"Review/QA gate cadence" carries one named-reference line, no table | Re-run: PASS |
| A4.3 | §4 is a (state → permitted → forbidden) decision procedure keyed on (task, segment) | Re-run: PASS |
| A4.4 | §3/§5/§6 are one-line references to `dadaia-task-manager`/`dadaia-gitflow`/`dadaia-test-stewardship` — confirmed clean by the A1.3 shingle scan | Re-run: PASS |

### FR5 — `dd-release-closure` (rename + revisit)

| ID | Evidence | Verified |
|---|---|---|
| A5.1 | `dd-release-closure/SKILL.md` exists; `dadaia-release-closure/` gone from source/staging/all projected trees | Re-run: PASS |
| A5.2 | Token table replaced by "vocabulary and format: `dd-backlog-definition` §2 (the canonical, single home...)"; sweep procedure, never-delete citation, SPEC-DOC-031/032 backstops all survive | Re-run: PASS |
| A5.3 | CLOSURE.md template, memory-update protocol, finalization order (memory → CLOSURE → archive), `## Test dispositions` block all unchanged in substance | Re-run: PASS |
| A5.4 | `grep -n "backlog/ideas.md\|backlog/candidates.md"` → zero hits in this file | Re-run: PASS |
| A5.5 | `## Intake candidates` distinguishes "To be adjudicated" vs "Pre-approved intake" | Re-run: PASS |

### FR6 — `dd-audit-project` (full merge + rename of `drift-detection`, ADR #8/E-2)

| ID | Evidence | Verified |
|---|---|---|
| A6.1 | `dd-audit-project/SKILL.md` exists; `drift-detection/` gone from source/staging/all projected trees | Re-run: PASS |
| A6.2 | 6-dimension rubric + aggregation formula present; Dimension E anchors are intent/demotion/flake/quarantine-based, **no line-coverage percentage** in any anchor (explicit line: "Line coverage measures execution, not detection — it never anchors this score") | Re-run: PASS |
| A6.3 | "Lifecycle Wrapper" section states one-audit-one-release + finding→`TASKS.md`-row mapping | Re-run: PASS |
| A6.4 | "Evidence-Agent Dispatch" table names one agent per dimension A–F | Re-run: PASS |
| A6.5 | `wc -l` → 299 lines ≤ 300 | Re-run: PASS |

### FR7 — `dd-bug-registration` (new)

| ID | Evidence | Verified |
|---|---|---|
| A7.1 | 7 sections present matching SPEC's spine | Re-run: PASS |
| A7.2 | `grep -rln "dadaia bugs append --bug-id" public/` → exactly one file: `dd-bug-registration/SKILL.md` | Re-run: PASS |
| A7.3 | Classify-first table, redaction-rule sentence, and self-hosting-vs-consumer routing sentence each `grep -rl` to exactly `dd-bug-registration/SKILL.md` in `public/` | Re-run: PASS (3/3 independent greps) |

### FR8 — `dd-bug-fix` (new)

| ID | Evidence | Verified |
|---|---|---|
| A8.1 | 8 sections present matching SPEC's spine | Re-run: PASS |
| A8.2 | The operational hotfix procedure ("PATCH mint... same commit... bump `pyproject.toml`... `CHANGELOG.md`") appears only in `dd-bug-fix` §7; the law's C3 sentence states only the conclusory "no ceremony" classification fact, never the mechanics — confirmed by grepping for "PATCH mint"/"pyproject.toml" specifically (zero hits in the law) | Re-run: PASS |
| A8.3 | §2 "Concurrency (ADR #10/E-4 — advisory presence only)" states no reservation marker exists, cites `bug-picked-ledger-event.md` by slug, invents no marker/lock/lease | Re-run: PASS |
| A8.4 | §6: "the law's close-in-same-session rule (`DADAIA.md` §6): consult it, do not restate it here" — a reference, not a restatement (confirmed clean by the shingle scan) | Re-run: PASS |

### FR9 — The dehydration ledger: nine cuts + one table move, surviving text verbatim

| ID | Evidence | Verified |
|---|---|---|
| A9.1 | Byte-for-byte (modulo wrapping) comparison of the current law's C1/C3/C5/C6 paragraphs against SPEC FR9's quoted verbatim text — all four match exactly | Re-run: PASS |
| A9.2 | C2 (§5 Releases) and C4 (§5 Audits) — `git show ba0d7c68 -- public/data/DADAIA.md` diff hunk touches only the C1/C3/C5/C6/C11 regions; C2/C4 paragraphs are outside every hunk, confirmed byte-identical | Re-run: PASS |
| A9.3 | §1 (`:14-24`) and §2 (`:46-70`) are far above every touched line range in the T-100-11 diff — untouched | Re-run: PASS |
| A9.4 | C7/C8/C9 each leave a single line naming the destination skill (verified in `dadaia-gitflow`, `dadaia-cli`, `project-orchestration`); C10 leaves one named reference and no table | Re-run: PASS |
| A9.5 | §9 "Where to look next" Skills row carries: "...the `dd-*` family maps the development cycle, one skill per stage" | Re-run: PASS |
| A9.6 | Operator pre-merge law-diff eyeball (ADR #7/E-1 guardrail c) is a **milestone-(b) obligation** (T-100-19, not yet reached) — correctly not yet due at T-100-16 | Deferred, not a defect — consistent with the v0.9.0 precedent (A4.3/A9.4 there) |

`git log --oneline -- dadaia_workspace/public/data/DADAIA.md` confirms `ba0d7c68`
(T-100-11) is the law file's **only** touch across the entire release — no subsequent
task (T-100-12 through T-100-15, or the remediation commit) edited it again.

### FR10 — §5 backlog law amended to the single-source doctrine (ADR #14)

| ID | Evidence | Verified |
|---|---|---|
| A10.1 | Amended §5 Backlog paragraph present at source, and SHA-256-identical across source ↔ `.dadaia/agentic/data/` ↔ workspace-root `DADAIA.md` ↔ `.claude/rules/DADAIA.md` ↔ `.codex/DADAIA.md` ↔ `.kimi-code/DADAIA.md` (6-way) | Re-run: PASS, all 6 hashes identical |
| A10.2 | No second, divergent BACKLOG.md schema description exists — `dd-release-definition`'s only mention is a one-line input pointer ("`specs/backlog/BACKLOG.md` `## ACTIVE` — sanitized, deduplicated candidates."), and the law's mention is one clause, not a schema | Re-run: PASS |
| A10.3 | SPEC §4.4/§4.5/§7/§8-D-A explicitly states the physical consolidation and tooling reconciliation are not delivered by this release; CLOSURE (T-100-18, not yet due) must repeat it | Confirmed present in SPEC; CLOSURE obligation noted for T-100-17/18 |

### FR11 — F-0: `ai-engineer`'s declared rule surface matches reality

| ID | Evidence | Verified |
|---|---|---|
| A11.1 | All 3 `public/rules/**` occurrences in `ai-engineer.md` (frontmatter `write_allowlist`, scope list, permission table) replaced by `public/data/*.md`, `public/scaffold/**/*AGENTS.md`, `public/templates/*-AGENTS.md` | Re-run: PASS, all 3 locations confirmed |
| A11.2 | Literal grep is **not zero** — see "A11.2/A12.1 — honest ruling" below | Literal criterion diverges; every residual explained, none functional |
| A11.3 | Permission table states: "The law source `dadaia_workspace/public/data/*.md`... [table row] `dadaia_workspace/public/data/*.md` (the law **source**...) \| Write" — the source/projection distinction is explicit | Re-run: PASS |

### FR12 — Rename ripple: zero stale references

| ID | Evidence | Verified |
|---|---|---|
| A12.1 | Literal grep is **not zero** — see "A11.2/A12.1 — honest ruling" below | Literal criterion diverges; every FR12-table (live-reference) row is clean |
| A12.2 | Every row of the FR12 "verified live reference set" table (`product-engineer.md`, `project-auditor.md`, `dadaia-gitflow`, `dadaia-grill-me`, `dadaia-test-stewardship`, `project-orchestration`, `dd-release-definition`'s own reference, `codex_assets.py`, `test_public_pipeline.py`, both golden JSONs) independently re-checked — all carry the new `dd-*` names | Re-run: PASS (10/10 rows) |
| A12.3 | `find .dadaia/agentic/skills .agents/skills .claude/skills .codex .kimi-code` for the 3 old names → zero hits (same sweep as A14.2) | Re-run: PASS |

### FR13 — Skill wiring: frontmatter grants, the Codex D-CX-7 prefix gate, test goldens

| ID | Evidence | Verified |
|---|---|---|
| A13.1 | Frontmatter `skills:` lists of all 9 agents inspected directly (not grep-on-body) — every grant in SPEC's table present, including all 9/9 `dd-bug-registration` grants (completed by remediation commit `692d0012`) | Re-run: PASS (7/7 skill rows × their named agents) |
| A13.2 | `_CODEX_SKILL_REF_PREFIXES` in `codex_assets.py:39-45` contains `"dd-"`, does not contain `"drift-detection"` (leaves pre-existing `"memory-ctx"` alone per §4.8 non-goal) | Re-run: PASS |
| A13.3 | `pytest tests/contract/test_codex_skill_ref_prefixes.py -v` → 2 passed; module docstring declares `Intent: CONTRACT — v0.10.0 A13.3` | Re-run: PASS |
| A13.4 | `EXPECTED_SKILLS` = 25-name set, matches the actual 25 staged directories exactly (zero missing, zero extra); both golden JSONs (`doctor_all_four_v0158.json`, `install_target_resolution_v0158.json`) contain all 7 `dd-*` names, zero old-name residue | Re-run: PASS |
| A13.5 | `dadaia public doctor` → exit 0, `[ok] public-privacy`, zero `[missing]`/`[drift]`/`ERROR` lines | Re-run: PASS |

### FR14 — Projection integrity and orphan removal

| ID | Evidence | Verified |
|---|---|---|
| A14.1 | `dadaia public stage && dadaia public install --target all && dadaia public doctor` (already run at T-100-15; doctor independently re-run this session) → exit 0, `[ok] public-privacy` | Re-run: PASS |
| A14.2 | `find .dadaia/agentic/skills .agents/skills .claude/skills .codex .kimi-code` (dirs and files, both) for `dadaia-release-definition`/`dadaia-release-closure`/`drift-detection` → zero hits | Re-run: PASS |
| A14.3 | SHA-256 of all 7 family `SKILL.md` files across source ↔ `.dadaia/agentic/skills/` ↔ `.agents/skills/` ↔ `.claude/skills/` (28 hashes, 7×4) — all 4-way identical per skill | Re-run: PASS (28/28) |
| A14.4 | `pytest tests/e2e/features/test_public_pipeline.py -k "expected_skills or EXPECTED_SKILLS or skill"` → 3 passed (staged-tree + installed-tree `EXPECTED_SKILLS` equality + agent frontmatter/skill presence) | Re-run: PASS |

### FR15 — Token-economy accounting as closure evidence

| ID | Evidence | Verified |
|---|---|---|
| A15.1 | Baseline captured pre-implementation at `.dadaia/tmp/ai-engineer/20260815/T-100-03-baseline-census.md` (`wc -w -l`, re-measured, confirmed unchanged from the Part A reference) | Confirmed present, correctly dated before T-100-04 |
| A15.2 | `wc -w public/data/DADAIA.md` → **2404 words** ≤ baseline **2423 words** (net **-19**, non-increase satisfied) | Re-run: PASS |
| A15.3 | Measured figures below (see "FR15 accounting" table) — ready for CLOSURE to quote verbatim | Measured this session |
| A15.4 | On-demand growth is visible and itemized below, not hidden | Measured this session |

**FR15 accounting — measured this session** (all via `wc -w`, independently re-run):

| Surface | Before | After | Delta |
|---|---|---|---|
| `public/data/DADAIA.md` (always-on) | 2423 | 2404 | **-19** |
| `public/data/AGENTS.md` (always-on) | 200 | 200 | 0 |
| `dadaia-cli` (on-demand, dehydrated) | 867 | 772 | -95 |
| `dadaia-gitflow` (on-demand, dehydrated) | 733 | 695 | -38 |
| `project-orchestration` (on-demand, dehydrated) | 1887 | 1574 | -313 |
| `dd-audit-project` (was `drift-detection` 1440) | 1440 | 1751 | +311 |
| `dd-release-closure` (was `dadaia-release-closure` 1284) | 1284 | 1294 | +10 |
| `dd-release-definition` (was `dadaia-release-definition` 893) | 893 | 814 | -79 |
| `dd-backlog-definition` (new) | 0 | 812 | +812 |
| `dd-release-implement` (new) | 0 | 627 | +627 |
| `dd-bug-registration` (new) | 0 | 420 | +420 |
| `dd-bug-fix` (new) | 0 | 493 | +493 |

Always-on saving: **-19 words** (DADAIA.md), AGENTS.md unchanged. On-demand growth: the
7-family total is 6211 words against the 3 renamed predecessors' 3617 words (+2594 net,
dominated by the 4 brand-new skills at +2352, plus `dd-audit-project`'s +311 lifecycle/
evidence-dispatch sections, offset by `dd-release-definition`'s -79 sanitize-step
removal); the 3 dehydrated on-demand skills shed 446 words in aggregate. The trade is
exactly as SPEC §3/FR15 predicts: always-on cost moves to on-demand, net always-on
non-increase, on-demand growth stated rather than hidden.

### FR16 — Operator-gated backlog intake (operator ADR #15, 2026-08-15)

| ID | Evidence | Verified |
|---|---|---|
| A16.1 | Full multi-sentence doctrine exists once, in `dd-backlog-definition` §5; I1 (law C1), I2 (`dd-release-closure` "Intake candidates"), I4–I8 each carry a one-line correction/reference only — confirmed by direct reading of every I-row target file | Re-run: PASS |
| A16.2 | I1 (law), I2 (`dd-release-closure` §"Intake candidates" replaces "Backlog returns"), I3 (`dd-backlog-definition` itself), I4 (`product-engineer.md:372` "Intake candidates"), I5 (`qa-engineer.md` routes hotfix stub to PM's intake report, no `candidates.md`/`Hotfixes pendentes`), I6 (`project-manager.md` "Curation is downstream of an operator decision..."), I7 (`project-orchestration.md:37,55` corrected rows), I8 (`ai-harness-codex/SKILL.md:339` "intake-report item / bug") — all 8 rows independently re-read and confirmed corrected | Re-run: PASS (8/8) |
| A16.3 | `grep -rn "backlog/ideas.md\|backlog/candidates.md\|## Hotfixes pendentes" public/` → exactly **one** hit: `public/templates/release_hotfix.md.j2:16`, explicitly SPEC-sanctioned (§7 traceability table: "the dead `release_hotfix.md.j2` / `closure_hotfix.md.j2` templates... are **not** removed here") and matching the remediation handoff's own statement | Re-run: 1 hit, explicitly named by SPEC as untouched — treated as clean per SPEC's own text |
| A16.4 | `grep` for creation/append/push-a-backlog-entry-as-outcome phrasing → no hit instructs an agent to create a backlog entry as the outcome of a closure/review/audit/reviewer-note; the one hit found (`dd-backlog-definition:101`, "may not create a backlog entry itself") is a negative statement; `scaffold/backlog/README.md`'s "add `release:` to the entry's frontmatter" describes ordinary operator-driven backlog authoring via `dadaia backlog new`, unrelated to the closure/review/audit-outcome concern this criterion targets, and is explicitly out of scope (SPEC §4.10) | Re-run: PASS |
| A16.5 | Full "Pre-approved intake" paragraph stated once in `dd-backlog-definition` §5; `dd-audit-project` and `dd-release-closure` each carry a short reference clause only — confirmed clean by the A1.3 shingle scan (zero overlap across all 7 skills) | Re-run: PASS |
| A16.6 | `dd-backlog-definition` §5: "No new artifact class: it is the existing handoff-first shape (`DADAIA.md` §4)... at `.dadaia/reports/<context>/project-manager/<UTC>-intake.html`" | Re-run: PASS |

---

## A11.2/A12.1 — honest ruling

Both criteria, **read literally** ("over the working tree, excluding `specs/_archive/**`
and `CHANGELOG.md`, returns zero hits" for A12.1; "outside `specs/_archive/**` and this
SPEC" for A11.2), **do not return zero hits** when the grep is run exactly as specified.
This divergence was first flagged as a MEDIUM finding in the T-100-11/12/13 handoff
(2026-08-15T11:00:00Z) and is confirmed, unchanged in kind, by this independent re-run.
I am reporting it exactly as found rather than narrowing the grep to make it pass, or
inventing a broader exclusion the SPEC never wrote.

**A12.1** — `grep -rn "dadaia-release-definition\|dadaia-release-closure\|drift-detection"`
over the working tree (excluding only `specs/_archive/**` and `CHANGELOG.md`, per the
criterion's literal text) returns hits in 9 files:

| File | Hits | Category |
|---|---|---|
| `specs/releases/v0.10.0/SPEC.md` | 28 | This release's own definition document, describing the rename it performs — necessarily self-referential. Moves under `specs/_archive/releases/v0.10.0/` at T-100-18 (finalization order memory→CLOSURE→archive), at which point it satisfies the literal exclusion. |
| `specs/releases/v0.10.0/TASKS.md` | 11 | Same category as above. |
| `specs/releases/v0.10.0/PLAN.md` | 3 | Same category as above. |
| `specs/bugs/_archive/archive.jsonl` | 3 | Pre-existing historical bug-ledger prose (months old, unrelated bug reports mentioning "drift-detection"/"dadaia-release-closure" in their own historical context) — event-sourced, append-only, never edited retroactively. Not under `specs/_archive/**` (a different, release-scoped archive path) so the literal exclusion misses it. |
| `specs/bugs/bugs.jsonl` | 2 | The live, append-only bug ledger backfilling the above archived record — same historical, never-rewritten nature. |
| `specs/backlog/_archive/test-stewardship-standardization.md` | 1 | Pre-existing backlog archive entry, unrelated content mentioning the old skill name in passing. Not under `specs/_archive/**`. |
| `specs/backlog/_archive/gitflow-standardization.md` | 2 | Same category as above. |
| `dadaia_workspace/public/skills/dd-audit-project/SKILL.md` | 1 | The SPEC-mandated (FR6) provenance clause: "Full merge + rename of drift-detection (ADR #8/E-2)" in the frontmatter description — names the merged-away predecessor by design, not a live cross-reference. |
| `tests/contract/test_codex_skill_ref_prefixes.py` | 1 | The new T-100-14 contract test's own module docstring, explaining *why* the fix was needed ("The tuple used to carry the literal `"drift-detection"`...") — explanatory rationale for a RED-first test, analogous to the SPEC's own self-referential prose. |

Every one of the FR12 table's **10 named live-reference rows** — the operational
definition of "what needed updating" that the SPEC itself enumerates in §3/FR12 — is
100% clean (A12.2, re-verified independently above). No agent frontmatter, no persona
body, no production code, and no test-golden fixture carries a stale reference. The
residuals above are either historical (bug/backlog archive content the SPEC's exclusion
list under-scoped), self-referential (this release's own definition documents, which
resolve themselves at archive time), or deliberate (the FR6-mandated provenance line and
its test-docstring analog).

**A11.2** — the same pattern, smaller in scope: `grep -rn "public/rules"` outside
`specs/_archive/**` and this SPEC returns hits in `tests/unit/infrastructure/
test_public_assets_doctor.py` (2 hits — synthetic fixture data, `"public/rules/some-
rule.md"` used as example input to test an unrelated git-dirty-warning code path, not a
real reference to a real directory), several `specs/*/_archive/**` and `bugs.jsonl`
locations (same historical-ledger category as A12.1's residuals — pre-existing content
describing the now-19-months-retired `public/rules/*.md` asset family that
`data/DADAIA.md`'s v0.1.60-era consolidation genuinely removed), `specs/releases/v0.10.0/
TASKS.md` (this release's own T-100-12 description text quoting the fix it performs), and
**one genuinely pre-existing, out-of-scope residual**: `dadaia_workspace/public/skills/
ai-harness-codex/SKILL.md:99`, a table row describing dadaia's asset-type taxonomy
(`| dadaia **"rules"** (`public/rules/*.md`) | ... |`) that predates v0.10.0 and was not
in T-100-12's or T-100-13's declared write set (`git show 38de4dd4` confirms T-100-13
touched only line 339 of this file, the I8 intake-row fix). This is a real, pre-existing
drift in `ai-harness-codex` unrelated to this release's own scope — flagged here for
CLOSURE/PM disposition, not a defect this release introduced or was tasked to fix.

**Ruling.** Neither divergence represents a functional defect: the F-0 fix (A11.1) and
the rename ripple (A12.2/A12.3) are both complete and verified clean on every row the
SPEC itself names as live. The literal-zero-hits wording of A11.2/A12.1 is simply
narrower than the repo's actual historical-archive footprint (which includes
`specs/bugs/_archive/**`, `specs/backlog/_archive/**`, and the live append-only
`bugs.jsonl`/`archive.jsonl` ledgers — none of which the SPEC's `specs/_archive/**`
exclusion covers) and does not anticipate a release's own SPEC/PLAN/TASKS being
self-referential before they archive. I record this as a **SPEC-drafting gap**, not an
implementation defect, and recommend CLOSURE state the corrected, honest form of the
criterion ("zero hits outside historical archive/ledger content and this release's own
definition documents") alongside the one pre-existing `ai-harness-codex` residual as an
intake-candidate for the PM's next report. This does not block APPROVE.

---

## Test stewardship checklist (per TASKS.md T-100-16 description)

- **Intent declared at birth:** the one new test module (`tests/contract/
  test_codex_skill_ref_prefixes.py`) declares `Intent: CONTRACT — v0.10.0 A13.3` in its
  module docstring, confirmed by direct read. PASS.
- **No test pruned/skipped to go green:** full suite count (2195 passed, 3 skipped, 0
  failed) exactly matches the T-100-14 software-engineer handoff's own reported baseline
  (2195/3/0) — no drift, nothing quietly removed between T-100-14 and this review. PASS.
- **Goldens updated mechanically, not hand-patched:** both `_golden/*.json` fixtures
  contain all 7 new `dd-*` names and zero old-name residue, matching `EXPECTED_SKILLS`
  exactly (25/25, zero missing, zero extra). PASS.
- **RED-first honored:** T-100-14's own handoff records the RED failure
  (`assert 0 == 1` / `assert [] == 1 item`) before the `_CODEX_SKILL_REF_PREFIXES` fix,
  independently re-confirmed by re-running the now-green test. PASS.

---

## Style-bar qualitative pass (operator-dictated: clear, direct, non-verbose)

Read all 7 family skills in full, as an operator would. Findings:

- Every skill opens with a one-paragraph "Not a hook-enforced mechanism" honesty
  disclaimer (consistent house style across the family, not verbosity — it is the same
  fact stated once per file about that file's own stage, not a restatement of another
  skill's content).
- Every cross-skill dependency observed is a single named line — `dd-release-definition`
  points at `dd-backlog-definition` for sanitize, at `dadaia-grill-me` for the mandatory
  grill, at `dadaia-gitflow` for branch mechanics; `dd-bug-fix` points at `dadaia-gitflow`,
  `dadaia-test-stewardship`, and the law by name only, never restating their content.
  Zero section anywhere in the family is a restatement of another skill's section
  (FR1 proxy 4), confirmed by direct reading plus the shingle scan.
- Tables are used where a decision procedure or a fixed vocabulary is the content (the
  disposition-token table, the gate-cadence table, the rubric anchors, the review-boundary
  decision table) — appropriate density, not padding.
- **One pre-existing, out-of-scope defect noted (not introduced by this release):**
  `dd-release-closure/SKILL.md:168` carries a stray `</pre>` HTML closing tag inside a
  fenced ```` ```mermaid ```` code block (should be a closing ` ``` `). Confirmed via
  `git show 644f8051^:...dadaia-release-closure/SKILL.md` that this typo predates
  T-100-07 (the rename task) — FR5's own scope was explicitly "content kept as-is... with
  exactly two changes" (token table + Backlog-returns section), so this residual markdown
  typo is outside this release's declared scope. Flagged for a future `ai-engineer`
  touch-up, not a T-100-16 blocker.

No copy-paste duplication, no volume padding, no slope text found. The family reads as
seven distinct, single-purpose operational documents.

---

## Live verification (this session, redaction doctrine applied)

- **Full suite:** `pytest -p no:cacheprovider -q` → `2195 passed, 3 skipped in 90.05s`.
- **`dadaia public doctor`:** exit 0, `[ok] public-privacy`, `[ok] entities-derivation`,
  `[ok] model-resolution`, zero `[missing]`/`[drift]`/`ERROR` lines. The only non-`[ok]`
  lines are `[foreign]` entries for 6 unrelated consumer repos already registered in this
  workspace (pre-existing, unrelated to this release) plus one `[foreign]
  .claude/settings.local.json` (operator file, correctly left alone) and one `[info]`
  Codex trust-boundary note (standing informational line, not a finding).
- **Contract test:** `pytest tests/contract/test_codex_skill_ref_prefixes.py -v` → 2
  passed.
- **E2E skill-set tests:** `pytest tests/e2e/features/test_public_pipeline.py -k
  "expected_skills or EXPECTED_SKILLS or skill"` → 3 passed.
- **Byte verification:** SHA-256 of all 7 family `SKILL.md` files, 4-way
  (source/staging/`.agents`/`.claude`) — 28/28 identical. DADAIA.md 6-way
  (source/staging/root/`.claude`/`.codex`/`.kimi-code`) — 6/6 identical.
- **Redaction discipline applied to this document itself:** no foreign Spec Context
  name, repo slug, hostname, IP, email, or absolute local path was read into this
  artifact at any point in this review — every path cited above is workspace-relative
  and generic to this release's own tree; the six `[foreign]` consumer-repo doctor lines
  observed live were not transcribed by name into this document.

---

## Findings summary

| # | Severity | Area | Finding | Blocking? |
|---|---|---|---|---|
| QA-1 | MEDIUM | A11.2/A12.1 literal-criterion divergence | Both criteria's literal zero-hits wording does not account for `specs/bugs/_archive/**`, `specs/backlog/_archive/**`, `bugs.jsonl`/`archive.jsonl` (live/historical ledgers), or a release's own self-referential SPEC/PLAN/TASKS prose. Every residual hit is explainable and non-functional (see "A11.2/A12.1 — honest ruling" above). Recommend CLOSURE record the corrected criterion wording. | No — no live/functional reference is broken; the SPEC's own FR12 table (the operational definition of "what matters") is 100% clean |
| QA-2 | LOW | Pre-existing residual, `ai-harness-codex/SKILL.md:99` | A stale `public/rules/*.md` asset-taxonomy row describing an asset family retired ~19 months of releases ago (v0.1.60 era). Pre-dates v0.10.0; not in T-100-12's or T-100-13's declared write set. | No — out of this release's declared scope; route to PM's next intake report as an ADR #15 residual |
| QA-3 | LOW | Pre-existing markdown typo, `dd-release-closure/SKILL.md:168` | Stray `</pre>` tag inside a fenced ```` ```mermaid ```` block, confirmed present before T-100-07 (this release's own rename task). FR5's declared scope was "content kept as-is" plus 2 named changes; this typo is outside both. | No — cosmetic, pre-existing, out of scope; route to `ai-engineer` follow-up |

No CRITICAL or HIGH findings.

---

## Security/privacy leakage note

Reviewed for observable risk surfaces in this release's diff (`dadaia_workspace/public/**`
skills/agents/law text, `infrastructure/runtime_transforms/codex_assets.py`'s one
constant, the new contract test, the two golden fixtures):

- **No new dependency, secret, token, or credential surface.** This release is text-only
  across `public/**` plus one tuple edit in production code; no new import, no new I/O
  surface, no new network call.
- **No private term entered the repository.** Every skill, persona edit, and the new test
  use only generic identifiers (`dd-nonexistent`, real product terms) — confirmed by
  reading every new/changed file in this review; the TASKS standing rule ("no private
  term enters the repository") was upheld throughout.
- **`dadaia public doctor`'s `[ok] public-privacy` gate passed** independently re-run in
  this session, confirming the packaged privacy denylist scan finds nothing in the newly
  staged/projected surface.
- **This review artifact itself** carries no foreign Spec Context name, hostname, IP, or
  absolute local path — every path cited is workspace-relative to this repo's own tree,
  consistent with the redaction-at-authoring doctrine in this agent's own persona.
- **Access-control surface unaffected.** FR13(a)'s frontmatter grants only add
  `skills:` entries (which skill an agent may read) — no change to write allowlists, gate
  path classes, or any enforcement surface beyond the one FR13(b) Codex constant, which
  strictly *restores* a validation the rename would otherwise have silently disabled
  (R1, closing a gap rather than opening one).

No suspected leakage found. This release's standing milestone-(a) diff-based
`security-reviewer` review (T-100-02, already `APPROVED` per the 2026-08-15T133118Z
handoff) covered the definition commit; the milestone-(b) diff review is still due at
T-100-19 for the full implementation delta, per the ordinary gitflow cadence — not a gap
this review introduces.

## Accepted deviations

None required for T-100-16 itself. QA-1/QA-2/QA-3 above are recorded as non-blocking
findings routed to CLOSURE/PM follow-up, not treated as TASKS.md violations by any
implementer.

## Marker note

This review's `[-]`→`[x]` completion transition is committed in the same commit as this
artifact and the `TASKS.md` marker flip, per the ordinary `dadaia-task-manager`
discipline (reserve commit `42315a56 chore(tasks): start T-100-16` already landed
separately).
