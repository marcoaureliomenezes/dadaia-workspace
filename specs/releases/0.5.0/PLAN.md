# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 3 — "onboarding foundation". SPEC FR1–FR11; ADRs 0033–0038, 0040, 0042–0046; main-thread
rulings 2026-09-25 (work key stores `feature/`; the `specs` fix line carries the three gitflow flags with
detected values; agent-step fix = SKILL path + pending list; `context` step keeps placeholders; a baseline
push failure after the local commit is finished by re-running; shrink = direction + per-unit estimate here,
measured at closure; `python3 .agents/…` constants out of scope).
Paths are relative to `dadaia_workspace/` unless they start with `tests/`, `docs/`, `specs/`, `.github/`.

## 1. As-is review

Surveys `inventory-c3-foundation-state-machine.md` and `inventory-c3-gitflow-and-c4-docs.md` §A were taken
at 1fce38d6. They were checked against 78bf410f: no production module has changed since (c2 touched only
release scripts and skills; Arm B touched only tests). The drift corrected here is listed in §1.2.
Ledger: 557 records, 0 open (2 new since the SPEC, both tests-only: `e2e-upgrade-previous-version-equals-source-version`
on the E2E journey, and the conftest cwd bug).

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `features/workspace/onboarding.py` `_lowest` + `_first_pass_done` + `_AUDITS_HISTO` | if-chain over 3 levels; level 3 = `audits_histo` stamp; POSIX `$(git rev-list …)` fix | 2 (`audit-close-refuses-a-clean-audit`, `session-start-bound-session-omits-onboarding-next-step`) | REBUILD | contract contradicts ADR 0033/0034; the stamp predicate is proven wrong |
| `features/workspace/onboarding.py` `cli_path` | absolute CLI path, only onboarding + init use it | 9-bug fix-line family | DELETE | moves to `core/cli_line.py` (no shim) |
| `features/workspace/onboarding.py` `Step` | `reason`, `command`; no kind | 0 | UPDATE | gains `kind`; `text()` names it |
| `core/kernel_tunables.py` `DADAIA_BIN` | relative POSIX CLI spelling, 40 uses in 7 importers | 9-bug fix-line family | DELETE | second spelling; wrong on Windows and from `repos/<slug>` |
| `features/specs/rules.py` fix_help strings | 7 `f"{DADAIA_BIN} …"`; TREE-5 advertises `doctor --fix` even where it is `fixable=False` | 1 (`tree8-fix-line-not-runnable-for-every-case`) | UPDATE | CLI remedies become argv, rendered once by `fix_line` |
| `core/doctor_rules.py` `_with_fix` | stamps a static `fix_help` string | 0 | UPDATE | the one render site: an argv `fix_help` is built with `fix_line(root, …)` |
| `features/spec_context/{service,doctor,gate_policy}.py`, `infrastructure/ledger_scripts.py`, `cli/commands/{context,doctor}.py` DADAIA_BIN sites | hand-built f-strings | 5 (gate_policy), 11 (context), 7 (service) | UPDATE | call-site migration only, no behaviour change |
| `hooks/venv_guard.py` corrected command (:120) | suggests `.dadaia/.venv/bin/dadaia …` (POSIX) | 0 | UPDATE | the suggestion becomes a `fix_line`; `_VENV_BIN` matcher and the `$DADAIA_BIN` env allowance stay (a matcher, not a spelling) |
| `features/ci_preflight/service.py` `$DADAIA_BIN` env read | resolves the hook-exported runner | 0 | KEEP | env var ≠ the constant; not a fix line |
| `features/specs/doctor_memory.py` FIXED-1 (:181) / FIXED-2 (:263) | embed bare `dadaia doctor --fix` | 1 (`shipped-text-cites-bare-dadaia-the-gate-blocks`) | UPDATE | remedy lives in the fix line only |
| `features/specs/doctor_structural.py` TREE-4/5 | bare `dadaia specs init` (:236); copy-a-library-path prose (:285-295); missing law file `fixable=False` | 3 (`doctor-messages-cite-dead-verbs`, `doctor-fix-tree8-deletes-operator-content`, `specs-doctor-segment-router-silent-skip`) | REBUILD | a stall: the advertised fix does not clear it; writing a missing template is lossless |
| `features/specs/template_history.py` | stdlib-only history of shipped hashes; sole prod caller `doctor_structural` | 0 | DELETE | moved to `core/template_history.py` (3 test importers updated) |
| `public/templates/shipped-hashes.json` | no memory-stub digests | 0 | UPDATE | + stripped digests of every historical scaffold ARCHITECTURE/QUALITY |
| `cli/commands/init.py` bind + refusals | binds (session record, `export` lines), "and bound"; 3 hand-built refusal fixes | 5 (`init-foreign-tree-fix-line-unrunnable`, `init-missing-harness-fix-line-drops-repo-flags`, `init-root-dir-crashes-deriving-sibling-fix`, …) | REBUILD | ADR 0038: a second bind author; ≥2 fix-line bugs |
| `cli/commands/context.py` `bind_session` + create bind + `_create_fix` | shared bind helper, create binds; baseline `--yes`/`--push` | 11 (`context-bind-session-id-mismatch`, `context-baseline-rejects-official-scaffold-followup`, …) | REBUILD | one bind author left (inline); consent = invoking the verb |
| `features/spec_context/service.py` `baseline` | unborn-only, convergent `has_commits` branch (:566), hard-coded `feature/0.1.0` (:585), `push` flag | 2 (`baseline-refuses-alive-scaffold-commit`, `context-baseline-rejects-official-scaffold-followup`) | REBUILD | the convergent branch is a symptom patch; ADR 0035 changes the contract |
| `features/spec_context/service.py` `_require_no_untracked_secrets` | secret scan before commit | 0 | KEEP | reused by the rebuild |
| `infrastructure/git_subprocess.py` `GitSubprocessClient` | clone/commit/push/create_branch…; no fetch, ls-remote, tag, refspec push, symbolic-ref | 2 (history walk, shallow checkout) | UPDATE | the new git reads the baseline and `specs init` need; concrete adapter, no new Protocol |
| `features/certification/service.py` baseline call (:389) | `--yes --push` | 10 on the file, 0 here | UPDATE | flags deleted |
| `hooks/ctx_inject.py` `_generic_preflight` + `_emit_bootstrap` | two `next_step` call sites (:288, :313) | 7 (1 is the duplicate's origin) | REBUILD | the second call site was a symptom patch; one helper |
| `cli/commands/doctor.py` `_onboarding_section` | ONBOARDING info from `next_step` | 0 | UPDATE | `--json` carries `step`, `kind` |
| `features/chokepoints/branch_policy.py` `_MAIN_RE`/`_DEVELOP_RE`/`_FEATURE_RE`/`_PERMITTED_BRANCH_RES`, `branch_name_is_permitted`, `parse_push_refs` | hard-coded names; two test-only functions | 8 hard-coded-name bugs | REBUILD | one name source (`core/gitflow`); dead code deleted |
| `features/chokepoints/__init__.py` exports of the two dead functions + stale comment | re-exports test-only API | 0 | DELETE | follows the deletion |
| `features/chokepoints/push_gate.py` `ObjectSource.parents`, `_run_specs_canon_scan` params, `push_gate_decision` | `parents` has no prod caller; unused `object_source`/`repo`; refuses every principal/integration push | 3 + 6 "already published" | REBUILD | births need `publishes_nothing` reusing `_base_exclusions`, never a second rule |
| `infrastructure/git_objects.py` `GitSubprocessObjectReader.parents` | dead | 0 | DELETE | replaced by `publishes_nothing` |
| `core/specs_version.py` `_STAMP_RE` + `write_pattern_version` | regex frontmatter read/write, one key | 3 | REBUILD | `core/frontmatter.parse` + one merge-writer for both keys |
| `features/specs/canon.py` `_CONSTITUTION_STUB` | only `specs_pattern_version` | 6 on the file | UPDATE | stub carries the default `gitflow:` block |
| `cli/commands/specs.py` `init` | no gitflow flags; `canon.scaffold` writes only missing files | 2 | UPDATE | +3 flags; merge the block into an existing tree |
| `features/specs/doctor_coherence.py` + `rules.py` | SPECS-VERSION beside SPEC-DOC | 0 | UPDATE | GITFLOW-1 (WARN) |
| `cli/commands/ci.py` pre-push | reads working-tree constitution for the pattern version | 6 | UPDATE | also resolves the gitflow (main → associated → default+warning) |
| `core/invocation.py` `_repo_slug_under_repos` | private | 0 | UPDATE | made public for `ci.py` (rename, no wrapper) |
| `public/scripts/pre-push-ci-gate.sh` wording | names `feature/`/`develop`/`main` | 0 | UPDATE | by role |
| `.github/workflows/ci.yml` `pr-source-guard` | literal branch names + a stale comment | 1 (`pr-source-guard-refuses-the-release-please-pr-to-main`) | REBUILD | reads the library gitflow; triggers pinned by contract test |
| shipped text (~36 lines: `dd-gitflow-default`, `CICD-AUTOMATION.md`, release/bug/audit skills, `RC-FLOW.md`, scaffold/templates AGENTS, `data/AGENTS.md`, `registry.json`, `release-state-v1` schema, README, docs, `llms.txt`, `CONTEXT.md`) | hard-coded branch names | 8-bug family | UPDATE | by role + pointer to the constitution |
| `public/skills/dd-audit-project/SKILL.md` first pass | condition = empty `audits_histo`; ends with `audit.py close` stamp | 1 | REBUILD | ADR 0034: done by real memory content |
| law/docs claiming bind-by-init/create or level 3 = stamp (`data/AGENTS.md` §7, `dd-cli-library`, `docs/{quickstart,index,getting-started}.md`, README, `CONSUMER_VALIDATION_RECIPE.md`, `CONTEXT.md`) | contradict ADRs 0034/0035/0038 | 2 (`onboarding-docs-contradict-the-cli`, `dd-cli-library-cites-a-dead-flag-and-omits-level-3`) | UPDATE | rewritten in place |
| `tests/contract/test_onboarding_text.py` | regex census of fix text | 0 | DELETE | replaced by the step census + the AST test (R4) |
| `tests/unit/features/workspace/test_onboarding.py` | tests the if-chain and stamp | 0 | REBUILD | per-step predicates; I1 |
| `tests/contract/test_audit_first_pass.py` | asserts the stamp flow | 0 | REBUILD | asserts memory-check end |
| `tests/unit/features/chokepoints/test_push_{branch_policy,denylist_scan,specs_canon_scan}.py`, `tests/contract/{test_push_gate_wiring,test_every_block_carries_a_fix}.py` | `parents` stubs, `parse_push_refs`, `branch_name_is_permitted` | 0 | UPDATE | stubs deleted, `parse_push_stdin(...)[0]`; gitflow cases |
| `tests/integration/{test_init_with_repo,test_context_create_transactional}.py`, `tests/contract/cli/test_cli_context.py`, `tests/contract/test_cli_output_stability.py` | assert bind output / session record | 0 | UPDATE | assert no binding; goldens regenerated |
| `tests/e2e/test_onboarding_journey.py` | journey ends with HEAD == `ls-remote HEAD` | 1 (`e2e-upgrade-previous-version-equals-source-version`) | REBUILD | the autopilot loop (FR10); keep the Upgrade scenario |
| `tests/e2e/test_push_gate_check.py`, `tests/contract/test_ci_workflow_hygiene.py`, `tests/contract/test_secret_scan_workflow_gitflow_triggers.py`, `tests/integration/cli/test_specs_init_levels.py` | literal gitflow | 0 | UPDATE | custom and absent gitflow cases |
| `core/cli_line.py` | — | — | ADD | no core module owns the CLI spelling, and features may not import each other (setup.cfg independence contract) |
| `core/gitflow.py` | — | — | ADD | a pure value both `chokepoints` and `specs` need; only `core` is importable by both |

Verdict counts: DELETE 6 · REBUILD 14 · UPDATE 21 · KEEP 2 · ADD 2.

### 1.1 Size estimates (AC11.3) — production Python, net lines vs 78bf410f

| module | now | est. Δ |
|---|---|---|
| `core/cli_line.py` (new) | 0 | +35 |
| `core/gitflow.py` (new) | 0 | +60 |
| `core/template_history.py` (move) | 60 | 0 |
| `core/kernel_tunables.py` | 62 | −5 |
| `core/specs_version.py` | 131 | −6 |
| `core/doctor_rules.py` / `core/invocation.py` | — | +5 / +0 |
| `features/workspace/onboarding.py` | 88 | +60 |
| `hooks/ctx_inject.py` | 401 | −10 |
| `cli/commands/init.py` | 232 | −12 |
| `cli/commands/context.py` | 691 | −45 |
| `features/spec_context/service.py` | 791 | +40 |
| `infrastructure/git_subprocess.py` | 350 | +70 |
| `features/chokepoints/branch_policy.py` | 209 | −40 |
| `features/chokepoints/push_gate.py` | 443 | −3 |
| `features/chokepoints/__init__.py` | — | −4 |
| `infrastructure/git_objects.py` | 923 | +7 |
| `features/specs/doctor_structural.py` | 493 | −20 |
| `features/specs/{rules,doctor_coherence,canon}.py` | — | +6 / +25 / +4 |
| `cli/commands/specs.py` / `cli/commands/ci.py` | 150 / 192 | +35 / +23 |
| migrations (gate_policy, ledger_scripts, spec_context/doctor, doctor_memory, cli doctor, venv_guard, certification) | — | ±0 |

Net ceiling **+230** lines. Growth sits only in the new modules, the step list, the baseline rewrite, the
new git reads and the gitflow CLI/doctor surface. Every AC11.2 unit shrinks.

### 1.2 Survey drift corrected

- `DADAIA_BIN` importers are **7**, not 9–10: `hooks/venv_guard.py` and `features/ci_preflight/service.py`
  read the `$DADAIA_BIN` *environment variable* exported by the pre-push hook, not the constant (SPEC AC2.2
  inherits the error; see §6).
- `ObjectSource.parents` fake stubs also sit in `tests/unit/features/chokepoints/test_push_specs_canon_scan.py:51,61`;
  `parse_push_refs` is also used there. `branch_name_is_permitted`/`parse_push_refs` are re-exported by
  `features/chokepoints/__init__.py:29-39`.
- `template_history` has 3 test importers (`test_copy_drift_scoped_law`, `test_migration_symlink_hardening`,
  `test_tree5_shipped_history`), not zero.
- FIXED-1 (`doctor_memory.py:181`) also embeds a bare `dadaia doctor --fix`; FIXED-2 is at :263.
- Line shifts: baseline `has_commits` :566, `feature/0.1.0` :585; TREE-5 copy prose :285-295; bare
  `specs init` :236.
- `Rule.fix_help` is a static module-level registry (no root). `fix_line` needs a root, so the render
  moves into `core/doctor_rules._with_fix` (§3).
- Ledger size: 557 (not 555).

## 2. Strategy by FR

- **FR2** `core/cli_line.py`: `cli_path(root)` and `fix_line(root, *argv)`. POSIX uses `shlex.join`;
  Windows uses `list2cmdline`, chosen by `core.platform.PLATFORM`. Seven importers migrate. Static rule
  remedies become `fix_help=("doctor","--fix")`, and `_with_fix` builds the line from the root the doctor
  passes. Gate messages (`gate_policy`) get the root they already resolve. The AST contract test scans every
  string in a fix position for the venv CLI path or a bare `dadaia `: an argument after `fix:`, a
  `fix=`/`fix_help=` kwarg, or a `Refusal`/`Step` fix. TREE-5 on a missing law file becomes fixable: the
  fixer writes the shipped template.
- **FR3** `core/template_history.py` (move). The stripped digest is computed with `memory_canon` extract. The
  backfill script output is committed into `shipped-hashes.json`, and the append-only test covers it. The
  `first-pass` predicate compares stripped digests and checks for an empty catalog.
- **FR6** `core/gitflow.py`: `Gitflow`, `DEFAULT`, `from_mapping` and `role_of` hold all naming logic.
  `core/specs_version.py` gains `read_gitflow` plus one `merge_frontmatter(specs_dir, **keys)` built on
  `frontmatter.parse`; `_STAMP_RE` goes. `ci.py` resolves the gitflow once per push. `specs init` gets 3
  flags plus `GitSubprocessClient.default_branch`. GITFLOW-1 lives in `doctor_coherence`.
- **FR5** `ObjectSource.publishes_nothing(repo, sha)` = the `_range_commit_shas(…, _base_exclusions(repo, ZERO))`
  range is empty, or is one parentless commit on the empty tree (SHA-1 or SHA-256).
  `push_gate_decision(…, gitflow)` computes the births. `check_branch_policy(refs, gitflow, births)` stays
  pure.
- **FR4** Rebuild `baseline(name)` as a straight line of steps:
  identity → dirty check → fetch → ensure principal/integration → version → cut work → commit paths → push -u.
  `GitSubprocessClient` gains `fetch`, `remote_heads`, `push_refspec`, `last_tag`, `config_value`, and
  `published(repo, path)` (`git log --remotes -n1 -- path`). Each refusal raises the existing typed errors
  carrying a `fix_line`.
- **FR7** Delete the binders in `init`/`create`. Inline `bind_session` into `bind`.
- **FR1** `STEPS: tuple[StepDef, ...]`. `StepDef` holds `id`, `kind`, `pending(state)` and `fix(state)`.
  `state` is a frozen snapshot: root, name→specs, session id and bound context. Callers read it, and
  predicates read the disk and git through `published`. `onboarding.lines(...)` is the one helper that
  doctor, init, create and both SessionStart paths call.
- **FR8/FR9/FR10** Delete the dead gate code alongside FR5/FR6. Rewrite law and docs by role. Build the
  autopilot E2E last.

## 3. Seams

- `core/cli_line` is a deep module with a one-function interface; its only adapter axis is the platform,
  hidden inside it.
- `core/doctor_rules._with_fix` is the one render seam for rule remedies. No second render path exists.
- `ObjectSource` (port) keeps two adapters: the git reader and the test fakes. `parents` is swapped for
  `publishes_nothing`; no method is added net.
- `GitSubprocessClient` stays concrete (ADR 0001): one adapter, so no Protocol.
- Gitflow resolution sits in the composition root (`ci.py`); features receive a `Gitflow` value.

## 4. Sequencing (inventory R7)

cli_line + DADAIA_BIN → template_history → gitflow + frontmatter → FR5 birth → FR4 baseline → FR7 →
FR1 steps + callers → shipped text/law/docs → autopilot E2E. FR5 has to land before FR4, because the
baseline's birth pushes go through the hook.

## 5. Risks — no stall

- Every refusal carries one runnable fix line; the property test (AC1.3) executes each command step's fix.
- A stale tracking ref makes `publish` pending and fails the birth closed. Both carry fixes (`context
  baseline`, `git fetch <remote>`).
- A missing identity refuses before any write, with a `git config` line. An offline run refuses with the
  same baseline line. A push failure after the commit is finished by re-running, which is idempotent.
- An absent or malformed gitflow falls back to `DEFAULT` with a warning, never a block. GITFLOW-1 is WARN
  only.
- The library's own `pr-source-guard` change takes effect on the PR that carries it. The trigger contract
  test prevents drift.
- The hypothesis property runs real git over `file://`. It is bounded with `max_examples` ≤ 25 and
  `deadline=None`, and marked integration.
- AST test scope (§6 issue 2): scanning prose too would pull in ~115 help and docstring sites across ~50
  modules, which is out of scope.

## 6. SPEC issues found (routed to main thread, planned as stated)

1. AC2.2 names `hooks/venv_guard.py` and `features/ci_preflight/service.py` as `DADAIA_BIN` importers. They
   are not. PLAN: `venv_guard`'s suggested command migrates to `fix_line`; `ci_preflight` stays (it reads
   the env var).
2. AC2.5 "a literal … holding a bare `dadaia ` command" is scoped here to fix positions. A total ban would
   reach ~115 prose, help and error sites in ~50 modules, e.g. `service.py` "Run 'dadaia context alive'".
3. AC6.4 "existing `core/invocation.py` functions": `_repo_slug_under_repos` is private and gets renamed
   public.
