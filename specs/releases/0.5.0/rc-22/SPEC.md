# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-21
**Origin:** bugs:init-no-terminal-fix-line-nests-one-act-label-inside-another,mcp-on-main-is-vulnerable-to-session-exhaustion,verdict-act-gate-lexer-lets-an-ampersand-redirection-or-a-midword-hash-hide-the-writer,verdict-act-gate-lexer-misses-the-module-name-attached-to-dash-m,merge-accepts-a-verdict-written-by-the-merger,t3-grader-requires-an-active-backlog-entry,init-over-a-folder-with-a-venv-fix-line-names-another-folder,merge-of-a-gone-tree-with-its-parent-gone-prints-a-generic-fix-line,reconcile-rollback-advice-is-prose-not-a-fix-line,code-breaks-the-constitution-complexity-and-import-cycle-law,stats-counts-audit-commits-as-non-block-work-after-closure,verdict-act-gate-regex-misses-spellings-and-refuses-reads,stats-reads-closure-files-by-whitespace-split-with-renames,reconcile-service-calls-act-through-an-attribute,init-fix-line-text-breaks-two-fix-line-contract-tests,merge-of-a-path-with-no-tree-and-no-branch-claims-merged; findings:20261022-bug-history-and-single-source-F001,20261022-bug-history-and-single-source-F002,20261022-bug-history-and-single-source-F003,20261022-bug-history-and-single-source-F004,20261022-bug-history-and-single-source-F005,20261022-bug-history-and-single-source-F006,20261022-bug-history-and-single-source-F007,20261022-bug-history-and-single-source-F008,20261022-bug-history-and-single-source-F009,20261022-bug-history-and-single-source-F010,20261022-bug-history-and-single-source-F011,20261022-bug-history-and-single-source-F012,20261022-bug-history-and-single-source-F013,20261022-bug-history-and-single-source-F014,20261022-bug-history-and-single-source-F015,20261022-bug-history-and-single-source-F016,20261022-bug-history-and-single-source-F017,20261022-bug-history-and-single-source-F018,20261022-bug-history-and-single-source-F019,20261022-bug-history-and-single-source-F020,20261022-bug-history-and-single-source-F021,20261022-bug-history-and-single-source-F022,20261022-bug-history-and-single-source-F023,20261022-bug-history-and-single-source-F024,20261022-bug-history-and-single-source-F025,20261022-bug-history-and-single-source-F026,20261022-bug-history-and-single-source-F027,20261022-bug-history-and-single-source-F028,20261022-bug-history-and-single-source-F029,20261022-bug-history-and-single-source-F030,20261022-bug-history-and-single-source-F031,20261022-bug-history-and-single-source-F032,20261022-bug-history-and-single-source-F033,20261022-bug-history-and-single-source-F034,20261022-bug-history-and-single-source-F035,20261022-bug-history-and-single-source-F036,20261022-bug-history-and-single-source-F037,20261022-bug-history-and-single-source-F038,20261022-bug-history-and-single-source-F039,20261022-bug-history-and-single-source-F040,20261022-bug-history-and-single-source-F041,20261022-bug-history-and-single-source-F042,20261022-bug-history-and-single-source-F043,20261022-bug-history-and-single-source-F044,20261022-bug-history-and-single-source-F045,20261022-bug-history-and-single-source-F046,20261022-bug-history-and-single-source-F047,20261022-bug-history-and-single-source-F048,20261022-bug-history-and-single-source-F049,20261022-bug-history-and-single-source-F050,20261022-bug-history-and-single-source-F051,20261022-bug-history-and-single-source-F052,20261022-bug-history-and-single-source-F053,20261022-bug-history-and-single-source-F054,20261022-bug-history-and-single-source-F055,20261022-bug-history-and-single-source-F056

---

## Bug window review

**Window:** every record closed after rc-21's birth (2026-10-20T15:14:19Z, `_RELEASE.json` log), read in `BUGS.jsonl` and `_archive/bugs_histo.jsonl` at `aa4c77ac0`: 13 resolved, 1 superseded. Each fix is found by its id line (`git log -E --grep '^(fix|refactor)\(bugs\): …<id>'`). The verdict and its evidence are the audit's per-bug judgement (`20261022-bug-history-and-single-source`, batches A–D at `6009dabc2`); this table does not re-audit. `F<nnn>` below is `20261022-bug-history-and-single-source-F<nnn>`.

