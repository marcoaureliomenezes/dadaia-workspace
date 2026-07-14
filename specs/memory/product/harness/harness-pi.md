---
slug: harness-pi
title: Harness - PI (pi-coding-agent)
category: product
tldr: Dual-layer PI runtime with a trusted TypeScript entry extension and a governed headless worker supporting Codex-subscription and explicit OpenRouter profiles.
summary: >-
  PI can enter the workspace interactively after explicit trust and can execute bounded
  Layer-2 workflow steps through `pi --mode json`. GPT profiles use provider-qualified
  Codex-subscription ids; optional OpenRouter profiles remain explicit.
tags:
- harness
- pi
- layer-1
- layer-2
- projection
token_estimate: 348
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

PI is both a Layer-1 entry harness and a Layer-2 workflow worker. It is an operator-
installed external CLI, not a Python package dependency.

## Layer 1

`.pi/` is a generated projection. PI loads its TypeScript SDD gate extension only after
the operator trusts the workspace. The extension maps PI tool events to the same Python
gate policies and sets `DADAIA_ENTRY_HARNESS=pi` so `--harness auto` can prefer PI.
Generated `.pi/**` files contain no secrets and must not be hand-edited.

## Layer 2

`PiHeadlessAdapter` invokes `pi --mode json` with the exact governed model id and
`--thinking` effort. It parses the event stream, validates `agent-run-result-v1`, retains
redacted diagnostics for malformed/non-zero attempts, and returns artifact references to
the lifecycle engine.

The built-in PI catalog includes:

- `openai-codex/gpt-5.5` at high, medium, and low reasoning;
- `moonshotai/kimi-k2.5` at high reasoning through the explicit OpenRouter profile.

Provider qualification is mandatory. A Codex-subscription profile cannot resolve to
OpenRouter, and an OpenRouter profile cannot masquerade as subscription-backed. OAuth
and API-key storage are operator/runtime concerns outside generated workspace assets;
the workspace never copies credential material.

## Workflow Use

All four dadaia-workflows accept PI globally or per step. The workflow policy freezes the
selected profile for each run. PI receives fragment plus persona, scoped context, allowed
paths, exact dependencies, and a required output schema just like Codex.

## Telemetry

The PI telemetry reader ingests allowlisted metadata from PI session records. It does
not ingest prompt or response bodies and does not fabricate pricing for models without a
known pricing row.

## Dependencies

[[dadaia-workflows]], [[lifecycle-foundation]], [[multi-platform-parity]],
[[agent-monitoring]], [[sdd-gate-v3]].
