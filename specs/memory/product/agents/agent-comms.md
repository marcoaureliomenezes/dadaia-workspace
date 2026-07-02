---
slug: agent-comms
title: agent-comms — Handoff Contract v1
category: product
tldr: 'handoff-v1.1 separa reports HTML de handoffs JSON em .dadaia/handoff/.'
summary: 'contrato handoff-v1.1 separa evidência humana de coordenação entre agentes:
  reports HTML em .dadaia/reports/<context>/<agent>/ e handoffs JSON em
  .dadaia/handoff/<context>/. O CLI valida schema e hash de artifact.path dentro
  do workspace — qualquer path relativo existente sob o root resolve
  workspace-rooted (incl. repos/<slug>/specs/audits), com fallback legacy
  handoff-dir; reports next e o gate QA/security consomem a raiz canônica.'
tags:
- agent-comms
- handoff
- schema
agent_tier: self-pull
token_estimate: 1200
last_updated: '2026-07-01'
release_origin: v0.1.47
---

CLI surface: `dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]` · `dadaia reports lint [DIR]` · `dadaia reports next [--context <ctx>] [--json]`

## O que é

O **handoff-v1** é o contrato JSON estruturado que cada agente especialista emite para coordenação entre agentes. Reports HTML permanecem em `.dadaia/reports/<context>/<agent>/`; handoffs JSON vivem em `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`. O documento referencia o report ou artefato entregue via `artifact.path` e `artifact.content_hash`.

Materializa o referente simbólico `schema_ref: handoff-schema-v1` declarado pelos agentes da topologia; o schema vive em disco (`public/schemas/` → staging) e é consumido por CLI + skill.

Resolve o pattern "build-on-stale-layer" identificado na auditoria de orquestração: `input_contract` era declarado como verificável, mas o referente apontava para vácuo. Qualquer handoff pode ser auditado mecanicamente via `dadaia reports validate <path>` ou `dadaia reports validate --all` — sem dependências externas além da stdlib.

O contrato separa evidência humana de coordenação máquina: HTML reports são para leitura humana/painel; handoffs são o estado verificável que outros agentes leem antes de QA, review, security ou closure.

## Schema location

  * **Canonical:** `dadaia_workspace/public/schemas/handoff-v1.schema.json` (JSON Schema Draft 2020-12, `$schema = "https://json-schema.org/draft/2020-12/schema"`).
  * **Staging projection:** `.dadaia/agentic/schemas/handoff-v1.schema.json` (gerado via `dadaia public stage`). É o path lógico que CLI + skill consomem em runtime.
  * **NÃO projetado** para `.claude/schemas/`, `.codex/schemas/`, `.pi/schemas/` — schema é consumido apenas pela CLI Python, não pelo runtime dos agentes. Decisão A1 economizou 3 duplicações.
  * **Asset type:** `schemas` é um dos asset types de `_COPY_DIRS` em `dadaia_workspace/infrastructure/public_assets_common.py`. A lista viva de asset types é documentada em [[public-asset-distribution]] (a constitution não enumera asset types).



The field contract's single source of truth is the schema file itself: `dadaia_workspace/public/schemas/handoff-v1.schema.json`. One-line summary: required top-level fields are `schema_version` (enum `"handoff-v1"` | `"handoff-v1.1"`), `agent`, `context`, `produced_at`, `artifact` (requires only `type`; `path` is optional and workspace-relative — `content_hash` must accompany it when present), `scope`, `metrics`; `findings[]` is OPTIONAL (each finding item requires `severity`, `message`, `detail_md`, `fix_recommendation`). Absolute paths and parent traversal are rejected; the top-level object is `additionalProperties: false` (while `metrics` accepts arbitrary keys).

