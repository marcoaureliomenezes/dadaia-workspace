---
slug: panel
title: panel
category: product
tldr: Local seven-tab panel with workflow governance, telemetry, reports, and wall-wrapping Snake/Tetris plus Codex Pong and PI Breakout.
summary: >-
  `dadaia panel` serves the local workspace UI. Its seven tabs are Projects, 1st
  Agentic Layer, 2nd Agentic Layer, Reports, Academy, Servers, and Games. The Games
  tab includes wall-wrapping Snake plus Tetris, Codex Pong, and PI Breakout. It is loopback-only, no-auth,
  Host-guarded, and CSP-constrained.
tags:
- panel
- ui
- http
- dashboard
- games
token_estimate: 481
last_updated: '2026-07-14'
release_origin: v0.2.7
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
7. **Games** - playable Snake (Codex), Tetris (PI), Pong (Codex), and Breakout (PI).

## Workflow Surface

The workflow catalog is server-rendered from the governed lifecycle catalog. Each card
shows purpose, availability, steps, roles, gates, harnesses, profiles, and an offline SVG
DAG. The catalog contains only `backlog_definition`, `release_definition`,
`implementation_reviews`, and `audit`. The policy editor persists profile ids, validates
harness/profile compatibility, and never invents a raw model outside the catalog.

## Games

Games use isolated canvas state and local JavaScript only. Snake runs on a 20x20 board,
wraps across all four walls to the opposite edge, keeps self-collision on the reset path,
and supports keyboard and direction-pad input. Tetris supports keyboard and touch/button
move, rotate, down, and drop controls. Pong uses a Codex panel with `#pong-canvas`,
`#pong-score`, `data-action="pong-toggle"`, `data-action="pong-reset"`, and up/down input
controls via both keyboard (`ArrowUp`/`ArrowDown`) and `data-pong-dir` buttons. Breakout adds a PI
panel with `#breakout-canvas`, `#breakout-score`, `data-action="breakout-toggle"`,
`data-action="breakout-reset"`, `data-breakout-dir="left"`, and `data-breakout-dir="right"` controls.
All games expose score, pause/start, and reset semantics. Stable canvas dimensions and responsive
constraints prevent layout shifts. Browser validation covers nonblank pixels, state changes
after input, desktop/mobile geometry, horizontal overflow, and game-switch visibility.

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

[[agent-orchestration]], [[agent-monitoring]],
[[server-registry]], [[brand-identity]].
