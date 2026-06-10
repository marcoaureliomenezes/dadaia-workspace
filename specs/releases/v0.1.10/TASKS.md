# TASKS: v0.1.10 — Concurrency Kernel + Workspace Truth

**Status:** Aprovado
**Release ID:** v0.1.10
**Owner:** product-engineer
**Created:** 2026-06-10 (revised same day for the R1–R8 extension)

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

Tracks K (kernel), T (tests), R (registries/push-gates), S (security), D (truth) are
safe to run in parallel **across** tracks with one declared exception: T-010-13
(Track D) shares `gate_policy.py` with T-010-03 (Track K) and is sequenced after it —
the file-disjoint claim does not hold for that pair. Within a track, respect the
listed preconditions. Hard spine: T-010-00 → 10 → 03 → 07 → {04,05,08} → {09,06} →
11 → 12 (plus 03 → 13); T-010-16 runs last (CLOSURE phase). Maximum one `[-]` per
owner unless tasks are in different tracks (disjoint write sets declared here).

---

## Pre-work

### [x] T-010-00 — Release start: ACTIVE.md → v0.1.10 — DONE: executed by product-engineer at approval (2026-06-10); ACTIVE.md phase set to IMPLEMENTATION per arch A5 release-start split.
- **Owner:** product-engineer · **Maps:** arch A5 (SPEC review), CONF-5; Decisions D-4/D-5 prelude
- **Write set:** `specs/releases/ACTIVE.md`
- **Preconditions:** SPEC+PLAN+TASKS Aprovado.
- **Acceptance:** `ACTIVE.md` reads `release: v0.1.10` / `phase: IMPLEMENTATION`
  **before any Track K work begins**, so gate legality and the new phase↔markers
  doctor invariant (T-010-14) hold for the whole release. The v0.1.9 retro-CLOSURE +
  archive repair remain in T-010-15 (unchanged).
- **Parallelism:** runs first, before all tracks.

### [x] T-010-01 — VERIFY: opencode-parity bug superseded by v0.1.8
- **Owner:** software-engineer · **Maps:** bug `opencode-parity-test-asserts-stale-bash-script-ref`, DRIFT-7
- **Write set:** `specs/bugs/opencode-parity-test-asserts-stale-bash-script-ref.md` (frontmatter only)
- **Acceptance:** `pytest -p no:cacheprovider -q tests/e2e/features/test_opencode_parity_hardening.py::TestPluginProjection::test_sdd_gate_plugin_projected` passes at HEAD; line 129 reads `assert "sdd-spec-gate.sh" not in text`. Bug set `status: Closed`, `superseded_by: v0.1.8`; pytest output captured for CLOSURE.
- **Parallelism:** independent; run first.

### [x] T-010-02 — VERIFY: claude-fable-5 registry precondition
- **Owner:** software-engineer · **Maps:** bug `model-catalog-modelmap-pricing-drift-no-registry` (precondition)
- **Write set:** none (read-only)
- **Acceptance:** `claude-fable-5` present in `MODEL_MAP` and `PRICING_TABLE` (python -c asserts); 5 agent `.md` files carry `model: claude-fable-5`. Evidence recorded.
- **Parallelism:** independent; gates T-010-23.

---

## Track K — Concurrency kernel

### [x] T-010-10 — R5: harness-env fixture contract (FIRST in track)
- **Owner:** software-engineer · **Maps:** CONF-6, qa defect 2, qa §6.1; bug `lease-stolen…` D3 (test side)
- **Write set:** `tests/fixtures/harness_env.py` (new — NOT `tests/conftest.py`, avoids colliding with T-010-25), `tests/contract/test_harness_env_contract.py` (new)
- **Preconditions:** T-010-00.
- **Acceptance (AC-R5-01):** `claude_hook_env()` / `codex_hook_env()` fixtures with pinned-minimal env + subprocess hook-runner helper exist; env contract test covers the **whole `DADAIA_*` namespace** with an explicit allowlist (e.g. `DADAIA_CONTEXT` operator-shell var) and fails any hook/gate/lease test that setenvs a non-allowlisted `DADAIA_*` outside the fixtures; second contract test flags direct hook-module import+call in `tests/**/hooks|gate/**` (behavior tests must use the subprocess runner — closes the `os.environ.update` evasion); new tests green on Windows/macOS CI legs; existing suites still green.
- **Parallelism:** independent of all other tracks; blocks T-010-03/04/05/09 acceptance.

