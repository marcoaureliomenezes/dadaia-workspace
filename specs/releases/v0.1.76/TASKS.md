# TASKS — Release v0.1.76 — Lock liberation (advisory presence)

**Status:** Aprovado

- [x] **T-1 — RED invariant tests (TDD first)** — owner: software-engineer
  Write set: `tests/**`
  New tests asserting the doctrine truth (failing now): presence module contract
  (upsert never raises, others_alive TTL semantics, renew, clear, sweep); gate:
  two-live-session MUTATING writes both ALLOW (+1 throttled advisory); rebind → write
  never blocks (CRITICAL-bug executed-path probe); pre-commit decision matrix all-ALLOW;
  mode: foreign READ bind never changes my session's mode; READ self-block kept;
  anon-session never creates presence.

- [-] **T-2 — presence.py + gate rewrite + self-scoped mode** — owner: software-engineer
  Write set: `dadaia_workspace/features/spec_context/presence.py`,
  `dadaia_workspace/features/spec_context/gate_policy.py`,
  `dadaia_workspace/hooks/sdd_gate.py`, `dadaia_workspace/hooks/sdd_post_gate.py`,
  `tests/**`
  Implement FR1/FR2(new module)/FR4; make T-1 green.

- [ ] **T-3 — lease demolition + chokepoint WARN-only + CLI** — owner: software-engineer
  Write set: `dadaia_workspace/features/spec_context/**`,
  `dadaia_workspace/features/chokepoints/**`, `dadaia_workspace/cli/**`, `tests/**`
  Delete acquire/CAS/adopt/index/incumbent-authority/`lock steal`; `context release`
  presence-based; pre-commit ALLOW-always (FR3); retire no-steal descendant tests
  (record list for CLOSURE).

- [ ] **T-4 — surfaces repoint + PI parity + platform seam** — owner: software-engineer
  Write set: `dadaia_workspace/**`, `tests/**`
  FR5 (PI extension session id + hook guard), FR6 (PLATFORM.has_fcntl ×3), FR7
  (doctor/panel/context-show/lifecycle-preflight presence repoint).

- [ ] **T-5 — full validation + ship gates** — owner: software-engineer
  Write set: `tests/**`
  Full suite green, mypy --strict, specs doctor 0 errors, ruff; AC1–AC5 checked;
  QA + security reviews; push.
