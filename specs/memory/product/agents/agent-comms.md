---
slug: agent-comms
title: agent-comms — Handoff Contract v1
category: product
tldr: 'handoff-v1.1 separa reports HTML de handoffs JSON em .dadaia/handoff/.'
summary: 'contrato handoff-v1.1 separa evidência humana de coordenação entre agentes:
  reports HTML em .dadaia/reports/<context>/<agent>/ e handoffs JSON em
  .dadaia/handoff/<context>/. O CLI valida schema e hash de artifact.path dentro
  do workspace; reports next e o gate QA/security consomem a raiz canônica.'
tags:
- agent-comms
- handoff
- schema
agent_tier: self-pull
token_estimate: 1230
last_updated: '2026-06-04'
release_origin: v0.1.4.3
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
  * **NÃO projetado** para `.claude/schemas/`, `.codex/schemas/`, `.opencode/schemas/` — schema é consumido apenas pela CLI Python, não pelo runtime dos agentes. Decisão A1 economizou 3 duplicações.
  * **Asset type novo:** `schemas` foi adicionado a `_COPY_DIRS` em `dadaia_workspace/infrastructure/public_assets.py`. Constitution L124 (originalmente target L106 da SPEC FR6) enumera os 10 tipos suportados: _rules, skills, commands, scripts, agents, templates, workflows, plugins, data, schemas_.



Required fields: `schema_version` (literal `"handoff-v1.1"`), `agent`, `context`, `produced_at` (ISO 8601 via `format: date-time`), `scope`, `metrics`, `artifact{type,content_hash}`, and `findings[]`. Optional: `artifact.path`, `release_id`, `decisions_required[]`, `next_handoff`, `verdict`, `verdict_reason`. `artifact.path` is workspace-relative when present; absolute paths and parent traversal are rejected. `additionalProperties: false` em todos os objetos.

## CLI


    dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]

  * **Validator stdlib-only** (~85 LoC em `infrastructure/stdlib_handoff_validator.py`): `json`, `re`, `datetime.fromisoformat`. Whitelist explícita de keywords (`type`, `required`, `enum`, `pattern`, `properties`, `items`, `additionalProperties`, `format`, `minimum`, `minItems`). Schema com keyword fora do whitelist (`oneOf`, `allOf`, `$ref`) levanta `HandoffSchemaError` no init.
  * **Discovery:** `--all` lê `.dadaia/handoff/` por padrão. Paths explícitos continuam suportados.
  * **Hash:** quando `artifact.path` existe, `validate_file()` resolve o artefato dentro do workspace e reprova mismatch, artefato ausente ou referência fora do workspace.
  * **Exit codes:** `0` = todos válidos (ou violations em non-strict); `1` = violation em strict; `2` = file not found; `3` = bad invocation (sem PATHS nem `--all`, ou workspace não inicializado).
  * **Default`--strict=false`**: violations aparecem como warning em non-strict. Gates de release usam handoffs QA/security com `verdict`, `release_id`, `context` e `agent` coerentes.
  * **Composição (constitution L67-compliant):** `cli/commands/reports.py` resolve `ReportsValidationService` via `container.build_reports_validation_service(workspace_root)`; `service.py` não importa `StdlibHandoffValidator` direto — recebe via `ValidatorPort` Protocol em `core/protocols/handoff_validator.py`.
  * **Coverage:** 98% scoped em `features/reports_validation` (NFR8 ≥ 80% honrado com folga).



## Skill: dadaia-handoff-emitter

Skill standalone em `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`, projetada para `.agents/skills/`, `.claude/`, `.codex/`, `.opencode/` via mecanismo padrão de assets. Protocolo em 3 passos:

  1. **sha256sum** do report HTML acabado de gerar.
  2. **Assemble dict** com campos obrigatórios + opcionais aplicáveis ao agente, referenciando o schema por path lógico `.dadaia/agentic/schemas/handoff-v1.schema.json` (A10 — skill não duplica conteúdo do schema dentro do markdown; single source of truth).
  3. **Write** o arquivo `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.



Handoff mínimo: ~500 bytes (apenas obrigatórios); típico: <2 KB; warning se >4 KB. Para report HTML médio de 50–70 KB, overhead ~3% no pior caso (NFR5).

## Adoção (15 de 15 agentes)

Os agentes públicos default declaram `dadaia-handoff-emitter` quando produzem
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

## Fora de escopo (deferido a backlog)

Itens explicitamente deferidos em SPEC §"Out-of-scope" e promovidos como candidatas no [backlog/candidates.md](../../backlog/candidates.md):

  * `reports-next-cli` — `dadaia reports next` (v2): descobre próximo handoff esperado dado o estado atual do workspace.
  * `reports-mcp-server` — MCP integration (v3): emissão programática via servidor MCP em vez de skill markdown.
  * `reports-evaluator` — Evaluator semântico (v4): valida qualidade de findings, não apenas estrutura JSON.
  * `agent-comms-wave-2` — Migrar `qa-engineer` para piloto (próxima onda).
  * `agent-comms-wave-3-7` — Migrar `devops-engineer`, `backend-engineer`, `frontend-engineer`, e 3 `game-*` (waves separadas).
  * `reports-ci-gate` — Job `dadaia reports validate --all --strict` em `.github/workflows/ci.yml` após 100% adoção (NFR4).
  * `reports-hash-mismatch-enforcement` — Promover hash-mismatch de warning para erro em strict (v2).
  * `spec-discovery-chain-workflow` — Workflow seed para o padrão D4 (PE→architect→SE→PE→SE), se virar recorrente (Q6).
  * `reports-handoff-schema-v2` — Evolução do schema para suportar `oneOf` e `$ref` (requer upgrade do validator).



## Referência

  * Release id: `agent-comms-v1` arquivada em `specs/_archive/releases/agent-comms-v1/` (SPEC + PLAN + TASKS + CLOSURE).
  * Dependência: [[public-asset-distribution]] — chain `public/` → `.dadaia/agentic/` → projeções multi-tool propaga o novo asset type `schemas`.
  * Constitution L17–28 (tech-stack) **não tocada** — NFR3 honra zero novas dependências de runtime (validator stdlib-only).
  * Constitution L124 (originalmente L106 no SPEC FR6 — file growth shifted line) enumera os 10 asset types canônicos.
  * ADR-006 (dual ownership de `public/agents/*.md`): SE owns frontmatter YAML, PE owns markdown body.
  * ADR-007 (procedure for constitution update in release): FR explícito + verification triple + operator confirmation via SPEC approval + doctor verde pós-patch.
  * Auditoria precedente que motivou a release: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-15-orchestration-audit.md`.
