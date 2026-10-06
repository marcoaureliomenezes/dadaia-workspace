# PLAN — Release: 0.5.0, candidate 10

**Status:** Approved — by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

The SPEC says what; this PLAN holds the as-is review, the DAG, the hot files and the schedule; `tasks/<job>.md` holds each job's stages and tasks. Read at `feature/0.5.0` d1d4d36c4 and on `wt/0.5.0-rc9/reconcile` 506d6835b (rc-9's JR.S5–S6 not yet on the work branch; rc-9's Reconciliation merged at cfe73a297). Path aliases: `f/` = `dadaia_workspace/features/`, `pub/` = `dadaia_workspace/public/`, `S/` = `pub/skills/`, `bugres/` = `S/dd-bug-resolution/`, `relimpl/` = `S/dd-release-implementation/`, `GF/` = `S/dd-gitflow-default/scripts/`, `evals:` = a path in `repos/dadaia-evals`.

## As-is review

Order per job: DELETE → REBUILD → UPDATE → KEEP → ADD. A REBUILD names its structural cause.

| job | unit | today | bugs on the unit | verdict | why |
|---|---|---|---|---|---|
| 1 | `bugres/scripts/bugs.py` `_fixes`, `_direction`, `fix` | greps subjects; a shape-4 task commit is linked with rows `None`, never diffed; a class commit (`chore(bugs): <verb> class …`, ids on body lines) is never linked | T-050-167 built it; `bugs-fix-nonrepo-test-not-portable` (rc-8, caused_by T-050-167); `bugs-fix-lists-one-commit-twice` (rc-9, de36b0e69); `bugs-fix-counts-a-reverted-fix` (rc-9, resolved by bd0628092, rewritten in-job by e638d4a88): 5 commits on `_fixes` (48376cb96, 19eb4c1a1, de36b0e69, bd0628092, e638d4a88) | REBUILD (AC1.1) | cause: the reader is a subject regex with one branch per shape; each shape added a branch and each fix patched one key or one arm. Redo: one link step (subject id list, or class body ids) then one diff step for every linked sha, a `Revert "…"`-undone fix dropped in the link step (absorbing bd0628092's and e638d4a88's arm, and fixing their two ceilings, SPEC AC1.1 (a) and (b)); the reader leaves `bugs.py` for its own module so `fix`, `stats`, `window` and `_candidates` read one function. Every prior fix's test rows stay unchanged |
| 1 | `bugres/scripts/_bugs_transition.py` `REQUIRED_BY_VERB["resolve"]` | `evidence_seam` retired by 0164 (4); 116/317 stored seams name a missing file | 0 on the unit | UPDATE (AC1.2) | required at resolve, checked textually there only; `check` unchanged; `window` marks a gone seam file |
| 1 | `S/dd-audit-project/PILLAR-BUGS.md:8`; `bugres/LINEAGE.md` step 7; `pub/scaffold/bugs/AGENTS.md` §2; `S/dd-code-review/SKILL.md:55`; `S/dd-release-definition/SKILL.md` §1 | "counted, never diffed"; bare `rebuild: none`; REBUILD only for a fix-induced bug; "or why not" | — | UPDATE (AC1.3–AC1.5) | law text; the canon pin moves with the scaffold law |
| 2, 3 | `evals:` repo | no `tasks/`, no `verify:`/`tests:` lines; `eval.yml` (main) never ran | 0 | ADD (AC2.1–AC3.1) | new tasks T1, T2; the graders are the product |
| 4 | `specs/memory/QUALITY.md` | no `## Bugs`; lessons live in the `bug-ledger` atom and four QUALITY sections, re-derived to `docs/bug-ledger-lessons.md` | 0 | ADD (AC4.1–AC4.4) | Job 4 ships the generator (`bugs.py` verb, new `bugres/scripts/_bugs_balance.py`, tests in `tests/unit/skills/test_bug_resolution_balance.py`), the closure check in `relimpl/scripts/_release_tree.py` and `## Bugs` in the scaffold memory law; Reconciliation writes the first block, the review and the atom move (AC4.5) |
| 4 | `f/specs/memory_lint.py:90` | LINT-1 already skips fenced code | 0 | KEEP | AC4.4's exemption holds today; no task |
| 5 | `f/spec_context/doctor.py` `check_installed_hooks` | `OSError` → `drifted = True`, one message "differs" | 0 since the 0.4.8 split | UPDATE (AC5.1) | one code, the message names absent vs differing; fix line unchanged |
| 6 | `GF/_worktree_end.py` `merge`, `_gate` | no test-path notion; `_gate` reads `verify*` from `<work>:AGENTS.md` | 7 records (rc-7 ×3, rc-8 ×3, rc-9 CRITICAL `verify-line-absent-…`, REBUILT under 0207) | UPDATE + ADD (AC6.0–AC6.2) | the hottest unit of the repo: the freeze lives in a new `GF/_worktree_freeze.py` (one pure judge over diff rows plus one git read); `merge` gains one call; the `AGENTS.md` line reader is lifted out of `_gate` so `verify*:` and `tests:` share one reader — no second authority. REBUILD trigger judged (≥ 2 fixes on the unit): it does not fire — the seven records hit `merge`'s kind and verdict arms, all REBUILT in rc-9 (0190) and `_gate` under 0207; none touches the code Job 6 adds, and Job 6 adds no arm to them |
| 6 | `pub/scaffold/releases/AGENTS.md` §3 same-task rewrite clause | allows rewriting a test in a code task | — | DELETE (AC6.3) | 0209 |
| 6 | `tests/unit/core/test_specs_version.py` `_CANON_AT` | the canon pin lives in a test file, so every law change edits a test | — | UPDATE | the pin moves to `core/specs_version.py`, (J6.S2.T4) |
| 7 | `tests/{unit,contract,integration}/**` (307 files), `tests/conftest.py` `_PATH_MARKERS`, `_TIER_TIMEOUTS` | tier from the folder | `windows-…` tier-ceiling bugs ×2 calibrated in the table | REBUILD (AC7.1–AC7.3) | cause: folder = size let a subprocess test sit in `unit/`; the size comes from the fixture (real git or a subprocess → medium) |
| 7 | `scripts/ci.py`, `.github/workflows/ci.yml`, `pyproject.toml` markers | select by folder and by `unit`/`contract`/`integration` | 0 | UPDATE | select by size marker |
| 8 | `tests/unit/conftest.py` autouse `worktree_rows` patch; `tests/contract/cli/test_cli_context.py:350` | monkeypatch of a module global | `unit-tests-spawn-the-worktree-script-through-a-cli-stub` | DELETE (AC8.2) | `SpecContextService`, `DoctorService` take a rows callable by constructor |
| 8 | `scripts/guards/isolation.py` `hook-stdin-not-in-process` | lists patch forms one by one | `hook-stdin-guard-misses-raw-assignment` (caused_by T-050-160), `heartbeat-test-drives-hook-in-process` | DELETE (AC8.3) | cause: a guard enumerating patch shapes; the harness `tests/fixtures/harness_env.run_hook_subprocess` is the one way |
| 8 | small tests spawning a process | present, unmeasured | rc-7 slow-class G4 | REBUILD (AC8.1) | pure core extracted, or the test turns medium |

