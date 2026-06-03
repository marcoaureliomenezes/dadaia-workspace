---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: diagnóstico + repair de invariantes do workspace state com --fix opcional.
summary: diagnóstico + repair de invariantes do workspace state com --fix opcional.
tags:
- workspace
- doctor
- health
- repair
agent_tier: self-pull
token_estimate: 779
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

CLI surface: `dadaia doctor [--fix]` · Closure: spec-context-session-locks-v1

## Propósito

Valida invariantes do estado do workspace — consistência de `spec_contexts.json` (schema v2: ALIVE/DEAD, sem `is_primary`), presença de arquivos esperados em `.dadaia/`, estado das branches dos repos clonados em `repos/`, e saúde dos lock files de implementação. Quando passado `--fix`, aplica reparos automáticos para issues marcados como fixable.

### Invariantes de estado de context (INV-4, INV-5)

Com o modelo v2 (ALIVE/DEAD), dois invariantes cobrem o ciclo de vida do context:

  * **INV-4:** context com `state=ALIVE` e repo ausente em `repos/` → WARN; sugestão: `dadaia context alive <name>`.
  * **INV-5:** context com `state=DEAD` e repo presente em `repos/` → WARN; sugestão: `dadaia context dead <name>` ou remover manualmente.



Os antigos INV-1, INV-2, INV-3, INV-6 (guards de `is_primary` e `primary_context.json`) foram removidos em v2. Não existem mais checks de "primary flag duplicado" ou "primary context sem arquivo" — o conceito de primary context global foi eliminado pelo modelo de session binding.

### Invariantes de lock (LOCK-1..LOCK-6)

Invariante| O que detecta| Auto-fix  
---|---|---  
LOCK-1| Dois arquivos `.json` para o mesmo par `<ctx>__<release>` em `.dadaia/locks/implementation/`| Mantém o mais recente por `last_seen_at`; renomeia os outros com sufixo `.conflicted`; appenda audit record; requer revisão humana.  
LOCK-2| Implementation lock existe para um context com `state=DEAD`| AUTO-FIX: deleta o lock file; appenda audit record. Context permanece DEAD.  
LOCK-3| Lock HELD com `last_seen_at` mais antigo que `ttl_seconds` (default 300 s)| Atualiza campo `state` para STALE; NÃO deleta. Reclaim requer comando explícito do operador (`dadaia context bind --force --reason ...`).  
LOCK-4| Mutação de arquivo de produção em `lock-events.jsonl` sem campo `task_id`| NO AUTO-FIX: reporta; bloqueia CLOSURE até reconciliação.  
LOCK-5| `lock-events.jsonl` contém evento `BLOCKED_ATTEMPT` (sessão não-owner tentou escrever)| NO AUTO-FIX: sinaliza como audit signal no report do doctor; nenhuma ação automática.  
LOCK-6| Session file `BOUND_REVIEW` em `.dadaia/sessions/` pertence a um context com `state=DEAD`| AUTO-FIX: deleta o session file; appenda audit record. Estende cobertura do LOCK-2 para review sessions.  
  
Mensagens de erro para locks STALE ou bloqueios de gate incluem: runtime do owner, session ID, e `last_seen_at` — para o operador decidir sobre reclaim.

## Fluxo de uso

  1. `dadaia doctor` — executa checklist de invariantes (INV-4, INV-5, LOCK-1..6) e lista issues com flag `[fixable]` ou `[manual]`.
  2. Operador inspeciona os issues; se todos forem `[fixable]`, roda `dadaia doctor --fix`.
  3. Doctor aplica os reparos e mostra a lista de ações realizadas.
  4. Re-rodar `dadaia doctor` deve retornar "All invariants OK".



## Trigger típico

Após crash de sessão de agente (verificar se locks STALE existem), após upgrade da versão do dadaia-workspace (garantir schema v2), antes de demos, ou quando o gate bloqueia com mensagem de lock STALE/conflito.

## Diferencial

Sem este guardrail, locks de implementação abandonados (crash de sessão) bloqueariam futuros binders indefinidamente (R-10). Os invariantes LOCK-3 e LOCK-6 detectam e marcam como STALE esses locks orpfãos; o operador reclaim com evidência em vez de editar JSON manualmente. LOCK-2 e LOCK-6 limpam automaticamente locks e sessions de contexts mortos (DEAD), mantendo o estado de `.dadaia/locks/` e `.dadaia/sessions/` consistente com o estado real dos contexts.

## Estado runtime tocado

  * Leitura: `.dadaia/states/spec_contexts.json`, `.dadaia/locks/implementation/*.json`, `.dadaia/sessions/*.json`, `.dadaia/logs/lock-events.jsonl`, `repos/`.
  * Escrita (apenas com `--fix`): correções em lock files, session files, e `spec_contexts.json`; appends em `lock-events.jsonl`.



## Dependências

  * Standalone. Não depende de nenhuma outra feature além da estrutura criada por [[workspace-init]].
  * Complementar a [[specs-doctor]] (este valida workspace runtime state; specs-doctor valida estrutura SDD).
  * Relacionado a [[context-management]] — os lock files que doctor inspeciona são criados pelo context bind/release flow.
