# TASKS — Release v0.1.69 — Context Resolution, Session Observability & CLI Surface

> **Status:** Aprovado
> **Release ID:** v0.1.69
> **Owner:** product-engineer

Marker contract: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. RED-first: commit the
failing proof, confirm it fails on current code, THEN implement the fix.

> **Revision (software-architect REVIEW, folded pre-implementation):** F1a added
> `lock.py` `_caller_session_id` to Wave A; F1b added the mandatory
> `ENTRY_SIGNAL_ENV_VARS` safety-envelope extension; F2 scoped `--context` to
> `preflight`+`specs doctor` only (not `status`/`handoffs doctor`, which are
> workspace-global); F3 expanded from "wire the stub" to building the
> preflight-input probe assembly (`build_lifecycle_preflight_input`) with per-producer
> RED tests. See SPEC Revision.

---

## Wave A — FR1: recognize CODEX_THREAD_ID (CRITICAL)

### T-69-01 — RED: CODEX_THREAD_ID not recognized `[x]`
- **Owner:** software-engineer
- **Write set:** `tests/unit/core/test_session_env.py` (additive cases)
- **Task:** With `CODEX_SESSION_ID` unset + `CODEX_THREAD_ID` set: assert
  `harness_session_id()` returns the thread id and `entry_harness() == "codex"`.
  CONFIRM RED (both None today).
- **AC:** SPEC AC1(repro) RED half, AC1.1.

### T-69-02 — GREEN: add CODEX_THREAD_ID at the single source + lock.py + envelope `[x]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/session_env.py`,
  `dadaia_workspace/cli/commands/lock.py`,
  `tests/fixtures/harness_env.py`
- **Preconditions:** T-69-01 `[x]`
- **Task:** (FR1.1–1.3) Append `"CODEX_THREAD_ID"` to `HARNESS_SESSION_ID_ENV_VARS`
  after `CODEX_SESSION_ID`; extend `entry_harness()` to accept `CODEX_SESSION_ID` OR
  `CODEX_THREAD_ID`. (FR1.4) Route `lock.py` `_caller_session_id()` through
  `harness_session_id()` (preserving the `DADAIA_SESSION_ID` override) or add
  `CODEX_THREAD_ID` to its tuple. (FR1.5 SAFETY) Add `"CODEX_THREAD_ID"` to
  `tests/fixtures/harness_env.py` `ENTRY_SIGNAL_ENV_VARS` with an inline reason
  comment. Re-run T-69-01 → GREEN. Add AC1.2 (both set ⇒ CODEX_SESSION_ID wins). Full
  suite green (incl. `test_ci_job_env_carries_no_entry_signal_vars`), 0 unrelated edits.
- **AC:** SPEC AC1.1, AC1.2, FR1.4, FR1.5, AC1(repro) GREEN half.

### T-69-03 — Integration: bind persists thread-keyed record, resolver attributes it `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_codex_thread_id_bind.py` (new)
- **Preconditions:** T-69-02 `[x]`
- **Task:** With only `CODEX_THREAD_ID` set in a `tmp_path` workspace, run `context
  bind` and assert a session record keyed to the thread id exists and a resolver call
  attributes the bound context without `--specs-dir`.
- **AC:** SPEC AC1.3.

## Wave B — FR2: --context on preflight + specs doctor (load-bearing only)

### T-69-04 — RED: preflight + specs doctor reject --context `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_diagnostic_context_option.py` (new)
- **Task:** CliRunner: `preflight --context <ctx> --release-id <rel>` and
  `specs doctor --context <ctx>` exit 2 ("No such option") today. CONFIRM RED. Also
  assert (positive control) `status`/`handoffs doctor` remain workspace-global — no
  `--context` (AC2.3), documenting the F2 decision.
- **AC:** SPEC AC2(repro) RED half, AC2.3.

### T-69-05 — GREEN: add --context/--release-id to preflight + specs doctor `[ ]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `dadaia_workspace/cli/commands/specs.py`
- **Preconditions:** T-69-04 `[x]`
- **Task:** Add `--context`+`--release-id` to `preflight`; add `--context` to
  `specs doctor` (via `resolve_specs_dir_for_cli`, mutually exclusive with
  `--specs-dir`). Do NOT touch `status`/`handoffs doctor`. Re-run T-69-04 → GREEN.