| fix (ids) | newest fix commit | audit class, quality | verdict | where |
|---|---|---|---|---|
| t3-instruction-omits-backlog-demand | `7c6a13c59` | text-only, 5 | KEEP the instruction (main-thread ruling "KEEP the instruction, its text-asserting test goes to 0.6.0 intake"); the grader is the REBUILD target | FR13 |
| t3-grader-requires-an-active-backlog-entry | `5fe06d62f` | structural, 4: a bare `release.py new` stub passes | REBUILD | FR13 (F026) |
| merge-accepts-a-verdict-written-by-the-merger, verdict-act-gate-regex-misses-spellings-and-refuses-reads | `356da1cda`, `2632edd92` | symptom patch, 4 and 3: one command spelling judged | REBUILD `gate_policy.verdict_act` | FR7 (F016) |
| init-over-a-folder-with-a-venv-fix-line-names-another-folder, init-fix-line-text-breaks-two-fix-line-contract-tests | `c3bd83228`, `bd867f57f` | bolt-on (`render=` switch), 4; text-only with an allow-list row, 5; REBUILD label overclaimed | REBUILD fix-line production | FR8 (F015) |
| merge-of-a-gone-tree-with-its-parent-gone-prints-a-generic-fix-line, merge-of-a-path-with-no-tree-and-no-branch-claims-merged, merge-of-a-never-opened-tree-claims-merged (superseded) | `cac2ec646`, `13f7f79a9`, — | structural, 7, but `caused_by: none` is wrong; text-only after the pin; no fix | REBUILD the head of `merge` | FR6 (F013) |
| reconcile-rollback-advice-is-prose-not-a-fix-line, reconcile-service-calls-act-through-an-attribute | `2ea8f2c4f`, `76183f983` | structural, 7, residual special case and a fix that misnames a cause; a rename labelled REBUILD, 6 | REBUILD the reconcile result | FR11 |
| code-breaks-the-constitution-complexity-and-import-cycle-law | `a53675d24` (7 commits) | structural, 6, net +114 | KEEP | — |
| stats-counts-audit-commits-as-non-block-work-after-closure, stats-reads-closure-files-by-whitespace-split-with-renames | `102d7ca9a`, `94534a576` | bolt-on, then a deletion, 8 | KEEP the one reader; the stored-sha read is REBUILD | FR10 (F008) |

**Overfitting check:** `7c6a13c59` hands the agent the work the grader needs, and T3's grader was loosened twice after a 0/3 (F026). `3cfe9443e` added an allow-list row to a guard. No fix in the window changed an assert. Three `caused_by` values are wrong (`t3-grader…`, `merge-of-a-gone-tree…`, `stats-counts…`); F029 owns that class.

## 1. Problem

The operator's words:

- 2026-10-21, the suspension (`AUDIT.md` Origin): "full audit on all the bugs after rc15 … I cannot trust about deploying this version"; "mapping places where we have repeated code or text … we need a unique source of truth"; and a definition of slop.
- Grill 2026-10-22 (handoff `2026-10-22T064642Z-main-thread-grill-remediation`):
  - R1: "Reescopar o rc-22 (Recommended)".
  - R2: "Definir em SLOP.md, casa única (Recommended)".
  - R3: "As 5, numa ADR só (Recommended)".
  - R4: "Medido + re-auditoria (Recommended)".
  - R5: "Corrigir os graders (Recommended)".
  - Summary: "Confirmo, segue (Recommended)".
- As-is rulings 2026-10-22 (handoff `2026-10-22T072837Z-main-thread-asis-rulings`; the ten questions ruled by law are its `findings`):
  - ADR 0280: "Aceito a ADR 0280 (Recommended)".
  - F047: "Pode trocar pelo ponteiro (Recommended)".
  - Q1: "Teste de token (Recommended)".
  - Q3: "Ordeno (a)–(d) (Recommended)".
  - Q5: "Ler, sem reescrever (Recommended)".
  - Q13: "Emendar (Recommended)".

