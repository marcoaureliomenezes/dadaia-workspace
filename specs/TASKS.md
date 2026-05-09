# TASKS: dadaia-workspace — Backlog Completo

> **Status:** Aprovado
> **Referência:** `specs/PLAN.md`

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

- [ ] T01 — Deletar `dadaia_workspace/infrastructure/database.py`
- [ ] T02 — Deletar `dadaia_workspace/infrastructure/sqlite_repositories.py`
- [ ] T03 — Deletar `dadaia_workspace/core/protocols/repositories.py`
- [ ] T04 — Deletar `dadaia_workspace/infrastructure/json_active_context_store.py`
- [ ] T05 — Atualizar `dadaia_workspace/core/models/spec_context.py`: renomear `primary_repo_slug` → `repo_slug`; adicionar `is_primary: bool`, `repo_url: str`, `created_at: str`, `activated_at: str | None`
- [ ] T06 — Atualizar `dadaia_workspace/core/models/workspace.py`: remover `contexts_dir` e `data_dir`
- [ ] T07 — Renomear `active_context_store.py` → `context_store.py`; expandir interface: `save(ctx)`, `update(ctx)`, `get(name)`, `list_all()`, `delete(name)`
- [ ] T08 — Criar `dadaia_workspace/core/protocols/primary_context_store.py`: `write(name, repo_slug, specs_dir)`, `read()`, `clear()`
- [ ] T09 — Criar `dadaia_workspace/core/protocols/git_client.py`: `clone(url, dest)`, `is_dirty(path)`, `commit_all(path, msg)`, `has_remote(path)`, `push(path)`
- [ ] T10 — Atualizar `dadaia_workspace/core/exceptions.py`: adicionar `GitSyncError`, `GitCloneError`
- [ ] T11 — Criar `dadaia_workspace/infrastructure/json_context_store.py`: CRUD atômico sobre `spec_contexts.json` (version + contexts array)
- [ ] T12 — Criar `dadaia_workspace/infrastructure/json_primary_context_store.py`: read/write/clear de `primary_context.json`
- [ ] T13 — Criar `dadaia_workspace/infrastructure/git_subprocess.py`: `GitSubprocessClient` implementando `GitClient`
- [ ] T14 — Reescrever `dadaia_workspace/container.py`: remover SQLite; montar com `JsonContextStore`, `JsonPrimaryContextStore`, `GitSubprocessClient`

---

## Fase 1 — WorkspaceService

- [ ] T15 — Atualizar `features/workspace/service.py`: remover `"data"` de `_DADAIA_DURABLE_DIRS`; adicionar `"reports/architect-agent-review"`, `"reports/specs-sdd-review"`, `"reports/bugs/soft-engineer-report"`
- [ ] T16 — Atualizar `features/workspace/service.py`: `init()` cria `spec_contexts.json` vazio `{"version":"1","contexts":[]}` e `academy.json` vazio `{"version":"1","courses":[]}`; remove `bootstrap_schema()` e `workspace_repo.save()`
- [ ] T17 — Atualizar `features/workspace/service.py`: `is_initialized()` checa `states/spec_contexts.json`
- [ ] T18 — Atualizar `tests/fakes.py`: substituir `FakeWorkspaceRepository`, `FakeSpecContextRepository`, `FakeActiveContextStore` por `FakeContextStore`, `FakePrimaryContextStore`, `FakeGitClient`; adicionar `FakeCourseStore`
- [ ] T19 — Criar `tests/unit/test_workspace_service.py`

---

## Fase 2 — SpecContextService (lifecycle completo)

