# Plan: Release — infra-correctness-v1

> **Status:** Aprovado
> **Release ID:** infra-correctness-v1
> **Owner:** product-engineer
> **Created:** 2026-05-20

---

## Estratégia

Sete fases parallelizáveis onde possível. P6 (install scope flags) precede P7 (coverage
lift) porque P6 adiciona código novo em `public_assets.py` — cobrir antes de ter o
código final gera gap. Todas as outras fases são independentes entre si.

**Agentes responsáveis por fase:**

| Phase | Agente | Item SPEC | Esforço est. |
|---|---|---|---|
| P1 — Exit code fix | `software-engineer-python` | Item 1 | 0.5 h |
| P2 — I6 topology guard | `ai-engineer` | Item 2 | 1 h |
| P3 — SQLite workflows drop | `software-engineer-python` | Item 5 | 0.5 h |
| P4 — CSP script-src harden | `software-engineer-python` | Item 4 | 1.5 h |
| P5 — Init resolver fix | `software-engineer-python` | Item 7 | 1 h |
| P6 — Install scope flags | `software-engineer-python` | Item 6 | 2 h |
| P7 — Coverage lift | `software-engineer-python` | Item 3 | 3–4 h |
| P8 — CLOSURE prep | `product-engineer` | — | 0.5 h |

---

## Camadas afetadas

| Arquivo | Fase | Ação |
|---|---|---|
| `dadaia_workspace/cli/commands/reports.py` | P1 | EDIT (mover linha 138 para inside try) |
| `tests/integration/test_cli_reports.py` | P1 | EDIT (remover xfail, assert exit 3) |
| `scripts/check_agent_topology.py` | P2 | EDIT (adicionar check_i6_skill_links) |
| `dadaia_workspace/features/telemetry/store/schema.py` | P3 | EDIT (migration 6, SCHEMA_VERSION=6) |
| `tests/unit/features/telemetry/` | P3 | EDIT (test migration 6) |
| `dadaia_workspace/features/panel/handler.py` | P4 | EDIT (CSP script-src com SHA-256 hashes) |
| `dadaia_workspace/features/panel/views/index.py` | P4 | READ (extrair texto dos scripts) |
| `dadaia_workspace/features/panel/views/wrapper.py` | P4 | READ (extrair texto dos scripts) |
| `tests/unit/features/panel/` | P4 | EDIT (assert CSP sem unsafe-inline em script-src) |
| `dadaia_workspace/core/workspace_resolver.py` | P5 | EDIT (adicionar resolve_workspace_root_for_init) |
| `dadaia_workspace/cli/commands/init.py` | P5 | EDIT (usar resolve_workspace_root_for_init, remover _resolve_workspace) |
| `tests/unit/core/test_workspace_resolver.py` | P5 | EDIT (unit tests para nova função) |
| `dadaia_workspace/infrastructure/public_assets.py` | P6 | EDIT (scope param em install()) |
| `dadaia_workspace/cli/commands/public.py` | P6 | EDIT (--repos-only, --workspace-only flags) |
| `tests/integration/test_cli_public.py` | P6 | EDIT (testes de cada scope) |
| `tests/unit/infrastructure/test_public_assets.py` | P7 | NEW (12–15 funções, ≥80% coverage) |

---

## P1 — Exit code fix

**Owner:** software-engineer-python
**Gate de entrada:** nenhum
**Arquivo:** `dadaia_workspace/cli/commands/reports.py`

### Passos

1. Ler `dadaia_workspace/cli/commands/reports.py:130–160` para confirmar posição exata da linha 138.
2. Mover `workspace_root = resolve_workspace_root()` para dentro do bloco `try` que inicia em 141.
3. Em `tests/integration/test_cli_reports.py`: remover `@pytest.mark.xfail` de `test_10_workspace_not_initialized_exits_3`. Confirmar que o teste agora passa sem xfail.
4. Rodar `pytest tests/integration/test_cli_reports.py -v` — todos devem passar.

**Critério de saída:** `test_10_workspace_not_initialized_exits_3` passa sem marcação xfail.

---

## P2 — I6 topology guard

**Owner:** ai-engineer
**Gate de entrada:** nenhum (independente)
**Arquivo:** `scripts/check_agent_topology.py`

### Passos

1. Ler `scripts/check_agent_topology.py` para entender `SKILLS_DIR`, `AGENTS_DIR` e o padrão das funções `check_i*` existentes.
2. Implementar `check_i6_skill_links(agents: dict[str, dict], errors: list[str]) -> None`:
   - Para cada agente em `agents`, ler `frontmatter.get("skills", [])`.
   - Para cada nome de skill: verificar que `SKILLS_DIR / skill_name` é diretório existente.
   - Em caso de falha: `errors.append(f"I6 FAIL: {agent_name}: skill ref {skill_name!r} not found in {SKILLS_DIR}")`.
