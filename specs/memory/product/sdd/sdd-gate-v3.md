---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "SDD gate: merged pre_gate PreToolUse (root-whitelist→venv-guard→SDD, first-block-wins); git chokepoints pre-commit/pre-push; lease O_EXCL CAS + pid veto."
summary: >-
  Enforcement em duas camadas. (1) Hooks Python: o PreToolUse roda por UM entrypoint
  merged — `dadaia_workspace.hooks.pre_gate` — que lê o stdin uma vez e avalia as
  policies em ordem fixa root-whitelist → venv-guard → SDD gate, first-block-wins,
  cada policy fail-open (PROTECTED é o único caminho fail-closed). O classificador SDD
  é context-relative (ADDITIVE allow sem lease, MEMORY gated por fase, FROZEN block —
  incl. os _archive per-artifact matchados ANTES de ADDITIVE (R-2),
  MUTATING adquire o TTL-lease via O_EXCL CAS com PID veto); apply_patch multi-file
  classifica TODOS os headers (veredito mais restritivo vence); READ é non-acquiring.
  O PostToolUse renova heartbeat via by-session index (sem full scan) e roda o
  reconciler advisory (nunca bloqueia). (2) Chokepoints git: pre-commit lease gate
  (cadeia DP-4, zero-false-block, degradação advisory ALLOW+WARN) e pre-push gate
  mecânico de verdict de security (metrics.commit_sha por sha pushed) — rodam
  independentemente de hooks de harness. Tunables em core/kernel_tunables.py;
  latência de hook em .dadaia/logs/hook-latency.jsonl.
tags:
- sdd
- gate
- hooks
- enforcement
- chokepoints
agent_tier: self-pull
token_estimate: 3250
last_updated: '2026-07-01'
release_origin: v0.1.47
---

Assets: `python -m dadaia_workspace.hooks.pre_gate` (PreToolUse, entrypoint único) · `python -m dadaia_workspace.hooks.sdd_post_gate` (PostToolUse, heartbeat + reconciler advisory) · `python -m dadaia_workspace.hooks.ctx_inject` · git hooks `pre-commit-lease-gate.sh` + `pre-push-ci-gate.sh` (instalados via `dadaia ci install-hook`; backends `dadaia ci pre-commit-check` / `dadaia ci push-gate-check`). Os módulos `sdd_gate` e `root_whitelist` são thin policy modules consumidos por `pre_gate` (`evaluate_payload()`); seus `main()` legados ficam mantidos por uma release.

## Propósito

Enforcement determinístico do lifecycle SDD em duas camadas complementares.

**Camada 1 — hooks de harness (file-write tools + Bash estreito).** Um único
entrypoint PreToolUse (`dadaia_workspace.hooks.pre_gate`) intercepta invocações de
ferramentas em Claude Code e Codex interativo: lê o envelope stdin **uma vez**, e
avalia as policies registradas em ordem fixa, **first-block-wins**:

1. **root-whitelist** — classifica pelo **primeiro componente do path relativo ao
   root**: bloqueia qualquer write cujo primeiro componente criaria uma entrada nova
   de top-level fora do whitelist canônico — inclusive writes ANINHADOS sob um novo
   top-level não-whitelisted (ex. `foo/bar/baz.txt` bloqueia se `foo/` não existe e
   não é whitelisted). Entradas existentes e globs de
   `.dadaia/states/root_exceptions.txt` passam.
2. **venv-guard** (somente eventos Bash) — check estreito de first-token: comandos
   `dadaia`, `pip`/`pip3` ou `python -m dadaia_workspace` não enraizados em
   `.dadaia/.venv/bin/` são bloqueados com o comando corrigido na mensagem.
   pytest/ruff/mypy NÃO são cobertos; `$DADAIA_BIN` e a forma workspace-absolute são
   permitidos. Sem parsing geral de shell — apenas padrões fixos de token inicial.
3. **SDD gate** — a política em `features/spec_context/gate_policy.py`; o hook delega,
   nunca re-deriva.

