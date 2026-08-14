---
slug: quality-assurance
title: quality-assurance
category: core
tldr: Layered pytest/browser validation with declared intent, size tiers, per-tier timeouts, a bug-gated quarantine lane, and strict CI gates.
summary: >-
  Defines test layers and their size tiers, the intent taxonomy mapping, safety fixtures,
  browser evidence, the flake/quarantine policy and its escalation ladder, the test-health
  metrics with tiered timeouts and ratcheted wall-clock ceilings, CI gates including the
  required pr-source-guard on main and the main/develop-only push triggers, coverage as a
  by-product metric, cross-platform checks, the consumer-side approval boundary, the
  redaction-at-authoring posture for diagnostic output, and anti-slop requirements.
tags:
- testing
- pytest
- ci
- quality
- test-architecture
- flake
- quarantine
- privacy
token_estimate: 1900
last_updated: '2026-08-14'
release_origin: v0.3.0
---

## Purpose

Tests prove public behavior and failure handling at the cheapest reliable layer. The
suite must be hermetic by default and must never invoke a paid/live binary without an
explicit opt-in.

## Layers

| Layer | Scope | Size tier |
|---|---|---|
| Unit | Pure behavior, validators, rendering, adapters with fakes. | SMALL |
| Contract | Public API/schema, architecture, security, projection, and invariant checks. | SMALL |
| Integration | CLI plus real temporary filesystem/state and composed services. | MEDIUM |
| E2E | Complete Python journeys and browser-backed panel behavior. | LARGE |
| Live opt-in | Explicit Codex binary validation outside default CI. | — |

Every test declares its **intent** in the module docstring —
`Intent: <KIND> — <AC id | bug-id | task-id>` — mapping to one of CONTRACT (permanent,
asserts an acceptance criterion or a bug), SENTINEL (permanent, the single integration
test of one seam), SCAFFOLD (temporary, expires at its task/release closure) or
QUARANTINE (flaky, carries a registered bug id). An undeclared test is SCAFFOLD. Intent
is never a pytest marker, because the marker namespace already binds `contract` to the
layer directory `tests/contract/` and a same-named intent marker would silently re-tier
tests and corrupt every `-m` selector. The taxonomy prose lives in `tests/AGENTS.md` and
the operational protocol — admission, demotion, deletion, flake handling, health — lives
in the universal skill `dadaia-test-stewardship`; memory records the state, not the
protocol.

`tests/conftest.py` carries two autouse safety backstops: it blocks accidental real
Codex invocation unless the corresponding live flag is set
(`DADAIA_E2E_REAL_WORKER` / `DADAIA_PI_LIVE` / `DADAIA_CODEX_LIVE` /
`DADAIA_CLAUDE_LIVE`), and it fakes `ensure_workspace_venv` so no test ever builds a
real venv (disk/time protection). Temporary workspaces use pytest `tmp_path` or
workspace `.dadaia/tmp/`; they never bootstrap the source repo as a consumer
workspace. The gating set is ~2,123 collected tests, of which 55 are LARGE (e2e-tier
pytest journeys; the wider LARGE census including the browser specs is ~84). A full
local run passes ~2,120 with 3 environment-conditional skips (two Windows-only, one
requiring a LAN IPv4) in 4:37 under `-n auto`.

## Root Cause, Always

A defect is reproduced on the executed path, pinned by a test that fails for the real
reason, fixed at the causal site, and proven green. Workarounds and symptom patches are
not acceptable outcomes. The recurrence evidence is unambiguous: structural fixes that
**delete** surface stay quiet, while additive fixes reproduce the next defect in the same
family within a day. Removal is the preferred remedy; an additive-only fix carries an
explicit justification of why removal was impossible.

## Redaction At Authoring