3. Conectar em `main()` após a chamada a `check_i5_no_bare_se()`.
4. Adicionar linha de summary: `print(f"  I6: {n_agents} agents, {n_skills} skill refs validated")`.
5. Rodar `python scripts/check_agent_topology.py` — deve passar I6 (todos os skills atuais existem).
6. Teste negativo: criar temporariamente um agente com skill ref inexistente e confirmar I6 FAIL.

**Critério de saída:** script reporta I6 no summary; I6 FAIL se skill ref quebrada.

---

## P3 — SQLite workflows drop

**Owner:** software-engineer-python
**Gate de entrada:** nenhum (independente)
**Arquivo:** `dadaia_workspace/features/telemetry/store/schema.py`

### Passos

1. Ler `schema.py` para confirmar `SCHEMA_VERSION = 5`, localizar migration 5, confirmar `# DEAD:` nas tabelas `workflows` e `workflow_agents`.
2. Incrementar `SCHEMA_VERSION = 6`.
3. Adicionar migração 6 ao dicionário/lista de migrations:
   ```sql
   DROP TABLE IF EXISTS workflow_agents;
   DROP TABLE IF EXISTS workflows;
   ```
   Ordem: `workflow_agents` antes de `workflows` (FK safety).
4. Localizar testes de migration existentes. Adicionar teste que:
   - Cria banco com migration 5.
   - Aplica migration 6.
   - Verifica que `SELECT name FROM sqlite_master WHERE type='table' AND name IN ('workflows','workflow_agents')` retorna vazio.
5. Rodar `pytest` nos testes de telemetry — sem regressão.

**Critério de saída:** `SCHEMA_VERSION == 6`; testes passam; tabelas ausentes após migration.

---

## P4 — CSP script-src harden

**Owner:** software-engineer-python
**Gate de entrada:** nenhum (independente)
**Arquivos:** `handler.py`, `index.py`, `wrapper.py`

### Passos

1. Ler `dadaia_workspace/features/panel/views/index.py` e `wrapper.py`: extrair o texto literal de cada bloco `<script>…</script>` inline. Identificar scripts distintos (pode haver 2 ou 3).
2. Para cada script distinto, computar:
   ```python
   import hashlib, base64
   digest = hashlib.sha256(script_content.encode()).digest()
   hash_b64 = base64.b64encode(digest).decode()
   csp_token = f"'sha256-{hash_b64}'"
   ```
3. Editar `dadaia_workspace/features/panel/handler.py:392`: substituir `'unsafe-inline'` na diretiva `script-src` pelos tokens `'sha256-<hash>'` computados. `style-src 'unsafe-inline'` permanece inalterado.
4. Adicionar constantes nomeadas `_CSP_SCRIPT_HASH_*` no topo de `handler.py` (ou inline na string CSP — preferir constantes para legibilidade de manutenção).
5. Adicionar (ou estender) teste unitário que:
   - Chama o handler com um request GET qualquer.
   - Extrai o header `Content-Security-Policy`.
   - Asserta que `script-src` não contém `'unsafe-inline'`.
   - Asserta que `script-src` contém pelo menos um token `'sha256-'`.
6. Rodar `pytest tests/unit/features/panel/ -v`.

**Critério de saída:** CSP header sem `unsafe-inline` em `script-src`; teste passa.

---

## P5 — Init resolver fix

**Owner:** software-engineer-python
**Gate de entrada:** nenhum (independente)
**Arquivos:** `workspace_resolver.py`, `init.py`

### Passos

1. Ler `dadaia_workspace/core/workspace_resolver.py` para entender `resolve_workspace_root` e o sentinel `_SENTINEL`.
2. Adicionar função `resolve_workspace_root_for_init(cwd: Path | None = None) -> Path`:
   - Tenta `resolve_workspace_root(cwd)` (sentinel walk).
   - Se `WorkspaceNotInitializedError` → retorna `cwd or Path.cwd()`.
   - Docstring: "Safe for first-time init: falls back to cwd when no sentinel found."
3. Ler `dadaia_workspace/cli/commands/init.py:1–50`: localizar `_resolve_workspace` e seu único caller em `init()`.
4. Em `init.py`: substituir chamada `_resolve_workspace(workspace)` por `resolve_workspace_root_for_init(workspace)`. Remover definição de `_resolve_workspace` (dead code).
5. Adicionar import de `resolve_workspace_root_for_init` no topo de `init.py`.
6. Adicionar testes em `tests/unit/core/test_workspace_resolver.py`:
   - Caso 1: sentinel existe no cwd pai → retorna workspace root correto.
   - Caso 2: sem sentinel em nenhum pai → retorna cwd (não lança exceção).
7. Rodar `pytest tests/unit/core/ -v`.

**Critério de saída:** `_resolve_workspace` removido; `resolve_workspace_root_for_init` em `workspace_resolver.py`; testes passam.