- [ ] T20 — Reescrever `features/spec_context/service.py`: `create(name, repo_slug, repo_url)` sem checar disco; `is_primary=False`, `created_at=now()`
- [ ] T21 — Implementar `activate(name)` em service: clona via `GitClient` se `repos/<slug>/` ausente; auto-promove se sem primário; `activated_at=now()`
- [ ] T22 — Implementar `deactivate(name)` em service: rejeita se `is_primary`; `git_client.is_dirty()` + `commit_all()` + `push()`; remove repo; marca `inativo`; `activated_at=None`
- [ ] T23 — Implementar `promote(name)` em service: remove `is_primary` do anterior; escreve `primary_context.json` via `PrimaryContextStore`
- [ ] T24 — Criar `features/spec_context/doctor.py`: `DoctorService` com `check()` (6 invariantes) e `fix()` (5 ações de reparo)
- [ ] T25 — Criar `cli/commands/doctor.py`: `dadaia doctor [--fix]`
- [ ] T26 — Criar `tests/unit/test_spec_context_service.py`

---

## Fase 3 — CLI alignment

- [ ] T27 — Atualizar `cli/commands/context.py`: `create` chama `repos_service.get_repo_url(slug)` antes de `context_service.create()`
- [ ] T28 — Atualizar `cli/commands/context.py`: `deactivate` recebe `<name>` como argumento obrigatório
- [ ] T29 — Atualizar `cli/commands/context.py`: adicionar subcomando `promote <name>`
- [ ] T30 — Atualizar `cli/commands/context.py`: `show --json` inclui `is_primary`; `_ctx_to_dict()` usa `repo_slug`
- [ ] T31 — Atualizar `cli/commands/context.py`: `list` exibe coluna `is_primary`
- [ ] T32 — Atualizar `cli/commands/init.py`: remover referências a SQLite; output alinhado ao FR-001
- [ ] T33 — Atualizar `cli/main.py`: registrar `doctor` e `academy` command groups

---

## Fase 4 — Academy

- [ ] T34 — Criar `dadaia_workspace/core/models/course.py`: `Course` frozen dataclass (slug, name, module_number, module_name, created_at, course_dir)
- [ ] T35 — Criar `dadaia_workspace/core/protocols/course_store.py`: `CourseStore` Protocol
- [ ] T36 — Criar `dadaia_workspace/infrastructure/json_course_store.py`: CRUD atômico sobre `academy.json`
- [ ] T37 — Criar `dadaia_workspace/features/academy/service.py`: `AcademyService` com `list()`, `create()`, `delete()`, `update()`, `list_modules()`
- [ ] T38 — Criar `dadaia_workspace/cli/commands/academy.py`: 5 subcomandos Typer
- [ ] T39 — Atualizar `container.py`: montar `AcademyService`
- [ ] T40 — Criar `tests/unit/test_academy_service.py`
- [ ] T41 — Criar `tests/e2e/features/test_academy.py`

---

## Fase 5 — Public assets

- [ ] T42 — Atualizar `infrastructure/public_assets.py`: adicionar `agents/` ao loop de instalação (destino `.claude/agents/`)
- [ ] T43 — Criar `dadaia_workspace/public/agents/architect-agent.md`
- [ ] T44 — Criar `dadaia_workspace/public/agents/product-auditor-agent.md`
- [ ] T45 — Criar `dadaia_workspace/public/agents/product-engineer-agent.md`
- [ ] T46 — Criar `dadaia_workspace/public/agents/soft-engineer-agent.md`
- [ ] T47 — Criar `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`
- [ ] T48 — Criar `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`
- [ ] T49 — Criar `dadaia_workspace/public/skills/dadaia-workspace-doctor/SKILL.md`
- [ ] T50 — Criar `dadaia_workspace/public/commands/dadaia-workspace-doctor.md`

---

## Fase 6 — Quality gate

- [ ] T51 — `ruff format dadaia_workspace/ tests/` — sem erros
- [ ] T52 — `ruff check dadaia_workspace/ tests/` — sem erros
- [ ] T53 — `mypy --strict dadaia_workspace/` — sem erros
- [ ] T54 — `pytest tests/unit/ -v` — todos passam
- [ ] T55 — `pytest tests/integration/ -v` — todos passam
- [ ] T56 — `pytest tests/e2e/ -v` — todos passam
- [ ] T57 — Teste manual E2E: `dadaia init`, context lifecycle, academy CRUD, `dadaia public install` instala agents/
