---
slug: quality-assurance
title: quality-assurance
category: core
tldr: 10 measured quality principles, then test layers, intent taxonomy, flake and quarantine policy, test health, CI gates and anti-slop rules.
summary: Part 1 carries the ADR-gated quality principles and the check that measures each; Part 2 describes the test layers, intent taxonomy, redaction, flake handling, test health, the CI gate set and the anti-slop rules.
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
Rationale: the registered id is the only thing that makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v26` (AST-exact; the test module is the ceiling's one numeric home).
ADR: none
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-24 · We declare intent at birth: the count of test files whose module docstring carries `Intent: <KIND> — <ref>` ratchets upward only.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v27` (the test module is the floor's one numeric home).
ADR: none
Rationale: an undeclared test is SCAFFOLD by default and cannot be pruned per file.

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

### Layers

The suite is hermetic by default and never invokes a paid or live binary without an explicit
opt-in.

| Layer | Scope | Size tier |
|---|---|---|
| Unit | Pure behavior, validators, rendering, adapters with fakes | SMALL |
| Contract | Public API/schema, architecture, security, projection, invariant checks | SMALL |
| Integration | CLI plus real temporary filesystem/state and composed services | MEDIUM |
| E2E | Complete Python journeys and browser-backed panel behavior | LARGE |
| Live opt-in | Explicit Codex binary validation outside default CI | — |

### Intent taxonomy

Every test declares `Intent: <KIND> — <AC id | bug-id | task-id>` in its module docstring,
over four kinds: CONTRACT (permanent, asserts an acceptance criterion or a bug), SENTINEL
(permanent, the single integration test of one seam), SCAFFOLD (temporary, expires at its
task/release closure) and QUARANTINE (flaky, carries a registered bug id). `REGRESSION` and
`BUG` are not tokens — a test pinning a fixed defect is CONTRACT against that bug id. An
undeclared test is SCAFFOLD. Intent is never a pytest marker, because the marker namespace
binds `contract` to the layer directory.

Enforcement has two arms. `tests/scripts/check_test_intent_declared.py` refuses an **e2e**
file with no `Intent:` header, excluding `__init__.py`, `rendezvous.py` and `conftest.py`,
wired into the gating suite through
`tests/integration/scripts/test_check_test_intent_declared.py`. Suite-wide, P-24's floor
measures the same declaration across every `tests/**/test_*.py`; the undeclared remainder is
disclosed debt. The taxonomy prose lives in `tests/AGENTS.md` and the operational protocol in
`dadaia-test-stewardship`.

### Safety backstops and derived inventories

`tests/conftest.py` carries two autouse backstops: it blocks real Codex invocation unless the
matching live flag is set (`DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`, `DADAIA_CODEX_LIVE`,
`DADAIA_CLAUDE_LIVE`), and it fakes `ensure_workspace_venv` so no test builds a real venv.
Temporary workspaces use `tmp_path` or `.dadaia/tmp/`.

An inventory a test asserts is derived, never hand-kept: the two install/doctor byte goldens
pin policy only — target mapping, banners, mode and newline conventions — while the per-file
asset inventory is a roster scanned from `dadaia_workspace/public/**` at test time through
the asset manager's own walk, with one derived oracle for the skill inventory. Every
source-scan test asserts its enumerated population is non-empty and contains one known
sentinel member, at each call site.

### Redaction at authoring

Diagnostic output naming a Spec Context other than the caller's own is captured with
`--redact` or masked by hand before it enters QA evidence, a SPEC, a closure record, a report
or a handoff. `dadaia doctor`, `dadaia context list` and `dadaia context show` accept
`--redact`, replacing every foreign context name and repo slug with a stable
`[REDACTED-CONTEXT-<n>]` placeholder at the render boundary only. The push-boundary denylist
scan ([[sdd-gate-v3]]) is the mechanical backstop, wired and measured by
`tests/contract/test_push_gate_wiring.py`; the authoring rule covers what an agent
transcribes by hand, since a document authored into an archive is an ordinary new blob.

### Satisfiable diagnostics

For every violation a check reports, some legal operation clears it, and that operation is
the one the message names. In an append-only store the healing action is a later record for
the same subject, never a rewrite of published history. At the push boundary the scope is the
objects the push would publish, so editing the file and rewriting those commits is always
available.

### Browser validation

Panel changes are checked through unit DOM/static-asset contracts and Chromium journeys at
desktop widths (1024/1440) only; no mobile viewport is exercised. Canvas games are asserted
as DOM contracts in unit tests; the nonblank-pixel-after-input journey is a normative
requirement for new canvas work, not yet enforced by an existing Playwright test. Screenshots
and Playwright outputs go outside the repository.

### Flake and quarantine

Two markers carry flake state: `flaky` (observed pass and fail on identical code, under
diagnosis) and `quarantine` (out of every gating selector, bug-gated by P-22 — without the id
`tests/conftest.py` refuses collection with a `pytest.UsageError` whose message reaches
stderr before the raise). The quarantine lane is empty. Its cap, the escalation clock, the
bounded diagnostic reruns and the flake-rate target each have one home in
`dadaia-test-stewardship`'s `PARAMETERS.md`.

A green run with quarantined tests is green; an **unregistered pass-on-retry is a failure**.
The panel E2E job keeps `retries: 1`, writes its Playwright JSON report outside the
repository, and a fail-closed CI step fails the job on any `passed`-after-retry result unless
that test is registered as quarantined, naming the offending spec — a missing, empty,
malformed or non-numeric report exits 1. Wiring pinned by
`tests/contract/test_ci_workflow_hygiene.py`.

### Test health

Three metrics stay continuously visible: flake rate, wall-clock trend, and the
failure-to-defect ratio per test. The full structural audit fires on a trigger, never a
calendar — wall-clock growth over 25 % without equivalent new behavior, flake rate above the
ceiling, LARGE count above its declared cap, or quarantine at cap.

Per-tier timeouts (P-21) are applied at collection from `tests/conftest.py`, one default per
layer directory. A test carrying a justified explicit ceiling above its tier cites its own
measured wall clock and names the structural split that would retire it, tracked in the
release record that curated it — never in a backlog slug.

Every file under `tests/e2e/**` names an owner, and every LARGE test carries a demotion with a
named replacement, a recorded "behaviour removed" supersession, or a written
keep-justification. The LARGE cap lives in `PARAMETERS.md` (P-26) and the tree does not meet
it today. Curation is verdict-driven: `qa-engineer` rules, `software-engineer` executes.

Wall-clock baselines are frozen and ratcheted, and each CI pytest job carries a
`timeout-minutes` ceiling set against them. Mutation testing runs once per release, off the
push path: `mutmut==3.7.0` pinned in the optional Poetry group `[tool.poetry.group.mutation]`
([[tech-stack]]), driven by `tests/scripts/run_mutation_baseline.sh`, which stages a scoped
copy and never writes inside the repo tree. It is absent from every push-path selector,
pinned by a contract test; its score is evidence, never a gate, and the score on `core/` is a
floor that ratchets upward only. The script declares a scope invariant (`core/models/` and
its unit tests import nothing beyond the standard library and pytest) and fails collection
outright when it stops holding. Every third-party tool this project prescribes is installed at
an exact version or hash pin.

### CI

CI runs importability, Ruff format/lint, import-linter, mypy strict, unit, contract with 80 %
coverage, Windows/macOS cross-platform subsets, integration, Python E2E, panel E2E,
repository hygiene, backlog doctor, branch/PR governance, the security-verdict PR gate, the
older dual qa-plus-security closure gate, and a gitleaks secret-scan job. Release publication
repeats the relevant ladder before build, approval, publish and package smoke test.

Every gating pytest selector excludes the quarantine lane — in `ci.yml`, `release.yml` and the
local preflight — so a quarantined test runs only under an explicit `-m quarantine`. The 80 %
floor on `unit or contract` is a gate and a by-product metric, never an acceptance target.

Push triggers are `main`, `develop` and `feature/**`; pull requests targeting `develop` or
`main` trigger the same matrix. `pr-source-guard` is one job carrying two rules — `main`
accepts a PR only from `develop`, `develop` only from `feature/{M.m.p}` — with the pattern
translated into POSIX ERE from the package's single pattern source. The head ref reaches the
job through `env:` and is compared as a quoted literal, because it is attacker-influenceable
on a fork PR. Both edges are pinned by `tests/contract/test_ci_v2_gitflow_pr_gate.py`.

The **security-verdict gate** is a fail-closed CI job on both PR edges requiring an APPROVED
`security-reviewer` handoff covering the PR head sha, read from committed evidence under
`specs/releases/<id>/verdicts/` ([[sdd-gate-v3]]), pinned by
`tests/contract/test_pr_verdict_check_gate.py`. Making it a **required** check is a repository
setting the operator applies.

The local preflight and CI gate the same check set — format, lint, `mypy --strict`, the
import-boundary contracts and the test suite — pinned by
`tests/contract/test_ci_preflight_ci_gating_parity.py`.

Every review verdict carries the **bug-surface delta** of each feature it touched as a
required field: reduced or increased, with evidence from `dadaia bugs stats`, not from the
test result. Internal gates never approve a deploy by themselves: every candidate wheel passes
the consumer-side validation matrix in `public/data/CONSUMER_VALIDATION_RECIPE.md` with an
APPROVED verdict ([[consumer-agent-support]]), pinned by
`tests/contract/test_consumer_validation_recipe.py`.

### Complexity and size

Ruff selects `C90` (`C901`) and `PLR1702` scoped to `dadaia_workspace/`, with their ceilings
pinned in `pyproject.toml` at this codebase's observed maxima and the ratchet direction
written beside them (P-19). The ceiling is pinned against the enforcing tool, never a proxy:
`radon cc` reports but does not gate, and for a factory returning a nested class it scores
only the factory's top-level branches while `C901` counts the enclosing lexical scope. A
ceiling that cannot be lowered safely stays where it is with the discrepancy documented
inline and registered as a bug.

Every release accounts for what it added: the `closure-size-accounting` note in
`RELEASE.jsonl` carries production LOC added/deleted/net, the three largest additions and
deletions by file, the `C90` and `PLR1702` ceilings before and after with a justification for
any decrease, and the nesting-violation count. Every figure is measured, never estimated.

### Anti-slop

pytest uses `-p no:cacheprovider`; mypy incremental state is disabled; Ruff, coverage and
Playwright outputs are redirected, and the venv guard refuses an invocation that would write
one in-tree. Forbidden repo-local artifacts are `__pycache__`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache`, `.hypothesis`, `.coverage`, `coverage/`, `test-results/`, `playwright-report/`,
`.venv/` and `.dadaia/`, measured by `tests/contract/test_source_repo_hygiene.py`.

### Dependencies

[[tech-stack]], [[architecture]], [[panel]], [[consumer-agent-support]], [[sdd-gate-v3]].