Allow exige que toda policy permita; cada policy é fail-open (uma policy que crasha
nunca bloqueia o harness); PROTECTED segue o único caminho fail-closed. Um interpreter
spawn por tool call (seed-5: um comando PreToolUse registrado por runtime).

O classificador SDD é **context-relative**: para um path sob `repos/<slug>/...`, o
prefixo `repos/<slug>/` é removido e a taxonomia ordenada `specs/` é aplicada ao
restante — a mesma que governa paths workspace-root. Um restante in-repo sem classe é
MUTATING (nunca UNGATED). Um `apply_patch` multi-file tem **todos** os headers
`*** Add/Update/Delete File:` classificados (`_common.target_paths()`); o veredito
mais restritivo vence — um arquivo FROZEN/PROTECTED/bloqueado bloqueia o patch inteiro.

| Classe | Paths | Decisão |
|--------|-------|---------|
| PROTECTED | `.dadaia/sessions/**` (workspace-root) | Block sempre — único caminho fail-closed (SEC-01); avaliado primeiro |
| FROZEN (R-2: antes de ADDITIVE) | `specs/backlog/_archive/`, `specs/audits/_archive/`, `specs/bugs/_archive/` (root **e** in-repo; trailing `/` load-bearing) | Block sempre para file tools — os `_archive` per-artifact são matchados ANTES dos prefixes ADDITIVE (senão `specs/bugs/` engoliria `specs/bugs/_archive/` como ADDITIVE); moves de archive rodam via `git mv` (Bash), fora do envelope file-tool |
| ADDITIVE | `specs/backlog/**`, `specs/bugs/**`, `specs/audits/**` (root **e** in-repo); `.dadaia/reports/**`, `.dadaia/handoff/**`, `.dadaia/tmp/**` (root) | Allow — zero leitura/escrita de lease |
| MEMORY | `specs/memory/**` (root **e** in-repo) | Allow apenas em fase DEFINITION ou CLOSURE; block caso contrário |
| FROZEN | `specs/_archive/**` (root **e** in-repo) | Block sempre |
| MUTATING | `specs/releases/**`, production tree, e todo in-repo path sem classe | READ-mode ⇒ block non-acquiring; senão acquire do lease (O_EXCL CAS + pid veto); block em live-lease conflict |
| UNGATED | Demais paths workspace-root (ex. fora de specs/.dadaia) | Allow |

**Camada 2 — chokepoints git (envelope que NÃO depende de hook de harness).** Writes
arbitrários via Bash continuam fora do envelope file-tool (o gate nunca parseia
strings de comando shell), mas os desfechos de lifecycle que importam são gated
deterministicamente em git hooks, que rodam mesmo quando nenhum hook de harness
disparou:

- **pre-commit lease gate** — um `git commit` num repo de Spec Context a partir de
  sessão que não segura o MUTATING lease do contexto é bloqueado com mensagem
  acionável. Cadeia de identidade do holder (DP-4): (1) sem lease, ou lease stale com
  holder pid morto ⇒ allow (trabalho ADDITIVE commita livre; zero-false-block);
  (2) `DADAIA_SESSION_ID` igual ao sid do holder ⇒ allow; (3) o pid registrado do
  holder é ancestral do processo invocante — via o port read-only `ProcessAncestry`
  (Linux `/proc` walk; macOS `ps -o ppid=`; Windows Toolhelp32 read-only; NUNCA
  `os.kill`) ⇒ allow; (4) ancestralidade indisponível/indeterminada, **ou holder pid
  morto** (não se pode ser descendente de processo morto — pid-veto canon) ⇒ **ALLOW
  com WARN logado** — zero-false-block domina; o chokepoint degrada para advisory
  nessa plataforma. Block APENAS em lease estrangeiro vivo com non-match positivo.
  Contexto derivado do path do repo, nunca first-ALIVE.