The gap is the audit: 56 findings, its five structural causes (`AUDIT.md` §1.7) and its two single-source passes (§1.5, §2.2). This SPEC cites them by id and never restates them.

## 2. Measurable goals (the exit, R4)

| # | goal | target | source |
|---|---|---|---|
| 1 | audit findings | 56 of 56 dispositioned; the audit closed | `audit.py check`, `audits_histo.jsonl` |
| 2 | divergent duplicates | text 0 (baseline 32), code 0 (baseline 17) | the re-audit on the new E (FR15) |
| 3 | bolt-ons and symptom patches in HEAD | 0 (baseline 43) | the re-audit |
| 4 | fix-induced bugs in the final round | 0 | the re-audit, origin column |
| 5 | REBUILD share (PILLAR-BUGS metric 9) for records registered after the ADR | 100% (baseline 57%) | the re-audit |
| 6 | full suite | every job of the existing CI green at E | the draft promote PR's CI run (AC15.4) |
| 7 | agentic scorecard | every cell >= 9 from both judges at the frozen tip | `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/` |
| 8 | evals on E, fixed graders | T1 3/3, T2 >= 2/3, T3 >= 2/3, `compare.py` prints `non-blocking`; Codex T1–T3 at k=3 as readout | `eval.yml` job summary; the local harbor run |
| 9 | the operator's validation round | the operator's words, logged | a `_RELEASE.json` note |
| 10 | E is the evaluated tree | `git diff --name-only E..<PR head>` lists only `specs/releases/0.5.0/_RELEASE.json` | git |

## 3. Non-goals (0.6.0)

- The CI Codex lane; graded rewards inside the graders (R5 keeps k=3 binary).
- Any change to a `verify:` line or a merge check, and any new gate. R3's checks are review criteria (root map §1 gate law).
- Re-registering the auditors' new defects as bugs: each stays one finding (grill handoff, finding 1).
- The T3 instruction's text-asserting test (ruled to 0.6.0 intake; a test leaves only on the operator's order).

## 4. Requirements

**Wave ranking** (grill summary). Each wave opens when the previous one has merged:

1. I: law. FR1 and FR2.
2. II: text. FR3.
3. III: code duplicates. FR4.
4. IV: REBUILD per unit. FR5–FR11.
5. V: tests. FR12.
6. VI: eval graders. FR13.
7. Then FR14 (scorecard), the closure, and FR15 (exit and promote).

The PLAN carries the waves' rows:

- PLAN §1 holds one row per audit unit (42) and per still-in-HEAD item (43), plus one row per row of the two deletion plans (29 text, 18 code). PLAN §1 is their durable home (G1).
- The PLAN caps parallel agents at 4 (summary).
- The held lanes `wt-hotfix-init-no-terminal-…` and `wt-hotfix-verdict-act-gate-lexer-…` do not merge. Their RED tests are reused by FR7 and FR8 (summary).

**Delivered, no task.** These lanes merged and resolved before the re-scope, and they stay delivered:

- The seven original lanes: `merge-accepts-…`, `t3-grader-…`, `init-over-a-folder-…`, `merge-of-a-gone-tree-…`, `reconcile-rollback-…`, `code-breaks-the-constitution-…`, `stats-counts-…`.
- Their five children: `verdict-act-gate-regex-…`, `stats-reads-closure-…`, `reconcile-service-…`, `init-fix-line-text-…`, `merge-of-a-path-…`.
- ADR 0279 (accepted).

The fixes the window review rates REBUILD are re-worked by the FRs named in its table.

### FR1 — the process ADR in law (R3; F001–F007, F009, F010, F027, F028, F051)

- AC1.1 ADR 0280 is accepted (`e2097af15`), before any wave II task opens. Test: none; `doctor` `LEDGER-ADR-SCHEMA`.
- AC1.2 Each of its five clauses lands in one law home, and every other copy of that rule becomes a pointer. The homes: the bugs law §2, `dd-code-review` §4–§4a, `dd-bug-resolution/LINEAGE.md`, `dd-release-definition` §1–§2, and `RELEASE-EVENTS.md`. The deferral line `specs/bugs/AGENTS.md:27` goes. Test: none (law text; the scorecard judges it); FR5 and FR10 own the code halves.
- AC1.3 F027 and F028 are dispositioned with ADR 0279 and AC1.2 as the reason. F051 is the history of the shapes AC1.2 now enforces at review. Test: none; `audit.py disposition`.

