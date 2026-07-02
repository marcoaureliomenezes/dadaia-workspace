# CLOSURE — v0.1.49 — Intake Integrity

**Status:** Aprovado
**Branch:** `feature/v0.1.49` · **Base:** `d81db184` (v0.1.48 closure) · **Merged:** `3743cb06` (PR #87, 38/38 checks green, squash)
**Origin:** operator-approved release sequence R1 (grill 2026-07-02, 3 operator
decisions) disposing 2 open bugs + 1 backlog entry.

## Summary

The release machine itself is now trustworthy: the backlog is git-tracked repository
truth exercised by real BL-* enforcement, the subject registry's invariant surface is
fail-closed (memory Markdown only — junk ids can no longer mint anchors), and the
memory-heading allowlist is consumer-extensible with the library's own scaffold
linting clean. Both picked bugs carry `resolved` terminal events; the consumed backlog
entry was removed with a durable copy and ledger.

## Shipped (conventional commits on `feature/v0.1.49`)

- `e809cd00` docs(T-49-01) — definition (SPEC/PLAN/TASKS `Aprovado` after dual
  REJECT→amend→approve reviews: software-architect + qa-engineer) + the 2026-07-02
  backlog-sanitization state (consumed v0.1.46 entry deleted; 3 bug `reported` events).
- `9ea457e2` feat(T-49-10) — FR1: `.gitignore` backlog opt-in block; 31 files tracked;
  BL-* pre-commit scope fired on the very commit that introduced it.
- `086291ab` fix(T-49-11) — FR2: `_derive_invariant_anchors` drops the `source_root`
  content-scan leg; `specs/memory/**` Markdown is the sole invariant surface.
- `76bb3dd7` feat(T-49-12) — FR3: `.heading-allowlist` union merge + Group S
  (`Padrões de qualidade`); projection stage/install/doctor exit 0.
- `e8edc565` test(T-49-10) — repo-hygiene contract updated to the tracked-backlog
  posture (the old posture was the dispositioned bug).
- `b70ca047` review(T-49-20) — qa alpha-gate APPROVE; `2fca11b2` docs — phase flip.

## Evidence triples (AC → command → observed)

- **AC-1** → `git ls-files specs/backlog/ | wc -l` → **31** post-W1 / **30** post-W5;
  `check-ignore` negative for entries, positive for `_archive/.gitkeep`.
- **AC-2** → `dadaia backlog subjects --specs-dir specs --source-root . | grep '^invariant'`
  → exactly `INV-1..INV-6` (junk ids `INV-foo/made-up/x/fixture-rule/no-claude-at-L2/
  no-fixture-drift` gone); committed tests are fixture-tree only (no-slop law).
- **AC-3** → `pytest tests/unit/scripts tests/unit/test_backlog_subject_registry.py`
  → 58 passed; live lint → **28 OK, 0 WARN, 0 ERROR**; scaffold-coverage test scoped
  to linted atoms (AGENTS.md/index.md excluded).
- **AC-4** → `ruff format --check` + `ruff check` + `mypy --strict` + full `pytest`
  → 750 formatted / all checks passed / 298 files clean / **4,386 passed**; pre-push
  preflight + security-verdict chokepoint passed; **PR #87: 38/38 green**.
- **AC-5** → `dadaia bugs status` → 1 open (the R2-scoped resolver bug only); 2
  `resolved` events with `--release v0.1.49`; durable copy + `consumed_backlog.json`
  under `specs/_archive/v0.1.49/`; memory atoms updated + catalog regenerated
  (25 features) + lint clean.

## Review ladder

- Definition: software-architect REJECT→APPROVE (2 MAJOR factual amendments: AC-1
  count, FR3 real gap) + qa-engineer REJECT→APPROVE (1 MAJOR: allowlist-pollution
  scope fence; 2 MINOR). All amendments landed before `Aprovado`.
- Alpha gate: qa-engineer APPROVE (live-evidence verification of every AC).
- Push gate: security-reviewer APPROVED (4 dimensions; verdict extended to tip
  `2fca11b2` after delta verification; handoff `metrics.commit_sha` validated).

## Validations

| Check | Result | Evidence |
|---|---|---|
| pytest (full suite) | 4,386 passed / 17 skipped (feature gate); 4,384 passed on the closure preflight before the CLOSURE-format fix | W4 gate + closure pre-push |
| ruff format --check + ruff check | clean (750 files) | W4 gate |
| mypy --strict | 0 issues (298 files) | W4 gate |
| lint-memory-atoms | 28 OK / 0 WARN / 0 ERROR | closure run |
| backlog doctor (CI-exact invocation) | clean; 30 tracked files post-consumption | W1 + closure runs |
| public doctor | exit 0 (lint script staged + projected) | W3 run |
| AC-1..AC-5 (SPEC §5) | all mechanical checks observed | evidence triples above |
| CI (PR #87) | 38/38 checks green | merge gate |

## Drifts / residuals (tracked, not dropped)

- Bugs `_archive/` gitignore block would track a `.gitkeep` if one existed — latent
  asymmetry with the new backlog block; future hygiene pass.
- `.heading-allowlist` unbounded read (CWE-400 defence-in-depth INFO) — non-blocking.
- SPEC-DOC-031 WARNs on backlog slugs mentioned by archived releases are the known
  ADR-6 false-positive class (mentions, not consumption) — no action.

## Backlog returns

None. One INFO note recorded for a future hygiene pass: the bugs `_archive/` gitignore
block would track a `.gitkeep` if one existed (latent asymmetry with the new backlog
block); `.heading-allowlist` size cap (CWE-400 defence-in-depth, non-blocking).

## Memory updates (this closure)

- `sdd-bug-backlog-governance.md`: backlog now git-tracked repository truth;
  invariant anchors memory-only; runtime-state line corrected.
- `specs-doctor.md`: LINT-1 allowlist = curated ∪ `.heading-allowlist` (MEMORY-class
  edit note). Both atoms `release_origin: v0.1.49`.
