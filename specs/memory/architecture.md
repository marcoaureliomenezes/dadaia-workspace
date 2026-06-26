---
slug: architecture
title: Architecture Memory
category: core
tldr: Layer rules, lifecycle spine, agent topology, merged pre_gate hook, git chokepoints, TTL+PID-veto lease, and projection chain.
summary: Defines the three-ring architecture (cli/features/infrastructure), dependency
  rules, 9-core agent roster with coordinator+sub-agent topology, the concurrency
  kernel (merged pre_gate PreToolUse entrypoint; context-relative path classifier;
  single-record JSON TTL-lease with pid veto and same-CAS by-session heartbeat index;
  git pre-commit/pre-push chokepoints; bind-driven context injection;
  session_identity store; bind-mode channel; kernel_tunables single home), 3
  report/comms channels, panel HTTP internals, ADRs, and state runtime.
tags:
- architecture
- layers
- dependency-rules
- adr
- agents
- backlog
agent_tier: self-pull
token_estimate: 9100
last_updated: '2026-06-26'
release_origin: v0.1.26
---

## Visão geral

Arquitetura em três anéis: (1) CLI thin em `dadaia_workspace/cli/`; (2) features isoladas em `dadaia_workspace/features/<name>/` cada uma com seu service/doctor/etc; (3) infrastructure em `dadaia_workspace/infrastructure/` (Git, JSON stores, public asset projection). Núcleo em `dadaia_workspace/core/` mantém models, protocols e exceptions — sem I/O. Dependency injection via `dadaia_workspace/container.py`.

Asset chain canonical → projeções: a fonte de cada agente, skill, rule, command, script, template, workflow vive em `dadaia_workspace/public/<type>/`; staging em `.dadaia/agentic/<type>/` (snapshots imutáveis com manifest.json); instalação espalha por `.claude/`, `.codex/`, `.pi/` (Layer-1 PI, target `pi`), `.agents/` seguindo regras por tool. O harness set de Layer-1 é exatamente **`{claude, codex, pi}`** — **OpenCode foi removido inteiramente em v0.1.24** (ambas as layers): não há mais target `opencode`, projeção `.opencode/`, nem entrada de manifest opencode; `_VALID_TARGETS` é `{agents, claude, codex, pi}` (+`all`). A fonte de prompt-fragments do lifecycle vive em `dadaia_workspace/public/lifecycle_fragments/` (projetada + manifest-tracked; ver "Two-layer agentic model").

## O Spec Context Project (conceito central)

O **Spec Context Project** é o conceito central do dadaia-workspace (constitution §0). Um Spec Context Project é **uma canonical specs folder bound to one repository**. É session-bindable, e o binding dispara uma cadeia de valor:

1. **Bind** — a sessão se anexa a um Spec Context Project (o contexto ativo).
2. **Inject** — o binding injeta a `constitution.md` do contexto e sua `memory/` na sessão por lazy product-feature consumption (index + catalog carregam up front; feature atoms são pulled on demand).
3. **Enforce** — o ciclo SDD (constitution §7) é enforced para cada write de produção sob aquele contexto: nenhuma mudança de produção sem release aprovado e task reservada.
4. **Parallel multi-project** — porque cada contexto carrega exatamente um MUTATING lease (§8), múltiplos Spec Context Projects podem ser trabalhados concorrentemente em sessões diferentes. Trabalho ADDITIVE dentro de qualquer contexto roda em paralelo — com segurança, porque o contrato de lock torna estruturalmente impossível ter mais de um writer MUTATING por contexto.

A cadeia bind → inject → enforce → parallel-multi-project é o que permite a um generic agent fleet construir projetos reais com segurança e de forma organizada. Ver constitution §0.

## Camadas

