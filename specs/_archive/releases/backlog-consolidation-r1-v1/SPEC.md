# SPEC — backlog-consolidation-r1-v1

**Status:** Aprovado

## Contexto

O workspace não tinha mecanismo formal de detecção e reporte de bugs. Bugs eram inseridos manualmente em `backlog/candidates.md` sem reprodutor, sem root-cause e sem staleness check. O `dadaia public doctor` era cego a drift `git_HEAD ↔ working_tree` em `public/` (editable install faz `Path(__file__)` apontar para working tree — mudanças não-commitadas afetam o workspace imediatamente mas o doctor dizia `[ok]`). Confirmado ao vivo: `data-analyst.md` e `data-engineer.md` foram modificados com specifics de `dd-chain-explorer` e o workspace rodou esses agentes corrompidos sem que o doctor detectasse.

Adicionalmente, 4 bugs confirmados em `dadaia context deactivate` estão ativos no código (`git_subprocess.py`, `service.py`) desde 2026-05-22 e o `data-architect` agent existe como arquivo não-commitado com description incorreta (dd-chain-explorer-specific em vez de genérica).

## Escopo

### FR1 — Bug reporting Phase 1: detecção automática

- CLI exception handler global (`typer` callback ou `app.callback()`) captura exceções inesperadas e escreve em `.dadaia/bugs/reported.json` com: timestamp, comando invocado, tipo de exceção, mensagem, traceback resumido, e git-log das áreas tocadas (lightweight root-cause).
- `dadaia public doctor`, `dadaia doctor`, `dadaia specs doctor` persistem cada finding `[missing]` / `[drift]` / `[fail]` no mesmo `.dadaia/bugs/reported.json`, além de imprimir no stdout.
- Formato JSON de entrada por bug: `{id, reported_at, source, command, exception_type, message, traceback_tail, git_context, status}` onde `status ∈ {open, stale, resolved}`.

### FR2 — Bug reporting Phase 2: resolução no planning

- `dadaia specs` (na criação ou abertura de release) lê `.dadaia/bugs/reported.json` e apresenta bugs com `status=open` ao operador.
- Operador decide quais incluir — os incluídos recebem `status=in_release` e são listados no SPEC da nova release como FR candidatos.
- Bugs não incluídos permanecem `status=open` para a próxima rodada.

### FR3 — Doctor git-dirty check

- `dadaia public doctor` adiciona novo status `[warn] git-dirty: <rel_path>` para cada arquivo em `dadaia_workspace/public/` que tem diff entre `git HEAD` e working tree.
- O check usa `git diff --name-only HEAD -- dadaia_workspace/public/` via subprocess.
- Se o repo não tiver git (workspace portável sem git), o check é `[not-applicable]`.

### FR4 — DEV Workspace Self-Reference — extensão da regra always-active

- Estender `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md` com seção `## 6. DEV Workspace Self-Reference` declarando:
  1. Este workspace é uma instância do próprio produto em desenvolvimento.
  2. O install é editable (`pip install -e`) — `Path(__file__)` aponta para working tree de `repos/dadaia-workspace/`. Mudanças em `public/` são imediatas, mesmo sem commit.
  3. `dadaia public doctor` é cego a `git_HEAD ↔ working_tree` — sempre rodar `git diff HEAD -- dadaia_workspace/public/` para diagnosticar drift real.
  4. Nunca editar agents/rules/skills em `public/` com context-specific details de um projeto consumidor. A lib é genérica (Pilar 1).

### FR5 — context-deactivate-hardening: 4 bug fixes

- **Bug 1** (`git_subprocess.py:30`): substituir `git add -A` por `git add --all -- .` com filtro explícito de `.claude/worktrees/` e de embedded git repos (via `git ls-files --error-unmatch` ou `.gitignore` template).
- **Bug 2** (`git_subprocess.py:32`): incluir `result.stdout` no erro de GitSyncError; tratar retorno não-zero com stdout vazio como no-op de submodule (não levantar exceção).
- **Bug 3** (`service.py:184`): antes de `shutil.rmtree`, verificar se existem arquivos não-deletáveis (root-owned via `os.access`); se sim, levantar `GitSyncError` com mensagem clara sugerindo `sudo chown -R $USER <path>`.
- **Bug 4** (`git_subprocess.py:40`): no `push()`, usar `git push -u origin <branch>` na primeira push (quando upstream tracking não está setado), detectando via `git rev-parse --abbrev-ref @{u}`.

### FR6 — data-architect como 21º agent universal

- Criar `dadaia_workspace/public/agents/data-architect.md` com:
  - `description`: genérica (sem referência a dd-chain-explorer).
  - `tier: 3`, `model: claude-sonnet-4-6`.
  - Skills: `dadaia-handoff-emitter`, `dadaia-task-manager`, `dadaia-workspace-spec-navigator`.
  - Ferramentas: `Read`, `Glob`, `Grep`, `Write` + MCP `awslabs.aws-documentation-mcp-server`.
  - `write_allowlist`: paths genéricos de repos ADR/specs (não hardcoded por projeto).
- Atualizar `tests/unit/features/agents/test_reader.py` para esperar 21 agents.

### FR7 — Backlog staleness cleanup

- Remover `codex-runtime-stage-gap-v1` de `specs/backlog/candidates.md` (stale — resolvido pelo hotfix `55cfb4f`).

## Fora de escopo

- Fixes de bugs em `dd-chain-explorer` ou outros projetos consumidores.
- Waves de migração do handoff-emitter (agent-comms-wave-2..7) — Tier B.
- Items arquitetônicos da lista Tier B: `release-pipeline`, `security`, `multi-bot-context-isolation`, workflows deferidos (Q3/Q4).
- Alterar `specs/memory/*.html` diretamente (gate-locked até CLOSURE).
- Mudanças na constitution ou em specs arquivadas.

## Critérios de aceite

- `dadaia context deactivate` com repo sujo, com submodule embedded, com root-owned files e sem upstream tracking: cada caso termina sem exceção inesperada ou com mensagem acionável.
- `dadaia public doctor` emite `[warn] git-dirty: <path>` quando `public/` tem diff não-commitado; emite `[ok]` quando não há.
- CLI failing command escreve entrada em `.dadaia/bugs/reported.json` com campos obrigatórios.
- `dadaia public doctor` com `[missing]`/`[drift]` persiste os findings em `.dadaia/bugs/reported.json`.
- `data-architect` agent carregável via `read_canonical_agents()`; description não contém nenhuma referência a projeto específico.
- Teste `test_public_agents_count_is_20` atualizado para 21 e verde.
- `dadaia-workspace-dev-guardrail.md` projetado via `dadaia public install --target claude` contém seção `## 6. DEV Workspace Self-Reference`.
- `codex-runtime-stage-gap-v1` ausente de `backlog/candidates.md`.
- `pytest` suite completa verde.
