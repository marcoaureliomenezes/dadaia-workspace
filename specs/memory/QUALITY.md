---
slug: QUALITY
title: quality-assurance
tldr: The measured quality principles, the test architecture (tiers, flake and quarantine policy) and the CI gate set with its slop ratchets.
summary: Canonical memory — statements and laws of testing and quality, each naming its code evidence.
tags: [testing, pytest, ci, quality, test-architecture, flake, quarantine, privacy]
---

## Principles

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS tier-timeout`; `--planted` turns it red on a test without its tier timeout and on an overridden explicit timeout.
Rationale: a test needing more time than its tier is mis-tiered.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS quarantine-needs-bug`; `--planted` turns it red on a `quarantine` mark without `bug=` and on a gating selector in `.github/workflows` that keeps the lane.
Rationale: the registered id is what makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS private-import-ratchet` (AST-exact; `scripts/guards/suite.py` is the ceiling's numeric home).
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` is the one list, and `flaky`/`quarantine` are always among them.
Measured by: `pytest --collect-only -q` exits 0 under `--strict-markers` in `pyproject.toml`'s `addopts`, which refuses any mark absent from `markers`.
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.

### P-33 · Only the library's own `.github/workflows/eval.yml` calls a model API, and only in `workflow_dispatch` or `schedule` jobs, each leg reading its one harness secret at job level from the `evals` environment and scanning every upload first (ADRs 0217, 0281); no other library workflow uses an `anthropics/*` action or references a model secret; the shipped law states no rule about a user's CI.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS no-model-api-in-ci`.
Rationale: a model call on a PR path fails closed without the paid key and exposes it; evals measure what ships, from the repo that ships it.

## Test architecture

- Size tiers `small` (10 s: no process, no real git), `medium` (60 s: reaches a process or real git) and `e2e` (120 s: a journey in `tests/e2e/**` naming its `Owner:`), read from what a test reaches by `tests/conftest.py`, never from its folder; a small test that starts a process fails (`small-spawns-no-process`); live Codex-binary validation is opt-in outside CI.
- `tests/<p>/test_<m>.py` mirrors `dadaia_workspace/<p>/<m>.py`, a second file for a module is `test_<m>__<topic>.py` (`tests-mirror-the-package`).
- The suite is hermetic; `tests/conftest.py` blocks a real Codex call without its live flag and fakes `ensure_workspace_venv`.
- `tests/conftest.py` prepends this checkout to `PYTHONPATH` once for the whole session, so every spawned CLI/hook subprocess imports the worktree under test, never the venv's installed package.
- Every guard check enumerates one set — `scripts/guards/run.py`'s `tracked()` over `git ls-files` — so a scratch file another process writes is outside the measurement by construction.
- Output naming a foreign Spec Context is `--redact`ed before entering evidence.

- `flaky` marks a pass-and-fail on identical code; `quarantine` leaves every gating selector, is bug-gated by P-22, and the lane is empty.
- Growth past the per-job wall-clock budget of ADR 0284 (the per-job maximum of the green runs it measured) is a budget breach, judged by `dd-code-reviewer` reading the CI job durations (`gh run view`, per job); the Windows and macOS legs carry no budget.
- A test, or an existing assert, leaves the suite or is removed or skipped only on the operator's order (root map §1, ADR 0249); a bug fix hardens the contract test in that contract's one home and never loosens it, and a cross-cutting contract may gain one parametrized home beside its per-site tests.
- Scaffolding (a seam RED, a refactor pin, a bug reproduction) lives in a versioned `tests/tmp/job-<n>/` (a hotfix lane: `tests/tmp/<bug-id>/`), collected during the job; the job merge refuses while git tracks a file there, so each test is promoted into its contract's home (the job's `merge` through `dadaia worktree`).
- Mutation runs from this repository's dev group: `scripts/mutate.py` mutates only a diff's lines and prints the score, the survivors, the kill matrix and the diff's branch coverage. Its readout is optional review evidence, never required; no gate and no test reads it as pass or fail, and it never authorizes a deletion (ADR 0248 as amended by 0249).

## Gates