**cli/** — typer app + 22 subcommands: `init`, `export`, `import`, `clean`, `context`, `lock`, `ci`, `repos`, `public`, `doctor`, `academy`, `orchestrate`, `reports`, `specs`, `server`, `migrate`, `panel`, `memory`, `release`, `backlog`, `bug`, `lifecycle`. Thin wrapper sobre features; sem business logic.

**features/** — cada feature é uma pasta com `service.py` + opcionalmente `doctor.py`, `resolver.py`, `runner.py`. Features atuais: `academy`, `agents` (canonical agent reader sobre `MarkdownAgentStore`), `backlog` (backlog-consistency engine: v0.1.25 `subject_registry.py` registry auto-derivado, `classifier.py` classificador fail-closed, `doctor.py` BL-* checks, `ledger.py` reader do sidecar `consumed_backlog.json`, `preview.py` superfície read-only; v0.1.26 `ledger_writer.py` writer do sidecar na shape exata do reader R1, `removal.py` hook de closure residual-aware (rewrite-down-to-residual default; full removal só a zero residual, com cópia durável em `_archive/<release>/consumed-backlog/` ANTES do unlink — ADR-C copy-before-remove), `removal_lifecycle.py` facade `BacklogRemovalLifecycle` ligando os dois lados — ver "Backlog-consistency subsystem" abaixo), `ci_preflight`, `export`, `import_`, `lifecycle` (multi-harness procedural lifecycle engine: state machine, preflight, semantic gates, hygiene, report workflow, scoped prompts + `prompt_builder.PromptPrefix` cacheable/hashed, run store, `agent_runner` Ring-2, `phase_workflow.py` single-step, `pipeline.py` multi-step phase ladder com per-step harness mixing + model tiers, `workflows/backlog_definition.py` — o corpo da workflow `backlog_definition` (§4: intake_grill → subject_bind → existing_backlog_review → reconcile_decision → conflict_resolution_grill → backlog_author → backlog_review_gate; mirror estrutural de `release_definition.py`, gates Python-owned), `context_selector.py` com o selector `backlog_index` (bound intents + status por item, frontmatter-only, paths injetados), e `antislop/{slop_scan,retention}.py` — directory-aware slop metric + boundary-safe RetentionSweep), `migrate`, `orchestration` (read-only reference: `list`/`show` mostram os workflow docs; `run`/`status`/`resume` permanecem como stubs inertes de compat — não despacham agente, exit 0 — pois o dispatch path foi retirado em WS-3 e a execução migrou para `dadaia lifecycle`), `panel` (descrito em detalhe abaixo), `public`, `repos`, `reports_next`, `reports_retention`, `server_registry`, `spec_artifacts`, `spec_context` (inclui `lease.py` — contrato de locking central), `specs`, `telemetry` (com `aggregator/queries.py` expondo `list_sessions(runtime, project=None, limit=None) -> SessionListResult` + `get_session(runtime, session_id) -> SessionDetail | None`; `aggregator/runtimes.py` declara o protocolo `RuntimeAdapter` com métodos `enrich_row`, `enrich_detail`, `liveness(session_id, cwd)` e implementações `ClaudeRuntimeAdapter` e `CodexRuntimeAdapter`; `TelemetryAggregator` mantém registry `{runtime: adapter}` e delega enrichment per row), `workflows` (`WorkflowsService` wrapping `MarkdownWorkflowStore` com mtime cache + `dag.py` SVG renderer server-side via longest-path layout), `workspace`.

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
- `core/protocols/` — OS-sensitive ports (`file_lock`, `telemetry_lock`, `platform_services`, `shutdown_handler`, `process_ancestry` — `ProcessAncestry`, probe read-only de ancestralidade de processo com adapters Linux `/proc` walk / macOS `ps -o ppid=` via ProcessRunner / Windows Toolhelp32 read-only, NUNCA `os.kill`; consumido pelo pre-commit lease gate e pelo `context release` default-flow) + domain protocols for DI, incluindo `process_runner` (`ProcessRunner`/`ProcessResult` — seam de execução de subprocess para features; nenhuma feature importa `subprocess` diretamente).
- `core/kernel_tunables.py` — single home das constantes do kernel de concorrência (lease TTL, GC TTLs, CAS retries, sentinel TTL, throttle do reconciler); constantes puras, zero I/O; leaf no import-linter.
- `core/scope_match.py` — classifier de path puro, compartilhado pelo Ring-2 do `LifecycleAgentRunner` e pelo Ring-1 write-permission decider do `ClaudeSdkAdapter` (one classifier, two boundaries). Vive em `core/` (não em `features/`) para que `infrastructure/` possa importá-lo sem violar o layering — correção da quebra `infrastructure → features` apanhada pelo `lint-imports`.

**infrastructure/** — implementações concretas dos protocols: `git_subprocess` (inclui `GitSubprocessClient.diff_name_only(path)` — lista de `git diff --name-only` working-tree+staged+untracked, fonte do Ring-2 `changed_paths` do PI), `json_*_store`, `public_assets`, `markdown_workflow_store`, `markdown_agent_store`, os agent-runtime adapters por trás de `AgentRuntimePort` (`codex_runtime.CodexExecAdapter`, `claude_sdk_runtime.ClaudeSdkAdapter` com Ring-1 write boundary via `core/scope_match` + transport `query_fn` injetável; `claude-agent-sdk` é extra opcional lazy-imported; `pi_runtime.PiHeadlessAdapter` + `PiHeadlessConfig` — twin estrutural do `CodexExecAdapter`, dirige `pi --mode json` via runner subprocess injetável, sem PI client em module-load, Ring-2 `changed_paths` de git-diff; `opencode_runtime` foi removido em v0.1.24), `excel_reader`, `python_env`, `subprocess_runner` (`SubprocessProcessRunner` — implementação production do `ProcessRunner`; consumida por `features/import_`, `features/ci_preflight`, `features/specs/doctor` e `features/server_registry` via Protocol/DI; contrato import-linter `features-no-subprocess` em `setup.cfg` proíbe `features → subprocess`). Toda I/O fica aqui. Adaptadores de plataforma: `file_lock_posix`, `file_lock_windows`, `telemetry_lock_posix`, `telemetry_lock_windows`, `file_permission_posix`, `file_permission_windows`, `process_probe_adapter`, `signal_shutdown_posix`, `signal_shutdown_windows`.

**container.py** — sole composition root. Lê `PLATFORM`, seleciona adapters (POSIX vs Windows) e injeta via `build_*_service(workspace_root)` factories. CLI commands chamam o container para obter serviços. `container.py` é o único local onde `PLATFORM` determina qual adapter concreto é instanciado.

**hooks/** — `dadaia_workspace/hooks/` Python package (8 módulos: `__init__`, `_common`, `pre_gate`, `sdd_gate`, `root_whitelist`, `venv_guard`, `ctx_inject`, `sdd_post_gate`) — a única implementação dos hooks de governança. O PreToolUse roda por **um entrypoint merged**, `pre_gate`: lê o stdin uma vez e avalia as policies em ordem fixa root-whitelist → venv-guard (Bash apenas) → SDD gate, first-block-wins; cada policy é fail-open (PROTECTED fail-closed dentro da policy SDD); `sdd_gate` e `root_whitelist` são thin policy modules (`evaluate_payload()`; `main()` legado mantido por uma release). `runtime_config.py` emite UM comando PreToolUse por runtime (`python -m dadaia_workspace.hooks.pre_gate`) para `.claude/settings.json` e `.codex/hooks.json`: matcher `Edit|Write|MultiEdit|NotebookEdit|Bash` no Claude; `^(apply_patch|Edit|Write|Bash)$` no Codex; PostToolUse match-all (heartbeat + reconciler advisory em todo tool). Shell assets git-hook: `public/scripts/pre-commit-lease-gate.sh` + `pre-push-ci-gate.sh` (chokepoints; instalados por `dadaia ci install-hook`; backends `dadaia ci pre-commit-check`/`push-gate-check`). `workspace/service.py` reconhece tanto o caminho `.sh` legado quanto o comando Python para evitar dupla-registro em settings pré-existentes. A policy SDD delega a `gate_policy.evaluate()` — não re-deriva política — e injeta o PID-probe no lease; `_common.target_paths()` classifica todos os headers de um `apply_patch` multi-file (veredito mais restritivo vence). Cada invocação de `pre_gate` appenda latência `{ts, hook, event, duration_ms}` em `.dadaia/logs/hook-latency.jsonl` (best-effort, fail-open). Constantes do kernel (lease TTL, GC TTLs, CAS retries, sentinel TTL, throttle do reconciler) têm single home em `core/kernel_tunables.py` (leaf; contrato import-linter).

**public/** — assets canônicos versionados: `agents/`, `skills/`, `rules/`, `commands/`, `scripts/`, `templates/`, `workflows/`, `lifecycle_fragments/` (prompt fragments do Layer-2; v0.1.24), `data/`, `scaffold/`. `public_assets.py` stage/install/doctor; targets de install = `{agents, claude, codex, pi}` (+`all`) — sem `opencode` (removido em v0.1.24). O `public/plugins/sdd-gate.ts` (gate plugin de Layer-1 do OpenCode) foi deletado. A função `_install_workspace_guardrail_pair` faz fan-out byte-identical de uma única fonte `data/AGENTS.md` para o par `AGENTS.md` + `CLAUDE.md` no workspace-root e em cada consumer-repo.

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

## Modelo de concorrência e lease (v0.1.14)

Constitution §8 define as duas activity classes que particionam todas as ações.

**Classificação context-relative (taxonomia classe × localização):** o path-classifier
(`features/spec_context/gate_policy.classify_path`) computa a classe sobre o caminho
**relativo ao contexto**. Para um write sob `repos/<slug>/...`, o prefixo
`repos/<slug>/` é removido e a taxonomia ordenada `specs/` (ADDITIVE → MEMORY → FROZEN)
é aplicada ao restante — exatamente a mesma que governa paths workspace-root. Um
restante in-repo que não casa com nenhuma classe é **MUTATING** (nunca cai em UNGATED):
production source e `specs/<other>` in-repo (ex. `specs/constitution.md`,
`specs/releases/**`) são MUTATING. As classes ADDITIVE de `.dadaia/` são
workspace-root-only (`.dadaia/` é proibido dentro de qualquer repo).

**ADDITIVE phases (1/2/3/4/7):** `specs/backlog/**`, `specs/bugs/**`, `specs/audits/**`
(no workspace-root **e** in-repo) + `.dadaia/reports/**`, `.dadaia/handoff/**`,
`.dadaia/tmp/**` (root). Allow com **zero leitura ou escrita de lease** — um write
ADDITIVE jamais aparece no lock record. Sessões concorrentes permitidas.

**MEMORY / FROZEN (root e in-repo):** `specs/memory/**` é gated por fase (allow apenas
em DEFINITION/CLOSURE — RULE A) e `specs/_archive/**` é read-only (RULE B) — as duas
regras executam também para os paths in-repo, onde os specs reais vivem.

**MUTATING phases (5/6/8):** `specs/releases/<id>/**`, o production tree do contexto, e
todo in-repo path sem classe. Exatamente um lease ativo por contexto. Gate bloqueia em
live-lease conflict.

### Schema do lease record (implementado em `features/spec_context/lease.py`)

```json
{
  "context": "<ctx-name>",
  "release": "<release-id>",
  "session_id": "<session-id>",
  "mode": "<mode>",
  "pid": 12345,
  "acquired_at": "<ISO 8601>",
  "heartbeat": "<ISO 8601>",
  "ttl": 120
}
```

- **Caminho:** `.dadaia/states/ctx_locks/<ctx>.lock.json`
- **Acquire E renew via O_EXCL CAS:** sentinel file (`open(path, "x")`) fecha o TOCTOU
  gap. `renew_heartbeat` roda o read→verify→write **dentro do mesmo sentinel CAS** que
  o acquire usa — um takeover estrangeiro nunca interleava entre o read e o write de uma
  renovação.
- **Liveness = TTL com PID veto** (`core/lock_liveness.is_stale`): `LEASE_TTL_SECONDS =
  120` é o piso de reclaimability, mas quando o record carrega `pid` e o probe injetado
  reporta o processo holder **vivo**, um record TTL-expirado é tratado como live —
  `acquire` estrangeiro **bloqueia** em vez de TAKEOVER (no-steal). O `pid` gravado é o
  do **processo harness de vida longa**, resolvido pelo hook
  (`hooks/sdd_gate._resolve_holder_pid`: `harness_pid`/`parent_pid`/`ppid` do payload
  stdin, senão `os.getppid()`) e threaded até `lease.acquire` — nunca o pid do
  subprocesso efêmero do hook. Pid morto/ausente,
  ou probe indisponível na plataforma (`PLATFORM.has_os_kill_liveness`) ⇒ fallback
  TTL-only (TAKEOVER). O probe (`infrastructure/process_probe_adapter.OsProcessProbe`,
  platform-seamed) é injetado pelo hook layer (`hooks/sdd_gate.py`) — `features/lease.py`
  nunca importa o adapter.
- **Holder-safe past TTL:** um holder confirmado (mesmo `session_id` ou `.ptr` match)
  renova mesmo com heartbeat expirado — nunca perde o próprio lease para a própria
  staleness.
- **By-session index (mesma transação CAS):** `acquire`/`steal`/`release` escrevem e
  removem `ctx_locks/by-session/<sid>.json` **dentro do mesmo O_EXCL sentinel CAS**
  que escreve o lock record — record e index não podem divergir estruturalmente. A
  renovação PostToolUse é index-driven (sem full scan do lock dir quando a sessão não
  segura nada; fallback full-scan quando o dir do index está ausente).
- **Release explícito:** `dadaia context release` solta o(s) lease(s) da sessão antes
  de remover o session record (eval flow: por sid do env; default flow: contexto bound
  + holder pid morto ou ancestry do chamador via `ProcessAncestry`; nunca solta holder
  estrangeiro vivo). `renew_heartbeat` nunca recria record ausente/foreign-sid —
  ressurreição pós-release é estruturalmente impossível (DP-3: sem guard de renovação
  baseado em session record; holder unbound continua renovando — FR-R2-01).
- **Tunables:** TTLs/retries/throttles do kernel vivem em `core/kernel_tunables.py`
  (constantes puras, zero I/O; `lease.LEASE_TTL_SECONDS` re-exportado por uma release).
- **Lock directory:** `0700`; lock file: `0600`.

### Heartbeat — PostToolUse com session id harness-native

`python -m dadaia_workspace.hooks.sdd_post_gate` roda após cada tool call e renova o
heartbeat de **todo lease cujo record nomeia o sid desta sessão**:

- O session id é resolvido do **payload stdin** do hook (`_common.resolve_session_id` —
  harness-native); `DADAIA_SESSION_ID` é apenas override de operador.
- O alvo da renovação é resolvido pelo **by-session index**
  (`ctx_locks/by-session/<sid>.json`) — sem full scan do lock dir quando a sessão não
  segura nada, e **nunca** via `DADAIA_CONTEXT` → first-ALIVE (a rota da contaminação
  cross-context).
- A renovação roda fora de qualquer guard de session-file; fail-open exit 0 sempre.
  `renew_heartbeat` nunca recria um record ausente ou de sid estrangeiro.
- No Claude Code o matcher PostToolUse é match-all `*`; no Codex o bloco PostToolUse
  vem **sem** matcher — a forma canônica match-all do Codex. Em ambos os harnesses o
  heartbeat dispara após todo tool (inclusive Bash) — um holder dentro de um pytest
  longo renova entre as calls, e uma única call que ultrapasse o TTL é coberta pelo
  PID veto (TTL-stale + pid harness vivo ⇒ block, não steal).
- O mesmo PostToolUse roda o **reconciler advisory** (FR-W1-03): flagueia paths
  MUTATING sujos fora de lease no repo do contexto bound (evento `RECONCILER_FLAG`
  em `.dadaia/logs/lock-events.jsonl`); nunca bloqueia, exit 0 em todos os branches;
  throttle por sessão (`.dadaia/tmp/reconciler-last-<sid>`, TTL de `kernel_tunables`).

### Identidade de sessão — `session_identity.py` (single owner)

`features/spec_context/session_identity.py` é o **único** reader/writer dos pointer
namespaces e do session record:

- `.dadaia/sessions/runtime/<ctx>.ptr` — pointer do incumbente do contexto (lease
  holder ou último bind; o `bind` o atualiza e o gate o lê na resolução de modo —
  honrado apenas quando nenhum lease **vivo** nomeia outro sid: liveness do holder
  vence o pointer, anti-downgrade).
- `.dadaia/sessions/runtime/<session_id>.ptr` — pointer de sessão do ctx-inject.
- `.dadaia/sessions/<id>.json` — session record (`session_id`, `context`, `mode`,
  `release`, `pid`, `bound_at`, `last_seen_at`, `ttl_seconds`).

`lease.py` mantém ownership do lock record em si, mas roteia todo pointer I/O por aqui.
A coerência lock-holder ↔ incumbent ptr ↔ session record é contract-tested e validada
post-hoc por `dadaia specs doctor` (SPEC-DOC-029). Artefatos legados de layouts
anteriores são ignored-and-superseded, nunca migrados.

Lógica de acquire (FR-P1-15 + pid veto):
1. `.ptr` file matches `session_id` → **RENEW** incondicionalmente (mesmo se o record mostrar outro session_id por relaunch).
2. Record com `session_id` matching → **RENEWED**, mesmo past-TTL (holder-safe).
3. Record ausente, ou TTL-stale com pid do holder morto/ausente → **ACQUIRED** (takeover).
4. Record foreign live — TTL-fresh, **ou** TTL-stale com pid vivo (veto) → **LockHeldError** com yield message. Gate bloqueia o write.

### Canal de modo — bind → session record → gate

`dadaia context bind <ctx>` (`--mode` opcional, default `read`) **persiste** o modo no
session record via `session_identity` **e atualiza o incumbent pointer do contexto**
(`sessions/runtime/<ctx>.ptr`) — o bind vincula o CONTEXTO: o sid que o CLI cunha não é
o sid que o harness reporta, então é via incumbent que o gate resolve o modo bound no
fluxo default. O bind não emite eval-exports por default; `--print-env` é o escape
back-compat para operadores que ainda rodam `eval $(dadaia context bind ...)`.
Mapeamento de modos: `read`/`spec` (legacy) → `READ`; `implementation` →
`BOUND_IMPLEMENTATION`; `review` → `BOUND_REVIEW` (modos lease-taking exigem
`--release`).

O gate resolve o modo da sessão na ordem: (1) `DADAIA_MODE` env (escape de shell do
operador — harness nunca o seta), (2) `mode` do session record keyed pelo sid
harness-native (sessão que se auto-bindou; vence o incumbent — um holder vivo nunca é
downgraded), (3) modo do **incumbent do contexto** via `<ctx>.ptr` — o caminho
harness-real do bind default; honrado só se não contradiz um lease holder vivo
(anti-downgrade guard: lease record nomeando outro sid ⇒ incumbent stale, ignorado),
(4) default `IMPLEMENTATION`. Sessão READ-resolved é **non-acquiring**: write MUTATING é bloqueado
**antes** de qualquer chamada ao lease (sessão read nunca cria, renova ou rouba lease);
ADDITIVE flui normalmente. Sessão sem modo (nenhum bind, nenhum env — toda sessão
harness comum) permanece IMPLEMENTATION-capable: pode adquirir um lease **livre**, mas
nunca TAKEOVER de um holder vivo (Decision D-3 + PID veto).

### Escopo do determinismo (D-2 superado pelo envelope de chokepoints)

O envelope file-tool do gate cobre file-write tools (Claude PreToolUse matcher
`Edit|Write|MultiEdit|NotebookEdit|Bash`; Codex `^(apply_patch|Edit|Write|Bash)$` — o
evento Bash alimenta apenas o venv-guard de padrão fixo; o gate nunca parseia strings
de shell). Writes arbitrários via Bash continuam fora desse envelope, mas os desfechos
de lifecycle que importam são gated deterministicamente nos **chokepoints git**, que
rodam mesmo sem nenhum hook de harness (constitution §8):

- **pre-commit lease gate** — commit num repo de Spec Context sem segurar o MUTATING
  lease do contexto é bloqueado. Cadeia DP-4: sem lease/stale-dead ⇒ allow; env-sid
  igual ao holder ⇒ allow; pid do holder ancestral do processo invocante (port
  `ProcessAncestry`: Linux `/proc` walk, macOS `ps -o ppid=`, Windows Toolhelp32
  read-only; nunca `os.kill`) ⇒ allow; ancestralidade indeterminada OU holder pid
  morto ⇒ **ALLOW + WARN logado** (zero-false-block domina; degradação advisory
  documentada). Block apenas em lease estrangeiro vivo com non-match positivo;
  contexto derivado do path do repo, nunca first-ALIVE.
- **pre-push gate** — o mesmo hook roda `dadaia ci preflight` E o check mecânico de
  verdict de security: para cada sha non-zero das ref lines do stdin deve existir um
  handoff `security-reviewer` APPROVED com `metrics.commit_sha` igual àquele sha
  (campo canônico único; nunca `rev-parse HEAD`); deleções/tag-only passam; APPROVE
  stale bloqueia; commits nunca são review-blocked.
- **Escape hatch:** `--no-verify` bypassa git hooks — postura
  deterministic-at-the-chokepoint, não unbypassable; o backstop pós-hoc segue sendo a
  coerência lease↔session do doctor (SPEC-DOC-029).

O gate **não lê** `TASKS.md`, status `Aprovado`, markers `[-]` nem write-allowlists de
agente — o que ele enforça deterministicamente é path-class × lease × fase × modo;
markers, aprovações e allowlists são disciplina de agente/PM (workspace-protocol), não
mecanismo.

**Reclaim-iff-stale, yield-iff-live-foreign:** o gate reclaims e heals em lease ausente
ou expirado-com-holder-morto (nunca bloqueia em lease stale/missing reclaimable); em
lease estrangeiro vivo (TTL-fresh ou pid-vivo): yield informativo. A mensagem **nunca**
instrui o operador a rebind, relaunch, ou steal — nenhuma cerimônia manual de
desbloqueio.

**GC:** `dadaia doctor --fix` reclama leases TTL-expirados cujo holder está morto ou é
unprobeable (`LOCK-GC` — records pré-`pid` são unprobeable ⇒ reclaimable por TTL puro; um
holder com pid **vivo** nunca é reclaimed, mesmo past-TTL; probe injetado no composition
root via `container`), além de session files e sentinel files órfãos. `dadaia lock steal
<ctx>` é probe-gated: recusa quando o pid registrado do holder está vivo. Bind/session
records decaem por TTL medido contra `last_seen_at`, que o heartbeat PostToolUse renova a
cada tool use — uma sessão READ ativa nunca decai para IMPLEMENTATION; records sem
`last_seen_at` mantêm TTL-from-creation. O pid do session record (pid do bind-CLI, morto
por construção) não participa do bind-GC.

**fcntl Lock-1/Lock-2 retidos** em `locking.py` — serializam curtas git ops no mesmo processo (workspace-level e per-context). Não são usados para mutex de release.

**Staleness predicates — `core/lock_liveness.py`:** `is_stale(record, clock, pid_probe)`
é a única fonte de verdade para staleness de lease (TTL piso + PID veto, zero I/O, seams
injetados); `is_stale_session(last_seen_at, ttl_seconds)` é a fonte para staleness de
sessão, consumida pelo painel Kanban (`features/panel/views/kanban.py`) e por
`features/spec_context/locking.py`.

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
    D --> P[.pi/<type>/<file>]
    D --> H[.agents/<type>/<file>]
    I[manifest.json] --> J[dadaia public doctor]
    J -.audit.-> E
    J -.audit.-> F
    J -.audit.-> P
    J -.audit.-> H
```

## Fluxo de dados — gate v3 SDD (v0.1.14: entrypoint merged pre_gate)

O PreToolUse roda por UM entrypoint — `python -m dadaia_workspace.hooks.pre_gate`
(Python puro; Windows/macOS/Linux) — que lê o stdin uma vez e avalia root-whitelist →
venv-guard (Bash) → SDD gate, first-block-wins, cada policy fail-open. A policy SDD usa
um path-classifier de 6 classes — ADDITIVE / MEMORY / FROZEN / MUTATING / PROTECTED /
UNGATED — computado **context-relative** (prefixo `repos/<slug>/` removido antes da
taxonomia `specs/`); resolve o slug PATH-first do write target, o modo (env → session
record → incumbent do contexto → IMPLEMENTATION) e delega a `gate_policy.evaluate()` —
não re-deriva política. Um `apply_patch` multi-file tem todos os headers classificados
(veredito mais restritivo vence). `.dadaia/sessions/**` é PROTECTED (o único caminho
fail-closed, SEC-01). O gate não lê TASKS.md nem status de specs — markers e aprovações
são disciplina, não mecanismo.

```mermaid
sequenceDiagram
    participant Tool as Agent Tool
    participant PreHook as PreToolUse Hook (write tools + Bash)
    participant Gate as hooks/pre_gate.py (root-whitelist -> venv-guard -> SDD)
    participant Classifier as gate_policy.py (context-relative)
    participant Active as releases/ACTIVE.md
    participant Sess as session_identity (mode record)
    participant Lease as lease.py (O_EXCL CAS + pid veto)
    participant PostHook as PostToolUse Hook (todos os tools)
    Tool->>PreHook: Write/Edit (file_path)
    PreHook->>Gate: stdin JSON (lido uma vez; tool_name + file_path + session_id)
    Gate->>Classifier: classify path (strip repos/<slug>/; todos os headers)
    alt PROTECTED (.dadaia/sessions/**)
        Gate-->>PreHook: block (fail-closed, SEC-01)
    else ADDITIVE (backlog/bugs/audits root+in-repo; reports/handoff/tmp root)
        Classifier-->>Gate: allow (zero lease I/O)
    else MEMORY (specs/memory/** root+in-repo)
        Gate->>Active: read phase
        alt phase == CLOSURE or DEFINITION
            Gate-->>PreHook: allow
        else
            Gate-->>PreHook: block
        end
    else FROZEN (specs/_archive/** root+in-repo)
        Gate-->>PreHook: block
    else MUTATING (production + in-repo sem classe)
        Gate->>Sess: resolve mode (env -> record -> incumbent -> IMPLEMENTATION)
        alt mode == READ
            Gate-->>PreHook: block (non-acquiring, sem lease I/O)
        else lease-taking
            Gate->>Lease: acquire(ctx, session_id, release, mode, pid_probe)
            alt ACQUIRED or RENEWED
                Gate-->>PreHook: exit 0 (allow)
            else LockHeldError (TTL-fresh OU TTL-stale com pid vivo)
                Gate-->>PreHook: block with yield message
            end
        end
    else UNGATED
        Gate-->>PreHook: allow
    end
    PreHook-->>Tool: allow/block (first-block-wins)
    Tool->>PostHook: tool completed (qualquer tool, incl. Bash)
    PostHook->>Lease: renew heartbeat via by-session index (CAS atômico)
    PostHook->>PostHook: reconciler advisory (nunca bloqueia; throttled)
```

## Contratos entre módulos

De| Para| Tipo de contrato| Notas
---|---|---|---
cli/commands/*| container.build_*_service| Factory call| Cada command resolve workspace_root e chama factory
features/*| core/protocols/*| Protocol / ABC| Injetado via constructor — features não conhecem implementação
features/specs/doctor| specs/ filesystem| Path-based, read-only| Recebe specs_dir absoluto; nunca escreve. Inclui D-OC-1 (bidirectional router/workflow wikilink validation) e os ledger invariants SPEC-DOC-024 (fase ↔ markers), 026 (release ids únicos releases+archive), 027 (naming canon `^v\d+\.\d+\.\d+$`), 028 (file refs da constitution resolvem) e 029 (coerência lease↔session, backstop D-2).
infrastructure/public_assets| public/ ↔ .dadaia/agentic/ ↔ projeções| Manifest + file copy| Manifest.json é o cache do que foi propagado
PreToolUse hook| `python -m dadaia_workspace.hooks.pre_gate` (root-whitelist → venv-guard → SDD) + `gate_policy.py` + `lease.py`| JSON stdin (lido uma vez) / stdout + O_EXCL CAS| First-block-wins; cada policy fail-open: erros não-PROTECTED → allow; `.dadaia/sessions/**` PROTECTED → fail-closed (SEC-01); live-foreign lease (TTL-fresh ou pid-vivo) → block; READ-mode → block non-acquiring; context-slug derivado PATH-first do write target; pid-probe injetado pelo hook; latência appendada em hook-latency.jsonl
PostToolUse hook| `python -m dadaia_workspace.hooks.sdd_post_gate` + `lease.py`| JSON stdin (session_id harness-native)| Renova heartbeat via by-session index (sem full scan; nunca via DADAIA_CONTEXT→first-ALIVE); roda o reconciler advisory (nunca bloqueia); fail-open exit 0
git chokepoints| `pre-commit-lease-gate.sh` / `pre-push-ci-gate.sh` → `dadaia ci pre-commit-check` / `ci preflight` + `ci push-gate-check`| git hook (stdin ref lines no pre-push)| Pre-commit: cadeia DP-4 (zero-false-block; indeterminado/holder-pid-morto ⇒ ALLOW+WARN advisory); pre-push: APPROVED security handoff com `metrics.commit_sha` por sha pushed; runner resolution fail-closed; independem de hooks de harness
features/spec_context/lease.py| `.dadaia/states/ctx_locks/<ctx>.lock.json` + `ctx_locks/by-session/<sid>.json`| Single-record JSON TTL-lease; O_EXCL CAS em acquire E renew; index na mesma transação| `LEASE_TTL_SECONDS` (single home `core/kernel_tunables.py`; piso 120) + PID veto (`core/lock_liveness.is_stale`); holder-safe past TTL; pointer I/O via `session_identity`
features/spec_context/session_identity.py| `.dadaia/sessions/runtime/*.ptr` + `.dadaia/sessions/<id>.json`| Single-owner module| Único reader/writer dos pointers e session records; consumido por lease, hooks, bind CLI e doctor GC; coerência validada por SPEC-DOC-029
hooks/* + features/spec_context/{lease,gate_policy}.py + ci chokepoint backends| `core/kernel_tunables.py`| Import-linter leaf contract (`setup.cfg`)| Single home das constantes do kernel (lease TTL, GC TTLs, CAS retries, sentinel TTL, throttle do reconciler); constantes puras zero I/O; o contrato garante que `kernel_tunables` é leaf (não importa de nenhuma camada) e que hooks/features importam os valores de lá; `lease.LEASE_TTL_SECONDS` re-exportado por uma release
features/telemetry/aggregator/queries.py| features/telemetry/aggregator/runtimes.py| RuntimeAdapter protocol + registry| `TelemetryAggregator` mantém registry `{runtime: RuntimeAdapter}` e delega enrichment per row + liveness per runtime.

## Estado runtime

Locais canônicos de estado em disco e seu propósito:

  * `.dadaia/states/spec_contexts.json` — todos os Spec Context Projects (`schema_version: "2"`; state ALIVE/DEAD; sem flag global de contexto; campos `alive_since` e `dead_since`).
  * `.dadaia/states/.ws_lock` — fcntl workspace-wide lock (gitignored; criado em runtime; Lock 1 — serializa mutações em `spec_contexts.json`).
  * `.dadaia/states/ctx_locks/<slug>.lock` — fcntl per-context lock (gitignored; Lock 2 — serializa git clone/rmtree).
  * `.dadaia/states/ctx_locks/<ctx>.lock.json` — single-record JSON TTL-lease; schema `{context, release, session_id, mode, pid, acquired_at, heartbeat, ttl}`; acquire e renew via O_EXCL CAS; staleness = TTL piso + PID veto.
  * `.dadaia/states/ctx_locks/by-session/<sid>.json` — by-session heartbeat index; escrito/removido na mesma transação CAS do lock record; renovação PostToolUse O(1).
  * `.dadaia/states/bind_epoch/<ctx>` — bind-epoch marker escrito por `dadaia context bind`; trigger e fonte de descoberta da injeção bind-driven de contexto.
  * `.dadaia/states/ctx_locks/<ctx>.lock.sentinel` — CAS sentinel file (transient; criado e deletado atomicamente durante acquire/renew).
  * `.dadaia/sessions/runtime/<ctx>.ptr` — stable-session-identity pointer (lease incumbent); contém `session_id` do holder; RENEW incondicionalmente quando match. I/O exclusivo via `session_identity.py`.
  * `.dadaia/sessions/runtime/<session_id>.ptr` — pointer de sessão do ctx-inject (idempotência de injeção). I/O exclusivo via `session_identity.py`.
  * `.dadaia/sessions/<id>.json` — session record CLI-owned (`session_id`, `context`, `mode`, `release`, `pid`, `bound_at`, `last_seen_at`, `ttl_seconds`); escrito por `dadaia context bind` via `session_identity`; lido pelo gate (resolução de modo), pelo `sdd_post_gate` (refresh `last_seen_at`) e pelo Kanban do panel.
  * `.dadaia/logs/lock-events.jsonl` — audit log append-only (O_APPEND; eventos: acquire, release, steal, HEARTBEAT, RECONCILER_FLAG).
  * `.dadaia/logs/hook-latency.jsonl` — telemetria de latência de hook (`{ts, hook, event, duration_ms}` por invocação de `pre_gate`; best-effort, fail-open).
  * `.dadaia/agentic/<type>/` — staging de assets (snapshot imutável).
  * `.dadaia/agentic/manifest.json` — registro do que foi propagado para cada tool.
  * `dadaia_workspace/hooks/` — Python package de governança (8 módulos); única implementação dos hooks de harness; UM comando PreToolUse por runtime (`pre_gate`), registrado em `.claude/settings.json` e `.codex/hooks.json` por `infrastructure/runtime_config.py`; os shell assets são exclusivamente os git chokepoints (`pre-commit-lease-gate.sh`, `pre-push-ci-gate.sh`), instalados em `.git/hooks/` por `dadaia ci install-hook`.
  * `.dadaia/reports/<context>/<agent>/*.html` — reports HTML produzidos por especialistas; consumidos por `project-manager` no Discovery e por `project-auditor` nas auditorias.
  * `.dadaia/handoff/<context>/*.handoff.json` — agent↔agent JSON handoffs (canal 2 dos 3 canais).
  * `.dadaia/states/report_retention.json` — important-mark set para report retention; keys são caminhos workspace-relativos.
  * `.dadaia/states/root_exceptions.txt` — lista de entradas de root permitidas além do whitelist canônico.
  * `specs/releases/ACTIVE.md` — release ativa + phase.
  * `specs/audits/<ts>-<session_id_8chars>/` — audit results committados (canal 3 dos 3 canais; project-auditor).
  * `specs/memory/*.md` — memory atômica (Markdown + frontmatter YAML; rendered in-memory pelo panel via mistune).
  * `specs/memory/product/catalog.json` — gerado por `generate-memory-catalog.py` a partir do frontmatter dos `.md`; committed; índice machine-readable.
  * `specs/_archive/releases/<id>/` — releases concluídas com CLOSURE.
  * `specs/_archive/<release-id>/consumed_backlog.json` — sidecar JSON machine-readable (um por release arquivada; entries `{slug, shipped_anchors[]}`) lido por `backlog doctor` BL-STALE via exact slug membership; escrito por `ledger_writer.write_consumed` (v0.1.26) via a facade `BacklogRemovalLifecycle`. **Producer wiring na superfície real de release-definition é resíduo R2 (`wire-consumed-ledger-producer-at-release-definition`)** — em produção o sidecar ainda não é emitido. Ausência = no-op (sem false ERROR).
  * `specs/_archive/<release-id>/consumed-backlog/<slug>.md` — cópia durável de um item de backlog full-removed no closure (escrita por `removal.apply_removal` ANTES do unlink — ADR-C copy-before-remove; backlog é gitignored, então esta é a única cópia sobrevivente de um registro de segurança CRITICAL).
  * `.dadaia/states/backlog_subject_aliases.txt` — alias map do backlog mantida pelo operador (uma linha `synonym -> canonical-anchor`); lida por path injetado; em R1 é o único caminho de binding para subjects `panel`/`api`.

**Stores que não existem (não recriar):** `.dadaia/locks/implementation/<ctx>__<release>.json` (Lock 3), `.dadaia/states/ctx_locks/<ctx>.semaphore.json` (semaphore / Lock 4), `.dadaia/logs/semaphore-reclaims.jsonl`, marcador global de contexto, e qualquer script bash de gate em `.dadaia/scripts/`. O mutex MUTATING é exclusivamente o TTL-lease em `.dadaia/states/ctx_locks/<ctx>.lock.json`; o session record `.dadaia/sessions/<id>.json` não é mecanismo de locking — carrega identidade/modo da sessão (lido pelo gate para resolução de modo) e alimenta o Kanban.

## Memory injection subsystem

O subsistema garante que agentes nunca iniciam trabalho sem contexto de produto. Opera nos runtimes de entrada de Layer 1 — Claude Code e Codex (hook `ctx_inject`); o harness de entrada PI (`pi`) lê `AGENTS.md`/`CLAUDE.md` nativamente up-tree (sem hook de injeção de Layer 1). O harness set de Layer-1 é `{claude, codex, pi}` — **OpenCode foi removido em v0.1.24**. PI também roda como worker de Layer 2 headless (`PI_HEADLESS`) sem hook de entrada — ver "Two-layer agentic model" abaixo.

### Lean payload

O bootstrap injetado é **tech-stack + catalog apenas** (~2.400 tokens). `architecture.md` é intencionalmente não injetado — é large e é self-pulled pelos agentes antes de qualquer trabalho arquitetural ou cross-layer, exatamente como feature atoms são pulled on demand.

### ctx_inject hook (Claude Code + Codex)

`python -m dadaia_workspace.hooks.ctx_inject` — módulo do pacote de hooks Python. Em Codex roda no `SessionStart` (matcher `startup|resume`) carregando o contexto completo **uma vez por sessão**; em Claude Code roda no `UserPromptSubmit`. Os hooks podem disparar a cada prompt, mas a injeção completa ocorre só uma vez por sessão lógica. (PI lê a law nativamente up-tree, sem hook de injeção de Layer 1.)

A injeção é **bind-driven** (DP-2, v0.1.14): `dadaia context bind` escreve o marker
standalone `.dadaia/states/bind_epoch/<ctx>` e é o ÚNICO trigger de injeção de
context-memory. O first-ALIVE foi deletado da cadeia de injeção (permanece apenas na
resolução de lease-context do gate). O hook:

1. Resolve o contexto: `DADAIA_CONTEXT` env → session record self-keyed (contexto bound) → **marker bind-epoch mais novo que o sentinel desta sessão** (o marker carrega o slug; é o caminho harness-real, já que o sid do bind-CLI ≠ sid do harness) → **preflight genérico apenas** (preflight de dispatcher + lista de contexts ALIVE; SEM context memory).
2. Resolve um `SESSION_ID` **estável** (env harness-native `CLAUDE_CODE_SESSION_ID`/`CODEX_SESSION_ID`/`OPENCODE_SESSION_ID`, depois o `session_id` do payload stdin; sem fallback de PID) e o sanitiza antes de usá-lo como componente de filename. Verifica o sentinel de first-message keyed nesse id. Re-injeta quando (a) não há sentinel para o sid, ou (b) um marker bind-epoch é mais novo que o mtime do sentinel (re-bind para outro contexto re-injeta; o sentinel é estampado com o slug injetado). Marker pré-existente nunca binda sessão fresca — sem sentinel, a cadeia cai no preflight genérico (que estampa o sentinel). Caso contrário, **não emite nada** e sai.
3. Cria/estampa o sentinel (pointer de sessão via `session_identity`) e emite o payload completo dentro de bounded markers:

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

## Backlog-consistency subsystem (`features/backlog/`, v0.1.25)

O backlog é mantido como um **SET deduplicado, conflict-free e não-stale**, enforçado
**mecanicamente** — não por julgamento de modelo nem por vigilância humana/de agente (ambos
já falharam e corromperam um projeto). O subsistema vive em `dadaia_workspace/features/backlog/`
(módulos puros, roots sempre injetados, espelhando `features/ci_preflight/`).

**Item schema — `intents[]`.** Todo item de backlog carrega frontmatter `intents[]`, onde
cada intent é `Subject{kind, ref} → change`. `Subject` e `Intent` são dataclasses frozen
puras em `core/models/backlog.py`; `kind ∈ {code, api, cli, panel, doc, invariant, catalog}`
e `ref` é uma **referência tipada, nunca free text**. Refs de `code` são sempre
**module-relative** `path#symbol` (ex. `dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind`)
— a registry rejeita paths absolutos/operator-local e nomes de repo privado de qualquer
intent committado (privacy).

**Registry canônico de subjects (a linchpin) — `subject_registry.py`.** **Auto-derivado,
recomputado a partir da verdade viva a cada run** — nunca um arquivo de registry armazenado
(que iria ele mesmo ficar stale, a meta-versão do bug que corrigimos). R1 auto-deriva
exatamente **cinco** kinds de anchor, cada um lastreado por um registry-of-truth real na
árvore viva: `code` (`path#symbol` validado por walk AST com fallback grep), `cli` (ids de
comando do Typer app-tree), `catalog` (slugs de `specs/memory/product/catalog.json` + ids de
atom), `doc` (ids spec-doc `SPEC-DOC-NNN` + heading anchors de memory), `invariant` (`INV-*`
nomeados). **`panel`/`api` NÃO são auto-deriváveis em R1** (não há route registry de onde
derivar; grep-derivá-los seria a heurística fuzzy que este design rejeita) — ligam **apenas**
pela alias map; auto-derivação desses kinds é diferida para R2. Mais um **alias map** mantido
pelo operador em `.dadaia/states/backlog_subject_aliases.txt` (uma linha
`synonym -> canonical-anchor`), lido por **path explicitamente injetado** (nunca cwd), que
colapsa sinônimos a um anchor canônico — e, em R1, é o único caminho de binding para
`panel`/`api`. **Contrato de binding:** o modelo **propõe** uma string de subject; Python
normaliza + **liga** a um anchor de registry e **HALTa (rejeita, não silent NEW)** qualquer
intent cujo subject resolva para nenhum anchor ou um set ambíguo.

**Classificador determinístico fail-closed — `classifier.py`.** Python é dono da fronteira
UNRELATED/CONFLICT via **set-intersection de anchors canônicos**; o modelo nunca decide
UNRELATED-vs-não. Intersecção vazia → `UNRELATED` (final, sem chamada de modelo); mesmos
anchors + mesma change → `DUPLICATE`; **anchor compartilhado + change divergente** defaulta
**fail-closed** a `DIVERGENT_CONFLICT` (o gêmeo perigoso). O modelo só pode **downgrade**
(para `OVERLAP`/`SUPERSEDES`) com um merge explícito, estruturado e provado-compatível —
nunca pode *perder* um conflito, porque same-anchor+differing-change defaulta a conflito. R1
embarca o **core determinístico** (steps 1–2 + o default fail-closed); a seam de
model-adjudication é exposta mas **OFFLINE** em R1 (um `Callable` defaultando a "no
downgrade") — R2 exercita o step de modelo dentro do workflow.

**`dadaia backlog doctor` (o backstop ENFORCED) — `doctor.py`.** Postura honesta
oriented-vs-enforced: `specs/backlog/` é gitignored + ADDITIVE, então a gate PreToolUse/lease
NÃO classifica um arquivo de backlog hand-written como MUTATING — o **workflow (R2) é o
happy-path ORIENTED; o doctor no chokepoint git é o ENFORCEMENT real**. Um único engine de
check **parametrizado** (sem fan-out copy-paste) emite quatro check codes (StrEnum):
**BL-SCHEMA** (todo item tem `intents[]` ligado + status válido), **BL-DUP** (dois itens
compartilham anchor-set + change → ERROR), **BL-CONFLICT** (dois itens compartilham um anchor
com change incompatível → ERROR — o gêmeo divergente, apanhado mesmo se hand-written),
**BL-STALE** (um slug listado no ledger `consumed_backlog` de qualquer release arquivada que
ainda existe em `specs/backlog/` → ERROR). `run_backlog_doctor(*, specs_dir, source_root,
catalog_path, alias_map_path, archive_root)` — todos os paths injetados. Wiring: `backlog
doctor` roda no **pre-commit chokepoint** (ao lado dos checks lease/CI existentes, via o
backend `dadaia ci pre-commit-check`) e em **CI** (`ci.yml`), mirrorando o padrão
`ci preflight` — um gêmeo divergente hand-written é **rejeitado no commit**, fechando o
bypass gitignore/ADDITIVE. Superfície read-only de resolve/preview (`preview.py`):
`dadaia backlog subjects` (lista o anchor set vivo, opcional `--kind`/`--resolve "<ref>"`) e
`dadaia backlog doctor --explain` (mostra como um subject proposto resolve: anchor ligado, ou
`UNRESOLVED`/`AMBIGUOUS` + candidate set + sugestão de alias) — nunca escreve um arquivo de
backlog ou a alias map.

**Ledger `consumed_backlog` — `ledger.py` (reader) + `ledger_writer.py` (writer, v0.1.26).**
BL-STALE liga a um **ledger estruturado** fixado a um **sidecar JSON machine-readable** em
`specs/_archive/<release-id>/consumed_backlog.json` (um arquivo por release arquivada;
entries `{slug, shipped_anchors[]}` keyed pelo set de subject-anchors verificado realmente
shipado) e casa por **exact slug membership** — substituindo a heurística de prosa
SPEC-DOC-031. `read_consumed(archive_root)` varre todos os
`specs/_archive/*/consumed_backlog.json` por membership exata e **tolera ausência** (sem
ledger arquivado → BL-STALE é no-op, nunca false ERROR). O writer (`write_consumed`, v0.1.26)
emite exatamente essa shape de reader; roots injetados; anchors module-relative.

**Workflow `backlog_definition` + removal-on-release (v0.1.26).** O happy-path ORIENTED
existe: `features/lifecycle/workflows/backlog_definition.py` é o corpo §4 da workflow
(`intake_grill → subject_bind → existing_backlog_review → reconcile_decision →
conflict_resolution_grill → backlog_author → backlog_review_gate`), mirror estrutural de
`release_definition.py`, com **gates Python-owned**, atrás de `dadaia lifecycle backlog
define` (container factory `build_backlog_definition_workflow`; LAW 1 `{pi,codex,fake}`,
LAW 2 modelo discreto). O step `existing_backlog_review` **roda o classifier R1 live**:
Python dispõe todo veredito determinístico; o modelo é invocado **só** pela seam `downgrade`
para um par same-anchor differing-change e **só para downgrade com evidência** (fail-closed →
`DIVERGENT_CONFLICT`) — a seam que R1 embarcou OFFLINE agora é exercitada end-to-end. O
selector `backlog_index` (frontmatter-only, paths injetados) alimenta os steps de review com
os bound intents + status de cada item. Os fragments reais
(`public/lifecycle_fragments/backlog_definition/{intake_grill,conflict_scan,conflict_resolution_grill,backlog_authoring}.md`)
substituíram o stub `_README.md` e são staged/installed.

O **mecanismo** de removal-on-release existe: o writer (`ledger_writer.py`), o hook de
closure residual-aware (`removal.py` — rewrite-down-to-residual default; full removal só a
zero residual, com cópia durável em `_archive/<release>/consumed-backlog/<slug>.md` ANTES do
unlink), e a facade `BacklogRemovalLifecycle` (`removal_lifecycle.py`) ligando producer
(`consume_at_release_definition`) e consumer (`remove_at_closure`). **O lado de closure
(`remove_at_closure`) está wired em `dadaia lifecycle close`; o lado producer
(`consume_at_release_definition`) ainda NÃO está wired na superfície real de
release-definition** — em produção nada escreve o ledger ainda, então `remove_at_closure`
lê um ledger vazio e no-opa, e o loop BL-STALE está provado só a nível
função/integração (`tests/integration/test_backlog_removal_loop.py`), **não end-to-end em
release real**. Wiring do producer (depende de uma convenção de declaração-de-consumo no
release) é o resíduo R2, rastreado em
`specs/backlog/wire-consumed-ledger-producer-at-release-definition.md`
(`FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01`, HIGH).

## Multi-harness runtime parity (constitution §4)

### Two-layer agentic model

dadaia-workspace runs agents at **two distinct layers**, and "harness" means a
different thing at each. Conflating them is the source of most parity confusion.

```mermaid
flowchart TB
    OP(["Operator no terminal"])
    subgraph L1["LAYER 1 — entry harness (terminal)"]
        direction LR
        CC["claude"]:::h
        CX["codex"]:::h
        PIe["pi"]:::h
    end
    GOV["Governança Layer 1:<br/>AGENTS.md up-tree + projeções .claude/ .codex/ .pi/<br/>PreToolUse pre_gate (onde suportado) + git chokepoints"]
    CLI["dadaia lifecycle &lt;verb&gt; --harness {pi|codex|fake} --model &lt;id&gt;<br/>(dadaia-workflow: corpo Python + fragments + gates)"]
    subgraph L2["LAYER 2 — worker harness (AgentRuntimePort) — LAW 1: pi/codex/fake"]
        direction LR
        FK["FAKE<br/>in-process"]:::w
        CXk["CODEX_EXEC<br/>codex exec"]:::w
        PIk["PI_HEADLESS<br/>pi --mode json"]:::w
        CLk["CLAUDE_SDK<br/>SDK · Ring-1 · kept, NOT um workflow harness"]:::x
    end
    OP --> L1
    L1 --> GOV
    L1 -->|"o harness invoca a CLI dadaia"| CLI
    CLI --> L2
    L2 -->|"Ring-2: git-diff changed_paths + git chokepoints"| OUT(["produção: código · specs · memory"])
    classDef h fill:#1f6feb,color:#fff,stroke:#1f6feb;
    classDef w fill:#238636,color:#fff,stroke:#238636;
    classDef x fill:#6e7681,color:#fff,stroke:#6e7681;
