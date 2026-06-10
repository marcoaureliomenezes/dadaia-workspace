---
slug: architecture
title: Architecture Memory
category: core
tldr: Layer rules, agent topology (9 core + 3 plugins), single-record TTL-lease concurrency model, 3-channel comms, and asset projection chain for dadaia-workspace.
summary: Defines the three-ring architecture (cli/features/infrastructure), dependency
  rules, 9-core agent roster with coordinator+sub-agent topology, single-record JSON
  TTL-lease (v0.1.6), 3 report/comms channels, panel HTTP internals, ADRs, and state
  runtime for the workspace.
tags:
- architecture
- layers
- dependency-rules
- adr
- agents
agent_tier: self-pull
token_estimate: 3795
last_updated: '2026-06-09'
release_origin: 0.1.8
---

## Visão geral

Arquitetura em três anéis: (1) CLI thin em `dadaia_workspace/cli/`; (2) features isoladas em `dadaia_workspace/features/<name>/` cada uma com seu service/doctor/etc; (3) infrastructure em `dadaia_workspace/infrastructure/` (Git, JSON stores, public asset projection). Núcleo em `dadaia_workspace/core/` mantém models, protocols e exceptions — sem I/O. Dependency injection via `dadaia_workspace/container.py`.

Asset chain canonical → projeções: a fonte de cada agente, skill, rule, command, script, template, workflow vive em `dadaia_workspace/public/<type>/`; staging em `.dadaia/agentic/<type>/` (snapshots imutáveis com manifest.json); instalação espalha por `.claude/`, `.codex/`, `.opencode/`, `.agents/` seguindo regras por tool.

## O Spec Context Project (conceito central)

O **Spec Context Project** é o conceito central do dadaia-workspace (constitution §0). Um Spec Context Project é **uma canonical specs folder bound to one repository**. É session-bindable, e o binding dispara uma cadeia de valor:

1. **Bind** — a sessão se anexa a um Spec Context Project (o contexto ativo).
2. **Inject** — o binding injeta a `constitution.md` do contexto e sua `memory/` na sessão por lazy product-feature consumption (index + catalog carregam up front; feature atoms são pulled on demand).
3. **Enforce** — o ciclo SDD (constitution §7) é enforced para cada write de produção sob aquele contexto: nenhuma mudança de produção sem release aprovado e task reservada.
4. **Parallel multi-project** — porque cada contexto carrega exatamente um MUTATING lease (§8), múltiplos Spec Context Projects podem ser trabalhados concorrentemente em sessões diferentes. Trabalho ADDITIVE dentro de qualquer contexto roda em paralelo — com segurança, porque o contrato de lock torna estruturalmente impossível ter mais de um writer MUTATING por contexto.

A cadeia bind → inject → enforce → parallel-multi-project é o que permite a um generic agent fleet construir projetos reais com segurança e de forma organizada. Ver constitution §0.

## Camadas

