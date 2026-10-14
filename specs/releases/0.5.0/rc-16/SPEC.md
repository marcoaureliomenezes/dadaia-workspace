# SPEC — Release: 0.5.0, candidate 16 — the worktree hierarchy

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-14
**Origin:** backlog:worktree-hierarchy; bugs:protected-globs-miss-a-plain-tree-path,new-reconcile-opens-while-a-job-is-open

Sources: the as-is review at `13e3fc074` (ASIS, landing as PLAN §1; its findings H1–H9 are cited by id), the backlog and release grills of 2026-10-14, and the `worktree-hierarchy` entry. Paths are relative to `repos/dadaia-workspace/`. The decision is ADR **0264** (proposed).

Operator rulings, verbatim:

- Backlog grill: "Integração real"; "Lanes laterais para ambos"; "Verbo CLI + git hook"; "Apagar o tipo plain"; "Reusar o gate de job". On the per-level `AGENTS.md`: "é so porque eu não quero criar .gitkeep files ... deve estar na criação". On the agent defaults (leaf names `wt-rc`, `wt-main`, `wt-task-<k>` in 3 digits; branch = path; a `sync` verb; Arm A delivery; per-context layout out): "O resto confirmamos".
- Release grill: "specs init corta o branch (Recommended)"; "Agente arruma, sem perda (Recommended)"; "Só reporta (Recommended)"; "Converter em teste de recusa (Recommended)".

Decided by law (agent default, unruled — reason: the law decides):

- Q1: the WT stays in `dd-gitflow-default/scripts/`, and `dadaia worktree` is a thin runner of it (ASIS §3 seam 1).
- Q3: audits keep their direct-write law.
- Q5: the cutover follows §6.
- Defects B, C (all but `_plain_base`), E and F are fixed at HEAD and are not re-registered (ASIS §1.2).

---

## Bug window review

