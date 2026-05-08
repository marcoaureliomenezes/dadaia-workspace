# Spec: Feature — Dadaia Academy

> **Status:** Aprovado  
> **Versão:** 0.1  
> **Autor:** Marco Menezes  
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/product.md`, `specs/memory/architecture.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## Contexto

A **Dadaia Academy** é a camada de aprendizagem prática do dadaia-workspace. Ela existe para reduzir a dependência de documentação externa dispersa e para transformar o próprio runtime do workspace em um ambiente de estudo guiado, com sessões, referências e exemplos reutilizáveis.

No primeiro incremento, a Academy entrega um **material base inicial** em `<workspace-root>/.dadaia/academy/`. Em um incremento posterior, um slash command de agente chamado `/dadaia-academy` usará esse material base, as specs relevantes do workspace e um prompt customizado do usuário para gerar cursos vivos e mais especializados.

O comando `/dadaia-academy` pertence ao ambiente de agentes instalado em `.claude/commands/`. Ele não altera a CLI top-level congelada do binário `dadaia`.

---

## Glossário

| Termo | Definição |
|---|---|
| **Academy root** | Diretório `<workspace-root>/.dadaia/academy/`, que contém o material base e os cursos gerados |
| **Material base** | Conteúdo inicial, estático e curado manualmente que serve de referência universal para a academy |
| **Curso vivo** | Curso gerado ou expandido a partir de um prompt do usuário usando o material base como grounding |
| **Sessão** | Unidade principal de aprendizagem, organizada em uma pasta numerada |
| **Módulo numerado** | Arquivo markdown com prefixo de dois dígitos que compõe o conteúdo principal da sessão |
| **Academy command** | Slash command `/dadaia-academy` instalado no ambiente de agentes para gerar ou enriquecer cursos |

---

## Usuários e Goals

### US-001: Explorar o material base da academy dentro do workspace

- **Como** engenheiro usando o dadaia-workspace
- **Quero** encontrar uma trilha inicial de sessões diretamente em `.dadaia/academy/`
- **Para** aprender o produto e o ecossistema agentic sem depender de links espalhados ou memória informal

**Critérios de Aceite:**
- Dado um workspace com a Academy inicializada, quando abro `.dadaia/academy/`, então encontro sessões numeradas com nomes descritivos
- Dado uma sessão da Academy, quando abro sua pasta, então encontro `README.md`, `REFERENCES.md`, `EXAMPLE.md` e módulos numerados em markdown

### US-002: Aprender a usar o dadoia-workspace e seu ecossistema agentic

- **Como** usuário novo do workspace
- **Quero** uma trilha inicial cobrindo o produto, Claude Code, Open Code, SDD e multi-agent orchestration
- **Para** acelerar onboarding e adoção prática das convenções do produto

**Critérios de Aceite:**
- Dado o material base inicial, quando percorro a Academy, então encontro as cinco sessões canônicas previstas nesta spec
- Dado cada sessão, quando concluo a leitura, então encontro um exemplo prático simples, profundo e reutilizável imediatamente

### US-003: Gerar cursos vivos a partir de um prompt customizado

- **Como** engenheiro ou agente de IA
- **Quero** invocar `/dadaia-academy` com um prompt customizado
- **Para** gerar ou expandir cursos dentro da Academy usando a base local como referência

**Critérios de Aceite:**
- Dado o slash command `/dadaia-academy`, quando ele recebe um prompt customizado do usuário, então cria ou expande um curso apenas dentro de `.dadaia/academy/`
- Dado um workflow de geração de curso, quando ele produz conteúdo, então usa o material base da Academy e as specs relevantes do workspace como grounding prioritário

### US-004: Preservar uma estrutura didática padronizada

- **Como** mantenedor do material da Academy
- **Quero** uma estrutura de sessão sempre igual
- **Para** permitir evolução incremental do conteúdo, revisões futuras e geração consistente por agentes

**Critérios de Aceite:**
- Dado uma sessão da Academy, quando seus arquivos são inspecionados, então a estrutura sempre inclui `README.md`, `REFERENCES.md`, `EXAMPLE.md` e arquivos de conteúdo com prefixo numérico de dois dígitos
- Dado um módulo de conteúdo da Academy, quando seu nome é criado, então usa `snake_case` ASCII com prefixo numérico como `01_introducao.md`

### US-005: Manter rastreabilidade das fontes usadas em cada sessão

- **Como** mantenedor da Academy
- **Quero** registrar as referências usadas na produção do conteúdo
- **Para** conseguir revisar, atualizar e enriquecer a sessão ao longo do tempo

**Critérios de Aceite:**
- Dado uma sessão da Academy, quando abro `REFERENCES.md`, então encontro as URLs externas e os arquivos internos usados como base
- Dado uma atualização futura da sessão, quando novas fontes forem adicionadas, então `REFERENCES.md` continua sendo o registro explícito dessas fontes

---

## Requisitos Funcionais

### Modelo do Runtime
- FR-001: The system shall reserve `<workspace-root>/.dadaia/academy/` as the root directory for Dadaia Academy base content and generated courses.
- FR-002: The first base curriculum of Dadaia Academy shall be represented by numbered session directories directly under `<workspace-root>/.dadaia/academy/`.
- FR-003: The academy workflow shall never create or update course artifacts outside `<workspace-root>/.dadaia/academy/`.

