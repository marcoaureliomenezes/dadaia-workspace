# PLAN: v0.1.4.5 — gate-env-free-session-resolution

**Status:** Aprovado
**Release ID:** v0.1.4.5
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Strategy

One surgical change to `sdd-spec-gate.sh` (env-free resolution + durable lock
heartbeat), guarded by regression tests, landed via a one-time authorized bash
break-glass (because the gate blocks edits to its own source), then projected via
`dadaia public install`. After landing, the fix is validated end-to-end by binding
the context from a Bash shell (no relaunch) and performing a real production write
through the projected gate.

---

## 2. Execution Order (DAG)

```text
T-SEMA-00  paper trail (SPEC/PLAN/TASKS) + ACTIVE.md → v0.1.4.5   [meta-edits, no env]
      |
      v
T-SEMA-01  patch sdd-spec-gate.sh (SCOPE-01 env-free + SCOPE-02 lock heartbeat)
           via bash break-glass; show git diff
      |
      v
T-SEMA-02  dadaia public stage && install --target all && doctor  (projects patched gate)
      |
      v
T-SEMA-03  bind v0.1.4.5 from Bash (no relaunch) → live end-to-end write proves AC-1
      |
      v
T-SEMA-04  regression tests in test_gate_session_locks.py (AC-1..AC-5) + update AC-T13-1
      |
      v
T-SEMA-05  full pytest -q -p no:cacheprovider (AC-7)
      |
      v
[parallel] T-SEMA-06 code-reviewer ; T-SEMA-07 security-reviewer  (enforcement-core pairing)
```

---

## 3. Design

### 3.1 RULE E env-free resolution (SCOPE-01)

In `_rule_e()` Step 1, before the hard block on empty `DADAIA_SESSION_ID`, insert
a fallback: when `sess_id` is empty and `CONTEXT_SLUG` is known, iterate
`.dadaia/locks/implementation/<CONTEXT_SLUG>__*.json`; for each, compute
held/stale from `last_seen_at + ttl_seconds` (same logic the rest of RULE E uses);
adopt the `session_id` of the first **non-stale** lock, `export DADAIA_SESSION_ID`
for the remainder of the hook run, and log the adoption. If none adopted, block
with a **no-relaunch** message. Env-set path is untouched (the fallback only runs
when the env var is empty).

### 3.2 Durable lock heartbeat (SCOPE-02)

In the inline heartbeat Python at the tail of the script (the block that renews the
session file's `last_seen_at`), after computing `context`/`release`, also open
`.dadaia/locks/implementation/<context>__<release>.json`; if its `session_id`
matches the current session, renew its `last_seen_at` atomically (tmp + os.replace),
matching the session-file renewal style. Best-effort: failures are swallowed; the
gate never blocks on heartbeat I/O.

### 3.3 Tests (SCOPE-03)

Use the existing helpers (`_install_scripts`, `_make_primary_context`,
`_make_active_release`, `_make_session_file`, `_make_impl_lock`, `_run_gate`,
`_stale_ts`). New tests follow AC-T13-4's shape but pass `session_id=None` to
`_run_gate` so the env var is absent and the fallback must resolve from the lock.

---

## 4. Implementation Surfaces

Area | Owner | Files
---|---|---
RULE E env-free + lock heartbeat | (break-glass author) | `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
Regression tests | (break-glass author) | `tests/integration/test_gate_session_locks.py`
Propagation | — | `.dadaia/scripts/sdd-spec-gate.sh` (via `dadaia public install`)
Code review | code-reviewer | reports only
Security review | security-reviewer | reports only

---

## 5. Validation Commands

```bash
# After patch + stage + install:
diff -q dadaia_workspace/public/scripts/sdd-spec-gate.sh .dadaia/scripts/sdd-spec-gate.sh  # identical
dadaia public doctor   # exit 0

# Targeted regression
pytest -q -p no:cacheprovider tests/integration/test_gate_session_locks.py

# Full suite (no regression)
pytest -q -p no:cacheprovider
```

---

## 6. Risks and Mitigations

Risk | Mitigation
---|---
Break-glass bypasses SDD discipline for one file | Single authorized file; git diff shown; covered by SPEC + tests + dual review
Adopting a wrong/foreign lock | Only one impl lock exists per `context__release`; only non-stale adopted; ownership re-verified downstream in RULE E step 4c
Stale-lock adoption reintroducing races | Stale locks explicitly excluded; matches existing held/stale logic
Hidden dependence on old "DADAIA_SESSION_ID is not set" wording | Only AC-T13-1 asserts that wording; updated in SCOPE-03
Projection drift (source patched, projection not) | T-SEMA-02 install + `diff -q` source vs projection in validation
