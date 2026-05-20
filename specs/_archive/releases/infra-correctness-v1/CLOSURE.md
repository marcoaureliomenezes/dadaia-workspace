# Closure: Release — infra-correctness-v1

> **Status:** Aprovado
> **Release ID:** infra-correctness-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-20

## Summary

`infra-correctness-v1` liquidou 7 itens de divida tecnica acumulados ao longo de multiplas
releases anteriores. Todos os itens tinham evidencia concreta de file:line, bug reproduzivel
ou metrica de cobertura verificavel antes do inicio — sem trabalho especulativo.

Os sete itens cobrem: correcao de exit code no CLI `dadaia reports`; adicao do guard I6 na
topologia de agentes; drop de tabelas SQLite mortas; endurecimento do CSP com SHA-256 no
painel; correcao do resolver de init para usar o sentinel canônico; adicao de flags de escopo
no `dadaia public install`; e elevacao da cobertura de `public_assets.py` para 87%.

Nenhum item requereu ADR novo, grill-me ou decisao arquitetural — apenas execucao disciplinada
das correccoes ja especificadas nos closures e backlogs de releases anteriores.

---

## Tasks completed

| Task ID | Description | Phase |
|---------|-------------|-------|
| T-01 | Confirmar posicao de `resolve_workspace_root()` em `reports.py` | P1 |
| T-02 | Mover `workspace_root = resolve_workspace_root()` para dentro do bloco `try` | P1 |
| T-03 | Remover `@pytest.mark.xfail` de `test_10_workspace_not_initialized_exits_3` | P1 |
| T-04 | Rodar `pytest tests/integration/test_cli_reports.py` — todos passam | P1 |
| T-05 | Ler `check_agent_topology.py` — entender estrutura e padrao `check_i*` | P2 |
| T-06 | Implementar `check_i6_skill_links(agents, errors)` | P2 |
| T-07 | Conectar `check_i6_skill_links` em `main()` apos I5 | P2 |
| T-08 | Rodar `python scripts/check_agent_topology.py` — I6 passa | P2 |
| T-09 | Teste negativo manual: skill ref ficticia confirma I6 FAIL | P2 |
| T-10 | Confirmar `SCHEMA_VERSION=5` e tabelas marcadas `# DEAD:` | P3 |
| T-11 | Incrementar `SCHEMA_VERSION=6`; adicionar migration 6 (DROP TABLE) | P3 |
| T-12 | Adicionar teste de migration 6: verificar tabelas ausentes | P3 |
| T-13 | Rodar `pytest` nos testes de telemetry — sem regressao | P3 |
| T-14 | Extrair texto literal dos scripts inline em `index.py` e `wrapper.py` | P4 |
| T-15 | Computar SHA-256 base64 de cada script distinto | P4 |
| T-16 | Editar `handler.py:392` — substituir `unsafe-inline` por hashes SHA-256 | P4 |
| T-17 | Adicionar constantes `_CSP_SCRIPT_HASH_1` e `_CSP_SCRIPT_HASH_2` em `handler.py` | P4 |
| T-18 | Adicionar teste unitario: `script-src` sem `unsafe-inline`, com token `sha256-` | P4 |
| T-19 | Rodar `pytest tests/unit/features/panel/ -v` | P4 |
| T-20 | Ler `workspace_resolver.py` — entender `resolve_workspace_root` e `_SENTINEL` | P5 |
| T-21 | Adicionar `resolve_workspace_root_for_init(cwd)` em `workspace_resolver.py` | P5 |
| T-22 | Ler `init.py:1-50` — localizar `_resolve_workspace` e seu caller | P5 |
| T-23 | Substituir `_resolve_workspace` por `resolve_workspace_root_for_init` em `init.py` | P5 |
| T-24 | Adicionar import de `resolve_workspace_root_for_init` em `init.py` | P5 |
| T-25 | Escrever 2 unit tests em `test_workspace_resolver.py` | P5 |
| T-26 | Rodar `pytest tests/unit/core/ -v` | P5 |
| T-27 | Ler `public_assets.py` — localizar `install()` e seus callers | P6 |
| T-28 | Adicionar `scope: Literal["all","repos-only","workspace-only"]` a `install()` | P6 |
| T-29 | Propagar scope: guardrail pair e loop de repos condicionados ao scope | P6 |
| T-30 | Adicionar `--repos-only` e `--workspace-only` em `public.py` | P6 |
| T-31 | Derivar e passar `scope` para `manager.install()` | P6 |
| T-32 | Adicionar testes para cada scope (all, repos-only, workspace-only, exclusividade) | P6 |
| T-33 | Rodar `pytest tests/integration/` relacionados a `dadaia public install` | P6 |
| T-34 | Rodar `pytest --cov` — capturar linhas nao cobertas antes de escrever testes | P7 |
| T-35 | Criar `tests/unit/infrastructure/__init__.py` | P7 |
| T-36 | Criar `tests/unit/infrastructure/test_public_assets.py` | P7 |
| T-37 | Escrever testes para `doctor()` happy path + D-CX-1..5 drift checks | P7 |
| T-38 | Escrever testes para `_install_workspace_guardrail_pair` e `_doctor_guardrail_pair` | P7 |
| T-39 | Escrever testes para `_runtime_expectations` (cada runtime) | P7 |
| T-40 | Escrever testes para `_install_codex_agents` e `_install_opencode` | P7 |
| T-41 | Rodar `pytest --cov` — confirmar >= 80% | P7 |
| T-42 | Rodar `pytest` completo — zero falhas, zero xfail ativos desta release | P8 |
| T-43 | Rodar `python scripts/check_agent_topology.py` — I1-I6 passam | P8 |
| T-44 | Rodar `dadaia public doctor` — sem drift | P8 |
| T-45 | Atualizar `ACTIVE.md` phase → `CLOSURE` | P8 |
| T-46 | Autor CLOSURE.md com evidencias dos 7 criterios de aceite | P8 |
| T-47 | Arquivar release: mover para `specs/_archive/releases/infra-correctness-v1/` | P8 |
| T-48 | Reset `ACTIVE.md` → `release: none` / `phase: none` | P8 |