### [x] T-010-03 — R1: classifier re-root — full class×location taxonomy
- **Owner:** software-engineer · **Maps:** CONF-1, arch F1, sec F-1, ai D-3/D-4/D-5/C-1; bugs `lease-stolen…` (D1), `gate-fpath-not-canonicalized-before-classifier` (Python surface)
- **Write set:** `dadaia_workspace/features/spec_context/gate_policy.py`, `tests/unit/features/spec_context/test_gate_policy.py`, `tests/integration/gate/` (matrix + symlink + incident regression)
- **Preconditions:** T-010-10.
- **Acceptance (AC-R1-01/02/03):** FR-R1-01..08 — matrix tests class×{root,in-repo}×{default,non-default slug}; in-repo MEMORY phase-rule and FROZEN block exercised (`gate_policy.py:90-93,137-143` no longer dead); symlink→MEMORY regression test named; full-pipeline incident regression (dual-session, injected clock, ALLOW + holder unchanged in lock record); full gate integration matrix green; **explicit re-baseline** of existing gate/lease tests whose expected class changes under the re-root (~30-60 assertions; HIGH blast radius — acknowledged in PLAN risk note) — each flipped expectation re-derived from the new taxonomy, not mechanically inverted.
- **Parallelism:** spine; before T-010-07.

### [x] T-010-07 — R3: session_identity consolidation module
- **Owner:** software-engineer · **Maps:** arch F7, CONF-1/2 substrate
- **Write set:** `dadaia_workspace/features/spec_context/session_identity.py` (new), `dadaia_workspace/features/spec_context/lease.py` (pointer reads), `dadaia_workspace/hooks/ctx_inject.py`, `dadaia_workspace/features/spec_context/doctor.py` (PTR-GC, `:126,572-581`), `dadaia_workspace/core/specs_resolver.py` (`:19`) — both consume the session stores R3 consolidates and would fail FR-R3-01's residue grep if left unmigrated — `tests/unit/features/spec_context/test_session_identity.py` (new), `tests/contract/test_session_store_ownership.py` (new)
- **Preconditions:** T-010-03.
- **Acceptance (AC-R3-01):** FR-R3-01..03 — single owner module; residue grep contract proves no other module opens `sessions/runtime/*.ptr` / `sessions/<id>.json`; coherence contract (lock holder vs incumbent vs session record); workspace-doctor PTR-GC/SENTINEL-GC consumers of `sessions/runtime/*.ptr` updated/verified against the collapsed store; legacy artifacts ignored-and-superseded; pytest green.
- **Parallelism:** spine; before T-010-04/05/08.

### [x] T-010-04 — R2a: PostToolUse heartbeat, harness-native session id
- **Owner:** software-engineer · **Maps:** CONF-2, arch F2, ai D-12; bug `lease-stolen…` (D2/D3)
- **Write set:** `dadaia_workspace/hooks/sdd_post_gate.py`, `tests/unit/hooks/test_sdd_post_gate.py`
- **Preconditions:** T-010-07, T-010-10.
- **Acceptance (AC-R2-01):** FR-R2-01/02 — session id from stdin payload (`resolve_session_id`), env as override only; renewal context resolved from the session_identity record / leases held by this sid (NOT `DADAIA_CONTEXT`→first-ALIVE; first-ALIVE documented last resort only); renew called outside any session-file guard; subprocess test under `claude_hook_env()` (no hand-planted env) observes fresher lease heartbeat after a simulated Bash PostToolUse; fail-open exit 0 on all errors; no-session-file variant passes; green on Windows/macOS CI legs.
- **Parallelism:** parallel with T-010-05/08 (disjoint files).

### [x] T-010-05 — R2b: pid-liveness probe before TAKEOVER + holder-safe renew
- **Owner:** software-engineer · **Maps:** CONF-2, arch F2 (PID lesson restored), C-14
- **Write set:** `dadaia_workspace/features/spec_context/lease.py`, `dadaia_workspace/features/spec_context/gate_policy.py` (`pid_probe` must thread through `gate_policy.evaluate` — `gate_policy.py:147` is the sole caller of `lease.acquire`), `dadaia_workspace/hooks/sdd_gate.py` (sources `OsProcessProbe` from `container.py`), `dadaia_workspace/core/lock_liveness.py` (explicit EDIT target, not "(consume)": activate the never-called `pid_probe` param; rewrite the stale docstring at `:11-13,54-56`), `tests/unit/features/spec_context/test_lease_*.py`
- **Preconditions:** T-010-07.
- **Acceptance (AC-R2-02/03):** FR-R2-03/04 — lease record gains `pid`; TTL-stale+alive-probe ⇒ block (no TAKEOVER), TTL-stale+dead/absent-pid ⇒ TAKEOVER; probe injected via the existing `pid_probe` callable param of `core/lock_liveness.is_stale` (or a core protocol port) wired from hooks/container — `features/lease.py` does NOT import `infrastructure/process_probe_adapter`, no new import-linter ignores; `has_os_kill_liveness` seam with TTL fallback; confirmed holder renews past TTL; renew atomic vs foreign acquire (stress/property test on lock-file history — the `lease.py:379-394` race is fixed); docstring `lease.py:16-19` rewritten truthful; liveness tests green on Windows/macOS CI legs; pytest green.
- **Parallelism:** parallel with T-010-04/08.

