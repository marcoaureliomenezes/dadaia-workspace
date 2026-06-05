---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "hook PreToolUse (RULE A/B/D/E/C/F) + PostToolUse sdd-post-gate.sh; RULE E resolves session via env → runtime ptr file → non-stale lock → deny (no relaunch). Context semaphore enforces at most one impl+review holder per context."
summary: hook PreToolUse (RULE A/B/D/E/C/F) + PostToolUse sdd-post-gate.sh
  (heartbeat); RULE E resolves session via env var → runtime ptr file
  (`.dadaia/sessions/runtime/<pid>.ptr`) → non-stale lock → deny (env-free,
  no relaunch); RULE C accepts both `- [-] T-xxx` and `- **Status:** [-]` marker
  forms; CONTEXT_SLUG sanitized before path construction (CWE-22); lock glob
  narrowed to exact active-release match.
tags:
- sdd
- gate
- hooks
- enforcement
agent_tier: self-pull
token_estimate: 1700
last_updated: '2026-06-05'
release_origin: v0.1.5
---

Assets: `.dadaia/scripts/sdd-spec-gate.sh` (PreToolUse) · `.dadaia/scripts/sdd-post-gate.sh` (PostToolUse) · Codex also projects `UserPromptSubmit` where supported · Closure: v0.1.5/rc-1

## Propósito

Par de hooks bash que intercepta invocações de ferramentas em Claude Code,
Codex e equivalentes. `sdd-spec-gate.sh` decide **allow** ou **block** antes de
writes; `sdd-post-gate.sh` mantém heartbeat após chamadas de ferramenta. Codex
usa matchers amplos para manter paridade comportamental com Claude Code, e os
scripts decidem se o payload é relevante.

  * **RULE A (memory atomicity):** bloqueia edits em `specs/memory/**/*.md` fora da fase CLOSURE e bloqueia sempre formatos legados `.html`, `.yaml` e `.yml`.
  * **RULE B (archive read-only):** bloqueia qualquer write em `specs/_archive/**`.
  * **RULE D (path-scope):** valida `file_path` contra `paths.write_allowlist` do frontmatter do agente ativo.
  * **RULE E (session + lock enforcement, T-13/T-8 completion):** valida identidade de sessão e ownership do implementation lock. Ver detalhes abaixo.
  * **RULE C (task marker):** exige que exista pelo menos uma task `[-]` em `specs/releases/<active-release-id>/TASKS.md`. Aceita **ambas** as formas de marker: inline `- [-] T-xxx` e canônica `- **Status:** [-]`. Ainda rejeita `[ ]` e `[x]`. Para sessões IMPLEMENTATION-mode, o release ativo é resolvido do lock file — não do `ACTIVE.md` (T-8 completion, ADR D-9).
  * **RULE F (temporary paths):** permite imediatamente writes sob `.dadaia/tmp/` antes das checagens de produção.



Fail-open remains only for internal hook crashes. Write-like tools with no
parseable target path fail closed, and production writes without
`DADAIA_SESSION_ID` fail closed with an orientation message to bind an
implementation session. Temporary paths remain allowed by RULE F.

### RULE E — Session identity resolution

Ordem de resolução da identidade da sessão (a mesma em todos os runtimes):

  1. **`DADAIA_SESSION_ID` env var** — exportado por `eval $(dadaia context bind ...)`. É a chave estável e portável. O gate usa este como primary.
  2. **Runtime ptr file (v0.1.5/rc-1, T-R1-01)** — quando `DADAIA_SESSION_ID` está ausente, o gate lê `.dadaia/sessions/runtime/<pid>.ptr` para o PID do processo atual (escrito por `ctx-inject.sh` no session start e limpo no session end). Isso elimina a necessidade de o operador exportar env vars manualmente entre fases.
  3. **Env-free lock fallback (v0.1.4.5, SCOPE-01)** — quando runtime ptr também está ausente e `CONTEXT_SLUG` é conhecido, o gate itera `.dadaia/locks/implementation/<CONTEXT_SLUG>__<ACTIVE_RELEASE>.json` (glob **narrowed** para o release ativo exato — T-R1-04, elimina não-determinismo multi-lock), adota o `session_id` do primeiro lock **não-stale**, exporta `DADAIA_SESSION_ID` para o restante do run do hook, e prossegue. Locks stale nunca são adotados (fail-safe). Se nenhum lock não-stale existir, bloqueia orientando `dadaia context bind` — **sem necessidade de relaunch**.
  4. **Fail-closed** — sem env var, sem runtime ptr e sem lock não-stale, o gate bloqueia escrita de produção.