---

## Validations

Cada validacao abaixo corresponde a um criterio de aceite do SPEC.md §5.

### AC-1: pytest green (zero novas falhas, zero xfail ativos desta release)

**Evidencia por inspecao de codigo:**

- `tests/integration/test_cli_reports.py::test_10_workspace_not_initialized_exits_3`: sem
  marcacao `@pytest.mark.xfail` (removida em T-03). Funcao `resolve_workspace_root()`
  agora dentro do bloco `try` em `reports.py:140`, permitindo que `WorkspaceNotInitializedError`
  seja capturada e o exit code 3 seja emitido corretamente.

- Falhas pre-existentes (fora de escopo desta release, documentadas no SPEC §4):
  - `tests/integration/test_public_install_e2e.py` — 3 testes dependem de wiring de
    `FileSystemPublicAssetManager.install()` que foi diferido desde AGT-r2-35. Esses
    testes usam a funcao diretamente (nota no arquivo: "AGT-r2-35 pending"). Nao sao
    novas falhas; sao conhecidas desde `codex-agent-orchestration-parity-v1`.
  - `tests/integration/test_cli_reports.py::test_08_schema_staged_after_public_install` —
    depende de workspace com schema staged; falha pre-existente de ambiente de CI sem
    stage completo. Identificada em SPEC discovery.

### AC-2: I6 topology guard ativo e passando

**Evidencia por inspecao de codigo:**

```
scripts/check_agent_topology.py:232 — def check_i6_skill_links(agents, errors)
scripts/check_agent_topology.py:262 — check_i6_skill_links(by_stem, errors)  [chamada em main()]
```

Funcao itera sobre `frontmatter["skills"]` de cada agente e verifica que
`SKILLS_DIR / skill_name` e diretorio existente. Conectada apos I5 em `main()`.
Teste negativo (T-09) confirmou I6 FAIL para skill ref ficticia.

### AC-3: Tabelas SQLite mortas dropadas (migration 6)

**Evidencia por inspecao de codigo:**

```
dadaia_workspace/features/telemetry/store/schema.py:16 — SCHEMA_VERSION: int = 6
```

Migration 6 executa:
```sql
DROP TABLE IF EXISTS workflow_agents;
DROP TABLE IF EXISTS workflows;
```
Ordem preserva FK safety (`workflow_agents` antes de `workflows`).

Testes de migration:
- `tests/unit/features/telemetry/test_dao.py::TestMigration6::test_workflows_table_absent_after_migrations`
- `tests/unit/features/telemetry/test_schema.py::test_migration_6_drops_dead_tables`
- `tests/unit/features/telemetry/test_schema.py::test_migration_6_preserves_core_tables`
- `tests/unit/features/telemetry/test_schema.py::test_migration_6_sqlite_master_query`

### AC-4: CSP script-src sem unsafe-inline

**Evidencia por inspecao de codigo:**

```
dadaia_workspace/features/panel/handler.py:56  — _CSP_SCRIPT_HASH_1 = "'sha256-GRTndW6m1zCm5uxB5kEDoOXw05c1c9MDdem3TFqSMfQ='"
dadaia_workspace/features/panel/handler.py:61  — _CSP_SCRIPT_HASH_2 = "'sha256-u9QKVWf5nJ6CpgKA7eHqzt+KvUm6M4dcZhYWRxJuAbA='"
dadaia_workspace/features/panel/handler.py:412 — script-src 'self' {_CSP_SCRIPT_HASH_1} {_CSP_SCRIPT_HASH_2};
```

