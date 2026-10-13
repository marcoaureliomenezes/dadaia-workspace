# SPEC — Release: 0.5.0, candidate 15 — clean-up: the five open bugs and the rc-14 carry

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-13
**Origin:** backlog:one-bytecode-off-owner,release-drift-edge-runs-memory-drift,architecture-adr-section-generated,one-owner-residue-after-the-kernel,reconcile-tree-writes-have-a-commit-shape,task-worktree-cap-removed; bugs:backlog-exit-refuses-on-an-unrelated-spec-origin,preflight-skips-checks-merge-runs,verdict-context-pattern-disagrees-with-core,verdict-validation-stated-three-ways-without-the-reviewed-tree,verdict-writer-emits-a-handoff-the-schema-rejects

Sources: the as-is review, read at `33cab8274`, whose table and sections now live in PLAN §1 to §1.6; the main thread's grill of 2026-10-13 (AskUserQuestion; each chosen option quoted verbatim where it rules); each Origin entry's `BACKLOG.json` description. Paths are relative to `repos/dadaia-workspace/`.

Operator rulings, verbatim:

- Scope, 2026-10-13: "Fora: rc-15 só limpa (Recommended)" — the evals and promote items stay out (§5).
- `one-bytecode-off-owner`, 2026-10-11: "Backlog for rc-15 (Recommended)".
- Q1, backlog-exit fix line: "Só a --release (Recommended)" — the refusal's fix names the Origin act under `releases/<--release>/` only; this is the operator's order (root map §1, ADR 0249) for the assert at `tests/public/skills/dd_backlog_definition/scripts/test_backlog.py:284-298`.
- Q-cap: "Trocar o assert (Recommended)" — at `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py:138-152` the sixth task opens; the orphan and job-branch asserts stay.
- Q5, ADR triage: "Por classe (Recommended)" — class-level superseding proposals, each naming many ids, each accepted by the operator.
- Q6, ADR 0193's `amends`: "Novo registro (Recommended)" — a new record amends 0152; the ledger stays append-only; the ADR 0138 repair lane is not widened.
- Q7, `measured_by` existence: "Construir e recusar (Recommended)" — built in the doctor's ADR code, refusing at regeneration, after the class triage.
- DEFINITION done-marker check, 2026-10-13: "Apagar check e testes (Recommended)" — the check and its tests are deleted by this order (root map §1, ADR 0249), together with the last `TASKS.md` read in `_release_tree.py` (FR11).
- Memory-in-`W:` rule, 2026-10-13: "Regra só antes do CLOSURE (Recommended)" — `release.py check`'s memory-in-`W:` refusal judges candidates in DEFINITION and IMPLEMENTATION only.
- Carried, `architecture-adr-section-generated`: "Triagem + gerada (Recommended)" (2026-10-11); "Real no closure" (2026-10-03).
- Carried, `task-worktree-cap-removed`: "Descartar (Recommended)" and "e vai fazer de novo quantas vezes???" (2026-10-13).
- Carried, G7 (rc-14 SPEC G7, operator 2026-10-11/12): "Não tolerarei nem mesmo 30% dessa quantidade de retrabalhos que tivemos."

Agent defaults, unruled (main thread, 2026-10-13): Q2 bytecode = option B (the child env comes from `_git.scrubbed_env`; the `-B` argv literals stay, each with a reason); Q3 release drift = option B (the decider and `CATALOG` move into the kernel); Q4 reconcile shape = option B (readouts only in the closure summary; `reconcile` added to the exit and repair rows; no §4 exception); Q8 G7 = as the rc-14 SPEC wrote it, a readout (operator, 2026-10-12: "quero que na proxima release candidate eu possa medir o quanto melhorou"). Main-thread rulings, 2026-10-13: the job-gate `doctor` (AC5.3) is kept under the gate-cost line; FR10's triage proposals land in a `backlog/<slug>` tree; the instance is reprojected after each wave's merges, so FR7's `preflight` and FR8's writer act on rc-15's own later reviews (G7). The sr's own defaults are labelled where they appear.