---

## P6 — Install scope flags

**Owner:** software-engineer-python
**Gate de entrada:** nenhum (independente; mas P7 deve rodar APÓS P6)
**Arquivos:** `public.py`, `public_assets.py`

### Passos

1. Ler `dadaia_workspace/infrastructure/public_assets.py`: localizar `install()` e os pontos onde `_install_workspace_guardrail_pair` e o loop de repos são chamados.
2. Adicionar `from typing import Literal` se ausente. Adicionar `scope: Literal["all", "repos-only", "workspace-only"] = "all"` como parâmetro de `FileSystemPublicAssetManager.install()`.
3. Propagar scope:
   - `if scope in ("all", "workspace-only"):` → chamar `_install_workspace_guardrail_pair(...)`.
   - `if scope in ("all", "repos-only"):` → executar loop de repos.
4. Ler `dadaia_workspace/cli/commands/public.py`: localizar comando `install`.
5. Adicionar opções mutuamente exclusivas:
   ```python
   repos_only: bool = typer.Option(False, "--repos-only", help="Install only consumer repo assets.")
   workspace_only: bool = typer.Option(False, "--workspace-only", help="Install only workspace-root guardrail pair.")
   ```
6. Validar exclusividade: se ambos → `typer.echo("Error: --repos-only and --workspace-only are mutually exclusive"); raise typer.Exit(1)`.
7. Derivar `scope`: `"repos-only"` se `repos_only`, `"workspace-only"` se `workspace_only`, `"all"` otherwise. Passar para `manager.install(scope=scope, ...)`.
8. Adicionar testes de integração (ou unit com mock do manager) para cada scope: all, repos-only, workspace-only, e erro de exclusividade.
9. Rodar `pytest tests/integration/` relacionados a `public`.

**Critério de saída:** `dadaia public install --repos-only` e `--workspace-only` funcionam; erro claro para os dois juntos.

---

## P7 — Coverage lift

**Owner:** software-engineer-python
**Gate de entrada:** P6 concluído (novo código de P6 incluído na medição)
**Arquivos:** `tests/unit/infrastructure/test_public_assets.py` (novo)

### Passos

1. **Passo 0 — medir:** Rodar `pytest --cov=dadaia_workspace/infrastructure/public_assets --cov-report=term-missing tests/`. Capturar linhas não cobertas. Identificar os 4–5 clusters maiores.
2. Criar `tests/unit/infrastructure/__init__.py` se não existir.
3. Criar `tests/unit/infrastructure/test_public_assets.py`. Estrutura mínima:
   ```python
   # tests/unit/infrastructure/test_public_assets.py
   import pytest
   from unittest.mock import patch, MagicMock
   from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
   ```
4. Escrever 12–15 funções de teste cobrindo:
   - `doctor()` happy path (todos os checks passam).
   - `doctor()` drift detectado em D-CX-1..5 (verificar que doctor reporta `[drift]`).
   - `_install_workspace_guardrail_pair` happy path.
   - `_doctor_guardrail_pair` happy path.
   - `_runtime_expectations` para cada runtime suportado.
   - `_install_codex_agents` com mock de filesystem.
   - `_install_opencode` com mock de filesystem.
5. Rodar `pytest --cov=dadaia_workspace/infrastructure/public_assets --cov-report=term-missing` → verificar ≥ 80%.
6. Se abaixo de 80%, adicionar testes nos clusters ainda descobertos até atingir a meta.

**Critério de saída:** `pytest --cov` reporta ≥ 80% no módulo; arquivo de teste existe.

---

## P8 — CLOSURE prep

**Owner:** product-engineer
**Gate de entrada:** P1–P7 todos com `[x]` em TASKS.md

### Passos

1. Rodar `pytest` completo — zero falhas, zero xfail ativos relacionados a esta release.
2. Rodar `python scripts/check_agent_topology.py` — I1–I6 todos passam.
3. Rodar `dadaia public doctor` — sem drift.
4. Verificar `ACTIVE.md` phase → flippada para CLOSURE na etapa de TASKS.
5. Autor CLOSURE.md com evidências dos 7 critérios de aceite.
6. Arquivar release: `git mv specs/releases/infra-correctness-v1/ specs/_archive/releases/infra-correctness-v1/`.
7. Reset `ACTIVE.md` → `release: none` / `phase: none`.

**Critério de saída:** CLOSURE.md emitido; release arquivada; ACTIVE.md zerado.

---

## Ordem de execução recomendada

```
P1, P2, P3, P4, P5, P6   ← parallelizáveis entre si (sem dependências)
P7                         ← após P6 (aguarda código novo de install scope)
P8                         ← após P7 (todos os [x])
```

P1–P6 podem ser despachados em paralelo para agentes distintos ou executados
sequencialmente pelo mesmo agente — a escolha é do operador.
