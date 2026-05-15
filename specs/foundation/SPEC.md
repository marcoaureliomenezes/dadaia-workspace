# Spec: Foundation — Arquitetura e Qualidade de Software

> **Status:** Em revisão
> **Versão:** 3.1
> **Escopo:** Princípios de arquitetura, design e qualidade que governam **toda** a implementação do dadaia-workspace
> **Referências:** `specs/constitution.md`, `specs/features/multi-agent-orchestration/SPEC.md`, `specs/features/release-pipeline/SPEC.md`

---

## Contexto

Esta spec congela a arquitetura de implementação do dadaia-workspace. Ela existe para impedir que cada incremento de feature reabra decisões sobre camadas, nomes, estados, pontos de composição e distribuição de artefatos de agente.

**Problema central a evitar:** *slope code* causado por inconsistência estrutural entre specs e por camadas paralelas criadas para acomodar ambiguidades.

---

## Requisitos de Arquitetura

### RF-ARCH-001: Quatro camadas e uma composition root
The implementation shall use exactly four layers plus a composition root:

```
CLI  →  Features  →  Core  ←  Infrastructure
           \                  /
            \                /
             └ container ───┘
```

- `cli/` depende de `features/`, `core/` e do `container`.
- `features/` depende apenas de `core/`.
- `infrastructure/` implementa Protocols de `core/`.
- `core/` não depende de nenhuma outra camada.
- `dadaia_workspace/container.py` é a composition root do pacote.

### RF-ARCH-002: Estrutura oficial do pacote

The Python package shall follow the structure below exactly. The enumerated names of `public/<type>/` assets are **authoritative** — any addition, removal, or rename in `dadaia_workspace/public/` shall be reflected here in the same PR.

```
dadaia_workspace/
  __init__.py
  container.py
  cli/
    __init__.py
    main.py
    commands/
      __init__.py
      init.py
      context.py
      repos.py
      public.py
      doctor.py
      academy.py
      export.py
      import_.py
      orchestrate.py                   ← NOVO (multi-agent-orchestration)
  core/
    __init__.py
    exceptions.py
    models/
      __init__.py
      workspace.py
      spec_context.py
      course.py
      export.py
      import_.py
      workflow.py                      ← NOVO: WorkflowDefinition, WorkflowStage, WorkflowInput, ExitCriterion
      run_state.py                     ← NOVO: RunManifest, StageState, RunEvent, DispatcherCapabilities, StageInvocation, StageResult
    protocols/
      __init__.py
      context_store.py
      primary_context_store.py
      git_client.py
      storage.py
      runtime_env.py
      course_store.py
      workflow_store.py                ← NOVO Protocol
      run_state_store.py               ← NOVO Protocol
      agent_dispatcher.py              ← NOVO Protocol
  features/
    __init__.py
    workspace/
      __init__.py
      service.py
    spec_context/
      __init__.py
      service.py
      doctor.py
    repos/
      __init__.py
      service.py
    public/
      __init__.py
      service.py
      staging.py
      doctor.py
    academy/
      __init__.py
      service.py
      knowledge_basis/
    export/
      __init__.py
      service.py
    import_/
      __init__.py
      service.py
    orchestration/                     ← NOVA feature
      __init__.py
      service.py                       ← OrchestrationService
      runner.py                        ← WorkflowRunner (DAG execution)
      resolver.py                      ← InputResolver (pure function)
  infrastructure/
    __init__.py
    json_context_store.py
    json_primary_context_store.py
    json_course_store.py
    git_subprocess.py
    excel_reader.py
    public_assets.py
    python_env.py
    markdown_workflow_store.py         ← NOVO (multi-agent-orchestration)
    json_run_state_store.py            ← NOVO
    claude_agent_dispatcher.py         ← NOVO
    cli_agent_dispatcher.py            ← NOVO (default + opencode/codex via adapter)
  public/
    agents/
      product-engineer.md
      software-architect.md
      software-engineer.md
      qa-engineer.md
      devops-engineer.md
      game-developer.md
    rules/
      dadaia-workspace-dev-guardrail.md
      game-developer-scope.md
    skills/
      architect-code-audit/
      architect-design-patterns/
      dadaia-grill-me/
      dadaia-workspace-doctor/
      dadaia-workspace-manager/
      dadaia-workspace-spec-navigator/
      dadaia-workspace-spec-reviewer/
      devops-deploy-strategies/
      devops-gitflow-governance/
      game-map-architect/
      game-packaging-distribution/
      game-physics-engine/
      game-platform-browser/
      game-platform-godot/
      game-platform-unity/
      game-platform-unreal/
      github-actions-pipelines/
    commands/
      dadaia-academy.md
      dadaia-workspace-doctor.md
      dadaia-workspace-refine-specs.md
      spec-context.md
    workflows/                         ← NOVO tipo de asset (multi-agent-orchestration)
      spec-refinement.workflow.md
      tdd-cycle.workflow.md
    scripts/
    templates/
      AGENTS.md
      opencode.json
      codex/
        config.toml
        hooks.json
    scaffold/
      constitution.md
      SPEC.md
      memory/
      foundation/
    data/
      repos.xlsx
    plugins/                           ← presente; tipo neutro (extensão futura)
tests/
  fakes.py
  unit/
  integration/
  e2e/
    features/
      test_workspace_setup.py
      test_spec_context.py
      test_public_pipeline.py
      test_orchestration_pipeline.py   ← NOVO (multi-agent-orchestration)
```