### [x] T-010-08 — R4a: bind `--mode` optional; mode persisted in session record
- **Owner:** software-engineer · **Maps:** CONF-3, arch F3; bug `context-bind-forces-mode-choice-on-operator`
- **Write set:** `dadaia_workspace/cli/commands/context.py` (bind, `--mode` at `:260`), `tests/` CLI integration
- **Preconditions:** T-010-07.
- **Acceptance:** FR-R4-01/02 — `dadaia context bind <ctx>` (no `--mode`) exits 0, default `read`; explicit modes still work; bind **stops emitting the eval-export theater** (`context.py:273`) and persists the session record (via session_identity) instead; legacy modes map explicitly: `spec` → `READ`, `review` → `IMPLEMENTATION/REVIEW` (accepted as aliases, persisted as the mapped mode); pytest green.
- **Parallelism:** parallel with T-010-04/05; before T-010-09.

### [x] T-010-09 — R4b: gate mode resolution; READ non-acquiring
- **Owner:** software-engineer · **Maps:** CONF-3, ai D-10; bugs `context-bind-…`, `lease-stolen…` (read-session steal family)
- **Write set:** `dadaia_workspace/hooks/sdd_gate.py`, `tests/unit/hooks/test_sdd_gate.py`
- **Preconditions:** T-010-08, T-010-10.
- **Acceptance (AC-R4-01/02):** FR-R4-03/04 — resolution order env→session-record→IMPLEMENTATION; READ ⇒ MUTATING blocked (no lease write; message has no auto-rebind nag but MAY name `bind --mode implementation` as the documented path to write rights) and ADDITIVE allowed — verified under `claude_hook_env()` with **no** env vars (session-record path); both-absent ⇒ IMPLEMENTATION, free-lease acquire proceeds; PROTECTED unchanged; pytest green.
- **Parallelism:** after T-010-08.

### [x] T-010-06 — R2c: two-actor concurrency e2e (no-steal invariant)
- **Owner:** software-engineer · **Maps:** CONF-2/CONF-6, qa §6.2; bug `lease-stolen…` (incident e2e)
- **Write set:** `tests/e2e/test_two_actor_lease.py` (new) + shared rendezvous helper
- **Preconditions:** T-010-04, T-010-05.
- **Acceptance (AC-R2-04):** real OS processes + file rendezvous; holder busy >TTL: (i) foreign ADDITIVE write → ALLOW, lock-file history never names the foreign session; (ii) foreign MUTATING attempt → blocked while holder pid alive; (iii) two contexts mutating disjoint repos concurrently → no cross-block; (iv) dead-holder real-process takeover e2e — holder process exits, foreign acquire TAKEOVERs; invariants asserted on lock-file history, not return values; green on Windows/macOS CI legs (platform-seamed pid probe).
- **Parallelism:** after 04+05; final task of Track K.

---

## Track T — Test kernel completion

