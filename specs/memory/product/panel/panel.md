---
slug: panel
title: panel
category: product
tldr: Local five-tab panel with agent model governance, telemetry, reports, academy, and servers.
summary: >-
  `dadaia panel` serves the local workspace UI. Its five tabs are Projects,
  Agents, Reports, Academy, and Servers. It is loopback-only, no-auth,
  Host-guarded, and CSP-constrained.
tags:
- panel
- ui
- http
- dashboard
token_estimate: 430
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Purpose

The panel exposes local workspace state and governance without becoming a remote
service. It binds only to `127.0.0.1`; the Host allowlist rejects DNS-rebinding attempts.
There is no panel token, cookie, or credential store.

## Tabs

1. **Projects** - active Spec Context Projects and current memory.
2. **Agents** - agent model templates/overrides plus the aggregate
   Sessions telemetry dashboard.
3. **Reports** - handoff/report discovery and retention controls.
4. **Academy** - packaged knowledge-base content.
5. **Servers** - registered development servers and TTL/PID status.

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

[[agent-orchestration]], [[agent-monitoring]], [[server-registry]], [[brand-identity]].
