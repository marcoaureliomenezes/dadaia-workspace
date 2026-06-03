---
slug: panel
title: Panel
category: product
tldr: Painel web de controle do dadaia-workspace.
summary: HTTP server Python puro (no frameworks) que serve a UI do workspace com rotas para agentes, specs, memória e Kanban.
tags: [panel, http, ui]
agent_tier: self-pull
token_estimate: 350
last_updated: "2026-06-01"
release_origin: memory-markdown-source-v1
---

## Propósito

O Panel é um servidor HTTP Python puro (sem frameworks) que serve a interface web do workspace.

Veja [[architecture]] para as camadas e [[tech-stack]] para o stack.

## Fluxo de uso

1. Operador executa `dadaia panel start`
2. Panel escuta em `localhost:<port>`
3. Navegador acessa `/` para a interface principal

## Trigger típico

`dadaia panel start --port 8080`

## Diferencial

Servidor HTTP sem dependências externas de framework — apenas `http.server` da stdlib.

## Estado runtime tocado

- Processo do servidor HTTP (PID registrado via `dadaia server register`)
- `specs/releases/ACTIVE.md` — exibida no painel

## Dependências

- `dadaia_workspace/features/panel/handler.py`
- `dadaia_workspace/features/panel/views/`
- `mistune` para renderização de atoms de memória

## Diagrama de rotas

```mermaid
graph LR
  Browser --> Handler
  Handler --> Views[Views: index, agents, memory, kanban]
  Handler --> API[API: /api/*]
  Views --> Specs[specs/]
```
