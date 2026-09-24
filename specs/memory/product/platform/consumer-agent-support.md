---
slug: consumer-agent-support
title: Consumer validation gate
tldr: A consumer-side validation agent running the shipped recipe on a real workspace is the release gate; no wheel publishes until every statement reports PASS.
summary: The release gate is a consumer-side validation agent running the shipped recipe on a real workspace; dadaia certify runs the deterministic journey in a disposable workspace and is necessary, never sufficient.
tags: [consumer-validation, release-gate, sdd]
sources:
  - dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md
  - dadaia_workspace/features/certification/**
  - dadaia_workspace/infrastructure/certification_process.py
  - dadaia_workspace/cli/commands/certify.py
---

## The gate

- A candidate wheel is certified by a consumer-side validation agent operating dadaia-workspace outside this repository; no version publishes until every recipe statement reports PASS, none excepted.
- `dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md` ships two matrices: the deterministic `F-` statements plus structural certification, and the real-use `R-` statements — among them real-demand backlog consumption, doctor-clean repair of a fresh and of an old tree, the bug record round-trip, the Kimi Code harness end to end, producers passing their own validators, the agent-model roster running on its mapped models, a hostile filesystem at bootstrap, no verb traceback on any failure, and an unrepairable environment limit never reported as repairable.
- A round runs against the operator's environment or a throwaway `dadaia init` workspace through supported interfaces only: the version-matched skills, every cited verb checked against live `--help`, the projected hooks invoked directly.
- Governance coherence is proven, not asserted: the full `[ ] → [-] → [x]` cycle with a clean worktree at each commit, valid memory and schema state, immutable evidence.
- A round budgets one remediation cycle; what the environment could not exercise is reported as not exercised, never as passed.

## `dadaia certify`

- `dadaia certify [--json]` runs the deterministic public-feature journey in a disposable workspace under `.dadaia/tmp/certification/<id>/`, with its own `HOME` and the session and context variables cleared, and reports one check per step; its empty-remote step walks the onboarding levels — `context create --main-repo <bare remote>`, `specs init --context`, `context baseline --yes --push`.
- A failed certify check is a release blocker, yet a green certify never approves a release by itself ([[pypi-distribution]]).

## Dependencies

[[workspace-init]], [[ARCHITECTURE]], [[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[capabilities]].
