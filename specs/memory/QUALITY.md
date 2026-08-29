---
slug: quality-assurance
title: quality-assurance
category: core
tldr: 10 measured quality principles, then test layers, intent taxonomy, flake and quarantine policy, CI gates and anti-slop rules.
summary: Part 1 carries the ADR-gated quality principles and the check measuring each; Part 2 records test layers, intent taxonomy, flake handling, the CI gate set and the anti-slop rules.
tags: [testing, pytest, ci, quality, test-architecture, flake, quarantine, privacy]
---

## Part 1 — Principles

### P-18 · We hold decomposed modules under a line-count ceiling that only decreases, and a deleted god module stays deleted.
Measured by: `pytest tests/contract/test_module_size_ceiling.py` — the test module is the ceilings' one numeric home.
ADR: none
Rationale: split modules grow back one helper at a time unless a number refuses it.

### P-19 · We pin cyclomatic complexity and nesting at their measured maxima and move them only downward, with the justification in the reducing release's closure record.
Measured by: `ruff check --no-cache dadaia_workspace/` (`C901`, `PLR1702`; ceilings pinned in `pyproject.toml`), run by `dadaia ci preflight` and the CI lint job.
ADR: none
Rationale: a ceiling measured first and pinned second is red only on growth.

### P-20 · We do not grow `specs upgrade` / `specs doctor`: their complexity is pinned and the migration module changes only with a same-commit justification.
Measured by: `pytest tests/contract/test_specs_cli_complexity_ratchet.py` (radon complexity plus a pinned hash of `features/migrate/upgrade.py`).
ADR: none
Rationale: these two surfaces absorbed every migration this product shipped.

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `pytest tests/contract/test_stewardship_mechanics.py -k timeout` (executed path: the marker on the test's own item).
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
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v27` (the test module is the floor's numeric home).
ADR: none
Rationale: an undeclared test is SCAFFOLD by default.

### P-25 · We expire SCAFFOLD: every `Intent: SCAFFOLD` names `expires: <M.m.p>`, and one naming an archived release is red until renewed by a `qa-engineer` verdict.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v28`.
ADR: none
Rationale: a temporary test that never expires is a permanent cost.

### P-26 · We keep one number per parameter: `dadaia-test-stewardship`'s `PARAMETERS.md` is the LARGE cap's only literal home; every other doctrine file references it.
Measured by: `pytest tests/contract/test_test_suite_ratchets.py -k v29` (competing-home ceiling, ratchet down only).
ADR: none
Rationale: two homes for one parameter guarantee two different values.

### P-27 · We measure the pyramid every run — SMALL/MEDIUM/LARGE shares from one `--collect-only`, judged against 75/20/5 (±5 pp) — reported, not gated; a drift is a closure finding.
Measured by: `pytest -s tests/contract/test_test_suite_ratchets.py -k v30` (prints the shares; the detector is proven on a mutation fixture).
ADR: none
Rationale: a reported number promoted as if it gated is fabricated detection.

## Part 2 — Implementation

### Layers and intent

- Size tiers: unit and contract SMALL, integration MEDIUM, E2E LARGE (Python journeys plus Playwright panel), live Codex-binary validation opt-in outside CI.
- The suite is hermetic; `tests/conftest.py` blocks a real Codex call without its live flag and fakes `ensure_workspace_venv`.
- `tests/conftest.py` prepends this checkout to `PYTHONPATH` once for the whole session, so every spawned CLI/hook subprocess imports the worktree under test, never the venv's installed package.
- Every suite ratchet enumerates the same set — `tests/helpers/suite_files.tracked_test_files()` over `git ls-files -- tests` — so scratch files a concurrent xdist worker writes are outside the measurement by construction.
- Module docstrings declare `Intent: <KIND> — <ref>` over CONTRACT, SENTINEL, SCAFFOLD and QUARANTINE; an undeclared test is SCAFFOLD, and intent is never a marker.
- Output naming a foreign Spec Context is `--redact`ed before entering evidence ([[sdd-gate-v3]]).

### Flake, quarantine and health

- `flaky` marks a pass-and-fail on identical code; `quarantine` leaves every gating selector, is bug-gated by P-22, and the lane is empty.
- Quarantine cap, escalation clock, diagnostic reruns, flake-rate target and the LARGE cap have one home each in `dadaia-test-stewardship`'s `PARAMETERS.md`.
- A fail-closed step on the retrying panel E2E job turns an unregistered pass-on-retry red.
- The structural audit fires on a trigger: wall-clock growth over 25 %, flake rate above ceiling, LARGE count above cap, or quarantine at cap.
- Every `tests/e2e/**` file names an owner; every LARGE test carries a demotion, supersession or keep-justification, and the tree misses the LARGE cap.
- Curation is a `qa-engineer` verdict; `software-engineer` executes.
- Mutation testing runs once per release off the push path (`mutmut==3.7.0`); its score is evidence, never a gate, and `core/` ratchets upward only.

### CI and anti-slop

- CI runs the preflight ladder plus cross-OS subsets, integration, Python and panel E2E, repo hygiene, backlog doctor, PR governance, the security-verdict gate and gitleaks.
- Push triggers are `main`, `develop` and `feature/**`; PRs to `develop` or `main` run the same matrix as the local preflight.
- `pr-source-guard` is fail-closed, and the security-verdict gate needs an APPROVED handoff covering the PR head sha from `specs/releases/<id>/verdicts/` ([[sdd-gate-v3]]).
- Every review verdict states the bug-surface delta from `dadaia bugs stats`, and no deploy is approved without the consumer-side matrix ([[consumer-agent-support]]).
- Ruff `C901` and `PLR1702` are scoped to `dadaia_workspace/` with ceilings pinned in `pyproject.toml` against the enforcing tool; `radon cc` reports and never gates.
- Caches and artifacts are redirected outside the repository, and the forbidden repo-local set is measured by `tests/contract/test_source_repo_hygiene.py`.
- Memory-vs-code drift is a `specs doctor` WARNING, never a push-gated test: a package added mid-implementation is drift to fix at the next closure, not a red build ([[specs-doctor]]).

### Dependencies

[[tech-stack]], [[architecture]], [[panel]], [[consumer-agent-support]], [[sdd-gate-v3]].
