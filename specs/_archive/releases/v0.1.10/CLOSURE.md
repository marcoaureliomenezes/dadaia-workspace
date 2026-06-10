# Closure: Release — v0.1.10

> **Status:** Aprovado
> **Release ID:** v0.1.10
> **Owner:** product-engineer
> **Closed:** 2026-06-10

## Summary

v0.1.10 ("Concurrency Kernel + Workspace Truth") remediated the full 2026-06-10
project audit (`specs/audits/2026-06-10T010550Z/`, baseline **5/10**) to a final
re-audit verdict of **9.0/10 with all six dimensions ≥ 9 and auditor verdict SHIP**
(`specs/audits/2026-06-10T052944Z/index.md`). The release closed the reproduced
CRITICAL lease-theft incident at root cause: the SDD gate classifier is now
context-relative (in-repo `specs/bugs|backlog|audits` are ADDITIVE and never touch the
lease), lease liveness is real (harness-native heartbeat on every PostToolUse on both
harnesses + a no-steal pid veto recording the long-lived harness pid), session identity
is consolidated in one module, and `bind --mode` actually governs the gate (READ binds
are non-acquiring through the incumbent pointer, with a liveness-correct anti-downgrade
guard).

Around the kernel, the release made the workspace stop lying about itself: the dead
bash hook quartet was retired (Decision D-1), `dadaia specs doctor` gained five ledger
invariants plus an identity-coherence backstop (SPEC-DOC-024..029), the v0.1.9 ledger
was retro-closed and the archive id collision repaired (D-4/D-5), the AI surface's 14
contradictions (C-1..C-14) were rewritten to verified behavior, memory and constitution
were rewritten to the post-fix contract, the security tail (privacy fail-closed
baseline, panel loopback auth, `dead()` review gate + secret scan, token-mode recheck,
dev pins) closed, and anti-drift contracts (single model registry, import-linter cap,
residue greps, consistency-contract-at-introduction policy) now hold the line.

Score journey: **5/10 → 9.0/10** (spec/ledger 4→9, memory 3→9, architecture 6→9.0,
test quality 5→9.25, AI-surface honesty 5→9.0, security 7→9.0).

A subsequent operator-mandated pre-deploy verification audit
(`specs/audits/2026-06-10T140553Z/`) initially failed two lanes and drove an in-release
**rc-3** iteration (tasks T-010-30..34); its delta re-audit closed the release at
**all lanes ≥ 9** (arch 9.2, qa 9.5, spec/ledger 9.5, memory 9.5) — see §rc-3 amendment.

## Tasks completed

All **29 tasks (T-010-00..28) `[x]`**, zero `[ ]`/`[-]` (grep-verified by the final
audit); the rc-3 amendment later appended **T-010-30..34** (all `[x]` at `762b4b6` —
ledger in §rc-3, bringing the release total to 34 tasks). Implementation landed as coordinated **wave commits** on `feature/v0.1.10`
rather than one commit per task; per-task evidence is the task's handoff JSON under
`.dadaia/handoff/dadaia-workspace/` (filenames carry the task id, e.g.
`2026-06-10T024848Z-software-engineer-t-010-03-classifier-reroot.handoff.json`).

Commit ledger:

| Commit | Content |
|--------|---------|
| `a1f331f` | Wave 1 — pre-work + first kernel/test substrate tasks |
| `4acecdf` | Wave 2 |
| `9611f43` | Wave 3 |
| `87b333b` | Wave 4 |
| `09c919e` | Wave 5 |
| `da719cc` | Wave 6 |
| `c7391a0` | Wave 7 — closes the 7-wave implementation of T-010-00..27 |
| `5374495` | Final gate T-010-28 (10/10 checks green) |
| `fc388d7` | rc-2 amendment — NF-1, NF-2, N-2 + security R-2 suffix gap (see §rc-2) |
| `9ca2d2a` | rc-2 final — NF-4 anti-downgrade liveness predicate (HEAD at rc-2 audit SHIP) |
| `e93a7d8` | rc-3 definition — TASKS T-010-30..34 + PE-direct fixes M-1/M-2/M-3, S-1/S-2/S-3 (see §rc-3) |
| `762b4b6` | rc-3 implementation — T-010-30..34 (HEAD at verification-audit PASS) |

