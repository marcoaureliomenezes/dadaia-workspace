# TASKS — v0.1.66 Layer-2 Worker Path Remediation

**Status:** Aprovado

Marker legend: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]`
per owner at a time, except within a wave explicitly declared parallel-safe
below (disjoint write sets). Every code task's FIRST step is authoring the RED
executed-path reproduction test named in SPEC.md and recording the captured
failure (paste the exact assertion failure / block reason into the task's
completion commit message or an inline note) — per the operator's hard mandate,
this is not optional even for the "trivial config" tasks in Wave A.

---

## Wave A — trivial-looking config fixes, STILL repro-proven (parallel-safe within the wave; T-66-02/03 serialized on `codex_runtime.py`)

### T-66-01 — FR3: valid OpenRouter kimi model id `[-]`

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/model_profiles.py`,
  `dadaia_workspace/core/harness_models.py`,
  `tests/unit/features/lifecycle/test_model_profiles.py`,
  `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or sibling repro
  file per PLAN.md's judgment call)
- **Preconditions:** none (Wave A start)
- **RED-first:** write executed-path test
  `test_pi_openrouter_kimi_profile_reaches_command_with_valid_id` driving
  `dadaia lifecycle pipeline --harness pi --step-model implement=pi-openrouter-kimi-high`
  through the real CLI with a faked `subprocess.run` capturing the argv;
  assert the `--model` value is `moonshotai/kimi-k2.5`. Run it, confirm it
  FAILS on current code (captures literal `kimi-2.7`), record the failure.
- **Fix:** replace `"kimi-2.7"` with `"moonshotai/kimi-k2.5"` in
  `model_profiles.py:102-103` (`model_id` + `label`) and
  `harness_models.py:75,99` (`HarnessModelOption` + `LAYER2_EXTRA_MODEL_IDS`).
  Update the pre-existing pin `test_openrouter_kimi_profile_is_a_governed_pi_option`
  in the same commit.
- **Done criterion:** AC3.1, AC3.2, AC3.3, AC3(repro) all GREEN; repro test
  confirmed it was RED before the fix (recorded).
- **Parallelism:** disjoint from T-66-02/T-66-03/T-66-04..T-66-08.

### T-66-02 — FR4: codex adapter passes `--skip-git-repo-check`

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_runtime.py` (the
  `_command` method only), `tests/unit/infrastructure/test_codex_exec_runtime.py`,
  `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or sibling repro
  file)
- **Preconditions:** none (Wave A; runs before T-66-03 on the same file)
- **RED-first:** write executed-path test
  `test_codex_pipeline_untrusted_dir_no_longer_blocks_on_trust_error` driving
  `dadaia lifecycle pipeline --harness codex` through the real CLI with a
  faked `subprocess.run` that returns the real codex trust-error stderr
  whenever `--skip-git-repo-check` is absent from the captured argv. Confirm
  RED on current code (pipeline blocks with the trust-error reason), record
  it.
- **Fix:** add `"--skip-git-repo-check"` to the fixed argv list in
  `_command`.
- **Done criterion:** AC4.1, AC4(repro) GREEN; RED capture recorded.
- **Parallelism:** must land before T-66-03 (same file, sequenced not
  concurrent).

### T-66-03 — FR5: codex sandbox env override

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_runtime.py` (the
  `CodexExecConfig` dataclass and/or `container.py`'s codex-adapter
  construction site — NOT `_command`'s argv-token list itself, which T-66-02
  already touched), `dadaia_workspace/container.py` (if the env read belongs
  at the wiring call site), `tests/unit/infrastructure/test_codex_exec_runtime.py`,
  `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or sibling repro
  file)
- **Preconditions:** T-66-02 `[x]` DONE (avoids a merge collision on
  `codex_runtime.py`)
- **RED-first:** write executed-path test
  `test_codex_pipeline_sandbox_override_avoids_container_bwrap_failure`
  driving `dadaia lifecycle pipeline --harness codex` with
  `DADAIA_CODEX_SANDBOX=workspace-write` set, through the real CLI with a
  faked `subprocess.run` that returns the real bwrap-failure stderr whenever
  `--sandbox` in the captured argv is `read-only`. Confirm RED on current
  code (env var is read nowhere, argv still carries `read-only`, pipeline
  blocks with the bwrap error), record it.
- **Fix:** read `DADAIA_CODEX_SANDBOX` at adapter-construction time; validate
  against `{read-only, workspace-write, danger-full-access}` (raise a clear
  error on an unrecognized value — AC5.3); override `sandbox` when set;
  compiled-in default stays `read-only` when unset (AC5.2).
- **Done criterion:** AC5.1, AC5.2, AC5.3, AC5(repro) all GREEN; RED capture
  recorded.
- **Parallelism:** sequenced after T-66-02.

---

## Wave B — pi/codex result-contract fixes (serial: T-66-04 before T-66-05 before T-66-06 — each builds on the prior's fix being present so the executed-path tests compose correctly)

### T-66-04 — FR1: pi non-zero exit reported as FAILED `[-]`

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/pi_runtime.py` (the
  `_result_from_output` method only), `tests/unit/infrastructure/test_pi_runtime.py`,
  `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or sibling repro
  file)
- **Preconditions:** Wave A `[x]` DONE (not a hard dependency, but sequenced
  after per PLAN.md wave ordering)
- **RED-first:** write unit test (AC1.1: faked `returncode=1`, non-empty
  stdout+stderr → expect `FAILED` + real stderr in `error`) AND executed-path
  test `test_pi_pipeline_surfaces_real_setup_failure_not_generic_block` (AC1
  repro: same scenario driven through the real CLI, asserting the block
  reason contains the real stderr text, not the generic message). Confirm
  BOTH are RED on current code (unit test: result is SUCCEEDED not FAILED;
  executed-path: block reason is the generic string), record both failures.
- **Fix:** in `_result_from_output`, change
  `if returncode != 0 and not text:` to `if returncode != 0:` (drop the
  `and not text` conjunct), keeping `error=""` so `run()`'s existing
  stderr-backfill (lines 138-144, UNCHANGED) populates the real reason.
- **Done criterion:** AC1.1, AC1.2, AC1(repro) GREEN; AC1.3 regression guard
  (`test_pi_adapter_nonzero_exit_with_no_output_returns_failed`) still GREEN
  UNMODIFIED; both RED captures recorded.
- **Parallelism:** none — Wave B is serial.

### T-66-05 — FR2: tolerant worker-result contract, no-op invariant preserved

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/headless_adapter_base.py`
  (the `classify_result_payload` and `normalize_artifact_refs` functions
  only), `tests/unit/infrastructure/test_headless_adapter_base.py`,
  `tests/unit/infrastructure/test_pi_runtime.py` (new tests only — the two
  invariant-pinning tests at lines 471/717 must NOT be edited),
  `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or sibling repro
  file)
- **Preconditions:** T-66-04 `[x]` DONE
- **RED-first:** write unit tests (AC2.1: `schema_version` equivalence;
  AC2.2: singular `artifact.path` harvest; AC2.3: list content wins when both
  present) AND executed-path tests
  `test_pi_pipeline_accepts_schema_version_and_singular_artifact_result`
  (AC2 repro) and `test_pi_pipeline_still_blocks_on_genuine_noop_worker`
  (AC2 repro-negative — this one is expected to PASS on current code too;
  confirm it does, as the baseline proof the invariant already holds before
  touching anything). Confirm AC2.1/2.2/2.3 and the repro test are RED on
  current code, record the failures.
- **Fix:** (i) in `classify_result_payload`, compare
  `payload.get("schema") or payload.get("schema_version")` against
  `expected_schema` for STRICT; (ii) in `normalize_artifact_refs`, when the
  list-based extraction yields `()`, additionally check
  `payload.get("artifact")` for a dict with a string `path` and return it as
  a one-element tuple.
- **Done criterion:** AC2.1, AC2.2, AC2.3, AC2(repro) GREEN; AC2.4 invariant
  guard — `test_pi_noop_worker_yields_empty_artifact_refs` and
  `test_pi_adapter_bare_json_without_result_shape_is_rejected` byte-identical
  to their pre-task state (verified via `git diff` on those two test
  functions showing zero changes) and GREEN; AC2(repro-negative) GREEN both
  before and after; RED captures recorded.
- **Parallelism:** none — Wave B is serial.

### T-66-06 — FR8: precise upstream failure detail enrichment

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/agent_runner.py` (the
  `_blocked_result` method's `not result.artifact_refs` branch only),
  `tests/unit/features/lifecycle/test_agent_runner.py` (or equivalent
  existing suite), `tests/integration/cli/test_lifecycle_pipeline_cli.py`
  (or sibling repro file)
- **Preconditions:** T-66-05 `[x]` DONE
- **RED-first:** write executed-path test
  `test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty`:
  pre-write a genuinely valid, independently-validating handoff file at the
  expected `.dadaia/handoff/<context>/` path; drive the real CLI with a faked
  worker whose result has empty `artifact_refs`; assert
  `blocked.detail["validated_handoff_path"]` equals that path AND
  `status == "BLOCKED"`. Confirm RED on current code (`detail` is `{}`),
  record it.
- **Fix:** in `_blocked_result`'s `not result.artifact_refs` branch, look up
  a matching, independently-validating handoff file under
  `.dadaia/handoff/<context>/` (the step's context/agent naming convention)
  and pass it as `detail={"validated_handoff_path": <path>}` to `_blocked`
  when found; `detail={}` unchanged when no such file exists.
- **Done criterion:** AC8(repro) GREEN; AC8.1/AC8.2 confirmed satisfied by
  T-66-04's and T-66-02/03's own repro tests (cite the test names, no
  re-implementation); the run remains BLOCKED in the new test (never
  converts to a pass); RED capture recorded.
- **Parallelism:** none — Wave B is serial; Wave C may start once Wave B is
  fully `[x]` DONE.

---

## Wave C — engine-level fixes (T-66-07 and T-66-08 sequenced on `cli/commands/lifecycle.py` overlap; otherwise disjoint)

### T-66-07 [-] — FR6: `resume` reports the real run status

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/service.py` (the
  `resume_run` method only), `dadaia_workspace/cli/commands/lifecycle.py`
  (the `resume` command only), `tests/unit/features/lifecycle/` (service
  test), `tests/integration/cli/test_lifecycle_cli.py`
- **Preconditions:** Wave B `[x]` DONE
- **RED-first:** write unit tests (AC6.1: BLOCKED run → BLOCKED result with
  real reason; AC6.2: non-BLOCKED run → OK unchanged) AND executed-path test
  `test_lifecycle_resume_cli_exits_nonzero_on_still_blocked_run` driving
  `dadaia lifecycle resume <run_id>` through the real CLI against a fixture
  run state file persisted with `status=BLOCKED`; assert
  `result.exit_code != 0` and the real block reason appears in the output.
  Confirm RED on current code (`exit_code == 0`, output is
  `"OK resumed <id>"`), record it.
- **Fix:** `resume_run` inspects the loaded run's `status`; when
  `LifecycleRunStatus.BLOCKED`, returns
  `LifecycleCommandResult(status=BLOCKED, message=<run's blocked.reason>)`.
  Route the `resume` CLI command through the existing
  `_emit_command_result`/`_exit_for_command_result` machinery (no new
  exit-code convention introduced).
- **Done criterion:** AC6.1, AC6.2, AC6(repro) GREEN; RED capture recorded.
- **Parallelism:** must land before or after T-66-08 without overlapping
  edits to `cli/commands/lifecycle.py` — sequenced first.

### T-66-08 — FR7: implement step write scope covers the reserved task

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/pipeline.py` (the
  `PipelineStep` dataclass — new `extra_allowed_paths` field — and `_scope`
  only), `dadaia_workspace/cli/commands/lifecycle.py` (new `--write-scope`
  option on `implement` and `pipeline` commands only, disjoint region from
  T-66-07's `resume` command edit), `tests/unit/features/lifecycle/test_pipeline.py`,
  `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or sibling repro
  file)
- **Preconditions:** T-66-07 `[x]` DONE (avoids a merge collision on
  `cli/commands/lifecycle.py`)
- **RED-first:** write unit tests (AC7.1: `extra_allowed_paths` reaches
  `implement`'s `allowed_paths` union; AC7.2: ignored for `review_qa`) AND
  executed-path test
  `test_implement_pipeline_write_scope_covers_reserved_task_production_path`
  driving `dadaia lifecycle pipeline --harness fake --write-scope <path-glob>`
  through the real CLI with an injected `FakeAgentRuntime` result whose
  `structured_output["changed_paths"]` includes a path under that glob.
  Confirm RED on current code (gate rejects the path as out-of-scope,
  pipeline blocks with `"agent result contains out-of-scope paths"`), record
  it.
- **Fix:** add `PipelineStep.extra_allowed_paths: tuple[str, ...] = ()`
  (additive-optional); `_scope` computes `allowed_paths` for the `implement`
  step as the union of the existing handoff-dir glob and
  `step.extra_allowed_paths`; review steps unchanged (handoff-only). Add the
  repeatable `--write-scope PATH` CLI option, threading its values into
  `PipelineStep.extra_allowed_paths` for the `implement` step only.
- **Done criterion:** AC7.1, AC7.2, AC7(repro) GREEN; RED capture recorded.
- **Parallelism:** sequenced after T-66-07.

---

## QA wave

### T-66-09 — executed-path re-verification + golden regression + import-linter + AC-MUT

- **Owner:** qa-engineer
- **Write set:** none (read-only verification; may add QA report artifacts
  under `.dadaia/reports/dadaia-workspace/qa-engineer/`)
- **Preconditions:** T-66-01..T-66-08 all `[x]` DONE
- **Steps:**
  1. Re-run every `AC-N(repro)` test named in SPEC.md end-to-end against the
     final tree; confirm all GREEN.
  2. Re-run the full existing lifecycle test suite
     (`tests/unit/features/lifecycle/`,
     `tests/unit/infrastructure/test_pi_runtime.py`,
     `tests/unit/infrastructure/test_headless_adapter_base.py`,
     `tests/unit/infrastructure/test_codex_exec_runtime.py`,
     `tests/integration/cli/test_lifecycle_*.py`) — zero regressions.
  3. Re-run `test_pipeline_runs_to_closure_on_fake`
     (`test_lifecycle_pipeline_full.py`) unmodified — golden happy-path proof
     survives.
  4. Re-run `lint-imports` — confirm zero new ignored edges, all contracts in
     `setup.cfg` `[importlinter]` still pass (per PLAN.md's import-linter
     safety table).
  5. AC-MUT proof-of-bite: for each of AC1.1, AC2.1-2.3, AC3.1-3.2, AC4.1,
     AC5.1-5.3, AC6.1-6.2, AC7.1-7.2 — briefly revert the corresponding fixed
     condition locally, re-run the specific unit test, confirm it FAILS,
     re-apply the fix, confirm it PASSES again. Record each proof-of-bite
     result.
  6. Confirm AC2.4's invariant guard: `git diff` on
     `test_pi_noop_worker_yields_empty_artifact_refs` and
     `test_pi_adapter_bare_json_without_result_shape_is_rejected` shows zero
     changes across the entire release's commit range.
  7. Confirm zero workaround-shaped fixes landed: read every task's fix
     description against the mandate's forbidden-shape list (try/except
     swallow, config-only band-aid, wrapper script/PATH shim, local alias
     file) — flag any violation back to product-engineer before approving.
- **Done criterion:** all 7 steps pass; QA handoff emitted with `verdict:
  APPROVED` referencing this task.
- **Parallelism:** none — final gate before CLOSURE.

---

## Golden/AC re-verification tail

After T-66-09 is `[x]` DONE and QA APPROVED, `code-reviewer` and
`security-reviewer` run their standard review passes (per
`release-governance`'s review cadence — this release has no security-sensitive
surface beyond FR4/FR5's sandbox/trust posture, which the SPEC's Security/
operations deltas section already documents and code/security review must
explicitly re-confirm does not widen the real security boundary, i.e. that the
outer `dadaia lifecycle` gate — not codex's own sandbox/trust flags — remains
the actual write/access control). Once all three reviews are green and the
push-cycle security verdict is APPROVED for the final commit sha, the release
proceeds to CLOSURE per the `dadaia-release-closure` skill.
