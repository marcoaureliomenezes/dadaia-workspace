---
slug: quality-assurance
title: quality-assurance
category: core
tldr: Two-tier memory: 10 measured quality principles, then test layers, intent taxonomy, flake and quarantine policy, test health, CI gates and anti-slop rules.
summary: >-
  Part 1 carries the ADR-gated quality principles, each naming the existing mechanical
  check that measures it — module-size and complexity ratchets, the tier timeouts,
  bug-gated quarantine, the private-symbol and intent ratchets, SCAFFOLD expiry, one
  number per parameter, and the reported (not gated) pyramid measurement. Part 2
  describes the practice those principles govern: test layers and size tiers, the
  four-token intent taxonomy and its e2e gate, safety backstops, derived inventories,
  the root-cause and satisfiable-diagnostics doctrines, redaction at authoring, browser
  validation, flake handling, test-health metrics and baselines, the CI gate set with
  its two-edge pr-source-guard and security-verdict gate, and the anti-slop rules.
tags:
- testing
- pytest
- ci
- quality
- test-architecture
- flake
- quarantine
- privacy
last_updated: '2026-08-27'
release_origin: 0.5.0
---

## Part 1 — Principles

A principle is admitted only with an **existing mechanical check** that fails when it is
violated; its `Measured by:` line names that check verbatim. A rule nobody can measure is
Part-2 description, never a principle. Every `ADR:` below is `proposed` until the operator
accepts it — an agent never writes `accepted`.

### P-18 · We hold decomposed modules under a line-count ceiling that only decreases, and a deleted god module stays deleted.
Measured by: `pytest -p no:cacheprovider tests/contract/test_module_size_ceiling.py` — the test module is the ceilings' one numeric home.
ADR: 0018 (proposed)
Rationale: the modules that were split grow back one helper at a time unless a number
refuses the regrowth.

