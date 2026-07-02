---
name: panel-telemetry-sqlite-corrupts-under-concurrent-access
status: Open
severity: MEDIUM
reported: 2026-07-01
surface: dadaia panel — telemetry SQLite store (/api/agents, /api/agents/<id>/sessions)
session_id: null
---

**Symptom:** During a long-running panel Playwright suite run against a panel dev-server
that had been up for a while, the telemetry SQLite database corrupted. The panel detected
the corruption, quarantined the file to `telemetry.sqlite.corrupt.<UTC>`, and thereafter
served every telemetry-backed route with:

```
HTTP 503
{"error": "telemetry_degraded",
 "message": "Telemetry database is corrupt and has been quarantined.
             Restart the panel after investigating .../telemetry.sqlite.corrupt.*"}
```

`/api/agents`, `/api/agents/<id>/sessions`, and the agents sub-section of the Agentic tab
returned 503 until the panel was restarted. Non-telemetry routes (`/api/workflows`,
`/api/personas`, `/`) stayed healthy. The 503 + quarantine + "restart" message is the
**designed** graceful degradation and is correct; the underlying corruption is the bug.

**Repro:** Not deterministically reproduced. Observed once when a panel dev-server that had
served traffic for an extended period was hit by the full panel Playwright suite (~3.6 min,
serial worker) while another local process was also reading/writing the same
`~/.dadaia/state/telemetry/telemetry.sqlite`. The quarantined DB was ~21 MB (real data).
A freshly-started panel on a separate port created a clean telemetry DB and the full
69-test Playwright suite passed 69/69, confirming the failures were entirely downstream of
the corrupt DB, not the panel markup.

**Expected:** The telemetry SQLite store should not corrupt under concurrent read/write
access from more than one process. If concurrent access is a supported mode, the store
should open in WAL mode with a busy-timeout so overlapping readers/writers serialise
rather than corrupt; if it is single-writer-only by contract, that constraint should be
enforced/documented and the reader path should open read-only.

**Notes:**
- The graceful-degradation path (quarantine + 503 + restart hint) works as designed — this
  bug is about preventing the corruption, not about the degradation response.
- Aligns with the known concurrency gotcha (concurrent panel + local session activity on
  shared workspace SQLite state). A `BrokenPipeError` on client disconnect during a
  telemetry response was also observed in the fresh-panel run at test teardown — harmless
  (client closed the page mid-response) but worth handling quietly rather than logging a
  full traceback.
- Suggested investigation: confirm the telemetry store's SQLite `journal_mode`
  (WAL vs default rollback), `busy_timeout`, and whether the reader opens the same file the
  writer holds open across processes.
