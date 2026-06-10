# Test-Quality RE-AUDIT — dadaia-workspace after v0.1.10

- **Auditor:** qa-engineer (re-audit of own lane, baseline `specs/audits/2026-06-10T010550Z/qa-engineer.md`)
- **Date:** 2026-06-10T052944Z
- **Scope:** `tests/` at `feature/v0.1.10` HEAD `f77e96c` (2,788 tests collected) vs the 5 systemic defects and the 32-bug escape matrix of the baseline audit
- **Mode:** AUDIT ONLY — verification by reading + targeted/full test runs; no production or test edits

---

## Verdict in one paragraph

The v0.1.10 release answered the baseline audit on its own terms, and the answer is mostly
structural, not cosmetic: the fictional environment is gone at every surface that bled
(harness-env fixture + subprocess channel, enforced by an honest growth-only ratchet), the
fixture monoculture is matrixed at the kernel (location × slug × context-count), all seven
named drift-ratifiers are dead and replaced by single-source contracts, a real consistency
tier exists with a binding at-introduction policy, and the two-actor e2e is genuine
falsification — real OS processes, the real pid probe, the real gate subprocess, invariants
asserted on the lock-file *history*. The ~270 added tests are high quality; I found no slop.
What remains short of a clean bill: the env-fidelity ratchet still carries a baseline
(32 setenvs / 4 in-process hook unit files, burn-down slated v0.1.11), the
lifecycle-asymmetry defect is fixed by policy + kernel-surface examples but has no
retroactive coverage map and no mechanical enforcement, and the escape-record axis can only
be re-earned by a cycle in which bugs stop escaping past green tests — that cannot be bought
in the same release that wrote the tests.

**Test-quality score: 8.5/10** (was 5/10). Per-axis at end.

---

## 1. Per-defect verdicts

### Defect 1 — Single-context / single-session fixture monoculture → **RESOLVED (kernel surfaces)**