**Window:** fixes closed after `00edfadff` (rc-15's define base, 2026-10-13T14:44Z), from `BUGS.jsonl` and `_archive/bugs_histo.jsonl`. That gives **37 resolved bugs**, none archived:

- 36 are the ids in rc-15's last closure summary (`_RELEASE.json`, ts 2026-10-14T19:53:08Z).
- The 37th is the hotfix `release-check-memory-task-check-reads-retired-tasks-md` (`23e182e19`). `rc-15/SPEC.md:179` named it open, and no window has judged it. Agent default, unruled: it is included, for that reason.

Each fix was read with `git show`, and each series with `git log` over its unit. The sha column lists the whole series, because the ledger `fix_sha` is only its last commit. Verdicts: 27 KEEP, 10 REBUILD in five units, R1–R5.

| bug id | fix sha(s) | unit | verdict | reason (evidence) |
|---|---|---|---|---|
| `release-check-memory-task-check-reads-retired-tasks-md` | `23e182e19` | release-check (`_release_tree.py`, `_release_schema.py`) | REBUILD R1 | first of four fixes on one unit in the window; +5/-2 on a second reader of retired state |
| `release-check-names-the-memory-pass-an-operator-action` | `5c964ae7b`, `52d086a0d` | release-check | REBUILD R1 | label fix on `_release_tree.py` (+4), the third touch of the unit's findings (`52d086a0d` stat) |
| `release-check-info-origin-rows-carry-a-fix` | `1454be5f9`, `0a8902e64` | release-check | REBUILD R1 | a REBUILD (`_findings.info`), but the same function `_origin_row` is edited by the next row's fix a day later |
| `release-check-origin-sweep-reads-a-retired-log-kind` | `8d807208c`, `49163dacd` | release-check | REBUILD R1 | `_swept` now keys on the closure summary; three more readers still decide which summary counts (`_release_tree.py:133,145`, `release.py:194-220`) |
| `mem-placeholder-fix-deletes-a-memory-file-that-mentions-a-token` | `f4063ae8d` | `doctor_memory.py` placeholder detector | REBUILD R2 | CRITICAL; substring detector turned into a frontmatter test (`:63-70`) and the `--fix` still unlinks files |
| `mem-placeholder-fix-deletes-an-atom-the-operator-filled` | `48f70750a`, `c974efbe5` | `doctor_memory.py` | REBUILD R2 | CRITICAL; second data-loss fix within a day on the same detector; adds a hard-coded legacy-template table (`:42`) |
| `doctor-ledger-lane-absent-specs-dir-fix-never-clears` | `ff1f3b3d3`, `7bc7f26e5` | `ledger_scripts.script_findings`, `cli/commands/doctor.py` | REBUILD R3 | third fix on the lane's absent-tree fallback (the commit body names two prior bugs); it layers `_absent_tree` and `target = None if absent` into `doctor()` (`doctor.py:196,303-304`) |
| `worktree-merge-crashes-with-a-traceback-when-the-job-tree-is-gone` | `53107aeed`, `7682b3a92`, `7b84a7ff5` | WT error edge (`worktree.py`, `_worktree_end.py`) | REBUILD R4 | the ledger sha is a help-text edit; the third crash of the class ends in two `except` arms and an `Operator action` for an agent act (`worktree.py:78-83`) |
| `worktree-list-hides-a-non-empty-stray-directory` | `f1f7aad93`, `ffa34bb48` | WT `list` (`_worktree_git.py` `_absent`) | REBUILD R4 | per-row patch of one function (+4/-1), the list logic the hierarchy demand replaces |
| `init-reports-same-when-the-venv-probe-fails` | `9e4bb5a28`, `1e52fb25c` | `python_env.version_change`, `init._reconcile_upgrade` | REBUILD R5 | the "repair" case is a `before` is None branch in the printer (`init.py:194`) and a ternary in the decider (`python_env.py:488`); the decider already returns `action` |
| `scorecard-fix-3-left-the-repo-specs-law-stale` | `2108a984c` (RED), `142095c44` | specs law mirrors | KEEP | RED widened the test filter to every `AGENTS.md` (tighter); 19 mirror files refreshed by the doctor render, net -3 |
| `mutate-owner-import-writes-checkout-bytecode` | `da4bbb99a` | `scripts/mutate.py`, `certification/service.py` | KEEP | REBUILD of the entry; certification env now built by `_git.scrubbed_env` (net -2 in the package); `sys.dont_write_bytecode` before first import is the convention of 8 entries (`audit.py:21` ...), not a new path |
| `backlog-exit-refuses-on-an-unrelated-spec-origin` | `ab690576f` (RED), `2eba6ed5e` | `_backlog_exit._release` | KEEP | REBUILD, the exit reads only the `--release` SPEC (+16/-13); no assert edited |
| `preflight-skips-checks-merge-runs` | `3420e5976` (RED), `d2cea6103` | `_worktree_end._kind_checks` | KEEP | REBUILD, preflight is merge minus the verdict (`_worktree_end.py:355-399`); the composition the hierarchy gate reuse needs |
| `verdict-validation-stated-three-ways-without-the-reviewed-tree` | `d2cea6103`, `6f882432c`, `fd82f9c2b` | gate fix line, `verdict.py`, `dd-handoff-emitter` SKILL step 7 | KEEP | three statements collapsed to one owner (the writer); ledger sha is the SKILL edit (+3/-3) |
| `verdict-writer-emits-a-handoff-the-schema-rejects` | `cb6f34e3f` (RED), `6f882432c` | `verdict.py` | KEEP | writer validates its own file and unlinks it on failure (+37/-2); growth is the rc-15 G3 FR8 reason, one validation owner |
| `verdict-context-pattern-disagrees-with-core` | `710554fee` (RED), `d072cd85e` | `verdict.py`, `_grammar.py` | KEEP | one kernel grammar read by core and the writer (+8/-7) |
| `check-reads-crash-on-non-utf8-input` | `712484919` (RED), `b0f986e54`..`c449b3779` | `_jsonl.py`, `python_env` digest | KEEP | one kernel decode-aware reader; HEAD `_jsonl.py:51-57` takes the line from `exc.start` with no second scan; one child bug (next row) was fixed in-window |
| `check-verbs-text-output-drops-the-fix-line` | `09d0d6717` (RED), `26e8f0ad4`..`ec7e4cf48` | fix-line printers | KEEP | five verb printers on one kernel renderer, net -6 on the last commit; spelling owner `_refusal.py:21` |
| `doctor-specs-dir-file-reads-as-a-foreign-tree` | `0c3b7a923` (RED), `f4433343d`, `43be3fdf9`, `963cdb310`, `9f300b4a1` | `core/specs_version.state`, `core/gitflow.py` | KEEP | REBUILD, two probes collapse into `specs_path_kind` (net -9); the FIFO and file kinds stay pinned by the unchanged canon tests |
| `specs-init-on-a-file-crashes-with-a-traceback` | `ea975c41f` (RED), `d6985eb19`, `9f300b4a1` | `cli/commands/specs.py`, `state()` | KEEP | same series as the row above, one commit resolves both |
| `specs-dir-symlink-refusal-prints-no-fix-line` | `bf42f2d50` (RED), `537233467` | `core/invocation.resolve_specs_dir` | KEEP | the refusal becomes the one `DadaiaError` shape `fail()` prints as a fix line (+4/-4) |
| `e2e-bootstrap-fixture-seeds-a-venv-without-python` | `427d7966c` (RED), `ae2d5c349`, `333a6c371`, `33c304189` | `tests/fixtures/stores.py` `fake_venv` | KEEP | REBUILD of three seeders into one home (+18/-34); the test seeds a state a real venv has |
| `init-oserror-from-the-venv-interpreter` | `3614b020f` (RED), `133b8c89a`, `835772b75`, `1f2e57da6`, `4d5e767d0`, `d2bd75b30` | `python_env` venv-python runs | KEEP | REBUILD `133b8c89a` (+36/-26): one runner turns `OSError` into the refusal; the ledger sha is a docstring edit |
| `test-doctor-judges-no-instance-cannot-tell-fenced-from-crashed` | `0d0fbd910` | `tests/scripts/test_ci.py` | KEEP | test-only, +3 asserts; a tightening (a crashed doctor now fails) |
| `verdict-refusals-print-no-fix-line` | `c165046de` (RED), `6a1cd01fa`..`1899b2863` | `verdict.py`, `_refusal.py` | KEEP | every refusal goes through one kernel printer; the ledger sha is a 1-line quote edit in `registry.py` |
| `worktree-no-work-branch-fix-names-the-tag-derived-version-not-the-live-release` | `cd92ebf29` (RED), `4e098074c`, `7777ebd43`, `b10444ce5` | `_grammar.sole_live` | KEEP | REBUILD of the one-live rule into one owner (`_worktree_git.py:88,110`); ledger sha is a docstring |
| `bug-lineage-refuses-a-task-id-of-the-historical-grammar` | `b0f3d7a38` (RED), `35d0c8b98` | `_bugs_check.tasks`, `_grammar.py` | KEEP, noted | net -2 in the reader, but `HISTORICAL_TASK_RE` (`_grammar.py:21`) is a second task grammar, finite history only; it carries `J[A-Z].S..`, the `.S<m>` shape the hierarchy demand retires |
| `adr-superseded-citation-judges-the-generated-adr-list-block` | `1e5d26896` (RED), `a6cddda33` | `doctor_adr.py` | KEEP | scan reads `authored_text` (`doctor_adr.py:78`); the generated-block class was REBUILT onto one reader (`a1654984f`, `d67cfa3a5`) in the same series |
| `mem-drift-2-judges-the-generated-adr-list-block` | `47567ca7f` (RED), `a1654984f`, `d67cfa3a5`, `beb24bde5` | `citations.py`, `doctor_adr.py`, `memory_lint.py` | KEEP | one reader `core.fixed_sections.authored_text` for every memory judge (4 call sites, `citations.py:230`, `memory_lint.py:147`); `beb24bde5` is a one-line regex tightening |
| `cli-line-guard-judges-the-generated-adr-list-block` | `5913791d6` (RED), `2192e2e46`, `c54cbf98c`, `51119a027`, `4abd0df01` | `scripts/guards/repo.py`, 5 test scans | KEEP, noted | the test side reads `authored_text` (`repo.py:329,502`); five fixes in one family were caused by the single decision to render a generated block into an authored file, and the adversarial-block proof test now guards every reader |
| `memory-entry-until-breaks-when-the-reconcile-tree-rebases` | `5b64988f5`, `04510a316` | `_release_store.py:63-67`, `_memory_drift.py` | KEEP | REBUILD of the window start (+19/-20): candidates newest first, first one HEAD reaches; the later bug of a chain (`memory-window-bound-shallow-clone-named-as-rebase`) |
| `restore-and-reinstall-fix-lines-name-an-operator-action` | `d05b1a6b4` (RED), `5c964ae7b`, `52d086a0d` | `_jsonl.py`, `reinstall_fix` | KEEP | child of `check-reads-crash...`: its first relabel printed a `git checkout` discard; HEAD names the re-encode of the one bad line and `reinstall_fix(start)` (`_jsonl.py:25-49`) |
| `agent-acts-are-labelled-operator-action` | `dd5dd7df2`..`6ea866584`, REBUILD `764651946` | fix-line grammar across the package | KEEP | ADR 0263 adds the `Agent action:` form; 122 `Agent action:` literals vs 20 `Operator action:` by `git grep`, judged by `fix_defect` (`tests/core/test_cli_line__fix_line_contract.py:94`); ledger sha is a skill-name edit |
| `states-file-write-block-prints-public-install-as-its-fix` | `3a10072c5` (RED), `10bff2858`, `a23e1d65c` | `workspace_layout.py:93,130`, `gate_policy.py` | KEEP | one new member in the two total tables (`FloorRefusal.STATE`), no branch; the hierarchy gate edit touches the same files |
| `guard-fix-lines-keep-placeholders` | `f2140a625` (RED), `52739ac3c` | `scripts/guards/repo.py` | KEEP | +3/-3, the guard prints the real file and owner |
| `ship-archive-never-reaches-the-next-work-branch` | `cfe37ae02` (RED), `fb127322a` | work-branch decider (`_worktree_git.work_versions`, `core/gitflow.py`, `dd-gitflow-default` step 11) | KEEP, noted | REBUILD, three disagreeing deciders become one rule read by every tree and the push gate; +76/-43 in 9 files, so it grew; the hierarchy replaces the work-branch concept, so the unit is rewritten there anyway |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened):