`law-one-home-residual` exited `delivered` at rc-14; its parts (b), the ADR-ledger triage, and (c), 0193's `amends`, are carried by `architecture-adr-section-generated` (FR10). Its histo reason "(b) ADR 0243 accepted" stands uncorrected: `backlog.py` has no verb to amend an exit.

---

## Bug window review

rc-14 ran from its birth at `c5dfdc07f` (2026-10-11) to its closure (2026-10-13). Twenty-two bugs closed in that window (21 fix commits), judged with `git show <fix_sha>` against the overfitting patterns; `release-closure-refuses-the-next-candidates-define-tree` (`d68a7c42f`) was judged by rc-14 itself.

| verdict | disposition | fixes |
|---|---|---|
| REBUILD — FR8 | `fcbbe0850` (+1/−1): `--reviewed-root` added to the gate's call only; the fix line in `_check_approved` and `dd-handoff-emitter` SKILL.md step 7 still state the old command. Same unit, second bug: `verdict-validation-stated-three-ways-without-the-reviewed-tree`. | `merge-gate-validates-the-verdict-without-the-reviewed-tree` |
| REBUILD — FR2 | `5bb7044cc` (+9/−4): one more per-site bytecode switch in a test helper, the class's ninth site. | `skill-owner-tests-write-bytecode-into-the-source-tree` |
| REBUILD — FR4 | `9c5911a51` moved the navigator's runner onto `_git`; `bugs.py:114` still runs an unscrubbed `git ls-files`. | `skill-git-runners-read-the-callers-git-env` |
| REBUILD — FR6 | Not a fix: `e3e5b747d` (J11.T2, +29/−25) made the Origin scan strict across every release, and its body states the open bug's behaviour. | (cause of `backlog-exit-refuses-on-an-unrelated-spec-origin`) |
| KEEP, noted | `babc1a587` (+40/−32): renamed its own RED test and folded two asserts into a loop over two same-second binds. That is a tightening. `hooks/ctx_inject.py` is also touched by `60aa7f27c`, in another function (`_worktrees` vs the sentinel), and no bug followed. | `rebind-in-the-stamp-second-is-not-reinjected` |
| KEEP, noted | `2ff0ee151`: rewrote its test's asserts on `dd-gitflow-default` wording (tightened to both verbs); an assert on law text is a QA-lens smell, sent to the next bug window. | `gitflow-pu3-refuses-the-job-branch-rebase-merge-prescribes` |
| KEEP | Each shrinks or holds its unit; no assert edited, no branch, no reach; no record names it in `caused_by`: `aba07db4c`, `ce0464fde` (−22), `072c5e907`, `d2d806027` (two bugs, one commit), `2e0f5b340`, `a7a346c31` (−102), `60aa7f27c`, `d32ec2281` (test-only, tracked files), `7e0a831a3`, `cbc16fec4`, `ee69ed20a` (−59), `c1d5bd2d4`, `64b6f360b`, `6f7aff3d5` (memory), `3a3bd1262`, `feae01fba`. | `worktree-new-crashes-on-an-unreadable-release-state`, `release-check-admits-a-dag-that-phase-refuses`, `verify-line-shlex-mangles-windows-paths`, `context-repo-refusals-carry-no-fix-line`, `context-alive-crashes-on-a-non-git-repo-dir`, `release-new-orphans-a-drafted-next-rc`, `codex-persona-frontmatter-drops-on-crlf`, `doctor-misses-worktrees-of-a-repo-that-left-its-context`, `job-gate-red-on-untracked-bytecode`, `cross-os-ci-masks-utf8`, `cli-refusals-print-no-fix-line`, `ledger-replace-destroys-a-symlinked-ledger`, `frontmatter-parsers-disagree-on-crlf-and-bom`, `slug-grammar-four-patterns-disagree`, `schema-move-left-memory-sources-stale`, `orchestration-operator-only-list-is-closed`, `behavior-map-schema-ships-library-paths-and-adr-ids` |

