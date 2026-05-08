# Architecture: dadaia-workspace

## Escopos Distintos

- `dadaia-workspace/` é o **repositório da biblioteca**: authoring de código, specs e assets de agente.
- `<workspace-root>/` é o **runtime workspace do usuário**: local onde a biblioteca cria `.dadaia/` e `.claude/`.
- O template canônico do runtime workspace é definido neste arquivo. Outros documentos devem referenciar este contrato, não reescrevê-lo.

## Visão Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        dadaia-workspace                            │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐               │
│  │ CLI Layer   │──▶│ Features    │──▶│ Core         │               │
│  │ (Typer)     │   │ (Business)  │   │ (Models +    │               │
│  └─────────────┘   └─────────────┘   │ Protocols)   │               │
│          │                ▲          └──────────────┘               │
│          ▼                │                 ▲                       │
│   container.py ───────────┘                 │                       │
│          │                                  │                       │
│          ▼                                  │                       │
│   Infrastructure (SQLite, git, XLSX, public assets)                │
└─────────────────────────────────────────────────────────────────────┘
```

`dadaia_workspace/container.py` é a composition root e monta serviços a partir de implementações concretas da infraestrutura.

---

## Estrutura do Workspace em Disco

```
<workspace-root>/
  .claude/
    rules/
    skills/
    commands/
  .dadaia/
    academy/
      01_o_que_e_o_dadaia_workspace/
        README.md
        REFERENCES.md
        EXAMPLE.md
        01_visao_geral.md
    .venv/
    reports/
    scripts/
    states/
    src/
      repos.xlsx
    data/
      dadaia.db
    tmp/
      python/
      json/
    contexts/
      <context-name>/
        repos/
          <repo-slug>/
  specs/
```

### Princípio operacional
- `.claude/` no workspace do usuário contém artefatos instalados para execução.
- `.dadaia/academy/` contém o material base da Dadaia Academy e os cursos gerados no runtime do usuário.
- `.dadaia/.venv/` é o ambiente Python isolado do workspace.
- `.dadaia/contexts/` contém apenas materializações gerenciadas pelo produto.
- `.dadaia/tmp/python/` e `.dadaia/tmp/json/` são as únicas áreas válidas para artefatos efêmeros gerados por agentes.
- `.dadaia/reports/` contém relatórios persistentes e legíveis para humanos.
- `.dadaia/scripts/` contém scripts de automação persistentes do workspace (ex: watchdog, deploy, manutenção).
- `.dadaia/states/` contém arquivos JSON de estado durável do workspace (ex: whitelist de modelos, estado de audit). Distinto de `tmp/json/` que é efêmero.
- `.dadaia/src/` contém arquivos fonte do workspace, como `repos.xlsx`.
- Repositórios de origem apontados por `repo_ref` não são apagados nem mutados diretamente pelo sistema de deleção.

### Política de efemeridade
- Scripts e artefatos transitórios gerados por sessão não pertencem ao repositório da biblioteca.
- O conteúdo de `.dadaia/tmp/` pode ser recriado, limpo ou substituído sem impacto no estado durável do workspace.
- O conteúdo de `.dadaia/academy/` não é efêmero: ele faz parte do runtime durável do workspace e pode ser enriquecido incrementalmente pelo usuário ou por workflows de agente.
- O conteúdo de `.dadaia/states/` é durável: JSON states não devem ser limpos por rotinas de manutenção; somente o sistema que os escreve pode atualizá-los ou removê-los.
- O conteúdo de `.dadaia/scripts/` é durável: scripts de automação persistem entre sessões e devem ser versionados ou gerenciados explicitamente pelo usuário.

---

## State Machine: Spec Context Project

```
create
  └──────────────▶ INATIVO
                      │
                      │ activate
                      ▼
                   ATIVO
                    │  ▲
         deactivate │  │ activate outro
                    ▼  │
                 STANDBY