- **pre-push gate** — o mesmo hook pre-push roda o CI preflight E o check mecânico de
  verdict de security: para cada `<local-sha>` non-zero das ref lines do stdin, deve
  existir um handoff `security-reviewer` com `"verdict": "APPROVED"` cujo
  `metrics.commit_sha` seja igual àquele sha (campo canônico único; sem fallback de
  `scope`; nunca `rev-parse HEAD`). Deleções de branch (sha zero) e pushes tag-only
  passam sem verdict; APPROVE stale (sha antigo) não passa; commits nunca são
  review-blocked.
- **reconciler advisory (PostToolUse)** — flagueia paths MUTATING sujos fora de lease
  no repo do contexto bound (evento `RECONCILER_FLAG` em
  `.dadaia/logs/lock-events.jsonl`); NUNCA bloqueia, exit 0 em todos os branches
  (incl. falha de `git status`); throttle por sessão
  (`.dadaia/tmp/reconciler-last-<sid>`, TTL de `kernel_tunables`).
- **Honestidade do escape hatch:** chokepoints são git hooks — `--no-verify` os
  bypassa. A postura é deterministic-at-the-chokepoint, não unbypassable; a coerência
  lease↔session do doctor (SPEC-DOC-029) segue como backstop post-hoc.

**O que NÃO é mecanismo do gate (disciplina de agente/PM):** o gate não lê `TASKS.md`,
não verifica `**Status:** Aprovado`, não verifica markers `[-]`, e não valida
`paths.write_allowlist` de personas. Essas leis são disciplina coordenada
(workspace-protocol, dadaia-task-manager) com verificação post-hoc por reviewers e
`dadaia specs doctor`.

**Regras da policy SDD:**
- **RULE A (memory atomicity):** `specs/memory/**` fora de DEFINITION/CLOSURE → block. O gate classifica apenas por **path**, nunca por formato/extensão.
- **RULE B (archive read-only):** `specs/_archive/**` → block sempre — inclusive in-repo.
- **RULE READ (mode channel):** sessão com modo resolvido READ/BOUND_READ é non-acquiring — write MUTATING bloqueado **antes** de qualquer chamada ao lease; ADDITIVE flui. Resolução de modo: `DADAIA_MODE` env (escape de operador) → `mode` do session record keyed pelo sid harness-native → modo do **incumbent do contexto** (`sessions/runtime/<ctx>.ptr`, atualizado pelo `bind`; ignorado se um lease vivo nomeia outro sid, anti-downgrade guard) → default `IMPLEMENTATION`.
- **PROTECTED (SEC-01):** `.dadaia/sessions/**` é CLI-owned; block incondicional protege o `.ptr` de forgery.

Fail-open permanece para crashes internos do hook e para MUTATING sem contexto
resolvível; PROTECTED é a única classe fail-closed.

**ctx-inject com atribuição de sessão:** o hook `ctx_inject` (mesmo pacote) honra um
bind-epoch marker (`.dadaia/states/bind_epoch/<ctx>`) apenas quando o **pid gravado no
conteúdo do marker** — escrito por `dadaia context bind` com o pid do harness de vida
longa — casa com o harness pid do próprio hook. Um bind de outra sessão nunca rouba a
injeção desta; marker vazio/legado é não-atribuível ⇒ ignorado (preflight genérico,
nunca o contexto de outra sessão). Mecânica de bind/injeção: [[context-management]].

**Tunables e telemetria:** todas as constantes do kernel (lease TTL, GC TTLs, CAS
retries, sentinel TTL, throttle do reconciler) vivem em `core/kernel_tunables.py`
(constantes puras, zero I/O); hooks e lease importam de lá
(`lease.LEASE_TTL_SECONDS` permanece como re-export por uma release). Cada invocação
de `pre_gate` appenda um record `{ts, hook, event, duration_ms}` em
`.dadaia/logs/hook-latency.jsonl` (best-effort, fail-open — logs dir ausente/não
gravável nunca muda veredito nem exit code; sem payload, paths ou session ids).