Task → workstream map (owners per TASKS.md):

| Tasks | Workstream |
|-------|-----------|
| T-010-00/01/02 | Pre-work: release start; opencode-parity supersession verify; fable-5 registry precondition |
| T-010-10, 03, 07, 04, 05, 08, 09, 06 | Track K — concurrency kernel (R1 classifier re-root, R3 session_identity, R2 heartbeat + pid veto, R4 mode channel, two-actor e2e) |
| T-010-11, 12 | Track T — fixture matrix, kill drift-ratifying tests, 7/7 bug regressions |
| T-010-23, 24, 25, 26, 27 | Track R — model registry + doctor check, ci-preflight self-pollution, pre-push venv probe, contracts/cap |
| T-010-19, 20, 21, 22 | Track S — dead() review gate, privacy fail-closed, panel loopback auth + token mode, dev pins |
| T-010-13, 14, 18, 15, 17, 16 | Track D — bash quartet retirement, doctor ledger invariants, matcher scoping, v0.1.9 retro-CLOSURE + archive repair, AI-surface honesty, memory/constitution truth |
| T-010-28 | Final gate (`5374495`) |

## rc-2 amendment (in-release iteration, re-audit-driven)

**Ledger honesty note:** after all 29 tasks were `[x]` and the final gate passed, the
re-audit's lane passes found four defects in the just-shipped kernel/surface. They were
fixed as an **in-release rc-2 iteration** (`fc388d7`, `9ca2d2a`) per the
release-governance maturity cadence — **TASKS.md carries no T entries for this work**;
this section is its ledger of record.

| Finding | Sev (lane) | Defect | Fix + falsifying test | Commit |
|---------|-----------|--------|----------------------|--------|
| NF-1 (architect; bug `lease-pid-veto-records-ephemeral-hook-pid`) | CRITICAL/HIGH | pid veto inert in production: `lease.acquire` recorded the ephemeral sdd_gate hook subprocess pid, dead before any foreign probe → TAKEOVER of a live holder still possible | `hooks/sdd_gate.py::_resolve_holder_pid` records the long-lived harness pid (payload `harness_pid`/`parent_pid`/`ppid`, else `os.getppid()`), threaded `evaluate(holder_pid=…)` → `lease.acquire(pid=…)`; renew preserves it. `tests/e2e/test_two_actor_lease.py::test_hook_acquired_holder_no_steal_while_driver_alive_then_takeover` + unit pid-resolution tests | `fc388d7` |
| NF-2 (architect; bug `bind-mode-session-record-keyed-by-cli-sid`) | HIGH | bind minted its own CLI sid, so the gate (harness-sid keyed) never found the record — `--mode read` had no effect in a real harness session | gate mode resolution gained the context-incumbent fallback (env → self record → live-checked incumbent `.ptr` → IMPLEMENTATION); bind refreshes the incumbent pointer. `tests/unit/hooks/test_sdd_gate.py::test_resolve_mode_falls_back_to_context_incumbent` (+3) and cross-sid READ subprocess tests in `tests/integration/gate/test_read_mode_non_acquiring.py` | `fc388d7` |
| N-2 (ai lane; bug `codex-posttooluse-heartbeat-matcher-write-only`) | HIGH | Codex PostToolUse heartbeat wired with the WRITE matcher — renewal starvation persisted on the Codex harness | `codex_hooks()` PostToolUse block omits `matcher` (Codex match-all form); PreToolUse stays write-scoped. `tests/unit/infrastructure/test_public_assets.py::TestConfigGenerators::test_codex_posttooluse_heartbeat_fires_on_all_tools` | `fc388d7` |
| NF-4 (architect) | HIGH | anti-downgrade guard tested incumbent record *presence*, not *liveness* — a dead leftover lock record silently defeated a fresh READ bind | `_incumbent_is_stale` consumes canonical `core.lock_liveness.is_stale` with the injected probe (`hooks/sdd_gate.py:197-205`); falsifying tests `tests/unit/hooks/test_sdd_gate.py:465-534` (unit + real-subprocess) | `9ca2d2a` |
| R-2 (security) | LOW | `dead()` secret scan missed binary suffixes (`.pem/.key/.p12`) | suffix scan + `test_dead_with_commit_blocks_on_untracked_pem_key_file` + negative control | `fc388d7` |

