# SPEC — Release v0.1.67 — Test-Infra Executed-Path Integrity

> **Status:** Aprovado
> **Release ID:** v0.1.67
> **Owner:** product-engineer
> **Picked set:** 2 open bugs, ONE shared root cause

## Objective

Fix the shared root cause behind two open test-infrastructure bugs that let
CLI-level "executed-path" pi/codex tests silently invoke the REAL local
`pi`/`codex` binary instead of the faked subprocess seam, and add a durable,
suite-wide guard so this defect class cannot silently recur.

## Picked bugs

| Bug id | Severity | Disposition this release |
|---|---|---|
| `pi-executed-path-cli-tests-invoke-real-pi-binary` | MEDIUM | Fixed (FR1) |
| `pi-e2e-test-false-positive-loose-blocked-reason-assertion` | HIGH | Fixed (FR1 + FR2) |

Both bugs are the SAME root cause observed from two angles: FR1 fixes the
mechanism (the adapter's runner-resolution defect); FR2 fixes the specific
false-positive test that the mechanism defect was hiding behind. Neither bug is
superseded — both are fixed directly, not routed to backlog.

## Root cause (verified by inspection — see grill report)

`PiHeadlessAdapter.__init__` (`dadaia_workspace/infrastructure/pi_runtime.py:89`)
and `CodexExecAdapter.__init__` (`dadaia_workspace/infrastructure/codex_runtime.py:155`)
both declare:

```python
def __init__(self, config: ..., *, runner: Runner = subprocess.run, ...) -> None:
```

Python evaluates a keyword-default expression exactly ONCE, at
function/class-body definition time (import time). `runner` therefore
permanently captures the real `subprocess.run` function object at import.
`monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake)`
patches the `subprocess` module's `run` attribute — but the adapter's `self._runner`
was already bound to the original object before the patch runs, so
`adapter._runner is fake` is `False` and the REAL `pi`/`codex` binary on `PATH`
executes end-to-end inside a test that believes it is hermetic.

`dadaia_workspace/infrastructure/git_subprocess.py`'s `_run()` helper does NOT
have this defect: it calls `subprocess.run(...)` directly inside the function
body — a dynamic module-attribute lookup performed at CALL time, not a
default-argument snapshot — so a `monkeypatch.setattr(".git_subprocess.subprocess.run", fake)`
genuinely intercepts it. This is the reference pattern DEC-A generalizes.

`dadaia_workspace/container.py`'s `build_agent_runtime` (the production factory,
lines ~401-428) constructs both adapters with **no `runner=` argument**,
confirming the defect sits on the live production dispatch path, not merely in
test scaffolding.

The pre-existing test `tests/integration/cli/test_lifecycle_pipeline_cli.py::test_pipeline_runs_first_step_on_pi_harness_end_to_end`
"passed" anyway because its only assertion on the outcome
(`assert payload["blocked"]["reason"]`) is truthy-only — the REAL `pi` CLI's own
`"No API key found for azure-openai-responses...."` failure message also makes
that assertion pass. The test has never actually verified the injected fake
stream drove the block.

## Functional Requirements

### FR1 — Adapter mechanism fix: live runner indirection (DEC-A)

**Maps to bug:** `pi-executed-path-cli-tests-invoke-real-pi-binary` (MEDIUM), and
is the load-bearing fix for `pi-e2e-test-false-positive-loose-blocked-reason-assertion` (HIGH).

Both `PiHeadlessAdapter` and `CodexExecAdapter` must resolve their subprocess
runner via a live, call-time indirection when no explicit `runner` is injected,
instead of a class-definition-time default snapshot.

