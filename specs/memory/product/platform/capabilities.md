---
slug: capabilities
title: capabilities
tldr: "dadaia capabilities [--json] prints the installed provider's contract — distribution version, specs pattern version, status tokens, certification entry point."
summary: "A read-only verb an agent runs first in a new or upgraded session: a dadaia-capabilities-v2 JSON payload naming the installed distribution version, the canonical specs pattern version and status tokens, context states and the certify command; the table view is a digest of the same payload."
tags: [capabilities, contract, provider, onboarding]
sources:
  - dadaia_workspace/features/capabilities/**
  - dadaia_workspace/cli/commands/capabilities.py
---

## Behavior

- `dadaia capabilities --json` prints one sorted-key JSON object, `schema_version` `dadaia-capabilities-v2`; without `--json` it prints a short table (provider, specs pattern version, context commands, the machine-output hint).
- `provider.distribution_version` is the installed `dadaia-workspace` version (`0+source` when the package metadata is absent); it is the value a runtime converge passes to `dadaia reconcile --expect-version` before `dadaia certify --json` ([[consumer-agent-support]]).
- `specs.pattern_version` is the canonical specs pattern version and `specs.status_tokens` the canonical `**Status:**` tokens, both derived from the code the doctor enforces ([[workspace-doctor]], [[specs-migration]]).
- `certification` names `dadaia certify --json` and its `dadaia-certification-v1` schema; `consumer_requirements` states the consumer's obligations (exact provider version, reconcile after upgrade, load scoped context after bind, keep diagnostics whole, credentials only in the root `.env`).

## Boundaries

- The `contexts`, `harnesses` and `surfaces` blocks are a hand-kept list, not derived from the command tree; the live verb set is `dadaia help tree` and each group's `--help`.
- The verb reads nothing from the workspace and writes nothing.

## Dependencies

[[consumer-agent-support]], [[workspace-doctor]], [[pypi-distribution]].
