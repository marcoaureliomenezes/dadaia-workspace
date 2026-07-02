---
name: e2e-journey-coverage-and-test-canon
status: candidate
opened: 2026-07-02
owner: project-manager (curates)
source: operator architectural deep-review 2026-07-02 (lane C — test architecture)
intents:
  - subject: { kind: cli, ref: "context bind" }
    change: "add the missing master E2E journey: in a sandboxed workspace, context create -> alive -> real subprocess bind -> ctx-inject injection observed across the process boundary -> lease/gate behavior asserted, as ONE narrative scenario; today create/alive/dead are proven only in in-process CliRunner contract tests while bind/lease/gate E2E exist as isolated probes"
  - subject: { kind: cli, ref: "specs upgrade" }
    change: "add the specs-upgrade E2E: scaffold an old-shape workspace, run dadaia specs upgrade, then init + doctor must exit green in one sandboxed scenario — the consumer upgrade path currently has zero E2E coverage"
  - subject: { kind: doc, ref: "memory/quality-assurance.md#Purpose" }
    change: "disposition the post-deletion residue tests against the written no-slop law ('no test may assert that deleted code remains deleted'): tests/contract/test_retired_model_id_residue.py, tests/contract/test_bash_hook_residue.py, and the legacy-YAML absence assertions in test_onboarding_tree_v2_e2e.py — default disposition is DELETE; any test kept must be matched by an explicit named carve-out amendment in the quality-assurance atom so the code and the law stop contradicting each other"
---

# BACKLOG — E2E journey coverage + test canon

**Priority:** HIGH. The 2026-07-02 review found the pyramid healthy (≈25:4:1 across
~3.9k tests, live-harness suites correctly env-gated, no unbounded timing patterns)
and scaffold/doctor/panel E2E genuinely strong — the debt is narrative journeys, the
upgrade path, and the residue-test/law contradiction above. Also owns (prose scope):
extend the panel Playwright suite with at least one real context OPERATION journey
(today it asserts rendering and API 200s only — align with whatever surface survives
`panel-sessions-cost-dashboard-only`), and consolidate the ~226 near-duplicate
"returns empty when missing" store assertions via parametrization (LOW).

Coverage verified already strong and NOT re-owned here: all-harness scaffold structure
E2E (`tests/e2e/features/test_public_pipeline.py` — stage/install/doctor incl. drift
and deletion detection), doctor E2E matrix, and panel rendering/API E2E (10 Playwright
specs in CI). Per-harness-profile scaffold E2E is the acceptance bar of
`harness-isolation-profiles` (cross-ref).