**Mechanism (settled):** keep the existing constructor-injection seam
(`runner: Runner | None = None`) — this preserves the ~30 existing unit tests
that already pass `runner=fake_runner` explicitly, unmodified. When `runner` is
`None` at construction, store `None` on the instance; at each call site inside
`.run()`, resolve the runner via a private helper that performs the
module-qualified lookup at call time (mirroring `git_subprocess.py`'s pattern):

```python
def _resolve_runner(self) -> Runner:
    return self._runner if self._runner is not None else subprocess.run
```

`self._runner` is set from the constructor parameter (which defaults to `None`,
not `subprocess.run`). `subprocess.run` inside `_resolve_runner`'s body is a
plain attribute access on the module-level `subprocess` import, executed
每 call — so `monkeypatch.setattr("<module>.subprocess.run", fake)` is honored,
because the lookup happens strictly after the patch is applied, on every call.
Apply the identical fix to BOTH `PiHeadlessAdapter.__init__`/`.run()`
(`pi_runtime.py`) and `CodexExecAdapter.__init__`/`.run()` (`codex_runtime.py`).
No other adapter (`ClaudeSdkAdapter`, `FakeAgentRuntime`) is affected — they do
not use this `Runner = subprocess.run` pattern (`ClaudeSdkAdapter` has no
subprocess machinery per `headless_adapter_base.py`'s module docstring).

**Acceptance criteria:**

- **AC1.1** `PiHeadlessAdapter(config)` constructed with NO explicit `runner`
  argument, after `monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake)`,
  genuinely calls `fake` when `.run(request)` executes — proven by an identity
  or call-recorded assertion (e.g. `fake` records its own invocation and the
  test asserts the recorded call happened, not merely that some result came
  back).
- **AC1.2** Same as AC1.1 for `CodexExecAdapter(config)` with
  `monkeypatch.setattr("dadaia_workspace.infrastructure.codex_runtime.subprocess.run", fake)`.
- **AC1.3** Explicit constructor injection (`runner=fake_runner`) continues to
  work identically for both adapters — no regression in the ~30 existing unit
  tests in `tests/unit/infrastructure/test_pi_runtime.py` and
  `tests/unit/infrastructure/test_codex_exec_runtime.py` (0 modifications
  required to those files; they pass unchanged).
- **AC1(repro)** — RED before fix / GREEN after: a new unit test
  `test_pi_runtime.py::test_default_runner_resolves_subprocess_run_at_call_time_not_construction_time`
  (or equivalent name) that: (a) constructs `PiHeadlessAdapter` with no `runner`
  kwarg, (b) monkeypatches the MODULE attribute `pi_runtime.subprocess.run`
  AFTER construction, (c) calls `.run(...)`, (d) asserts the fake was invoked.
  On current code (default snapshot at class-definition time) this test FAILS
  (the real function was already bound before the monkeypatch runs, so the
  fake is never called — assert on a call-recorder or a distinctive
  fake-produced return value fails). After the fix it is GREEN. Mirror for
  `CodexExecAdapter` in `test_codex_exec_runtime.py`.

### FR2 — False-positive test rewrite + full-suite idiom convergence: call-recorder + fake-unique-field content (DEC-B)

**Maps to bug:** `pi-e2e-test-false-positive-loose-blocked-reason-assertion` (HIGH).

> **Revision (architect review F2/F3, 2026-07-08):** the original SPEC
> understated the scope of this FR (F2 — one more broken-pattern site was
> unacknowledged) and proposed an unsatisfiable assertion example (F3 — the
> `implement` create step blocks on a FIXED CONSTANT, never fake-derived text).
> Both are corrected below. See "Revision log" at the end of this document.

**F3 correction — why `blocked.reason` cannot be the fake-derived anchor.**
`features/lifecycle/agent_runner.py:220` blocks a no-artifact CREATE step
(`implement` is `is_review=False`) with the fixed constant string
`"agent result missing artifact evidence"` — this string is emitted
regardless of what the fake stream's `content` field carried; it is never
fake-derived. (The `is_review=True` REVIEW-step sibling emits the equally
fixed `"agent result missing APPROVED verdict"` at line 209.) Any assertion
anchored on `blocked.reason` containing fake-unique text (e.g. `"injected pi
stream"`) is **unsatisfiable** for this test's shape and — if written as a
substring-in-generic-constant check — reopens the exact false positive,
because a real-binary auth failure with no artifacts produces the identical
generic constant. The correct fake-derivation proof for a CREATE-step
executed-path test is a **call-recorder** (the fake closure appends its own
`args` to a list; the test asserts the list has the expected length) **plus**
an assertion on a **structural field the fake's own behaviour drives** (e.g.
`payload["steps"][0]["runtime"] == "pi_headless"` and
`payload["steps"][0]["accepted"] is False`) — exactly the idiom already used
correctly by `test_lifecycle_pipeline_v0166_repro.py`'s four tests (e.g.
`test_pi_pipeline_still_blocks_on_genuine_noop_worker`: `calls` list +
`assert len(calls) == 1` + structural field checks). Where a test's fake DOES
drive real stderr into `blocked.reason` (the FR1-fixed non-zero-exit path,
`test_pi_pipeline_surfaces_real_setup_failure_not_generic_block`), an exact
`blocked.reason` string match is legitimate — but that is a different code
path (non-zero returncode, not a no-artifact SUCCEEDED result) and does not
apply to this FR's target test.

