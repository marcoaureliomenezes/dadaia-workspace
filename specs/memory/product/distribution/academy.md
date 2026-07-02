---
slug: academy
title: academy
category: product
tldr: knowledge_basis navegável na aba Academy do panel + gestão copy-from-template via CLI.
summary: a aba Academy do panel navega diretamente os módulos da knowledge_basis
  (GET /api/academy lista todos os módulos com títulos e contagem de lições; rota
  read-only traversal-guarded GET /academy/<module>/<lesson> renderiza a lição em
  Markdown). A CLI copy-from-template (dadaia academy create/update/delete)
  permanece como superfície de gestão de cursos derivados.
tags:
- academy
- onboarding
- courses
agent_tier: self-pull
token_estimate: 660
last_updated: '2026-06-12'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia academy {modules|list|create|update|delete}` · Panel: `Academy` tab at `http://127.0.0.1:4999/#academy` · Closure: dadaia-workspace-panel-r5-v1 · 2026-05-21

## Propósito

Sistema interno de cursos para onboarding e estudo, com duas superfícies:

1. **Browsing direto da knowledge_basis (acesso primário).** A aba Academy do panel
   (`http://127.0.0.1:4999/#academy`) lista TODOS os módulos shipped em
   `dadaia_workspace/features/academy/knowledge_basis/` via `GET /api/academy`
   (títulos + contagem de lições). Clicar em um módulo expande suas lições; clicar em
   uma lição renderiza o Markdown no panel via a rota read-only
   `GET /academy/<module>/<lesson>` — traversal-guarded (single-segment +
   `Path.resolve()` + `is_relative_to`). Nenhum `dadaia academy create` é
   pré-condição para a aba ter conteúdo.
2. **Gestão copy-from-template (CLI).** `dadaia academy create` copia um módulo da
   knowledge basis para `.dadaia/academy/<slug>/`, registrado no índice
   `academy.json`; update/delete gerenciam esses cursos derivados.

O módulo `07_codex` é um curso completo em inglês sobre o runtime Codex
(README + lições numeradas + exercises + example + references), com fatos
live-verificados do contrato Codex anotados por evidence-level.

Útil para acelerar onboarding de novos contribuidores (humanos) ou produzir material de referência estruturado que agentes podem consultar.

## Fluxo de uso

  1. `dadaia panel` → aba **Academy** : `GET /api/academy` lista todos os módulos da knowledge_basis com título e contagem de lições.
  2. Clicar em um módulo expande a lista de lições; clicar em uma lição carrega `GET /academy/<module>/<lesson>` e renderiza o Markdown inline com breadcrumb `[← Back to Academy]`.
  3. `dadaia academy modules` — lista os módulos disponíveis na knowledge basis (numerados) via CLI.
  4. `dadaia academy create "my-course" --module 1` — copia o módulo 1 para `.dadaia/academy/my-course/` e registra em `academy.json`.
  5. `dadaia academy list` / `update` / `delete` — gestão dos cursos derivados via CLI.



## Trigger típico

Onboarding de novo contribuidor ou agente; criação de material de referência estruturado. O operador abre o panel e acessa a aba Academy para navegar os módulos disponíveis sem sair da janela.

## Diferencial

Templated learning — acelera onboarding oferecendo conhecimento estruturado em vez de documentação dispersa. Cada curso é uma pasta versionável que pode ser editada pelo operador. A integração como aba no panel elimina a necessidade de sair da janela de controle para consultar conteúdo de onboarding.

## Estado runtime tocado

  * `dadaia_workspace/features/academy/knowledge_basis/<NN_module>/` — fonte read-only dos módulos shipped (lida por `GET /api/academy` para o catálogo e por `GET /academy/<module>/<lesson>` para o conteúdo; render via `views/_md_render.py`).
  * `.dadaia/academy/academy.json` — índice de cursos derivados (lido por `AcademyService.list_all()`; escrito por CLI `dadaia academy create/update/delete`).
  * `.dadaia/academy/<slug>/` — diretório do curso copy-from-template (copiado pela CLI).
  * `GET /api/academy` — lista os módulos da knowledge_basis (títulos + lesson counts).
  * `GET /academy/<module>/<lesson>` — rota read-only traversal-guarded (single-segment + resolve + `is_relative_to`) que renderiza a lição Markdown.



## Dependências

  * Depende de [[workspace-init]] (cria `academy.json` e instala módulos via `public-asset-distribution`).
  * [[panel]]: `AcademyService` é injetado como DI opcional em `PanelService(academy=None)` no composition root de `panel.py`. A aba Academy no panel consome `GET /api/academy` via `academy.js`, que regista o módulo via `window.Panel.register('academy', Academy)` e usa `window.authedFetch` e `window.escHtml` (globais de `core.js`; `authedFetch` is a residual name — it is a thin alias of plain `fetch` that sends NO credential, per the panel's no-auth model).