### FR2 — slop has one home (R2; F052)

- AC2.1 `SLOP.md` states the definition R2 words: the deletion test plus the evidence test, and the four new signals. Test: none (law text).
- AC2.2 No other law, skill or persona file defines slop. Each one points to `SLOP.md`; `git grep -n` of a second definition prints nothing. Test: none; the grep, at review.

### FR3 — one owner per fact, text (F041–F050)

- AC3.1 Every text deletion-plan row in PLAN §1 keeps its owner. Each other copy is deleted or becomes a pointer (`<owner> §n`, `<script> --help`). Test: none (text); the existing projection guards stay green.
- AC3.2 Every divergence F042–F049 names now reads as its owner does. Test: none; the re-audit's text pass.
- AC3.3 `specs/constitution.md:25,29` (F047) points the harness roster at `dadaia_workspace/core/harness_registry.py`, a wave II task by the operator's F047 answer. Test: none.
- AC3.4 F050 is resolved by AC3.1, because a pointer leaves nothing to hold equal. No guard is added. Test: none.

### FR4 — one owner per question, code (F030–F040)

- AC4.1 Every code deletion-plan item in PLAN §1 ends with one owner. A missing kernel function is added beside its kernel peers, the losing unit is deleted, and its callers call the owner (ADR 0246). Test: unit, the owner's contract test file.
- AC4.2 Each divergence repro (F031–F040 and the rest of F030's 17) becomes a row at the owner's contract test, RED before the merge and green after. Test: unit.
- AC4.3 No guard, gate or allow-list is added; each item's net source lines are <= 0, or the reviewer accepts the stated reason. Test: none; review.

### FR5 — REBUILD: the bug ledger kernel (F005, F006, F007, F018, F019, F020, F029, F045)

- AC5.1 A unit's history is the id-line git query. Nothing reads `fix_files` for history. One REBUILD-due decider in `bugs.py` (`append` and `stats` agree) says due on a child after the unit's last REBUILD. Test: unit (`test_bugs.py`).
- AC5.2 The 124 legacy event lines of `_archive/bugs_histo.jsonl` stay untouched (Q5). One reader recognises the legacy shape from the line itself, and the shape-picking flag is deleted. `resolve` refuses an ambiguous bare task id in `caused_by` and its fix line names the candidate-qualified form; one grammar (Q11). `main_checkout` has no sentinel value. Test: unit.

### FR6 — REBUILD: worktree merge and its refusals (F013, F017; batch A units 1, 2, 5, 6, 11)

- AC6.1 `merge` reads from git whether a branch is already merged. A missing tree or branch is never success, and a never-opened path refuses with one fix line. Test: unit (`test__worktree_end__removal.py`).
- AC6.2 An rc merge runs its ledger checks from the instance's copy only, never a tree-tracked script (Q2). Test: unit.
- AC6.4 The built-in test-path fallback of the RED separation stays, under one rule; a user repo is never required to declare `tests:` (Q2). Test: unit.
- AC6.3 Every `dd-gitflow-default` refusal prints a fix line that clears it, the catch-all `worktree.py` GitError line included. FR12's census proves it. Test: unit.

### FR7 — REBUILD: the verdict-writer gate (F016; open bugs `verdict-act-gate-lexer-lets-…`, `verdict-act-gate-lexer-misses-…`)

- AC7.1 On a harness whose registry row names a subagent key, a Bash command from a non-reviewer whose text holds `verdict.py` (or `-m verdict`) and `--verdict`, in any shell form, is refused (Q1). The lexer is deleted. The root map §3 states the residual: a read-only mention is refused too. Test: unit (`test_gate_policy.py`, F016's probe set, the held lane's REDs).
- AC7.2 ADR 0279's residual on harnesses with no key is unchanged. Both open records resolve with a `refactor(bugs)` line. Test: none; `bugs.py check`.

### FR8 — REBUILD: fix-line production (F015, F042 code half; open bug `init-no-terminal-fix-line-nests-one-act-label-inside-another`)

- AC8.1 No act sentence holds a second label: all six F015 sites, swept by the AST walk of every `act()` call. Test: unit (`test_cli_line__fix_line_contract.py`).
- AC8.2 `InitPlan.command`'s `render=` switch is deleted. Init's foreign-tree fix line keeps the operator's Q11 text. Test: unit (init refusal tests).

### FR9 — REBUILD: chokepoints and the gate (batch C units: ref gate, `gate_policy` scope, `workspace_layout`)

- AC9.1 Each unit's PLAN §1 row is rebuilt to one decider per question, with no special case kept for a test value. Test: unit, each unit's contract file.

### FR10 — REBUILD: release state, stats and the fold (F008; R3 clause 5)

- AC10.1 No milestone, memory-window bound or stats input is a stored sha that a rewrite can orphan: `release.py` stops writing the milestone shas, and the schema no longer requires `sha` (Q6). A missing closure commit is a refusal, never a metric of 0. Test: unit (`test_release__release_script.py`, `test_verdict.py`).
- AC10.3 The 5 uncited and 28 id-line-less historic bug records clear through ADR 0278's one `bugs.py archive` act; no baseline list (Q6). Test: none; `bugs.py check`.
- AC10.2 The fold's rewriting remedy, `ci push-gate-check --rewrite-from`, is deleted with its fix line. Test: unit (the push-gate refusal's fix-line row).

