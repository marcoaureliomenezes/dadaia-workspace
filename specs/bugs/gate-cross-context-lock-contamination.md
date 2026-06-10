---
name: gate-cross-context-lock-contamination
status: Closed
severity: CRITICAL
reported: 2026-06-09
surface: sdd-spec-gate.sh — CONTEXT_SLUG resolution + MUTATING lease acquire
session_id: null
resolved_in: 0.1.7 (rc-4, T-017-29)
---

**Resolution (0.1.7 rc-4, T-017-29):** `sdd-spec-gate.sh` now resolves CONTEXT_SLUG from the write-target path (`repos/<slug>/…`) instead of first-ALIVE; if under no repo → UNGATED (no lease). Verified: integration test `test_no_cross_context_lease_contamination` (write to repo A while repo B lease is live → ALLOW) + `test_mutating_blocked_by_live_foreign_lease` (same-repo foreign-live → BLOCK). Reprojected live; the false `[SDD LOCK]` that was blocking this very release no longer fires. The Bash/CLI-bypass note (lease only mediates agent Write/Edit) is tracked separately per ADR-3 (backlog `lease-shell-write-coverage-gap`).


> **Severity escalated HIGH → CRITICAL (2026-06-09).** This defect makes the **single
> deterministic lock the product keeps after 0.1.7 rc-3** (the per-Spec-Context lease)
> fire **across unrelated contexts**, falsely blocking a legitimate workflow. That is the
> exact failure mode the operator's law forbids ("no workflow is ever lock-blocked; locks
> serialize only the SAME Spec Context, one bound session"). Two sessions on **different**
> repos must NEVER contend — here they do. Confirmed live (below), actively blocking work.

## Confirmed live reproduction (2026-06-09) — bidirectional

Observed while finalizing release 0.1.7 rc-3. A second, genuinely live **Codex** session
(`f94f1f66-…`, OS pid 783932) was working the **`dadaia-agents`** repo. My Claude session
(`a1b1b325-…`) was working **`dadaia-workspace`**. Disjoint repos — yet I was `[SDD LOCK]`
blocked. Gate log (`/tmp/sdd-gate.log`) proves the mechanism:

```
# Codex edits a DIFFERENT repo's release file...
tool=Edit path=…/repos/dadaia-agents/specs/releases/v0.1.0/TASKS.md
class=MUTATING ctx=dadaia-workspace session=f94f1f66…  ALLOW: lease RENEWED ctx=dadaia-workspace
# ...which RENEWS the dadaia-workspace lease (wrong context!). Then my legit write:
tool=Edit path=…/repos/dadaia-workspace/specs/releases/0.1.7/SPEC.md
class=MUTATING ctx=dadaia-workspace session=a1b1b325…  BLOCKED: live-foreign lease
```

The audit log shows the lease ping-ponging between `a1b1b325` (me, dadaia-workspace),
`f94f1f66`/`bf85f523`/`076107cb` (other sessions touching other repos) — all keyed onto the
**dadaia-workspace** lease because none exported `DADAIA_CONTEXT` and all fell back to the
first-ALIVE context.

## Definitive root cause (two compounding defects in `sdd-spec-gate.sh`)

1. **Context is resolved globally, not from the write target.** `CONTEXT_SLUG`
   (lines ~69-90) resolves from `DADAIA_CONTEXT` → **first ALIVE** in `spec_contexts.json`
   → session file. It is **never derived from `FPATH`**. So a write to
   `repos/<other>/…` resolves to `dadaia-workspace` (the first ALIVE) whenever
   `DADAIA_CONTEXT` is unset — which it is for every harness that doesn't export it
   (Codex, and Claude subagents).
2. **The MUTATING classifier is context-agnostic.** `*/specs/releases/*`,
   `*/specs/memory/*`, etc. (lines ~101-107) match **any** repo's specs path → CLASS=MUTATING.
   The lease is then acquired with the **mis-resolved** `CONTEXT_SLUG` (line ~195) and the
   active release is read from `repos/$CONTEXT_SLUG/specs/releases/ACTIVE.md` — the wrong
   repo entirely.

