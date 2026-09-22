---
slug: capabilities
title: capabilities
tldr: "dadaia capabilities [--json] prints the installed contract: distribution and specs pattern versions, status tokens, the live verbs and harnesses."
summary: "A read-only verb an agent runs first in a new or upgraded session: a dadaia-capabilities-v3 JSON payload naming the installed distribution version, the canonical specs pattern version and status tokens, the context states, commands and selection contract, the Layer-1 harnesses and every command group with its subcommands, all derived from the live command tree and the harness registry, plus the certify command; the table view is a digest of the same payload."
tags: [capabilities, contract, provider, onboarding]
sources:
  - dadaia_workspace/features/capabilities/**
  - dadaia_workspace/cli/commands/capabilities.py
---

## Behavior

- `dadaia capabilities --json` prints one sorted-key JSON object, `schema_version` `dadaia-capabilities-v3` (`dadaia_workspace/public/schemas/dadaia-capabilities-v3.schema.json`); without `--json` it prints a short table (provider, specs pattern version, context commands, the machine-output hint).
- `provider.distribution_version` is the installed `dadaia-workspace` version (`0+source` when the package metadata is absent); it is the value a runtime converge passes to `dadaia reconcile --expect-version` before `dadaia certify --json` ([[consumer-agent-support]]), and the value reconcile's capability-canary step compares against `--expect-version`.
- `specs.pattern_version` is the canonical specs pattern version and `specs.status_tokens` the canonical `**Status:**` tokens, both derived from the code the doctor enforces ([[workspace-doctor]], [[specs-migration]]); `specs.commands` is `dadaia specs <verb>` for every `specs` subcommand.
- `contexts` carries `states` (`alive`, `dead`), `commands` (every `context` subcommand) and `selection_contract` `explicit-or-caller-owned-bind` ([[context-management]]).
- `harnesses.layer_1` lists the Layer-1 entry harnesses of `dadaia_workspace/core/harness_registry.py`.
- `surfaces` maps every top-level command group to its subcommand names — `{group: [subcommands]}`, a leaf command mapping to an empty list.
- `certification` names `dadaia certify --json` and its `dadaia-certification-v1` schema; `consumer_requirements` states the consumer's obligations (exact provider version, reconcile after upgrade, load scoped context after bind, keep diagnostics whole, credentials only in the root `.env`).

## Boundaries

- Every advertised verb derives from the live command tree the CLI hands in and every harness from the harness registry, so the payload cannot name what the installation does not ship; each group's `--help` still carries the flags.
- The verb reads nothing from the workspace and writes nothing.

## Dependencies

[[consumer-agent-support]], [[workspace-doctor]], [[pypi-distribution]], [[context-management]].
