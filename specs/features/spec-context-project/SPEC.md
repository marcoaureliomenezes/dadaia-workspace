# Spec: Feature — Spec Context Project

> **Status:** Aprovado
> **Versão:** 4.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`
> **Substitui:** v3.0 (descartada integralmente)

---

## Contexto

O **Spec Context Project** é a entidade central do dadaia-workspace. Representa um projeto com specs SDD que o operador quer trabalhar, identificado por um nome, por um repo no whitelist e por um ciclo de vida que gerencia a presença do repo em disco.

### O que mudou da v3.0 para a v4.0

| Aspecto | v3.0 | v4.0 |
|---|---|---|
| Persistência | SQLite (`dadaia.db`) | JSON (`spec_contexts.json`) atômico |
| Repos em disco | Sempre presentes em `repos/` (responsabilidade do usuário) | Gerenciados pelo ciclo de vida: clone em `activate`, remove em `deactivate` |
| Contexto ativo | Único ativo por vez; `active_context.json` aponta para ele | Múltiplos ativos; `primary_context.json` aponta para o primário |
| Seleção de primário | N/A (único ativo = primário implícito) | Explícita via `dadaia context promote` |
| Segurança de remoção | N/A (repos nunca removidos) | Git sync obrigatório antes de remover do disco |
| Whitelist | Consultivo (repos.xlsx) | Obrigatório: create rejeita repo fora do whitelist |
| Scaffold | N/A | Activate cria scaffold mínimo de specs após clone se ausente |
| Reparo de estado | Não havia | `dadaia doctor [--fix]` |

---

## Glossário

| Termo | Definição |
|---|---|
| **Spec Context Project** | Entidade que registra nome + repo + estado + URL de clone |
| **repo_slug** | Nome da pasta em `repos/` onde o repositório vive (também key no whitelist) |
| **repo_url** | URL git do repositório; vem do whitelist ao criar o contexto |
| **specs_dir** | Caminho `repos/<slug>/specs/` dentro do workspace; fonte canônica de specs |
| **Estado `inativo`** | Contexto registrado; repo NÃO está em disco |
| **Estado `ativo`** | Repo clonado em disco; specs disponíveis |
| **`is_primary`** | Flag booleana; somente um contexto pode ter `is_primary=True` ao mesmo tempo |
| **Contexto primário** | O contexto `ativo` com `is_primary=True`; o hook e o ambiente do workspace apontam para ele |
| **`spec_contexts.json`** | Arquivo JSON em `.dadaia/states/`; fonte da verdade de todos os contextos |
| **`primary_context.json`** | Arquivo JSON em `.dadaia/states/`; ponteiro do contexto primário; lido pelo hook |
| **DADAIA_CONTEXT** | Env var que, quando definida, isola uma sessão de agente no contexto nomeado |
| **Whitelist** | `repos.xlsx` em `.dadaia/src/`; define repos válidos para criar contextos |
| **Git sync** | Antes de deactivate: `git add -A && git commit` (se dirty) + `git push` (se tem remote) |
| **Scaffold** | Estrutura mínima de `specs/` criada por `activate` quando o repo clonado não tem `specs/` |

---

## Usuários e Goals

### US-001: Criar um Spec Context Project a partir do whitelist

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia context create <nome> --repo <slug>`, então o sistema verifica que `<slug>` existe no whitelist, obtém `repo_url` do whitelist, e registra o contexto em `inativo` no JSON.
- Dado que `<slug>` não está no whitelist, quando executo `create`, então o sistema rejeita e lista os repos disponíveis do whitelist.
- Dado um nome já existente no JSON, quando executo `create` com o mesmo nome, então o sistema rejeita sem alterar estado.
- Dado que `repos/<slug>/specs/` não existe no disco (em caso de repo já clonado), quando o contexto é criado, o sistema não cria scaffold ainda — scaffold acontece apenas em `activate` se o repo for clonado.

### US-002: Ativar um contexto e garantir presença do repo em disco

**Critérios de Aceite:**
- Dado um contexto `inativo`, quando executo `dadaia context activate <nome>`, então o sistema clona o repo em `repos/<slug>/` se ausente, resolve `specs_dir`, marca `ativo`, e auto-promove a primário se não há primário.
- Dado que o repo já está em disco, quando executo `activate`, então o sistema apenas atualiza o estado sem re-clonar.
- Dado que `repos/<slug>/specs/` não existe após o clone, então o sistema cria o scaffold de specs e emite aviso.
- Dado que não há contexto primário, quando qualquer contexto é ativado, então ele é automaticamente promovido a primário.

