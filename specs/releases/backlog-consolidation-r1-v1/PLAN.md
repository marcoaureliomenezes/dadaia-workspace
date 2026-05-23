# PLAN — backlog-consolidation-r1-v1

**Status:** Aprovado

## Estratégia

Sete fases sequenciais agrupadas por owner e dependência. Housekeeping e assets canônicos vêm primeiro (sem deps de código). Fixes de infraestrutura seguem. A camada de observabilidade de bugs (FR1-FR2) fecha o ciclo porque depende do formato JSON estabilizado pelo doctor (FR3).

```
Phase A (housekeeping + assets)  → sem deps de código, pode ser dispatched imediatamente
Phase B (deactivate fixes)       → independente do resto, pode correr em paralelo com A
Phase C (doctor git-dirty)       → independente, pode correr em paralelo com B
Phase D (bug reporting P1)       → depende de FR3 (formato [warn] estabilizado)
Phase E (bug reporting P2)       → depende de FR1 (reported.json format definido)
Phase F (testes + validação)     → fecha o ciclo; qa-engineer valida todos os FRs
Phase G (propagação)             → stage + install + doctor; fecha IMPLEMENTATION
```

## Fases e responsáveis

| Phase | FRs | Agente | Domínio |
|-------|-----|--------|---------|
| A — Housekeeping + assets canônicos | FR4, FR6, FR7 | `ai-engineer` + `product-engineer` | rules, agents, backlog |
| B — context-deactivate fixes | FR5 (bugs 1-4) | `software-engineer-python` | infrastructure/git, features/spec_context |
| C — Doctor git-dirty | FR3 | `software-engineer-python` | infrastructure/public_assets |
| D — Bug reporting Phase 1 | FR1 | `software-engineer-python` | cli/main + infrastructure/public_assets |
| E — Bug reporting Phase 2 | FR2 | `software-engineer-python` | cli/commands/specs |
| F — Test suite | FR1-FR6 | `software-engineer-python` | tests/unit + tests/integration |
| G — Propagação | — | `software-engineer-python` | dadaia public stage + install |

## Detalhamento por fase

### Phase A — Housekeeping + assets canônicos

**T-BCR-01 (product-engineer):** Remover `codex-runtime-stage-gap-v1` de `specs/backlog/candidates.md`. Zero risco — apenas edição de markdown.

**T-BCR-02 (ai-engineer):** Estender `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md` com seção `## 6. DEV Workspace Self-Reference` contendo os 4 pontos:
1. Este workspace é instância do produto em desenvolvimento (self-referential DEV).
2. Install editable — `Path(__file__)` aponta para working tree de `repos/dadaia-workspace/`; mudanças em `public/` são imediatas.
3. `dadaia public doctor` é cego a `git_HEAD ↔ working_tree`; diagnóstico correto: `git diff HEAD -- dadaia_workspace/public/`.
4. Nunca inserir context-specific details de projeto consumidor em assets de `public/`.

Após edição: rodar `dadaia public stage && dadaia public install --target claude --force`.

**T-BCR-03 (ai-engineer):** Criar `dadaia_workspace/public/agents/data-architect.md` com description genérica. Campos obrigatórios:
- `name: data-architect`
- `description`: sem referência a dd-chain-explorer — ex.: `"Data platform architect. Designs Medallion models, ADRs, ingestion strategies, FinOps analyses. NEVER writes production code. Escalates impl to data-engineer/backend-engineer/devops-engineer."`
- `tier: 3`, `model: claude-sonnet-4-6`
- `tools: [Read, Glob, Grep, Write, mcp__awslabs.aws-documentation-mcp-server__*]`
- `skills: [dadaia-handoff-emitter, dadaia-task-manager, dadaia-workspace-spec-navigator]`
- `write_allowlist`: paths genéricos de ADR e specs (sem hardcode de projeto)

Após criação: rodar `dadaia public stage && dadaia public install --target all`.

### Phase B — context-deactivate fixes

**T-BCR-04 (software-engineer-python):** Quatro bug fixes em `dadaia_workspace/infrastructure/git_subprocess.py` e `dadaia_workspace/features/spec_context/service.py`:

- **Bug 1** — `commit_all` usa `git add -A` que engole embedded git repos (`.claude/worktrees/agent-*`). Fix: substituir por `git add --all` com `--ignore-errors` ou pré-filtrar paths excluindo embedded repos. Alternativa: injetar `.gitignore` template no create com entrada para `.claude/`.
- **Bug 2** — `GitSyncError` levanta com `result.stderr.strip()` vazio quando commit retorna não-zero em submodule no-op. Fix: incluir `result.stdout` na mensagem; tratar caso `returncode != 0 and not result.stdout.strip() and not result.stderr.strip()` como no-op silencioso.
- **Bug 3** — `shutil.rmtree(repo_path)` falha com `PermissionError` em arquivos root-owned. Fix: antes de rmtree, checar arquivos não-acessíveis com `os.access(f, os.W_OK)` recursivamente; se encontrar, levantar `GitSyncError` com mensagem: `"PermissionError em <paths>. Rode: sudo chown -R $USER <repo_path>"`.
- **Bug 4** — `push()` usa `git push` sem `-u origin <branch>` em primeira push. Fix: detectar se upstream tracking está setado via `git rev-parse --abbrev-ref @{u}`; se não, usar `git push -u origin <branch>`.

Write set: `dadaia_workspace/infrastructure/git_subprocess.py`, `dadaia_workspace/features/spec_context/service.py`.

