# PLAN — Release v0.2.9 — Hermes real-use convergence (zero-bug gate)

> **Status:** Aprovado

**Release ID:** v0.2.9
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.2.9/SPEC.md`
**Workflow:** release-definition / plan_create

## 1. Planning problem

Four independent fix classes plus a recipe expansion, sequenced so each lands with
tests before the next hermes round. The discipline rule from the operator: fix
CLASSES, never instances; no workarounds that bend the architecture.

## 2. Architectural approach

### FR1 — materialization delta (F1)

`features/lifecycle/workflows/backlog_definition.py`: today the `backlog_author`
step passes `deliverable_globs` to the generic runner (`agent_runner.py`), whose
zone check proves zone-non-empty. The workflow ALREADY owns the delta truth
(`_backlog_snapshot()` captured pre-authoring; `_authored_backlog_paths()` diffs
it post-step). The acceptance path becomes: runner gate passes AND
`_authored_backlog_paths()` non-empty; else the step blocks with the worker
diagnostic and the existing bounded structural-correction retry (same retry the
0.3.1 deliverable mechanism introduced). The generic `deliverable_globs` check
stays as-is for other steps (release-definition's create steps prove zones whose
pre-existence is legitimate — backlog's "must change" semantics is step-specific
and lives in the workflow, not the runner).

### FR2 — scaffold placeholder repair (F2)

Two seams, one contract: (a) `features/specs/scaffolder.py` / spec_artifacts memory
writer — `specs init` stops emitting the raw `feature.md` placeholder; a fresh tree
carries a valid empty catalog (`specs doctor` 0/0 out of the box). (b) a repair
leg in `specs upgrade` and `specs doctor --fix`: detect atoms whose frontmatter
still carries unsubmitted `*_PLACEHOLDER` markers and remove the file (documented
in `--help`), leaving the tree doctor-clean. Detection must never touch a filled
atom (markers exact-match only).

### FR3 — pain sweep

Each pain becomes an investigation → registered bug → class fix or evidence-backed
refutation:

- release-definition stall: reproduce in the live path; find where the run loses
  its terminal state after SPEC.md (likely a blocked step without persisted
  `blocked` detail) and make the terminal state honest.
- implementation-reviews retry prompt size: bound the rejection-correction digest
  (token budget + truncation contract) in the resume/retry path.
- release-id canon: validate `--release-id` against `core/specs_version.RELEASE_SEMVER_RE`
  (the same canon `specs doctor` enforces) at workflow intake.
- skills vs CLI syntax: grep-driven audit of projected skills against CLI help;
  fix divergences.
- reconcile/doctor loose-root-files error text: append the `root_exceptions.txt`
  guidance line.

### FR4 — recipe v2

New section in `public/data/CONSUMER_VALIDATION_RECIPE.md` (shipped in the wheel):
"Real-use matrix" with the live-chain gate and per-activity statements from the
hermes inventory; explicit note that deterministic certification never approves a
release alone.

## 3. Implementation contract bindings

- FR1: `backlog_definition._run_model_step` — after `runner.evaluate_gate_with_result`
  returns `blocked is None` for `backlog_author`, require
  `self._authored_backlog_paths()` non-empty; else synthesize the step block
  (worker diagnostic + retry semantics identical to the deliverable block).
  Tests: new unit tests around a no-write worker and an editing worker; the
  existing backlog workflow suites keep passing.
- FR2: `specs init` scaffold output change (no placeholder atom) + repair function
  shared by `specs upgrade` and `specs doctor --fix`; tests for both paths;
  doctor on a repaired tree reports 0/0.
- FR3: one commit per fixed class, each with its bug registration (reported +
  resolved) and tests.
- FR4: recipe section + hermes round protocol.

## 4. File-touch map (expected)

- `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`
- `dadaia_workspace/features/specs/scaffolder.py`, `features/specs/doctor*.py`,
  `cli/commands/specs.py` (upgrade/--fix repair)
- `features/lifecycle/` (retry digest bound, release-id intake canon)
- `public/skills/*` (syntax alignment), `features/spec_context/doctor.py` (error text)
- `public/data/CONSUMER_VALIDATION_RECIPE.md` (real-use matrix)
- Tests: `tests/unit/features/lifecycle/test_backlog*`(new/extend),
  `tests/unit/features/specs/*`, integration workflow suites
- `specs/releases/v0.2.9/*`, `specs/bugs/` (registrations), `specs/memory/*` (closure)

## 5. Validation strategy

- Per-class pytest runs; full suite before each hermes round.
- Hermes rounds with the expanded contract until a full real-use round = zero failures.
- Final: security review, push, PR, CI, release-gate, deploy 0.4.1.
