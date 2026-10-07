---
slug: QUALITY
title: quality-assurance
tldr: The measured quality principles, the test architecture (tiers, flake and quarantine policy) and the CI gate set with its slop ratchets.
summary: Canonical memory — statements and laws of testing and quality; a `### P-NN` principle changes with its accepted ADR, any other section under the ADR 0138 lane.
tags: [testing, pytest, ci, quality, test-architecture, flake, quarantine, privacy]
---

## Principles

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS tier-timeout`; `--planted` turns it red on a test without its tier timeout and on an overridden explicit timeout.
ADR: 0167 (accepted)
Rationale: a test needing more time than its tier is mis-tiered.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS quarantine-needs-bug`; `--planted` turns it red on a `quarantine` mark without `bug=` and on a gating selector in `.github/workflows` that keeps the lane.
ADR: 0167 (accepted)
Rationale: the registered id is what makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS private-import-ratchet` (AST-exact; `scripts/guards/suite.py` is the ceiling's numeric home).
ADR: 0167 (accepted)
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` is the one list, and `flaky`/`quarantine` are always among them.
Measured by: `pytest --collect-only -q` exits 0 under `--strict-markers` in `pyproject.toml`'s `addopts`, which refuses any mark absent from `markers`.
ADR: 0167 (accepted)
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.

### P-29 · We derive every human- and agent-facing document from a named memory atom under a content hash: each `## ` section of `README.md`, `llms.txt` and every `docs/*.md` names its atom and the atom's current sha256, and `docs/cli.md` is the committed output of `dadaia help tree`.
Measured by: `pytest tests/contract/test_docs_derived_from_memory.py`.
ADR: 0012 (accepted)
Rationale: a document written beside memory rots; one that names its source is red the moment the source moves.

### P-33 · Only the library's own `.github/workflows/eval.yml` calls a model API, and only in `workflow_dispatch` or `schedule` jobs, reading the model secret at job level from the `evals` environment and scanning every upload first (ADR 0217); no other library workflow uses an `anthropics/*` action or references a model secret; the shipped law states no rule about a user's CI.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS no-model-api-in-ci`.
ADR: 0217 (accepted, superseding 0177 and 0179)
Rationale: a model call on a PR path fails closed without the paid key and exposes it; evals measure what ships, from the repo that ships it.

## Test architecture

- Size tiers `small` (10 s: no process, no real git), `medium` (60 s: reaches a process or real git) and `e2e` (120 s: a journey in `tests/e2e/**` naming its `Owner:`), read from what a test reaches by `tests/conftest.py`, never from its folder; a small test that starts a process fails (`small-spawns-no-process`); live Codex-binary validation is opt-in outside CI.
- `tests/<p>/test_<m>.py` mirrors `dadaia_workspace/<p>/<m>.py`, a second file for a module is `test_<m>__<topic>.py` (`tests-mirror-the-package`).
- The suite is hermetic; `tests/conftest.py` blocks a real Codex call without its live flag and fakes `ensure_workspace_venv`.
- `tests/conftest.py` prepends this checkout to `PYTHONPATH` once for the whole session, so every spawned CLI/hook subprocess imports the worktree under test, never the venv's installed package.
- Every guard check enumerates one set — `scripts/guards/run.py`'s `tracked()` over `git ls-files` — so a scratch file another process writes is outside the measurement by construction.
- Output naming a foreign Spec Context is `--redact`ed before entering evidence.

- `flaky` marks a pass-and-fail on identical code; `quarantine` leaves every gating selector, is bug-gated by P-22, and the lane is empty.
- Growth past the per-job wall-clock budget frozen by ADR 0119 is a budget breach, judged by `dd-code-reviewer` reading the CI job durations (`gh run view`, per job; ADR 0166).
- Curation is a `code-reviewer` verdict (QA lens); `software-engineer` executes.
- Mutation evidence is operator tooling, outside the repo (ADR 0166).

## Gates