- Job 1, rows the window gains at the rebase (two more bugs confirmed after the SPEC: `bugs-fix-counts-a-reverted-fix`, resolved by bd0628092 on the fix reader, and `memory-window-bound-unreachable-from-head`, `S/dd-spec-navigator/scripts/_memory_drift.py`): each REBUILD row becomes one born task (`tasks/job1.md` J1.S3.T2+); a KEEP row needs none. The first is absorbed by AC1.1's single link step (its test row stays).

### Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| which commits fixed a bug, their surface and rework | `bugres/scripts/_bugs_fix.py` (Job 1) | `bugs.py` `fix`, `stats`, `window`, `_candidates` | `bugs.py` `_fixes`, `_direction`, the `None` arm |
| which paths are tests | the `tests:` line of `<work>:AGENTS.md`, read by the one line reader lifted from `_gate` (Job 6); with `tests-red:`, the one marker form whose deletion lands | `GF/_worktree_freeze.py` | — |
| a test's size tier | the fixtures it requests, `tests/conftest.py` (Job 7) | `scripts/ci.py`, `ci.yml` selectors | `_PATH_MARKERS`, the folder rule |
| a context's worktree rows | the rows callable `SpecContextService`/`DoctorService` take by constructor (Job 8) | `container.py`, `tests/fakes.py` | the module-global `worktree_rows` read, the autouse patch |
| how a hook test feeds stdin | `tests/fixtures/harness_env.run_hook_subprocess` (Job 8) | every hook test | the `hook-stdin-not-in-process` guard check, `sys.stdin` patches |
- Bug-surface delta expected: Job 1 reduces (one reader, the `None` arm gone); Job 5 neutral; Job 6 adds a module but no branch to `merge`'s kinds; Jobs 7–8 reduce (a guard check, an autouse patch and a folder rule gone).

## DAG

