# SPEC — Release: 0.5.0, candidate 12 — futures restored

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-09
**Origin:** backlog:skill-scripts-one-kernel,one-task-id-subject-grammar,origin-findings-renamed-to-the-spec-head; bugs:context-show-live-branch-test-rmtree-readonly-git-on-windows,coverage-line-test-spawns-bare-python-on-windows,fix-line-run-tests-spawn-wsl-bash-on-windows,fix-line-tests-expect-posix-bin-paths-on-windows,hook-wrapper-tests-run-an-unrunnable-fixture-python-on-windows,job-merge-accepts-any-ci-run-url,job-merge-requires-a-remote-ci-run,merge-gate-accepts-verdict-written-by-the-merger,orphan-worktree-line-absent-from-the-bind-block-on-windows,root-gate-blocks-editing-an-existing-entry,shipped-law-hardcodes-the-posix-venv-path,worktree-script-run-fails-winerror-193-on-windows,worktree-new-opens-a-job-outside-implementation; findings:20260930-structural-convergence-F003,20260930-structural-convergence-F004,20260930-structural-convergence-F005,20260930-structural-convergence-F009,20260930-structural-convergence-F018,20260930-structural-convergence-F048,20260930-structural-convergence-F051,20260930-structural-convergence-F123,20260930-structural-convergence-F135

The candidate is also an operator demand: the 2026-10-09 futures grill (`.dadaia/handoff/dadaia-workspace/2026-10-09T124816Z-main-thread-rc12-futures-grill.handoff.json`) and the law ≥ 9 order. The Origin grammar (`specs/releases/AGENTS.md` §2) admits `operator-demand` only on its own, so the counted line carries the picked ids and the demand is recorded here.

---

## Bug window review

rc-11 ran from its birth at 2026-10-08T20:26:37Z to its integration (PR 289, 2026-10-09T12:56:05Z). `bugs.py window` was deleted in rc-11 (392769e97, AC4.1), so the window was read from `BUGS.jsonl` and the archive per `dd-bug-resolution/LINEAGE.md`. One bug was found and fixed in rc-11. No record since rc-11's birth names an rc-11 fix, task or window row in `caused_by`.

| verdict | disposition | fixes |
|---|---|---|
| KEEP | `git show 27de80923`: RED test first in c05177c19; the fix replaces two `prefix_rule` patterns with their `--force` forms; there is no new rule, branch or flag (+14/−13, including the registry mandate and `CODEX.md` line). No assert was edited and no test value is special-cased. The command-policy block carries four fixes (d9c0abfad, d7a726a2f, 98599990a, 27de80923), and this fix is itself the REBUILD that the ≥ 2-fix trigger requires. It leaves the first-level window. `codex_assets.py` is revisited structurally with CP6 in rc-13. | `codex-public-install-stall` |
| REBUILD — still in window | rc-11 replaced these rc-10 rows (rc-11 table, `REBUILD — rc-11` and `REBUILD — deletion`). Each leaves the window only if rc-12 closes with no child bug. rc-12's review has none so far, and rc-13 records the outcome. | the 43 ids of rc-11's two REBUILD rows |
| REBUILD — scope | rc-11's `REBUILD — rc-12 Job 1` row is scope of this candidate (FR3), not intake. | the 12 ids of FR3 |

## 1. Problem

