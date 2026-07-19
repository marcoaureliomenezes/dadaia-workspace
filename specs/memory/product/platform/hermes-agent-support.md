---
slug: hermes-agent-support
title: Hermes agent — supported consumer environment
category: product
tldr: 'Hermes agent is a supported consumer: certified end-to-end via the consumer recipe Real-use matrix, converged to zero failures in v0.2.9.'
summary: >-
  The hermes agent (dd-chain-capture hermes-crawler) is the canonical consumer and
  release gate of dadaia-workspace. Since v0.2.9 it is a declared SUPPORTED
  environment: the consumer validation recipe carries a Real-use matrix built from
  the hermes day-to-day inventory, and the 0.4.1 candidate converged to a full
  real-use round with zero failures (CERTIFIED_100, 35/35).
tags:
- hermes
- consumer-validation
- release-gate
- sdd
token_estimate: 400
last_updated: '2026-07-19'
release_origin: v0.2.9
---

## Purpose

Hermes agent is the canonical consumer of dadaia-workspace: it certifies every
candidate wheel before deploy (the release law: no PyPI publish without its
CERTIFIED_100). Declaring hermes "supported" means its day-to-day activities run
on dadaia-workspace without product bugs — proven by a full real-use round with
zero failures, not by point checks.

## The support contract

`dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md` ships two halves:

- The deterministic matrix (F-01…F-26 + structural certification): components in
  isolation. Necessary, never sufficient alone.
- The **Real-use matrix (R-01…R-08)**, derived from the hermes day-to-day
  inventory (discovery task tg-1784485392): the live Codex chain with per-link
  artifact proofs (backlog → release → implementation → audit), canonical backlog
  consumption, fresh/old-context doctor-clean repair, release-definition terminal
  honesty, bug-ledger round-trip, fake-chain honesty, and the kimi-code harness
  surface. Every release candidate must pass ALL of it.

## Convergence posture (v0.2.9)

The v0.2.9 loop worked by root-cause classes, never instance patches:
materialization delta gating, placeholder-atom repair, bounded retry digests, and
observable bounded revisions (`revision_note` on the run record, both retry
mechanisms). The hermes verdict for 0.4.1 is CERTIFIED_100 — 35 PASS / 0 FAIL /
0 EXCEPTION — so hermes is declared supported from this release onward.

## How to validate

Stage the candidate wheel at the hermes worker (`/opt/data/candidate/` +
`CANDIDATE.txt`), submit the certification demand through the task journal
(`hermes-task-v1`, `tg-<digits>`) and the worker socket trigger, and require a
full sweep: structural gate + deterministic matrix + the whole Real-use matrix in
one batch, never stopping at the first FAIL.

## Dependencies

[[workspace-init]], [[tech-stack]], [[spec-context-project]], [[sdd-gate-v3]],
[[workspace-doctor]].