Bugs law §2: the PLAN's first jobs execute the REBUILD rows.

## 1. Problem

rc-14 left five open bugs. Each one is a fact still stated in two or three places:

- the backlog exit scans every release's Origin when the law asks about one;
- `preflight` runs a check list that `merge` extends inline;
- the verdict rule is stated three ways, and none of them is the writer;
- the context name has two grammars.

The rc-14 G1 readout also left residue: an unscrubbed git call, a refusal template built four times, the last cross-skill import (`_memory_drift`), and bytecode-off decided at about 14 sites by 8+ ledger bugs. Two rules have no measured reason: a fixed five-task cap, and an `ADR:` label plus a pairing law that duplicate ledger status in prose. The reconcile tree writes with no commit shape. Of rc-14's 47 review sequences, 23 were rejected on the first pass.

## 2. Measurable Goals

- G1. `bugs.py status --specs specs` lists none of the five Origin bugs as open at closure.
- G2. No skill script imports another skill except the kernel: `_CROSS_SKILL_EDGES` and `_EDGE_PATH_LINES` are gone and the thin-wrapper test is green.
- G3. Production code shrinks or holds: the closure summary records the net production lines of rc-15 (`git diff --shortstat <rc-15 cut>..<reconcile head> -- dadaia_workspace scripts`). Each growth names its reason (FR8, FR10).
- G7. Measured at rc-15 closure by `verdict.py stats 0.5.0-rc15`, recorded in the closure summary: REJECTED at most 30% of rc-14's, so ≤ 10 (35 × 0.3), and first-pass rejected at most 20% of rc-15's sequences. The rc-14 baseline is pinned here because verdict records age out of the hold: `verdict.py stats 0.5.0-rc14` read 2026-10-13T13:39Z gave 47 sequences, 81 verdicts, 35 rejected, 23/47 first-pass rejected; the closure summary had recorded 46 / 79 / 34 / 22. G7 is a readout, per the operator's words of 2026-10-12: "quero que na proxima release candidate eu possa medir o quanto melhorou". A miss joins the closure-summary batch for the operator and adds no gate.

## 3. Requirements

Wave ranking: Wave 1 is law, skills and the dev loop (FR1, FR2). Wave 2 is the shared foundation (FR3 to FR5). Wave 3 is features and bugs (FR6 to FR9, FR11). Wave 4 is promote-facing (FR10, then the Reconciliation). FR7 is the G7 lever and every later review leans on `preflight`, so the PLAN may lift it into Wave 1 (PLAN §1.6). After each wave's merges the instance is reprojected (main thread, 2026-10-13), so the fixed `preflight` and verdict writer judge rc-15's own later reviews.

### Wave 1 — law, skills and dev loop

#### FR1 — the reconcile tree's writes have their shape (`reconcile-tree-writes-have-a-commit-shape`; Q4 option B, agent default, unruled)

- AC1.1 (no test — reviewer sweep): `dd-gitflow-default` §3a names `reconcile` in two rows: row 2's backlog entry or exit, and row 2's in-place `measured_by` repair. Rows 4 and 8 are unchanged. `specs/AGENTS.md` §4 keeps "read-only after its closure" and gains no exception.
- AC1.2 (no test — reviewer sweep; an addition): No shipped text places a readout in a PLAN or SPEC; rc-13 and rc-14 did it by themselves. `RC-FLOW.md:39` already routes the closure narrative to the summary. RC-FLOW step 4 gains one clause: the rc's closure readouts (its independent measurement, `verdict.py stats`, the goal readouts) go in the `_RELEASE.json` closure summary, never in the closed PLAN or SPEC.
- AC1.3 (no test — closure check): rc-15's own reconcile commits touch neither `rc-15/SPEC.md` nor `rc-15/PLAN.md`. Proof: `git diff --stat <phase CLOSURE sha>..<reconcile head> -- specs/releases/0.5.0/rc-15/SPEC.md specs/releases/0.5.0/rc-15/PLAN.md` prints nothing.

