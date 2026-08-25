# S1 — AS-5 verdict: `windows-xdist-workers-crash-on-unit-fast-tier`

**Author:** qa-engineer, 2026-08-25
**Governs:** SPEC.md §2.3 AS-5, §6 R-9; TASKS.md T-045-09 (`AS-5` column)
**Input:** `.dadaia/tmp/software-engineer/20260825/T-045-09-evidenced-negative.md`
(time-boxed root-cause attempt, inconclusive by the SE's own record)

## Decision

**(b) No-quarantine verdict.** The bug stays **OPEN and unpicked**. No test selector is
quarantined. Two CI-config mitigations are named below as intake candidates for the PM
— not implemented in this release (rc scope law).

## Evidence chain

1. CI run `32763757511`, job `97548409516` (`Unit fast (Windows/macOS) (windows-latest)`,
   attempt 1) — the actual crashing attempt (the bug's own `repro` field cites the run's
   *second*, green attempt; the SE's evidence file corrects this to the right job id):
   - Invocation: `pytest -q -m "unit and not slow and not quarantine" tests/unit -n auto
     --durations=25`.
   - `[gw0] node down: Not properly terminated`; `[gw2] node down: Not properly
     terminated`.
   - gw0 died running `tests/unit/infrastructure/test_public_assets_kimi.py::
     test_install_refreshes_stale_block_and_shims`.
   - gw2 died running `tests/unit/features/reports/test_handoff_v12_validation.py::
     test_v12_sidecar_never_routes_to_v10_compat_cli`.
   - Crash at ~73-77% through the run's wall-clock; no `MemoryError`,
     `STATUS_ACCESS_VIOLATION`, `Fatal Python error`, or `WinError` string anywhere in
     the captured job log — xdist's generic "node down" is the only signal GH Actions'
     hosted-runner log surfaces for a dead worker OS process.
2. Same commit range: attempt 2 of the same job — green. rc-1's final merge run — green.
   Two data points consistent with transient runner-load pressure, not a deterministic
   code defect (unproven either way — no native crash telemetry is captured by this CI
   job).
3. Hypothesis (a) — worker count (`-n auto` -> 4 workers on windows-latest's 4 vCPU/16 GB
   hosted runner) vs. available memory late in a ~2,600-test fan-out, with both crashed
   tests being heavier-than-median real disk writers (`WorkspaceService.init()`,
   `FileSystemPublicAssetManager().stage()+install()`): plausible, **unproven** — no
   per-process memory telemetry in the log.
4. Hypothesis (b) — shared-path collision between the two crashed tests: **ruled out**.
   Both tests' fixtures resolve through xdist-namespaced `tmp_path`; neither references
   `tests/tmp/`, a hardcoded shared filename, or any other test's fixture. The two tests
   share no code path, module, or functional relationship.
5. Hypothesis (c) — a real but **separate** finding, surfaced while auditing `tests/**`
   for shared-path xdist races: `tests/contract/test_frozen_clock_aging_ratchet.py`'s
   `_test_files()` used a raw `Path.rglob("*.py")` that (unlike `pyproject.toml`'s
   `norecursedirs`) does not exclude `tests/tmp/`, racing a concurrent xdist worker's
   scratch-file writes in that directory — a catchable `FileNotFoundError` TOCTOU.
   Confirmed real, root-caused, RED-to-GREEN fixed, committed as
   `fix(T-045-09): exclude tests/tmp/ scratch dir from the frozen-clock ratchet's file
   scan` (commit `0d9d49bb`); registered and `resolved` as bug
   `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` in `specs/bugs/bugs.jsonl`. It runs
   in a different CI job/tier (`tests/contract/`, "Contract coverage"), touches different
   tests, and fails a different way (a catchable Python exception, not a hard OS-level
   worker death). **It does not explain this bug's symptom** and does not resolve it.

## Why the alternative (a quarantine selector) is rejected

AS-5 permits a quarantine verdict as the fallback when the bounded root-cause attempt is
inconclusive — but a quarantine still requires the quarantined thing to *be* the failing
unit, and `dadaia-test-stewardship` §F's quarantine mechanism is a per-test mark. The
evidence above shows the failing unit here is not a test: it is the xdist **worker OS
process**. `test_install_refreshes_stale_block_and_shims` and
`test_v12_sidecar_never_routes_to_v10_compat_cli` share no fixture, no module, no
functional relationship — the only thing that connects them is that each happened to be
executing on the worker that died at that moment, in a 4-worker fan-out across ~2,600
tests. A worker death lands on whatever test it is running when it dies; quarantining
either of these two selectors would not address recurrence, because the next crash would
land on a different, unrelated test while the quarantined selectors sat in the suite
carrying a bug id that describes a failure mode neither of them actually has. That is the
superstition the root-cause law (`DADAIA.md` §7) forbids: a test-level workaround for a
non-test-level defect. The two real mitigations both live outside the test layer:

- **CI-config candidate 1:** job-level retry/backoff on the `unit-fast-cross`
  windows-latest leg.
- **CI-config candidate 2:** pin a fixed, smaller `-n` worker count (e.g. `-n 2`) for the
  windows-latest leg of `unit-fast-cross`, trading wall-clock time for headroom.

Both are `.github/workflows/ci.yml` changes — new scope, owned by `software-engineer`,
outside this release's picked FR set (SPEC §6 R-7: `rc` scope is fixes/adjustments to
picked scope only; a CI-matrix retry/worker-count policy was never picked). They are
named here as PM intake candidates, not implemented in this release.

## What `CLOSURE.md` must record

Per SPEC.md §5 closure obligations and §6 R-9:

- `windows-xdist-workers-crash-on-unit-fast-tier` recorded **still open, unpicked** — no
  `resolved`/`superseded` event exists for it. Confirmed via `dadaia bugs stats`: 2 bugs
  are currently `status:open` workspace-wide, this one and
  `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (disposed
  elsewhere in this release, bundled into FR7 per SPEC §7).
- No test disposition (demotion / quarantine / SCAFFOLD expiry) applies to this bug —
  none was filed, per the decision above.
- Two named CI-config intake candidates (job-level retry; pinned `-n 2` on the
  windows-latest leg) routed to the PM's intake report — not implemented in this
  release.
- The bundled separable finding, bug `frozen-clock-ratchet-scans-tests-tmp-scratch-dir`,
  is `resolved`/`Closed` in the same `S1` sweep, recorded independently of this bug's
  still-open disposition — it is a different bug on a different surface.
- Per the quality law (`DADAIA.md` §7): the pass-on-retry occurrence already observed
  (attempt 1 crash, attempt 2 green, on the same commit range) was registered at report
  time (the bug's `reported` event already records this transient-vs-deterministic
  framing) — no further registration action is owed by this verdict. Any *future*
  pass-on-retry occurrence on this tier must be registered as its own event.

## Security/privacy leakage note

None. This verdict cites only already-public CI log content (run/job ids, test
selectors, xdist diagnostic strings) and the existing bug ledger. No secrets, tokens,
credentials, consumer-specific data, or PII are referenced or introduced. No dependency
or generated-file change results from this verdict. No public-asset privacy concern —
this document lives under `specs/releases/`, not any `public/` projection.

## Bug-surface axis

This verdict does not close a bug by design (AS-5 leaves it open). The touched surface
(`tests CI matrix / pytest-xdist`, `windows-latest` leg of `unit-fast-cross`) has exactly
one bug ever registered against it — this one, first occurrence, no prior history on
this surface. The bug surface is neither reduced nor increased by this verdict: no
production or test code changed on the crashing surface itself (`tests/unit/**` on the
windows-latest leg). The separable finding fixed along the way
(`frozen-clock-ratchet-scans-tests-tmp-scratch-dir`) reduces a *different* surface's bug
count by one — its first and only registered bug on `tests/contract/test_frozen_clock_
aging_ratchet.py`, now resolved with a regression-proof exclusion, no recurrence.
