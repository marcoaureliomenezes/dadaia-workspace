# Auditoria de Arquitetura — Multi-Agent Orchestration

> Data: 2026-05-15
> Repo: `dadaia-workspace`
> Escopo: feature `multi-agent-orchestration` (v0.1, implementada em 2026-05-14)
> Veredito: **CONDITIONAL PASS** — arquitetura sólida, mas com 2 bugs de correção (CRITICAL/HIGH) e gaps importantes de teste E2E

---

## 1. Como funciona hoje

### 1.1 Arquitetura geral (visão de camadas)

A feature segue rigorosamente a regra de dependências `CLI → Features → Core ← Infrastructure`, com um único composition root em `container.py`:

```
┌───────────────────────────────────────────────────────────────┐
│ CLI (Typer)                                                   │
│   dadaia_workspace/cli/commands/orchestrate.py                │
│   - list / show / run / status / resume                       │
│   - resolve_workspace(), resolve_context(), parse_inputs()    │
└──────────────────────────┬────────────────────────────────────┘
                           │ chama container.build_orchestration_service()
                           ▼
┌───────────────────────────────────────────────────────────────┐
│ Composition Root                                              │
│   dadaia_workspace/container.py                               │
│   build_orchestration_service(workspace_root, runtime=?)      │
│   ↳ MarkdownWorkflowStore + JsonRunStateStore +               │
│     _select_dispatcher(runtime) → OrchestrationService        │
└──────────────────────────┬────────────────────────────────────┘
                           ▼
┌───────────────────────────────────────────────────────────────┐
│ Feature: orchestration                                        │
│   features/orchestration/service.py    OrchestrationService   │
│   features/orchestration/runner.py     DAG helpers (puros)    │
│   features/orchestration/resolver.py   InputResolver (puro)   │
└──────────────────────────┬────────────────────────────────────┘
                           │ depende SOMENTE de Protocols
                           ▼
┌───────────────────────────────────────────────────────────────┐
│ Core (domínio + contratos)                                    │
│   core/models/workflow.py       WorkflowDefinition,           │
│                                 WorkflowStage, …              │
│   core/models/run_state.py      RunManifest, StageState,      │
│                                 RunEvent, StageInvocation     │
│   core/protocols/workflow_store.py                            │
│   core/protocols/run_state_store.py                           │
│   core/protocols/agent_dispatcher.py                          │
│   core/exceptions.py            WorkflowSchemaError,          │
│                                 RunNotFoundError, …           │
└───────────────────────────────────────────────────────────────┘
                           ▲
                           │ implementa Protocols
┌──────────────────────────┴────────────────────────────────────┐
│ Infrastructure (adaptadores)                                  │
│   infrastructure/markdown_workflow_store.py   → WorkflowStore │
│   infrastructure/json_run_state_store.py      → RunStateStore │
│   infrastructure/claude_agent_dispatcher.py   → AgentDispatcher (native) │
│   infrastructure/cli_agent_dispatcher.py      → AgentDispatcher (cli, opencode, codex) │
└───────────────────────────────────────────────────────────────┘
```