#### FR2 — bytecode-off has one env owner (`one-bytecode-off-owner`; Q2 option B, agent default, unruled)

- AC2.1 (unit, RED first): The kernel's `_git.scrubbed_env()` carries `PYTHONDONTWRITEBYTECODE=1`. A child Python started with it from a temporary package writes no `__pycache__`.
- AC2.2 (integration): Five env sites build their child env on the owner and drop their own literal. The sites are `scripts/ci.py`, `scripts/mutate.py`, `features/certification/service.py`, `tests/fixtures/harness_env.py` and `test__atomic.py:216` (PLAN §1.2 lists their lines). Every existing test stays green unedited.
- AC2.3 (no test — reviewer `git grep`): `git grep -nE 'PYTHONDONTWRITEBYTECODE|dont_write_bytecode|-B\b' -- dadaia_workspace scripts tests` hits only the set PLAN §1.2 measured, each hit with its reason there. That set is:
  - the owner and its test;
  - the 8 skill-script top lines;
  - the `core/skill_owner.py` toggle;
  - the `tests/conftest.py` and `test__ledger.py` in-process switches;
  - the `-B` argv literals where `-I` or a clean env hides the variable (`python_env.py`, `hook_wrappers.py` ×2, six test sites);
  - the deliberate absence at `test__worktree_end__scaffold.py:92`;
  - two text hits: `tests/conftest.py:53` (a comment) and `tests/core/test_skill_owner.py:25` (a docstring);
  - seven more hits: `test_harness_env.py:22`, `test_ci.py:57`, `test_impact.py:95`, `test_mutate.py:74`, `hook_wrappers.py:39`, the `<sha-B>` text in the finding schema, and `privacy_baseline.json:22`.

  This replaces the entry's done-when ("names only the owner and its test"), which option B does not reach.
- AC2.4 (unit — existing tripwire): The `tests/conftest.py` repo-tree write tripwire stays unedited and green on a clean checkout. It is the class's only catch for a new spawner.

### Wave 2 — shared foundation

#### FR3 — one context-name grammar (bug `verdict-context-pattern-disagrees-with-core`)

- AC3.1 (unit, RED first): `verdict.py` accepts a context name that core registers (`My_Ctx`). `--context` accepts exactly what the core grammar accepts. It still refuses a name that leaves `.dadaia/handoff/` (`../../evil`, `a/b`, `a\b`) and the empty name, because the allowlist stays (CWE-22). By the operator's order of 2026-10-13, "Mover as linhas (Recommended)" (root map §1, ADR 0249), the `_x` and `A` rows of `test_verdict.py:182-194` move from the refused partition to the accepted partition for `--context`. They stay refused for `--slug`. Every other row stays refused.
- AC3.2 (no test — reviewer `git grep`): The pattern has one definition, the kernel's `_grammar.CONTEXT_NAME_RE`. `core/models/spec_context.py` loads it through `load_owner`, and `verdict.py:22` `_CONTEXT` leaves.

#### FR4 — the one-owner residue (`one-owner-residue-after-the-kernel`)

- AC4.1 (unit, RED first): `bugs.py`'s `git ls-files` call goes through `_git.git`. With `GIT_DIR` pointing at another repo, `bugs.py` still answers for its own (the rc-14 AC11.2 partition, extended to this site).
- AC4.2 (unit): The refusal "would not pass check — nothing was written" is built four times today: `_commit.py` (`validated`), `_backlog_store.py`, `_release_store.py` and `dd-audit-project/scripts/_audit_store.py`. After the change it is built once, in `_commit.validated`, which the three stores call; their existing tests stay green unedited. Done when `git grep -n 'would not pass check — nothing was written' -- dadaia_workspace/public/skills` returns one line, in `_commit.py`. `release.py`'s "the ship ledger would not pass check:" is a different refusal, outside this grep and this AC.
- AC4.3 (no test — reviewer sweep): PLAN §1.3 keeps each of these with its reason:
  - `infrastructure/git_subprocess.py` `_run`;
  - the 8 non-git `subprocess.run` calls;
  - the two `os.replace` path moves (D2);
  - the three ledger-store `commit` adapters (D7);
  - the two `histo_findings` wrappers (D9);
  - `cli/commands/specs.py:94`. Moving it changes the prefix asserted at `tests/features/migrate/test_upgrade.py:81`, and no operator order covers that.

  Done when, as call-site counts: `git grep -n '_commit\.commit(' -- dadaia_workspace/public/skills` returns 3, and every `"git"` argv under `dadaia_workspace/public/skills` outside `_git.py` is in a file PLAN §1 names.