**Nota:** os nomes e quantidades de assets em `public/` listados acima são **fonte autoritativa**. Toda atualização (adição, remoção, rename) em `public/<type>/` deve refletir-se nesta RF-ARCH-002 via PR único — qualquer drift entre esta seção e o conteúdo real do diretório é tratado como bug e registrado em `z_bug_specs.md`.

### RF-ARCH-003: Protocol-first
Every infrastructure dependency used by a feature shall first be expressed as a `Protocol` in `core/protocols/`.

### RF-ARCH-004: Composition root fora do core
The composition root shall live at `dadaia_workspace/container.py`, not inside `core/`.

### RF-ARCH-005: Zero imports cross-feature
No module inside `features/X/` shall import from `features/Y/` where `X != Y`.

### RF-ARCH-006: Modelos imutáveis e estados fixos
Core models shall be frozen dataclasses. The only valid context states are `inativo` and `ativo`. The `is_primary` boolean flag distinguishes the primary context within `ativo` state.

### RF-ARCH-007: Estado persistido e sem globais
Application state shall be persisted and reloaded per operation from JSON files. Module-level mutable state is prohibited.

### RF-ARCH-008: Ciclo de vida de repos gerenciado
The product shall manage repository clones in `<workspace-root>/repos/<slug>/`. Cloning happens on `activate`. Removal (after mandatory git sync) happens on `deactivate`. No other mechanism creates or removes repos.

### RF-ARCH-008-B: Diretórios de runtime do workspace
The bootstrap flow shall create the following canonical subdirectories inside `.dadaia/`:

| Diretório | Tipo | Propósito |
|---|---|---|
| `.venv/` | Durável | Python environment isolado para automações do workspace |
| `agentic/` | Gerado | Staging local dos assets públicos do pacote, com manifest e hashes |
| `reports/` | Durável | Relatórios persistentes legíveis para humanos |
| `scripts/` | Durável | Scripts de automação do workspace (ctx-inject.sh, watchdog, etc.) |
| `states/` | Durável | Arquivos JSON de estado durável (`spec_contexts.json`, `primary_context.json`) |
| `src/` | Durável | Arquivos fonte do workspace (ex: `repos.xlsx`) |
| `dist/` | Durável | Artefatos de export gerados por `dadaia export` — criado on-demand, não por `dadaia init` |
| `runs/` | Durável | Estado durável de runs de workflows multi-agente; criado on-demand por `dadaia orchestrate run`; cada run vive em `runs/<run-id>/` com `manifest.json` (atômico) + `events.jsonl` (append-only). NOVO (multi-agent-orchestration). |
| `tmp/python/` | Efêmero | Scripts transitórios de agentes — podem ser limpos a qualquer momento |
| `tmp/json/` | Efêmero | Outputs JSON transitórios de agentes — podem ser limpos a qualquer momento |

**Não existem mais**: `.dadaia/data/` (SQLite removido) e `.dadaia/contexts/` (materialização gerenciada removida).

### RF-ARCH-009: Poetry como única ferramenta de build
The project shall use Poetry as the only dependency and build manager.

