# PLAN: v0.1.10 — Concurrency Kernel + Workspace Truth

**Status:** Em revisão
**Release ID:** v0.1.10
**Owner:** product-engineer
**Created:** 2026-06-10 (revised same day for the R1–R8 extension)

---

## Strategy

Eight workstreams in dependency order R1→R8 (audit `index.md §6`), executed as five
parallel tracks. The kernel track (R1→R3→R2/R4) is the centerpiece — the concurrency/
identity foundation is rebuilt once, soundly, instead of a fifth symptom pass. The test
kernel (R5) lands its fixtures FIRST so kernel acceptance runs on harness-real
environments. Truth pass (R6) documents the FIXED contract, so its memory/constitution
half executes at CLOSURE. Security tail (R7) and anti-drift (R8) are independent.

No state migration: legacy session artifacts are ignored-and-superseded; old lease
records remain readable (new `pid` field optional on read, written on acquire).

## Layers affected

| WS | Files | Layer |
|---|---|---|
| R1 | `features/spec_context/gate_policy.py` | features |
| R2 | `features/spec_context/lease.py`, `hooks/sdd_post_gate.py`, `core/lock_liveness.py` (consume) | features + hooks |
| R3 | `features/spec_context/session_identity.py` (new), `hooks/ctx_inject.py`, lease/gate consumers | features + hooks |
| R4 | bind CLI (`cli/…context…`), `hooks/sdd_gate.py` | cli + hooks |
| R5 | `tests/` (fixtures, matrix, contract tier, two-actor helper) | tests |
| R6 | `public/scripts/` (delete quartet), `features/specs/doctor.py`, `infrastructure/runtime_config.py`, public agents/skills/rules/schemas, `specs/` ledger+memory+constitution | public + features + infra + specs |
| R7 | `features/spec_context/service.py` (dead), `infrastructure/privacy_check.py`, `features/panel/{handler,auth}.py`, `pyproject.toml` dev pins | features + infra |
| R8 | `core/model_registry.py` (new), `infrastructure/runtime_transforms/model_mapping.py`, `features/telemetry/pricing.py`, `features/public/` doctor, `features/ci_preflight/service.py`, `public/scripts/pre-push-ci-gate.sh`, `setup.cfg` cap | core + infra + features + public |

## Execution order and parallelism

```
PRE   T-010-01 (verify opencode supersession)  T-010-02 (verify fable-5 precondition)

TRACK K — kernel (sequential spine, R1 first)
  T-010-10 (R5 harness-env fixtures — FIRST: kernel acceptance depends on them)
  T-010-03 (R1 classifier re-root + matrix + symlink + incident regression)
  T-010-07 (R3 session_identity module)
  ── then in parallel (disjoint files):
  T-010-04 (R2 PostToolUse heartbeat)   T-010-05 (R2 pid probe, no-steal)
  T-010-08 (R4 bind persists mode)  →  T-010-09 (R4 gate mode resolution)
  T-010-06 (R2 two-actor e2e — after 04+05)

TRACK T — test kernel (after K lands the behavior)
  T-010-11 (fixture matrix + kill drift-ratifiers)  →  T-010-12 (escape-matrix regressions)

TRACK R — registries / push gates (independent)
  T-010-23 (model registry)  →  T-010-24 (public doctor model check)
  T-010-25 (ci-preflight self-pollution)   T-010-26 (pre-push venv probe)
  T-010-27 (consistency contracts + linter cap — after 23)

TRACK S — security tail (independent)
  T-010-19 (dead() gate)  T-010-20 (privacy fail-closed)  T-010-21 (panel auth)  T-010-22 (dev pins)

TRACK D — truth pass
  T-010-13 (bash quartet retirement)   T-010-14 (doctor invariants)   T-010-18 (matcher scoping)
  T-010-15 (PE: v0.1.9 retro-closure + archive repair — after 14)
  T-010-17 (ai-engineer: C-1..C-14 honesty rewrite — after K + 13)
  T-010-16 (PE: memory + constitution rewrite — CLOSURE phase, after everything)

FINAL T-010-28 (full release gate)
```