### Phase C — Doctor git-dirty

**T-BCR-05 (software-engineer-python):** Adicionar check `git-dirty` em `FileSystemPublicAssetManager.doctor()` em `dadaia_workspace/infrastructure/public_assets.py`:

```python
# Após os checks existentes de source ↔ staging ↔ projection:
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD", "--", str(self._public_dir)],
    capture_output=True, text=True, cwd=self._public_dir.parent.parent
)
if result.returncode == 0:
    for dirty_path in result.stdout.splitlines():
        lines.append(f"[warn] git-dirty: {dirty_path}")
elif result.returncode == 128:  # não é git repo
    lines.append("[not-applicable] git-dirty check (not a git repo)")
```

Emitir `[warn]` (não `[error]`) — drift de working tree é informativo, não bloqueante.

### Phase D — Bug reporting Phase 1

**T-BCR-06 (software-engineer-python):** Implementar infra de bug reporting em dois pontos:

**D1 — CLI exception handler global** em `dadaia_workspace/cli/main.py`:
```python
@app.callback()
def _global_callback(ctx: typer.Context) -> None:
    # Registrar result_callback para capturar exceções
    pass
```
Ou via `app = typer.Typer(result_callback=_on_result)`. No handler: capturar qualquer exceção não-`typer.Exit`/`SystemExit`, serializar entry e escrever em `.dadaia/bugs/reported.json`.

**D2 — Doctor persistence** — após emitir cada `[missing]`/`[drift]`/`[fail]`/`[warn] git-dirty`, escrever entry em `.dadaia/bugs/reported.json`.

**Formato JSON de cada entry:**
```json
{
  "id": "<uuid4>",
  "reported_at": "<ISO8601>",
  "source": "cli-exception | doctor-public | doctor-workspace | doctor-specs",
  "command": "dadaia context deactivate tauan-games",
  "exception_type": "GitSyncError",
  "message": "...",
  "traceback_tail": "...",
  "git_context": "git log --oneline -3 <area>",
  "status": "open"
}
```

Operações de escrita: append atômico (ler JSON array, append, `os.replace()`).

### Phase E — Bug reporting Phase 2

**T-BCR-07 (software-engineer-python):** Integrar leitura de `.dadaia/bugs/reported.json` em `dadaia_workspace/cli/commands/specs.py` no comando de abertura/criação de release (ex.: `dadaia specs hotfix` ou no flow de `dadaia specs init`):

1. Ler `reported.json`, filtrar `status=open`.
2. Imprimir lista de bugs com ID, source, mensagem resumida.
3. Perguntar ao operador via `typer.confirm()` para cada um (ou flag `--include-bugs` para incluir todos).
4. Bugs selecionados: `status → in_release`.

Se `reported.json` não existe ou está vazio: pular silenciosamente.

### Phase F — Test suite

**T-BCR-08 (software-engineer-python):** Testes de regressão para todos os FRs desta release:
- `tests/unit/infrastructure/test_git_subprocess.py` — bugs 1-4 (mock git subprocess; testar cada caso de erro)
- `tests/unit/infrastructure/test_public_assets.py` — git-dirty check (mock `subprocess.run` retornando paths dirty)
- `tests/unit/cli/test_bug_reporter.py` — CLI handler escreve entry válida; doctor persistence; append atômico
- `tests/unit/features/agents/test_reader.py` — atualizar `test_public_agents_count_is_20` → 21; adicionar test para `data-architect` fields
- `tests/integration/test_cli_context.py` — smoke test de deactivate com upstream tracking

### Phase G — Propagação e validação final

**T-BCR-09 (software-engineer-python):**
```bash
dadaia public stage
dadaia public install --target all --force
dadaia public doctor          # → tudo [ok]; nenhum [drift]/[missing]
pytest tests/                 # → suite completa verde
```

## Arquivos previstos

```
dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md   ← T-BCR-02
dadaia_workspace/public/agents/data-architect.md                  ← T-BCR-03
specs/backlog/candidates.md                                       ← T-BCR-01
dadaia_workspace/infrastructure/git_subprocess.py                 ← T-BCR-04
dadaia_workspace/features/spec_context/service.py                 ← T-BCR-04
dadaia_workspace/infrastructure/public_assets.py                  ← T-BCR-05
dadaia_workspace/cli/main.py                                      ← T-BCR-06
dadaia_workspace/cli/commands/specs.py                            ← T-BCR-07
tests/unit/infrastructure/test_git_subprocess.py                  ← T-BCR-08
tests/unit/infrastructure/test_public_assets.py                   ← T-BCR-08
tests/unit/cli/test_bug_reporter.py                               ← T-BCR-08
tests/unit/features/agents/test_reader.py                         ← T-BCR-08
tests/integration/test_cli_context.py                             ← T-BCR-08
.dadaia/.venv/                                                    ← T-BCR-09 (runtime)
```

## Validação

```bash
# Phase B validation
pytest tests/unit/infrastructure/test_git_subprocess.py -v

# Phase C validation
pytest tests/unit/infrastructure/test_public_assets.py -k "git_dirty" -v

# Phase D+E validation
pytest tests/unit/cli/test_bug_reporter.py -v

# Phase F validation — agent count
pytest tests/unit/features/agents/test_reader.py::test_public_agents_count_is_20 -v

# Full suite
.dadaia/.venv/bin/python -m pytest tests/ -v

# Propagação
dadaia public stage && dadaia public install --target all --force && dadaia public doctor
```