### [x] T-010-11 — R5: fixture matrix + kill drift-ratifying tests
- **Owner:** software-engineer · **Maps:** CONF-6, qa defects 1+3 (named tests)
- **Write set:** `tests/unit/features/spec_context/test_lease_property.py`, `test_lease_activity_exemption.py`, `tests/unit/gate/test_post_gate_heartbeat.py`, gate/lease suites (parametrization)
- **Preconditions:** T-010-03..09 merged.
- **Acceptance (AC-R5-02):** root-only ADDITIVE assertions (`test_lease_property.py:74`, `test_lease_activity_exemption.py:27`) replaced by the R1 matrix; `test_post_gate_heartbeat.py:79` migrated to harness-env fixture; gate/lease suites parametrized {1,2 contexts}×{default,non-default slug}×{seeded,empty}; evidence = the named file:lines removed, recorded for CLOSURE + AC-R1-01 matrix carries an in-repo variant per class (replaces the unmechanical residue grep; bash-pinning residue stays covered by T-010-13's contract).
- **Parallelism:** after Track K.

### [x] T-010-12 — R5: escape-matrix regression coverage (7/7 bugs)
- **Owner:** software-engineer · **Maps:** CONF-6, qa escape matrix; all 7 open bugs
- **Write set:** `tests/` (named regression per bug where not already created in K/R tracks), bug frontmatter (`status: Closed` + regression-test name)
- **Preconditions:** T-010-06, T-010-11, T-010-23..26.
- **Acceptance (AC-R5-03):** table bug → named regression test, 7/7, recorded for CLOSURE; each bug file closed with the test reference (opencode bug already closed superseded in T-010-01).
- **Parallelism:** late; after K+R tracks.

---

## Track R — Registries + push gates

### [x] T-010-23 — R8a: core/model_registry.py single source
- **Owner:** software-engineer · **Maps:** CONF-9, arch cluster F; bug `model-catalog-modelmap-pricing-drift-no-registry`
- **Write set:** `dadaia_workspace/core/model_registry.py` (new), `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py`, `dadaia_workspace/features/telemetry/pricing.py`, their unit tests
- **Preconditions:** T-010-02.
- **Acceptance (AC-R8-01 part):** `ModelEntry{claude_id,codex_id,pricing:list[ModelPricing] dated append-only,tier}`; `MODEL_MAP`/`PRICING_TABLE` derived views (most-recent row); haiku `claude-haiku-4-5-20251001` in both; `claude-fable-5` row (10.00/50.00/12.50/1.00, 2026-06-01); contradictory pins in `test_pricing.py:47,212` vs `test_model_mapping.py:25` replaced by cross-table key-equality contract test; mypy --strict + import-linter + pytest green.
- **Parallelism:** independent of K.

### [x] T-010-24 — R8b: public doctor model-resolution check
- **Owner:** software-engineer · **Maps:** CONF-9, ai C-8 (mechanical half)
- **Write set:** `features/public/` doctor module, `tests/unit/features/public/test_model_registry_doctor.py` (new)
- **Preconditions:** T-010-23; `features/public/ → core` linter edge verified/added.
- **Acceptance:** doctor errors on unknown `model:` frontmatter and on key-set desync; exits 0 with current fleet; pytest green.

### [x] T-010-25 — R8c: ci-preflight self-pollution fix
- **Owner:** software-engineer · **Maps:** bug `ci-preflight-self-pollution-gate-never-passes` (HIGH)
- **Write set:** `dadaia_workspace/features/ci_preflight/service.py`, `tests/conftest.py` (pollution-guard rescope), their tests
- **Preconditions:** SPEC+PLAN Aprovado.
- **Acceptance (AC-R8-02):** ruff invoked with `--no-cache`; mypy cache redirected under `.dadaia/tmp/`; conftest session-pollution guard does pre/post snapshot diff (fails only on session-created artifacts); unit fixtures per case; end-to-end `dadaia ci preflight` exit 0 on a clean tree, no cache dirs at repo root afterwards.
- **Parallelism:** independent.

### [x] T-010-26 — R8d: pre-push gate workspace venv probe
- **Owner:** software-engineer · **Maps:** arch F9; bug `pre-push-gate-cannot-locate-workspace-venv`
- **Write set:** `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`, `tests/unit/public/test_pre_push_gate_venv_probe.py` (new)
- **Preconditions:** SPEC+PLAN Aprovado.
- **Acceptance (AC-R8-03):** probe order `DADAIA_BIN` → walk-up `<ws>/.dadaia/.venv/bin/dadaia` → poetry → repo `.venv`; fail-closed clear error when none; fake-tree unit tests for all four branches; stage/install/doctor after edit; manual smoke `git push` from `repos/dadaia-workspace/` recorded for CLOSURE.
- **Parallelism:** independent.

### [x] T-010-27 — R8e: consistency-contract policy + import-linter cap
- **Owner:** software-engineer · **Maps:** CONF-9, arch F10, qa §6.4
- **Write set:** `tests/contract/` (cap test, residue greps), `setup.cfg` (comment-pin), `specs/AGENTS.md` (policy paragraph)
- **Preconditions:** T-010-23, T-010-13.
- **Acceptance (AC-R8-04):** linter ignore-edge cap test fails on growth beyond recorded count; residue greps active (retired bash hooks, retired models); consistency-contract-at-introduction policy documented in `specs/AGENTS.md` + `tests/contract/` README, including the **lifecycle-asymmetry policy** (audit §6.5): every feature documents per-feature delete/orphan + dirty-input + missing-dependency coverage or a justified absence.
- **Parallelism:** after 23 and 13.

---

## Track S — Security tail

### [x] T-010-19 — R7a: `dead()` review gate + secret scan
- **Owner:** software-engineer · **Maps:** CONF-8, sec F-5
- **Write set:** `dadaia_workspace/features/spec_context/service.py`, related CLI, tests
- **Acceptance (AC-R7-01):** untracked files + no `--commit` ⇒ refuse, push nothing; `--commit` ⇒ privacy-engine scan of staged content blocks on a planted secret; clean-tree `dead()` unchanged; pytest green.

### [x] T-010-20 — R7b: privacy gate fail-closed baseline denylist
- **Owner:** software-engineer · **Maps:** sec F-2
- **Write set:** `dadaia_workspace/infrastructure/privacy_check.py`, packaged baseline data, tests
- **Acceptance (AC-R7-02):** absent operator denylist ⇒ baseline structural scan still runs and flags planted IP/hostname; `[ok] public-privacy` emitted only after a real scan; pytest green.

### [x] T-010-21 — R7c: panel loopback auth + token-mode recheck
- **Owner:** software-engineer · **Maps:** sec F-3, F-7
- **Write set:** `dadaia_workspace/features/panel/handler.py`, `dadaia_workspace/features/panel/auth.py`, unit + e2e tests
- **Acceptance (AC-R7-03):** tokenless loopback request to a sensitive API ⇒ 401 (contract pinned by test); `ensure_token` tightens a pre-existing 0o644 token to 0o600 (platform-seam aware); panel e2e green.

### [x] T-010-22 — R7d: dev dependency pins
- **Owner:** software-engineer · **Maps:** sec F-6
- **Write set:** `pyproject.toml`, `poetry.lock` (dev/build group)
- **Acceptance:** `poetry` ≥ 2.3.4, `dulwich` ≥ 1.2.5; `pip-audit` clean of the 4 named CVEs; suite green.

---

## Track D — Truth pass

### [x] T-010-13 — R6a: retire the bash hook quartet (Decision D-1)
- **Owner:** software-engineer · **Maps:** ai S-1/S-2/C-9, DRIFT-6, sec F-4; bug `gate-fpath-not-canonicalized-before-classifier` (bash surface)
- **Write set:** `dadaia_workspace/public/scripts/{sdd-spec-gate,sdd-post-gate,root-whitelist-gate,ctx-inject}.sh` (delete), `public/scripts/__pycache__/` (delete), manifest/staging/projection code+tests, `features/spec_context/gate_policy.py:1-8` docstring, `tests/contract/test_bash_hook_residue.py` (new)
- **Preconditions:** T-010-03 merged (shares `gate_policy.py` — the docstring fix lands after the re-root; declared exception to cross-track file-disjointness).
- **Acceptance (AC-R6-01):** quartet absent from canonical assets, staging manifest, and all projections; `pre-push-ci-gate.sh` retained; docstring names the Python hooks; residue grep contract green; `dadaia public stage && install --target all && public doctor` exit 0; bug closed referencing T-010-03's symlink regression + this retirement.
- **Parallelism:** after T-010-03; otherwise independent.

### [x] T-010-14 — R6b: specs-doctor ledger invariants + coherence backstop
- **Owner:** software-engineer · **Maps:** CONF-5, arch F6, index §4; Decision D-2 backstop
- **Write set:** `dadaia_workspace/features/specs/doctor.py`, `tests/unit/features/specs/test_doctor_ledger_invariants.py` (new)
- **Preconditions:** SPEC+PLAN Aprovado.
- **Acceptance (AC-R6-02):** five invariants (phase↔markers; CLOSURE-before-archive; unique release ids across releases+_archive; `^v\d+\.\d+\.\d+$` naming with legacy WARN; constitution file-ref resolution) + lease↔session coherence backstop; one failing fixture per invariant; pytest green.
- **Parallelism:** independent; before T-010-15.

### [x] T-010-18 — R6c: Claude PreToolUse matcher scoping
- **Owner:** software-engineer · **Maps:** ai C-12
- **Write set:** `dadaia_workspace/infrastructure/runtime_config.py`, its tests
- **Preconditions:** T-010-04 merged (PostToolUse breadth requirement known).
- **Acceptance (AC-R6-05):** generated PreToolUse write-gate matcher scoped to `Edit|Write|MultiEdit|NotebookEdit`; PostToolUse matcher fires on all tools (heartbeat); UserPromptSubmit unchanged; regenerated `.claude/settings.json` validated by unit test; live instance reprojected.
- **Parallelism:** after T-010-04.

### [x] T-010-15 — R6d: v0.1.9 retro-CLOSURE + archive repair (ledger truth)
- **Owner:** product-engineer · **Maps:** CONF-5, DRIFT-5, arch F6; Decisions D-4/D-5
- **Write set:** `specs/releases/v0.1.9/**` (CLOSURE.md), `specs/_archive/releases/` (renames via git mv — request devops/operator), mapping README
- **Preconditions:** T-010-14 (invariants define the target state). ACTIVE.md → v0.1.10 already done at T-010-00 (release-start split, arch A5) — not part of this task.
- **Acceptance (AC-R6-03):** v0.1.9 CLOSURE.md authored from implemented evidence (19 tasks, SHAs); v0.1.9 archived; `_archive/releases/v0.2.0/v0.1.{6..9}` renamed non-colliding + mapping README; `dadaia specs doctor` exit 0 with the new invariants active.
- **Parallelism:** PE-track; does not block code tracks.

### [x] T-010-17 — R6e: AI-surface honesty rewrite (C-1..C-14)
- **Owner:** ai-engineer · **Maps:** CONF-4, ai C-1..C-14, D-1/D-8 honesty, Decision D-2/D-6
- **Write set:** `dadaia_workspace/public/{data/AGENTS.md, rules/*, skills/*, agents/*, schemas/handoff-v1.schema.json}` (canonical sources only; then stage/install/doctor)
- **Preconditions:** Track K merged; T-010-13 done (surface must describe the fixed product).
- **Acceptance (AC-R6-04):** contradiction table C-1..C-14 → commit/file:line complete; SDD-gate sections state real enforcement (path-class×lease×phase) with Aprovado/`[-]` as discipline (C-5); F8 allowlist claim corrected (C-2); handoff-first emitter executable (C-7, D-6); memory phases unified DEFINITION+CLOSURE (C-4); workflow inventory (C-3); report-header blockquotes (C-6/S-7); tier tables from registry (C-8); dispatch column reworded + PM-top-level precondition (C-10); hook ownership corrected (C-11); task-manager in English (C-13); determinism language scoped to write-tools, Bash bypass documented out of scope (D-2); `dadaia public doctor` exit 0 after reprojection.
- **Parallelism:** after K + 13; parallel with T/R/S tails.

### [ ] T-010-16 — R6f: memory + constitution truth rewrite (CLOSURE phase)
- **Owner:** product-engineer · **Maps:** DRIFT-1/2/3, arch F4 (closure REJECT gate)
- **Write set:** `specs/memory/architecture.md`, `specs/memory/product/<gate atom>.md`, `specs/memory/tech-stack.md`, `specs/constitution.md` (operator confirmation required)
- **Preconditions:** ALL code tasks merged and reviewed; ACTIVE.md phase CLOSURE.
- **Acceptance (AC-R6-04 memory half):** architecture.md concurrency section and constitution §0/§8 match the merged R1–R4 contract (reviewer cross-check vs code); no changelog sections; `dadaia specs doctor` exit 0; constitution diff explicitly confirmed by operator before commit.
- **Parallelism:** LAST before release CLOSURE.md.

---

## Final gate

### [-] T-010-28 — Release final gate
- **Owner:** software-engineer · **Maps:** all
- **Write set:** none (verification)
- **Preconditions:** all tasks above `[x]` except T-010-16 (which follows in CLOSURE).
- **Acceptance:** (1) `pytest -p no:cacheprovider` 0 failures; (2) `ruff format --check && ruff check --no-cache` clean; (3) `mypy --strict` clean; (4) import-linter 0 violations + cap respected; (5) `dadaia public doctor` exit 0; (6) `dadaia specs doctor` exit 0; (7) `dadaia ci preflight` exit 0 end-to-end on a clean tree; (8) two-actor e2e green; (9) `dadaia context bind dadaia-workspace` (no `--mode`) exit 0; (10) tokenless loopback panel request → 401.

---

## Public-asset propagation note

T-010-13/17/26 modify `dadaia_workspace/public/**`. After each:
`dadaia public stage && dadaia public install --target all && dadaia public doctor`
(exit 0 required before the final gate).
