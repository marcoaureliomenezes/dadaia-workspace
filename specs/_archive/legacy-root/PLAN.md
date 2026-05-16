# PLAN: dadaia-workspace — Backlog Completo

> **Status:** Em revisão
> **Versão:** 3.1
> **Referências:** `specs/SPEC.md` (v3.1), `specs/foundation/SPEC.md` (v3.1), todos os `specs/features/*/SPEC.md` incluindo `multi-agent-orchestration` e `release-pipeline`

---

## Decisões Técnicas

| Decisão | Escolha |
|---|---|
| Persistência | Plain JSON via `os.replace()`. SQLite removido. |
| Protocol de contextos | Dois: `ContextStore` (spec_contexts.json) + `PrimaryContextStore` (primary_context.json) |
| Git operations | `GitClient` Protocol → `git_subprocess.py` via `subprocess` (stdlib) |
| Academy storage | `CourseStore` Protocol → `json_course_store.py` |
| Workspace init check | `is_initialized()` checa existência de `.dadaia/states/spec_contexts.json` |
| Repo validation em create | CLI layer chama `ReposService` → obtém `repo_url` → passa para `SpecContextService.create()` |
| Multi-context | Múltiplos `ativo` permitidos; apenas um `is_primary=True` por vez |
| Agentes públicos | 4 personas `.md` em `dadaia_workspace/public/agents/`; staged em `.dadaia/agentic/` e projetadas para runtimes suportados |

---

## Fases e Arquivos

### Fase 0 — Foundation cleanup (pré-requisito de tudo)

Remove SQLite e alinha core models + protocols com a spec v4.0.

**Deletar:**
- `dadaia_workspace/infrastructure/database.py`
- `dadaia_workspace/infrastructure/sqlite_repositories.py`
- `dadaia_workspace/core/protocols/repositories.py`
- `dadaia_workspace/infrastructure/json_active_context_store.py`

**Modificar:**
- `dadaia_workspace/core/models/spec_context.py` — campos v4.0: `repo_slug`, `is_primary`, `repo_url`, `created_at`, `activated_at`
- `dadaia_workspace/core/models/workspace.py` — remover `contexts_dir`, `data_dir`
- `dadaia_workspace/core/protocols/active_context_store.py` → renomear para `context_store.py`; interface: `save`, `update`, `get`, `list_all`, `delete`
- `dadaia_workspace/core/exceptions.py` — adicionar `GitSyncError`, `GitCloneError`

**Criar:**
- `dadaia_workspace/core/protocols/context_store.py`
- `dadaia_workspace/core/protocols/primary_context_store.py` — `write(name, repo_slug, specs_dir)`, `read()`, `clear()`
- `dadaia_workspace/core/protocols/git_client.py` — `clone`, `is_dirty`, `commit_all`, `has_remote`, `push`
- `dadaia_workspace/infrastructure/json_context_store.py` — CRUD atômico sobre spec_contexts.json
- `dadaia_workspace/infrastructure/json_primary_context_store.py` — read/write/clear de primary_context.json
- `dadaia_workspace/infrastructure/git_subprocess.py` — implementação via subprocess
- `dadaia_workspace/container.py` — reescrito; usa JSON stores

### Fase 1 — WorkspaceService (dadaia init)

**Modificar:**
- `dadaia_workspace/features/workspace/service.py`
  - `_DADAIA_DURABLE_DIRS`: remover `"data"`; adicionar report subdirs
  - `init()`: criar JSON files vazios; remover SQLite bootstrap
  - `is_initialized()`: checar `states/spec_contexts.json`
- `tests/fakes.py` — substituir fakes SQLite por `FakeContextStore`, `FakePrimaryContextStore`, `FakeGitClient`, `FakeCourseStore`

**Criar:**
- `tests/unit/test_workspace_service.py`

### Fase 2 — SpecContextService (lifecycle completo)

**Reescrever:**
- `dadaia_workspace/features/spec_context/service.py`
  - `create(name, repo_slug, repo_url)` — sem checar disco
  - `activate(name)` — clona via `GitClient`; auto-promove
  - `deactivate(name)` — rejeita se `is_primary`; git sync; remove repo
  - `promote(name)` — escreve `primary_context.json`

**Criar:**
- `dadaia_workspace/features/spec_context/doctor.py` — `DoctorService` (6 invariantes + 5 ações de reparo)
- `dadaia_workspace/cli/commands/doctor.py`
- `tests/unit/test_spec_context_service.py`

### Fase 3 — CLI alignment

**Modificar:**
- `dadaia_workspace/cli/commands/context.py` — `deactivate <name>`, `promote`, `show --json` com `is_primary`, `_ctx_to_dict` com `repo_slug`
- `dadaia_workspace/cli/commands/init.py` — remover SQLite
- `dadaia_workspace/cli/main.py` — adicionar `doctor` e `academy`

### Fase 4 — Academy

