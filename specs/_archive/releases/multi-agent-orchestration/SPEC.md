# Spec: Feature — Multi-Agent Orchestration

> **Status:** Implementado (v0.1 — 2026-05-14)
> **Versão:** 0.1
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/SPEC.md`, `specs/foundation/SPEC.md`, `specs/memory/architecture.md`, `specs/features/agents/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`, `specs/features/universal-agentic-assets/SPEC.md`, `specs/features/cross-tool-parity/SPEC.md`
> **Reports de entrada:** `.dadaia/reports/dadaia-workspace/software-architect/2026-05-14T122340Z-orchestration-arch.md`, `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-14T122340Z-test-strategy.md`, `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-14T122340Z-discovery-orchestration.md`

---

## Contexto

Até a v3.0 do produto, o dadaia-workspace tratava orquestração entre agentes como **fora de escopo** (vide `specs/SPEC.md` linha 254 da v3.0). Coordenação multi-agente acontecia manualmente: o operador escrevia prompts longos, agentes consumiam reports uns dos outros por convenção de pasta. Não havia tipo de asset versionado, nem CLI dedicada, nem estado durável de run.

Esta feature gradua **workflows multi-agente** ao status de **tipo de asset universal de primeira classe**, ao lado de `agents/`, `skills/`, `rules/`, `commands/` e `scripts/`. Um workflow declara, em Markdown com frontmatter YAML, uma sequência de stages cada um operado por um agente, com dependências, paralelismo, contratos de input/output e gates humanos opcionais.

A orquestração roda em modelo **híbrido**: a CLI `dadaia orchestrate` prepara estado durável e arquivos de invocação por stage; o **agente principal** da sessão (Claude/OpenCode/Codex) executa cada stage via tool nativa (`Agent` no Claude). Esse desenho honra **RF-ARCH-011 (CLI-first)** — toda capacidade de orquestração é exposta via CLI; o agente apenas lê/escreve arquivos.

Sem framework externo. Sem `langgraph`, `crewai` ou Agent SDK. Apenas três Protocols (`WorkflowStore`, `RunStateStore`, `AgentDispatcher`), três módulos de feature (`service.py`, `runner.py`, `resolver.py`) e quatro implementações concretas em `infrastructure/`.

---

## Glossário

| Termo | Definição |
|---|---|
| **Workflow** | Asset versionado em `dadaia_workspace/public/workflows/<name>.workflow.md`. Markdown com frontmatter YAML declarando `name`, `description`, `inputs`, `stages`, `exit_criteria`. |
| **Stage** | Unidade atômica de um workflow. Tem `id`, `agent`, `needs`, `parallel_group?`, `inputs`, `expected_output`, `gate?`. |
| **Run** | Execução concreta de um workflow. Identificada por `run_id` ULID-like. Estado persistido em `<workspace-root>/.dadaia/runs/<run-id>/`. |
| **Run manifest** | `manifest.json` com a projeção materializada do estado do run (status agregado, transições). Escrito atomicamente via `os.replace()`. |
| **Run events** | `events.jsonl` append-only com a sequência de eventos (`run_started`, `stage_started`, `stage_completed`, `gate_pending`, etc.). É **source of truth**; manifest é projeção reconstrutível. |
| **Invocation** | `runs/<run-id>/<stage_id>/invocation.md` — arquivo que a CLI prepara para que o agente principal saiba como executar aquele stage. |
| **Input Contract** | Declaração obrigatória no frontmatter de cada agente em `public/agents/` listando `requires_inputs`, `produces_outputs`, `stop_if_missing`. Definido em `specs/features/agents/SPEC.md`. |
| **Handoff schema v1** | Header padrão obrigatório de todo report inter-agente. Definido em `specs/features/agents/SPEC.md`. |
| **AgentDispatcher** | Protocol responsável por traduzir `(stage, inputs)` em invocação concreta no runtime alvo. Tem variantes `claude`, `opencode`, `codex`, `cli`. |
| **`partial`** | Novo status reportado por `dadaia public doctor` quando um runtime declara suporte best-effort a uma capacidade (ex: OpenCode com `parallel_group` executado sequencialmente). |
| **`unsupported`** | Status existente, mantido honestamente para Codex em workflows com `parallel_group`. |

---

## Usuários e Goals

### US-ORCH-001: Listar workflows disponíveis

- **Como** operador
- **Quero** descobrir quais workflows estão instalados no workspace
- **Para** decidir qual rodar sem precisar inspecionar diretórios manualmente

**Critérios de Aceite:**
- Dado um workspace com workflows projetados em `.dadaia/agentic/workflows/`, quando executo `dadaia orchestrate list`, então a CLI exibe uma tabela com `name`, `version`, `description` (uma linha por workflow).
- Dado um workspace sem workflows, quando executo `dadaia orchestrate list`, então a CLI exibe "Nenhum workflow instalado." e retorna exit code 0.

### US-ORCH-002: Inspecionar um workflow

- **Como** operador ou agente
- **Quero** ler o conteúdo declarado de um workflow específico
- **Para** entender stages, dependências e inputs antes de executar

**Critérios de Aceite:**
- Dado um workflow `spec-refinement` instalado, quando executo `dadaia orchestrate show spec-refinement`, então a CLI exibe `name`, `description`, lista de `inputs` (nome, tipo, required, default), lista de `stages` (id, agent, needs, parallel_group, gate).
- Dado um nome inexistente, quando executo `dadaia orchestrate show ghost`, então a CLI retorna exit code != 0 com mensagem orientada: "workflow 'ghost' não encontrado. Use `dadaia orchestrate list`."

### US-ORCH-003: Iniciar uma run de um workflow

- **Como** operador
- **Quero** iniciar uma execução concreta de um workflow contra o contexto ativo
- **Para** registrar estado durável e preparar a invocação do primeiro stage

**Critérios de Aceite:**
- Dado um workflow válido e um contexto primário ativo, quando executo `dadaia orchestrate run spec-refinement [--context <nome>]`, então a CLI cria `.dadaia/runs/<run-id>/manifest.json` (status `pending` ou `running`), escreve `events.jsonl` com `run_started`, prepara `runs/<run-id>/<primeiro-stage>/invocation.md` e imprime o `run_id` + path da invocação.
- Dado um workspace sem contexto primário ativo, quando executo `dadaia orchestrate run` sem `--context`, então a CLI rejeita com mensagem orientando `dadaia context activate <nome>` ou passagem de `--context`.
- Dado um workflow inexistente, quando executo `run`, então a CLI rejeita com mensagem clara antes de tocar qualquer arquivo de estado.
- Dado um workflow cujos `agent` referenciados não existem em `public/agents/`, quando executo `run`, então a CLI rejeita na validação de schema antes de criar `manifest.json`.

### US-ORCH-004: Consultar status de uma run

- **Como** operador
- **Quero** saber em que stage uma run está, qual o status agregado e qual o próximo gate
- **Para** decidir se aprovo, retomo ou abandono

**Critérios de Aceite:**
- Dado um `run_id` existente, quando executo `dadaia orchestrate status <run-id>`, então a CLI exibe `workflow_name`, `status` agregado, `stages[]` com `id`, `agent`, `status`, `started_at`, `finished_at`, e o próximo gate pendente (se houver).
- Dado um `run_id` inexistente, quando executo `status`, então a CLI rejeita com erro orientado.
- Dado um workspace com várias runs, quando executo `dadaia orchestrate status` sem argumento, então a CLI lista todas as runs registradas em `.dadaia/runs/` (uma linha por run).

### US-ORCH-005: Retomar uma run pausada em gate ou falha

- **Como** operador que aprovou um gate ou corrigiu uma falha
- **Quero** retomar a run a partir do último stage não-completo
- **Para** evitar reexecutar stages já concluídos

**Critérios de Aceite:**
- Dado uma run com status `awaiting_gate`, quando executo `dadaia orchestrate resume <run-id>`, então a CLI marca o gate como resolvido, escreve `gate_resolved` em `events.jsonl`, prepara a invocação do próximo stage e atualiza `manifest.json`.
- Dado uma run com status `failed`, quando executo `resume`, então a CLI retoma do stage falho — sem reexecutar stages `completed`.
- Dado uma run com status `completed`, quando executo `resume`, então a CLI retorna exit code 0 sem nenhuma alteração e imprime "run já concluído".
- Dado um `run_id` inexistente, quando executo `resume`, então a CLI rejeita com erro orientado.
- A operação `resume` é **idempotente**: chamada N vezes em uma run em estado estável não corrompe o estado.

### US-ORCH-006: Executar workflow `spec-refinement` em modo orchestrator-worker

- **Como** product-engineer rodando esta própria evolução
- **Quero** disparar `spec-refinement`, ver 3 especialistas em paralelo (Claude) ou sequencial (OpenCode), e depois consolidar
- **Para** acelerar refinamento de specs com paralelismo seguro e gates humanos

**Critérios de Aceite:**
- Dado runtime Claude e um workflow com `parallel_group`, quando o agente principal lê o `invocation.md` de cada stage do grupo, então o operador (ou o agente principal) dispara as N chamadas `Agent` em **uma única mensagem** — convenção declarada explicitamente no header de cada `invocation.md`.
- Dado runtime OpenCode, então `dadaia public doctor` reporta `partial` para esse workflow; os stages do `parallel_group` são executados sequencialmente sem perda de correção.
- Dado runtime Codex e um workflow com `parallel_group`, então `dadaia public doctor` reporta `unsupported`; tentativa de `run` com `--runtime codex` em workflow com `parallel_group` rejeita com `OrchestrationUnsupportedError` orientado a ação ("use --runtime claude ou rode em sequência").

---

## Requisitos Funcionais

### Tipo de Asset `workflows/`

- **FR-ORCH-001:** The system shall recognize `workflows/` as a first-class versioned asset type alongside `agents/`, `skills/`, `rules/`, `commands/`, and `scripts/`. Authoring source lives at `dadaia_workspace/public/workflows/<slug>.workflow.md`.
- **FR-ORCH-002:** Each workflow file shall use the suffix `.workflow.md`. The filename (without suffix) shall match the `name` field of the YAML frontmatter case-insensitively.
- **FR-ORCH-003:** The workflow frontmatter shall conform to schema version `"1"` and include at minimum: `name`, `description`, `version`, `schema_version`, `inputs` (map), `stages` (non-empty ordered list). `exit_criteria` is optional.
- **FR-ORCH-004:** Each `stage` shall declare at minimum: `id` (snake_case unique within the workflow), `agent` (must reference a file in `public/agents/`), and `expected_output` (`path` template + optional `must_include` checks). Optional: `needs`, `parallel_group`, `inputs`, `gate`, `on_failure`.
- **FR-ORCH-005:** The system shall validate every workflow on load and reject (with error orientado a recuperação per RF-QA-007) when any of the following occurs:
  - `name` differs from filename or is duplicated in the workflow store
  - `agent` references a name absent from `public/agents/`
  - `stages` forms a cycle (validated by Kahn topological sort; error must list the cycle)
  - any `needs` references an unknown stage id
  - any `parallel_group` includes stages whose `needs` reference another stage in the same group (parallel members cannot depend on each other)
  - any input declared without `default` and without `required: true`
- **FR-ORCH-006:** `dadaia public stage` shall copy `public/workflows/` to `<workspace-root>/.dadaia/agentic/workflows/` and include the files in `manifest.json` with sha256 hashes. Staging a workflow that fails schema validation shall abort the stage operation with a clear error.

### CLI `dadaia orchestrate`

- **FR-ORCH-007:** The CLI shall provide a command group `dadaia orchestrate` with subcommands: `list`, `show <workflow>`, `run <workflow> [--context <name>] [--runtime claude|opencode|codex|cli] [--input k=v ...] [--dry-run]`, `status [<run-id>]`, `resume <run-id>`.
- **FR-ORCH-008:** `dadaia orchestrate list` shall read from `<workspace-root>/.dadaia/agentic/workflows/` and return one row per validated workflow with `name`, `version`, `description`.
- **FR-ORCH-009:** `dadaia orchestrate show <workflow>` shall print the workflow's declared inputs, stages (id, agent, needs, parallel_group, gate), and exit_criteria; pretty-printed for humans + `--json` for machine consumption.
- **FR-ORCH-010:** `dadaia orchestrate run` shall:
  - resolve the active context (via `--context` flag, `DADAIA_CONTEXT` env var, or primary context from `primary_context.json`, in that priority);
  - validate the workflow against the agent catalog;
  - generate a ULID-like `run_id` (timestamp prefix + short random suffix);
  - create `<workspace-root>/.dadaia/runs/<run-id>/` and write `manifest.json` atomically;
  - append `run_started` event to `events.jsonl`;
  - prepare `runs/<run-id>/<first-stage-id>/invocation.md` for the agent runtime to consume;
  - print on stdout the `run_id`, the runtime selected, the path to the first `invocation.md`, and the recommended next action.
- **FR-ORCH-011:** `dadaia orchestrate status` shall report run state without mutating any file. Output includes per-stage status (`pending`, `running`, `awaiting_gate`, `completed`, `failed`, `skipped`). Supports `--json` for machine consumption.
- **FR-ORCH-012:** `dadaia orchestrate resume <run-id>` shall:
  - load the run state from `manifest.json` (reconstructed from `events.jsonl` when manifest is inconsistent);
  - if the run is `completed`, exit 0 with a no-op message;
  - if the run is `awaiting_gate`, append `gate_resolved` event and prepare the next stage invocation;
  - if the run is `failed`, replay from the first non-completed stage;
  - guarantee idempotency: re-invoking `resume` on an already-resumed run that is now `running` or `awaiting_gate` shall not corrupt state.
- **FR-ORCH-013:** All `dadaia orchestrate` errors shall comply with **RF-QA-007**: identify the failed capability (`orchestrate`), the workflow/run-id involved, the cause (validation, missing file, unsupported runtime), and the next safe action.

### Run State

- **FR-ORCH-014:** Run state shall persist under `<workspace-root>/.dadaia/runs/<run-id>/` with two canonical files: `manifest.json` (atomic writes via `os.replace()`) and `events.jsonl` (append-only).
- **FR-ORCH-015:** `events.jsonl` shall be the **source of truth** for run progression. `manifest.json` shall be reconstructable by replaying events. On corruption or partial write of `manifest.json`, `resume` shall rebuild it from events.
- **FR-ORCH-016:** Allowed run statuses: `pending`, `running`, `awaiting_gate`, `completed`, `failed`, `needs_resume`.
- **FR-ORCH-017:** Allowed stage statuses: `pending`, `running`, `awaiting_gate`, `completed`, `failed`, `skipped`.
- **FR-ORCH-018:** Allowed event kinds: `run_started`, `stage_started`, `stage_completed`, `stage_failed`, `gate_pending`, `gate_resolved`, `run_completed`, `run_failed`.
- **FR-ORCH-019:** `run_id` shall be ULID-like (timestamp + short random suffix, ≤22 chars), guaranteeing chronological ordering when listed.
- **FR-ORCH-020:** Run directories under `.dadaia/runs/` are **durable**; they shall not be deleted by `dadaia doctor` and shall persist across sessions and exports (unless an explicit operator command removes them).

### Protocols (core)

- **FR-ORCH-021:** A new Protocol `WorkflowStore` shall live at `dadaia_workspace/core/protocols/workflow_store.py` with at minimum: `list() -> tuple[WorkflowDefinition, ...]`, `get(name) -> WorkflowDefinition`, `validate(name) -> tuple[str, ...]`.
- **FR-ORCH-022:** A new Protocol `RunStateStore` shall live at `dadaia_workspace/core/protocols/run_state_store.py` with at minimum: `create_run`, `load_run`, `update_manifest`, `append_event`, `list_runs`, `iter_events`.
- **FR-ORCH-023:** A new Protocol `AgentDispatcher` shall live at `dadaia_workspace/core/protocols/agent_dispatcher.py` with at minimum: `capabilities() -> DispatcherCapabilities`, `dispatch(invocation) -> StageResult`, `dispatch_parallel(invocations) -> tuple[StageResult, ...]`. `DispatcherCapabilities` carries `runtime_name`, `supports_parallel`, `supports_gates_inline`, `mode` (`native | best-effort-sequential | unsupported | cli-only`).

### Feature module (`features/orchestration/`)

- **FR-ORCH-024:** A new feature directory shall live at `dadaia_workspace/features/orchestration/` with exactly three modules: `service.py` (`OrchestrationService`), `runner.py` (`WorkflowRunner` — DAG execution and propagation), `resolver.py` (`InputResolver` — pure function resolving stage inputs from workflow inputs and stage outputs). No additional modules without RF-SLOPE-003 justification.
- **FR-ORCH-025:** `OrchestrationService` shall expose: `list_workflows`, `show_workflow`, `start_run`, `resume_run`, `get_run_status`. The service depends only on the three Protocols above plus `workspace_root: Path` and `clock: Callable[[], datetime]`.

### Infrastructure implementations

- **FR-ORCH-026:** A new module `infrastructure/markdown_workflow_store.py` shall implement `WorkflowStore` by reading `*.workflow.md` files from `<workspace-root>/.dadaia/agentic/workflows/`, parsing YAML frontmatter, and validating per FR-ORCH-005.
- **FR-ORCH-027:** A new module `infrastructure/json_run_state_store.py` shall implement `RunStateStore` writing `manifest.json` atomically (tmp + `os.replace()`) and `events.jsonl` as append-only.
- **FR-ORCH-028:** A new module `infrastructure/claude_agent_dispatcher.py` shall implement `AgentDispatcher` with `mode="native"`, `supports_parallel=True`. The dispatcher writes the `invocation.md` for each stage; the actual `Agent` tool call is performed by the host agent (Claude session). The dispatcher returns `awaiting_gate` immediately after preparing invocations, signaling the host agent to dispatch.
- **FR-ORCH-029:** A new module `infrastructure/cli_agent_dispatcher.py` shall implement `AgentDispatcher` with `mode="cli-only"`. Default fallback when no agent runtime is detected. Prepares `invocation.md` files for the operator to execute manually. Used in CI and shells without an agent host. Also covers OpenCode (`mode="best-effort-sequential"`, `supports_parallel=False`) and Codex (`mode="unsupported"`, raises `OrchestrationUnsupportedError` on `dispatch_parallel`) by adapter pattern over the same module — exact split between adapters is an implementation detail captured in `PLAN.md`.
- **FR-ORCH-030:** Dispatcher selection shall be driven by env var `DADAIA_AGENT_RUNTIME` (`claude | opencode | codex | cli`) with fallback `cli`. The CLI flag `--runtime` overrides the env var when present.

### Composition root

- **FR-ORCH-031:** `dadaia_workspace/container.py` shall expose `build_orchestration_service(workspace_root: Path, runtime: str | None = None) -> OrchestrationService` following the same factory pattern as the existing builders (workspace, spec_context, public, academy). State stays out of `core/`.

### Universal distribution

- **FR-ORCH-032:** `dadaia public stage` shall include `workflows/` in `_COPY_DIRS` so files in `public/workflows/` are staged to `.dadaia/agentic/workflows/`.
- **FR-ORCH-033:** `dadaia public install --target all` shall project `.dadaia/agentic/workflows/` to: `<workspace-root>/.agents/workflows/`, `.claude/workflows/`, `.opencode/workflows/`, `.codex/workflows/`. The files installed in Codex/OpenCode are **reference documents**; runtime support for execution semantics is reported by `dadaia public doctor`.
- **FR-ORCH-034:** `dadaia public doctor` shall classify each workflow per runtime using these statuses: `ok` (full support, including parallel), `partial` (best-effort fallback, e.g. OpenCode running parallel as sequential), `unsupported` (e.g. Codex with `parallel_group`), `missing`, `drift`. The status `partial` is **new** in this evolution and must be added to the existing doctor classifier.

### Workflows seed (shipped in the library)

- **FR-ORCH-035:** The package shall ship at minimum two seed workflows in `public/workflows/`:
  - `spec-refinement.workflow.md` — discovery (product-engineer) → 3-way parallel (software-architect, devops-engineer, qa-engineer) → synthesis (product-engineer). Includes a gate `operator-approval` between discovery and the parallel group, and another gate after synthesis.
  - `tdd-cycle.workflow.md` — pair software-engineer ↔ qa-engineer reading an approved TASKS.md task, alternating red-green-refactor; `product-engineer` available as optional consult via a `consult-product` gate.
- **FR-ORCH-036:** Seed workflows shall pass schema validation on every `dadaia public stage`. CI shall enforce this (validated by a feature test).

### Operator-orchestrator decision (deferred)

- **FR-ORCH-037:** The library shall **not** ship a `workflow-orchestrator` agent as a versioned asset in v0.1. The host agent of the runtime session is the orchestrator. A future evolution may introduce this agent if and only if the product accumulates ≥5 workflows with >3 stages each **and** measurement shows operator-in-the-loop is a bottleneck.

---

## Requisitos Não-Funcionais

- **NFR-ORCH-001 [Atomicidade]:** Every write to `manifest.json` shall be atomic (`tmp + os.replace()`). Concurrent reads must always observe a consistent snapshot.
- **NFR-ORCH-002 [Append-only]:** Every line written to `events.jsonl` shall be a single complete JSON object with mandatory fields `ts`, `run_id`, `kind`. Partial lines on crash must remain detectable on re-read.
- **NFR-ORCH-003 [Diagnosabilidade]:** `dadaia orchestrate status --json` shall be stable enough for autonomous agent consumption; field renames require a SemVer minor bump and a deprecation window.
- **NFR-ORCH-004 [Honestidade de plataforma]:** Generated workflow projections shall never claim unsupported parity. `doctor` shall always emit `partial` or `unsupported` honestly per runtime capability.
- **NFR-ORCH-005 [Portabilidade]:** The orchestration feature shall not depend on any external orchestration framework (no `langgraph`, `crewai`, `agno`, `autogen`). Only the new `pyyaml` runtime dependency is added (ADR-ORCH-001).
- **NFR-ORCH-006 [Determinismo]:** `InputResolver` shall be a pure function. Given the same workflow definition + accumulated run state, it returns identical resolved inputs.
- **NFR-ORCH-007 [Reparabilidade]:** A run whose `manifest.json` is corrupted shall be repairable by replaying `events.jsonl`; `resume` is the trigger.

---

## Decisões Arquiteturais

### ADR-ORCH-001: `pyyaml` é dependência runtime obrigatória

Workflows usam YAML aninhado (lista de stages com lista de inputs). Regex sobre YAML é frágil. `pyyaml` é stdlib-grade, estável, sem deps transitivas pesadas. Adiciona-se `pyyaml ^6.0` em `pyproject.toml` na seção `[tool.poetry.dependencies]`. A constituição (`specs/constitution.md`) deverá ser atualizada para listar `pyyaml` ao lado de `typer`, `rich`, `openpyxl` em rodada subsequente.

### ADR-ORCH-002: Modelo híbrido CLI prepara + agente executa

A CLI `dadaia orchestrate run` **não invoca o LLM diretamente**. Ela:
1. Cria o estado durável (`runs/<run-id>/manifest.json` + `events.jsonl`);
2. Prepara `runs/<run-id>/<stage_id>/invocation.md` com instruções concretas para o próximo stage;
3. Retorna ao operador, que (na sessão de agente ativa) instrui o host agent a ler o `invocation.md` e disparar o agente alvo via tool nativa (`Agent` no Claude).

Esse desenho honra **RF-ARCH-011 (CLI-first)** sem inventar uma camada de invocação de LLM dentro da CLI Python. Mantém o operador in-the-loop em todos os gates explícitos.

### ADR-ORCH-003: `events.jsonl` é source of truth, `manifest.json` é projeção

Crashes entre escrever uma transição no `manifest.json` e adicionar o evento correspondente em `events.jsonl` causam drift se o manifest for canônico. Convenção invertida: **evento primeiro** (append-only é mais robusto), depois atualizar manifest. `resume` sempre pode reconstruir manifest a partir dos eventos.

### ADR-ORCH-004: Status `partial` é novo no doctor

O classificador atual de `dadaia public doctor` retorna `ok | missing | drift | unsupported`. Esta evolução adiciona `partial` para representar "runtime declarou capacidade best-effort". Aplicação imediata: OpenCode com `parallel_group` (executa sequencialmente).

### ADR-ORCH-005: Não criar agente `workflow-orchestrator` em v0.1

A literatura sugere um agente dedicado de orquestração. Em v0.1, isso introduziria quatro níveis de delegação (operador → workflow-orchestrator → product-engineer → 3 paralelos) sem benefício mensurado. O host agent (Claude/OpenCode/Codex) já exerce esse papel via tool `Agent`. Decisão registrada como **diferida**, com critério explícito de reabertura (FR-ORCH-037).

### ADR-ORCH-006: Workflows seed shipped na lib são contrato

Os 2 workflows seed (`spec-refinement.workflow.md`, `tdd-cycle.workflow.md`) são parte do contrato versionado do produto. Mudanças neles seguem o mesmo processo de qualquer feature spec.

---

## Estrutura de Arquivos

### Fonte canônica (pacote)

```
dadaia_workspace/
  core/
    protocols/
      workflow_store.py        ← NOVO Protocol
      run_state_store.py       ← NOVO Protocol
      agent_dispatcher.py      ← NOVO Protocol
    models/
      workflow.py              ← NOVO: WorkflowDefinition, WorkflowStage, WorkflowInput, ExitCriterion (frozen dataclasses)
      run_state.py             ← NOVO: RunManifest, StageState, RunEvent, DispatcherCapabilities, StageInvocation, StageResult
  features/
    orchestration/
      __init__.py
      service.py               ← OrchestrationService
      runner.py                ← WorkflowRunner
      resolver.py              ← InputResolver
  infrastructure/
    markdown_workflow_store.py
    json_run_state_store.py
    claude_agent_dispatcher.py
    cli_agent_dispatcher.py    ← cobre cli (default), opencode (best-effort), codex (unsupported) via adapter
  cli/
    commands/
      orchestrate.py           ← NOVO: Typer app com 5 subcomandos
  public/
    workflows/                 ← NOVO tipo de asset
      spec-refinement.workflow.md
      tdd-cycle.workflow.md