**cli/** — typer app + 21 subcommands: `init`, `export`, `import`, `clean`, `context`, `lock`, `ci`, `repos`, `public`, `doctor`, `academy`, `orchestrate`, `reports`, `specs`, `server`, `migrate`, `panel`, `memory`, `release`, `backlog`, `bug`. Thin wrapper sobre features; sem business logic.

**features/** — cada feature é uma pasta com `service.py` + opcionalmente `doctor.py`, `resolver.py`, `runner.py`. Features atuais: `academy`, `agents` (canonical agent reader sobre `MarkdownAgentStore`), `ci_preflight`, `export`, `import_`, `migrate`, `orchestration`, `panel` (descrito em detalhe abaixo), `public`, `repos`, `reports_next`, `reports_retention`, `server_registry`, `spec_artifacts`, `spec_context` (inclui `lease.py` — contrato de locking central), `specs`, `telemetry` (com `aggregator/queries.py` expondo `list_sessions(runtime, project=None, limit=None) -> SessionListResult` + `get_session(runtime, session_id) -> SessionDetail | None`; `aggregator/runtimes.py` declara o protocolo `RuntimeAdapter` com métodos `enrich_row`, `enrich_detail`, `liveness(session_id, cwd)` e implementações `ClaudeRuntimeAdapter` e `CodexRuntimeAdapter`; `TelemetryAggregator` mantém registry `{runtime: adapter}` e delega enrichment per row), `workflows` (`WorkflowsService` wrapping `MarkdownWorkflowStore` com mtime cache + `dag.py` SVG renderer server-side via longest-path layout), `workspace`.

**panel — arquitetura HTTP interna (pós R5):**

  * **Route categories (3 tipos declarados em `handler.py`)**:
    * _Public_ : rotas em `_COMPILED_ROUTES`, sem autenticação — `GET /`, `GET /static/<name>`, `GET /memory/<slug>/<path>`, `GET /memory-view/<slug>/<file>`, `GET /reports/<path>` (path-traversal guard via `Path.resolve()` + `relative_to(workspace_root/.dadaia/reports/)`; 403 se fora do boundary).
    * _Bearer-only_ : `_BEARER_ONLY_ROUTES` — normalmente exigem header `Authorization: Bearer <token>`; incluem todos os `/api/*` endpoints: `/api/servers`, `/api/contexts`, `/api/agents`, `/api/agents/<id>/prompt`, `/api/workflows`, `/api/workflows/<name>`, `/api/sessions`, `/api/sessions/<runtime>/<id>`, `/api/academy`, `/api/reports`, `DELETE /api/reports/<path>`, `/api/kanban`. **Loopback bypass:** quando o panel inicia com `bind == "127.0.0.1"`, `loopback_bypass=True` é passado para `make_handler_class()`; `GET /api/*` retorna 200 sem token em bind loopback. Mutações (`POST`, `DELETE`) não são afetadas.
    * _Telemetry_ : `_tel_patterns` — subconjunto das bearer-only rotas de sessions que delegam para `TelemetryAggregator`.
  * **`do_DELETE` handler**: espelha o padrão de auth (Bearer validation constant-time); despacha `api_report_delete` via regex dispatch; mesmo traversal guard que `GET /reports/<path>`. `api_report_delete` remove o HTML report + canonical handoff em `.dadaia/handoff/` em um único passo atômico.
  * **Report retention**: `GET /api/reports` descobre reports por artifact HTML (HTML-first); enriquece cada row com sidecars canônicos de `.dadaia/handoff/`; deduplica para uma row por HTML report; adiciona campos `important: boolean`, `expires_at: string | null`, `is_expired: boolean`, `retention_reason: string | null`. `POST /api/reports/<path>/important` e `DELETE /api/reports/<path>/important` são as mutações de retention. Estado persiste em `.dadaia/states/report_retention.json`.
  * **Static asset registry** : `static.py _ASSETS` dict é o registry central de todos os assets servidos por `/static/<name>`.
  * **View composition** : `container.py build_panel_views()` instancia e retorna o dict de 15+ view callables. `views/kanban.py` serve `GET /api/kanban` (read-only; lê `.dadaia/sessions/*.json`; agrupa cards por context e modo; computa `is_stale` em read-time; nunca 500 para ausência do diretório).
  * **`window.Panel` registry pattern** em `core.js`: objeto `{ register(name, mod), activate(name, opts) }`. Lazy tab module loading. Módulos registrados: `agents`, `workflows`, `sessions`, `academy`, `reports`.
  * **Workspace resolver** : `_resolve_workspace()` em `panel.py` caminha de baixo para cima do cwd até encontrar o diretório contendo `.dadaia/` — `dadaia panel` funciona de qualquer subdiretório do workspace.

**core/** — `models/` (dataclasses puras), `protocols/` (ABCs / Protocols para DI), `exceptions.py`, `platform.py`. Zero I/O — a única exceção autorizada é `core/platform.py`, que lê `sys.platform` (o único site autorizado para essa chamada em todo o codebase). Pode importar stdlib apenas.

- `core/platform.py` — plataforma seam: `Capabilities` frozen dataclass com `detect()` classmethod e singleton `PLATFORM` em module-level. Flags: `has_fcntl`, `has_proc_fs`, `has_posix_chmod`, `has_sigterm`, `venv_scripts_dir`, `venv_exe_suffix`, `tmp_dir`. Nenhum outro arquivo pode ler `sys.platform` diretamente.
- `core/exceptions.py` — `PlatformSecurityError(DadaiaError)` e `PlatformCapabilityError(DadaiaError)` com atributos `feature_name: str` e `platform: str`.
- `core/protocols/` — 20 protocol files total: 4 OS-sensitive ports (`file_lock`, `telemetry_lock`, `platform_services`, `shutdown_handler`) + 16 domain protocols for DI.

**infrastructure/** — implementações concretas dos protocols: `git_subprocess`, `json_*_store`, `public_assets`, `markdown_workflow_store`, `markdown_agent_store`, `claude_agent_dispatcher`, `cli_agent_dispatcher`, `excel_reader`, `python_env`. Toda I/O fica aqui. Adaptadores de plataforma: `file_lock_posix`, `file_lock_windows`, `telemetry_lock_posix`, `telemetry_lock_windows`, `file_permission_posix`, `file_permission_windows`, `process_probe_adapter`, `signal_shutdown_posix`, `signal_shutdown_windows`.

**container.py** — sole composition root. Lê `PLATFORM`, seleciona adapters (POSIX vs Windows) e injeta via `build_*_service(workspace_root)` factories. CLI commands chamam o container para obter serviços. `container.py` é o único local onde `PLATFORM` determina qual adapter concreto é instanciado.

**hooks/** — `dadaia_workspace/hooks/` Python package (6 módulos: `__init__`, `_common`, `sdd_gate`, `root_whitelist`, `ctx_inject`, `sdd_post_gate`). Substitui os hooks bash de governança. Cada módulo tem entrypoint `__main__`. `runtime_config.py` emite comandos Python (`python -m dadaia_workspace.hooks.<name>`) para `.claude/settings.json` e `.codex/hooks.json`. `workspace/service.py` reconhece tanto o caminho `.sh` antigo quanto o novo comando Python para evitar dupla-registro. `sdd_gate.py` delega a `gate_policy.evaluate()` — não re-deriva política. `pre_push_ci.py` NÃO está no pacote — o hook `.sh` pre-push é retido.

**public/** — assets canônicos versionados: `agents/`, `skills/`, `rules/`, `commands/`, `scripts/`, `templates/`, `workflows/`, `plugins/`, `data/`, `scaffold/`. `public_assets.py` stage/install/doctor. A função `_install_workspace_guardrail_pair` faz fan-out byte-identical de uma única fonte `data/AGENTS.md` para o par `AGENTS.md` + `CLAUDE.md` no workspace-root e em cada consumer-repo.

## Topologia de agentes (9 core + 3 plugins)

A topologia pública default é definida na constitution §14. Dois papéis de dispatcher; todos os demais são workers.

**Dispatchers (apenas 2 podem despachar sub-agentes via Agent tool — constitution §9):**
- `project-manager` — coordinator do lifecycle; holds + coordinates + releases the release lease; pode despachar qualquer worker.
- `project-auditor` — audit fan-out; despacha workers de auditoria (ADDITIVE, sem lease).

**Curator (1):**
- `product-engineer` — author de SPEC/PLAN/TASKS/CLOSURE; guardião de `specs/memory/**`; runs como sub-agente de PM durante MUTATING phases.

**Workers leaf (6 core):**
- `software-engineer` — implementação de produção (código + testes); PM sub-agent.
- `qa-engineer` — review → commit gate (ADDITIVE evidence; votes).
- `security-reviewer` — review → push gate (ADDITIVE evidence; votes).
- `code-reviewer` — review → PR gate (ADDITIVE evidence; votes).
- `ai-engineer` — dono da superfície AI-entity (`dadaia_workspace/public/**`); usa seu próprio short MUTATING lease fora de spans de release, bloqueado pela gate se PM lease estiver vivo.
- `software-architect` — architectural soundness; feeds findings into phases 4/5 (ADDITIVE).

**Plugins (não pertencem ao core roster):**
- `frontend-engineer`, `design-specialist` — plugin `frontend-design`.
- `devops-engineer` — plugin `devops`.

**Dispatcher purity (constitution §9):** Apenas `project-manager` e `project-auditor` podem despachar sub-agentes via Agent tool. Workers não spawnam outros agentes — surfaceiam a necessidade ao dispatcher. Worker→worker dispatch é uma impossibilidade estrutural.

**Sub-agent architecture:** `product-engineer` e `software-engineer` rodam como PM sub-agentes sob o single lease do PM coordinator. Eles nunca adquirem um lease independentemente. O "writer role" move-se entre sub-agentes quando PM despacha o próximo — o lease nunca muda de mãos. Isso torna deadlocks entre sessões em diferentes lifecycle phases estruturalmente impossíveis.

## Modelo de concorrência e lease (v0.1.6 + D1 soul-fold)

Constitution §8 define as duas activity classes que particionam todas as ações:

**ADDITIVE phases (1/2/3/4/7):** writes targets são `specs/backlog/**`, `specs/bugs/**`, `specs/audits/**`, `.dadaia/reports/**`, `.dadaia/handoff/**`. Nenhum lease é requerido. Sessões concorrentes permitidas. Gate permite incondicionalmente para esses paths.

**MUTATING phases (5/6/8):** write targets são `specs/releases/<id>/**`, o production tree do contexto ativo, e `specs/memory/**`. Exatamente um lease ativo por contexto. Gate bloqueia em live-lease conflict.

### Schema do lease record (implementado em `features/spec_context/lease.py`)

```json
{
  "context": "<ctx-name>",
  "release": "<release-id>",
  "session_id": "<session-id>",
  "mode": "<mode>",
  "acquired_at": "<ISO 8601>",
  "heartbeat": "<ISO 8601>",
  "ttl": 120
}
```

- **Caminho:** `.dadaia/states/ctx_locks/<ctx>.lock.json`
- **Acquire:** O_EXCL CAS via sentinel file (`open(path, "x")`) — fecha o TOCTOU gap.
- **TTL:** `LEASE_TTL_SECONDS = 120` (OQ-1, operador 2026-06-06). Heartbeat renovado a cada PreToolUse.
- **Sem PID field** — cross-platform; sem `os.kill`; sem `/proc`.
- **Lock directory:** `0700`; lock file: `0600`.

### Stable session identity (D1 soul-fold)

Arquivo pointer: `.dadaia/sessions/runtime/<ctx>.ptr` contém o `session_id` do holder incumbente.

Lógica de acquire (FR-P1-15):
1. `.ptr` file matches `session_id` → **RENEW** incondicionalmente (mesmo se o record mostrar outro session_id por relaunch).
2. Record ausente ou stale → **ACQUIRED** (fresh write).
3. Record live, `session_id` matches lock record → **RENEWED** (heartbeat updated).
4. Record live, foreign `session_id`, sem `.ptr` match → **LockHeldError** com yield message (yield-iff-live-foreign). Gate bloqueia o write.

**Reclaim-iff-stale:** Gate reclaims e heals em lease ausente ou expirado (nunca bloqueia em lease stale/missing). Em lease estrangeiro vivo: yield informativo. A mensagem **nunca** instrui o operador a rebind, relaunch, ou steal — nenhuma cerimônia manual de desbloqueio.

**GC:** `dadaia doctor --fix` deleta `.lock.json` stale, session files órfãos, e sentinel files órfãos.

**fcntl Lock-1/Lock-2 retidos** em `locking.py` — serializam curtas git ops no mesmo processo (workspace-level e per-context). Não são usados para mutex de release.

**Staleness predicate — `core/lock_liveness.py`:** `is_stale_session(last_seen_at, ttl_seconds)` é a única fonte de verdade para decidir se uma sessão/lease está stale (TTL excedido a partir do último heartbeat). Consumido pelo reclaim-iff-stale do lease, pelo painel Kanban (`features/panel/views/kanban.py`) e por `features/spec_context/locking.py` — antes da extração (v0.1.7 / T-017-10) cada um tinha sua própria cópia do predicado `_is_stale`.

## Os 3 canais de reporte/comunicação (constitution §11)

dadaia-workspace tem exatamente três canais, cada um com um único destino canônico:

1. **User reports** — HTML, escrito em `.dadaia/reports/<context>/<agent>/`. Surfaced no panel. Para consumo humano quando explicitamente solicitado.
2. **Agent↔agent communication** — JSON handoffs, escrito em `.dadaia/handoff/<context>/` apenas. Este é o contrato máquina entre agentes.
3. **Audit results** — Markdown committado, escrito em `specs/audits/<ts>-<session_id_8chars>/` (archive: `specs/audits/_archive/`). Project-auditor escreve findings versionados ao lado das specs que audita.

Nenhum `specs/releases/<id>/evidence/` subtree existe ou é autorizado. Constitution §12 anti-slop: nenhum fato é gravado em duas fontes.

## Regras de dependência

Setas indicam dependência permitida; ausência de seta significa proibição.

```mermaid
flowchart TB
    cli --> features
    cli --> container
    features --> core
    infrastructure --> core
    container --> features
    container --> infrastructure
    container --> core
    hooks --> core
```

**Proibido:** core nunca importa de features/infrastructure/cli; features não importam de cli; features não importam outras features (passar pelo container); **features não importam `infrastructure/` diretamente** — toda dependência OS-sensível é injetada via Protocol por `container.py`.

**Layering invariant (v0.1.8):**
- `core/` — zero I/O, zero `sys.platform` (exceto `core/platform.py`). Zero `import fcntl / signal / subprocess / msvcrt`.
- `infrastructure/` — todos os adapters OS. Todo `fcntl`, `os.kill`, `os.chmod`, `signal.signal`, `subprocess`, `/proc`, `msvcrt` vive aqui atrás de Protocol interfaces.
- `features/` — business logic only. Zero `import fcntl / import signal / os.chmod / os.kill` direto. Recebe capability OS via Protocol injetado.
- `container.py` — sole composition root. Lê `PLATFORM`, seleciona adapters, injeta.

**Enforcement (dois layers):**
- `import-linter` (`setup.cfg`): contrato `features → infrastructure` import ban + `core → OS-primitive modules` ban. `core.platform` whitelisted para `sys`. Roda no CI `lint` job.
- `dadaia doctor` grep check: falha com `[ERROR]` em qualquer `import fcntl` / `os.chmod` / `os.kill` / `os.open` em `features/**/*.py`.

**Transitional debt (ADR-1):** Guards `sys.platform` em function bodies de `locking.py` e `telemetry/service.py` são permitidos durante a janela transitional, cada um anotado `# TODO: Replace with PLATFORM.has_<flag>`. `import-linter` tem 7 `ignore_imports` para o backlog item `features-import-infrastructure-direct-debt`. A remoção completa dessas dependências diretas é escopo de release futura.

