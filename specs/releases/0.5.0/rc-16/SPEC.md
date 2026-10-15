# SPEC — Release: 0.5.0, candidate 16 — the worktree hierarchy

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-14
**Origin:** backlog:worktree-hierarchy; bugs:new-reconcile-opens-while-a-job-is-open

Sources: the as-is review at `13e3fc074` (ASIS, `.dadaia/reports/dadaia-workspace/rc16-definition/ASIS.md`, PLAN §1; H1–H9 by id), the bug window (`.dadaia/reports/dadaia-workspace/rc16-definition/BUG-WINDOW.md`), the grills of 2026-10-14, the `worktree-hierarchy` entry, and the define review of `411f0cf13` (REJECTED). Paths are relative to `repos/dadaia-workspace/`. The decision is ADR **0264**.

Operator rulings, verbatim:

- Backlog grill: "Integração real"; "Lanes laterais para ambos"; "Verbo CLI + git hook"; "Apagar o tipo plain"; "Reusar o gate de job". On the per-level `AGENTS.md`: "é so porque eu não quero criar .gitkeep files ... deve estar na criação". On the agent defaults (leaf names `wt-rc`, `wt-main`, `wt-task-<k>` in 3 digits; branch = path; a `sync` verb; Arm A delivery; per-context layout out): "O resto confirmamos".
- Release grill: "specs init corta o branch (Recommended)"; "Agente arruma, sem perda (Recommended)"; "Só reporta (Recommended)"; "Converter em teste de recusa (Recommended)". On the cleanup's timing: "Antes de instalar o hook em cada repo".
- Definition batch: "Aceito a ADR 0264 (Recommended)"; "specs init commita o scaffold (Recommended)".

Decided by law (agent default, unruled — reason: the law decides):

- Q1: the WT stays in `dd-gitflow-default/scripts/`; `dadaia worktree` is a thin runner of it (ASIS §3 seam 1).
- Q3: audits keep their direct-write law.
- Q5: job branches are local-only from Job 4's merge (§6 Cutover).
- Defects B, C (all but `_plain_base`), E and F are fixed at HEAD and are not re-registered (ASIS §1.2). Defect A is a hotfix outside the rc (§5).

---

## Bug window review