### FR11 — REBUILD: the remaining units (F021, F025; batch C reconcile, template history; batch D export, guards, version label, Windows timing)

- AC11.1 Each remaining unit with `addressed` no or partly, and each still-in-HEAD item no other FR names, gets its PLAN §1 REBUILD or DELETE row, and the row lands. Test: unit, per row.
- AC11.2 The template-history row is REBUILT to one normalised digest, gated by a script that recomputes every published digest from git. If any published digest fails to recompute, the row is KEEP and its finding is dispositioned with that measured reason (Q9). Test: unit; the recompute script's output.

### FR12 — tests (F009, F011, F012, F014, F022, F023, F024)

- AC12.1 The fix-line census covers every `dd-gitflow-default` worktree script (F014). Test: unit (the census test).
- AC12.2 `fake_venv` is `venv.create(with_pip=False)` (F022). The repo `AGENTS.md` line "Tests never build a real venv (exhausts disk)" becomes "Tests never pip-install into a venv (exhausts disk)" (Q13). Tests write scratch only under a tmp path and never under `tests/`, through one enumerator (F023). Test: unit.
- AC12.3 Each contract's literal is pinned in one test home (F024). The vacuous RED goes red on revert (F011). The asserts F012 names are restored. Test: unit; the reviewer's revert check.
- AC12.4 F009 is answered by ADR 0280 clause 3, not by a `verify:` change. Test: none.
- AC12.5 The removals the operator ordered (Q3), in order; each contract keeps one test in its one home, and each commit names the ruling. Test: none; the reviewer's check of each kept home.
  - (a) `tests/core/test_spec_status.py`, the pinned pair with `core/spec_status.py`.
  - (b) `tests/features/chokepoints/test_fold.py` and the fold rows of `tests/fixtures/fix_world.py` and `fix_census.py`, with `--rewrite-from`.
  - (c) the 8 `repack_installed_wheel`/`build_digest` tests in `test_python_env.py`/`test_one_line_bootstrap.py`; `repack_installed_wheel` is deleted when no consumer remains at the verified label.
  - (d) duplicate pins: `SKILL-MD-LENGTH` x3 to 1 and `SeveralWork` x5 to 1 in `test_cli_line__fix_line_contract.py`, the asset-count literals, the `45` change-detector at `tests/scripts/test_ci.py:183`, and the T3 prompt-wording test at `tests/e2e/test_evals_t3.py:87`.

### FR13 — eval graders (R5; F026)