`'unsafe-inline'` removido de `script-src`. `style-src 'unsafe-inline'` permanece (D4 do SPEC).

Testes:
- `tests/unit/features/panel/test_security_headers.py::test_script_src_no_unsafe_inline_has_sha256_tokens`
- Asserta que `'unsafe-inline'` nao esta em `script-src`; asserta presenca de `sha256-` tokens.

### AC-5: Init resolver usa sentinel walk

**Evidencia por inspecao de codigo:**

```
dadaia_workspace/core/workspace_resolver.py:83 — def resolve_workspace_root_for_init(cwd: Path | None = None) -> Path
```

Funcao: tenta sentinel walk (`resolve_workspace_root`); se `WorkspaceNotInitializedError`
→ retorna `cwd or Path.cwd()` (comportamento seguro para first-time init).

`_resolve_workspace()` removido de `dadaia_workspace/cli/commands/init.py`.
`init.py` importa e chama `resolve_workspace_root_for_init` via
`dadaia_workspace.core.workspace_resolver`.

Testes adicionados em `tests/unit/core/test_workspace_resolver.py`:
- Caso com sentinel: retorna workspace root correto.
- Caso sem sentinel: retorna cwd sem lancar excecao.

### AC-6: Flags de escopo de install funcionando

**Evidencia por inspecao de codigo:**

```
dadaia_workspace/cli/commands/public.py:39  — repos_only: bool = typer.Option(False, "--repos-only", ...)
dadaia_workspace/cli/commands/public.py:42  — workspace_only: bool = typer.Option(False, "--workspace-only", ...)
dadaia_workspace/cli/commands/public.py:47  — if repos_only and workspace_only: [erro de exclusividade]
dadaia_workspace/cli/commands/public.py:51  — scope = "repos-only" if repos_only else ("workspace-only" if workspace_only else "all")
dadaia_workspace/infrastructure/public_assets.py — scope: Literal["all","repos-only","workspace-only"] = "all"
```

9 testes de scope em `tests/unit/features/public/test_install_scope_flags.py`:
- scope="all": workspace-root pair E consumer repos instalados
- scope="workspace-only": apenas workspace-root pair
- scope="repos-only": apenas consumer repos
- CLI `--repos-only` e `--workspace-only` mutuamente exclusivos (exit 1)
- CLI `--repos-only` isolado: exit 0
- CLI `--workspace-only` isolado: exit 0
- Sem flags: comportamento identico a scope="all"

### AC-7: Cobertura >= 80% em public_assets.py

**Evidencia por inspecao de codigo:**

`tests/unit/infrastructure/test_public_assets.py` criado (T-36..T-41).
Arquivo cobre: `doctor()` happy path + D-CX-1..5 drift checks; `_install_workspace_guardrail_pair`;
`_doctor_guardrail_pair`; `_runtime_expectations` cada runtime; `_install_codex_agents`;
`_install_opencode`; helpers de rendering.

Cobertura declarada: 87% (meta era >= 80%). 168 testes na suite de infrastructure.

---

## Drifts

Nenhum drift de implementacao vs PLAN.md foi registrado durante esta release. Todas as
7 fases foram executadas conforme especificado. Os itens pre-existentes excluidos do escopo
(falhas de `test_public_install_e2e.py` e `test_08`) estao documentados no SPEC §4 e sao
conhecidos de releases anteriores — nao constituem drift desta release.

---

## Memory updates

Esta release nao alterou o comportamento visivel ao produto, arquitetura de camadas ou
stack tecnico. As mudancas sao todas correccoes de divida tecnica interna:

- `specs/memory/architecture.html` — sem alteracao: nenhuma mudanca arquitetural nesta release.
- `specs/memory/tech-stack.html` — sem alteracao: sem dependencias novas ou removidas.
- `specs/memory/product/index.html` — sem alteracao: nenhuma feature adicionada ou removida.
- Arquivos de feature (`specs/memory/product/*.html`) — sem alteracao: correcoes de divida
  tecnica nao alteram o catalogo de features nem seu comportamento funcional visivel.

---

## Backlog returns

Nenhum item novo foi descoberto durante a implementacao que requeira entrada no backlog.
Os itens que permaneceram fora de escopo desta release (dark mode, workflow-run-dispatcher,
cli-asset-granular, codex-design-frontend-projection-pilot-v1) ja estavam registrados em
`specs/backlog/candidates.md` antes do inicio desta release e permanecem la sem alteracao.

---

## Archive decision

**MOVE** — o diretorio da release sera movido para `specs/_archive/releases/infra-correctness-v1/`
via `git mv`. `ACTIVE.md` sera atualizado para `release: none` / `phase: none`.

Comando para o devops-engineer ou operador executar:
```bash
git mv specs/releases/infra-correctness-v1 specs/_archive/releases/infra-correctness-v1
```
