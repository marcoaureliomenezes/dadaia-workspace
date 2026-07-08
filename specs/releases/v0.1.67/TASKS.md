# TASKS — Release v0.1.67 — Test-Infra Executed-Path Integrity

> **Status:** Aprovado
> **Release ID:** v0.1.67
> **Owner:** product-engineer

Marker contract: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]`
at a time unless disjoint write sets are declared. RED-first: every FR1/FR3
task starts by writing the failing proof, confirming it fails on current code,
THEN implementing the fix.

> **Revision (software-architect review, 2026-07-08, folded same session):**
> tasks renumbered/added to fold F1 (4-flag guard union + explicit per-flag
> proofs), F2 (new T-67-07 migration + explicit documented decision on
> `v0166_repro.py`), F3 (call-recorder idiom in T-67-05/06/07), F4 (T-67-10
> corrected to "9 kept"), F6 (xfail-first pinned in T-67-08). See SPEC.md's
> "Revision log" for the full per-finding record.

---

## Wave A — FR1: adapter mechanism fix (DEC-A)

### T-67-01 — RED: pi call-time-interception proof (FAILING on current code) `[x]`

- **Owner:** software-engineer
- **Write set:** `tests/unit/infrastructure/test_pi_runtime.py` (additive test only)
- **Preconditions:** none (first task)
- **Task:** Add a new unit test constructing `PiHeadlessAdapter(PiHeadlessConfig(cwd=...))`
  with NO `runner=` kwarg, then `monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake)`
  AFTER construction (mirroring the exact monkeypatch pattern from the bug
  report), then call `.run(request)`, and assert the fake was actually invoked
  (a call-recorder closure that flips a flag, or asserts on a distinctive
  fake-produced `AgentRunResult.summary` string). Run the test and CONFIRM it
  FAILS on current code (the real `subprocess.run` was already bound at class
  definition; the fake is never reached).
- **Done criterion:** new test exists, confirmed RED on current
  `pi_runtime.py`. Commit message documents the RED confirmation
  (`test(pi-runtime): T-67-01 RED — proves class-def-time runner binding defect`).
- **AC:** SPEC AC1(repro) (pi half).
- **Parallelism:** none — first task, serial dependency for T-67-02.

### T-67-02 — GREEN: pi mechanism fix `[x]`

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/pi_runtime.py`
- **Preconditions:** T-67-01 `[x]` (RED proof committed)
- **Task:** Change `PiHeadlessAdapter.__init__`'s `runner` parameter to
  `runner: Runner | None = None`; store `self._runner = runner`. In `.run()`
  (the single call site that invokes `self._runner(...)`), resolve the actual
  callable at call time: if `self._runner is not None` use it, else call
  `subprocess.run` via the module-qualified lookup (either inline or via a
  small `_resolve_runner()` helper — implementer's choice, SPEC allows either
  shape). Re-run T-67-01's test — confirm GREEN. Re-run the FULL existing
  `test_pi_runtime.py` suite — confirm 100% green, 0 modifications to any
  pre-existing test in that file.
- **Done criterion:** T-67-01 test GREEN; full `test_pi_runtime.py` suite
  green with 0 pre-existing-test edits.
- **AC:** SPEC AC1.1, AC1.3 (pi half), AC1(repro) GREEN half.
- **Parallelism:** none — depends on T-67-01.

### T-67-03 — RED: codex call-time-interception proof (FAILING on current code) `[-]`

- **Owner:** software-engineer
- **Write set:** `tests/unit/infrastructure/test_codex_exec_runtime.py` (additive test only)
- **Preconditions:** none (independent of pi wave; may run in parallel with T-67-01/02 — disjoint write sets)
- **Task:** Mirror T-67-01 for `CodexExecAdapter`: construct with no `runner=`,
  monkeypatch `"dadaia_workspace.infrastructure.codex_runtime.subprocess.run"`
  after construction, call `.run(request)`, assert the fake was invoked.
  Confirm RED on current code.
- **Done criterion:** new test exists, confirmed RED on current
  `codex_runtime.py`.
- **AC:** SPEC AC1(repro) (codex half).
- **Parallelism:** SAFE parallel with T-67-01/T-67-02 — disjoint files
  (`test_codex_exec_runtime.py` vs `test_pi_runtime.py`/`pi_runtime.py`).

