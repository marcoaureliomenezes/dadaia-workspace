# Spec: Feature — Spec Context Project

> **Status:** Aprovado  
> **Versão:** 1.1  
> **Autor:** Marco Menezes  
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`

---

## Contexto

O **Spec Context Project** é a entidade central do dadaia-workspace. Ele representa um foco de trabalho SDD associado a um repositório principal e a zero ou mais repositórios secundários. O contrato desta feature precisa resolver quatro pontos ao mesmo tempo: lifecycle claro, materialização segura em disco, descoberta confiável para agentes e deleção implementável sem comportamentos implícitos.

---

## Glossário

| Termo | Definição |
|---|---|
| **Spec Context Project** | Entidade de negócio que organiza um contexto de trabalho SDD |
| **Repositório principal** | Repositório primário do contexto; é dele que sai o `specs_dir` ativo |
| **Repositório secundário** | Repositório adicional afetado pelo mesmo contexto |
| **Repo reference (`repo_ref`)** | Referência de origem do repositório; pode ser URL git ou caminho local de um repositório git |
| **Materialização gerenciada** | Clone gerenciado em `.dadaia/contexts/<name>/repos/` usado pelo contexto |
| **Estado `inativo`** | Contexto existe no banco, mas ainda não possui materialização gerenciada |
| **Estado `standby`** | Contexto possui materialização gerenciada, porém não é o foco atual |
| **Estado `ativo`** | Contexto atual de desenvolvimento; existe no disco e é o único foco ativo |

---

## Usuários e Goals

### US-001: Criar um contexto sem materializar imediatamente

- **Como** engenheiro iniciando uma mudança multi-repositório
- **Quero** registrar o contexto antes de ativá-lo
- **Para** poder preparar o trabalho sem já criar clones e side effects em disco

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia context create minha-feature --repo <repo-ref>`, então o sistema cria o contexto em `inativo`
- Dado `--secondary <repo-ref>`, quando o comando é executado, então o sistema registra os repositórios secundários no mesmo contexto
- Dado um nome já existente, quando executo `create` com o mesmo nome, então o sistema rejeita a operação sem alterar estado persistido

### US-002: Visualizar contexto por saída humana e machine-readable

- **Como** engenheiro ou agente
- **Quero** listar e inspecionar um contexto individual
- **Para** entender rapidamente o estado atual e automatizar decisões com segurança

**Critérios de Aceite:**
- Dado que existem contextos, quando executo `dadaia context list`, então o sistema exibe uma tabela com nome, estado e repo principal
- Dado um contexto ativo, quando executo `dadaia context show --json`, então o sistema retorna JSON estável com `name`, `state`, `context_dir`, `specs_dir`, `primary_repo` e `secondary_repos`
- Dado que não existe contexto ativo, quando executo `dadaia context show --json`, então o sistema retorna resposta estável informando ausência de contexto ativo

### US-003: Ativar e trocar de contexto com materialização segura

- **Como** engenheiro começando a trabalhar em um contexto
- **Quero** ativá-lo com um único comando
- **Para** que o contexto fique materializado e pronto para humanos e agentes

**Critérios de Aceite:**
- Dado um contexto `inativo`, quando executo `dadaia context activate <nome>`, então o sistema cria a materialização gerenciada do contexto, valida a estrutura mínima de specs do repo principal e move o contexto para `ativo`
- Dado um contexto `standby`, quando executo `dadaia context activate <nome>`, então o sistema reaproveita a materialização existente e move o contexto para `ativo`
- Dado que existe outro contexto `ativo`, quando executo `activate <nome>`, então o sistema desativa o atual para `standby` e ativa o novo em uma transição atômica de estado do workspace

### US-004: Desativar o contexto atual

- **Como** engenheiro pausando o trabalho
- **Quero** desativar o contexto ativo
- **Para** preservar a materialização gerenciada sem mantê-lo como foco atual

**Critérios de Aceite:**
- Dado um contexto `ativo`, quando executo `dadaia context deactivate`, então o sistema move o contexto para `standby`
- Dado que nenhum contexto está ativo, quando executo `dadaia context deactivate`, então o sistema responde com erro informativo e não altera nada

### US-005: Deletar um contexto de forma implementável e segura

- **Como** engenheiro concluindo ou descartando um contexto
- **Quero** removê-lo sem apagar repositórios de origem fora da área gerenciada
- **Para** evitar perda de dados e comportamento implícito perigoso

**Critérios de Aceite:**
- Dado um contexto `inativo`, quando executo `dadaia context delete <nome>`, então o sistema remove apenas a metadata do banco
- Dado um contexto `standby`, quando executo `dadaia context delete <nome>`, então o sistema tenta sincronizar os repositórios materializados do contexto e, se todas as etapas obrigatórias tiverem sucesso, remove a materialização gerenciada e a metadata do banco
- Dado um contexto `ativo`, quando executo `dadaia context delete <nome>`, então o sistema rejeita a operação e orienta a executar `dadaia context deactivate` antes
- Dado que uma sincronização falha no meio da deleção, quando o comando termina, então a metadata e a materialização local do contexto permanecem intactas e o sistema informa que efeitos remotos anteriores podem já ter ocorrido

### US-006: Ajustar repositórios secundários de um contexto existente

- **Como** engenheiro refinando o escopo de uma mudança
- **Quero** adicionar ou remover repositórios secundários
- **Para** manter o contexto aderente ao trabalho real sem recriar tudo