INATIVO ─── delete ─▶ [remove metadata]
STANDBY ─── delete ─▶ [sync managed repos → remove managed files → remove metadata]
ATIVO ───── delete ─▶ ERRO
```

### Definição dos Estados

| Estado | Materialização gerenciada | Significado |
|---|---|---|
| `inativo` | Não | Contexto existe apenas como metadata |
| `standby` | Sim | Contexto existe em `.dadaia/contexts/`, mas não é o foco atual |
| `ativo` | Sim | Contexto atual de desenvolvimento; somente um pode existir |

### Regras de Transição

- `create` sempre começa em `inativo`.
- `activate` de `inativo` cria a materialização e muda para `ativo`.
- `activate` de `standby` reaproveita a materialização existente.
- `activate` de outro contexto move o antigo `ativo` para `standby` em uma transição atômica de estado persistido.
- `deactivate` só existe sem parâmetro e opera sobre o contexto `ativo` atual.
- `delete` só é permitido para `inativo` e `standby`.

---

## Modelo de Dados (SQLite)

### Tabela: `workspaces`

| Coluna | Tipo | Descrição |
|---|---|---|
| `root_path` | TEXT PK | Caminho do workspace |
| `created_at` | TEXT NOT NULL | Timestamp ISO 8601 |
| `updated_at` | TEXT NOT NULL | Timestamp ISO 8601 |

### Tabela: `spec_context_projects`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Identificador único |
| `name` | TEXT UNIQUE NOT NULL | Nome do contexto |
| `state` | TEXT NOT NULL | `inativo` / `standby` / `ativo` |
| `context_dir` | TEXT | Diretório gerenciado do contexto |
| `specs_dir` | TEXT | Diretório `specs/` derivado do repo principal materializado |
| `created_at` | TEXT NOT NULL | Timestamp ISO 8601 |
| `activated_at` | TEXT | Timestamp ISO 8601 |
| `updated_at` | TEXT NOT NULL | Timestamp ISO 8601 |

### Tabela: `spec_context_repositories`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Identificador único |
| `context_id` | INTEGER FK | Referência ao contexto |
| `role` | TEXT NOT NULL | `primary` / `secondary` |
| `repo_ref` | TEXT NOT NULL | URL git ou caminho local do repo de origem |
| `source_kind` | TEXT NOT NULL | `remote_url` / `local_path` |
| `repo_slug` | TEXT NOT NULL | Nome estável usado no disco |
| `materialized_path` | TEXT | Clone gerenciado do repo |
| `has_specs_dir` | INTEGER NOT NULL | 0 / 1 |
| `created_at` | TEXT NOT NULL | Timestamp ISO 8601 |
| `updated_at` | TEXT NOT NULL | Timestamp ISO 8601 |

### Restrições

- `UNIQUE(context_id, repo_ref)` para impedir repositórios duplicados no mesmo contexto.
- Índice único parcial para garantir apenas um contexto com `state = 'ativo'`.

---

## Materialização de Repositórios

### Contrato
- `repo_ref` pode ser uma URL git ou um caminho local para um repositório git.
- A materialização sempre cria clones gerenciados em `.dadaia/contexts/<name>/repos/<repo-slug>/`.
- Mesmo quando `repo_ref` é um caminho local, o sistema trabalha sobre o clone gerenciado, não sobre a origem direta.

### Benefício
Isso isola o workspace-managed state do estado do repositório de origem e torna a deleção implementável sem risco de apagar conteúdo fora da área gerenciada.

---

## Ambiente Python do Workspace

- O bootstrap de `dadaia init` cria `<workspace-root>/.dadaia/.venv/`.
- Dependências Python do `dadaia-workspace` e automações auxiliares vivem dentro dessa venv.
- Após o bootstrap, agentes devem usar `<workspace-root>/.dadaia/.venv/bin/python` e `<workspace-root>/.dadaia/.venv/bin/pip` para operações Python.

---

## Fluxo de Ativação

1. Carregar metadata do contexto.
2. Se o contexto estiver `inativo`, criar `.dadaia/contexts/<name>/`.
3. Materializar todos os repositórios do contexto em `repos/`.
4. Derivar `specs_dir` a partir do clone gerenciado do repo principal.
5. Se `specs/constitution.md` ou `specs/SPEC.md` não existirem no repo principal materializado, emitir warning.
6. Persistir a troca de estado para `ativo`, movendo o contexto antigo para `standby` quando necessário.

---

## Fluxo de Deleção

### Contexto `inativo`
1. Remover registros de banco.
2. Encerrar operação.

### Contexto `standby`
1. Para cada repositório materializado do contexto, executar a etapa de sync do fluxo de deleção.
2. Se um repo não tiver mudanças, pular commit nesse repo.
3. Se uma etapa obrigatória falhar, manter metadata e arquivos gerenciados intactos.
4. Reportar explicitamente que repositórios anteriores podem já ter sido sincronizados remotamente.
5. Apenas se todos os sync steps obrigatórios tiverem sucesso: remover `.dadaia/contexts/<name>/` e a metadata persistida.

---

## Catálogo de Repositórios Conhecidos

`.dadaia/src/repos.xlsx` é um catálogo consultivo do workspace. Ele ajuda descoberta e preenchimento de referências, mas não limita o uso de `repo_ref` a entradas previamente cadastradas.

Colunas mínimas esperadas:
- `name`
- `repo_ref`
- `description` (opcional)

---

## Dadaia Academy no Runtime

### Contrato atual
- O material base da academy vive em `<workspace-root>/.dadaia/academy/`.
- A primeira trilha canônica da academy usa diretórios de sessão numerados diretamente sob `.dadaia/academy/`.
- Cada sessão possui `README.md`, `REFERENCES.md`, `EXAMPLE.md` e arquivos markdown de conteúdo com prefixo numérico de dois dígitos.
- O conteúdo da academy deve ser durável, legível por humanos e utilizável por agentes como material de grounding.

### Relação com `.claude/`
- `.claude/commands/` é o local de instalação de slash commands de agente, incluindo o futuro `/dadaia-academy`.
- Esses commands operam sobre `.dadaia/academy/`, mas não substituem o runtime pedagógico por arquivos dentro de `.claude/`.
- O binário `dadaia` continua responsável pela CLI congelada do produto; a academy agent-facing entra como command do ambiente de agente.

---

## Camada de Integração com Agentes

### Modelo em dois níveis

1. **Fonte versionada no pacote:** `dadaia_workspace/public/` dentro deste repositório.
2. **Instalação runtime:** `.claude/` do workspace do usuário.

`dadaia-workspace/.claude/` não faz parte do produto e não deve existir como source of truth local do repositório.

### Descoberta do contexto ativo

Agentes não devem depender de parsing de `dadaia context list`. O contrato oficial é:

```bash
dadaia context show --json
```

Essa saída deve permitir resolver:
- `name`
- `state`
- `context_dir`
- `specs_dir`
- `primary_repo`
- `secondary_repos`

### Autodiscovery e recuperação via CLI

- A superfície oficial de autodiscovery para agentes inclui `dadaia --help`, `dadaia <grupo> --help` e `dadaia <grupo> <subcomando> --help`.
- Quando existir comando oficial para uma capacidade, a CLI é a fronteira canônica; acesso direto a banco, metadata ou módulos internos não substitui esse contrato.
- Se a CLI ainda não cobrir um caso específico, o fallback permitido é script efêmero em `.dadaia/tmp/python/` com saída estruturada em `.dadaia/tmp/json/`.
- A implementação deve preservar a cadeia de erro entre infraestrutura, features e CLI para que falhas permaneçam diagnósticas para agentes.

### Governança de Specs

Quando arquivos em `specs/` são alterados, uma revisão de consistência deve ler o conjunto relevante de specs e registrar qualquer problema remanescente em `z_bug_specs.md`.
