# PLAN — v0.1.66 Layer-2 Worker Path Remediation

**Status:** Aprovado

## Strategy

Fix 7 root-cause defects across the Layer-2 worker adapters (`pi`, `codex`) and
the lifecycle engine (`resume`, `implement` write scope), each proven by a
RED-first executed-path test per the SPEC's non-negotiable "Reproduction & TDD
mandate." No fix may be a workaround, config band-aid, or test-only shim — the
mandate rejects any PLAN step that masks a failure instead of removing its
cause. Work proceeds in 3 waves, ordered cheapest-risk-first, each wave
independently shippable (green CI at every task boundary per
`release-governance`'s "never push red" law):

1. **Wave A — trivial-looking but repro-proven config fixes** (FR3, FR4, FR5):
   one literal / one argv token / one env override each, but EVERY task still
   opens with an executed-path RED reproduction proving the real invocation was
   broken, per the mandate's explicit carve-out closing that loophole.
2. **Wave B — pi/codex result-contract fixes** (FR1, FR2, FR8): the adapter
   non-zero-exit classification and the shared result-extraction tolerance,
   plus the FR8 observability proof that ties FR1+FR2 to the existing
   `_blocked_result` routing.
3. **Wave C — engine-level fixes** (FR6, FR7): `resume` status honesty and the
   `implement` step's write-scope union.
4. **QA wave** — executed-path re-verification of the full AC/AC-MUT matrix,
   plus the golden pipeline-to-CLOSURE regression test
   (`test_pipeline_runs_to_closure_on_fake`) to prove no wave broke the happy
   path.

## Layers affected

| Layer | Modules touched | New cross-layer edge? |
|---|---|---|
| `infrastructure` | `pi_runtime.py`, `codex_runtime.py`, `headless_adapter_base.py` | No — all 3 already exist in this layer; no new imports added. |
| `features/lifecycle` | `service.py`, `pipeline.py`, `model_profiles.py` | No — all 3 already exist in this layer. |
| `core` | `harness_models.py` (data-only literal change) | No — pure constant edit, no new import. |
| `cli` | `commands/lifecycle.py` (`resume` exit routing, new `--write-scope` option) | No — `cli` already depends on `features.lifecycle` and `container`. |
| `container` | `container.py` (env-var read for FR5's sandbox override, if resolved at the container-wiring call site rather than inside `CodexExecConfig`) | No — `container` already wires `infrastructure` adapters. |

**Import-linter safety (verified against `setup.cfg` `[importlinter]`
contracts before writing this PLAN):**
- `features-no-infrastructure` (features must not import infrastructure
  directly): FR1/FR2/FR4/FR5 stay entirely inside `infrastructure/`. FR3 stays
  inside `features/lifecycle/model_profiles.py` + `core/harness_models.py`
  (no infrastructure import). FR6/FR7 stay inside
  `features/lifecycle/{service,pipeline}.py` (no new infrastructure import —
  `pipeline.py` already imports only from `core`/`features.lifecycle`). No new
  edge.
- `infrastructure-no-upper-layers`: none of FR1/FR2/FR4/FR5's edits add an
  import of `features`/`cli`/`hooks` into `infrastructure/`. No new edge.
- `lifecycle-no-workflows`: none of the touched `features/lifecycle/*` modules
  import `features.workflows`. No new edge.
- `cli-no-infrastructure`: FR6/FR7's `cli/commands/lifecycle.py` edits call
  existing `container`/`features.lifecycle` functions only — no direct
  `infrastructure` import added to `cli/`.
- Net ignore-edge count in `setup.cfg` (`features-no-infrastructure` /
  `features-no-subprocess` ignore lists) is UNCHANGED — this release adds zero
  new ignored edges. Confirmed by re-running `lint-imports` locally after each
  wave (task-level AC in TASKS.md).

## Execution order (per wave, task IDs match TASKS.md)

### Wave A — T-66-01..T-66-03 (parallel-safe, disjoint files)

- **T-66-01 (FR3):** `features/lifecycle/model_profiles.py:102-103`,
  `core/harness_models.py:75,99`. RED: executed-path test asserting the real
  argv captured by a faked `subprocess.run` carries `moonshotai/kimi-k2.5`
  when `--step-model implement=pi-openrouter-kimi-high` is passed to
  `dadaia lifecycle pipeline --harness pi`. Fix: literal swap in 3 locations +
  `label` string. Update the pre-existing pin
  (`tests/unit/features/lifecycle/test_model_profiles.py:101-119`) in the same
  commit.
- **T-66-02 (FR4):** `infrastructure/codex_runtime.py:186-208` `_command`.
  RED: executed-path test with a faked `subprocess.run` that returns the real
  codex trust-error stderr whenever `--skip-git-repo-check` is absent from the
  captured argv. Fix: add the token.
- **T-66-03 (FR5):** `infrastructure/codex_runtime.py:64-79`
  (`CodexExecConfig`) + `container.py` codex-adapter construction site. RED:
  executed-path test with a faked `subprocess.run` that returns the real
  bwrap-failure stderr whenever `--sandbox` in the captured argv is
  `read-only`, run with `DADAIA_CODEX_SANDBOX=workspace-write` set and
  asserting failure on current code. Fix: read `DADAIA_CODEX_SANDBOX`,
  validate against the 3-value finite set, override `sandbox`; default stays
  `read-only` when unset.

Write sets are disjoint (T-66-01 touches `model_profiles.py`/
`harness_models.py`; T-66-02/T-66-03 both touch `codex_runtime.py` but
different regions — `_command`'s argv list vs `CodexExecConfig`'s default/env
read — TASKS.md sequences them serially within Wave A to avoid a merge
collision on the same file, not because they are logically dependent).

### Wave B — T-66-04..T-66-06 (serial: T-66-05 builds on T-66-04's test scaffolding)

- **T-66-04 (FR1):** `infrastructure/pi_runtime.py:187-206`
  `_result_from_output`. RED: unit test (AC1.1) + executed-path test (AC1
  repro) per SPEC. Fix: `if returncode != 0 and not text:` →
  `if returncode != 0:` (drop the `and not text` conjunct), returning FAILED
  with `error=""` so `run()`'s existing stderr-backfill (lines 138-144) fires.
  Regression guard: AC1.3 (`test_pi_adapter_nonzero_exit_with_no_output_returns_failed`
  unmodified, still green).
- **T-66-05 (FR2):** `infrastructure/headless_adapter_base.py:85-148`
  (`classify_result_payload`, `normalize_artifact_refs`). RED: unit tests
  (AC2.1-2.3) + executed-path tests (AC2 repro, AC2 repro-negative). Fix:
  (i) `payload.get("schema") or payload.get("schema_version")` for STRICT
  label comparison; (ii) `normalize_artifact_refs` falls back to a singular
  `payload["artifact"]["path"]` only when the list-based extraction is empty.
  Invariant guard: AC2.4 — `test_pi_noop_worker_yields_empty_artifact_refs`
  and `test_pi_adapter_bare_json_without_result_shape_is_rejected` MUST remain
  byte-identical and green; task fails if either file is touched.
- **T-66-06 (FR8):** `features/lifecycle/agent_runner.py` — no source change
  to `_blocked_result` logic; add a `detail={"validated_handoff_path": ...}`
  enrichment on the `not result.artifact_refs` block branch (line 198-199)
  per DEC-A(iii): look up a matching, independently-validating handoff file
  under `.dadaia/handoff/<context>/` for the step's context/agent naming
  convention when refs are empty. RED: executed-path test (AC8 repro) with a
  pre-written valid handoff fixture + a faked worker with empty
  `artifact_refs`; asserts the block's `detail` carries the path AND the run
  is still BLOCKED. AC8.1/AC8.2 are satisfied by T-66-04/T-66-02+03's own
  repro tests (cited, not re-implemented).

### Wave C — T-66-07..T-66-08 (parallel-safe, disjoint files)

- **T-66-07 (FR6):** `features/lifecycle/service.py:210-222` `resume_run` +
  `cli/commands/lifecycle.py:289-297` `resume`. RED: unit test (AC6.1-6.2) +
  executed-path test (AC6 repro) driving the real `dadaia lifecycle resume`
  CLI against a fixture run persisted with `status=BLOCKED`. Fix: `resume_run`
  branches on the loaded run's status; routes the `resume` CLI command through
  the existing `_emit_command_result`/`_exit_for_command_result` machinery
  (no new exit-code convention).
- **T-66-08 (FR7):** `features/lifecycle/pipeline.py:75-105` (`PipelineStep`),
  `:492-515` (`_scope`) + `cli/commands/lifecycle.py` (new `--write-scope`
  option on `implement` and `pipeline` commands). RED: unit tests
  (AC7.1-7.2) + executed-path test (AC7 repro) with an injected `FakeAgentRuntime`
  result whose `changed_paths` includes a production file path, proving the
  gate blocks on current code and passes once `--write-scope` reaches
  `allowed_paths` for the `implement` step only.

Wave C's two tasks are disjoint (`service.py`+CLI resume command vs
`pipeline.py`+CLI implement/pipeline commands — the CLI file overlaps but in
non-adjacent regions; TASKS.md sequences them serially to avoid a merge
collision on `cli/commands/lifecycle.py`).

### QA wave — T-66-09

`qa-engineer` re-runs every AC(repro) test listed in SPEC.md end-to-end against
the final Wave-A/B/C state, re-runs the full existing lifecycle test suite
(`tests/unit/features/lifecycle/`, `tests/unit/infrastructure/test_pi_runtime.py`,
`tests/integration/cli/test_lifecycle_*.py`) to prove zero regressions,
re-runs `lint-imports` to confirm the import-linter safety claims above, and
performs the one-time AC-MUT proof-of-bite pass (briefly revert each fixed
condition, confirm the corresponding unit test fails, re-apply).

## Test plan

**Unit-level.** Standard `pytest` unit tests colocated with existing suites:
`tests/unit/infrastructure/test_pi_runtime.py` (FR1, FR2's pi-side),
`tests/unit/infrastructure/test_headless_adapter_base.py` (FR2, shared),
`tests/unit/infrastructure/test_codex_exec_runtime.py` (FR4, FR5),
`tests/unit/features/lifecycle/test_model_profiles.py` (FR3),
`tests/unit/features/lifecycle/test_lifecycle_service.py` or equivalent (FR6),
`tests/unit/features/lifecycle/test_pipeline.py` (FR7).

**Executed-path E2E — the SPEC's mandatory reproduction tests.** New tests
added to `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or a new
sibling file `test_lifecycle_pipeline_v0166_repro.py` if the existing file
would grow unwieldy — task-level judgment call, not a PLAN decision) following
the exact pre-existing pattern in that file and in
`tests/integration/cli/test_lifecycle_pipeline_full.py`: `CliRunner` +
`dadaia_workspace.cli.main.app`, real `container.build_agent_runtime`, with
ONLY the `subprocess.run` seam faked via
`monkeypatch.setattr("dadaia_workspace.infrastructure.<pi_runtime|codex_runtime>.subprocess.run", fake_run)`
(the proven pattern from `test_pipeline_runs_first_step_on_pi_harness_end_to_end`,
lines 63-126 of that file) for FR1/FR2/FR3/FR4/FR5/FR8, or an injected
`FakeAgentRuntime(result=...)` via the `container.build_agent_runtime`
monkeypatch (the proven pattern from `test_pipeline_runs_to_closure_on_fake`,
`test_lifecycle_pipeline_full.py` lines 75-156) for FR6/FR7 where the engine
logic under test is downstream of the adapter boundary. Every executed-path
test is named exactly as SPEC.md's `AC-N(repro)` criteria specify, so
traceability from SPEC → test is by name, not by inference.

**Golden regression.** `test_pipeline_runs_to_closure_on_fake`
(`test_lifecycle_pipeline_full.py`) re-run unmodified at the QA wave — proves
none of the 8 FRs' changes broke the happy-path ladder to `CLOSURE`.

## Risks

See SPEC.md "Dependencies and risks" — reproduced here with the PLAN-level
mitigation owner:

| Risk | Mitigation | Owner |
|---|---|---|
| FR2 over-acceptance turns a no-op worker into a pass | AC2.4 (byte-identical invariant tests) + AC2(repro-negative) | T-66-05 + T-66-09 (QA re-verify) |
| FR3 id drift (OpenRouter renames/deprecates) | Out of scope; future rename is a new bug, not a v0.1.66 defect | N/A |
| FR5 sandbox override misuse (`workspace-write`/`danger-full-access` widen codex's own access) | Outer `dadaia lifecycle` gate remains the real boundary regardless of codex's sandbox; default stays `read-only` (AC5.2) | T-66-03 |
| Executed-path test flakiness from faked subprocess seams | Follow the exact proven pattern already in the test suite (cited above); no new test-double mechanism invented | T-66-04..T-66-08, T-66-09 |
| A fix is accidentally a workaround (violates the mandate) | PLAN review rejects any task whose fix description matches a workaround shape (try/except swallow, config-only band-aid defaulted only in tests, wrapper script); TASKS.md AC explicitly names the source-level root-cause change | product-engineer (SPEC/PLAN authoring), qa-engineer (T-66-09 verification) |

## Rollback

Each wave is an independently revertable set of commits (disjoint files per
task within a wave, as noted above). If a wave's QA re-verification
(T-66-09) finds a regression attributable to one specific FR, that FR's
task commit(s) can be reverted independently without reverting the other 7
FRs — none of the 8 FRs share a code edit inside the same function body (FR1
and FR2 both touch the pi/shared-adapter files but in non-overlapping
functions: `_result_from_output`'s guard vs `classify_result_payload`/
`normalize_artifact_refs`). No schema/data migration is introduced by this
release (no persisted-state shape change) — rollback is a pure code revert
with no cleanup step required.