rc-2 text amendments (ai-engineer) and the rc-2 lane re-scores (qa 9.25, ai 9.0,
architect 9.0 final at HEAD) are in the handoffs listed under §Review trail. Test count
chain: 2,779 (`f77e96c`) → 2,792 (`fc388d7`) → 2,795 (`9ca2d2a`).

## rc-3 amendment (2026-06-10, verification-audit-driven)

**Why.** After the rc-2 SHIP verdict, the operator mandated an independent pre-deploy
verification audit (`specs/audits/2026-06-10T140553Z/`, lanes: software-architect,
qa-engineer, project-auditor on specs/memory/constitution). At the initial HEAD
(`429ed03`) it **failed two lanes at the ≥9 bar**: architecture **8.5** (A1 HIGH — the
SPEC-DOC-029 lease↔session backstop was dead on arrival: doctor globbed `*.lock` while
lease records are `<ctx>.lock.json`, and `session_identity.coherence()` had zero
callers; plus A2/A3/A4) and memory **8.5** (M-1/M-2/M-3 atom-theater findings). The
release was un-archived from `specs/_archive/` back to `specs/releases/v0.1.10/`, five
tasks T-010-30..34 were appended to TASKS.md under the §rc-3 amendment note (same SPEC
scope — remediation of already-claimed deliverables, no scope change), and PR #53 was
held unmerged pending all lanes ≥ 9.

**Definition commit `e93a7d8`** carried the TASKS amendment plus the PE-direct
(non-task) fixes: M-1/M-2 (`specs/memory/product/sdd/sdd-gate-v3.md` — false
`.html/.yaml/.yml` gate-enforcement claim re-attributed to constitution §3 law; Codex
PostToolUse row corrected to matcher-less match-all), M-3
(`specs/memory/product/index.md` regenerated, generator-verified), S-1/S-2
(constitution §8 — 4-step mode chain; audit-dir naming law grandfather amendment),
S-3 (this CLOSURE's R6 dead "mapping README" reference corrected + drift
`archive-mapping-readme-not-shipped` recorded).

**Implementation commit `762b4b6`** — the five tasks, each with its evidence triple:

| Task | Fix | Evidence (commit + file + named test) |
|------|-----|----------------------------------------|
| T-010-30 | SPEC-DOC-029 backstop made real: doctor reads the real `<ctx>.lock.json` records and delegates to `session_identity.coherence()` (one implementation); CLI wires `workspace_state_dir` | `762b4b6`; `dadaia_workspace/features/specs/doctor.py` + `dadaia_workspace/cli/commands/specs.py:52,123-128`; `tests/unit/features/specs/test_doctor_ledger_invariants.py::test_incoherent_lease_session_via_production_writers_reports_doc_029` (+ coherent negative) and CLI-level `tests/integration/cli/test_cli_specs_doctor_coherence.py::test_cli_doctor_reaches_coherence_check_on_incoherent_state` — incoherence created via the **production writers**, not fabricated fixtures |
| T-010-31 | `session_identity` dead exports pruned; write-only session-keyed `<sid>.ptr` no longer written by `ctx_inject` (GC sweep removed); every surviving public name has a production caller | `762b4b6`; `dadaia_workspace/features/spec_context/session_identity.py` + `dadaia_workspace/hooks/ctx_inject.py`; `tests/unit/features/spec_context/test_session_identity.py::test_coherence_three_disagreeing_sessions_is_reported` (+3 coherence tests) and `tests/contract/test_session_store_ownership.py` |
| T-010-32 | qa-lane test debt: dead-by-skip panel e2e revived against a tmp markdown-memory workspace; always-XPASS xfail made falsifiable; `test_views_*` tautology family consolidated 33→8 behavior-bearing tests, zero coverage loss | `762b4b6`; `tests/e2e/features/test_panel.py::test_memory_view_iframe_loads` (runs, no skip); `tests/unit/infrastructure/test_process_probe_adapter.py::test_pid_zero_returns_a_bool_without_raising`; `tests/unit/features/panel/test_views_*.py` |
| T-010-33 | Layering frozen bidirectionally: 2 reverse-direction import-linter contracts ("core must not import features/infrastructure/cli/hooks", "infrastructure must not import features/cli/hooks", zero ignores); cross-feature `model_resolution → telemetry.pricing` edge removed via `core/model_registry`; ignore cap flat at 17 | `762b4b6`; `setup.cfg:99,110` + `dadaia_workspace/features/public/model_resolution.py`; `tests/unit/features/telemetry/test_pricing.py::test_model_map_and_pricing_table_key_sets_identical` and `tests/contract/test_import_linter_ignore_cap.py` |
| T-010-34 | New doctor WARN **SPEC-DOC-030**: any new `specs/audits/` dir not matching `<YYYYMMDDTHHMMSSZ>-<sid8>` (the four §8-grandfathered dirs and `_archive/` excepted) | `762b4b6`; `dadaia_workspace/features/specs/doctor.py`; `tests/unit/features/specs/test_doctor_ledger_invariants.py::test_non_conforming_new_audit_dir_reports_doc_030_warning` (+ conforming and grandfathered negatives) |

**Delta re-audit outcome (at `762b4b6`,** `specs/audits/2026-06-10T140553Z/index.md`**):**

| Lane | Initial (`429ed03`) | rc-3 delta (`762b4b6`) |
|------|--------------------|------------------------|
| Software architecture | 8.5 FAIL | **9.2 PASS** |
| Test architecture & quality | 9.1 PASS | **9.5 PASS** |
| Spec/ledger fidelity | 9.0 PASS | **9.5 PASS** |
| Memory fidelity | 8.5 FAIL | **9.5 PASS** |

Verdict: **PASS — all dimensions ≥ 9, clear to ship** (operator holds the PR #53 merge
click). Integrated validation at `762b4b6`: full suite **2774 passed / 7 skipped, exit
0** (count down from rc-2's 2,795 by design — T-010-32's 33→8 tautology consolidation
outweighs the rc-3 additions; zero xpassed remains), `dadaia specs doctor` and
`dadaia doctor` both **0 errors**.

**Ledger-honesty notes (auditor INFO, recorded for archaeology):**

1. **The DEFINITION window existed but is invisible in git.** ACTIVE.md was set to
   `phase: DEFINITION` before the rc-3 memory edits (M-1/M-2/M-3 — gate-legal per
   constitution §13), then to `IMPLEMENTATION` for T-010-30..34. The phase flips were
   not committed individually, so the committed history shows the pointer jumping
   none→IMPLEMENTATION; the intermediate DEFINITION state was real on disk and
   gate-enforced, just not a separate commit.
