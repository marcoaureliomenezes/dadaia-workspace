# TASKS — 0.5.0 rc-10, Job 9 — evals in the library's own CI

**Status:** Approved
**Approval:** pending — dd-code-reviewer review of this file and the PLAN amendment; SPEC amended at e261c7e8b, ADR 0217 accepted at cdecfbbdb. The P-33 rewrite in `specs/memory/QUALITY.md` is not this job's: a principle changes only in the commit carrying its accepted ADR (`specs/memory/AGENTS.md`), so it landed on the reconcile branch at daf177d2b, so that precondition is met. J9.S3.T4 keeps the atom, the catalog and the Gates line.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `GF/`); `ev:` = the dadaia-evals tree at c075ed6, the port's read-only source. Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every implementation brief carries the pre-review checklist, items 1–13. Platform facts go only through `dadaia_workspace/core/platform.py`. Host-side test code uses `Path` and `sys.executable`. Bash runs only inside a task container. `eval.yml` is ubuntu-only because the tasks need Docker.

- Edges: Jobs 7 and 8 merged: the mirror rule and the size decider in `tests/conftest.py`. J9.S1–S2 run beside Job 6. J9.S3 opens only after Job 6 has merged and the job branch is rebased on it, because both jobs write `S/dd-gitflow-default/SKILL.md` and `pub/entities/behavior-map.json`. Job 9 merges after Job 6, so the freeze (0209) binds its later stages: RED rows are a strict xfail on one `@pytest.mark.xfail(strict=True, reason=…)` line (PLAN agent default 11), and each GREEN task deletes only its own file's marker lines.
- Not ported: `ev:scripts/check_workflows.py` and its 40 `ev:tests/plants/*.yml`; their clauses become the guard (J9.S2.T3). Also not ported: `ev:tests/test_scripts.py`'s `WorkflowCheck` and `ClaudeCliPin` classes (the pin becomes the guard check `eval-cli-pin`), `ev:AGENTS.md`, `ev:README.md`, `ev:.github/workflows/ci.yml`, and the `DADAIA_WORKSPACE_LIB` lib-path variable. The lib is the checkout itself.
- Design seams, closed:
  - Wheel: `eval.yml` builds it from its own checkout sha, which is the dispatched ref or `main` on schedule. The step stamps `poetry version` from `release-please-config.json`'s `release-as` only when that file has one, else it builds at the pyproject version (main has no `release-as`, and the weekly schedule runs from main), then runs `poetry build -f wheel`. poetry comes from `pipx install poetry==2.5.1`, the repo's pin and above the guard floor.
  - How the graders' tests find the wheel: no env var. `tests/helpers/evals.py` builds the checkout with `_build_wheel` from `tests/e2e/test_one_line_bootstrap.py`, which is offline `pip wheel --no-build-isolation`. That is one builder, imported, never copied. `ci.yml` and the local `verify:` therefore set nothing.
  - Baseline: `dadaia-workspace==<baseline>` from PyPI. The input `baseline` is `required: false, type: string`, with no default (main's skeleton has the same). The job-level env holds `BASELINE: ${{ inputs.baseline || '0.4.7' }}`, so a schedule run gets 0.4.7 and the literal lives in one place.
  - Triggers: `workflow_dispatch` plus `schedule` (weekly, `cron: '0 6 * * 1'`).
  - The run job sits in environment `evals`. `CLAUDE_CODE_OAUTH_TOKEN` and `SCAN_SECRET` are read from `secrets.CLAUDE_CODE_OAUTH_TOKEN` only in that job's `env`. No other key reads a secret.
  - The run: one job on `ubuntu-24.04`. harbor comes from `pipx install harbor==0.23.0`. The run is T1 and T2, `-k 3 -n 2`, on the baseline and then on the candidate. Then `compare.py` (`continue-on-error`), the scan `python3 evals/scripts/scan.py evals/jobs evals/summary.md`, the summary line, the upload of `evals/jobs/` and `evals/summary.md`, and a last step that fails the job when compare blocked. The scan and publishing order is the guard's (J9.S2.T3).
  - The run job holds no check job: CI's `e2e-python` leg already ran the grader tests on the same sha.
  - Every `${{ }}` sits in an `env:`, never in a `run:` body, because `workflow-expression-in-a-run-body` judges every workflow.
  - Lib layer: each task's `environment/lib/requirements.txt` names `dadaia-workspace==<v>` or `/lib/<wheel>` beside it. It is written per run, in a tmp copy by the test helper or in the checkout by `eval.yml`, and is never committed.
  - Plants: the T2 fixes live in `tests/fixtures/evals/t2/` (`correct-fix.sh`, `assert-rewrite.sh`). The workflow plants become one-line `_edit` plants on `eval.yml` in `CHECKS["no-model-api-in-ci"]`.
  - The guard's adversary rows are plants under `scripts/guards/`, outside the `tests:` paths, so they are born with their clause in J9.S2.T3, as J8.S3.T1 did, and S1 holds none of them.
  - Docker, network and timeouts: the grader tests are e2e (`tests/e2e/**`, an `Owner:` line, the `e2e-python` leg on `ubuntu-latest`, where Docker and uv are already present). They are the suite's only Docker tests. A missing `docker` fails the row and never skips it.
  - The files declare `pytestmark = pytest.mark.timeout(600)`. The justification: evals' whole suite, with four image builds, took 95 s on ubuntu-24.04 (run 37554712931, c075ed6, 00:58:16Z–00:59:51Z).
  - No host venv is built: each image's venv lives in its container.
  - RED by assertion: the helper asserts that `evals/tasks/<task>` exists before any copy or Docker call, and the scripts tests assert on a subprocess exit code. A missing port therefore fails by `AssertionError`.
  - `evals/**/*.py` is outside mypy's `dadaia_workspace/ scripts/`, because it runs on each container's `python3`, stdlib only. ruff format and check run on any touched `.py` at the task gate; CI's lint `SRC` (`scripts/ci.py`) excludes `evals/` today, so J9.S2.T1 adds `"evals/"` to it (a one-line edit; the stage gate's full lint then covers the port) and the port is ruff-clean with behaviour unchanged.
  - `evals/tasks/*/tests/` is outside `tests: tests/**`. Graders stay editable, which AC11.6 needs ("fixed in the grader").
  - `ci.py task` collects owner tests only under `tests/` (J9.S2.T1). Today it would run `pytest` on `evals/tasks/*/tests/test_grade.py`, which holds no test function and exits 5.

