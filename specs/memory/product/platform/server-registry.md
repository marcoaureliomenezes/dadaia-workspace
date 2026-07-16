---
slug: server-registry
title: server-registry
category: product
tldr: internal port registry with TTL+PID to avoid conflicts between parallel agents'
  dev servers; the 3000-3999 range applies only to next_port allocation.
summary: internal port registry with TTL+PID to avoid conflicts between parallel agents'
  dev servers. The 3000-3999 range is enforced only by next_port allocation;
  register() accepts any port.
tags:
- server
- registry
- ports
- ttl
token_estimate: 750
last_updated: '2026-07-16'
release_origin: v0.1.61
---

CLI surface: `dadaia server {list,next,register,release,show,clean,scan}` · Closure: v0.1.1 (hotfix)

## Purpose

Internal registry of ports associated with projects, with TTL and PID tracking. The 3000-3999 range is enforced **only** by `next_port` allocation (defaults `min_port`/`max_port`); `register()` accepts any explicit port (e.g. a panel on 4999 or a dev server outside the range). It prevents port conflicts between dev servers spawned in parallel by different agents and lets other sessions discover a project's active URL without hardcoding.

An automatic sweeper expires entries whose TTL has elapsed or whose PID is no longer alive (resilient to malformed entries via skip-and-log) — it preserves root-owned PIDs (e.g. docker-proxy) by differentiating `PermissionError` ("alive but unprobable") from `ProcessLookupError` ("dead").

The `dadaia server scan` subcommand reconciles the registry with the OS's real listeners: it parses `ss -tlnp` filtered by the operator's uid, lists ports in LISTEN without a corresponding registry entry, and marks `lan_exposed` for `0.0.0.0` binds.

## Usage flow

  1. An agent or script spawns a dev server and registers the port: `register(port=3001, project="web-app", pid=os.getpid(), ttl_hours=8)`.
  2. Other sessions query: `get(port=3001)` → `PortEntry(url="http://localhost:3001", project, pid, expires_at)`.
  3. Before spawning on a new port: `next_port()` returns the next free port in the 3000-3999 range (the only point where the range is enforced).
  4. The sweeper runs periodically, removing entries with a dead PID (ProcessLookupError) or expired TTL; unprobable PIDs (PermissionError, e.g. root) remain active.
  5. **Manual reconciliation**: `dadaia server scan` (read-only) lists orphans — unregistered listeners — with port/bind/pid/cmdline/cwd/lan_exposed. The operator calls `dadaia server register --port <p> --project <name> --pid <pid>` to move an orphan → registry.



## Typical trigger

When agents or scripts spawn local dev servers and need to coordinate to avoid port collisions. `dadaia server scan` is invoked when the operator suspects a ghost listener (a port consumed but absent from `list` + panel).

## Differentiator

Without the registry, parallel agents would overwrite each other's ports — a non-deterministic, hard-to-diagnose bug. TTL + PID tracking avoids slot leaks when processes die unexpectedly; correct `PermissionError` semantics prevent root-owned PIDs (docker-proxy) from being auto-swept; store resilience (per-entry skip-and-log) prevents a single malformed JSON entry from breaking the whole `list_all()`; `scan` provides observability over listeners left outside the registry (push-only was invisible, now reconcilable).

## Runtime state touched

  * The panel itself obeys this law: `dadaia panel` self-registers its port as
    `dadaia-panel` before serving and releases the entry on a clean stop
    (`cli/commands/panel.py`).

  * **Read+Write**: `.dadaia/states/server_registry.json` — array of PortEntry with TTL+PID. Resilient load: `JSONDecodeError` or per-entry `KeyError/TypeError/ValueError` emit the structured warning `registry_entry_malformed` + skip; never raise.
  * **Read**: `ss -tlnp` via subprocess (filtered by the current user's uid; ports <1024 skipped); `/proc/<pid>/cmdline` and `/proc/<pid>/cwd` to enrich orphans. If `ss` is absent: returns an empty list + warning.
  * **Resolver**: `resolve_workspace_root(cwd)` in `core/workspace_resolver.py` requires `.dadaia/states/spec_contexts.json` (not just `.dadaia/`), preventing sub-repos with an agentic projection from confusing the walk-up.



## Dependencies

  * Standalone — depends on no other features beyond the structure created by [[workspace-init]].
  * Consumed by [[panel]]: the Servers tab reads `list_all()` via `ServerRegistryService` and `list_unregistered_listeners()` via `PanelService` (route `GET /api/panel-status`).
  * Stdlib only: `subprocess` for `ss`, `pathlib`, `json`, `dataclasses`.
