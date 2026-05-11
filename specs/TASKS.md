# TASKS: dadaia-workspace — Backlog Completo

> **Status:** Aprovado
> **Referência:** `specs/PLAN.md`

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

- [ ] T51 — `ruff format dadaia_workspace/ tests/` — sem erros
- [ ] T52 — `ruff check dadaia_workspace/ tests/` — sem erros
- [ ] T53 — `mypy --strict dadaia_workspace/` — sem erros
- [ ] T54 — `pytest tests/unit/ -v` — todos passam
- [ ] T55 — `pytest tests/integration/ -v` — todos passam
- [ ] T56 — `pytest tests/e2e/ -v` — todos passam
- [ ] T57 — Teste manual E2E: `dadaia init`, context lifecycle, academy CRUD, `dadaia public install` instala agents/

---

## Fase 7 — Governança SDD (backlog crítico)

> Fase criada em 2026-05-11 após auditoria grill-me revelar duas falhas de governança graves.

### 7A — Correção do sdd-spec-gate (CRÍTICO)

**Problema identificado:** `sdd-spec-gate.sh` só protege paths VPS (`services/`, `docker/`, `scripts/`). Qualquer escrita em `repos/<slug>/` não é interceptada — o SDD nunca disparou durante o desenvolvimento da dadaia-workspace. Além disso, o gate verifica apenas "existe algum SPEC.md aprovado?" em vez de "existe uma task aberta que cobre este arquivo?", tornando a verificação trivialmente satisfatória.

- [ ] T58 — Escrever `specs/features/sdd-enforcement/SPEC.md`: especificar escopo correto do gate (protege `repos/<slug>/` quando slug tem context ativo), granularidade mínima aceitável, e política de fail-open vs fail-closed por tipo de path
- [ ] T59 — Escrever `specs/features/sdd-enforcement/PLAN.md` e `TASKS.md`
- [ ] T60 — Implementar: expandir `case` do `sdd-spec-gate.sh` para incluir `"$WS/repos/"*` com resolução de `specs_dir` via context ativo
- [ ] T61 — Implementar: adicionar verificação de TASKS.md — bloquear Write/Edit se nenhuma task OPEN ou IN PROGRESS cobre o arquivo-alvo (ou se o arquivo está fora do escopo de qualquer task aprovada)
- [ ] T62 — Distribuir script atualizado via `dadaia public install` para que todos os tools (Claude Code, Codex, OpenCode) usem o gate correto
- [ ] T63 — Adicionar teste E2E: verificar que Write em `repos/<slug>/` sem context ativo é bloqueado; verificar que Write com context ativo e spec aprovada passa

### 7B — Task state tracking: OPEN → IN PROGRESS → DONE

**Problema identificado:** O TASKS.md atual só tem dois estados (`[ ]` e `[x]`). Quando um agente inicia uma task, não há sinal de que ela está em andamento — outro agente (ou instância paralela) pode pegar a mesma task, causando conflito. Não há rastreabilidade de "quem pegou o quê".

- [ ] T64 — Escrever `specs/features/task-state-tracking/SPEC.md`: definir os 3 estados (`[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE), semântica de cada transição, regras de precedência (nunca 2 `[-]` simultâneos), e como o gate usa o estado para decidir
- [ ] T65 — Escrever `specs/features/task-state-tracking/PLAN.md` e `TASKS.md`
- [ ] T66 — Criar skill `dadaia-task-manager/SKILL.md` em `dadaia_workspace/public/skills/`: protocolo para agentes lerem, atualizarem e commitarem mudanças de estado em TASKS.md antes de iniciar work
- [ ] T67 — Integrar com sdd-spec-gate: Write/Edit só permitido se houver uma task com estado `[-]` (IN PROGRESS) que cubra o arquivo-alvo
- [ ] T68 — Distribuir skill via `dadaia public install --target all`
- [ ] T69 — Atualizar `foundation/SPEC.md` e `specs/SPEC.md` para refletir a nova política de estados de task como contrato normativo
