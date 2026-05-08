# Spec: dadaia-workspace

> **Status:** Aprovado  
> **Versão:** 1.3  
> **Autor:** Marco Menezes  
> **Referências:** `specs/constitution.md`, `specs/memory/product.md`, `specs/foundation/SPEC.md`

---

## Contexto

dadaia-workspace é o produto que organiza o desenvolvimento AI-assisted em torno de um workspace, de Spec Context Projects e de artefatos de agente instaláveis. O sistema precisa ser simples de descobrir pela CLI, seguro para evoluir com SDD e consistente o suficiente para que agentes não tomem decisões arquiteturais por conta própria.

O runtime workspace do produto vive fora do repositório da biblioteca. No setup inicial, o produto deve criar o template canônico em `<workspace-root>/.dadaia/` e preparar `.claude/` para uso de agentes. Os artefatos versionados do produto vivem em `dadaia_workspace/public/` e são sempre extraídos para a `.claude/` na raiz do workspace do usuário.

Dentro do runtime do usuário, o produto também precisa sustentar uma camada de aprendizagem prática chamada **Dadaia Academy**. O material base e os cursos vivos dessa feature pertencem a `<workspace-root>/.dadaia/academy/`. O fluxo de geração da academy será exposto por slash command de agente, preservando a CLI congelada do binário `dadaia`.

Esta spec define o comportamento do produto como um todo. Regras de arquitetura e detalhes por domínio ficam nas specs de `foundation/` e `features/`.

---

## Usuários e Goals

### US-001: Bootstrap de um workspace AI-native

- **Como** engenheiro iniciando um novo workspace
- **Quero** executar um único bootstrap inicial
- **Para** que o diretório fique pronto para trabalho com `.dadaia/`, `.claude/` e artefatos necessários instalados

**Critérios de Aceite:**
- Dado um diretório ainda não inicializado, quando executo `dadaia init`, então o sistema cria o template canônico de `<workspace-root>/.dadaia/` com `contexts/`, `data/`, `reports/`, `scripts/`, `states/`, `src/`, `tmp/python/`, `tmp/json/`, e `.dadaia/.venv/`, cria `.claude/` se necessário, instala os artefatos públicos necessários no `.claude/` do workspace e exibe confirmação clara
- Dado um workspace parcialmente inicializado, quando executo `dadaia init`, então o sistema reconcilia os paths mínimos ausentes sem destruir conteúdo já existente e informa quais estruturas foram criadas ou preservadas

### US-002: Gerenciar Spec Context Projects com estados claros

- **Como** engenheiro trabalhando em mudanças multi-repositório
- **Quero** criar, ativar, desativar, visualizar, deletar e ajustar repositórios de um contexto
- **Para** manter o foco de trabalho rastreável, materializado e consistente para humanos e agentes

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia context create <nome> --repo <ref>`, então o sistema cria o contexto em `inativo`
- Dado um contexto `inativo` ou `standby`, quando executo `dadaia context activate <nome>`, então o sistema materializa o contexto quando necessário e o move para `ativo`
- Dado um contexto `ativo`, quando executo `dadaia context deactivate`, então o sistema move o contexto para `standby`
- Dado um contexto `standby`, quando executo `dadaia context delete <nome>`, então o sistema sincroniza os repositórios materializados de forma segura e remove apenas a materialização gerenciada e a metadata do contexto

### US-003: Descoberta confiável por humanos e agentes

- **Como** agente de IA ou engenheiro
- **Quero** descobrir o estado do workspace e do contexto ativo por comandos de help e por saída estável
- **Para** operar o sistema sem depender de documentação externa ou parsing frágil de tabela humana

**Critérios de Aceite:**
- Dado qualquer ambiente com dadaia instalado, quando executo `dadaia --help`, então o sistema lista `init`, `context`, `repos` e `public` com descrições claras
- Dado qualquer grupo ou subcomando da CLI congelada, quando executo `--help`, então o sistema explica uso, parâmetros e precondições de forma clara para autodiscovery por agentes e humanos
- Dado `dadaia context show --json`, quando existe um contexto ativo, então o sistema retorna uma saída machine-readable estável com contexto, paths e repositórios associados
- Dado que não existe contexto ativo, quando executo `dadaia context show --json`, então o sistema retorna uma resposta estável indicando ausência de contexto ativo

### US-006: Diagnosticar e contornar falhas da CLI

- **Como** agente de IA ou engenheiro
- **Quero** receber erros claros, com contexto e próxima ação segura
- **Para** me autorresolver sem depender de inspeção de código na maioria dos casos

**Critérios de Aceite:**
- Dado uma chamada CLI com precondição ausente ou input inválido, quando o comando falha, então a mensagem identifica o comando ou capacidade, o contexto ou recurso relevante, a causa provável recuperável e a próxima ação segura sugerida
- Dado uma falha originada em camada interna, quando ela é propagada para a CLI, então a cadeia causal da exceção é preservada de forma diagnóstica

### US-004: Instalar e atualizar artefatos de agente

- **Como** usuário do dadaia-workspace
- **Quero** instalar rules, skills e workflows distribuídos pelo pacote
- **Para** que meu workspace fique pronto para seguir o padrão SDD recomendado sem configuração manual extensa

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia public install`, então o sistema copia os artefatos distribuídos do pacote para o `.claude/` alvo
- Dado que o workspace já possui artefatos locais customizados, quando executo `dadaia public install` sem força, então o sistema não sobrescreve silenciosamente arquivos existentes

