# TASKS: dadaia-workspace — Backlog Completo

> **Status:** Em revisão
> **Versão:** 3.1
> **Referência:** `specs/PLAN.md` (v3.1)

## Convenção de estado

| Marcador | Estado | Semântica |
|---|---|---|
| `[ ]` | OPEN | Não iniciada |
| `[-]` | IN PROGRESS | Agente está trabalhando — não pegar sem desmarcar a anterior |
| `[x]` | DONE | Implementada, verificada, commitada |

**Regra operacional:** ao iniciar uma task, marque `[-]` antes de escrever qualquer código. Ao concluir, mude para `[x]`. Nunca duas tasks com `[-]` ao mesmo tempo no mesmo TASKS.md.

---

## Pre-implementation checklist
- [x] `specs/SPEC.md` marcado como Aprovado
- [x] `specs/foundation/SPEC.md` marcado como Aprovado
- [x] `specs/features/spec-context-project/SPEC.md` marcado como Aprovado
- [x] `specs/features/dadaia-academy/SPEC.md` marcado como Aprovado
- [x] `specs/features/agents/SPEC.md` marcado como Aprovado
- [x] `specs/features/agent-rules-skills/SPEC.md` marcado como Aprovado
- [x] `specs/features/dev-workspace-governance/SPEC.md` marcado como Aprovado
- [x] `specs/PLAN.md` marcado como Aprovado

---

## Fase 0 — Foundation cleanup

- [x] T01 — Deletar `dadaia_workspace/infrastructure/database.py`
- [x] T02 — Deletar `dadaia_workspace/infrastructure/sqlite_repositories.py`
- [x] T03 — Deletar `dadaia_workspace/core/protocols/repositories.py`
- [x] T04 — Deletar `dadaia_workspace/infrastructure/json_active_context_store.py`
- [x] T05 — Atualizar `dadaia_workspace/core/models/spec_context.py`: renomear `primary_repo_slug` → `repo_slug`; adicionar `is_primary: bool`, `repo_url: str`, `created_at: str`, `activated_at: str | None`
- [x] T06 — Atualizar `dadaia_workspace/core/models/workspace.py`: remover `contexts_dir` e `data_dir`
- [x] T07 — Renomear `active_context_store.py` → `context_store.py`; expandir interface: `save(ctx)`, `update(ctx)`, `get(name)`, `list_all()`, `delete(name)`
- [x] T08 — Criar `dadaia_workspace/core/protocols/primary_context_store.py`: `write(name, repo_slug, specs_dir)`, `read()`, `clear()`
- [x] T09 — Criar `dadaia_workspace/core/protocols/git_client.py`: `clone(url, dest)`, `is_dirty(path)`, `commit_all(path, msg)`, `has_remote(path)`, `push(path)`
- [x] T10 — Atualizar `dadaia_workspace/core/exceptions.py`: adicionar `GitSyncError`, `GitCloneError`
- [x] T11 — Criar `dadaia_workspace/infrastructure/json_context_store.py`: CRUD atômico sobre `spec_contexts.json` (version + contexts array)
- [x] T12 — Criar `dadaia_workspace/infrastructure/json_primary_context_store.py`: read/write/clear de `primary_context.json`
- [x] T13 — Criar `dadaia_workspace/infrastructure/git_subprocess.py`: `GitSubprocessClient` implementando `GitClient`
- [x] T14 — Reescrever `dadaia_workspace/container.py`: remover SQLite; montar com `JsonContextStore`, `JsonPrimaryContextStore`, `GitSubprocessClient`

---

## Fase 1 — WorkspaceService

- [x] T15 — Atualizar `features/workspace/service.py`: remover `"data"` de `_DADAIA_DURABLE_DIRS`; adicionar `"reports/architect-agent-review"`, `"reports/specs-sdd-review"`, `"reports/bugs/soft-engineer-report"`
- [x] T16 — Atualizar `features/workspace/service.py`: `init()` cria `spec_contexts.json` vazio `{"version":"1","contexts":[]}` e `academy.json` vazio `{"version":"1","courses":[]}`; remove `bootstrap_schema()` e `workspace_repo.save()`
- [x] T17 — Atualizar `features/workspace/service.py`: `is_initialized()` checa `states/spec_contexts.json`
- [x] T18 — Atualizar `tests/fakes.py`: substituir `FakeWorkspaceRepository`, `FakeSpecContextRepository`, `FakeActiveContextStore` por `FakeContextStore`, `FakePrimaryContextStore`, `FakeGitClient`; adicionar `FakeCourseStore`
- [x] T19 — Criar `tests/unit/test_workspace_service.py`