```

A mesma palavra "harness" nomeia coisas diferentes em cada layer: no Layer 1 é o agente
de terminal que o operador inicia; no Layer 2 é um worker `AgentRuntimeKind` que o engine
dirige por step. PI aparece nos dois (entrada `.pi/` + worker `PI_HEADLESS`); FAKE existe
só no Layer 2. **OpenCode foi removido inteiramente em v0.1.24** (ambas as layers).

- **Layer 1 — entry harness (terminal).** The AI coding harness the operator launches
  in the workspace terminal: exactly `{claude, codex, pi}` (OpenCode removed in v0.1.24).
  Governance at this layer is `AGENTS.md` read up-tree natively + the projected `.X/`
  asset trees (`.claude/`, `.codex/`, `.pi/`) staged from `dadaia_workspace/public/` by
  `dadaia public install`. Deterministic enforcement at Layer 1 is per-entry-harness
  (PreToolUse hooks where supported + git chokepoints) — the table immediately below is
  the **Layer-1 entry-harness** enforcement parity, not the worker-runtime set.
- **Layer 2 — worker harness (inside the lifecycle engine).** The bounded agent workers
  that `dadaia lifecycle` drives per step behind `AgentRuntimePort`
  (`container.build_agent_runtime(kind, *, cwd, model)`), one harness selectable per step
  via `--harness` / `--step-harness`. The `AgentRuntimeKind` enum (`core/models/lifecycle.py`)
  is `FAKE`, `CODEX_EXEC`, `CLAUDE_SDK`, `PI_HEADLESS` (`OPENCODE_RUN` removed in v0.1.24).
  **LAW 1 (v0.1.24):** the selectable Layer-2 **workflow** harnesses are exactly
  `{pi, codex, fake}`. `CLAUDE_SDK` is **kept in code and unit-tested** (Layer-1 Claude is
  unaffected) but is **NOT a selectable workflow `--harness`** — `claude` is rejected with a
  Layer-1 pointer, because running Claude as a Layer-2 worker would spend credits outside
  the operator's subscription. The transport differs per harness: **SDK** (Claude —
  in-process `claude_sdk_runtime.py`, the only adapter with a real Ring-1 write boundary via
  `core/scope_match`) and **CLI-headless** (Codex `codex exec`, PI `pi --mode json` —
  subprocess-backed, one-shot per step). RPC stays dropped (ADR-23-1, carried forward). The
  factory is total over the enum; `core/`/`features/` stay provider-agnostic. See
  [[lifecycle-foundation]] for the engine spine.
- **LAW 2 (v0.1.24) — discrete per-harness GPT model catalog.** Each Layer-2 workflow
  harness has a discrete model catalog selected on the CLI (`--model` / `--step-model`),
  validated against the chosen harness's set; an invalid `(harness, model)` pair is rejected
  with the valid set. **pi → 3 models:** `(gpt-5.5, high)`, `(gpt-5.5, low)`,
  `(gpt-5.3-codex, medium)`. **codex → 2 models:** `(gpt-5.5, high)`, `(gpt-5.5, medium)`.
  Both catalogs are **GPT-only** by construction (PI runs on the operator's Codex
  subscription → GPT ids): no `claude-*` id (including the region-restricted
  `claude-fable-5`) is **ever** selectable at Layer 2. The catalog is explicit GPT data
  keyed by harness (`core/harness_models.py`), consistent with — but not a tier-view of —
  `core/model_registry.py`; PI honors the model (`pi --model <id>`), Codex takes the
  discrete `(id, effort)`.

A harness can exist at one layer and not the other. PI ships as a real **Layer-2**
worker (`PiHeadlessAdapter`, wired in `container.py`, Ring-2 only) and a **Layer-1** `.pi/`
projection that, post-v0.1.18, points at the law and, post-v0.1.21 (WS-PI-4), carries a
real **Ring-1** SDD-gate extension (`.pi/extensions/dadaia-sdd-gate.ts`): PI's CLI exposes
a genuine pre-disk hook (an extension `tool_call` handler can block a write before it
executes), and the extension delegates write/edit to the same Python `pre_gate` the other
harnesses use. The block is **active once the operator grants `.pi/` trust** (the assets
are post-trust executable). Note the two PI layers differ: the Layer-2 `PI_HEADLESS`
worker keeps Ring-2 + chokepoints; the Layer-1 interactive `pi` gains the post-trust Ring-1.

### dadaia-workflows + prompt-fragment library (Layer-2, v0.1.24)

Os verbos de `dadaia lifecycle` são os **dadaia-workflows** canônicos: cada um é um corpo
Python que (1) importa **prompt fragments** de `dadaia_workspace/public/lifecycle_fragments/`
(Markdown + frontmatter `id/role/workflow/step/static_inputs/dynamic_inputs/output_schema/
max_context_policy`, carregados/validados por `features/lifecycle/fragments/loader.py`,
projetados + manifest-tracked), (2) seleciona contexto dinâmico via
`features/lifecycle/context_selector.py` (selectors de memory atoms, catalog, backlog,
bugs, audits, release artifacts, source summaries, diffs, test outputs, prior handoffs;
políticas `exact-files-only`/`summary`/`catalog-only`/`diff-only`/`previous-handoff-only`),
(3) chama um worker `(harness, model)` discreto, e (4) avança **gates Python-validados** —
o modelo recomenda, o Python decide a legalidade da transição e **bloqueia em handoff
ausente/rejeitado**. A primeira workflow migrada end-to-end onto fragments é a
**release-definition** (`features/lifecycle/workflows/release_definition.py`): seu prompt
por step é `role + fragment bundle + dynamic context + output schema`, não mais o sufixo
genérico. Cada run record persiste a composição do prompt por step (fragment ids, refs de
contexto dinâmico, `prefix_hash`, modelo discreto, runtime kind, output schema, gate
result) para observabilidade. Workflows backlog/audit/research/bug-report estão
**scaffolded + fail-loud** (`NotImplementedError("deferred to follow-up release")`),
explicitamente diferidas. A garantia de **harness-universalidade** é comportamental: o
`output_schema` de cada fragment shipped passa pelos parsers PI (fenced-json/`message_end`)
e Codex (`--output-last-message`) via fixtures FAKE com extração de verdict idêntica
asseverada; a denylist de tokens harness-específicos é lint secundário.

### Layer-1 entry-harness enforcement parity

| Runtime | PreToolUse hooks (`pre_gate`) | Git chokepoints | Postura |
|---------|-------------------------------|-----------------|---------|
| Claude Code | sim — `python -m dadaia_workspace.hooks.pre_gate` (matcher `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash`) | sim | determinístico: hooks + chokepoints |
| Codex interativo (TUI) | sim — `pre_gate` em `.codex/hooks.json` (matcher `^(apply_patch\|Edit\|Write\|Bash)$`) | sim | determinístico: hooks + chokepoints |
| Codex headless (`codex exec`) | **não — exec não dispara hooks** (defeito upstream codex-cli 0.139.0, live-verificado) | sim | **chokepoints only** |
| PI (`pi`) | **sim (post-trust)** — `.pi/extensions/dadaia-sdd-gate.ts` `tool_call` hook mapeia write→Write/edit→Edit e delega ao `pre_gate` (WS-PI-4); ativo quando o operador concede trust a `.pi/` | sim | determinístico post-trust + chokepoints; `.pi/**` é post-trust executable |

(OpenCode foi removido como entry harness em v0.1.24 — o harness set de Layer-1 é
exatamente `{claude, codex, pi}`.)

Codex-specific behavior é expresso em termos Codex-nativos: `AGENTS.md` context, `.codex/config.toml`, `.codex/skills`, hooks onde suportados, e deferred tool discovery para multi-agent capability.

### Layer-2 worker-runtime posture (`AgentRuntimePort`)

| AgentRuntimeKind | Adapter | Transport | Ring-1 write boundary | Layer-2 workflow harness? |
|------------------|---------|-----------|------------------------|---------------------------|
| `FAKE` | `fake_runtime.py` | in-process | n/a (test/offline) | sim (`fake`) |
| `CODEX_EXEC` | `codex_runtime.py` | CLI-headless (`codex exec`) | não | sim (`codex`) |
| `PI_HEADLESS` | `pi_runtime.py` | CLI-headless (`pi --mode json`) | não | sim (`pi`) |
| `CLAUDE_SDK` | `claude_sdk_runtime.py` | SDK (in-process) | **sim** — `core/scope_match` | **não** — kept/tested, mas `claude` é rejeitado como `--harness` (LAW 1) |

Apenas `CLAUDE_SDK` enforça hoje um Ring-1 real; os demais workers são one-shot por step.
**LAW 1 (v0.1.24):** as harnesses **workflow** selecionáveis no Layer 2 são exatamente
`{pi, codex, fake}` — `claude` é rejeitado com um Layer-1 pointer (o adapter SDK permanece
importável + unit-tested para uso de Layer-1). `OPENCODE_RUN` foi removido inteiramente em
v0.1.24. Transporte RPC permanece dropado (ADR-23-1; engine é one-shot-per-step).
Selecionável por step via `--harness`/`--step-harness` + modelo discreto via
`--model`/`--step-model` (LAW 2; `cli/commands/lifecycle.py` `_HARNESS_KINDS` +
`core/harness_models.py`).

**path-scope (disciplina, não gate)** — `paths.write_allowlist` do frontmatter dos agentes é **convenção de instrução de agente** (workspace-protocol §6), não enforcement do gate: nenhum hook conhece a persona do processo que escreve. O que o gate PreToolUse enforça deterministicamente é path-class × lease × fase × modo sobre os write tools. A divisão de superfície (`ai-engineer` dono de `dadaia_workspace/public/{skills,rules,workflows,commands,agents}/**`; `software-engineer` dono do código Python, incluindo `dadaia_workspace/hooks/*.py`) é mantida por disciplina de persona e review.

**rules folder** — 8 arquivos canônicos públicos: `workspace-protocol.md`, `tmp-file-guardrail.md`, `plugin-scope.md`, `dadaia-workspace-dev-guardrail.md`, `harness-skill-scope.md` (restringe `ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering` ao `ai-engineer`; `harness-primitives` é explicitamente não-restrita), `bug-registration-guardrail.md`, `backlog-ownership.md`, `release-governance.md`.

## Evidências visuais

Diagramas de classe e screenshots da CLI vão sob `specs/assets/architecture/`. Atualmente sem assets — primeira batch virá em release subsequente.
