---
slug: agent-comms
title: agent-comms
tldr: The handoff-v1 JSON contract agents emit, its validator behind `dadaia reports validate`, and ack-on-consume deletion with a one-day TTL.
summary: Agent-to-agent coordination is a JSON handoff under the workspace handoff tree, validated against the packaged handoff-v1 schema, with an HTML report as optional evidence.
tags: [agent-comms, handoff, schema]
sources:
  - dadaia_workspace/core/handoff_index.py
  - dadaia_workspace/cli/commands/reports.py
  - dadaia_workspace/public/schemas/handoff-v1.schema.json
  - dadaia_workspace/public/skills/dd-handoff-emitter/**
---

## The contract

- `handoff-v1` is the JSON record every agent emits, written to `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.
- An optional HTML report at `.dadaia/reports/<context>/<UTC>-<agent>-<slug>.html` — an output zone never reaped or committed — is referenced by `artifact.path` plus `artifact.content_hash`.
- `schema_version` accepts `handoff-v1`, `handoff-v1.1` and `handoff-v1.2`; `handoff-v1.2` carries `self_pull.refs` — the `specs/`-prefixed atoms the session read — and `handoff-v1.1` is the emission for a session that read none.
- An optional `verdict` (`APPROVED`/`REJECTED`) records `dd-code-reviewer`'s verdict, written only by the emitter's `verdict.py` (the reviewer's one write), which binds it to `reviewed_sha`, the commit judged, and `diff_sha256`, the hash of its diff from `worktree.py hash`; `worktree.py merge` lands a job, plain, `define` or backlog worktree only when the newest verdict naming its rebased HEAD, or a reflog sha of the same patch and message series, as `reviewed_sha` is a valid `APPROVED` whose `diff_sha256` matches the diff the merge lands, a task needing none ([[worktrees]]).
- `dadaia_workspace/public/schemas/handoff-v1.schema.json` is the single source of field semantics, staged to `.dadaia/agentic/schemas/` and never projected into a harness root; only the CLI reads it.

## Validation

- `dadaia reports validate` is the `reports` group's only verb: exit 0 all valid, 1 any refusal (an invalid file, a path not found, a bare call, no workspace); `--all` scans `.dadaia/handoff/`, `--release` filters by `release_id`, `--json` emits machine output.
- `--workspace` pins the workspace root; `--reviewed-root` resolves `self_pull.refs` against another tree (a worktree at the reviewed commit) before `repos/<context>/<ref>` and `<workspace>/<ref>`.
- `dadaia_workspace/core/handoff_index.py` is the one handoff reader: `HandoffIndex.validate_file()` validates, and `Handoff.validate()` checks schema shape (through `jsonschema`), version, the `self_pull` rule and the artifact hash; every other consumer calls it.
- The `self_pull` rule lives in the reader, not the schema: a `handoff-v1.2` record needs non-empty `refs`, each an existing file inside its boundary root.
- With `artifact.path` present the artifact is resolved inside the workspace (no `..` or symlink escape) and its SHA-256 recomputed.

## Lifecycle

- A consumed coordination handoff is deleted by the consumer that acted on it, scoped to that one file, refusing a target outside `.dadaia/` and never following a symlinked directory (`dd-handoff-emitter`).
- The `handoff` zone has a one-day TTL: every handoff expires one day after its mtime and `dadaia doctor --fix --expired-only` reaps it at session start, `artifact.path` or not ([[workspace-doctor]]).

## Dependencies

[[public-asset-distribution]] — the schema reaches `.dadaia/agentic/schemas/` through staging; [[workspace-doctor]] — the TTL reaper; [[worktrees]] — the merge's verdict gate.