## Acquire do lease (O_EXCL CAS + stable-session-identity)

Para writes MUTATING lease-taking, o gate chama `lease.acquire(ctx, session_id,
release, mode, pid_probe)` (in-process; o pid-probe `OsProcessProbe` é injetado pelo
hook — `features/lease.py` nunca importa o adapter). O acquire usa O_EXCL sentinel file
(único caminho — sem read-then-write TOCTOU); o `renew_heartbeat` roda dentro do mesmo
CAS. O record carrega `pid` — o do **processo harness de vida longa**, resolvido por
`sdd_gate._resolve_holder_pid` (`harness_pid`/`parent_pid`/`ppid` do payload stdin,
senão `os.getppid()`) e threaded até `lease.acquire`; nunca o pid do subprocesso
efêmero do hook. Decision tree:

1. `.ptr` match → **RENEW** incondicional (incumbente, mesmo após relaunch).
2. Record com mesmo `session_id` → **RENEWED**, mesmo past-TTL (holder-safe: um holder nunca perde o próprio lease pela própria staleness).
3. Record ausente, ou TTL-stale com pid do holder morto/ausente → **ACQUIRED** (takeover).
4. Record foreign vivo — TTL-fresh **ou** TTL-stale com pid vivo (**PID veto**, `core/lock_liveness.is_stale`) → **LockHeldError**; gate bloqueia com yield message. A mensagem informa holder e heartbeat e **nunca** instrui rebind, relaunch ou steal.

**Índice by-session (atomicidade estrutural):** `acquire`/`steal`/`release` escrevem e
removem a entrada `ctx_locks/by-session/<sid>.json` **dentro do MESMO O_EXCL sentinel
CAS** que escreve o lock record — uma unidade atômica por transição; record-write e
index-write não podem divergir (entrada perdida starvaria a renovação e reabriria a
classe lease-theft). Fallback: full scan quando o diretório by-session está ausente
(janela de migração).

**Heartbeat (PostToolUse):** `sdd_post_gate` resolve o session id do **payload stdin**
(harness-native; `DADAIA_SESSION_ID` é só override de operador) e renova o heartbeat
dos leases que o sid segura, via o índice by-session — **sem full scan do lock dir**
quando a sessão não segura nada, e nunca via `DADAIA_CONTEXT`→first-ALIVE.
`renew_heartbeat` nunca recria record ausente ou de sid estrangeiro — depois de um
`context release` deletar o record, ressurreição é estruturalmente impossível (DP-3:
não existe guard de renovação baseado em session record; um holder unbound sem session
record continua renovando — invariante v0.1.10 FR-R2-01 preservada). Roda fail-open
exit 0. No Claude Code o matcher é match-all `*`; no Codex o bloco PostToolUse vem
**sem** matcher (forma canônica match-all) — heartbeat após **todo** tool, incl. Bash;
uma única call acima do TTL é coberta pelo PID veto (pid harness vivo ⇒ block, não
steal).

**Canonical unblock:** se o gate bloqueia com live-foreign lease, a sessão aguarda o
holder terminar ou morrer — um holder morto é liberado por TTL+probe no próximo acquire.
Nenhuma ação manual é necessária; writes ADDITIVE seguem fluindo.

## Fluxo de uso

1. Agente invoca uma tool de escrita (ex. `Write` em `repos/<slug>/src/foo.py`) ou um comando Bash.
2. O harness executa `python -m dadaia_workspace.hooks.pre_gate` passando JSON em stdin com `tool_name`, `file_path`/`command` e `session_id`.
3. `pre_gate` lê o stdin uma vez e roda root-whitelist → venv-guard (Bash) → SDD gate; first-block-wins.
4. A policy SDD resolve workspace root, deriva o context slug **PATH-first** do write target, lê `releases/ACTIVE.md` do contexto para a fase, resolve sid e modo, e classifica context-relative (todos os headers em `apply_patch`).
5. Para MUTATING: READ-mode bloqueia non-acquiring; senão `lease.acquire` com pid-probe.
6. Allow → exit 0 (silencioso); Block → STDOUT JSON `{"decision":"block","reason":"..."}`; latência appendada em `hook-latency.jsonl`.
7. Após cada tool call (PostToolUse), `sdd_post_gate` renova o heartbeat via by-session index e roda o reconciler advisory (throttled).
8. Nos chokepoints: `git commit` passa pelo pre-commit lease gate (cadeia DP-4); `git push` passa pelo CI preflight + push-gate-check (verdict de security por sha).

