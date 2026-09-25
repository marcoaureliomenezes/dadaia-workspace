# TASKS — Release: 0.5.0

**Status:** Approved
**Owner:** dd-software-engineer

Paths are relative to `dadaia_workspace/` (abbreviated `pub/` for `dadaia_workspace/public/`) unless they
start with `tests/`, `docs/`, `specs/`, `.github/`. Every group commits green (ruff, mypy --strict, pytest).
DELETE/REBUILD rows (PLAN §1) land first. RED = the named test fails before the change.

## Candidate 3 — onboarding foundation

### G1 — one fix-line builder (FR2)

- [x] **T-050-07 — `core/cli_line.py`; `cli_path` leaves onboarding.**
  Add `cli_path`/`fix_line`; onboarding and init import from core; delete `onboarding.cli_path` (no shim).
  `Write set:` `core/cli_line.py`, `features/workspace/onboarding.py`, `cli/commands/init.py`,
  `tests/unit/core/test_cli_line.py`, `tests/unit/cli/test_init_{reinit_upgrade,plan}.py`
  `blocked by:` none · `delivers:` AC2.1 — POSIX + Windows forms pinned; today's fix lines unchanged
  `RED:` `test_cli_line.py` (module absent).

- [x] **T-050-08 — Delete `DADAIA_BIN`; every CLI fix goes through `fix_line`.**
  7 importers migrate; `Rule.fix_help` accepts an argv tuple rendered in `core/doctor_rules._with_fix`;
  `gate_policy` messages built with the resolved root; `venv_guard` suggestion via `fix_line`; init and
  create refusals via `fix_line`; constant deleted.
  `Write set:` `core/{kernel_tunables,doctor_rules}.py`, `features/specs/rules.py`,
  `features/spec_context/{service,doctor,gate_policy}.py`, `infrastructure/ledger_scripts.py`,
  `cli/commands/{context,doctor,init}.py`, `hooks/venv_guard.py`, affected tests
  `blocked by:` T-050-07 · `delivers:` AC2.2, AC2.6 — every doctor/gate/refusal fix is absolute and
  runnable from any cwd; one init refusal asserted in Windows form
  `RED:` `tests/contract/test_fix_lines_use_the_builder.py` (AST, fix positions per PLAN §2) lists the sites.

- [x] **T-050-09 — FIXED/TREE remedies honest; missing law file is fixable.**
  FIXED-1/2 and TREE-4/5 drop their embedded commands; a missing `specs/AGENTS.md` or
  `specs/<area>/AGENTS.md` is `fixable=True` (writes the shipped template); the copy-path prose is gone;
  an unfixable TREE-5 case advertises no `doctor --fix`.
  `Write set:` `features/specs/{doctor_memory,doctor_structural,rules}.py`,
  `tests/integration/test_doctor_fix_lines_clear_their_finding.py`
  `blocked by:` T-050-08 · `delivers:` AC2.3, AC2.4 — running the printed fix clears the finding
  `RED:` the integration test (missing law file stays after `doctor --fix`).

### G2 — first pass by real state (FR3, part)

- [x] **T-050-10 — `template_history` to core; stripped memory-stub digests.**
  Move (no re-export), callers + 3 test importers updated; backfill stripped digests of every historical
  `scaffold/memory/{ARCHITECTURE,QUALITY}.md` from `git log`; append-only test covers them.
  `Write set:` `features/specs/template_history.py` (delete), `core/template_history.py`,
  `features/specs/doctor_structural.py`, `pub/templates/shipped-hashes.json`,
  `tests/unit/core/test_template_history.py`, the 3 importing tests
  `blocked by:` none · `delivers:` AC3.2, AC3.3 — a FIXED-2-rewritten stub still matches a shipped digest
  `RED:` `test_template_history.py::test_fixed2_rewritten_stub_reads_shipped`.

### G3 — the project gitflow (FR6, FR8)

- [x] **T-050-11 — `core/gitflow.py` + frontmatter merge-writer.**
  `Gitflow`, `DEFAULT`, `from_mapping`, `role_of`; `read_gitflow` and one `merge_frontmatter` on
  `frontmatter.parse`; `_STAMP_RE` deleted; stub and library constitution carry the block.
  `Write set:` `core/{gitflow,specs_version}.py`, `features/specs/canon.py`, `specs/constitution.md`,
  `tests/unit/core/test_gitflow.py`, `tests/unit/core/test_specs_version.py`, core file-I/O allowlist test
  `blocked by:` none · `delivers:` AC6.1, AC6.2 — a constitution's gitflow reads back; other keys and body
  byte-identical after a merge
  `RED:` `test_gitflow.py` (module absent), merge preserves an unknown key.