**CONTEXT_SLUG sanitization (T-R1-04, CWE-22 hardening):** `CONTEXT_SLUG` é sanitizado (strip de caracteres não-alfanuméricos exceto `-_`) antes de qualquer construção de path no gate. Isso impede path-traversal via nomes de context malformados.

**Durable heartbeat (v0.1.5/rc-1, T-R1-03 + SCOPE-02):** o heartbeat inline do gate renova `last_seen_at` do session file, do implementation lock, **e do context semaphore** (quando presente). Best-effort: falhas de I/O são engolidas; o gate nunca bloqueia por falha no heartbeat.

**Context semaphore (v0.1.5/rc-1, T-R1-02):** per-context semaphore em `.dadaia/states/ctx_locks/<context>.semaphore.json` com campos `owner`, `phase`, `release`, `write_set`, `acquired_at`, `ttl`, `heartbeat`. No máximo um holder ativo (implement+review) por context. `dadaia context bind --mode implementation` adquire o semaphore; uma segunda tentativa é negada com o holder identificado no erro. Sessões read/spec nunca são bloqueadas pelo semaphore. `dadaia doctor` detecta semaphores orphan/stale/duplicate. Limitação conhecida: liveness reclaim (PID morto, session file ausente) só acontece no TTL (300 s); sem `doctor --fix` para semaphore ainda — ver [[semaphore-no-liveness-reclaim]] em `specs/bugs/`.

O `session_id` nativo do stdin payload do Claude Code é usado apenas para correlation logging, não como chave de identidade.

### Path-policy matrix por modo de sessão

Modo de sessão| Código produção (`repos/<slug>/`)| `specs/memory/**`| `releases/<id>/SPEC.md` (impl lock HELD)| `releases/<id>/TASKS.md`| `.dadaia/reports/**`
---|---|---|---|---|---
Sem sessão| BLOCK para código produção; `.dadaia/tmp/**` allowed| BLOCK| BLOCK| BLOCK| Allowed
READ| BLOCK| BLOCK| BLOCK| BLOCK| Allowed
SPEC| BLOCK| Allowed| BLOCK (R-9)| BLOCK (R-9)| Allowed
IMPLEMENTATION (owns lock)| Allowed| Allowed| BLOCK (read-only once impl started)| Allowed| Allowed
IMPLEMENTATION (não owns lock)| BLOCK| Allowed| BLOCK| BLOCK| Allowed
BOUND_REVIEW (mesmo context/release)| BLOCK (read-only)| BLOCK (read-only)| BLOCK (read-only)| BLOCK| Allowed

**R-9 (SPEC §T-13):** quando um impl lock está HELD para context/release X, sessões SPEC-mode são bloqueadas de escrever em `releases/X/SPEC.md` e `releases/X/PLAN.md` — o contrato não muda sob os pés do implementador.

**T-8 completion (ADR D-9):** para sessões IMPLEMENTATION-mode, o release ativo é resolvido do lock file (`.dadaia/locks/implementation/<ctx>__<release>.json`), não do `ACTIVE.md`. Isso garante que o gate valida a TASKS.md correta mesmo quando `ACTIVE.md` já apontou para outra release.

## Fluxo de uso

  1. Agente invoca uma tool de escrita (ex. `Write` em `dadaia_workspace/foo.py`).
  2. Claude Code (ou Codex/OpenCode) executa o hook `sdd-spec-gate.sh` passando JSON em stdin com tool_name + file_path.
  3. O gate resolve `WORKSPACE_ROOT`, context/specs path, `releases/ACTIVE.md` para phase, e `DADAIA_SESSION_ID` do env. Para Codex `apply_patch`, extrai o target path dos headers `*** Add/Update/Delete File:`.
  4. Aplica regras A, B, D, E, C nessa ordem. A primeira regra que decida block-or-allow encerra o gate.
  5. Allow → exit 0 (silencioso); Block → STDOUT JSON `{"decision":"block","reason":"..."}` com mensagem orientada e owner session_id quando relevante.
  6. Após o allow (PostToolUse), `sdd-post-gate.sh` renova `last_seen_at` do Lock 3 atomicamente (`tmp → os.replace()`) e appenda evento HEARTBEAT em `lock-events.jsonl`.
  7. Logs em `/tmp/sdd-gate.log` registram cada decisão com timestamp, tool, path, release-id e motivo.