### US-003: Promover um contexto a primário

**Critérios de Aceite:**
- Dado um contexto `ativo`, quando executo `dadaia context promote <nome>`, então o sistema remove `is_primary` do contexto primário anterior (se houver), marca o alvo como `is_primary=True`, escreve `primary_context.json` e salva o JSON.
- Dado um contexto `inativo`, quando executo `promote`, então o sistema rejeita com mensagem orientando a executar `activate` primeiro.
- Dado que o contexto já é primário, quando executo `promote`, então o sistema confirma sem alterar estado.

### US-004: Visualizar contextos por saída humana e machine-readable

**Critérios de Aceite:**
- Dado que existem contextos, quando executo `dadaia context list`, então o sistema exibe tabela com `nome`, `estado`, `is_primary` e `repo_slug`.
- Dado um contexto primário, quando executo `dadaia context show --json`, então o sistema retorna JSON com `name`, `state`, `is_primary`, `repo_slug` e `specs_dir`.
- Dado que não existe contexto primário, quando executo `dadaia context show --json`, então o sistema retorna `{"context": null}`.
- Dado `dadaia context show <nome>`, quando o contexto existe, então o sistema exibe detalhes daquele contexto específico.

### US-005: Desativar um contexto e liberar disco

**Critérios de Aceite:**
- Dado um contexto `ativo` e não primário, quando executo `dadaia context deactivate <nome>`, então o sistema executa git sync, remove `repos/<slug>/` e marca `inativo`.
- Dado um contexto `ativo` e primário, quando executo `dadaia context deactivate <nome>`, então o sistema rejeita e orienta a executar `dadaia context promote <outro>` primeiro.
- Dado que o git push falha, quando executo `deactivate`, então o sistema aborta sem alterar estado nem remover o repo.
- Dado que não há remote git, quando executo `deactivate`, então o sistema executa apenas commit (se dirty) e prossegue com a remoção.

### US-006: Deletar um contexto

**Critérios de Aceite:**
- Dado um contexto `inativo`, quando executo `dadaia context delete <nome>`, então o sistema remove a entrada do JSON sem afetar o disco.
- Dado um contexto `ativo`, quando executo `dadaia context delete <nome>`, então o sistema executa o fluxo de deactivate primeiro e, em seguida, remove do JSON.
- Dado um contexto `ativo` e primário, quando executo `delete`, então o sistema rejeita (deve promover outro antes de desativar).
- Dado um nome inexistente, quando executo `delete`, então o sistema retorna erro informativo.

### US-007: Diagnosticar e reparar inconsistências

**Critérios de Aceite:**
- Dado um contexto `ativo` cujo `repos/<slug>/` não está em disco, quando executo `dadaia doctor`, então o sistema reporta o problema.
- Dado `dadaia doctor --fix`, então o sistema re-clona o repo ausente (usando `repo_url` do JSON).
- Dado um `repos/<slug>/` órfão (em disco mas sem contexto correspondente no JSON), quando executo `dadaia doctor`, então o sistema reporta o problema.
- Dado `primary_context.json` com nome diferente do `is_primary` no JSON, quando executo `dadaia doctor`, então o sistema reporta e, com `--fix`, regenera o arquivo.

### US-008: Isolar sessão de agente via env var

**Critérios de Aceite:**
- Dado `DADAIA_CONTEXT=<name>` definido antes de iniciar o agente, quando o hook `UserPromptSubmit` dispara, então o contexto injetado é o do env var, não o de `primary_context.json`.
- A env var não altera `spec_contexts.json` nem `primary_context.json`.

### US-009: Isolar sessão de terminal via CLI ergonômica

**Critérios de Aceite:**
- Dado um operador abrindo uma nova sessão de terminal, quando executa `eval $(dadaia context use <name>)`, então `DADAIA_CONTEXT` fica definida para aquela sessão de shell sem alterar o estado global.
- Dado um nome inexistente, quando executa `dadaia context use <name>`, então o sistema rejeita com erro e lista os contextos disponíveis.
- Dado que múltiplas sessões usam `eval $(dadaia context use <name>)` com nomes diferentes, cada sessão vê apenas seu próprio contexto no hook `UserPromptSubmit`.

---

## Requisitos Funcionais

### Criação e Registro

