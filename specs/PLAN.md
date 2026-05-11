# PLAN: dadaia-workspace — Backlog Completo

> **Status:** Aprovado
> **Referências:** `specs/SPEC.md`, `specs/foundation/SPEC.md`, todos os `specs/features/*/SPEC.md`

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