- **AC:** SPEC AC2.1, AC2.2, AC2.3, AC2(repro) GREEN half.

## Wave C — FR3: preflight-input probe assembly + wire real preflight

### T-69-06 — RED: preflight returns the inert stub; probe builder absent `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/unit/features/lifecycle/test_preflight_input_builder.py` (new),
  `tests/integration/cli/test_preflight_real_wiring.py` (new)
- **Preconditions:** T-69-05 `[x]`
- **Task:** Assert `preflight --context <ctx> --release-id <rel> --json` returns the
  generic "requires resolved runtime inputs" stub today (spy: `service.preflight`
  never called). Add per-producer RED unit tests referencing the not-yet-existing
  `build_lifecycle_preflight_input` (import error / absent). CONFIRM RED.
- **AC:** SPEC AC3(repro) RED half, AC3.1 (stub-never side).

### T-69-07 — GREEN: build_lifecycle_preflight_input + wire, retire stub `[ ]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `dadaia_workspace/features/lifecycle/service.py`,
  `dadaia_workspace/cli/commands/lifecycle.py`
- **Preconditions:** T-69-06 `[x]`
- **Task:** Add `build_lifecycle_preflight_input(workspace_root, context, release_id)`
  composing state producers from EXISTING readers (active-release ← ACTIVE.md; git ←
  git adapter; specs-doctor ← specs-doctor service; lease/mode ← session_identity;
  hygiene ← `build_lifecycle_hygiene_service().status()`; bound context ← binding
  reader) + `expected_phase`/`required_mode` policy from ACTIVE.md phase. Wire
  `preflight` CLI to `service.preflight(data)`; retire `unresolved_runtime_preflight`
  (grep confirms `lifecycle.py:246` sole caller). Blocked ⇒ specific reason + non-null
  `operator_command`. Re-run T-69-06 → GREEN.
- **AC:** SPEC AC3.1, AC3.2 (via FR3.2/3.3), AC3(repro) GREEN half.

## Wave D — FR4: context show reads the incumbent pointer

### T-69-08 — RED: bind not reflected in show `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_context_show_reflects_bind.py` (new)
- **Task:** `tmp_path` workspace, `DADAIA_SESSION_ID` unset: `context bind <ctx>
  --mode implementation --release <rel>`, then `context show <ctx> --json` — assert
  `session` is `null` today. CONFIRM RED.
- **AC:** SPEC AC4(repro) RED half.

### T-69-09 — GREEN: show falls back to incumbent pointer `[ ]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/context.py`
- **Preconditions:** T-69-08 `[x]`
- **Task:** In `show`, when `DADAIA_SESSION_ID` absent, resolve via
  `session_identity.read_incumbent_ptr` (or `resolve_identity`), load + stale-check
  (`_load_session`/`_session_is_stale`), populate `data["session"]`. Env → pointer
  order; stale/absent ⇒ `null`. Re-run T-69-08 → assert bound sid appears. Full green.
- **AC:** SPEC AC4.1, AC4(repro) GREEN half.

## Wave E — FR5 + FR6: E2E + validation

### T-69-10 — E2E: a bound context is visible to the CLI `[ ]`
- **Owner:** software-engineer
- **Write set:** `tests/e2e/features/test_bound_context_visible_to_cli.py` (new)
- **Preconditions:** T-69-02, T-69-05, T-69-09 `[x]`
- **Task:** Provision a `tmp_path` workspace + context, bind it (no
  `DADAIA_SESSION_ID`), assert `context show --json` reflects the bind (FR4) and
  `preflight --context` targets it / resolves its specs (FR2). Hermetic.
- **AC:** SPEC AC5.1.

### T-69-11 — QA validation + gate green `[ ]`
- **Owner:** qa-engineer
- **Write set:** none (ADDITIVE handoff only)
- **Preconditions:** T-69-10 `[x]`
- **Task:** Full `pytest -p no:cacheprovider`, ruff format+check, `mypy --strict`,
  `lint-imports` (9). Mutation-sanity on FR1/FR3/FR4 tests. Confirm the
  `ENTRY_SIGNAL_ENV_VARS` guard still neutralizes `CODEX_THREAD_ID`
  (`test_ci_job_env_carries_no_entry_signal_vars` green). No pre-existing test
  weakened. Emit QA handoff.
- **AC:** SPEC AC-FR6.1, FR6.2.
