---
slug: workspace-portability
title: workspace-portability
category: product
tldr: export/import do workspace inteiro como tar.gz para backup ou migração entre
  máquinas.
summary: export/import do workspace inteiro como tar.gz para backup ou migração entre
  máquinas.
tags:
- portability
- export
- import
- backup
agent_tier: self-pull
token_estimate: 336
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia export [--output DIR] [--include-reports] [--exclude-mnt]` e `dadaia import <archive> [--workspace DEST] [--skip-activate]` · Closure: sdd-release-lifecycle-v1

## Propósito

Empacota e restaura o estado durável do workspace (state files, academy, rules, skills) como `.tar.gz` portável. Secretos (`.env`), caches e `repos/` clonados são excluídos por padrão; reports HTML opt-in via flag.

Restore patches absolute paths para a nova máquina, reativa contexts conforme estavam, e (a menos que `--skip-activate`) re-roda `workspace-init` para reconfigurar hooks.

## Fluxo de uso

  1. `dadaia export` — gera `.dadaia/dist/workspace-<timestamp>.tar.gz` com state + academy + rules + skills.
  2. Operador transporta o arquivo (scp, upload, etc.) para a nova máquina.
  3. Na nova máquina, em um diretório limpo: `dadaia import /path/to/archive.tar.gz`.
  4. Import extrai, faz patch de paths absolutos, restaura contexts e (default) executa init.
  5. Operador valida com `dadaia context list` e `dadaia doctor`.



## Trigger típico

Migração entre máquinas, backup periódico, ou sharing de workspace template para colega/equipe.

## Diferencial

Workspace reprodutível em alguns segundos sem rebuild manual — todas as configurações de contexts, regras, skills e materiais de academy preservadas. Sem essa feature, migrar workspace exigiria reproduzir manualmente dezenas de arquivos em vários runtime dirs.

## Estado runtime tocado

  * Export: cria `.dadaia/dist/<archive>.tar.gz`
  * Import: extrai sobre workspace destino, sobrescreve `.dadaia/states/*`, `.dadaia/academy/`, `.claude/rules/`, `.agents/skills/`
  * Repos clonados NÃO viajam — re-clone via `dadaia context alive` após import



## Dependências

  * Export depende de [[context-management]] (lê `spec_contexts.json`).
  * Import dispara [[workspace-init]] internamente para reconfigurar hooks.
