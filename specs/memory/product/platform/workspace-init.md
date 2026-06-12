---
slug: workspace-init
title: workspace-init
category: product
tldr: porta de entrada; cria .dadaia/, .venv, Python governance hooks e estrutura idempotente.
summary: porta de entrada; cria .dadaia/, .venv, Python governance hooks e estrutura
  idempotente; PreToolUse registrado como UM comando Python (python -m
  dadaia_workspace.hooks.pre_gate), não bash; ctx-inject.sh retido apenas como
  fallback não-instalado.
tags:
- workspace
- init
- setup
- idempotent
agent_tier: self-pull
token_estimate: 620
last_updated: '2026-06-12'
release_origin: v0.1.14
---

CLI surface: `dadaia init [--workspace PATH] [--skip-assets]` · Closure: sdd-release-lifecycle-v1

## Propósito

Porta de entrada do produto. Bootstrapa um workspace novo criando a estrutura idempotente em `.dadaia/` (academy, agentic, reports, scripts, states, src), o virtualenv Python (`.venv`), os diretórios de runtime dos quatro tools agentic (`.claude/`, `.agents/`, `.codex/`, `.opencode/`), faz stage+install dos assets canônicos públicos (agentes, skills, workflows, commands, rules, templates, scripts) e configura os hooks de governança em `.claude/settings.json` e `.codex/hooks.json`.

Os hooks de governança são registrados como **comandos Python** (`python -m dadaia_workspace.hooks.<name>`) via `infrastructure/runtime_config.py`. Não há dependência de bash para os hooks de SDD — o pacote `dadaia_workspace/hooks/` (8 módulos: `__init__`, `_common`, `pre_gate`, `sdd_gate`, `root_whitelist`, `venv_guard`, `ctx_inject`, `sdd_post_gate`) provê os hooks em Python puro, funcionando em Windows, macOS e Linux sem Git Bash ou WSL. O PreToolUse é UM único comando (`pre_gate`, que avalia root-whitelist → venv-guard → SDD gate, first-block-wins). Os git chokepoints (pre-commit lease gate + pre-push CI/security gate) são instalados separadamente por `dadaia ci install-hook`.

`workspace/service.py` reconhece tanto o caminho antigo (`.sh`) quanto o novo comando Python para evitar dupla-registro durante workspaces migrados. O script bash `ctx-inject.sh` existe em `.dadaia/scripts/` como artefato legado, mas não é mais o mecanismo de hook registrado.

É a única feature que pode ser executada em um workspace zero — sem ela, nenhuma outra feature tem onde escrever estado.

## Fluxo de uso

  1. Operador executa `dadaia init` (auto-detecta workspace root procurando `.claude/` ou `.dadaia/` em ancestrais).
  2. CLI cria a árvore idempotente sob `.dadaia/` e tools runtime dirs.
  3. `PythonEnvironmentManager` provisiona o `.venv` Python usando `PLATFORM.venv_scripts_dir` e `PLATFORM.venv_exe_suffix` para paths cross-platform.
  4. Faz `public stage` e `public install` automáticos (a menos que `--skip-assets`).
  5. Instala `repos.xlsx` catalog em `.dadaia/src/`.
  6. Registra as entradas de hook em `.claude/settings.json` e `.codex/hooks.json` com comando Python (`python -m dadaia_workspace.hooks.<name>`), não bash — PreToolUse único via `pre_gate`.



## Trigger típico

Primeira execução em um workspace novo, ou após clonar um repositório que ainda não tem `.dadaia/` local.

## Diferencial

Torna o workspace reproduzível desde o primeiro comando — agentes e operador descobrem e usam assets distribuídos (skills, workflows, agents) sem configuração manual em cada máquina nova. Sem init, cada workspace começaria do zero ou exigiria copy-paste manual de configs.

## Estado runtime tocado

  * `.dadaia/states/spec_contexts.json` — contexts list (vazia até primeira criação)
  * `.dadaia/academy/academy.json` — courses list (vazia)
  * `.dadaia/src/repos.xlsx` — catálogo estático de repos conhecidos
  * `.dadaia/scripts/ctx-inject.sh` — script bash legado (ainda presente; não é mais o hook registrado)
  * `.venv/` — virtualenv Python (caminho do executor resolvido por `PLATFORM.venv_scripts_dir`/`PLATFORM.venv_exe_suffix`)
  * `.claude/settings.json` — entradas de hook: `UserPromptSubmit` → `python -m dadaia_workspace.hooks.ctx_inject`; `PreToolUse` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`) → `python -m dadaia_workspace.hooks.pre_gate` (comando único); `PostToolUse` → `python -m dadaia_workspace.hooks.sdd_post_gate`
  * `.codex/hooks.json` — mesmas entradas em formato Codex (PreToolUse matcher `^(apply_patch|Edit|Write|Bash)$` → `pre_gate`)



## Dependências

  * Nenhuma feature precede init — é a primeira coisa que roda em um workspace zero.
  * Init dispara internamente `public-asset-distribution` (stage + install) para popular tools runtime dirs.
