# PLAN — Release v0.1.67 — Test-Infra Executed-Path Integrity

> **Status:** Aprovado
> **Release ID:** v0.1.67
> **Owner:** product-engineer

## Strategy

Root-cause a shared defect (class-definition-time default-argument binding of
`subprocess.run` in two adapter constructors) in four ordered waves: (A) fix
the mechanism in both adapters with a RED-first unit test proving the
call-time-vs-construction-time distinction; (B) rewrite the pre-existing
false-positive CLI test AND migrate the one additional broken-pattern site to
the already-established constructor-injection pattern with a genuinely
fake-derived (call-recorder + structural-field) assertion; (C) add a
suite-wide autouse guard that fails loud on any un-opted-in real-binary
invocation, unioning ALL FOUR established live-opt-in flags; (D) qa-engineer
validation, including per-flag guard non-interference and mutation-sanity.
Waves are ordered because B and C both depend on A's mechanism existing (B's
belt-and-suspenders construction injection works standalone, but the guard in
C specifically targets the module-attribute seam A makes genuinely
interceptable).

> **Revision (software-architect review, 2026-07-08, folded same session):**
> FR3's guard mechanism widened to a 4-flag union (F1); FR2 scope widened to
> cover `test_lifecycle_cli.py`'s sibling broken pattern with an explicit
> documented-debt decision on `test_lifecycle_pipeline_v0166_repro.py` (F2);
> the test plan's fake-derivation idiom corrected from an unsatisfiable
> `blocked.reason` example to the call-recorder + structural-field idiom (F3);
> import-linter expectation corrected 8→9 contracts (F4); AC3(repro)
> `xfail(strict=True)` pinned explicitly in the execution order (F6). See
> SPEC.md's "Revision log" for the full per-finding record.

## Modules affected

