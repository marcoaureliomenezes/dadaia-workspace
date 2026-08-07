---
slug: agent-comms
title: agent-comms — Handoff Contract v1
category: product
tldr: 'handoff-v1.2 separates HTML reports from JSON handoffs and carries the self_pull Layer-1 read-proof line.'
summary: 'the handoff-v1 family contract separates human evidence from agent-to-agent
  coordination: HTML reports in .dadaia/reports/<context>/<agent>/ and JSON handoffs
  in .dadaia/handoff/<context>/. Current version handoff-v1.2 requires self_pull.refs
  — the Layer-1 memory atoms the session actually read (specs/-prefixed, existence-checked,
  role-map coverage) — with historical v1/v1.1 documents valid forever (transition
  posture). The CLI validates schema, the v1.2 self_pull conditional, and artifact.path
  hash inside the workspace — any existing relative path under the root resolves
  workspace-rooted (incl. repos/<slug>/specs/audits), with a legacy handoff-dir
  fallback; reports next and the QA/security gate consume the canonical root.'
tags:
- agent-comms
- handoff
- schema
token_estimate: 1500
last_updated: '2026-08-07'
release_origin: v0.3.0
---

CLI surface: `dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]` · `dadaia reports lint [DIR]` · `dadaia reports next [--context <ctx>] [--json]`

## What it is

**handoff-v1** is the structured JSON contract family every specialist agent emits for agent-to-agent coordination; the current version token is **`handoff-v1.2`**. HTML reports stay in `.dadaia/reports/<context>/<agent>/`; JSON handoffs live in `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`. The document references the delivered report or artifact via `artifact.path` and `artifact.content_hash`.

A v1.2 handoff carries the **`self_pull` audit line** — `self_pull.refs` records the memory atoms the emitting session **actually self-pulled/read** (step0 atoms + any deep atom read during the task), as `specs/`-prefixed context-relative paths (e.g. `specs/memory/architecture.md`). It turns the step0 self-pull discipline into a validator-checkable contract, backed by the role→atom map (`core/role_atom_map.py`). An agent must never list an atom it did not read; the contract is honest-by-construction where mechanical (existence + coverage checks below) and discipline beyond that.

It materializes the symbolic referent `schema_ref: handoff-schema-v1` declared by the topology's agents; the schema lives on disk (`public/schemas/` → staging) and is consumed by CLI + skill.

It resolves the "build-on-stale-layer" pattern identified in the orchestration audit: `input_contract` was declared as verifiable, but the referent pointed at a vacuum. Any handoff can be audited mechanically via `dadaia reports validate <path>` or `dadaia reports validate --all` — with no external dependencies beyond the stdlib.

The contract separates human evidence from machine coordination: HTML reports are for human/panel reading; handoffs are the verifiable state other agents read before QA, review, security, or closure.

## Schema location

  * **Canonical:** `dadaia_workspace/public/schemas/handoff-v1.schema.json` (JSON Schema Draft 2020-12, `$schema = "https://json-schema.org/draft/2020-12/schema"`).
  * **Staging projection:** `.dadaia/agentic/schemas/handoff-v1.schema.json` (generated via `dadaia public stage`). It is the logical path CLI + skill consume at runtime.
  * **NOT projected** to `.claude/schemas/`, `.codex/schemas/`, `.pi/schemas/` — the schema is consumed only by the Python CLI, not by the agents' runtime. Decision A1 saved 3 duplications.
  * **Asset type:** `schemas` is one of the asset types in `_COPY_DIRS` in `dadaia_workspace/infrastructure/public_assets_common.py`. The live list of asset types is documented in [[public-asset-distribution]] (the constitution does not enumerate asset types).



The field contract's single source of truth is the schema file itself: `dadaia_workspace/public/schemas/handoff-v1.schema.json` (the filename names the v1 **family**; `$id`/`title` are `handoff-v1.2`). One-line summary: required top-level fields are `schema_version` (enum `"handoff-v1"` | `"handoff-v1.1"` | `"handoff-v1.2"`), `agent`, `context`, `produced_at`, `artifact` (requires only `type`; `path` is optional and workspace-relative — `content_hash` must accompany it when present), `scope`, `metrics`; `findings[]` is OPTIONAL (each finding item requires `severity`, `message`, `detail_md`, `fix_recommendation`); `self_pull` is schema-optional (`{"refs": [...]}`, `minItems: 1`, no-traversal item pattern) — its **version-conditional requirement lives in the service layer** (the stdlib validator has no `if`/`then`, so the schema declares only the shape). Absolute paths and parent traversal are rejected; the top-level object is `additionalProperties: false` (while `metrics` accepts arbitrary keys).

**Transition posture:** historical `handoff-v1`/`handoff-v1.1` documents on disk stay valid forever — the enum accepts all three tokens and the `self_pull` requirement applies to v1.2 only. New emissions are v1.2; the **only sanctioned v1.1 emission** is the honest zero-refs fallback (a session/run that genuinely read zero memory atoms emits v1.1 with no `self_pull` rather than fabricating a proof).

