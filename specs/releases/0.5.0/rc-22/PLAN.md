# PLAN — Release: 0.5.0, candidate 22

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-sw-engineer-sr

The SPEC says what (FR1 to FR10; `AC<n>.<k>` belongs to FR`<n>`); this PLAN records the as-is review, the DAG, the lanes and acts that are not tasks, and the notes the main thread needs to dispatch. Paths are repository-relative to `repos/dadaia-workspace/`; `S/` = `dadaia_workspace/public/skills/`. Task file: `tasks/job1.md`. FR10 (ADR 0279) was done in the define and has no task.

**The seven bugs are not rc jobs.** By the main-thread ruling "Any confirmed bug in code the work branch holds takes a `<v>/wt-hotfix-<bug-id>` lane" (`specs/bugs/AGENTS.md` §2), each lands by its own lane, each with its RED test and its `fix(bugs)` commit. The rc's own jobs are only what is not a lane: the scorecard (Job 1) and the closure acts (§3). §1 reviews every unit the lanes touch, because the as-is review is the record of why each unit has the verdict its lane carries.

**Evidence.** First read at `114b632b3` (`feature/0.5.0`); lane states re-read at `a4a3939f9` (the work branch tip when this PLAN was cut). The as-is slices count a unit's file name over `specs/bugs/BUGS.jsonl` (927 lines) and `_archive/bugs_histo.jsonl` (296 lines) by `fix_files`, which is write-once and absent on records before 2026-10-11, so counts are lower bounds. Nothing was timed here; the one measured cost is ADR 0279's pre-gate reading, 0.06 s per Bash call over 8 runs.

**Rulings carried (verbatim).** The SPEC's grill words (Q1-Q11, summary) stand. Main-thread: "Any confirmed bug in code the work branch holds takes a <v>/wt-hotfix-<bug-id> lane"; "KEEP the instruction, its text-asserting test goes to 0.6.0 intake". Agent defaults, unruled: Job 1's fix rows follow round 1's record; the closure holds the memory edits.

## 1. As-is review

