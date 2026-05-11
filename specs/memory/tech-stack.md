# Tech Stack: dadaia-workspace

## Linguagem e Runtime

| Item | Escolha | Justificativa |
|---|---|---|
| Linguagem | Python 3.12+ | Type hints maduros, stdlib robusta, boa ergonomia para CLI e tooling |
| Gerenciador de pacotes e build | Poetry | Dependency lock, scripts, build e packaging em um único fluxo |
| Ambiente Python isolado | `venv` (stdlib) em `.dadaia/.venv` | Isola dependências do workspace e padroniza a execução de agentes |

---

## CLI

| Item | Escolha | Justificativa |
|---|---|---|
| Framework CLI | Typer | Ajuda auto-documentada e ergonomia forte para comandos estruturados |
| Output rico | Rich | Tabelas e destaque visual em saídas humanas |
| Contrato machine-readable | JSON via `--json` | Evita parsing frágil por agentes |

### Superfície v4.0

```
dadaia init [--skip-assets]
dadaia context create|list|show|activate|deactivate|promote|delete|use
dadaia repos list
dadaia public stage
dadaia public install --target all|claude|codex|opencode|agents [--force]
dadaia public doctor
dadaia doctor [--fix]
```

### Política operacional para agentes
- A superfície de autodiscovery inclui `dadaia --help`, `dadaia <grupo> --help` e `dadaia <grupo> <subcomando> --help`.
- Falhas de comando preservam a causa original e expõem mensagens acionáveis para guiar retry, correção ou uso do comando adequado.

---

## Estado e Catálogo

| Item | Escolha | Justificativa |
|---|---|---|
| Estado de contextos | JSON (`spec_contexts.json`) via stdlib `json` | Simples, legível por humanos, reparável sem ferramentas especiais |
| Escrita atômica de estado | `os.replace()` com arquivo `.tmp` intermediário | Garante que o estado nunca fica corrompido por escrita parcial |
| Catálogo de repositórios | openpyxl sobre `.xlsx` | Formato facilmente editável pelo operador |

Paths operacionais:
- Venv: `.dadaia/.venv/`
- Estado de contextos: `.dadaia/states/spec_contexts.json`
- Ponteiro do primário: `.dadaia/states/primary_context.json`
- Catálogo: `.dadaia/src/repos.xlsx`
- Relatórios persistentes: `.dadaia/reports/`
- Scripts de automação: `.dadaia/scripts/`
- Staging de assets agentic: `.dadaia/agentic/`
- Skills universais: `.agents/skills/`
- Projeção Claude Code: `.claude/`
- Projeção Codex: `.codex/`
- Projeção OpenCode: `.opencode/` e `opencode.json`
- Efêmeros Python: `.dadaia/tmp/python/`
- Efêmeros JSON: `.dadaia/tmp/json/`

**Não existe mais** `.dadaia/data/dadaia.db` (SQLite removido) nem `.dadaia/contexts/` (materialização removida).

---

## Operações Git

| Item | Escolha | Justificativa |
|---|---|---|
| Execução git | `subprocess` com CLI `git` | Zero dependências extras; usa a configuração do sistema |
| Origem de credenciais | Sistema operacional | Mantém segurança fora do app |
| Uso no produto | clone em `activate`, commit+push em `deactivate` | Ciclo de vida de repos gerenciado |

O produto opera sobre repos clonados em `<workspace-root>/repos/`. O clone é feito via `git clone <repo_url>` usando `subprocess`. O git sync antes de deactivate é obrigatório para evitar perda de dados.

---

## Modelo de Execução Python

- Após `dadaia init`, o executável Python canônico é `<workspace-root>/.dadaia/.venv/bin/python`.
- O executável pip canônico é `<workspace-root>/.dadaia/.venv/bin/pip`.
- Agentes e automações devem preferir essa venv a qualquer Python global do sistema.
- Scripts Python efêmeros e dados transitórios usados por agentes pertencem apenas a `.dadaia/tmp/python/` e `.dadaia/tmp/json/`.

---

## Qualidade e Testes

| Item | Escolha |
|---|---|
| Framework de testes | pytest |
| Formatação e lint | ruff |
| Type checking | mypy --strict |
| Estratégia de testes de features | fakes sobre Protocols |
| Testes E2E | `tests/e2e/features/` com subprocess CLI |

---

## Estrutura do Pacote Python

```
dadaia_workspace/
  container.py
  cli/
    main.py
    commands/
      init.py
      context.py
      repos.py
      public.py
      doctor.py
  core/
    exceptions.py
    models/
      workspace.py
      spec_context.py
    protocols/
      context_store.py
      git_client.py
      storage.py
      runtime_env.py
  features/
    workspace/
      service.py
    spec_context/
      service.py
      doctor.py
    repos/
      service.py
    public/
      service.py
  infrastructure/
    json_context_store.py
    git_subprocess.py
    excel_reader.py
    public_assets.py
    python_env.py
  public/
    agents/
    rules/
    skills/
    commands/
    scripts/
    templates/
    data/
      repos.xlsx
tests/
  fakes.py
  unit/
  integration/
  e2e/
    features/
      test_workspace_setup.py
      test_spec_context.py
```

---

## Entry Point

```toml
[tool.poetry.scripts]
dadaia = "dadaia_workspace.cli.main:app"
```

Instalação de desenvolvimento: `poetry install`.
