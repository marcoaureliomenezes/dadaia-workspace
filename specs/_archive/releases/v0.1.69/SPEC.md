# SPEC — Release v0.1.69 — Context Resolution, Session Observability & CLI Surface

> **Status:** Aprovado
> **Release ID:** v0.1.69
> **Owner:** product-engineer
> **Picked set:** 4 open bugs (1 CRITICAL, 1 HIGH, 2 MEDIUM) — the CLI/context layer

## Objective

Make a bound context actually usable and visible from the CLI. Four defects
compound into "the operator cannot trust which context a command targets": a
modern Codex session's bind is invisible to every resolver-driven command
(CRITICAL); the diagnostic verbs won't accept an explicit `--context`; `preflight`
is an inert hardcoded stub; and `context show` never reflects a successful bind.
Each fixed at root cause, RED-first, no workarounds.

## Picked bugs

| Bug id | Severity | Disposition |
|---|---|---|
| `codex-thread-id-bind-resolution-breaks-cli` | CRITICAL | Fixed (FR1) |
| `lifecycle-diagnostic-commands-missing-context-options` | HIGH | Fixed (FR2) |
| `lifecycle-preflight-unusable-resolved-runtime-inputs` | MEDIUM | Fixed (FR3) |
| `context-bind-success-not-reflected-in-context-show` | MEDIUM | Fixed (FR4) |

All fixed directly; none superseded. FR1/FR4 restore implicit resolution; FR2
provides the explicit `--context` escape hatch the release law wants regardless;
FR3 makes `preflight` a real diagnostic.

## Reproduction & TDD mandate — no workarounds

Under `feedback-reproduce-rootcause-no-workaround`. Every FR carries an
`AC-N(repro)`: a failing executed-path test on current code that passes after the
root-cause fix. No wrapper scripts, no `--specs-dir` band-aids, no swallowed errors.

---

## Root causes (verified by inspection)

### FR1 — Codex `CODEX_THREAD_ID` is not a recognized harness session id (CRITICAL)

`dadaia_workspace/core/session_env.py:44`:
`HARNESS_SESSION_ID_ENV_VARS = ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID")` —
omits `CODEX_THREAD_ID`, which modern Codex tool subprocesses expose *instead* of
`CODEX_SESSION_ID`. So `harness_session_id()` (`:58-69`) returns `None` for a live
Codex session, `context bind` never persists a session record keyed to the live
thread, and (the Codex sandbox collapsing the process tree to PID 1 defeating the
ancestry fallback) every resolver-driven command — `bugs`, `specs`, `memory`,
`lifecycle` — fails with "Could not resolve specs_dir". `entry_harness()` (`:72-91`,
line 91) likewise checks only `CODEX_SESSION_ID`, so Codex entry detection is
invisible in the same runtime.

**Invariant to restore:** `CODEX_THREAD_ID` is a first-class Codex session id.
`harness_session_id()` returns it (preferring `CODEX_SESSION_ID` when both present);
`entry_harness()` treats it as a Codex entry signal. Consumers that iterate
`HARNESS_SESSION_ID_ENV_VARS` (`hooks/_common.resolve_session_id`, `core/specs_resolver`,
`context.py` bind via `harness_session_id()`) inherit automatically. No
`--specs-dir`/eval-export workaround.

**Two consumers do NOT inherit and are in scope (architect F1):**
1. `dadaia_workspace/cli/commands/lock.py` `_caller_session_id()` hardcodes its own
   tuple `("DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID")` and
   does not read `HARNESS_SESSION_ID_ENV_VARS` — in a modern Codex session
   `dadaia lock steal`/lease-transfer would key to a random `sess_<uuid>`. Route it
   through the single source (preserving the `DADAIA_SESSION_ID` override) or add
   `CODEX_THREAD_ID`.
2. **Test-hermeticity envelope (SAFETY):** `tests/fixtures/harness_env.py`
   `ENTRY_SIGNAL_ENV_VARS` + the autouse scrub (`tests/conftest.py`). Once FR1.2 makes
   `CODEX_THREAD_ID` a codex entry signal, a developer running pytest inside a modern
   Codex TUI (which exports `CODEX_THREAD_ID`) would have `entry_harness()` resolve
   `"codex"` *during the suite* and auto-default a real credit-spending Layer-2 worker
   — the exact hazard the v0.1.64 envelope prevents. `CODEX_THREAD_ID` MUST be added
   to `ENTRY_SIGNAL_ENV_VARS` (the scrub + `test_ci_job_env_carries_no_entry_signal_vars`
   guard inherit it). This is a mandatory, documented test-envelope extension, not a
   weakening.