### RF-ARCH-010: Contrato de artefatos de agente
The versioned source of truth for product agent assets shall live directly in `dadaia_workspace/public/`. Runtime projection directories (`.agents/`, `.claude/`, `.codex/`, `.opencode/`) shall not be part of the package authoring architecture.

### RF-ARCH-010-B: Staging agentic gerado
The workspace runtime shall stage package public assets in `<workspace-root>/.dadaia/agentic/` before installing runtime projections. The staging directory is generated state, not canonical source.

### RF-ARCH-010-C: Projeções runtime-specific
The public asset feature shall project staged assets into:
- `.agents/skills/` for universal skills;
- `.claude/` for Claude Code assets and supported hooks;
- `.codex/` for Codex config, hooks, rules and shared skills;
- `.opencode/` plus `opencode.json` for OpenCode native commands, skills, agents and instructions;
- `AGENTS.md` for universal workspace instructions.

Unsupported runtime capabilities shall be reported as `unsupported` by doctor instead of emulated as false parity.

### RF-ARCH-011: CLI-first para automação por agentes
The implementation shall treat the official `dadaia` CLI as the primary integration boundary for human and agent automation, with granular help at the root command, command-group, and subcommand levels.

### RF-ARCH-012: Objetos com intenção explícita
Classes, services, methods, and exceptions shall be named after the business capability they implement.

### RF-ARCH-013: OOP explícita nas capabilities
Business capabilities shall be implemented through explicit service classes and domain models.

### RF-ARCH-014: Orquestração via Protocols, sem framework externo

A orquestração multi-agente (`features/orchestration/`) shall depend only on three new Protocols (`WorkflowStore`, `RunStateStore`, `AgentDispatcher`) declared in `core/protocols/`. No external orchestration framework (`langgraph`, `crewai`, `agno`, `autogen`, `langchain-orchestrator`, etc.) shall be added to the runtime dependency set.

### RF-ARCH-015: Run state durável como source-of-truth append-only

Run state for multi-agent workflows shall persist under `<workspace-root>/.dadaia/runs/<run-id>/` with two files: `manifest.json` (written atomically via tmp + `os.replace()`) and `events.jsonl` (append-only). `events.jsonl` is the **source of truth**; `manifest.json` is a reconstructable projection. Detalhes em `specs/features/multi-agent-orchestration/SPEC.md` ADR-ORCH-003.

---

## Guardrails Anti-Slope Code

### RF-SLOPE-001: Sem wrappers vazios
The implementation shall not introduce classes or functions that only delegate to another class or function with no additional policy.

### RF-SLOPE-002: Um nível de abstração por módulo
Each module shall operate at a single abstraction level.

### RF-SLOPE-003: Novos módulos exigem justificativa real
New modules are justified only by a new Protocol, a new infrastructure implementation, a new feature service, or a new CLI command module.

### RF-SLOPE-004: Sem reabrir contratos no código
If the implementation encounters a missing or conflicting behavior contract, it shall stop and update the specs instead of inventing behavior in code.

### RF-SLOPE-005: Revisão obrigatória ao alterar `specs/`
Any task that edits files under `specs/` shall run a spec consistency review before completion. Remaining issues shall be logged in `z_bug_specs.md`.

### RF-SLOPE-006: Sem bypass da CLI oficial
If an official CLI command exists for a capability intended for agent use, installed assets and automations shall use that command instead of bypassing it through direct file or internal-module access.

### RF-SLOPE-007: Fallback efêmero controlado
When CLI coverage does not yet exist, the only allowed automation fallback is an ephemeral Python script in `.dadaia/tmp/python/` with structured transient outputs in `.dadaia/tmp/json/`. Persistent state that must survive across sessions shall be written to `.dadaia/states/` (JSON), never to `tmp/`.

---

## Requisitos de Qualidade

### RF-QA-001: Pirâmide de testes
The implementation shall follow a testing pyramid with `unit/`, `integration/`, and `e2e/` tests. E2E tests live under `tests/e2e/features/`.

### RF-QA-002: Fakes para features
Unit tests for feature services shall use fake implementations of Protocols rather than mocks as the primary strategy.