Order: DELETE, REBUILD, UPDATE, KEEP, ADD. Structural cause of the window's bugs: one fact, several deciders (who writes a verdict and where it lives; the entry rule; the parent-tree check; the command tree), each fixed one site at a time. `Lane` is the FR the unit's change belongs to.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `S/dd-handoff-emitter/scripts/verdict.py` `_run` (FR1) | the only verdict writer; stamps `agent` and `produced_at`; wrote under `.dadaia/handoff/<ctx>/`, a zone every agent writes | 4 | REBUILD of the output place; rest KEEP | the trust anchor was a writable path. Output now `.dadaia/states/verdicts/<ctx>/` |
| `S/dd-bug-resolution/scripts/_handoffs.py` `reviewer_records` (FR1) | globbed two writable zones and trusted the `agent` field | 1 | REBUILD | reads one protected dir; the hold glob and the `agent` filter are deleted |
| `S/dd-gitflow-default/scripts/_worktree_end.py` `_check_approved`, `_reviews`, `_moment` (FR1) | newest `produced_at` decides | 9 on the verdict gate in 18 days | KEEP, input changes | order is verdict.py's clock once the writer is exclusive; a change here is a layer |
| `S/dd-gitflow-default/scripts/_worktree_end.py` `merge` head and `_kind_checks` (FR4) | gone-tree path runs `_on_target` before any parent-tree check; the check lives only in `_kind_checks` | 44 name the file, 8 closed 2026-10-19/20 | REBUILD of the head of `merge` | two entry paths, one parent check. One `_require_into` called first by both; `_kind_checks` loses its copy, net <= 0 |
| `hooks/sdd_gate.py` `evaluate_payload`, `features/spec_context/gate_policy.py` `evaluate`, `hooks/root_whitelist.py` (FR1) | file-tool writes only; one `agent_type` reader | 4 on identity and the Bash boundary | UPDATE | one pure rule beside `evaluate`, one payload branch; the reader moved, not copied |
| `core/harness_registry.py` `HarnessRecord`, `infrastructure/runtime_transforms/hook_wrappers.py` Claude row (FR1) | no identity fact; Claude matcher excluded Bash | 8 on the table | UPDATE | `subagent_key` per record; matcher `+|Bash`; the table stays the decider |
| `core/workspace_layout.py` `STATES_CANON`, `verdict` (FR1, FR6) | closed canon; `verdict` is radon D 21 | 17 | UPDATE canon entry (FR1); REBUILD `verdict` split by level (FR6) | the existing STATE refusal covers the new place |
| `tests/helpers/worktree_ws.py` `approve` (FR1) | wrote a hand-made verdict under `.dadaia/handoff/` | 0 | UPDATE | writes `verdict.py`'s place and body shape |
| `evals/tasks/t3-discovery/tests/test_grade.py` `filled`, `problems` (FR2) | accepted only an active backlog entry | 2 | REBUILD | the grader restated the law's entry rule narrower than the law; it now reads the checkers' exit status |
| `evals/tasks/t3-discovery/instruction.md` (FR2) | hands the agent a concrete wish | 1 | KEEP | the wish is the operator demand the law admits |
| `cli/commands/init.py` `init`, `sibling_fix` (FR3, FR6) | foreign-tree refusal's fix onboarded another folder | 6, five the same sibling line | REBUILD | one fix line, `Operator action: empty <folder> or name another empty folder for the workspace, then run init on it`; the grade D split rides FR6 |
| `cli/commands/reconcile.py` (FR5) | rollback advice as prose | 0 | UPDATE | one `fix:` line through the one refusal renderer |
| `cli/help_digest.py` `command_paths` and its callers (FR6) | lazy `cli.main` import behind an `lru_cache` | 3 | REBUILD | root command comes from Typer's context; import and cache go |
| `bugs.py` `_read`, `_bugs_check.py` `findings_for`, `context.py` `show`, `reports.py` `validate`, `fold.py` `_fold`, `service.py` `baseline` and `_dead_preflight` (FR6) | nine functions at radon grade D with the cycle | 17, 15, 14, 4, 2, 25 | REBUILD (splits) | grade D and >= 2 bugs; output byte-identical; characterization tests are the guard |
| `S/dd-handoff-emitter/scripts/_stats.py` `_FREE` / `_after_closure` (FR7) | subject-prefix exemption list | 10 name the file | REBUILD `_after_closure` | the exemption is the law's path, not a subject list (landed as the lane) |
| `setup.cfg` import-linter contracts (FR6) | 7 kept, none covers `help_digest -> main` | 0 | UPDATE | +1 forbidden contract is the RED, inside the `lint-imports` that `ci.py` already runs |
| agentic set `dadaia_workspace/public/**` (FR8) | the scored surface | scorecard cells | KEEP, fix cells (Job 1) | corrections delete or correct before they add |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| who may write a reviewer verdict | `gate_policy` (one pure rule) via `sdd_gate.evaluate_payload` | `HarnessRecord.subagent_key`; `_common.subagent(payload)` | the `agent` field as an identity test (`_handoffs.py`) |
| where a verdict lives | `.dadaia/states/verdicts/<ctx>/`, written by `verdict.py`, read by `_handoffs.reviewer_records` | `_worktree_end._reviews`, `_stats.table` | the handoff-zone read and the reaper-hold glob |
| the order of verdicts | `verdict.py`'s clock | `_worktree_end._moment` | none |
| the entry rule (backlog or operator demand in SPEC Origin) | root map §1, judged by `backlog.py check` and `release.py check` | `test_grade.py` | `filled`'s private copy |
| the command tree | `help_digest.command_paths(root)` | `doctor`, `capabilities`, `help`, `public`, `reconcile` | `_root_command`'s `cli.main` import and its `lru_cache` |
| gone-tree vs present-tree parent check | `_worktree_end._require_into` | `merge` (both paths) | `_kind_checks`'s inline check |
| what a refused `init` onboards | `init.py` foreign-tree fix | `InitPlan.command` | `sibling_fix` for the foreign-tree refusal |
| a failed reconcile's remedy | the CLI's one refusal renderer (`cli/_fail.py`) | `reconcile.py` | `[rollback-required]` prose |
| metric 6's exemption | `_stats._after_closure` (the law's path) | `verdict.py stats` | the subject list |

### 1.2 Lane state and the pre-mortem

**Lanes (each `0.5.0/wt-hotfix-<bug-id>`, ruled by `specs/bugs/AGENTS.md` §2).** Merged on `feature/0.5.0`: FR5 reconcile (`2dcc10f5d`, fix `2ea8f2c4f`), FR3 init (`62ae52e04`, then the Q11 fix lines `813ab93ba`, `c3bd83228`), FR2 t3-grader (`332f2a5eb`, fix `5fe06d62f`), FR7 stats (`a58b605c7`, fix `ededdffdc`), FR1 verdict-writer (`a4a3939f9`, fix `ebf8c5a9b`). In review: FR4 gone-tree merge, FR6 constitution complexity (lane trees `wt-hotfix-merge-of-a-gone-tree-…`, `wt-hotfix-code-breaks-the-constitution-…`). Five further confirmed bugs will land as lanes, registration in progress: the verdict-gate regex, `_stats`'s second file reader, verdict binding after sync, reconcile's `platform.act` attribute calls, and init's action-label / operator-act contract. These five are not in the SPEC's Origin; see gap G1.