**Criar:**
- `dadaia_workspace/core/models/course.py`
- `dadaia_workspace/core/protocols/course_store.py`
- `dadaia_workspace/infrastructure/json_course_store.py`
- `dadaia_workspace/features/academy/service.py`
- `dadaia_workspace/cli/commands/academy.py`
- `tests/unit/test_academy_service.py`
- `tests/e2e/features/test_academy.py`

### Fase 5 — Universal agentic assets

**Modificar:**
- `dadaia_workspace/infrastructure/public_assets.py` — suportar staging, manifest e projeções runtime
- `dadaia_workspace/features/public/service.py` — adicionar `stage`, `install --target all|claude|codex|opencode|agents` e `doctor`
- `dadaia_workspace/cli/commands/public.py` — expor `stage`, `install` e `doctor`

**Criar:**
- `dadaia_workspace/public/agents/architect-agent.md`
- `dadaia_workspace/public/agents/product-auditor-agent.md`
- `dadaia_workspace/public/agents/product-engineer-agent.md`
- `dadaia_workspace/public/agents/soft-engineer-agent.md`
- `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`
- `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`
- `dadaia_workspace/public/skills/dadaia-workspace-doctor/SKILL.md`
- `dadaia_workspace/public/commands/dadaia-workspace-doctor.md`
- templates/configs universais em `dadaia_workspace/public/`

### Fase 6 — Quality gate

