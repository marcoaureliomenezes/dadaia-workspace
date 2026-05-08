# TASKS.md — dadaia-workspace

**Feature:** Implementação completa do pacote `dadaia-workspace`  
**Versão:** 1.4  
**Status:** Aprovado  
**Baseado em:** `specs/PLAN.md`, `specs/SPEC.md`, `specs/foundation/SPEC.md`, `specs/features/spec-context-project/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## Convenções deste backlog

- Cada task é uma unidade de commit pequena e verificável.
- Definition of Done por task: código + testes + `make lint` + `make typecheck`.
- Sempre citar o contrato coberto pela task em review de implementação.
- Qualquer mudança em `specs/` durante implementação deve atualizar `z_bug_specs.md` se restar novo gap.

---

## Phase 0 — Governança SDD Inicial

### T35 — Criar rules autoritativas em `dadaia_workspace/public/rules` `[Agent FR-001, FR-002, FR-005 a FR-009, FR-018 a FR-025]`
- `dadaia-workspace-sdd-enforcer`
- `dadaia-workspace-spec-governance`
- **Verificação:** frontmatter compatível com assets públicos, ordem canônica de revisão, política de `.dadaia/.venv/`, política de `.dadaia/tmp/`, política CLI-first para agentes, ausência de `.claude/` local no repositório e interpretação explícita de `**Status:** Aprovado`.

### T36 — Criar skills autoritativas em `dadaia_workspace/public/skills` `[Agent FR-010 a FR-025]`
- `dadaia-workspace-spec-navigator`
- `dadaia-workspace-spec-reviewer`
- **Verificação:** usam `dadaia context show --json` como contrato oficial, suportam modo local do repositório para pré-implementação, aplicam política CLI-first com help-first discovery, respeitam o fallback em `.dadaia/tmp/python/` e bloqueiam implementação sem status explícito de aprovação.

### T37 — Criar workflow markdown autoritativo em `dadaia_workspace/public/commands` `[Agent FR-001, FR-002, FR-008, FR-009, FR-018, FR-019]`
- Workflow de refinamento de specs antes de implementação, com ordem fixa, política de documentos derivados e política explícita de aprovação.

### T38 — Garantir extração de assets de `public/` para `.claude/` do workspace `[Agent FR-001 a FR-004, FR-020 a FR-025]`
- Implementar bootstrap e instalação lendo apenas de `dadaia_workspace/public/`.
- **Verificação:** `dadaia init` e `dadaia public install` nunca dependem de `dadaia-workspace/.claude/`.

### T39 — Adicionar teste de ausência de `.claude/` local e extração correta `[Agent NFR-003]`
- Garantir que o repositório não mantém `dadaia-workspace/.claude/` como fonte duplicada.
- Garantir que a instalação extrai os assets corretos de `dadaia_workspace/public/` para o `.claude/` do workspace alvo.

---

## Phase 1 — Scaffolding e Tooling

### T01 — Inicializar Poetry e dependências base `[SPEC FR-001, FR-005]`
- Configurar `pyproject.toml` com Poetry, Python 3.12+, Typer, Rich, openpyxl, pytest, ruff e mypy.
- **Verificação:** `poetry install` executa sem erro.

### T02 — Criar estrutura oficial do pacote `[Foundation RF-ARCH-002]`
- Criar diretórios e `__init__.py` conforme a estrutura congelada do plano.
- **Verificação:** árvore do pacote coincide com a seção 3 do `PLAN.md`.

### T03 — Configurar scripts, lint e typecheck `[Foundation RF-BUILD-001, RF-CONV-004]`
- Declarar entry point `dadaia`, configurar ruff, mypy e pytest.
- **Verificação:** `make lint` e `make typecheck` executam no scaffold.

### T04 — Criar `Makefile` e `.pre-commit-config.yaml` `[Foundation RF-QA-004, RF-CONV-004]`
- Incluir `install`, `test`, `lint`, `typecheck`, `format` e `clean`.
- **Verificação:** `pre-commit run --all-files` passa nos arquivos existentes.

---

## Phase 2 — Core Contracts e Fakes

### T05 — Implementar `core/exceptions.py` `[Foundation RF-ARCH-008, RF-QA-006, RF-QA-007]`
- Criar `DadaiaError` e subclasses alinhadas ao produto, com encadeamento explícito de causa e mensagens acionáveis para agentes.
- **Teste:** `tests/unit/core/test_exceptions.py`.

### T06 — Implementar modelos imutáveis de workspace e contexto `[SpecContext FR-001 a FR-016]`
- Criar `ContextState`, `RepoRole`, `RepoSourceKind`, `ContextRepositoryRef`, `SpecContextProject` e `Workspace`.
- **Teste:** imutabilidade e transições válidas.

### T07 — Definir Protocols de repositório, git, storage e runtime env `[Plan seção 5]`
- Criar `WorkspaceRepository`, `SpecContextRepository`, `GitClient`, `ExcelReader`, `PublicAssetManager` e `PythonEnvironmentManager`.
- **Verificação:** `mypy --strict`.

### T08 — Criar `tests/fakes.py` `[Foundation RF-QA-002]`
- Fakes para repositórios, git, excel e assets públicos.
- **Verificação:** unit tests de features podem rodar sem I/O.

---

## Phase 3 — Persistência e Infraestrutura

### T09 — Implementar schema e connection factory `[SPEC FR-002, SpecContext FR-012]`
- Criar `database.py` com schema completo, incluindo índice único parcial para `ativo`.
- **Teste de integração:** criação idempotente do banco.

### T10 — Implementar repositório SQLite do agregado de contexto `[SpecContext FR-001 a FR-027]`
- Persistir `spec_context_projects` e `spec_context_repositories` como um agregado único.
- **Teste de integração:** create/get/list/delete com primário + secundários.

### T11 — Implementar repositório SQLite de workspace `[SPEC FR-001, FR-002]`
- Persistir e recuperar metadata do workspace.
- **Teste de integração:** bootstrap e reload.

### T12 — Implementar `git_subprocess.py` `[SpecContext FR-013 a FR-023]`
- Suportar `clone`, `is_git_repo`, `has_changes`, `has_remote`, `commit_all`, `push`.
- **Teste de integração:** repo limpo, repo dirty, repo sem remote e falha de push.

### T13 — Implementar `excel_reader.py` `[SPEC FR-004]`
- Ler `repos.xlsx` e devolver linhas estruturadas.
- **Teste de integração:** workbook real em `tmp_path`.

### T14 — Implementar `public_assets.py` e `python_env.py` `[SPEC FR-005, FR-009, FR-013]`
- Instalar assets empacotados em diretório alvo com política de overwrite controlada.
- Implementar criação idempotente de `<workspace-root>/.dadaia/.venv/` e resolução dos executáveis `python` e `pip` do workspace.
- **Teste de integração:** cópia sem `--force`, cópia com `--force` e criação idempotente da venv.

---

## Phase 4 — Services de Workspace e Public Assets

### T15 — Implementar `features/workspace/service.py` `[SPEC FR-001, FR-009, FR-013, FR-014]`
- Responsável por bootstrap do template canônico de `.dadaia/`, criação de `.dadaia/.venv/`, política de `.dadaia/tmp/` e metadata do workspace.
- **Teste unitário:** init idempotente, reconciliação de template parcial e erro de workspace ausente.

### T16 — Implementar `features/public/service.py` `[SPEC FR-005, FR-009]`
- Orquestrar instalação de assets públicos em `.claude/` alvo.
- **Teste unitário:** no-overwrite por padrão.

### T17 — Implementar builders no `container.py` `[Foundation RF-ARCH-004]`
- Construir services de workspace, spec context, repos e public.
- **Verificação:** nenhum comando CLI instancia infraestrutura diretamente.

---

## Phase 5 — Service de Spec Context

### T18 — Implementar `create()` `[SpecContext FR-001 a FR-003]`
- Criar contexto em `inativo` com repositório principal e secundários.
- **Teste unitário:** duplicidade e criação válida.

### T19 — Implementar `list_all()` e `show()` `[SpecContext FR-004 a FR-006]`
- Listagem do agregado completo e resolução do contexto ativo ou nomeado.
- **Teste unitário:** show por nome, show do ativo e ausência de ativo.

### T20 — Implementar `activate()` com materialização `[SpecContext FR-007 a FR-016]`
- Materializar clones gerenciados, preencher `specs_dir`, mover antigo `ativo` para `standby`.
- **Teste unitário:** transição `inativo -> ativo`, `standby -> ativo` e troca de contexto.

### T21 — Implementar `deactivate()` `[SpecContext FR-010 a FR-012]`
- Operar sem parâmetro sobre o contexto ativo.
- **Teste unitário:** erro sem contexto ativo e transição para `standby`.

### T22 — Implementar `add-repo()` `[SpecContext FR-024, FR-025]`
- Adicionar repositório secundário ao agregado.
- **Teste unitário:** inclusão e duplicata.

### T23 — Implementar `remove-repo()` `[SpecContext FR-026, FR-027]`
- Remover repositório secundário sem permitir remoção do primário.
- **Teste unitário:** remoção válida e bloqueio do primário.

### T24 — Implementar `delete()` com contrato implementável `[SPEC FR-010, FR-011, SpecContext FR-017 a FR-023]`
- `inativo`: remove metadata.
- `standby`: sincroniza clones gerenciados, preserva local em caso de falha.
- **Teste unitário:** repo limpo, repo com mudanças, repo sem remote, erro parcial.

### T25 — Teste de integração do lifecycle completo `[SpecContext FR-001 a FR-030]`
- Fluxo: create → activate → show --json → deactivate → add/remove repo → delete.

---

## Phase 6 — Service de Repositórios Conhecidos

### T26 — Implementar `features/repos/service.py` `[SPEC FR-004]`
- Ler o catálogo consultivo e devolver estrutura para a CLI.
- **Teste unitário:** catálogo vazio e catálogo com dados.

---

## Phase 7 — CLI Congelada

### T27 — Implementar `cli/main.py` `[SPEC FR-012, FR-015, FR-017, FR-018, SpecContext FR-028 a FR-030]`
- Registrar a superfície congelada: `init`, `context`, `repos`, `public`, com help granular e tratamento compartilhado de falhas orientado a agentes.
- **Verificação:** `dadaia --help` lista exatamente esses grupos.

### T28 — Implementar `cli/commands/init.py` `[SPEC FR-001, FR-009, FR-013, FR-014]`
- Comando top-level `dadaia init [--skip-assets]`.
- **Teste E2E:** bootstrap inicial, template `.dadaia/` completo, criação da venv e segunda execução idempotente.

### T29 — Implementar `cli/commands/context.py` — create/list/show `[SpecContext FR-001 a FR-006]`
- Incluir `show --json` com contrato estável.
- **Teste E2E:** `create`, `list`, `show`, `show --json`.

### T30 — Implementar `cli/commands/context.py` — activate/deactivate/delete `[SpecContext FR-007 a FR-023]`
- **Teste E2E:** troca de contexto, desativação, deleção bloqueada em `ativo`, deleção segura em `standby`.

### T31 — Implementar `cli/commands/context.py` — add-repo/remove-repo `[SpecContext FR-024 a FR-027]`
- **Teste E2E:** duplicata, remoção válida, bloqueio do primário.

### T32 — Implementar `cli/commands/repos.py` `[SPEC FR-004]`
- **Teste E2E:** tabela do catálogo.

### T33 — Implementar `cli/commands/public.py` `[SPEC FR-005, Agent FR-003, FR-004]`
- Suportar `--target` e `--force`.
- **Teste E2E:** instalação padrão e overwrite com `--force`.

### T34 — Congelar help, JSON e contrato de erro `[SPEC NFR-002, NFR-006, SpecContext NFR-003]`
- Validar textos de help, snapshots da saída JSON e mensagens de erro da CLI para falhas comuns.
- **Verificação:** testes snapshot para `--help`, `show --json` e erros representativos.

---

## Phase 8 — Qualidade Final

### T40 — Completar suíte E2E do produto `[SPEC FR-001 a FR-012]`
- Cobrir bootstrap, lifecycle de contexto, catálogo e instalação de assets.

### T41 — Garantir cobertura mínima `[Foundation RF-QA-003]`
- Ajustar testes até atingir meta.

### T42 — Validar build do pacote com public assets `[Foundation RF-BUILD-002]`
- `poetry build` e inspeção do artefato.

### T43 — Validar fluxo README/Bootstrap do usuário `[SPEC US-001, US-004]`
- Ensaiar `poetry install` → `dadaia init` → `dadaia public install` em diretório limpo, incluindo criação e uso de `.dadaia/.venv/`.

### T44 — Validar superfície de erro agent-friendly `[SPEC FR-017, FR-018, NFR-006, Foundation RF-QA-006, RF-QA-007]`
- Cobrir falhas comuns da CLI com asserts de mensagem e cadeia causal preservada.
- **Verificação:** erro por workspace não inicializado, contexto ausente, input inválido e falha de sync exibem mensagem acionável e mantêm exceção de origem.

---

## Ordem Obrigatória

```
T35-T39 → T01-T04 → T05-T08 → T09-T14 → T15-T17 → T18-T25 → T26 → T27-T34 → T40-T44
```

---

## Anti-padrões Proibidos Durante Implementação

| Anti-padrão | Proibição |
|---|---|
| Reabrir arquitetura no código | Não criar `domain/`, `manager/` ou layers paralelas fora do plano |
| Reabrir state machine | Não introduzir `arquivado` ou `update` sem revisão de specs |
| Parsing humano para automação | Não usar `context list` como fonte canônica para agentes |
| Mutar repo de origem | Não operar delete fora de `.dadaia/contexts/` |
| Efêmeros fora do workspace | Não gerar scripts ou JSON transitórios fora de `.dadaia/tmp/` |
| Usar Python global | Não executar automação Python fora de `.dadaia/.venv/` após o bootstrap |
| Esquecer rastreabilidade | Toda task deve apontar para contratos específicos |