| Module | Change |
|---|---|
| `dadaia_workspace/infrastructure/pi_runtime.py` | `PiHeadlessAdapter.__init__`: `runner: Runner \| None = None`; store `self._runner = runner`. Add `_resolve_runner()` helper (or inline at the one call site in `.run()`) performing `subprocess.run` module-qualified lookup at call time when `self._runner is None`. |
| `dadaia_workspace/infrastructure/codex_runtime.py` | Identical change to `CodexExecAdapter.__init__` / `.run()`. |
| `tests/unit/infrastructure/test_pi_runtime.py` | Add AC1(repro) test: no-arg construction + late module-attr monkeypatch + call-time interception proof. Add AC3.1 guard-proof test (xfail-first, then permanent contract case per SPEC FR3's TDD-mandate decision). |
| `tests/unit/infrastructure/test_codex_exec_runtime.py` | Mirror AC1(repro) + AC3.2 for codex. |
| `tests/integration/cli/test_lifecycle_pipeline_cli.py` | Rewrite `test_pipeline_runs_first_step_on_pi_harness_end_to_end` to constructor-injection + `calls` call-recorder + structural-field assertion (F3 idiom). Migrate `test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo` to the same pattern (hardening, assertions otherwise unchanged, `calls` recorder added). |
| `tests/integration/cli/test_lifecycle_cli.py` | (F2, new) Migrate `_inject_pi_stream` (feeds `test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo`) from the broken `monkeypatch.setattr(".pi_runtime.subprocess.run", ...)` pattern to constructor-injection + `calls` call-recorder. Existing `payload["runtime"] == "pi_headless"` assertion preserved. |
| `tests/conftest.py` | Add new autouse fixture: real-binary guardrail (DEC-C), patches `pi_runtime.subprocess.run` / `codex_runtime.subprocess.run` to a raising sentinel unless ANY of `DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`, `DADAIA_CODEX_LIVE`, `DADAIA_CLAUDE_LIVE` == `"1"` (single named union predicate, F1). |

**Explicitly NOT touched (documented decision, F2):**
`tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py`'s
`_patch_pi_runner` (`__kwdefaults__` setitem, 5 call sites) stays as-is. It
survives FR1 unmodified (`__init__.__kwdefaults__["runner"]` remains a valid
key regardless of whether its bound default value is `subprocess.run` or
`None`) and every one of its assertions is already exact-content, not
truthy-only — it is not itself a false positive. T-67-08 re-runs this file's
full suite as an explicit regression check. See SPEC.md "Out of scope" for the
full reasoning.

No other module is touched. `dadaia_workspace/container.py`'s
`build_agent_runtime` is NOT modified — it already constructs both adapters
with no `runner=` kwarg, which is the exact call pattern FR1 must make safe by
construction (the container itself needs no change; the adapter's own default
resolution is what changes).

## Execution order

1. **T-67-01 (FR1, pi):** RED-first unit test in `test_pi_runtime.py` proving
   call-time interception fails on current code.
2. **T-67-02 (FR1, pi):** Implement the `pi_runtime.py` mechanism fix. Confirm
   T-67-01 GREEN. Confirm existing `test_pi_runtime.py` suite unchanged/green
   (AC1.3).
3. **T-67-03 (FR1, codex):** RED-first unit test in `test_codex_exec_runtime.py`
   mirroring T-67-01.
4. **T-67-04 (FR1, codex):** Implement the `codex_runtime.py` mechanism fix.
   Confirm T-67-03 GREEN + existing `test_codex_exec_runtime.py` suite green.
5. **T-67-05 (FR2):** Rewrite `test_pipeline_runs_first_step_on_pi_harness_end_to_end`
   per SPEC FR2's F3-corrected idiom: constructor injection + `calls`
   call-recorder (`assert len(calls) == 1`) + structural-field assertions
   (`runtime`, `accepted`, the fixed `blocked.reason` constant treated
   honestly as a structural check, not a fake-content claim). Confirm GREEN
   against the T-67-02 fix.
6. **T-67-06 (FR2):** Migrate `test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo`
   to the same constructor-injection + `calls` pattern (hardening; existing
   assertions preserved). Confirm GREEN.
7. **T-67-07 (FR2, F2 new):** Migrate `test_lifecycle_cli.py::_inject_pi_stream`
   (feeding `test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo`)
   to the same constructor-injection + `calls` pattern. Confirm GREEN.
   Explicitly do NOT touch `test_lifecycle_pipeline_v0166_repro.py` (documented
   decision above) — T-67-11 re-runs it as a regression check instead.
8. **T-67-08 (FR3):** Add the autouse guard fixture to `tests/conftest.py`,
   with the mechanism widened to the 4-flag union (single named predicate).
   Author the two guard-proof cases FIRST as `xfail(strict=True)` (F6 — never
   a live real-binary spawn in CI), confirm the xfail is honored, THEN
   implement the guard, remove the `xfail` marker, and confirm both now raise
   `RuntimeError` deterministically. Place the two cases in
   `tests/unit/infrastructure/test_pi_runtime.py` /
   `test_codex_exec_runtime.py` as small dedicated permanent cases per the
   TDD-mandate decision in SPEC.md.
9. **T-67-09 (FR3):** Add the 3 additional per-flag guard non-interference
   proofs referenced by AC3.3 — `DADAIA_PI_LIVE`, `DADAIA_CODEX_LIVE`,
   `DADAIA_CLAUDE_LIVE` — as targeted checks (not full live runs; see T-67-11
   for the full qa-engineer live-suite pass). This can be a small
   contract-style test or documented manual verification step depending on
   implementer judgment; either way each of the 4 flags must have an explicit,
   named, non-inferred proof (F1's specific requirement — the
   `DADAIA_CODEX_LIVE` regression must not be inferred from a
   `DADAIA_E2E_REAL_WORKER` run).
10. **T-67-10 (qa-engineer, validation wave):** Run the full unit + integration
    suite (excluding `*_live/`). Run `lint-imports --config setup.cfg
    --no-cache` and confirm **"9 kept, 0 broken"** (F4-corrected expectation —
    NOT "8 kept").
11. **T-67-11 (qa-engineer, validation wave):** Run `tests/integration/pi_live/`,
    `codex_live/`, `claude_live/` per AC3.3's per-flag matrix (each of the 4
    flags set independently, plus each directory with its flag unset to
    confirm the unchanged skip-reason text). Re-run
    `test_lifecycle_pipeline_v0166_repro.py`'s full suite explicitly (the F2
    documented-debt regression check). Mutation-sanity pass per SPEC AC-MUT
    (revert-and-confirm-RED for FR1 and FR3; FR2's mutation-sanity sequenced
    after F3's idiom is in place — documented, not committed).

## Test plan

**Unit level (pi_runtime, codex_runtime):**
- Proves the DEFECT class-time-vs-call-time distinction directly: construct
  adapter with no `runner=`, monkeypatch the MODULE attribute AFTER
  construction, call `.run(...)`, assert the fake was actually invoked (via a
  call-recorder closure or a distinctive fake-produced `AgentRunResult` field —
  never a bare truthy check).
- Confirms explicit `runner=fake_runner` injection is unaffected (existing test
  files, 0 modifications expected — a full pytest run on both files is the
  regression proof).

**Executed-path / CLI level (`test_lifecycle_pipeline_cli.py`,
`test_lifecycle_cli.py`) — F3-corrected idiom:**
- The rewritten/migrated tests drive the REAL CLI → real `LifecyclePipeline`
  or single-step verb → real `LifecycleAgentRunner` → the patched
  `container.build_agent_runtime` (constructor-injects the fake) → the real
  `PiHeadlessAdapter._command`/`.run()` body, unmodified above the
  construction seam. Fake-derivation is proven by a `calls` call-recorder
  list (`assert len(calls) == 1` or `>= 1` where the step may retry/advance)
  PLUS a structural-field assertion the fake's behaviour drives
  (`payload["steps"][0]["runtime"] == "pi_headless"`,
  `["accepted"] is False`). `blocked.reason` equality checks are used ONLY
  where the reason is a genuinely fixed, known constant (e.g.
  `"agent result missing artifact evidence"`) — treated as an honest
  structural check, never claimed as fake-derived content. This mirrors the
  already-correct idiom in `test_lifecycle_pipeline_v0166_repro.py`.

**Guard-proof level (contract-style, permanent, xfail-first per F6):**
- Two small, dedicated test cases (one pi, one codex) authored FIRST as
  `@pytest.mark.xfail(strict=True, ...)` wrapping a no-`runner=` construction
  + `.run()` call with none of the 4 opt-in flags set — never executed to a
  real-binary completion in CI; the `xfail(strict=True)` marker itself is the
  RED proof. After the guard fixture exists, the marker is removed and the
  test asserts `pytest.raises(RuntimeError)` deterministically (GREEN). These
  live permanently in the unit suites (not deleted after this release) so the
  guard's own behavior stays pinned against future regression.

**Guard non-interference level — per-flag matrix (F1-corrected):**
- `tests/integration/pi_live/` run with `DADAIA_E2E_REAL_WORKER=1` — guard
  never fires; separately with `DADAIA_PI_LIVE=1` for
  `test_pi_live_contract.py` — guard never fires.
- `tests/integration/codex_live/` run with `DADAIA_CODEX_LIVE=1` — guard
  never fires (the specific regression F1 identified; MUST be its own named
  check, never inferred from a pi-flag run).
- `tests/integration/claude_live/` run with `DADAIA_CLAUDE_LIVE=1` — guard
  never fires.
- Each `*_live/` directory run with its flag UNSET — pre-existing `skipif`
  skip-reason text unchanged (guard never reached; test itself skips first).
- qa-engineer runs each leg only if local preconditions allow (binary
  installed + authenticated); otherwise documents the explicit skip in
  validation evidence — consistent with how those suites already self-gate.

## Import-linter check (F4-corrected)

Confirmed at spec time (grill finding #8, re-verified during architect
review): no new cross-layer import is introduced. `pi_runtime.py` and
`codex_runtime.py` already import `subprocess` and
`headless_adapter_base.Runner`; the fix stays inside each module's own
`.run()`/`__init__`. `tests/conftest.py` is not subject to `[importlinter]`
(test tree is outside `source_modules = dadaia_workspace`). `setup.cfg`
defines **9** `[importlinter:contract:...]` blocks (verified by direct count:
`features-no-infrastructure`, `features-no-subprocess`,
`core-no-os-primitives`, `core-no-upper-layers`,
`infrastructure-no-upper-layers`, `kernel-tunables-is-a-leaf`,
`lifecycle-no-workflows`, `features-no-cross-feature`,
`cli-no-infrastructure` — the last added v0.1.61 FR5). qa-engineer
re-confirms at T-67-10 by running `lint-imports --config setup.cfg --no-cache`
and expecting **"9 kept, 0 broken"** — NOT the stale "8 kept" figure from the
original grill/SPEC draft.

## Risks

- **Guard under-bound risk (F1, now mitigated):** the original single-flag
  guard design would have broken `DADAIA_CODEX_LIVE=1` runs of
  `codex_live/test_codex_adapter_live_contract.py`. Mitigated by the 4-flag
  union predicate and AC3.3's explicit per-flag verification matrix.
- **Regression risk** on ~30 existing unit tests that already inject
  `runner=fake_runner` — mitigated by AC1.3/the mechanism design (explicit
  injection path structurally untouched).
- **Assertion-derivation risk (F3, now mitigated):** the original FR2
  assertion example pointed at a fixed-constant field
  (`blocked.reason == "agent result missing artifact evidence"`) as if it
  were fake-derived, which it is not. Mitigated by the call-recorder +
  structural-field idiom, which genuinely fails when the fake is not invoked.
- **Idiom-fragmentation risk (F2, accepted debt):** leaving
  `test_lifecycle_pipeline_v0166_repro.py`'s `__kwdefaults__` idiom unmigrated
  means the suite carries two idioms for this seam post-release. Accepted;
  T-67-11 confirms no regression; a future release may converge it.

## Rollback

Each task is independently revertible: FR1's two adapter changes are isolated
per-file diffs (revert `pi_runtime.py`/`codex_runtime.py` to restore the old
default-argument line); FR2's test rewrites/migrations revert to the prior
test bodies (reintroducing the false positives, so this rollback path is
discouraged once merged); FR3's guard fixture is a single addition to
`tests/conftest.py`, removable independently of FR1/FR2 if it is ever found to
over-fire in a way AC3.3's per-flag matrix did not anticipate. No production
runtime behavior changes (the `Runner | None = None` default with call-time
resolution to `subprocess.run` is behaviorally IDENTICAL to the old
`Runner = subprocess.run` default from the caller's perspective when no
`runner=` is passed — same function ultimately invoked, only the WHEN of the
lookup changes), so rollback carries no product risk.