---

## Fase 2 — SpecContextService (lifecycle completo)

- [x] T20 — Reescrever `features/spec_context/service.py`: `create(name, repo_slug, repo_url)` sem checar disco; `is_primary=False`, `created_at=now()`
- [x] T21 — Implementar `activate(name)` em service: clona via `GitClient` se `repos/<slug>/` ausente; auto-promove se sem primário; `activated_at=now()`
- [x] T22 — Implementar `deactivate(name)` em service: rejeita se `is_primary`; `git_client.is_dirty()` + `commit_all()` + `push()`; remove repo; marca `inativo`; `activated_at=None`
- [x] T23 — Implementar `promote(name)` em service: remove `is_primary` do anterior; escreve `primary_context.json` via `PrimaryContextStore`
- [x] T24 — Criar `features/spec_context/doctor.py`: `DoctorService` com `check()` (6 invariantes) e `fix()` (5 ações de reparo)
- [x] T25 — Criar `cli/commands/doctor.py`: `dadaia doctor [--fix]`
- [x] T26 — Criar `tests/unit/test_spec_context_service.py`

---

## Fase 3 — CLI alignment

- [x] T27 — Atualizar `cli/commands/context.py`: `create` chama `repos_service.get_repo_url(slug)` antes de `context_service.create()`
- [x] T28 — Atualizar `cli/commands/context.py`: `deactivate` recebe `<name>` como argumento obrigatório
- [x] T29 — Atualizar `cli/commands/context.py`: adicionar subcomando `promote <name>`
- [x] T30 — Atualizar `cli/commands/context.py`: `show --json` inclui `is_primary`; `_ctx_to_dict()` usa `repo_slug`
- [x] T31 — Atualizar `cli/commands/context.py`: `list` exibe coluna `is_primary`
- [x] T32 — Atualizar `cli/commands/init.py`: remover referências a SQLite; output alinhado ao FR-001
- [x] T33 — Atualizar `cli/main.py`: registrar `doctor` e `academy` command groups

---

## Fase 4 — Academy

- [x] T34 — Criar `dadaia_workspace/core/models/course.py`: `Course` frozen dataclass (slug, name, module_number, module_name, created_at, course_dir)
- [x] T35 — Criar `dadaia_workspace/core/protocols/course_store.py`: `CourseStore` Protocol
- [x] T36 — Criar `dadaia_workspace/infrastructure/json_course_store.py`: CRUD atômico sobre `academy.json`
- [x] T37 — Criar `dadaia_workspace/features/academy/service.py`: `AcademyService` com `list()`, `create()`, `delete()`, `update()`, `list_modules()`
- [x] T38 — Criar `dadaia_workspace/cli/commands/academy.py`: 5 subcomandos Typer
- [x] T39 — Atualizar `container.py`: montar `AcademyService`
- [x] T40 — Criar `tests/unit/test_academy_service.py`
- [x] T41 — Criar `tests/e2e/features/test_academy.py`

---

## Fase 5 — Universal agentic assets

- [x] T42 — Atualizar `infrastructure/public_assets.py`: suportar `stage`, manifest com hashes e projeções `all|claude|codex|opencode|agents`
- [x] T43 — Criar agente canônico de arquitetura em `dadaia_workspace/public/agents/` _(criado como `software-architect.md`; `architect-agent.md` original descontinuado e removido)_
- [x] T44 — Criar `dadaia_workspace/public/agents/product-auditor-agent.md`
- [x] T45 — Criar agente canônico de produto em `dadaia_workspace/public/agents/` _(criado como `product-engineer.md`; `product-engineer-agent.md` renomeado)_
- [x] T46 — Criar `dadaia_workspace/public/agents/soft-engineer-agent.md`
- [x] T47 — Criar `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`
- [x] T48 — Criar `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`
- [x] T49 — Criar `dadaia_workspace/public/skills/dadaia-workspace-doctor/SKILL.md`
- [x] T50 — Criar `dadaia_workspace/public/commands/dadaia-workspace-doctor.md`
- [x] T50a — Criar/organizar templates universais para `AGENTS.md`, `opencode.json`, `.codex/config.toml` e `.codex/hooks.json`
- [x] T50b — Implementar `dadaia public doctor` com status `ok`, `missing`, `drift`, `unsupported`
- [x] T50c — Garantir no-overwrite sem `--force` e overwrite de assets lib-originated com `--force`