2. **Two files landed outside declared TASKS write sets:**
   `dadaia_workspace/cli/commands/specs.py` (coordinator-authorized CLI wiring so the
   T-010-30 backstop actually runs from `dadaia specs doctor` — the task's write set
   named the feature module but not the CLI entry) and
   `tests/unit/hooks/test_ctx_inject.py` (mechanical consequence of the T-010-31
   ptr-writer removal decoupling `ctx_inject` from the session ptr). Both are
   in-scope-of-intent; recorded here since no write-set line in TASKS.md names them.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| R1 classifier re-root: full class×{root,in-repo}×{slug} matrix, incident regression (ALLOW + holder unchanged), symlink→MEMORY | `pytest -p no:cacheprovider -q tests/unit/features/spec_context/test_gate_policy.py tests/integration/gate/` | audit §3a AC-R1-01/02/03 sampled **PASS** at `9ca2d2a`; `tests/integration/gate/test_classifier_reroot_matrix.py`, `test_classifier_symlink_canonicalization.py` |
| R2 liveness: two-actor e2e (real OS processes) — live holder never loses the lease; ADDITIVE never appears in the lock record; dead-holder takeover; hook-acquired-holder topology | `pytest -p no:cacheprovider -q tests/e2e/test_two_actor_lease.py` | scenarios (i)-(v) green in the HEAD run; audit §1 test-quality 9.25; `fc388d7`/`9ca2d2a` |
| R3 session identity: single-owner residue grep + coherence contract | `pytest -p no:cacheprovider -q tests/contract/test_session_store_ownership.py tests/unit/features/spec_context/test_session_identity.py` | green at `9ca2d2a` (in full-suite run below) |
| R4 mode channel: bind no-mode exits 0; READ non-acquiring via incumbent, no env vars | `dadaia context bind dadaia-workspace` + `pytest tests/integration/gate/test_read_mode_non_acquiring.py` | audit AC-R4-01 sampled **PASS** (`cli/commands/context.py:355-399`, `gate_policy.py:84-112`); final-gate check 9 |
| R5 test kernel: full suite green at HEAD | `pytest -p no:cacheprovider -q` | **2795 passed, 8 skipped, 1 xpassed, exit 0** at `9ca2d2a` (coordinator green run, recorded in audit §6) |
| R6 ledger: doctor invariants live on the repaired ledger | `dadaia specs doctor` | **0 errors / 19 warnings** with SPEC-DOC-024..029 active (audit §3a); v0.1.9 retro-CLOSURE at `specs/_archive/releases/v0.1.9/CLOSURE.md`; archive renames — alpha-N↔milestone mapping preserved in each `specs/_archive/releases/v0.2.0/alpha-N/SPEC.md` header (original milestone id + "Milestone within: v0.2.0"); the SPEC-promised standalone mapping README was never created (see drift `archive-mapping-readme-not-shipped`) |
| R6 surface honesty: contradiction table C-1..C-14 → commit/file:line | (review) | T-010-17 handoff `2026-06-10T044640Z-ai-engineer-t-010-17-honesty-rewrite-continuation.handoff.json`; ai lane re-audit "remaining theater: none" |
| R6 projections clean after quartet retirement + matcher scoping | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | exit 0, `[ok] public-privacy` (final gate checks 5; T-010-13/17/18 handoffs) |
| R7 security tail: loopback 401, dead() review gate + secret scan, privacy baseline, token tighten | `pytest` (panel/auth, spec_context service, privacy_check suites) | AC-R7-01/02/03 green; final-gate check 10 (tokenless loopback → 401); security lane 9.0 at `f77e96c` + architect adversarial probe of the rc-2 diff (audit §2.3) |
| R8 anti-drift: registry single source, key-equality contract, ci-preflight end-to-end, pre-push probe, linter cap | `dadaia ci preflight` + `pytest tests/unit/features/public/test_model_registry_doctor.py tests/unit/public/test_pre_push_gate_venv_probe.py` | final-gate checks 4/7 (`5374495`); `dadaia ci preflight` exit 0 on a clean tree; AC-R8-01..04 |
| Static gates | `ruff format --check && ruff check --no-cache && mypy --strict && lint-imports` | clean at `9ca2d2a` (final gate + coordinator run) |
| Ship bar | (re-audit synthesis) | `specs/audits/2026-06-10T052944Z/index.md` — **all six dimensions ≥ 9, verdict SHIP** |

