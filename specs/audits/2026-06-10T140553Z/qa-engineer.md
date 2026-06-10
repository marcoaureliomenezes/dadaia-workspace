---
name: test-architecture-verification-audit
date: 2026-06-10
auditor: qa-engineer
scope: >
  Adversarial verification audit of the dadaia-workspace test suite on branch
  feature/v0.1.10 (post-remediation). Verifies the remediation claims of release
  v0.1.10 against the actual tests: pyramid architecture, fixture design, isolation,
  contract-test layer, slop hunt across >=30 sampled files, bug-escape regression
  coverage for the five kernel bugs, and suite runtime optimization. Independent of
  the prior audits at 2026-06-10T010550Z (5/10) and 2026-06-10T052944Z (9.25/10).
---

# Test Architecture Verification Audit — feature/v0.1.10

**Method:** read-only adversarial review. One full suite run
(`pytest -p no:cacheprovider -q --durations=25`). Direct file reads of all four layers,
prioritizing v0.1.10-touched areas (gate_policy, lease, session_identity,
sdd_gate/sdd_post_gate hooks, ci_preflight, e2e two-actor). No prior-claim trust.

## 1. Suite shape & metrics

| Layer | Test files | Test functions (grep `def test_`) | Share |
|---|---|---|---|
| unit | 151 | 2012 | ~79% |
| integration | 45 | 319 | ~13% |
| contract | 21 | 128 | ~5% |
| e2e | 11 | 75 | ~3% |
| **total** | **228** | **2534 defs** (collected count higher via parametrize) | |

Pyramid verdict: shape is textbook (unit-heavy, thin e2e). Layer markers are applied
deterministically from directory layout in `tests/conftest.py::pytest_collection_modifyitems`
— no reliance on authors remembering to mark.

### 1.1 Runtime (single run, `pytest -p no:cacheprovider -q --durations=25`)

- **2795 passed, 8 skipped, 1 xpassed in 79.80s** (exit 0).
- Slowest test: 5.36s (`e2e/features/test_handoff_pipeline.py::test_full_handoff_emit_and_validate`);
  2nd: 4.78s (`integration/test_cli_import.py::test_import_extracts_archive` — real archive
  round-trip). The four two-actor e2e scenarios cost ~2.1s each — justified: real OS
  subprocesses + bounded rendezvous, no blind sleeps. The two harness-env AST contract scans
  cost 0.89s/0.82s — the price of the zero-baseline ratchet, acceptable.
- Nothing over 6s; ~28ms/test average. The historical 15-24 min / ENOSPC failure mode
  (real venv builds) is structurally dead via the autouse `_no_real_venv_in_tests` patch.
- **Optimization verdict: genuinely optimized.** The slow tail is exclusively real
  process-boundary work; no sleep-padding found in the top 25 (rendezvous helpers poll
  conditions with bounded deadlines).

## 2. Layer-by-layer architecture assessment

### 2.1 Fixture design — `tests/fixtures/harness_env.py` (VERIFIED STRONG)

This is the keystone remediation artifact and it is real, not theater:

- Pins, with per-var justification naming the production reader, exactly which env vars
  each harness delivers to a hook subprocess (`CLAUDE_CODE_SESSION_ID` / `CODEX_SESSION_ID`
  + scrubbed operator shell). `_FORBIDDEN_HOOK_ENV` actively scrubs the harness-fiction
  vars (`DADAIA_SESSION_ID`, persona, mode) so a leaked `os.environ` can never resurrect
  the simulated-env blind spot.
- `run_hook_subprocess` invokes `python -m dadaia_workspace.hooks.<name>` with a real
  stdin pipe — the production spawn topology, not an in-process `main()` call.
- `_harness_env` raises `ValueError` on any non-allowlisted `DADAIA_*` in `extra` — the
  fixture defends itself at runtime, not just via the contract scan.

### 2.2 Contract layer — `tests/contract/` (VERIFIED STRONG, one weak corner)