Tracks K/R/S and (13,14,18) of D are file-disjoint and may run concurrently. The only
hard spine is 10 → 03 → 07 → {04,05,08} → {09,06} → 11 → 12, and 16 last.

## Technical approach (condensed)

### R1 — classifier re-root (gate_policy.py)
Compute `ctx_rel = strip("repos/<slug>/", ws_rel)` (None when not under `repos/`);
run the SAME ordered taxonomy (ADDITIVE prefixes → MEMORY → FROZEN → releases/MUTATING)
against `ctx_rel` when present, else against `ws_rel`. PROTECTED stays first and
root-keyed. RULE A (memory phase from ACTIVE.md) and RULE B (frozen) now execute for
in-repo paths — re-run the full gate integration matrix; fail-open posture unchanged.

### R2 — liveness (lease.py + sdd_post_gate.py)
- `sdd_post_gate`: resolve session id via `_common.resolve_session_id` (stdin payload
  first, env override), call `lease.renew_heartbeat(ws, ctx, sid)` before/outside any
  session-file guard; context via PATH-irrelevant fallback (`DADAIA_CONTEXT` →
  first-ALIVE); broad try/except, always exit 0.
- `lease.acquire`: on TTL-stale record, read `record.pid`; if
  `PLATFORM.has_os_kill_liveness` and probe says alive → raise/Block (no TAKEOVER);
  dead/unprobeable → TAKEOVER (today). Record `pid=os.getpid()` of the hook process? No
  — pid of the *holder session* is not knowable from the hook; record the hook-writer
  pid lineage is useless. Instead: record the pid written by the session_identity
  record at bind/first-acquire (the harness process tree root when resolvable), with a
  documented fallback to TTL-only when `pid` is absent. The implementer validates which
  pid is stable per harness and documents it in the module; acceptance only requires:
  alive-probe ⇒ no steal, dead/absent ⇒ TTL behavior.
- `renew_heartbeat`: allow confirmed holder to renew past TTL; make the
  read-check-write atomic w.r.t. acquire (reuse the O_EXCL sentinel CAS or
  write-to-temp + rename with holder re-verify), eliminating the lease.py:379-394 race.

### R3 — session_identity.py
Single module: `read_session(sid)`, `write_session(sid, mode, pid, …)`,
`incumbent(ctx)`, `set_incumbent(ctx, sid)`. Storage: `.dadaia/sessions/<sid>.json` +
lease record; the dual `.ptr` files become derived/removed (ctx_inject and lease.py:330
migrate to the module). Contract test: no other module opens these paths.

### R4 — mode channel
CLI: `--mode` optional, default `read`; bind writes the session record via R3.
Gate (`sdd_gate.py`): mode = env `DADAIA_MODE` (fast-path) → session record → default
IMPLEMENTATION. READ ⇒ block MUTATING (message: no rebind instruction), allow
ADDITIVE/UNGATED, PROTECTED unchanged. Evaluated after PROTECTED short-circuit, before
`gate_policy.evaluate` lease acquisition.

### R5 — test kernel
`tests/conftest.py` (or `tests/fixtures/harness_env.py`): `claude_hook_env()` /
`codex_hook_env()` returning the pinned minimal env dicts; helper to run a hook module
as subprocess with stdin JSON envelope. Contract test greps hook/gate/lease suites for
out-of-fixture `DADAIA_*` setenv. Two-actor helper generalizes
`test_two_process_denial.py` (spawn real processes, file rendezvous, assert on lock-file
history). Fixture matrix via parametrize: contexts×slug×seeding.

### R6 — truth pass
- Quartet deletion: remove 4 `.sh` + `__pycache__` from `public/scripts/`, manifest,
  staging expectations, projection tests; keep `pre-push-ci-gate.sh`; fix
  `gate_policy.py:3-8` docstring; residue grep contract.