- CI runs ruff and `lint-imports`, mypy `--strict`, the guards (`scripts/guards/run.py`, plain and `--planted`), the small tier on Linux, the `not e2e` coverage run on Linux, Windows and macOS, the small tier again on Windows and macOS with an importability smoke, the medium tier, Python E2E, repo hygiene, `dadaia doctor` over the checked-out tree, PR governance and gitleaks — every PR job a required status check listed in `.github/required-checks.json` (`required-checks-listed`), gitleaks included; no job calls a model API (P-33) except `.github/workflows/eval.yml`, the one exception (ADR 0217).
- Push triggers are `main`, `develop`, `feature/**` and `wt/**`; PRs to `develop` or `main` run the same matrix.
- `pr-source-guard` is fail-closed; the security review of both PR edges is the `dd-code-reviewer` security lens on the PR head, run by the main thread before the PR.
- Every review verdict states the bug-surface delta from `bugs.py stats`, and no deploy is approved without the consumer-side matrix.
- Caches redirect by configuration, never by a remembered flag: `[tool.pytest.ini_options] addopts` (`-p no:cacheprovider`), hypothesis `database = None`, and ruff and mypy write to the absolute `.dadaia/tmp/<tool>-cache` that every harness env exports (`workspace_layout.TOOL_CACHE_ENV`); a bare `pytest`, `ruff check`, `ruff format --check`, `mypy --strict` from any cwd leaves the tree clean (`tests/infrastructure/test_runtime_config__tool_caches_stay_in_the_tmp_zone.py`).
- The forbidden repo-local set is `core/workspace_layout.REPO_TREE_EXCLUDED`, measured here by `ci.yml`'s `repo-hygiene` job and swept at every ALIVE repo by `dadaia doctor`.
- Memory-vs-code drift is a `dadaia doctor` `specs`-section WARNING (`MEM-DRIFT-1` for the features package map, `MEM-DRIFT-2` for a dead `dadaia <verb>` or path an atom cites), never a push-gated test: a package added or a verb deleted mid-implementation is memory drift to fix at the next closure, not a red build.
- A citation of a superseded decision is an ERROR (`ADR-SUPERSEDED-CITATION`): a rule pointing at a dead ADR fails the build.
- A doctor fix is proven on the executed path: `tests/cli/commands/test_doctor.py` executes every specs rule's fix line against a planted finding and re-runs the rule, which must then emit nothing, never the fixer's return value; the `ledgers` section delegates to each ledger's skill script (`tests/infrastructure/test_ledger_scripts__doctor_ledgers_delegate_to_scripts.py`); a schema drop ships with its repair and its test in the same change.
- The closed pytest marker set is seven — e2e, small, medium, slow, tmp, flaky, quarantine (P-28).
- Every `ci.yml` checkout fetches full history (`ci-checkout-history`); `release.yml`'s build and `secret-scan.yml` fetch full history; no job fetches history for a bug record's sake.

- Repo-pure ratchets move only downward and run as `scripts/guards/run.py` checks: `suite.py` holds `private-import-ratchet` (V26, P-23); `slop.py` holds V32 (governance ids in production comments and docstrings), V33 (`PREFIX-NN` families without a mechanical reader) and `ignore-cap` (suppressed layering edges, P-10) as pinned counts, V37 (one home per definition), V38 (deletes only in `features/spec_context/sweep.py`) and V39 (every doctor code has a fix-clears case) as keyed allowances whose keys stay within their birth keys, and V40 (every JSONL ledger read through the one reader) at zero; no check pins a file's line or byte count (`no-size-pin`, ADR 0143).
- The derived-docs contract `tests/contract/test_docs_derived_from_memory.py` (P-29) checks every `<!-- derived-from: <slug> sha256:<12 hex> -->` marker's slug and hash over `README.md`, `llms.txt` and `docs/*.md`, the `docs/cli.md` body against `render_digest()`, the one tagline across `README.md`, `pyproject.toml` and `llms.txt`, the five `[tool.poetry.urls]` keys, and runs `dead_citations` over the same set; a red row is closure work — after the memory merge, in an `impl` worktree (the `release` kind holds no `docs/`), re-read the atom, re-derive the section and re-record the hash (`dd-release-implementation` MEMORY-UPDATE).
- Stale handoffs and scratch are a closure readout, never a ratchet: `dd-release-implementation` RC-FLOW step 8 runs `dadaia doctor` dry, then `dadaia doctor --fix` (slop moved to `reaped/`, expired entries deleted), and the `kind: artifact-gc` log entry records the `compliance(total)` line and what the reaper holds.
- `dd-audit-project` pillar 2 re-measures the ratchets over the audit window and applies `dd-code-review` SLOP.md S1–S10 to a commit sample; the fixed law sections are kept byte-exact by `dadaia doctor` FIXED-1/2.

Related: [[ARCHITECTURE]]

<!-- dadaia:fixed slop-tests -->
### Slop — tests (fixed)
- A test follows the root `AGENTS.md` map §1 test basics; an own module is tested through its interface.
- A test name states current behavior; a tombstone (a test of an absence) dies with its target.
- Pruning is a `dd-code-reviewer` verdict executed by `dd-software-engineer`; a deletion cites its criterion and its replacement `file:line`.
- Detection: `dd-code-review` SLOP.md S3.
<!-- /dadaia:fixed slop-tests -->
