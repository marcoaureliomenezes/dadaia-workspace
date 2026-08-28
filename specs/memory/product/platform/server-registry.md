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

## Behavior

`dadaia server {list,next,register,release,show,clean,scan}` keeps a registry of ports associated
with projects so parallel dev servers do not collide and other sessions can discover a project's
active URL. The 3000-3999 range is enforced **only** by `next_port` allocation; `register()` accepts
any explicit port.

A sweeper expires entries whose TTL elapsed or whose PID is gone, distinguishing
`ProcessLookupError` ("dead", swept) from `PermissionError` ("alive but unprobable", kept), so a
root-owned PID such as `docker-proxy` survives. `dadaia server scan` is read-only: it parses
`ss -tlnp` filtered by the operator's uid, lists LISTEN ports with no registry entry, enriches them
from `/proc/<pid>/`, and marks `lan_exposed` for `0.0.0.0` binds; with `ss` absent it returns an
empty list plus a warning, and the operator promotes an orphan with `dadaia server register`.
Loading is resilient per entry: a malformed record emits the structured warning
`registry_entry_malformed` and is skipped rather than breaking `list_all()`. `dadaia panel` obeys
the same law, self-registering its port as `dadaia-panel` before serving and releasing on a clean
stop.

Runtime state is `.dadaia/states/server_registry.json`, an array of `PortEntry` with TTL and PID,
plus read-only `ss -tlnp` and `/proc/<pid>/` probes. `resolve_workspace_root(cwd)` requires
`.dadaia/states/spec_contexts.json`, not merely `.dadaia/`, so a sub-repo carrying an agentic
projection cannot confuse the walk-up.

## Dependencies

[[workspace-init]] creates the state directory; [[panel]]'s Servers tab reads it through
`ServerRegistryService` and `PanelService`. Stdlib only.
