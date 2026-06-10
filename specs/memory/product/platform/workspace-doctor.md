---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: diagnóstico + repair de invariantes do workspace state com --fix opcional; emite LOCK-NEW, INV-4, INV-5, SENTINEL-GC, PTR-GC.
summary: diagnóstico + repair de invariantes do workspace state com --fix opcional.
  Cobre context ALIVE/DEAD (INV-4, INV-5), TTL-lease stale/inválido (LOCK-NEW),
  orphan sentinel files (SENTINEL-GC) e orphan .ptr files (PTR-GC). Invariantes
  SEM-1 e Lock-3 foram removidos em v0.1.6. Os antigos LEASE-1..4 não existem no
  código — os códigos reais são LOCK-NEW (doctor.py:300), INV-4 (doctor.py:376),
  INV-5 (doctor.py:389), SENTINEL-GC e PTR-GC (doctor.py:558-593, sem código nomeado no output).
tags:
- workspace
- doctor
- health
- repair
agent_tier: self-pull
token_estimate: 700
last_updated: '2026-06-09'
release_origin: v0.1.9
---

CLI surface: `dadaia doctor [--fix]`

## Propósito

Valida invariantes do estado do workspace — consistência de `spec_contexts.json` (schema v2: ALIVE/DEAD, sem flag global de contexto), presença de arquivos esperados em `.dadaia/`, estado das branches dos repos clonados em `repos/`, e saúde do TTL-lease. Quando passado `--fix`, aplica reparos automáticos para issues marcados como fixable.

### Invariantes de estado de context (INV-4, INV-5)

Com o modelo v2 (ALIVE/DEAD), dois invariantes cobrem o ciclo de vida do context:

  * **INV-4:** context com `state=ALIVE` e repo ausente em `repos/` → WARN; sugestão: `dadaia context alive <name>`.
  * **INV-5:** context com `state=DEAD` e repo presente em `repos/` → WARN; sugestão: `dadaia context dead <name>` ou remover manualmente.

Os antigos INV-1, INV-2, INV-3, INV-6 (guards do marcador global de contexto legado) foram removidos em v2.

### Verificações de lock/lease (v0.1.6+)

O TTL-lease usa um single-record JSON por context em `.dadaia/states/ctx_locks/<ctx>.lock.json`. O doctor verifica:

| Código | O que detecta | Auto-fix |
|--------|---------------|----------|
| `LOCK-NEW` | `.lock.json` com JSON inválido, campos obrigatórios ausentes, ou `heartbeat` stale (TTL 120s excedido) — `_check_lease_records`, `doctor.py:300` | AUTO-FIX (`--fix`): deleta o `.lock.json` stale ou inválido. |
| `INV-4` | Context com `state=ALIVE` e repo ausente em `repos/` — `doctor.py:376` | Manual: `dadaia context alive <name>`. |
| `INV-5` | Context com `state=DEAD` e repo presente em `repos/` — `doctor.py:389` | AUTO-FIX: `dadaia context dead <name>` ou remoção manual. |
| `SENTINEL-GC` | Orphan `.lock.sentinel` com mtime > 30s (processo morreu entre CAS e unlink) — `doctor.py:558–593`, sem código nomeado no output | AUTO-FIX (`--fix`): deleta o sentinel. |
| `PTR-GC` | Orphan `.ptr` file em `.dadaia/sessions/runtime/` para um context sem `.lock.json` ou com lease expirado — `doctor.py:572–592` | AUTO-FIX (`--fix`): deleta o `.ptr`. |

Mensagens de `LOCK-NEW` incluem: `context`, `session_id` do holder, e `heartbeat` — informação suficiente para diagnóstico sem instrução de reclaim manual.

## Fluxo de uso

  1. `dadaia doctor` — executa checklist de invariantes (INV-4, INV-5, LOCK-NEW, SENTINEL-GC, PTR-GC) e lista issues com flag `[fixable]` ou `[manual]`.
  2. Operador inspeciona os issues; se todos forem `[fixable]`, roda `dadaia doctor --fix`.
  3. Doctor aplica os reparos e mostra a lista de ações realizadas.
  4. Re-rodar `dadaia doctor` deve retornar "All invariants OK".

## Trigger típico

Após crash de sessão de agente (verificar se leases STALE existem), após upgrade da versão do dadaia-workspace (garantir schema v2), antes de demos, ou quando o gate bloqueia com mensagem de lease STALE/conflict.

## Diferencial

Sem este guardrail, leases de implementação abandonados (crash de sessão) bloqueariam futuros writers indefinidamente. O invariante `LOCK-NEW` detecta e deleta esses leases órfãos ou stale; o operador é informado com evidência em vez de ter que editar JSON manualmente. `SENTINEL-GC` garante que orphan sentinels (processo morto entre O_EXCL CAS e unlink) não causem bloqueio permanente.

## Estado runtime tocado

  * Leitura: `.dadaia/states/spec_contexts.json`, `.dadaia/states/ctx_locks/*.lock.json`, `.dadaia/states/ctx_locks/*.lock.sentinel`, `.dadaia/sessions/runtime/*.ptr`, `repos/`.
  * Escrita (apenas com `--fix`): correções em lock files, sentinel files, ptr files; appends em `.dadaia/logs/lock-events.jsonl`.

## Dependências

  * Standalone. Não depende de nenhuma outra feature além da estrutura criada por [[workspace-init]].
  * Complementar a [[specs-doctor]] (este valida workspace runtime state; specs-doctor valida estrutura SDD).
  * Relacionado a [[context-management]] — os lock files que doctor inspeciona são criados pelo acquire inline do gate.
