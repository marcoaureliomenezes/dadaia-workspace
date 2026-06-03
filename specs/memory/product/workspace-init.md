---
slug: workspace-init
title: workspace-init
category: product
tldr: porta de entrada; cria .dadaia/, .venv, hooks e estrutura idempotente.
summary: porta de entrada; cria .dadaia/, .venv, hooks e estrutura idempotente.
tags:
- workspace
- init
- setup
- idempotent
agent_tier: self-pull
token_estimate: 413
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia init [--workspace PATH] [--skip-assets]` · Closure: sdd-release-lifecycle-v1

## Propósito

Porta de entrada do produto. Bootstrapa um workspace novo criando a estrutura idempotente em `.dadaia/` (academy, agentic, reports, scripts, states, src), o virtualenv Python (`.venv`), os diretórios de runtime dos quatro tools agentic (`.claude/`, `.agents/`, `.codex/`, `.opencode/`), faz stage+install dos assets canônicos públicos (agentes, skills, workflows, commands, rules, templates, scripts) e configura o hook `UserPromptSubmit` em `.claude/settings.json` para injeção automática de contexto.

É a única feature que pode ser executada em um workspace zero — sem ela, nenhuma outra feature tem onde escrever estado.

## Fluxo de uso

  1. Operador executa `dadaia init` (auto-detecta workspace root procurando `.claude/` ou `.dadaia/` em ancestrais).
  2. CLI cria a árvore idempotente sob `.dadaia/` e tools runtime dirs.
  3. `PythonEnvironmentManager` provisiona o `.venv` Python.
  4. Faz `public stage` e `public install` automáticos (a menos que `--skip-assets`).
  5. Instala `repos.xlsx` catalog em `.dadaia/src/` e o script `.dadaia/scripts/ctx-inject.sh`.
  6. Registra a entrada do hook em `.claude/settings.json`.



## Trigger típico

Primeira execução em um workspace novo, ou após clonar um repositório que ainda não tem `.dadaia/` local.

## Diferencial

Torna o workspace reproduzível desde o primeiro comando — agentes e operador descobrem e usam assets distribuídos (skills, workflows, agents) sem configuração manual em cada máquina nova. Sem init, cada workspace começaria do zero ou exigiria copy-paste manual de configs.

## Estado runtime tocado

  * `.dadaia/states/spec_contexts.json` — contexts list (vazia até primeira criação)
  * `.dadaia/academy/academy.json` — courses list (vazia)
  * `.dadaia/src/repos.xlsx` — catálogo estático de repos conhecidos
  * `.dadaia/scripts/ctx-inject.sh` — hook bash de injeção de contexto
  * `.venv/` — virtualenv Python
  * `.claude/settings.json` — entrada do `UserPromptSubmit` hook



## Dependências

  * Nenhuma feature precede init — é a primeira coisa que roda em um workspace zero.
  * Init dispara internamente `public-asset-distribution` (stage + install) para popular tools runtime dirs.
