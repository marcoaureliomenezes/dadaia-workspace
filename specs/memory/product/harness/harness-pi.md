---
slug: harness-pi
title: Harness - PI (pi-coding-agent)
category: product
tldr: Entry harness with a trusted TypeScript gate extension projected into .pi/, plus allowlisted PI session telemetry.
summary: >-
  PI enters the workspace interactively after the operator explicitly trusts it. The
  `.pi/` projection carries prompts and the TypeScript SDD gate extension that maps PI
  tool events onto the same Python gate policies. PI session metadata feeds the panel's
  telemetry surface.
tags:
- harness
- pi
- projection
- telemetry
token_estimate: 300
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Purpose

PI is an entry harness. It is an operator-installed external CLI, not a Python package
dependency.

## Projection And Enforcement

`.pi/` is a generated projection carrying the staged `prompts/` and `extensions/` trees
plus the projected law file. PI loads its TypeScript SDD gate extension only after the
operator trusts the workspace. The extension maps PI tool events to the same Python gate
policies and sets `DADAIA_ENTRY_HARNESS=pi`. Generated `.pi/**` files contain no secrets
and must not be hand-edited.

OAuth and API-key storage are operator/runtime concerns outside generated workspace
assets; the workspace never copies credential material.

## Telemetry

The PI telemetry reader ingests allowlisted metadata from PI session records. It does
not ingest prompt or response bodies and does not fabricate pricing for models without a
known pricing row.

## Runtime state touched

Scaffold projected by `dadaia public install --target pi`: `.pi/prompts/`,
`.pi/extensions/` (incl. `dadaia-sdd-gate.ts`), and the projected law file. A PI-only
workspace = `--target pi` (+ shared `--target agents`).

## Dependencies

[[multi-platform-parity]], [[agent-monitoring]], [[sdd-gate-v3]],
[[public-asset-distribution]].