Rewrite `test_pipeline_runs_first_step_on_pi_harness_end_to_end` in
`tests/integration/cli/test_lifecycle_pipeline_cli.py` to use the ALREADY
ESTABLISHED correct pattern in the same file (the one
`test_pi_openrouter_kimi_profile_reaches_command_with_valid_id` and
`_patch_build_agent_runtime_for_codex` already use): patch
`container.build_agent_runtime`'s `PI_HEADLESS` branch to construct
`PiHeadlessAdapter(pi_config, runner=fake_pi_run, environ={}, git=GitSubprocessClient())`
explicitly, so the fake is injected at construction regardless of whether FR1's
live-indirection mechanism is also in place (belt-and-suspenders — the test
must not silently pass only because FR1 happens to intercept the class-level
monkeypatch too).

Replace the current truthy-only `assert payload["blocked"]["reason"]` with the
call-recorder + structural-field idiom (per the F3 correction above):

```python
calls: list[object] = []

def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
    calls.append(args)
    return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

# ... invoke the CLI ...

assert len(calls) == 1, "the faked pi subprocess seam must be invoked exactly once"
assert payload["steps"][0]["runtime"] == "pi_headless"
assert payload["steps"][0]["accepted"] is False
assert payload["blocked"]["reason"] == "agent result missing artifact evidence"
```

The `calls` list is the fake-derivation proof (only the fake could append to
it — a real-binary run leaves it empty and the test would fail before ever
reaching the `payload` assertions); the `blocked.reason` equality is now an
honest structural-constant check, not a claimed fake-content anchor.

`test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo` (same file, uses
the same broken class-level monkeypatch pattern) is migrated to the same
constructor-injection + call-recorder pattern for consistency and correctness.
Its existing assertions (`payload["steps"][0]["runtime"] == "pi_headless"`
plus the stderr echo text) are content-specific enough that they were not
already exploitably false-positive, but the migration adds the same `calls`
call-recorder so fake-invocation is proven, not merely implied.

**F2 correction — completeness: TWO additional artifacts carry the identical
root-cause pattern and are now in scope, converging the suite on ONE idiom:**

1. **`tests/integration/cli/test_lifecycle_cli.py:274-295`** — the
   `_inject_pi_stream` helper (feeding
   `test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo`) uses the
   IDENTICAL broken `monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)`
   pattern. This is the single-step-verb (`dadaia lifecycle implement`)
   sibling of the pipeline-level test FR2 already targets. It must be
   migrated to the same constructor-injection pattern (patching
   `container.build_agent_runtime`'s `PI_HEADLESS` branch) with a `calls`
   call-recorder added. Its existing structural assertion
   (`payload["runtime"] == "pi_headless"`) is preserved.
2. **`tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py`** — its
   `_patch_pi_runner` helper (used by 5 tests) patches the bound
   keyword-default directly:
   `monkeypatch.setitem(PiHeadlessAdapter.__init__.__kwdefaults__, "runner", fake_pi_run)`.
   This is a SECOND, competing idiom for the same seam, keyed on the
   implementation detail FR1 restructures (`__kwdefaults__["runner"]` moves
   from the value `subprocess.run` to `None`). **Decision:** this workaround
   is NOT migrated in this release. It continues to work unmodified after
   FR1 (the `setitem` still overwrites whatever default value the key holds
   — `None` or `subprocess.run` — with `fake_pi_run`, so
   `self._runner is fake_pi_run` remains `True`), and its existing content
   assertions are already correctly fake-derived where structurally possible
   (e.g. `test_pi_pipeline_surfaces_real_setup_failure_not_generic_block`
   asserts the EXACT injected stderr text, a legitimate fake-derived anchor
   on the non-zero-exit path). Leaving it is accepted **explicit debt**, not
   silent debt: it is recorded here, in `## Out of scope`, and T-67-08 must
   re-run this file's full suite to confirm FR1 does not break it (the
   `__kwdefaults__` key access pattern survives the default-value change).
   A future release may converge this file onto the constructor-injection or
   corrected module-attr idiom; this release does not require it because (a)
   it is not itself a false positive (every assertion in this file is
   already exact-content, not truthy-only) and (b) `__kwdefaults__` access
   is standard-library-guaranteed Python semantics, not a fragile private
   API — the debt is stylistic (three idioms instead of one), not
   correctness-bearing.