- Job 1 takes R1 (one closure-summary reader, AC1.1–AC1.2), R2 (report-only, AC1.3) and R5 (`repair`, AC1.4).
- R2's fix form is `Agent action`, by ruling. The window's draft said `Operator action`.
- Job 5 takes R4: the WT error edge and the orphan rows, rewritten on the new layout (AC5.5).
- Job 6 takes R3: the absent `--specs-dir` lane (AC6.4).
- Job 5 keeps green the contract tests of the landed REBUILDs `fb127322a`, `d2cea6103` and `4e098074c`.
- Job 3 edits `HISTORICAL_TASK_RE`.
- Two of rc-15's three non-blocking findings are R1. The third, `release-lifecycle.md:27`, is fixed in the memory pass (AC10.1).

## 1. Problem

The worktree layer is the library's most churned surface: 49 bugs, 13 of them in verdict and gate, and 91 commits from 09-30 to 10-13. ASIS §1 finds four structural causes:

- **No rc level.** Jobs merge straight into `feature/<v>`, which therefore holds the jobs of rcs still open. Abandoning an rc reverts N merges.
- **Three base deciders.** The name regex, a base recorded in git config (`plain`) and the work-branch rule each decide the base. `plain` takes any slug; it was used for a bug fix and for a promote. Its path tail starts one level too deep, so a `[protected]` glob misses it (`protected-globs-miss-a-plain-tree-path`, HIGH, security).
- **Special cases.** These are the `--` separator, the define gate row, the closure exception for the next define tree (ADR 0241), and a `reconcile` tree that opens while a job is open (`new-reconcile-opens-while-a-job-is-open`).
- **No chokepoint.** A raw `git worktree add`, or a raw `git merge` into `feature/*`, passes every hook.

