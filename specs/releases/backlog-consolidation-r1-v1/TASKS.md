# TASKS — backlog-consolidation-r1-v1

**Status:** Aprovado

---

## Phase A — Housekeeping + assets canônicos

- [x] T-BCR-01 — Remover `codex-runtime-stage-gap-v1` de `specs/backlog/candidates.md` (stale — resolvido pelo hotfix 55cfb4f).
  - Owner: `product-engineer`
  - Write set: `specs/backlog/candidates.md`
  - Aceite: entrada ausente do arquivo após edição.

- [x] T-BCR-02 — Estender `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md` com seção `## 6. DEV Workspace Self-Reference`.
  - Owner: `ai-engineer`
  - Write set:
    - `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`
  - Pós-edição: `dadaia public stage && dadaia public install --target claude --force`
  - Aceite: seção presente com os 4 pontos (self-referential, editable install, doctor blind spot, never insert consumer specifics). `dadaia public doctor` retorna `[ok]` para a rule.

- [x] T-BCR-03 — Criar `dadaia_workspace/public/agents/data-architect.md` com description genérica (21º agent universal).
  - Owner: `ai-engineer`
  - Write set:
    - `dadaia_workspace/public/agents/data-architect.md`
  - Pós-criação: `dadaia public stage && dadaia public install --target all`
  - Aceite: arquivo carregável via `read_canonical_agents()`; description sem referência a projeto específico; `dadaia public doctor` retorna `[ok]` para o agent.

---

## Phase B — context-deactivate fixes

- [x] T-BCR-04 — Corrigir 4 bugs em `dadaia context deactivate`.
  - Owner: `software-engineer-python`
  - Write set:
    - `dadaia_workspace/infrastructure/git_subprocess.py`
    - `dadaia_workspace/features/spec_context/service.py`
  - Bugs:
    - **Bug 1**: `commit_all` — `git add -A` engole embedded git repos; fix: filtrar `.claude/` ou injetar `.gitignore`.
    - **Bug 2**: `GitSyncError` com stderr vazio em submodule no-op; fix: incluir stdout; tratar caso vazio como no-op.
    - **Bug 3**: `shutil.rmtree` falha com `PermissionError` em root-owned files; fix: detectar arquivos não-acessíveis antes de rmtree, levantar `GitSyncError` com sugestão `sudo chown`.
    - **Bug 4**: `git push` sem upstream tracking; fix: usar `git push -u origin <branch>` na primeira push.
  - Aceite: cada caso de erro termina com comportamento correto ou mensagem acionável. Testes unitários cobrem os 4 casos.

---

## Phase C — Doctor git-dirty check

- [x] T-BCR-05 — Adicionar status `[warn] git-dirty: <path>` em `FileSystemPublicAssetManager.doctor()`.
  - Owner: `software-engineer-python`
  - Write set:
    - `dadaia_workspace/infrastructure/public_assets.py`
  - Aceite: `dadaia public doctor` emite `[warn] git-dirty: <rel_path>` quando `dadaia_workspace/public/` tem arquivo com diff não-commitado; emite `[not-applicable]` quando não é git repo. Teste unitário via mock de `subprocess.run`.

---

## Phase D — Bug reporting Phase 1

- [-] T-BCR-06 — Implementar infra de bug reporting: CLI exception handler + doctor persistence.
  - Owner: `software-engineer-python`
  - Write set:
    - `dadaia_workspace/cli/main.py`
    - `dadaia_workspace/infrastructure/public_assets.py`
  - Aceite:
    - CLI exception inesperada escreve entry em `.dadaia/bugs/reported.json` com campos: `id`, `reported_at`, `source`, `command`, `exception_type`, `message`, `traceback_tail`, `git_context`, `status=open`.
    - Doctor `[missing]`/`[drift]`/`[fail]`/`[warn] git-dirty` persiste entry em `reported.json`.
    - Append é atômico (write temp + `os.replace()`).
    - Testes unitários para handler e persistence.

---

## Phase E — Bug reporting Phase 2

- [ ] T-BCR-07 — Integrar leitura de `reported.json` em `dadaia specs` ao criar/abrir release.
  - Owner: `software-engineer-python`
  - Write set:
    - `dadaia_workspace/cli/commands/specs.py`
  - Aceite:
    - Ao criar release, se `reported.json` tem entries `status=open`, lista é exibida ao operador.
    - Operador seleciona via `typer.confirm()` quais incluir.
    - Selecionados recebem `status=in_release`; não-selecionados permanecem `open`.
    - Se `reported.json` ausente ou vazio: fluxo prossegue sem interrupção.

---

## Phase F — Test suite

- [ ] T-BCR-08 — Testes de regressão para todos os FRs.
  - Owner: `software-engineer-python`
  - Write set:
    - `tests/unit/infrastructure/test_git_subprocess.py`
    - `tests/unit/infrastructure/test_public_assets.py`
    - `tests/unit/cli/test_bug_reporter.py`
    - `tests/unit/features/agents/test_reader.py`
    - `tests/integration/test_cli_context.py`
  - Aceite:
    - 4 testes unitários para os bugs de deactivate (um por bug).
    - 1 teste para `[warn] git-dirty` (mock subprocess dirty output).
    - 2 testes para bug reporting: CLI handler escreve entry; doctor persiste.
    - `test_public_agents_count_is_20` renomeado/atualizado para 21 e verde.
    - 1 smoke test de deactivate com upstream tracking via integration test.
    - `pytest tests/` suite completa verde.

---

## Phase G — Propagação e validação final

- [ ] T-BCR-09 — Propagação completa + validação final.
  - Owner: `software-engineer-python`
  - Write set: nenhum arquivo de produção — apenas runtime
  - Comandos:
    ```bash
    dadaia public stage
    dadaia public install --target all --force
    dadaia public doctor
    .dadaia/.venv/bin/python -m pytest tests/ -v
    ```
  - Aceite: `dadaia public doctor` all `[ok]`; suite completa verde; nenhum `[drift]`/`[missing]`.