The 2026-10-09 coupling audit (base `68557c582`, re-measured at this candidate's birth on `b1e402511`) found 264 of 889 bugs in seven coupling points. Those points also account for 98 of 218 regressions and 36 CRITICAL bugs. Each fix there added coupling and spent future options, so the same surfaces re-bug (finding F004: 71% within 3 days). Three of the points are small, central and already measured: an informal skill kernel joined by `sys.path` mutations and import cycles (CP1), ledgers parsed by many modules (CP3), and a registry with three writers (CP4). Restoring them without changing any behaviour is the option-restoring half of Features × Futures (constitution §6).

The agentic law that every later agent reads scored 7.2/7.3 at `b1e402511`, with 40–41% of cells at ≥ 8. The operator raised the bar: "não admitiremos menos que nota 9 em todos os quesitos a partir de agora … nota 9 é o mínimo". The law therefore moves first, so every later job is executed under law that holds the bar.

## 2. Measurable Goals

- G1. The PLAN's critical path is at most 8.7 wall-clock hours, from explicit task durations and DAG edges, with aggregate agent-hours, measured baselines, uncertainty and contingency disclosed. When the estimate exceeds the ceiling, CP3 (FR7, with its two backlog items) moves to rc-13 first.
- G2. Every cell of the agentic-set scorecard scores ≥ 9 under two new independent judges, and the three design skills ship nowhere.
- G3. The CP jobs are pure refactoring: exit codes, `fix:`/`Operator action:` lines, ledgers and files written, JSON output, and BLOCK/ALLOW decisions are identical before and after. The characterization net (FR4) proves it.
- G4. The coupling metrics move, re-measured with the audit scripts at `.dadaia/reports/dadaia-workspace/futures-audit/` (`coupling/analyze.py`; `coupling/summarize.py` on `uvx radon` 6.0.1 output):

| metric | before (`b1e402511`) | after | owner |
|---|---|---|---|
| `sys.path` mutations (`analyze.py` `syspath_manipulations`) | 44 | 0 | FR6 |
| unit import cycles (`analyze.py` `unit_sccs_all_coarse` cycles) | 7 | 0 | FR6 |
| `BUGS.jsonl` reader modules (`summarize.py` `ledger_parsers_estimated`) | 8 | 1 | FR7 |
| `spec_contexts.json` writer modules (`git grep -nE "spec_contexts\.json" -- dadaia_workspace`, filtered to write sites — `write_bytes`, `write_text`, `atomic_write`, `unlink` — counted per module) | 3 (`json_context_store`, `migrate/state_v2`, `reconcile/service`) | 1 | FR5 |
| `setup.cfg` `ignore_imports` edges (`analyze.py` `ignored_imports`) | 2 | 0 | FR5 |

- G5. Each CP's test actions (delete, lint, rewrite, narrow) land in that CP's job, and each CP job's net line count, tests included, is ≤ 0.
- G6. Every AGENTS.md, SKILL.md, disclosed-sibling and persona source changed by this candidate is named in this SPEC (AC1.6). Approval is the operator's authorization for those edits.

## 3. Non-goals

- CP2 (the library executes skill code through `ledger_scripts.load_owner`) and CP6 (three frontmatter grammars) are rc-13.
- CP7 (policy in god-functions: `_worktree_end.py`, `push_gate.py`, `guards/repo.py`, `slop.py`) and CP5 (the `spec_context` god-feature and the bypassed container) are rc-14.
- The 29 other open governance findings of `20260930-structural-convergence` go to a governance slice before the 0.5.0 promote.
- No behaviour change in any CP job. The one intended behaviour change is FR2's bug, kept in its own job.
- No new mechanism to raise a scorecard cell. A law edit deletes or corrects text before it adds any.
- The operator's private `~/.claude` scorecard rule is not repository work.

## 4. Requirements

### FR1 — law ≥ 9 (runs first)

- AC1.1 (no test — reviewer source sweep): The job applies every row of the law-9 edit plan (`.dadaia/reports/dadaia-workspace/agentic-scorecard/20261009T1335Z/PLAN-law9.md`, 288 official cells below 9, `plan.json`). Where the two judges propose different edits for one cell, the edit that deletes more and satisfies both applies. The plan's four conflict resolutions apply as written: the release-state schema path is `.dadaia/agentic/schemas/release-state-v1.schema.json`; `SLOP.md` keeps the verdict rule and `dd-code-review/SKILL.md:59` is deleted; `SLOP.md:17` names "the domain names the repo's specs already use"; and the G rows replace J1/J2 for gitflow S4, manager S4, grill S5 and rel-impl S3.
- AC1.2 (integration): The library deletes `dd-domain-modeling`, `dd-codebase-design` and `dd-architecture-survey` and every reference to them in the AC1.6 sources, `behavior-map.json`, `CONTEXT-MAP.md`, the repo's `CONTEXT.md` and `tests/infrastructure/test_public_assets.py`. A rule that lived only in those skills moves to its owning skill as a pointer. `public stage`, `public install` and `public doctor` finish clean, and install prunes the instance copies. `git grep -nE 'dd-(domain-modeling|codebase-design|architecture-survey)' -- dadaia_workspace tests CONTEXT.md` returns no hit. Ledgers, ADRs, `CHANGELOG.md` and archived history are not rewritten.
- AC1.3 (no test — operator ruling): Constitution §5 reads ≥ 9 in place of both "≥ 8" (item 3's "scripts" criterion and the closing measure line), with every cell counted and a scorecard at least every 2 days and before evals, promote or publication. The amendment lands in one define-tree commit with the main thread's acceptance of proposed ADR 0239. On acceptance, ADR 0239 sets `amends: "0219"` and the operator's ruling. `constitution_version` goes from 6.2.0 to 7.0.0, because §4 makes a changed article MAJOR.
- AC1.4 (no test — independent judgement): Acceptance requires two new independent read-only `dd-code-reviewer` judges, neither of them an author of the plan or the edits. Each scores every cell (R1–R8, P1–P3, S1–S12, C1–C6) with `path:line` for any score below 9. The loop is score, fix, re-score until both judges put every cell at ≥ 9. The main thread never scores. The record lands under `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/`.
- AC1.5 (unit): The five code-text fixes of the plan land as string and docstring edits with no behaviour change:
  - `features/chokepoints/push_gate.py:210-211` drops "or the verdict rule".
  - `features/specs/canon.py:23,167` stops citing the absent `verdict_violations`.
  - `cli/commands/ci.py:74` help drops "that runs as a PR gate".
  - The `release.py` `--origin` help prints `_ORIGIN_GRAMMAR`.
  - The `core/invocation.py:3` docstring points to `.dadaia/AGENTS.md` §2.
  - The `_worktree_end.py:229-230` docstring stops assuming CI exists.

  The release.py help change is the only one a test can observe; its help test asserts the grammar.
- AC1.6 (no test — reviewer source sweep): The complete authorized law, skill and persona source write set is listed below. Adding another such source returns this Draft to the operator. Generated projections change only by stage and install.
  - Law: `dadaia_workspace/public/data/{AGENTS,dadaia-AGENTS,states-AGENTS,handoff-AGENTS,tmp-AGENTS,worktrees-AGENTS}.md`, `dadaia_workspace/public/data/CONTEXT-MAP.md`, `dadaia_workspace/public/templates/{repo-AGENTS,specs-AGENTS}.md`, `dadaia_workspace/public/scaffold/{ADRs,audits,backlog,bugs,memory,releases}/AGENTS.md`. Also the repo's own copies these sources scaffold (`specs/AGENTS.md`, `specs/{ADRs,audits,backlog,bugs,memory,releases}/AGENTS.md`), by `specs upgrade` only, and the repo root `AGENTS.md`, which receives the line moved out of `dd-software-engineer.md`.
  - Personas: `dadaia_workspace/public/agents/{dd-code-reviewer,dd-product-engineer,dd-software-engineer}.md`.
  - Skills (`SKILL.md`): `dd-ai-eng-knowhow`, `dd-audit-project`, `dd-backlog-definition`, `dd-bug-registration`, `dd-bug-resolution`, `dd-cli-library`, `dd-code-review`, `dd-gitflow-default`, `dd-grill-me`, `dd-handoff-emitter`, `dd-manager-orchestration`, `dd-release-definition`, `dd-release-implementation`, `dd-spec-navigator`, each under `dadaia_workspace/public/skills/`.
  - Disclosed siblings: `dd-ai-eng-knowhow/{AUTHORING,CLAUDE-CODE,CODEX,CONTEXT-ENGINEERING}.md`, `dd-audit-project/{FINDINGS-FORMAT,PILLAR-BUGS,PILLAR-MEMORY,PILLAR-SPECS}.md`, `dd-bug-resolution/{LINEAGE,RED-LOOP}.md`, `dd-code-review/SLOP.md`, `dd-grill-me/{EMISSION-FORMAT,PROBLEM-TAXONOMY}.md`, `dd-release-implementation/{MEMORY-UPDATE,RC-FLOW,RELEASE-EVENTS}.md`.
  - Deleted whole: `dadaia_workspace/public/skills/dd-domain-modeling/`, `dd-codebase-design/`, `dd-architecture-survey/`.
  - Entity data: `dadaia_workspace/public/entities/behavior-map.json`, `dadaia_workspace/public/entities/registry.json` (only where a deleted skill is named), `dadaia_workspace/public/templates/shipped-hashes.json` (re-recorded by its tool).

### FR2 — a release job opens only in IMPLEMENTATION (Arm B, behaviour change)

Bug `worktree-new-opens-a-job-outside-implementation` (MEDIUM, merged 4f8024cab). Law: `specs/AGENTS.md` §3. This FR is the candidate's only intended behaviour change and lands in its own job, apart from every CP job.

- AC2.1 (integration, RED first): The RED test runs the bug for real: rc SPEC Approved, PLAN Draft, `_RELEASE.json` phase `DEFINITION`. It asserts that `worktree.py new <repo> <M.m.p>-rc<N>/<job>` exits non-zero with exactly one `fix:` line and creates no tree or branch.
- AC2.2 (integration): When the phase reads `IMPLEMENTATION`, a job, task and `reconcile` tree opens as today. A `reconcile` tree is cut before `phase CLOSURE`. `define` and hotfix trees are unaffected.
- AC2.3 (no test — reviewer diff check): The fix replaces the SPEC-status check at `_worktree_new.py:87-95` with one phase check, read through the existing `_release_schema` import. Both checks are not kept, and the net lines are ≤ 0.
- AC2.4 (no test — reviewer source sweep): In the same fix, `dadaia_workspace/public/data/worktrees-AGENTS.md:12` ("a job needs its rc's approved SPEC") becomes a pointer to `specs/AGENTS.md` §3. The resolve records the gate at `_worktree_new.py:87-95`; the record's repro cites 85-93, which is wrong.

### FR3 — REBUILD the twelve rc-11 carry units

- AC3.1 (integration): Each unit of rc-11's `REBUILD — rc-12 Job 1` row is reworked with the code around it, and its regression tests are kept. The units are: `context-show-live-branch-test-rmtree-readonly-git-on-windows`, `coverage-line-test-spawns-bare-python-on-windows`, `fix-line-run-tests-spawn-wsl-bash-on-windows`, `fix-line-tests-expect-posix-bin-paths-on-windows`, `hook-wrapper-tests-run-an-unrunnable-fixture-python-on-windows`, `job-merge-accepts-any-ci-run-url`, `job-merge-requires-a-remote-ci-run`, `merge-gate-accepts-verdict-written-by-the-merger`, `orphan-worktree-line-absent-from-the-bind-block-on-windows`, `root-gate-blocks-editing-an-existing-entry`, `shipped-law-hardcodes-the-posix-venv-path` and `worktree-script-run-fails-winerror-193-on-windows`. The pull-request matrix (Linux, Windows, macOS) is green on the rebuilt units.
- AC3.2 (no test — reviewer diff check): Each REBUILD commit takes shape 3 `refactor(bugs): <id> — REBUILD <unit>: …`. It adds no branch, flag, special case or second path, and its net lines are ≤ 0, or the commit body says why.

### FR4 — characterization net (before any CP refactor)

- AC4.1 (integration): The audit inventory `.dadaia/reports/dadaia-workspace/futures-audit/seams-42.txt` lists 42 public seams without a contract-complete test, each with its owning CP. Before any CP job merges, each of the 19 seams owned by CP1 (5), CP3 (9) and CP4 (5), and every other listed seam an rc-12 job touches, has a test at its public seam. The test asserts the exit code, the exact `fix:`/`Operator action:` line, and the artifact written (file, ledger record or JSON). The 10 unowned seams (`registry.py` ×6, `capabilities`, `certify`, `help tree`, `reports validate`) and the seams owned by CP2, CP5, CP6 and CP7 get their net in rc-13 and rc-14, before those refactors.
- AC4.2 (integration): Byte-exact tests pin `BUGS.jsonl` and `_RELEASE.json`. Each writer verb run on a fixed fixture yields the same bytes before and after every CP job.
- AC4.3 (no test — reviewer check): Each characterization test is green on the pre-refactor head and on every CP job's head, and no CP job edits one of them.

### FR5 — CP4: `spec_contexts.json` has one writer

- AC5.1 (unit): `infrastructure/json_context_store.py` is the only module that writes `spec_contexts.json`. `features/migrate/state_v2.py` and `features/reconcile/service.py` write through it.
- AC5.2 (unit): Both `setup.cfg` `ignore_imports` edges (`reconcile.service` → `capabilities` and `reconcile.service` → `migrate.state_v2`) are deleted, and the ignore cap in `scripts/guards/slop.py` drops to match. `lint-imports` passes.

### FR6 — CP1: one skill kernel (absorbs `skill-scripts-one-kernel`)

- AC6.1 (unit): The skill scripts share one kernel: one `Refusal`, one store commit loop, one git wrapper and one root finder. No skill script mutates `sys.path` (44 → 0).
- AC6.2 (unit): No import cycle remains between skill units (7 → 0, `analyze.py`).
- AC6.3 (integration): Every skill script still runs as `python3 .agents/skills/<skill>/scripts/<script>.py` from the workspace root after `public install`, with the AC4.1 outputs unchanged.

### FR7 — CP3: one query API per ledger (absorbs `one-task-id-subject-grammar`, `origin-findings-renamed-to-the-spec-head`)

- AC7.1 (unit): Each ledger (`BUGS.jsonl`, `BACKLOG.json`, `_RELEASE.json`, `FINDINGS.jsonl`) is parsed by its owner's query API only. `BUGS.jsonl` reader modules go from 8 to 1, and `_release_tree.py` reads the other ledgers through their APIs.
- AC7.2 (unit): One subject parser reads task ids and commit-subject shapes for every reader. Current `J<n>.T<k>` and historical `J<n>.S<m>.T<k>` ids stay readable.
- AC7.3 (unit): `_release_tree._origin_findings` is renamed to name both of its judgements (SPEC head and Origin line). No symbol `_origin_findings` remains, and its findings are unchanged.

### FR8 — audit findings

- AC8.1 (no test — closure measurement): F004 is an acceptance metric. The same-surface re-bug rate, measured at closure with the finding's metric-4 command over rc-12's window, is ≤ 30% at 3 days. The 14-day figure (target ≤ 50%) is re-measured before the 0.5.0 promote.
- AC8.2 (no test — closure measurement): F009 is an acceptance metric, and this statement is its target: zero bugs found in rc-12's window carry a `caused_by` that names an rc-12 CP or REBUILD task or fix. The fix-induced share of rc-12-window resolutions is reported against the 37/189 baseline with no numeric target; F009 states none, and the zero-caused rule is stricter than any share.
- AC8.3 (no test — reviewer diff check): F003 and F005 resolve through G5 and AC3.2. Each rc-12 fix or REBUILD is net ≤ 0 or justified in its body, and no rc-12 commit adds an entry to a hand-kept list except `shipped-hashes.json` re-recorded by its tool.
- AC8.4 (integration): F018 is resolved when every test that spawns a child process builds its environment through one builder in `tests/fixtures/harness_env.py`. The PLAN names the grep that proves no other construction remains. Live probes stay out of the default suite.
- AC8.5 (no test — evidence): F048 and F051 are dispositioned `resolved`. Their bugs (`ci-preflight-writes-coverage-into-the-repo`, `hook-entrypoints-invisible-to-coverage`) were resolved on 2026-10-05, and the disposition cites those records.
- AC8.6 (no test — closure memory): F123 is resolved when the `specs/memory/ARCHITECTURE.md` line on import-linter contracts states the `setup.cfg` truth after FR5 (the contract count and zero suppressed edges). F135 is resolved with `git ls-files` plus a directory listing showing no package directory without a tracked file.

## 5. Constraints and risks

### Replaces

- The SPEC-status check that opens a release job becomes a phase check (FR2).
- Three design skills become pointers inside their owning skills, and the skills are deleted (AC1.2).
- The constitution §5 bar of ≥ 8 per criterion becomes ≥ 9 per cell with a 2-day cadence (AC1.3).
- `sys.path`-joined skill scripts with seven `Refusal` classes and copied commit loops become one kernel (FR6).
- N ad-hoc ledger parsers become one query API per ledger, and three task-id/subject parsers become one (FR7).
- Three `spec_contexts.json` writers and two suppressed import edges become one writer and no suppressed edge (FR5).
- The twelve rc-11 carry fixes become rebuilt units (FR3).
- Ad-hoc child-process test environments become one builder (AC8.4).

### Governance sequencing

1. ADR 0239 (proposed, `docs(adr): propose constitution-article-5-bar-nine`) amends 0219 on acceptance. ADR law M2 forbids a proposed record from naming a ruled one, so `amends` is set at acceptance.
2. On the operator's ruling, the main thread writes `accepted`, `ruling` and `amends: "0219"`. The dd-product-engineer's constitution §5 amendment lands in the same define-tree commit (constitution §4). Approval of SPEC and PLAN is a separate commit.

### Delivery constraints

- Ceiling: 8.7 h on the critical path (rc-11 measured 14.6 h for 4 jobs). Over the ceiling, CP3 (FR7) moves to rc-13 first. The SPEC stays Draft, and estimates are never compressed to fit.
- Order: FR1 runs first, because every later agent reads that law. FR4 precedes every CP job (FR5, FR6, FR7). FR2 is a separate job. FR3's `shipped-law-hardcodes-the-posix-venv-path` edits public law, so it runs inside or after FR1. FR2 and FR6 both touch `_worktree_new.py`, and the PLAN orders them. AC1.5 touches `release.py` and `_worktree_end.py`, which FR6 and FR3 also touch, and the PLAN assigns each write once.
- The job-0 red-test batch is empty: the suite on `b1e402511` passed 2982, skipped 7 and failed 0. Re-run it at rc-12 birth.
- Structure and behaviour commits stay separate. Every behaviour task is two dispatches (RED, then implementation). Each job receives one reviewer verdict.

### Risks

| risk | control |
|---|---|
| A refactor silently changes an exit code or fix line. | FR4 is green before and after every CP job (AC4.3). |
| Law edits regress a cell that already scored 9 or more. | AC1.4 re-scores every cell, not only those below 9. |
| The before→after measurement drifts from its method. | The audit scripts and their outputs live at `.dadaia/reports/dadaia-workspace/futures-audit/` (the `reports/` zone, never reaped); the after-measurement re-runs them unchanged. |
| Parallel jobs collide on `_worktree_*` and `release.py`. | PLAN `W:` sets are disjoint per wave, and the overlap check refuses a collision. |

## 6. Open questions

None.
