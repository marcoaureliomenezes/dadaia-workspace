---
slug: panel
title: panel
category: product
tldr: Loopback-only local control surface with seven tabs, four workflow diagrams/policies, agent governance, telemetry, reports, and playable Snake/Tetris.
summary: >-
  `dadaia panel` serves the local workspace UI. Its seven tabs are Projects, 1st
  Agentic Layer, 2nd Agentic Layer, Reports, Academy, Servers, and Games. It is
  loopback-only, no-auth, Host-guarded, and CSP-constrained.
tags:
- panel
- ui
- http
- dashboard
- games
token_estimate: 394
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

The panel exposes local workspace state and governance without becoming a remote
service. It binds only to `127.0.0.1`; the Host allowlist rejects DNS-rebinding attempts.
There is no panel token, cookie, or credential store.

## Tabs

1. **Projects** - active Spec Context Projects and current memory.
2. **1st Agentic Layer** - Layer-1 agent model templates/overrides plus the aggregate
   Sessions telemetry dashboard.
3. **2nd Agentic Layer** - exactly four workflow diagram cards and per-step
   harness/profile policy controls.
4. **Reports** - handoff/report discovery and retention controls.
5. **Academy** - packaged knowledge-base content.
6. **Servers** - registered development servers and TTL/PID status.
7. **Games** - playable Snake (Codex) and Tetris (PI).

## Workflow Surface

The workflow catalog is server-rendered from the governed lifecycle catalog. Each card
shows purpose, availability, steps, roles, gates, harnesses, profiles, and an offline SVG
DAG. The catalog contains only `backlog_definition`, `release_definition`,
`implementation_reviews`, and `audit`. The policy editor persists profile ids, validates
harness/profile compatibility, and never invents a raw model outside the catalog.

## Games

Games use isolated canvas state and local JavaScript only. Snake supports keyboard and
direction-pad input; Tetris supports keyboard and touch/button move, rotate, down, and
drop controls. Both expose score, pause/start, and reset. Stable canvas dimensions and
responsive constraints prevent layout shifts. Browser validation covers nonblank pixels,
state changes after input, desktop/mobile geometry, and horizontal overflow.

## HTTP Boundary

The stdlib HTTP server uses strict CSP, `nosniff`, loopback binding, and Host validation
for reads and mutations. Operator-controlled strings are escaped. Mutating policy routes
validate payloads before atomic writes. Static CSS/JS assets are served from packaged
source; no external CDN is required.

## Runtime State

- `.dadaia/states/agent_model_policy.json`
- `.dadaia/states/workflow_model_policy.json`
- `.dadaia/states/server_registry.json`
- `.dadaia/reports/` and `.dadaia/handoff/`
- operator telemetry database outside repositories

## Dependencies

[[dadaia-workflows]], [[agent-orchestration]], [[agent-monitoring]],
[[server-registry]], [[brand-identity]].
