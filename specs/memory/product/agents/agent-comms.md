---
slug: agent-comms
title: agent-comms — Handoff Contract v1
category: product
tldr: 'handoff-v1.1 separates HTML reports from JSON handoffs in .dadaia/handoff/.'
summary: 'the handoff-v1.1 contract separates human evidence from agent-to-agent
  coordination: HTML reports in .dadaia/reports/<context>/<agent>/ and JSON handoffs
  in .dadaia/handoff/<context>/. The CLI validates schema and artifact.path hash
  inside the workspace — any existing relative path under the root resolves
  workspace-rooted (incl. repos/<slug>/specs/audits), with a legacy handoff-dir
  fallback; reports next and the QA/security gate consume the canonical root.'
tags:
- agent-comms
- handoff
- schema
agent_tier: self-pull
token_estimate: 1075
last_updated: '2026-07-02'
release_origin: v0.1.48
---

CLI surface: `dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]` · `dadaia reports lint [DIR]` · `dadaia reports next [--context <ctx>] [--json]`

## What it is

**handoff-v1** is the structured JSON contract every specialist agent emits for agent-to-agent coordination. HTML reports stay in `.dadaia/reports/<context>/<agent>/`; JSON handoffs live in `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`. The document references the delivered report or artifact via `artifact.path` and `artifact.content_hash`.

It materializes the symbolic referent `schema_ref: handoff-schema-v1` declared by the topology's agents; the schema lives on disk (`public/schemas/` → staging) and is consumed by CLI + skill.

It resolves the "build-on-stale-layer" pattern identified in the orchestration audit: `input_contract` was declared as verifiable, but the referent pointed at a vacuum. Any handoff can be audited mechanically via `dadaia reports validate <path>` or `dadaia reports validate --all` — with no external dependencies beyond the stdlib.

The contract separates human evidence from machine coordination: HTML reports are for human/panel reading; handoffs are the verifiable state other agents read before QA, review, security, or closure.

## Schema location

  * **Canonical:** `dadaia_workspace/public/schemas/handoff-v1.schema.json` (JSON Schema Draft 2020-12, `$schema = "https://json-schema.org/draft/2020-12/schema"`).
  * **Staging projection:** `.dadaia/agentic/schemas/handoff-v1.schema.json` (generated via `dadaia public stage`). It is the logical path CLI + skill consume at runtime.
  * **NOT projected** to `.claude/schemas/`, `.codex/schemas/`, `.pi/schemas/` — the schema is consumed only by the Python CLI, not by the agents' runtime. Decision A1 saved 3 duplications.
  * **Asset type:** `schemas` is one of the asset types in `_COPY_DIRS` in `dadaia_workspace/infrastructure/public_assets_common.py`. The live list of asset types is documented in [[public-asset-distribution]] (the constitution does not enumerate asset types).



The field contract's single source of truth is the schema file itself: `dadaia_workspace/public/schemas/handoff-v1.schema.json`. One-line summary: required top-level fields are `schema_version` (enum `"handoff-v1"` | `"handoff-v1.1"`), `agent`, `context`, `produced_at`, `artifact` (requires only `type`; `path` is optional and workspace-relative — `content_hash` must accompany it when present), `scope`, `metrics`; `findings[]` is OPTIONAL (each finding item requires `severity`, `message`, `detail_md`, `fix_recommendation`). Absolute paths and parent traversal are rejected; the top-level object is `additionalProperties: false` (while `metrics` accepts arbitrary keys).

## CLI


    dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]

  * **Stdlib-only validator** (`infrastructure/stdlib_handoff_validator.py`): `json`, `re`, `datetime.fromisoformat`. Explicit keyword whitelist (`type`, `required`, `enum`, `pattern`, `properties`, `items`, `additionalProperties`, `format`, `minimum`, `minItems`). A schema with a keyword outside the whitelist (`oneOf`, `allOf`, `$ref`) raises `HandoffSchemaError` at init.
  * **Discovery:** `--all` reads `.dadaia/handoff/` by default. Explicit paths remain supported.
  * **Hash:** when `artifact.path` exists, `validate_file()` resolves the artifact inside the workspace and rejects mismatch, missing artifact, or a reference outside the workspace.
  * **`artifact.path` resolution (workspace-rooted):** any **relative** path that exists under the workspace root resolves from the root — covering `repos/<slug>/specs/audits/<UTC>/…` (the auditor's committed channel) and any other workspace-rooted path, not just `.dadaia/…`. The legacy fallback (resolution relative to the handoff's own directory) is kept for paths that only exist there; when a path resolves both ways, **workspace-root wins**. Absolute paths and `..` segments remain rejected by the schema; the `_within_workspace` guard remains.
  * **Exit codes:** `0` = all valid (or violations in non-strict); `1` = violation in strict; `2` = file not found; `3` = bad invocation (neither PATHS nor `--all`, or workspace not initialized).
  * **Default `--strict=false`**: violations surface as warnings in non-strict. Release gates use QA/security handoffs with coherent `verdict`, `release_id`, `context`, and `agent`.
  * **Composition (constitution L67-compliant):** `cli/commands/reports.py` resolves `ReportsValidationService` via `container.build_reports_validation_service(workspace_root)`; `service.py` does not import `StdlibHandoffValidator` directly — it receives it via the `ValidatorPort` Protocol in `core/protocols/handoff_validator.py`.
  * **Coverage:** 98% scoped in `features/reports_validation` (NFR8 ≥ 80% honored with room to spare).



## Skill: dadaia-handoff-emitter

Standalone skill at `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`, projected to `.agents/skills/` (universal projection — the Codex runtime consumes this dir) and `.claude/skills/`; nothing lands in `.codex/skills/` or `.pi/` (the PI projection carries only the staged `pi/` tree). 3-step protocol:

  1. **sha256sum** of the just-generated HTML report.
  2. **Assemble dict** with the required fields + the optional fields applicable to the agent, referencing the schema by the logical path `.dadaia/agentic/schemas/handoff-v1.schema.json` (A10 — the skill does not duplicate schema content inside the markdown; single source of truth).
  3. **Write** the file `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.



Minimal handoff: ~500 bytes (required fields only); typical: <2 KB; warning if >4 KB. For an average 50–70 KB HTML report, overhead is ~3% worst case (NFR5).

## Adoption (9 core agents)

The 9 core public agents declare `dadaia-handoff-emitter` when they produce
reports/handoffs that need a machine-readable sidecar. Optional packs may adopt the
same contract, but they are not part of the default public topology.

```mermaid
flowchart LR
    AG[Pilot agent] -->|generates| HTML[HTML report]
    AG -->|invokes| SKILL[dadaia-handoff-emitter SKILL]
    SKILL -->|sha256sum| HASH[content_hash]
    SKILL -->|assembles dict| DOC[HandoffDocument]
    SKILL -->|Write| JSON[.dadaia/handoff/context/file.handoff.json]
    JSON -.artifact.path.- HTML
    CLI[dadaia reports validate] -->|read| JSON
    CLI -->|read| SCHEMA[.dadaia/agentic/schemas/handoff-v1.schema.json]
    CLI -->|stdlib-only| VAL[StdlibHandoffValidator]
    VAL -->|0 ok / 1 strict / 2 nf / 3 bad| EXIT[exit code]
```

## Dependencies

  * [[public-asset-distribution]] — the `public/` → `.dadaia/agentic/` → multi-tool projection chain propagates the `schemas` asset type.