#### FR5 — the closure worklist decider lives in the kernel (`release-drift-edge-runs-memory-drift`; Q3 option B, agent default, unruled)

- AC5.1 (integration): `report`, `render`, `worklist` and `git` of `_memory_drift.py` move to the kernel with their decisions unchanged, and `CATALOG` moves to the kernel's `_specs.py`. The release and navigator skills both import them, typed `Refusal` included. `release.py drift`, `memory` and `check` and `memory.py drift` keep their existing tests green. The only edit is the `sys.path` setup at `test__memory_drift.py:196,236`, which names the kernel only.
- AC5.2 (unit, RED first): The thin-wrapper test loses `_CROSS_SKILL_EDGES` and `_EDGE_PATH_LINES`. Any import outside the stdlib, the skill's folder and the kernel fails it, and a planted cross-skill import turns it red. This tightens the invariant. The `sys.path.insert` at `_release_tree.py:19` leaves.
- AC5.3 (integration; the sr's default, PLAN §1, kept by the main thread's ruling of 2026-10-13): `scripts/ci.py` `STAGE` runs the existing `doctor` job, so memory drift turns the job gate red instead of only CI. Measured cost at `33cab8274`: `python -m dadaia_workspace doctor --specs-dir specs` 0.91 s wall, exit 0, far below one run of the job's `verify:` gate, so the gate-cost line (root map §1) holds without the operator. The task re-measures it and states the number in its commit body. The change adds no new check and no second decider beside LINT-1.

### Wave 3 — features and bugs

#### FR6 — the backlog exit reads the `--release` SPEC only (bug `backlog-exit-refuses-on-an-unrelated-spec-origin`; Q1 "Só a --release (Recommended)")

- AC6.1 (integration, RED first): Another candidate has an Origin-less draft SPEC. `backlog.py exit <slug> --disposition delivered --release <id>` still exits 0 when `<id>`'s SPEC names the slug.
- AC6.2 (integration): When the `--release` SPEC does not name the slug, the refusal's one `fix:` line names the Origin act under `releases/<--release>/` only. The assert at `test_backlog.py:284-298` changes to that in a `test(...)` commit that names the operator's order of 2026-10-13: "Só a --release (Recommended)".
- AC6.3 (no test — reviewer sweep): One reader decides. `_picks`'s cross-release scan and the latest-picking-release suggestion leave.

#### FR7 — `preflight` is `merge` minus the verdict (bug `preflight-skips-checks-merge-runs`)

- AC7.1 (integration, RED first): Per tree kind, `preflight` and `merge` return the same refusal for two trees: one with an ignored file that is neither kept nor dropped, and one whose target checkout is off its target branch.
- AC7.2 (no test — reviewer sweep): `_kind_checks` is the one complete list, with the ignored-file and target-checkout checks inside it. `merge` runs the list, then lands. `preflight` skips only the verdict check and takes `--keep`/`--drop`, so its fix line equals the one `merge` prints. Neither verb runs a check outside the list.

#### FR8 — the verdict writer validates its own output (bugs `verdict-validation-stated-three-ways-without-the-reviewed-tree`, `verdict-writer-emits-a-handoff-the-schema-rejects`)

