# PLAN.md — dadaia-workspace

**Feature:** Implementação completa do pacote `dadaia-workspace`  
**Versão:** 1.3  
**Status:** Aprovado  
**Baseado em:** `specs/SPEC.md`, `specs/foundation/SPEC.md`, `specs/features/spec-context-project/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## 1. Decisões Técnicas Congeladas

| Categoria | Decisão | Justificativa |
|---|---|---|
| Package manager | Poetry | Fluxo único para dependências, scripts e build |
| Arquitetura | `CLI -> Features -> Core <- Infrastructure` + `container.py` | Impede drift estrutural e separa composição do núcleo |
| Persistência | SQLite (`sqlite3`) | Metadata local com restrições e índice parcial para contexto ativo |
| Ambiente Python | `venv` (stdlib) em `<workspace-root>/.dadaia/.venv/` | Isola dependências do workspace e padroniza automações dos agentes |
| Catálogo | `repos.xlsx` com openpyxl | Consulta humana simples, sem acoplar criação a cadastro prévio |
| Git | `subprocess` + CLI `git` | Reuso das credenciais do sistema |
| Modelagem | Frozen dataclasses | Imutabilidade e transições explícitas |
| Estilo de implementação | Serviços OO explícitos + modelos de domínio + exceções nomeadas | Mantém responsabilidades claras e favorece diagnóstico por agentes |
| Contrato para agentes | `dadaia context show --json` | Evita parsing de tabela humana |
| Integração agent-facing | CLI-first + help granular + JSON estável | Favorece autodiscovery e uso natural da CLI por agentes |
| Diagnóstico de falhas | Hierarquia explícita de exceções + `raise ... from` + mensagens acionáveis | Mantém stack clara e recuperável para agentes |
| Artefatos de agente | `dadaia_workspace/public/` versionado, `<workspace-root>/.claude/` como destino de instalação | Elimina fonte duplicada e separa pacote de runtime do usuário |

---

## 2. Superfície de CLI Congelada

### 2.1 Comandos top-level

| Comando | Propósito | Saída principal |
|---|---|---|
| `dadaia init` | Bootstrap do workspace | Mensagem humana |
| `dadaia context ...` | Lifecycle dos Spec Context Projects | Mensagem humana / tabela / JSON |
| `dadaia repos list` | Consulta catálogo de repositórios | Tabela humana |
| `dadaia public install` | Instalar artefatos públicos do pacote | Lista de arquivos instalados |

### 2.2 Subcomandos de `context`

| Comando | Opções principais | Contrato |
|---|---|---|
| `create <name>` | `--repo`, `--secondary` | cria em `inativo` |
| `list` | — | tabela humana com destaque do `ativo` |
| `show [name]` | `--json` | humano ou machine-readable estável |
| `activate <name>` | — | move para `ativo`, materializa se preciso |
| `deactivate` | — | move o contexto ativo para `standby` |
| `delete <name>` | — | remove metadata e, se aplicável, materialização gerenciada |
| `add-repo <name>` | `--repo` | adiciona repo secundário |
| `remove-repo <name>` | `--repo` | remove repo secundário |

### 2.3 Contratos adicionais

- `dadaia init` aceita `--skip-assets` para não instalar artefatos públicos no bootstrap.
- `dadaia public install` aceita `--target <path>` e `--force`.
- `dadaia context show --json` é o contrato oficial para automação por agentes.

### 2.4 Política operacional para agentes e erros

- Comandos e subcomandos da CLI são a fronteira oficial para automação; `--help` granular faz parte do contrato.
- Quando a CLI não cobrir uma capacidade, o fallback permitido é script efêmero em `.dadaia/tmp/python/` com output estruturado em `.dadaia/tmp/json/`.
- `core/exceptions.py` define a hierarquia de erros de domínio e de uso da CLI; camadas superiores devem preservar `__cause__` com `raise ... from`.
- A CLI deve renderizar erros com nome da capacidade, recurso afetado e próxima ação segura quando existir.

---

## 3. Estrutura do Pacote

```
dadaia-workspace/
├── pyproject.toml
├── README.md
├── Makefile
├── .pre-commit-config.yaml
├── dadaia_workspace/
│   ├── __init__.py
│   ├── container.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── init.py
│   │       ├── context.py
│   │       ├── repos.py
│   │       └── public.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── workspace.py
│   │   │   └── spec_context.py
│   │   └── protocols/
│   │       ├── __init__.py
│   │       ├── repositories.py
│   │       ├── git_client.py
│   │       ├── storage.py
│   │       └── runtime_env.py
│   ├── features/
│   │   ├── __init__.py
│   │   ├── workspace/service.py
│   │   ├── spec_context/service.py
│   │   ├── repos/service.py
│   │   └── public/service.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── sqlite_repositories.py
│   │   ├── git_subprocess.py
│   │   ├── excel_reader.py
│   │   ├── public_assets.py
│   │   └── python_env.py
│   └── public/
│       ├── rules/
│       ├── skills/
│       └── commands/
└── tests/
    ├── fakes.py
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 4. Modelo de Domínio