No further codex-side test rewrite is required beyond FR1: codex's
executed-path CLI tests (`test_codex_pipeline_untrusted_dir_no_longer_blocks_on_trust_error`,
`test_codex_pipeline_sandbox_override_avoids_container_bwrap_failure`,
`test_codex_pipeline_sandbox_default_stays_read_only_when_env_unset`) already
use the correct constructor-injection pattern via
`_patch_build_agent_runtime_for_codex` and already assert exact argv/reason
content — verified by inspection, no false positive present on the codex side.

**Acceptance criteria:**

- **AC2.1** `test_pipeline_runs_first_step_on_pi_harness_end_to_end` constructs
  its fake `PiHeadlessAdapter` via a patched `container.build_agent_runtime`
  (constructor injection), not via `monkeypatch.setattr(".pi_runtime.subprocess.run", ...)`,
  and records fake invocation via a `calls` list asserted `len(calls) == 1`.
- **AC2.2** The test's outcome assertion set includes the `calls`
  call-recorder proof PLUS a structural field the fake's behaviour drives
  (`payload["steps"][0]["runtime"]`, `["accepted"]`) — not a bare
  `blocked.reason` truthiness check, and not a `blocked.reason` substring
  claim that the generic constant cannot satisfy (F3 correction).
- **AC2.3** `test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo` is
  migrated to the same constructor-injection + call-recorder pattern; its
  existing assertions remain green afterward.
- **AC2.4** (new, F2) `test_lifecycle_cli.py::test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo`
  (via `_inject_pi_stream`) is migrated to the constructor-injection +
  call-recorder pattern; its existing `payload["runtime"] == "pi_headless"`
  assertion remains green afterward.
- **AC2.5** (new, F2) `test_lifecycle_pipeline_v0166_repro.py`'s 5
  `_patch_pi_runner`-based tests are NOT migrated in this release (explicit
  documented debt — see the F2 correction above) but are confirmed still
  100% green after FR1 ships (T-67-08 re-runs this file explicitly).
- **AC2(repro)** — RED before fix / GREEN after: temporarily reproduce the
  original defect by reverting FR1 in a throwaway branch check (or, more
  practically for CI-safety, prove the repro at spec-review time per the
  bug's own `repro` field — see "Reproduction & TDD mandate" below) and show
  the OLD test body (broken monkeypatch + truthy assertion) is satisfied by a
  real-binary run whose `calls` list would stay empty (proving the fake was
  never reached) while the OLD assertion still passed; the NEW test body's
  `calls`-based assertion correctly FAILS in that scenario (empty list) and
  PASSES once construction-injection + FR1 are both in place. This is
  documented as evidence in CLOSURE.md rather than re-run destructively in CI
  (see AC-MUT below for the mechanical mutation-sanity proof instead).

### FR3 — Real-binary guardrail (DEC-C)

**Maps to:** durable protection requested by the operator — "tests must never
silently hit the real binary" — not a specific bug id (a suite-wide hardening
requirement spanning both picked bugs).

> **Revision (architect review F1, 2026-07-08):** the original SPEC falsely
> claimed the `*_live/` suites all gate on `DADAIA_E2E_REAL_WORKER`. Verified
> against the real source: they gate on THREE DISTINCT flags. The guard
> mechanism below is corrected to the union of all four live-opt-in flags. See
> "Revision log" at the end of this document.

**F1 correction — the real opt-in surface (verified against source).** The
`*_live/` suites do NOT share one flag:

| Directory | File(s) | Flag |
|---|---|---|
| `tests/integration/pi_live/` | `test_pi_command_smoke.py`, `test_real_layer2_worker_workflow_e2e.py` | `DADAIA_E2E_REAL_WORKER` |
| `tests/integration/pi_live/` | `test_pi_live_contract.py` | `DADAIA_PI_LIVE` |
| `tests/integration/codex_live/` | `test_codex_adapter_live_contract.py`, `test_codex_live_contract.py` | `DADAIA_CODEX_LIVE` |
| `tests/integration/claude_live/` | `test_claude_live_contract.py` | `DADAIA_CLAUDE_LIVE` |