## 2. Measurable Goals

- G1. `bugs.py status --specs specs` lists neither Origin bug as open at closure.
- G2. There is one base decider. `git grep -nE 'dadaia-base|recorded_base|record_base|_plain_base' -- dadaia_workspace` prints nothing, and AC5.2 is green.
- G3. The CLI is the only path. AC4.3's real-git test refuses a raw `worktree add -b wt/x` and a raw merge into the work branch, and lets `git pull` through.
- G4. There is one grammar. The AC7.2 sweep prints nothing, and so does `grep -rnE -- '-rc<N>/|<job>--|wt/hotfix/|wt/backlog/' dadaia_workspace/public`.
- G5. Size readout, never a gate. The closure summary records `git diff --shortstat <rc-16 cut>..<wt head> -- dadaia_workspace scripts`. ASIS §6 estimates +15 python lines (range −10 to +60) and +40 shell lines: four new capabilities against about 115 deleted lines. Python growth above +60 names its reason.
- G6. The closure summary holds `verdict.py stats 0.5.0-rc16` (a readout).

## 3. Requirements

FR<n> is Job <n>, and its ACs are AC<n>.<k>, the same ids the job files use.

**Wave ranking.** The pick has one subject, the dev loop:

- Wave 1: the foundation and the chokepoint, Jobs 1–4.
- Wave 2: the layout, Job 5.
- Wave 3: the consumers, law text, `sync` and onboarding, Jobs 6–9.
- Wave 4: the Reconciliation, Job 10.

Law text is Wave 3 (agent default, unruled — reason: text written for behaviour that is not yet built drifts). Job 5 waits on Job 2, Jobs 6–9 wait on Job 5, and Job 10 waits on all.

**Merge order:**

1. Job 2 merges first of all rc-16 jobs (`block: security`).
2. Jobs 1, 3 and 4.
3. The main thread's cleanup of off-grammar trees (§6 Cutover).
4. Job 5, as late as Wave 2 allows.
5. Wave 3.
6. Job 10.

### Wave 1 — foundation and chokepoint

#### FR1 — bug-window REBUILDs R1, R2, R5 (Job 1; independent tasks in parallel)

- AC1.1 (unit, RED first; R1): one reader in `_release_schema.py` returns the live candidate's closure-summary fields (delivered, carried, exits). It reads them from the last `kind: summary` entry at or after `defined.ts`, past DEFINITION.
  - An Origin id found only in the previous candidate's summary reads `untraced`.
  - A bug that summary carried does not satisfy this candidate's `--allow-open`.
  - `_trace` matches inside field values only, so an id equal to a label word (`carried`) is untraced.
