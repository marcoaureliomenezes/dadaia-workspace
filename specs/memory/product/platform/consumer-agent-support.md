---
slug: consumer-agent-support
title: Consumer validation gate
tldr: A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes until every statement reports PASS.
summary: The canonical release gate is a consumer-side validation agent running the shipped recipe on a real workspace; a deterministic internal gate never approves a release by itself.
tags: [consumer-validation, release-gate, sdd]
---

## The gate

- A candidate wheel is certified by a consumer-side validation agent operating dadaia-workspace outside this repository, and no version publishes until every recipe statement reports PASS.
- Internal gates, `dadaia certify` included, are never validation by themselves, and an environment is supported only after a full real-use round reports zero failures.
- `public/data/CONSUMER_VALIDATION_RECIPE.md` ships the deterministic matrix (F-01…F-25 plus structural certification), necessary and never sufficient.
- It also ships the real-use matrix (R-01…R-21) from a real consumer's inventory — among them real-demand backlog consumption, doctor-clean repair of a fresh and of an old tree, the bug record round-trip, the Kimi Code harness end to end, producers passing their own validators, surfaced foreign presence, the agent-model roster running on its mapped models, a hostile filesystem at bootstrap, no verb traceback on any failure, and an unrepairable environment limit never reported as repairable.
- Every candidate wheel must pass all of both — every statement PASS, none excepted.
- A round runs against the operator's environment or a throwaway `dadaia init` workspace, through supported interfaces only: the version-matched skill surface, every cited verb checked against the live `--help`, and the projected hooks invoked directly.
- Governance coherence is proven, not asserted — the full `[ ] → [-] → [x]` cycle with a clean worktree at each commit, valid memory and schema state, immutable evidence.
- The round budgets one remediation cycle inside itself, and what the environment could not exercise is reported as not exercised, never as passed.

## Dependencies

[[workspace-init]], [[TECHSTACK]], [[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]].
