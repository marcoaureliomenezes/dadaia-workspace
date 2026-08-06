---
release: v0.1.66
---

# SPEC — v0.1.66 Layer-2 Worker Path Remediation

**Status:** Aprovado

## Objective

A remote user driving `sample-consumer v0.2.0` through `dadaia lifecycle pipeline`
hit 7 dadaia-workspace defects that made the pi AND codex Layer-2 worker paths
unusable end-to-end: a pi setup failure silently reported as a generic block, a
too-strict worker-result contract that rejected a valid worker output, an invalid
built-in OpenRouter model id, a missing codex trust flag, a codex sandbox default
that fails under container `bwrap`, a `resume` command that lies about advancing a
blocked run, and an `implement` step whose write scope structurally cannot cover
production/test paths. All 7 are registered bugs
(`specs/bugs/20260708T15Z-00.jsonl`, all `HIGH`/`MEDIUM`, all open). This release
fixes the root cause of each at its source location, with no workaround,
config-only band-aid, or test-only shim accepted as a substitute for a real fix,
and adds an observability guarantee (FR8) so a future upstream failure surfaces a
precise reason instead of collapsing into the overloaded "agent result missing
artifact evidence" message.

## Reproduction & TDD mandate — no workarounds

This is a non-negotiable release gate, binding on every FR below.

