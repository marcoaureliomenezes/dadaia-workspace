# CLOSURE — Release v0.1.75 — Test-suite rearchitecture

**Release ID:** v0.1.75
**Status:** Aprovado
**Shipped:** PR #145, squash-merged `81e60ef7` (2026-07-10).

## Delivered

| FR | Result |
|---|---|
| FR1 cluster rearchitecture | 4,450 → **1,327** authored test fns (−70%) across 7 clusters, per the classification plans (every file read/classified). Collected: 2,822. |
| FR2 frozen-suite re-baseline | Explicit, QA-adjudicated: successor manifest (38-row invariant mapping) at `.dadaia/tmp/claude/20260710/frozen-suite-successor-baseline.md`; spec_context zero-diff in final rounds; concurrency/property files + goldens verbatim. v0.1.79's zero-diff gate re-keys to this successor baseline. |
| FR3 speed wiring | Pre-push hook → `ci preflight --quick` (security push-gate-check unconditional — reviewer-verified); pytest-xdist `-n auto` on preflight + CI unit tiers (3× randomized green); `tests/tmp/` gitignored. |
| FR4 shared fixtures | Session-scoped workspace template + panel_server_factory conftests; panel tab list single-sourced (`PANEL_PRIMARY_TABS`) for v0.1.77. |

## Validations

| Gate | Result |
|---|---|
| Full suite | GREEN — 2,812 passed, 0 failed, **2:52** wall-clock (was 14:45) |
| Coverage (unit+contract) | **84.30%** (≥80 gate) |
| Security | APPROVED per-sha ×3 (`d6b3f44c`, `f82b81ec` token-verified format-only, `fb0716d3` CWE-404 fix reviewed on merits) |
| CI | PR #145 all checks green on Linux/macOS/Windows |

## Deviations

1. **Count vs window:** 1,327 vs the operator's 1,000–1,200. Three squeeze rounds + two
   independent fresh-eyes sweeps + AST duplicate scan: zero literal duplication remains;
   the residual 127 are named CRIT detectors, AC-mapped e2e, and documented survivors.
   Recorded in TASKS; operator may order a round-3 cut into those classes.
2. **In-release production fixes (test-only release):** the rearchitected tests exposed
   3 latent cross-platform defects — one production (CWE-404 sqlite connection leak in
   `CodexRuntimeAdapter._classify_liveness`, bug
   `codex-liveness-sqlite-connection-leak` reported+resolved this release with CI
   before/after evidence) and two test-env assumptions (case-insensitive-fs dir
   collision, missing local git identity).

## Bug ledger

`codex-liveness-sqlite-connection-leak`: resolved (evidence-carrying). **5 open** —
the 2026-07-10 remote intake (1 CRITICAL lease-identity + 4 HIGH lifecycle) + the P0
cross-harness lock audit, all reserved for the next release per
open-work-outranks-backlog.

## Next

v0.1.76 redefined as **bug + audit remediation**: the 5 open bugs + P0 audit
dispositions, absorbing the overlapping backlog entries
(`central-bind-resolution-seam`, `preflight-block-reasons`,
`implement-review-write-scope`) per the audit-disposition law.