### T-67-04 — GREEN: codex mechanism fix

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_runtime.py`
- **Preconditions:** T-67-03 `[x]`
- **Task:** Identical fix to T-67-02, applied to `CodexExecAdapter.__init__`/`.run()`.
  Re-run T-67-03's test — confirm GREEN. Re-run the FULL existing
  `test_codex_exec_runtime.py` suite — confirm 100% green, 0 modifications to
  any pre-existing test.
- **Done criterion:** T-67-03 test GREEN; full `test_codex_exec_runtime.py`
  suite green with 0 pre-existing-test edits.
- **AC:** SPEC AC1.2, AC1.3 (codex half), AC1(repro) GREEN half.
- **Parallelism:** depends on T-67-03; safe to run parallel with T-67-01/02
  (disjoint write sets: `codex_runtime.py` vs `pi_runtime.py`).

---

## Wave B — FR2: false-positive test rewrite + idiom convergence (DEC-B, F2/F3-corrected)

### T-67-05 — Rewrite the pre-existing false-positive pi executed-path test

- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_lifecycle_pipeline_cli.py`
  (function `test_pipeline_runs_first_step_on_pi_harness_end_to_end` only)
- **Preconditions:** T-67-02 `[x]` (pi mechanism fix in place — though this
  task's constructor-injection pattern is belt-and-suspenders independent of
  it per SPEC FR2)
- **Task:** Replace the broken `monkeypatch.setattr(".pi_runtime.subprocess.run", fake_pi_run)`
  pattern with the established constructor-injection pattern (patch
  `container.build_agent_runtime`'s `PI_HEADLESS` branch to construct
  `PiHeadlessAdapter(pi_config, runner=fake_pi_run, environ={}, git=GitSubprocessClient())`,
  following the exact shape already used by
  `test_pi_openrouter_kimi_profile_reaches_command_with_valid_id` in the same
  file). **F3-corrected idiom:** add a `calls: list[object] = []` closure that
  the fake appends its own `args` to; replace the truthy-only
  `assert payload["blocked"]["reason"]` with:
  `assert len(calls) == 1` (fake-derivation proof) +
  `assert payload["steps"][0]["runtime"] == "pi_headless"` +
  `assert payload["steps"][0]["accepted"] is False` +
  `assert payload["blocked"]["reason"] == "agent result missing artifact evidence"`
  (the real, verified fixed constant from `agent_runner.py:220` for a
  no-artifact CREATE step — an honest structural check, not a claimed
  fake-content anchor). Run the test — confirm GREEN.
- **Done criterion:** test uses constructor injection (no
  `monkeypatch.setattr(".pi_runtime.subprocess.run", ...)` remains in this
  test function); a `calls` call-recorder proves fake invocation; the
  `blocked.reason` assertion targets the real, verified constant; test is
  GREEN.
- **AC:** SPEC AC2.1, AC2.2.
- **Parallelism:** none — single-file edit, must not race with T-67-06 on the
  same file (serialize).

### T-67-06 — Migrate the entry-pin echo test to the same pattern (hardening)

- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_lifecycle_pipeline_cli.py`
  (function `test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo` only)
- **Preconditions:** T-67-05 `[x]` (same file, serialize after)
- **Task:** Migrate this test's `monkeypatch.setattr(".pi_runtime.subprocess.run", fake_pi_run)`
  pattern to the same constructor-injection pattern used in T-67-05, adding a
  `calls` call-recorder (`assert len(calls) == 1`). Existing assertions
  (`payload["steps"][0]["runtime"] == "pi_headless"`, the stderr echo text)
  are preserved unchanged — this is a hardening migration, not a new
  assertion. Confirm GREEN.
- **Done criterion:** test uses constructor injection + `calls` recorder; all
  pre-existing assertions in this test still pass unmodified.
- **AC:** SPEC AC2.3.
- **Parallelism:** depends on T-67-05 (same file).

### T-67-07 — (F2, new) Migrate the `test_lifecycle_cli.py` sibling broken-pattern site

- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_lifecycle_cli.py`
  (`_inject_pi_stream` helper and
  `test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo` only)
- **Preconditions:** T-67-02 `[x]` (pi mechanism fix); independent of T-67-05/06
  (different file) — SAFE to run in parallel with Wave B's other tasks once
  T-67-02 lands, but serialize against any other edit to this same file.
