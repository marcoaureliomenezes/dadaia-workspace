# TASKS — Release v0.1.78 — Lifecycle correctness & diagnosability

**Status:** Aprovado
(PLAN is folded into SPEC FRs — research already produced the per-intent task
decomposition; anchors verified in `specs/backlog/candidates.md`.)

- [x] **T-A — explicit step kind** (S) — owner: software-engineer
  Write set: `dadaia_workspace/cli/commands/lifecycle.py`,
  `dadaia_workspace/features/lifecycle/**`, `tests/**`
- [x] **T-B — atomic pipeline terminal state + step payloads** (M) — owner: software-engineer
  Write set: `dadaia_workspace/features/lifecycle/**`, `tests/**`
- [x] **T-C — one cleanup contract + 7 operator_commands** (M) — owner: software-engineer
  Write set: `dadaia_workspace/features/lifecycle/**`, `dadaia_workspace/core/models/**`,
  `dadaia_workspace/cli/**`, `tests/**`
- [x] **T-D — worker diagnostics + PI --thinking** (M) — owner: software-engineer
  Write set: `dadaia_workspace/features/lifecycle/**`,
  `dadaia_workspace/infrastructure/pi_runtime.py`, `tests/**`
- [x] **T-E — write-scope parity + parser hardening** (M) — owner: software-engineer
  Write set: `dadaia_workspace/cli/commands/lifecycle.py`,
  `dadaia_workspace/features/lifecycle/tasks_write_scope.py`, `tests/**`
- [-] **T-F — full validation + ship gates** — owner: software-engineer
  Write set: `tests/**`
