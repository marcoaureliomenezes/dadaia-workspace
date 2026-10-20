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
- An optional `verdict` (`APPROVED`/`REJECTED`) records `dd-code-reviewer`'s verdict, written only by the emitter's `verdict.py` (the reviewer's one write), which binds it to `reviewed_sha`, the commit judged (a SHA-1 or SHA-256 object id), and `diff_sha256`, the hash of its diff from the worktree script's `hash`, then validates the written file with `reports validate --reviewed-root <tree>` (a workspace CLI that is missing or cannot start is a refusal carrying the `uvx dadaia-workspace init` fix): a file that fails is deleted and the refusal names the failing field, so the printed path is a valid verdict. `--context` follows the kernel's context-name grammar, and every `verdict.py` refusal prints one `fix:` line; the `merge` verb of `dadaia worktree` lands a `wt-main`, `wt-rc`, backlog or hotfix tree only when the newest verdict naming its rebased HEAD, or a reflog sha of the same patch and message series, as `reviewed_sha` is a valid `APPROVED` whose `diff_sha256` matches the diff the merge lands, a task needing none ([[worktrees]]).
- `verdict.py stats <M.m.p>-rc<N> [--specs <dir>]` prints one candidate's local readout table, each metric with its value and target, read from the ledgers, the verdict handoffs and git, never a remote or a host CLI: (1) fix-induced bugs, the share of records closed in the bug window whose `caused_by` is not `none`; (2) first-pass approval, the share of trees, lanes included, whose first verdict between the candidate's birth and its CLOSURE stamp is `APPROVED`; (4) closure duration, the CLOSURE stamp to the first merge on the integration branch's first-parent line that holds the closure sha, else `n/a`; (6) commits landed after that sha that are neither a closure-record shape nor a `block:` fix; (7) the atoms `release.py drift` names, for the newest candidate only; (9) the REBUILD-due fixes among the bugs closed in the bug window. The bug window runs from the previous candidate's CLOSURE stamp (empty for the first candidate) to this one's (now while it has none), read from `_RELEASE.json`'s `log`, so a bug closed between two candidates counts in exactly one; its counts come from running `bugs.py stats --closed-after <ts> --closed-until <ts>`, never from importing the ledger's code. It first runs `release.py check` on the specs tree and refuses, with `[error]` and check's first finding and one fix line, any tree check refuses — a release state that breaks the release schema included, and in CLOSURE one whose memory pass is not yet recorded — then reads `_RELEASE.json`; a version with no release folder, a candidate the log never names, or a malformed name reads `n/a` for every metric. Only verdicts of the context that owns the repo count, the repo named by the kernel's one main-checkout helper so a worktree reads the same table as its checkout, and the context and its integration branch read through the bug ledger's one context reader ([[bug-ledger]]), whose failing `context list --json` refuses with the CLI's own fix. A last row names the oldest verdict record read, and a value the local data cannot give reads `n/a` ([[release-lifecycle]]).
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