## Stage J9.S1 — RED

- Contract: exit tests every AC11.1 row and J9.S2.T1's row RED as strict xfail. The stage gate's small tier runs `test_ci.py`. The three e2e files are run by hand: `pytest -p no:randomly -m e2e tests/e2e/test_evals_t1.py tests/e2e/test_evals_t2.py tests/e2e/test_evals_scripts.py` shows only `xfailed`. Every RED marker line is `@pytest.mark.xfail(strict=True, raises=AssertionError, reason=…)` on one line (it still matches the repo's `tests-red:` regex `^\s*@pytest\.mark\.xfail\(strict=True`), and the evidence includes the same command with `--runxfail`, which shows `AssertionError` per row. Envelope `tests/**`. ACs AC11.1.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J9.S1.T1 | AC11.1 | `tests/helpers/evals.py`, `tests/e2e/test_evals_t1.py`, `tests/e2e/test_evals_t2.py`, `tests/fixtures/evals/t2/correct-fix.sh`, `tests/fixtures/evals/t2/assert-rewrite.sh` | RED, ported from `ev:tests/test_t1_cold_onboarding.py` and `ev:tests/test_t2_block_list_bug.py`: each image builds with the 0.4.7 layer and with the checkout's wheel; the T1 grader passes a hand-onboarded workspace of each version and fails an empty one; on T2, on each version, the planted correct fix passes and the planted assert-rewriting fix fails |
| J9.S1.T2 | AC11.1 | `tests/e2e/test_evals_scripts.py` | RED, ported from `ev:tests/test_scripts.py` `Scan` and `Compare`, through `sys.executable evals/scripts/<x>.py`: scan exits 1 on a token in JSON or binary, a missing path, a planted token shape or `$SCAN_SECRET`'s value, and 0 on a clean tree; compare's seven gate cases |
| J9.S1.T3 | AC11.1 | `tests/scripts/test_ci.py` (one new function) | RED: `plan(["task", "evals/tasks/t1-cold-onboarding/tests/test_grade.py"])` holds no `owner tests` step, while a `tests/…/test_x.py` still gets one |

## Stage J9.S2 — the guard, eval.yml, the scripts

- Contract: exit tests J9.S1.T2 and T3 green; `python scripts/guards/run.py` and `--planted` green; unit green. Envelope `scripts/ci.py`, `scripts/guards/repo.py`, `.github/workflows/eval.yml`, `evals/scripts/**`, and the two test files' marker lines. ACs AC11.1–AC11.3.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J9.S2.T1 | AC11.1 | `scripts/ci.py` (`_task`: owner tests are `test_*.py` under `tests/` only; `SRC` gains `"evals/"`), `tests/scripts/test_ci.py` (its marker line) | `tests/scripts/test_ci.py` |
| J9.S2.T2 | AC11.1 | `evals/scripts/compare.py`, `evals/scripts/scan.py` (ported; docstrings cite 0217, never 0177/0179), `tests/e2e/test_evals_scripts.py` (its marker lines) | `tests/e2e/test_evals_scripts.py` |
| J9.S2.T3 | AC11.2, AC11.3 | `scripts/guards/repo.py`, `.github/workflows/eval.yml` | guard plants: `run.py --planted` reds each plant; `run.py` passes on the tree with `eval.yml` |

- J9.S2.T3 changes in `scripts/guards/repo.py`:
  - `no_model_calls_in_ci` (one decider, `check_workflows.py` merged in): a model marker — an `anthropics/*` action or reusable workflow, or `_MODEL_SECRET`, which gains `CLAUDE_CODE_OAUTH_TOKEN` — is refused in any workflow but `eval.yml`. The `check_workflows.py` clauses carry over with one narrowing: the every-workflow clauses (exact hosted `runs-on`, trigger allowlist, action allowlist) apply to `eval.yml` only, and clause (a) narrows "any job environment" to `environment: evals`, because `ci.yml` uses `runs-on: ${{ matrix.os }}` and `workflow_call`, and `release.yml` uses `environment: release-gate`/`pypi` on push. (a) any non-eval workflow that names `environment: evals`, or reads any non-`GITHUB_TOKEN` secret, is model-capable, so it runs on dispatch or schedule only; (b) the word `secrets` as a key or in an expression (minus `secrets.GITHUB_TOKEN`), anywhere outside `eval.yml`'s job-level `env`, which catches `secrets['X']`, `toJSON(secrets)` and a reusable call's `secrets: inherit`; (c) the publishing steps are contiguous after the scan step up to the last publishing step, so a write between or after them is refused.
  - In `eval.yml`: triggers are a non-empty subset of {`workflow_dispatch`, `schedule`}; every `runs-on` is an exact hosted label from a literal set, never self-hosted, a list or an expression; `secrets.` only in a job-level `env`; no `defaults`; actions only `actions/checkout@`, `actions/upload-artifact@`; publishing steps (upload, the `$GITHUB_STEP_SUMMARY` line) are unconditional, follow the canonical scan step and upload only what it covers.
  - New check `eval-cli-pin`: every `evals/tasks/*/environment/Dockerfile` `ARG CLAUDE_CODE_VERSION` equals `eval.yml`'s `env.CLAUDE_CODE_VERSION`. It is ported from `ClaudeCliPin`.
  - `_COPIED` gains `evals`.
- J9.S2.T3 plants, one line each:
  - a model secret in a push workflow;
  - `eval.yml` with `pull_request`;
  - `eval.yml` `runs-on: self-hosted`;
  - a workflow-level secret;
  - a step-level secret;
  - `defaults`;
  - an upload before the scan;
  - `if: always()` on the upload;
  - `continue-on-error` on the scan;
  - an action outside the allowlist;
  - an upload path the scan does not cover;
  - a mismatched Dockerfile ARG;
  - the source's plants, restored as one-line `_edit` plants, same names; `runs-on-list-hosted`, `action-prefix-lookalike` and `pull-request-target-no-secret` edit `eval.yml`, the `*-push` names plant a non-eval workflow, the rest edit `eval.yml`: `evals-environment-push`, `tojson-secrets-push`, `bracket-secret-push`, `write-after-scan`, `write-between-publishes`, `scan-or-true`, `scan-conditional`, `scan-wrong-path`, `summary-other-source`, `summary-unscanned`, `summary-step-extra-key`, `uses-summary`, `upload-on-failure`, `upload-not-cancelled`, `action-prefix-lookalike`, `runs-on-list-hosted`, `runs-on-prefix-label`, `lowercase-secret-push`, `renamed-secret-push`, `job-container-secret`, `pull-request-target-no-secret`, `quoted-on-push`, `no-on`, `env-dict-prt`, `defaults-job-level`; plus the new `reusable-call-has-no-runs-on`, which plants a non-eval push workflow whose job has `uses: ./.github/workflows/eval.yml` and `secrets: inherit`.
- J9.S2.T3 is mutated by hand through `run.py --planted`. Marker reasons stay short (line-length 100).

## Stage J9.S3 — the tasks; the public law states no model-API rule

- Contract: exit tests J9.S1.T1 green under `-m e2e`; guards (with `eval-cli-pin` over both Dockerfiles), unit, integration and e2e green. Envelope `evals/tasks/**`, the two e2e test files' marker lines, `pub/data/AGENTS.md`, `S/dd-gitflow-default/SKILL.md`, `S/dd-gitflow-default/CICD-AUTOMATION.md`, `CONTEXT.md`, `.github/workflows/ci.yml`, `specs/memory/QUALITY.md`, `specs/memory/product/sdd/sdd-gate-v3.md`, `specs/memory/product/catalog.json`. ACs AC11.1, AC11.4.
- Opens after Job 6 merged and the rebase (header). Nothing in it reads across tasks.
- The AC11.4 sweep, rerun at the close task with its hit count in the close commit body: `git grep -n -i 'model api\|model-calling\|model secret\|evals repo\|dadaia-evals' -- dadaia_workspace CONTEXT.md specs/memory .github scripts` prints only the expected residual hits, each listed in the close commit body with the count: the guard in `scripts/guards/`, `.github/workflows/eval.yml`, and the new P-33 text from 0217. Baseline at 4b5156bc3: 17 hits. ADR 0217's narrow grep, `git grep -n -i 'evals repo\|dadaia-evals' -- dadaia_workspace CONTEXT.md specs/memory`, prints nothing at the close task (6 hits today). The close task recounts both.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J9.S3.T1 | AC11.1 | `evals/tasks/t1-cold-onboarding/instruction.md`, `evals/tasks/t1-cold-onboarding/task.toml`, `evals/tasks/t1-cold-onboarding/environment/Dockerfile`, `evals/tasks/t1-cold-onboarding/tests/test.sh`, `evals/tasks/t1-cold-onboarding/tests/test_grade.py` (ported; the Dockerfile's last layer is the lib, its comment cites 0217), `tests/e2e/test_evals_t1.py` (its marker lines) | `tests/e2e/test_evals_t1.py` |
| J9.S3.T2 | AC11.1 | `evals/tasks/t2-block-list-bug/instruction.md`, `evals/tasks/t2-block-list-bug/task.toml`, `evals/tasks/t2-block-list-bug/environment/Dockerfile`, `evals/tasks/t2-block-list-bug/environment/project.sh`, `evals/tasks/t2-block-list-bug/tests/test.sh`, `evals/tasks/t2-block-list-bug/tests/test_grade.py` (ported, same rules), `tests/e2e/test_evals_t2.py` (its marker lines) | `tests/e2e/test_evals_t2.py` |
| J9.S3.T3 | AC11.4 | `pub/data/AGENTS.md` (map §3: the model-API clause leaves the git-chokepoints line), `S/dd-gitflow-default/SKILL.md` (§3b: the model-API bullet and its five clauses leave), `S/dd-gitflow-default/CICD-AUTOMATION.md` (its model-API wiring note leaves), `CONTEXT.md` (the term "Evals repo" leaves), `.github/workflows/ci.yml` (line 7's "No job calls a model API" clause leaves; the security-review half stays) | check: the AC11.4 sweep over these paths prints only the expected residual hits |
| J9.S3.T4 | AC11.4 | `specs/memory/QUALITY.md` (the Gates line, "no job calls a model API (P-33)", names `eval.yml` as the one exception; `### P-33` is not touched here, see the header), `specs/memory/product/sdd/sdd-gate-v3.md` (the "no workflow calls a model API" line and summary name `eval.yml` as the one exception), `specs/memory/product/catalog.json` (by `memory.py catalog generate`) | author `dd-product-engineer` (memory law); check: `memory.py check` green and the AC11.4 sweep over `specs/memory` prints only the expected residual hits |
| J9.S3.T9 | — | this file | close task, last. It regenerates `pub/entities/behavior-map.json` (T3 moved skill hashes) and runs the AC11.1 wheel check: `pip wheel --no-deps --no-build-isolation -w <workspace>/.dadaia/tmp/<agent>/<YYYYMMDD>/ .` (`<workspace>` is the workspace root, never the repo tree) then `python -c "import zipfile,glob,sys; sys.exit(any(n.startswith('evals/') for n in zipfile.ZipFile(glob.glob('<workspace>/.dadaia/tmp/<agent>/<YYYYMMDD>/*.whl')[0]).namelist()))"` exits 0. It reruns the sweep and writes `test-audit:`, `mutation:` (compare, scan, `ci.py _task`, the guard clauses by hand mutants) and `done` |

## Stage J9.S4 — after the job merges to `feature/0.5.0` (driver)

- Contract: no acceptance test exists (AC11.5, AC11.6 are observed). The driver logs each row as a `_RELEASE.json` `kind: note`. ACs AC11.5, AC11.6.
- A grader that fails in the run is a bug: register it, fix it in the bug batch with a RED row in `tests/e2e/test_evals_t<n>.py` (the graders are outside `tests:`), and run that task once more before Reconciliation.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J9.S4.T1 | AC11.5 | — (driver, operator order "Eu gravo via gh api": main gets only the dispatch-only skeleton, blob `924b17769edacf82562b12029f5425e8d17f502c`, dd-code-reviewer APPROVED, delivered once the operator lifts `enforce_admins`. At the promote, the add/add conflict on `eval.yml` takes the feature version: the stub lacks `env.CLAUDE_CODE_VERSION`, so the `eval-cli-pin` check catches a wrong pick) | check: `gh api repos/marcoaureliomenezes/dadaia-workspace/contents/.github/workflows/eval.yml?ref=main` succeeds |
| J9.S4.T2 | AC11.6 | — (driver: `gh workflow run eval.yml --ref feature/0.5.0`, after the operator sets `CLAUDE_CODE_OAUTH_TOKEN` in Environment `evals`, branches `main` and `feature/*`; confirms `dadaia capabilities --json` names the stamped candidate and that `evals/jobs/` holds no rate-limit error) | check: the `kind: note` names the run URL, the verdict per 0178 (2), tokens and wall time |

- done: Job 9 — every task landed on `wt/0.5.0-rc10/job9`: J9.S1.T1 8ec72c78e, T2 045e5227a, T3 d90143964; J9.S2.T1 8cb15d6c0, T2 46acad8ef, T3 656ed4e8d; J9.S3.T1 1aea48077, T2 ee18dd596, T3 66e1306da, T4 59910d096; closed by J9.S3.T9 89e852fad. J9.S4 is the driver, after the merge.
