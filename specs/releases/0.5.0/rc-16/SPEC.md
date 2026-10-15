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
| `release-check-memory-task-check-reads-retired-tasks-md` | `23e182e19` | release-check (`_release_tree.py`, `_release_schema.py`) | REBUILD R1 | first of four fixes on one unit in the window; +5/-2 on a second reader of retired state |
| `release-check-names-the-memory-pass-an-operator-action` | `5c964ae7b`, `52d086a0d` | release-check | REBUILD R1 | label fix (+4), the unit's third findings touch |
| `release-check-info-origin-rows-carry-a-fix` | `1454be5f9`, `0a8902e64` | release-check | REBUILD R1 | `_origin_row` edited again by the next row's fix a day later |
| `release-check-origin-sweep-reads-a-retired-log-kind` | `8d807208c`, `49163dacd` | release-check | REBUILD R1 | three more readers still decide which summary counts (`_release_tree.py:133,145`, `release.py:194-220`) |
| `mem-placeholder-fix-deletes-a-memory-file-that-mentions-a-token` | `f4063ae8d` | `doctor_memory.py` placeholder detector | REBUILD R2 | CRITICAL; the `--fix` still unlinks files |
| `mem-placeholder-fix-deletes-an-atom-the-operator-filled` | `48f70750a`, `c974efbe5` | `doctor_memory.py` | REBUILD R2 | CRITICAL; second data-loss fix in a day; a hard-coded template table (`:42`) |
| `doctor-ledger-lane-absent-specs-dir-fix-never-clears` | `ff1f3b3d3`, `7bc7f26e5` | `ledger_scripts.script_findings`, `cli/commands/doctor.py` | REBUILD R3 | third fix on the absent-tree fallback; layers `_absent_tree` and `target = None` (`doctor.py:196,303-304`) |
| `worktree-merge-crashes-with-a-traceback-when-the-job-tree-is-gone` | `53107aeed`, `7682b3a92`, `7b84a7ff5` | WT error edge (`worktree.py`, `_worktree_end.py`) | REBUILD R4 | third crash of the class; two `except` arms and an `Operator action` for an agent act (`worktree.py:78-83`) |
| `worktree-list-hides-a-non-empty-stray-directory` | `f1f7aad93`, `ffa34bb48` | WT `list` (`_worktree_git.py` `_absent`) | REBUILD R4 | per-row patch (+4/-1) of the logic the demand replaces |
| `init-reports-same-when-the-venv-probe-fails` | `9e4bb5a28`, `1e52fb25c` | `python_env.version_change`, `init._reconcile_upgrade` | REBUILD R5 | a `before is None` branch (`init.py:194`) and a ternary (`python_env.py:488`); the decider already returns `action` |
| `scorecard-fix-3-left-the-repo-specs-law-stale` | `2108a984c` (RED), `142095c44` | specs law mirrors | KEEP | RED tightened the filter; 19 mirrors refreshed by the render, net -3 |
| `mutate-owner-import-writes-checkout-bytecode` | `da4bbb99a` | `scripts/mutate.py`, `certification/service.py` | KEEP | env built by `_git.scrubbed_env` (net -2); `dont_write_bytecode` is the convention of 8 entries |
| `backlog-exit-refuses-on-an-unrelated-spec-origin` | `ab690576f` (RED), `2eba6ed5e` | `_backlog_exit._release` | KEEP | REBUILD: reads only the `--release` SPEC (+16/-13); no assert edited |
| `preflight-skips-checks-merge-runs` | `3420e5976` (RED), `d2cea6103` | `_worktree_end._kind_checks` | KEEP | REBUILD: preflight is merge minus the verdict (`_worktree_end.py:355-399`) |
| `verdict-validation-stated-three-ways-without-the-reviewed-tree` | `d2cea6103`, `6f882432c`, `fd82f9c2b` | gate fix line, `verdict.py`, emitter step 7 | KEEP | three statements collapsed to one owner, the writer |
| `verdict-writer-emits-a-handoff-the-schema-rejects` | `cb6f34e3f` (RED), `6f882432c` | `verdict.py` | KEEP | the writer validates its own file (+37/-2), rc-15 FR8's one validation owner |
| `verdict-context-pattern-disagrees-with-core` | `710554fee` (RED), `d072cd85e` | `verdict.py`, `_grammar.py` | KEEP | one kernel grammar for core and writer (+8/-7) |
| `check-reads-crash-on-non-utf8-input` | `712484919` (RED), `b0f986e54`..`c449b3779` | `_jsonl.py`, `python_env` digest | KEEP | one decode-aware reader (`_jsonl.py:51-57`); its child bug fixed in-window |
| `check-verbs-text-output-drops-the-fix-line` | `09d0d6717` (RED), `26e8f0ad4`..`ec7e4cf48` | fix-line printers | KEEP | five printers on one renderer, net -6 |
| `doctor-specs-dir-file-reads-as-a-foreign-tree` | `0c3b7a923` (RED), `f4433343d`, `43be3fdf9`, `963cdb310`, `9f300b4a1` | `core/specs_version.state`, `core/gitflow.py` | KEEP | REBUILD: two probes into `specs_path_kind` (net -9) |
| `specs-init-on-a-file-crashes-with-a-traceback` | `ea975c41f` (RED), `d6985eb19`, `9f300b4a1` | `cli/commands/specs.py`, `state()` | KEEP | same series as the row above |
| `specs-dir-symlink-refusal-prints-no-fix-line` | `bf42f2d50` (RED), `537233467` | `core/invocation.resolve_specs_dir` | KEEP | the one `DadaiaError` shape (+4/-4) |
| `e2e-bootstrap-fixture-seeds-a-venv-without-python` | `427d7966c` (RED), `ae2d5c349`, `333a6c371`, `33c304189` | `tests/fixtures/stores.py` `fake_venv` | KEEP | three seeders into one home (+18/-34) |
| `init-oserror-from-the-venv-interpreter` | `3614b020f` (RED), `133b8c89a`, `835772b75`, `1f2e57da6`, `4d5e767d0`, `d2bd75b30` | `python_env` venv-python runs | KEEP | REBUILD `133b8c89a`: one runner turns `OSError` into the refusal |
| `test-doctor-judges-no-instance-cannot-tell-fenced-from-crashed` | `0d0fbd910` | `tests/scripts/test_ci.py` | KEEP | test-only tightening, +3 asserts |
| `verdict-refusals-print-no-fix-line` | `c165046de` (RED), `6a1cd01fa`..`1899b2863` | `verdict.py`, `_refusal.py` | KEEP | every refusal through one kernel printer |
| `worktree-no-work-branch-fix-names-the-tag-derived-version-not-the-live-release` | `cd92ebf29` (RED), `4e098074c`, `7777ebd43`, `b10444ce5` | `_grammar.sole_live` | KEEP | one-live rule in one owner (`_worktree_git.py:88,110`) |
| `bug-lineage-refuses-a-task-id-of-the-historical-grammar` | `b0f3d7a38` (RED), `35d0c8b98` | `_bugs_check.tasks`, `_grammar.py` | KEEP, noted | net -2; `HISTORICAL_TASK_RE` (`_grammar.py:21`) is a second, history-only task grammar (§5) |
| `adr-superseded-citation-judges-the-generated-adr-list-block` | `1e5d26896` (RED), `a6cddda33` | `doctor_adr.py` | KEEP | reads `authored_text` (`doctor_adr.py:78`) |
| `mem-drift-2-judges-the-generated-adr-list-block` | `47567ca7f` (RED), `a1654984f`, `d67cfa3a5`, `beb24bde5` | `citations.py`, `doctor_adr.py`, `memory_lint.py` | KEEP | one reader `authored_text` for every memory judge (4 sites) |
| `cli-line-guard-judges-the-generated-adr-list-block` | `5913791d6` (RED), `2192e2e46`, `c54cbf98c`, `51119a027`, `4abd0df01` | `scripts/guards/repo.py`, 5 test scans | KEEP, noted | five fixes from one decision (a generated block in an authored file); the adversarial-block test now guards every reader |
| `memory-entry-until-breaks-when-the-reconcile-tree-rebases` | `5b64988f5`, `04510a316` | `_release_store.py:63-67`, `_memory_drift.py` | KEEP | REBUILD of the window start (+19/-20) |
| `restore-and-reinstall-fix-lines-name-an-operator-action` | `d05b1a6b4` (RED), `5c964ae7b`, `52d086a0d` | `_jsonl.py`, `reinstall_fix` | KEEP | names the re-encode of the one bad line (`_jsonl.py:25-49`) |
| `agent-acts-are-labelled-operator-action` | `dd5dd7df2`..`6ea866584`, REBUILD `764651946` | fix-line grammar | KEEP | ADR 0263's `Agent action:` form, judged by `fix_defect` (`test_cli_line__fix_line_contract.py:94`) |
| `states-file-write-block-prints-public-install-as-its-fix` | `3a10072c5` (RED), `10bff2858`, `a23e1d65c` | `workspace_layout.py:93,130`, `gate_policy.py` | KEEP | one table member (`FloorRefusal.STATE`), no branch |
| `guard-fix-lines-keep-placeholders` | `f2140a625` (RED), `52739ac3c` | `scripts/guards/repo.py` | KEEP | +3/-3: the real file and owner |
| `ship-archive-never-reaches-the-next-work-branch` | `cfe37ae02` (RED), `fb127322a` | work-branch decider (`_worktree_git.work_versions`, `core/gitflow.py`) | KEEP, noted | three deciders into one rule (+76/-43); the hierarchy rewrites the unit |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened): Job 1 takes R1 (AC1.1), R2 (AC1.2; `Agent action` by ruling, where the window's draft said `Operator action`) and R5 (AC1.3). Job 4 takes R4 (AC4.2, AC4.6) and keeps green the contract tests of `fb127322a`, `d2cea6103` and `4e098074c`. Job 5 takes R3 (AC5.4). Two of rc-15's three non-blocking findings are R1; the third, `release-lifecycle.md:27`, is fixed in the memory pass (AC10.1).

## 1. Problem

The worktree layer is the library's most churned surface: 49 bugs, 13 in verdict and gate, 91 commits from 09-30 to 10-13. ASIS §1 finds four structural causes:

- **No rc level.** Jobs merge straight into `feature/<v>`, which holds the jobs of open rcs; abandoning an rc reverts N merges.
- **Three base deciders:** the name regex, a base recorded in git config (`plain`, any slug, used for a bug fix and a promote), the work-branch rule.
- **Special cases:** the `--` separator, the define gate row, the next-define closure exception (ADR 0241), a `reconcile` tree that opens while a job is open (`new-reconcile-opens-while-a-job-is-open`).
- **No chokepoint:** a raw `git worktree add` or `git merge` into `feature/*` passes every hook.

## 2. Measurable Goals

- G1. `bugs.py status --specs specs` does not list `new-reconcile-opens-while-a-job-is-open` open at closure.
- G2. One base decider: `git grep -nE 'dadaia-base|recorded_base|record_base|_plain_base' -- dadaia_workspace` prints nothing; AC4.1 green.
- G3. The CLI is the only path: AC3.3 green, the hook installed by AC9.1.
- G4. One grammar: the AC6.1–AC6.4 sweeps and `grep -rnE -- '-rc<N>/|<job>--|wt/hotfix/|wt/backlog/' dadaia_workspace/public` print nothing; AC9.2 holds.
- G5. Size readout, never a gate: `git diff --shortstat <rc-16 cut>..<wt head> -- dadaia_workspace scripts` in the closure summary; ASIS §6 estimates +15 python (−10 to +60) and +40 shell; above +60 python names its reason.
- G6. `verdict.py stats 0.5.0-rc16` in the closure summary.

## 3. Requirements

FR<n> is Job <n>; its ACs are AC<n>.<k>, the job files' ids; a task split for size keeps its AC.

**Waves** (one subject, the dev loop; law text in wave 3, agent default, unruled — reason: text written before its behaviour drifts): 1 foundation and chokepoint, Jobs 1–3; 2 layout, Job 4 (waits on Job 2); 3 consumers, law, `sync`, onboarding, Jobs 5–8 (wait on Job 4); 4 activation, Job 9 (waits on Jobs 1–8); 5 Reconciliation, Job 10. Merge order is the wave order, Job 4 as late as wave 2 allows. ADR 0264 is accepted by ruling, so no merge waits on it. The cutover is §6 Cutover, stated once.

#### FR1 — bug-window REBUILDs R1, R2, R5 (Job 1)

- AC1.1 (integration, RED first; R1): one reader in `_release_schema.py` returns the live candidate's closure-summary fields (delivered, carried, exits) from the last `kind: summary` entry at or after `defined.ts`, past DEFINITION. An Origin id only in the previous candidate's summary reads `untraced`; a bug that summary carried does not satisfy `--allow-open`; an id equal to a label word (`carried`) is not traced by the label. `_last_summary` and `release.py`'s partition leave; `_swept`, `_trace` and `_refuse_unauthorized` consult the reader. The `release-check-*` partitions stay green unedited. Net ≤ 0.
- AC1.2 (unit, RED first; R2; operator: "Só reporta (Recommended)"): an atom with an unfilled placeholder is reported with `fix: Agent action: fill or delete the atom`; `doctor --fix` leaves it byte for byte. `_TEMPLATE_LINES`, the unlink, `rules.py`'s `fix=` pair and the `slop.py:46` row leave. The "filled atom" and "mention is not flagged" partitions are unchanged; the remove-on-`--fix` assert is rewritten by this ruling, never deleted.
- AC1.3 (unit, RED first; R5): `version_change` returns `repair` for an existing entrypoint whose probe fails; `init` prints `repaired -> B` from the action. The `before is None` ternary leaves; decider cases unchanged; net ≤ 0.

#### FR2 — delete `plain`; the sanction marker (Job 2; operator: "Apagar o tipo plain")

- AC2.1 (unit, RED first): `scrubbed_env()` and the env `git_subprocess._run` builds carry `{"DADAIA_WT": "1"}` and still drop the repo-selecting `GIT_*` variables.
- AC2.2 (unit, RED first; operator: "Converter em teste de recusa (Recommended)"): no test is deleted. The plain-only tests become refusal tests — `new r maintenance` exits 1 with `not a worktree name` and the `list` fix; `merge`/`preflight` of a plain name refuse alike (`test__worktree_new.py:135,176,249`, `test__worktree_end.py:612,631`, `test__worktree_end__preflight.py:134`, `test__worktree_end__verdict_binding.py:170`). The `:640` `dadaia-base` assert becomes "no base is recorded in git config". Example-only tests run on a job tree, assert count per file unchanged. `plain()`, `NAME_RE`'s plain alternative, `record_base`, the plain half of `recorded_base`, `_plain_base`, the plain `_kind_checks` row and the git-config base leave.
- AC2.3 (unit, RED first): the SKILL-MD-LENGTH fix reads `Agent action: add the split of <skill>/SKILL.md to a task of the open rc, then run public install`, opens no plain tree, and still clears its finding.

#### FR3 — ref gate, hook script, CLI group (Job 3; operator: "Verbo CLI + git hook")

The hook script ships here, tested in a temporary repo; no installer row names it before Job 9.

- AC3.1 (unit, RED first): `branch_policy.check_ref_policy` refuses moving a work-role ref (`Gitflow.role_of == "work"`) to a sha other than `refs/remotes/origin/<same>`, with one runnable `fix:`; it passes origin's sha, creation, deletion, every non-work ref, and an update touching only `specs/audits/**` (Q3, the `audit` zone predicate).
- AC3.2 (integration, RED first): `dadaia ci ref-gate-check` reads `old new ref` lines on stdin, exits 1 with `[ref-gate] BLOCKED …` and one `fix:` on a refusal, 0 otherwise; inputs from `_gate_inputs`.
- AC3.3 (integration, real git): the hook refuses raw `worktree add -b wt/x` and raw `merge --ff-only`, `reset --hard` and `commit` on the work branch; it passes the same add with `DADAIA_WT=1`, `branch -D wt/x` (old = new = 0, ASIS H2), `pull --ff-only` and `branch -m`. An unresolvable runner warns and exits 0 (agent default, unruled — reason: the hook fires on every ref update; pre-push stays the fail-closed chokepoint). Every fix line it prints is runnable.
- AC3.4 (integration, RED first): `dadaia worktree <verb> …` forwards argv, stdout and exit code to the installed `worktree.py`; `--help` lists the verbs; with no script installed it refuses with `fix: <dadaia> public install`.
- AC3.5 (integration, real git): a commit in an existing `wt/*` tree (old ≠ 0) passes with no python call.
- AC3.6 (integration, real git): creating the tag `archive/wt/<name>` passes.
- AC3.7 (integration, real git): creating a harness-native worktree branch (not `wt/*`, `worktrees-AGENTS.md:7`) passes.

#### FR4 — the hierarchy (Job 4; operator: "Integração real", "Reusar o gate de job"; R4)

Layout `worktrees/<repo>/<v>/{wt-hotfix-<bug>, wt-backlog-<slug>, rc-<N>/{wt-rc, job-<n>/{wt-main, wt-task-<k>}}}`; each branch is `wt/` plus the path under `worktrees/<repo>/`.

- AC4.0 (no test — support code every owner test exercises): fixture constants and `tests/helpers/worktree_ws.py` use the new names; helper behaviour unchanged.
- AC4.1 (unit, RED first): `locate` keys on the first `wt-` segment: `worktrees/<r>/<v>/rc-N/job-n/wt-task-001/secrets/k` → `(r, "<v>/rc-N/job-n/wt-task-001", ("secrets", "k"))`. `kind_of` reads the leaf; `base_of`: task → `wt-main` → `wt-rc` → `<work><v>`, a lane → `<work><v>`; `pushable` holds for rc, main and backlog only; `name_of` gives the branch.
- AC4.2 (unit, RED first): `ours` counts `ahead` against the parent branch; `_absent` reports an orphan `wt/*` and a non-empty or empty stray folder at any depth, one row per path with its removal as the fix; `registered:false` rows and the frozen row schema unchanged; `record_base`/`recorded_base` leave.
- AC4.3 (integration, RED first): `new` opens each kind on its parent's branch. `<v>` names an existing `<work><v>`; `wt-main` needs `_RELEASE.json` IMPLEMENTATION on its `wt-rc`; a task needs its `wt-main`; a hotfix needs its open bug; old-grammar and `reconcile` names refuse with a new-shape fix.
- AC4.4 (integration, RED first): merge by kind — task → main: hygiene plus test separation; main → rc and hotfix → `<work><v>`: the job gate; backlog → `<work><v>`: specs-only plus ledgers (the `define_gate` tests ported, asserts intact); rc → `<work><v>`: job gate plus ledgers. `merge` fast-forwards in the parent's checkout; an open child blocks its parent. `_check_approved`, `_gate`, `_ledgers`, `_check_specs_only`, `_check_ancestor` stay untouched.
- AC4.5 (no test — strength-preserving port): package-reader and hook-payload fixtures use the new names, asserts intact; `test_branch_policy.py` keeps `pushable` and the `archive/wt` carve-out; a depth-agnostic file is left untouched and reported.
- AC4.6 (integration; R4): a `GitError` in any verb ends as one refusal with an `Agent action` fix, through one edge in `main`; AC4.2's rows are the orphan listing; the tests of `fb127322a`, `d2cea6103`, `4e098074c` stay green.
- AC4.7 (unit): protection holds at every depth, whatever `locate` returns. `classify_path` is PROTECTED under a `[protected]` glob at lane, rc, main and task depth, and for a path with no `wt-` segment such as `worktrees/r/a/b/secrets/k` under `secrets/**` — the hotfix's depth-free contract (§5), whose tests stay green unedited.

#### FR5 — consumers (Job 5; `new-reconcile-opens-while-a-job-is-open`, R3)

- AC5.1 (unit, RED first; the bug): `release.py phase CLOSURE` refuses while a job, task or lane tree of the repo is open and passes when only `wt-rc` trees are open. The `f"{nxt}/define"` exception (ADR 0241) leaves; the stacked `release.py new` flow is unchanged.
- AC5.2 (unit, RED first): `verdict.py stats` counts verdicts of trees under `wt/<M.m.p>/rc-<N>/`. `hash` and every internal call stay on the sibling script (`verdict.py:27`, `_release_phase.py:64`), never through the CLI.
- AC5.3 (unit, RED first as `test(...)`): every fix line printed by the gate, the rows reader or the kernel names `dadaia worktree …` and is runnable; the sweep covers this job's `W:` only.
- AC5.4 (integration; R3): an absent explicit `--specs-dir` gives one finding from the specs-section builder carrying `state()`'s fix; the ledger lane keeps one guard; `_absent_tree` and `target = None` leave; the three predecessor bugs' asserts are unchanged; net ≤ 0.
- AC5.5 (unit, RED first): closure exempts the tree it runs from, whatever its layout: from an old-layout `reconcile` tree or a `wt-rc`, `phase CLOSURE` does not refuse on it; another open job, task or lane tree still refuses.

#### FR6 — law, skills, agents, templates (Job 6; text only; no test — AI-surface lens, `public doctor` `[ok] public-privacy`, sweep = 0 per AC)

- AC6.1: `worktrees-AGENTS.md` states the hierarchy, leaf names, three merges, lanes, `sync` and the hook in fewer than its 39 lines.
- AC6.2: `dd-gitflow-default` (§2a, §3a, §2 step 11, §5), `RC-FLOW.md` and `dd-release-implementation`: define and reconcile are `wt-rc` commits; shapes 9 and 10 name their trees; no old grammar word left.
- AC6.3: the other skills of ASIS §2.2 name the hierarchy and `dadaia worktree`.
- AC6.4: agents, projected map sources, data files, scaffold laws (`releases` "define tree" → `wt-rc`, `bugs` §2 hotfix text), `repo-AGENTS.md` and schema descriptions follow the new names.

#### FR7 — `sync` and the level `AGENTS.md` (Job 7)

- AC7.1 (integration, RED first, real git; operator: "Lanes laterais para ambos"): `dadaia worktree sync <path>` rebases parents first (`wt-rc` onto `<work><v>`, each `wt-main` onto `wt-rc`, then each task); skips a tree holding its base; stops at the first conflict or dirty tree with one fix line; completes on a re-run; never pushes. After a lane lands, `sync <rc>` makes the rc's `merge` pass; the ancestor refusal's fix is `dadaia worktree sync <tree>` (agent default, unruled — reason: the smallest cascade the existing predicates allow).
- AC7.2 (integration, RED first; operator: "é so porque eu não quero criar .gitkeep files ... deve estar na criação"): `new` writes a 5–10 line `AGENTS.md` once into each folder it creates (`<v>/`, `rc-<N>/`, `job-<n>/`), never over an existing file; `merge` and `clean` remove a level folder holding only it; `list` shows no stray for it.

#### FR8 — onboarding without `plain` (Job 8; operator: "specs init corta o branch (Recommended)", "specs init commita o scaffold (Recommended)")

- AC8.1 (integration, RED first): `dadaia specs init` on a repo with no work branch cuts the local `<work><next_version>`, commits only the scaffold, on the new branch, and leaves it checked out; a rerun with the branch present cuts and commits nothing; nothing is pushed. The `test_absent_specs_scaffolds_lists_paths_and_commits_nothing` assert "commits nothing" becomes "commits only the scaffold, on the new branch", in a `test(...)` commit naming the ruling.
- AC8.2 (integration, RED first): `context baseline` on a repo whose local work branch exists publishes it, anchor-first, and returns it.
- AC8.3 (unit, RED first): the ONBOARDING `first-pass` fix line is `Agent action: open the lane … worktree new <repo> <v>/wt-backlog-first-pass, then run the dd-audit-project first pass in it — <pending files>`; step order and kinds unchanged.

#### FR9 — activation (Job 9, after every code job)

- AC9.1 (integration, RED first, real git): the hook becomes installable: `INSTALLED_GIT_HOOKS` gains the `reference-transaction` row and `shipped-hashes.json` its entry; HOOKS-DRIFT-1 reports the row absent in a repo without it; `install_git_hooks` writes it; the installed hook refuses AC3.3's raw moves.
- AC9.2 (unit, RED first as `test(...)`): the full sweep — every fix line the package prints that names a WT verb reads `dadaia worktree <verb>` and is runnable; `grep -rn 'worktree\.py' dadaia_workspace .github scripts` hits only the runner's resolve constant, AC5.2's sibling-script calls, `ledger_scripts.WORKTREE_SCRIPT` and docstrings, each hit classified in the hand-back.

#### FR10 — Reconciliation (Job 10, last; rc-16's old-layout `reconcile` tree)

- AC10.1 (no test — `MEMORY-UPDATE.md` in full): the atoms of ASIS §2.3 are told true; `worktrees.md` rewritten whole (closes defect B); `release-lifecycle.md:27` reads "the newest `until` HEAD reaches opens the window"; catalog and ADR block regenerated; `memory.py check` exits 0.
- AC10.2 (no test — derived docs): `docs/*.md`, the byte-equal `tests/fixtures/quickstart.md`, `README.md` and `CONTEXT.md` name the hierarchy and `dadaia worktree`.
- AC10.3 (no test — closure check): closure runs the tree's own copy, `python3 dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py phase CLOSURE --specs specs`, and passes with its own tree open (AC5.5); §4's exits recorded; `measured_by` repaired; G5, G6 in the summary; `bugs.py archive` run; `release.py check` exits 0.
- AC10.4 (no test): §4's rollout listed, in order, in the closure summary.

## 4. Exits at closure

- `worktree-hierarchy` exits `delivered`; `new-reconcile-opens-while-a-job-is-open` resolves on AC5.1's fix.
- **Rollout** (AC10.4): main-thread acts after the Reconciliation merge; no migration code.
  1. Cleanup (operator: "Agente arruma, sem perda (Recommended)", "Antes de instalar o hook em cada repo"): in every repo, empty dirs and `wt/*` branches with no own commit are deleted; a tree with its own work becomes the tag `archive/wt/<name>`, then leaves. Known: `worktrees/rand-engine/0.8.0-rc1/define` (live, ahead: its context merges it first — agent default, unruled; reason: the old instance WT merges it until step 2), `worktrees/rand-engine/0.7.0-rc1` (empty dir), `worktrees/<consumer>/0.12.0b-impl`, branches `wt/0.12.0{a,b,c}`.
  2. `public install`, then `doctor --fix` and `doctor`.
  3. `ci install-hook --force` in each repo (clears HOOKS-DRIFT-1).
  4. `certify` green. The new layout applies from rc-17, whose `wt-rc` opens after step 2.

## 5. Not in rc-16

- `worktree-layout-per-context` stays an idea; every other `active[]` entry is untouched.
- The `.S<m>` retirement of `TASK_ID_RE` goes to the next intake: the demand does not need it (ASIS H6), and it would loosen `memory_lint.py:74,79`'s task-id ban.
- Bug `protected-globs-miss-a-plain-tree-path` (HIGH, security) is a hotfix outside the DAG (`specs/bugs/AGENTS.md` §2): the `[protected]` glob is tested against every suffix of the path below `worktrees/<r>/`. AC4.7 keeps that contract.

## 6. Constraints and risks

### Replaces

- FR1: `doctor --fix` deleting a placeholder atom, and `_TEMPLATE_LINES` → report-only (R2); four closure-summary readers → one (R1); `version_change`'s `before is None` ternary → the `repair` action (R5).
- FR2: the `plain` kind, its recorded base (`record_base`, `recorded_base`, `branch.<b>.dadaia-base`, `_plain_base`) and gate row → a refused name (a bug goes to a hotfix lane or a next-rc job, a promote to PR + `release.py ship`); plain-only tests → refusal tests; the SKILL-MD-LENGTH plain tree → an agent act in a task of the open rc.
- FR3 (installed by FR9): a raw `worktree add`, merge, reset or commit on a work branch → refused by the hook.
- FR4: `NAME_RE`'s six alternations and the `--` separator → one leaf grammar, branch = `wt/` + path; `locate`'s fixed two-segment guess → the first `wt-` segment; jobs merge into `wt-rc`, not `feature/<v>`; the `define`/`reconcile` kinds and their special cases (define gate row, `pushable`'s define exclusion, `new`'s phase skip, `== "define"` tests) → the first and last commits of `wt-rc`; `_open_tasks`' `startswith(f"{name}--")` → `_open_children` by path; `_refuse_unready` reads `_RELEASE.json` from the `wt-rc`; `main`'s two `except` arms and `_absent`'s per-row patch → one `GitError` edge and one row per path (R4).
- FR5: closure's next-define exception (ADR 0241) → "any open job, task or lane tree refuses; a `wt-rc` and the tree closure runs from do not"; `stats`' prefix `wt/{rc}/` → `wt/<M.m.p>/rc-<N>/`; doctor's `_absent_tree`/`target = None` → one specs-section finding (R3).
- FR5, FR9: printed fix lines naming `worktree.py <verb>` → `dadaia worktree <verb>`.
- FR6: the seven-kind `worktrees-AGENTS.md` and the old grammar in skills and agents → the hierarchy text.
- FR7: per-agent `git rebase <work>` → `dadaia worktree sync`.
- FR8: the first-pass plain tree → the `wt-backlog-first-pass` lane; `specs init`'s "commits nothing" → a scaffold commit on the branch it cuts.
- ADRs 0125, 0191, 0241 and 0120's "a wt/ branch is never pushed as a branch" → ADR 0264.

### Governance

ADR 0264 is proposed with `supersedes`/`amends` null (the doctor refuses an unruled record naming an accepted one). The operator accepted it ("Aceito a ADR 0264 (Recommended)"); the main thread's accept commit writes the ruling, `supersedes: "0125,0191,0241"` and `amends: "0120"`, and flips 0125, 0191 and 0241 to `superseded`.

### Cutover (Q5; ASIS H1)

- rc-16 is built in the old layout by the instance WT (`.agents/`), which speaks the old grammar until rollout step 2.
- The package reads the grammar from the editable checkout: from Job 4's merge, `locate`, `kind_of` and `pushable` flip live; job branches are local-only, `verify:` runs at merge, `feature/0.5.0` pushes continue, doctor shows PROJECTION drift until step 2. Protection does not move with `locate` (AC4.7).
- From Job 9's merge until rollout step 3, HOOKS-DRIFT-1 reports `reference-transaction` absent in every repo, as expected; `ci install-hook`, `context create` and `context alive` do not run then, since the old WT sets no `DADAIA_WT` and an installed hook would refuse its `new` and `merge` (a Stall). The window holds only Job 10.
- Job 10 closes from its own tree (AC5.5, AC10.3); no other tree of the repo is open then, since rc-17 is defined after step 2.

### Delivery constraints

- No test or assert is removed or loosened; tests change only where a ruling orders it (AC1.2, AC2.2, AC8.1).
- Gate cost (root map §1): the `wt-rc` merge adds one `verify:` run and one review per rc; the hook's shell path costs about 0 s, its python path 0.24 s, only on an unmarked move of a non-`wt/` head (ASIS §3 seam 13).
- Public needs only shell and local git; platform facts go through `core/platform.py`; memory changes only at the Reconciliation.

### Risks

| risk | control |
|---|---|
| a hook false positive blocks `git commit` | fails open on a runner fault; the shell fast path passes `wt/*` (AC3.3, AC3.5) |
| a forged marker | a speed bump: pre-push and review stay the chokepoints |
| the hook installed before the WT sets the marker | the installer row lands in Job 9; the Cutover window |
| a `sync` conflict mid-cascade | stops with one fix line; a re-run finishes (AC7.1) |
| an off-grammar tree at the rollout | rollout step 1 |

## 7. Open questions

- Resolved: `specs init` commits the scaffold ("specs init commita o scaffold (Recommended)"), AC8.1.
- Pending the operator: ADR 0250 (accepted, amends 0191) decides "The rest of 0191 and 0125 stands, including one define tree per rc.", while 0264 supersedes both. 0250 is unchanged here; no job reads it.
