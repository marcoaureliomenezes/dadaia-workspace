# PLAN — Release: spec-context-session-locks-v1

**Status:** Aprovado
**Release ID:** spec-context-session-locks-v1
**Owner:** product-engineer
**Opened:** 2026-05-30

---

## 1. Dependencies (activation gate)

This release may NOT enter IMPLEMENTATION until:

1. **`spec-context-tree-v2` (R1) phase = ARCHIVED.** The `releases/` directory structure
   from R1's T-4 must be present in the scaffold. T-10's `context bind` command writes
   lock files into that tree.
2. **`go-open-source` phase = ARCHIVED.** R2 modifies `sdd-spec-gate.sh` (T-13), which
   R1 also touched (T-8a). Zero concurrent writes on gate scripts.
3. **Operator approval of SPEC.md + this PLAN.md** — both `**Status:** Aprovado` required
   before TASKS advance to IMPLEMENTATION.

OQ-3 (OpenCode post-tool hook compatibility) must be confirmed by `devops-engineer`
before T-13 starts. If a runtime lacks post-tool hook support, the heartbeat must be
inlined into `sdd-spec-gate.sh` as an exit hook. Devops-engineer must report back to
product-engineer before PLAN is finalized.

---

## 2. Strategy overview

This is a MAJOR semver break (2.0.0). The work falls into four sequential layers:

**Layer 1 — Full state model break (T-10a → T-10b → T-10c → T-10d)**
Replaces the entire `ATIVO/INATIVO` + `is_primary` model. T-10a (models + store) and
T-10c (migrate command) must ship together — a v2 model without a migration command
breaks all existing consumers immediately. T-10b (service methods) and T-10d (CLI verbs)
follow in that order. No lock code yet; this layer is purely the model refactor.

**Layer 2 — Three-layer lock architecture (T-11)**
Depends on T-10 (service methods and models must exist). Introduces workspace-wide fcntl
Lock 1, per-context Lock 2, and per-release implementation Lock 3 (JSON file). Closes
R-1, R-3, R-4, R-5, R-8. Also implements the Impl-XOR-Review mutual exclusion at Lock 3
(closes R-9 partially — path-policy matrix completes in T-13).

**Layer 3 — Heartbeat + TTL + doctor LOCK invariants (T-12)**
Depends on T-11 (lock files must exist). Implements the 300-second heartbeat protocol,
staleness check, audited reclaim, and doctor LOCK-1..LOCK-6 invariants. Closes R-10.

**Layer 4 — Pre/post-tool hooks and gate rewrite (T-13)**
Depends on T-12 (heartbeat and staleness check must exist; RULE E checks staleness
before verifying lock ownership). Introduces RULE E in `sdd-spec-gate.sh`, the new
`sdd-post-gate.sh` post-tool hook, and completes T-8 by resolving active release from
the implementation lock. `devops-engineer` injects hooks into all three runtimes after
`software-engineer-python` finalizes the hook scripts.

---

## 3. Internal task ordering DAG (SPEC §13.2 — verbatim)

```
T-10a (models + store)
  ↓
T-10b (service methods: alive/dead)
  ↓
T-10c (migrate command)       ← T-10a and T-10c MUST ship together
  ↓
T-10d (CLI verbs: alive/dead/bind/release)
  ↓
T-11 (three-layer lock architecture)
  ↓
T-12 (heartbeat + TTL + doctor LOCK-*)
  ↓
T-13 (RULE E + sdd-post-gate.sh + hook injection)
```

T-13 has an intra-task dependency: `software-engineer-python` finalizes hook scripts
first; `devops-engineer` injects into runtime settings only after scripts are confirmed.

---

## 4. Layers affected