- AC8.1 (integration, RED first): A body whose finding lacks `fix_recommendation` makes `verdict.py` exit nonzero. Its stderr follows the script's own grammar, `[error] …` plus one `fix:` line, and names the failing key. No file is left behind.
- AC8.2 (integration, RED first): A verdict that cites a file only the reviewed tree holds is written, and it validates. The writer runs the workspace CLI's `reports validate <path> --reviewed-root <tree>` on its own output, and builds the CLI path with the kernel's `_platform`.
- AC8.3 (integration): The merge gate's fix line for an invalid verdict carries `--reviewed-root <tree>`.
- AC8.4 (no test — reviewer sweep): `dd-handoff-emitter` SKILL.md step 7 and its Done-when lose the manual `reports validate` run. The validation rule is stated once, by the writer. Growth reason: the bug's expected behaviour is validation before the file is accepted (about +8 production lines, as estimated by the as-is review).

#### FR9 — no task-tree cap (`task-worktree-cap-removed`; Q-cap "Trocar o assert (Recommended)")

- AC9.1 (integration): A sixth task tree of one rc opens. At `test__worktree_new.py:138-152` the sixth-refusal and "cap counts tasks only" asserts become "the sixth opens", in a `test(...)` commit that names the operator's order of 2026-10-13: "Trocar o assert (Recommended)". The orphan and job-branch asserts stay unedited.
- AC9.2 (no test — reviewer sweep): Three things leave: `TASK_CAP`, its refusal in `_worktree_new.py`, and the law clause "at most 5 task worktrees are open per rc" (`public/data/worktrees-AGENTS.md`). The `worktrees` memory atom line changes at the Reconciliation. Concurrency stays the approved PLAN's schedule.

#### FR11 — the DEFINITION done-marker check leaves (operator, 2026-10-13: "Apagar check e testes (Recommended)")

Job files carry no `[x]`/`[-]` markers, so the check reads markers only from the retired `rc-<N>/TASKS.md` and never fires on a current candidate. The hotfix `release-check-memory-task-check-reads-retired-tasks-md` keeps that read only for this check, until FR11 deletes it.

- AC11.1 (no test — reviewer sweep; tests deleted by the operator's order): The marker half of `_definition_findings` (`_release_tree.py`, "task … is marked past '[ ]' in phase DEFINITION") and the last `TASKS.md` read in `_release_tree.py` leave. `git grep -n 'TASKS.md' -- dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` returns nothing. The tests leave in one `test(...)` commit that names the order "Apagar check e testes (Recommended)": the two marker rows of `test_check_judges_a_definition_release` (`test_release.py`, `("- [x] **T-1** done\n", [], "T-1")` and `("- [-] **T-1** reserved\n", [], "T-1")`), plus any test the hotfix adds for that read alone (the PLAN names it at the hotfix's merged sha).
- AC11.2 (integration — existing tests): The closure-entry-after-birth finding of `_definition_findings` reads `_RELEASE.json`, not `TASKS.md`, and stays. Its parametrised rows stay unedited. `test_a_definition_finding_stamps_the_commit_that_touched_the_trio` moves onto the closure-entry trigger and its assert stays. The main thread ruled this move on 2026-10-13, and its `test(...)` commit names that ruling (root map §1).
- AC11.3 (no test — reviewer `git grep`): The operator's order "Apagar check e testes (Recommended)" also covers `MARK_RE`, `MARKS` (`_release_schema.py`) and any test that exists only for the deleted done-marker check, including the thin-wrapper `_SCHEMA` allowlist entry (main thread, 2026-10-13). If the assert at `test_release.py:324` judges anything else, the task stops and asks the operator (ADR 0249).

### Wave 4 — promote-facing

#### FR10 — ARCHITECTURE.md's ADR section is generated from the ledger (`architecture-adr-section-generated`, with `law-one-home-residual` (b) and (c))

