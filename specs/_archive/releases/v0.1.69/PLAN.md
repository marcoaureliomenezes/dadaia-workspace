# PLAN — Release v0.1.69 — Context Resolution, Session Observability & CLI Surface

> **Status:** Aprovado
> **Release ID:** v0.1.69
> **Owner:** product-engineer

## Strategy

Four CLI/context defects, each fixed RED-first, then a single E2E (FR5) proving a
bound context is visible to the CLI — the operator-observability path all four
jointly broke. Waves ordered by dependency:

- **Wave A — FR1 (`CODEX_THREAD_ID`).** `core/session_env.py` single-source constant +
  `entry_harness` predicate, PLUS (architect F1a) `lock.py` `_caller_session_id`
  routed through the single source, PLUS (architect F1b, SAFETY) the
  `ENTRY_SIGNAL_ENV_VARS` hermeticity envelope extended so pytest inside a Codex TUI
  cannot auto-spawn a real Layer-2 worker. RED: unit tests with `CODEX_SESSION_ID`
  unset / `CODEX_THREAD_ID` set; plus an integration test for bind→resolver.
- **Wave B — FR2 (diagnostic `--context` parity).** `cli/commands/lifecycle.py` +
  `specs.py`. RED: CliRunner asserts exit 2 today. GREEN adds the options and threads
  them; mirrors the existing `pipeline`/`implement-review` option shape (no new
  mechanism).
- **Wave C — FR3 (build the preflight-input probe assembly + wire).** Depends on FR2's
  options. Architect F3: this is NOT wiring — `LifecyclePreflightInput`'s state classes
  have zero producers; the stub stands in for a subsystem never built. GREEN adds a
  container builder `build_lifecycle_preflight_input` composing producers from EXISTING
  readers (git/active-release/specs-doctor/lease/hygiene/binding) + an
  `expected_phase`/`required_mode` policy, each with its own RED test; wires
  `service.preflight`; retires the stub. AC3.1 accepts OK **or** a specific blocked
  reason with a non-null `operator_command` (a dirty/unbound checkout correctly blocks).
- **Wave D — FR4 (`show` reads incumbent pointer).** `cli/commands/context.py` only.
  RED: bind then `show --json` returns `session: null`. GREEN adds the pointer
  fallback.
- **Wave E — FR5 (E2E) + FR6 (validation).** The bound-context-visible E2E; qa
  validates the suite + gates.

FR1/FR4/FR-A are disjoint files and may proceed in parallel; FR3 depends on FR2
(both touch `lifecycle.py`, different functions — serialize or declare disjoint
function write sets).

## Test plan
- Executed-path RED proofs per FR (drive real CLI via CliRunner / real
  `session_env`/`service` functions), each committed FAILING first.
- FR5 E2E provisions a real `tmp_path` context + bind and asserts CLI visibility.
- Full `pytest -p no:cacheprovider`, `ruff format --check`, `ruff check --no-cache`,
  `mypy --strict`, `lint-imports` (9).

## Risk
- FR1 is a single-source constant + predicate; lowest code risk, highest value.
  Guard: AC1.2 preserves `CODEX_SESSION_ID` preference when both present.
- FR3 retires a stub — confirm no other caller depends on `unresolved_runtime_preflight`
  (grep); if a test pins the stub's BLOCKED output, correct it with a documented reason.
- FR2/FR4 are additive CLI/observability; prior behavior preserved when the new
  option/pointer is absent.

## Review gate
- software-architect REVIEW on SPEC+PLAN before implementation.
- Post-implementation: qa-engineer suite/mutation validation + security-reviewer
  push-cycle handoff keyed to the pushed sha (FR1 touches session identity — security
  confirms no auth/attribution weakening).