---

## Fase 6 — Quality gate

> Estes são gates de verificação contínua — devem ser re-executados antes de qualquer release.

- [x] T51 — `ruff format dadaia_workspace/ tests/` — sem erros
- [x] T52 — `ruff check dadaia_workspace/ tests/` — sem erros
- [x] T53 — `mypy --strict dadaia_workspace/` — sem erros
- [x] T54 — `pytest tests/unit/ -v` — todos passam
- [x] T55 — `pytest tests/integration/ -v` — todos passam
- [x] T56 — `pytest tests/e2e/ -v` — todos passam
- [ ] T57 — Teste manual E2E: `dadaia init`, context lifecycle, academy CRUD, `dadaia public install` instala agents/

---

## Fase 7 — Governança SDD (backlog crítico)

> Fase criada em 2026-05-11 após auditoria grill-me revelar duas falhas de governança graves.

### 7A — Correção do sdd-spec-gate (CRÍTICO)

**Problema identificado:** `sdd-spec-gate.sh` só protege paths VPS (`services/`, `docker/`, `scripts/`). Qualquer escrita em `repos/<slug>/` não é interceptada — o SDD nunca disparou durante o desenvolvimento da dadaia-workspace. Além disso, o gate verifica apenas "existe algum SPEC.md aprovado?" em vez de "existe uma task aberta que cobre este arquivo?", tornando a verificação trivialmente satisfatória.

- [x] T58 — Escrever `specs/features/sdd-enforcement/SPEC.md`: especificar escopo correto do gate (protege `repos/<slug>/` quando slug tem context ativo), granularidade mínima aceitável, e política de fail-open vs fail-closed por tipo de path
- [x] T59 — Escrever `specs/features/sdd-enforcement/PLAN.md` e `TASKS.md`
- [x] T60 — Implementar: expandir `case` do `sdd-spec-gate.sh` para incluir `"$WS/repos/"*` com resolução de `specs_dir` via context ativo
- [x] T61 — Implementar: adicionar verificação de TASKS.md — bloquear Write/Edit se nenhuma task OPEN ou IN PROGRESS cobre o arquivo-alvo (ou se o arquivo está fora do escopo de qualquer task aprovada)
- [x] T62 — Distribuir script atualizado via `dadaia public install` para que todos os tools (Claude Code, Codex, OpenCode) usem o gate correto
- [x] T63 — Adicionar teste E2E: verificar que Write em `repos/<slug>/` sem context ativo é bloqueado; verificar que Write com context ativo e spec aprovada passa

### 7B — Task state tracking: OPEN → IN PROGRESS → DONE

**Problema identificado:** O TASKS.md atual só tem dois estados (`[ ]` e `[x]`). Quando um agente inicia uma task, não há sinal de que ela está em andamento — outro agente (ou instância paralela) pode pegar a mesma task, causando conflito. Não há rastreabilidade de "quem pegou o quê".