```

### Runtime workspace

```
<workspace-root>/
  .dadaia/
    agentic/
      workflows/               ← staging via dadaia public stage
        spec-refinement.workflow.md
        tdd-cycle.workflow.md
    runs/                      ← novo diretório durável (criado por `dadaia orchestrate run`)
      <run-id>/
        manifest.json
        events.jsonl
        <stage-id>/
          invocation.md
  .agents/
    workflows/                 ← projeção universal
  .claude/
    workflows/
  .opencode/
    workflows/
  .codex/
    workflows/
```

---

## Schema YAML do Frontmatter de Workflow (v1)

```yaml
---
name: string                # único; snake-case-with-dashes; bate com filename sem .workflow.md
description: string         # 1–3 frases; usado por `dadaia orchestrate list/show`
version: string             # SemVer da definição do workflow
schema_version: "1"         # versão do schema (gate de evolução)
inputs:                     # map de parâmetros de entrada
  <field_name>:
    type: string            # string | path | enum
    required: true | false  # default false
    description: string
    default: <value>        # opcional; só se required=false
stages:                     # lista ordenada, >=1
  - id: string              # snake_case, único dentro do workflow
    agent: string           # deve existir em public/agents/
    needs: [stage_id, ...]  # opcional; default []
    parallel_group: string  # opcional
    inputs:                 # opcional
      - kind: workflow_input | stage_output | path | literal
        from: <ref>         # ex: "$.inputs.context" ou "stages.<id>.output"
        as: string          # nome do parâmetro esperado pelo agente
    expected_output:
      path: string          # template; pode conter {context}, {run_ts}, {run_id}
      must_include: [str]   # opcional; sub-strings que devem aparecer no output
    gate:                   # opcional; pausa após o stage
      kind: operator-approval | none
      prompt: string        # texto exibido ao operador
    on_failure: stop | continue | mark-needs-resume   # default: stop
