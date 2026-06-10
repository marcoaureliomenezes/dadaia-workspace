# SPEC: v0.1.10 — Concurrency Kernel + Workspace Truth (audit remediation R1–R8)

**Status:** Em revisão
**Release ID:** v0.1.10
**Owner:** product-engineer
**Created:** 2026-06-10
**Revised:** 2026-06-10 (extended per audit `specs/audits/2026-06-10T010550Z/` — coverage verdict PARTIAL → full R1–R8)

---

## Objective

One release that remediates the full 2026-06-10 audit so the next full audit scores
≥9/10 on all six dimensions (spec fidelity 4→9, memory fidelity 4→9, architecture 6→9,
test quality 5→9, AI-surface honesty 5→9, security 7→9). The prior v0.1.10 draft
(lock correctness + model registry) is **extended, not replaced**: its WS-1/2/3/4/6
content is preserved where the audit confirmed it correct, and broadened per the audit's
remediation order R1–R8 (`index.md §6`).

Scope: the concurrency/identity kernel (classifier, lease liveness, session identity,
mode channel), the test-architecture kernel, the ledger/memory/constitution truth pass,
the security tail, and anti-drift consistency contracts. All 7 open bugs are solved or
explicitly superseded.

**Grill-me:** satisfied by the operator's explicit written directive + the audit corpus
(4 lane reports + synthesis), per release-governance.

---

## Bug inventory and resolution map (7/7)

| Bug | Sev | Resolution |
|-----|-----|-----------|
| `lease-stolen-by-additive-write-from-live-session` | CRITICAL | R1 (T-010-03), R2 (T-010-04/05/06), R3 (T-010-07), R4 (T-010-09) |
| `ci-preflight-self-pollution-gate-never-passes` | HIGH | R8 (T-010-25) |
| `gate-fpath-not-canonicalized-before-classifier` | MEDIUM | R1 symlink regression (T-010-03) + bash-gate retirement (T-010-13) |
| `context-bind-forces-mode-choice-on-operator` | MEDIUM | R4 (T-010-08/09) |
| `model-catalog-modelmap-pricing-drift-no-registry` | MEDIUM | R8 (T-010-23/24/27) |
| `pre-push-gate-cannot-locate-workspace-venv` | MEDIUM | R8 (T-010-26) |
| `opencode-parity-test-asserts-stale-bash-script-ref` | MEDIUM | Superseded by v0.1.8 — verified at HEAD (T-010-01); see §Bug supersession |

No bug is silently dropped (bug-always-solved law).

### Bug supersession

`opencode-parity-test-asserts-stale-bash-script-ref`: verified on disk at definition
time — `tests/e2e/features/test_opencode_parity_hardening.py:129` reads
`assert "sdd-spec-gate.sh" not in text` (the correct post-ADR-7 assertion). The fix
shipped with v0.1.8. T-010-01 captures pytest evidence and closes the bug with
`superseded_by: v0.1.8`. (The audit lane's "still asserts `in`" entry predates this
verification and is refuted by HEAD.)

---

## Workstreams

### WS-R1 — Classifier re-root: context-relative class × location taxonomy

**Audit:** CONF-1 (CRITICAL, 4/4 lanes), arch F1, sec F-1, ai D-3/D-4/D-5/C-1, qa 17-D1.

**Root cause:** `gate_policy.classify_path` (`gate_policy.py:37-46,84-98`) matches
ADDITIVE/MEMORY/FROZEN prefixes against workspace-root-relative paths only; `repos/`
matches MUTATING first (`:94`). The root-whitelist law forbids a root `specs/`, so the
three classes are **unreachable in any compliant workspace**: in-repo bugs/backlog/audits
acquire/steal the lease, in-repo memory bypasses the PE phase-lock, in-repo `_archive`
is writable.