## Fluxo de dados — pipeline asset chain

```mermaid
flowchart LR
    A[public/<type>/<file>] --> B[dadaia public stage]
    B --> C[.dadaia/agentic/<type>/<file>]
    C --> D[dadaia public install --target all]
    D --> E[.claude/<type>/<file>]
    D --> F[.codex/<type>/<file>]
    D --> G[.opencode/<type>/<file>]
    D --> H[.agents/<type>/<file>]
    I[manifest.json] --> J[dadaia public doctor]
    J -.audit.-> E
    J -.audit.-> F
    J -.audit.-> G
    J -.audit.-> H
```

## Fluxo de dados — gate v3 SDD (v0.1.8: Python hooks)

O gate usa um path-classifier de 5 classes: ADDITIVE / MEMORY / FROZEN / MUTATING / UNGATED. RULE E e o 4-store / semaphore model estão removidos. O hook é agora `python -m dadaia_workspace.hooks.sdd_gate` (Python puro, sem bash, funciona em Windows/macOS/Linux). `sdd_gate.py` delega a `gate_policy.evaluate()` — não re-deriva política. `.dadaia/sessions/**` é PROTECTED (fail-closed, SEC-01).

```mermaid
sequenceDiagram
    participant Tool as Agent Tool
    participant PreHook as PreToolUse Hook
    participant Gate as hooks/sdd_gate.py (Python)
    participant Classifier as gate_policy.py Path Classifier
    participant Active as releases/ACTIVE.md
    participant Lease as lease.py (O_EXCL CAS)
    participant TASKS as releases/<id>/TASKS.md
    participant PostHook as PostToolUse Hook
    Tool->>PreHook: Write/Edit (file_path)
    PreHook->>Gate: stdin JSON
    Gate->>Classifier: classify path
    alt ADDITIVE path (backlog/bugs/audits/reports/handoff)
        Classifier-->>Gate: allow (no lease check)
    else MEMORY path (specs/memory/**)
        Gate->>Active: read phase
        alt phase == CLOSURE or DEFINITION
            Gate-->>PreHook: allow
        else
            Gate-->>PreHook: block
        end
    else FROZEN path (_archive/**)
        Gate-->>PreHook: block
    else MUTATING path (production)
        Gate->>Lease: acquire(ctx, session_id, release, mode)
        alt ACQUIRED or RENEWED
            Gate->>TASKS: grep [-] marker (RULE C)
            alt task [-] found
                Gate-->>PreHook: exit 0 (allow)
            else
                Gate-->>PreHook: block (no active task)
            end
        else LockHeldError (live foreign lease)
            Gate-->>PreHook: block with yield message
        end
    else UNGATED
        Gate-->>PreHook: allow
    end
    PreHook-->>Tool: allow/block
    Tool->>PostHook: tool completed
    PostHook->>Gate: renew heartbeat (atomic)
```