## Review trail

- **SPEC review (pre-approval):** software-architect (7 findings folded), qa-engineer
  (9 findings folded), software-engineer implementability (S1–S5 folded) — all
  APPROVE-WITH-CHANGES applied before `**Status:** Aprovado` (SPEC header).
- **Implementation review trio:** code-reviewer
  (`2026-06-10T021500Z-code-reviewer-v0110-review.handoff.json`), security-reviewer
  (`2026-06-10T000000Z-security-reviewer-v0110-rc-review.handoff.json` +
  `2026-06-10T052944Z-security-reviewer-v0110-reaudit.handoff.json`), qa-engineer
  (`2026-06-10T230500Z-qa-engineer-v0110-post-impl-review.handoff.json`) — **APPROVE**.
- **Re-audit lanes:** software-architect, qa-engineer, ai-engineer, security-reviewer
  under `specs/audits/2026-06-10T052944Z/` + rc-2 delta re-scores
  (`…-qa-engineer-v0110-rc2-delta-rescore`, `…-ai-engineer-v0110-rc2-delta-rescore`,
  `…-software-architect-v0110-rc2-final-architecture-verdict`).
- **Auditor synthesis:** `specs/audits/2026-06-10T052944Z/index.md` — SHIP at `9ca2d2a`.

## Bugs closed (11 bug files)

8 closed in the original waves + 3 filed-and-closed in rc-2 (`specs/bugs/` frontmatter
is the source of truth; 0 files remain `status: Open`):

| Bug | Sev | Closed by | Named regression |
|-----|-----|-----------|------------------|
| `lease-stolen-by-additive-write-from-live-session` | CRITICAL | T-010-03/04/05 | `tests/e2e/test_two_actor_lease.py::test_holder_busy_foreign_additive_allowed_and_never_named`; `tests/integration/gate/test_classifier_reroot_matrix.py::test_lease_theft_incident_in_repo_additive_does_not_steal` + `::test_lease_theft_dual_session_foreign_mutating_still_blocks_live_holder` |
| `ci-preflight-self-pollution-gate-never-passes` | HIGH | T-010-25 | `tests/unit/features/ci_preflight/test_no_pollution.py`, `test_pollution_guard_diff.py`, `test_service.py` |
| `gate-fpath-not-canonicalized-before-classifier` | MEDIUM | T-010-03 (Python) + T-010-13 (bash retired) | `tests/integration/gate/test_classifier_symlink_canonicalization.py`; `tests/contract/test_bash_hook_residue.py` |
| `context-bind-forces-mode-choice-on-operator` | MEDIUM | T-010-08 | `tests/contract/cli/test_cli_context.py::test_context_bind_no_mode_exits_zero_default_read` + `::test_context_bind_no_mode_prints_human_confirmation` |
| `model-catalog-modelmap-pricing-drift-no-registry` | MEDIUM | T-010-23/24 | `tests/unit/features/public/test_model_registry_doctor.py` + MODEL_MAP↔PRICING_TABLE key-equality contract |
| `pre-push-gate-cannot-locate-workspace-venv` | MEDIUM | T-010-26 | `tests/unit/public/test_pre_push_gate_venv_probe.py` (7 tests incl. `::test_branch2_walk_up_to_workspace_venv`, `::test_none_found_fails_closed`) |
| `opencode-parity-test-asserts-stale-bash-script-ref` | MEDIUM | T-010-01 — `superseded_by: v0.1.8` (bug-always-solved law: supersession recorded, not dropped) | `tests/e2e/features/test_opencode_parity_hardening.py::TestPluginProjection::test_sdd_gate_plugin_projected` |
| `v0110-cross-test-session-state-pollution-order-sensitive` | LOW | verified NOT REPRODUCIBLE on the integrated tree (T-010-07/10/11 isolation) | full-suite + named-victim-order repro commands green (recorded in the bug file) |
| `lease-pid-veto-records-ephemeral-hook-pid` (rc-2) | HIGH | `fc388d7` (NF-1) | `tests/e2e/test_two_actor_lease.py::test_hook_acquired_holder_no_steal_while_driver_alive_then_takeover` + unit pid-resolution tests in `tests/unit/hooks/test_sdd_gate.py` |
| `bind-mode-session-record-keyed-by-cli-sid` (rc-2) | MEDIUM | `fc388d7` (NF-2) | `tests/unit/hooks/test_sdd_gate.py::test_resolve_mode_falls_back_to_context_incumbent` (+ `_self_record_wins_over_incumbent`, `_incumbent_ignored_when_live_holder_differs`, `_incumbent_honored_when_no_lease_holder`); `tests/integration/gate/test_read_mode_non_acquiring.py` cross-sid tests |
| `codex-posttooluse-heartbeat-matcher-write-only` (rc-2) | HIGH | `fc388d7` (N-2) | `tests/unit/infrastructure/test_public_assets.py::TestConfigGenerators::test_codex_posttooluse_heartbeat_fires_on_all_tools` |

