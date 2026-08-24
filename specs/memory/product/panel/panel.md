---
slug: panel
title: panel
category: product
tldr: Local six-tab panel with agent model governance, agentic entities, telemetry, reports, academy, and servers.
summary: >-
  `dadaia panel` serves the local workspace UI. Its six tabs are Projects,
  Agents, Agentic Entities, Reports, Academy, and Servers. It is loopback-only,
  no-auth, Host-guarded, and CSP-constrained.
tags:
- panel
- ui
- http
- dashboard
last_updated: '2026-08-24'
release_origin: v0.3.0
---

## Purpose

The panel exposes local workspace state and governance without becoming a remote
service. It binds only to `127.0.0.1`; the Host allowlist rejects DNS-rebinding attempts.
There is no panel token, cookie, or credential store.

## Tabs

1. **Projects** - active Spec Context Projects and current memory. A context card lists
   its main repository and, when it has any, its associated repositories; a context with
   none renders exactly as it always did, and the JSON contract carries the same list
   ([[context-management]]).
2. **Agents** - Persona definition cards, agent model templates/overrides, plus
   the aggregate Sessions telemetry dashboard.
3. **Agentic Entities** - the abstract-entity registry rendered server-side:
   universal Skills/AGENTS.md, Deterministic Actions, and Rules with their
   per-harness derivations ([[agentic-entities]]).
4. **Reports** - handoff/report discovery and retention controls.
5. **Academy** - packaged knowledge-base content.
6. **Servers** - registered development servers and TTL/PID status.

## Model Governance Surface

The Agents tab is the panel's only governance editor. It renders the
Layer-1 agent model templates and the operator overlay, validates a submitted
model/effort pair against the registry, and writes
`.dadaia/states/agent_model_policy.json` atomically. It never invents a model outside
the registry catalog.

## HTTP Boundary

The stdlib HTTP server uses strict CSP, `nosniff`, loopback binding, and Host validation
for reads and mutations. Operator-controlled strings are escaped. Mutating policy routes
validate payloads before atomic writes. Static CSS/JS assets are served from packaged
source; no external CDN is required.

## Runtime State

- `.dadaia/states/agent_model_policy.json`
- `.dadaia/states/server_registry.json`
- `.dadaia/reports/` and `.dadaia/handoff/`
- operator telemetry database outside repositories

## Dependencies

[[agent-orchestration]], [[agent-monitoring]], [[agentic-entities]], [[server-registry]], [[brand-identity]].
