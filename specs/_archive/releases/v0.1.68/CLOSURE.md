# CLOSURE — Release v0.1.68 — Lifecycle Evidence/Handoff Engine Correctness

> **Status:** Aprovado
> **Release ID:** v0.1.68
> **Merged:** `b1e469f8` (PR #130, squash), all CI green post-merge.

## Summary

Three HIGH lifecycle-engine bugs — all live on `main` at HEAD `54e9be0e`, the exact
commit the remote reporter runs — fixed at root cause, RED-first, no workarounds, plus
the full-pipeline end-to-end test that never existed:

| Bug | Fix | Disposition |
|---|---|---|
| `lifecycle-pipeline-selects-stale-unrelated-handoff` | FR1 — removed the run-unscopable block-evidence disk-glob (`_build_handoff_lookup`) + injection; block now carries an honest `no_current_artifact` detail | resolved |
| `implement-review-completed-run-leaves-unconsumed-required-payload` | FR2 — terminal APPROVED review declares `()` consumers (no phantom `implement` consumer) | resolved |
| `pipeline-does-not-derive-write-scope-from-tasks` | FR3 — new `tasks_write_scope.py` resolves the reserved task's `Write set:` into the implement scope | resolved |

FR4 added `tests/e2e/features/test_pipeline_end_to_end_throwaway_context.py` — drives a
real release through `pipeline` + `implement-review` on the fake harness end to end,
asserting all three invariants. Its absence is why these shipped.

**Partial-fix lesson (post-mortem seed):** FR3 completed the *unmet half* of v0.1.66's
"resolved" `lifecycle-implement-step-write-scope-too-narrow` — v0.1.66 shipped only the
manual `--write-scope` hatch and marked the bug resolved, but the operator's real need
(auto-derivation from TASKS.md) was never delivered. "Resolved" must mean the reported
need is met, not that a narrower reading was patched.

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 4996 passed / 18 skipped / 0 failed | `pytest -p no:cacheprovider` |
| Mutation-sanity | PASS — all 3 fixes non-false-positive (revert → RED on both targeted test and E2E) | qa-engineer handoff `2026-07-09T031824Z` |
| Lint / types / imports | PASS — ruff format+check, mypy --strict (320 files), lint-imports 9/9 | pre-push preflight + CI |
| Architect spec review | REVISE folded (F1 removal-not-rescoping, F2 FR8-test reconcile, F3 grammar, F4 co-location) | pre-implementation |
| Code review | APPROVE (2 non-blocking findings → backlog) | code-reviewer handoff `2026-07-09T032716Z` |
| Security push-gate | APPROVED, keyed to `5edb7dcc` (feature) + `85f227ac` (closure) | security-reviewer handoffs |
| CI (full matrix) | GREEN — ubuntu + Windows/macOS, PR #130 + post-merge main | GitHub Actions |

## Drifts

- One in-spirit public seam added (`container.resolve_context_specs_dir`) to avoid
  duplicating context-specs resolution in the CLI. Reviewed, non-breaking.
- Two non-blocking reviewer findings routed to backlog:
  `tasks-write-scope-traversal-hardening` (LOW defense-in-depth) and
  `implement-review-write-scope-from-tasks-parity` (MEDIUM follow-up).

## Memory updates

None in this release. Memory consolidation for the whole remediation arc — the
engine-correctness invariants and the "adapter-validated ≠ workflow-validated"
post-mortem — is done once, after Release C (v0.1.70), per the operator's directive to
consolidate memory and write the post-mortem after all issues are solved.

## Next

Release B (v0.1.69) — context resolution, session observability & CLI surface
(`codex-thread-id-bind-resolution-breaks-cli` CRITICAL + 3 more).