```bash
cd /home/ubuntu/workspace/repos/dadaia-workspace
ruff format dadaia_workspace/ tests/
ruff check dadaia_workspace/ tests/
mypy --strict dadaia_workspace/
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

---

### Fase 9 — Multi-Agent Orchestration (multi-agent-orchestration v0.1)

> Endereça `specs/features/multi-agent-orchestration/SPEC.md`. Adiciona orquestração como tipo de asset universal de primeira classe + CLI `dadaia orchestrate`. Decisões: ADR-ORCH-001..006 (vide spec).

**Criar (Protocols em `core/protocols/`):**
- `dadaia_workspace/core/protocols/workflow_store.py` — Protocol `WorkflowStore` (list, get, validate)
- `dadaia_workspace/core/protocols/run_state_store.py` — Protocol `RunStateStore` (create_run, load_run, update_manifest, append_event, list_runs, iter_events)
- `dadaia_workspace/core/protocols/agent_dispatcher.py` — Protocol `AgentDispatcher` (capabilities, dispatch, dispatch_parallel) + `DispatcherCapabilities` dataclass

**Criar (Models em `core/models/`):**
- `dadaia_workspace/core/models/workflow.py` — `WorkflowDefinition`, `WorkflowStage`, `WorkflowInput`, `ExitCriterion` (frozen dataclasses)
- `dadaia_workspace/core/models/run_state.py` — `RunManifest`, `StageState`, `RunEvent`, `StageInvocation`, `StageResult`

**Criar (feature module `features/orchestration/`):**
- `dadaia_workspace/features/orchestration/__init__.py`
- `dadaia_workspace/features/orchestration/service.py` — `OrchestrationService` (list_workflows, show_workflow, start_run, resume_run, get_run_status)
- `dadaia_workspace/features/orchestration/runner.py` — `WorkflowRunner` (DAG execution, propagação de status, agrupamento parallel_group)
- `dadaia_workspace/features/orchestration/resolver.py` — `InputResolver` (função pura — workflow_input + stage_output → StageInvocation.inputs)

**Criar (implementações em `infrastructure/`):**
- `dadaia_workspace/infrastructure/markdown_workflow_store.py` — `MarkdownWorkflowStore` (lê `*.workflow.md` de `.dadaia/agentic/workflows/`; parse YAML + validação de schema; usa `pyyaml`)
- `dadaia_workspace/infrastructure/json_run_state_store.py` — `JsonRunStateStore` (manifest.json atômico + events.jsonl append-only; ULID-like run_id)
- `dadaia_workspace/infrastructure/claude_agent_dispatcher.py` — `ClaudeAgentDispatcher` (mode=native; prepara `invocation.md` por stage; host agent dispara via tool `Agent`)
- `dadaia_workspace/infrastructure/cli_agent_dispatcher.py` — `CliAgentDispatcher` (default; mode=cli-only) + adapters para OpenCode (`best-effort-sequential`) e Codex (`unsupported` para parallel_group)

**Criar (CLI em `cli/commands/`):**
- `dadaia_workspace/cli/commands/orchestrate.py` — Typer app com 5 subcomandos: `list`, `show`, `run`, `status`, `resume`

**Criar (workflows seed em `public/workflows/`):**
- `dadaia_workspace/public/workflows/spec-refinement.workflow.md`
- `dadaia_workspace/public/workflows/tdd-cycle.workflow.md`

**Modificar:**
- `dadaia_workspace/container.py` — adicionar `build_orchestration_service(workspace_root, runtime=None)` + `_select_dispatcher(runtime)` helper
- `dadaia_workspace/cli/main.py` — registrar grupo `orchestrate`
- `dadaia_workspace/infrastructure/public_assets.py` — incluir `"workflows"` em `_COPY_DIRS`, `_CLAUDE_DIRS`, `_OPENCODE_DIRS`; adicionar projeção para `.codex/workflows/` e `.agents/workflows/`
- `dadaia_workspace/features/public/doctor.py` — adicionar status `partial` ao classificador de runtime (além dos existentes `ok | missing | drift | unsupported`)
- `dadaia_workspace/public/agents/*.md` (todos os 6) — adicionar bloco `input_contract` no frontmatter conforme `specs/features/agents/SPEC.md` FR-018..023
- `pyproject.toml` — adicionar `pyyaml = "^6.0"` em `[tool.poetry.dependencies]`
- `specs/constitution.md` — atualizar lista de stack para incluir `pyyaml` (rodada de governança subsequente)

**Criar (testes):**
- `tests/unit/test_workflow_schema.py` — parse + validação + erros (sem name, sem stages, ciclo, agent inexistente, parallel_group inválido)
- `tests/unit/test_run_state_store.py` — lifecycle de run, atomicidade, idempotência de resume, events.jsonl append-only
- `tests/unit/test_orchestration_service.py` — gates, resume, parallel_group via fake dispatcher
- `tests/unit/test_orchestration_runtime.py` — testes paramétricos por runtime (claude full / opencode partial / codex unsupported)
- `tests/integration/test_cli_orchestrate.py` — happy path + erros principais
- `tests/e2e/features/test_orchestration_pipeline.py` — `stage → install → list → run → status → resume → status` em modo `--runtime cli`
- `tests/fakes.py` — adicionar `FakeWorkflowStore`, `FakeRunStateStore`, `FakeAgentDispatcher`

### Fase 10 — Release Pipeline v0.1.0 (release-pipeline)

> Endereça `specs/features/release-pipeline/SPEC.md`. Inclui pré-requisitos de fechamento de gaps QA antes da tag.

**Pré-release (fechar gaps QA antes da tag v0.1.0):**

- Corrigir as 3 falhas pré-existentes do CI (FR-REL-028): `test_academy_modules` (Typer API), `test_stage_creates_all_expected_skills` e `test_install_all_populates_universal_skills` (`EXPECTED_SKILLS` desatualizado — adicionar `dadaia-workspace-manager`).
- Criar unit tests para `features/export/service.py`, `features/import_/service.py`, `features/repos/service.py`.
- Criar integration tests para CLI `dadaia context` (create/activate/deactivate/promote/show/list/delete), `dadaia export`, `dadaia import`, `dadaia doctor`.
- Criar testes para hooks `ctx-inject.sh` e `sdd-spec-gate.sh` via subprocess.
- Adicionar gate `--cov-fail-under=80` em `pyproject.toml`.

**Criar (root files do repositório):**
- `.github/workflows/ci.yml` — 3 jobs (lint, typecheck, test) + 1 condicional (pr-title); Python 3.12; ubuntu-latest; cache poetry
- `.github/workflows/release.yml` — 4 jobs (validate → build → publish → smoke-test); OIDC trusted publishing
- `.github/CODEOWNERS` — global fallback owner + explicit ownership de `.github/`, `pyproject.toml`, `Makefile`, `scripts/`
- `CHANGELOG.md` — Keep a Changelog 1.1.0; seção `[Unreleased]` no topo + `[0.1.0]` inicial
- `RELEASING.md` — passo a passo: bump pyproject → CHANGELOG → commit → tag → push → monitor → smoke verify

**Modificar (configurações operacionais — operador executa, não código):**
- Criar conta PyPI (operador)
- Configurar pending publisher no PyPI para `dadaia-workspace` (workflow `release.yml`, environment `pypi`)
- Criar environment `pypi` no GitHub Actions com deployment branches `v*.*.*`
- Configurar branch protection em `main` (require PR, required status checks `lint`/`typecheck`/`test`, no force push, include administrators)
- Adicionar `poetry.lock` ao git (se ainda não estiver)

**Não cria:** `.pre-commit-config.yaml`, Trivy/SAST, Codecov, Renovate, semantic-release, multi-OS matrix, multi-Python matrix. Justificativas em `release-pipeline/SPEC.md` "Fora de Escopo (v0.1)".

---

## Verificação Manual (E2E)

```bash
dadaia init --workspace /tmp/test-ws
ls /tmp/test-ws/.dadaia/states/           # spec_contexts.json, academy.json
dadaia context create proj --repo dadaia-workspace
dadaia context activate proj              # clona + auto-promote
dadaia context show --json                # is_primary: true
dadaia context deactivate proj            # rejeita (é primário)
dadaia academy modules
dadaia academy create c1 --module 4
dadaia academy list
dadaia academy delete c1
dadaia public stage
dadaia public install --target all
dadaia public doctor
ls /tmp/test-ws/.agents/skills/
ls /tmp/test-ws/.claude/agents/           # Claude Code agent files
ls /tmp/test-ws/.codex/
ls /tmp/test-ws/.opencode/
dadaia doctor
dadaia doctor --fix
```