- AC1.2 (no test — reviewer `git grep`; R1): `_last_summary` and `release.py`'s summary partition leave, and `_swept`, `_trace` and `_refuse_unauthorized` consult the one reader. `_SUMMARY` stays the one grammar. The R1 contract tests in `test_release__lean_state.py` and `test_release__release_script.py` stay green unedited. Net production lines ≤ 0.
- AC1.3 (unit, RED first; R2; operator: "Só reporta (Recommended)"): doctor reports an atom that still holds a placeholder token, with `fix: Agent action: fill or delete the atom <path>`. `doctor --fix` leaves every memory file byte-identical. `_TEMPLATE_LINES` and the unlink leave. The "mention is not flagged" and "filled atom survives `--fix`" partitions stay. The tests asserting that `--fix` removes a pure-template atom now assert that it survives; this ruling changes that product contract, and the `test(...)` commit names it.
- AC1.4 (unit, RED first; R5): `version_change` returns `repair` when the entrypoint exists and its probe fails, and `init` prints from the action (`repaired -> B`). The `before is None` ternary leaves. The `-k probe_fails` and decider tests stay green. Net ≤ 0.

#### FR2 — delete `plain`; the sanction marker (Job 2; operator: "Apagar o tipo plain")

- AC2.1 (unit, RED first): every git child of `_git.scrubbed_env()` and of the package git client carries `DADAIA_WT=1`, and still drops the repo-selecting `GIT_*` variables.
- AC2.2 (unit, RED first; bug `protected-globs-miss-a-plain-tree-path`): `new <repo> <one-segment>` refuses the name as not a worktree name, with the `list` fix line, and `list` has no plain row, so no tree can open whose tail starts one level too deep. The fix commit's body names `block: security`. AC5.1 pins the glob at every new depth.
- AC2.3 (unit; operator: "Converter em teste de recusa (Recommended)"): no test is deleted.
  - Each plain-only test becomes a test that the plain name is refused with its fix line: `test__worktree_new.py:135,176,249`, `test__worktree_end.py:612,631` with its `:640` `dadaia-base` assert, `test__worktree_end__preflight.py:134` and `test__worktree_end__verdict_binding.py:170`.
  - A test that uses plain only as an example runs on a job tree with every assert intact.
- AC2.4 (no test — reviewer `git grep`): these leave: `plain()`, the plain alternative of `NAME_RE`, `record_base`, the plain half of `recorded_base`, `_plain_base`, the plain row of `_kind_checks` and the `branch.<b>.dadaia-base` config.
- AC2.5 (unit, RED first): the SKILL-MD-LENGTH fix line opens no plain tree. It reads `Agent action: add the split of <skill>/SKILL.md to a task of the open rc, then run public install`, with real values, and it still clears its finding.

#### FR3 — retire `.S<m>` (Job 3)

- AC3.1 (unit, RED first): `TASK_ID_RE.fullmatch("J1.S3.T1")` is falsy and `fullmatch("J13.T6")` is truthy. `release.py check` refuses a job file with the task id `J1.S3.T1`.
- AC3.2 (unit): `bugs.py check` still accepts a resolved bug whose `caused_by` is `J1.S3.T1` when an archived `tasks/job1.md` carries it, because `HISTORICAL_TASK_RE` gains the `.S` form for lineage only (ASIS H6). If no live caller uses the `## Stage` parse, it leaves; otherwise the task reports it.

#### FR4 — ref gate, hook, CLI group (Job 4; operator: "Verbo CLI + git hook")

- AC4.1 (unit, RED first): `branch_policy.check_ref_policy` refuses moving a work-role ref (`Gitflow.role_of == "work"`) to a sha other than `refs/remotes/origin/<same>`, with one runnable fix line. It passes:
  - a move to origin's sha;
  - creation and deletion;
  - non-work refs;
  - an update whose `old..new` touches only `specs/audits/**` (Q3, which reuses the `audit` zone predicate).
- AC4.2 (integration): `dadaia ci ref-gate-check` reads `old new ref` lines on stdin. A refusal exits 1 with `[ref-gate] BLOCKED …` and one `fix:` line; anything else exits 0. The gitflow comes from `_gate_inputs`.
- AC4.3 (integration, real git, hook installed):
  - Raw `git worktree add -b wt/x` is refused; with `DADAIA_WT=1` it passes.
  - A commit in a `wt/*` tree passes with no python call.
  - `git branch -D wt/x` passes (ASIS H2).
  - Raw `merge --ff-only`, `reset --hard` and `commit` on the work branch are refused.
  - `git pull --ff-only` and `git branch -m` pass.
  - An unresolvable runner warns and exits 0. Agent default, unruled — reason: the hook fires on every ref update, and pre-push stays the chokepoint that fails closed.