### US-005: Consultar o catálogo de repositórios conhecidos

- **Como** engenheiro criando ou ajustando um contexto
- **Quero** consultar os repositórios conhecidos do workspace
- **Para** reutilizar referências já registradas sem precisar memorizar links

**Critérios de Aceite:**
- Dado que o catálogo de repositórios contém entradas, quando executo `dadaia repos list`, então o sistema exibe a lista de repositórios conhecidos com identificadores úteis
- Dado que o catálogo está vazio, quando executo `dadaia repos list`, então o sistema informa claramente que nenhum repositório foi registrado

### US-007: Aprender e gerar material com a Dadaia Academy

- **Como** engenheiro usando o dadaia-workspace
- **Quero** acessar material base e futuramente acionar um workflow de academy a partir de slash command
- **Para** aprender o workspace, Claude Code, Open Code, SDD e multi-agent orchestration sem depender de documentação externa dispersa

**Critérios de Aceite:**
- Dado um workspace com academy inicializada, quando exploro `<workspace-root>/.dadaia/academy/`, então encontro sessões numeradas e padronizadas com conteúdo didático, referências e exemplos práticos
- Dado o slash command `/dadaia-academy`, quando ele for invocado por um agente com um prompt customizado do usuário, então o workflow cria ou expande cursos apenas dentro de `<workspace-root>/.dadaia/academy/`, usando o material base e as specs relevantes como grounding
- Dado que a academy é uma capacidade agent-facing, quando observo `dadaia --help`, então a superfície top-level congelada do binário permanece limitada a `init`, `context`, `repos` e `public`

---

## Requisitos Funcionais

