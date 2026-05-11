# Spec: dadaia-workspace

> **Status:** Aprovado
> **Versão:** 3.0
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/memory/product.md`, `specs/foundation/SPEC.md`

---

## Contexto

dadaia-workspace é o produto que organiza o desenvolvimento AI-assisted em torno de um workspace, de Spec Context Projects e de artefatos de agente instaláveis para Claude Code, OpenCode e Codex. O sistema precisa ser simples de descobrir pela CLI, seguro para evoluir com SDD e consistente o suficiente para que agentes não tomem decisões arquiteturais por conta própria.

O runtime workspace vive fora do repositório da biblioteca. No setup inicial, o produto cria o template canônico em `<workspace-root>/.dadaia/`, gera staging em `.dadaia/agentic/`, instala skills universais em `.agents/skills/` e projeta artefatos para `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md` conforme as capacidades de cada runtime.

O estado de todos os Spec Context Projects é gerenciado por `spec_contexts.json`. Repositórios são clonados automaticamente ao ativar um contexto e removidos (após git sync obrigatório) ao desativá-lo. Apenas os repos dos contextos ativos existem em disco.

---

## Usuários e Goals

### US-001: Bootstrap de um workspace AI-native

- **Como** engenheiro iniciando um novo workspace
- **Quero** executar um único bootstrap inicial
- **Para** que o diretório fique pronto para trabalho com `.dadaia/`, `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `AGENTS.md` e configs de runtime configuradas

**Critérios de Aceite:**
- Dado um diretório ainda não inicializado, quando executo `dadaia init`, então o sistema cria o template canônico de `.dadaia/` com `agentic/`, `scripts/`, `states/`, `src/`, `tmp/python/`, `tmp/json/`, `.venv/`, copia scripts para `.dadaia/scripts/`, copia `repos.xlsx` para `.dadaia/src/`, executa staging de assets públicos, instala projeções para `.agents/`, `.claude/`, `.codex/`, `.opencode/`, cria `AGENTS.md`, gera configs suportadas, e exibe confirmação clara.
- Dado um workspace parcialmente inicializado, quando executo `dadaia init`, então o sistema reconcilia os paths mínimos ausentes sem destruir conteúdo já existente.

### US-002: Criar um Spec Context Project a partir do whitelist

- **Como** engenheiro iniciando trabalho em um projeto
- **Quero** criar um Spec Context Project associado a um repo do whitelist
- **Para** registrar esse projeto no workspace sem ainda precisar clonar o repo

**Critérios de Aceite:**
- Dado um repo válido no whitelist, quando executo `dadaia context create <nome> --repo <slug>`, então o sistema registra o contexto em `inativo` no JSON (sem clonar o repo).
- Dado um slug não presente no whitelist, quando executo `create`, então o sistema rejeita com erro claro listando os repos disponíveis.
- Dado um nome já existente no JSON, quando executo `create` com o mesmo nome, então o sistema rejeita sem alterar estado.

### US-003: Ativar um contexto e trabalhar com o repo

- **Como** engenheiro pronto para trabalhar em um projeto
- **Quero** ativar um contexto
- **Para** que o repo seja clonado localmente e o ambiente do workspace aponte para as specs desse projeto

**Critérios de Aceite:**
- Dado um contexto `inativo`, quando executo `dadaia context activate <nome>`, então o sistema clona o repo em `repos/<slug>/` (se ausente), marca o contexto como `ativo`, e auto-promove a primário se não há primário.
- Dado que o repo já existe em disco, quando executo `activate`, então o sistema apenas atualiza o estado sem re-clonar.
- Dado que `repos/<slug>/specs/` não existe após o clone, então o sistema cria o scaffold de specs e emite aviso.

### US-004: Promover um contexto a primário

- **Como** engenheiro com múltiplos contextos ativos
- **Quero** designar qual é o contexto primário
- **Para** que o hook de agente injete as specs corretas automaticamente

**Critérios de Aceite:**
- Dado um contexto `ativo`, quando executo `dadaia context promote <nome>`, então o sistema remove `is_primary` do anterior (se houver), marca o novo como primário e escreve `primary_context.json`.
- Dado um contexto `inativo`, quando executo `promote`, então o sistema rejeita com erro orientando a ativar primeiro.

### US-005: Desativar um contexto e liberar espaço em disco

- **Como** engenheiro concluindo trabalho em um projeto
- **Quero** desativar um contexto
- **Para** que o repo seja sincronizado e removido do disco, liberando espaço

