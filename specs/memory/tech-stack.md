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

### Superfície congelada do v1.0
- `dadaia init`
- `dadaia context create|list|show|activate|deactivate|delete|add-repo|remove-repo`
- `dadaia repos list`
- `dadaia public install`

### Política operacional para agentes
- A superfície de autodiscovery inclui `dadaia --help`, `dadaia <grupo> --help` e `dadaia <grupo> <subcomando> --help`.
- Sempre que uma capacidade existir na CLI oficial, agentes devem preferir a CLI ao acesso direto a arquivos, banco ou módulos internos.
- Falhas de comando devem preservar a causa original e expor mensagens acionáveis o suficiente para guiar retry, correção de entrada ou uso do comando adequado.

---

## Persistência e Catálogo

| Item | Escolha | Justificativa |
|---|---|---|
| Estado persistido | SQLite via `sqlite3` | Simples, local, suficiente para metadata e restrições de unicidade |
| Catálogo de repositórios | openpyxl sobre `.xlsx` | Formato facilmente editável pelo usuário |

Paths operacionais:
- Venv: `.dadaia/.venv`
- Banco: `.dadaia/data/dadaia.db`
- Catálogo: `.dadaia/src/repos.xlsx`
- Relatórios persistentes: `.dadaia/reports/`
- Scripts de automação: `.dadaia/scripts/`
- Estados JSON duráveis: `.dadaia/states/`
- Efêmeros Python: `.dadaia/tmp/python/`
- Efêmeros JSON: `.dadaia/tmp/json/`
- Materialização: `.dadaia/contexts/<context-name>/`
- Academy: `.dadaia/academy/`

---

## Operações Git

| Item | Escolha | Justificativa |
|---|---|---|
| Execução git | `subprocess` com CLI `git` | Zero dependências extras; usa a configuração do sistema |
| Origem de credenciais | Sistema operacional | Mantém segurança fora do app |

O produto opera sobre clones gerenciados materializados no workspace, não sobre o repositório de origem diretamente.

---

## Modelo de Execução Python

- Após `dadaia init`, o executável Python canônico é `<workspace-root>/.dadaia/.venv/bin/python`.
- O executável pip canônico é `<workspace-root>/.dadaia/.venv/bin/pip`.
- Agentes e automações devem preferir essa venv a qualquer Python global do sistema.
- Scripts Python efêmeros e dados transitórios usados por agentes pertencem apenas a `.dadaia/tmp/python/` e `.dadaia/tmp/json/`.
- Scripts efêmeros são fallback controlado, não a interface primária, para capacidades que já existam na CLI oficial.

---

## Qualidade e Testes

| Item | Escolha |
|---|---|
| Framework de testes | pytest |
| Formatação e lint | ruff |
| Type checking | mypy --strict |
| Estratégia de testes de features | fakes sobre Protocols |

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
  core/
    exceptions.py
    models/
    protocols/
  features/
    workspace/
    spec_context/
    repos/
    public/
  infrastructure/
    database.py
    sqlite_repositories.py
    git_subprocess.py
    excel_reader.py
    public_assets.py
  public/
    rules/
    skills/
    commands/
```

---

## Entry Point

```toml
[tool.poetry.scripts]
dadaia = "dadaia_workspace.cli.main:app"
```

Instalação de desenvolvimento: `poetry install`.
