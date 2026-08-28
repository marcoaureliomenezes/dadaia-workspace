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

## Purpose

The panel exposes local workspace state and governance without becoming a remote service.
It binds only to `127.0.0.1`, a Host allowlist rejects DNS-rebinding, and there is no
token, cookie or credential store.

## Tabs

| Tab | Content |
|---|---|
| Projects | Spec Context Projects and their memory; each card lists the main repo and any associated repos ([[context-management]]) |
| Agents | Persona cards, agent model templates/overrides, and the Sessions telemetry dashboard |
| Agentic Entities | the abstract-entity registry rendered server-side ([[agentic-entities]]) |
| Reports | handoff/report discovery and retention controls |
| Academy | packaged knowledge-base content ([[academy]]) |
| Servers | registered dev servers with TTL/PID status ([[server-registry]]) |

## Model governance surface

The Agents tab is the panel's only governance editor: it renders the Layer-1 model
templates and the operator overlay, validates a submitted model/effort pair against the
registry catalog, and writes `.dadaia/states/agent_model_policy.json` atomically. It
never invents a model outside the catalog.

## HTTP boundary

The stdlib HTTP server applies strict CSP, `nosniff`, loopback binding and Host
validation to reads and mutations alike. Operator-controlled strings are escaped,
mutating routes validate payloads before atomic writes, and CSS/JS assets are served from
packaged source with no external CDN.

## Runtime state

`.dadaia/states/agent_model_policy.json`, `.dadaia/states/server_registry.json`,
`.dadaia/reports/`, `.dadaia/handoff/`, and the telemetry database outside repositories.

## Dependencies

[[agent-orchestration]], [[agent-monitoring]], [[agentic-entities]], [[server-registry]],
[[brand-identity]].