Each is read via `os.environ.get("<FLAG>") != "1"` in that file's own
`skipif`-gated marker (e.g. `codex_live/test_codex_adapter_live_contract.py`'s
own precondition helper). A guard whitelisting only
`DADAIA_E2E_REAL_WORKER` would raise its `RuntimeError` inside
`test_codex_exec_adapter_maps_live_run_to_result` (constructed with no
`runner=`, `.run()` called) the moment an operator legitimately runs
`DADAIA_CODEX_LIVE=1 pytest tests/integration/codex_live/` — a live false
block on the sanctioned smoke path.

Add a suite-wide `autouse=True` pytest fixture in `tests/conftest.py` (alongside
the existing `_scrub_entry_signal_env` / `_no_real_venv_in_tests` hermeticity
fixtures) that FAILS LOUD if either `PiHeadlessAdapter` or `CodexExecAdapter`
would invoke the real subprocess runner (i.e. `subprocess.run` un-faked) DURING
a test that has not explicitly opted in.

**Mechanism (corrected):** the fixture patches `pi_runtime.subprocess.run` and
`codex_runtime.subprocess.run` (module-qualified, the same seam FR1 makes
genuinely interceptable) to a sentinel function that raises
`RuntimeError("real pi/codex binary invocation attempted without a live-opt-in flag set — ...")`
UNLESS **the UNION of all four established opt-in flags** — any one of
`DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`, `DADAIA_CODEX_LIVE`,
`DADAIA_CLAUDE_LIVE` — is set to `"1"` for the current test. Implement this as
a single named predicate (e.g. `_real_worker_opt_in() -> bool` in
`tests/conftest.py`, or a small shared helper in `tests/fixtures/`) so there is
ONE source of truth for "is a live opt-in active", rather than four inline
checks duplicated at the fixture site — this reuses the EXISTING opt-in
convention verbatim (no new env var is introduced; the flag NAMES are
unchanged) while correctly widening the guard's allow-condition to their
union. Any test in `tests/unit/**` or `tests/integration/cli/**` that
constructs a `PiHeadlessAdapter`/`CodexExecAdapter` WITHOUT an explicit
`runner=` and without ANY of the four flags set will raise immediately from
the fixture's sentinel the moment `.run()` is reached, rather than silently
completing against the real binary. Tests that pass `runner=fake_...`
explicitly at construction are UNAFFECTED (the constructor-injected runner is
used, never the patched module attribute).

**Guardrail scope note:** this is a suite-hermeticity guard for
`tests/unit/**` and `tests/integration/cli/**` (where "executed-path" CLI tests
live). The `*_live/` directories (`tests/integration/pi_live/`,
`tests/integration/codex_live/`, `tests/integration/claude_live/`) are the
sanctioned real-binary smoke suite and each sets its OWN opt-in flag (per the
table above) before invoking a real adapter — the guard must not fire in any
of them once the union predicate covers all four flags.

**Acceptance criteria:**

- **AC3.1** A new throwaway/permanent test that constructs
  `PiHeadlessAdapter(config)` with no `runner=` and calls `.run(...)` WITHOUT
  setting any of the four opt-in flags raises the guard's `RuntimeError`
  (proving the guard fires) instead of hanging/spawning the real binary.
- **AC3.2** Same as AC3.1 for `CodexExecAdapter`.
- **AC3.3** (corrected, F1) The guard's non-interference is verified
  per-flag, not against a single flag:
  - `tests/integration/pi_live/` (both `DADAIA_E2E_REAL_WORKER=1` and,
    separately, `DADAIA_PI_LIVE=1` for `test_pi_live_contract.py`) — guard
    never fires.
  - `tests/integration/codex_live/` with `DADAIA_CODEX_LIVE=1` — guard never
    fires (this is the specific regression F1 identified; it MUST be an
    explicit, named check, not inferred from the pi-flag run).
  - `tests/integration/claude_live/` with `DADAIA_CLAUDE_LIVE=1` — guard
    never fires.
  - Each `*_live/` directory run with its flag UNSET still shows its
    pre-existing `skipif` skip-reason text, unchanged (the guard is never
    reached because the test itself skips first).
- **AC3.4** Every test in `tests/unit/infrastructure/test_pi_runtime.py` and
  `tests/unit/infrastructure/test_codex_exec_runtime.py` (which always inject
  `runner=fake_runner` explicitly) is unaffected by the guard — 0 regressions.
