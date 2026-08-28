---
slug: quality-assurance
title: quality-assurance
category: core
tldr: 10 measured quality principles, then test layers, intent taxonomy, flake and quarantine policy, test health, CI gates and anti-slop rules.
summary: Part 1 carries the ADR-gated quality principles and the check that measures each; Part 2 records the test layers, intent taxonomy, flake handling, test health, the CI gate set and the anti-slop rules.
tags:
- testing
- pytest
- ci
- quality
- test-architecture
- flake
- quarantine
- privacy
---

## Part 1 — Principles

### P-18 · We hold decomposed modules under a line-count ceiling that only decreases, and a deleted god module stays deleted.
Measured by: `pytest -p no:cacheprovider tests/contract/test_module_size_ceiling.py` — the test module is the ceilings' one numeric home.
ADR: none
Rationale: split modules grow back one helper at a time unless a number refuses it.

### P-19 · We pin cyclomatic complexity and nesting at their measured maxima and move them only downward, with the justification in the reducing release's closure record.
Measured by: `ruff check --no-cache dadaia_workspace/` (`C901`, `PLR1702`; the ceilings' one numeric home is `pyproject.toml`), run by `dadaia ci preflight` and the CI lint job.
ADR: none
Rationale: a ceiling measured first and pinned second is red only on growth.

### P-20 · We do not grow `specs upgrade` / `specs doctor`: their complexity is pinned and the migration module changes only with a same-commit justification.
Measured by: `pytest -p no:cacheprovider tests/contract/test_specs_cli_complexity_ratchet.py` (radon per-function complexity plus a pinned content hash of `features/migrate/upgrade.py`).
ADR: none
Rationale: these two surfaces absorbed every migration this product shipped.

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "timeout"` (executed path: the marker on the test's own item; `tests/conftest.py`).
ADR: none
Rationale: a test needing more time than its tier is mis-tiered.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "quarantine"`.
ADR: none
Rationale: the registered id is what makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v26` (AST-exact; the test module is the ceiling's one numeric home).
ADR: none
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-24 · We declare intent at birth: the count of test files whose module docstring carries `Intent: <KIND> — <ref>` ratchets upward only.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v27` (the test module is the floor's one numeric home).
ADR: none
Rationale: an undeclared test is SCAFFOLD by default.

### P-25 · We expire SCAFFOLD: every `Intent: SCAFFOLD` names `expires: <M.m.p>`, and one naming an archived release is red until renewed by a `qa-engineer` verdict.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v28`.
ADR: none
Rationale: a temporary test that never expires is a permanent cost.

### P-26 · We keep one number per parameter: `dadaia-test-stewardship`'s `PARAMETERS.md` is the LARGE cap's only literal home; every other doctrine file references it.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v29` (competing-home ceiling, ratchet down only, with a mutation fixture proving the detector fires).
ADR: none
Rationale: two homes for one parameter guarantee two different values.

### P-27 · We measure the pyramid every run — SMALL/MEDIUM/LARGE shares from one `--collect-only`, judged against 75/20/5 (±5 pp) — **reported, not gated**; a drift is a closure finding.
Measured by: `pytest -p no:cacheprovider -s tests/contract/test_test_suite_ratchets.py -k v30` (prints the shares; the detector is proven on a mutation fixture).
ADR: none
Rationale: promoting a reported number as if it gated would be fabricated detection.

## Part 2 — Implementation

### Layers and intent

The suite is hermetic by default and invokes no paid or live binary without an explicit opt-in.

| Layer | Scope | Size tier |
|---|---|---|
| Unit | Pure behavior, validators, rendering, adapters with fakes | SMALL |
| Contract | Public API/schema, architecture, security, projection, invariants | SMALL |
| Integration | CLI plus real temporary filesystem/state and composed services | MEDIUM |
| E2E | Complete Python journeys and browser-backed panel behavior | LARGE |
| Live opt-in | Explicit Codex binary validation outside default CI | — |

`Intent: <KIND> — <ref>` in the module docstring, over four kinds: CONTRACT (permanent, pins an
acceptance criterion or a bug), SENTINEL (permanent, the one integration test of a seam), SCAFFOLD
(temporary) and QUARANTINE (bug-gated flake). `REGRESSION` and `BUG` are not tokens; an undeclared
test is SCAFFOLD; intent is never a pytest marker. Protocol: `dadaia-test-stewardship`.
`tests/conftest.py` blocks real Codex invocation unless the matching live flag is set and fakes
`ensure_workspace_venv`, so no test builds a real venv. An inventory a test asserts is scanned from
`dadaia_workspace/public/**`, never hand-kept, and every source-scan test asserts its population is
non-empty and holds a known sentinel. Output naming a foreign Spec Context is `--redact`ed before it
enters evidence, backstopped by the push denylist scan ([[sdd-gate-v3]]).

### Flake, quarantine and health

`flaky` marks a test observed to pass and fail on identical code; `quarantine` removes it from every
gating selector and is bug-gated by P-22. The quarantine lane is empty; its cap, escalation clock,
diagnostic reruns and flake-rate target have one home each in `dadaia-test-stewardship`'s
`PARAMETERS.md`. A green run with quarantined tests is green; an unregistered pass-on-retry is a
failure, which a fail-closed CI step enforces on the `retries: 1` panel E2E job.

Flake rate, wall-clock trend and failure-to-defect ratio stay continuously visible, and the
structural audit fires on a trigger, never a calendar: wall-clock growth over 25 % without
equivalent new behavior, flake rate above the ceiling, LARGE count above its cap, or quarantine at
cap. Every file under `tests/e2e/**` names an owner; every LARGE test carries a demotion with a
named replacement, a recorded supersession, or a written keep-justification. The LARGE cap lives in
`PARAMETERS.md` (P-26) and the tree does not meet it today. Curation is verdict-driven:
`qa-engineer` rules, `software-engineer` executes. Mutation testing runs once per release off the
push path (`mutmut==3.7.0`, [[tech-stack]]); its score is evidence, never a gate, and the `core/`
score is a floor that ratchets upward only.

### CI

CI runs importability, Ruff format/lint, import-linter, mypy strict, unit, contract with 80 %
coverage, Windows/macOS cross-platform subsets, integration, Python E2E, panel E2E, repository
hygiene, backlog doctor, branch/PR governance, the security-verdict PR gate, the older dual
qa-plus-security closure gate, and a gitleaks secret-scan job; release publication repeats the
relevant ladder before build, approval, publish and smoke test. Push triggers are `main`, `develop`
and `feature/**`; PRs targeting `develop` or `main` run the same matrix. The 80 % floor on
`unit or contract` is a gate and a by-product metric, never an acceptance target, and the local
preflight and CI gate the same check set.

Two PR-edge jobs are fail-closed: `pr-source-guard` accepts `main` only from `develop` and `develop`
only from `feature/{M.m.p}`, comparing the attacker-influenceable head ref as a quoted `env:`
literal; the **security-verdict gate** requires an APPROVED `security-reviewer` handoff covering the
PR head sha from committed evidence under `specs/releases/<id>/verdicts/` ([[sdd-gate-v3]]), whose
promotion to a required check is an operator repository setting. Every review verdict carries the
bug-surface delta of each feature it touched, evidenced from `dadaia bugs stats`, and no internal
gate approves a deploy by itself: every candidate wheel passes the consumer-side matrix in
`public/data/CONSUMER_VALIDATION_RECIPE.md` with an APPROVED verdict ([[consumer-agent-support]]).

### Complexity, size and anti-slop

Ruff `C90` (`C901`) and `PLR1702` are scoped to `dadaia_workspace/`, ceilings pinned in
`pyproject.toml` at observed maxima with the ratchet direction beside them (P-19). A ceiling is
pinned against the enforcing tool, never a proxy — `radon cc` reports but does not gate — and one
that cannot be lowered safely stays where it is, documented inline and registered as a bug. The
release's `closure-size-accounting` record carries measured LOC added/deleted/net, the three largest
additions and deletions by file, both ceilings before and after, and the nesting-violation count.

pytest uses `-p no:cacheprovider`, mypy incremental state is off, and Ruff, coverage and Playwright
outputs are redirected outside the repository; the venv guard refuses an invocation that would write
one in-tree. Forbidden repo-local artifacts are `__pycache__`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache`, `.hypothesis`, `.coverage`, `coverage/`, `test-results/`, `playwright-report/`,
`.venv/` and `.dadaia/`, measured by `tests/contract/test_source_repo_hygiene.py`.

### Dependencies

[[tech-stack]], [[architecture]], [[panel]], [[consumer-agent-support]], [[sdd-gate-v3]].