```mermaid
sequenceDiagram
    participant T as Tool Write/Edit
    participant PreH as PreToolUse Hook
    participant G as sdd-spec-gate.sh
    participant A as releases/ACTIVE.md
    participant S as .dadaia/sessions/sess_*.json
    participant P as .dadaia/sessions/runtime/<pid>.ptr
    participant SEM as .dadaia/states/ctx_locks/<ctx>.semaphore.json
    participant L as .dadaia/locks/implementation/
    participant K as releases/<id>/TASKS.md
    participant PostH as PostToolUse Hook
    participant PG as sdd-post-gate.sh
    T->>PreH: file_path
    PreH->>G: stdin JSON
    G->>A: read phase
    G->>G: RULE A: memory/* + phase≠CLOSURE → block
    G->>G: RULE B: _archive/* → block
    G->>G: RULE D: path-scope allowlist check + CONTEXT_SLUG sanitize
    G->>S: read session (DADAIA_SESSION_ID env var)
    alt DADAIA_SESSION_ID set
        G->>G: check staleness (last_seen_at + TTL)
        G->>SEM: check semaphore (holder, phase, TTL)
        G->>L: read impl lock (if IMPLEMENTATION mode)
        G->>G: RULE E: path-policy matrix
        alt allowed
            G->>K: grep [-] marker RULE C (both forms)
            alt task [-] found
                G-->>PreH: exit 0 (allow)
            else
                G-->>PreH: {block: nenhuma task [-]}
            end
        else blocked
            G-->>PreH: {block: reason + owner session_id}
        end
    else DADAIA_SESSION_ID absent
        G->>P: read runtime ptr for current PID (T-R1-01)
        alt ptr file found
            G->>G: adopt session_id from ptr; export DADAIA_SESSION_ID
            G->>G: RULE E: path-policy matrix (same checks)
            alt allowed
                G->>K: grep [-] marker RULE C
                alt task [-] found
                    G-->>PreH: exit 0 (allow)
                else
                    G-->>PreH: {block: nenhuma task [-]}
                end
            else blocked
                G-->>PreH: {block: reason}
            end
        else no ptr file
            G->>L: scan context__<active_release>.json for non-stale lock (SCOPE-01 narrow glob, T-R1-04)
            alt non-stale lock found
                G->>G: adopt session_id; export DADAIA_SESSION_ID
                G->>G: RULE E: path-policy matrix
                alt allowed
                    G->>K: grep [-] marker RULE C
                    alt task [-] found
                        G-->>PreH: exit 0 (allow)
                    else
                        G-->>PreH: {block: nenhuma task [-]}
                    end
                else blocked
                    G-->>PreH: {block: reason}
                end
            else no non-stale lock
                G-->>PreH: block; orient to dadaia context bind (no relaunch needed)
            end
        end
    end
    PreH-->>T: allow/block
    T->>PostH: tool completed
    PostH->>PG: DADAIA_SESSION_ID
    PG->>S: renew last_seen_at (atomic tmp→replace)
    PG->>L: renew lock last_seen_at (T-R1-03 dual heartbeat)
    PG->>SEM: renew semaphore heartbeat (T-R1-03)
    PG->>L: append HEARTBEAT to lock-events.jsonl
```

## Trigger típico

Automaticamente invocado a cada Write/Edit/MultiEdit em sessões de agente (PreToolUse) e após cada tool call (PostToolUse para heartbeat). Operador raramente interage diretamente — só quando recebe um `{"decision":"block"}` que precisa ser entendido e resolvido (ex: session STALE, lock não próprio).

## Diferencial

