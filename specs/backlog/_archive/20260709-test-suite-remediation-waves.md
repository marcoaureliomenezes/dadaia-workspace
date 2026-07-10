---
name: test-suite-remediation-waves
status: consumed
consumed_by: v0.1.75 (shipped 2026-07-10, PR #145)
opened: 2026-07-09
owner: project-manager (curates)
source: "2026-06-03 test-suite audit (report + memory project_test_suite_audit); 2026-07-09 re-measure on feature/v0.1.74 — the audit's 3-wave remediation was never converted to a backlog item, so it was never scheduled or executed"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/ci_preflight/service.py#checks_for" }
    change: "Full test-suite rearchitecture to the operator-mandated 1,000-1,200 well-designed test fns (from ~4,450): every test fn classified KEEP (unique failure detector of one real behavior/contract, outcome asserts through the executed path) / MERGE (parametrize near-duplicate input variants; one behavior = one test) / DELETE (JS/CSS/HTML string-greps, field-presence/mock-echo asserts, cross-tier duplicates, dead/always-skipped tests). Per-cluster classification plans (all 7 clusters, every file read) live in .dadaia/tmp/claude/20260709/test-rearch/. Speed items ride along: pre-push hook switches to `ci preflight --quick` (e2e stays CI-sharded), pytest-xdist on unit tiers, tests/tmp/ gitignored, shared session-scoped workspace/panel-server fixtures replacing per-test stage+install."
---

# BACKLOG — Test-suite remediation waves (June 2026 audit, re-measured 2026-07-09)

**Problem.** The 2026-06-03 audit's remediation plan was never tracked as backlog and
never executed. Re-measure (2026-07-09): coverage-in-every-run, marker taxonomy, and
teardown findings are FIXED; suite growth 1,926→4,452 fns is legitimate executed-path
coverage of new subsystems (not slop regrowth). What remains: pre-push still runs the
full suite incl. e2e serially (~13 min, no xdist), ~60-100 residual string-grep slop
fns in the panel unit cluster, and structural consolidation debt.

**Operator mandate (2026-07-09, supersedes the incremental waves).** "Its unacceptable
these volume of tests. We have not so much features. … we only need between 1000 and
1200 tests well structured and designed." Full rearchitecture, not trimming: every test
fn classified KEEP / MERGE (parametrize, one behavior = one test) / DELETE (string-grep,
field-presence, mock-echo, redundant-with-other-tier, dead). High-value definition: a
test that is the unique failure detector for one real behavior/contract, asserting
outcomes through the executed path — never implementation strings, never a duplicate of
another tier's coverage.

**Acceptance.**
- Total collected python test fns between 1,000 and 1,200.
- No behavior/contract loses its ONLY coverage (per-cluster classification plans prove
  it; CRITICAL machinery — gate, lease, redaction, chokepoints, migrations — keeps
  consolidated coverage).
- Coverage gate (80% CI) stays green; full suite green; pre-push wall-clock materially
  down.
- Wave-1 speed items ride along: pre-push `--quick`, pytest-xdist on unit tiers,
  `tests/tmp/` gitignored.