### 4.1 Enums

```python
class ContextState(StrEnum):
    INATIVO = "inativo"
    STANDBY = "standby"
    ATIVO = "ativo"

class RepoRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"

class RepoSourceKind(StrEnum):
    REMOTE_URL = "remote_url"
    LOCAL_PATH = "local_path"
```

### 4.2 Modelos

```python
@dataclass(frozen=True)
class ContextRepositoryRef:
    role: RepoRole
    repo_ref: str
    source_kind: RepoSourceKind
    repo_slug: str
    materialized_path: str | None = None
    has_specs_dir: bool = False

@dataclass(frozen=True)
class SpecContextProject:
    name: str
    state: ContextState
    context_dir: str | None
    specs_dir: str | None
    repos: tuple[ContextRepositoryRef, ...]
    created_at: datetime
    activated_at: datetime | None = None
    updated_at: datetime | None = None

@dataclass(frozen=True)
class Workspace:
    root_path: str
    created_at: datetime
    updated_at: datetime
```

### 4.3 Regras de transição

- `create` produz `INATIVO` com `context_dir = None`.
- `activate` em `INATIVO` calcula `context_dir`, materializa repos e preenche `specs_dir`.
- `deactivate` sempre produz `STANDBY`.
- `delete` nunca opera em `ATIVO`.

---

## 5. Protocolos

### 5.1 `core/protocols/repositories.py`

```python
class WorkspaceRepository(Protocol):
    def get(self) -> Workspace | None: ...
    def save(self, workspace: Workspace) -> None: ...

class SpecContextRepository(Protocol):
    def get_by_name(self, name: str) -> SpecContextProject | None: ...
    def get_active(self) -> SpecContextProject | None: ...
    def list_all(self) -> list[SpecContextProject]: ...
    def save(self, context: SpecContextProject) -> None: ...
    def delete(self, name: str) -> None: ...
```

### 5.2 `core/protocols/git_client.py`

```python
class GitClient(Protocol):
    def clone(self, repo_ref: str, dest: str) -> None: ...
    def is_git_repo(self, path: str) -> bool: ...
    def has_changes(self, repo_path: str) -> bool: ...
    def has_remote(self, repo_path: str) -> bool: ...
    def commit_all(self, repo_path: str, message: str) -> None: ...
    def push(self, repo_path: str) -> None: ...
```

### 5.3 `core/protocols/storage.py`

```python
class ExcelReader(Protocol):
    def read_repos(self, file_path: str) -> list[dict[str, str]]: ...

class PublicAssetManager(Protocol):
    def install_assets(self, target_dir: str, force: bool = False) -> list[str]: ...
```

### 5.4 `core/protocols/runtime_env.py`

```python
class PythonEnvironmentManager(Protocol):
    def ensure_workspace_venv(self, workspace_root: str) -> str: ...
    def python_executable(self, workspace_root: str) -> str: ...
    def pip_executable(self, workspace_root: str) -> str: ...
```

---

## 6. Schema SQLite

```sql
CREATE TABLE IF NOT EXISTS workspaces (
    root_path TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spec_context_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK(state IN ('inativo', 'standby', 'ativo')),
    context_dir TEXT,
    specs_dir TEXT,
    created_at TEXT NOT NULL,
    activated_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spec_context_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id INTEGER NOT NULL REFERENCES spec_context_projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('primary', 'secondary')),
    repo_ref TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK(source_kind IN ('remote_url', 'local_path')),
    repo_slug TEXT NOT NULL,
    materialized_path TEXT,
    has_specs_dir INTEGER NOT NULL DEFAULT 0 CHECK(has_specs_dir IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(context_id, repo_ref)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_one_active_context
ON spec_context_projects(state)
WHERE state = 'ativo';
```

### Observações

- O repositório SQLite precisa montar e desmontar o agregado `SpecContextProject` + `ContextRepositoryRef`.
- `repos.xlsx` não participa de chaves ou integridade do contexto; ele é apenas catálogo consultivo.

---

## 7. Fluxos Críticos

### 7.1 Bootstrap do workspace

1. Garantir `.dadaia/reports`, `.dadaia/src`, `.dadaia/data` e `.dadaia/contexts`.
2. Garantir `.dadaia/tmp/python`, `.dadaia/tmp/json` e `.dadaia/.venv`.
3. Garantir `.claude/` no workspace alvo.
4. Inicializar banco e schema.
5. Instalar assets públicos em `.claude/`, salvo `--skip-assets`.

