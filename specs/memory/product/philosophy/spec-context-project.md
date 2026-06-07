---
slug: spec-context-project
title: spec-context-project
category: product
tldr: The keystone concept — one canonical specs folder + one repo, session-bindable, enabling safe parallel multi-project work (constitution §0).
summary: Defines the Spec Context Project — the central organizing unit of dadaia-workspace.
  One canonical specs folder bound to one repository. Session binding triggers the
  bind→inject→enforce→parallel-multi-project value chain that lets a generic agent
  fleet build real projects safely and concurrently. Constitution §0 is the single
  source of truth for this concept.
tags:
- spec-context
- sdd
- lifecycle
- concurrency
agent_tier: self-pull
token_estimate: 700
last_updated: '2026-06-06'
release_origin: v0.2.0
---

## Propósito

O **Spec Context Project** é o conceito central do dadaia-workspace. Constitution §0 define-o como the single unit through which the workspace's purpose is delivered. Tudo o mais na constitution — o lock model (§8), o roster de agentes (§14), a lifecycle gate sequence (§7), o coordinator + sub-agent topology (§9) — é maquinaria a serviço deste conceito.

Um Spec Context Project é **uma canonical specs folder bound to one repository**. A specs folder segue um pattern fixo (`backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, mais `constitution.md` e `AGENTS.md`); o repository é o código que as specs governam.

## Fluxo de uso

O binding de um Spec Context Project a uma terminal session dispara a cadeia de valor:

1. **Bind** — a sessão se anexa a um Spec Context Project. O operador executa `eval $(dadaia context bind <name>)`, que exporta `DADAIA_CONTEXT`, `DADAIA_SESSION_ID`, e `DADAIA_MODE` para o shell da sessão.

2. **Inject** — o binding injeta a `constitution.md` do contexto e sua `memory/` na sessão por **lazy product-feature consumption**: `tech-stack.md` e `catalog.json` carregam up front (~2.400 tokens); feature atoms individuais são pulled on demand pelo agente conforme relevantes à tarefa. Nenhuma sessão paga pelo catálogo inteiro antecipadamente.

3. **Enforce** — o SDD lifecycle (constitution §7) é enforced para cada production write sob aquele contexto: nenhuma mudança de produção sem release aprovado e task reservada. O gate `sdd-spec-gate.sh` verifica ativo-context + lease + task marker `[-]` antes de cada write.

4. **Parallel multi-project** — porque cada contexto carrega exatamente um MUTATING lease (§8), múltiplos Spec Context Projects podem ser trabalhados concorrentemente em sessões diferentes. Trabalho ADDITIVE (backlog, bugs, research, audit, review) dentro de qualquer contexto roda em paralelo — sem colisão, porque o lock contract torna structuralmente impossível ter mais de um MUTATING writer por contexto ao mesmo tempo.

## Trigger típico

Quando o operador ou o project-manager inicia trabalho num projeto: `dadaia context bind <name>` em um novo terminal. Cada projeto ativo roda em seu próprio terminal — o binding é o ato de declarar "esta sessão trabalha neste contexto". Para trabalho ADDITIVE (reports, handoffs, audits), o binding é opcional; o gate permite esses writes unconditionally.

## Diferencial

Sem o Spec Context Project como unidade central, um generic agent fleet teria que re-derivar como trabalhar a cada sessão, não teria memória de produto persistente, não teria lifecycle enforcement, e colidiria em projetos paralelos. O Spec Context Project é o que transforma um generic fleet em uma disciplined, parallel, multi-project software team:

- **Context engineering sem re-derivação:** constitution + memory são injetados automaticamente; os agentes nunca começam às cegas.
- **SDD enforcement mecânico:** o gate bloqueia writes fora de scope — não é uma convenção, é um PreToolUse hook.
- **Paralelismo seguro:** a single-lease-per-context invariant (§8) garante exclusividade estrutural para writers MUTATING; writers ADDITIVE correm concorrentemente por design.

## Estado runtime tocado

  * `.dadaia/states/spec_contexts.json` — registry de todos os Spec Context Projects (`schema_version: "2"`; state ALIVE/DEAD).
  * `.dadaia/states/ctx_locks/<ctx>.lock.json` — single-record JSON TTL-lease para o contexto (adquirido no primeiro write MUTATING da sessão).
  * `.dadaia/sessions/runtime/<ctx>.ptr` — stable-session-identity pointer (D1 soul-fold).
  * `specs/memory/**` — memory canônica do contexto (architecture.md, tech-stack.md, product/).
  * `specs/releases/ACTIVE.md` — release ativa do contexto.

## Dependências

  * [[context-management]] — gerencia o ALIVE/DEAD lifecycle e o session binding.
  * [[sdd-gate-v3]] — enforce o SDD contract a cada production write.
  * [[agent-orchestration]] — coordina os agentes que trabalham dentro do contexto.
  * [[public-asset-distribution]] — projeta a canonical surface para todos os runtimes que servem o contexto.
  * Constitution §0 é a single source of truth para a definição e filosofia deste conceito — este atom cita, não duplica.