### FR2 — Diagnostic CLI verbs reject explicit `--context`/`--release-id` (HIGH)

`dadaia_workspace/cli/commands/lifecycle.py`: `status` (`def status`, ~:154),
`preflight` (~:241), and `handoffs_doctor` (~:1888) expose only `--json`/`--help`,
while `pipeline` (~:1582) and `implement_review` (~:1497) already accept `--context`
(default `dadaia-workspace`) and `--release-id`. `specs doctor` offers only
`--specs-dir`. With implicit resolution unreliable/wrong (FR1/FR4), the missing
`--context` makes context-scoped diagnostics unusable for a non-default context.

**Scope `--context` only where it is load-bearing (architect F2).** The builders
differ: `build_lifecycle_hygiene_service(workspace_root)` (backing `status`) and
`build_workflow_handoff_doctor(workspace_root)` (backing `handoffs doctor`) are
**workspace-global** — they read workspace-level `.dadaia/` state, not
`repos/<ctx>/specs`. Adding `--context` there would be *accepted-but-ignored* (worse
than absent). So only `preflight` and `specs doctor` — where `--context`/`--release-id`
genuinely select `repos/<ctx>/specs` and feed `LifecyclePreflightInput` — get the options.

**Invariant to restore:** `preflight` accepts `--context` (default
`dadaia-workspace`) + `--release-id`; `specs doctor` accepts `--context` (resolving
`repos/<context>/specs` via `resolve_specs_dir_for_cli`, mutually exclusive with
`--specs-dir`). `status`/`handoffs doctor` stay workspace-global (no scoping option).
No new resolution mechanism — reuse the existing specs-resolver path.

### FR3 — `preflight` has no runtime-probe producer; the stub stands in for a subsystem that was never built (MEDIUM bug, feature-sized fix — architect F3)

`dadaia_workspace/cli/commands/lifecycle.py` `preflight` calls
`service.unresolved_runtime_preflight()`, which at
`dadaia_workspace/features/lifecycle/service.py:195-209` unconditionally returns
BLOCKED ("lifecycle preflight requires resolved runtime inputs", `operator_command:
null`). The real `LifecyclePreflightService.preflight(data)` (`service.py:175-193`)
consumes a `LifecyclePreflightInput` (`service.py:119-134`) whose 11 fields include
four **structured state classes** — `ActiveReleaseState`, `GitPreflightState`,
`SpecsDoctorState`, `LeaseModeState` — plus `HygieneCounters`, `expected_phase`,
`required_mode`, `required_handoffs`. **Those state classes have zero producer
functions in the production tree** (verified: `LifecyclePreflightInput(...)` is
constructed only in `test_preflight_service.py` with hand-fed states). The stub exists
precisely because **the runtime-probe layer was never built** — so `preflight(data)`
has never been reachable from any live probe. This is a feature-sized fix presented in
the bug as "wire the stub"; it is scoped honestly here.

**Invariant to restore:** build a real preflight-input assembly — a container builder
`build_lifecycle_preflight_input(workspace_root, context, release_id)` that composes
the state producers from **existing readers** wherever they exist (active-release ←
`ACTIVE.md`; git ← the git adapter for dirty/upstream/unpushed; specs-doctor ← the
specs-doctor service; lease/mode ← `session_identity`; hygiene ←
`build_lifecycle_hygiene_service().status()`; bound context ← the binding reader), and
a small `expected_phase`/`required_mode` policy derived from `ACTIVE.md` phase. The
`preflight` CLI calls `service.preflight(data)` with that input; the
`unresolved_runtime_preflight` stub is retired (grep confirms `lifecycle.py:246` is its
only production caller). A dirty/unbound/behind checkout SHOULD block — but with a
**specific** reason and a non-null `operator_command`, never the generic stub string.
Reuse existing readers; do not fork a second git/specs-doctor/lease implementation.

### FR4 — `context show` ignores the incumbent pointer a bind just wrote (MEDIUM)

