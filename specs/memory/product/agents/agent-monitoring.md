---
slug: agent-monitoring
title: agent-monitoring
category: product
tldr: Stdlib-only local agent telemetry behind an allowlist gate, plus the event-driven lifecycle of every runtime artifact under .dadaia/.
summary: '`features/telemetry/` ingests Claude Code, Codex and Kimi Code session metadata into a local SQLite store behind a hardcoded allowlist gate and serves the panel dashboard; the same atom owns artifact GC, reconciler reaping and write-time log rotation under `.dadaia/`.'
tags:
- monitoring
- telemetry
- sessions
- lifecycle
last_updated: '2026-08-28'
release_origin: 0.5.0
---

## Purpose

Local agent telemetry read only from the operator's own files — no remote API, no Node
dependency. `features/telemetry/` materializes SQLite at
`~/.dadaia/state/telemetry/telemetry.sqlite` (WAL, foreign keys, `PRAGMA user_version`,
one pragmatized factory `store/schema.open_connection`) and serves `/api/sessions`,
`/api/agents`, `/api/agents/{id}/sessions` and `/api/agents/{id}/prompt` to the [[panel]].

Runtimes are `claude`, `codex`, `kimi-code`, each with a reader (`reader/claude.py`,
`reader/codex.py`, `reader/kimi.py`) and an adapter in `aggregator/runtimes.py`. Kimi has
no per-event pricing, so its cost is reported unknown rather than faked.

**Privacy by construction:** `reader/allowlist.py` is a hardcoded key allowlist every event
passes before reaching SQLite; no column and no endpoint carries message content. Routes
carry no credential, behind the panel's loopback bind and Host allowlist. `os.getuid() == 0`
refuses to start the service.

## Usage flow

1. `dadaia panel` boots telemetry; a database failing `PRAGMA integrity_check` is renamed
   aside and the endpoints answer 503.
2. On a cache miss the service takes the `telemetry.lock` file lock, runs the readers under
   a per-cycle byte/line/event budget, filters through the allowlist gate, and inserts
   idempotently by hashed event id.
3. Each session's `cwd` resolves to a Spec Context at query time via
   `SpecContextService.list_all()`, with an "unassigned" bucket for a cwd outside every
   context.
4. Sub-agent identity comes from the Claude `agent-name` event plus `isSidechain`, so
   sub-agents aggregate separately.

The Sessions tab is dashboard-only: aggregate cards, no per-session list or detail view.
There is no Agents tab; `/api/agents` has no dedicated UI consumer. Session ids render
truncated.

## Runtime state touched

- Read: `~/.claude/projects/*/*.jsonl` (incremental tail, byte-offset checkpoint, inode
  rotation detection), `~/.codex/state_5.sqlite` (read-only URI, env-overridable),
  `~/.kimi-code/session_index.jsonl` (index metadata only; session content is never opened
  and IO/parse failure degrades silently).
- Read+write: the SQLite file (chmod 600, dir 0o700) with tables `reader_state`,
  `sessions`, `agents`, `events`; and `telemetry.lock`, a `flock` guard against concurrent
  refresh.
- No retention or compaction exists — raw events accumulate. The 180-day figure is the
  aggregation query's default window, exposed as the `days` parameter.
- Stdlib only: `sqlite3`, `fcntl`, `subprocess`, `pathlib`, `json`, `dataclasses`,
  `datetime`, `re`.

## Lifecycle

Runtime artifacts under `.dadaia/` die when the thing they exist for dies. Each capability
is fail-open where it rides a hook, and each resolves its target, refuses a resolved target
outside `.dadaia/`, and never follows a symlinked directory.

- **Release closure** sweeps that release's reports, handoffs, `tmp/<agent>/` captures and
  run records, after its evidence pointers are final and before the archive move. Anything
  a surviving pointer references is kept; another release's artifacts are never in scope.
- **The reconciler reaps what it walks:** session and presence records stale beyond 3× TTL
  go with their tmp markers, the directories they empty, and zombie run records. A live
  session is never touched. It runs in the PostToolUse pass behind the reconciler's
  30-second throttle, isolated so a reap failure cannot break the pass.
- **Each `.dadaia/logs/*.jsonl` writer rotates its own file** through
  `infrastructure/jsonl_log_rotation.py`: at a 1 MB cap it rotates and retains current + 1
  generation. Size is re-checked under a lock before the replace; the lock is taken only at
  or over the cap, and a contended timeout appends without rotating. No external cron.
- **A cache is refused, not deleted:** the venv guard blocks the invocation that would write
  one into a repo tree ([[sdd-gate-v3]]).

`dadaia tmp gc` is the only calendar-based backstop: dated scratch older than 3 days, any
`*cache*` directory under `.dadaia/` excluding the venv and session records, and orphaned
session markers. It takes no path argument, offers a dry run, is idempotent, never removes
a live session's markers or a non-dated path, and is safe at `SessionStart`.

## Dependencies

[[panel]] (injects the service, renders the dashboard), [[context-management]] (cwd→context
lookup), [[brand-identity]] (cost/warning/alert tokens).
