# Audit 20261022-bug-history-and-single-source

A three-pillar audit of every bug registered since rc-15 was defined. It adds a single-source-of-truth pass over all code and text.

- **Timestamp:** 2026-10-22T03:00Z.
- **Window:** the operator chose it: every ledger record with `ts` ≥ 2026-10-13T15:04:49Z (the rc-15 `defined` milestone, `71eb1a091`), read at `feature/0.5.0` @ `6009dabc2`. That is 172 records: 163 resolved, 5 open, 4 superseded.
- **Origin:** the operator, 2026-10-21. They suspended the 0.5.0 promotion and ordered this audit: "full audit on all the bugs after rc15 … incidence, how many of them were reviewed, rebuilt the solution, when they appear … the fixes applied, what is the quality … if the bugs once fixed repeat … review if our layout in job 1 handles previous bugs … I cannot trust about deploying this version". They also asked for a duplication audit: "mapping places where we have repeated code or text … we need a unique source of truth". And for a definition of slop.
- **Agents:**
  - Seven read-only `dd-code-reviewer` runs, audit lens, none writing a verdict: bug batches A (worktree/gitflow, 53 bugs), B (ledger/release/verdict, 38), C (CLI/init/gate/core, 51) and D (tests/CI/export/evals, 30); one process audit; one text single-source audit; one code single-source audit.
  - The main thread computed the per-bug mechanical facts (`facts.py`: ledger + git) and wrote this record from the seven reports.
- **Method:** every claim cites a `path:line`, a sha, or a command and its result. Each RED test was run at the pin on a `git archive` copy. Revert checks covered every fix rated a symptom patch or bolt-on, and at least one in four of the rest. Divergence repros ran on scratch copies with the live root fenced.
- **Findings:** 56 in `FINDINGS.jsonl`: 33 HIGH, 21 MEDIUM, 2 LOW.
- **Not established:** reviewer verdicts for rc-15..rc-19 (reaped); Windows partitions (no Windows host); the detection source of 13 bugs (handoffs reaped). The definition-phase matches are file-level, so their counts are upper bounds.

## 1. Pillar 1 — bugs

### 1.1 Where the 172 bugs came from (F001)

| origin | n | detected by | n |
|---|---|---|---|
| fix-induced | 58 | implementer | 45 |
| feature-induced (an rc task) | 50 | CI after a green merge | 33 |
| latent, no test covered it | 23 | reviewer | 31 |
| test or fixture defect | 16 | audit | 26 |
| platform-only | 12 | main thread | 20 |
| law or doc defect | 7 | operator | 7 |
| not a bug in hindsight | 6 | evals | 3 |

108 bugs came from a change that had already passed the APPROVED gate.

### 1.2 Fix quality, rewrites, repeats (F002–F004, F010–F012)

