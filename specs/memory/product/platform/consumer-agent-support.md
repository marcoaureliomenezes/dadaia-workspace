---
slug: consumer-agent-support
title: Consumer validation gate — supported consumer environments
category: product
tldr: 'A consumer-side validation agent running the shipped recipe is the release gate: no wheel is published without its CERTIFIED_100 verdict.'
summary: >-
  A consumer-side validation agent running the shipped consumer validation recipe on
  a real workspace is the canonical release gate of dadaia-workspace. A consumer
  environment is declared SUPPORTED only after a full real-use round reports zero
  failures. Deterministic certification alone never approves a release. A round may also
  run against a throwaway real workspace created with dadaia init; whatever such an
  environment cannot exercise is recorded as a named limit and reported as not exercised,
  never as passed, and one remediation cycle is budgeted inside the round itself.
tags:
- consumer-validation
- release-gate
- sdd
last_updated: '2026-08-18'
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

## Convergence posture

The loop converges by **root-cause classes, never instance patches**: materialization
delta gating, placeholder-atom repair, bounded retry digests, and observable bounded
revisions (`revision_note` on the run record, on both retry mechanisms). A candidate is
certified only at `CERTIFIED_100` — every statement of both matrices PASS, none excepted.

Alongside the operator's own consumer environment, a release round may run against a
**throwaway real workspace** created with `dadaia init` under the workspace tmp and
exercised through supported interfaces only. Real, not simulated: the installed
version-matched skill surface is what the round consumes, every `dadaia` verb it references
is cross-checked against the live `--help`, and the throwaway repo's own projected hooks
are invoked directly to confirm the FROZEN-block and ADDITIVE-allow behavior in the
consumer's own tree. Governance coherence is proven in that workspace rather than asserted:
the full `[ ] → [-] → [x]` marker cycle with a clean worktree at each commit, valid
memory/schema state, immutable release evidence. The in-place upgrade path is proven from
both ends — a pre-single-source workspace **surfaces** its un-migrated backlog as a warning
count equal to its loose per-entry-file count while the backlog doctor is legitimately
clean on an absent document, then folds to a clean two-doctor state after migration.

The round budgets **one remediation cycle inside itself**: a finding is root-caused and
fixed there, not deferred out. What the environment could not exercise is recorded as a
limit and reported as **not exercised** — never as passed. That distinction is the whole
value of the round: an unexercised criterion silently reported green would make the gate
itself the bug it exists to catch.

## How to validate

The operator hands the candidate wheel to the consumer-side validation agent and
requires a full sweep in one batch: structural gate + deterministic matrix + the
whole Real-use matrix, never stopping at the first FAIL. A round that reaches into new
runtime behavior states which capabilities it actually exercised and which it could not,
by name. How that agent is deployed, triggered, and hosted is the **operator's private
environment** and is deliberately not described here — this library documents the gate's
contract, not any consumer's infrastructure.

## Dependencies

[[workspace-init]], [[tech-stack]], [[spec-context-project]], [[sdd-gate-v3]],
[[workspace-doctor]].