| job | waits on | why |
|---|---|---|
| Job 1 | — | runs from minute 1 |
| Job 2 | — | `dadaia-evals` only; disjoint |
| Job 3 | Job 2 | AC3.1 runs `eval.yml` from evals `main`, after Job 2's PR edges merge |
| Job 4 | Job 1 | both write `bugres/scripts/bugs.py` and the canon pin; Job 4's tests go to its own `tests/unit/skills/test_bug_resolution_balance.py` (the SPEC's "an edge") |
| Job 5 | — | `f/spec_context/doctor.py` and its two test files; disjoint from 1, 2, 4 |
| Job 7 | Jobs 1, 4, 5 | Job 7 moves every test file those jobs write; they land first in today's paths |
| Job 8 | Job 7 | `tests/conftest.py`, `test_cli_context.py`'s moved path (SPEC edge) |
| Job 6 | Jobs 1, 2, 3, 4, 5, 7, 8 | SPEC: the DAG's last job; the canon pin after Job 1's; `tests/conftest.py` after 7, 8 |
| Bug batch | Job 6 | AC9.1; opened after Job 6, so frozen |
| Reconciliation | Bug batch | AC10 |

- Critical path: Job 1 → Job 4 → Job 7 → Job 8 → Job 6 → bug batch → Reconciliation.
- Job 6 was parked on F-3 (c32f07811) and is un-parked by the ruling (a); the bug batch and Reconciliation run under the freeze.
- After every job that writes `pub/` (Jobs 1, 4, 5, 6, 8) the driver re-projects the instance (`dadaia public stage` / `install` / `doctor`); `WT merge` runs the projected `worktree.py`, so the freeze binds only once Job 6 is re-projected.

### Hot files

- `bugres/scripts/bugs.py`: Job 1, then Job 4. `tests/unit/skills/test_bug_resolution_bugs_script.py`: Job 1, then Job 7 (move); Job 4 writes its own `test_bug_resolution_balance.py`.
- `S/dd-spec-navigator/scripts/_memory_drift.py`: Job 1 only (J1.S3.T2). `tests/unit/skills/test_memory_drift.py`: Job 1 (J1.S3.T2), then Job 7 (move); the DAG edge Job 7 ← Job 1 orders them.
- `core/specs_version.py`, `pub/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py` (canon pin): Job 1 (AC1.5), Job 4 (scaffold memory law), then Job 6 (AC6.3).
- `S/dd-release-definition/SKILL.md`: Job 1 (§1), then Job 6 (§5).
- `f/spec_context/doctor.py`: Job 5, then Job 8.
- `tests/conftest.py`: Job 7, Job 8, Job 6, in that order. `scripts/guards/isolation.py`: Job 7, then Job 8.
- `specs/memory/QUALITY.md`: Reconciliation only (AC4.5, AC10.1, AC10.2).
- `specs/bugs/BUGS.jsonl`: written only by `bugs.py`; a rebase conflict is redone by its writer (0180).
- `specs/releases/0.5.0/_RELEASE.json`: the driver's `kind: merge`/`note` entries, one job at a time.
- Generated, in no `W:`: `pub/entities/behavior-map.json` and the derived docs; each job's close task regenerates them.
- Job 6 and Job 8 file `W:` sets name today's test paths; at each job's open the driver rewrites them to Job 7's mirror paths (an edit to that job's own file).

### Parallel schedule

Tests run only in the main thread's serialized `WT merge` and stage/job gates; a task agent runs at most its task gate, and at most 2 task agents run at once. Lane A holds the critical path.

| wave | lane A | lane B | opens when |
|---|---|---|---|
| 1 | Job 1 | Job 2 | rc-10 enters (rc-9 CLOSURE + rebase) |
| 2 | Job 4 | Job 5 | Job 1 merged (A); Job 2 merged (B) |
| 3 | Job 7 | Job 3 (CI run; grader fixes take the slot) | Jobs 4, 5 merged; Job 2 on evals `main` |
| 4 | Job 8 | — | Job 7 merged |
| 5 | Job 6 | — | Jobs 3, 8 merged |
| 6 | bug batch | — | Job 6 merged and re-projected |
| 7 | Reconciliation | — | bug batch merged |

## Agent defaults — unruled

Each is the literal, smallest-surface reading; the reviewer judges it; none is an operator ruling.