- **Fix class:** structural 87, symptom patch 25, text-only 24, bolt-on 17, deletion 10, none or open 8.
- **Fix rounds:** 0 rounds 38, 1 round 47, 2–3 rounds 59, 4 or more 25.
- **Repeats:** about 110 bugs saw the same symptom or surface come back. Of those, 43 were the same root cause recurring, or a defect the fix itself bred.
- **Quality at HEAD:** mean 5.9/10, and 58 bugs score 5 or below.
- **Still in HEAD:** 43 bolt-ons or symptom patches (the batch reports' worklists). There are 59 test gaps, and 42 units carry two or more window bugs.
- **RED tests:** every existing RED passes at the pin. 39 resolved fixes have no `test(<id>)` commit, and 28 have no id-line commit at all. Two REDs are not red on revert; one of them has been vacuous since `e2830acf2` (F011).
- **Chains of bugs behind bugs:**
  - the check relay: six REBUILDs in about 30 h;
  - `worktree-sync-orphans`: four children, one a CRITICAL Stall;
  - `denylist-scan`: three children;
  - the verdict writer: three text-rule versions, then two lexer bugs;
  - `671587164`: swept no callers, leaving six nested-label sites (F015).

### 1.3 Does the definition phase use bug history? (F005, F006)

No. It records bug history but does not act on it:

- The history slice reads `fix_files`, which 1022 of 1094 resolved records lack.
- The "≥ 2 bugs" trigger lists 399 files as rebuild-due.
- 30 of the 54 KEEP rows that name a file saw a later bug on that file. So did 30 of the 37 REBUILD rows.
- `_worktree_end.py` was judged REBUILD in six candidates and kept breaking. Each REBUILD reworked the last fix, not the unit.
- Rc-22's own bug work bypassed its as-is review as one-id hotfix lanes.

### 1.4 What review, tests and evals are worth (F009, F026, F028)

- **Review:** 23 of 43 lanes needed a REJECTED round. Of the 20 bugs reviewers reported, at least 15 escaped an earlier review. A sibling sweep is asked for only on re-review (`dd-code-review` SKILL.md:62).
- **Tests:** `verify:` runs 1577 of 5364 tests (29%, measured 74.3 s). 33 bugs went red only in CI after a green merge.
- **Evals:** they found 3 of 172 bugs. A stub passes T3, and k=3 with binary reward gives a 50% pass chance to a p=0.5 agent.

### 1.5 Single source of truth — code (F030–F040)

- **Scale:** 35 questions are answered by more than one unit, and 17 answer differently today. Every divergence has a scratch repro.
- **Package versus kernel:** ADR 0246 holds wherever the kernel owns the function. Every duplicate is either a fact the kernel never got a function for, or a reader bypassing the file's owning skill.
- **Two recurrences:** `privacy-denylist-has-two-loaders` and `append-crashes-on-the-event-shaped-archive` were resolved, yet the same class is live again.

### 1.6 The nine forensic metrics (baseline: 20260930-structural-convergence, `git show ce035219c^`)

| # | Metric | Now | Baseline | Target |
|---|---|---|---|---|
| 1 | Registrations per reporter | sr 122, main 27, reviewer 20, pe 2, jr 1 | unmeasurable | — |
| 2 | Complete resolutions (id-line commit reachable) | 135/163 (83%) | 189/189 presence only | 100% verified |
| 3 | Fix shape neg/(neu+pos) | 0.17 (20/25/90) | 1.70 | ≥ 1.5 |
| 4 | Same-surface re-bug 3d / 14d | 79% / 82% (14d censored) | 71% / 82% | ≤ 30% / ≤ 50% |
| 5 | Hand-kept-list touches | 4% (10/283) | 36% | ≤ 10% |
| 6 | Test-layer bug share | 15.1% (26/172) | 6.3% | ≤ 10% |
| 7 | Scanner-vs-prose recurrence | 0 | 3 | 0 |
| 8 | Sweep closures as resolved | 43 | 0 | 0 |
| 9 | REBUILD share (caused_by ≠ none) | 75/132 (57%) | not defined | 100% (specs/bugs/AGENTS.md:26) |

### 1.7 The five structural causes, ranked by bugs explained

1. **Fix at the ticket's site now, REBUILD a candidate later** (specs/bugs/AGENTS.md:22, :27, against :26). This explains 58 fix-induced bugs and about 104 solutions redone.
2. **Review approves without a first-pass sweep of the fixed pattern, without platform proof, and without a growth check.** This explains 50 feature-induced bugs and 12 platform-only bugs; 23 of 43 lanes needed rework.
3. **The green signal is partial.** `verify:` runs 29% of the suite; 33 bugs were found by CI after a green merge.
4. **The history slice is blind and the trigger is saturated.** The slice reads `fix_files`, missing on 93% of records; the trigger lists 399 files as rebuild-due.
5. **History rewrites orphan stored shas.** 45 `fix_sha` values are unreachable, and 5 of 14 milestones.

Beside the five causes: the text single-source pass (§2.2) traces 39 ledger bugs to restated law, doc or memory text.

## 2. Pillar 2 — specs

### 2.1 Canon and shapes (F051)

- 63 of 1734 window commits break the `dd-gitflow-default` §3a table. One of them is the define commit `995ac1256`, which carries 127 files of code and tests.
- SPEC/PLAN files were edited 27 times after approval.
- 5 of 14 window milestone shas are unreachable from the pin.
- `bugs.py check` and `release.py check` exit 0. They cannot see the 45 unreachable `fix_sha` values or the 5 uncited resolved records.
- 0 immutable-core edits across 381 ledger commits.

### 2.2 Single source of truth — text (F041–F050)

- **Scale:** 92 rules or facts are written in 499 places, and 32 disagree today.
  - By class: 62 unguarded restatements, 18 hand-kept lists, 7 guarded projections, 5 pointers.
- **Fixed bugs coming back:** four of today's divergences are bugs that were already fixed. Each fix rewrote the copies it found and kept them as copies.
- **Guards that hold every copy equal:** FIXED-1/2, TREE-5 with shipped-hashes, `memory.py check`, the rendered registry tables with public doctor, and the cli.md digest.
- **What no check holds equal:** atom content, doc rule text, registry prose, the CONTEXT-MAP §1 table, the root map's copy of gate code lists, counts in prose, and § citations in code.

### 2.3 The definition of slop (F052)

The law states slop as "what passes the deletion test without loss" (SLOP.md:4). The forms this audit measured fall outside that definition:
- unverified claims;
- symptom fits;
- bolt-ons;
- dishonest labels;
- tests that cannot fail;
- restated facts;
- evals tuned until they pass.

The remediation release owns the amendment.

## 3. Pillar 3 — memory (F053–F056)

- All 22 P-NN principles pass their `Measured by:` check.
- Three atom claims are false against the code:
  - `workspace-init.md:27`;
  - `harness-claude-code.md:25` and `sdd-gate-v3.md:26` (the matcher without Bash);
  - `ARCHITECTURE.md:112`.
- The `capabilities` atom changed in the window and was never reviewed. 20 atoms have changed sources since the last memory pass.
- Nine of the 32 text divergences sit in memory atoms. MEM-DRIFT-2 checks only that cited verbs and paths exist.

## 4. Lifecycle

- One remediation release dispositions every finding (`specs/audits/AGENTS.md` §2).
- Close with `audit.py close specs/audits/20261022-bug-history-and-single-source --sha <window-end>` once no finding is `open`.