```mermaid
sequenceDiagram
    participant T as Tool Write/Edit/Bash
    participant PreH as PreToolUse Hook
    participant PG as hooks/pre_gate.py (entrypoint único)
    participant C as gate_policy.py (context-relative)
    participant L as lease.py (O_EXCL CAS + pid veto)
    participant PostH as PostToolUse Hook (todos os tools)
    participant GitC as git pre-commit (lease gate DP-4)
    participant GitP as git pre-push (preflight + security verdict)
    T->>PreH: tool call
    PreH->>PG: stdin JSON (lido uma vez)
    PG->>PG: root-whitelist
    PG->>PG: venv-guard (Bash apenas)
    PG->>C: SDD gate: classify (strip repos/<slug>/; todos os headers)
    alt PROTECTED
        PG-->>PreH: block (fail-closed)
    else ADDITIVE
        C-->>PG: allow (sem lease I/O)
    else MEMORY fora de DEFINITION/CLOSURE
        PG-->>PreH: block
    else FROZEN
        PG-->>PreH: block
    else MUTATING lease-taking
        PG->>L: acquire(ctx, sid, release, mode, pid_probe)
        alt ACQUIRED or RENEWED
            PG-->>PreH: exit 0 (allow)
        else LockHeldError (TTL-fresh ou pid vivo)
            PG-->>PreH: block with yield message
        end
    end
    PreH-->>T: allow/block (first-block-wins)
    T->>PostH: tool completed
    PostH->>L: renew heartbeat (by-session index, CAS)
    PostH->>PostH: reconciler advisory (nunca bloqueia)
    T->>GitC: git commit
    GitC->>GitC: DP-4 (no-lease/env-sid/ancestry/indeterminate⇒ALLOW+WARN)
    T->>GitP: git push
    GitP->>GitP: preflight + APPROVED security handoff por sha pushed
```

## Trigger típico

Automaticamente invocado a cada Write/Edit/MultiEdit/NotebookEdit/Bash em sessões de agente (PreToolUse via `pre_gate`), após cada tool call (PostToolUse), e em todo `git commit`/`git push` nos repos de Spec Context (chokepoints, independentes de harness). Operador raramente interage diretamente — só quando recebe um `{"decision":"block"}` ou um block de chokepoint que precisa ser entendido.

## Diferencial

Sem este kernel, agentes podem escrever em qualquer lugar a qualquer momento — memory vira changelog, archive ganha edits acidentais, dois agentes mutam o mesmo contexto simultaneamente, e o buraco do Bash deixaria commits/pushes sem governo. A classificação context-relative faz as classes valerem onde os specs reais vivem; o PID veto garante que um holder vivo nunca tem o lease roubado; o by-session index torna a renovação O(1) e estruturalmente lossless; os chokepoints git fecham o buraco do Bash nos desfechos que importam (commit/push) sem parsing de shell e sem depender de hooks de harness (cobrem inclusive Codex headless); e a exigência zero-false-block (ADR-G1) é vinculante — em dúvida, o chokepoint degrada para advisory (ALLOW+WARN) em vez de bloquear o holder legítimo.

