---
slug: panel
title: panel
category: product
tldr: Local loopback-only six-tab workspace UI — Projects, Agents, Agentic Entities, Reports, Academy, Servers.
summary: "`dadaia panel` serves a loopback-only, no-auth, Host-guarded, CSP-constrained six-tab UI over local workspace state; the Agents tab is its only governance editor."
tags:
- panel
- ui
- http
- dashboard
---

## Boundary and tabs

The panel exposes local workspace state and governance without becoming a remote service: it binds
only to `127.0.0.1`, a Host allowlist rejects DNS-rebinding, and there is no token, cookie or
credential store. The stdlib HTTP server applies strict CSP, `nosniff`, loopback binding and Host
validation to reads and mutations alike; operator-controlled strings are escaped, mutating routes
validate payloads before atomic writes, and CSS/JS assets are served from packaged source with no
external CDN.

Six tabs: **Projects** (Spec Context Projects and their memory, each card listing the main repo and
any associated repos, [[context-management]]), **Agents** (persona cards, agent model
templates/overrides, and the Sessions telemetry dashboard), **Agentic Entities** (the
abstract-entity registry rendered server-side, [[agentic-entities]]), **Reports** (handoff/report
discovery and retention controls), **Academy** ([[academy]]) and **Servers** (registered dev servers
with TTL/PID status, [[server-registry]]).

The Agents tab is the panel's only governance editor: it renders the Layer-1 model templates and the
operator overlay, validates a submitted model/effort pair against the registry catalog, and writes
`.dadaia/states/agent_model_policy.json` atomically, never inventing a model outside the catalog.

## Runtime state

`.dadaia/states/agent_model_policy.json`, `.dadaia/states/server_registry.json`,
`.dadaia/reports/`, `.dadaia/handoff/`, and the telemetry database outside repositories.

## Dependencies

[[agent-orchestration]], [[agent-monitoring]], [[agentic-entities]], [[server-registry]],
[[brand-identity]].
