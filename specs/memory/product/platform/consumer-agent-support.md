---
slug: consumer-agent-support
title: Consumer validation gate
category: product
tldr: A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes without its CERTIFIED_100 verdict.
summary: The canonical release gate is a consumer-side validation agent running the shipped recipe on a real workspace; a deterministic internal gate never approves a release by itself.
tags: [consumer-validation, release-gate, sdd]
---

## The gate

- A candidate wheel is certified by a consumer-side validation agent operating dadaia-workspace outside this repository, and no version publishes without its `CERTIFIED_100` verdict.
- Internal gates, `dadaia certify` included, are never validation by themselves, and an environment is supported only after a full real-use round reports zero failures.
- `public/data/CONSUMER_VALIDATION_RECIPE.md` ships the deterministic matrix (F-01…F-26 plus structural certification), necessary and never sufficient.
- It also ships the real-use matrix (R-01…R-08) from a real consumer's inventory — the live Codex chain with per-link artifact proofs, backlog consumption, doctor-clean repair, terminal honesty, bug-ledger round-trip and the kimi-code surface.
- Every candidate must pass all of both; `CERTIFIED_100` means every statement PASS, none excepted.
- A round runs against the operator's environment or a throwaway `dadaia init` workspace, through supported interfaces only: the version-matched skill surface, every cited verb checked against the live `--help`, and the projected hooks invoked directly.
- Governance coherence is proven, not asserted — the full `[ ] → [-] → [x]` cycle with a clean worktree at each commit, valid memory and schema state, immutable evidence.
- The round budgets one remediation cycle inside itself, and what the environment could not exercise is reported as not exercised, never as passed.

## Dependencies

[[workspace-init]], [[tech-stack]], [[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]].