## Estado runtime tocado

  * Read-only pelo PreToolUse gate: `releases/ACTIVE.md` do contexto (fase/release), `.dadaia/sessions/<id>.json` (modo via `session_identity`).
  * Read-write (in-process via `lease.py`): `.dadaia/states/ctx_locks/<ctx>.lock.json`, `.dadaia/states/ctx_locks/<ctx>.lock.sentinel`, `.dadaia/states/ctx_locks/by-session/<sid>.json` (mesma transação CAS), `.dadaia/sessions/runtime/<ctx>.ptr`.
  * Write pelo PostToolUse: renew heartbeat dos lock records deste sid (via by-session index); refresh best-effort de `last_seen_at` no session record; eventos `RECONCILER_FLAG`; throttle marker `.dadaia/tmp/reconciler-last-<sid>`.
  * Logs: `.dadaia/logs/lock-events.jsonl` (append-only; acquire, release, steal, HEARTBEAT, RECONCILER_FLAG) · `.dadaia/logs/hook-latency.jsonl` (telemetria `{ts, hook, event, duration_ms}`).
  * Git hooks: `.git/hooks/pre-commit` + `.git/hooks/pre-push` (instalados por `dadaia ci install-hook`; resolução de runner fail-closed: `$DADAIA_BIN` → venv do workspace → poetry → repo venv → fail).
  * Saída: STDOUT JSON quando bloqueia; exit 0 (silencioso) quando permite.

## Dependências

  * Depende de [[context-management]] (session record persistido por `dadaia context bind`; lease records criados pelo acquire inline; `context release` solta o lease).
  * `core/kernel_tunables.py` — single home das constantes do kernel (leaf: não importa de nenhuma camada).
  * `features/spec_context/session_identity.py` — único owner dos pointers e session records que o gate e o post-gate consomem.
  * `infrastructure/process_probe_adapter.OsProcessProbe` (platform seam `has_os_kill_liveness`) — injetado pelo hook; fallback TTL-only quando indisponível.
  * Port `ProcessAncestry` (core protocol; adapters Linux `/proc` / macOS `ps` / Windows Toolhelp32 read-only, selecionados no composition root) — consumido pelo pre-commit lease gate e pelo `context release` default-flow.
  * Depende de [[agent-orchestration]] indiretamente (releases ativas geradas pelo product-engineer durante orchestration).
  * Variáveis de ambiente (apenas overrides de operador; nenhuma é requerida em harness real): `WORKSPACE_ROOT`, `DADAIA_CONTEXT`, `DADAIA_SESSION_ID`, `DADAIA_MODE`, `DADAIA_BIN`.

### Hook injection por runtime (matriz de enforcement por harness)

Runtime| PreToolUse (`pre_gate`)| PostToolUse| Chokepoints git| Postura
---|---|---|---|---
Claude Code| `.claude/settings.json` matcher `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash` → `python -m dadaia_workspace.hooks.pre_gate` (comando único)| matcher `*` (todos os tools)| sim| determinístico: hooks + chokepoints
Codex interativo (TUI)| `.codex/hooks.json` matcher `^(apply_patch\|Edit\|Write\|Bash)$` → `pre_gate`| **sem matcher** (match-all canônico)| sim| determinístico: hooks + chokepoints
Codex headless (`codex exec`)| **não — exec não dispara hooks** (defeito upstream codex-cli 0.139.0; live-verificado, `tests/integration/codex_live/`, opt-in `DADAIA_CODEX_LIVE=1`)| não| sim| **chokepoints only**
PI (`pi`) — Layer 1 interativo| Extensão TS `.pi/extensions/dadaia-sdd-gate.ts` registra o hook `tool_call`; mapeia write→Write/edit→Edit e delega ao `pre_gate` via subprocess (venv-path resolution); **ativa post-trust** (WS-PI-4)| sem post-hook (efeito Ring-1 só pré-disk via tool_call)| sim| determinístico post-trust + chokepoints; `.pi/**` é post-trust executable
PI — Layer 2 worker (`PI_HEADLESS`)| n/a — worker headless `pi --mode json`, sem hook de entrada| n/a| sim| Ring-2 (git-diff) + chokepoints (não tem Ring-1; distinto do Layer 1)
