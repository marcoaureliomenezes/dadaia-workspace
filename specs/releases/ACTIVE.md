---
release: v0.1.28
phase: IMPLEMENTATION
---

# Active release: v0.1.28 — Workflow Model Governance + Panel Control Plane

Implements `FEAT-WORKFLOW-MODEL-GOVERNANCE-01` (whole epic A→D, sliced into 4 waves).

**Phase:** IMPLEMENTATION. DEFINITION complete — SPEC/PLAN/TASKS Aprovado; grill recorded
in `GRILL.md`; DEFINITION review APPROVED by software-architect (0 crit/high, 3 MEDIUM)
and qa-engineer (0 crit, 2 HIGH impl-time obligations). Review handoffs under
`.dadaia/handoff/dadaia-workspace/`.

Binding implementation-time obligations carried from review:
- M3: Wave A resolver sources library defaults from `model_profiles.py` directly so Wave A
  is independently green; catalog defaults (Wave B) extend, not gate, the resolver.
- M1: keep `LifecycleRun` schema version literal; assert old-format records still load.
- M2: single ordered precedence for resolved_model vs legacy tier-match in CodexExecAdapter.
- H1: panel editor E2E is a Playwright `tests/e2e/panel/*.spec.ts`; update existing
  `workflows-tab.spec.ts` for first-class Workflows nav (D-5).
- H2: closure pins the GitHub Actions `e2e-panel` job green (not run by `ci preflight`).
- AC-6: in-flight test injects the policy mutation BETWEEN step 1 and step 2 via fake hook.
- AC-7: historical-run read pinned to a task; reads snapshot, never re-resolves.

Branch: `feature/v0.1.28`. Waves run A → B → C → D, each green before the next.