- `test_harness_env_contract.py` is a genuine **zero-baseline AST ratchet** (verified by
  reading the AST visitor): it catches `monkeypatch.setenv`, `os.environ[...]=`,
  `setdefault`, `update`, and the `monkeypatch.setitem(os.environ, ...)` escape hatch for
  any `DADAIA_*` write outside the fixture, and separately flags any file that imports a
  hook behavior module AND patches `sys.stdin` in-process. The rc-2 claim "baselines
  burned to zero" is true — no baseline dict exists in the file. Known evadable forms
  (dynamically-constructed var names, `os.putenv`) would slip past, but that requires
  deliberate evasion, not drift.
- The README inventory matches the on-disk contract files (spot-checked all 13 named
  rows exist). The retroactive **lifecycle-asymmetry coverage map** is grep-grounded —
  I verified a sample of named tests exist (`test_dead_with_commit_blocks_on_planted_secret`,
  `test_acquire_ttl_stale_alive_holder_blocks_no_takeover`, `test_row2_missing_fields_is_stale`,
  `test_subprocess_runner_missing_binary_returns_127_not_traceback`) — none aspirational.
- Weak corner: two contracts pin **prose**, not behavior (`test_codex_reference_only_wording.py`
  asserts substrings like "does not auto-execute" in docs;
  `test_workflow_review_gate_contract.py` asserts `REQUIRED_GATE_TERMS` substrings in agent
  persona files). These are deliberate anti-drift residue greps on governance wording, but
  they are brittle to semantically-equivalent rewording and test documentation, not code.
  Acceptable as a minority pattern; see slop inventory.

### 2.3 Unit layer (VERIFIED STRONG)

Sampled in depth: `test_lease_pid_liveness.py`, `test_lease_stale.py`, `test_lock_steal.py`,
`test_lease_property.py`, `test_sdd_gate.py`, `test_sdd_post_gate.py`,
`test_sdd_post_gate_behavior.py`, `test_stable_session_identity.py` (header),
`ci_preflight/test_service.py`, `telemetry/test_pricing.py`, plus stores/infrastructure
samples.

- **Determinism:** all lease/gate timing flows through injected `FakeClock`s and fake
  pid probes — zero real `datetime.now` dependence in the kernel tests, no `time.sleep`
  padding anywhere in unit (grep-verified; the only real sleep >50ms in the suite is one
  0.1s in a POSIX flock test).
- **Race coverage is real:** `test_lease_pid_liveness.py` drives the renew-vs-foreign-acquire
  interleaving deterministically via the `_before_write` seam under Hypothesis
  (40 examples) and asserts on **lock-file history**, not return values. The sentinel-CAS
  serialization test probes `O_EXCL` failure from *inside* the critical section. This is
  falsifying design — remove the CAS and these fail.
- **Mock hygiene:** only 10 of 228 files reference `unittest.mock` at all, each ≤5 uses,
  mostly spies on `os.replace` or fault injection. No over-mocked layer exists. The old
  "magic mock inflation" failure mode is absent.