**Critérios de Aceite:**
- Dado um contexto `ativo` e não primário, quando executo `dadaia context deactivate <nome>`, então o sistema executa commit+push (se necessário), remove `repos/<slug>/` e marca o contexto como `inativo`.
- Dado um contexto `ativo` e primário, quando executo `deactivate`, então o sistema rejeita e orienta a executar `dadaia context promote <outro>` primeiro.
- Dado que o git push falha, quando executo `deactivate`, então o sistema aborta sem remover o repo do disco.

### US-006: Descoberta confiável por humanos e agentes

- **Como** agente de IA ou engenheiro
- **Quero** saber qual contexto é o primário sem precisar invocar a CLI explicitamente
- **Para** operar o sistema sem depender de documentação externa

**Critérios de Aceite:**
- Dado um runtime com hook de prompt suportado, quando o agente recebe uma mensagem, então o contexto primário é injetado por hook.
- Dado um runtime sem hook de prompt suportado, quando o agente inicia uma sessão, então `AGENTS.md` instrui a descoberta explícita via `dadaia context list` e `dadaia context show --json`.
- Dado `dadaia context show --json`, quando existe um contexto primário, então o sistema retorna saída machine-readable com `name`, `state`, `is_primary`, `repo_slug` e `specs_dir`.
- Dado que não existe contexto primário, quando executo `dadaia context show --json`, então o sistema retorna `{"context": null}`.

### US-007: Gerenciar cursos de aprendizagem da dadaia-academy

- **Como** usuário do dadaia-workspace
- **Quero** criar e gerenciar cursos a partir do catálogo de módulos do pacote
- **Para** aprender sobre o workspace e práticas SDD diretamente no meu ambiente de trabalho

**Critérios de Aceite:**
- Dado um módulo válido (1–6), quando executo `dadaia academy create <slug> --module <n>`, então o sistema copia o módulo para `.dadaia/academy/<slug>/` e registra o curso em `academy.json`.
- Dado cursos existentes, quando executo `dadaia academy list`, então o sistema exibe tabela com slug, name e module_name.
- Dado um slug existente, quando executo `dadaia academy delete <slug>`, então o sistema remove o diretório do disco e a entrada do JSON.
- Dado um curso existente e módulo válido, quando executo `dadaia academy update <slug> --module <n>`, então o sistema substitui o conteúdo pelo novo módulo.

### US-008: Instalar e atualizar artefatos de agente

- **Como** usuário do dadaia-workspace
- **Quero** staged assets e projeções de rules, skills, agents, commands, hooks e configs distribuídos pelo pacote
- **Para** que meu workspace fique pronto para SDD sem configuração manual

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia public stage`, então o sistema materializa os artefatos distribuídos em `.dadaia/agentic/` e escreve manifest com hashes.
- Dado um workspace inicializado, quando executo `dadaia public install --target all`, então o sistema instala as projeções suportadas em `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md`.
- Dado que o workspace já possui artefatos customizados, quando executo `dadaia public install` sem força, então o sistema não sobrescreve arquivos existentes.

### US-009: Consultar o catálogo de repositórios disponíveis

- **Como** engenheiro criando um novo contexto
- **Quero** consultar os repositórios do whitelist
- **Para** escolher qual repo usar sem memorizar slugs ou URLs

**Critérios de Aceite:**
- Dado que o catálogo contém entradas, quando executo `dadaia repos list`, então o sistema exibe a lista com nome, URL e descrição.
- Dado que o catálogo está vazio, quando executo `dadaia repos list`, então o sistema informa claramente.

### US-010: Diagnosticar e reparar estado do workspace

- **Como** engenheiro com estado potencialmente corrompido
- **Quero** diagnosticar e reparar o workspace automaticamente
- **Para** restaurar a consistência sem recriar o workspace do zero

**Critérios de Aceite:**
- Dado um workspace com state inconsistente, quando executo `dadaia doctor`, então o sistema lista todos os problemas encontrados.
- Dado `dadaia doctor --fix`, então o sistema repara automaticamente o que conseguir (re-clone, remove orphan repos, regenera primary_context.json).

### US-011: Isolar contexto por sessão de agente

- **Como** operador com múltiplos projetos ativos simultaneamente
- **Quero** trabalhar em projeto A em um terminal e projeto B em outro sem conflito
- **Para** paralelizar trabalho sem que sessões interfiram entre si

**Critérios de Aceite:**
- Dado a env var `DADAIA_CONTEXT=<name>` definida antes de iniciar uma sessão de agente, quando o hook dispara, então aquela sessão usa o contexto indicado pela env var, ignorando `primary_context.json`.

### US-012: Exportar o workspace para migração de VPS

- **Como** operador migrando para um novo VPS
- **Quero** exportar todo o estado durável do workspace em um único artefato portátil
- **Para** restaurar o ambiente sem perda de state (contexts, academy, scripts, hooks, configs) num novo servidor

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia export`, então o sistema gera `.dadaia/dist/workspace-<timestamp>.tar.gz` incluindo `.dadaia/states/`, `.dadaia/academy/`, `.dadaia/scripts/`, `.dadaia/src/`, `.dadaia/agentic/manifest.json`, `CLAUDE.md`, `AGENTS.md`, `opencode.json`, `.agents/skills/`, `.claude/`, `.codex/`, `.opencode/` e `mnt/` (se existir).
- Dado `dadaia export`, então o artefato NUNCA contém `*.env`, `.dadaia/.venv/`, `.dadaia/tmp/`, ou `repos/`.
- Dado `dadaia export --list`, quando executo, então o sistema imprime o manifest JSON em stdout sem criar arquivo.
- Dado `dadaia export --exclude-mnt`, quando executo, então `mnt/` é omitido do artefato.
- Dado `dadaia export --include-reports`, quando executo, então `.dadaia/reports/` é adicionado ao artefato.
- Dado extrair o artefato em `/home/ubuntu/workspace/` num novo VPS e executar `dadaia init`, então o workspace é restaurado sem recriar do zero.