- AC4.4 (unit): HOOKS-DRIFT-1 reports the `reference-transaction` row absent, and `install_git_hooks` writes it. This needs one `INSTALLED_GIT_HOOKS` row and one `shipped-hashes.json` entry, and no change to the installer code.
- AC4.5 (integration): `dadaia worktree <verb> …` forwards argv, stdout and exit code to the installed `worktree.py`, and `--help` lists the verbs. With no script installed, it refuses with `fix: <dadaia> public install`.

### Wave 2 — the layout

#### FR5 — the hierarchy (Job 5; operator: "Integração real", "Reusar o gate de job"; carries R4 and defect A)

The layout is `worktrees/<repo>/<v>/{wt-hotfix-<bug>, wt-backlog-<slug>, rc-<N>/{wt-rc, job-<n>/{wt-main, wt-task-<k>}}}`. Each branch is `wt/` plus the path under `worktrees/<repo>/`.

- AC5.1 (unit, RED first; defect A): `locate` keys on the first `wt-` segment.
  - `worktrees/<r>/<v>/rc-N/job-n/wt-task-001/secrets/k` gives `(r, "<v>/rc-N/job-n/wt-task-001", ("secrets", "k"))`.
  - A path with no `wt-` leaf gives `(r, None, ())`.
  - A `[protected]` glob is PROTECTED at lane, rc, main and task depth (`classify_path`).
- AC5.2 (unit, RED first): `kind_of` reads the leaf: `wt-rc`, `wt-main`, `wt-task-NNN`, `wt-hotfix-<bug>` or `wt-backlog-<slug>`. `base_of` maps task → `wt-main` → `wt-rc` → `<work><v>`, and a lane → `<work><v>`. `pushable` holds for rc, main and backlog only.
- AC5.3 (integration, RED first): `new` opens each kind on its parent's branch, and `<v>` must name an existing local `<work><v>`.
  - `wt-main` needs IMPLEMENTATION in the `_RELEASE.json` on its rc's `wt-rc`.
  - A task needs its `wt-main`.
  - A hotfix needs its open bug.
  - An old-grammar name refuses with a fix line in the new shape.
- AC5.4 (integration, RED first): `merge` by kind:
  - task → main: hygiene and test separation;
  - main → rc, and hotfix → `<work><v>`: the job gate;
  - backlog → `<work><v>`: specs-only plus ledgers;
  - rc → `<work><v>`: the job gate plus ledgers.

  An open child blocks its parent. `merge` fast-forwards in the parent's checkout. `_check_approved`, `_gate`, `_ledgers`, `_check_specs_only` and `_check_ancestor` stay untouched.
- AC5.5 (integration; R4): `list` counts `ahead` against the parent branch. It reports an orphan `wt/*`, a non-empty stray and an empty stray at any depth, one row per path, each with its removal fix. The row schema is frozen (ASIS §3 seam 12). A `GitError` in any verb ends as one refusal with one fix line, an `Agent action` where an agent can rerun.
- AC5.6 (no test — reviewer diff check): every test and fixture that names the old grammar is ported with the same assert strength.

### Wave 3 — consumers, law, sync, onboarding

#### FR6 — consumers (Job 6; carries `new-reconcile-opens-while-a-job-is-open` and R3)

- AC6.1 (unit, RED first; the bug): `release.py phase CLOSURE` refuses, naming the tree, while a job, task or lane tree of the repo is open. It passes when only `wt-rc` trees are open. The `f"{nxt}/define"` exception leaves. Reconcile becomes the last commits of `wt-rc`, and no `reconcile` kind is left to open early.
- AC6.2 (unit, RED first): `verdict.py stats <M.m.p>-rc<N>` counts the trees under `wt/<M.m.p>/rc-<N>/`, and the binding runs through `dadaia worktree hash`.
- AC6.3 (unit, RED first as `test(...)`): every fix line that named `worktree.py` names `dadaia worktree …`. `grep -rn 'worktree\.py' dadaia_workspace .github scripts` hits only the runner's resolve constant and the script's own docstring.
- AC6.4 (integration; R3): an explicit `--specs-dir` that holds no tree reports one finding, from the specs-section builder, carrying `state()`'s fix. The ledger lane keeps one guard. `_absent_tree` and the `target = None` reassignment leave. The REDs are the three predecessor bugs' cases with their asserts unchanged. Net ≤ 0.

#### FR7 — law, skills, agents, templates (Job 7; text only)

- AC7.1 (no test — law text; reviewer AI-surface lens; `public doctor` prints `[ok] public-privacy`): `worktrees-AGENTS.md` states the hierarchy, the leaf names, the merges, the lanes, `sync` and the hook in at most 39 lines, today's count.
- AC7.2 (no test — sweep): the ASIS J6.T2 sweep prints nothing over:
  - the files of ASIS §2.2;
  - `specs/releases/AGENTS.md:27`, where "define tree" becomes `wt-rc`;
  - `dd-gitflow-default` shape 9, where the first-pass tree becomes `wt-backlog-first-pass`.

  `WT` reads `dadaia worktree`, and `test_gate_policy__law_states_what_the_code_does.py` stays green.