1. **RED first, on the real executed path.** For every FR, before any source fix
   lands, an executed-path test must exist that drives the **real** production
   entrypoint the user actually hit — the `dadaia lifecycle` Typer CLI command (via
   `CliRunner` + `dadaia_workspace.cli.main.app`) invoking the real
   `container.build_agent_runtime` / real `LifecycleAgentRunner` / real
   `LifecycleStateMachine` chain, with only the outermost I/O boundary faked (the
   subprocess `runner` seam for pi/codex adapters, or an injected `FakeAgentRuntime`
   result only where the FR is about engine logic downstream of the adapter, e.g.
   FR6/FR7). **Never** call the fixed helper function directly and call that
   "reproduction" — the bug that shipped `blocked_by_write_scope` as a dead-code
   check (prior release's KILLER GOTCHA) is the standing proof that a helper-level
   unit test does not prove the real invocation is fixed. The test must FAIL for
   the **exact reason the user hit it** (e.g. pi non-zero exit collapsing to
   "agent result missing artifact evidence"; `kimi-2.7` rejected as invalid by the
   allowlist-parity assertion; codex trust/sandbox failure surfaced from a faked
   `bwrap`-style stderr; `resume` exiting 0 while the run stays BLOCKED; an
   `implement` step whose faked git diff touches a production path being rejected
   as out-of-scope).
2. **Root-cause fix only.** The fix changes the defective source logic identified
   below per FR — never a try/except that swallows the failure, never a
   config-only workaround that leaves the code path broken, never a wrapper
   script, manual PATH shim, or local alias file (the exact class of workaround
   the intake reports used as a *mitigation*, e.g.
   `~/.pi/agent/models.json` alias, a `--skip-git-repo-check`-injecting PATH
   wrapper, a `--dangerously-bypass-approvals-and-sandbox` wrapper — all
   FORBIDDEN as the release's actual fix; they are exactly the workarounds this
   release exists to make unnecessary).
3. **GREEN after the fix, same test.** The identical reproduction test (not a
   rewritten weaker variant) must pass once the root-cause fix lands, in the same
   task/commit.
4. **Config-looking fixes are not exempt.** FR3 (kimi id), FR4
   (`--skip-git-repo-check`), and FR5 (sandbox default) look like one-token
   changes, but each is proven by an executed-path reproduction showing the real
   invocation was broken (OpenRouter/codex would reject the old value/missing
   flag/failing sandbox) and is fixed (the new value/flag/override reaches the
   real command construction and the adapter no longer fails for that reason) —
   never by a bare literal-value assertion alone.

Every FR's acceptance criteria below include an `AC-N(repro)` criterion in the
form: *executed-path test `<name>` FAILS on current code for reason `<X>`, PASSES
after the root-cause fix.* PLAN.md must not propose any fix that masks a failure
(swallows an exception, downgrades a real error to a generic message, or hides a
still-broken path behind a config flag defaulted to the working case only in
tests) — such a proposal is rejected at PLAN review.

## Product deltas

None. This release fixes internal lifecycle-engine defects; no product-facing
feature surface changes. The panel, CLI command surface (aside from `resume`'s
exit-code honesty and new optional flags), and memory atoms are unaffected in
scope, except as noted per-FR.

## Architecture deltas

- `infrastructure/pi_runtime.py` — corrected non-zero-exit classification (FR1).
- `infrastructure/headless_adapter_base.py` — widened (never loosened below the
  no-op-worker invariant) result-payload/ref extraction (FR2), shared by both
  `pi_runtime.py` and `codex_runtime.py` unchanged (single-source reuse
  preserved).
- `features/lifecycle/model_profiles.py` + `core/harness_models.py` — corrected
  OpenRouter model id (FR3).
- `infrastructure/codex_runtime.py` — added `--skip-git-repo-check` (FR4) and an
  env-overridable sandbox default (FR5).
- `features/lifecycle/service.py` + `cli/commands/lifecycle.py` — `resume_run`
  reports the real run status instead of unconditional OK (FR6).
- `features/lifecycle/pipeline.py` (`PipelineStep`, `_scope`) +
  `cli/commands/lifecycle.py` (new `--write-scope` option) — implement step's
  `allowed_paths` becomes the union of the handoff dir and any explicitly
  supplied extra write-scope paths (FR7).
- `features/lifecycle/agent_runner.py` — no code change required; FR8 is proven
  by executed-path tests that the existing `_blocked_result` routing (line
  183-199) now receives a precise `result.error`/`result.status` from FR1+FR2,
  plus a `detail` enrichment on the artifact-evidence block path (FR2/DEC-A(iii)).

No new cross-layer import edge: every touched module stays within its existing
layer (`infrastructure`, `features/lifecycle`, `cli`); `setup.cfg`
`[importlinter]` contracts are unaffected (verified in PLAN.md).

## Tech-stack deltas

None.

## Security/operations deltas

- FR5 introduces `DADAIA_CODEX_SANDBOX` as a new environment-variable input
  read by the codex adapter construction path. It is validated against the
  same finite set codex itself accepts (`read-only` / `workspace-write` /
  `danger-full-access`); an invalid value is rejected at construction rather
  than passed through blind. The compiled-in default remains `read-only` — no
  silent security posture downgrade for operators who do not set the override.
- FR4's `--skip-git-repo-check` addition is scoped to the already
  `--ignore-user-config` governed Layer-2 worker invocation path — this is not
  a change to Layer-1 interactive Codex sessions, which never pass
  `--ignore-user-config` and are unaffected.

## Memory files affected at closure

- `specs/memory/product/sdd/lifecycle-foundation.md` — the pi/codex adapter
  result-extraction tolerance (FR2) and the implement step's write-scope
  channel (FR7) are current-truth product behavior; the atom's summary is
  updated to reflect the corrected contract once this release ships.
- `specs/memory/product/harness/harness-pi.md` — the OpenRouter model id
  correction (FR3) touches the documented model set.
- `specs/memory/product/harness/harness-codex.md` — the `--skip-git-repo-check`
  and sandbox-override behavior (FR4/FR5) touch documented Codex headless
  invocation behavior.
- No other memory atom is affected. `catalog.json` regeneration happens at
  CLOSURE per standard protocol.

## Functional Requirements

### FR1 — pi non-zero exit reported as FAILED (bug: `pi-headless-nonzero-exit-misreported`)

`PiHeadlessAdapter._result_from_output` (`infrastructure/pi_runtime.py:187-206`)
must return `AgentRunStatus.FAILED` whenever the subprocess `returncode != 0`,
regardless of whether `stdout` is empty. The existing `run()` stderr-backfill
(lines 138-144) already threads the real (redacted) `proc.stderr`/`proc.stdout`
into `result.error` whenever `_result_from_output` returns FAILED with an empty
`error` — no additional plumbing is needed downstream of this fix.

**Acceptance criteria:**
- AC1.1: a faked pi subprocess that exits `returncode=1` with non-empty stdout
  (JSONL session/event preamble, no usable `message_end`) and non-empty stderr
  (`"No API key found for azure-openai-responses."`) yields
  `AgentRunResult(status=FAILED, error="No API key found for azure-openai-responses.")`
  — unit-level, `infrastructure/pi_runtime.py` `PiHeadlessAdapter.run`.
- AC1.2: the SAME faked-subprocess scenario, driven through the real
  `dadaia lifecycle pipeline --harness pi` CLI command (via `CliRunner` +
  `container.build_agent_runtime` with only `subprocess.run` faked at the
  adapter boundary — not the adapter's `run()` method itself), blocks with a
  reason containing the real stderr text, NOT the generic
  `"agent result missing artifact evidence"` string.
- **AC1(repro):** executed-path test `test_pi_pipeline_surfaces_real_setup_failure_not_generic_block`
  FAILS on current code (asserts block reason contains `"No API key found"`; on
  current code the block reason is `"agent result missing artifact evidence"`,
  so the assertion fails), PASSES after the `_result_from_output` guard fix.
- AC1.3 (regression guard): `test_pi_adapter_nonzero_exit_with_no_output_returns_failed`
  (the pre-existing empty-stdout pinning test) still passes unmodified — the fix
  only widens the FAILED condition, it does not change behavior for the
  already-correct empty-stdout case.

### FR2 — tolerant worker-result contract, no-op invariant preserved (bug: `lifecycle-agent-run-result-extraction-too-strict`)

`headless_adapter_base.classify_result_payload` and `normalize_artifact_refs`
(`infrastructure/headless_adapter_base.py:85-148`) must accept, in addition to
the current strict/structural `artifact_refs`-list contract:
(i) `schema_version` as an equivalent label to `schema` for STRICT
classification; (ii) a singular `payload["artifact"]["path"]` as a one-element
`artifact_refs` fallback when the list-based extraction yields nothing.

**What MUST still block (invariant — non-negotiable):** a genuine no-op worker
— no fenced or bare JSON result object present at all (`extract_result_payload`
returns `None`) — MUST continue to yield empty `artifact_refs` and BLOCK exactly
as today. `test_pi_noop_worker_yields_empty_artifact_refs` and
`test_pi_adapter_bare_json_without_result_shape_is_rejected` (both pre-existing,
`tests/unit/infrastructure/test_pi_runtime.py:717,471`) MUST pass unmodified —
neither test is edited by this release. Widening (i)/(ii) only ever accepts a
payload that genuinely IS a result object with real content; it never turns
"nothing emitted" into "something accepted."

**Acceptance criteria:**
- AC2.1: `classify_result_payload({"schema_version": "agent-run-result-v1", ...}, "agent-run-result-v1")`
  returns `ResultMatch.STRICT` — unit-level.
- AC2.2: `normalize_artifact_refs({"artifact": {"type": "other", "path": "repos/x/f.py"}})`
  (no `artifact_refs` key at all) returns `("repos/x/f.py",)` — unit-level.
- AC2.3: `normalize_artifact_refs({"artifact_refs": [...], "artifact": {...}})`
  (both present) returns the `artifact_refs` list content unchanged — the
  singular-`artifact` fallback never overrides populated list content.
- AC2.4 (invariant guard): `test_pi_noop_worker_yields_empty_artifact_refs` and
  `test_pi_adapter_bare_json_without_result_shape_is_rejected` pass unmodified
  (byte-identical test source) after this FR's change.
- **AC2(repro):** executed-path test
  `test_pi_pipeline_accepts_schema_version_and_singular_artifact_result`
  FAILS on current code (the pipeline blocks at `implement` with "agent result
  missing artifact evidence" when the faked pi worker emits
  `{"schema_version": "agent-run-result-v1", "artifact": {"path": "..."}}"`),
  PASSES after the fix (the same faked worker output now advances the step).
- **AC2(repro-negative):** executed-path test
  `test_pi_pipeline_still_blocks_on_genuine_noop_worker` PASSES on current code
  AND continues to PASS after the fix (a faked pi worker that emits only prose,
  no JSON result object at all, still blocks with
  "agent result missing artifact evidence") — proves the invariant survives the
  fix, driven through the real CLI.

### FR3 — valid OpenRouter kimi model id (bug: `pi-openrouter-kimi-profile-invalid-model-id`)

Replace the invalid literal `"kimi-2.7"` with the OpenRouter-valid
`"moonshotai/kimi-k2.5"` in all 3 coordinated locations:
`features/lifecycle/model_profiles.py:102-103` (`model_id` + `label`),
`core/harness_models.py:75` (`HarnessModelOption` in the PI options tuple),
`core/harness_models.py:99` (`LAYER2_EXTRA_MODEL_IDS` allowlist).

**Acceptance criteria:**
- AC3.1: `model_profiles.resolve("pi-openrouter-kimi-high").model_id == "moonshotai/kimi-k2.5"`.
- AC3.2: `"moonshotai/kimi-k2.5"` is a member of `harness_models.options_for("pi")`
  and of `LAYER2_EXTRA_MODEL_IDS` (the no-second-table guard stays green — the
  profile resolves to a real, single-sourced catalog option, not a drifting
  duplicate).
- AC3.3: the pre-existing pinning test
  `test_openrouter_kimi_profile_is_a_governed_pi_option`
  (`tests/unit/features/lifecycle/test_model_profiles.py:101-119`) is updated in
  the SAME commit to assert the new id — this is a deliberate pin update (the
  old pinned value was itself the bug), not a silent weakening.
- **AC3(repro):** executed-path test
  `test_pi_openrouter_kimi_profile_reaches_command_with_valid_id` FAILS on
  current code (drives `dadaia lifecycle pipeline --harness pi --step-model implement=pi-openrouter-kimi-high`
  through the real CLI with a faked `subprocess.run` that asserts the argv's
  `--model` value; on current code the faked runner receives literal
  `kimi-2.7` and the test's assertion that the value is prefixed
  `moonshotai/` fails), PASSES after the fix (the faked runner's captured argv
  carries `moonshotai/kimi-k2.5`). This proves the real command construction
  path, not just the profile registry in isolation.

### FR4 — codex adapter passes `--skip-git-repo-check` (bug: `codex-exec-adapter-missing-skip-git-repo-check`)

`CodexExecAdapter._command` (`infrastructure/codex_runtime.py:186-208`) must
include `"--skip-git-repo-check"` in the fixed argv, unconditionally, alongside
the existing `--ignore-user-config`.

**Acceptance criteria:**
- AC4.1: `CodexExecAdapter._command(...)` includes `"--skip-git-repo-check"` in
  its returned argv list — unit-level.
- **AC4(repro):** executed-path test
  `test_codex_pipeline_untrusted_dir_no_longer_blocks_on_trust_error` FAILS on
  current code (drives `dadaia lifecycle pipeline --harness codex` through the
  real CLI with a faked `subprocess.run` that returns
  `returncode=1, stderr="Not inside a trusted directory and --skip-git-repo-check was not specified."`
  whenever the captured argv does NOT contain `--skip-git-repo-check` — on
  current code the argv omits the flag, so the fake returns the trust error and
  the pipeline blocks with that reason), PASSES after the fix (the argv now
  carries the flag, the fake returns success, the step advances).

### FR5 — codex sandbox override for constrained containers (bug: `codex-exec-sandbox-default-fails-in-container`)

Add an env-var override `DADAIA_CODEX_SANDBOX` read at the point
`CodexExecConfig`/`CodexExecAdapter` construction resolves its `sandbox` value
(the container-wiring call site in `container.py` and/or `CodexExecConfig`
itself). When set to one of `read-only` / `workspace-write` /
`danger-full-access`, it overrides the compiled-in default; an unrecognized
value is rejected at construction (fail loud, not silently ignored). The
compiled-in default stays `read-only` when the env var is unset.

**Acceptance criteria:**
- AC5.1: with `DADAIA_CODEX_SANDBOX=workspace-write` set, the constructed
  `CodexExecConfig`/adapter's resolved `sandbox` is `"workspace-write"` —
  unit-level.
- AC5.2: with `DADAIA_CODEX_SANDBOX` unset, the resolved `sandbox` remains
  `"read-only"` (no behavior change for the unset case) — unit-level regression
  guard.
- AC5.3: with `DADAIA_CODEX_SANDBOX=not-a-real-value` set, construction raises
  a clear, actionable error (not a silent pass-through to `codex exec`) —
  unit-level.
- **AC5(repro):** executed-path test
  `test_codex_pipeline_sandbox_override_avoids_container_bwrap_failure` FAILS
  on current code (drives `dadaia lifecycle pipeline --harness codex` through
  the real CLI with a faked `subprocess.run` that returns
  `returncode=1, stderr="bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"`
  whenever the captured argv's `--sandbox` value is `read-only` — on current
  code, with `DADAIA_CODEX_SANDBOX=workspace-write` set in the test's env, the
  argv STILL carries `read-only` because nothing reads the env var, so the fake
  returns the bwrap failure and the pipeline blocks), PASSES after the fix (the
  env var reaches the argv as `--sandbox workspace-write`, the fake returns
  success, the step advances).

### FR6 — `resume` reports the real run status (bug: `lifecycle-resume-reports-ok-without-advancing`)

`LifecyclePreflightService.resume_run` (`features/lifecycle/service.py:210-222`)
must inspect the loaded run's persisted status/blocked-state after
`run_store.resume(run_id)`. If the run's `status` is
`LifecycleRunStatus.BLOCKED`, `resume_run` returns a `LifecycleCommandResult`
with `status=LifecycleCommandStatus.BLOCKED` and a `message` that surfaces the
run's own `blocked.reason` — never the unconditional `OK`. The
`resume` CLI command (`cli/commands/lifecycle.py:289-297`) routes this result
through the existing `_emit_command_result`/`_exit_for_command_result` path
(the same generic mechanism other verbs already use), so a resume of a still-
blocked run exits non-zero.

**Acceptance criteria:**
- AC6.1: `resume_run` on a persisted run with `status=BLOCKED` and
  `blocked.reason="agent result missing artifact evidence"` returns
  `LifecycleCommandResult(status=BLOCKED, message` containing that reason) —
  unit-level, `features/lifecycle/service.py`.
- AC6.2: `resume_run` on a persisted run with `status` NOT `BLOCKED` (e.g.
  `RUNNING`/`COMPLETED`) still returns `OK` — no regression for the
  already-correct non-blocked case.
- **AC6(repro):** executed-path test `test_lifecycle_resume_cli_exits_nonzero_on_still_blocked_run`
  FAILS on current code (drives `dadaia lifecycle resume <run_id>` through the
  real CLI against a fixture run state file persisted with `status=BLOCKED`;
  asserts `result.exit_code != 0` and the output contains the real block
  reason — on current code `exit_code == 0` and the output is
  `"OK resumed <id>"`, so the assertion fails), PASSES after the fix.

### FR7 — implement step write scope covers the reserved task (bug: `lifecycle-implement-step-write-scope-too-narrow`)

`LifecyclePipeline._scope` (`features/lifecycle/pipeline.py:492-515`) hardcodes
`allowed_paths=(f".dadaia/handoff/{context}/**",)` for every step, including
`implement`, which structurally prevents an implement worker from legally
editing any production/test path. Per DEC-C (grill refinement,
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-08T153000Z-refine-v0166.html`):
add an additive-optional `PipelineStep.extra_allowed_paths: tuple[str, ...] = ()`
field and a new repeatable `--write-scope PATH` CLI option on the `implement`
and `pipeline` commands. `_scope` computes `allowed_paths` for the `implement`
step (only) as the union of the existing handoff-dir glob and
`step.extra_allowed_paths`; review steps (`review_qa`/`review_security`/
`review_code`) keep the handoff-only scope unchanged — they must never gain
production write rights.

A full TASKS.md-derived write-set parser is explicitly OUT OF SCOPE for this
release (see Open Questions / backlog follow-ups) — this FR builds the
plumbing and the union computation; the operator supplies the paths via
`--write-scope` per invocation.

**Acceptance criteria:**
- AC7.1: `PipelineStep(..., extra_allowed_paths=("repos/x/src/**",))` fed into
  `_scope` for the `implement` step yields `allowed_paths` containing both
  `.dadaia/handoff/<context>/**` and `repos/x/src/**` — unit-level.
- AC7.2: the same `extra_allowed_paths` value fed into a `review_qa`-labeled
  step is IGNORED — `_scope`'s union only applies to `implement` — regression
  guard proving review steps stay handoff-only.
- **AC7(repro):** executed-path test
  `test_implement_pipeline_write_scope_covers_reserved_task_production_path`
  FAILS on current code (drives `dadaia lifecycle pipeline --harness fake
  --write-scope repos/sample-consumer/docker/sample-capture/**` through the
  real CLI with an injected `FakeAgentRuntime` result whose
  `structured_output["changed_paths"]` includes
  `repos/sample-consumer/docker/sample-capture/Dockerfile` — on current code
  the gate's `out_of_scope_paths` check rejects that path because
  `allowed_paths` is handoff-only, so the pipeline blocks with
  `"agent result contains out-of-scope paths"`), PASSES after the fix (the
  `--write-scope` value reaches `allowed_paths`, the changed path is in-scope,
  the step advances).

### FR8 — precise upstream failure reaches the operator (observability NFR, cross-cutting)

The block reason `"agent result missing artifact evidence"`
(`features/lifecycle/agent_runner.py:198-199`) must not be the ONLY signal an
operator sees when the true cause is a distinct upstream failure. The routing
that makes this possible already exists at `_blocked_result`
(`agent_runner.py:183-199`): when `result.status is not SUCCEEDED`, the block
reason is `result.error or result.summary` (line 190) — a real, non-generic
reason — rather than falling into the `not result.artifact_refs` branch
(reached only when `status IS SUCCEEDED`). FR8 requires no new routing code; it
requires (a) FR1 and FR2 to correctly populate `result.status`/`result.error`
so this existing routing carries a precise reason, and (b) per DEC-A(iii), the
`"agent result missing artifact evidence"` block's `detail` dict (already
`dict[str, str]`-typed, precedent at line 209's `out_of_scope` detail) is
enriched with a `validated_handoff_path` key when a well-formed, independently
validating handoff file exists in `.dadaia/handoff/<context>/` for the current
step's context/agent naming convention, even though the gate still blocks (this
never turns a genuine no-op worker into a pass — see FR2's invariant).

**Acceptance criteria:**
- AC8.1: a pi worker that fails per FR1 (non-zero exit, real stderr) surfaces
  a block reason containing the real stderr text end-to-end through the CLI —
  covered by AC1(repro); no separate test needed, cited here as the FR8 proof
  for the pi-setup-failure case.
- AC8.2: a codex worker that fails per FR4/FR5 surfaces a block reason
  containing the real codex stderr (trust error / bwrap error) end-to-end
  through the CLI — covered by AC4(repro)/AC5(repro); cited here as the FR8
  proof for the codex-adapter-failure case.
- **AC8(repro):** executed-path test
  `test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty`
  FAILS on current code (drives the real CLI with a faked worker result that
  has empty `artifact_refs` but a genuinely valid, pre-written handoff file on
  disk at the expected path; asserts `blocked.detail["validated_handoff_path"]`
  equals that path — on current code `detail` is `{}`, so the assertion fails),
  PASSES after the DEC-A(iii) enrichment lands. The test also asserts the run
  is STILL blocked (`status == BLOCKED`) — this AC never converts a block into
  a pass.

## AC-MUT — mutation-sanity

For every FR's unit-level ACs above (AC1.1, AC2.1-2.3, AC3.1-3.2, AC4.1,
AC5.1-5.3, AC6.1-6.2, AC7.1-7.2), a deliberate mutation of the fixed condition
(e.g. reverting FR1's guard to `and not text`, reverting FR3's id literal,
removing FR4's argv token, reverting FR6's status check) must make the
corresponding unit test FAIL. This is proven during PLAN/TASKS execution by
briefly reverting each fix locally, re-running the affected unit test, and
confirming a failure, then re-applying the fix — recorded as evidence in the
task's completion note (not a permanent CI mutation-testing harness; a
one-time proof-of-bite check per fixed condition, consistent with the AC-7
mutation-sanity practice this workspace already applies to prior releases).
This does not replace the RED-first executed-path mandate above — it is
additional proof that the unit-level ACs are not vacuously true (e.g. a test
that asserts something so loose it would pass even against the old broken
code).

## Out of scope

- A full TASKS.md write-set declaration syntax + parser (FR7 builds only the
  plumbing + an explicit `--write-scope` CLI channel; see backlog follow-up
  `lifecycle-tasks-md-write-set-parser`).
- `resume` actually re-driving/re-invoking a blocked step's worker (FR6 only
  makes the reported status honest; see backlog follow-up
  `lifecycle-resume-redrive-blocked-step`).
- Codex sandbox capability auto-detection/probing (FR5 is an explicit env
  override only; see backlog follow-up `codex-exec-sandbox-capability-probe`).
- Any change to the Claude SDK adapter (`claude_sdk_runtime.py`) — out of
  scope; claude is never a Layer-2 worker (constitution law), unaffected by
  this release.
- Any panel UI change.

## Open Questions

None outstanding. All design decisions (DEC-A..D) were resolved by source
inspection and recorded with an adopted recommendation in the grill refinement
report:
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-08T153000Z-refine-v0166.html`.

## Dependencies and risks

- **Dependency:** none on other in-flight releases; `ACTIVE.md` shows no prior
  release blocking this one (`release: none` before this SPEC).
- **Risk — FR2 over-acceptance.** The primary risk of this release is a
  regression that makes the create-step gate accept a genuine no-op worker.
  Mitigated by: (a) the explicit non-negotiable invariant in FR2's own text;
  (b) AC2.4 requiring the two existing invariant-pinning tests to pass
  UNMODIFIED; (c) AC2(repro-negative) proving the invariant survives at the
  executed-path level, not just the unit level.
- **Risk — FR3 id drift.** `moonshotai/kimi-k2.5` is the operator-verified
  working id from the intake's local workaround, but OpenRouter's catalog may
  rename/deprecate ids over time. Out of scope to build id-liveness probing;
  AC3.3's pin update is the tracked contract — a future OpenRouter-side
  deprecation is a new bug, not a defect of this release.
- **Risk — FR5 sandbox override misuse.** `workspace-write`/
  `danger-full-access` widen codex's write/network access. Mitigated by: the
  outer `dadaia lifecycle` gate (`allowed_paths`/review gates) remaining the
  real security boundary regardless of codex's own sandbox setting (same
  reasoning as FR4's `--skip-git-repo-check`), and by the default remaining
  `read-only` when the override is unset (AC5.2).
- **Risk — executed-path test flakiness from faked subprocess boundaries.**
  Mitigated by following the exact pre-existing pattern in
  `tests/integration/cli/test_lifecycle_pipeline_full.py` and
  `tests/unit/features/lifecycle/test_pi_runner_ring2.py` (fake the `Runner`/
  `subprocess.run` seam only, drive everything above it for real) rather than
  inventing a new test-double mechanism.