---

## Requisitos Funcionais

- FR-001: The system shall provide `dadaia init` to bootstrap the workspace. The command is idempotent and creates the following canonical structure:

  | Path | Type | Notes |
  |---|---|---|
  | `.dadaia/.venv/` | Durable | Isolated Python environment |
  | `.dadaia/academy/` | Durable | Working copies of academy courses |
  | `.dadaia/reports/architect-agent-review/` | Durable | architect-agent output dir |
  | `.dadaia/reports/specs-sdd-review/` | Durable | product-auditor-agent output dir |
  | `.dadaia/reports/bugs/soft-engineer-report/` | Durable | soft-engineer-agent bug reports |
  | `.dadaia/scripts/` + `ctx-inject.sh` | Durable | Hook script, copied from package |
  | `.dadaia/src/` + `repos.xlsx` | Durable | Whitelist, copied from package |
  | `.dadaia/states/` | Durable | JSON state directory |
  | `.dadaia/states/academy.json` | Durable | Empty course registry `{"version":"1","courses":[]}` |
  | `.dadaia/tmp/python/` | Ephemeral | Transient agent scripts |
  | `.dadaia/tmp/json/` | Ephemeral | Transient structured outputs |
  | `.dadaia/agentic/` | Generated | Staged public assets with manifest |
  | `.agents/skills/` | Generated projection | Universal skills |
  | `.claude/` + `settings.json` | Generated projection | Claude Code assets and supported hooks |
  | `.codex/` | Generated projection | Codex config, hooks, rules |
  | `.opencode/` + `opencode.json` | Generated projection | OpenCode assets and instructions |
  | `AGENTS.md` | Generated projection | Universal AI instructions |

  **Does not create** `.dadaia/data/` (SQLite removed). Feature specs (agents FR-009, academy FR-019) that reference init behavior defer to this table.