- CI runs ruff (its preview rule `PLW1514`, a text open with no explicit encoding, selected alone through `explicit-preview-rules`) and `lint-imports`, mypy `--strict`, the guards (`scripts/guards/run.py`, plain and `--planted`), the small tier on Linux, the `not e2e` coverage run on Linux, Windows and macOS, the small tier again on Windows and macOS with an importability smoke, the medium tier, Python E2E, repo hygiene, `dadaia doctor` over the checked-out tree, PR governance and gitleaks — every PR job a required status check listed in `.github/required-checks.json` (`required-checks-listed`), gitleaks included; on a PR into `main` the model-free `Eval gate` passes only with a green `eval.yml` run on a commit whose diff to the head is release bookkeeping (`evals/scripts/gate.py`); no job calls a model API (P-33) except `.github/workflows/eval.yml`, the one exception (ADR 0217).
- Push triggers are `main`, `develop`, `feature/**` and `wt/**`; PRs to `develop` or `main` run the same matrix.
- `pr-source-guard` is fail-closed; the security review of both PR edges is the `dd-code-reviewer` security lens on the PR head, run by the main thread before the PR.
- Every review verdict states the bug-surface delta from each touched file's history, the id-line query `git log -E --grep '^(fix|refactor)\(bugs\): ' -- <file>`, and no deploy is approved without the consumer-side matrix.
- Caches redirect by configuration, never by a remembered flag: `[tool.pytest.ini_options] addopts` (`-p no:cacheprovider`), hypothesis `database = None`, and ruff and mypy write to the absolute `.dadaia/tmp/<tool>-cache` that every harness env exports (`workspace_layout.TOOL_CACHE_ENV`); a bare `pytest`, `ruff check`, `ruff format --check`, `mypy --strict` from any cwd leaves the tree clean (`tests/infrastructure/test_runtime_config__tool_caches_stay_in_the_tmp_zone.py`).
- The forbidden repo-local set is `core/workspace_layout.REPO_TREE_EXCLUDED`, measured here by `ci.yml`'s `repo-hygiene` job and swept at every ALIVE repo by `dadaia doctor`.
- Memory-vs-code drift is a `dadaia doctor` `specs`-section WARNING (`MEM-DRIFT-2`, a dead `dadaia <verb>` or path an atom cites), never a push-gated test: a verb deleted mid-implementation is memory drift to fix at the next closure, not a red build. The one exception is this repo's features package map: the guard `features-map-matches-architecture` (`scripts/guards/repo.py`) fails the build while `ARCHITECTURE.md`'s map and the tracked feature packages disagree.
- A citation of a superseded decision is an ERROR (`ADR-SUPERSEDED-CITATION`): a rule pointing at a dead ADR fails the build.
- A doctor fix is proven on the executed path in the fix-line contract's one home, `tests/core/test_cli_line__fix_line_contract.py`: its doctor-specs and doctor-workspace sites execute each rule's fix line against a planted finding and re-run the rule, which must then emit nothing, never the fixer's return value, beside the per-rule cases of `tests/cli/commands/test_doctor.py`; the `ledgers` section delegates to each ledger's skill script (`tests/infrastructure/test_ledger_scripts__doctor_ledgers_delegate_to_scripts.py`); a schema drop ships with its repair and its test in the same change. The same home greps every `.py` and `.sh` file of the package and finds an `Agent action:` or `Operator action:` literal only in the kernel's `act` producer and the pre-push shim's one fix line.
- The closed pytest marker set is seven — e2e, small, medium, slow, tmp, flaky, quarantine (P-28).
- Every `ci.yml` checkout fetches full history (`ci-checkout-history`); `release.yml`'s build and `secret-scan.yml` fetch full history; no job fetches history for a bug record's sake.

- Repo-pure ratchets move only downward and run as `scripts/guards/run.py` checks: `suite.py` holds `private-import-ratchet` (V26, P-23); `slop.py` holds V32 at ceiling 0 over the three trees `dadaia_workspace/`, `tests/` and `scripts/` (a governance-id grammar judged by kind, one named group per id kind, plus every exact bug and backlog id of the ledgers and their archives, skill and persona names excepted, in comment tokens and docstring lines), `ignore-cap` (suppressed layering edges, P-10) as a pinned count, V37 (one home per definition), V38 (deletes only in `features/spec_context/sweep.py`) and V39 (every doctor code has a fix-clears case) as keyed allowances whose keys stay within their birth keys, V40 (every JSONL ledger read through the one reader) and V41 (no locale-decoded subprocess output) at zero; no check pins a file's line or byte count (`no-size-pin`, ADR 0143).
- The documentation contract `tests/contract/test_docs_derived_from_memory.py` checks the authored-document set, complete `llms.txt` navigation, absolute README links, one tagline, the five PyPI links, live CLI/path citations, byte equality between `docs/cli.md` and `render_digest()` and between `llms-full.txt` and `scripts/llms_full.py`'s output, `llms.txt` linking `llms-full.txt`, every PyPI keyword named by the README, the README agent section opening with at most five lines, and `docs/index.md` and `docs/quickstart.md` naming `init --from` with no `pip install` promise on the index; `tests/e2e/test_onboarding_journey.py` runs the quickstart's three shell blocks as printed. Closure reconciles prose from changed atoms; no prose hash marker is stored.
- Stale handoffs and scratch are a closure readout, never a ratchet: reconciliation runs `dadaia doctor` dry and then its own repair lane; the release log retains only the summary and one structured memory record for closure.
- `dd-audit-project` pillar 2 re-measures the ratchets over the audit window and applies every `dd-code-review` SLOP.md signal to a commit sample; the fixed law sections are kept byte-exact by `dadaia doctor` FIXED-1/2.

Related: [[ARCHITECTURE]]

<!-- dadaia:fixed slop-tests -->
### Slop — tests (fixed)
- A test follows the root `AGENTS.md` map §1 test basics; an own module is tested through its interface.
- A test name states current behavior; a tombstone is a test of an absence (removal: root map §1).
- Detection: `dd-code-review` SLOP.md S3.
<!-- /dadaia:fixed slop-tests -->
