---
slug: QUALITY
title: quality-assurance
tldr: The measured quality principles, the test architecture (tiers, intent, flake and quarantine policy) and the CI gate set with its slop ratchets.
summary: Canonical memory — statements and laws of testing and quality; changed only in the commit that carries an accepted ADR.
tags: [testing, pytest, ci, quality, test-architecture, flake, quarantine, privacy]
---

## Principles

### P-18 · We hold decomposed modules under a line-count ceiling that only decreases, and a deleted god module stays deleted.
Measured by: `pytest tests/contract/test_module_size_ceiling.py` — the test module is the ceilings' one numeric home.
ADR: none
Rationale: split modules grow back one helper at a time unless a number refuses it.

### P-19 · We pin cyclomatic complexity and nesting at their measured maxima and move them only downward, with the justification in the reducing release's closure record.
Measured by: `ruff check dadaia_workspace/` (`C901`, `PLR1702`; ceilings pinned in `pyproject.toml`), run by `dadaia ci preflight` and the CI lint job.
ADR: none
Rationale: a ceiling measured first and pinned second is red only on growth.

### P-20 · We do not grow `specs upgrade` / `dadaia doctor`: their complexity is pinned and the migration module changes only with a same-commit justification.
Measured by: `pytest tests/contract/test_specs_cli_complexity_ratchet.py` (radon complexity of `cli/commands/specs.py#upgrade` and `cli/commands/doctor.py#doctor` plus a pinned hash of `features/migrate/upgrade.py`).
ADR: none
Rationale: these two surfaces absorbed every migration this product shipped.

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k "test_contract_tier_carries_30s_timeout or test_explicit_timeout_marker_is_never_overridden or test_tier_timeout_table_covers_all_four_layers"` (executed path: the marker on the test's own item; F041 — the bare `-k timeout` also matched the tier marker every contract item carries, collecting all 8 with 0 deselected).
ADR: none
Rationale: a test needing more time than its tier is mis-tiered.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k quarantine`.
ADR: none
Rationale: the registered id is what makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v26` (AST-exact; the test module is the ceiling's numeric home).
ADR: none
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-24 · We declare intent at birth: the count of test files whose module docstring carries `Intent: <KIND> — <ref>` ratchets upward only.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v31` (the test module is the ceiling's numeric home, per tier).
ADR: none
Rationale: an undeclared test is SCAFFOLD by default.

### P-25 · We expire SCAFFOLD: every `Intent: SCAFFOLD` names `expires: <M.m.p>`, and one naming an archived release is red until renewed by a `code-reviewer` verdict.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v28`.
ADR: none
Rationale: a temporary test that never expires is a permanent cost.

### P-26 · We keep one number per parameter: `dd-test-stewardship`'s `PARAMETERS.md` is the LARGE cap's only literal home; every other doctrine file references it.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v29` (competing-home ceiling, ratchet down only).
ADR: none
Rationale: two homes for one parameter guarantee two different values.

### P-27 · We measure the pyramid every run — SMALL/MEDIUM/LARGE shares from one `--collect-only`, judged against 75/20/5 (±5 pp) — reported, not gated; a drift is a closure finding.
Measured by: `pytest -s tests/contract/test_test_suite_ratchets.py -k v30` (prints the shares; the detector is proven on a mutation fixture).
ADR: none
Rationale: a reported number promoted as if it gated is fabricated detection.

### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` equals `tests/conftest.py`'s `_KNOWN_MARKERS`, and `flaky`/`quarantine` are always among them.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k marker_set`.
ADR: none
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.

### P-29 · We derive every human- and agent-facing document from a named memory atom under a content hash: each `## ` section of `README.md`, `llms.txt` and every `docs/*.md` names its atom and the atom's current sha256, and `docs/cli.md` is the committed output of `dadaia help tree`.
Measured by: `pytest tests/contract/test_docs_derived_from_memory.py`.
ADR: 0012 (accepted)
Rationale: a document written beside memory rots; one that names its source is red the moment the source moves.

## Test architecture

- Size tiers: unit and contract SMALL, integration MEDIUM, E2E LARGE (Python journeys), live Codex-binary validation opt-in outside CI.
- The suite is hermetic; `tests/conftest.py` blocks a real Codex call without its live flag and fakes `ensure_workspace_venv`.
- `tests/conftest.py` prepends this checkout to `PYTHONPATH` once for the whole session, so every spawned CLI/hook subprocess imports the worktree under test, never the venv's installed package.
- Every suite ratchet enumerates the same set — `tests/helpers/suite_files.tracked_test_files()` over `git ls-files -- tests` — so scratch files a concurrent xdist worker writes are outside the measurement by construction.
- Module docstrings declare `Intent: <KIND> — <ref>` over CONTRACT, SENTINEL, SCAFFOLD and QUARANTINE; an undeclared test is SCAFFOLD, and intent is never a marker.
- Output naming a foreign Spec Context is `--redact`ed before entering evidence ([[sdd-gate-v3]]).

- `flaky` marks a pass-and-fail on identical code; `quarantine` leaves every gating selector, is bug-gated by P-22, and the lane is empty.
- Quarantine cap, escalation clock, diagnostic reruns, flake-rate target and the LARGE cap have one home each in `dd-test-stewardship`'s `PARAMETERS.md`.
- The structural audit fires when a `PARAMETERS.md` ceiling is crossed — flake rate, LARGE count, quarantine cap; wall-clock growth is a closure readout with no pinned number.
- Every LARGE test carries a demotion, supersession or keep-justification, and the tree misses the LARGE cap.
- Curation is a `code-reviewer` verdict (QA lens); `software-engineer` executes.
- Mutation testing runs once per release off the push path (`mutmut==3.7.0`); its score is evidence, never a gate, and the `core/models/` score ratchets upward only.

## Gates

- CI runs the preflight ladder plus cross-OS subsets, integration, Python E2E, repo hygiene, `dadaia doctor` over the checked-out tree, PR governance, the `security-review` job (the official `anthropics/claude-code-security-review` Action) and gitleaks — every job a required status check on `develop`, gitleaks included.
- Push triggers are `main`, `develop` and `feature/**`; PRs to `develop` or `main` run the same matrix as the local preflight.
- `pr-source-guard` is fail-closed, and `security-review` reviews the PR diff on both edges ([[sdd-gate-v3]]).
- Every review verdict states the bug-surface delta from `bugs.py stats`, and no deploy is approved without the consumer-side matrix ([[consumer-agent-support]]).
- Ruff `C901` and `PLR1702` are scoped to `dadaia_workspace/` with ceilings pinned in `pyproject.toml` against the enforcing tool; `radon cc` reports and never gates.
- Caches redirect by configuration, never by a remembered flag: `[tool.pytest.ini_options] addopts` (`-p no:cacheprovider`), `[tool.ruff] cache-dir` and `[tool.mypy] cache_dir` (`../../.dadaia/tmp/<tool>-cache`, relative on every OS), hypothesis `database = None`; a bare `pytest`, `ruff check`, `ruff format --check`, `mypy --strict` from the repo root leaves the tree clean (`tests/unit/features/ci_preflight/test_no_pollution.py`), so `dadaia ci preflight` runs exactly the bare commands.
- The forbidden repo-local set is `core/workspace_layout.REPO_TREE_EXCLUDED`, measured by `tests/contract/test_source_repo_hygiene.py` and swept at every ALIVE repo by `dadaia doctor` ([[workspace-doctor]]).
- Memory-vs-code drift is a `dadaia doctor` `specs`-section WARNING (`MEM-DRIFT-1` for the features package map, `MEM-DRIFT-2` for a dead `dadaia <verb>` or path an atom cites), never a push-gated test: a package added or a verb deleted mid-implementation is memory drift to fix at the next closure, not a red build ([[workspace-doctor]]).
- A citation of a superseded decision is an ERROR (`ADR-SUPERSEDED-CITATION`): a rule pointing at a dead ADR fails the build ([[workspace-doctor]]).
- A doctor fix is proven on the executed path: `tests/contract/test_ledgers_validate.py` locates the issue and `tests/unit/features/specs/test_ledgers_fix_canonical_form.py` runs `--fix` over a committed-shaped record file and asserts the re-serialized line, never the fixer's return value; a schema drop ships with its repair and its test in the same change.
- The closed pytest marker set is eight — unit, contract, integration, e2e, slow, tmp, flaky, quarantine (P-28).
- `ci.yml` checks out at the default depth (the `security-review` job fetches depth 2 for the PR diff); `release-please.yml` and `secret-scan.yml` fetch full history; no job fetches history for a bug record's sake.

- Five repo-pure ratchets pin slop counts and move only downward: V31 (Intent-less test files per tier) in `tests/contract/test_test_suite_ratchets.py`; V32 (governance ids in production comments and docstrings), V33 (`PREFIX-NN` families without a mechanical reader), V34 (live SPEC/TASKS byte ceiling) and V35 (skill directories ≤ 18 and total `public/skills/**/*.md` lines, pinned at the measured value and re-pinned at every corpus-touching closure) in `tests/contract/test_slop_ratchets.py`; `PLAN.md` has no byte ratchet (`SPEC-DOC-005` is advisory).
- The derived-docs contract sits beside the ratchets: `tests/contract/test_docs_derived_from_memory.py` (P-29) checks every `<!-- derived-from: <slug> sha256:<12 hex> -->` marker's slug and hash over `README.md`, `llms.txt` and `docs/*.md`, the `docs/cli.md` body against `render_digest()`, the 10 KB README budget, the one tagline across `README.md`, `pyproject.toml` and `llms.txt`, the five `[tool.poetry.urls]` keys, and runs `dead_citations` over the same set; a red row is closure work — re-read the atom, re-derive the section, re-record the hash in the atom's own commit (`dd-release-implementation` MEMORY-UPDATE).
- Stale handoffs and scratch are a closure readout, never a ratchet: `dd-release-implementation` RC-FLOW step 8 runs `dadaia doctor` dry, then `dadaia doctor --fix` (slop moved to `reaped/`, expired entries deleted), and the `kind: artifact-gc` log entry records the `compliance(total)` line and what the reaper holds ([[workspace-doctor]]).
- `dd-audit-project` pillar 2 re-measures the ratchets over the audit window and applies `dd-code-review` SLOP.md S1–S10 to a commit sample; the fixed law sections are kept byte-exact by `dadaia doctor` FIXED-1/2.

Related: [[ARCHITECTURE]], [[consumer-agent-support]], [[sdd-gate-v3]], [[bug-ledger]], [[backlog-ledger]], [[release-lifecycle]], [[workspace-doctor]].

<!-- dadaia:fixed slop-tests -->
### Slop — tests (fixed)
- A test is born with `Intent:`, fails for a real regression and asserts a value that comes from outside the code under test.
- A mock exists only at the system boundary (network, clock, randomness); an own module is tested through its interface.
- A test name states current behavior; a tombstone (a test of an absence) and an expired SCAFFOLD die at closure.
- Pruning is a `dd-code-reviewer` verdict executed by `dd-software-engineer`; a deletion cites its criterion and its replacement `file:line`.
- Detection: `dd-code-review` SLOP.md S3; measured by ratchet V31 and `test_test_suite_ratchets.py`.
<!-- /dadaia:fixed slop-tests -->