- **AC3(repro)** — RED before fix / GREEN after, via `xfail(strict=True)` ONLY
  (never a bare real-binary invocation in CI — see F6 correction below): the
  throwaway/permanent tests in AC3.1/AC3.2 are authored FIRST as
  `@pytest.mark.xfail(strict=True, reason="no guard yet — would spawn/hang on the real binary")`
  wrapping a construction + `.run()` call that is never actually executed to
  completion against a real binary (the `xfail(strict=True)` marker records
  the RED expectation declaratively — a `strict=True` xfail that unexpectedly
  PASSES is itself a hard failure, which is the correct RED signal for a test
  whose failure mode is "dangerous side effect", not "raises an assertion").
  After FR3 ships, remove the `xfail` marker; the test must now raise
  `RuntimeError` deterministically (GREEN under `pytest.raises(RuntimeError)`).
  This is the ONLY sanctioned way to demonstrate AC3(repro)'s RED state —
  never a live, un-`xfail`-wrapped real-binary spawn in CI.

## Reproduction & TDD mandate — no workarounds

Per operator hard rule for this release: every fix must be reproduced first
with a FAILING test proving the defect, then root-caused, then GREEN. Concretely:

1. Before touching `pi_runtime.py`/`codex_runtime.py`, write AC1(repro) — a unit
   test asserting the fake IS called after a module-level `subprocess.run`
   monkeypatch, with no explicit `runner=` at construction. Confirm it FAILS on
   current code (the identity/call-recorder assertion does not observe the
   fake).
2. Implement FR1's live-indirection mechanism. Re-run AC1(repro) — now GREEN.
3. Rewrite the pre-existing false-positive test per FR2 (the `calls`
   call-recorder + structural-field idiom — F3 correction). Migrate the two
   additional broken-pattern sites named in FR2's F2 correction
   (`test_lifecycle_cli.py::_inject_pi_stream` is migrated;
   `test_lifecycle_pipeline_v0166_repro.py`'s `_patch_pi_runner` is
   explicitly NOT migrated — documented debt). Confirm the OLD assertion
   shape would have passed under either binary (the `calls` list would stay
   empty yet the old truthy check still passed — documented in CLOSURE, not
   re-run destructively) and the NEW `calls`-based assertion is GREEN only
   when the fake's invocation is actually what drove the outcome.
4. Add the FR3 guard (union of all four live-opt-in flags — F1 correction).
   Author the two guard-proof tests (AC3.1/AC3.2) FIRST as
   `xfail(strict=True)` (never a live real-binary spawn in CI — F6
   correction), confirm the `xfail` is honored (i.e. currently would fail/
   hang, correctly recorded as expected-fail), then implement the guard,
   remove the `xfail` marker, and confirm both now raise `RuntimeError`
   deterministically. Keep them as permanent regression tests (folded into
   `tests/unit/infrastructure/test_pi_runtime.py` /
   `test_codex_exec_runtime.py` as small dedicated cases — decided at TASKS
   time, see PLAN.md test plan) so the guard's own behavior is pinned, not
   just exercised once and discarded.

NO workaround is acceptable: do not "fix" this by only tightening FR2's test
assertion while leaving the class-definition-time default-binding landmine in
place for the next author who writes an executed-path test. FR1 (the mechanism)
is mandatory alongside FR2 (the test) — shipping FR2 without FR1 leaves the
landmine live for every FUTURE test, which is exactly the recurrence FR3 exists
to catch, but catching it later is strictly worse than removing it now.

## AC-MUT — Mutation-sanity

For FR1: temporarily re-introduce the original defect (revert `_resolve_runner`
to a class-definition-time default snapshot: `runner: Runner = subprocess.run`)
in a local, uncommitted working-tree edit and re-run AC1.1/AC1.2 (or the folded
AC1(repro) tests) — they MUST fail. Revert the mutation before continuing. This
proves the new tests actually exercise the call-time-vs-construction-time
distinction rather than passing vacuously.

For FR2: **this proof is sequenced AFTER F3's correction is implemented** (the
`calls` call-recorder + structural-field idiom must exist first — architect
finding F7 notes the original truthy-vs-tightened mutation check was
meaningless until the "tightened" assertion was itself genuinely
fake-derived, which it was not in the original SPEC text). With the corrected
idiom in place: temporarily revert the `calls`-based assertion to the
original truthy-only `assert payload["blocked"]["reason"]` while keeping the
constructor-injection fix — the test should still pass (truthy is a WEAKER
assertion, satisfied by the tightened case too), which is expected and does
NOT indicate a mutation-sanity failure; the mutation that DOES matter for FR2
is reverting to the OLD monkeypatch mechanism (removing the `calls`
call-recorder and the constructor-injection patch), which is caught
structurally by AC2.1's code-review check (the diff literally removes the
broken pattern) and functionally by re-running AC2(repro)'s documented
evidence (the `calls` list would stay empty under a real-binary run).

