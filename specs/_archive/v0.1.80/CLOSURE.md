# CLOSURE — Release v0.1.80 — LOW-debt cleanup & resolution-rung allowlist

**Shipped:** PR #157, squash-merged to main as `4f9ae75a` (2026-07-11). All PR checks
green; post-merge main CI green.

## Delivered

- FR1: perf-flake root-cause — RSS ceiling replaced by an environment-independent
  content-bytes budget; the real ~500MB source identified by isolated tracemalloc
  measurement (pre-existing legitimate `sorted(rglob())` materialization, documented
  inline). **First fully-green suite run of the arc: 2,884 passed / 0 failed, no
  deselects.**
- FR2: handoff-emitter example hardening — honest correction (literal claim already
  fixed in v0.1.62); the surviving report-mode placeholder defect fixed + a new
  schema-validity contract test extracting the live examples from SKILL.md; projected.
- FR3: `[A-Za-z0-9_-]+` fullmatch allowlist at the explicit/env resolution rungs —
  closes the v0.1.77 security INFO; explicit-raises vs env-skips asymmetry
  (DoS-preventing); exception-safe env scope/restore.

## Dispositions

- Bug `perf-hygiene-scan-rss-ceiling-flaky-in-sandbox` (LOW): **RESOLVED** at root
  cause with fault-injection regression-detector proof (QA independently verified,
  catching and correcting its own false-negative probe).
- Bug `handoff-emitter-example-omits-required-artifact` (LOW): **RESOLVED** with the
  honest already-fixed-in-v0.1.62 correction + the surviving defect fixed and pinned.
- Backlog `context-name-allowlist-at-resolution-rungs` (P4): **delivered**, archived.

**Ledger after closure: 0 open bugs.** Open backlog: only
`20260710-deprecation-strips-and-doctor-cleanup` (v0.1.81, ship ≥ 2026-08-01).

## Validations

- Full suite 2,884 passed / 10 skipped / 0 failed (perf test in-suite); mypy --strict
  clean; ruff clean; doctors green.
- QA APPROVED (adversarial fault-injection verification); security APPROVED ×2
  (per-sha, incl. token-level review of the env scope/restore and fullmatch anchoring).