Conformidade com Hexagonal/Ports-and-Adapters: **correta** com uma única exceção (ver finding CRITICAL #1).

### 1.2 Componentes principais e responsabilidades

| Camada | Módulo | Responsabilidade |
|---|---|---|
| Core (modelos) | `core/models/workflow.py` | Dataclasses frozen do workflow declarado: `WorkflowDefinition`, `WorkflowStage`, `StageInputBinding`, `StageExpectedOutput`, `StageGate`, `WorkflowInput`, `ExitCriterion`. |
| Core (modelos) | `core/models/run_state.py` | Dataclasses frozen do estado runtime: `RunManifest`, `StageState`, `RunEvent`, `StageInvocation`, `StageResult`, `DispatcherCapabilities`. Enums: `RunStatus`, `StageStatus`, `EventKind`, `DispatcherMode`. |
| Core (contratos) | `core/protocols/*.py` | 3 Protocols: `WorkflowStore`, `RunStateStore`, `AgentDispatcher`. |
| Feature | `features/orchestration/service.py` | `OrchestrationService` — orquestra start/resume; cliente direto das 3 Protocols. |
| Feature | `features/orchestration/runner.py` | Funções puras sobre o grafo: `topo_order`, `next_ready_stages`, `group_ready`, `build_invocation`, `update_stage_state`, `with_status`, `dispatch_stages`, `emit_event`. |
| Feature | `features/orchestration/resolver.py` | `resolve_stage_inputs` (mapeia bindings de input em valores concretos) + `render_output_path` (substitui templates). |
| Infrastructure | `markdown_workflow_store.py` | Parser YAML-frontmatter de `*.workflow.md`; validação de schema, ciclos, parallel_groups, agentes existentes. |
| Infrastructure | `json_run_state_store.py` | Persistência atômica do `manifest.json` (tmp + `os.replace`) e append-only `events.jsonl`. Gera `run_id` ULID-like. |
| Infrastructure | `claude_agent_dispatcher.py` | Modo `NATIVE`, `supports_parallel=True`. Escreve `invocation.md` no formato Claude. |
| Infrastructure | `cli_agent_dispatcher.py` | 3 adapters em um arquivo: `CliAgentDispatcher` (modo `CLI_ONLY`), `OpenCodeAgentDispatcher` (`BEST_EFFORT_SEQUENTIAL`), `CodexAgentDispatcher` (`UNSUPPORTED`). |
| CLI | `cli/commands/orchestrate.py` | Typer subcomandos `list / show / run / status / resume` + `--json`/`--dry-run`. |

### 1.3 Ciclo de vida de um workflow run

Trace completo do operador-comando até a primeira invocation:

```
operador
  └── $ dadaia orchestrate run spec-refinement --runtime claude --input ...
       │
       ├── orchestrate.run() [cli/commands/orchestrate.py]
       │     ├── _resolve_workspace()        ─→ descobre workspace_root via .dadaia/
       │     ├── _resolve_context()          ─→ flag > DADAIA_CONTEXT > primary_context.json
       │     ├── _parse_inputs(--input k=v)
       │     └── container.build_orchestration_service(root, runtime)
       │            ├── _guard_initialized()              valida .dadaia/states/spec_contexts.json
       │            ├── MarkdownWorkflowStore(...)        agent_catalog descoberto on-the-fly
       │            ├── JsonRunStateStore(.dadaia/runs)
       │            ├── _select_dispatcher(runtime)       → ClaudeAgentDispatcher
       │            └── OrchestrationService(...)
       │
       └── service.start_run(name, context=, runtime=, inputs=)
             ├── workflow = workflow_store.get(name)                ─→ parse + validate
             ├── run_id  = make_run_id(clock)                       (timestamp-hex6)
             ├── manifest = RunManifest(status=RUNNING, stages=[all PENDING])
             ├── runs.create_run(manifest)                          → manifest.json + events.jsonl tocado
             ├── emit_event(RUN_STARTED)
             └── self._advance(workflow, manifest)
                   ├── ready = next_ready_stages(wf, manifest)      → stages cujas deps estão COMPLETED
                   ├── for group in group_ready(ready):
                   │      ├── build_invocation() para cada membro  (resolve_stage_inputs, render path)
                   │      ├── update manifest: RUNNING + emit STAGE_STARTED
                   │      ├── runs.update_manifest(manifest)        ← snapshot intermediário
                   │      ├── dispatch_stages(dispatcher, group)    → escreve invocation.md
                   │      └── update manifest: AWAITING_GATE +
                   │           emit GATE_PENDING (output_path ← invocation_path) ⚠ ver CRITICAL #2
                   └── with_status(AWAITING_GATE) + update_manifest
```

Quando o operador (ou o host agent) terminou o stage e escreveu o artefato real, invoca:

```
$ dadaia orchestrate resume <run-id>
  └── service.resume_run(run_id)
        ├── if status == COMPLETED → noop
        ├── if status == AWAITING_GATE → _resolve_awaiting_gates()
        │      └── para cada stage AWAITING_GATE: status = COMPLETED,
        │          emit GATE_RESOLVED + STAGE_COMPLETED, status do run = RUNNING
        ├── if status == FAILED → _reset_failed_for_retry()
        │      └── stages FAILED voltam a PENDING
        └── self._advance(workflow, manifest)  (mesma máquina acima)
```

### 1.4 Formatos de dados

#### Workflow (`*.workflow.md`)

YAML-frontmatter + corpo Markdown livre. Validações estritas no parser:
- arquivo deve ter sufixo `.workflow.md` e stem case-insensitive == `name`;
- `name`, `description`, `version`, `schema_version`, `inputs`, `stages` obrigatórios no frontmatter;
- Cada stage: `id` (snake_case, único), `agent` (presente em `public/agents/`), `expected_output.path`;
- `needs` deve referenciar id existente; ciclos rejeitados via Kahn topo-sort (`WorkflowCycleError`);
- `parallel_group` rejeita: (a) deps entre membros do mesmo grupo, (b) gate em stage do grupo;
- inputs sem `default` e sem `required: true` rejeitados.

Templates suportados em `expected_output.path`: `{run_id}`, `{context}`, `{run_ts}`. **Aviso:** os 2 workflows seed (`tdd-cycle.workflow.md`) usam `{task_id}` — ver MEDIUM #1.

#### Run state (durável em `<workspace>/.dadaia/runs/<run_id>/`)

```
.dadaia/runs/
└── 20260514T122340Z-a3f1b7/
    ├── manifest.json          ← projeção atômica (tmp + os.replace)
    ├── events.jsonl           ← source of truth, append-only
    └── <stage_id>/
        └── invocation.md      ← preparado pelo dispatcher
```

`manifest.json` carrega: `run_id`, `workflow_name`, `workflow_version`, `context`, `runtime`, `status`, `started_at`, `finished_at`, `inputs`, `stages[]` (id, agent, status, started_at, finished_at, output_path, error).

`events.jsonl`: uma linha JSON por evento (`ts`, `run_id`, `kind`, `stage_id?`, `payload?`). Kinds: `run_started`, `stage_started`, `stage_completed`, `stage_failed`, `gate_pending`, `gate_resolved`, `run_completed`, `run_failed`.

`run_id` é ULID-like: `YYYYMMDDTHHMMSSZ-<6 hex chars>` (≤22 chars, ordenável).

### 1.5 Dispatchers disponíveis

| Runtime | Classe | Mode | supports_parallel | Comportamento |
|---|---|---|---|---|
| `claude` | `ClaudeAgentDispatcher` | `NATIVE` | True | Escreve `invocation.md` com header que diz ao host agent para disparar N `Agent` numa única mensagem. |
| `opencode` | `OpenCodeAgentDispatcher` | `BEST_EFFORT_SEQUENTIAL` | False | Escreve `invocation.md`; em `parallel_group`, adiciona nota: "OpenCode does not support true parallel...". |
| `codex` | `CodexAgentDispatcher` | `UNSUPPORTED` | False | Sequencial OK; lança `OrchestrationUnsupportedError` em `dispatch_parallel` com `parallel_group`. |
| `cli` | `CliAgentDispatcher` | `CLI_ONLY` | False | Default fallback. Escreve `invocation.md` para execução manual. |

Seleção: flag `--runtime` > env `DADAIA_AGENT_RUNTIME` > default `cli`.

---

## 2. Estado dos testes

### 2.1 Cobertura de testes unitários

| Arquivo | Foco | Avaliação |
|---|---|---|
| `tests/unit/test_workflow_schema.py` | Parser+validação YAML. 7 testes: valid, missing name, filename mismatch, unknown agent, ciclo, parallel_group com dep interna, get unknown. | **Sólido** — cobre as 6 regras de FR-ORCH-005. **Lacuna:** não testa rejeição de gate dentro de parallel_group; não testa input sem default sem required:true; não testa exit_criteria parse. |
| `tests/unit/test_run_state_store.py` | Persistência. 5 testes: create+load, events append-only, atomic update, list_runs, run_id único. | **Bom mas raso** — atomicidade só testa “sobrescrita funciona”, não testa crash entre tmp e replace; **não há teste de reconstrução de manifest a partir de events.jsonl** (NFR-ORCH-007 não validado). |
| `tests/unit/test_orchestration_runner.py` | Helpers puros. 15+ testes: topo_order linear/parallel/singleton; stage_by_id; next_ready_stages; group_ready; update_stage_state; resolver (workflow_input, default, stage_output, path, literal, kind desconhecido, render_output_path). | **Excelente cobertura dos puros** — provavelmente o melhor arquivo da suíte. |
| `tests/unit/test_orchestration_service.py` | Máquina de estados do service com fakes. 7 testes: start dispatcha só o primeiro; resume despacha parallel_group num batch; resume avança até completion; resume em completed é noop; workflow desconhecido; list_runs; reset de failed stages. | **Bom** — cobre os caminhos principais. **Lacunas críticas:** não testa `on_failure: continue`; não testa `stop_if_missing`; não testa workflow vazio; não testa `_maybe_complete` quando há stages PENDING mas nenhum ready (estado “órfão”). |
| `tests/unit/test_orchestration_runtime.py` | Dispatchers concretos paramétricos. 6 testes: capabilities por runtime; Claude escreve header parallel; CLI omite parallel; OpenCode marca best-effort; Codex rejeita parallel; Codex aceita sequencial. | **Sólido** — testa o contrato `DispatcherCapabilities` exaustivamente. |

**O que os unitários cobrem bem:**
- Parser + validação de schema (5 das 6 regras FR-ORCH-005)
- Funções puras (resolver e runner)
- Contratos de cada dispatcher concreto
- Máquina de estados happy-path do service
- Persistência básica do store JSON

**O que NÃO é coberto:**
1. **Reconstrução de manifest a partir de events.jsonl** (NFR-ORCH-007 + FR-ORCH-015): a SPEC promete isso explicitamente, **não há um único teste que valide essa propriedade**. Nem mesmo o método existe — `JsonRunStateStore` não tem `rebuild_manifest_from_events()`.
2. **Crash safety** do atomic write: nenhum teste simula crash entre `tmp.write_text` e `os.replace`.
3. **Idempotência real** de `resume`: o teste `test_resume_on_completed_run_is_noop` cobre só o caso terminal. Não testa: `resume` em estado RUNNING (sem gates resolvidos ainda).
4. **`on_failure: continue`** e **`on_failure: mark-needs-resume`**: a SPEC declara 3 opções, só `stop` é exercitado.
5. **`gate_resolved` event ordering** vs `manifest.json`: a SPEC (ADR-ORCH-003) diz "evento primeiro, manifest depois"; não há teste de ordem.
6. **`exit_criteria`**: declarado na SPEC e no schema, totalmente ignorado pelo runner. Não há teste — porque não há código.
7. **`must_include`** nos outputs: a SPEC promete validação de conteúdo no resume. Não há código nem teste.
8. **`stage_failed` event**: nunca emitido pelo service (search por `STAGE_FAILED`: zero matches em `service.py`).

### 2.2 Os "E2E" são E2E de verdade?

**Resposta direta: não.** Os arquivos em `tests/e2e/features/test_orchestration_pipeline.py` são **fluxos integrados em processo**, não E2E:

- Bootstrap real do workspace: `WorkspaceService.init()` cria `.dadaia/`.
- Stage + install **reais** via `FileSystemPublicAssetManager`.
- `OrchestrationService` instanciado via `container.build_orchestration_service(..., runtime="cli")` — usa `CliAgentDispatcher` real, que **escreve arquivos `invocation.md` de verdade**.
- Mas: **nenhum agente é invocado, em nenhum runtime.** O teste apenas chama `resume_run()` repetidamente e o service marca cada stage como COMPLETED no resume seguinte, sem nunca verificar se o artefato (`expected_output_path`) foi criado.

A SPEC US-ORCH-005 diz: “Dado uma run com status awaiting_gate, quando executo `dadaia orchestrate resume <run-id>`, então a CLI marca o gate como resolvido…”. O service hoje implementa isso assumindo cegamente que o operador fez o trabalho — não há validação de `must_include` nem de `expected_output_path` existir.

Os testes E2E confirmam que **o estado interno avança**, não que **a orquestração funcionou ponta a ponta**. Falta o "agente" real ou um substituto que escreva o artefato esperado entre `resume`s.

A integração `tests/integration/test_cli_orchestrate.py` é o que mais se parece com E2E real — invoca o Typer CLI via `CliRunner`, lê outputs, valida exit codes. Cobre 15 cenários (list, show, run happy/error, status, resume, dry-run, JSON). É a melhor camada de cobertura externa que existe hoje.

### 2.3 Gaps críticos de teste

| # | Gap | Impacto |
|---|---|---|
| G1 | Sem teste de reconstrução de manifest a partir de events.jsonl | NFR-ORCH-007 não validada — a "robustez" do append-only é teórica |
| G2 | Sem teste com agente real escrevendo artefato + resume → verificação | Não sabemos se uma run inteira funciona end-to-end |
| G3 | Sem teste de `must_include` validation (não há código para isso) | Operador pode fazer resume sem ter escrito nada e a run avança |
| G4 | Sem teste de race / concorrência (2 `resume` simultâneos no mesmo run_id) | Drift entre manifest e events em produção é possível |
| G5 | Sem teste de `parallel_group` no dispatcher Claude **escrevendo todos os invocation.md** simultaneamente em estrutura coerente | Header diz "dispatch all N in single message" mas nada checa que os N arquivos estão prontos antes do retorno |
| G6 | Sem teste de `on_failure: continue` / `mark-needs-resume` | 2 das 3 opções declaradas no schema não são usáveis (não há código) |
| G7 | Sem teste de timestamp/clock injetado afetando `run_id` ou `started_at` | O parâmetro `clock` existe em `OrchestrationService` mas nenhum teste o usa — determinismo não é exercitado |
| G8 | Sem teste de leitura de workflow com BOM / encoding diferente / linhas CRLF | Cross-platform não é validado |
| G9 | E2E não roda contra `--runtime claude` real (mesmo só preparando invocation.md, não validando que o `Agent` foi chamado) | Mode NATIVE é exercitado apenas em unit |

---

## 3. O que pode melhorar

### 3.1 Problemas de design / fragilidades arquiteturais

#### [CRITICAL] Layer violation: feature importa de infrastructure

- **Location:** `dadaia_workspace/features/orchestration/service.py:29`
- **Issue:** `from dadaia_workspace.infrastructure.json_run_state_store import make_run_id`. A feature `orchestration` importa um helper diretamente do módulo de infraestrutura, violando a regra de dependência declarada na arquitetura (`features` só pode depender de `core`).
- **Why it matters:** Esse é exatamente o tipo de import que destrói arquitetura sob crescimento. Hoje é um helper inocente; amanhã alguém em paralelo importa outro símbolo de `json_run_state_store.py` e em pouco tempo `service.py` está acoplado à implementação concreta de persistência, quebrando substituição via Protocol e testabilidade com fakes. Já fragiliza o teste unitário: `test_orchestration_service.py` usa `FakeRunStateStore` mas ainda assim ativa `infrastructure/json_run_state_store.py` indiretamente.
- **Trade-off if fixed:** Custa 1 linha — mover `make_run_id` para um lugar correto. Ganho: regra de camadas preservada, intent claro.
- **Recommendation:** Mover `make_run_id` para `dadaia_workspace/core/models/run_state.py` (é uma função pura de geração de id sobre `datetime`; pertence ao domínio) **ou** expor via `RunStateStore.new_run_id() -> str` no Protocol e mover a implementação para `JsonRunStateStore`. A primeira opção é mais simples e correta — `make_run_id` não tem nada de persistência.

#### [CRITICAL] `output_path` do stage aponta para a invocation, não para o artefato

- **Location:** `dadaia_workspace/features/orchestration/service.py:164`
- **Issue:** Após dispatch, `update_stage_state(..., output_path=inv.invocation_path)` armazena o caminho do arquivo de instrução (`runs/<run-id>/<stage>/invocation.md`) como o `output_path` do stage. Depois, em `resolve_stage_inputs` (`resolver.py:36`), quando um stage downstream faz binding `kind: stage_output, from: stages.<upstream>.output`, ele recebe o caminho da **invocation**, não do **expected_output** real que o agente deveria ter escrito.
- **Why it matters:** Quebra a contratualidade dos workflows. O workflow `spec-refinement` declara `synthesis` recebendo `arch_report`, `devops_report`, `qa_report` via `stages.<id>.output`. O que o agente `product-engineer` vai ler? O **invocation.md** dos especialistas, não os reports deles. O workflow funciona "no papel" (state machine avança), mas semanticamente está errado — e os testes E2E não detectam isso porque nunca leem o conteúdo do que é injetado. Esse é o caso clássico de **build-on-stale-layer**: alguém vai construir cima desse comportamento, descobrir tarde demais que está usando o arquivo errado, e diagnosticar isso será doloroso.
- **Trade-off if fixed:** Médio. Requer trocar `output_path=inv.invocation_path` por `output_path=inv.expected_output_path` (que já é renderizado e disponível). Também requer que `_resolve_awaiting_gates` preserve esse valor (hoje preserva `s.output_path` corretamente — então só o ponto de set inicial está errado).
- **Recommendation:** Trocar linha 164 para `output_path=inv.expected_output_path`. Adicionar teste em `test_orchestration_service.py` que cria workflow com duas stages, primeira COMPLETED com `expected_output.path` conhecido, e valida que o input resolvido na segunda é exatamente esse path — não o da invocation.

#### [HIGH] `manifest.json` não é reconstrutível a partir de `events.jsonl`

- **Location:** `dadaia_workspace/infrastructure/json_run_state_store.py` (sem método de rebuild)
- **Issue:** ADR-ORCH-003 e NFR-ORCH-007 afirmam que `events.jsonl` é a source-of-truth e que `manifest.json` é projeção reconstrutível. O código nunca lê os events para reconstruir — `load_run` lê apenas `manifest.json` e levanta `RunNotFoundError` se ele não existir, mesmo que `events.jsonl` esteja íntegro. A SPEC FR-ORCH-015 também é explícita: "On corruption or partial write of manifest.json, resume shall rebuild it from events."
- **Why it matters:** A promessa principal da arquitetura event-sourced não está implementada. Se um crash corromper `manifest.json`, a run é dada como perdida. O event log é redundante e não cumpre a função para a qual foi desenhado. Pior: gera **falsa confiança** — operadores vão assumir que está protegido contra crash e descobrirão na pior hora.
- **Trade-off if fixed:** Médio. Requer implementar `rebuild_manifest_from_events(run_id) -> RunManifest` em `JsonRunStateStore`, e modificar `load_run` para fallback nesse caminho quando `manifest.json` ausente/corrompido. O reducer é determinístico (events conhecidos: run_started, stage_started, stage_completed, gate_pending, gate_resolved, …); umas 60–80 linhas.
- **Recommendation:** Implementar reducer puro `_apply_event(state, event)` em `core/models/run_state.py` (puro, testável trivialmente) e `JsonRunStateStore._rebuild(run_id)` que chama o reducer sobre os events. Atualizar `load_run`: try manifest → catch JSONDecodeError/FileNotFound → rebuild. Adicionar 2 testes: rebuild full lifecycle + rebuild após partial-write simulado.

#### [HIGH] `must_include` declarado mas não validado

- **Location:** `dadaia_workspace/core/models/workflow.py:25` (modelo) + `dadaia_workspace/features/orchestration/service.py` (sem uso)
- **Issue:** O modelo `StageExpectedOutput` carrega `must_include: tuple[str, ...]`. O parser lê do YAML. O dispatcher Claude até loga "## Output must include" no `invocation.md`. Mas nada no `resume_run` lê o artefato real e verifica que essas substrings estão presentes. `_resolve_awaiting_gates` apenas marca COMPLETED cegamente.
- **Why it matters:** É um contrato sem enforcement. O operador pode fazer `resume` sem ter escrito nada — o stage será marcado COMPLETED e o próximo dispatch vai resolver inputs apontando para um arquivo que pode nem existir. Já é exatamente o que acontece nos testes E2E e ninguém percebe porque o teste não exercita o conteúdo.
- **Trade-off if fixed:** Pequeno-médio. Em `_resolve_awaiting_gates`, antes de promover para COMPLETED, ler o arquivo em `s.output_path`; checar que cada `must_include` aparece; se não, marcar FAILED e emitir `STAGE_FAILED` com `error` específico. Ganho enorme em segurança de contrato.
- **Recommendation:** Implementar a verificação em `service.py` (não em runner — depende de I/O). Manter `must_include` em `WorkflowStage` (já está) e adicionar um teste que monta um workflow com `must_include=("Findings",)`, escreve manualmente um output sem essa string e valida que `resume` falha com mensagem orientada (RF-QA-007).

#### [HIGH] `exit_criteria` é declarável mas inerte

- **Location:** `dadaia_workspace/core/models/workflow.py:48` (modelo `ExitCriterion`) + `dadaia_workspace/features/orchestration/service.py:197` (`_ = workflow`)
- **Issue:** O schema aceita `exit_criteria: [{all_stages: completed}, {file_exists: <path>}]`. O parser carrega. O service tem o comentário `_ = workflow  # surfaced via load_run; kept for future validations`. Nunca é checado. A heurística de "run concluída" é simplesmente `all(s.status == COMPLETED)`.
- **Why it matters:** A SPEC FR-ORCH-003 lista `exit_criteria` como opcional mas o schema é mantido como contrato. Operadores que confiarem em `file_exists: <path>` para validar correção de workflow encontrarão a run completing sem o arquivo existir — silenciosamente.
- **Trade-off if fixed:** Pequeno. Implementar 2 checadores (all_stages, file_exists) em `runner.py` como função pura `evaluate_exit_criteria(workflow, manifest) -> tuple[str, ...]` (retorna lista de criteria não satisfeitos). Em `_maybe_complete`, se houver não-satisfeitos, marcar run FAILED com erro orientado.
- **Recommendation:** Implementar ou **remover do schema** se a equipe decidir que `exit_criteria` é overkill em v0.1. Não há razão para manter código morto/aspiracional no Protocol. Decisão arquitetural: ou cumpre, ou deixa a SPEC explícita de que ficou para v0.2.

#### [HIGH] `_select_dispatcher` faz `import os` dentro da função

- **Location:** `dadaia_workspace/container.py:100-110`
- **Issue:** Import local de `os` dentro da função. Não há razão técnica — `os` é stdlib, sem custo de import. Pior: o `container.py` é o composition root, é o lugar onde dependências de ambiente devem ser **explícitas**.
- **Why it matters:** Pequeno smell agora, vetor de inconsistência depois. Outros builders nesse mesmo arquivo importam tudo no topo. Inconsistência local em composition roots é especialmente nociva porque quem busca "onde dispatcher é configurado" pode não encontrar o `os.environ.get` em uma scan top-of-file.
- **Trade-off if fixed:** Trivial (mover import para topo). Sem trade-off.
- **Recommendation:** Mover `import os` para o topo de `container.py` e considerar receber `runtime_env: dict[str, str] | None = None` na função para permitir injeção em testes (RuntimeOption: extrair env-reading para uma função `_runtime_from_env(env: Mapping[str, str]) -> str` testável).

#### [MEDIUM] `output_path` no `StageState` é overload semântico

- **Location:** `core/models/run_state.py:50` + uso em `service.py` + `resolver.py`
- **Issue:** O campo `output_path` em `StageState` é usado para 2 propósitos: (a) caminho da invocation enquanto AWAITING_GATE, (b) caminho do artefato esperado depois (idealmente — ver CRITICAL #2). Mesmo após o fix do CRITICAL #2, ainda há ambiguidade conceitual: o campo deveria ser sempre "o que o downstream resolverá como `stages.X.output`", ou seja, o `expected_output_path`.
- **Why it matters:** Ambiguidade de semântica em modelo de domínio é fonte recorrente de bugs. O nome `output_path` sugere "onde o stage escreveu o resultado"; o uso atual é "onde está alguma coisa relacionada ao stage".
- **Trade-off if fixed:** Médio. Adicionar segundo campo `invocation_path` no `StageState` é correto mas custa migration cuidadosa (manifest.json de runs antigas).
- **Recommendation:** Para v0.1, garantir que após o fix CRITICAL #2 `output_path` sempre carregue o `expected_output.path` renderizado. Em v0.2, separar formalmente em `invocation_path` e `expected_output_path` no `StageState`. Documentar a semântica no docstring do dataclass.

#### [MEDIUM] Workflow `tdd-cycle.workflow.md` usa `{task_id}` em paths mas o resolver só substitui `{run_id}`, `{context}`, `{run_ts}`

- **Location:** `dadaia_workspace/public/workflows/tdd-cycle.workflow.md` linhas 19, 30, 41, 54 + `features/orchestration/resolver.py:46`
- **Issue:** O workflow seed declara `path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-red.md"`. O `render_output_path` em `resolver.py:46-51` substitui apenas `{run_id}`, `{context}`, `{run_ts}`. `{task_id}` permanece literal no path final.
- **Why it matters:** Um dos 2 workflows seed (cobrados como contrato em ADR-ORCH-006) gera paths literalmente errados. Um artefato vai parar em `.dadaia/reports/demo/qa-engineer/20260514T122340Z-{task_id}-red.md` — com chaves no path. O E2E test passa porque nunca lê o `expected_output_path` resolvido — só conta stages.
- **Trade-off if fixed:** Pequeno. Generalizar `render_output_path` para suportar substituição genérica de `{<workflow_input_name>}` a partir de `manifest.inputs`.
- **Recommendation:** Generalizar para `render_output_path(template: str, *, run_id, context, run_ts, workflow_inputs: Mapping[str, str]) -> str`. Adicionar teste com workflow que tem input customizado + path template referenciando esse input. Sem isso, o segundo workflow seed é cosmético, não funcional.

#### [MEDIUM] `WorkflowStore.validate` declarada no Protocol, sem implementação real útil

- **Location:** `core/protocols/workflow_store.py:11` + `infrastructure/markdown_workflow_store.py:245-250`
- **Issue:** `validate(name)` em `MarkdownWorkflowStore` chama `self.get(name)`, captura `WorkflowSchemaError`, retorna a tupla `(str(e),)` ou tupla vazia. Mas `get` faz `list()` que parseia todos os workflows — então `validate("X")` parseia todos e ainda assim só reporta o primeiro erro encontrado em X. Não é incremental, não cumula erros, não é mais útil que tentar `get` direto.
- **Why it matters:** Protocol method com semântica fraca. Hoje ninguém chama `validate()` no codepath — `start_run` faz `workflow_store.get(name)` direto. É **speculative generality** (anti-pattern).
- **Trade-off if fixed:** Pequeno. Ou se torna útil (acumular todos os erros, validar parallel_group internos com mais detalhes, validar `agent_catalog` mesmo quando o store foi criado sem catalog), ou se remove.
- **Recommendation:** Remover do Protocol em v0.1 (não há consumer); reintroduzir em v0.2 se `dadaia public stage` for refatorado para usar `WorkflowStore` em vez do `MarkdownWorkflowStore` concreto direto.

#### [MEDIUM] `parallel_group` ordering dentro do batch não é determinístico

- **Location:** `dadaia_workspace/features/orchestration/runner.py:78-82` (`group_ready`)
- **Issue:** `by_group` é `dict` (insertion-ordered desde 3.7, ok). Mas a iteração para construir invocations dentro de um grupo segue a ordem em que os stages aparecem em `ready` — que vem de `next_ready_stages` que itera `workflow.stages` na ordem do file. Isso é determinístico **hoje**. Mas: `singletons` é separado de `by_group.values()` e adicionados em ordens distintas em `grouped`. Para um workflow com 1 singleton + 1 parallel_group de 3, a ordem do `invocations` retornado é singleton-first, parallel-second — não documentado.
- **Why it matters:** Operador que confia em ordem dos `invocation.md` apresentados no terminal pode ser surpreendido. NFR-ORCH-006 promete determinismo do resolver mas não cobre ordem de retorno do runner.
- **Trade-off if fixed:** Trivial. Garantir ordem por ordem de declaração em `workflow.stages`.
- **Recommendation:** Reescrever `group_ready` para produzir grupos na **ordem em que aparecem em `workflow.stages`** (preservando que grupos paralelos vêm como tupla atômica). Adicionar teste explícito.

#### [LOW] Mensagens de erro misturam Português e Inglês

- **Location:** `dadaia_workspace/cli/commands/orchestrate.py` linhas 38, 83, 95, 171, 188, 197, 205, 231, 246, 304, 308…
- **Issue:** Mensagens ao operador alternam entre `"workflow 'ghost' não encontrado"` (vinda do Protocol em inglês), `"Nenhum workflow instalado."` (PT), `"run já concluído"` (PT), `"Workspace not initialized. Run 'dadaia init' first."` (EN), etc. Inconsistente.
- **Why it matters:** Cosmético, mas a SPEC e os outros comandos da CLI parecem mirar PT-BR. Inconsistência sinaliza falta de revisão de UX.
- **Trade-off if fixed:** Pequeno (~20 strings).
- **Recommendation:** Decidir idioma única e padronizar. Sugestão: PT-BR consistente (alinhado com docstrings da CLI).

#### [LOW] `service.py` é o maior módulo da feature (282 LoC)

- **Location:** `dadaia_workspace/features/orchestration/service.py`
- **Issue:** A SPEC FR-ORCH-024 diz "exatamente três módulos: service.py, runner.py, resolver.py". Cumprido formalmente. Mas `OrchestrationService._advance` (linhas 122-178) é uma função de 57 linhas com 4 loops aninhados. `_resolve_awaiting_gates` (200-249) é outra função densa.
- **Why it matters:** Cohesion local OK, mas legibilidade compromete revisões e onboarding. A função `_advance` mistura: (a) computação de ready, (b) grouping, (c) update intermediário do manifest, (d) dispatch, (e) update pós-dispatch — cada etapa de fato distinta.
- **Trade-off if fixed:** Médio. Extrair para 2–3 funções privadas em `runner.py` (já contém helpers) ou criar `_dispatch_group(...)` em `service.py`. Risco de violar a regra "exatamente 3 módulos".
- **Recommendation:** Manter os 3 módulos mas refatorar `_advance` em 2–3 helpers em `runner.py` (puros, recebem manifest e retornam manifest). O service apenas orquestra os helpers.

#### [LOW] Type unsafety em alguns pontos

- **Location:** `dadaia_workspace/infrastructure/json_run_state_store.py:84` (`finished_at=d.get("finished_at")  # type: ignore[arg-type]`)
- **Issue:** `# type: ignore` é o sintoma. O modelo `RunManifest.finished_at` é `str | None`; `d.get("finished_at")` retorna `Any | None`. Pequeno smell — o ignore mascara o fato de que não há `str(...)` cast.
- **Why it matters:** Marginal. Mas é o tipo de coisa que se acumula.
- **Trade-off if fixed:** Trivial: `finished_at=str(d["finished_at"]) if d.get("finished_at") else None`.
- **Recommendation:** Eliminar o `type: ignore` com cast explícito. Padrão mais limpo.

### 3.2 Gaps de funcionalidade em relação à SPEC

| # | SPEC ref | Gap | Severidade |
|---|---|---|---|
| F1 | FR-ORCH-015 + NFR-ORCH-007 | Reconstrução de manifest a partir de events.jsonl **não existe** | HIGH (já listado em finding HIGH acima) |
| F2 | FR-ORCH-004 / schema YAML | `must_include` não é validado em runtime | HIGH (já listado) |
| F3 | FR-ORCH-003 / schema YAML | `exit_criteria` aceito no schema, nunca avaliado | HIGH (já listado) |
| F4 | FR-ORCH-005 | "input declarado sem default e sem required:true" — o parser hoje aceita `required:true` sem default e aceita `default` sem `required`, mas o caminho "nem default nem required" é validado. **Não há teste explícito** dessa rejeição. | MEDIUM |
| F5 | FR-ORCH-012 | `resume` em status `failed` "replay from the first non-completed stage" — implementado corretamente (`_reset_failed_for_retry`), mas o stage falho original perde seu `error` ao resetar. SPEC não fala em preservar, mas para diagnóstico futuro seria útil emitir `STAGE_FAILED` antes de resetar | MEDIUM |
| F6 | FR-ORCH-013 + RF-QA-007 | Mensagens de erro: a maioria está orientada. Mas `WorkflowSchemaError` cru de `start_run` propaga sem prefixar "workflow X / stage Y". Já há contexto na origem, mas a apresentação na CLI pode melhorar. | LOW |
| F7 | FR-ORCH-019 | `run_id` ≤22 chars — atual é 23 chars (16 do timestamp `YYYYMMDDTHHMMSSZ` + 1 hífen + 6 hex). **Excede o limite declarado**. | MEDIUM |
| F8 | US-ORCH-005 / FR-ORCH-012 | Idempotência verbal de resume: testes cobrem completed (no-op). Não cobrem resume em RUNNING (impossível hoje porque sempre vira AWAITING_GATE imediatamente — mas se algum dia o dispatcher Claude **executar inline** isso muda) | LOW |
| F9 | FR-ORCH-029 | Spec menciona "exact split entre adapters é detalhe capturado em PLAN.md" — `cli_agent_dispatcher.py` tem 3 classes (CliAgentDispatcher + OpenCodeAgentDispatcher + CodexAgentDispatcher) usando herança. OK funcionalmente, mas é inheritance-for-code-reuse — flag de design pattern. | LOW |
| F10 | ADR-ORCH-005 / FR-ORCH-037 | Ausência de `workflow-orchestrator` agent é deliberada e bem documentada. Sem gap. | — |

### 3.3 Melhorias nos testes E2E

#### [P1] Adicionar um pseudo-agente de teste que escreve o `expected_output_path`

Hoje os "E2E" não validam que o conteúdo certo é gerado. Sugestão: criar `tests/fakes_agents.py` com um `TestAgentRunner` que:
1. Lê `invocation.md`;
2. Pega `expected_output_path`;
3. Escreve um arquivo com conteúdo determinístico (incluindo `must_include` strings + IDs únicos do stage);
4. Chama `dadaia orchestrate resume`.

Loop esse fluxo para cada stage. Agora **a run inteira é verificada**: que o `synthesis` recebe os 3 reports corretos como inputs, que `must_include` valida, que ordem de gates é respeitada.

#### [P1] Teste de crash + reconstrução

Simular: matar o processo entre `_write_manifest_atomic` tmp.write e `os.replace`. Verificar que `load_run` reconstrói via events. Requer implementar o rebuild primeiro (HIGH #3).

#### [P2] Teste de E2E com `--runtime claude` (sem agente real)

Mesmo com Claude, o dispatcher só prepara `invocation.md`. Cobrir que o header tem a string exata "dispatch all members in a single host-agent message" para parallel_group, e que `--runtime claude` no CLI propaga até o dispatcher selecionado. Hoje só o unit test exercita isso.

#### [P2] Teste de workflow com `{custom_input}` no path template

Quando F8/MEDIUM #2 for resolvido, garantir que `tdd-cycle.workflow.md` produz paths corretos.

#### [P3] Property-based testing do runner

`hypothesis` para gerar DAGs aleatórios válidos e propriedades:
- `topo_order(wf)` sempre tem comprimento `len(wf.stages)`;
- `next_ready_stages(wf, m)` retorna ∅ sse há stage ready (cobrir terminação);
- start → N×resume → status COMPLETED, qualquer ordem.

### 3.4 Outros: DX, observabilidade

#### [P1] `dadaia orchestrate status <run-id>` deveria mostrar o próximo gate explícito

US-ORCH-004 promete "o próximo gate pendente (se houver)". O comando atual lista stages e status, mas não diz "Aguardando aprovação do gate em <stage_id>: <prompt>" para o operador. Para um operador casual, é a peça mais útil de output.

#### [P1] `dadaia orchestrate run` deveria imprimir o caminho relativo da `invocation.md`

Hoje imprime path absoluto `/<runs_dir>/<run_id>/<stage>/invocation.md`. Em terminais estreitos é ilegível. Imprimir relativo a `cwd` melhora UX.

#### [P2] Falta um `dadaia orchestrate cancel <run-id>`

Listado como "Fora de Escopo" na SPEC (linha 392) — decisão consciente. Mas a primeira coisa que operador descobre quando uma run trava é a vontade de cancelar. Sugestão de v0.2.

#### [P2] Falta um log estruturado por run

`events.jsonl` é estruturado mas não é human-readable. Faltam comandos `dadaia orchestrate events <run-id>` para listar eventos formatados (timestamp, kind, stage, payload). Sem isso, debugar runs requer `cat .dadaia/runs/<id>/events.jsonl | jq`.

#### [P2] `dadaia orchestrate resume` poderia validar gate prompts

A SPEC declara `StageGate.prompt`. Hoje o prompt é registrado mas nunca exibido. Em `resume`, antes de marcar GATE_RESOLVED, exibir cada prompt e pedir confirmação interativa (com flag `--yes` para CI).

#### [P3] Telemetria local

Por run, agregar métricas: tempo médio entre start e resume, tempo total, número de gates, número de stages COMPLETED vs FAILED. `dadaia orchestrate stats` é candidato natural a v0.2 — útil para descobrir se algum stage está sempre travando.

---

## 4. Backlog de Melhorias (priorizado)

| # | Prioridade | Item | Severidade | Esforço |
|---|---|---|---|---|
| 1 | P1 | Corrigir `output_path` ← `expected_output_path` em `service.py:164` | CRITICAL | S |
| 2 | P1 | Mover `make_run_id` para `core/models/run_state.py` (remover layer violation) | CRITICAL | S |
| 3 | P1 | Implementar rebuild de manifest a partir de events.jsonl | HIGH | M |
| 4 | P1 | Implementar validação de `must_include` em `_resolve_awaiting_gates` | HIGH | S |
| 5 | P1 | Implementar (ou remover formalmente) `exit_criteria` | HIGH | S |
| 6 | P1 | Generalizar `render_output_path` para qualquer `workflow_input` (corrigir tdd-cycle) | MEDIUM | S |
| 7 | P1 | Adicionar pseudo-agente nos testes E2E para fechar o loop fim-a-fim | — | M |
| 8 | P2 | Mover `import os` para topo de `container.py` + extrair `_runtime_from_env` | MEDIUM | S |
| 9 | P2 | Reduzir `run_id` ou ajustar SPEC para 23 chars (decidir) | MEDIUM | S |
| 10 | P2 | Refatorar `OrchestrationService._advance` em helpers de `runner.py` | LOW | M |
| 11 | P2 | `dadaia orchestrate status` exibir próximo gate explicitamente | — | S |
| 12 | P2 | Remover ou tornar útil `WorkflowStore.validate` | MEDIUM | S |
| 13 | P2 | Garantir ordem determinística de `group_ready` | MEDIUM | S |
| 14 | P3 | Padronizar idioma das mensagens da CLI | LOW | S |
| 15 | P3 | `dadaia orchestrate events <run-id>` (formatted event log) | — | M |
| 16 | P3 | `dadaia orchestrate cancel <run-id>` | — | M |
| 17 | P3 | Property-based testing do runner (hypothesis) | — | M |

Legenda: S = horas; M = dias.

---

## 5. Veredito

A feature de orquestração multi-agente é, no agregado, **uma das melhores peças de arquitetura do repositório**:

- **Layers respeitadas** quase perfeitamente — única violação (`make_run_id` import) é trivial de corrigir.
- **Protocols bem desenhados**, com 3 contratos claros que isolam dispatcher, persistence e workflow loading.
- **Funções puras** dominam o runner e o resolver; testáveis sem I/O.
- **Atomicidade real** no `manifest.json` via tmp + `os.replace`.
- **Honestidade de plataforma** (status `partial` / `unsupported` por runtime) é exemplar.
- **SPEC bem escrita** e majoritariamente cumprida (32 de 37 FRs implementados; 5 são gaps específicos listados acima).

Os 2 bugs CRITICAL são **localizados e corrigíveis em horas**, mas o segundo (output_path ← invocation_path) é precisamente o tipo de erro que se tornaria catastrófico ao construir features em cima da v0.1 sem revisar — exatamente o anti-pattern "build-on-stale-layer" que esta auditoria existe para detectar.

Os gaps HIGH (rebuild, must_include, exit_criteria) são **promessas da SPEC ainda não cumpridas**, não bugs no que existe. Cada um é uma feature completa em si.

**Recomendação:** antes de promover novos workflows ao seed (FR-ORCH-035) ou adicionar nova feature que dependa de orchestrate, fechar os 5 itens P1 acima. São <2 dias de trabalho concentrado e elevam a feature de "funciona em fluxos felizes" para "cumpre o contrato declarado".

---

## Anexos

### Arquivos auditados

Código fonte:
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/features/orchestration/{__init__,service,runner,resolver}.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/cli/commands/orchestrate.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/core/models/{workflow,run_state}.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/core/protocols/{workflow_store,run_state_store,agent_dispatcher}.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/core/exceptions.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/infrastructure/{markdown_workflow_store,json_run_state_store,claude_agent_dispatcher,cli_agent_dispatcher}.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/infrastructure/public_assets.py` (seções workflows)
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/container.py` (build_orchestration_service)
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/dadaia_workspace/public/workflows/{spec-refinement,tdd-cycle}.workflow.md`

Testes:
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/tests/fakes.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/tests/unit/test_orchestration_{service,runner,runtime}.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/tests/unit/test_workflow_schema.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/tests/unit/test_run_state_store.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/tests/integration/test_cli_orchestrate.py`
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/tests/e2e/features/test_orchestration_pipeline.py`

Spec:
- `/home/marco/workspace/dadaia/repos/dadaia-workspace/specs/features/multi-agent-orchestration/SPEC.md`
