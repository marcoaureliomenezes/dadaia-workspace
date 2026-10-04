---
slug: QUALITY
title: quality-assurance
tldr: The measured quality principles, the test architecture (tiers, flake and quarantine policy) and the CI gate set with its slop ratchets.
summary: Canonical memory — statements and laws of testing and quality; changed only in the commit that carries an accepted ADR.
tags: [testing, pytest, ci, quality, test-architecture, flake, quarantine, privacy]
---

## Principles

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k "test_contract_tier_carries_30s_timeout or test_explicit_timeout_marker_is_never_overridden or test_tier_timeout_table_covers_all_four_layers"` (executed path: the marker on the test's own item; F041 — the bare `-k timeout` also matched the tier marker every contract item carries, collecting all 8 with 0 deselected).
ADR: 0167 (accepted)
Rationale: a test needing more time than its tier is mis-tiered.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k quarantine`.
ADR: 0167 (accepted)
Rationale: the registered id is what makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v26` (AST-exact; the test module is the ceiling's numeric home).
ADR: 0167 (accepted)
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` equals `tests/conftest.py`'s `_KNOWN_MARKERS`, and `flaky`/`quarantine` are always among them.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k marker_set`.
ADR: 0167 (accepted)
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.

### P-29 · We derive every human- and agent-facing document from a named memory atom under a content hash: each `## ` section of `README.md`, `llms.txt` and every `docs/*.md` names its atom and the atom's current sha256, and `docs/cli.md` is the committed output of `dadaia help tree`.
Measured by: `pytest tests/contract/test_docs_derived_from_memory.py`.
ADR: 0012 (accepted)
Rationale: a document written beside memory rots; one that names its source is red the moment the source moves.

### P-33 · No CI job of a context's main repo or associated repos calls a model API, except an evals repo's, only in `workflow_dispatch` or `schedule` jobs (ADR 0177); no library workflow uses an `anthropics/*` action or references a model API secret; the security review is the local `dd-code-reviewer` lens.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS no-model-api-in-ci`.
ADR: 0177 (accepted)
Rationale: a CI job that needs a paid model key fails closed on every PR without it and forces admin merges.

## Test architecture

- Size tiers: unit and contract SMALL, integration MEDIUM, E2E LARGE (Python journeys), live Codex-binary validation opt-in outside CI.
- The suite is hermetic; `tests/conftest.py` blocks a real Codex call without its live flag and fakes `ensure_workspace_venv`.
- `tests/conftest.py` prepends this checkout to `PYTHONPATH` once for the whole session, so every spawned CLI/hook subprocess imports the worktree under test, never the venv's installed package.
- Every guard check enumerates one set — `scripts/guards/run.py`'s `tracked()` over `git ls-files` — so a scratch file another process writes is outside the measurement by construction.
- Output naming a foreign Spec Context is `--redact`ed before entering evidence.

- `flaky` marks a pass-and-fail on identical code; `quarantine` leaves every gating selector, is bug-gated by P-22, and the lane is empty.
- Curation is a `code-reviewer` verdict (QA lens); `software-engineer` executes.

## Gates

- CI runs ruff and `lint-imports`, mypy `--strict`, the guards (`scripts/guards/run.py`, plain and `--planted`), unit and contract tiers with Windows/macOS subsets and an importability smoke, integration, Python E2E, repo hygiene, `dadaia doctor` over the checked-out tree, PR governance and gitleaks — every PR job a required status check listed in `.github/required-checks.json` (`required-checks-listed`), gitleaks included; no job calls a model API (P-33).
- Push triggers are `main`, `develop` and `feature/**`; PRs to `develop` or `main` run the same matrix.
- `pr-source-guard` is fail-closed; the security review of both PR edges is the `dd-code-reviewer` security lens on the PR head, run by the main thread before the PR.
- Every review verdict states the bug-surface delta from `bugs.py stats`, and no deploy is approved without the consumer-side matrix.
- Caches redirect by configuration, never by a remembered flag: `[tool.pytest.ini_options] addopts` (`-p no:cacheprovider`), hypothesis `database = None`, and ruff and mypy write to the absolute `.dadaia/tmp/<tool>-cache` that every harness env exports (`workspace_layout.TOOL_CACHE_ENV`); a bare `pytest`, `ruff check`, `ruff format --check`, `mypy --strict` from any cwd leaves the tree clean (`tests/integration/test_tool_caches_stay_in_the_tmp_zone.py`).
- The forbidden repo-local set is `core/workspace_layout.REPO_TREE_EXCLUDED`, measured here by `ci.yml`'s `repo-hygiene` job and swept at every ALIVE repo by `dadaia doctor`.
- Memory-vs-code drift is a `dadaia doctor` `specs`-section WARNING (`MEM-DRIFT-1` for the features package map, `MEM-DRIFT-2` for a dead `dadaia <verb>` or path an atom cites), never a push-gated test: a package added or a verb deleted mid-implementation is memory drift to fix at the next closure, not a red build.
- A citation of a superseded decision is an ERROR (`ADR-SUPERSEDED-CITATION`): a rule pointing at a dead ADR fails the build.
- A doctor fix is proven on the executed path: `tests/integration/test_doctor_fix_lines_clear_their_finding.py` executes every specs rule's fix line against a planted finding and re-runs the rule, which must then emit nothing, never the fixer's return value; the `ledgers` section delegates to each ledger's skill script (`tests/integration/test_doctor_ledgers_delegate_to_scripts.py`); a schema drop ships with its repair and its test in the same change.
- The closed pytest marker set is eight — unit, contract, integration, e2e, slow, tmp, flaky, quarantine (P-28).
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
