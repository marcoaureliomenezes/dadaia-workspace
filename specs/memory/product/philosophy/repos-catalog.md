---
slug: repos-catalog
title: repos-catalog
category: product
tldr: lookup do repos.xlsx para discovery rápida de repos conhecidos com slug + URL.
summary: lookup do repos.xlsx para discovery rápida de repos conhecidos com slug +
  URL.
tags:
- repos
- catalog
- discovery
agent_tier: self-pull
token_estimate: 212
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia repos list` · Closure: sdd-release-lifecycle-v1

## Propósito

Consulta o catálogo estático de repos conhecidos em `.dadaia/src/repos.xlsx` e exibe slug, URL, descrição. Serve como discovery rápida para o operador criar novos contexts sem memorizar URLs.

## Fluxo de uso

  1. `dadaia repos list` — mostra tabela com todos os repos do catálogo.
  2. Operador identifica o slug desejado e usa em `dadaia context create <name> --repo <slug>`.
  3. **Programmatic consumer:** `dadaia context create` sem `--url` consulta o catálogo via `ReposService.list_known()` (`cli/commands/context.py` → `container.build_repos_service()`) para back-fill do `repo_url`, falhando gracefully quando o catálogo está ausente; `--url` explícito vence o lookup.
  4. Para atualizar o catálogo: editar manualmente o XLSX (ou regenerar via release dedicada).



## Trigger típico

Quando o operador vai criar um context para um repo que não lembra a URL exata.

## Diferencial

Sem o catálogo, criar context exigia colar URL completa cada vez. O slug curto encurta o caminho e centraliza descoberta.

## Estado runtime tocado

  * Read-only: `.dadaia/src/repos.xlsx`



## Dependências

  * Depende de [[workspace-init]] (instala o XLSX em `.dadaia/src/`).
  * Consumido pela [[context-management]] (operador olha repos list antes de criar context).
