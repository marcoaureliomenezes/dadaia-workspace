# PLAN — Release v0.1.76 — Lock liberation (advisory presence)

**Status:** Aprovado

## Architecture

**New module** `features/spec_context/presence.py` — the ONLY concurrency-signal
surface:
- `upsert(workspace, ctx, session_id, *, runtime, pid) -> None` — atomic
  temp+`os.replace` write of `.dadaia/states/presence/<ctx>/<session_id>.json`;
  swallows every exception (presence must never fail a write).
- `others_alive(workspace, ctx, session_id) -> list[PresenceRecord]` — sibling records
  with fresh heartbeat (TTL = `LEASE_TTL_SECONDS`) excluding self; corrupt/stale
  records skipped (and opportunistically GC'd).
- `renew(workspace, session_id)` — heartbeat touch of every presence record the
  session owns (PostToolUse path).
- `clear(workspace, session_id, ctx=None)` — delete own records (context release /
  session stop).
- `sweep(workspace) -> list[str]` — GC stale records (doctor).

**Gate** (`gate_policy.py`): the MUTATING mode!=READ branch becomes:
`presence.upsert(...)`; `others = presence.others_alive(...)`; if others and not
throttled → ALLOW with advisory message; else ALLOW silent. No lease import. Advisory
throttle: marker file `.dadaia/tmp/presence-warn-<sid>-<ctx>` (mtime, e.g. 300s).

**Deletions** (lease.py + callers): `acquire`, `LockHeldError` blocking path,
sentinel CAS helpers, `adopt_if_own_lineage`, by-session index, incumbent `.ptr`
authority (`session_identity.set_incumbent/read_incumbent_ptr` callers repointed or
removed), `lock steal` CLI, `pre_commit_decision` BLOCK rung. Mode resolution in
`gate_policy._resolve_mode`: drop rung-3 (context incumbent), keep env → own session
record → IMPLEMENTATION.

**Kept:** locking.py micro-locks (with `PLATFORM.has_fcntl` seam), PROTECTED/FROZEN/
MEMORY/READ path classes, `.dadaia/sessions` records (mode/identity storage), bind-epoch
memory-injection machinery, pre-push security gate, lock-events JSONL (new event names:
PRESENCE_UPSERT/PRESENCE_WARN/PRESENCE_GC — appended, schema additive).

**PI parity (FR5):** `.pi` L1 extension source under `dadaia_workspace/public/` emits
stable session id + pid on both hooks; hook-side guard: `anon-session` (or absent id)
never creates a presence record.

## Tasks → ordered waves

- **T-1 (RED first):** new invariant tests: presence module contract; gate
  concurrent-write-allows; rebind-never-blocks executed path (the CRITICAL bug probe);
  pre-commit always-ALLOW matrix; READ self-scope / foreign-bind-never-changes-mode.
  These FAIL against the current blocking implementation where they assert the new
  truth (e.g. two-session write currently raises LockHeldError → test asserts ALLOW).
- **T-2:** presence.py + gate rewrite + mode self-scoping (make T-1 green).
- **T-3:** lease.py demolition + chokepoint WARN-only + CLI verbs (`lock steal` gone,
  `context release` presence-based) + retired-test re-baseline (delete/flip the
  no-steal descendant rows — QA-adjudicated list recorded in CLOSURE).
- **T-4:** surfaces repoint (doctor, panel, `context show`, lifecycle preflight
  `_check_lease` → presence advisory) + PI extension parity + platform seam (FR6).
- **T-5:** full-suite green + mypy + doctor; executed-path harness probes; QA review;
  security push-gate; ship.

## Risks

- Test blast radius: the lease/no-steal suite rows are numerous — every deletion is
  listed in CLOSURE (re-baseline law), never silent.
- Hidden lease readers: grep-driven inventory (`lease.`, `LockHeldError`, `acquire(`,
  `incumbent`, `by-session`) before demolition; every reader repointed or deleted in
  the same commit that removes its source.
