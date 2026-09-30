# PLAN — Release: 0.4.8

**Status:** Approved
**Release ID:** 0.4.8
**Owner:** dd-software-engineer

Candidate 1 — "onboarding in three levels". SPEC 45620ce5; ADRs 0027–0031 (A1–A5) accepted at append
(grill ruling 2026-09-23). Paths below are relative to `dadaia_workspace/` unless they start with `tests/`,
`docs/`, `specs/` or `.github/`.

## 1. Core problem and bug history

- Core problem: onboarding is four verbs plus a hidden side effect (`alive` scaffolds and auto-commits specs);
  the side effect and the create/alive split are where the ledger's bugs cluster (`python_env.py` 10,
  `cli/commands/context.py` 8, `spec_context/service.py` 7, `init.py` 3, `scaffolder` 3). Every prior fix
  added a branch to `alive`; this candidate deletes the branch instead.
- Structural cause: level 2 (a context) and level 3 (a specs tree) were fused inside `alive`; the
  command that owns repos also owned specs, backups (`core/specs_backup.py`) and commits.
- Direction: separate the levels at their seams — `SpecContextService.create` owns repos + hook + ALIVE +
  bind; `specs init` owns the specs tree; one pure function derives "what's next" from disk.

## 2. Seams and the deletion test

| Module | Change | Deletion test / justification |
|---|---|---|
| `core/specs_backup.py` | DELETE | fails the test (git `specs-bkp/` replaces it); caller in `spec_context/service.py` loses it |
| `features/workspace/bootstrap.py` | DELETE | a pass-through to clone+hook; `install_git_hooks` and `slug_from_url` move into `features/spec_context/service.py` (their one owner); `cli/commands/ci.py` re-imports |
| `features/spec_context/service.py` `alive` | SHRINK | scaffold, upgrade hint, `chore(scaffold)` commit removed; gains hook install (one line: the same helper `create` uses) |
| `features/spec_context/service.py` `create` | REPLACE | clone + adopt + hook + ALIVE + bind + rollback in one path; `create`+`alive` share one `_materialize` (collapse two clone paths into one) |
| `cli/commands/context.py` `create` | REPLACE | `--url`/`--associated-repos` removed, `--main-repo <url>` + repeated `--associated-repo`; fix line built from the parsed invocation (RV1) |
| `cli/commands/init.py` | REPLACE | flags and TTY prompts fill one `InitPlan`; per-asset listing deleted (R1); `--repo` calls `SpecContextService.create`; existing workspace → upgrade (A5) |
| `infrastructure/python_env.py` | SHRINK | temp re-packed wheel removed; ensurepip absence diagnosed as such (AC1.6) |
| `features/reconcile/service.py` | reuse | called by the upgrade path, unchanged interface |
| `cli/commands/specs.py` `init` + `features/specs/{canon,scaffolder}.py` | REPLACE | dadaia/foreign classification (D7/D9) in `canon`; foreign → `git mv specs specs-bkp`; no commit; English constitution, fixed sections |
| `features/workspace/onboarding.py` | NEW (≈60 lines) | justified: replaces three divergent "what's next" texts (`alive` hint, ctx_inject `[no bound context]`, docs); one pure `next_step(workspace_root) -> Step | None`, three callers — earns its keep by the deletion test (complexity reappears in 3 callers) |
| `cli/commands/doctor.py`, `features/spec_context/doctor.py` | SHRINK | ghost context → exit 1 + fix, no fallback to `<ws>/specs` (R4); hook check scoped to the context's repos (R5); onboarding finding from `onboarding.next_step` |
| `hooks/ctx_inject.py` | SHRINK | the zero-context branch prints `onboarding.next_step` text |
| `core/harness_registry.py` | read-only | source of the harness prompt choices (AC1.3); no change expected |

- Net production diff under `dadaia_workspace/` (Python) must be ≤ 0 at closure (AC9.3); measured by
  `git diff --stat 45620ce5..HEAD -- 'dadaia_workspace/*.py'` in the closure log. `onboarding.py` is the only
  new module; the two deleted modules and the `alive` branch pay for it.