Diagnostic output naming a Spec Context other than the caller's own is the entry path by
which a private name reaches an authored document. It is captured with `--redact` or
masked by hand before it enters QA evidence, a SPEC, a CLOSURE, a report, or a handoff; a
foreign Spec Context name or repo slug is never pasted verbatim. The three operator verbs
whose output can name a foreign context — `dadaia doctor`, `dadaia context list`,
`dadaia context show` — all accept `--redact`, which replaces every context name and repo
slug other than the caller's resolved context with a stable `[REDACTED-CONTEXT-<n>]`
placeholder, ordinal by first appearance within one invocation. Redaction is opt-in and
happens only at the render boundary: default output is unchanged, the services keep
returning true names, and the `--json` form stays valid JSON with the same key set. The
doctrine binds the `qa-engineer` persona, which carries it in its canonical source; the
push-boundary denylist scan ([[sdd-gate-v3]]) is the mechanical backstop for the same
class of leak on the exit path.

## Satisfiable Diagnostics

A gate never demands what its own tooling refuses. Every diagnostic must be **healable by
an action the product accepts**: for each violation a check reports, some legal operation
must exist that clears it, and that operation is the one the check's message names. A
check that no legal action can satisfy is a defect in the check, not a standing debt in
the data.

In an append-only, event-sourced store the healing action is a compensating **event**,
never an edit: a violation is reported only while no later event of the compensating kind
exists for the same subject, and history is corrected by appending rather than by
rewriting a row. Enforcement and diagnosis are separate authorities that must agree by
construction — enforcement answers *may this next event be appended*, diagnosis answers
*is this history healed*, and they agree precisely because the compensation is an event
enforcement already accepts. Healing history never disables the check: a fresh,
uncompensated violation still fails.

The push-boundary denylist refusal ([[sdd-gate-v3]]) is the same contract outside an
event-sourced store. It names the offending object, its line, and the term in masked
form, and it names the single action that clears it: edit the file, then rewrite the
offending commits before the push so no pushed object carries the term. Because the
scan's scope is the objects the push would publish, that action is always available and a
rewrite of already-published history is never demanded — a refusal clearable only by
rewriting published history would be a defect in the check.

## Browser Validation

Panel changes are checked through unit DOM/static-asset contracts and Chromium journeys.
Responsive checks currently run at desktop widths (1024/1440) only — no mobile viewport
is exercised yet. Canvas games are asserted as DOM contracts in unit tests; the
nonblank-pixel-after-input journey is a normative requirement for new canvas work, not
yet enforced by an existing Playwright test. Screenshots and Playwright outputs go
outside the repository.

## Flake Policy

Two markers carry flake state: `flaky` (observed pass and fail on identical code, under
diagnosis) and `quarantine` (out of every gating selector). A `quarantine` mark requires
a registered bug id as `bug="<bug-slug>"`; without it `tests/conftest.py` refuses
collection with a `pytest.UsageError` whose actionable message is printed to stderr
before the raise, so the reason survives an xdist worker crash. The marker set is closed
and pinned: a contract test compares `pyproject.toml`'s markers against the known set in
`tests/conftest.py`, so a typo cannot become a new exclusion lane.

Quarantine is capped at 8 tests and, at cap, blocks admission of new LARGE tests.
Escalation is time-bound: 30 days unresolved becomes `disabled`; 30 clean days restores
the test; `disabled` plus one release with no registered plan is deleted. Diagnostic
reruns are bounded at 3. The flake rate targets under 0.5 % of runs against a hard
ceiling of 1 %.

Quarantine is a carve-out of push-green, never a loosening of it. A green run with
quarantined tests is green; an **unregistered pass-on-retry is a failure**. The panel E2E
job keeps `retries: 1` and writes a Playwright JSON report outside the repository tree; a
CI step fails the job on any `passed`-after-retry result unless that test is registered as
quarantined, and names the offending spec. The step is fail-closed: a missing, empty,
malformed or non-numeric report exits 1 rather than passing.

## Test Health

Three metrics stay continuously visible: flake rate, wall-clock trend, and the
failure-to-defect ratio per test. The full structural audit fires on a trigger, never on a
calendar — wall-clock growth over 25 % without equivalent new behavior, flake rate above
the ceiling, LARGE count above the declared cap, or quarantine at cap.