**Fix (extends the prior draft's ADDITIVE-only short-circuit to the full taxonomy):**
classification is computed on the **context-relative path** — strip a leading
`repos/<slug>/` segment, then run the full class taxonomy (ADDITIVE, MEMORY, FROZEN,
releases-MUTATING) against the context-relative string. Workspace-root paths classify
exactly as today. PROTECTED (`.dadaia/sessions/`) remains workspace-root and is
evaluated first, unchanged. RULE A (memory phase-lock) and RULE B (frozen archive) must
therefore execute for in-repo paths — they are no longer dead code.

**Functional requirements:**
- FR-R1-01: `repos/<slug>/specs/bugs|backlog|audits/**` → ADDITIVE; `Decision.ALLOW`
  with **no lease read or write**.
- FR-R1-02: `repos/<slug>/specs/memory/**` → MEMORY; PE-phase rule (DEFINITION/CLOSURE
  per ACTIVE.md) is evaluated and blocks outside those phases.
- FR-R1-03: `repos/<slug>/specs/_archive/**` → FROZEN; Write/Edit blocked.
- FR-R1-04: `repos/<slug>/specs/releases/**` and all other in-repo paths → MUTATING
  (lease-acquiring), unchanged. A `ctx_rel` matching no class NEVER falls through to
  UNGATED: no class match ⇒ MUTATING. In-repo production source
  (`repos/<slug>/src/**`, `repos/dadaia-workspace/dadaia_workspace/**`) and in-repo
  `specs/<other>` (e.g. `repos/<slug>/specs/constitution.md`) are MUTATING.
- FR-R1-05: workspace-root paths (`specs/bugs/`, `.dadaia/reports/`, etc.) classify
  identically to pre-change behavior (no regression).
- FR-R1-06: **matrix tests** — every class × {workspace-root, in-repo} × {default slug,
  non-default slug} asserted in `tests/unit/features/spec_context/test_gate_policy.py`.
- FR-R1-07: symlink regression — the Python gate resolves (`hooks/sdd_gate.py` uses
  `.resolve()`) before classifying; an automated test creates a symlink from an ungated
  location into `specs/memory/` and asserts MEMORY classification, not UNGATED
  (closes the Python-surface acceptance of `gate-fpath-not-canonicalized-before-classifier`).
- FR-R1-08: full-pipeline regression of the incident: session A holds the lease; clock
  advanced 130 s with no Write/Edit from A; session B `gate_policy.evaluate` end-to-end
  on `repos/dadaia-workspace/specs/bugs/<slug>.md` → ALLOW **and** `lease.read_record()`
  still names session A (lease untouched).

### WS-R2 — Lease liveness: harness-native heartbeat + process probe; no TAKEOVER from a live session

**Audit:** CONF-2 (CRITICAL), arch F2, ai D-2/D-12/C-14, qa 17-D2/D3. Restores the
PID-liveness lesson learned in v0.1.5 rc-2 and discarded in the v0.1.6 lease rewrite.

**Root cause (three parts):** (a) lease heartbeat renews only inside
`gate_policy.evaluate` for MUTATING Edit/Write — a holder inside any >120 s Bash call
(pytest) starves; (b) the PostToolUse heartbeat (`hooks/sdd_post_gate.py:38`) is keyed
on `DADAIA_SESSION_ID`, an env var no harness sets — permanent no-op; (c) staleness is
TTL-only — `lease.acquire` auto-TAKEOVERs a "stale" record even when the holder process
is alive. `lease.py:16-19` docstring claims renewal "on every PreToolUse" — false.

**Fix:**
1. `sdd_post_gate` resolves the session id **harness-natively**: stdin `session_id`
   payload first (same `_common.resolve_session_id` channel `sdd_gate` uses), env var
   as override only. It calls `lease.renew_heartbeat` on **every** PostToolUse (all
   tools, incl. Bash), placed **outside** any session-file existence guard.
2. `renew_heartbeat` must allow the **confirmed holder** to renew past TTL (relax the
   is_stale no-op for same session_id), and the renew path must be holder-safe (atomic
   compare-on-holder write; a concurrent foreign replace must never be overwritten with
   stale holder data — the `lease.py:379-394` check-then-act race is **fixed**, not
   acknowledged, because AC-R2-04's lock-history invariant cannot hold otherwise).
3. `lease.acquire` consults a **process-liveness probe** before TAKEOVER: the lease
   record gains a `pid` field at acquire; when a record is TTL-stale, acquire probes the
   holder pid via the existing platform seam (`core/lock_liveness.py` +
   `has_os_kill_liveness` non-destructive probe, v0.1.8). If the holder process is
   alive → **no TAKEOVER**: the foreign MUTATING write is blocked with a clear,
   no-rebind-instruction message. If dead or unprobeable on the platform → TTL fallback
   (today's behavior).
4. `lease.py` docstring rewritten to the implemented liveness model (fixes C-14).

**Functional requirements:**
- FR-R2-01: PostToolUse renews the lease heartbeat with session id resolved from the
  stdin payload (no env var required), outside any session-file guard; fail-open
  (exit 0) on any error; non-holder renewal is a guarded no-op.
- FR-R2-02: a holder running a >120 s Bash call with no Write/Edit keeps a fresh
  heartbeat via PostToolUse renewal.
- FR-R2-03: lease record carries `pid`; TTL-stale + alive-probe ⇒ acquire raises/blocks
  (no TAKEOVER); TTL-stale + dead-probe ⇒ TAKEOVER as today.
- FR-R2-04: confirmed holder can renew past TTL; renew is atomic w.r.t. foreign acquire.
- FR-R2-05: **two-actor concurrency test** (real OS processes, file rendezvous,
  generalizing `tests/e2e/test_two_process_denial.py`): holder busy past TTL while a
  second actor (i) writes ADDITIVE — lock-file history shows the holder never changed;
  (ii) attempts MUTATING — blocked while the holder process is alive; (iii) two
  contexts mutating disjoint repos concurrently — no cross-block; (iv) dead-holder
  takeover e2e — the holder process really exits, foreign acquire TAKEOVERs.

### WS-R3 — Session-identity consolidation (one module, four stores collapsed)

**Audit:** arch F7, CONF-1/CONF-2 substrate.

**Root cause:** four fragmented identity/liveness artifacts with two key schemes —
`.dadaia/states/ctx_locks/<ctx>.lock.json`, `.dadaia/sessions/runtime/<ctx>.ptr`,
`.dadaia/sessions/runtime/<session_id>.ptr` (written by `ctx_inject.py:99-106`),
`.dadaia/sessions/<id>.json` — no module owns "who is this session".

**Fix:** one CLI-owned module `features/spec_context/session_identity.py` is the sole
reader/writer of session-identity state: session record (id, mode, pid, created_at,
last_seen_at) and the lease-incumbent pointer. `lease.py`, `hooks/ctx_inject.py`,
`hooks/sdd_post_gate.py`, `hooks/sdd_gate.py`, and the bind CLI consume it. Redundant
artifacts are eliminated or derived (target: ≤2 on-disk artifacts — lease record +
session record; the dual `.ptr` namespace collapses). Migration: stale legacy artifacts
are ignored-and-superseded, not migrated.

**Functional requirements:**
- FR-R3-01: a single module owns all reads/writes of session identity; grep shows no
  other module opens `sessions/runtime/*.ptr` or `sessions/<id>.json` directly.
- FR-R3-02: lease record holder, incumbent pointer, and session record can never name
  three different sessions for one context (consistency asserted by contract test).
- FR-R3-03: all artifacts live under PROTECTED `.dadaia/sessions/` or
  `.dadaia/states/ctx_locks/`; no new gate classes.

### WS-R4 — Bind-mode channel: mode persisted where hooks read it; READ binds non-acquiring

**Audit:** CONF-3 (HIGH), arch F3, ai D-10/D-11; bug `context-bind-forces-mode-choice-on-operator`.

**Root cause:** `bind --mode` only prints `export` lines; hooks run in harness env that
never inherits them; `sdd_gate.py:127` defaults `DADAIA_MODE` to IMPLEMENTATION; the
`mode` stored in the lease record is never read by any decision. Mode is theater, and
the CLI forces the operator to choose a mode that has no effect.

**Fix:**
- Part A (CLI): `--mode` becomes optional, default `read`. Bind persists the mode in the
  CLI-owned session record (WS-R3) — the store hooks actually read — keyed by the
  harness-native session id when resolvable, else by the bind-created session id.
- Part B (gate): mode resolution order: (1) `DADAIA_MODE` env fast-path override;
  (2) session record `mode` via session_identity; (3) default IMPLEMENTATION.
  When mode resolves to READ/BOUND_READ: the session is **non-acquiring** — MUTATING
  writes are blocked with a message that never auto-instructs rebinding mid-flow; it
  MAY name `dadaia context bind <ctx> --mode implementation` as the documented path to
  write rights (distinct from the banned auto-rebind nag); ADDITIVE/UNGATED
  follow their normal policies; PROTECTED stays fail-closed.
- Missing-mode sessions (no bind, no env — every plain harness session) default to
  IMPLEMENTATION and may acquire a **free** lease, but may never TAKEOVER from a
  live-probed holder (WS-R2 FR-R2-03 supplies the no-steal half). See Decision D-3.

**Functional requirements:**
- FR-R4-01: `dadaia context bind <name>` with no `--mode` exits 0; default mode `read`;
  explicit `--mode implementation|read` still works.
- FR-R4-02: bind writes `mode` into the session record; the gate reads it without any
  env var present (the harness-real path).
- FR-R4-03: READ-resolved session: MUTATING → BLOCK (no lease write); ADDITIVE → ALLOW.
- FR-R4-04: both-sources-absent → IMPLEMENTATION (backward compatible; existing
  sessions unaffected).

### WS-R5 — Test-architecture kernel (acceptance substrate for R1–R4)

**Audit:** CONF-6 (HIGH), qa defects 1–3 + strategy §6; covers 11 of 16 blind escapes.

**Fix (three pillars):**
1. **Harness-env fixture contract.** New fixtures `claude_hook_env()` / `codex_hook_env()`
   contain ONLY what each harness actually provides to hook subprocesses (pinned once,
   documented in the fixture docstring with the verification source). All hook/gate/
   lease tests run hooks through these fixtures. Hook BEHAVIOR tests in
   `tests/**/hooks|gate/**` MUST invoke hooks via the subprocess runner helper; a
   contract test flags direct hook-module import+call in those suites (closes the
   `os.environ.update` evasion). The env-contract grep covers the whole `DADAIA_*`
   namespace with an explicit allowlist (e.g. `DADAIA_CONTEXT`, an operator-shell var),
   failing any test that `setenv`s a non-allowlisted `DADAIA_*` outside the fixtures.
2. **Two-actor / multi-context tier + fixture matrix.** The two-actor pattern of
   FR-R2-05 becomes a reusable helper; gate/lease/renderer tests parametrize over
   {1, 2 contexts} × {default, non-default slug} × {seeded, empty}.
3. **Kill drift-ratifying tests** (qa-named): `test_lease_property.py:74` and
   `test_lease_activity_exemption.py:27` (root-only ADDITIVE paths → replaced by the
   R1 matrix); `test_post_gate_heartbeat.py:79` (hand-planted `DADAIA_SESSION_ID` →
   migrated to harness-env fixture); the contradictory haiku pins
   `test_pricing.py:47,212` vs `test_model_mapping.py:25` (replaced by the registry
   cross-table contract, WS-R8). Each named regression test for the 7 open bugs ships
   in this release (escape-matrix-driven coverage).

**Functional requirements:**
- FR-R5-01: `claude_hook_env()`/`codex_hook_env()` exist and are the only env source
  for hook subprocess tests; hook behavior tests in `tests/**/hooks|gate/**` invoke
  hooks via the subprocess runner helper; contract tests present for (a) out-of-fixture
  `DADAIA_*` setenv (full namespace, explicit allowlist) and (b) direct hook-module
  import+call in those suites.
- FR-R5-02: fixture-matrix parametrization applied to the gate/lease suites.
- FR-R5-03: zero remaining assertions pinning the retired bash-hook behavior or the
  root-only ADDITIVE assumption (residue grep test).
- FR-R5-04: every one of the 7 open bugs has a named regression test listed in CLOSURE.

### WS-R6 — Ledger / memory / constitution truth pass + AI-surface honesty

**Audit:** CONF-4, CONF-5 (HIGH), DRIFT-1..7, arch F4/F6/F8, ai C-1..C-14, S-1/S-2.
Arch review gate: any v0.1.10 closure that fixes code without rewriting memory/
constitution is REJECTED (F4).

**Fix (six parts):**
1. **Retire the dead bash hook quartet** (`public/scripts/{sdd-spec-gate,sdd-post-gate,
   root-whitelist-gate,ctx-inject}.sh`): removed from canonical assets, staging manifest,
   and projections. `pre-push-ci-gate.sh` is kept (a real git hook, deliberately shell —
   ai D-13 DETERMINISTIC). Delete `public/scripts/__pycache__/` (S-1). Fix the
   `gate_policy.py:3-8` docstring to name the Python hooks as the enforced gate
   (C-9/DRIFT-6). This retirement is the resolution of sec F-4 — see Decision D-1.
2. **Doctor invariants (SDD machine validates its own state):** `dadaia specs doctor`
   errors on (a) ACTIVE.md phase inconsistent with TASKS markers (e.g. phase SPEC/TASKS
   while all tasks `[x]`, or phase IMPLEMENTATION with no `[-]`/`[x]`); (b) a fully-`[x]`
   archived release without CLOSURE.md; (c) duplicate release ids across
   `specs/releases/` + `specs/_archive/releases/` (any depth); (d) release dir names
   not matching `^v\d+\.\d+\.\d+$` (new releases; pre-canon archive ids reported as
   WARN with the documented mapping); (e) constitution file references that do not
   resolve on disk.
3. **Ledger repair (PE):** author the missing v0.1.9 retro-CLOSURE from the implemented
   evidence, archive v0.1.9, and resolve the archive release-id collision
   (`_archive/releases/v0.2.0/{v0.1.6..v0.1.9}` renamed to non-colliding milestone
   names with a mapping README) — Decision D-4/D-5.
4. **Memory + constitution rewrite (PE, CLOSURE phase):** `specs/memory/architecture.md`
   §"Modelo de concorrência" (ADDITIVE-unconditional and heartbeat-per-PreToolUse claims)
   and constitution §0/§8 lifecycle claims rewritten to the **post-fix verified**
   contract (R1–R4). Constitution edits require explicit operator confirmation.
5. **AI-surface honesty rewrite (ai-engineer):** all 14 contradictions C-1..C-14
   resolved — each claim either becomes true in code (covered by R1–R8 tasks) or is
   reworded as discipline. Key items: the SDD Gate section of root AGENTS.md +
   `dadaia-task-manager` skill state what the gate **actually** enforces (path-class ×
   lease × memory-phase) and that Aprovado/`[-]` markers are agent discipline (C-5/D-1,
   CONF-4); the harness skill F8 allowlist claim corrected (C-2); handoff-emitter skill +
   schema made executable for the handoff-first default (C-7); memory-phase wording
   unified to DEFINITION+CLOSURE (C-4); PM workflow inventory corrected (C-3); persona
   HTML-report header blockquotes reconciled with handoff-first (C-6/S-7); model-tier
   tables regenerated from the registry (C-8); dispatch column reworded as
   handoff-routing intent + PM-top-level precondition stated (C-10); hook ownership
   table corrected — `dadaia_workspace/hooks/*.py` is software-engineer production
   Python (C-11); `dadaia-task-manager` translated to English (C-13); lease docstring
   (C-14, done in R2); tmp-file-guardrail "Enforcement" relabeled discipline (D-8).
6. **Bash-bypass honesty (Decision D-2):** enforcement-scope language ("deterministically",
   "blocked unconditionally") rewritten to scope all PreToolUse determinism claims to
   `Edit|Write|apply_patch`-family tools; Bash-side writes are explicitly documented as
   outside the determinism envelope. A doctor backstop check validates lease-record ↔
   session-record coherence (detects out-of-band `.ptr`/lock forgery after the fact).

**Functional requirements:**
- FR-R6-01: no `.sh` hook of the quartet remains in canonical assets, manifest, or
  projections; residue grep contract test passes; `pre-push-ci-gate.sh` retained.
- FR-R6-02: the five doctor invariants implemented with unit tests (one fixture per
  violation class) and `dadaia specs doctor` exit 0 on the repaired ledger.
- FR-R6-03: v0.1.9 CLOSURE.md exists with evidence; archive contains no duplicate
  release ids; mapping README present.
- FR-R6-04: memory/constitution concurrency sections match the implemented contract
  (reviewer cross-checks against R1/R2 code).
- FR-R6-05: a contradiction-resolution table in CLOSURE maps each of C-1..C-14 to a
  commit or a reworded file:line.

### WS-R7 — Security tail

**Audit:** sec F-2/F-3/F-5/F-6/F-7 (F-1 = R1; F-4 = R6 retirement; F-8 INFO = D-2).

- **F-5 `dead()` push review gate:** `context dead()` refuses to auto-commit untracked
  files unless `--commit` is passed explicitly; with `--commit`, a secret/pattern scan
  (reusing the privacy-check engine) runs before push and blocks on findings.
- **F-2 privacy gate fail-closed:** `infrastructure/privacy_check.py:95-97` ships an
  in-package baseline structural denylist (IP/hostname/path regexes) so the check is
  never a no-op when the operator denylist is absent; operator terms stay additive.
- **F-3 panel loopback bypass:** Bearer auth required even on 127.0.0.1 binds (or
  same-origin/Host allowlist check — implementer chooses, test pins the contract:
  tokenless request to a sensitive API on loopback → 401).
- **F-7 token-mode recheck:** `panel/auth.py:34-35` `ensure_token` verifies the mode of
  a pre-existing token file and tightens to 0o600 (platform-seam aware).
- **F-6 dev pins:** bump dev/build `poetry`/`dulwich` past the named CVEs.

### WS-R8 — Anti-drift consistency contracts + push-gate repair

**Audit:** CONF-9, arch cluster F + F9/F10, qa defect 4; bugs `model-catalog-…`,
`ci-preflight-self-pollution…`, `pre-push-gate-…`.

- **Single model registry (preserved from prior draft WS-4):**
  `core/model_registry.py` defines `ModelEntry{claude_id, codex_id,
  pricing: list[ModelPricing] (dated, append-only), tier}`; `MODEL_MAP` and
  `PRICING_TABLE` become derived views (PRICING_TABLE = most-recent row per model);
  haiku desync corrected (`claude-haiku-4-5-20251001`); `claude-fable-5` entry
  (input $10.00 / output $50.00 / cache-write-5m $12.50 / cache-read $1.00 per MTok,
  effective 2026-06-01) — workaround already applied, precondition satisfied.
  `dadaia public doctor` check: every `model:` in `public/agents/*.md` resolves in the
  registry; `MODEL_MAP`/`PRICING_TABLE` key sets identical.
- **ci-preflight self-pollution fix:** `features/ci_preflight/service.py:46-47` invokes
  ruff with `--no-cache`; mypy with an explicit cache redirect (`MYPY_CACHE_DIR` /
  `--cache-dir` under `.dadaia/tmp/`); the conftest session-pollution guard scoped to
  artifacts **created during the pytest session** (snapshot-diff), so the gate's own
  earlier checks can never fail its final check. Acceptance: `dadaia ci preflight`
  exits 0 on a clean tree end-to-end.
- **Pre-push gate venv probe (preserved WS-6):** runner resolution priority
  `DADAIA_BIN` env → walk-up workspace venv (`<ws>/.dadaia/.venv/bin/dadaia`) →
  `poetry` on PATH → repo-local `.venv`; fail-closed with a clear error when none found.
- **Consistency-contract-at-introduction policy:** documented in `tests/contract/`
  scope notes + `specs/AGENTS.md`: any pair of modules sharing an identifier set gets a
  consistency contract at introduction time. Concrete contracts shipped: MODEL_MAP↔
  PRICING_TABLE key equality; retired-bash-hook residue grep; import-linter ignore-list
  **cap** (CI fails if `setup.cfg` ignore edges grow beyond the current count, F10).
- **Lifecycle-asymmetry policy (audit §6.5):** every feature carries per-feature
  delete/orphan + dirty-input + missing-dependency coverage, or a justified absence,
  documented in the same policy home (`specs/AGENTS.md` + `tests/contract/` README;
  folded into T-010-27).

---

## Decisions (D-1..D-6 ALL ratified by the architect at SPEC review, 2026-06-10)

- **D-1 Bash gate retired, not canonicalized.** The shell hook quartet is an unexecuted
  dual implementation requiring hand byte-parity, already drifted (S-2, C-9, DRIFT-6);
  live wiring has invoked the Python hooks on all harnesses since v0.1.8. Retiring it
  resolves sec F-4 (no bash classifier surface remains), C-9, and the bash half of
  `gate-fpath-not-canonicalized-before-classifier`. `pre-push-ci-gate.sh` (git hook,
  D-13 deterministic) is explicitly kept.
- **D-2 Bash tool bypass: documented out of determinism scope, not closed.** Per sec
  F-8 (INFO — fail-open is non-destructive and the intended posture) and the harness
  skill's own "guardrail, not a hard boundary": classifying Bash command strings is
  brittle theater. Instead, all "deterministic/unconditional" enforcement language is
  scoped to file-write tools, and a doctor coherence backstop detects out-of-band
  session/lock forgery.
- **D-3 Missing-mode sessions remain IMPLEMENTATION-capable.** Strict
  "missing ⇒ non-acquiring" would block every plain harness session (none has a bind
  record) and violate the flow-never-stops law. Adopted composition: missing mode may
  acquire a **free** lease; the no-steal property for held leases comes from the R2
  liveness probe; only explicit READ blocks MUTATING. Ratified by the architect at
  SPEC review.
- **D-4 v0.1.9 closed retroactively inside v0.1.10** (R6 ledger repair), not reopened.
- **D-5 Archive id collisions fixed by renaming** the `v0.2.0` internal milestone dirs
  (with a mapping README), not by history rewrite.
- **D-6 Handoff-emitter executability (C-7):** the skill/schema are aligned so the
  handoff-first default (no HTML) is executable; exact mechanism (conditional
  `content_hash` or subject-artifact hash) is the ai-engineer task's acceptance.

---

## Architecture deltas

- `features/spec_context/gate_policy.py` — full context-relative classification
  (ADDITIVE/MEMORY/FROZEN reachable in-repo); READ-mode non-acquiring evaluation.
- `features/spec_context/lease.py` — `pid` in the lease record; liveness probe before
  TAKEOVER via `core/lock_liveness.py` + platform seam; holder-safe renew; truthful
  docstring.
- `features/spec_context/session_identity.py` (new) — sole owner of session records and
  incumbent pointers; consumed by lease, hooks, bind CLI.
- `hooks/sdd_post_gate.py` — heartbeat on every PostToolUse, stdin-resolved session id.
- `hooks/sdd_gate.py` — mode resolution (env fast-path → session record → default).
- `cli` bind — `--mode` optional (default read), persists mode in the session record.
- `core/model_registry.py` (new, zero-I/O) — single source for model id/pricing/tier;
  `model_mapping.MODEL_MAP` and `telemetry/pricing.PRICING_TABLE` become views.
- `infrastructure/runtime_config.py` — Claude PreToolUse write-gate matchers scoped to
  `Edit|Write|MultiEdit|NotebookEdit` (C-12); PostToolUse stays broad (heartbeat needs
  every tool); ctx-inject UserPromptSubmit unchanged.
- `features/specs/doctor.py` — five ledger invariants + identity-coherence backstop.
- `features/ci_preflight/service.py` — no-cache/redirected check invocations.
- Public assets: bash hook quartet removed; `pre-push-ci-gate.sh` venv probe.
- No new CLI commands; no new agent personas; lease record schema gains `pid` only.

## Tech-stack deltas

None at runtime. Dev/build pins: `poetry` ≥ 2.3.4, `dulwich` ≥ 1.2.5 (F-6).

## Security/operations deltas

- R1+R2+R4 close the confused-deputy lease-theft family (sec F-1 HIGH).
- R7: `dead()` no longer pushes unreviewed untracked files (F-5); privacy gate never
  no-ops (F-2); panel loopback requires auth (F-3); legacy token modes tightened (F-7).
- D-2: enforcement posture documented honestly; no destructive failure modes added.

## Memory files affected at closure

- `specs/memory/architecture.md` — concurrency model, gate taxonomy, session identity,
  hook wiring (bash quartet removed), doctor invariants.
- `specs/memory/product/sdd/sdd-gate-v3.md` (or current gate atom) — class×location
  taxonomy, mode channel, liveness contract.
- `specs/memory/tech-stack.md` — model registry module; dev pins.
- `specs/constitution.md` — §0/§8 concurrency claims (operator confirmation required).

---

## Acceptance criteria

Each AC is reviewer-verifiable (file:line / named test / command + expected output).

- **AC-R1-01** Matrix test `tests/unit/features/spec_context/test_gate_policy.py`
  covers {ADDITIVE, MEMORY, FROZEN, MUTATING, PROTECTED} × {root, in-repo} ×
  {default, non-default slug}, with an in-repo variant per class, including rows for
  in-repo production source (`repos/<slug>/src/**`, `dadaia_workspace/**`) and in-repo
  `specs/<other>` (e.g. `repos/<slug>/specs/constitution.md`) → MUTATING, never
  UNGATED; all pass (FR-R1-01..06).
- **AC-R1-02** Full-pipeline incident regression (FR-R1-08) passes in a dual-session
  fixture; lock record asserted on file content, not return value.
- **AC-R1-03** Symlink regression (FR-R1-07) passes; named test referenced in the
  `gate-fpath-…` bug closure.
- **AC-R2-01** PostToolUse heartbeat test runs the hook as a subprocess under
  `claude_hook_env()` (no hand-planted `DADAIA_SESSION_ID`) and observes a fresher
  lease heartbeat (FR-R2-01/02); green on the Windows/macOS CI legs too.
- **AC-R2-02** TTL-stale + alive holder ⇒ foreign `lease.acquire` blocked; TTL-stale +
  dead pid ⇒ TAKEOVER (FR-R2-03), with injected clock + fake/real pid; liveness tests
  green on the Windows/macOS CI legs (platform-seamed pid probe; no Linux-only
  acceptance).
- **AC-R2-03** Holder renews past TTL; concurrent foreign acquire cannot interleave a
  stale overwrite (FR-R2-04, property/stress test on the lock file history).
- **AC-R2-04** Two-actor e2e (FR-R2-05): "a live holder never loses the lease; an
  ADDITIVE write never appears in the lock record" asserted on lock-file history;
  plus disjoint-repos no-cross-block and dead-holder real-process takeover scenarios;
  green on the Windows/macOS CI legs.
- **AC-R3-01** `session_identity.py` is the only module touching session stores
  (residue grep contract test); coherence contract test passes (FR-R3-02).
- **AC-R4-01** `dadaia context bind <ctx>` (no `--mode`) exits 0; session record has
  `mode: read`; gate blocks a MUTATING write from that session **with no env vars set**
  (harness-real path); block message contains no auto-rebind nag — it MAY name
  `bind --mode implementation` as the documented path to write rights (FR-R4-01..03).
- **AC-R4-02** No-bind/no-env session: MUTATING write on a free lease proceeds
  (FR-R4-04).
- **AC-R5-01** `claude_hook_env()`/`codex_hook_env()` fixtures exist; contract tests
  fail on (a) out-of-fixture `DADAIA_*` setenv (full namespace, explicit allowlist) and
  (b) direct hook-module import+call in `tests/**/hooks|gate/**`; new hook-subprocess
  tests green on the Windows/macOS CI legs.
- **AC-R5-02** The four qa-named drift-ratifying tests are removed/replaced, evidenced
  by the named file:lines removed (`test_lease_property.py:74`,
  `test_lease_activity_exemption.py:27`, `test_post_gate_heartbeat.py:79`,
  `test_pricing.py:47,212`/`test_model_mapping.py:25`) recorded in CLOSURE; AC-R1-01's
  matrix includes an in-repo variant per class (mechanical replacement for the
  unmechanical residue grep); bash-hook pinning covered by T-010-13's residue contract.
- **AC-R5-03** 7/7 open bugs each have a named regression test (table in CLOSURE).
- **AC-R6-01** Bash quartet absent from `public/scripts/`, manifest, and projections;
  `dadaia public doctor` exit 0; `pre-push-ci-gate.sh` present.
- **AC-R6-02** Five doctor invariants: one failing fixture each (unit-tested) and
  `dadaia specs doctor` exit 0 on the repaired workspace ledger.
- **AC-R6-03** v0.1.9 CLOSURE.md exists; no duplicate release ids under releases +
  archive; mapping README present.
- **AC-R6-04** Contradiction table C-1..C-14 → commit/file:line, complete in CLOSURE;
  reviewer spot-checks C-2, C-5, C-7, C-12 minimum.
- **AC-R6-05** Generated `.claude/settings.json` PreToolUse write-gate matcher is
  scoped (not empty); PostToolUse fires on all tools (unit test on runtime_config).
- **AC-R7-01** `dead()` on a tree with untracked files and no `--commit` refuses and
  pushes nothing; with `--commit`, a planted fake secret blocks the push (tests).
- **AC-R7-02** Privacy check with operator denylist absent still scans the baseline
  list and flags a planted IP/hostname (test); `[ok] public-privacy` only after a real
  scan.
- **AC-R7-03** Tokenless loopback request to a sensitive panel API → 401 (e2e/unit);
  pre-existing 0o644 token tightened to 0o600 on `ensure_token`.
- **AC-R8-01** `core/model_registry.py` single source; key-set equality contract test;
  haiku id `claude-haiku-4-5-20251001` in both views; `claude-fable-5` resolves for the
  5 retiered agents; `dadaia public doctor` model check green; mypy --strict +
  import-linter pass.
- **AC-R8-02** `dadaia ci preflight` exits 0 on a clean tree (full run, no
  `--no-verify`); no `.ruff_cache`/`.mypy_cache` at repo root afterwards.
- **AC-R8-03** Pre-push gate unit tests (fake tree): DADAIA_BIN honored; workspace-venv
  walk-up found; fail-closed error when none. Manual smoke: `git push` from
  `repos/dadaia-workspace/` runs the suite.
- **AC-R8-04** Import-linter ignore-list cap test fails when an edge is added beyond
  the recorded count.

---

## Out of scope

- Classifying Bash command strings in PreToolUse (Decision D-2 — documented honestly
  instead).
- Harness config changes to propagate `DADAIA_*` env into hook subprocesses (session
  record + stdin payload are the channels).
- Multi-holder/queued leases; lease schema beyond the `pid` field.
- Bulk model-catalog expansion beyond registry consolidation.
- ctx-inject payload slimming (ai §4 bloat finding) and rules-tree scoping (S-5/S-6) —
  backlog returns, not release scope.
- Reopening archived releases; PyPI publish (operator-gated as always).

## Dependencies and risks

- **R1 touches the fail-open/fail-closed boundary** — full gate integration matrix must
  re-run; PROTECTED ordering unchanged and re-asserted.
- **R2 PID probe platform-sensitivity** — mitigated by the existing v0.1.8 seam
  (`has_os_kill_liveness`, non-destructive OpenProcess on Windows); TTL fallback where
  unprobeable. PID-reuse false-alive accepted (worst case = today's block-not-steal,
  never theft).
- **R3 is a refactor under live state** — legacy artifacts ignored-and-superseded;
  doctor coherence check catches residue.
- **PostToolUse latency** — renew is one JSON read + atomic write; accept < 10 ms,
  else sample.
- **R6 constitution edits** require explicit operator confirmation before commit.
- **Sequencing risk** — memory/constitution rewrite (R6.4) must land AFTER R1–R4 code
  is merged, in CLOSURE, so it documents the fixed contract (arch F4 gate).
- **WS-R8 registry refactor** changes telemetry import surface — mypy --strict + full
  pytest before merge; `features/public/ → core/` import-linter edge verified first.
