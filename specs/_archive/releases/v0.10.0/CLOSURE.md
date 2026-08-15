# Closure: Release — v0.10.0 — `dd-` lifecycle skills family and rule dehydration

**Status:** Aprovado
**Release ID:** v0.10.0
**Owner:** product-engineer
**Closed:** 2026-08-15
**Branch:** `feature/v0.10.0` (cut from `develop` at `0f66fb3f`; branch contract: `dadaia-gitflow`)
**Source SPEC:** `specs/releases/v0.10.0/SPEC.md` · **Source PLAN:** `specs/releases/v0.10.0/PLAN.md`
**QA close of the flat increment:** `specs/releases/v0.10.0/ALPHA-1-QA.md` (APPROVED, 69/69 acceptance ids)
**Closed against the protocol this release itself renamed:** `dd-release-closure` — the
first closure written under the skill it shipped, including its `## Intake candidates`
section (ADR #15 / FR16), which replaces the `## Backlog returns` heading v0.9.0 used.

---

## Summary

v0.10.0 gives the development cycle a skill surface that matches its shape. Seven `dd-`
prefixed skills now exist, one per lifecycle stage — backlog definition, release
definition, release implementation, release closure, project audit, bug registration, bug
fix — and each is the single operational home of its stage's protocol. Four were written
from scratch (`dd-backlog-definition`, `dd-release-implement`, `dd-bug-registration`,
`dd-bug-fix`); three are renames with a narrow revisit (`dadaia-release-definition` →
`dd-release-definition`, `dadaia-release-closure` → `dd-release-closure`, and
`drift-detection` merged whole into `dd-audit-project` with a lifecycle wrapper and an
evidence-agent dispatch section). Before this release, three of the seven stages had no
end-to-end protocol anywhere, two had their procedure stated twice in different files, and
the most-consulted artifact by implementers — the review/QA gate-cadence table — lived
inside a skill scoped to dispatchers.

The second half of the release is subtractive. Cycle-specific procedure was **dehydrated**
out of `public/data/DADAIA.md`, the always-on law that every agent reads in every session
and that is projected byte-identically to six locations: the `dadaia bugs append` command
block, the hotfix mechanics, the watch-CI paragraph and the §5 backlog paragraph were
replaced by the four surviving paragraphs the operator approved verbatim with the SPEC
(D-B), each ending in a one-line pointer at the skill that now owns the procedure. The
classification-relevant rows — §1's Arm A/B split, §2's dispatch table, §5 Releases, §5
Audits — were verified byte-identical afterwards, because an agent must still be able to
tell which arm and stage it is in from the law alone. Three on-demand skills
(`dadaia-cli`, `dadaia-gitflow`, `project-orchestration`) shed their duplicated blocks the
same way. The law came out 19 words shorter while **gaining** the ADR #14 single-source
`BACKLOG.md` doctrine and the ADR #15 operator-gated intake rule, which is the FR15
non-increase bar met with new doctrine on board rather than by cutting.

Two corrections rode the release because the work was impossible or unverifiable without
them. `ai-engineer`'s persona declared its rule write surface as
`dadaia_workspace/public/rules/**` — a directory that exists nowhere in the tree — in three
places; that was the permission basis on which the law source itself had to be edited, so
F-0 was fixed first (FR11, ratified as D-C). And the Codex D-CX-7 skill-reference check
gates on a prefix tuple containing the literal `"drift-detection"`: had the rename landed
without it, the check would have silently stopped validating that reference and **never**
validated a single `dd-` skill, degrading to a no-op for the entire new family with no
error line. One production-code touchpoint, one RED-first contract test that fails if the
gate ever goes inert again, and both golden fixtures regenerated from 21 to 25 skills. The
increment closed APPROVED on 69/69 acceptance ids, with a MEDIUM finding against the SPEC's
own grep wording — recorded below as a drift, not rounded into a pass.

## Tasks completed

Paired SHAs are `reserve / final`: the `chore(tasks): start <id>` reservation commit, then
the commit carrying the work and the `[-]` → `[x]` flip, per `dadaia-task-manager`. No
history was rewritten in this release, so every sha below resolves on `feature/v0.10.0` as
it stands.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-100-01 | [git] Commit the definition content on `feature/v0.10.0` (trio + `ACTIVE.md` → IMPLEMENTATION) | `bf684512` |
| T-100-02 | [git] Milestone (a): merge into `develop`, diff-based security review, push | merge `02ba1fcb` (pushed, CI green); marker flip `c1540af0` |
| T-100-03 | Baseline census — the FR15 denominator (`DADAIA.md` 2423 words / 315 lines; 21 skills, 27,653 words / 3,873 lines) | `d7e8d2a4` / `6673be87` |
| T-100-04 | `dd-backlog-definition` (new) — disposition vocabulary home, `BACKLOG.md` ACTIVE+LEDGER schema, operator-gated intake gate — 119 lines | `40ae9a34` / `db1fa568` |
| T-100-05 | `dd-release-definition` (rename + revisit) — sanitize step dehydrated to a reference, pick-time-priority blockquote — 109 lines | `fba8c043` / `34cadcae` |
| T-100-06 | `dd-release-implement` (new) + the E-3 gate-cadence table **moved** out of `project-orchestration` — 74 lines | `e9688315` / `1d056f4d` |
| T-100-07 | `dd-release-closure` (rename + revisit) — token table → reference; `## Backlog returns` → `## Intake candidates` — 210 lines | `6175a980` / `644f8051` |
| T-100-08 | `dd-audit-project` — full merge + rename of `drift-detection`, plus lifecycle wrapper and evidence-agent dispatch — 299 lines | `787abad1` / `c25a0b3a` |
| T-100-09 | `dd-bug-registration` (new) + `dadaia-cli` dehydrated — 65 lines | `86184ce2` / `3684e963` |
| T-100-10 | `dd-bug-fix` (new) + `dadaia-gitflow` dehydrated — 68 lines | `cfbe9a00` / `20959b43` |
| T-100-11 | Law dehydration at the source: C1/C3/C5/C6 replaced, C11 added; 2423 → 2404 words; C1/C3/C5/C6 verbatim-verified against SPEC FR9 | `11622236` / `ba0d7c68` |
| T-100-12 | F-0 persona-scope fix (FR11) + the rename ripple across 9 files (FR12) + the FR13(a) grants | `61bd3e9d` / `da4b58df` |
| T-100-13 | ADR #15 external surfaces I4–I8 (personas, orchestration, Codex harness skill) | `6be8da0f` / `38de4dd4` |
| — | Remediation, not a TASKS entry: 3 proxy-2 shingle overlaps deduplicated (3 → 0), 3 incomplete FR13(a) grants completed (9/9), 1 spec-reviewer residual — found by self-review **after** batch 3 (see `## Drifts › remediation-outside-the-batch-write-sets`) | `692d0012` |
| T-100-14 | Codex D-CX-7 prefix gate, its RED-first contract test, and the test goldens (21 → 25 skills); suite 2195/3/0 | `1e27dbd7` / `a11c5fb8` |
| T-100-15 | Re-projection, orphan sweep (9 stale files pruned across `.dadaia/agentic`, `.agents`, `.claude`), byte verification (28 + 6 SHA-256 identical) | `51e22a7d` / `f0f87e97` |
| T-100-16 | `qa-engineer` review of the increment (flat alpha close) — **APPROVED**, 69/69 acceptance ids | `42315a56` / `e35cc0c7` |
| T-100-17 | Memory update in CLOSURE phase — four atoms + `catalog.json` + `index.md` TOC | `b502da92` / `cb72a178` |
| T-100-18 | CLOSURE, dispositions, release archive, version bump | reserve `20abf265`-parented `chore(tasks): start T-100-18`; final `docs(T-100-18): close release v0.10.0` (sha assigned by the dispatcher at commit time) |
| T-100-19 | [git] Milestone (b): ship — code review incl. the operator's law-diff eyeball (A9.6), merge, security review, push, PR `develop` → `main` | Archives `[ ]` **by design** — the ship task cannot flip its own marker after T-100-18 moves the directory into FROZEN `specs/_archive/`. Third occurrence of the same flat-release canon gap (v0.8.0, v0.9.0, here); its completion evidence lives in the milestone-(b) merge commit, the two reviewer handoffs, the PR and CI. Not re-raised as a new intake candidate |

## Validations

V1–V15 are the PLAN §7 validation plan, one row each. Evidence is a figure independently
re-measured by `qa-engineer` in `ALPHA-1-QA.md`, a commit sha, or a captured command
output. Where a criterion was not fully met, the row says so rather than rounding.

| Description | Command | Evidence |
|-------------|---------|----------|
| V1 — Family exists; every per-skill line budget and the family total hold (A1.1, A1.2) | `wc -l dadaia_workspace/public/skills/dd-*/SKILL.md` | 7 directories, each `SKILL.md`'s `name:` matching its directory. Lines, alphabetical: `dd-audit-project` **299** (≤300) · `dd-backlog-definition` **119** (≤160) · `dd-bug-fix` **68** (≤130) · `dd-bug-registration` **65** (≤110) · `dd-release-closure` **210** (≤220) · `dd-release-definition` **109** (≤130) · `dd-release-implement` **74** (≤160). **Family total 944 ≤ 1210.** Every budget holds with margin; the tightest is `dd-audit-project` at 299/300, which absorbed `drift-detection` whole plus two new sections |
| V2 — No duplicated law text: zero non-exempt 15-word shingles (A1.3) | paragraph-scoped normalized 15-word shingle scan across the 7 family skills + `public/data/DADAIA.md`, `<=2`-line blockquotes exempted per FR1 proxy 2 | **ZERO overlaps across all pairs.** QA re-ran it with its own independently written script rather than the implementer's, confirming remediation commit `692d0012`'s 3 → 0 claim. QA also records a scanning artifact worth keeping: a naive whole-document (non-paragraph-scoped) variant reports one false positive where an 11-word shared clause bridges a blockquote→heading boundary through line-join concatenation — it disappears under per-paragraph shingling, which is the correct reading of "duplicated law text" |
| V3 — Listing tax: every family `description` ≤ 350 characters (A1.4) | frontmatter `description` length per family skill | 335 / 304 / 272 / 229 / 301 / 318 / 308 characters (audit-project, backlog-definition, bug-fix, bug-registration, release-closure, release-definition, release-implement). All ≤ 350 |
| V4 — Zero stale skill names (A12.1) | `grep -rn "dadaia-release-definition\|dadaia-release-closure\|drift-detection"` excluding `specs/_archive/**` and `CHANGELOG.md` | **Literal criterion not met — recorded as a drift, not as a pass.** See `## Drifts › literal-zero-hit-greps-were-under-scoped`. What *is* clean: all **10 rows** of SPEC FR12's "verified live reference set" table — every agent frontmatter and persona body, `dadaia-gitflow`, `dadaia-grill-me`, `dadaia-test-stewardship`, `project-orchestration`, `codex_assets.py`, `test_public_pipeline.py` and both golden fixtures — re-verified row by row by QA (A12.2, 10/10). The 9 residual files are historical ledgers/archives outside the SPEC's exclusion list, this release's own self-referential SPEC/PLAN/TASKS, the FR6-mandated provenance line, and the new test's own explanatory docstring. No functional reference is broken anywhere in the tree |
| V5 — Zero stale intake flow (A16.3) | `grep -rn "backlog/ideas.md\|backlog/candidates.md\|## Hotfixes pendentes" dadaia_workspace/public/` | **Exactly 1 hit:** `public/templates/release_hotfix.md.j2:16` — one of the dead hotfix templates SPEC §7 explicitly names as **not removed by this release** (operator ruling D4's retirement is a separate, named backlog item). Treated as clean per the SPEC's own text; every live surface is corrected. All 8 ADR #15 rows I1–I8 re-read and confirmed by QA (A16.2, 8/8) |
| V6 — Law fidelity (A9.1–A9.3) | diff of `public/data/DADAIA.md` against SPEC FR9's verbatim text; byte-identity check on C2 / C4 / §1 / §2 | C1, C3, C5 and C6 match the operator-approved surviving text **byte-for-byte modulo wrapping** (D-B fidelity check, verified by QA). C2 (§5 Releases) and C4 (§5 Audits) sit outside every diff hunk of `ba0d7c68` and are byte-identical; §1 (`:14-24`) and §2 (`:46-70`) untouched. C11 present in the §9 Skills row. `git log --oneline -- dadaia_workspace/public/data/DADAIA.md` confirms `ba0d7c68` is the law file's **only** touch in the entire release — no later task edited it again |
| V7 — Law net size (A15.2) | `wc -w dadaia_workspace/public/data/DADAIA.md` vs the T-100-03 baseline | **2423 → 2404 words, net −19.** The non-increase bar is met while the law *gained* the ADR #14 `BACKLOG.md` doctrine and the ADR #15 intake rule — the arithmetic came out negative without cutting a `KEEP` row, which is the outcome PLAN §4(b) required |
| V8 — D-CX-7 live for the family (A13.3) | `pytest tests/contract/test_codex_skill_ref_prefixes.py -v` | 2 passed. **RED observed first, for the real reason:** before the tuple change the test failed with `assert 0 == 1` / `assert [] == 1 item` — a projected Codex persona citing a non-existent `dd-` skill produced **no** ERROR line, because the prefix gate silently skipped the entire family. Module docstring declares `Intent: CONTRACT — v0.10.0 A13.3` at birth. `_CODEX_SKILL_REF_PREFIXES` now contains `"dd-"` and not `"drift-detection"`; the pre-existing `"memory-ctx"` entry was deliberately left alone (SPEC §4.8) |
| V9 — Skill set pinned (A13.4) | full `pytest -p no:cacheprovider -q`, incl. `EXPECTED_SKILLS` and both goldens | **2195 passed, 3 skipped, 0 failed** (90.05 s, QA's own re-run — identical to the T-100-14 implementer baseline, so nothing moved between implementation and review). `EXPECTED_SKILLS` equals the 25-name set and matches the 25 staged directories exactly (zero missing, zero extra); both `_golden/*.json` fixtures carry all 7 `dd-*` names with zero old-name residue |
| V10 — Projection chain (A14.1) | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | Exit 0, `[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution`; zero `[missing]`/`[drift]`/`ERROR` lines. The only non-`[ok]` lines are pre-existing `[foreign]` entries for unrelated consumer repos and the operator's own settings file, plus a standing `[info]` Codex trust-boundary note |
| V11 — No orphans (A14.2) | absence check across `.dadaia/agentic/skills/`, `.agents/skills/`, `.claude/skills/`, `.codex/`, `.kimi-code/` | Zero hits for all three old names, files **and** directories. T-100-15 pruned **9 orphaned files** explicitly; see `## Drifts › install-prunes-more-than-fr14-assumed` for what `install` turned out to do on its own |
| V12 — Byte identity across trees (A14.3) | `sha256sum` over source ↔ staging ↔ `.agents` ↔ `.claude` | **28/28 identical** (7 family skills × 4 trees). `DADAIA.md` additionally verified **6-way identical** (source ↔ `.dadaia/agentic/data/` ↔ workspace root ↔ `.claude/rules/` ↔ `.codex/` ↔ `.kimi-code/`) — the projection integrity that makes a 19-word law saving a saving in six places |
| V13 — Push preflight | `ruff format --check`; `ruff check`; `mypy --strict`; `lint-imports`; `dadaia ci preflight` | All clean: `mypy --strict` over **265 files**, import-linter **9/9 contracts kept**, preflight **PASS** (software-engineer report, T-100-14). This release adds no import, no I/O surface and no dependency, so purity was never at risk — it is verified rather than assumed |
| V14 — Token accounting (A15.1–A15.4) | `wc -w` before/after; baseline at `.dadaia/tmp/ai-engineer/20260815/T-100-03-baseline-census.md` | See `## FR15 token accounting` below. Baseline captured **before** the first content task (T-100-04), as A15.1 requires — the 2026-08-14 Part A figures were re-measured, not reused |
| V15 — Frontmatter grants (A13.1) | direct inspection of all 9 agents' frontmatter `skills:` lists | Every grant in SPEC FR13(a)'s table present, including all **9/9** `dd-bug-registration` grants. Three of those nine were missing at the end of batch 3 and were completed by remediation commit `692d0012` — recorded as a drift rather than folded silently into this row |
| — | A9.6 — the operator's pre-merge eyeball of the `public/data/DADAIA.md` diff (ADR #7/E-1 guardrail c) | **Not yet due, not a gap.** It is a milestone-(b) obligation discharged at T-100-19, alongside the `code-reviewer` six-axis pass. Per D-B it checks **fidelity only** against the SPEC's verbatim text — which V6 already reports clean — and is not a second wording review |

### FR15 token accounting

All figures `wc -w`, measured against the T-100-03 baseline and independently re-run by QA
at the review tip. The trade this release makes is deliberate: cost moves from the
always-on surface, paid by every agent in every session, to on-demand skills paid only by
the session actually running that stage.

| Surface | Before | After | Delta |
|---|---|---|---|
| `public/data/DADAIA.md` (always-on, every agent, every session) | 2423 | 2404 | **−19** |
| `public/data/AGENTS.md` (always-on root pointer) | 200 | 200 | 0 |
| `dadaia-cli` (on-demand, dehydrated) | 867 | 772 | −95 |
| `dadaia-gitflow` (on-demand, dehydrated) | 733 | 695 | −38 |
| `project-orchestration` (on-demand, dehydrated) | 1887 | 1574 | −313 |
| `dd-audit-project` (was `drift-detection`) | 1440 | 1751 | +311 |
| `dd-release-closure` (was `dadaia-release-closure`) | 1284 | 1294 | +10 |
| `dd-release-definition` (was `dadaia-release-definition`) | 893 | 814 | −79 |
| `dd-backlog-definition` (new) | 0 | 812 | +812 |
| `dd-release-implement` (new) | 0 | 627 | +627 |
| `dd-bug-registration` (new) | 0 | 420 | +420 |
| `dd-bug-fix` (new) | 0 | 493 | +493 |

**Always-on saving: −19 words**, ≈ **−25 tokens** at the design report's 1.33 tokens/word
ratio — per session, per agent, in six projected locations, and paid back on every dispatch
of all nine agents. `AGENTS.md` unchanged.

**On-demand growth, stated rather than hidden (A15.4):** the 7-family total is **6211
words** against the 3 renamed predecessors' 3617 — **+2594 net**, dominated by the four
brand-new skills (+2352) plus `dd-audit-project`'s +311 of lifecycle-wrapper and
evidence-dispatch content, offset by `dd-release-definition`'s −79 from the removed
sanitize step. The three dehydrated on-demand skills shed **446 words** in aggregate.

The honest reading of these numbers: the always-on saving is small in absolute terms, and
the release's real return is structural rather than arithmetic — three stages that had no
protocol now have one, four duplications are gone, and the gate-cadence table finally lives
where implementers look for it. The −19 words matter because they prove the law absorbed a
new doctrine without growing, which is the property that keeps the always-on file from
ratcheting upward one release at a time.

## Drifts

### literal-zero-hit-greps-were-under-scoped

**Description:** 2026-08-15, raised by QA as finding **QA-1 (MEDIUM)**. Acceptance criteria
A11.2 and A12.1 are written as literal zero-hit greps — A12.1: *"over the working tree,
excluding `specs/_archive/**` and `CHANGELOG.md`, returns zero hits"*; A11.2: *"outside
`specs/_archive/**` and this SPEC"*. Run exactly as written, neither returns zero. A12.1
returns hits in 9 files, in four categories: this release's own `SPEC.md` (28),
`TASKS.md` (11) and `PLAN.md` (3), which necessarily describe the rename they perform and
which satisfy the exclusion the moment this closure archives them; the append-only bug
ledgers `specs/bugs/bugs.jsonl` (2) and `specs/bugs/_archive/archive.jsonl` (3) plus two
`specs/backlog/_archive/` entries (3), all pre-existing historical content that is never
retroactively rewritten and that lives under archive paths the SPEC's `specs/_archive/**`
exclusion does not cover; the FR6-**mandated** provenance clause in `dd-audit-project`'s own
description ("full merge + rename of `drift-detection`"); and the new contract test's module
docstring explaining why the fix was needed. A11.2 is the same shape, smaller: synthetic
fixture data in a doctor unit test, the same historical-ledger class, this release's own
TASKS prose — and one genuine pre-existing residual at `ai-harness-codex/SKILL.md:99`.

**Resolution:** Reported as found. QA declined both available shortcuts — narrowing the grep
until it passes, and inventing a broader exclusion the SPEC never wrote — and instead
enumerated every residual with its category. I rule this a **SPEC-drafting gap, not an
implementation defect**, and the ruling is falsifiable rather than convenient: the SPEC
itself defines what "needed updating" means, in FR12's ten-row "verified live reference set"
table, and QA re-verified all ten rows clean independently. No agent frontmatter, no persona
body, no production code and no test golden carries a stale name; `dadaia public doctor`
exits 0. The corrected, honest form of the criterion — the wording a future SPEC should use
— is: *zero hits outside historical archive/ledger content and the release's own definition
documents*. The one live residual QA surfaced (`ai-harness-codex:99`) is genuinely
pre-existing and outside every task's declared write set, verified by `git show 38de4dd4`;
it is listed under `## Intake candidates` rather than fixed opportunistically here.

**Memory updates:** none — a criterion-wording defect in one release's SPEC is not current
product truth. The lesson belongs to the next SPEC's drafting, and is routed there as an
intake candidate.

### remediation-outside-the-batch-write-sets

**Description:** 2026-08-15. An unnumbered remediation commit, `692d0012`, was needed after
batch 3 (T-100-11/12/13) self-review: 3 proxy-2 shingle overlaps between family skills, 3 of
the 9 `dd-bug-registration` frontmatter grants still missing, and 1 residual flagged by
spec review. None of these were caught inside the task that created them, because the
release's write-set discipline is per-task and the defects are *cross-task*: a shingle
overlap exists between two files that two different tasks own, and a grant table is only
complete once the last agent persona is edited. Each batch's self-check ran against the
family members already written, exactly as TASKS' standing rule prescribes — which is
necessary but structurally cannot see a duplication introduced by a *later* sibling.

**Resolution:** Fixed at the root in one commit, with the outcomes verified independently
afterwards rather than asserted: QA re-ran a shingle scan written from scratch in its own
session and confirmed **0 overlaps across all pairs**, and re-read all nine agents'
frontmatter directly (not by grepping bodies) confirming **9/9** grants. The process cost is
recorded rather than smoothed: a per-file style bar with no linter (SPEC §4.6 declines to
build one) needs a whole-family check at the end of the family, not only an incremental
check inside each task — the ordering PLAN §3 chose made that end-check the reviewer's job,
and it worked, one commit later than ideal. Attribution debt is settled here by giving the
commit its own row in `## Tasks completed` rather than by rewriting history.

**Memory updates:** none — an intra-release sequencing artifact is not current product
truth.

### install-prunes-more-than-fr14-assumed

**Description:** 2026-08-15, found at T-100-15. SPEC FR14 states the orphan hazard as:
`stage()` rebuilds staging with an `rmtree` so staging self-heals, while `install` "copies
staged → projected and **prunes nothing**", leaving old skill directories as orphans in
every projected tree after a rename. Reality is narrower than that worst case: `install`
**does** auto-prune stale skill files under `.agents/` and `.claude/`. The residue that
actually needed explicit removal was 9 files, swept by T-100-15, not the untouched old
directory trees FR14 anticipated.

**Resolution:** No product change. The SPEC was over-cautious in a direction that costs
nothing — it made removal an acceptance criterion (A14.2) and a byte-verification an
acceptance criterion (A14.3), and both were discharged: zero old-name hits across all five
trees, 28/28 four-way byte-identical family skills, `DADAIA.md` 6-way identical. Recording
this drift is the point: the next release that renames a projected asset should verify
`install`'s actual pruning behaviour rather than inherit FR14's worst-case assumption, and
should equally not *rely* on the auto-prune, since the observed behaviour was measured on
one rename shape and never specified.

**Memory updates:** none. The atom `public-asset-distribution` already describes the
staging/projection contract and the doctor's three comparison passes; a measured nuance of
`install`'s pruning on one rename shape is not yet a stated contract, and writing it into
memory would state as product truth something no test pins. If a future release specifies
and tests the pruning behaviour, that is when it becomes an atom sentence.

### two-facts-with-no-section-5-row-left-out-of-memory

**Description:** 2026-08-15, an authoring judgement recorded so it is visible rather than
invisible. Two facts this release established are absent from every memory atom: (1) the
Codex D-CX-7 skill-reference gate now keys on the `dd-` prefix, so the check is live for
the whole family — the fix that prevents a silent no-op; and (2) `ai-engineer`'s declared
write surface is `public/data/*.md`, `public/scaffold/**/*AGENTS.md` and
`public/templates/*-AGENTS.md`, with `public/data/DADAIA.md` named as the law **source**
while its projections stay PROTECTED. Neither has a row in SPEC §5's memory table.

**Resolution:** Deliberately **not** written to memory, and deliberately flagged instead of
either being quietly added or quietly dropped. The test is whether an atom currently says
something *false* without the update: none does — no atom states the prefix tuple's
contents, and none states `ai-engineer`'s write allowlist. Memory is not a mirror of the
diff. Adding rows outside the approved §5 list at closure time would be a unilateral scope
expansion by the agent that also owns the file, which is exactly the move the CLOSURE-phase
memory-write authorization is narrow to prevent. If a later reader judges either fact to
belong in `agentic-entities` or `public-asset-distribution`, this drift is the pointer to
where it came from.

**Memory updates:** none, by decision — the decision itself is the record.

## Memory updates

All memory writes landed in the CLOSURE phase (`ACTIVE.md` `phase: CLOSURE` set before the
first write) and **before** this file, holding the finalization order memory → CLOSURE →
archive. Single commit: `cb72a178` (T-100-17). Every SPEC §5 row is discharged below, file
by file, including the two rows that resolved to "no change".

- `specs/memory/product/distribution/public-asset-distribution.md` — the "Universal skills
  have one canonical home and are never derived" section gains a paragraph naming the `dd-`
  family as the development cycle's on-demand protocol surface, distributed on the same
  universal path as `dadaia-gitflow` and `dadaia-test-stewardship`: all seven skills listed,
  one per stage, each the single operational home of its stage's protocol, with the standing
  rule that the always-on law carries the classification and points at the stage's skill
  while the procedure exists only in the skill.
- `specs/memory/product/agents/agentic-entities.md` — the universal-surface bullet records
  that the cycle's seven `dd-` skills are universal in exactly the registry's sense: one
  canonical `.agents/skills/` home, **no** `public/entities/registry.json` entry, no
  per-harness copy and no harness toggle — the derivation law governs derived per-harness
  entities, and these are not derived.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the `## Backlog` section is
  rewritten to current truth: the backlog is the operator's demand queue, curated by
  `project-manager` as the single source `specs/backlog/BACKLOG.md` with an `ACTIVE` section
  (one full-prose subsection per live candidate) and a `LEDGER` section (one line per closed
  item: slug · disposition · release-or-reason · date); intake is operator-gated, no agent
  materializes an entry, residuals are listed as intake candidates and compiled by the PM
  into an intake report the operator adjudicates, with the operator-ratified in-release
  deferral as the single pre-approved carve-out; curation is continuous with staleness and
  dedup scans; nothing is deleted — an item leaves `ACTIVE` only by gaining a LEDGER line,
  and a picked item leaves in the same commit that creates the release SPEC (purge-on-pick).
  The section names `dd-backlog-definition` as the one home of the entry schema, intake
  protocol and disposition vocabulary. It closes with the **honest pending-state paragraph**
  A10.3 requires: the doctrine is in the law and the skill, the physical backlog is **not**
  consolidated, `specs/backlog/` still holds per-entry Markdown files and the `dadaia
  backlog` verbs still read and write that model — consolidation is PM curation work,
  tooling reconciliation is a `software-engineer` follow-up, and neither weakens the intake
  gate. Frontmatter `tldr`/`summary` updated accordingly.
- `specs/memory/product/agents/agent-orchestration.md` — the ordered-lifecycle paragraph
  names the skill that owns each stage by reference rather than restating any of them:
  `dd-backlog-definition`, `dd-release-definition`, `dd-release-implement`,
  `dd-release-closure`, `dd-audit-project`, `dd-bug-registration`, `dd-bug-fix`. Frontmatter
  `tldr`/`summary` updated to state that each stage's protocol has one owning `dd-` skill
  the law points at.
- `specs/memory/product/catalog.json` — regenerated via
  `dadaia_workspace/public/scripts/generate-memory-catalog.py`, as SPEC §5 conditions on a
  touched atom's `tldr`/`summary` having changed: two did (`agent-orchestration`,
  `sdd-bug-backlog-governance`). No slug was added, removed or re-ranked.
- `specs/memory/product/index.md` — **changed, where SPEC §5 predicted no change.** The
  index's catalog table renders each atom's `tldr`, so regenerating the catalog propagated
  the two changed one-liners into the TOC. This is a generated-consistency ripple, not a
  feature-catalog change: no feature was added, removed or re-ranked, and the vision, users,
  capability-map and limits sections are untouched. Recorded here rather than left as an
  unexplained diff against the SPEC's expectation.
- `specs/memory/product/agents/agent-comms.md` — **no change**, as SPEC §5 anticipated. FR16
  introduces no new artifact class: the intake report is the existing handoff-first shape
  (JSON handoff with `next_handoff.agent: human` plus the HTML it points at), so the atom's
  handoff contract already describes it.
- `specs/memory/architecture.md` — **no change.** No layer boundary, port, module contract
  or dependency rule moved; FR13's production touchpoint edits one constant inside an
  existing module and adds one test.
- `specs/memory/tech-stack.md` — **no change:** no dependency, command or language version
  moved. This release is text plus one tuple entry.

No atom gained a `Changelog`, `History`, `Histórico` or `Versions` section, and none
narrates a past version. This release's history lives in this file and in the archived
release directory.

## Dispositions

This release picked **no bug and no audit**. `dadaia bugs status` reported **0 open audits**
and **2 open LOW bugs** at pick time; both bugs were left in the Arm B lane by explicit
operator direction — a bug fix is a `hotfix/{M.m.p}`, never release material (`DADAIA.md`
§1/§5), so leaving them open here is the law's outcome, not an omitted disposition. The
sweep below is therefore complete with one picked row.

**Purge-on-pick was performed by the PM at `be4d3064`**, before this closure. The pending
state SPEC §7 recorded at authoring time ("delegated and pending") is resolved: the live
entry file left the backlog, the provenance record is SPEC §7, and the ledger row is
retained forever per the never-delete law.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/20260814-dd-lifecycle-skills-family.md` | backlog | `DELIVERED — v0.10.0` | The entire release scope. FR1–FR16 delivered and QA-verified across **69/69** acceptance ids (`ALPHA-1-QA.md`); live entry purged at pick, commit `be4d3064`; provenance `SPEC.md` §7 |

Explicit non-flips, so a later reader does not read them as an incomplete sweep:

- `specs/backlog/codex-persona-law-context-dehydration.md` — **not absorbed, stays a
  candidate** (SPEC §4.2 + §6-D). Three reasons, unchanged at closure: it targets generated
  Codex TOMLs and four production Python modules — `software-engineer` surface, not
  `ai-engineer`'s; its own acceptance criterion (*"Codex is the only changed projection"*)
  becomes unsatisfiable if merged with a release that changes `.claude/` and `.agents/` by
  construction; and no grill ADR absorbed it. **Its numeric baseline is now invalidated by
  this release** — it pins a nine-TOML byte census and derives its 60%-reduction target from
  it, and v0.10.0 edited three personas that render into those TOMLs. The PM re-measures and
  rewrites the figures **after this ships**, before the entry is ever picked. Recorded here
  because a stale baseline discovered at pick time is a far more expensive surprise.
- `specs/backlog/bug-picked-ledger-event.md` — stays a candidate. Referenced **by slug** from
  `dd-bug-fix` §2 (A8.3), which documents today's advisory-presence signal only and invents
  no marker, lock or lease.
- `specs/backlog/retire-dead-hotfix-surface.md` — untouched. The dead
  `release_hotfix.md.j2` / `closure_hotfix.md.j2` templates and the `specs hotfix open` verb
  are **not** removed here (SPEC §7); this is why V5's single grep hit exists and is
  sanctioned.
- `specs/backlog/test-suite-remediation-stewardship.md`,
  `specs/backlog/changelog-version-axis-reconciliation.md` — untouched; neither was picked
  and neither is affected by this release.
- **No bug status was flipped and no `dadaia bugs append` event was emitted by the release
  scope.** The two open LOW bugs remain open, correctly, for their own hotfix lane.

**ADR #14 scope split, restated as A10.3 requires.** This release ships the **doctrine**
only: the §5 law amendment (FR10) and the entry schema, purge-on-pick rule and disposition
vocabulary in `dd-backlog-definition` (FR2). It does **not** deliver the physical
consolidation of the per-entry backlog files into `BACKLOG.md` (PM curation surface,
delegated per D-A), and it does **not** deliver the backlog tooling reconciliation — the
five `features/backlog/*` modules, `dadaia backlog new`, `backlog doctor`'s
`BL-SCHEMA`/`BL-STALE`, `SPEC-DOC-031`, the consumer scaffold README and the validation
recipe all still assume per-entry files and **keep working** against them. The doctrine
therefore outruns its tooling, deliberately and visibly, until the named follow-up release
ships. This paragraph is the CLOSURE repetition A10.3 demands, and the same statement is
written into the `sdd-bug-backlog-governance` atom as current product truth.

## Test dispositions

No demotion, no quarantine expiry and no SCAFFOLD expiry occurred. This release is
overwhelmingly prose; exactly one behavioral test exists in it, and it was written RED-first.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| demotion | none | none — no LARGE test was replaced, removed or demoted; the release added no e2e test | `ALPHA-1-QA.md` "Test stewardship checklist" |
| quarantine expiry | none | none — no quarantine marker added or expired | full-suite count unchanged at 2195/3/0 between T-100-14 and the QA re-run |
| SCAFFOLD expiry | none | none — the one new module, `tests/contract/test_codex_skill_ref_prefixes.py`, declares `Intent: CONTRACT — v0.10.0 A13.3` in its docstring at birth | QA read the docstring directly; RED failure (`assert 0 == 1`) independently re-confirmed |
| golden regeneration | — | `EXPECTED_SKILLS` and both `_golden/*.json` fixtures moved 21 → **25** skills, regenerated mechanically rather than hand-patched — zero missing, zero extra, zero old-name residue | `ALPHA-1-QA.md` A13.4 |

**Nothing was pruned, skipped or disabled to reach green.** The QA re-run's suite count is
byte-for-byte the implementer's reported baseline, which is what makes that claim checkable
rather than asserted.

## Intake candidates

Residuals discovered during this release, **listed** for the PM's operator-facing intake
report (ADR #15 / FR16). This closure creates **no** backlog entry and flips no backlog
status — that was the old `## Backlog returns` model this release itself retired, and this
is the first closure written under its replacement.

### To be adjudicated

No prior operator ruling covers these; the PM's next intake report presents each for
approval, rejection or discard.

- **QA-2 (LOW) — stale `public/rules/*.md` taxonomy row at `ai-harness-codex/SKILL.md:99`.**
  A table row describing dadaia's asset types still names an asset family that the law-file
  consolidation retired many releases ago. Pre-existing, genuinely live (unlike this
  release's other A11.2 residuals), and outside T-100-12's and T-100-13's declared write
  sets — `git show 38de4dd4` confirms T-100-13 touched only line 339 of that file. Not fixed
  opportunistically here precisely because "while I'm in the file" is how write-set
  discipline erodes.
- **QA-3 (LOW) — stray `</pre>` tag at `dd-release-closure/SKILL.md:168`,** inside a fenced
  ` ```mermaid ` block where a closing fence belongs. Confirmed pre-existing via
  `git show 644f8051^` — it predates this release's rename task, and FR5's declared scope was
  "content kept as-is" plus two named changes. **Worth the operator's attention as a
  candidate for a trivial pre-ship fix**, since it lives in a file this release ships and a
  one-character correction now avoids a follow-up round trip. Listed, not taken.
- **A12.1/A11.2 wording — a SPEC-drafting lesson, not a code change.** Future SPECs that
  state a "zero hits" grep criterion must scope their exclusions to the tree that actually
  exists: `specs/bugs/**` and `specs/backlog/_archive/**` are historical/append-only and are
  not covered by `specs/_archive/**`, and a release's own SPEC/PLAN/TASKS are necessarily
  self-referential until they archive. See `## Drifts ›
  literal-zero-hit-greps-were-under-scoped` for the corrected form of the criterion.

### Pre-approved intake

Operator-ratified during this release (in its SPEC or at approval) — already-approved
intake, not re-adjudicated by a later intake report.

- **The backlog tooling reconciliation follow-up release** (D-A, named at approval): the
  five `features/backlog/*` modules, `dadaia backlog new`, `backlog doctor`'s
  `BL-SCHEMA`/`BL-STALE`, `SPEC-DOC-031`, `public/scaffold/backlog/README.md` and the
  consumer validation recipe — `software-engineer` surface, explicitly out of this
  AI-surface release's scope (SPEC §4.5, §4.10).
- **The physical `BACKLOG.md` consolidation** (D-A): merging the current per-entry files
  plus `candidates.md` into the single-source ACTIVE + LEDGER document. PM curation surface;
  `product-engineer` does not curate the backlog.
- **F-1 — `dadaia-cli` is granted to no agent** (SPEC §4.7). Its description claims "all
  agents may use it" while it appears in no agent's frontmatter `skills:` list, so under
  frontmatter-scoped grants it is reachable only by the top-level session. Pre-existing and
  independent of this family.
- **The `memory-ctx` phantom prefix** (SPEC §4.8): `_CODEX_SKILL_REF_PREFIXES` names a skill
  that does not exist in `public/skills/`. FR13 deliberately changed only the two entries the
  rename required and left this one alone.
- **Rewrite of `codex-persona-law-context-dehydration`'s byte baseline** (SPEC §6-D): this
  release invalidated its nine-TOML census and the 60%-reduction target derived from it. The
  PM re-measures after ship, before the entry is picked.

## Version bump decision

**Decision: bump `pyproject.toml` `0.6.0` → `0.7.0` (minor) and add a `CHANGELOG.md` entry
under `[0.7.0]`.** Recorded here as **owed**; the dispatcher executes both, since
`product-engineer` has no shell.

1. **New capability, backward-compatible.** Seven lifecycle skills — four of them entirely
   new — ship inside the wheel: `public/**` assets are packaged, so a wheel built from this
   tree hands a consumer a protocol surface the previous one did not have. Under the
   package's `0.x` scheme, added capability with nothing removed and nothing broken is a
   minor.
2. **The always-on law changed for every consumer.** `public/data/DADAIA.md` is projected
   into every instantiated workspace; this release amends §5's backlog doctrine and §6's
   registration paragraph. That is a behavioural change in what every downstream agent
   reads, not a documentation touch-up, and it should not arrive as a patch.
3. **Not a patch, because this is not a hotfix.** Law §5 binds PATCH-with-CHANGELOG to a
   hotfix merge; this is a feature release closing at milestone (b), and minting a PATCH
   would misfile a capability as a fix.
4. **The two version axes stay distinct.** `v0.10.0` is the SDD release identity; `0.7.0` is
   the package version (ADR-2, `specs/memory/product/distribution/pypi-distribution.md`).
   Neither is renumbered to chase the other.

The `[0.7.0]` entry should name the seven-skill family, the three renames (so a consumer
whose own notes cite `drift-detection`, `dadaia-release-definition` or
`dadaia-release-closure` can find them), the law amendment, and the D-CX-7 prefix fix. The
pre-existing CHANGELOG version-axis incoherence is already tracked as a live backlog entry
and is **not** re-raised here; write the entry in the file's current shape rather than using
it as an occasion to reconcile the axes.

## Archive decision

**MOVE** — `specs/releases/v0.10.0/` moves to `specs/_archive/releases/v0.10.0/` via
`git mv`, executed by the dispatcher, in the same commit that carries this file. `ACTIVE.md`
is set to `release: none` / `phase: none`: no release follows immediately, and the next pick
is the PM's. At that pick the queue is bugs-and-audits-first by law — 0 open audits, 2 open
LOW bugs in the Arm B lane — with the first ADR #15 intake round (the 8 technical residuals
from the post-v0.9.0 materialization, plus this closure's candidates) due before fresh
backlog is picked.

The archive move also resolves the largest category of the A12.1 residuals on its own: this
release's SPEC, PLAN and TASKS stop being working-tree files and become archived history the
criterion's own exclusion covers.

After the move, nothing under `specs/_archive/` is edited again — including T-100-19's `[ ]`
marker, which archives open by design (see `## Tasks completed`). This document is a **new
blob** wherever it lands and is scanned by the v0.9.0 push-range denylist gate like any other
authored file; every path cited here is workspace-relative and no foreign context name,
hostname, IP, email or absolute local path was written into it.