- [x] **T-050-12 — Branch policy reads the gitflow; dead gate code deleted.**
  Delete the 3 regexes, `_PERMITTED_BRANCH_RES`, `branch_name_is_permitted`, `parse_push_refs`, their
  exports, unused `_run_specs_canon_scan` params, stale comments; `check_branch_policy(refs, gitflow)`;
  `push_gate_decision` requires `gitflow`; `ci.py` resolves main → associated (public
  `repo_slug_under_repos`) → DEFAULT + warning; hook wording by role.
  `Write set:` `features/chokepoints/{branch_policy,push_gate,__init__}.py`, `cli/commands/ci.py`,
  `core/invocation.py`, `pub/scripts/pre-push-ci-gate.sh`,
  `tests/unit/features/chokepoints/test_push_{branch_policy,denylist_scan,specs_canon_scan}.py`,
  `tests/contract/test_every_block_carries_a_fix.py`, `tests/e2e/test_push_gate_check.py`
  `blocked by:` T-050-11 · `delivers:` AC6.4, AC6.5, AC8.1 — a `trunk`/`next`/`work/` project pushes its
  work branch; refusals name its branches; an associated repo inherits
  `RED:` custom-gitflow cases in `test_push_branch_policy.py`.

- [x] **T-050-13 — `specs init` gitflow flags + GITFLOW-1.**
  `--principal/--integration/--work-prefix`; principal detected by `GitSubprocessClient.default_branch`
  (local `symbolic-ref`, else `main`); written fresh or merged; idempotent; stdout names it; GITFLOW-1 WARN
  with the `specs init` fix line carrying the detected flags.
  `Write set:` `cli/commands/specs.py`, `infrastructure/git_subprocess.py`,
  `features/specs/{doctor_coherence,rules}.py`, `tests/integration/cli/test_specs_init_levels.py`,
  `tests/integration/test_doctor_fix_lines_clear_their_finding.py`
  `blocked by:` T-050-08, T-050-11 · `delivers:` AC6.3, AC6.6 — the operator sees and sets the gitflow;
  running GITFLOW-1's fix clears it
  `RED:` flag cases in `test_specs_init_levels.py`.

### G4 — bootstrap birth (FR5)

- [x] **T-050-14 — `publishes_nothing` replaces `parents`; births pass.**
  Port and reader swap the method (reusing `_base_exclusions`); fake stubs deleted; births computed in
  `push_gate_decision` for principal/integration refs with a zero remote sha; stale tracking refs refuse with
  `fix: git fetch <remote>`.
  `Write set:` `features/chokepoints/{push_gate,branch_policy}.py`, `infrastructure/git_objects.py`,
  `tests/unit/infrastructure/test_git_object_reader.py`, `tests/contract/test_push_gate_wiring.py`,
  chokepoint unit tests
  `blocked by:` T-050-12 · `delivers:` AC5.1–AC5.4 — an empty-root principal and `git branch <integration>
  <principal>` push; a birth carrying a commit is refused
  `RED:` the orphan-empty-root case refused today.

### G5 — the one publish verb (FR4)

- [x] **T-050-15 — Rebuild `context baseline`.**
  Delete the convergent `has_commits` branch, `feature/0.1.0`, `--yes`/`--push`; straight-line flow per
  PLAN §2 with the new git reads; certification drops the flags.
  `Write set:` `features/spec_context/service.py`, `infrastructure/git_subprocess.py`,
  `cli/commands/context.py`, `features/certification/service.py`,
  `tests/integration/test_context_baseline.py`, `tests/contract/cli/test_cli_context.py`
  `blocked by:` T-050-11, T-050-14 · `delivers:` AC4.2–AC4.7 — one line publishes principal, integration
  and `<prefix>0.1.0` on any remote state, a re-run is a no-op
  `RED:` the 9 AC4.6 cases (unborn, principal only, both, tag, dirty, re-run, paths-only, offline, identity).

### G6 — the derived step list (FR7, FR1, FR3)

- [-] **T-050-16 — Only `context bind` binds.**
  `init`/`create` write no session record, print no export, drop "and bound"; `bind_session` inlined into
  `bind`.
  `Write set:` `cli/commands/{init,context}.py`, `tests/integration/{test_init_with_repo,
  test_context_create_transactional}.py`, `tests/contract/cli/test_cli_context.py`,
  `tests/contract/test_cli_output_stability.py`
  `blocked by:` T-050-08 · `delivers:` AC7.1 — init/create leave no session record
  `RED:` `test_init_with_repo.py` asserts no session record.

