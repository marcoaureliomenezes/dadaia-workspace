---
name: lease-stolen-by-additive-write-from-live-session
status: Closed
severity: CRITICAL
reported: 2026-06-10
resolved_in: v0.1.10
surface: hooks/sdd_gate.py + spec_context/gate_policy.py + spec_context/lease.py heartbeat model
session_id: null
---

**Resolution (v0.1.10):** Fixed by T-010-03 (classifier re-root — full
class×location taxonomy: in-repo `specs/bugs|audits|backlog` writes classify
ADDITIVE and acquire/steal no lease) together with T-010-04/05 (PostToolUse
heartbeat = real liveness signal, not write-recency; a live holder is never
taken over). Regression tests (all green):
`tests/e2e/test_two_actor_lease.py::test_holder_busy_foreign_additive_allowed_and_never_named`,
`tests/integration/gate/test_classifier_reroot_matrix.py::test_lease_theft_incident_in_repo_additive_does_not_steal`,
and `::test_lease_theft_dual_session_foreign_mutating_still_blocks_live_holder`
(the last proves a foreign MUTATING write is still blocked while the live
holder's pid is alive — the lease is never stolen, only ADDITIVE passes through).


**Symptom:** A second session that only wrote a **bug file** (an ADDITIVE
artifact the product law says is "never gate-blocked, never locked") **took
over the IMPLEMENTATION lease** of a live session that was mid-CLOSURE
final-gate. Observed live, 2026-06-10T00:02:36Z:

- Session A held the `dadaia-workspace` lease (mode IMPLEMENTATION), was
  ALIVE — at 00:00:09Z it started the full-pytest final gate, at 00:02:04Z it
  dispatched a closure re-audit subagent.
- Session B (read-only intent; had run `context bind --mode read`) wrote
  `repos/dadaia-workspace/specs/bugs/<slug>.md` at 00:02:36Z.
- The lock record flipped to: holder = session B, mode = IMPLEMENTATION,
  release = v0.1.9. Session A silently lost mutual exclusion during its own
  final gate; its next write gets `[SDD LOCK]`-blocked by the thief until the
  thief's TTL lapses (ping-pong).

**Repro:** with session A holding the lease and busy >120 s inside one long
Bash call (e.g. full pytest), have session B `Write` any file under
`repos/<ctx>/specs/bugs/`. The write is allowed AND the lock record now names
session B.

**Expected:** (1) additive writes never touch the lease; (2) a live session
never loses its lease; (3) a read-bound session never becomes an
IMPLEMENTATION lease holder.

**Root cause — three compounding defects:**

- **D1 — ADDITIVE classifier blind to in-repo specs.**
  `gate_policy.classify_path` matches `_ADDITIVE_PREFIXES` (`specs/bugs/`,
  `specs/backlog/`, `specs/audits/`, …) only against the **workspace-root**
  relative path. In any context repo — including the self-hosting workspace,
  where the law mandates bugs go to `repos/dadaia-workspace/specs/bugs/` —
  the path matches the `repos/` prefix first and classifies **MUTATING**.
  Consequences: an in-repo bug/backlog/audit write (a) acquires/steals the
  lease, and (b) would have been BLOCKED had the holder's heartbeat been
  fresh — directly violating "bug files are ADDITIVE (never gate-blocked)".
  The gate's own BLOCK message ("Additive writes ... are still allowed") is
  false for every in-repo specs path.

- **D2 — lease heartbeat starves while the holder is alive.**
  The lease record's `heartbeat` is renewed only when the holder performs a
  gate-visible Write/Edit (`gate_policy.evaluate` → `lease.acquire` same-
  holder renewal). The PostToolUse heartbeat hook (`hooks/sdd_post_gate.py`)
  renews a *different* artifact (`.dadaia/sessions/<id>.json:last_seen_at`)
  and is keyed by `DADAIA_SESSION_ID` — an env var hook subprocesses never
  receive (see D3), so it no-ops in harness sessions. Net: a holder inside
  one long Bash call (pytest final gate — the most common closure activity)
  emits no lease heartbeats; after `ttl=120 s` any other writer auto-
  TAKEOVERs (the 0.1.6 freeze-fix made `lease.acquire` never raise on a
  stale-foreign lease). The "heartbeat-vs-reclaim" race flagged in the
  2026-06-04 dev/test/review audit is now reproduced in production.

- **D3 — `context bind` mode/identity never reaches the gate.**
  `dadaia context bind` only prints `export DADAIA_CONTEXT/SESSION_ID/MODE`
  lines for shell eval. Harness hooks run in the harness process environment,
  and harness Bash calls are fresh shells — so the exports reach neither.
  `hooks/sdd_gate.py` then defaults `mode = os.environ.get("DADAIA_MODE",
  "IMPLEMENTATION")` and takes its session id from the hook payload. Result:
  a `--mode read` bind is theater; every writing session presents as an
  IMPLEMENTATION candidate, and the bind-issued `sess_*` id is a third
  identity unrelated to both the lock record and the heartbeat hook key.
  (Release id is read from the context's `ACTIVE.md`, so the thief's lock
  record even shows the victim's release.)

**Notes:**
- Distinct from (and adjacent to) `gate-cross-context-lock-contamination`:
  that one was fixed by PATH-first slug resolution in the Python gate; this
  incident is the next lock-correctness layer down.
- Fix directions: classify ADDITIVE on the **context-relative** path
  (`repos/<ctx>/specs/bugs/...` → ADDITIVE) so additive writes bypass
  `lease.acquire` entirely; renew the lease heartbeat from PostToolUse on
  *any* tool call by the holder (or use PID/process liveness via the existing
  `lock_liveness` seam) instead of write-only renewal; make TAKEOVER check a
  real liveness signal, not write-recency; honor a read-mode binding by
  refusing lease acquisition (gate should treat missing/READ mode as
  non-acquiring for MUTATING paths, blocking instead).
- Evidence (UTC): lock record before/after takeover captured in session
  transcripts; lock-events.jsonl HEARTBEAT/ACQUIRE entries around
  2026-06-10T00:02:36Z corroborate.