### 7.1.1 Política de Python e efêmeros

- O bootstrap de `dadaia init` cria `<workspace-root>/.dadaia/.venv/` de forma idempotente.
- Após o bootstrap, comandos Python de automação e scripts auxiliares usam essa venv como caminho canônico.
- Scripts transitórios devem ser escritos em `<workspace-root>/.dadaia/tmp/python/`.
- Dados JSON transitórios devem ser escritos em `<workspace-root>/.dadaia/tmp/json/`.

### 7.2 Ativação do contexto

1. Carregar contexto por nome.
2. Se `INATIVO`, criar `context_dir` e materializar todos os repos.
3. Derivar `specs_dir` do clone gerenciado do repo principal.
4. Emitir warning se o repo principal materializado não tiver `specs/constitution.md` e `specs/SPEC.md`.
5. Persistir a troca de estados: antigo `ATIVO -> STANDBY`, novo `-> ATIVO`.

### 7.3 Deleção do contexto `standby`

1. Iterar apenas repositórios materializados do contexto.
2. Se o repo não tem mudanças, pular commit.
3. Se tem mudanças, `commit_all()`.
4. Se houver remote, `push()`; se não houver remote configurado, falhar explicitamente.
5. Em qualquer falha: manter metadata e arquivos gerenciados, reportando que repositórios anteriores podem já ter sido sincronizados remotamente.
6. Apenas após sucesso completo: apagar `.dadaia/contexts/<name>/` e remover metadata do banco.

### 7.4 Contrato JSON de `show`

```json
{
  "context": {
    "name": "rest-api",
    "state": "ativo",
    "context_dir": "/workspace/.dadaia/contexts/rest-api",
    "specs_dir": "/workspace/.dadaia/contexts/rest-api/repos/dd_chain_explorer/specs",
    "primary_repo": {
      "repo_ref": "git@github.com:org/dd_chain_explorer.git",
      "source_kind": "remote_url",
      "materialized_path": "/workspace/.dadaia/contexts/rest-api/repos/dd_chain_explorer"
    },
    "secondary_repos": []
  },
  "selected_by": "active"
}
```

Quando não houver contexto correspondente:

```json
{
  "context": null,
  "selected_by": "active"
}
```

Quando `show` receber um nome explícito:

```json
{
    "context": {
        "name": "rest-api",
        "state": "standby",
        "context_dir": "/workspace/.dadaia/contexts/rest-api",
        "specs_dir": "/workspace/.dadaia/contexts/rest-api/repos/dd_chain_explorer/specs",
        "primary_repo": {
            "repo_ref": "git@github.com:org/dd_chain_explorer.git",
            "source_kind": "remote_url",
            "materialized_path": "/workspace/.dadaia/contexts/rest-api/repos/dd_chain_explorer"
        },
        "secondary_repos": []
    },
    "selected_by": "name"
}
```

---

## 8. Arquitetura dos Artefatos de Agente

### 8.1 Fluxo oficial

```
dadaia_workspace/public/ (single versioned source)
        ↓ dadaia public install / dadaia init
<workspace>/.claude/ (installed runtime assets)
```

`dadaia-workspace/.claude/` não faz parte do produto e não deve existir.

### 8.2 Artefatos iniciais

- Rule: `dadaia-workspace-sdd-enforcer`
- Rule: `dadaia-workspace-spec-governance`
- Skill: `dadaia-workspace-spec-navigator`
- Skill: `dadaia-workspace-spec-reviewer`
- Workflow markdown: refinamento de specs antes de implementar

### 8.3 Política de overwrite

- `dadaia public install` sem `--force` não sobrescreve arquivos existentes.
- `dadaia init` segue a mesma política padrão.

---

## 9. Estratégia de Testes

### Unit
- `features/workspace/service.py`
- `features/spec_context/service.py`
- `features/repos/service.py`
- `features/public/service.py`

### Integration
- `database.py`
- `sqlite_repositories.py`
- `git_subprocess.py`
- `excel_reader.py`
- `public_assets.py`

### E2E
- `dadaia init`
- `dadaia context create/list/show/activate/deactivate/delete`
- `dadaia repos list`
- `dadaia public install`

---

## 10. Matriz de Rastreabilidade

| Contrato | Cobertura no plano |
|---|---|
| `specs/SPEC.md` FR-001 a FR-012 | seções 2, 6, 7, 8, 9 |
| `features/spec-context-project/SPEC.md` FR-001 a FR-030 | seções 2, 4, 5, 6, 7, 9 |
| `features/agent-rules-skills/SPEC.md` FR-001 a FR-025 | seções 2, 7.1, 7.4, 8, 9 |
| NFRs de performance, segurança e descoberta | seções 2, 7, 8, 9 |