- AC10.1 (no test — ledger, operator acts; Q5 "Por classe (Recommended)"): The triage proposes a few class-level superseding records, each naming many ids in `supersedes`. The classes are process rules and spent rulings, each superseded by its law line. Each record carries `options` and a self-contained `ruling.words` (ADR 0245). The operator accepts each. Each survivor keeps or gains a `measured_by` that resolves ("Real no closure").
- AC10.2 (no test — ledger; Q6 "Novo registro (Recommended)"): A new record amends 0152, recording 0193's change. 0193 stays untouched, and the ADR 0138 repair lane does not widen.
- AC10.3 (unit, RED first; Q7 "Construir e recusar (Recommended)"): The doctor's ADR code refuses an accepted, non-superseded record whose `measured_by` resolves to none of the forms `specs/memory/AGENTS.md` §2 accepts (a tracked test path or node id, a doctor code, a lint contract, a CI job). The refusal carries one fix line, and it fires at the regeneration, which runs only after AC10.1's acceptances. Plants: a record naming a missing path is refused; one naming a real node id passes.
- AC10.4 (integration, RED first): `ARCHITECTURE.md` carries one ledger-rendered block, written through `core/fixed_sections.py`'s markers, with id and title per accepted non-superseded ADR. FIXED-2 flags a diff, `--fix` regenerates the block, and MEM-NARRATIVE-1 exempts it. The block itself is written by the Reconciliation's memory pass, never by a job, and the five label drifts go by construction.
- AC10.5 (no test — reviewer sweep): The `ADR:` label grammar and the pairing law leave:
  - the guard's `_ADR_LINE` rows and plants (`scripts/guards/repo.py`); narrowing a guard's reach takes the main thread's ruling, named in a `test(...)` commit (root map §1);
  - the pairing clauses of `specs/ADRs/AGENTS.md` (§2, §5, §5.1) and `specs/memory/AGENTS.md`;
  - `PILLAR-MEMORY.md`'s pairing check (its missing-`Measured by:` finding stays) and the scaffold mirrors;
  - §3a row 2's "with its canonical-memory hunk";
  - the 19 `ADR:` lines in `ARCHITECTURE.md` and `QUALITY.md`, removed at the Reconciliation.

  `test_memory_lint.py:346-350` and `:427-431` stay unedited, because no operator order covers them.

## 4. Exits at closure

Each picked entry exits once at closure (`backlog.py exit`, from the reconcile tree per FR1): `one-bytecode-off-owner`, `release-drift-edge-runs-memory-drift`, `architecture-adr-section-generated`, `one-owner-residue-after-the-kernel`, `reconcile-tree-writes-have-a-commit-shape` and `task-worktree-cap-removed`, each `delivered`.

## 5. Not in rc-15

- **Non-goals** (operator, 2026-10-13: "Fora: rc-15 só limpa (Recommended)"): `promote-gate-050`, `release-approve-requires-evals-gate`, `windows-smoke-t1-at-release`, `eval-codex-lane-in-library-ci`. They stay active and untouched. `evals-benchmark-lanes` is not destined to 0.5.0.
- **Hotfix:** `release-check-memory-task-check-reads-retired-tasks-md` is open and fixed now as a hotfix outside the rc's DAG; FR11 deletes the one `TASKS.md` read it leaves.
- **Every other `active[]` entry** stays active and untouched.

## 6. Constraints and risks

### Replaces

- `_picks`'s strict cross-release Origin scan and its latest-picking-release suggestion become one reader of the `--release` SPEC (FR6).
- `merge`'s two inline tail checks become one check list that both verbs run (FR7).
- The reviewer's manual `reports validate` step, and the gate's fix line without the tree, become the writer validating its own output with the reviewed tree (FR8).
- `verdict.py`'s `_CONTEXT` and core's literal pattern become the kernel grammar (FR3).
- The release skill's import of the navigator's `_memory_drift`, `_CROSS_SKILL_EDGES`, `_EDGE_PATH_LINES` and the `sys.path` insert become the kernel decider (FR5).
- Five per-site `PYTHONDONTWRITEBYTECODE` env literals become the kernel env (FR2).
- `bugs.py`'s unscrubbed `git` call and the three inline copies of the "would not pass check — nothing was written" refusal (in `_backlog_store.py`, `_release_store.py` and `_audit_store.py`) become their owners (FR4).
- `TASK_CAP`, its refusal and its law clause leave (FR9).
- The `ADR:` label grammar, its guard rows and plants, the pairing law and row 2's hunk clause become one generated block and a `measured_by` check (FR10).
- Closure readouts in a closed PLAN or SPEC become the closure summary only (FR1).
- The DEFINITION done-marker check, its last `TASKS.md` read and its two marker test rows leave by the operator's order (FR11).

