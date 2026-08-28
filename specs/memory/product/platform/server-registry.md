---
slug: server-registry
title: server-registry
category: product
tldr: Port registry with TTL and PID tracking so parallel agents' dev servers never collide; the 3000-3999 range binds only `next_port`.
summary: An internal registry of dev-server ports with TTL and PID tracking, an expiry sweeper that distinguishes unprobable from dead PIDs, and a read-only scan against real OS listeners.
tags: [server, registry, ports, ttl]
---

## Behavior

- `dadaia server {list,next,register,release,show,clean,scan}` keeps a registry of ports per project so parallel dev servers do not collide and other sessions can discover a project's URL.
- The 3000-3999 range is enforced only by `next_port` allocation; `register()` accepts any explicit port.
- A sweeper expires entries whose TTL elapsed or whose PID is gone, distinguishing `ProcessLookupError` (dead, swept) from `PermissionError` (alive but unprobable, kept), so a root-owned PID survives.
- `dadaia server scan` is read-only: it parses `ss -tlnp` for the operator's uid, lists unregistered LISTEN ports enriched from `/proc/<pid>/`, and marks `lan_exposed` for `0.0.0.0` binds.
- With `ss` absent, scan returns an empty list plus a warning.
- A malformed record emits the warning `registry_entry_malformed` and is skipped rather than breaking `list_all()`.
- `dadaia panel` self-registers its port as `dadaia-panel` before serving and releases it on a clean stop.
- Runtime state is `.dadaia/states/server_registry.json`, an array of `PortEntry` with TTL and PID.
- `resolve_workspace_root(cwd)` requires `.dadaia/states/spec_contexts.json`, not merely `.dadaia/`, so a sub-repo with an agentic projection cannot confuse the walk-up.

## Dependencies

[[workspace-init]] creates the state directory; [[panel]]'s Servers tab reads it through `ServerRegistryService`. Stdlib only.
