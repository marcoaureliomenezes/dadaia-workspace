---
slug: server-registry
title: server-registry
tldr: Dev-server port registry with TTL and PID tracking so parallel sessions never collide — one stdlib skill script over one JSON state file; no CLI verb.
summary: python3 .agents/skills/dd-cli-library/scripts/registry.py keeps .dadaia/states/server_registry.json — per-project ports with TTL and PID, deterministic next-port allocation, idempotent register, release, stale sweep and a read-only scan of unregistered OS listeners.
tags: [server, registry, ports, ttl]
sources:
  - dadaia_workspace/public/skills/dd-cli-library/scripts/registry.py
---

## Behavior

- Every verb is `python3 .agents/skills/dd-cli-library/scripts/registry.py <verb>`: `list`, `next`, `register`, `release`, `clean`, `scan`; exit 0 on success, 1 on a refused verb. The source is `dadaia_workspace/public/skills/dd-cli-library/scripts/registry.py`, stdlib only.
- `list [--project <name>] [--status active|stale|all] [--json]` shows entries, active by default.
- `next --project <name> [--min-port N] [--max-port N] [--json]` returns the project's live port if it holds one, else a base port hashed from the project name in 3000-3999, else the first free port; a full range exits 1 naming `clean`.
- `register --port N --project <name> [--url] [--pid] [--ttl <hours, default 8>] [--description]` drops stale entries first, is idempotent for the same project, and exits 1 naming the owner when another project holds the port; any explicit port is accepted.
- `release --port N` and/or `--project <name>` removes matching entries; a port owned by another project exits 1.
- `clean [--dry-run]` removes entries whose TTL elapsed or whose PID is gone; on a non-POSIX host only the TTL is judged.
- `scan [--json]` is read-only: it parses `ss -tlnp`, lists LISTEN ports above 1024 that no entry covers, enriched with the process command line and cwd, and marks `lan_exposed` for wildcard binds; without `/proc` or `ss` it returns an empty list.

## Runtime state

`.dadaia/states/server_registry.json` — `{"version", "range", "entries": [{port, project, url, status, pid, reserved_at, expires_at, description}]}`, seeded by [[workspace-init]]; the script finds it by walking up from the cwd to the nearest `.dadaia/`, and `--registry <path>` overrides.

## Dependencies

[[workspace-init]], [[agentic-entities]].