`dadaia_workspace/cli/commands/context.py`: `bind` (`def bind`, ~:307) mints a
session id, writes the record, and refreshes the incumbent pointer via
`session_identity.set_incumbent(...)` (`:413`) — but only *prints* the sid. `show`
(`def show`, ~:184) resolves the session **solely** from
`os.environ.get("DADAIA_SESSION_ID")` (`:207`); when unset (the normal case after a
bare `bind`), `session` is `None` — it never consults the incumbent pointer `bind`
just wrote. So a successful bind is invisible to `show`.

**Invariant to restore:** when `DADAIA_SESSION_ID` is absent, `show` falls back to
`session_identity.read_incumbent_ptr(workspace, ctx)` (or `resolve_identity`), loads
and stale-checks that record, and populates `session` with sid/mode/release/context.
Resolution order: env `DADAIA_SESSION_ID` → context incumbent pointer. Reuses the
pointer `bind` already writes — no new persistence.

---

## Functional requirements

### FR1 — Recognize `CODEX_THREAD_ID`
- **FR1.1** Append `"CODEX_THREAD_ID"` to `HARNESS_SESSION_ID_ENV_VARS`, ordered
  *after* `CODEX_SESSION_ID` (session-id preferred when both present).
- **FR1.2** `entry_harness()` treats `CODEX_SESSION_ID` **or** `CODEX_THREAD_ID` as
  the Codex entry signal.
- **FR1.3** No change to Claude/other detection; a Claude session (no Codex vars)
  is unaffected.
- **FR1.4 (architect F1a)** Route `lock.py` `_caller_session_id()` through the single
  source `harness_session_id()` (preserving the `DADAIA_SESSION_ID` override), OR add
  `CODEX_THREAD_ID` to its hardcoded tuple — so lease-transfer keys to the live thread.
- **FR1.5 (architect F1b — SAFETY, mandatory)** Add `"CODEX_THREAD_ID"` to
  `tests/fixtures/harness_env.py` `ENTRY_SIGNAL_ENV_VARS` so the autouse scrub and
  `test_ci_job_env_carries_no_entry_signal_vars` neutralize it — otherwise a developer
  running pytest inside a Codex TUI auto-spawns a real Layer-2 worker. Documented
  test-envelope extension (FR6.2), not a weakening.

**AC1.1** With `CODEX_SESSION_ID` unset and `CODEX_THREAD_ID` set,
`harness_session_id()` returns the (sanitized) thread id and `entry_harness()`
returns `"codex"`.
**AC1.2** With both set, `harness_session_id()` returns the `CODEX_SESSION_ID`
value (preference preserved).
**AC1.3** Integration: with only `CODEX_THREAD_ID` set, `context bind` persists a
session record keyed to the thread id and a subsequent resolver call attributes the
bound context (no `--specs-dir`).
**AC1(repro)** executed-path test FAILS on current code (returns `None`/no record),
PASSES after FR1.

### FR2 — Diagnostic CLI context/release parity (scoped where load-bearing)
- **FR2.1** Add `--context` (default `dadaia-workspace`) + `--release-id` to
  `preflight` (the verb where they feed `LifecyclePreflightInput`).
- **FR2.2** Add `--context` to `specs doctor` (resolving `repos/<context>/specs` via
  `resolve_specs_dir_for_cli`), mutually exclusive with `--specs-dir`.
- **FR2.3 (architect F2)** `status` and `handoffs doctor` are workspace-global (their
  builders take no specs_dir) — do NOT add a `--context` that changes nothing. If a
  JSON surface benefits, an echo of the active context may be added as clearly
  advisory, not as scoping.

**AC2.1** `dadaia lifecycle preflight --context <ctx> --release-id <rel>` exits ≠ 2
(no "No such option") and resolves `repos/<ctx>/specs`.
**AC2.2** `dadaia specs doctor --context <ctx>` resolves `repos/<ctx>/specs`; passing
both `--context` and `--specs-dir` errors clearly.
**AC2.3** `status`/`handoffs doctor` remain workspace-global (no false `--context`).
**AC2(repro)** CliRunner executed-path test for `preflight`+`specs doctor` FAILS on
current code (exit 2), PASSES after FR2.

### FR3 — Build the preflight-input probe assembly and wire the real preflight
- **FR3.1** Add a container builder
  `build_lifecycle_preflight_input(workspace_root, context, release_id)` composing the
  state producers from **existing readers** (active-release ← `ACTIVE.md`; git ← the
  git adapter; specs-doctor ← the specs-doctor service; lease/mode ← `session_identity`;
  hygiene ← `build_lifecycle_hygiene_service().status()`; bound context ← binding
  reader) + an `expected_phase`/`required_mode` policy from `ACTIVE.md` phase. Each
  producer gets its own RED unit test.