### P-19 · We pin cyclomatic complexity and nesting at their measured maxima and move them only downward, with the justification in the reducing release's closure record.
Measured by: `ruff check --no-cache dadaia_workspace/` (`C901`, `PLR1702`; the ceilings' one numeric home is `pyproject.toml`), run by `dadaia ci preflight` and the CI lint job.
ADR: 0019 (proposed)
Rationale: a ceiling measured first and pinned second is green on day one and red only on
growth; a ceiling that fires on arrival is a target masquerading as a gate.

### P-20 · We do not grow `specs upgrade` / `specs doctor`: their complexity is pinned and the migration module changes only with a same-commit justification.
Measured by: `pytest -p no:cacheprovider tests/contract/test_specs_cli_complexity_ratchet.py` (radon per-function complexity plus a pinned content hash of `features/migrate/upgrade.py`).
ADR: 0020 (proposed)
Rationale: these two surfaces absorbed every migration this product ever shipped; without a
pin they absorb the next one too.

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "timeout"` (executed path: the marker on the test's own item; `tests/conftest.py`).
ADR: 0021 (proposed)
Rationale: a test that needs more time than its tier is mis-tiered — the tier is what gets
fixed, and a per-tier default is what makes the mis-tiering visible.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "quarantine"`.
ADR: 0022 (proposed)
Rationale: quarantine without a bug is deletion with extra steps; the registered id is the
only thing that makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v26` (AST-exact; the test module is the ceiling's one numeric home).
ADR: 0023 (proposed)
Rationale: a test reaching into a private symbol pins an implementation detail and turns a
safe refactor red, which is how a suite starts resisting change.

### P-24 · We declare intent at birth: the count of test files whose module docstring carries `Intent: <KIND> — <ref>` ratchets upward only.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v27` (the test module is the floor's one numeric home).
ADR: 0024 (proposed)
Rationale: an undeclared test is SCAFFOLD by default, and a suite of undeclared tests cannot
be pruned without an argument about every single file.

### P-25 · We expire SCAFFOLD: every `Intent: SCAFFOLD` names `expires: <M.m.p>`, and one naming an archived release is red until renewed by a `qa-engineer` verdict.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v28`.
ADR: 0025 (proposed)
Rationale: temporary tests that never expire are the permanent cost of a temporary decision.

### P-26 · We keep one number per parameter: `dadaia-test-stewardship`'s `PARAMETERS.md` is the LARGE cap's only literal home; every other doctrine file references it and carries no number of its own.
Measured by: `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v29` (competing-home ceiling, ratchet down only, with a mutation fixture proving the detector fires).
ADR: 0026 (proposed)
Rationale: two homes for one parameter guarantee two different values, and the reader
believes whichever they opened first.

### P-27 · We measure the pyramid every run — SMALL/MEDIUM/LARGE shares from one `--collect-only`, judged against 75/20/5 (±5 pp) — **reported, not gated**; a drift is a closure finding.
Measured by: `pytest -p no:cacheprovider -s tests/contract/test_test_suite_ratchets.py -k v30` (prints the shares; the detector is proven on a mutation fixture).
ADR: 0027 (proposed)
Rationale: the statement says exactly what the measure does — promoting a reported number as
if it gated would be the fabricated detection this product refuses.

## Part 2 — Implementation

### Purpose

Tests prove public behavior and failure handling at the cheapest reliable layer. The suite is
hermetic by default and never invokes a paid or live binary without an explicit opt-in.

### Layers

| Layer | Scope | Size tier |
|---|---|---|
| Unit | Pure behavior, validators, rendering, adapters with fakes. | SMALL |
| Contract | Public API/schema, architecture, security, projection, and invariant checks. | SMALL |
| Integration | CLI plus real temporary filesystem/state and composed services. | MEDIUM |
| E2E | Complete Python journeys and browser-backed panel behavior. | LARGE |
| Live opt-in | Explicit Codex binary validation outside default CI. | — |

#### Intent taxonomy

Every test declares its **intent** in the module docstring —
`Intent: <KIND> — <AC id | bug-id | task-id>` — mapping to one of CONTRACT (permanent,
asserts an acceptance criterion or a bug), SENTINEL (permanent, the single integration test
of one seam), SCAFFOLD (temporary, expires at its task/release closure) or QUARANTINE (flaky,
carries a registered bug id). **Those four are the whole vocabulary.** `REGRESSION` and `BUG`
are not tokens: a test pinning a fixed defect is CONTRACT declared against that bug id, which
is what the id in the header is for. An undeclared test is SCAFFOLD. Intent is never a pytest
marker, because the marker namespace already binds `contract` to the layer directory
`tests/contract/` and a same-named intent marker would silently re-tier tests and corrupt
every `-m` selector. The taxonomy prose lives in `tests/AGENTS.md` and the operational
protocol — admission, demotion, deletion, flake handling, health — lives in the universal
skill `dadaia-test-stewardship`; memory records the state, not the protocol.

Enforcement has two arms, and the gap between them is measured rather than asserted away.
`tests/scripts/check_test_intent_declared.py` refuses an **e2e** file carrying no module
`Intent:` header, excluding the support modules `__init__.py`, `rendezvous.py` and
`conftest.py`; it is wired into the gating suite through
`tests/integration/scripts/test_check_test_intent_declared.py`. Suite-wide, P-24's floor
measures the same declaration across every `tests/**/test_*.py`: **108 files declare it
today**, pinned as a ratchet-up-only floor whose target is every file — the remaining
undeclared files are the gap that ratchet closes, not a rule that does not apply to them.

#### Safety backstops

`tests/conftest.py` carries two autouse safety backstops: it blocks accidental real Codex
invocation unless the corresponding live flag is set (`DADAIA_E2E_REAL_WORKER` /
`DADAIA_PI_LIVE` / `DADAIA_CODEX_LIVE` / `DADAIA_CLAUDE_LIVE`), and it fakes
`ensure_workspace_venv` so no test ever builds a real venv (disk/time protection). Temporary
workspaces use pytest `tmp_path` or workspace `.dadaia/tmp/`; they never bootstrap the source
repo as a consumer workspace. A full local run passes with 4 environment-conditional skips —
two Windows-only, one requiring a LAN IPv4, and one honest degrade when the installed Codex
binary is present but unusable.

#### Derived inventories

**An inventory a test asserts is derived, never hand-kept.** Three seams hold that rule. The
two install/doctor byte goldens pin **policy only** — target mapping, banners, mode and
newline conventions — while the per-file asset inventory they used to carry is a **roster
scanned from `dadaia_workspace/public/**`** at test time, reusing the asset manager's own
walk, so adding or removing an asset fails the roster and never forces a golden regen whose
multi-line diff could hide a policy change. The skill inventory has **one derived oracle**,
extracted from that same roster, consumed by the pipeline e2e, the integration path assertions
and the orphan checker alike. Both helpers reach for the product's own enumeration rather than
a second walk, because a second walk is the next inventory to drift.

**A tree-walking scan test proves its own population.** Every source-scan test asserts the
enumerated population is non-empty **and** that one known sentinel member is in it, applied as
a two-line convention at each call site — deliberately not a shared harness or base class,
which would couple independent ratchets to one framework. A walker that loses its root then
fails loudly at its own call site instead of scanning zero files and passing vacuously green
forever. The census of those call sites lives in the convention helper's own docstring.

### Root cause, always

A defect is reproduced on the executed path, pinned by a test that fails for the real reason,
fixed at the causal site, and proven green. Workarounds and symptom patches are not acceptable
outcomes. The bug record carries the evidence: resolving a bug sets its cause, its causing
release and its resolution on the one `BUGS.jsonl` record for that bug — one record per bug
with an enumerated set of mutable governance fields, never an event stream — and a net-positive
diff on the touched feature routes through `software-architect` before the commit
([[sdd-bug-backlog-governance]]). The recurrence evidence is unambiguous: structural fixes that
**delete** surface stay quiet, while additive fixes reproduce the next defect in the same
family within a day. Removal is the preferred remedy; an additive-only fix carries an explicit
justification of why removal was impossible.

### Redaction at authoring

Diagnostic output naming a Spec Context other than the caller's own is the entry path by which
a private name reaches an authored document. It is captured with `--redact` or masked by hand
before it enters QA evidence, a SPEC, a closure record, a report, or a handoff; a foreign Spec
Context name or repo slug is never pasted verbatim. The three operator verbs whose output can
name a foreign context — `dadaia doctor`, `dadaia context list`, `dadaia context show` — all
accept `--redact`, which replaces every context name and repo slug other than the caller's
resolved context with a stable `[REDACTED-CONTEXT-<n>]` placeholder, ordinal by first
appearance within one invocation. Redaction is opt-in and happens only at the render boundary:
default output is unchanged, the services keep returning true names, and the `--json` form
stays valid JSON with the same key set.

By-hand masking is not the only branch. The gate's own render boundary masks the
private-name-bearing segments of every blob path it prints — the denylist refusal and the
oversized-blob note alike — through the same masking primitive the `--redact` verbs use, so a
diagnostic that names a file cannot itself leak the name it is protecting. The push-boundary
denylist scan ([[sdd-gate-v3]]) is the mechanical backstop on the exit path, wired and measured
by `tests/contract/test_push_gate_wiring.py`; the authoring rule above is the discipline that
covers everything an agent transcribes by hand, because a document authored into
`specs/_archive/` is an ordinary new blob and a closure that transcribes a private literal
refuses its own push.

### Satisfiable diagnostics

A gate never demands what its own tooling refuses. Every diagnostic must be **healable by an
action the product accepts**: for each violation a check reports, some legal operation must
exist that clears it, and that operation is the one the check's message names. A check that no
legal action can satisfy is a defect in the check, not a standing debt in the data.

In an append-only store the healing action is the append the store already accepts — a later
record for the same subject, never a rewrite of published history. Enforcement and diagnosis
stay separate authorities that agree by construction: enforcement answers *may this next
record be appended*, diagnosis answers *is this history healed*, and they agree precisely
because the compensation is an append enforcement already accepts. Healing history never
disables the check: a fresh, uncompensated violation still fails.

The push-boundary denylist refusal ([[sdd-gate-v3]]) is the same contract outside a
record-append store. It names the offending object, its line, and the term in masked form, and
it names the single action that clears it: edit the file, then rewrite the offending commits
before the push so no pushed object carries the term. Because the scan's scope is the objects
the push would publish, that action is always available and a rewrite of already-published
history is never demanded. The same principle governs the one case where whole-blob matching
would otherwise produce an unclearable refusal: a value the same path already published never
refuses again, so editing a long-lived file that carries a matching line is never a demand to
rewrite content the operator has already published, and the bypass the gate names as
discouraged is never the only escape.

### Browser validation

Panel changes are checked through unit DOM/static-asset contracts and Chromium journeys.
Responsive checks currently run at desktop widths (1024/1440) only — no mobile viewport is
exercised yet. Canvas games are asserted as DOM contracts in unit tests; the
nonblank-pixel-after-input journey is a normative requirement for new canvas work, not yet
enforced by an existing Playwright test. Screenshots and Playwright outputs go outside the
repository.

### Flake policy

Two markers carry flake state: `flaky` (observed pass and fail on identical code, under
diagnosis) and `quarantine` (out of every gating selector, bug-gated by P-22 — without the id
`tests/conftest.py` refuses collection with a `pytest.UsageError` whose actionable message is
printed to stderr before the raise, so the reason survives an xdist worker crash).

**No test is quarantined today**: the lane is empty, and the last observed pass-and-fail on
identical code was root-caused at its seam instead — a porcelain comparison that raced a
concurrent session's legitimate ADDITIVE write, which the no-locks doctrine permits. The
quarantine cap, the escalation clock, the bounded diagnostic reruns and the flake-rate target
are parameters with one home each: `dadaia-test-stewardship`'s `PARAMETERS.md`.

Quarantine is a carve-out of push-green, never a loosening of it. A green run with quarantined
tests is green; an **unregistered pass-on-retry is a failure**. The panel E2E job keeps
`retries: 1` and writes a Playwright JSON report outside the repository tree; a CI step fails
the job on any `passed`-after-retry result unless that test is registered as quarantined, and
names the offending spec. The step is fail-closed: a missing, empty, malformed or non-numeric
report exits 1 rather than passing, and the workflow wiring is pinned by
`tests/contract/test_ci_workflow_hygiene.py`.

### Test health

Three metrics stay continuously visible: flake rate, wall-clock trend, and the
failure-to-defect ratio per test. The full structural audit fires on a trigger, never on a
calendar — wall-clock growth over 25 % without equivalent new behavior, flake rate above the
ceiling, LARGE count above its declared cap, or quarantine at cap.

Per-tier timeouts (P-21) are applied at collection:

| Tier | Directory | Timeout |
|---|---|---|
| unit | `tests/unit/**` | 10 s |
| contract | `tests/contract/**` | 30 s |
| integration | `tests/integration/**` | 60 s |
| e2e (LARGE) | `tests/e2e/**` | 120 s |

Two tests carry a justified explicit ceiling above their tier — 180 s on a CLI-runner
integration journey and 300 s on the full handoff emit-and-validate e2e pipeline. Each cites
its own measured wall clock and names the structural split that would retire it, tracked in
the release record that curated it — never in a backlog slug, because a memory pointer into
the demand queue dangles the moment that item is consumed.

Every file under `tests/e2e/**` names an owner, and every LARGE test carries either a demotion
with a named replacement, a recorded "behaviour removed" supersession, or a written
keep-justification. The LARGE cap itself is a parameter with one home,
`dadaia-test-stewardship`'s `PARAMETERS.md`, and this atom states no number of its own for it
(P-26); the tree does not meet that cap today, which makes it a remediation target owned there
rather than a ceiling asserted here. The curation is verdict-driven — `qa-engineer` rules,
`software-engineer` executes, and no test is deleted, skipped or disabled without a verdict
carrying evidence.

Wall-clock baselines are frozen and ratcheted rather than open-ended: pre-push preflight quick
2:38, preflight full ~5:30, panel E2E 1:10, full local suite 4:37 under `-n auto`. Each CI
pytest job carries a `timeout-minutes` ceiling set against those baselines, so raising a budget
is a reviewable diff that requires a justification in the release's closure record.

Mutation testing runs once per release, off the push path, as the judge of detection value.
The tool is **`mutmut==3.7.0`**, pinned in the optional Poetry group
`[tool.poetry.group.mutation]` ([[tech-stack]]), and the cadence is backed by a runnable
command — `tests/scripts/run_mutation_baseline.sh`, which stages a scoped copy and never
writes inside the repo tree. It is absent from every push-path selector, pinned there by a
contract test, so CI push timing is unaffected; its score is evidence, never a gate.

Every third-party tool this project prescribes — **audit tooling and quality tooling alike** —
is installed at an exact version or hash pin, never a floating `pip install <name>` or
`npx <name>`. The rule is stated once on the audit surface so a newly added tool inherits it by
reading it.

The protocol behind every value above — escalation, admission, demotion, deletion — is operated
from `dadaia-test-stewardship`, the single operational home.

### CI

CI runs importability, Ruff format/lint, import-linter, mypy strict, unit, contract with 80 %
coverage, Windows/macOS cross-platform subsets, integration, Python E2E, panel E2E, repository
hygiene, backlog doctor, branch/PR governance, the security-verdict PR gate, the older dual
qa-plus-security closure gate, and a gitleaks secret-scan job on every push/PR. Release
publication repeats the relevant quality ladder before build, approval, publish, and package
smoke test.

Every gating pytest selector excludes the quarantine lane — the six in `ci.yml`, the four in
`release.yml`, and the base arguments of the local pre-push preflight — so a quarantined test
runs only under an explicit `-m quarantine` diagnosis invocation and never inside a gate. The
unit and unit-plus-contract coverage jobs report `--durations=25`; integration and E2E report
`--durations=30`. Every pytest job carries a `timeout-minutes` ceiling (unit fast 2, contract
coverage 5, cross-platform legs 8, integration 6, Python E2E 6, panel E2E 8). The 80 % floor on
`unit or contract` is a CI gate and a by-product metric — never an acceptance target, never a
reason to write a test, and never a score anchor for an audit.

Push triggers are `main`, `develop` and `feature/**`, and pull requests targeting `develop` or
`main` trigger the same matrix. The feature-branch trigger is what makes the branch contract's
first publication a fully gated one: the work is exercised by CI on the push that opens its
pull request, not first seen at a merge.

`pr-source-guard` is **one job carrying two rules**: `main` accepts a pull request only from
`develop`, and `develop` accepts one only from `feature/{M.m.p}`, the pattern translated into
POSIX ERE from the package's single pattern source with a cross-reference at the site. A PR
from any other head is mechanically unmergeable rather than merely red. The head ref reaches
the job through `env:` and is compared as a quoted literal, never interpolated into a shell
string, because it is attacker-influenceable on a fork PR. Both edges are pinned by
`tests/contract/test_ci_v2_gitflow_pr_gate.py`.

The **security-verdict gate** is a CI job on both PR edges rather than a step of the push hook:
it requires an APPROVED `security-reviewer` handoff covering the PR head sha, read from
committed evidence under `specs/releases/<id>/verdicts/` ([[sdd-gate-v3]]), pinned by
`tests/contract/test_pr_verdict_check_gate.py`. It fails closed — an unreadable coverage diff
refuses rather than assumes, and the release id is constrained to the release-id canon before
it reaches a path. Making it a **required** check is a repository setting the operator applies.

The local preflight and CI gate the **same check set** — format, lint, `mypy --strict`, the
import-boundary contracts and the test suite — pinned by
`tests/contract/test_ci_preflight_ci_gating_parity.py`, which fails when either side gains a
check the other lacks. A local green that CI turns red is the loop the root-cause law forbids,
so the parity is a test rather than a convention.

Every review verdict — `code-reviewer`, `qa-engineer`, `software-architect`,
`security-reviewer` — carries the **bug-surface delta** of each feature it touched as a
required field: reduced or increased, with evidence read from the bug ledger
(`dadaia bugs stats`), not from the test result. A verdict without it is incomplete, and "tests
green" is stated as insufficient once per persona.

Internal gates never approve a deploy by themselves: every candidate wheel must pass the
consumer-side validation matrix shipped in the package
(`public/data/CONSUMER_VALIDATION_RECIPE.md`) with an APPROVED verdict from the operator's
consumer-side validator, pinned by `tests/contract/test_consumer_validation_recipe.py`. A green
internal gate that diverges from real consumer behavior is itself a bug.

### Complexity and size

Complexity and size are governed by a **measured ratchet** (P-19), never by an aspiration. Ruff
selects `C90` (`C901`) and `PLR1702` scoped to `dadaia_workspace/`, with their ceilings pinned
in `pyproject.toml` at the observed maxima of this codebase and the ratchet direction written
beside them, so the reader of the rule and the reader of the number see the same law.

Every release accounts for what it added. The closure narrative in the release's
`RELEASE.jsonl` carries a mandatory `closure-size-accounting` note — production LOC added,
deleted and net; the three largest additions and the three largest deletions by file; the
`C90` and `PLR1702` ceilings before and after with a justification for any decrease; and the
nesting-violation count against the pinned ceiling. Every figure is measured, never estimated.

### Anti-slop

pytest uses `-p no:cacheprovider`; mypy incremental state is disabled; Ruff, coverage, and
Playwright outputs are redirected — the venv guard refuses an invocation that would write one
in-tree. Forbidden repo-local artifacts include `__pycache__`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache`, `.hypothesis`, `.coverage`, `coverage/`, `test-results/`, `playwright-report/`,
`.venv/`, and `.dadaia/`, measured by `tests/contract/test_source_repo_hygiene.py`.

### Dependencies

[[tech-stack]], [[architecture]], [[panel]], [[consumer-agent-support]], [[sdd-gate-v3]].