For FR3: temporarily comment out the guard fixture's `monkeypatch.setattr(...)`
calls in a local edit and re-run AC3.1/AC3.2 (with their `xfail` markers
already removed, post-FR3) — they MUST fail (no `RuntimeError` raised;
real-binary invocation attempted/hangs — the local mutation-sanity run only,
never committed, never run destructively in shared CI). Revert before
continuing.

## Out of scope

- `pi-headless-nonzero-exit-misreported`, `lifecycle-agent-run-result-extraction-too-strict`,
  `pi-openrouter-kimi-profile-invalid-model-id`, `codex-exec-adapter-missing-skip-git-repo-check`,
  `codex-exec-sandbox-default-fails-in-container`, `lifecycle-resume-reports-ok-without-advancing`,
  `lifecycle-implement-step-write-scope-too-narrow` — all 7 already `resolved` in
  v0.1.66; not reopened here.
- No change to `ClaudeSdkAdapter` (no subprocess machinery; not affected by this
  defect class per `headless_adapter_base.py`'s own module docstring).
- No change to the `*_live/` real-binary smoke suites' own logic — FR3 must not
  alter their behavior, only leave them unaffected (per-flag, per the F1
  correction's union mechanism).
- No new CLI verb, no new public command, no memory atom changes (this is a
  test-infrastructure-only release; product behavior is unchanged).
- **(F2 correction) `tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py`'s
  `_patch_pi_runner` (`__kwdefaults__` setitem) idiom is explicitly NOT migrated
  to the constructor-injection/module-attr pattern in this release.** It is a
  second, competing idiom for the same seam and is recorded as accepted debt
  (see FR2's F2 correction for the full reasoning): it is not itself a false
  positive (every assertion in that file is already exact-content), it
  survives FR1 unmodified (`__kwdefaults__["runner"]` still exists as a key
  regardless of whether its default value is `subprocess.run` or `None`), and
  converging it onto one idiom is a stylistic cleanup, not a correctness fix.
  T-67-08 re-runs this file's full suite as a regression check. A future
  release may migrate it.
- Live backlog items (`panel-tab-reorg-agentic-layers`,
  `dispatch-band-legacy-fallback-removal`, `platform-seam-todo-retirement`,
  `specs-doctor-partial-archive-invariant`) are untouched by this release.

## Memory files affected at closure

None. This release changes only test infrastructure and an internal adapter
call-time-resolution detail (not a documented product behavior surface) — no
`specs/memory/**` atom describes subprocess-runner binding mechanics at this
level of detail. `sdd-bug-backlog-governance`'s atom already covers the bug
lifecycle; no update needed there either (no new governance mechanic
introduced). CLOSURE.md will confirm "no change" explicitly per the closure
protocol.

## Dependencies and risks

- **Risk:** the FR3 guard could over-fire and break the legitimate `*_live/`
  smoke suites. Mitigated by AC3.3 (explicit per-flag verification against
  ALL FOUR live-opt-in flags — `DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`,
  `DADAIA_CODEX_LIVE`, `DADAIA_CLAUDE_LIVE` — corrected per architect finding
  F1) and by reusing the EXACT existing opt-in flag NAMES rather than
  inventing a new one.
- **Risk:** the FR1 mechanism change could subtly alter behavior for the ~30
  existing unit tests that inject `runner=fake_runner` explicitly. Mitigated
  by AC1.3 (explicit regression check) and by the mechanism design itself
  (explicit injection path is structurally untouched — only the no-argument
  fallback changes).
- **Dependency:** none on other in-flight releases; `v0.1.66` is closed and
  archived. This release is self-contained.
- **Risk:** import-linter contracts (`setup.cfg`) — verified NO new edge is
  needed. `setup.cfg` defines **9 contracts** (`features-no-infrastructure`,
  `features-no-subprocess`, `core-no-os-primitives`, `core-no-upper-layers`,
  `infrastructure-no-upper-layers`, `kernel-tunables-is-a-leaf`,
  `lifecycle-no-workflows`, `features-no-cross-feature`,
  `cli-no-infrastructure` — the last added v0.1.61 FR5; the original grill
  report's "8" figure was stale, copied from a header comment in `setup.cfg`
  that predates that addition — corrected per architect finding F4). Expected
  `lint-imports` result is **"9 kept, 0 broken"**. PLAN.md and TASKS.md
  re-confirm at implementation time as a guardrail check.
- **Risk:** leaving `test_lifecycle_pipeline_v0166_repro.py`'s
  `__kwdefaults__`-setitem idiom unmigrated (F2 correction, see "Out of
  scope") means the suite ships this release with TWO idioms
  (constructor-injection and `__kwdefaults__` setitem) instead of one for
  faking this seam. Accepted as documented debt, not a release blocker —
  neither idiom is itself incorrect after FR1 ships; T-67-08 confirms no
  regression.

## Open Questions

None outstanding. All findings resolved by inspection during the mandatory
grill session — see
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-08T180000Z-refine-v0167.html`.
One judgment call was defaulted rather than escalated: FR1's mechanism keeps
the constructor-injection seam (`runner: Runner | None = None` + call-time
resolution) rather than deleting it, to avoid touching ~30 passing unit tests
unnecessarily — recorded above under FR1 "Mechanism (settled)".

## Revision log

**2026-07-08T19:00:00Z — software-architect review
(`.dadaia/reports/dadaia-workspace/software-architect/2026-07-08T190000Z-review-v0167-definition.md`),
verdict REVISE, folded same session.** FR1's mechanism (F5) was confirmed
sound and unchanged. Per-finding edits:

| Finding | Severity | Section(s) edited | Edit |
|---|---|---|---|
| F1 | HIGH | FR3 (mechanism, AC3.3), Dependencies and risks | Corrected the false claim that all `*_live/` suites gate on `DADAIA_E2E_REAL_WORKER`; verified the real 4-flag surface (`DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`, `DADAIA_CODEX_LIVE`, `DADAIA_CLAUDE_LIVE`); widened the guard's mechanism to a single named union predicate; added explicit per-flag AC3.3 sub-checks incl. a dedicated `DADAIA_CODEX_LIVE=1` check. |
| F2 | HIGH | FR2 (new "F2 correction" subsection, AC2.4/AC2.5), Out of scope, Dependencies and risks | Added the previously-unacknowledged `test_lifecycle_cli.py:274-295` (`_inject_pi_stream`) migration (AC2.4). Added an explicit, justified, documented-debt decision for `test_lifecycle_pipeline_v0166_repro.py`'s `__kwdefaults__`-setitem idiom (AC2.5, Out of scope, risk note) rather than silently leaving it unaddressed. |
| F3 | MEDIUM | FR2 (new "F3 correction" subsection, assertion example, AC2.1/AC2.2, AC2(repro)), AC-MUT (FR2) | Replaced the unsatisfiable `blocked.reason` fake-content example (the create-step gate emits a FIXED constant, verified at `agent_runner.py:220`) with the call-recorder (`calls` list) + structural-field idiom already used correctly by `test_lifecycle_pipeline_v0166_repro.py`; re-sequenced AC-MUT-FR2 to depend on this correction (also closes F7). |
| F4 | MEDIUM | Dependencies and risks | Corrected "8 kept, 0 broken" → "9 kept, 0 broken" (verified `setup.cfg` defines 9 `[importlinter:contract:...]` blocks incl. `cli-no-infrastructure`, added v0.1.61 FR5); PLAN.md and TASKS.md corrected in the same pass. |
| F6 | LOW | FR3 (AC3(repro)), Reproduction & TDD mandate step 4 | Pinned `xfail(strict=True)` as the ONLY sanctioned way to demonstrate AC3(repro)'s RED state; explicitly forbade a live, un-wrapped real-binary spawn in CI to prove RED. |
| F7 | LOW | AC-MUT (FR2) | Noted explicitly that AC-MUT-FR2 is sequenced after F3's correction lands, since a mutation-sanity check on a non-fake-derived assertion proves nothing. |

No SPEC finding required operator escalation — all six were resolved by
direct source verification against the files the architect cited (confirmed
independently before editing: `codex_live`/`claude_live`/`pi_live` flag names
via grep on each `*_live/` file; `agent_runner.py:209/220`'s two fixed block
constants; `test_lifecycle_cli.py:291`'s broken pattern; `test_lifecycle_pipeline_v0166_repro.py`'s
5 `_patch_pi_runner` call sites and their existing exact-content assertions;
`setup.cfg`'s 9 contract blocks).