- FR-002: The system shall persist all Spec Context Project state in `.dadaia/states/spec_contexts.json` using atomic writes.
- FR-003: The system shall provide a `dadaia context` command group with subcommands: `create`, `list`, `show`, `activate`, `deactivate`, `promote`, `delete`, and `use`.
- FR-004: The system shall provide `dadaia repos list` for consulting the workspace repository whitelist.
- FR-005: The system shall provide `dadaia public stage`, `dadaia public install --target all|claude|codex|opencode|agents [--force]`, and `dadaia public doctor` for staging, projecting, and diagnosing distributed agent artifacts.
- FR-006: When a context is activated and `repos/<slug>/` does not exist, the system shall clone the repo using `git clone <repo_url>`.
- FR-007: When a context is deactivated, the system shall perform mandatory git sync (commit if dirty, push if has remote) before removing `repos/<slug>/`. If git sync fails, deactivate shall abort.
- FR-008: The system shall guarantee that at most one Spec Context Project has `is_primary=True` at any time.
- FR-009: When `activate` is called and no context is currently primary, the system shall auto-promote the newly activated context to primary.
- FR-010: The system shall prevent `deactivate` on a primary context; the user must run `dadaia context promote <other>` first.
- FR-011: The system shall provide `dadaia context promote <name>` to designate a new primary context, transferring `is_primary` atomically.
- FR-012: When `promote` is called, the system shall write `primary_context.json` atomically.
- FR-013: The system shall provide `dadaia context show [<name>] [--json]`. Without a name, it displays the current primary context. With a name, it displays that specific context.
- FR-014: The `--json` output shall include `name`, `state`, `is_primary`, `repo_slug`, and `specs_dir`.
- FR-015: The system shall provide `dadaia doctor [--fix]` to diagnose and optionally repair inconsistencies between `spec_contexts.json` and the disk state.
- FR-016: The context injection script shall check `DADAIA_CONTEXT` env var first; if set, use `repos/<DADAIA_CONTEXT>/specs/` as the active specs path, ignoring `primary_context.json`. It shall be wired only into runtimes whose hook model supports the behavior.
- FR-017: When `activate` clones a repo and `repos/<slug>/specs/` does not exist after cloning, the system shall create a minimal scaffold specs structure and emit a warning.
- FR-018: `create` shall validate that the requested `repo_slug` exists in the whitelist (`repos.xlsx`); if not, the command shall reject with an error listing available repos.
- FR-019: All commands shall provide self-sufficient help text for human and agent use.
- FR-020: If a CLI invocation fails, the system shall emit an error message identifying the failed capability, the relevant resource, and the next safe recovery action.
- FR-021: The system shall treat `<workspace-root>/.dadaia/.venv/` as the isolated Python environment for workspace automation after bootstrap.
- FR-022: The system shall reserve `.dadaia/tmp/python/` and `.dadaia/tmp/json/` for ephemeral agent artifacts.
- FR-023: The system shall never delete or mutate content in `repos/<slug>/` except as part of an explicit `deactivate` or `delete` lifecycle operation.
- FR-024: The system shall provide 4 specialized agent files in `dadaia_workspace/public/agents/` and project them to each supported runtime according to that runtime's native agent model.
- FR-025: The system shall provide a `dadaia-grill-me` skill at `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`, installed universally to `<workspace-root>/.agents/skills/dadaia-grill-me/` and mirrored to runtime-specific skill directories when supported.
- FR-026: `dadaia init` shall create academy-related directories: `.dadaia/academy/` and `.dadaia/states/academy.json` (empty), and report subdirectories: `.dadaia/reports/architect-agent-review/`, `.dadaia/reports/specs-sdd-review/`, `.dadaia/reports/bugs/soft-engineer-report/`.
- FR-027: `dadaia academy create <slug> --module <n>` shall copy the knowledge_basis module to `.dadaia/academy/<slug>/` and register the course atomically in `academy.json`.
- FR-028: `dadaia academy delete <slug>` shall remove `.dadaia/academy/<slug>/` from disk and its entry from `academy.json`.
- FR-029: `dadaia academy update <slug> --module <n>` shall replace `.dadaia/academy/<slug>/` with the selected module and update `academy.json` atomically.
- FR-030: `dadaia academy list` shall display all courses in `academy.json` with slug, name, and module_name.
- FR-031: The system shall provide a `dadaia academy` command group with subcommands: `list`, `create`, `delete`, `update`, and `modules`.
- FR-032: The system shall provide `dadaia export` to generate a portable `.tar.gz` archive of all durable workspace state to `.dadaia/dist/workspace-<timestamp>.tar.gz` by default. Full behavior is specified in `specs/features/workspace-export/SPEC.md`.
- FR-033: `dadaia export` shall support flags: `--output <dir>` (alternate output path), `--include-reports` (include `.dadaia/reports/`), `--exclude-mnt` (omit `mnt/`), and `--list` (dry-run: print manifest without creating file). The archive shall never include `*.env` files, `.dadaia/.venv/`, `.dadaia/tmp/`, or `repos/`.

---

## Requisitos Não-Funcionais

- NFR-001: [Performance] The CLI shall respond to non-networked commands within 1 second under normal conditions.
- NFR-002: [Usabilidade] The `--help` and `--json` surfaces shall be stable enough for autonomous agent usage.
- NFR-003: [Portabilidade] The system shall run on Linux and macOS with Python 3.12+ and git installed.
- NFR-004: [Segurança] The system shall never persist credentials, tokens or secrets inside workspace state or agent artifacts.
- NFR-005: [Integridade] Deactivation shall never result in data loss. Git sync failure must abort the operation, leaving the repo in place.
- NFR-006: [Diagnosabilidade] Common CLI failures shall be understandable enough for an autonomous agent to select a safe recovery path.
- NFR-007: [Reparabilidade] The workspace state shall be fully diagnosable and repairable by `dadaia doctor` without recreating the workspace.

---

## Fora de Escopo (v3.0)

- GUI ou interface web
- Repositórios secundários por contexto
- Sincronização bidirecional automática de specs entre repositórios
- Tracking de progresso por curso (exercícios completados, notas pessoais)
- Múltiplos primários simultâneos
- Geração de conteúdo de curso via LLM API pelo CLI Python
- Orquestração automática entre agentes especializados

---

## Questões Abertas

*Nenhuma bloqueante. Questões residuais devem ser registradas em `z_bug_specs.md`.*
