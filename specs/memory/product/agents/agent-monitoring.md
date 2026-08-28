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
---

## Telemetry

Local agent telemetry read only from the operator's own files — no remote API, no Node dependency.
`features/telemetry/` materializes SQLite at `~/.dadaia/state/telemetry/telemetry.sqlite` and serves
`/api/sessions`, `/api/agents`, `/api/agents/{id}/sessions` and `/api/agents/{id}/prompt` to the
[[panel]]. Runtimes are `claude`, `codex` and `kimi-code`, each with its own reader and aggregator
adapter; Kimi has no per-event pricing, so its cost is reported unknown rather than faked.

**Privacy by construction:** `reader/allowlist.py` is a hardcoded key allowlist every event passes
before reaching SQLite; no column and no endpoint carries message content. Routes carry no
credential, behind the panel's loopback bind and Host allowlist, and `os.getuid() == 0` refuses to
start the service. Reads are incremental and non-destructive, the SQLite file is chmod 600 inside a
0o700 directory, Kimi session content is never opened, and IO/parse failure degrades silently.

`dadaia panel` boots telemetry; a database failing `PRAGMA integrity_check` is renamed aside and the
endpoints answer 503. On a cache miss the service takes a file lock, runs the readers under a
per-cycle byte/line/event budget, filters through the allowlist gate, and inserts idempotently by
hashed event id. Each session's `cwd` resolves to a Spec Context at query time, with an "unassigned"
bucket for a cwd outside every context; sub-agent identity comes from the Claude `agent-name` event
plus `isSidechain`. The Sessions tab is dashboard-only and there is no Agents tab. No retention or
compaction exists: raw events accumulate, and the 180-day figure is the aggregation query's default
window.

## Artifact lifecycle

Runtime artifacts under `.dadaia/` die when the thing they exist for dies. Each capability is
fail-open where it rides a hook, and each resolves its target, refuses a resolved target outside
`.dadaia/`, and never follows a symlinked directory.

- **Release closure** sweeps that release's reports, handoffs, `tmp/<agent>/` captures and run
  records, after its evidence pointers are final and before the archive move. Anything a surviving
  pointer references is kept; another release's artifacts are never in scope.
- **The reconciler reaps what it walks:** session and presence records stale beyond 3× TTL go with
  their tmp markers, the directories they empty, and zombie run records; a live session is never
  touched. It runs in the PostToolUse pass behind a 30-second throttle, isolated so a reap failure
  cannot break the pass.
- **Each `.dadaia/logs/*.jsonl` writer rotates its own file** at a 1 MB cap, retaining current + 1
  generation, taking a lock only at or over the cap and appending without rotating on a contended
  timeout. No external cron.
- **A cache is refused, not deleted:** the venv guard blocks the invocation that would write one
  into a repo tree ([[sdd-gate-v3]]).

`dadaia tmp gc` is the only calendar-based backstop: dated scratch older than 3 days, any `*cache*`
directory under `.dadaia/` excluding the venv and session records, and orphaned session markers. It
takes no path argument, offers a dry run, is idempotent, never removes a live session's markers or a
non-dated path, and is safe at `SessionStart`.

## Dependencies

[[panel]], [[context-management]] (cwd→context lookup), [[brand-identity]] (cost/alert tokens).