- Bug surface: shrinks — the two recurring sites (create/alive split, scaffold-inside-alive) are removed,
  not patched.

## 3. Order of work (demolition first)

1. **RED acceptance first** — T-048-01 writes the FR8 journey with every scenario/level marked
   `xfail(strict=True, reason="T-048-nn")`; each later task flips its own marks.
2. **Demolish** — T-048-02 (alive's scaffold, `specs_backup`, auto-commit) and T-048-05 (level 3) run in
   parallel (disjoint write sets).
3. **Collapse level 2** — T-048-03 (create one step, `bootstrap.py` deleted).
4. **Level 1** — T-048-04 (init plan object, `--repo` delegates), then T-048-06 (re-init upgrade).
5. **Guidance** — T-048-07 (onboarding status in doctor/init/create/SessionStart; R2, R4, R5 doctor half).
6. **Text** — T-048-08 (first-pass skill section, parallel any time), T-048-09 (law + skills),
   T-048-10 (docs + fix-line contract test).
7. **Close the journey** — T-048-11 flips the last xfails, wires CI/release, re-runs the audit script.

## 4. Parallel groups (disjoint write sets)

| Group | Tasks | Why disjoint |
|---|---|---|
| P1 | T-048-01, T-048-02, T-048-05, T-048-08 | e2e file / spec_context+context.py+specs_backup / specs.py+canon+scaffolder / audit skill |
| P2 | T-048-03 | service.py + context.py + bootstrap.py + ci.py (after 02) |
| P3 | T-048-04 → T-048-06 | both own init.py + python_env.py (sequential) |
| P4 | T-048-07 | touches init.py, context.py, doctor, ctx_inject (after 03, 05, 06) |
| P5 | T-048-09 ‖ T-048-10 | public law/skills vs docs/README/tests contract |
| P6 | T-048-11 | e2e + workflows, last |

## 5. Traceability

| FR / AC | Task |
|---|---|
| FR1 AC1.1–1.7 | T-048-04 (AC1.5 with T-048-03) |
| FR2 AC2.1–2.3 | T-048-06; AC2.4 T-048-10 |
| FR3 AC3.1–3.6, 3.8 | T-048-03; AC3.7 T-048-02 (alive) + T-048-07 (doctor hooks) |
| FR4 AC4.1–4.6 | T-048-05; AC4.7 T-048-02 |
| FR5 AC5.1–5.2 | T-048-08 |
| FR6 AC6.1–6.3 | T-048-07; AC6.4 T-048-10; AC6.5 T-048-09 |
| FR7 AC7.1–7.2 | T-048-09, T-048-10; AC7.3 closure (dd-product-engineer — memory atoms are never a task write set, SPEC-DOC-047) |
| FR8 AC8.1–8.3 | T-048-01 (RED), T-048-11 (GREEN + CI) |
| FR9 AC9.1–9.3 | T-048-02, T-048-03, T-048-04; AC9.3 measured at closure |

## 6. Verification

- Per task: RED test first, `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` (unit+contract
  +integration) green; `dadaia public stage && dadaia public install && dadaia doctor` exit 0 on the instance
  after any `public/` change.
- Candidate: `pytest -m e2e tests/e2e/test_onboarding_journey.py` green with no xfail left; CI every job
  green on the develop PR; `.dadaia/tmp/onboarding-audit/<date>/run.sh` re-run (scenarios on the new CLI)
  ≥ 90/100; net Python diff ≤ 0.

## 7. Risks

- Shared version 0.4.7 between source and PyPI: T-048-01 builds the wheel with a `+e2e` local version.
- The journey needs `uv` and network for the previous-PyPI upgrade scenario; the scenario is marked
  `network` and runs in CI where uv is provisioned (T-048-11).
- A1 amends projected law: T-048-09 reprojects in the same task.
