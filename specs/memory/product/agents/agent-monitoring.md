---
slug: agent-monitoring
title: agent-monitoring
category: product
tldr: Stdlib-only local agent telemetry behind an allowlist gate, plus the event-driven lifecycle of every runtime artifact under .dadaia/.
summary: Telemetry ingests Claude Code, Codex and Kimi Code session metadata into a local SQLite store behind an allowlist gate; the same atom owns artifact GC, reconciler reaping and log rotation.
tags: [monitoring, telemetry, sessions, lifecycle]
---

## Telemetry

- Local agent telemetry reads only the operator's own files — no remote API, no Node dependency.
- `features/telemetry/store.py`'s `TelemetryStore` owns the SQLite file at `~/.dadaia/state/telemetry/telemetry.sqlite` — open, migrate, `integrity_check`, `quarantine` — and no caller reaches a connection past it.
- `TelemetryService(store, readers, clock)` exposes refresh and the session/agent aggregations the panel's sessions, agents and agent-prompt routes read ([[panel]]).
- Runtimes are `claude`, `codex` and `kimi-code`, each with its own reader and aggregator; Kimi has no per-event pricing, so its cost is reported unknown, never faked.
- `reader/allowlist.py` is a hardcoded key allowlist every event passes before reaching SQLite; no column and no endpoint carries message content.
- Routes carry no credential, sit behind the panel's loopback bind and Host allowlist, and `os.getuid() == 0` refuses to start the service.
- Reads are incremental, the SQLite file is chmod 600 inside a 0o700 directory, and IO or parse failure degrades silently.
- A database failing `PRAGMA integrity_check` is quarantined beside itself with its sidecars and the endpoints answer 503.
- On a cache miss the service runs the readers under a per-cycle budget behind a file lock and inserts idempotently by hashed event id.
- A session's `cwd` resolves to a Spec Context at query time, with an unassigned bucket outside every context; sub-agent identity comes from the Claude `agent-name` event plus `isSidechain`.
- No retention or compaction exists; the 180-day figure is the aggregation query's default window.

## Artifact lifecycle

- Runtime artifacts under `.dadaia/` die when the thing they exist for dies; each capability is fail-open where it rides a hook, refuses a target outside `.dadaia/`, and never follows a symlinked directory.
- Release closure sweeps that release's reports, handoffs, captures and run records after its evidence pointers are final and before the archive move, keeping whatever a surviving pointer references.
- `presence.gc()` is the one reaper of presence records, throttle and sentinel markers and the directories they empty; a live session's own record is never touched, and it runs from `doctor --fix` and the PostToolUse pass behind one throttle ([[context-management]]).
- Each `.dadaia/logs/*.jsonl` writer rotates its own file at a 1 MB cap, keeping current + 1 generation, locking only at or over the cap and appending without rotating on a contended timeout.
- A cache is refused, not deleted: the venv guard blocks the invocation that would write one into a repo tree ([[sdd-gate-v3]]).
- `dadaia tmp gc` is the only calendar-based backstop, covering dated scratch older than 3 days, `*cache*` directories under `.dadaia/` outside the venv, and orphaned session markers.
- It offers a dry run, is idempotent, never removes a live session's markers or a non-dated path, and is safe at `SessionStart`.

## Dependencies

[[panel]], [[context-management]], [[brand-identity]].