#### FR8 — `sync` and level `AGENTS.md` (Job 8)

- AC8.1 (integration, RED first, real git; operator: "Lanes laterais para ambos"): `dadaia worktree sync <path>` rebases parents before children.
  - The order is `wt-rc` onto `<work><v>`, each `wt-main` onto `wt-rc`, then each task onto its `wt-main`.
  - It skips a tree that already contains its base.
  - At the first conflict or dirty tree it stops, names that tree and exits 1 with one fix line. A re-run completes the cascade.
  - It never pushes.
  - After a lane merges, `sync <rc>` makes the rc's merge pass.
  - `_check_ancestor`'s fix names `dadaia worktree sync <tree>`.
  - Agent default, unruled — reason: the smallest cascade the existing predicates allow.
- AC8.2 (integration, RED first; operator: "é so porque eu não quero criar .gitkeep files ... deve estar na criação"): `new` writes a 5–10 line `AGENTS.md` once into each folder it creates (`<v>/`, `rc-<N>/`, `job-<n>/`) and never over an existing one. `merge` and `clean` remove a level folder that holds only that file, and `list` reports no stray for it.

#### FR9 — onboarding without `plain` (Job 9; operator: "specs init corta o branch (Recommended)")

- AC9.1 (integration, RED first): on a repo with no work branch, `dadaia specs init --context <ctx>` leaves a local branch `<work><next_version>`. With a work branch present it cuts nothing. It pushes nothing.
- AC9.2 (integration): the ONBOARDING `first-pass` fix line opens `dadaia worktree new <repo> <v>/wt-backlog-first-pass` and runs the first pass there. `context baseline` publishes as today, and its tests stay green unedited. The tree it sees is the open question in §7.

### Wave 4 — promote-facing

#### FR10 — Reconciliation (Job 10, last; rc-16's own old-layout tree)

- AC10.1 (no test — `MEMORY-UPDATE.md` in full): the atoms of ASIS §2.3 are told true.
  - `worktrees.md` is rewritten whole, which closes defect B.
  - `release-lifecycle.md:27` reads "the newest `until` HEAD reaches opens the window".
  - `memory.py check` exits 0.
- AC10.2 (no test — derived docs): `docs/*.md`, `README.md` and `CONTEXT.md` (ASIS §2.3) name the hierarchy and `dadaia worktree`.
- AC10.3 (no test — closure check): §4's exits are recorded, G5 and G6 are in the closure summary, and `release.py check` exits 0.

## 4. Exits at closure

- `worktree-hierarchy` exits `delivered`.
- `protected-globs-miss-a-plain-tree-path` resolves on Job 2's fix (AC2.2), and `new-reconcile-opens-while-a-job-is-open` on Job 6's (AC6.1).
- **Rollout**, a main-thread act after the Reconciliation merge and not a job task (Q5): `public install` projects the new WT, the hook and the law; then `ci install-hook` runs in each repo, which clears HOOKS-DRIFT-1; then `doctor`. The new layout applies from rc-17.

## 5. Not in rc-16

- `worktree-layout-per-context` stays an idea ("O resto confirmamos"); every other `active[]` entry stays untouched.

## 6. Constraints and risks

### Replaces

