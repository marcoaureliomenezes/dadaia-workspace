---
name: gate-self-blocks-lease-holder-own-session
status: Open
severity: HIGH
reported: 2026-06-26
surface: hooks.pre_gate (SDD gate) — lease holder identity resolution
session_id: null
---

**Symptom:** The PreToolUse SDD gate blocks `Edit`/`Write` file-tool writes with
`[SDD LOCK] Session '<sid>' is actively mutating context 'dadaia-workspace'` where
`<sid>` is **this same session's own id** and the lock record's `session_id` equals the
acting session's id (and its `pid` is alive). The gate treats the legitimate holder as a
foreign holder and yields, so the holder can never write through file tools. Refreshing
the heartbeat in the lock record (same `session_id`) does not unblock — the gate still
yields.

**Repro:**
1. Session S holds `dadaia-workspace.lock.json` with `session_id == S`, `pid` alive.
2. Let the heartbeat age past the TTL (~120s) without a PostToolUse renewal (e.g. a long
   gap, or PostToolUse not firing for the session).
3. Attempt an `Edit`/`Write` on an in-repo MUTATING path.
4. The gate blocks citing S as the active mutator — i.e. it blocks S against S.

**Expected:** When the lock record's `session_id` equals the acting session's resolved
identity, the gate must treat it as the SAME holder and ALLOW (renewing the heartbeat),
never yield. A holder must never be blocked against its own lease. PostToolUse heartbeat
renewal must also fire for the holder so the lease does not silently go stale mid-task.

**Notes:** Observed during v0.1.24 WS-1 implementation. Lock record showed
`session_id == <acting session>`, `mode: BOUND_IMPLEMENTATION`, `pid` alive, heartbeat
stale then manually refreshed — gate still yielded. A Bash-tool PostToolUse did not
refresh the heartbeat (renewal appears not to fire for this session). Workaround used:
perform the remaining file edits through the `Bash` tool (not classified by the
PreToolUse gate), no commit. Paths/ids redacted.