1. AC1.1: the REBUILT reader moves to `bugres/scripts/_bugs_fix.py`; `bugs.py` keeps the verbs.
2. AC3.1: Job 3 opens a `dadaia-evals` tree only if a grader needs a fix; its run note is the driver's `_RELEASE.json` `kind: note`, written with Job 3's `kind: merge` entry; with no tree Job 3 logs only that note. Evals trees cannot write dadaia-workspace files: Reconciliation writes Jobs 2 and 3's `done` lines.
3. AC4.1: the generator is a `bugs.py balance` verb (`--write` regenerates the block); the dev-tooling class is the `.gitattributes` attribute `dadaia-dev-tooling`.
4. AC6.1 "cannot close": a RED test is a strict xfail; the suite's conftest gives every strict xfail `raises=AssertionError`, so an erroring RED test reads failed and `WT stage` refuses on the existing `verify-stage:` line. `worktree.py` learns no language. Known limit: evals' `unittest.expectedFailure` counts an error as an expected failure.
5. AC6.2 (the reviewer's literal reading): the anchor derives from subjects — the parent of the job's first commit outside `J<n>.S1`, else the job base — and the freeze fails closed when it cannot derive one; after the anchor any modified or deleted test line, in any file, refuses, except a `tests-red:` marker deletion (F-3 (a)) and a pure rename; added test lines land only in a group (a stage id; a commit with no stage id is its own group) that touches test paths alone. Residual: an added line (an inserted skip) passes the gate; the law text names it as caught by the RED review and test-audit.
6. AC7.1 mirror: `dadaia_workspace/<p>/<m>.py` → `tests/<p>/test_<m>.py` (a leading underscore kept: `_bugs_fix.py` → `test__bugs_fix.py`), a hyphen in a directory becoming `_` (importable packages); `scripts/<p>/<m>.py` → `tests/scripts/<p>/test_<m>.py`; the suite's own tests (conftest, `harness_env`) → `tests/fixtures/test_<m>.py`.
7. AC7.3 markers: `small`, `medium`, `e2e` replace `unit`, `contract`, `integration`; the tier timeouts keep their values under the new names (small 10 s, medium 60 s).
8. Job 7 → Job 8 bridge: Job 7 moves `tests/unit/conftest.py`'s autouse fixture into `tests/conftest.py`, applied to `small` items, so the moved tests keep it; Job 8 deletes it.
9. F-3 (a) form: the repo declares `tests-red: <regex>` beside `tests:` in its tracked `AGENTS.md`, read by the same line reader; one regex, one line. dadaia-workspace: `^\s*@pytest\.mark\.xfail\(strict=True`; dadaia-evals: `^\s*@unittest\.expectedFailure`. A repo with no `tests-red:` line lets no marker deletion through. The evals line: resolved by the main thread on evals `feature/0.5.0`.
10. Amendment visibility (AC6.3): the gate sees no approval and no gate path edits a pre-anchor test line (HIGH-2 stays closed). An amendment lands as a new tests-only RED stage that adds the corrected test; the wrong test's existing lines change only past the refusal's `Operator action:` (stop and report), by the operator's act. The approval lives in the job file and the review. No law changes; the alternative (a tests-only stage editing pre-anchor lines through the gate) would reopen HIGH-2 and is left unruled.
11. The RED marker's form (HIGH-A): one decorator line matching `tests-red:`, a one-line `reason` at 100 columns, never `marks=` in `pytest.param` nor a module constant, a parametrized RED row its own function. A marker-only deletion can leave `import pytest` unused; the option weakening no check is the authoring rule "a RED test file uses pytest beyond the marker", never a ruff F401 ignore.

### For the operator — consequences of reading 10

- "The operator's own act" is a direct commit on the work branch.
- Overnight, a wrong pre-anchor test stops its job until the operator acts.

## Flagged — not chosen (law or ruling)

- F-1 (MEDIUM-1): shape 3 (`dd-gitflow-default` §3a) is ONE commit holding code + regression test + the `BUGS.jsonl` line; under AC6.2 a fix commit touching a test after the anchor refuses. J6.S2.T4's `W:` carries `S/dd-gitflow-default/SKILL.md` and `bugres/SKILL.md` with their hash re-record; resolved with F-3: J6.S2.T4 rewrites shape 3 as a RED commit in a RED stage, then a fix commit with the code, the `BUGS.jsonl` line and the marker-line deletion (0209 + F-3 (a)).
- F-2: resolved — the four gate lines are on `dadaia-evals` `feature/0.5.0` by cbaa6f3 (operator act by delegation), CI run 37463825307.
- F-3 (HIGH-1) — RESOLVED, operator ruling 2026-10-06 (AskUserQuestion), verbatim: "(a) Só apagar a linha de marcação RED (Recommended)" (handoff `2026-10-06T044815Z-main-thread-overnight-delegation`). Job 6 un-parked; form: reading 9. Was: the freeze has no way to turn a RED test green — AC6.2 refuses the strict-xfail mark removal, and the canon pin `_CANON_AT` lives in a test file. Options: (a) the freeze allows a diff whose only change deletes a RED-marker line the repo declares beside `tests:`; (b) the RED expectation leaves the test files; (c) a non-strict xfail plus a tests-only flip stage. The pin's move to `core/specs_version.py` is recorded independent of the choice (J6.S2.T4). 