## Contratos entre módulos

De| Para| Tipo de contrato| Notas
---|---|---|---
cli/commands/*| container.build_*_service| Factory call| Cada command resolve workspace_root e chama factory
features/*| core/protocols/*| Protocol / ABC| Injetado via constructor — features não conhecem implementação
features/specs/doctor| specs/ filesystem| Path-based, read-only| Recebe specs_dir absoluto; nunca escreve. Inclui invariante D-OC-1 (bidirectional router/workflow wikilink validation).
infrastructure/public_assets| public/ ↔ .dadaia/agentic/ ↔ projeções| Manifest + file copy| Manifest.json é o cache do que foi propagado
PreToolUse hook| `python -m dadaia_workspace.hooks.sdd_gate` (+ `root_whitelist`) + `lease.py`| JSON stdin / stdout + O_EXCL CAS| Fail-open: erros não-PROTECTED → allow; `.dadaia/sessions/**` PROTECTED → fail-closed (SEC-01); live-foreign lease → block; context-slug derivado PATH-first do write target
features/spec_context/lease.py| `.dadaia/states/ctx_locks/<ctx>.lock.json`| Single-record JSON TTL-lease; O_EXCL CAS acquire| `LEASE_TTL_SECONDS = 120`; sem PID; stable-session-identity via `.ptr` file
features/telemetry/aggregator/queries.py| features/telemetry/aggregator/runtimes.py| RuntimeAdapter protocol + registry| `TelemetryAggregator` mantém registry `{runtime: RuntimeAdapter}` e delega enrichment per row + liveness per runtime.

## Estado runtime

Locais canônicos de estado em disco e seu propósito:

  * `.dadaia/states/spec_contexts.json` — todos os Spec Context Projects (`schema_version: "2"`; state ALIVE/DEAD; sem flag global de contexto; campos `alive_since` e `dead_since`).
  * `.dadaia/states/.ws_lock` — fcntl workspace-wide lock (gitignored; criado em runtime; Lock 1 — serializa mutações em `spec_contexts.json`).
  * `.dadaia/states/ctx_locks/<slug>.lock` — fcntl per-context lock (gitignored; Lock 2 — serializa git clone/rmtree).
  * `.dadaia/states/ctx_locks/<ctx>.lock.json` — single-record JSON TTL-lease (v0.1.6); schema `{context, release, session_id, mode, acquired_at, heartbeat, ttl}`; acquire via O_EXCL CAS.
  * `.dadaia/states/ctx_locks/<ctx>.lock.sentinel` — CAS sentinel file (transient; criado e deletado atomicamente durante acquire).
  * `.dadaia/sessions/runtime/<ctx>.ptr` — stable-session-identity pointer (D1 soul-fold); contém `session_id` do holder incumbente; RENEW incondicionalmente quando match.
  * `.dadaia/logs/lock-events.jsonl` — audit log append-only (O_APPEND; eventos: acquire, release, steal, HEARTBEAT).
  * `.dadaia/agentic/<type>/` — staging de assets (snapshot imutável).
  * `.dadaia/agentic/manifest.json` — registro do que foi propagado para cada tool.
  * `.dadaia/scripts/sdd-spec-gate.sh` — script bash legado (ainda presente como fallback; superseded por `python -m dadaia_workspace.hooks.sdd_gate`).
  * `.dadaia/scripts/sdd-post-gate.sh` — script bash legado (ainda presente; superseded por `python -m dadaia_workspace.hooks.sdd_post_gate`).
  * `dadaia_workspace/hooks/` — Python package de governança (6 módulos); registrado em `.claude/settings.json` e `.codex/hooks.json` por `infrastructure/runtime_config.py`.
  * `.dadaia/reports/<context>/<agent>/*.html` — reports HTML produzidos por especialistas; consumidos por `project-manager` no Discovery e por `project-auditor` nas auditorias.
  * `.dadaia/handoff/<context>/*.handoff.json` — agent↔agent JSON handoffs (canal 2 dos 3 canais).
  * `.dadaia/states/report_retention.json` — important-mark set para report retention; keys são caminhos workspace-relativos.
  * `.dadaia/states/root_exceptions.txt` — lista de entradas de root permitidas além do whitelist canônico.
  * `specs/releases/ACTIVE.md` — release ativa + phase.
  * `specs/audits/<ts>-<session_id_8chars>/` — audit results committados (canal 3 dos 3 canais; project-auditor).
  * `specs/memory/*.md` — memory atômica (Markdown + frontmatter YAML; rendered in-memory pelo panel via mistune).
  * `specs/memory/product/catalog.json` — gerado por `generate-memory-catalog.py` a partir do frontmatter dos `.md`; committed; índice machine-readable.
  * `specs/_archive/releases/<id>/` — releases concluídas com CLOSURE.

**Removido em v0.1.6:** os stores `.dadaia/locks/implementation/<ctx>__<release>.json` (Lock 3), `.dadaia/states/ctx_locks/<ctx>.semaphore.json` (Lock 4 / semaphore), e `.dadaia/logs/semaphore-reclaims.jsonl`. O modelo 4-store foi substituído pelo single-record JSON TTL-lease. `semaphore.py` foi deletado. RULE E do gate foi removido. O antigo marcador global de contexto foi eliminado na migração v1→v2.

**Retido em v0.1.6:** `.dadaia/sessions/<sess_*>.json` — session binding files gravados por `cli/commands/context.py:bind` (linha 334-335) e lidos por `panel/views/kanban.py` para exibir o estado de sessões ativas na aba Kanban. Estes arquivos não são o mecanismo de locking (Lock-3 foi removido); servem exclusivamente para display de sessão (Kanban view e context bind/release). O mecanismo de locking é agora exclusivamente o TTL-lease em `.dadaia/states/ctx_locks/<ctx>.lock.json`.

## Memory injection subsystem

O subsistema garante que agentes nunca iniciam trabalho sem contexto de produto. Opera em três runtimes (Claude Code, OpenCode, Codex).

### Lean payload

O bootstrap injetado é **tech-stack + catalog apenas** (~2.400 tokens). `architecture.md` é intencionalmente não injetado — é large e é self-pulled pelos agentes antes de qualquer trabalho arquitetural ou cross-layer, exatamente como feature atoms são pulled on demand.

### ctx-inject.sh (Claude Code + Codex + OpenCode)

`dadaia_workspace/public/scripts/ctx-inject.sh` — lib-originated, projetado para `.dadaia/scripts/ctx-inject.sh`. Em Codex roda no `SessionStart` (matcher `startup|resume`) carregando o contexto completo **uma vez por sessão**; em Claude Code roda no `UserPromptSubmit` e em OpenCode no `chat.message`. Os hooks podem disparar a cada prompt, mas a injeção completa ocorre só uma vez por sessão lógica.

O script:
1. Resolve `$SPECS_DIR` de `$DADAIA_CONTEXT`, session file ligado, ou flags explícitos.
2. Resolve um `SESSION_ID` **estável** (env `CLAUDE_CODE_SESSION_ID`/`CODEX_SESSION_ID`/`OPENCODE_SESSION_ID`, depois o `session_id` que o Codex passa no stdin; sem fallback de PID `$$`) e sanitiza-o antes de usá-lo como nome de arquivo. Verifica o sentinel de first-message em `.dadaia/tmp/ctx-inject-fired-<SESSION_ID>`. Se existir, **não emite nada** e sai — nem o breadcrumb de context-name (a injeção completa já ocorreu no SessionStart).
3. Cria o sentinel e emite o payload completo dentro de bounded markers:

```
=== workspace memory (tech + catalog) ===
...tech-stack.md content verbatim...
...catalog.json content...
=== end memory bootstrap ===
```

### catalog.json generation pipeline

`dadaia_workspace/features/specs/catalog.py` — reads frontmatter YAML blocks from `specs/memory/product/*.md` files. CLI: `dadaia memory catalog generate [--specs-dir PATH]`. O generated file é committed como `specs/memory/product/catalog.json`. O script `generate-memory-catalog.py` é o equivalente standalone.

### CAT-1 doctor check

Verifica que o conjunto de slugs em `catalog.json` matches o conjunto de `*.md` files (excluindo `index.md`) em `specs/memory/product/`. Severity: WARNING.

## Structured-memory-source subsystem (memory-markdown-source-v1)

Memory atoms são `.md` files com YAML frontmatter + Markdown body. HTML é ephemeral (rendered in-memory pelo panel via `mistune`; nunca escrito em disco).

### Source format

Cada atom é um `.md` file com strict YAML frontmatter block (`---` delimiters). Frontmatter schema: `memory-frontmatter-v1` (`additionalProperties: false`). Required fields: `slug`, `title`, `category`, `tldr`, `summary`, `tags`, `agent_tier`, `token_estimate`, `last_updated`, `release_origin`. Body: Markdown com `##` heading allowlist. `## Changelog`, `## Histórico`, `## History`, `## Versions` são hard errors.

### Panel render path (`features/panel/views/_md_render.py`)

O panel lê `.md` source em serve time, converte para HTML usando `mistune~=3.0` com custom hooks:
- Mermaid fenced code block → `<pre class="mermaid">…</pre>`
- `wikilink` → `<a href="…">` anchor
- Sanitiser: strips inline `<script>` e `<style>` do rendered output (XSS guard)

Output é cached by mtime. Nenhum `.html` file é escrito em disco.

### Lint tooling (`lint-memory-atoms.py`)

Valida cada atom:
- Frontmatter present, parseable, required fields, no extra fields
- `##` headings são subset do allowlist; sem duplicates
- `slug` wikilinks resolvem para `.md` files reais em `specs/memory/`
- Forbidden headings — hard ERROR

Invocado por doctor check `LINT-1`. Exit 0 = all valid; exit 1 = ao menos um ERROR.

## Multi-harness runtime parity (constitution §4)

| Runtime | Hook enforcement | Notes |
|---------|-----------------|-------|
| Claude Code | Real PreToolUse block (`python -m dadaia_workspace.hooks.sdd_gate`) | Strongest enforcement; Python, no bash dependency |
| Codex | Guardrail in trusted-workspace mode | `python -m dadaia_workspace.hooks.sdd_gate` registered in `.codex/hooks.json`; advisory on untrusted Codex |
| OpenCode | `.ts` plugins call Python subprocess | `sdd-gate.ts` + `ctx-inject.ts` call Python hooks via venv-path resolution (`.dadaia/.venv/bin/python` → `.dadaia/.venv/Scripts/python.exe` → bare `python`); Bun cross-platform `.env()` API used for env-passing — governed on Windows; `dadaia public doctor` reporta `[unsupported]` para PostToolUse target opencode — esperado |

Codex-specific behavior é expresso em termos Codex-nativos: `AGENTS.md` context, `.codex/config.toml`, `.codex/skills`, hooks onde suportados, e deferred tool discovery para multi-agent capability.

**path-scope enforcement** — O gate PreToolUse (`python -m dadaia_workspace.hooks.sdd_gate`, desde 0.1.8) valida o `file_path` de Write/Edit/MultiEdit e headers de Codex `apply_patch` contra `paths.write_allowlist` do frontmatter do agente ativo. `ai-engineer` tem write authority exclusiva sobre `dadaia_workspace/public/{skills,rules,workflows,commands,agents,hooks}/**`; `software-engineer` é banido dessa superfície AI-entity (e vice-versa: `ai-engineer` não escreve código Python/Node nem specs).

**rules folder** — 5 arquivos canônicos públicos: `workspace-protocol.md`, `tmp-file-guardrail.md`, `plugin-scope.md`, `dadaia-workspace-dev-guardrail.md`, `harness-skill-scope.md` (restringe `ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering` ao `ai-engineer`; `harness-primitives` é explicitamente não-restrita).

## Evidências visuais

Diagramas de classe e screenshots da CLI vão sob `specs/assets/architecture/`. Atualmente sem assets — primeira batch virá em release subsequente.