- FR-001: `dadaia context create <name> --repo <slug>` shall register a context in `inativo` state in `spec_contexts.json`.
- FR-002: `create` shall validate that `<slug>` exists in the whitelist (`repos.xlsx`). If not, reject with error listing available repos.
- FR-003: `create` shall obtain `repo_url` from the whitelist and persist it in the context entry.
- FR-004: `create` shall reject if a context with the same name already exists in the JSON.
- FR-005: `create` shall not clone the repo — cloning happens on `activate`.

### Ativação

- FR-006: `dadaia context activate <name>` shall clone `repo_url` to `repos/<slug>/` if the directory does not exist.
- FR-007: After cloning, if `repos/<slug>/specs/` does not exist, `activate` shall create a minimal scaffold.
- FR-008: `activate` shall mark the context as `ativo` and resolve `specs_dir` in the JSON.
- FR-009: If no context currently has `is_primary=True`, `activate` shall auto-promote the newly activated context.
- FR-010: If a context is already `ativo`, re-activating shall be a no-op (no re-clone).

### Promoção a Primário

- FR-011: `dadaia context promote <name>` shall require the target context to be `ativo`.
- FR-012: `promote` shall atomically remove `is_primary=True` from the current primary (if any) and set it on the target.
- FR-013: `promote` shall write `primary_context.json` atomically after updating the JSON.

### Desativação

- FR-014: `dadaia context deactivate <name>` shall reject if the target context is `is_primary=True`. Error message must instruct user to promote another context first.
- FR-015: Before removing the repo, `deactivate` shall:
  a. Check for uncommitted changes; if found: `git add -A && git commit -m "chore: auto-commit before deactivation"`.
  b. Check for a configured git remote; if found: `git push`. If push fails: abort with error, make no state changes.
- FR-016: After successful git sync, `deactivate` shall remove `repos/<slug>/` from disk.
- FR-017: `deactivate` shall mark the context as `inativo` and clear `activated_at` in the JSON.
- FR-018: If the context has no git remote, git push is skipped; only commit runs (if dirty).

### Deleção

- FR-019: `dadaia context delete <name>` shall reject for a non-existent context.
- FR-020: For an `ativo` (non-primary) context: `delete` shall run the deactivate flow, then remove the entry from the JSON.
- FR-021: For an `ativo` (primary) context: `delete` shall reject. User must promote another context first.
- FR-022: For an `inativo` context: `delete` shall remove the entry from the JSON without touching the disk.

### Visualização

- FR-023: `dadaia context list` shall display a table with `name`, `state`, `is_primary`, and `repo_slug` for all contexts.
- FR-024: `dadaia context show [--json]` without a name shall display the primary context.
- FR-025: `dadaia context show <name> [--json]` shall display the named context.
- FR-026: `--json` output shall include `name`, `state`, `is_primary`, `repo_slug`, and `specs_dir`.
- FR-027: When no primary context exists, `dadaia context show --json` shall return `{"context": null}`.

### Doctor

- FR-028: `dadaia doctor` shall check all consistency invariants listed in `specs/memory/architecture.md` and report issues.
- FR-029: `dadaia doctor --fix` shall auto-repair: re-clone missing repos, remove orphan repos, regenerate or delete `primary_context.json`.

### Persistência JSON

- FR-030: All writes to `spec_contexts.json` shall be atomic: write to `.tmp` file then `os.replace()`.
- FR-031: All writes to `primary_context.json` shall be atomic.
- FR-032: `spec_contexts.json` shall include a `version` field for future schema evolution.

### Hook e Isolamento de Sessão

- FR-033: `ctx-inject.sh` shall check `DADAIA_CONTEXT` env var before reading `primary_context.json`. If set, output `[<name>]` (context name found) or `[<name>] WARNING: specs not found` (context name set but specs dir absent). If not set, read `primary_context.json` and output `[<name>]` when found, or `[context: none] — run: eval $(dadaia context use <name>)` when absent.
- FR-034: Session-level override via `DADAIA_CONTEXT` shall not modify `spec_contexts.json` or `primary_context.json`.
- FR-034-B: `dadaia context show --json` shall always read from `spec_contexts.json` and `primary_context.json`, ignoring the `DADAIA_CONTEXT` environment variable. The env var is exclusive to `ctx-inject.sh`.

### Isolamento via CLI

- FR-037: `dadaia context use <name>` shall validate that the context exists in `spec_contexts.json`, then write `export DADAIA_CONTEXT=<name>` to stdout. It shall not modify `spec_contexts.json` or `primary_context.json`. When the context does not exist, it shall exit with an error message listing available contexts.