## Drifts

### rc-2-in-release-iteration

**Description:** The re-audit (after 29/29 `[x]` and a green final gate) surfaced four
real defects (NF-1/NF-2/N-2/NF-4) — the pid veto and bind-mode channel were inert in
the harness-real topology, the Codex heartbeat matcher was write-only, and the
anti-downgrade guard ignored liveness. PLAN/TASKS had no provision for a re-audit fix
loop.

**Resolution:** Fixed as an in-release rc-2 amendment (`fc388d7`, `9ca2d2a`) under the
release-governance rc cadence, with falsifying tests and lane re-scores, instead of
opening v0.1.11 for kernel correctness. Documented honestly in §rc-2 above since
TASKS.md carries no T entries for it.

**Memory updates:** `specs/memory/architecture.md`, `specs/memory/product/sdd/sdd-gate-v3.md`,
`specs/memory/product/platform/context-management.md` describe the **post-rc-2**
contract (harness-pid recording, incumbent fallback, match-all Codex PostToolUse,
liveness-correct anti-downgrade) — verified line-for-line by the auditor (§3b MATCH table).

### segment-label-vs-flat-layout

**Description:** `ACTIVE.md` carried `segment: alpha-1` while the release was
implemented flat (`releases/v0.1.10/{SPEC,PLAN,TASKS}.md`, no segment subdir) — the
auditor's LOW label nit (§3a).

**Resolution:** `segment:` line dropped at closure. Convention (continuing the v0.1.9
closure layout decision): single-segment releases use the flat layout and OMIT the
`segment:` field; `segment:` appears only when artifacts actually live under
`releases/<id>/<segment>/`.

**Memory updates:** none (ledger-only).

### tech-stack-dependency-rows-stale

**Description:** Auditor DRIFT-M1/M2 (LOW): `tech-stack.md` called Jinja2 a
"transitive dependency" though `pyproject.toml:37` declares `jinja2 = "^3.1"` direct
and `features/specs/scaffolder.py:14-15` imports it; and pinned `rich ^13` vs the
actual `rich = ">=13,<16"`.

**Resolution:** Both rows corrected at closure (jinja2 added to the approved-deps table
as a direct runtime dep of the SDD scaffolder; rich range aligned).

**Memory updates:** `specs/memory/tech-stack.md`.

### transient-cross-test-pollution

**Description:** Mid-release, order-sensitive cross-test session-state pollution was
filed (LOW) against the in-flight working tree (T-010-04/05/08 partially integrated).

**Resolution:** Verified not reproducible on the integrated tree (isolation supplied by
T-010-07/10/11); bug closed with the repro commands green. No plan change.

**Memory updates:** none.

### archive-mapping-readme-not-shipped