- Doctor invariants in `features/specs/doctor.py`: phase↔markers, CLOSURE-before-
  archive, unique release ids (releases ∪ _archive, rglob), `^v\d+\.\d+\.\d+$` naming
  (WARN for documented legacy), constitution ref resolution; plus lease↔session
  coherence backstop (D-2).
- Ledger repair (PE, Write/Edit + git mv via devops/operator): v0.1.9 CLOSURE.md from
  implemented evidence; archive v0.1.9; rename `_archive/releases/v0.2.0/v0.1.{6..9}` →
  `milestone-{1..4}` (or equivalent) + mapping README.
- Honesty rewrite (ai-engineer): edit canonical sources under
  `dadaia_workspace/public/`, then stage/install/doctor (lib-guardrail workflow); C-12
  matcher fix is code (`runtime_config.py`, software-engineer, T-010-18).
- Memory/constitution (PE, CLOSURE): rewrite to post-fix contract; constitution diff
  presented to operator for explicit confirmation before commit.

### R7 — security tail
`dead()`: tree-clean check before auto-commit; `--commit` flag + privacy-engine scan of
staged content, block on findings. Privacy baseline denylist as packaged data
(importlib.resources). Panel: drop `loopback_bypass` default (Bearer always) or
Host/Origin check — pin via test. `ensure_token`: stat existing file, chmod 0o600 via
platform seam. Dev pins in pyproject + lock regen.

### R8 — registries + push gates
Registry per prior draft (preserved): `ModelEntry` with dated pricing list; views
derived; doctor check in `features/public/`; verify/add `features/public/ → core`
import-linter edge. ci-preflight: `ruff --no-cache`, `MYPY_CACHE_DIR=<ws>/.dadaia/tmp/...`
(or `--cache-dir`); conftest pollution guard does pre/post snapshot diff. Pre-push
probe order: `DADAIA_BIN` → walk-up `.dadaia/.venv/bin/dadaia` → poetry → `.venv`;
fail-closed message when none. Linter cap: contract test pins the ignore-edge count.

## Validation plan

1. `pytest -p no:cacheprovider` full suite — 0 failures (includes new matrix,
   two-actor e2e, contract tier).
2. `ruff format --check && ruff check --no-cache` clean; `mypy --strict` clean.
3. `import-linter` — 0 violations; ignore-list count ≤ recorded cap.
4. `dadaia public doctor` exit 0 (model check + quartet absence).
5. `dadaia specs doctor` exit 0 on the repaired ledger (new invariants active).
6. `dadaia ci preflight` exit 0 on a clean tree (AC-R8-02 — the gate gates itself).
7. Manual smokes: `git push` from `repos/dadaia-workspace/` without `--no-verify`;
   `dadaia context bind dadaia-workspace` (no `--mode`) exit 0; tokenless loopback
   panel request → 401.
8. Reviewer cross-check: memory/constitution concurrency text vs merged R1/R2 code;
   C-1..C-14 table complete.

## Technical risks

| Risk | L | Mitigation |
|------|---|-----------|
| R1 changes fail-open/fail-closed boundary | M | full gate integration matrix re-run; PROTECTED-first re-asserted |
| Holder-pid not stably knowable per harness | M | acceptance is behavioral (alive⇒no-steal, absent⇒TTL); TTL fallback documented |
| renew/acquire atomicity rework introduces deadlock | M | property/stress test on lock history; fail-open posture preserved |
| R3 refactor breaks live self-hosting state | M | ignored-and-superseded legacy artifacts; doctor coherence backstop |
| Quartet retirement breaks a projection consumer | L | residue grep + projection tests + public doctor in CI |
| PRICING_TABLE view refactor breaks telemetry imports | M | mypy --strict + full pytest before merge |
| PostToolUse latency | L | renew = 1 read + 1 atomic write; accept <10 ms |
| Constitution edit blocked by operator | L | D-3 + §0/§8 diffs presented early at SPEC review |
| ci-preflight guard rescoping hides real pollution | L | snapshot-diff still fails on session-created dirs; unit fixtures per case |
