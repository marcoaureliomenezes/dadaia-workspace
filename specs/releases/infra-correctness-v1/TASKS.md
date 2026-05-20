# Tasks: Release — infra-correctness-v1

> **Status:** Aprovado
> **Release ID:** infra-correctness-v1
> **Owner:** product-engineer
> **Created:** 2026-05-20

---

## P1 — Exit code fix

- [ ] T-01 `[software-engineer-python]` Ler `reports.py:130–160`, confirmar posição da linha 138
- [ ] T-02 `[software-engineer-python]` Mover `workspace_root = resolve_workspace_root()` para dentro do bloco `try` (linha 141)
- [ ] T-03 `[software-engineer-python]` Remover `@pytest.mark.xfail` de `test_10_workspace_not_initialized_exits_3`
- [ ] T-04 `[software-engineer-python]` Rodar `pytest tests/integration/test_cli_reports.py -v` — todos passam

---

## P2 — I6 topology guard

- [ ] T-05 `[ai-engineer]` Ler `check_agent_topology.py` — entender `SKILLS_DIR`, `AGENTS_DIR`, padrão `check_i*`
- [ ] T-06 `[ai-engineer]` Implementar `check_i6_skill_links(agents, errors)` — valida que `SKILLS_DIR / skill_name` existe
- [ ] T-07 `[ai-engineer]` Conectar `check_i6_skill_links` em `main()` após I5; adicionar linha de summary
- [ ] T-08 `[ai-engineer]` Rodar `python scripts/check_agent_topology.py` — I6 passa para todos os agentes atuais
- [ ] T-09 `[ai-engineer]` Teste negativo manual: skill ref fictícia → I6 FAIL confirmado

---

## P3 — SQLite workflows drop

- [ ] T-10 `[software-engineer-python]` Ler `schema.py` — confirmar `SCHEMA_VERSION=5`, `# DEAD:` nas tabelas
- [ ] T-11 `[software-engineer-python]` Incrementar `SCHEMA_VERSION = 6`; adicionar migration 6 (`DROP TABLE IF EXISTS workflow_agents; DROP TABLE IF EXISTS workflows;`)
- [ ] T-12 `[software-engineer-python]` Adicionar teste de migration 6: aplicar sobre banco com migration 5; verificar tabelas ausentes
- [ ] T-13 `[software-engineer-python]` Rodar `pytest` nos testes de telemetry — sem regressão

---

## P4 — CSP script-src harden

- [ ] T-14 `[software-engineer-python]` Extrair texto literal dos scripts inline em `index.py` e `wrapper.py`
- [ ] T-15 `[software-engineer-python]` Computar SHA-256 base64 de cada script distinto
- [ ] T-16 `[software-engineer-python]` Editar `handler.py:392` — substituir `'unsafe-inline'` em `script-src` pelos tokens `'sha256-<hash>'`
- [ ] T-17 `[software-engineer-python]` Adicionar constantes `_CSP_SCRIPT_HASH_*` nomeadas em `handler.py`
- [ ] T-18 `[software-engineer-python]` Adicionar/estender teste unitário: `script-src` sem `unsafe-inline`, com pelo menos um token `sha256-`
- [ ] T-19 `[software-engineer-python]` Rodar `pytest tests/unit/features/panel/ -v`

---

## P5 — Init resolver fix

- [ ] T-20 `[software-engineer-python]` Ler `workspace_resolver.py` — entender `resolve_workspace_root` e `_SENTINEL`
- [ ] T-21 `[software-engineer-python]` Adicionar `resolve_workspace_root_for_init(cwd)` em `workspace_resolver.py` (sentinel walk + fallback para cwd)
- [ ] T-22 `[software-engineer-python]` Ler `init.py:1–50` — localizar `_resolve_workspace` e seu caller
- [ ] T-23 `[software-engineer-python]` Substituir `_resolve_workspace(workspace)` por `resolve_workspace_root_for_init(workspace)` em `init.py`; remover `_resolve_workspace`
- [ ] T-24 `[software-engineer-python]` Adicionar import de `resolve_workspace_root_for_init` em `init.py`
- [ ] T-25 `[software-engineer-python]` Escrever 2 unit tests em `test_workspace_resolver.py` (com sentinel; sem sentinel → retorna cwd)
- [ ] T-26 `[software-engineer-python]` Rodar `pytest tests/unit/core/ -v`

---

## P6 — Install scope flags

- [ ] T-27 `[software-engineer-python]` Ler `public_assets.py` — localizar `install()`, `_install_workspace_guardrail_pair`, loop de repos
- [ ] T-28 `[software-engineer-python]` Adicionar `scope: Literal["all","repos-only","workspace-only"] = "all"` a `FileSystemPublicAssetManager.install()`
- [ ] T-29 `[software-engineer-python]` Propagar scope: guardrail pair apenas em `"all"` ou `"workspace-only"`; loop de repos apenas em `"all"` ou `"repos-only"`
- [ ] T-30 `[software-engineer-python]` Adicionar `--repos-only` e `--workspace-only` em `public.py`; validar exclusividade mútua
- [ ] T-31 `[software-engineer-python]` Derivar e passar `scope` para `manager.install()`
- [ ] T-32 `[software-engineer-python]` Adicionar testes para cada scope (all, repos-only, workspace-only, exclusividade)
- [ ] T-33 `[software-engineer-python]` Rodar `pytest tests/integration/` relacionados a `dadaia public install`

---

## P7 — Coverage lift  *(após P6)*

- [ ] T-34 `[software-engineer-python]` **Passo 0:** Rodar `pytest --cov=dadaia_workspace/infrastructure/public_assets --cov-report=term-missing` — capturar linhas não cobertas
- [ ] T-35 `[software-engineer-python]` Criar `tests/unit/infrastructure/__init__.py` se ausente
- [ ] T-36 `[software-engineer-python]` Criar `tests/unit/infrastructure/test_public_assets.py`
- [ ] T-37 `[software-engineer-python]` Escrever testes para `doctor()` happy path + D-CX-1..5 drift checks
- [ ] T-38 `[software-engineer-python]` Escrever testes para `_install_workspace_guardrail_pair` e `_doctor_guardrail_pair`
- [ ] T-39 `[software-engineer-python]` Escrever testes para `_runtime_expectations` (cada runtime)
- [ ] T-40 `[software-engineer-python]` Escrever testes para `_install_codex_agents` e `_install_opencode` (com mock de filesystem)
- [ ] T-41 `[software-engineer-python]` Rodar `pytest --cov` → confirmar ≥ 80%; adicionar testes se abaixo

---

## P8 — CLOSURE prep  *(após P7)*

- [ ] T-42 `[product-engineer]` Rodar `pytest` completo — zero falhas, zero xfail ativos desta release
- [ ] T-43 `[product-engineer]` Rodar `python scripts/check_agent_topology.py` — I1–I6 passam
- [ ] T-44 `[product-engineer]` Rodar `dadaia public doctor` — sem drift
- [ ] T-45 `[product-engineer]` Atualizar `ACTIVE.md` phase → `CLOSURE`
- [ ] T-46 `[product-engineer]` Autor CLOSURE.md com evidências dos 7 critérios de aceite
- [ ] T-47 `[product-engineer]` Arquivar release: mover para `specs/_archive/releases/infra-correctness-v1/`
- [ ] T-48 `[product-engineer]` Reset `ACTIVE.md` → `release: none` / `phase: none`
