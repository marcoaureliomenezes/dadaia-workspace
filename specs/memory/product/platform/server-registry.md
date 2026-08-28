---
slug: server-registry
title: server-registry
category: product
tldr: Port registry with TTL and PID tracking so parallel agents' dev servers never collide; the 3000-3999 range binds only `next_port`.
summary: An internal registry of dev-server ports with TTL and PID tracking, an expiry sweeper that distinguishes unprobable from dead PIDs, and a read-only `scan` that reconciles it against real OS listeners.
tags:
- server
- registry
- ports
- ttl
---

## Purpose

`dadaia server {list,next,register,release,show,clean,scan}` keeps a registry of ports
associated with projects so dev servers spawned in parallel by different agents do not
collide, and so other sessions can discover a project's active URL without hardcoding it.
The 3000-3999 range is enforced **only** by `next_port` allocation (`min_port`/`max_port`
defaults); `register()` accepts any explicit port.

## Behavior

- A sweeper expires entries whose TTL elapsed or whose PID is gone. It distinguishes
  `ProcessLookupError` ("dead", swept) from `PermissionError` ("alive but unprobable",
  kept), so a root-owned PID such as `docker-proxy` survives.
- `dadaia server scan` is read-only: it parses `ss -tlnp` filtered by the operator's uid,
  lists LISTEN ports with no registry entry, enriches them from `/proc/<pid>/cmdline` and
  `/proc/<pid>/cwd`, and marks `lan_exposed` for `0.0.0.0` binds. The operator promotes an
  orphan with `dadaia server register --port <p> --project <name> --pid <pid>`. With `ss`
  absent it returns an empty list plus a warning.
- Loading is resilient per entry: a `JSONDecodeError`, `KeyError`, `TypeError` or
  `ValueError` emits the structured warning `registry_entry_malformed` and skips that
  entry rather than breaking `list_all()`.
- `dadaia panel` obeys the same law: it self-registers its port as `dadaia-panel` before
  serving and releases the entry on a clean stop.

## Runtime state touched

- Read+write `.dadaia/states/server_registry.json` — an array of `PortEntry` with TTL and
  PID.
- Read `ss -tlnp` via subprocess (ports below 1024 skipped), plus `/proc/<pid>/`.
- `resolve_workspace_root(cwd)` in `core/workspace_resolver.py` requires
  `.dadaia/states/spec_contexts.json`, not merely `.dadaia/`, so a sub-repo carrying an
  agentic projection cannot confuse the walk-up.

## Dependencies

[[workspace-init]] creates the state directory; [[panel]]'s Servers tab reads `list_all()`
through `ServerRegistryService` and `list_unregistered_listeners()` through `PanelService`
(`GET /api/panel-status`). Stdlib only.