**Window:** fixes closed after `00edfadff` (rc-15's define base, 2026-10-13T14:44Z), from `BUGS.jsonl` and `_archive/bugs_histo.jsonl`: **37 resolved bugs**, none archived. 36 are the ids of rc-15's last closure summary (`_RELEASE.json`, ts 2026-10-14T19:53:08Z); the 37th is the hotfix `release-check-memory-task-check-reads-retired-tasks-md` (`23e182e19`), which `rc-15/SPEC.md:179` named open and no window judged (agent default, unruled: included, for that reason).

Each fix was read with `git show`, each series with `git log` over its unit; the sha column lists the whole series, since the ledger `fix_sha` is only its last commit. Verdicts: 27 KEEP, 10 REBUILD in five units, R1–R5.

| bug id | fix sha(s) | unit | verdict | reason (evidence) |
|---|---|---|---|---|
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
| `bug-lineage-refuses-a-task-id-of-the-historical-grammar` | `b0f3d7a38` (RED), `35d0c8b98` | `_bugs_check.tasks`, `_grammar.py` | KEEP, noted | net -2 in the reader, but `HISTORICAL_TASK_RE` (`_grammar.py:21`) is a second task grammar, finite history only; it carries the `J[A-Z].S..` shape (§5) |
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

- Job 1: R1 (one closure-summary reader, AC1.1), R2 (report-only, AC1.2; its fix form is `Agent action` by ruling, where the window's draft said `Operator action`) and R5 (`repair`, AC1.3).
- Job 4: R4, the WT error edge and the orphan rows on the new layout (AC4.2, AC4.6); it keeps green the contract tests of `fb127322a`, `d2cea6103` and `4e098074c`.
- Job 5: R3, the absent `--specs-dir` lane (AC5.4).
- Two of rc-15's three non-blocking findings are R1; the third, `release-lifecycle.md:27`, is fixed in the memory pass (AC10.1).

## 1. Problem

The worktree layer is the library's most churned surface: 49 bugs, 13 of them in verdict and gate, and 91 commits from 09-30 to 10-13. ASIS §1 finds four structural causes:

- **No rc level.** Jobs merge straight into `feature/<v>`, which therefore holds the jobs of rcs still open; abandoning an rc reverts N merges.
- **Three base deciders.** The name regex, a base recorded in git config (`plain`) and the work-branch rule each decide the base. `plain` takes any slug; it was used for a bug fix and for a promote.
- **Special cases.** The `--` separator, the define gate row, the closure exception for the next define tree (ADR 0241), and a `reconcile` tree that opens while a job is open (`new-reconcile-opens-while-a-job-is-open`).
- **No chokepoint.** A raw `git worktree add`, or a raw `git merge` into `feature/*`, passes every hook.

## 2. Measurable Goals

- G1. `bugs.py status --specs specs` does not list `new-reconcile-opens-while-a-job-is-open` as open at closure.
- G2. One base decider: `git grep -nE 'dadaia-base|recorded_base|record_base|_plain_base' -- dadaia_workspace` prints nothing, and AC4.1 is green.
- G3. The CLI is the only path: AC3.3's real-git test refuses a raw `worktree add -b wt/x` and a raw merge into the work branch and lets `git pull` through; AC9.1 installs the hook.
- G4. One grammar: the AC6.1–AC6.4 sweeps and `grep -rnE -- '-rc<N>/|<job>--|wt/hotfix/|wt/backlog/' dadaia_workspace/public` print nothing, and AC9.2's sweep holds.
- G5. Size readout, never a gate: the closure summary records `git diff --shortstat <rc-16 cut>..<wt head> -- dadaia_workspace scripts`. ASIS §6 estimates +15 python lines (range −10 to +60) and +40 shell lines; python growth above +60 names its reason.
- G6. The closure summary holds `verdict.py stats 0.5.0-rc16` (a readout).

## 3. Requirements

FR<n> is Job <n>; its ACs are AC<n>.<k>, the ids the job files use. A task split for size keeps its AC.

**Wave ranking** (one subject, the dev loop; law text sits in wave 3, agent default, unruled — reason: text written before its behaviour drifts):

| wave | jobs | waits on |
|---|---|---|
| 1 foundation and chokepoint | 1, 2, 3 | — |
| 2 layout | 4 | Job 2 |
| 3 consumers, law, `sync`, onboarding | 5, 6, 7, 8 | Job 4 |
| 4 activation | 9 | Jobs 1–8 |
| 5 Reconciliation | 10 | Job 9 |

Merge order is the wave order; Job 4 merges as late as wave 2 allows. ADR 0264 is accepted by ruling, so no merge waits on it. The cutover is §6 Cutover, stated once; the PLAN and job files point to it.

#### FR1 — bug-window REBUILDs R1, R2, R5 (Job 1; independent tasks in parallel)

- AC1.1 (integration, RED first; R1): one reader in `_release_schema.py` returns the live candidate's closure-summary fields (delivered, carried, exits) from the last `kind: summary` entry at or after `defined.ts`, past DEFINITION. An Origin id found only in the previous candidate's summary reads `untraced`; a bug that summary carried does not satisfy `--allow-open`; an id equal to a label word (`carried`) is not traced by the label. `_last_summary` and `release.py`'s partition leave; `_swept`, `_trace` and `_refuse_unauthorized` consult the reader. The existing `release-check-*` partitions stay green unedited. Net production lines ≤ 0.
- AC1.2 (unit, RED first; R2; operator: "Só reporta (Recommended)"): an atom with an unfilled placeholder is reported with `fix: Agent action: fill or delete the atom`, and `doctor --fix` leaves it byte for byte. `_TEMPLATE_LINES`, the unlink, `rules.py`'s `fix=` pair and the `slop.py:46` allowance row leave. The "filled atom" and "mention is not flagged" partitions are unchanged; the old remove-on-`--fix` assert is rewritten, never deleted (this ruling changes the product contract).
- AC1.3 (unit, RED first; R5): `version_change` returns `repair` for an existing entrypoint whose probe fails, and `init` prints `repaired -> B` from the action. The `before is None` ternary leaves; the decider cases stay unchanged. Net ≤ 0.

#### FR2 — delete `plain`; the sanction marker (Job 2; operator: "Apagar o tipo plain")

- AC2.1 (unit, RED first): `scrubbed_env()`, and the env `git_subprocess._run` builds, carry `{"DADAIA_WT": "1"}` and still drop the repo-selecting `GIT_*` variables.
- AC2.2 (unit, RED first; operator: "Converter em teste de recusa (Recommended)"): no test is deleted. The plain-only tests become refusal tests: `new r maintenance` exits 1 with `not a worktree name` and the `list` fix, and `merge`/`preflight` of a plain name refuse the same way (`test__worktree_new.py:135,176,249`, `test__worktree_end.py:612,631`, `test__worktree_end__preflight.py:134`, `test__worktree_end__verdict_binding.py:170`). The `:640` `dadaia-base` assert becomes "no base is recorded in git config". Example-only tests run on a job tree, the assert count per file unchanged. `plain()`, the plain alternative of `NAME_RE`, `record_base`, the plain half of `recorded_base`, `_plain_base`, the plain row of `_kind_checks` and the git-config base leave.
- AC2.3 (unit, RED first): the SKILL-MD-LENGTH fix reads `Agent action: add the split of <skill>/SKILL.md to a task of the open rc, then run public install`, opens no plain tree, and still clears its finding.

#### FR3 — ref gate, hook script, CLI group (Job 3; operator: "Verbo CLI + git hook")

The hook script ships here and its tests run it in a temporary repo; no installer row names it before Job 9.

- AC3.1 (unit, RED first): `branch_policy.check_ref_policy` refuses moving a work-role ref (`Gitflow.role_of == "work"`) to a sha other than `refs/remotes/origin/<same>`, with one runnable `fix:`. It passes origin's sha, creation and deletion, every non-work ref, and an update touching only `specs/audits/**` (Q3, reusing the `audit` zone predicate).
- AC3.2 (integration, RED first): `dadaia ci ref-gate-check` reads `old new ref` lines on stdin; it exits 1 with `[ref-gate] BLOCKED …` and one `fix:` line on a refusal, 0 otherwise. Its inputs come from `_gate_inputs`.
- AC3.3 (integration, real git): the hook in a temporary repo refuses raw `worktree add -b wt/x`; it passes the same command with `DADAIA_WT=1`, `branch -D wt/x` (old = new = 0, ASIS H2), `pull --ff-only` and `branch -m`; it refuses raw `merge --ff-only`, `reset --hard` and `commit` on the work branch. An unresolvable runner warns and exits 0 (agent default, unruled — reason: the hook fires on every ref update, and pre-push stays the fail-closed chokepoint). Every fix line the hook prints is runnable.
- AC3.4 (integration, RED first): `dadaia worktree <verb> …` forwards argv, stdout and the exit code to the installed `worktree.py`, and `--help` lists the verbs. With no script installed it refuses with `fix: <dadaia> public install`.
- AC3.5 (integration, real git): a commit in an existing `wt/*` tree passes (an update, old ≠ 0) with no python call.
- AC3.6 (integration, real git): creating the tag `archive/wt/<name>` passes.
- AC3.7 (integration, real git): creating a harness-native worktree branch (not `wt/*`, `worktrees-AGENTS.md:7`) passes.

#### FR4 — the hierarchy (Job 4; operator: "Integração real", "Reusar o gate de job"; carries R4)

The layout is `worktrees/<repo>/<v>/{wt-hotfix-<bug>, wt-backlog-<slug>, rc-<N>/{wt-rc, job-<n>/{wt-main, wt-task-<k>}}}`. Each branch is `wt/` plus the path under `worktrees/<repo>/`.

- AC4.0 (no test — support code every owner test exercises): the fixture constants and `tests/helpers/worktree_ws.py` use the new names; the helper's behaviour is unchanged.
- AC4.1 (unit, RED first): `locate` keys on the first `wt-` segment: `worktrees/<r>/<v>/rc-N/job-n/wt-task-001/secrets/k` → `(r, "<v>/rc-N/job-n/wt-task-001", ("secrets", "k"))`. `classify_path` returns PROTECTED at lane, rc, main and task depth. `kind_of` reads the leaf. `base_of`: task → `wt-main` → `wt-rc` → `<work><v>`; a lane → `<work><v>`. `pushable` holds for rc, main and backlog only. `name_of` gives the branch.
- AC4.2 (unit, RED first): `ours` counts `ahead` against the parent branch. `_absent` reports an orphan `wt/*`, a non-empty stray folder and an empty one at any depth, one row per path with its removal as the fix. The `registered:false` rows and the frozen row schema are unchanged. `record_base`/`recorded_base` leave.
- AC4.3 (integration, RED first): `new` opens each kind on its parent's branch. `<v>` must name an existing `<work><v>`; `wt-main` needs `_RELEASE.json` IMPLEMENTATION on its rc's `wt-rc`; a task needs its `wt-main`; a hotfix needs its open bug. Old-grammar and `reconcile` names refuse with a fix in the new shape.
- AC4.4 (integration, RED first): merge by kind. task → main: hygiene plus test separation. main → rc, and hotfix → `<work><v>`: the job gate. backlog → `<work><v>`: specs-only plus ledgers (the `define_gate` tests are ported to this kind, asserts intact). rc → `<work><v>`: the job gate plus ledgers. `merge` fast-forwards in the parent's checkout, and an open child blocks its parent. `_check_approved`, `_gate`, `_ledgers`, `_check_specs_only` and `_check_ancestor` stay untouched.
- AC4.5 (no test — strength-preserving port): the fixtures of the package readers and the hook payloads use the new names with their asserts intact. `test_branch_policy.py` keeps `pushable` and the `archive/wt` tag carve-out. A file already depth-agnostic is left untouched and reported.
- AC4.6 (integration; R4): a `GitError` in any verb ends as one refusal with an `Agent action` fix, and `main` has one `GitError` edge. The `list` rows of AC4.2 are the orphan listing. The contract tests of `fb127322a`, `d2cea6103` and `4e098074c` stay green.
- AC4.7 (unit, kept green; the hotfix's contract, §5): protection never depends on `locate`. A path under `worktrees/<r>/` with no `wt-` segment, such as `worktrees/r/a/b/secrets/k`, stays PROTECTED under the glob `secrets/**`, since the glob is tested against every suffix of the path below `worktrees/<r>/`. The hotfix's tests stay green unedited; this partition is added only if they lack it.

#### FR5 — consumers (Job 5; carries `new-reconcile-opens-while-a-job-is-open` and R3)

- AC5.1 (unit, RED first; the bug): `release.py phase CLOSURE` refuses while a job, task or lane tree of the repo is open, and passes when only rcs' `wt-rc` trees are open. The `f"{nxt}/define"` exception (ADR 0241) leaves. The stacked `release.py new` flow is unchanged.
- AC5.2 (unit, RED first): `verdict.py stats` counts the verdicts of trees under `wt/<M.m.p>/rc-<N>/`. Internal calls stay on the sibling script (`verdict.py:27`, `_release_phase.py:64`); only printed fix lines say `dadaia worktree …`.
- AC5.3 (unit, RED first as `test(...)`): every fix line printed by the gate, the rows reader or the kernel names `dadaia worktree …` and is runnable. The sweep covers this job's `W:` only; the package-wide sweep is AC9.2.
- AC5.4 (integration; R3): an absent explicit `--specs-dir` gives one finding, from the specs-section builder, that carries `state()`'s fix. The ledger lane keeps one guard; `_absent_tree` and `target = None` leave. The three predecessor bugs' cases keep their asserts unchanged. Net ≤ 0.
- AC5.5 (unit, RED first): closure exempts the tree it runs from, whatever its layout. Run from an old-layout `reconcile` tree or from a `wt-rc`, `phase CLOSURE` does not refuse on that tree; another open job, task or lane tree still refuses.

#### FR6 — law, skills, agents, templates (Job 6; text only; no test — reviewer AI-surface lens, `public doctor` `[ok] public-privacy`, sweep = 0 per AC)

- AC6.1: `worktrees-AGENTS.md` states the hierarchy, leaf names, the three merges, the lanes, `sync` and the hook, in fewer lines than its 39 today.
- AC6.2: `dd-gitflow-default` (§2a, §3a, §2 step 11, §5), `RC-FLOW.md` and `dd-release-implementation`: define and reconcile are `wt-rc` commits, and shapes 9 and 10 name their trees; no old grammar word is left.
- AC6.3: the other skills of ASIS §2.2: old tree names and `worktree.py` become the hierarchy and `dadaia worktree`.
- AC6.4: agents, projected map sources, data files, scaffold laws (`releases` "define tree" → `wt-rc`, `bugs` §2 hotfix text), `repo-AGENTS.md` and schema descriptions follow the new names.

#### FR7 — `sync` and the level `AGENTS.md` (Job 7)

- AC7.1 (integration, RED first, real git; operator: "Lanes laterais para ambos"): `dadaia worktree sync <path>` rebases parents first: `wt-rc` onto `<work><v>`, each `wt-main` onto `wt-rc`, then each task. It skips a tree that already holds its base, stops at the first conflict or dirty tree with one fix line, completes on a re-run and never pushes. After a lane lands, `sync <rc>` makes the rc's `merge` pass. The ancestor refusal's fix is `dadaia worktree sync <tree>` (agent default, unruled — reason: the smallest cascade the existing predicates allow).
- AC7.2 (integration, RED first; operator: "é so porque eu não quero criar .gitkeep files ... deve estar na criação"): `new` writes a 5–10 line `AGENTS.md` once into each folder it creates (`<v>/`, `rc-<N>/`, `job-<n>/`), never over an existing file. `merge` and `clean` remove a level folder that holds only that file; `list` shows no stray for it.

#### FR8 — onboarding without `plain` (Job 8; operator: "specs init corta o branch (Recommended)", "specs init commita o scaffold (Recommended)")

- AC8.1 (integration, RED first): `dadaia specs init` on a repo with no work branch cuts the local `<work><next_version>` and leaves it checked out. A rerun with the branch present cuts nothing; nothing is pushed.
- AC8.2 (integration, RED first): `context baseline` on a repo whose local work branch already exists publishes it, anchor-first, and returns the work branch.
- AC8.3 (unit, RED first): the ONBOARDING `first-pass` fix line is `Agent action: open the lane … worktree new <repo> <v>/wt-backlog-first-pass, then run the dd-audit-project first pass in it — <pending files>`. Step order and step kinds are unchanged.
- AC8.4 (integration, RED first): the branch `specs init` cuts carries one commit holding only the scaffold paths; a run that cuts no branch commits nothing. The `test_absent_specs_scaffolds_lists_paths_and_commits_nothing` assert "commits nothing" becomes "commits only the scaffold, on the new branch", in a `test(...)` commit naming the ruling.

#### FR9 — activation (Job 9, after every code job)

- AC9.1 (integration, RED first, real git): `INSTALLED_GIT_HOOKS` gains the `reference-transaction` row and `shipped-hashes.json` its entry. HOOKS-DRIFT-1 reports the row absent in a repo without it, `install_git_hooks` writes it, and the installed hook refuses AC3.3's raw moves. Before this job no installer names the hook.
- AC9.2 (unit, RED first as `test(...)`): every fix line the package prints that names a WT verb reads `dadaia worktree <verb>` and is runnable. `grep -rn 'worktree\.py' dadaia_workspace .github scripts` hits only the runner's resolve constant, the sibling-script calls of AC5.2, `ledger_scripts.WORKTREE_SCRIPT` and docstrings; the hand-back classifies every hit.

#### FR10 — Reconciliation (Job 10, last; rc-16's own old-layout `reconcile` tree)

- AC10.1 (no test — `MEMORY-UPDATE.md` in full): the atoms of ASIS §2.3 are told true. `worktrees.md` is rewritten whole, which closes defect B; `release-lifecycle.md:27` reads "the newest `until` HEAD reaches opens the window"; the catalog and the ADR block are regenerated; `memory.py check` exits 0.
- AC10.2 (no test — derived docs): `docs/*.md`, the byte-equal `tests/fixtures/quickstart.md`, `README.md` and `CONTEXT.md` name the hierarchy and `dadaia worktree`.
- AC10.3 (no test — closure check): closure runs the tree's own copy, `python3 dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py phase CLOSURE --specs specs`, and passes with its own tree open (AC5.5). The exits of §4 are recorded; `measured_by` is repaired; G5 and G6 are in the closure summary; `bugs.py archive` has run; `release.py check` exits 0.
- AC10.4 (no test — the rollout list in the closure summary): §4's rollout, in order.

## 4. Exits at closure

- `worktree-hierarchy` exits `delivered`; `new-reconcile-opens-while-a-job-is-open` resolves on Job 5's fix (AC5.1).
- **Rollout** (AC10.4): main-thread acts after the Reconciliation merge, not job tasks; no migration code.
  1. Cleanup (operator: "Agente arruma, sem perda (Recommended)"; "Antes de instalar o hook em cada repo"). In every repo, empty dirs and `wt/*` branches with no commit of their own are deleted; a tree holding its own work becomes the tag `archive/wt/<name>` before removal. Known: `worktrees/rand-engine/0.8.0-rc1/define` (a live definition, 4 ahead: its context merges it first, agent default, unruled — reason: the old instance WT merges it until step 2), `worktrees/rand-engine/0.7.0-rc1` (an empty dir), `worktrees/<consumer>/0.12.0b-impl` and the branches `wt/0.12.0{a,b,c}`.
  2. `public install`, then `doctor --fix` and `doctor`.
  3. `ci install-hook --force` in each repo; this clears HOOKS-DRIFT-1.
  4. `certify` runs green.

  The new layout applies from rc-17; its `wt-rc` opens after step 2.

## 5. Not in rc-16

- `worktree-layout-per-context` stays an idea ("O resto confirmamos"); every other `active[]` entry stays untouched.
- The `.S<m>` retirement of `TASK_ID_RE` (v1 FR3) goes to the next intake: the demand does not need it (ASIS H6: the `wt-task` leaf does not use `TASK_ID_RE`), and it would loosen `memory_lint.py:74,79`'s task-id ban.
- Bug `protected-globs-miss-a-plain-tree-path` (HIGH, security, block-list item 4) is a hotfix outside the DAG (`specs/bugs/AGENTS.md` §2): its fix tests the `[protected]` glob against every suffix of the path below `worktrees/<r>/`, depth-free in both layouts. AC4.7 keeps that contract.

## 6. Constraints and risks

### Replaces

- The `plain` kind, its recorded base (`record_base`, `recorded_base`, `branch.<b>.dadaia-base`, `_plain_base`) and its gate row become a refused name; a bug goes to a hotfix lane or a next-rc job, a promote to PR + `release.py ship` (FR2).
- Plain-only tests become refusal tests (FR2).
- The SKILL-MD-LENGTH fix that opened a plain tree becomes an agent act in a task of the open rc (FR2).
- A raw `worktree add`, merge, reset or commit on a work branch is refused by the hook (FR3, installed by FR9).
- `NAME_RE`'s six alternations (`<M.m.p>-rc<N>/<job>[--<task-id>]`, `backlog/<slug>`, `hotfix/<bug>`) and the `--` separator become one leaf grammar, branch = `wt/` + path (FR4).
- `locate`'s fixed two-segment guess becomes the first `wt-` segment (FR4).
- Jobs merge into `wt-rc`, not `feature/<v>` (FR4).
- The `define` and `reconcile` kinds become the first and last commits of `wt-rc`; their special cases leave: the define gate row, `pushable`'s define exclusion, `new`'s phase skip and the `== "define"` tests (FR4).
- `_open_tasks`' `startswith(f"{name}--")` becomes `_open_children` by path (FR4).
- `_refuse_unready` reads `_RELEASE.json` from the rc's `wt-rc`, not the work branch (FR4).
- `worktree.py main`'s two `except` arms ending in `Operator action`, and `_absent`'s per-row patch, become one `GitError` edge and one row per path (FR4, R4).
- Closure's exception for the next define tree (ADR 0241) becomes "any open job, task or lane tree refuses; a `wt-rc` and the tree closure runs from do not" (FR5).
- `verdict.py stats`' prefix `wt/{rc}/` becomes `wt/<M.m.p>/rc-<N>/` (FR5).
- Printed fix lines that name `worktree.py <verb>` name `dadaia worktree <verb>` (FR5, FR9).
- doctor's `_absent_tree`/`target = None` fallback becomes one specs-section finding (FR5, R3).
- The seven-kind `worktrees-AGENTS.md` and the old grammar in skills and agents become the hierarchy text (FR6).
- Per-agent `git rebase <work>` becomes `dadaia worktree sync` (FR7).
- Onboarding's first-pass plain tree becomes the `wt-backlog-first-pass` lane, and `specs init`'s "commits nothing" becomes a scaffold commit on the branch it cuts (FR8).
- `doctor --fix` deleting a placeholder atom, and `_TEMPLATE_LINES`, become report-only (FR1, R2).
- The four closure-summary readers become one (FR1, R1).
- `version_change`'s `before is None` ternary becomes the `repair` action (FR1, R5).
- ADRs 0125, 0191 and 0241, and 0120's "a wt/ branch is never pushed as a branch", are replaced by ADR 0264.

### Governance

- ADR 0264 is proposed here with `supersedes` and `amends` null, since the doctor refuses an unruled record that names an accepted one. The operator accepted it ("Aceito a ADR 0264 (Recommended)"); the main thread's accept commit writes the ruling, `supersedes: "0125,0191,0241"` and `amends: "0120"` (0120's push clause), and flips 0125, 0191 and 0241 to `superseded`.

### Cutover (Q5; ASIS H1)

- rc-16 is built in the old layout by the instance's WT (`.agents/`), which speaks the old grammar until rollout step 2.
- The package reads the WT grammar from the editable checkout. From Job 4's merge, `locate`, `kind_of` and `pushable` flip live: job branches are local-only, `verify:` runs at merge, `feature/0.5.0` pushes continue, and doctor shows PROJECTION drift until step 2. Protection does not move with `locate` (AC4.7).
- From Job 9's merge until rollout step 3, HOOKS-DRIFT-1 reports `reference-transaction` absent in every repo. That finding is expected: `ci install-hook`, `context create` and `context alive` (the installer's callers) do not run in that window, since the old instance WT sets no `DADAIA_WT` and an installed hook would refuse its `new` and `merge` (a Stall). The window holds only Job 10.
- Job 10 closes from its own tree (AC5.5, AC10.3); no other tree of the repo is open then, since rc-17 is defined after step 2.

### Delivery constraints

- No test or assert is removed or loosened. Tests change only where a ruling orders it: AC1.2 (`--fix`), AC2.2 (refusal tests), AC8.4 (the scaffold commit).
- Gate cost (root map §1): the `wt-rc` merge adds one `verify:` run and one review per rc. The hook's shell path costs about 0 s; its python path costs 0.24 s and runs only on an unmarked move of a non-`wt/` head (ASIS §3 seam 13).
- Public needs only shell and local git. Platform facts go through `core/platform.py`. Memory changes only at the Reconciliation.

### Risks

| risk | control |
|---|---|
| a hook false positive blocks `git commit` | it fails open on a runner fault, and the shell fast path passes `wt/*` (AC3.3, AC3.5) |
| a forged marker | a speed bump: pre-push and review stay the chokepoints |
| the hook installed before the instance WT sets the marker | the installer row lands only in Job 9; Cutover's window rule |
| a `sync` conflict mid-cascade | it stops at the first conflict with one fix line, and a re-run finishes (AC7.1) |
| an off-grammar tree at the rollout | rollout step 1 |

## 7. Open questions

- Resolved: `specs init` commits the scaffold on the branch it cuts ("specs init commita o scaffold (Recommended)"); AC8.4 pins it.
- Pending the operator: ADR 0250 (accepted, amends 0191) decides "The rest of 0191 and 0125 stands, including one define tree per rc.", while 0264 supersedes 0191 and 0125. 0250 is left unchanged here; no job reads it.