### Command de Agente
- FR-004: The system shall provide an agent-facing slash command named `/dadaia-academy`.
- FR-005: The academy command shall be installed through the agent-assets mechanism under `.claude/commands/`.
- FR-006: The academy command shall remain separate from the frozen top-level surface of the `dadaia` binary.
- FR-007: When invoked with a custom user prompt, the academy command shall generate or expand course content grounded in the local academy base material and relevant dadaia-workspace specs.

### Estrutura das Sessões
- FR-008: Each academy session shall live in a sequentially numbered directory with a descriptive name, such as `01_o_que_e_o_dadaia_workspace/`.
- FR-009: Each academy session directory shall contain `README.md`, `REFERENCES.md`, `EXAMPLE.md`, and numbered markdown lesson files.
- FR-010: Numbered lesson files shall use a two-digit prefix and `snake_case` naming, such as `01_introducao.md` and `02_modelos_de_linguagem.md`.
- FR-011: The content of academy sessions shall be written in pt-BR with correct grammar and accents, while preserving technical English terms in English.
- FR-012: Each academy session shall end with at least one practical example that the user can reuse as a base for their own projects.

### Material Base Inicial
- FR-013: The initial base curriculum shall include exactly these five canonical sessions: `01_o_que_e_o_dadaia_workspace`, `02_claude_code_quick_start`, `03_open_code_quick_start`, `04_sdd_quick_start`, and `05_agents_e_multi_agent_orchestration_quick_start`.
- FR-014: The session `01_o_que_e_o_dadaia_workspace` shall explain the workspace vision, setup flow, features, SDD orientation, `.dadaia/`, `.claude/`, and Spec Context Projects.
- FR-015: The session `02_claude_code_quick_start` shall use the official Claude Code references as factual grounding for CLI, commands, skills, tools, and the Python Agent SDK.
- FR-016: The session `03_open_code_quick_start` shall use the official Open Code references as factual grounding for CLI, tools, rules, commands, and skills.
- FR-017: The session `04_sdd_quick_start` shall use the specified SDD references and the local dadaia-workspace specs to explain SDD conceptually and operationally.
- FR-018: The session `05_agents_e_multi_agent_orchestration_quick_start` shall use the specified external references and the local harness-engineering material to explain agents and orchestration in a practical way.

### Rastreabilidade e Reaproveitamento
- FR-019: Each `REFERENCES.md` shall explicitly list the URLs and local files used to build its session.
- FR-020: The academy workflow shall treat the existing local base material as reusable grounding that can be enriched over time rather than recreated from scratch.
- FR-021: Supplemental advanced tracks may coexist under the academy root, but they shall not replace the five canonical initial sessions.

---

## Requisitos Não-Funcionais

- NFR-001: [Didática] Each session shall favor clear, direct, practice-oriented explanations over encyclopedic coverage.
- NFR-002: [Consistência] The academy structure shall remain stable enough for future automation by slash command and specialized skills.
- NFR-003: [Rastreabilidade] The base material shall remain inspectable and updateable by humans without hidden generation steps.
- NFR-004: [Portabilidade] The base material shall be usable from the workspace filesystem without depending on network access after it has been created.

---

## Estrutura de Arquivos

```
<workspace-root>/
  .dadaia/
    academy/
      01_o_que_e_o_dadaia_workspace/
        README.md
        REFERENCES.md
        EXAMPLE.md
        01_visao_geral_do_workspace.md
        02_arquitetura_do_runtime.md
        03_fluxo_de_trabalho_orientado_a_sdd.md
      02_claude_code_quick_start/
        README.md
        REFERENCES.md
        EXAMPLE.md
        01_visao_geral_do_claude_code.md
        02_commands_tools_e_skills.md
        03_agent_sdk_python_e_fluxos_praticos.md
      03_open_code_quick_start/
        README.md
        REFERENCES.md
        EXAMPLE.md
        01_visao_geral_do_open_code.md
        02_cli_tools_e_rules.md
        03_commands_skills_e_uso_pratico.md
      04_sdd_quick_start/
        README.md
        REFERENCES.md
        EXAMPLE.md
        01_por_que_sdd.md
        02_artefatos_phase_gates_e_ears_gears.md
        03_aplicando_sdd_no_dadaia_workspace.md
      05_agents_e_multi_agent_orchestration_quick_start/
        README.md
        REFERENCES.md
        EXAMPLE.md
        01_o_que_e_um_agent.md
        02_padroes_de_orquestracao.md
        03_aplicacoes_praticas_em_claude_code_e_open_code.md
```

---

## Fora de Escopo (incremento atual)

- Tracking de progresso do usuário
- Persistência de progresso ou preferências da Academy em SQLite
- Interface web ou GUI da Academy
- Implementação de skills especializadas para geração de cursos além do command `/dadaia-academy`
- Empacotamento definitivo do material base dentro da lib `dadaia-workspace`

---

## Questões Abertas

*Nenhuma bloqueante para a criação do material base inicial. A promoção futura do conteúdo base para `dadaia_workspace/public/` será tratada em um incremento posterior.*