- **Task:** `_inject_pi_stream` (lines ~274-295) uses the identical broken
  `monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)`
  pattern — the single-step-verb (`dadaia lifecycle implement`) sibling of the
  pipeline-level test T-67-05 targets. Migrate it to constructor-injection
  (patch `container.build_agent_runtime`'s `PI_HEADLESS` branch) plus a
  `calls` call-recorder. Preserve the existing
  `payload["runtime"] == "pi_headless"` assertion. Confirm GREEN.
- **Done criterion:** `_inject_pi_stream` uses constructor injection + `calls`
  recorder; `test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo`'s
  existing assertion remains green.
- **AC:** SPEC AC2.4.
- **Parallelism:** SAFE parallel with T-67-05/06 (disjoint file:
  `test_lifecycle_cli.py` vs `test_lifecycle_pipeline_cli.py`).

**Explicit non-task (F2 documented decision):**
`tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py`'s
`_patch_pi_runner` (`__kwdefaults__` setitem) is deliberately NOT migrated in
this release — see SPEC.md "Out of scope" and PLAN.md's modules table for the
full reasoning. T-67-11 re-runs this file's suite as a regression check
instead of migrating it.

---

## Wave C — FR3: real-binary guardrail (DEC-C, F1/F6-corrected)

### T-67-08 — Add the autouse real-binary guard (4-flag union) + permanent guard-proof tests, xfail-first

- **Owner:** software-engineer
- **Write set:** `tests/conftest.py`; `tests/unit/infrastructure/test_pi_runtime.py`
  (one new permanent guard-proof test case); `tests/unit/infrastructure/test_codex_exec_runtime.py`
  (one new permanent guard-proof test case)
- **Preconditions:** T-67-02 `[x]` and T-67-04 `[x]` (guard patches the same
  module-qualified seam FR1 makes genuinely interceptable)
- **Task:**
  1. RED first, `xfail(strict=True)`-wrapped (F6 — never a live real-binary
     spawn in CI): add the two guard-proof test cases, each decorated
     `@pytest.mark.xfail(strict=True, reason="no guard yet — would spawn/hang on the real binary")`,
     wrapping a no-`runner=` construction + `.run(...)` call with none of the
     4 opt-in flags set. Confirm the `xfail` is honored (recorded as
     expected-fail, not executed to a real-binary completion).
  2. Add the new `autouse=True` fixture to `tests/conftest.py` (alongside
     `_scrub_entry_signal_env`/`_no_real_venv_in_tests`): implement a single
     named predicate (e.g. `_real_worker_opt_in() -> bool`) that returns
     `True` iff ANY of `DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`,
     `DADAIA_CODEX_LIVE`, `DADAIA_CLAUDE_LIVE` equals `"1"` in
     `os.environ`. The fixture patches
     `dadaia_workspace.infrastructure.pi_runtime.subprocess.run` and
     `dadaia_workspace.infrastructure.codex_runtime.subprocess.run` to a
     sentinel that raises `RuntimeError` UNLESS the predicate is `True`.
  3. Remove the `xfail` markers from the two guard-proof tests; re-run them —
     confirm GREEN (each now asserts `pytest.raises(RuntimeError)`, guard
     fires as designed).
  4. Re-run the FULL unit + integration suite (excluding `*_live/`) — confirm
     no regressions (every existing test either injects `runner=fake_...`
     explicitly, unaffected by the module-level patch, or does not construct
     these adapters at all).
- **Done criterion:** guard fixture exists in `tests/conftest.py` with the
  4-flag union predicate; both guard-proof tests are permanent, committed,
  xfail-then-GREEN as designed; full non-live suite green.
- **AC:** SPEC AC3.1, AC3.2, AC3.4, AC3(repro).
- **Parallelism:** none — single shared-file (`conftest.py`) task, run after
  Wave A completes.

### T-67-09 — (F1, new) Per-flag guard non-interference proofs

- **Owner:** software-engineer
- **Write set:** a small contract-style test (implementer's choice of file
  under `tests/unit/` or `tests/contract/`) exercising the guard predicate
  directly per flag; OR documented manual verification steps recorded for
  T-67-11 to execute — implementer's judgment, either satisfies this task.
- **Preconditions:** T-67-08 `[x]`
- **Task:** Prove, with an explicit and NAMED check per flag (never inferred
  from another flag's run — this is the specific gap F1 identified), that the
  guard predicate added in T-67-08 returns `True` (guard does not fire) when
  each of `DADAIA_PI_LIVE=1`, `DADAIA_CODEX_LIVE=1`, `DADAIA_CLAUDE_LIVE=1` is
  set individually (in addition to `DADAIA_E2E_REAL_WORKER=1`, already
  covered structurally by T-67-08's own opt-in verification). A direct unit
  test on the predicate function (parametrized over the 4 flag names) is the
  simplest sufficient proof and is RECOMMENDED over a full live-suite run at
  this task (T-67-11 covers the full live-suite pass separately).
- **Done criterion:** all 4 flags individually proven to satisfy the guard's
  allow-condition, each with its own named assertion.
- **AC:** SPEC AC3.3 (the per-flag matrix, specifically the
  `DADAIA_CODEX_LIVE` named check F1 required).
- **Parallelism:** depends on T-67-08; otherwise independent of Wave B.

---

## Wave D — Validation (qa-engineer)

### T-67-10 — Full non-live suite + import-linter (F4-corrected expectation)

- **Owner:** qa-engineer
- **Write set:** none (validation only — may add a `.dadaia/reports/` /
  `.dadaia/handoff/` artifact, no production/test-source edits)
- **Preconditions:** T-67-01 through T-67-09 all `[x]`
- **Task:**
  1. Run the full unit + integration + contract suite (excluding `*_live/`).
     Confirm green.
  2. Run `lint-imports --config setup.cfg --no-cache` — confirm
     **"9 kept, 0 broken"** (F4-corrected expectation; `setup.cfg` defines 9
     contracts including `cli-no-infrastructure` added v0.1.61 FR5 — do NOT
     expect the stale "8 kept" figure from the original grill draft).
- **Done criterion:** full non-live suite green; import-linter shows exactly
  "9 kept, 0 broken".
- **AC:** SPEC "Dependencies and risks" (F4-corrected import-linter risk item).
- **Parallelism:** none — depends on all implementation waves.

### T-67-11 — Live-suite non-interference matrix + regression re-run + mutation-sanity

- **Owner:** qa-engineer
- **Write set:** none (validation only)
- **Preconditions:** T-67-10 `[x]`
- **Task:**
  1. Per AC3.3's per-flag matrix: run `tests/integration/pi_live/` with
     `DADAIA_E2E_REAL_WORKER=1` (guard never fires) and, separately, with
     `DADAIA_PI_LIVE=1` for `test_pi_live_contract.py` (guard never fires).
     Run `tests/integration/codex_live/` with `DADAIA_CODEX_LIVE=1` (guard
     never fires — the specific F1 regression, confirm this explicitly, not
     inferred). Run `tests/integration/claude_live/` with
     `DADAIA_CLAUDE_LIVE=1` (guard never fires). For each directory, also run
     with its flag UNSET and confirm the pre-existing skip-reason text is
     unchanged. If local preconditions (binary installed + authenticated) do
     not allow a given leg, document the explicit skip in validation evidence
     — not a release blocker, consistent with how these suites already
     self-gate.
  2. Re-run `test_lifecycle_pipeline_v0166_repro.py`'s full suite explicitly
     (the F2 documented-debt regression check — confirm all 5
     `_patch_pi_runner`-based tests remain 100% green after FR1 shipped).
  3. Mutation-sanity (SPEC AC-MUT): in an uncommitted local working-tree edit,
     revert `pi_runtime.py`'s and `codex_runtime.py`'s fix back to
     `runner: Runner = subprocess.run` — confirm T-67-01's/T-67-03's tests
     (or their now-folded permanent equivalents) FAIL. Revert the mutation.
     Then, with FR2's F3-corrected `calls`-based idiom in place, revert the
     `calls`-based assertion to the original truthy-only
     `assert payload["blocked"]["reason"]` while keeping constructor
     injection — confirm it still passes (expected — truthy is weaker, NOT a
     mutation-sanity failure); instead confirm the OLD monkeypatch mechanism
     reintroduced (removing constructor injection + `calls`) makes the
     `calls`-based assertion fail (empty list). Revert. Then comment out the
     T-67-08 guard fixture's `monkeypatch.setattr` calls — confirm the two
     guard-proof tests FAIL. Revert. Record all mutation-sanity results in
     the validation evidence.
- **Done criterion:** all sub-checks above pass or are explicitly documented
  as environment-gated skips; the `DADAIA_CODEX_LIVE` proof is explicit and
  named; mutation-sanity proofs recorded for FR1, FR2, and FR3.
- **AC:** SPEC AC3.3 (full matrix), AC2.5, AC-MUT (full, including the
  F7-sequenced FR2 dependency on F3).
- **Parallelism:** none — final gate, runs after T-67-10.

---

## Golden / AC re-verification tail

Before CLOSURE: re-run the full non-live suite once more on the final commit
SHA (post any review-requested changes) and re-confirm every AC listed above
against that SHA, including the corrected expectations (9 kept import-linter
result; 4-flag guard union; call-recorder FR2 idiom). Record the SHA +
command + pass/fail evidence triple in CLOSURE.md's `## Validations` table per
the `dadaia-release-closure` skill template.