**Pre-mortem hits and their answers** (read-only `dd-researcher` pre-mortem, summarized by the main thread).

| hit | answer | where it lands |
|---|---|---|
| R1 memory and law staleness: `sdd-gate-v3.md:26`, `harness-claude-code.md:25`, the ARCHITECTURE ADR 0096/0133 summaries | memory text, written only at closure | closure memory pass (§3, act C2) |
| R1 `worktrees-AGENTS.md:22` states "only the dispatched `dd-code-reviewer` writes a verdict" yet holds only where a harness row names a subagent key | law text already merged; whether it is accurate enough is a scorecard cell | Job 1 (a cell below 9 becomes a fix row) |
| R2 pre-verdict-move verdicts invisible to merge and `verdict.py stats`: `stats` for rc-21 undercounts; no open tree depends on a pre-move verdict after the reprojection | the undercount is read beside rc-21's value (SPEC goal 8, rc-21's metric 6 already corrected for its three `chore(audits)` commits); no code | closure readout note (act C3) |
| R2 `agent-comms.md:16,20`, `sdd-gate-v3.md` verdict place | memory text | closure memory pass (C2) |
| R2 stale wording at `handoff-AGENTS.md:22`; no owner row for `verdicts/` in `states-AGENTS.md`; `_worktree_end.py:400` refusal text ("the file comes from the reviewer's verdict") | public law and a refusal's text: a lane fix, not a closure edit (a fix line stays Arm B). Proposed home: the verdict-binding-after-sync and verdict-gate-regex lanes; see gap G2 | lane fix |
| R2 `CONTEXT.md:237` | derived glossary wording | gap G3 |
| R2 `reports validate --all` blind to verdicts; the states zone has no TTL, so verdicts never expire | by design of the protected place (the gate's own validation runs at write and at merge); unbounded growth is a clean-up question | 0.6.0 intake (the main thread's batch), not written here |
| R4 map §3 Operator-action classes against Q11 | fixed in the init action-label / operator-act contract lane; the scorecard verifies the map text after it merges | lane, then Job 1 |
| R5 | no breaks | none |
| R6 | handled in the constitution lane (FR6); the constitution text is the operator's | lane |

## DAG

| job | waits on | wave | `W:` |
|---|---|---:|---|
| Job 1 | — | 1 | `.dadaia/reports/dadaia-workspace/agentic-scorecard/` |

Edges and why. Job 1 has no job edge, but it opens only after the last lane that writes `dadaia_workspace/public/**` has merged and `worktree sync` has run (constitution §5: the scorecard runs last among the text-changing work). Closure, E and every act of §3 wait on Job 1. The fix rows round 1 yields join Job 1 by amendment (job file, DAG `W:`), before its `wt-main` opens.

## 2. Notes for dispatch

- **Agent cap.** One task runs the job: the closing row (`cr`), plus the fix rows, which share no file with each other; they run in parallel up to the agent cap of four.
- **Gate law.** The repo `verify:` is `python scripts/ci.py job`; no `verify:` change, no new gate, no preflight. The closing row has no code and no `verify:` beyond the merge's.
- **No bug is open on Job 1's units** at the time of cut; a fix row that finds a contract bug stops and returns it to the main thread (Arm B).
- **Reproject.** Every lane and Job 1 change projected sources; after each merge the main thread runs `public install`, then `doctor` on the instance (act AP).
- **Net lines.** Job 1's fix rows are at or below 0 (a fix deletes or corrects before it adds); the closing row writes nothing in the repo. The lanes' net bounds are their own: FR4 <= 0 on `_worktree_end.py` (AC4.1).
- **Intake, for the main thread's batch (not written).** The text-asserting `test_the_instruction_gives_the_operator_work_and_names_the_workspace` (ruled 0.6.0), `reports validate --all` and the verdict-store TTL, the CI Codex lane (SPEC §3).

## 3. Acts that are not tasks

Main-thread and operator acts in order. `release.py check` refuses a `specs/memory` path in a task's `W:`, so the memory edits are acts of the closure reconcile, as in rc-19 to rc-21.

