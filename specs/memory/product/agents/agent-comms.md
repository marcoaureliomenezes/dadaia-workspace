---
slug: agent-comms
title: agent-comms
category: product
tldr: The handoff-v1 JSON contract agents emit, its stdlib validator behind `dadaia reports`, and ack-on-consume deletion.
summary: Agent-to-agent coordination is a JSON handoff under `.dadaia/handoff/<context>/`, validated against the packaged `handoff-v1` schema; HTML reports are optional evidence under `.dadaia/reports/<context>/<agent>/`.
tags:
- agent-comms
- handoff
- schema
last_updated: '2026-08-28'
release_origin: 0.5.0
---

## What it is

`handoff-v1` is the JSON contract every agent emits for agent-to-agent coordination,
written to `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`. An optional HTML
report under `.dadaia/reports/<context>/<agent>/` is referenced by `artifact.path` +
`artifact.content_hash`.

The current token is `handoff-v1.2`, which carries `self_pull.refs` — the `specs/`-prefixed
memory atoms the emitting session read. The enum also accepts `handoff-v1` and
`handoff-v1.1`; v1.1 is the sanctioned emission for a session that read zero atoms.

## Schema location

- Canonical: `dadaia_workspace/public/schemas/handoff-v1.schema.json` (Draft 2020-12) —
  the single source of field semantics.
- Staged: `.dadaia/agentic/schemas/handoff-v1.schema.json`, the path CLI and skill name.
- Not projected into `.claude/` or `.codex/`: only the Python CLI reads it.

Required top level: `schema_version`, `agent`, `context`, `produced_at`, `artifact`,
`scope`, `metrics`; `findings[]` and `self_pull` are optional. The object is
`additionalProperties: false` (`metrics` accepts arbitrary keys); absolute paths and `..`
are rejected.

## CLI

`dadaia reports {validate|lint|doctor|next|status|cleanup|important|mark-important|unmark-important|mark-efficiency-audit}`.

- `validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]`; `--all`
  discovers `.dadaia/handoff/`. Exit `0` valid, `1` invalid (or soft violation under
  `--strict`), `2` file not found, `3` bad invocation.
- Validation is stdlib-only (`infrastructure/stdlib_handoff_validator.py`) behind
  `core/protocols/handoff_validator.py`'s `ValidatorPort`; `features/reports/validation.py`
  is built by the container. A schema keyword outside the validator's whitelist raises at
  init.
- The v1.2 `self_pull` rule lives in the service, not the schema: non-empty `refs`, each
  ref existing inside the workspace, and role-map coverage — an agent mapped in
  `core/role_atom_map.py` must list its mapped atom.
- With `artifact.path` present the artifact is resolved inside the workspace and its
  SHA-256 recomputed.

## Skill: dadaia-handoff-emitter

`public/skills/dadaia-handoff-emitter/` holds the emission protocol, projected to
`.agents/skills/` and `.claude/skills/`. Every emission-instruction surface carries the
v1.2/`self_pull` instruction, pinned by
`tests/contract/test_handoff_instruction_adoption.py` with a roster-completeness assert.

## Lifecycle

A consumed **coordination** handoff is deleted by the consumer that acted on it, scoped to
that one file. A handoff carrying `artifact.path` is artifact-bearing and exempt, following
its report's retention. Every deletion lane resolves its target, refuses one outside
`.dadaia/`, and never follows a symlinked directory; the remainder is swept at release
closure ([[agent-monitoring]]).

## Dependencies

[[public-asset-distribution]] — the `schemas` asset type reaches staging and the runtime
roots through the projection chain.