- FR-001: The system shall provide a top-level `dadaia init` command that bootstraps the current directory as a dadaia workspace.
- FR-002: The system shall durably persist workspace state and Spec Context Project metadata across sessions.
- FR-003: The system shall provide a `dadaia context` command group with the frozen v1.0 subcommands: `create`, `list`, `show`, `activate`, `deactivate`, `delete`, `add-repo`, and `remove-repo`.
- FR-004: The system shall provide a `dadaia repos list` command for consulting the workspace repository catalog.
- FR-005: The system shall provide a `dadaia public install` command for installing distributed agent artifacts into a target `.claude/` directory.
- FR-006: The system shall guarantee that at most one Spec Context Project has state `ativo` at any given time.
- FR-007: The system shall provide a machine-readable `dadaia context show --json` output suitable for agent automation.
- FR-008: When a context transitions from `inativo` to `ativo`, the system shall materialize a managed working area for that context inside the workspace.
- FR-009: The bootstrap flow shall create the canonical `<workspace-root>/.dadaia/` template, including `.dadaia/.venv/`, `.dadaia/reports/`, `.dadaia/scripts/`, `.dadaia/states/`, `.dadaia/tmp/python/`, `.dadaia/tmp/json/`, `.dadaia/data/`, `.dadaia/src/`, and `.dadaia/contexts/`, create `.claude/` if needed, and install distributed agent artifacts unless the user explicitly opts out.
- FR-010: When deleting a `standby` context, the system shall remove workspace-managed materialization only after all required sync steps for that context have succeeded.
- FR-011: If a sync step fails during deletion after previous repositories were already synchronized, the system shall keep local metadata and managed files intact and explicitly report that remote side effects may already have occurred.
- FR-012: All commands in the frozen CLI surface shall provide self-sufficient help text for human and agent use.
- FR-013: The system shall treat `<workspace-root>/.dadaia/.venv/` as the isolated Python environment for workspace automation after bootstrap.
- FR-014: The system shall reserve `<workspace-root>/.dadaia/tmp/python/` and `<workspace-root>/.dadaia/tmp/json/` for ephemeral agent artifacts and transient generated data.
- FR-015: The system shall provide granular help text at the root command, command-group, and subcommand levels of the frozen CLI surface for autonomous discovery by humans and agents.
- FR-016: The system shall treat the official CLI as the primary supported integration surface for agent automation whenever a command exists for the requested capability.
- FR-017: If a CLI invocation fails, the system shall emit an error message that identifies the failed capability or command, the relevant workspace/context/resource, and the next safe recovery action when one exists.
- FR-018: The system shall preserve causal error context across layers so CLI failures remain diagnosable instead of opaque.
- FR-019: The system shall reserve `<workspace-root>/.dadaia/academy/` for Dadaia Academy base materials and generated learning artifacts.
- FR-020: The system shall support an agent-facing academy workflow exposed through an installed slash command `/dadaia-academy`, separate from the frozen top-level `dadaia` CLI surface.
- FR-021: Dadaia Academy sessions shall be organized as sequentially numbered directories inside `<workspace-root>/.dadaia/academy/`, each containing `README.md`, `EXAMPLE.md`, `REFERENCES.md`, and numbered markdown content files.
- FR-022: When the academy workflow generates or updates a course from a custom user prompt, it shall ground the material in the local academy base content and the relevant dadaia-workspace specs.
- FR-023: The bootstrap flow shall create `<workspace-root>/.dadaia/states/` as the durable storage area for persistent JSON state files written by workspace automations (e.g., model whitelists, audit snapshots). This directory shall not be cleared by maintenance routines; only the system that writes a state file may update or remove it.
- FR-024: The bootstrap flow shall create `<workspace-root>/.dadaia/scripts/` as the persistent storage area for workspace automation scripts (e.g., watchdog, deploy, maintenance). Scripts placed here survive across sessions and are managed explicitly by the user or by automation.

---

## Requisitos Não-Funcionais

- NFR-001: [Performance] The CLI shall respond to non-networked commands within 1 second under normal conditions.
- NFR-002: [Usabilidade] The `--help` and `--json` surfaces shall be stable enough for autonomous agent usage.
- NFR-003: [Portabilidade] The system shall run on Linux and macOS with Python 3.12+ and git installed.
- NFR-004: [Segurança] The system shall never persist credentials, tokens or secrets inside workspace state or agent artifacts.
- NFR-005: [Segurança Operacional] The system shall never delete source repositories outside the workspace-managed materialization area.
- NFR-006: [Diagnosabilidade] Common CLI failures shall be understandable enough for an autonomous agent to select a safe recovery path without inspecting source code in the common case.

---

## Fora de Escopo (v1.0)

- GUI ou interface web
- Comando `update` para renomear contextos
- Estado `arquivado`
- Sincronização bidirecional automática de specs entre repositórios
- Gerenciamento de branches além das operações git mínimas definidas nas specs de feature
- Integração com CI/CD
- Tracking de progresso da Dadaia Academy
- Persistência da Academy em SQLite no v1.0

---

## Questões Abertas

*Nenhuma bloqueante após esta rodada de refinamento. Questões residuais não-bloqueantes, se surgirem, devem ser registradas em `z_bug_specs.md`.*
