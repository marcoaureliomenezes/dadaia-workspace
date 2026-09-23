---
slug: agent-comms
title: agent-comms
tldr: The handoff-v1 JSON contract agents emit, its stdlib validator behind `dadaia reports validate`, and ack-on-consume deletion with a one-day TTL.
summary: Agent-to-agent coordination is a JSON handoff under the workspace handoff tree, validated against the packaged handoff-v1 schema, with an HTML report as optional evidence.
tags: [agent-comms, handoff, schema]
sources:
  - dadaia_workspace/core/handoff_index.py
  - dadaia_workspace/cli/commands/reports.py
  - dadaia_workspace/public/schemas/handoff-v1.schema.json
---

## The contract

- `handoff-v1` is the JSON record every agent emits, written to `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.
- An optional HTML report under `repos/<slug>/reports/<agent>/` is referenced by `artifact.path` plus `artifact.content_hash`.
- `schema_version` accepts `handoff-v1`, `handoff-v1.1` and `handoff-v1.2`; `handoff-v1.2` carries `self_pull.refs` — the `specs/`-prefixed atoms the session read — and `handoff-v1.1` is the emission for a session that read none.
- An optional `verdict` (`APPROVED`/`REJECTED`) records `dd-code-reviewer`'s recommendation.
- `dadaia_workspace/public/schemas/handoff-v1.schema.json` is the single source of field semantics, staged to `.dadaia/agentic/schemas/` and never projected into a harness root; only the CLI reads it.

## Validation

- `dadaia reports validate` is the `reports` group's only verb: exit 0 all valid, 1 any invalid, 2 a path not found, 3 bad invocation or no workspace; `--all` scans `.dadaia/handoff/`, `--release` filters by `release_id`, `--json` emits machine output.
- `--workspace` pins the workspace root; `--reviewed-root` resolves `self_pull.refs` against another tree (a worktree at the reviewed commit) before `repos/<context>/<ref>` and `<workspace>/<ref>`.
- `dadaia_workspace/core/handoff_index.py` is the one handoff reader: `HandoffIndex.scan()` discovers, `Handoff.validate()` checks schema shape and version, the `self_pull` rule and the artifact hash; every other consumer calls it.
- Validation is stdlib-only, and a schema keyword outside the supported set raises rather than passing unchecked.
- The `self_pull` rule lives in the reader, not the schema: a `handoff-v1.2` record needs non-empty `refs`, each an existing file inside its boundary root.
- With `artifact.path` present the artifact is resolved inside the workspace (no `..` or symlink escape) and its SHA-256 recomputed.

## Lifecycle

- A consumed coordination handoff is deleted by the consumer that acted on it, scoped to that one file, refusing a target outside `.dadaia/` and never following a symlinked directory (`dd-handoff-emitter`).
- The `handoff` zone has a one-day TTL: every handoff expires one day after its mtime and `dadaia doctor --fix --expired-only` reaps it at session start, `artifact.path` or not ([[workspace-doctor]]).

## Dependencies

[[public-asset-distribution]] — the schema reaches `.dadaia/agentic/schemas/` through staging; [[workspace-doctor]] — the TTL reaper.