### CLI Help

- FR-035: `dadaia context --help` shall list exactly: `create`, `list`, `show`, `activate`, `deactivate`, `promote`, `delete`, and `use`.
- FR-036: Each subcommand shall have dedicated help text documenting preconditions and expected outcomes.

---

## Requisitos Não-Funcionais

- NFR-001: [Atomicidade] Todas as escritas em `spec_contexts.json` e `primary_context.json` devem ser atômicas. Estado corrompido por escrita parcial é proibido.
- NFR-002: [Integridade de dados] `deactivate` nunca remove o repo sem git sync bem-sucedido (ou ausência de remote). Dados não são perdidos.
- NFR-003: [Segurança Operacional] O produto nunca deleta ou muta conteúdo em `repos/<slug>/` fora do fluxo explícito de `deactivate`.
- NFR-004: [Feedback] Cada comando emite confirmação, warning ou erro legível.
- NFR-005: [Descoberta] O contrato JSON de `dadaia context show --json` é estável para uso por agentes.
- NFR-006: [Reparabilidade] O estado em `spec_contexts.json` pode ser totalmente verificado e reparado por `dadaia doctor` sem recriar o workspace.

---

## Modelo de Domínio (v4.0)

### `ContextState` (enum)

```python
class ContextState(StrEnum):
    INATIVO = "inativo"
    ATIVO   = "ativo"
```

### `SpecContextProject` (Python dataclass)

```python
@dataclass(frozen=True)
class SpecContextProject:
    name: str
    state: ContextState
    is_primary: bool
    repo_slug: str
    repo_url: str
    specs_dir: Path | None
    created_at: str           # ISO 8601
    activated_at: str | None  # ISO 8601; None quando inativo
```

### `spec_contexts.json` (formato canônico)

```json
{
  "version": "1",
  "contexts": [
    {
      "name": "dadaia-workspace",
      "state": "ativo",
      "is_primary": true,
      "repo_slug": "dadaia-workspace",
      "repo_url": "https://github.com/marcoaureliomenezes/dadaia-workspace.git",
      "specs_dir": "/workspace/repos/dadaia-workspace/specs",
      "created_at": "2026-05-09T10:00:00Z",
      "activated_at": "2026-05-09T10:00:00Z"
    }
  ]
}
```

### `primary_context.json` (formato canônico)

```json
{
  "name": "dadaia-workspace",
  "repo_slug": "dadaia-workspace",
  "specs_dir": "/workspace/repos/dadaia-workspace/specs"
}
```

---

## State Machine (v4.0)

```
create
  └──────────▶ INATIVO (is_primary=False)
                  │
                  │ activate (clone se ausente)
                  ▼
               ATIVO (is_primary=False)
                  │
                  │ promote
                  ▼
               ATIVO (is_primary=True) ──▶ primary_context.json escrito
                  │
                  │ deactivate (git sync + remove repo)
                  │ [ERRO se is_primary=True]
                  ▼
               INATIVO (is_primary=False) ──▶ primary_context.json NÃO apagado
                                               (só apagado se promoted out)

INATIVO ────── delete ──▶ [remove do JSON]
ATIVO (não primary) ── delete ──▶ [deactivate + remove do JSON]
ATIVO (primary) ─── delete ──▶ ERRO: promova outro primeiro
```

---

## Contrato JSON v4.0 (`dadaia context show --json`)

Contexto primário ativo:
```json
{
  "name": "dadaia-workspace",
  "state": "ativo",
  "is_primary": true,
  "repo_slug": "dadaia-workspace",
  "specs_dir": "/workspace/repos/dadaia-workspace/specs"
}
```

Sem contexto primário:
```json
{
  "context": null
}
```

---

## Scaffold de Specs

Quando `activate` é chamado para um repo sem `specs/`, o sistema cria:

```
repos/<slug>/specs/
  constitution.md     ← template mínimo
  memory/
    product.md
    architecture.md
    tech-stack.md
  foundation/
    SPEC.md
  SPEC.md
```

O conteúdo do scaffold vem de `dadaia_workspace/public/scaffold/`.

---

## Fora de Escopo (v4.0)

- Repositórios secundários por contexto
- Sincronização bidirecional automática de specs entre repositórios
- Branch orchestration
- Renomear contextos
- Múltiplos primários simultâneos
- Estado `standby` ou `arquivado`
- Ops granulares de whitelist via CLI (adicionar/remover repos ao xlsx)