- **In-process vs subprocess split is principled:** `test_sdd_post_gate.py` unit-tests
  internals by monkeypatching the production `read_stdin_json` symbol (fault injection,
  permitted), while its behavior twin `test_sdd_post_gate_behavior.py` goes through
  `run_hook_subprocess`. (Minor: its module docstring still says the contract "baselines
  this file" — stale wording from rc-1; the zero-baseline contract no longer needs to.)

### 2.4 Integration layer (VERIFIED STRONG)

- `gate/test_classifier_reroot_matrix.py` drives the **whole** `gate_policy.evaluate`
  pipeline for in-repo paths across default + non-default slugs and asserts the
  lease-theft incident regression **on file content** of the lock record.
- `gate/test_read_mode_non_acquiring.py` proves READ enforcement at the real hook
  boundary with **no env var anywhere** — the exact channel the original audit showed was
  the only one that physically exists. Includes the cross-sid incumbent falsification.
- `test_lease_property.py` fixed the audit's "drift-ratifying" root-only ADDITIVE rows:
  every spec-relative row now runs at both `root` and `in_repo` locations across two slugs.

### 2.5 E2E layer (VERIFIED STRONG)

`test_two_actor_lease.py` is the standout: real OS subprocesses driving the real lease and
the real `sdd_gate` hook, file rendezvous with bounded deadlines (no blind sleeps —
`lease_rendezvous.py` polls conditions), short-TTL injection instead of 120s waits, and
invariants asserted on the **`LockJournal` lock-file history** ("B never appears") rather
than return codes. Scenario (v) reproduces the production process topology: a long-lived
driver spawning the ephemeral hook child. The only test-only shortcut —
`_set_short_ttl_on_record` rewriting `ttl` on a genuinely hook-written record — is
documented and compresses only the staleness clock, not the semantics. The journal
mechanism itself is guarded by `test_journal_records_raw_lock_versions`.

### 2.6 Isolation (VERIFIED)

- Autouse `_no_real_venv_in_tests` kills the historical real-venv/ENOSPC failure mode.
- Per-test snapshot-diff guard over `.claude/ .agents/ .codex/ .opencode/ .dadaia/` +
  guarded root files, AND a session-level pollution-dir diff guard that **fails the exit
  status**, not just warns. The diff (vs existence) design correctly avoids tripping on
  the preflight gate's own earlier artifacts (documented bug reference).
- `addopts = "-ra -p no:cacheprovider"` pinned in `pyproject.toml`.
- One smell: `e2e/features/test_panel.py::test_memory_view_iframe_loads` points at the
  REAL workspace root (`cwd=_DADAIA_WORKSPACE_ROOT`) — but it permanently skips (see §5),
  so the isolation breach is latent, not active.
- No order dependence observed: tmp_path-per-test everywhere sampled; the suite passed
  in one run with the autouse guards active.

## 3. Slop inventory

The suite is remarkably clean for its size. Full-suite AST scan for assertion-free tests
plus manual sampling of 30+ files found only:

| # | Item | Location | Why it's (mild) slop | Severity |
|---|---|---|---|---|
| 1 | Permanently-skipping dead test | `tests/e2e/features/test_panel.py:381` (`test_memory_view_iframe_loads`) | Skip guard references `specs/memory/architecture.html` — memory migrated to `.md` (memory-markdown-source-v1), so the fixture can never exist; the test has been dead-by-skip since the migration. Docstring also references retired `primary_context.json`. Looks like coverage, is none. (Mitigated: `unit/features/panel/test_memory_byte_identity.py` covers byte identity.) | MEDIUM |
| 2 | Near-tautology smoke tests in panel views | e.g. `tests/unit/features/panel/test_views_agents.py:18` (`test_render_agents_section_returns_string` — asserts `isinstance(str)` + `len>0`); same pattern across several `test_views_*.py` | Cannot fail unless the renderer crashes; the substring tests beside them subsume it | LOW |
| 3 | Redundant duplicate assertion | `test_views_agents.py:25` (`test_section_has_role_tabpanel`) re-asserts `id="agents-grid"` which `test_section_has_grid_container:38` exists to assert | Copy-paste residue from the T-016-P09 refactor | LOW |
| 4 | Prose-pinning contracts | `tests/contract/test_codex_reference_only_wording.py`; `tests/contract/test_workflow_review_gate_contract.py` | Substring pins on documentation/persona prose ("does not auto-execute", `REQUIRED_GATE_TERMS`) — test wording, not behavior; brittle to honest rewording. Deliberate anti-drift choice, kept small | LOW |
| 5 | Stale docstring | `tests/unit/hooks/test_sdd_post_gate.py:4-6` says the env contract "baselines this file" — baselines were burned to zero in rc-2 | Misleading to future authors, zero runtime effect | INFO |
| 6 | Non-strict xfail that XPASSes every run | `tests/unit/infrastructure/test_process_probe_adapter.py::test_pid_zero_documented_as_xfail` | Permanently-XPASS noise in the summary; should be a plain documented test or `strict=True` with a platform guard | INFO |
| 7 | ~29 assertion-free "does not raise" tests | e.g. `test_json_course_store.py::test_delete_nonexistent_is_noop`, `test_bug_reporter.py::test_never_raises_on_write_error` | Verified by reading samples: these are **intentional no-raise contracts** with comments and real failure modes (chmod'd dirs, etc.) — NOT slop; listed for transparency of the scan | NONE |

Not found (hunted explicitly): assert-on-configured-mock tautologies; over-mocked
tests that can't fail; copy-paste families beyond item 3; tests re-implementing the SUT;
volume padding (the per-area counts track real surface — panel's 36 files map to 36
modules/views, not duplicates of one behavior).

## 4. Bug-regression verification table

Each named kernel bug, the test(s) found, and an adversarial would-it-catch verdict:

| Bug | Regression test(s) (read in full) | Would it catch recurrence? |
|---|---|---|
| **Lease theft** (live foreign holder stolen on TTL expiry; in-repo ADDITIVE misclassified MUTATING) | `e2e/test_two_actor_lease.py` (i)+(ii): real busy-past-TTL process, real `OsProcessProbe`, history asserts "B never appears"; `integration/gate/test_classifier_reroot_matrix.py` (incident regression on lock-file content); `unit/.../test_lease_pid_liveness.py::test_acquire_ttl_stale_alive_holder_blocks_no_takeover` | **YES — falsifying.** Reverting the no-steal veto or the classifier re-root flips the journal history / the ALLOW verdict directly. |
| **Ephemeral-pid veto** (lease recorded the dead hook child's pid, making the veto inert) | `e2e/test_two_actor_lease.py` scenario (v): driver spawns the REAL `sdd_gate` hook child; asserts `rec["pid"] == driver_pid` (getppid), then no-steal while driver alive, takeover after driver death | **YES — exact production topology.** Recording the hook child's pid again fails the `rec0["pid"] == driver_pid` assert immediately. |
| **Bind-sid mismatch** (bind mints a sid the harness never reports → mode channel dead) | `integration/gate/test_read_mode_non_acquiring.py::test_cross_sid_read_bind_blocks_mutating_via_incumbent` (+additive twin) at the real hook boundary, zero env vars; `contract/cli/test_cli_context.py::test_context_bind_refreshes_context_incumbent_pointer` pins the CLI side | **YES.** The cross-sid test uses a harness sid ≠ bind sid with no self record — only the incumbent-pointer channel can satisfy it. |
| **Write-only Codex heartbeat** (Codex PostToolUse pinned to write tools → starvation in long Bash calls) | `unit/infrastructure/test_public_assets.py::test_codex_posttooluse_heartbeat_fires_on_all_tools` (omitted matcher = Codex match-all, write gates stay scoped); `unit/hooks/test_sdd_post_gate_behavior.py::test_bash_post_tool_use_renews_held_lease` (real subprocess, Bash payload, heartbeat moves) | **YES, with a documented residual:** the config-shape pin + Bash-payload behavior test catch the regression. The Codex-side semantic "omitted matcher = match-all" is a harness behavior untestable in-repo — acceptable, but it should stay called out (it is, in the test docstring). |
| **Incumbent liveness** (dead leftover lock record defeats a fresh `bind --mode read`) | `unit/hooks/test_sdd_gate.py::test_resolve_mode_dead_leftover_record_does_not_defeat_read_bind` (NF-4, stale hb + pid 0) and `::test_resolve_mode_dead_leftover_record_blocks_mutating_write` (real hook subprocess), with the anti-downgrade inverse `::test_resolve_mode_live_divergent_record_overrides_read_incumbent` | **YES — both directions.** Presence-vs-liveness regression fails the dead-leftover pair; over-correction (ignoring live holders) fails the inverse. |

Additionally `e2e/test_short_heartbeat_triad.py` pins the AC-19 triad (relaunch-renew /
TTL-boundary reclaim parameterised at TTL±1 / forbidden-ceremony wording), and the
disjoint-context scenario (iii) covers gate-cross-context-lock-contamination.

## 5. Skips / xfails inventory

From the single run (2795 passed, 8 skipped, 1 xpassed):

| Skip | Justified? |
|---|---|
| `test_panel.py:345` — no non-loopback IPv4 on host | YES — environmental, runs where a LAN address exists |
| `test_panel.py:381` — memory fixture `.html` not found | **NO — permanently dead** (stale `.html` path post-markdown migration; slop item 1) |
| `test_file_lock_windows.py` ×4, `test_file_permission_windows.py:195`, `test_telemetry_lock_windows.py:129` | YES — Windows-runner-only; these run on the (hard-gated, per v0.1.8 rc-2) Windows CI leg |
| XPASS `test_process_probe_adapter.py::test_pid_zero_documented_as_xfail` | Non-strict xfail that always XPASSes on Linux — noise (slop item 6) |

No xfails hiding real failures. No skip is masking a Linux-leg defect except item 1.

## 6. Score

**9.1 / 10 — the remediation is real.** This is not self-certification echo: every load-bearing
claim I checked against the actual test code held up, and several (lock-journal history
assertions, zero-baseline AST ratchet, driver/hook-child topology) exceed what the re-audit
described.

Deductions, explicit:
- **−0.3** — a permanently-dead e2e test (`test_memory_view_iframe_loads`) that also
  latently targets the real workspace root; stale since the memory-markdown migration and
  it survived two audits and a remediation release unnoticed.
- **−0.2** — panel `test_views_*` family carries near-tautology smoke tests and
  copy-paste assertion redundancy (low value-per-test in the suite's weakest corner).
- **−0.2** — prose-pinning contract minority (codex wording / gate terms) tests
  documentation rather than behavior; brittle to honest rewording and gives a false sense
  of behavioral coverage of the review gate.
- **−0.2** — residual unverifiable seams, honestly documented but still seams: the Codex
  "omitted matcher = match-all" semantic is pinned only as config shape; the two-actor e2e
  compresses TTL by editing the record in place; stale docstring in `test_sdd_post_gate.py`
  and the always-XPASS marker are small hygiene misses that pattern-match to drift.

Not deducted: suite runtime (excellent), pyramid shape (textbook), mock hygiene (best I
have seen at this scale), isolation (two-layer guard with exit-status enforcement).

## 7. Residual actions, ranked

1. **Fix or delete `test_memory_view_iframe_loads`** (`tests/e2e/features/test_panel.py:370`)
   — repoint to `specs/memory/architecture.md` rendering via a tmp workspace fixture (not
   the real workspace root), or delete it as superseded by
   `test_memory_byte_identity.py`. A conditional skip on a path that can never exist is a
   lie in the coverage report.
2. **Promote a Codex-side heartbeat residual note into the contract README** — the
   "omitted matcher = match-all" assumption should be a row in the inventory so the next
   Codex schema change re-verifies it deliberately.
3. **Sweep the panel `test_views_*` family** — drop the `*_returns_string` near-tautologies
   and deduplicate repeated id asserts; ~15-20 tests could go with zero coverage loss.
4. **Make `test_pid_zero_documented_as_xfail` a plain test** (or `strict=True` with a
   platform guard) to kill the permanent XPASS.
5. **Refresh the stale docstring** in `tests/unit/hooks/test_sdd_post_gate.py` (no
   baseline exists anymore).
6. Consider tightening the env-contract visitor to also catch `os.putenv` — currently the
   only un-scanned setenv spelling (deliberate-evasion-only, low priority).
