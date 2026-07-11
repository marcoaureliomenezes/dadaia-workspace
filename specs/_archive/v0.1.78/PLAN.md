# PLAN — Release v0.1.78 — Lifecycle correctness & diagnosability

**Status:** Aprovado

The per-intent decomposition was produced by the 2026-07-10 research pass (all 5
intents CONFIRMED with anchors and sizing — recorded in
`specs/backlog/candidates.md`), so this PLAN records the executed order:

1. T-A explicit step kind (S) → 2. T-B atomic pipeline terminal state (M) →
3. T-C one cleanup contract + operator_command everywhere (M) → 4. T-D worker
diagnostics + PI --thinking (M) → 5. T-E write-scope parity + parser hardening (M) →
6. T-F full validation + ship gates.

TDD law per task: RED executed-path test reproducing the bug first, then the fix,
then GREEN; no test may ratify old broken behavior. Grill correction applied during
implementation: only FIVE `operator_command=None` sites remain (not seven) — v0.1.76
already converted the two lease sites to advisory warnings.