### RF-QA-003: Cobertura mínima
The `features/` layer shall maintain coverage of at least 80%. `core/models/` and `core/exceptions.py` shall have full coverage.

### RF-QA-004: Type hints completos
All public functions and methods shall pass `mypy --strict`.

### RF-QA-005: Contratos automáveis
Any CLI surface intended for agent automation shall expose a stable machine-readable mode when the human-readable output would be fragile to parse.

### RF-QA-006: Causalidade explícita de erros
The implementation shall preserve exception causality across infrastructure, features, and CLI boundaries.

### RF-QA-007: Mensagens de erro orientadas a autorrecuperação
CLI-facing errors shall identify the failed capability, the relevant workspace/context/resource, the likely recoverable cause, and the next safe recovery action when one exists.

---

## Convenções de Código

### RF-CONV-001: Nomenclatura

| Elemento | Convenção | Exemplo |
|---|---|---|
| Classes | PascalCase | `SpecContextService` |
| Funções e métodos | snake_case | `build_spec_context_service()` |
| Constantes de módulo | UPPER_SNAKE_CASE | `STATE_FILE_NAME` |
| Arquivos Python | snake_case | `json_context_store.py` |
| Variáveis privadas | prefixo `_` | `self._store` |
| Protocols | sem prefixo `I` | `ContextStore` |

### RF-CONV-002: Surface da CLI congelada
The CLI surface shall remain frozen as defined in `specs/SPEC.md` and feature specs unless the specs are explicitly revised first.

### RF-CONV-003: Output na CLI
The CLI layer shall use `typer.echo()` and/or `rich`. `print()` outside CLI is prohibited.

### RF-CONV-004: Formatação e linting
The project shall pass `ruff format`, `ruff check`, and `mypy` before a task is considered done.

### RF-CONV-005: Nomes guiados por intenção
Public classes and methods shall prefer names that encode business intent over vague transport-agnostic names.

### RF-CONV-006: Task State Contract

Every backlog task in a `TASKS.md` file shall use exactly three state markers:

| Marcador | Estado | Semântica |
|---|---|---|
| `[ ]` | TODO | Task ainda não iniciada |
| `[-]` | IN PROGRESS | Task em execução — exatamente uma por sessão de trabalho |
| `[x]` | DONE | Task completa e verificada |

**Invariantes:**

- Nunca mais de uma task `[-]` por TASKS.md ativo por vez.
- Um agente nunca começa a escrever código de produção sem marcar a task alvo como `[-]` primeiro.
- Um agente nunca marca `[x]` sem verificar que os critérios de aceite da task foram atendidos.
- A transição `[ ]` → `[-]` é a chave que desbloqueia o SDD Gate (`sdd-spec-gate.sh`) para edições em paths de produção.

**Skill de enforcement:** `dadaia-task-manager` — disponível em todos os agentes que implementam backlog.

---

## Configuração de Projeto

### RF-BUILD-001: Entry point oficial
```toml
[tool.poetry.scripts]
dadaia = "dadaia_workspace.cli.main:app"
```

### RF-BUILD-002: Public assets empacotados
The package shall include the contents of `dadaia_workspace/public/` in the built distribution, including `dadaia_workspace/public/data/repos.xlsx`.

### RF-BUILD-003: Diretórios de projeção são somente runtime do workspace
The repository shall not contain product-local `.agents/`, `.claude/`, `.codex/`, or `.opencode/` directories as authoring sources.

---

## Fora de Escopo desta Spec

- Detalhes comportamentais de cada feature (vivem em `specs/features/<nome>/SPEC.md`)
- Especificação completa do gitflow, branch protection, OIDC, smoke test e procedimento de release — domínio de `specs/features/release-pipeline/SPEC.md`
- Schema YAML do frontmatter de workflow + ciclo de vida de run — domínio de `specs/features/multi-agent-orchestration/SPEC.md`
- Conteúdo dos 2 workflows seed (`spec-refinement`, `tdd-cycle`) — entregue como código em `dadaia_workspace/public/workflows/`
- Decisões cosméticas de naming dentro de `public/<type>/` quando não impactam contratos cross-feature

> **Nota:** CI/CD e publicação no PyPI deixaram de ser "fora de escopo" e passam a ser cobertos por `specs/features/release-pipeline/SPEC.md` a partir desta v3.1.