- AC13.1 The T3 grader gives 0 to a stub SPEC (the bare `release.py new` output). Test: E2E (`tests/e2e/test_evals_t3.py`, a stub row).
- AC13.2 Every grader gives 0 to a trial whose verdict was written outside the dispatched reviewer. k=3 and the local Codex readout stay. That check lives once, in `compare.py`, reading the trial transcript (Q8). Test: E2E (one row per task).

### FR14 — the agentic scorecard (constitution §5)

- AC14.1 Two independent `dd-code-reviewer` judges score every cell at the tip after FR13. A fix deletes or corrects before it adds. The loop stops when both put every cell at >= 9. Test: none; the record.

### FR15 — the exit and the promote (R4; ADRs 0269, 0277)

- AC15.1 After the closure reconcile, E is the last commit that is not `_RELEASE.json`. Test: none; git.
- AC15.2 The same audit, re-run on E, reports goals 2–5 at target. Each finding it raises enters by Arm B or the intake, and E is re-cut. Test: none; the new audit record.
- AC15.3 Goals 6, 8 and 9 hold on E. Each is recorded as a `chore(release):` note with its run URL or the operator's words. Test: E2E (the eval run); none for the rest.
- AC15.4 The PR `feature/0.5.0` → `develop` opens as a draft at E; every job of the existing CI on it is goal 6 (G3). It is marked ready and merged only after every other goal holds, continuing rc-21 SPEC FR6–FR9. The portfolio PR #33 merge and the PyPI approval stay the operator's acts. Test: none; the PRs.

### Replaces

- FR1: the one-id hotfix lane at the ticket's site for a fix with a culprit (`specs/bugs/AGENTS.md:22`), and the deferral of its REBUILD to the next rc's window and Job 1 (`:27`). Also review's sibling sweep only on a re-review (`dd-code-review` §4a); the `fix_files` slice and the ">= 2 bugs" trigger (F005, F006).
- FR2: `SLOP.md:4`'s one-line definition.
- FR3: every restated copy of a fact in the text deletion plan.
- FR4: every losing duplicate of the code deletion plan (F031–F040).
- FR5: the two REBUILD-due thresholds, the archive's shape-picking flag, the ambiguous bare task id in `caused_by`, and the `Path(".")` sentinel.
- FR6: `merge`'s absence-based success path, its tree-tracked ledger-script execution, and the catch-all GitError fix line.
- FR7: the verdict gate's lexer.
- FR8: `InitPlan.command`'s `render=` switch and the nested-label act sentences.
- FR9, FR11: each PLAN §1 REBUILD or DELETE row's current behaviour.
- FR10: stored milestone and memory-window shas, the schema's required `sha`, and `--rewrite-from`.
- FR12: `fake_venv`, the scratch writers under `tests/`, the duplicate literal pins, and the tests AC12.5 removes.
- FR13: T3's pass on a stub.

### Closure

- The bug archive takes every resolved Origin record. `mcp-on-main-is-vulnerable-to-session-exhaustion` resolves at the promote (rc-21 AC9.2).
- Each finding is dispositioned through `audit.py disposition … --release 0.5.0`, then `audit.py close`.
- The memory pass (`MEMORY-UPDATE.md`) covers F053–F056 and every atom with changed sources, followed by `memory.py catalog generate`.
- `llms-full.txt` is regenerated. All of this lands before E.

## 5. Constraints and risks

- A library change is finished only once the instance is reprojected and `doctor` is clean.
- A bug found during the remediation follows ADR 0280: the REBUILD of its unit, in its lane.
- Risk: waves II–IV touch the same files (`_worktree_end.py`, `gate_policy.py`, the laws). The PLAN serializes overlapping `W:` sets across waves.
- Risk: the re-audit finds what this release left. Its findings re-cut E (AC15.2). The release has no date.

## 6. Open questions

None open.

- G1 closed: PLAN §1 is the repo's durable home of the unit rows, the worklist and the deletion plans; the evidence copy is outside the repo, at `.dadaia/reports/dadaia-workspace/audit-20261022-bug-history-and-single-source/`.
- G2 closed: ADR 0280's ruling words name 0267, 0235 and 0264 clause 3.
- G3 ruled: goal 6 is every job of the existing CI on the promote PR `feature/0.5.0` → `develop` at E, a draft until every other goal holds (AC15.4). No leg, tier or gate changes.
