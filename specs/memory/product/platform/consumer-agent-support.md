---
slug: consumer-agent-support
title: Consumer validation gate
category: product
tldr: A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes without its CERTIFIED_100 verdict.
summary: The canonical release gate is a consumer-side validation agent running `CONSUMER_VALIDATION_RECIPE.md` on a real workspace; a deterministic internal gate never approves a release by itself.
tags:
- consumer-validation
- release-gate
- sdd
---

## Purpose

A candidate wheel is certified by a **consumer-side validation agent** — an agent
operating dadaia-workspace on a real workspace outside this repository — before any
deploy. No version publishes without that agent's `CERTIFIED_100` verdict. Internal gates,
`dadaia certify` included, are never validation by themselves: a green internal gate that
diverges from real consumer behavior is itself a bug.

An environment is declared **supported** only when a full real-use round reports zero
failures, not from point checks.

## The support contract

`dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md` ships two halves:

- the deterministic matrix (F-01…F-26 plus structural certification) — components in
  isolation, necessary and never sufficient;
- the **real-use matrix (R-01…R-08)** derived from a real consumer's day-to-day
  inventory: the live Codex chain with per-link artifact proofs (backlog → release →
  implementation → audit), canonical backlog consumption, fresh/old-context doctor-clean
  repair, release-definition terminal honesty, bug-ledger round-trip, fake-chain honesty,
  and the kimi-code harness surface.

Every candidate must pass all of both. `CERTIFIED_100` means every statement PASS, none
excepted.

## Round shape

A round may run against the operator's own environment or a throwaway real workspace
created with `dadaia init` and exercised through supported interfaces only: the installed
version-matched skill surface is what it consumes, every `dadaia` verb it cites is
cross-checked against the live `--help`, and the throwaway repo's own projected hooks are
invoked directly to confirm FROZEN-block and ADDITIVE-allow behavior in the consumer's own
tree. Governance coherence is proven rather than asserted — the full `[ ] → [-] → [x]`
cycle with a clean worktree at each commit, valid memory and schema state, immutable
release evidence.

The round budgets **one remediation cycle inside itself**: a finding is root-caused and
fixed there. What the environment could not exercise is recorded as a named limit and
reported as **not exercised**, never as passed. The operator requires the full sweep in
one batch, never stopping at the first FAIL. How the validation agent is deployed and
hosted is the operator's private environment and is not described here.

## Dependencies

[[workspace-init]], [[tech-stack]], [[spec-context-project]], [[sdd-gate-v3]],
[[workspace-doctor]].
