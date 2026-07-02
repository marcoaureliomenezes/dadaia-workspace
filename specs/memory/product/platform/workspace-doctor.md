---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: 'diagnóstico + repair do workspace state; checks LOCK-NEW/LOCK-GC/LOCK-4/5/CTX-URL-1/INV-4/5/ROOT-1..4/VENV-1; --fix roda SENTINEL/PTR/GRAVEYARD-GC.'
summary: >-
  diagnóstico + repair de invariantes do workspace state com --fix opcional.
  Checks emitidos: context ALIVE/DEAD (INV-4, INV-5), TTL-lease inválido (LOCK-NEW),
  lease stale de holder morto/unprobeable (LOCK-GC — nunca reclama pid vivo),
  production-write sem task_id no audit log (LOCK-4), BLOCKED_ATTEMPT no audit log
  (LOCK-5, sinal), context ALIVE com repo_url vazio (CTX-URL-1), root whitelist +
  caches proibidos + tool configs + subdirs de .dadaia/ (ROOT-1..4), saúde do venv
  (VENV-1). Ações fix-only (aparecem só no --fix, não como issues): SENTINEL-GC,
  PTR-GC, GRAVEYARD-GC. Bind/session records decaem por TTL contra last_seen_at
  heartbeat-renovado. Limitação conhecida: o comando sai 0 mesmo com issues.
tags:
- workspace
- doctor
- health
- repair
agent_tier: self-pull
token_estimate: 1000
last_updated: '2026-07-01'
release_origin: v0.1.47
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
| `LOCK-NEW` | `.lock.json` com JSON inválido ou campos obrigatórios ausentes — `_check_lease_records` | AUTO-FIX (`--fix`): deleta o `.lock.json` inválido. |
| `LOCK-GC` | Lease TTL-expirado cujo holder está **morto** (pid probe, injetado no composition root via `container`) ou é **unprobeable** (record pré-`pid` ⇒ TTL-only reclaimable) | AUTO-FIX (`--fix`): reclaim (deleta o record). Um holder com pid **vivo** NUNCA é reclaimed, mesmo past-TTL (invariante no-steal). |
| `CTX-URL-1` | Context com `state=ALIVE` e `repo_url` vazio no record (context não-portável) | Manual: `dadaia context update <name> --url <url>` — ou back-fill automático em `alive`/`dead` quando o repo on-disk tem origin. |
| `INV-4` | Context com `state=ALIVE` e repo ausente em `repos/` | Manual: `dadaia context alive <name>`. |
| `INV-5` | Context com `state=DEAD` e repo presente em `repos/` | AUTO-FIX: `dadaia context dead <name>` ou remoção manual. |
| `LOCK-4` | Evento de production-write em `lock-events.jsonl` sem campo `task_id` | Manual (sinal de disciplina). |
| `LOCK-5` | Evento `BLOCKED_ATTEMPT` em `lock-events.jsonl` | Manual (sinal — surfaced, sem fix). |
| `ROOT-1` | Entrada de top-level no workspace root fora do whitelist (+ `root_exceptions.txt`) | Manual. |
| `ROOT-2` | Cache/output proibido no root (ex. `.pytest_cache/`, `coverage/`) | Manual. |
| `ROOT-3` | Tool config fora do home canônico e fora da exception list (WARN) | Manual. |
| `ROOT-4` | Subdir desconhecido de top-level dentro de `.dadaia/` (allowlist inclui `hooks/`) | Manual. |
| `VENV-1` | Saúde do venv do workspace: `.dadaia/.venv` ausente, `bin/dadaia` ausente ou não-executável, ou interpreter incoerente com o venv do workspace (complementa o venv-guard do hook `pre_gate`) | Manual: recriar/reparar o venv (`dadaia init` ou provisionamento do `.dadaia/.venv`). |

**Ações fix-only** (executadas por `--fix`, não emitidas como issues do `check()`):
`SENTINEL-GC` (deleta orphan `.lock.sentinel` com mtime > 30s), `PTR-GC` (deleta orphan
`.ptr` em `.dadaia/sessions/runtime/` sem lease vivo) e `GRAVEYARD-GC` (deleta session
files expirados).

Bind/session records (`.dadaia/sessions/<id>.json`) são coletados por TTL medido contra
`last_seen_at`, que o heartbeat PostToolUse renova a cada tool use — um bind de sessão
ativa nunca decai; record sem `last_seen_at` mantém TTL-from-creation; o pid do record
(bind-CLI, morto por construção) não é consultado.

Mensagens de `LOCK-NEW`/`LOCK-GC` incluem `context`, `session_id` do holder e
`heartbeat`; a mensagem de `LOCK-GC` **nomeia as remediações** (`dadaia doctor --fix`
ou `dadaia lock steal <ctx>`) para um lease stale-dead seguro de reclamar.

**Limitação conhecida:** `dadaia doctor` imprime as issues mas **sai com exit 0 mesmo
quando há issues** (só sai non-zero quando o workspace não está inicializado) — não
serve como gate mecânico em pipelines sem parsing do output.

## Fluxo de uso

  1. `dadaia doctor` — executa checklist de invariantes (LOCK-NEW, LOCK-GC, LOCK-4, LOCK-5, CTX-URL-1, INV-4, INV-5, ROOT-1..4, VENV-1) e lista issues com flag `[fixable]` ou `[manual]`.
  2. Operador inspeciona os issues; se todos forem `[fixable]`, roda `dadaia doctor --fix`.
  3. Doctor aplica os reparos e mostra a lista de ações realizadas.
  4. Re-rodar `dadaia doctor` deve retornar "All invariants OK".

## Trigger típico

Após crash de sessão de agente (verificar se leases STALE existem), após upgrade da versão do dadaia-workspace (garantir schema v2), antes de demos, ou quando o gate bloqueia com mensagem de lease STALE/conflict.

## Diferencial

Sem este guardrail, leases de implementação abandonados (crash de sessão) bloqueariam futuros writers indefinidamente e ficariam permanentemente irrecuperáveis (records pré-`pid` eram un-reclaimable até v0.1.10). `LOCK-GC` reclama esses leases com segurança — o pid probe garante que um holder vivo nunca é roubado; `LOCK-NEW` deleta records inválidos; o operador é informado com evidência em vez de ter que editar JSON manualmente. `SENTINEL-GC` garante que orphan sentinels (processo morto entre O_EXCL CAS e unlink) não causem bloqueio permanente. `CTX-URL-1` impede contexts ALIVE não-portáveis (URL vazia) de falharem silenciosamente num export/import.

## Estado runtime tocado

  * Leitura: `.dadaia/states/spec_contexts.json`, `.dadaia/states/ctx_locks/*.lock.json`, `.dadaia/states/ctx_locks/*.lock.sentinel`, `.dadaia/sessions/runtime/*.ptr`, `repos/`.
  * Escrita (apenas com `--fix`): correções em lock files, sentinel files, ptr files; appends em `.dadaia/logs/lock-events.jsonl`.

## Dependências

  * Standalone. Não depende de nenhuma outra feature além da estrutura criada por [[workspace-init]].
  * Complementar a [[specs-doctor]] (este valida workspace runtime state; specs-doctor valida estrutura SDD).
  * Relacionado a [[context-management]] — os lock files que doctor inspeciona são criados pelo acquire inline do gate.
