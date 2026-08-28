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
---

## The contract

`handoff-v1` is the JSON contract every agent emits for agent-to-agent coordination, written to
`.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`. An optional HTML report under
`.dadaia/reports/<context>/<agent>/` is referenced by `artifact.path` + `artifact.content_hash`.
The current token is `handoff-v1.2`, carrying `self_pull.refs` — the `specs/`-prefixed memory atoms
the emitting session read; the enum also accepts `handoff-v1` and `handoff-v1.1`, the latter being
the sanctioned emission for a session that read zero atoms.
`dadaia_workspace/public/schemas/handoff-v1.schema.json` is the single source of field semantics,
staged to `.dadaia/agentic/schemas/` — the path the CLI and skills name — and never projected into a
harness root, since only the Python CLI reads it.

## Validation and lifecycle

`dadaia reports validate` exits `0` valid, `1` invalid (or soft violation under `--strict`), `2`
file not found, `3` bad invocation, and discovers `.dadaia/handoff/` under `--all`; sibling verbs
cover lint, doctor, next, status, cleanup and the importance/efficiency marks. Validation is
stdlib-only behind `core/protocols/handoff_validator.py`'s `ValidatorPort`, and a schema keyword
outside the validator's whitelist raises at init. The v1.2 `self_pull` rule lives in the service,
not the schema: non-empty `refs`, each ref existing inside the workspace, and role-map coverage — an
agent mapped in `core/role_atom_map.py` must list its mapped atom. With `artifact.path` present the
artifact is resolved inside the workspace and its SHA-256 recomputed.
`public/skills/dadaia-handoff-emitter/` holds the emission protocol, and every
emission-instruction surface carries the v1.2/`self_pull` instruction, pinned by a contract test.

A consumed **coordination** handoff is deleted by the consumer that acted on it, scoped to that one
file. A handoff carrying `artifact.path` is artifact-bearing and exempt, following its report's
retention. Every deletion lane resolves its target, refuses one outside `.dadaia/`, and never
follows a symlinked directory; the remainder is swept at release closure ([[agent-monitoring]]).

## Dependencies

[[public-asset-distribution]] — the `schemas` asset type reaches staging and the runtime roots
through the projection chain.
