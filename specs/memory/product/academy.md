---
slug: academy
title: academy
category: product
tldr: sistema de cursos copy-from-template para onboarding de contribuidores e agentes.
summary: sistema de cursos copy-from-template para onboarding de contribuidores e
  agentes.
tags:
- academy
- onboarding
- courses
agent_tier: self-pull
token_estimate: 660
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia academy {modules|list|create|update|delete}` · Panel: `Academy` tab at `http://127.0.0.1:4999/#academy` · Closure: dadaia-workspace-panel-r5-v1 · 2026-05-21

## Propósito

Sistema interno de cursos para onboarding e estudo. O operador escolhe um módulo built-in da knowledge basis (ex. `01_foundations`, `02_intermediate`) e gera um curso copy-from-template em `.dadaia/academy/<slug>/`, registrado no índice `academy.json`.

O acesso primário ao Academy é via a **aba Academy do panel** (`http://127.0.0.1:4999/#academy`): a aba lista todos os cursos criados como cards (type chip + título + description + "Open →" CTA) e renderiza o conteúdo do módulo inline ao clicar. A CLI (`dadaia academy`) permanece como superfície de gestão (criar, atualizar, deletar cursos) e é pré-condição para que a aba exiba conteúdo.

Útil para acelerar onboarding de novos contribuidores (humanos) ou produzir material de referência estruturado que agentes podem consultar.

**Nota:** os módulos da knowledge basis (arquivos 01–06) ainda não foram criados — seu conteúdo é pendente de uma release subsequente. A infraestrutura (API, DI, aba no panel) está pronta; a aba exibe empty state "No academy modules available" até que módulos sejam criados via `dadaia academy create`.

## Fluxo de uso

  1. `dadaia academy modules` — lista os módulos disponíveis na knowledge basis (numerados).
  2. `dadaia academy create "my-course" --module 1` — copia o módulo 1 para `.dadaia/academy/my-course/` e registra em `academy.json`.
  3. `dadaia academy list` — mostra os cursos criados com slug, nome, módulo e created_at.
  4. `dadaia panel` → aba **Academy** : carrega `GET /api/academy` e renderiza cards. Clicar em um card exibe o HTML do módulo inline com breadcrumb `[← Back to Academy]`.
  5. `dadaia academy update my-course --module 2` — muda o módulo associado (CLI).
  6. `dadaia academy delete my-course` — remove curso do índice (arquivos do disco podem permanecer).



## Trigger típico

Onboarding de novo contribuidor ou agente; criação de material de referência estruturado. O operador abre o panel e acessa a aba Academy para navegar os módulos disponíveis sem sair da janela.

## Diferencial

Templated learning — acelera onboarding oferecendo conhecimento estruturado em vez de documentação dispersa. Cada curso é uma pasta versionável que pode ser editada pelo operador. A integração como aba no panel elimina a necessidade de sair da janela de controle para consultar conteúdo de onboarding.

## Estado runtime tocado

  * `.dadaia/academy/academy.json` — índice de cursos (lido por `AcademyService.list_all()`; escrito por CLI `dadaia academy create/update/delete`).
  * `.dadaia/academy/<slug>/` — diretório do curso (copiado do template pela CLI; lido pelo panel para renderizar conteúdo).
  * `GET /api/academy` — endpoint bearer-only no panel que chama `AcademyService.list_all()` e serializa a lista; retorna `[]` com 200 quando `service.academy is None` (DI not wired) ou quando não existem cursos.



## Dependências

  * Depende de [[workspace-init]] (cria `academy.json` e instala módulos via `public-asset-distribution`).
  * [[panel]]: `AcademyService` é injetado como DI opcional em `PanelService(academy=None)` no composition root de `panel.py`. A aba Academy no panel consome `GET /api/academy` via `academy.js`, que regista o módulo via `window.Panel.register('academy', Academy)` e usa `window.authedFetch` e `window.escHtml` (globais de `core.js`).