### Governance sequencing

1. ADR proposals land in a `define` or `backlog/<slug>` tree (§3a row 2), carrying `options` and self-contained `ruling.words` (ids above 0246). Only the operator accepts. FR10's class-triage proposals (AC10.1) land in a `backlog/<slug>` tree during rc-15 (main thread, 2026-10-13); the PLAN schedules that tree.
2. Two accepted records state what this SPEC deletes. ADR 0191 states "At most 5 task worktrees per rc", carrying 0125 (3) (FR9). ADR 0245 (4) keeps the id-only `ADR:` label and the pairing rule (FR10). ADR 0250 (amends 0191) and ADR 0251 (amends 0245) were accepted by the operator on 2026-10-13, "Aceitar (Recommended)"; each record's `ruling` holds the question and the chosen option.
3. FR10's order: the triage (AC10.1) proposes after the bug jobs merge, when the ledger is final. AC10.3's refusal runs only after the operator has accepted those proposals. The Reconciliation regenerates the block.

### Delivery constraints

- No test and no existing assert is removed or skipped without the operator's order (root map §1, ADR 0249). This SPEC changes two asserts and deletes two test rows, each by an operator order: AC6.2, AC9.1 and AC11.1. AC11.2 and AC11.3 name the test edits that still need a ruling. Every other RED is a new partition, or a tightening checked by the reviewer's revert check.
- A docstring or comment states only its unit's contract.
- Simplicity first: each FR deletes before it adds. FR8 and FR10 state their growth.
- Tidy First: an owner moves before its behaviour changes (FR3 and FR5 before FR8); each bug fix lands its RED test first.
- What ships stays language-neutral and requires no CI, remote, PR host or vendor CLI. `scripts/ci.py`, `mutate.py` and the guards are this repository's own.
- Memory atoms change only at the Reconciliation. Rule for rc-15's PLAN: no task's `W:` names `specs/memory`; a memory change rides the define tree with its ADR acceptance, or the Reconciliation (§3a shapes 2 and 9).

### Risks

| risk | control |
|---|---|
| AC10.3 refuses most of the ledger before the triage (the as-is review's heuristic: 98 of 209 accepted records unresolved) | order forced: triage acceptance, then the refusal |
| `scrubbed_env` now carries a non-git key | one owner of a child env; the PLAN names it so a reader does not split it again |
| The kernel grows by one module with two consumers (FR5) | ADR 0246 admits it; net lines about 0 |

## 7. Open questions

None.

Notes (not blocking):

- The harness atoms `harness-claude-code`, `harness-codex` and `harness-kimi-code` still list `Bash` in the pre-gate matcher. That drift came from `b3374373b` (scorecard-fix). The fix is a Reconciliation memory-pass item that the PLAN's Reconciliation lists: a define tree writes memory only with an ADR acceptance (§3a rows 2 and 9).
- rc-14 tasks J16.T5 (`specs/memory/AGENTS.md`, the law mirror), J18.T5 (`specs/memory/ARCHITECTURE.md`, `QUALITY.md`) and J26.T7 (`specs/memory/QUALITY.md`), which re-rendered fixed blocks, wrote `specs/memory` against §3a shapes 2 and 9. The memory-in-`W:` check passed them because it read the retired `TASKS.md`. The job files stay as history. Under the 2026-10-13 ruling, the check judges candidates before CLOSURE only.
- The gate's other fix line (`_check_approved`, `reports validate --all` when no verdict decides) names the validator where the remedy is to write a verdict (PLAN §1, the `_check_approved` row). It is not in a bug record; it goes to the next bug window as a proposal.
- `test_memory_lint.py:346-350,427-431` assert a label grammar FR10 deletes from the law. They still pass, and changing them needs the operator's order.