| Layer | Changed by |
|-------|-----------|
| `core/models/spec_context.py` | T-10a |
| `infrastructure/json_context_store.py` | T-10a, T-11 (fcntl Lock 1) |
| `features/spec_context/service.py` | T-10b, T-11, T-12 |
| `features/spec_context/doctor.py` | T-10a (remove INV-1..3,6), T-12 (LOCK-1..6) |
| `cli/commands/context.py` | T-10d |
| `cli/commands/migrate.py` | T-10c (new command) |
| `public/scripts/sdd-spec-gate.sh` | T-13 (RULE E + lock-based release resolution) |
| `public/scripts/sdd-post-gate.sh` | T-13 (new file) |
| `.dadaia/agentic/manifest.json` | T-13 (new post-gate asset registered) |
| `.dadaia/sessions/`, `.dadaia/locks/`, `.dadaia/states/ctx_locks/`, `.dadaia/logs/` | T-10c (created by migrate), T-11 |

No changes to `public/scaffold/` or `public/templates/` (those are R1).

---

## 5. Race remediation coverage

All HIGH-severity races must be closed before CLOSURE. Per SPEC §4:

| Race | Severity | Closed by | Task |
|------|----------|-----------|------|
| R-1 | HIGH | Workspace-wide fcntl Lock 1 | T-11 |
| R-2 | HIGH | Design elimination (`promote` removed) | T-10 |
| R-3 | MED | Per-context Lock 2 | T-11 |
| R-4 | HIGH | Per-context Lock 2 + ContextLockedError | T-11 |
| R-5 | MED | Workspace-wide Lock 1 | T-11 |
| R-6 | LOW | Deferred to backlog (fail-open acceptable) | — |
| R-7 | LOW | By design (records < PIPE_BUF) | T-11 |
| R-8 | HIGH | Per-release Lock 3 + RULE E | T-11 + T-13 |
| R-9 | HIGH | Path-policy matrix in RULE E | T-13 |
| R-10 | MED | TTL + heartbeat + doctor LOCK-3 | T-12 |

---

## 6. Technical risks and mitigations

| Risk | Mitigation |
|------|-----------|
| OQ-3: OpenCode post-tool hook incompatibility | Devops-engineer confirms before T-13; fallback: inline heartbeat in pre-tool hook exit path |
| Migration guard breaks CI pipelines upgrading to 2.0.0 | Migration guard documented in 2.0.0 release notes; `dadaia migrate --yes` is CI-safe (idempotent on v2) |
| fcntl not available on Windows | Documented as Linux/macOS-only (ADR D-4; no Windows support claimed) |
| T-10a/T-10c must ship atomically | Single PR or single commit covering both; CI gate enforces |
| Residual TOCTOU on review→impl bind check | Accepted (sub-ms window, lower severity than R-8 per SPEC §3 T-10d) |

---

## 7. Validation plan

Per SPEC §11 acceptance criteria summary:

- **AC-RACE-1..6:** 6 deterministic race reproduction tests using `threading.Barrier`/
  `threading.Event`. No `time.sleep`. All pass (not xfail) after R2. CI check for
  `time.sleep` in tests (hard gate per AC-RACE-2).
- **AC-LOCK-1..9:** 9 lock state machine tests.
- **AC-T11-1..12:** 12 lock architecture tests including BOUND_REVIEW mutual exclusion.
- **AC-T12-1..7:** 7 heartbeat/TTL/doctor tests.
- **AC-T13-1..10:** 10 hook integration tests (session identity, path-policy, heartbeat).
- **AC-DOC-L1..L12:** 12 doctor LOCK invariant tests on real `tmp_path`.
- **AC-REV-1..5:** BOUND_REVIEW mode tests.
- **Coverage thresholds:** `json_context_store.py` ≥ 95%, `service.py` ≥ 90%,
  `doctor.py` ≥ 90% (AC-COV-1..3).
- QA source: `.dadaia/reports/dadaia-workspace/qa-engineer/
  2026-05-30T120000Z-test-strategy-spec-context-v2.html` §3, §4.3, §5, §7.2.

---

## 8. Rollback

This is a MAJOR breaking change. Rollback means reverting to the last 1.x tag. The
migration command is one-directional (no v2→v1 downgrade command). Consumer CI must
pin to `< 2.0.0` until ready to migrate. The `schema_version: "1"` guard in the loader
prevents silent corruption on rollback.

---

*Product Engineer — dadaia-workspace | 2026-05-30*