Verified:
- `tests/unit/features/spec_context/test_lease_activity_exemption.py` — the exemption
  matrix is re-rooted and parametrized over `{root, in_repo} × {default, non-default slug}`
  on top of class × lease-state (the 64-cell matrix, lines 118–147). The docstring names
  the original blind spot honestly ("certified a class taxonomy that was dead for every
  compliant workspace").
- `tests/unit/features/spec_context/test_lease_property.py` — parametrized over
  location × slug **and** `{one_ctx, two_ctx}` (lines 110–158).
- `tests/integration/gate/test_classifier_reroot_matrix.py` (T-010-03) — drives the whole
  `gate_policy.evaluate` pipeline (classify → lease) for in-repo paths under both
  `dadaia-workspace` and `rand-engine` slugs; asserts the lease record stays *absent* for
  ADDITIVE (FR-R1-01) and the holder stays untouched in the incident regression
  (FR-R1-08), on file content, not return values.
- Two-actor e2e scenario (iii) — two ALIVE contexts mutating disjoint repos concurrently,
  no cross-block (the gate-cross-context-lock-contamination regression at the process tier).

Residual: the matrix discipline is applied where the baseline showed bleeding (gate, lease,
classifier); it is not retrofitted to every fixture in the suite (panel/renderer fixtures
are still mostly default-slug). Acceptable — the unfalsifiable-fallback class is closed at
the surfaces where the fallback exists.

### Defect 2 — Simulated harness environment → **SUBSTANTIALLY RESOLVED; ratchet honest, baseline caps the score**

Verified:
- `tests/fixtures/harness_env.py` is exactly the corrective the baseline demanded (§6.1):
  pinned-minimal env per harness (`claude_hook_env`/`codex_hook_env`), explicit scrub list
  of vars no harness delivers (`DADAIA_SESSION_ID`, persona, mode, foreign session ids),
  `ValueError` on injecting a non-allowlisted `DADAIA_*`, and `run_hook_subprocess` as the
  single sanctioned behavior channel (`python -m dadaia_workspace.hooks.<name>`, stdin JSON
  envelope — the way the harness actually spawns hooks). The verification source is cited
  (hooks' own env reads + the pre-existing gate subprocess tests).
- Adoption is real, not decorative: `test_two_actor_lease.py`,
  `test_classifier_incident_hooklevel.py`, `test_classifier_symlink_canonicalization.py`,
  `test_read_mode_non_acquiring.py`, `test_sdd_post_gate_behavior.py` all drive hooks
  through `run_hook_subprocess`.
- The worst baseline offender — `tests/unit/gate/test_post_gate_heartbeat.py` with its
  test-planted `DADAIA_SESSION_ID` heartbeat (17-D3) — **no longer exists**; the directory
  holds only `__init__.py`. Heartbeat behavior now lives in the short-TTL triad e2e and the
  post-gate behavior subprocess tests.
- `tests/contract/test_harness_env_contract.py` enforces the discipline with an AST scan
  (not grep — catches `os.environ[...]=`, `setdefault`, `update`, `monkeypatch.setenv`),
  growth-only baselines, **and anti-rot meta-tests in both directions**:
  `test_baseline_does_not_overcount` (a file that improves must lower its baseline) and
  `test_baseline_files_still_exist` (a migrated file must leave the baseline). The ratchet
  cannot silently rot; it can only bite.

Judgment on ratchet-with-baseline: this is the correct engineering for landing the regime
green — the baseline is recorded current reality, self-auditing, and named for burn-down
(T-010-11 follow-through, v0.1.11). But the axis is *environment fidelity*, and until the
baseline is zero, 7 files still write `DADAIA_*` out-of-fixture and 4 hook unit files
(`test_ctx_inject`, `test_root_whitelist`, `test_sdd_gate`, `test_sdd_post_gate`) still
exercise hook modules in-process — the exact channel through which 17-D3 was certified
dead-green. A ratchet prevents *new* fiction; it does not retire the existing fiction.
**Score effect: env fidelity 1.5/2, capped by the baseline, not by the design.**

### Defect 3 — Drift-ratifying assertions → **RESOLVED (all named ratifiers killed)**

Verified kills, one for one against the baseline §3 list:
- Lease ADDITIVE root-only pins (`test_lease_property.py:74` / `test_lease_activity_exemption.py:27`,
  bug 17-D1) → re-rooted matrices above; the in-repo form is now the asserted form.
- Pricing↔mapping contradiction (bug 18) → both tables are now **derived views over
  `core.model_registry`** with key-equality asserted three ways:
  `set(MODEL_MAP) == registry claude_ids` (`test_model_mapping.py:51`),
  `set(PRICING_TABLE) == registry claude_ids` and `set(MODEL_MAP) == set(PRICING_TABLE)`
  (`test_pricing.py:235–242`). The brittle `len(MODEL_MAP) == 5` pin was removed with a
  docstring explaining why. `tests/contract/test_retired_model_id_residue.py` greps the
  retired `claude-haiku-3-5` id out of live code permanently.
- Stale opencode pin (bug 19) → assertion flipped: `test_opencode_parity_hardening.py:128-129`
  now asserts `"dadaia_workspace.hooks.sdd_gate" in text` **and** `"sdd-spec-gate.sh" not in
  text`; `tests/contract/test_bash_hook_residue.py` kills the retired-bash-quartet class.
- Install-skip lineage (bug 15) → `test_install_skip_idempotent.py` now lives in
  `tests/contract/` pinning idempotency-across-newline-conventions (the contract), not
  skip-on-exists (the optimization).
- Task-manager / review-gate contract re-pinned: `tests/contract/test_workflow_review_gate_contract.py`.

### Defect 4 — No cross-component consistency tier → **RESOLVED**

`tests/contract/` is now a real tier: 14 inventoried contracts (cap on import-linter
ignores ≤17, model-id residue, bash-hook residue, harness-env ratchets, session-store and
session-bound-context residues, source-repo hygiene, handoff schema, platform classifiers,
reports retention, codex wording, review gate, CLI contracts), every file
`pytest.mark.contract`, README carries the inventory table with an "add a row in the same
change" rule. The **consistency-contract-at-introduction** policy is binding prose in both
`tests/contract/README.md` and `specs/AGENTS.md` ("never land the pairing first and the
guard later"). All 140 e2e+contract tests pass (run evidence below).

### Defect 5 — Lifecycle asymmetry → **PARTIALLY RESOLVED (policy + kernel examples; no retroactive coverage, no enforcement)**

What exists:
- Binding policy in `specs/AGENTS.md` ("Lifecycle-Asymmetry Coverage": delete/orphan, dirty
  input, missing dependency — "Silence is not coverage; an undocumented asymmetric path is
  a gap") mirrored in `tests/contract/README.md` with the residue-grep canonical form.
- The release itself practiced it where it touched: dead-holder takeover (delete),
  symlink-into-memory (dirty/hostile input), pre-push venv probe fail-CLOSED when no runner
  found (missing dependency), holder-busy-past-TTL (time × concurrency composed — the exact
  17-D2 gap).

What does not exist: a retroactive per-feature coverage map for the pre-existing surface,
and any mechanical check that the "documented justified absence" actually gets written
(doctor/CI do not verify it). This is the same enforcement gap the baseline flagged for
`tests/tmp/` conventions. Honest verdict: the *defect instances* are closed; the *systemic
guarantee* is a convention awaiting either a sweep or an enforcement hook.

---

## 2. Two-actor e2e — is it real falsification?

**Yes.** `tests/e2e/test_two_actor_lease.py` is the strongest artifact in the suite:

- Real OS subprocesses driving the **real** lease and the **real** `sdd_gate` hook
  subprocess, wired with the **real platform-seamed `OsProcessProbe`** — genuinely
  alive/dead PIDs, not fakes.
- All four AC-R2-04 invariants: (i) holder busy past TTL + foreign in-repo ADDITIVE write
  → ALLOW and the lock history never names the foreign session (the exact 2026-06-10
  lease-theft incident); (ii) foreign MUTATING vetoed while the holder pid is alive,
  including the forbidden-law assertion that the yield message never instructs a manual
  unblock ceremony; (iii) disjoint contexts no cross-block; (iv) dead-holder takeover after
  the process genuinely exits and the OS reaps the pid.
- Invariants asserted on the **lock-file history** (`LockJournal`), not return values, and
  the journal itself has a meta-test (`test_journal_records_raw_lock_versions`) proving it
  reflects the literal on-disk record — the measuring instrument is calibrated.
- Bounded file rendezvous throughout (`wait_for_file`/`wait_until` with deadlines, short
  injected TTL); no blind `time.sleep` of the full duration, leaked children self-terminate.

This generalizes `test_two_process_denial.py` from one-off to standing pattern, exactly as
the baseline §6.2 demanded. Pre-fix, scenarios (i) and (ii) fail by construction — this is
falsification, not ratification.

## 3. Escape-matrix delta

Baseline: 32 bugs — 14 no-test, 16 blind, 2 untestable; 5 still Open (12, 17, 18, 19, 27).
Current: **zero bugs with `status: Open` in `specs/bugs/`**. The T-010-12 closure commit
(`c7391a0`) closes 8/8 in-scope bugs each with **named** regression tests, verified to exist
and pass:

| Bug (baseline #) | Named regression now in tree |
|---|---|
| 12 gate-fpath-not-canonicalized | `tests/integration/gate/test_classifier_symlink_canonicalization.py` — real subprocess, symlink → MEMORY classification (was no-test) |
| 17 lease-stolen (D1/D2/D3) | `test_two_actor_lease.py::test_holder_busy_foreign_additive_allowed_and_never_named` + `test_classifier_reroot_matrix.py::test_lease_theft_*` (D1 re-root, D2 time×concurrency composed, D3 heartbeat test deleted + subprocess behavior tests) |
| 18 model/pricing drift | registry key-equality contracts (both tables) + `test_retired_model_id_residue.py` |
| 19 opencode stale pin | assertion flipped + `test_bash_hook_residue.py` |
| 27 pre-push venv probe | `tests/unit/public/test_pre_push_gate_venv_probe.py` — drives the real shell script in `--probe-only`, asserts the 4-step resolution order **and fail-CLOSED** |
| 9 bind forces --mode | closed; `dadaia context bind <ctx>` no-flag is final-gate acceptance item (9) |
| + ci-preflight self-pollution, test-session-state-pollution | closed with conftest pre/post snapshot guard rescope (T-010-25) |

The baseline's most damning pattern — "fixes ship WITH the regression test that would have
caught the bug" — is now inverted where it matters: the two-actor suite and the re-rooted
matrices were written to *falsify the buggy kernel*, and the at-introduction policy targets
the root cause (guards landing after pairings).

## 4. New-test quality (slop scan of the ~270 added)

~221 new test functions across 49 changed files (`git diff 73164c9..f77e96c -- tests/`).
Sampled in depth: `test_two_actor_lease.py`, `test_harness_env_contract.py`,
`test_classifier_reroot_matrix.py`, `test_classifier_symlink_canonicalization.py`,
`test_lease_activity_exemption.py`, `test_pre_push_gate_venv_probe.py`. Findings:

- **No slop found.** No tautologies, no mock-the-world (mock density stays near zero — the
  new tests use real subprocesses, real files, real probes), no copy-paste batteries
  (parametrize does the fan-out: the 64-cell matrix is one function).
- Quality markers above the suite's prior bar: AST-based contract scanning instead of
  brittle regex; meta-tests that calibrate the measuring instruments (journal verbatim,
  baseline overcount/underclaim); docstrings that cite the bug, task, FR/AC ids, and the
  audit finding they answer; PATH-from-scratch isolation in the shell-probe tests with an
  explicit comment on why host-PATH assertions were wrong.
- One structural caution, not slop: the ratchet baselines are hand-maintained data tables
  inside a test file — exactly the "hand-maintained pairing" class the new policy governs.
  They are self-guarded (the anti-rot tests), so compliant with their own law.

## 5. Run evidence

- `tests/e2e/test_two_actor_lease.py + test_two_process_denial.py + test_short_heartbeat_triad.py + tests/contract/` → **140 passed** (28.0s).
- `tests/integration/gate/ + tests/unit/features/spec_context/ + tests/unit/hooks/ + pricing + model_mapping + test_opencode_parity_hardening.py` → **372 passed** (6.7s).
- Full suite `pytest -p no:cacheprovider tests/` → **2,779 passed, 8 skipped, 1 xpassed, exit 0** (2,788 collected; 120s; skips are platform/feature guards, the xpass is a documented platform-defined PID-0 probe).
- Preflight e2e exit 0: final-gate acceptance item (1)–(10) recorded in T-010-28
  (`5374495`), including `dadaia ci preflight` exit 0 end-to-end and panel tokenless 401;
  consistent with the conftest pollution-guard rescope verified above.

---

## 6. Score: 8.5/10 (was 5/10)

| Axis | Was | Now | Justification |
|------|-----|-----|---------------|
| Mechanical craft | 2/2 | **2/2** | Bar held and raised: AST contracts, bounded rendezvous, calibrated instruments, zero new mocks |
| Contract fidelity | 0.5/2 | **2/2** | All 7 named ratifiers dead; single-source registry contracts; at-introduction policy binding + inventoried tier |
| Environment fidelity | 0.5/2 | **1.5/2** | Harness-env fixture + subprocess channel adopted at every bug-bearing surface; worst offender deleted; matrices kill the monoculture. Capped by the ratchet baseline: 32 out-of-fixture setenvs in 7 files + 4 in-process hook unit files remain (burn-down v0.1.11) |
| Adversarial coverage | 1/2 | **1.5/2** | Time×concurrency composed, delete/dirty/missing-dep all exercised at the kernel; lifecycle-asymmetry policy binding. Capped: policy is not retroactive and has no mechanical enforcement |
| Escape record | 1/2 | **1.5/2** | 0 Open bugs, 8/8 closed with named falsifying regressions, root-cause policy targets the grows-by-post-mortem pattern. Capped: this axis is earned by the *next* cycle producing no escapes past green tests — it cannot be awarded in the release that wrote the tests |

### What blocks 9 (real gaps, in priority order)

1. **Ratchet burn-down to zero** (env fidelity → 2/2): migrate the 4 in-process hook unit
   files to `run_hook_subprocess` (or demonstrate they are pure-classification tests) and
   eliminate the 32 baselined `DADAIA_*` setenvs; delete both baselines. Already slated
   v0.1.11 — finishing it is the single cheapest +0.5.
2. **Lifecycle-asymmetry enforcement** (adversarial → 2/2): a one-time retroactive
   per-feature coverage map (tests or justified absence) plus a mechanical check (doctor or
   a contract test that every feature dir/atom carries the asymmetry record), so the policy
   cannot decay into the same convention-only state as the old `tests/tmp/` rule.
3. **Escape record** (→ 2/2): time-earned — one release cycle in which no bug escapes past
   a green test on its surface. Not purchasable; do 1 and 2 and let the cycle run.

---

*Audit artifacts: this file. No production, test, or spec files were modified. Evidence:
read-only inspection + pytest runs recorded in §5.*