## CLI


    dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]

  * **Validator stdlib-only** (`infrastructure/stdlib_handoff_validator.py`): `json`, `re`, `datetime.fromisoformat`. Whitelist explícita de keywords (`type`, `required`, `enum`, `pattern`, `properties`, `items`, `additionalProperties`, `format`, `minimum`, `minItems`). Schema com keyword fora do whitelist (`oneOf`, `allOf`, `$ref`) levanta `HandoffSchemaError` no init.
  * **Discovery:** `--all` lê `.dadaia/handoff/` por padrão. Paths explícitos continuam suportados.
  * **Hash:** quando `artifact.path` existe, `validate_file()` resolve o artefato dentro do workspace e reprova mismatch, artefato ausente ou referência fora do workspace.
  * **Resolução de `artifact.path` (workspace-rooted):** qualquer path **relativo** que exista sob o workspace root resolve a partir do root — cobre `repos/<slug>/specs/audits/<UTC>/…` (o canal committado do auditor) e qualquer outro path workspace-rooted, não só `.dadaia/…`. O fallback legacy (resolução relativa ao diretório do próprio handoff) é mantido para paths que só existem lá; quando um path resolve das duas formas, **workspace-root vence**. Paths absolutos e segmentos `..` continuam rejeitados pelo schema; o guard `_within_workspace` permanece.
  * **Exit codes:** `0` = todos válidos (ou violations em non-strict); `1` = violation em strict; `2` = file not found; `3` = bad invocation (sem PATHS nem `--all`, ou workspace não inicializado).
  * **Default`--strict=false`**: violations aparecem como warning em non-strict. Gates de release usam handoffs QA/security com `verdict`, `release_id`, `context` e `agent` coerentes.
  * **Composição (constitution L67-compliant):** `cli/commands/reports.py` resolve `ReportsValidationService` via `container.build_reports_validation_service(workspace_root)`; `service.py` não importa `StdlibHandoffValidator` direto — recebe via `ValidatorPort` Protocol em `core/protocols/handoff_validator.py`.
  * **Coverage:** 98% scoped em `features/reports_validation` (NFR8 ≥ 80% honrado com folga).



## Skill: dadaia-handoff-emitter

Skill standalone em `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`, projetada para `.agents/skills/` (universal projection — the Codex runtime consumes this dir) e `.claude/skills/`; nothing lands in `.codex/skills/` or `.pi/` (the PI projection carries only the staged `pi/` tree). Protocolo em 3 passos:

  1. **sha256sum** do report HTML acabado de gerar.
  2. **Assemble dict** com campos obrigatórios + opcionais aplicáveis ao agente, referenciando o schema por path lógico `.dadaia/agentic/schemas/handoff-v1.schema.json` (A10 — skill não duplica conteúdo do schema dentro do markdown; single source of truth).
  3. **Write** o arquivo `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.



Handoff mínimo: ~500 bytes (apenas obrigatórios); típico: <2 KB; warning se >4 KB. Para report HTML médio de 50–70 KB, overhead ~3% no pior caso (NFR5).

## Adoção (9 agentes core)

Os 9 agentes públicos core declaram `dadaia-handoff-emitter` quando produzem
reports/handoffs que precisam de sidecar machine-readable. Optional packs podem
adotar o mesmo contrato, mas não fazem parte da topologia pública default.

```mermaid
flowchart LR
    AG[Agente piloto] -->|gera| HTML[report HTML]
    AG -->|invoca| SKILL[dadaia-handoff-emitter SKILL]
    SKILL -->|sha256sum| HASH[content_hash]
    SKILL -->|monta dict| DOC[HandoffDocument]
    SKILL -->|Write| JSON[.dadaia/handoff/context/file.handoff.json]
    JSON -.artifact.path.- HTML
    CLI[dadaia reports validate] -->|read| JSON
    CLI -->|read| SCHEMA[.dadaia/agentic/schemas/handoff-v1.schema.json]
    CLI -->|stdlib-only| VAL[StdlibHandoffValidator]
    VAL -->|0 ok / 1 strict / 2 nf / 3 bad| EXIT[exit code]
```

## Dependências

  * [[public-asset-distribution]] — chain `public/` → `.dadaia/agentic/` → projeções multi-tool propaga o asset type `schemas`.
