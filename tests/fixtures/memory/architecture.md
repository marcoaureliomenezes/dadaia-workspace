---
slug: architecture
title: Arquitetura
category: core
tldr: Visão geral das camadas e contratos do dadaia-workspace.
summary: Define as camadas (features, infrastructure, CLI), regras de dependência e contratos entre componentes.
tags: [architecture, layers, contracts]
agent_tier: self-pull
token_estimate: 420
last_updated: "2026-06-01"
release_origin: memory-markdown-source-v1
---

## Propósito

O dadaia-workspace é uma biblioteca Python que provê a infraestrutura de agentes, specs, e painel de controle.

Referência cruzada: ver [[tech-stack]] para detalhes do stack e [[panel]] para o painel.

## Fluxo de uso

Cada release passa por fases: SPEC → PLAN → TASKS → IMPLEMENTATION → CLOSURE.

| Fase | Responsável | Artefato |
|------|-------------|---------|
| SPEC | product-engineer | SPEC.md |
| PLAN | product-engineer | PLAN.md |
| TASKS | software-engineer | TASKS.md |

## Estado runtime tocado

- `specs/releases/ACTIVE.md` — release ativa
- `.dadaia/states/primary_context.json` — contexto primário

## Dependências

Dependências principais:

- `typer` — CLI framework
- `jinja2` — template engine
- `pyyaml` — YAML parsing

## Diagrama de dependências

```mermaid
graph LR
  CLI --> Features
  Features --> Infrastructure
  Infrastructure --> External[External APIs]
```

## Diagrama de fluxo SDD

```mermaid
sequenceDiagram
  PE->>Tasks: flip [ ] to [-]
  SE->>Code: implement
  SE->>Tasks: flip [-] to [x]
```