Per-test timeouts are applied by tier at collection and never override an explicit
`@pytest.mark.timeout`:

| Tier | Directory | Timeout |
|---|---|---|
| unit | `tests/unit/**` | 10 s |
| contract | `tests/contract/**` | 30 s |
| integration | `tests/integration/**` | 60 s |
| e2e (LARGE) | `tests/e2e/**` | 120 s |

A test that needs more time than its tier is mis-tiered: the tier is what gets fixed, never
the default. Two tests carry a justified explicit ceiling above their tier — 180 s on a
CLI-runner integration journey and 300 s on the full handoff emit-and-validate e2e
pipeline — each citing a measured wall clock and a named remediation entry in the backlog.

Every file under `tests/e2e/**` names an owner. The LARGE cap for this repository is 30,
declared and measured as a WARN rather than a hard failure while the count is above it.

Wall-clock baselines are frozen and ratcheted rather than open-ended: pre-push preflight
quick 2:38, preflight full ~5:30, panel E2E 1:10, full local suite 4:37 under `-n auto`.
Each CI pytest job carries a `timeout-minutes` ceiling set against those baselines, so
raising a budget is a reviewable diff that requires a justification in the release CLOSURE.

Mutation testing runs once per release, off the push path, as the judge of detection
value; the cadence is declared and the tool is not yet selected. The protocol behind every
value above — escalation, admission, demotion, deletion — is operated from
`dadaia-test-stewardship`, the single operational home.

## CI

CI runs importability, Ruff format/lint, import-linter, mypy strict, unit, contract with
80% coverage, Windows/macOS cross-platform subsets, integration, Python E2E, panel E2E,
repository hygiene, backlog doctor, branch/PR governance, security verdict, and a
gitleaks secret-scan job on every push/PR. Release publication repeats the relevant
quality ladder before build, approval, publish, and package smoke test.

Every gating pytest selector excludes the quarantine lane — the six in `ci.yml`, the four
in `release.yml`, and the base arguments of the local pre-push preflight — so a quarantined
test runs only under an explicit `-m quarantine` diagnosis invocation and never inside a
gate. The unit and unit-plus-contract coverage jobs report `--durations=25`; integration
and E2E report `--durations=30`. Every pytest job carries a `timeout-minutes` ceiling
(unit fast 2, contract coverage 5, cross-platform legs 8, integration 6, Python E2E 6,
panel E2E 8). The 80 % floor on `unit or contract` is a CI gate and a by-product metric —
never an acceptance target, never a reason to write a test, and never a score anchor for an
audit.

Push triggers are `main` and `develop` only, matching the branches that exist remotely;
feature and hotfix branches are local-only and carry no trigger, so their coverage is the
local pre-push preflight plus the `develop` push. `pr-source-guard` is a **required**
check on `main`: it fires on any pull request targeting `main` and fails unless the head
ref is exactly `develop`, making a PR from any other head mechanically unmergeable rather
than merely red. The head ref reaches the job through `env:` and is compared as a quoted
literal, never interpolated into a shell string, because it is attacker-influenceable on a
fork PR.

Internal gates never approve a deploy by themselves: every candidate wheel must pass the
consumer-side validation matrix shipped in the package
(`public/data/CONSUMER_VALIDATION_RECIPE.md`) with an APPROVED verdict from the
operator's consumer-side validator. A green internal gate that diverges from real
consumer behavior is itself a bug.

## Anti-Slop

pytest uses `-p no:cacheprovider`; mypy incremental state is disabled; Ruff, coverage,
and Playwright outputs are redirected. Forbidden repo-local artifacts include
`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `.coverage`,
`coverage/`, `test-results/`, `playwright-report/`, `.venv/`, and `.dadaia/`.

## Dependencies

[[tech-stack]], [[architecture]], [[panel]], [[consumer-agent-support]], [[sdd-gate-v3]].