- [ ] **T-050-17 — `STEPS`: context, bind, specs, first-pass, publish; one caller helper.**
  Delete `_lowest`, `_first_pass_done`, `_AUDITS_HISTO`; `StepDef` tuple, `Step.kind`; first-pass via
  stripped digests + catalog atoms, fix = installed SKILL path + pending list; publish via
  `published(repo, "specs/constitution.md")`; bind only with a resolvable, unbound session id; doctor
  `--json` `step`/`kind`; ctx_inject one helper for both paths; `test_onboarding_text.py` deleted, step
  census added.
  `Write set:` `features/workspace/onboarding.py`, `hooks/ctx_inject.py`, `cli/commands/{doctor,context,init}.py`,
  `tests/unit/features/workspace/test_onboarding.py`, `tests/unit/hooks/test_ctx_inject.py`,
  `tests/contract/test_onboarding_{text,steps}.py`
  `blocked by:` T-050-10, T-050-13, T-050-15, T-050-16 · `delivers:` AC1.1, AC1.2, AC1.5–AC1.7, AC3.1,
  AC4.1, AC7.2 — doctor, init, create and SessionStart print the same next step
  `RED:` I1 (writing `audits_histo` changes a step today); bound SessionStart text ≠ doctor's.

- [ ] **T-050-18 — Property test: every command fix clears its step.**
  Hypothesis over real-state prefixes (tmp dirs, `file://` remotes, `max_examples` ≤ 25): execute each
  pending command step's fix (placeholders substituted), assert cleared and index strictly increasing.
  `Write set:` `tests/integration/test_onboarding_steps_property.py`, `tests/unit/features/workspace/`
  `blocked by:` T-050-17 · `delivers:` AC1.3, AC1.4, AC7.3 — no step can stall
  `RED:` run against T-050-17 before its last fix; a non-clearing step fails.

### G7 — text by role, law, docs (FR6, FR3, FR9)

- [ ] **T-050-19 — Shipped text by role; library `pr-source-guard` reads the gitflow.**
  Rewrite the ~36 PLAN §1 literals by role with a pointer to the constitution; `dd-gitflow-default` table by
  role; `ci.yml` guard reads `read_gitflow`; triggers stay literal, pinned by contract test.
  `Write set:` the PLAN §1 shipped-text files, `.github/workflows/ci.yml`,
  `tests/contract/{test_ci_workflow_hygiene,test_secret_scan_workflow_gitflow_triggers}.py`
  `blocked by:` T-050-12 · `delivers:` AC6.7–AC6.9 — agents read the gitflow by role
  `RED:` trigger-equality contract test against a changed library gitflow.

- [ ] **T-050-20 — Law, docs, first-pass skill, glossary; reproject.**
  `dd-audit-project` first pass ends at `memory.py check` (no FINDINGS, no `audit.py close`); bind and
  level-3 claims rewritten; `CONTEXT.md` gets the §3 terms; `public stage/install/doctor` + `doctor` exit 0.
  `Write set:` `pub/skills/{dd-audit-project,dd-cli-library}/SKILL.md`, `pub/data/{AGENTS.md,
  CONSUMER_VALIDATION_RECIPE.md}`, `docs/{quickstart,index,getting-started}.md`, `README.md`, `CONTEXT.md`,
  `tests/contract/test_audit_first_pass.py`
  `blocked by:` T-050-17 · `delivers:` AC3.4, AC9.1, AC9.2, AC9.4 — law and docs match the CLI
  `RED:` `test_audit_first_pass.py` asserts no `audit.py close`.

### G8 — autopilot (FR10)

- [ ] **T-050-21 — Autopilot E2E journey.**
  From an empty dir, `file://` remotes, `DADAIA_SESSION_ID` set, one `init … --repo`: loop `doctor --json` →
  run the ONBOARDING fix (`shlex.split`; agent step via scripted stand-in), cap 10; greenfield, v6 tree,
  foreign tree; HEAD == upstream; Upgrade scenario kept.
  `Write set:` `tests/e2e/test_onboarding_journey.py`
  `blocked by:` T-050-18, T-050-20 · `delivers:` AC10.1–AC10.3 — an agent loops from nothing to a
  published project
  `RED:` the loop reaches the cap on today's code.

Closure (not tasks): AC9.3 memory pass (dd-product-engineer); AC11.3 net-lines measurement vs PLAN §1.1.