Sem este gate, agentes podem escrever em qualquer lugar a qualquer momento — memory vira changelog, archive ganha edits acidentais, dois agentes editam a mesma release simultaneamente (R-8), um agente muda a SPEC enquanto outro a lê (R-9). O gate é a camada mecânica do tripé de atomicidade: junto com o contrato product-engineer e o doctor post-hoc, torna o modelo release-lifecycle não apenas documentado mas enforceável em runtime. O PostToolUse heartbeat garante que locks são liberados automaticamente por TTL quando uma sessão crasheia, evitando o bloqueio permanente (R-10).

## Estado runtime tocado

  * Read-only pelo PreToolUse gate: `releases/ACTIVE.md`, `releases/<active-id>/TASKS.md`, `.dadaia/sessions/<sess_*>.json`, `.dadaia/sessions/runtime/<pid>.ptr` (runtime ptr lookup, T-R1-01), `.dadaia/locks/implementation/<ctx>__<release>.json` (glob narrowed, T-R1-04), `.dadaia/states/ctx_locks/<ctx>.semaphore.json` (semaphore check, T-R1-02). Em modo legado (`SDD_LEGACY_FEATURES=1`): também `features/*/TASKS.md`.
  * Write pelo PreToolUse gate (inline heartbeat): `.dadaia/sessions/<sess_*>.json` (`last_seen_at`, renovado atomicamente); `.dadaia/locks/implementation/<ctx>__<release>.json` (`last_seen_at`); `.dadaia/states/ctx_locks/<ctx>.semaphore.json` (`heartbeat`, T-R1-03). Best-effort — falhas engolidas.
  * Write pelo `ctx-inject.sh` (session start/end): `.dadaia/sessions/runtime/<pid>.ptr` criado no start; removido no end (T-R1-01).
  * Write pelo PostToolUse gate (`sdd-post-gate.sh`): `.dadaia/sessions/<sess_*>.json` (`last_seen_at`); `.dadaia/logs/lock-events.jsonl` (append HEARTBEAT event).
  * Write: `/tmp/sdd-gate.log` (append-only audit log do gate).
  * Saída: STDOUT JSON quando bloqueia; exit 0 (silencioso) quando permite.



**Removido em v2:** o gate não lê mais o marcador global de contexto legado. `DADAIA_CONTEXT` é metadado contextual, não fallback de autorização. Não há first-ALIVE nem workspace-scan fallback para autorização de escrita. A resolução env-free adicionada em v0.1.4.5 (SCOPE-01) adota o `session_id` de um **lock de implementação não-stale em disco** — isso é diferente de um workspace-scan; requer que `dadaia context bind --mode implementation` tenha sido executado previamente de qualquer shell.

## Dependências

  * Depende de [[context-management]] (`DADAIA_SESSION_ID` exportado por `eval $(dadaia context bind ...)`; Lock 3 files criados por bind).
  * Depende de [[agent-orchestration]] indiretamente (releases ativas geradas pelo product-engineer durante orchestration).
  * Projetado para `.dadaia/scripts/` via [[public-asset-distribution]].
  * Variáveis de ambiente: `WORKSPACE_ROOT` (override), `DADAIA_CONTEXT` (context resolution), `DADAIA_SESSION_ID` (identidade de sessão), `DADAIA_MODE` (modo de bind), `SDD_LEGACY_FEATURES` (habilita fallback para features/*).



### Hook injection por runtime

Runtime| PreToolUse| PostToolUse| Observação
---|---|---|---
Claude Code| `.claude/settings.json hooks.PreToolUse[*]`| `hooks.PostToolUse[*]`| Shell script direto; ambos instalados via `dadaia public install --target claude`
Codex| `.codex/hooks.json` `PreToolUse` matcher for `apply_patch`/`Edit`/`Write`| `PostToolUse` same write matcher| Shell script direto; `UserPromptSubmit` injects JSON additional context via `DADAIA_HOOK_OUTPUT=codex-json`; instalado via `dadaia public install --target codex`
OpenCode| Plugin TS `sdd-gate.ts` (`tool.execute.before`)| Inline no path allow do pre-gate (fallback OQ-3)| OpenCode não suporta shell post-hook separado; heartbeat inlineado no exit path do sdd-spec-gate.sh; doctor reporta `[unsupported]` para PostToolUse target opencode — esperado.