exit_criteria:              # opcional
  - all_stages: completed
  - file_exists: <path>
---

# <name>

Documentação humana do workflow (markdown). Não é parseada.
```

---

## Critérios de Aceite (Spec Aprovada)

- [ ] `dadaia orchestrate {list, show, run, status, resume}` está implementado e cada subcomando responde ao `--help` com mensagem orientada por intenção.
- [ ] `dadaia public stage` inclui `public/workflows/` em `_COPY_DIRS` e produz hashes no manifest.
- [ ] `dadaia public install --target all` projeta `.agents/workflows/`, `.claude/workflows/`, `.opencode/workflows/`, `.codex/workflows/`.
- [ ] `dadaia public doctor` retorna `partial` para OpenCode e `unsupported` para Codex quando o workflow tem `parallel_group`.
- [ ] `pyyaml` está em `[tool.poetry.dependencies]` do `pyproject.toml`.
- [ ] Os 3 novos Protocols (`workflow_store`, `run_state_store`, `agent_dispatcher`) existem em `core/protocols/`.
- [ ] Os 3 módulos em `features/orchestration/` (`service.py`, `runner.py`, `resolver.py`) existem e estão cobertos por unit tests com fakes.
- [ ] As 4 implementações em `infrastructure/` existem (`markdown_workflow_store.py`, `json_run_state_store.py`, `claude_agent_dispatcher.py`, `cli_agent_dispatcher.py`).
- [ ] O composition root `container.py` expõe `build_orchestration_service(workspace_root, runtime=None)`.
- [ ] `public/workflows/spec-refinement.workflow.md` passa validação de schema e produz a run referência (este próprio refinamento).
- [ ] `public/workflows/tdd-cycle.workflow.md` passa validação de schema.
- [ ] `events.jsonl` é append-only; `manifest.json` reconstrutível a partir dos eventos (verificado por teste).
- [ ] `dadaia orchestrate resume` é idempotente (chamadas repetidas em estado estável não corrompem).
- [ ] `RF-ARCH-001` a `RF-ARCH-013` preservados; zero imports cross-feature; container fora de `core/`.
- [ ] `RF-SLOPE-001` a `RF-SLOPE-007` preservados; sem wrappers vazios; tipo `workflows/` é Protocol-backed.
- [ ] `RF-QA-001` a `RF-QA-007` atendidos: testes unit com fakes dos 3 novos Protocols + integration + E2E em modo `--runtime cli`.

---

## Riscos e Mitigações

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| R1 | Modelo híbrido (CLI prepara + agente executa) pode confundir operador novo | Alta | Diagrama no Status `--json`; cada `invocation.md` cabeça com instrução explícita |
| R2 | `parallel_group` no Claude depende do agente principal disparar N `Agent` numa só mensagem | Média | Header de cada `invocation.md` declara `# PARALLEL GROUP: <name> — dispatch all N in a single message`; workflow doctor sinaliza |
| R3 | Dispatcher selection via env var pode colidir com `DADAIA_CONTEXT` | Média | `dadaia orchestrate run` imprime `runtime=<X>, context=<Y>` no header da saída |
| R4 | Drift `manifest.json` ↔ `events.jsonl` por crash entre escritas | Média | Evento append-only sempre primeiro; manifest é projeção; `resume` reconstrói (ADR-ORCH-003) |
| R5 | `parallel_group` com gate dentro do grupo causa deadlock | Baixa | Validador rejeita `gate` em stage dentro de `parallel_group` |
| R6 | Foundation SPEC drift retorna se `workflows/` for adicionado sem disciplina de PR único | Média | PLAN.md exige que qualquer alteração em `public/<type>/` toque também `foundation/SPEC.md` RF-ARCH-002 |

---

## Fora de Escopo (v0.1)

- Agente versionado `workflow-orchestrator` (ADR-ORCH-005; reabertura possível segundo FR-ORCH-037).
- Workflows com sub-workflows aninhados (composição recursiva de workflows).
- Execução paralela real em CI sem host agent (modo `cli-only` apenas prepara invocations).
- Persistência de outputs de LLM dentro de `manifest.json` (outputs ficam nos paths declarados em `expected_output.path`; o manifest só carrega referências).
- Streaming de eventos em tempo real para um dashboard.
- Cancelamento gracioso de runs em andamento (`dadaia orchestrate cancel <run-id>`).
- Cleanup automático de runs antigas (deletion is operator responsibility).

---

## Questões Abertas

*Nenhuma bloqueante. Decisões de tipo "naming" e "schema cosmético" não impedem aprovação. Qualquer ambiguidade não resolvida deve ir para `z_bug_specs.md`.*