| act | when | who | what | check |
|---|---|---|---|---|
| AP | after each lane merge and after Job 1 | main thread | `public install`, then `doctor`, on the instance | `public doctor` prints `[ok] public-privacy`; `doctor` exits 0 |
| L | until every lane has merged | main thread | the lanes of §1.2 in the r2 handoff's order, FR6 last; each lane followed by `worktree sync <wt-rc path>`; reviews in flight on open lanes are redone after FR1 (ADR 0279) | `bugs.py status --specs specs`: the seven Origin records `resolved` and each fix commit found by its id line |
| S1 | after the last lane that writes `dadaia_workspace/public/**` | main thread, two `dd-code-reviewer` judges | scorecard round 1 at that tip; fix rows join Job 1 | the record under `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/` |
| C1 | after Job 1 merges | `dd-product-engineer` in the `wt-rc` | `release.py phase CLOSURE --sha <sha>`; the bug archive takes the seven Origin records and every lane resolved in the rc (the mcp record stays open and carried, rc-21 AC9.2) | `bugs.py check` exit 0 |
| C2 | after C1 | `dd-product-engineer` | the memory pass (`MEMORY-UPDATE.md`): the atoms of SPEC §Closure (`workspace-init.md:27`, `agent-evals.md:16`, `harness-claude-code.md:25`, the ARCHITECTURE ADR 0096/0133 summaries, `sdd-gate-v3.md:26`, `agent-comms.md:16,20`, the verdict place in `agent-orchestration`, `worktrees`, `bug-ledger`, `docs/getting-started.md:32`), then `memory.py catalog generate`, `release.py memory --reviewed … --changed …` | `memory.py check`, `release.py check`, `doctor` exit 0 |
| C3 | with C2 | `dd-product-engineer` | the readout: `verdict.py stats 0.5.0-rc22` beside rc-21's (2/2, 5/7, n/a, 4, 0, 0; metric 6 corrected), the `summary` entry with `carried: mcp-on-main-is-vulnerable-to-session-exhaustion` | the `summary` entry in `_RELEASE.json` |
| C4 | with C2 | `dd-product-engineer` | `python scripts/llms_full.py` regenerates `llms-full.txt` | the file matches its generator |
| E | after C4, reviewer APPROVED on the `wt-rc` head, merged | main thread | E = the last commit that is not `_RELEASE.json`; push; every CI job green | `git rev-parse` names E; CI green |
| G | on E | main thread, operator | AC9.2 `eval.yml` on E (T1 3/3, T2 >= 2/3, T3 >= 2/3, `non-blocking`); AC9.3 the local Codex readout at k=3; AC9.4 the checkpoint scores; a `chore(release):` note names the run URL, the verdict and E | the notes; `git diff --name-only E..<promote head>` lists only `_RELEASE.json` |
| P | the operator's order | main thread, operator | AC9.5: the promote PR `feature/0.5.0` → `develop` opens once the gate is `non-blocking`, then rc-21 SPEC FR6-FR9; the portfolio PR #33 merge and the PyPI approval stay the operator's | the PRs and merge states |

## 4. Open points and seams

1. **G1 — five confirmed bugs outside the Origin.** The SPEC's Origin lists seven ids; the five further lanes are not in it, and the SPEC (`dd-product-engineer`) says rc-23's window takes lanes resolved after rc-22's birth. The main thread rules whether the Origin line grows by amendment or they ride the closure archive without an Origin id; `release.py check` accepts either today.
2. **G2 — law text and one refusal text with no lane yet.** `handoff-AGENTS.md:22`, the `states-AGENTS.md` owner row for `verdicts/`, and `_worktree_end.py:400` need a lane each (one lane can hold all three if they share a bug record). The main thread assigns them to the verdict lanes in registration or registers a new bug. If none lands before round 1, the scorecard finds the first two and Job 1 carries them as fix rows; the refusal text is Arm B only.
3. **G3 — `CONTEXT.md:237`.** The repo-root glossary sits outside `dd-gitflow-default` shape 9's paths (`specs/memory/*`, `README.md`, `docs/*.md`). The main thread rules its shape (a lane, or the closure's derived docs).
4. **Job 1's fix rows come from round 1** and amend this PLAN's DAG `W:` and `tasks/job1.md` together before the job opens, as rc-21's Job 5 did.
5. **The closure is acts, not a job.** Its files are `specs/memory/**`, `llms-full.txt`, `docs` and `_RELEASE.json`; none can be a task's `W:` (`release.py check`), the same as rc-21's A4.
