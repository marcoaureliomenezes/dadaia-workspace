---
slug: harness-pi
title: Harness - PI (pi-coding-agent)
category: product
tldr: Entry harness whose TypeScript SDD-gate extension loads only after the operator explicitly trusts the workspace.
summary: >-
  PI enters the workspace interactively after explicit trust. Its `.pi/**` projection is
  post-trust EXECUTABLE TypeScript, unlike every other projection, which makes trusting it
  a deliberate privilege grant rather than inert configuration.
tags:
- harness
- pi
- layer-1
- projection
token_estimate: 380
last_updated: '2026-07-14'
release_origin: v0.2.5
---

## Purpose

PI is an entry harness. It is an operator-installed external CLI, not a Python package
dependency.

## Projection

`.pi/` is a generated projection. PI loads its TypeScript SDD gate extension only after
the operator trusts the workspace. The extension maps PI tool events to the same Python
gate policies and sets `DADAIA_ENTRY_HARNESS=pi` to identify the entry session.
Generated `.pi/**` files contain no secrets and must not be hand-edited.

## Telemetry

The PI telemetry reader ingests allowlisted metadata from PI session records. It does
not ingest prompt or response bodies and does not fabricate pricing for models without a
known pricing row.

## Dependencies

[[multi-platform-parity]],
[[agent-monitoring]], [[sdd-gate-v3]].
