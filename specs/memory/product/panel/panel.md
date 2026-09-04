---
slug: panel
title: panel
category: product
tldr: Local loopback-only four-tab workspace UI — Projects, Agents, Agentic Entities, Servers.
summary: The panel serves a loopback-only, no-auth, Host-guarded, CSP-constrained four-tab UI over local workspace state; the Agents tab is its only governance editor.
tags: [panel, ui, http, dashboard]
---

## Boundary and tabs

- The server binds only to `127.0.0.1`, a Host allowlist rejects DNS-rebinding, and no token, cookie or credential store exists.
- The stdlib HTTP server applies strict CSP and `nosniff` to reads and mutations alike.
- One `(method, pattern, view_name, params)` table in `features/panel/handler.py` dispatches every route; a route absent from it cannot exist, and there is no silent-public fallback.
- Each view lives in its own module, receives the panel service from the container and imports nothing but that service and `core.models`; telemetry reaches them only through `TelemetryStore`'s service ([[agent-monitoring]]).
- Operator-controlled strings are escaped, mutating routes validate payloads before atomic writes, and assets are served from packaged source with no CDN.
- The four tabs are Projects (contexts and their memory, each card listing main and associated repos, [[context-management]]), Agents (persona cards, model templates and overrides, plus the Sessions telemetry dashboard), Agentic Entities (the registry rendered server-side, [[agentic-entities]]) and Servers ([[server-registry]]).
- The Agents tab is the only governance editor: it validates a submitted model/effort pair against the registry catalog and writes `.dadaia/states/agent_model_policy.json` atomically, never inventing a model outside the catalog.

## Runtime state

`.dadaia/states/agent_model_policy.json`, `.dadaia/states/server_registry.json` and the telemetry database outside repositories.

## Dependencies

[[agent-orchestration]], [[agent-monitoring]], [[agentic-entities]], [[server-registry]], [[brand-identity]].