**Critérios de Aceite:**
- Dado um contexto existente, quando executo `dadaia context add-repo <nome> --repo <repo-ref>`, então o sistema adiciona um repositório secundário ao contexto
- Dado que o `repo_ref` já existe como primário ou secundário, quando executo `add-repo`, então o sistema retorna aviso e não duplica a associação
- Dado um contexto existente, quando executo `dadaia context remove-repo <nome> --repo <repo-ref>`, então o sistema remove a associação secundária
- Dado que o `repo_ref` corresponde ao repositório principal, quando executo `remove-repo`, então o sistema rejeita a operação

### US-007: Descoberta completa da CLI do contexto

- **Como** agente de IA trabalhando em um dadaia-workspace
- **Quero** descobrir toda a superfície de contexto via help e JSON estável
- **Para** operar o workspace sem parsing frágil ou documentação externa

**Critérios de Aceite:**
- Dado qualquer terminal com dadaia instalado, quando executo `dadaia --help`, então a CLI lista `init`, `context`, `repos` e `public`
- Quando executo `dadaia context --help`, então a CLI lista exatamente os subcomandos `create`, `list`, `show`, `activate`, `deactivate`, `delete`, `add-repo` e `remove-repo`
- Cada subcomando fornece `--help` próprio e `show` fornece também `--json`

---

## Requisitos Funcionais

### Criação e Registro
- FR-001: The system shall provide `dadaia context create <name> --repo <repo-ref>` to create a new Spec Context Project in state `inativo`.
- FR-002: Where one or more `--secondary <repo-ref>` options are included, the system shall register secondary repositories during context creation.
- FR-003: If a context name already exists, then the system shall reject creation without changing persisted data.

### Visualização e Descoberta
- FR-004: The system shall provide `dadaia context list` to display all contexts in a formatted table showing at minimum `name`, `state`, and primary repository.
- FR-005: The system shall provide `dadaia context show [<name>]` where omitting `<name>` means “show the current active context”.
- FR-006: Where `--json` is included in `dadaia context show`, the system shall return a stable machine-readable representation of the context.

### Ativação e Desativação
- FR-007: The system shall provide `dadaia context activate <name>` to transition a context to `ativo`.
- FR-008: When `activate` is called for an `inativo` context, the system shall materialize managed clones for the context in `.dadaia/contexts/<name>/repos/` before marking it `ativo`.
- FR-009: When `activate` is called and another context is already `ativo`, the system shall transition the currently active context to `standby` and the requested one to `ativo` as a single atomic workspace-state transition.
- FR-010: The system shall provide `dadaia context deactivate` to transition the current active context to `standby`.
- FR-011: If `deactivate` is called while no context is `ativo`, then the system shall report an error and make no state changes.
- FR-012: The system shall guarantee that at most one context is in state `ativo`, enforced at the database level.

### Materialização e Specs
- FR-013: The system shall treat `repo_ref` as either a git URL or a local git repository path.
- FR-014: When materializing a context from a local git repository path, the system shall clone that repository into the managed context directory rather than mutate the source path directly.
- FR-015: The system shall derive `specs_dir` from the managed clone of the primary repository.
- FR-016: If the managed primary repository does not contain `specs/constitution.md` and `specs/SPEC.md`, the system shall emit a warning and keep the context usable, but mark the spec navigation capability as incomplete.

### Deleção
- FR-017: The system shall provide `dadaia context delete <name>` to remove a Spec Context Project.
- FR-018: When deleting a context in `inativo`, the system shall remove only the database metadata.
- FR-019: When deleting a context in `standby`, the system shall attempt sync steps against each materialized repository associated with the context before removing managed files and database metadata.
- FR-020: If a materialized repository has no changes to commit, the system shall skip commit creation for that repository and continue the deletion flow.
- FR-021: If any required sync step fails while deleting a `standby` context, the system shall keep local metadata and managed files intact, report the failure, and warn that earlier repositories may already have been synchronized remotely.
- FR-022: If the context is `ativo`, then `delete` shall be rejected.
- FR-023: Delete operations shall remove only files inside the managed context directory under `.dadaia/contexts/`.

### Gestão de Repositórios
- FR-024: The system shall provide `dadaia context add-repo <name> --repo <repo-ref>` to add a secondary repository.
- FR-025: If the same `repo_ref` is already associated to the context, then `add-repo` shall warn and make no changes.
- FR-026: The system shall provide `dadaia context remove-repo <name> --repo <repo-ref>` to remove a secondary repository.
- FR-027: If the target repository is the primary repository, then `remove-repo` shall reject the operation.

### CLI Help
- FR-028: The `dadaia --help` output shall list the frozen top-level surface: `init`, `context`, `repos`, and `public`.
- FR-029: The `dadaia context --help` output shall list exactly the eight frozen subcommands of the context surface.
- FR-030: Each context subcommand shall provide dedicated help text, and `show` shall document the JSON automation contract.

---

## Requisitos Não-Funcionais

- NFR-001: [Atomicidade de Estado] State transitions in the workspace database shall be atomic for `activate` and `deactivate`.
- NFR-002: [Segurança Operacional] Source repositories referenced by `repo_ref` shall never be deleted by the product.
- NFR-003: [Descoberta] The JSON contract used by agents shall not depend on parsing a human-formatted table.
- NFR-004: [Feedback] Every command shall emit a human-readable confirmation, warning or error.

---

## State Machine (Referência Visual)

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

INATIVO ──── delete ──▶ [remove metadata]
STANDBY ──── delete ──▶ [sync managed repos → remove managed files → remove metadata]
ATIVO ───── delete ──▶ ERRO
```

---

## Fora de Escopo (v1.0)

- Renomear contextos via `update`
- Estado `arquivado`
- Alteração do repositório principal após criação
- Branch orchestration e merge automation
- Sincronização automática de specs entre múltiplos repositórios

---

## Questões Abertas

*Nenhuma bloqueante após o congelamento desta superfície de CLI e desta state machine.*