**Description:** SPEC D-4/D-5 and T-010-15 promised a standalone "mapping README" for
the `_archive/releases/v0.2.0/` alpha-N renames; the rc-3 verification audit
(2026-06-10T140553Z, finding S-3) confirmed no such README exists anywhere under
`specs/_archive/` — the original R6 evidence row cited a non-existent artifact.

**Resolution:** Claim corrected at rc-3 (this amendment). The mapping is in fact
preserved — each renamed `alpha-N/SPEC.md` header retains its original milestone id
plus a "Milestone within: v0.2.0" line, so archaeology is fully recoverable without a
separate README. The standalone README is dropped as redundant rather than
retro-created inside the FROZEN archive.

**Memory updates:** none.

## Memory updates

Written in the CLOSURE phase (T-010-16, operator-confirmed for the constitution; plus
the closure nit fixes above):

- `specs/memory/architecture.md` — concurrency model rewritten to the verified post-fix
  contract: context-relative classifier taxonomy, PostToolUse heartbeat liveness,
  pid-veto/no-steal, session-identity module, mode channel, bash quartet removed,
  doctor invariants.
- `specs/memory/product/sdd/sdd-gate-v3.md` — class×location taxonomy, mode-resolution
  order, liveness contract, harness-pid recording.
- `specs/memory/product/platform/context-management.md` — bind semantics (mode optional,
  default read; incumbent pointer; no eval-export theater).
- `specs/memory/product/sdd/specs-doctor.md` — SPEC-DOC-024..029 ledger invariants +
  identity-coherence backstop.
- `specs/memory/tech-stack.md` — model registry single source + tier table; dev/tooling
  pins; closure fixes: jinja2 listed as a direct dep (scaffolder), rich `>=13,<16`.
- `specs/constitution.md` — §0/§8 concurrency/lifecycle claims rewritten to enforced
  reality (explicit operator confirmation obtained before commit).
- `specs/memory/product/index.md` / `catalog.json` — no change: no feature added or
  removed; catalog order unchanged.

rc-3 additions (DEFINITION window for M-1/M-2/M-3 at `e93a7d8`; CLOSURE polish after
the delta re-audit):

- `specs/memory/product/sdd/sdd-gate-v3.md` — M-1/M-2 (format-law claim re-attributed
  to constitution §3; Codex PostToolUse row → matcher-less match-all); closure polish:
  doctor format check stated to exact truth (`.html` only via SPEC-DOC-002L; no
  `.yaml/.yml` check exists — audit INFO residual).
- `specs/memory/product/index.md` — M-3: regenerated to frontmatter/catalog truth
  (generator-verified byte-identical thereafter).
- `specs/memory/product/sdd/specs-doctor.md` — SPEC-DOC-030 audits-naming WARN added
  to the ledger-invariant inventory (T-010-34).

## Backlog returns

- `specs/backlog/v0.1.11-audit-residuals.md` ← the auditor's 10 ranked residuals
  (audit §5), filed as ONE candidate (status CANDIDATE, PM-authorized at closure):
  probe-less CLI side doors (`lock steal` / `lease._main`), lifecycle-asymmetry map
  mechanical enforcement, bind-record GC decay, session-path ownership residue grep,
  panel `?token=` launch URL, ctx-inject bootstrap bloat + sentinel GC, public-source
  hygiene (`__pycache__`/xlsx), remaining doc/ledger nits, opportunistic venv tooling
  bumps, escape-record time-earned axis + WARN cleanups.
- `specs/backlog/candidates.md` ← index entry pointing at the file above.

## Archive decision

**MOVE** — release directory moves to `specs/_archive/releases/v0.1.10/` via `git mv`
(coordinator-run). `ACTIVE.md` then reads `release: none` / `phase: none` (the scaffold
default; `dadaia specs doctor` skips all release-gated checks for `release: none` and
accepts phase `none` as canonical) in the **same commit** as the move, so the pointer
never names a moved directory.