- [x] T64 — Escrever `specs/features/task-state-tracking/SPEC.md`: definir os 3 estados (`[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE), semântica de cada transição, regras de precedência (nunca 2 `[-]` simultâneos), e como o gate usa o estado para decidir
- [x] T65 — Escrever `specs/features/task-state-tracking/PLAN.md` e `TASKS.md`
- [x] T66 — Criar skill `dadaia-task-manager/SKILL.md` em `dadaia_workspace/public/skills/`: protocolo para agentes lerem, atualizarem e commitarem mudanças de estado em TASKS.md antes de iniciar work
- [x] T67 — Integrar com sdd-spec-gate: Write/Edit só permitido se houver uma task com estado `[-]` (IN PROGRESS) que cubra o arquivo-alvo
- [x] T68 — Distribuir skill via `dadaia public install --target all`
- [x] T69 — Atualizar `foundation/SPEC.md` e `specs/SPEC.md` para refletir a nova política de estados de task como contrato normativo

---

## Fase 8 — Branch tracking + Export trim

> Fase criada em 2026-05-12. Garante que export/import restaura a branch exata de cada repo.

### 8A — Modelo e protocolo

- [x] T70 — Adicionar `current_branch: str | None = None` a `dadaia_workspace/core/models/spec_context.py` (`SpecContextProject`)
- [x] T71 — Adicionar `current_branch(path: Path) -> str` ao Protocol `dadaia_workspace/core/protocols/git_client.py`
- [x] T72 — Adicionar `checkout(path: Path, branch: str) -> None` ao Protocol `dadaia_workspace/core/protocols/git_client.py`
- [x] T73 — Implementar `current_branch()` e `checkout()` em `dadaia_workspace/infrastructure/git_subprocess.py`
- [x] T74 — Atualizar `dadaia_workspace/infrastructure/json_context_store.py`: ler/escrever `current_branch` (campo opcional com default `None`)

### 8B — Activate e Deactivate

- [x] T75 — Atualizar `features/spec_context/service.py` `activate()`: após clone, se `ctx.current_branch` estiver definido, chamar `git_client.checkout(dest, ctx.current_branch)`; depois ler e armazenar branch atual via `git_client.current_branch(dest)`
- [x] T76 — Atualizar `features/spec_context/service.py` `deactivate()`: antes do git sync, ler e armazenar `current_branch` via `git_client.current_branch(repo_path)`

### 8C — Export trim + branch refresh

- [x] T77 — Atualizar `features/export/service.py` `resolve_includes()`: remover `.dadaia/scripts/`, `.dadaia/agentic/manifest.json`, `.dadaia/src/`
- [x] T78 — Adicionar `_refresh_branches()` ao `ExportService`: para cada repo ativo em disco, ler `git_client.current_branch()` e atualizar `spec_contexts.json` atomicamente antes de criar o artefato
- [x] T79 — Chamar `_refresh_branches()` em `ExportService.run()` antes de `resolve_includes()`

### 8D — Verificação E2E

- [x] T80 — Teste manual: checkout branch `feature/test` em um repo ativo → `dadaia export` → verificar que `spec_contexts.json` no artefato tem `current_branch: feature/test` → `dadaia import` em dir novo → verificar que o repo foi clonado e está na branch `feature/test`
- [x] T81 — Verificar que artefato não contém `.dadaia/scripts/`, `.dadaia/agentic/`, `.dadaia/src/`

---

## Fase 9 — Multi-Agent Orchestration (v0.1)

> Endereça `specs/features/multi-agent-orchestration/SPEC.md`. **Pré-requisito:** SPEC e PLAN aprovados (gate de operador). Tasks marcadas como `[P]` podem rodar em paralelo (sem precondição inter-task além do gate de aprovação).

### 9A — Models e Protocols (todas paralelizáveis após aprovação)

- [x] T82 [P] — Criar `dadaia_workspace/core/models/workflow.py`: frozen dataclasses `WorkflowDefinition`, `WorkflowStage`, `WorkflowInput`, `ExitCriterion`
- [x] T83 [P] — Criar `dadaia_workspace/core/models/run_state.py`: frozen dataclasses `RunManifest`, `StageState`, `RunEvent`, `StageInvocation`, `StageResult`, `DispatcherCapabilities`
- [x] T84 [P] — Criar `dadaia_workspace/core/protocols/workflow_store.py`: `WorkflowStore` Protocol (list, get, validate)
- [x] T85 [P] — Criar `dadaia_workspace/core/protocols/run_state_store.py`: `RunStateStore` Protocol (create_run, load_run, update_manifest, append_event, list_runs, iter_events)
- [x] T86 [P] — Criar `dadaia_workspace/core/protocols/agent_dispatcher.py`: `AgentDispatcher` Protocol (capabilities, dispatch, dispatch_parallel)
- [x] T87 [P] — Adicionar `pyyaml = "^6.0"` em `pyproject.toml` `[tool.poetry.dependencies]` (ADR-ORCH-001)
- [x] T88 [P] — Adicionar exceções específicas em `core/exceptions.py`: `WorkflowSchemaError`, `WorkflowCycleError`, `WorkflowNotFoundError`, `RunNotFoundError`, `OrchestrationUnsupportedError`

### 9B — Infrastructure (depende de Protocols)

- [x] T89 — Criar `dadaia_workspace/infrastructure/markdown_workflow_store.py`: parser YAML frontmatter + validação de schema (DAG via Kahn; agente existe; parallel_group sem deps internas; etc.)
- [x] T90 [P] — Criar `dadaia_workspace/infrastructure/json_run_state_store.py`: writes atômicas de `manifest.json`; append-only `events.jsonl`; ULID-like run_id
- [x] T91 [P] — Criar `dadaia_workspace/infrastructure/claude_agent_dispatcher.py`: mode=native; prepara `invocation.md` por stage; header de PARALLEL GROUP quando aplicável
- [x] T92 [P] — Criar `dadaia_workspace/infrastructure/cli_agent_dispatcher.py`: mode=cli-only (default) + adapters internos para opencode (best-effort-sequential) e codex (unsupported em parallel_group)

### 9C — Feature module (depende de Protocols + Models)

- [x] T93 — Criar `dadaia_workspace/features/orchestration/resolver.py`: `InputResolver` (função pura: workflow_input + stage_output → StageInvocation.inputs)
- [x] T94 — Criar `dadaia_workspace/features/orchestration/runner.py`: `WorkflowRunner` — execução DAG, propagação de status, agrupamento parallel_group, `must_include` checks
- [x] T95 — Criar `dadaia_workspace/features/orchestration/service.py`: `OrchestrationService` (list_workflows, show_workflow, start_run, resume_run, get_run_status) — consome apenas Protocols

### 9D — Composition root + CLI

- [x] T96 — Atualizar `dadaia_workspace/container.py`: adicionar `build_orchestration_service(workspace_root, runtime=None)` + helper `_select_dispatcher(runtime)` (lê `DADAIA_AGENT_RUNTIME` env var; default `cli`)
- [x] T97 — Criar `dadaia_workspace/cli/commands/orchestrate.py`: Typer app com 5 subcomandos `list`, `show`, `run`, `status`, `resume`; flags `--context`, `--runtime`, `--input k=v`, `--dry-run`, `--json`
- [x] T98 — Atualizar `dadaia_workspace/cli/main.py`: registrar grupo `orchestrate`

### 9E — Distribuição universal + doctor

- [x] T99 — Atualizar `dadaia_workspace/infrastructure/public_assets.py`: incluir `"workflows"` em `_COPY_DIRS`; adicionar projeção para `.agents/workflows/`, `.claude/workflows/`, `.opencode/workflows/`, `.codex/workflows/`
- [x] T100 — Atualizar `dadaia_workspace/features/public/doctor.py`: adicionar status `partial` ao classificador (manter `ok | missing | drift | unsupported` + `partial`)
- [x] T101 — Atualizar `dadaia_workspace/features/public/staging.py`: rejeitar `*.workflow.md` que falham validação de schema (abort do `dadaia public stage` com mensagem RF-QA-007)

### 9F — Input Contract nos agentes existentes (todos paralelizáveis)

- [x] T102 [P] — Adicionar bloco `input_contract` em `dadaia_workspace/public/agents/product-engineer.md`
- [x] T103 [P] — Adicionar bloco `input_contract` em `dadaia_workspace/public/agents/software-architect.md`
- [x] T104 [P] — Adicionar bloco `input_contract` em `dadaia_workspace/public/agents/software-engineer.md`
- [x] T105 [P] — Adicionar bloco `input_contract` em `dadaia_workspace/public/agents/qa-engineer.md`
- [x] T106 [P] — Adicionar bloco `input_contract` em `dadaia_workspace/public/agents/devops-engineer.md`
- [x] T107 [P] — Adicionar bloco `input_contract` em `dadaia_workspace/public/agents/game-developer.md`

### 9G — Workflows seed (depende de infraestrutura)

- [x] T108 [P] — Criar `dadaia_workspace/public/workflows/spec-refinement.workflow.md` (workflow desta própria evolução: discovery → 3-paralelo → synthesis com 2 gates)
- [x] T109 [P] — Criar `dadaia_workspace/public/workflows/tdd-cycle.workflow.md` (par software-engineer ↔ qa-engineer; consult-product gate opcional)

### 9H — Testes (todos paralelizáveis após implementação)

- [x] T110 [P] — Adicionar fakes em `tests/fakes.py`: `FakeWorkflowStore`, `FakeRunStateStore`, `FakeAgentDispatcher` (3 variantes: native, best-effort, unsupported)
- [x] T111 [P] — Criar `tests/unit/test_workflow_schema.py`: parse válido + 5 cenários de erro (sem name, sem stages, stage sem id/agent, ciclo, parallel_group inválido)
- [x] T112 [P] — Criar `tests/unit/test_run_state_store.py`: criar run, transições, append events, resume idempotente, atomicidade
- [x] T113 [P] — Criar `tests/unit/test_orchestration_service.py`: gate pausa execução, status retorna gate-pending, resume não reexecuta stages done
- [x] T114 [P] — Criar `tests/unit/test_orchestration_runtime.py`: testes paramétricos por dispatcher (claude/opencode/codex/cli)
- [x] T115 [P] — Criar `tests/integration/test_cli_orchestrate.py`: happy path + erros (workflow inexistente, run-id inexistente, contexto ausente, gate sem aprovação)
- [x] T116 [P] — Criar `tests/e2e/features/test_orchestration_pipeline.py`: `stage → install → list → run → status → resume → status` em modo `--runtime cli`
- [x] T117 [P] — Adicionar testes em `tests/e2e/features/test_public_pipeline.py`: validação de schema para workflows seed; `partial`/`unsupported` no doctor

---

## Fase 11 — Game Agents Split (game-developer → game-developer + game-designer + game-tester)

> Endereça a divisão do agente monolítico `game-developer` em 3 agentes especializados com skills próprias e workflows exclusivos para games. Referência: design doc em `docs/superpowers/specs/2026-05-16-game-agents-split-design.md`.

### 11A — Design e especificação

- [x] T145 — Escrever design doc em `docs/superpowers/specs/2026-05-16-game-agents-split-design.md`
- [x] T146 — Criar `specs/features/game-agents-split/SPEC.md` com Status: Aprovado (extraído do design doc)
- [x] T147 — Criar `specs/features/game-agents-split/PLAN.md`
- [x] T148 — Criar `specs/features/game-agents-split/TASKS.md`

### 11B — Novos agentes

- [x] T149 — Criar `dadaia_workspace/public/agents/game-designer.md`
- [x] T150 — Criar `dadaia_workspace/public/agents/game-tester.md`
- [x] T151 — Atualizar `dadaia_workspace/public/agents/game-developer.md` (narrow scope, redistribuir skills)

### 11C — Novas skills

- [x] T152 — Criar `dadaia_workspace/public/skills/game-unreal-developer/SKILL.md`
- [x] T153 — Criar `dadaia_workspace/public/skills/game-flight-dynamics/SKILL.md`
- [x] T154 — Criar `dadaia_workspace/public/skills/game-unreal-designer/SKILL.md`
- [x] T155 — Criar `dadaia_workspace/public/skills/game-visual-design/SKILL.md`
- [ ] T156 — Criar `dadaia_workspace/public/skills/game-geospatial-pipeline/SKILL.md`
- [ ] T157 — Criar `dadaia_workspace/public/skills/game-audio-design/SKILL.md`
- [ ] T158 — Criar `dadaia_workspace/public/skills/game-testing-ue5/SKILL.md`

### 11D — Novos workflows

- [ ] T159 — Criar `dadaia_workspace/public/workflows/game-spec-definition.workflow.md`
- [ ] T160 — Criar `dadaia_workspace/public/workflows/game-dev-cycle.workflow.md`
- [ ] T161 — Criar `dadaia_workspace/public/workflows/game-bugfix.workflow.md`

### 11E — Atualizações

- [x] T162 — Atualizar `dadaia_workspace/public/rules/game-developer-scope.md` (3 agentes + sub-domínios)
- [ ] T163 — Atualizar `dadaia_workspace/public/workflows/tdd-cycle.workflow.md` (remover game-developer do implementer list)
- [x] T166 — Criar `dadaia_workspace/public/rules/game-agents-coordination.md` (decision authority matrix + protocolo anti-deadlock com dadaia-grill-me)

### 11F — Propagação

- [ ] T164 — Rodar `dadaia public stage && dadaia public install --target all`
- [ ] T165 — Rodar `dadaia public doctor` — todos os entries devem ser `[ok]`

---

## Fase 10 — Release Pipeline v0.1.0

> Endereça `specs/features/release-pipeline/SPEC.md`. Fase 10A é pré-requisito para Fase 10B (não publicar com CI vermelho).

### 10A — Pré-release: fechar gaps QA (CI verde)

- [x] T-IMP-REWRITE-001 — Em `features/import_/service.py`: detectar e reescrever paths absolutos em arquivos não-lib-originated que apontem para fora do novo `workspace_root` (closes BUG-003 root cause). Foco em `.claude/settings.json`, `.codex/hooks.json`, `opencode.json`. Política: rewrite quando match exato com `old_workspace_root` no path; warning quando match parcial; ignorar paths externos legítimos.


- [x] T118 — Fix: `tests/e2e/features/test_public_pipeline.py` — adicionar `dadaia-workspace-manager` em `EXPECTED_SKILLS` (corrige 2 falhas atuais)
- [x] T119 — Fix: `tests/e2e/features/test_academy.py` — corrigir incompatibilidade Typer (`Parameter.make_metavar()` missing `ctx`). Considerar pin de versão Typer em `pyproject.toml` ou substituir `--help` por chamada direta de subcomando
- [x] T120 [P] — Criar `tests/unit/test_export_service.py`: cobertura ≥80% para `features/export/service.py`
- [x] T121 [P] — Criar `tests/unit/test_import_service.py`: cobertura ≥80% para `features/import_/service.py`
- [x] T122 [P] — Criar `tests/unit/test_repos_service.py`: cobertura ≥80% para `features/repos/service.py`
- [x] T123 [P] — Criar `tests/integration/test_cli_context.py`: cobertura E2E para `dadaia context {create, list, show, activate, deactivate, promote, delete, use}`
- [x] T124 [P] — Criar `tests/integration/test_cli_export.py`: cobertura E2E para `dadaia export` (happy + flags `--list`, `--exclude-mnt`, `--include-reports`)
- [x] T125 [P] — Criar `tests/integration/test_cli_import.py`: cobertura E2E para `dadaia import` (happy + flags `--skip-mnt`, `--skip-activate`, `--dry-run`)
- [x] T126 [P] — Criar `tests/integration/test_cli_doctor.py`: cobertura E2E para `dadaia doctor [--fix]` em estados degradados
- [x] T127 [P] — Criar `tests/integration/test_hooks.py`: testes de `ctx-inject.sh` e `sdd-spec-gate.sh` via subprocess
- [x] T128 — Atualizar `pyproject.toml`: adicionar `[tool.pytest.ini_options]` com `addopts = "--cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80"` (somente após T118–T127 verdes)

### 10B — Pipeline de CI/CD

- [x] T129 — Criar `.github/workflows/ci.yml`: 3 jobs paralelos (lint, typecheck, test) + 1 condicional (pr-title); ubuntu-latest; Python 3.12; cache poetry
- [x] T130 — Criar `.github/workflows/release.yml`: 4 jobs sequenciais (validate → build → publish → smoke-test); permissions: `contents: read` workflow-level + `id-token: write` job-level no publish; `environment: pypi`
- [x] T131 [P] — Criar `.github/CODEOWNERS`: global fallback + ownership de `.github/`, `pyproject.toml`, `Makefile`, `scripts/`
- [x] T132 [P] — Criar `CHANGELOG.md`: Keep a Changelog 1.1.0; seção `[Unreleased]` + `[0.1.0]`
- [x] T133 [P] — Criar `RELEASING.md`: passo a passo humano (10 passos do report devops)
- [x] T134 — Garantir que `poetry.lock` está commitado em `main`

### 10C — Configuração operacional (operador, não código)

- [ ] T135 — Operador: criar conta PyPI com 2FA (e-mail marcoaurelioreislima@gmail.com)
- [ ] T136 — Operador: configurar pending publisher no PyPI para `dadaia-workspace` (workflow `release.yml`, environment `pypi`, repo owner/name corretos)
- [ ] T137 — Operador: criar environment `pypi` no GitHub Actions com deployment branches `v*.*.*`
- [ ] T138 — Operador: configurar branch protection em `main` (require PR, required status checks `lint`/`typecheck`/`test`, no force push, include administrators)

### 10D — Release v0.1.0

- [x] T139 — Bump `pyproject.toml` para versão `0.1.0` (já está)
- [x] T140 — Atualizar `CHANGELOG.md`: mover `[Unreleased]` items para `[0.1.0] — <data>`
- [ ] T141 — Tag `v0.1.0` em `main` e push (`git tag v0.1.0 && git push origin v0.1.0`)
- [ ] T142 — Monitorar `release.yml` no GitHub Actions (validate → build → publish → smoke-test)
- [ ] T143 — Verificar `https://pypi.org/project/dadaia-workspace/0.1.0/`
- [ ] T144 — Verificar smoke local: `pip install dadaia-workspace==0.1.0` em venv limpa + `dadaia --help` + `dadaia init` em tmpdir