- **FR3.2** The `preflight` CLI calls `service.preflight(data)` with that input; retire
  `unresolved_runtime_preflight` (only production caller is `lifecycle.py:246`).
- **FR3.3** A blocked preflight carries a specific reason and a non-null
  `operator_command` — never the generic stub string.

**AC3.1** `preflight --context <ctx> --release-id <rel> --json` returns `status: OK`
**or** a specific blocked reason with a **non-null `operator_command`** — and never the
generic "requires resolved runtime inputs" stub. (A dirty/unbound checkout SHOULD block
with an actionable reason; that is correct, not a failure.)
**AC3.2** A spy/executed-path test asserts `service.preflight(data)` is invoked by
the command (the stub is no longer called).
**AC3(repro)** FAILS on current code (stub always BLOCKED), PASSES after FR3.

### FR4 — `context show` reads the incumbent pointer
- **FR4.1** When `DADAIA_SESSION_ID` is absent, `show` resolves the session from
  `session_identity.read_incumbent_ptr(workspace, ctx)` (or `resolve_identity`),
  loads + stale-checks the record, and populates `data["session"]`.
- **FR4.2** Resolution order env → incumbent pointer; a stale/absent pointer ⇒
  `session: null` (unchanged behavior).

**AC4.1** After `context bind <ctx> --mode implementation --release <rel>` (with
`DADAIA_SESSION_ID` unset), `context show <ctx> --json` reports
`session.session_id` == the bound sid and populated `mode`/`release`/`context`.
**AC4(repro)** FAILS on current code (`session: null`), PASSES after FR4.

### FR5 — End-to-end: a bound context is visible to diagnostics
- **FR5.1** An executed-path E2E provisions a `tmp_path` workspace + context, binds
  it (no `DADAIA_SESSION_ID` in env), then asserts `context show --json` reflects the
  bind (FR4) and a diagnostic verb accepts `--context` and targets it (FR2). This is
  the operator-observability path the four bugs jointly broke.

**AC5.1** `test_bound_context_visible_to_cli_e2e` green; RED on pre-FR2/FR4 code.

### FR6 — Regression & suite integrity
- **FR6.1** Full `pytest` green; `ruff format --check`, `ruff check`, `mypy
  --strict`, `lint-imports` (9) green.
- **FR6.2** No pre-existing test weakened. The **mandatory documented edits** are:
  (a) `tests/fixtures/harness_env.py` `ENTRY_SIGNAL_ENV_VARS` gains `CODEX_THREAD_ID`
  (FR1.5 safety envelope), which the autouse scrub +
  `test_ci_job_env_carries_no_entry_signal_vars` inherit; (b) any test pinning the
  retired `unresolved_runtime_preflight` stub's output is corrected with a reason
  (grep confirms none pins it directly). Both carry an inline reason comment.

---

## Non-goals
- Lifecycle engine internals (Release A, done); `agent_tier`/gitignore drift
  (Release C). No PyPI.

## Out-of-scope paths (write allowlist)
- `dadaia_workspace/core/session_env.py` (FR1.1–FR1.3)
- `dadaia_workspace/cli/commands/lock.py` (FR1.4 — `_caller_session_id` single-source)
- `dadaia_workspace/cli/commands/lifecycle.py` (FR2 preflight option, FR3 wiring)
- `dadaia_workspace/features/lifecycle/service.py` (FR3 — retire stub)
- `dadaia_workspace/container.py` (FR3 — `build_lifecycle_preflight_input` builder)
- `dadaia_workspace/cli/commands/context.py` (FR4)
- `dadaia_workspace/cli/commands/specs.py` (FR2 `specs doctor --context`)
- `dadaia_workspace/cli/_specs_resolution.py` (FR2 — if the resolver needs the ctx path, already present)
- `tests/fixtures/harness_env.py` (FR1.5 — `ENTRY_SIGNAL_ENV_VARS` envelope)
- `tests/unit/**`, `tests/integration/cli/**`, `tests/e2e/features/**` (RED-first + FR5 E2E)
- `specs/releases/v0.1.69/**`, `specs/bugs/**` (ADDITIVE), `specs/memory/**` (CLOSURE only)