## CLI


    dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]

  * **Stdlib-only validator** (`infrastructure/stdlib_handoff_validator.py`): `json`, `re`, `datetime.fromisoformat`. Explicit keyword whitelist (`type`, `required`, `enum`, `pattern`, `properties`, `items`, `additionalProperties`, `format`, `minimum`, `minItems`). A schema with a keyword outside the whitelist (`oneOf`, `allOf`, `$ref`) raises `HandoffSchemaError` at init.
  * **Discovery:** `--all` reads `.dadaia/handoff/` by default. Explicit paths remain supported.
  * **v1.2 conditional (service layer):** `ReportsValidationService.validate_file` enforces, after the schema pass, that a `schema_version == "handoff-v1.2"` document carries `self_pull` with a non-empty `refs` array (`HandoffValidationError("self_pull", ...)` on absence); v1/v1.1 documents are exempt. Three mechanical checks on v1.2 refs: (a) **existence** — each ref must resolve to an existing file, order `repos/<context>/<ref>` then `<workspace>/<ref>`, `_within_workspace`-guarded; fail-soft (shape-only) when the workspace root is `None`; (b) **role-map coverage** — when the emitting `agent` has a role→atom mapping (`core/role_atom_map.py` — e.g. `qa-engineer → specs/memory/quality-assurance.md`), the mapped atom's ref must appear in `self_pull.refs`; unmapped agents have no coverage requirement; (c) traversal-carrying refs are rejected by the schema item pattern.
  * **Sidecar version detection:** `cli/commands/reports.py#_detect_sidecar_version` treats `"handoff-v1.2"` (token or `$id`) as modern — a v1.2 sidecar never routes into the v1.0-compat path (which would hard-error on a missing `findings[]`).
  * **Hash:** when `artifact.path` exists, `validate_file()` resolves the artifact inside the workspace and rejects mismatch, missing artifact, or a reference outside the workspace.
  * **`artifact.path` resolution (workspace-rooted):** any **relative** path that exists under the workspace root resolves from the root — covering `repos/<slug>/specs/audits/<UTC>/…` (the auditor's committed channel) and any other workspace-rooted path, not just `.dadaia/…`. The legacy fallback (resolution relative to the handoff's own directory) is kept for paths that only exist there; when a path resolves both ways, **workspace-root wins**. Absolute paths and `..` segments remain rejected by the schema; the `_within_workspace` guard remains.
  * **Exit codes:** `0` = all valid; `1` = any INVALID file (always, regardless of `--strict`) or soft violations under `--strict`; `2` = file not found; `3` = bad invocation (neither PATHS nor `--all`, or workspace not initialized).
  * **Default `--strict=false`**: only SOFT warnings stay non-fatal in non-strict; a schema-invalid handoff is a hard exit-1 failure in any mode. Release gates use QA/security handoffs with coherent `verdict`, `release_id`, `context`, and `agent`.
  * **Composition (constitution L67-compliant):** `cli/commands/reports.py` resolves `ReportsValidationService` via `container.build_reports_validation_service(workspace_root)`; `service.py` does not import `StdlibHandoffValidator` directly — it receives it via the `ValidatorPort` Protocol in `core/protocols/handoff_validator.py`. The service now lives in `features/reports/validation.py`: the former top-level `reports_next` / `reports_retention` / `reports_validation` triplet was merged into one `features/reports/` package with flat `next` / `retention` / `validation` submodules (v0.1.55, behavior-preserving relocation); the `build_reports_*_service` factory names are unchanged (identifiers, not module paths).
  * **Coverage:** 98% scoped in `features/reports.validation` (NFR8 ≥ 80% honored with room to spare).



## Skill: dadaia-handoff-emitter

Standalone skill at `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`, projected to `.agents/skills/` (universal projection — the Codex runtime consumes this dir) and `.claude/skills/`; nothing lands in `.codex/skills/` or `.pi/` (the PI projection carries only the staged `pi/` tree). 3-step protocol:

  1. **sha256sum** of the just-generated HTML report (report mode only).
  2. **Assemble dict** with the required fields — `schema_version: "handoff-v1.2"` + `self_pull.refs` (the atoms actually read; honest v1.1 fallback when zero) — plus the optional fields applicable to the agent, referencing the schema by the logical path `.dadaia/agentic/schemas/handoff-v1.schema.json` (A10 — the skill does not duplicate schema content inside the markdown; single source of truth). The skill's required-fields table and both examples carry `self_pull`.
  3. **Write** the file `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.



Minimal handoff: ~500 bytes (required fields only); typical: <2 KB; warning if >4 KB. For an average 50–70 KB HTML report, overhead is ~3% worst case (NFR5).

## Adoption (15 instruction surfaces)

Every emission-instruction surface carries the v1.2/`self_pull` instruction, pinned by a
file-enumerated contract test (`tests/contract/test_handoff_instruction_adoption.py`, 15
surfaces): the 13 whole files — 12 agent bodies (9 core `public/agents/*.md` + 3 plugin
`public/plugins/*/agents/*.md`) plus `public/data/handoff-AGENTS.md` — and the
`dadaia-handoff-emitter` skill's two JSON examples. The 9 core public agents declare
`dadaia-handoff-emitter` when they produce reports/handoffs that need a machine-readable
sidecar. A roster-completeness assert backs the enumeration, so a renamed or new agent
body fails loudly instead of silently shrinking the contract.

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
