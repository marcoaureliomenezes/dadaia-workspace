---
slug: consumer-agent-support
title: Consumer validation gate — supported consumer environments
category: product
tldr: 'A consumer-side validation agent running the shipped recipe is the release gate: no wheel is published without its CERTIFIED_100 verdict.'
summary: >-
  A consumer-side validation agent running the shipped consumer validation recipe on
  a real workspace is the canonical release gate of dadaia-workspace. A consumer
  environment is declared SUPPORTED only after a full real-use round reports zero
  failures. Deterministic certification alone never approves a release.
tags:
- consumer-validation
- release-gate
- sdd
token_estimate: 300
last_updated: '2026-08-06'
release_origin: v0.2.9
---

## Purpose

The release law is consumer-first: a candidate wheel is certified by a
**consumer-side validation agent** — an agent operating dadaia-workspace on a real
workspace outside this repo — before any deploy. No version is published without a
`CERTIFIED_100` verdict from that agent. Internal gates (`certify` included) are
never, by themselves, validation: a green internal gate that diverges from real
consumer behavior is itself a bug.

Declaring a consumer environment **supported** means its day-to-day activities run
on dadaia-workspace without product bugs — proven by a full real-use round with
zero failures, not by point checks.

## The support contract

`dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md` ships two halves:

- The deterministic matrix (F-01…F-26 + structural certification): components in
  isolation. Necessary, never sufficient alone.
- The **Real-use matrix (R-01…R-08)**, derived from a real consumer's day-to-day
  inventory: the live Codex chain with per-link artifact proofs (backlog → release
  → implementation → audit), canonical backlog consumption, fresh/old-context
  doctor-clean repair, release-definition terminal honesty, bug-ledger round-trip,
  fake-chain honesty, and the kimi-code harness surface. Every release candidate
  must pass ALL of it.

## Convergence posture (v0.2.9)

The v0.2.9 loop worked by root-cause classes, never instance patches:
materialization delta gating, placeholder-atom repair, bounded retry digests, and
observable bounded revisions (`revision_note` on the run record, both retry
mechanisms). The 0.4.1 candidate reached CERTIFIED_100 — 35 PASS / 0 FAIL /
0 EXCEPTION.

## How to validate

The operator hands the candidate wheel to the consumer-side validation agent and
requires a full sweep in one batch: structural gate + deterministic matrix + the
whole Real-use matrix, never stopping at the first FAIL. How that agent is
deployed, triggered, and hosted is the **operator's private environment** and is
deliberately not described here — this library documents the gate's contract, not
any consumer's infrastructure.

## Dependencies

[[workspace-init]], [[tech-stack]], [[spec-context-project]], [[sdd-gate-v3]],
[[workspace-doctor]].