- The `plain` kind, its recorded base (`record_base`, `recorded_base`, `branch.<b>.dadaia-base`, `_plain_base`) and its gate row become a refused name. A bug goes to a hotfix lane or a next-rc job, and a promote to PR + `release.py ship` (FR2).
- Plain-only tests become refusal tests (FR2).
- The SKILL-MD-LENGTH fix that opened a plain tree becomes an agent act in a task of the open rc (FR2).
- `TASK_ID_RE`'s `.S<m>` is kept only in `HISTORICAL_TASK_RE`, for lineage (FR3).
- A raw `worktree add`, merge, reset or commit on a work branch is refused by the hook (FR4).
- `NAME_RE`'s six alternations (`<M.m.p>-rc<N>/<job>[--<task-id>]`, `backlog/<slug>`, `hotfix/<bug>`) and the `--` separator become one leaf grammar, branch = `wt/` + path (FR5).
- `locate`'s fixed two-segment guess becomes the first `wt-` segment (FR5).
- Jobs merge into `wt-rc`, not `feature/<v>` (FR5).
- The `define` and `reconcile` kinds and their special cases become the first and last commits of `wt-rc` (FR5). Those cases are the define gate row, `pushable`'s define exclusion, `new`'s phase skip and the `== "define"` tests.
- `_open_tasks`' `startswith(f"{name}--")` becomes `_open_children` by path (FR5).
- `_refuse_unready` reads `_RELEASE.json` from the rc's `wt-rc`, not the work branch (FR5).
- `worktree.py main`'s two `except` arms ending in `Operator action`, and `_absent`'s per-row patch, become one `GitError` edge and one row per path (FR5, R4).
- Closure's exception for the next define tree becomes "any open tree but a `wt-rc` refuses" (FR6).
- `verdict.py stats`' prefix `wt/{rc}/` becomes `wt/<M.m.p>/rc-<N>/` (FR6).
- Fix lines that name `worktree.py <verb>` name `dadaia worktree <verb>` (FR5, FR6).
- doctor's `_absent_tree`/`target = None` fallback becomes one specs-section finding (FR6, R3).
- The seven-kind `worktrees-AGENTS.md` and the old grammar in skills and agents become the hierarchy text (FR7).
- Per-agent `git rebase <work>` becomes `dadaia worktree sync` (FR8).
- Onboarding's first-pass plain tree becomes the `wt-backlog-first-pass` lane (FR9).
- `doctor --fix` deleting a placeholder atom, and `_TEMPLATE_LINES`, become report-only (FR1, R2).
- The four closure-summary readers become one (FR1, R1).
- `version_change`'s `before is None` ternary becomes the `repair` action (FR1, R5).
- ADRs 0125, 0191 and 0241, and 0120's "a wt/ branch is never pushed as a branch", are replaced by ADR 0264.

### Governance

- ADR 0264 is proposed here with `supersedes` and `amends` null, because the doctor refuses an unruled record that names an accepted one.
- Only the operator accepts 0264. Its accept commit writes `supersedes: "0125,0191"` and `amends: "0120"` (0120's push clause) with the ruling, and flips 0125 and 0191 to `superseded`.
- 0241 is retired with 0191's layout (AC6.1); the accept ruling names it.
- Job 5 merges only after that acceptance, because its code contradicts 0191.

### Cutover (Q5; ASIS H1)

- The package reads the WT grammar from the editable checkout, while the instance's WT runs from `.agents/`. When Job 5 merges, `locate`, `kind_of`, `pushable` and closure flip live.
- **The cleanup runs before Job 5's merge.** It is a main-thread step between Waves 1 and 2, not a job task (operator: "Agente arruma, sem perda (Recommended)"). In every repo, the agent deletes empty dirs and `wt/*` branches with no commit of their own. It turns a tree holding its own work into the tag `archive/wt/<name>` before removing it. There is no migration code. The known trees are `worktrees/rand-engine/0.8.0-rc1/define`, `worktrees/<consumer>/0.12.0b-impl` and the branches `wt/0.12.0{a,b,c}`. rc-16's own define tree merges before implementation starts.
- After Job 5 merges:
  - job branches are local-only, `verify:` runs at merge, and `feature/0.5.0` pushes continue;
  - doctor shows PROJECTION drift until the rollout (§4).
- Protected-glob exposure in this instance is nil, because `.dadaiaignore` has no `[protected]` section.

### Delivery constraints

- No test or assert is removed or loosened. The tests change only where two rulings order it: AC2.3 converts the plain-only tests, and AC1.3 changes `--fix`.
- Gate cost (root map §1): the `wt-rc` merge adds one `verify:` run and one review per rc. The hook's shell path costs about 0 s. Its python path costs 0.24 s and runs only on an unmarked move of a non-`wt/` head (ASIS §3 seam 13).
- Public needs only shell and local git. Platform facts go through `core/platform.py`. Memory changes only at the Reconciliation.

### Risks

| risk | control |
|---|---|
| a hook false positive blocks `git commit` | it fails open on a runner fault, and the shell fast path passes `wt/*` (AC4.3) |
| a forged marker | a speed bump: pre-push and review stay the chokepoints |
| a `sync` conflict mid-cascade | it stops at the first conflict with one fix line, and a re-run finishes (AC8.1) |
| an old-grammar tree still open at Job 5's merge | the pre-Job-5 cleanup (Cutover) |

## 7. Open questions

- **For the grill: FR9 against `specs init`'s "never committing" contract** (`cli/commands/specs.py:141`).
  - The problem: a lane cut from the new `<work><v>` cannot see the specs tree that `specs init` left uncommitted. If the lane writes memory files anyway, `context baseline` meets them as add/add conflicts against its anchor commit (`service.py` `baseline`). The ruling's stated cost was only "+≈6 lines".
  - (a), agent default, unruled: `specs init` commits its tree as the first commit of the branch it cuts, and `baseline` publishes that branch. The cost is two changed product contracts.
  - (b): Job 9 stops at AC9.1, and AC9.2 waits for a ruling.