Net: a session mutating context **B** acquires and heartbeats the lease of context **A**,
blocking a legitimate session on **A**. Cross-context false mutual exclusion.

## Fix direction

Derive the lease context **from the write target path**: if `FPATH` is under
`$WS/repos/<slug>/…`, use `<slug>` as `CONTEXT_SLUG` for classification AND lease
acquisition, overriding the first-ALIVE/env fallback. Only fall back to env/first-ALIVE
for targets not under any `repos/<slug>/`. Then two sessions on different contexts can
never contend, and the lease serializes strictly per-context as the rc-3 law requires.
Add an integration test: two distinct sessions, two different `repos/<slug>/specs/releases/`
targets, simultaneous → both ALLOW (no cross-block); same target+context, foreign live →
BLOCK.

## Relation to other work

- This is the bug behind the false `[SDD LOCK]` hit during 0.1.7 rc-3 finalization.
- It directly degrades the lease retained by rc-3 (`specs/releases/0.1.7/SPEC.md`), so it is
  the natural **next** lock-correctness fix (rc-4 or a 0.1.8 item).
- Companion to the persona-propagation theme: both stem from runtime identity/context not
  reaching the gate. See `codex-dispatched-agent-persona-not-propagated-to-sdd-gate.md`
  (closed by rc-3) and the backlog epic
  `harness-agentic-entities-and-determinism-parity.md`.

**Symptom:** When `DADAIA_CONTEXT` is not set in the agent's shell environment, the
SDD gate resolves `CONTEXT_SLUG` by falling back to the *first ALIVE context* in
`spec_contexts.json` (e.g. `dadaia-workspace`). It then attempts to acquire/check a
lease for *that* slug — even when the write target path is under a completely different
context's repo (e.g. `repos/dd-chain-explorer/`).

This causes a false `[SDD LOCK]` block: the live foreign lease for `dadaia-workspace`
prevents writes to `dd-chain-explorer` specs, even though `dd-chain-explorer` has no
active lease of its own. The two contexts have disjoint repos and independent specs
directories.

**Repro:**
1. Workspace has `dadaia-workspace` as the first ALIVE context in `spec_contexts.json`.
2. Another session (`a1b1b325-...`) holds a live `dadaia-workspace` IMPLEMENTATION lease
   (heartbeat active, TTL 120s).
3. A new Claude Code session attempts `Edit` on
   `repos/dd-chain-explorer/specs/releases/audit-remediation-r5/TASKS.md`.
4. `DADAIA_CONTEXT` is NOT set in the agent's shell environment (it was only in the
   dispatch prompt text, not exported).
5. Gate resolves `CONTEXT_SLUG=dadaia-workspace` (wrong — should infer `dd-chain-explorer`
   from the target path).
6. Gate checks `dadaia-workspace` lease → live-foreign conflict → BLOCKS the write.

**Expected:** The gate should infer the target context from the write path itself when
`DADAIA_CONTEXT` is not set. Specifically, for a path matching
`$WS/repos/<slug>/specs/...`, the gate should use `<slug>` as the context slug for lease
resolution, regardless of which context is first-ALIVE in `spec_contexts.json`.

Alternatively: the gate's path-classifier (lines 117-119 of `sdd-spec-gate.sh`) already
uses `$CONTEXT_SLUG` to check if a path is `MUTATING`. This same path-match logic
`$WS/repos/$CONTEXT_SLUG/*` could be used to infer the slug from the target path —
walk `spec_contexts.json` to find which ALIVE context slug matches the target path prefix,
and use that for lease acquisition.

**Notes:**
- `sdd-spec-gate.sh` source path: `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
- Bug manifested in session dispatched with `DADAIA_CONTEXT=dd-chain-explorer` as prompt
  text but without the env var exported into the Claude Code subprocess environment.
- The `DADAIA_CONTEXT` env var convention (from the workspace protocol) is the
  recommended fix for operators, but the gate should still handle the no-env-var case
  gracefully by inferring context from the target path.
- Workaround: operator sets `DADAIA_CONTEXT=dd-chain-explorer` in the session env before
  dispatching, OR waits for the foreign lease to expire (120s TTL, but will be renewed
  if the foreign session is still active).
