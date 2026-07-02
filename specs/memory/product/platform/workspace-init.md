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
token_estimate: 786
last_updated: '2026-07-01'
release_origin: v0.1.47
---

CLI surface: `dadaia init [--workspace PATH] [--skip-assets]` · Closure: sdd-release-lifecycle-v1

## Propósito

Porta de entrada do produto. Bootstrapa um workspace novo criando a estrutura idempotente em `.dadaia/` (academy, agentic, reports, scripts, states, src), o virtualenv Python (`.venv`), e os diretórios de runtime **`.claude/`, `.agents/skills/`, `.codex/`** — `.pi/` NÃO é criado pelo init: ele chega inteiro via `dadaia public install --target pi|all` (com `--skip-assets`, `.pi/` fica ausente até um install manual). Sem `--skip-assets`, o init faz stage+install dos assets canônicos públicos (agents, skills, rules, workflows, scripts, templates, schemas, data, personas, lifecycle_fragments, pi) e configura os hooks de governança em `.claude/settings.json` e `.codex/hooks.json`.

Os hooks de governança são o pacote Python `dadaia_workspace/hooks/` (8 módulos: `__init__`, `_common`, `pre_gate`, `sdd_gate`, `root_whitelist`, `venv_guard`, `ctx_inject`, `sdd_post_gate`), funcionando em Windows, macOS e Linux sem Git Bash ou WSL. Registro por runtime via `infrastructure/runtime_config.py`: no Claude, comandos `python -m dadaia_workspace.hooks.<name>`; no Codex, **wrappers executáveis self-locating** `.dadaia/hooks/codex-{pre-gate,post-gate,ctx-inject,ctx-inject-session-start}` referenciados em `.codex/hooks.json` (Codex direct-execs strings de hook — o wrapper resolve o venv Python relativo ao próprio path). O PreToolUse é UM único comando (`pre_gate`: root-whitelist → venv-guard → SDD gate, first-block-wins). Os git chokepoints (pre-commit lease gate + pre-push CI/security gate) são instalados separadamente por `dadaia ci install-hook`.

`workspace/service.py` reconhece tanto o caminho antigo (`.sh`) quanto o novo comando Python para evitar dupla-registro durante workspaces migrados. O script bash `ctx-inject.sh` existe em `.dadaia/scripts/` como artefato legado, mas não é mais o mecanismo de hook registrado.

É a única feature que pode ser executada em um workspace zero — sem ela, nenhuma outra feature tem onde escrever estado.

## Fluxo de uso

  1. Operador executa `dadaia init` (sem `--workspace`: walks up from cwd looking for the sentinel `.dadaia/states/spec_contexts.json` — a bare `.dadaia/` dir without `states/` is skipped as sub-repo/partial init — falling back to cwd when none is found; with `--workspace <dir>`, that dir is authoritative, no ancestor walk — `core/workspace_resolver.py`).
  2. CLI cria a árvore idempotente sob `.dadaia/` e os runtime dirs `.claude/`, `.agents/skills/`, `.codex/` (`.pi/` vem do public install).
  3. `PythonEnvironmentManager` provisiona o `.venv` Python usando `PLATFORM.venv_scripts_dir` e `PLATFORM.venv_exe_suffix` para paths cross-platform.
  4. Faz `public stage` e `public install` automáticos (a menos que `--skip-assets`).
  5. Instala `repos.xlsx` catalog em `.dadaia/src/`.
  6. Registra as entradas de hook: `.claude/settings.json` com comando Python; `.codex/hooks.json` apontando para os wrappers `.dadaia/hooks/codex-*` — PreToolUse único via `pre_gate`.



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
  * `.claude/settings.json` — entradas de hook: `UserPromptSubmit` → `python -m dadaia_workspace.hooks.ctx_inject`; `PreToolUse` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`) → `python -m dadaia_workspace.hooks.pre_gate` (comando único); `PostToolUse` (matcher `*`) → `python -m dadaia_workspace.hooks.sdd_post_gate`
  * `.codex/hooks.json` — mesmas entradas em formato Codex via os wrappers self-locating `.dadaia/hooks/codex-*` (PreToolUse matcher `^(apply_patch|Edit|Write|Bash)$` → `codex-pre-gate`; PostToolUse sem matcher; ctx-inject em `SessionStart` matcher `startup|resume` + `UserPromptSubmit`)



## Dependências

  * Nenhuma feature precede init — é a primeira coisa que roda em um workspace zero.
  * Init dispara internamente `public-asset-distribution` (stage + install) para popular tools runtime dirs.
