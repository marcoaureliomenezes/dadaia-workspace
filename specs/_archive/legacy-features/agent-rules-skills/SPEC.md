# Spec: Feature — Agent Rules, Skills & Public Assets

> **Status:** Em revisão
> **Versão:** 2.1
> **Autor:** Marco Menezes  
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`, `specs/features/multi-agent-orchestration/SPEC.md`
> **Consolidado por:** `specs/features/universal-agentic-assets/SPEC.md`

---

## Contexto

O dadaia-workspace precisa governar três camadas ao mesmo tempo:

1. o repositório da biblioteca, que versiona assets de agente diretamente em `dadaia_workspace/public/`;
2. o staging gerado do workspace em `.dadaia/agentic/`;
3. as projeções runtime-specific para `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md`.

Esta feature define esse contrato completo para que as regras SDD sejam sempre aplicadas, para que a revisão de spec seja obrigatória e para que a descoberta do contexto ativo seja estável para agentes.

Para assets instalados no workspace, a política operacional é CLI-first: agentes devem descobrir capacidades pela própria CLI oficial e só recorrer a fallback efêmero quando ainda não existir comando canônico para o caso desejado.

---

## Glossário

| Termo | Definição |
|---|---|
| **Packaged source of truth** | Arquivos de rule, skill e workflow versionados neste repositório em `dadaia_workspace/public/` |
| **Staged assets** | Artefatos copiados para `.dadaia/agentic/` a partir do pacote instalado |
| **Installed assets** | Artefatos projetados para `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md` |
| **Spec Navigator** | Skill que resolve o contexto ativo via `dadaia context show --json` |
| **Spec Reviewer** | Skill que lê o conjunto de specs e aponta conflitos, lacunas e inconsistências |
| **Academy Command** | Agent command projetado para runtimes que suportam commands e que opera sobre `.dadaia/academy/` |

---

## Convenção de Nomenclatura (Não-Negociável)

Todos os artefatos usam o prefixo `dadaia-workspace-`.

| Artefato | Nome | Tipo |
|---|---|---|
| Guardrail de DEV | `dadaia-workspace-dev-guardrail` | Rule |
| Navegador de specs | `dadaia-workspace-spec-navigator` | Skill |
| Revisor de specs | `dadaia-workspace-spec-reviewer` | Skill |
| Grill crítico de specs | `dadaia-grill-me` | Skill |
| Doctor do workspace | `dadaia-workspace-doctor` | Skill + Command |
| Arquiteto de software | `software-architect` | Agent |
| Auditor de produto | `product-auditor-agent` | Agent |
| Engenheiro de produto | `product-engineer` | Agent |
| Engenheiro de software | `software-engineer` | Agent |
| QA Engineer | `qa-engineer` | Agent |

---

## Usuários e Goals

### US-001: Regras de SDD sempre aplicadas

- **Como** engenheiro que quer impedir drift arquitetural e slope code
- **Quero** rules sempre ativas no repositório e no workspace do usuário
- **Para** que qualquer agente seja obrigado a respeitar o pipeline SDD e a consistência das specs

**Critérios de Aceite:**
- Dado um pedido para implementar sem spec aprovada, quando a rule de SDD estiver ativa, então o agente se recusa a implementar
- Dado um pedido para alterar `specs/`, quando a rule de governança estiver ativa, então o agente é obrigado a revisar o conjunto de specs antes de considerar a alteração pronta

### US-002: Revisão automática do conjunto de specs

- **Como** engenheiro refinando o produto
- **Quero** uma skill que leia o conjunto inteiro de especificações relevantes e aponte conflitos
- **Para** detectar problemas antes da implementação

**Critérios de Aceite:**
- Dado que uma skill de revisão é invocada, quando ela executa seu fluxo, então ela lê `constitution.md`, `SPEC.md`, `foundation/SPEC.md`, memórias arquiteturais e specs de feature relevantes
- Dado que a revisão encontra problemas ainda não resolvidos, quando ela conclui, então ela registra os pontos remanescentes em `z_bug_specs.md`

### US-003: Agente resolve o contexto ativo por contrato estável

- **Como** agente de IA
- **Quero** descobrir o contexto ativo por um contrato machine-readable
- **Para** carregar o conjunto certo de specs sem depender de parsing de tabela humana

**Critérios de Aceite:**
- Dado um contexto ativo, quando a skill `dadaia-workspace-spec-navigator` é invocada, então ela usa `dadaia context show --json` para resolver `specs_dir`
- Dado que não existe contexto ativo, quando a skill é invocada, então ela informa a ausência de contexto e pede ativação explícita antes de seguir

### US-004: Distribuição clara entre `public/`, staging e projeções

- **Como** mantenedor do dadoia-workspace
- **Quero** manter `dadaia_workspace/public/` como origem versionada, `.dadaia/agentic/` como staging gerado e diretórios runtime como projeções
- **Para** evitar conflito entre desenvolvimento interno e instalação para usuários finais

**Critérios de Aceite:**
- Dado este repositório, quando um artefato é evoluído, então a versão autoritativa existe em `dadaia_workspace/public/`
- Dado este repositório, quando o produto é inspecionado, então `dadaia-workspace/.agents/`, `.claude/`, `.codex/` e `.opencode/` não existem como diretórios de authoring do produto
- Dado o pacote distribuído, quando o usuário executa `dadaia public stage`, `dadaia public install` ou `dadaia init`, então os artefatos instalados vêm de `dadaia_workspace/public/` via `.dadaia/agentic/`

### US-005: Skills usam CLI e se recuperam por contratos estáveis

- **Como** agente de IA usando assets instalados
- **Quero** usar a CLI oficial como primeira interface e receber orientação suficiente para contornar falhas
- **Para** operar o workspace sem depender de inspeção ad hoc de arquivos internos

**Critérios de Aceite:**
- Dado que existe comando oficial para a capacidade desejada, quando uma skill precisa operar o produto, então ela usa a CLI `dadaia` e suas superfícies de help antes de qualquer fallback
- Dado que a CLI ainda não cobre a capacidade desejada, quando a skill precisa automatizar o caso, então ela usa apenas script efêmero em `.dadaia/tmp/python/` e dados estruturados em `.dadaia/tmp/json/`
- Dado que uma chamada de CLI falha, quando a skill reage ao erro, então ela trata a mensagem de erro e o help do comando como mecanismos primários de autorrecuperação

### US-006: Commands de agente sustentam a dadaia-academy

- **Como** usuário do workspace ou agente de IA
- **Quero** um slash command especializado para a dadaia-academy
- **Para** tutoria e personalização de cursos via agente sem mexer na CLI congelada do binário `dadaia`

**Critérios de Aceite:**
- Dado um workspace com assets instalados, quando o runtime suporta commands, então `/dadaia-academy` aparece como command do ambiente de agente
- Dado a invocação de `/dadaia-academy`, quando o agente tutora um curso, então ele usa `dadaia academy list` para descobrir cursos e lê `.dadaia/academy/<slug>/` como contexto primário
- O command `/dadaia-academy` não escreve em `academy.json` diretamente — orienta o usuário a usar a CLI para CRUD

### US-007: Agentes especializados disponíveis no workspace

- **Como** engenheiro com múltiplos papéis de desenvolvimento
- **Quero** 4 agentes especializados com papéis distintos e permissões restritas, projetados conforme suporte de cada runtime
- **Para** orquestrar reviews, auditorias, spec refinement e implementação sem interferência entre os papéis

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia public install --target all`, então os 5 agentes SDD são projetados para os runtimes suportados, incluindo `.claude/agents/` para Claude Code
- Dado um agente instalado, quando o operador o invoca, então o agente segue seu escopo de escrita restrito (software-architect→reports, auditor→reports, product-engineer→specs, software-engineer→código+reports, qa-engineer→testes E2E+reports)
- Dado o `software-architect` ou `product-auditor-agent`, quando invocados, então usam a skill `dadaia-grill-me` para revisar specs criticamente

---

## Requisitos Funcionais

### Modelo de Distribuição
- FR-001: The repository shall keep the versioned source of truth for agent assets under `dadaia_workspace/public/`.
- FR-002: Repository-local runtime projection directories (`.agents/`, `.claude/`, `.codex/`, `.opencode/`) shall not be used as authoring or storage for product agent assets.
- FR-003: The command `dadaia public stage` shall materialize packaged public assets into `.dadaia/agentic/`, and `dadaia public install --target all|claude|codex|opencode|agents` shall project staged assets into runtime-specific destinations.
- FR-004: The command `dadaia init` shall stage and install packaged public assets into supported workspace runtimes unless the user explicitly opts out.

### Rules
- FR-005: SDD enforcement and spec-governance instructions shall be delivered via `AGENTS.md`; dedicated rule files for these concerns are eliminated. The single remaining rule file is `dadaia-workspace-dev-guardrail`.

### Skills
- FR-010: The system shall provide a skill named `dadaia-workspace-spec-navigator`.
- FR-011: The `dadaia-workspace-spec-navigator` skill shall resolve the current active context using `dadaia context show --json`.
- FR-012: The navigator skill shall load, in order, the active context's `constitution.md`, `SPEC.md`, `foundation/SPEC.md`, and any feature spec relevant to the current task.
- FR-013: The system shall provide a skill named `dadaia-workspace-spec-reviewer`.
- FR-014: The `dadaia-workspace-spec-reviewer` skill shall review the full relevant spec set for architecture conflicts, state-machine conflicts, CLI drift, schema gaps, and missing traceability.
- FR-015: If the active context lacks a complete `specs/` structure, then the navigator skill shall warn and stop before claiming the context is fully ready.

### Compatibilidade com Repositórios Gerenciados
- FR-016: If the primary repository of an active context lacks `specs/constitution.md` or `specs/SPEC.md`, then the system shall warn instead of hard-failing context creation.
- FR-017: The JSON contract returned by `dadaia context show --json` shall be the canonical discovery mechanism for installed agent assets.

### Aprovação Explícita dos Artefatos Canônicos
- FR-018: The SDD enforcement flow shall treat a required canonical artifact as approved only when its header contains the explicit marker `**Status:** Aprovado`.
- FR-019: If a required canonical artifact is marked `Em revisão`, `Draft`, or lacks the explicit approval marker, then the agent shall stop before implementation.

### Política CLI-First para Skills
- FR-020: Installed skills shall use official `dadaia` CLI commands as the primary interface for workspace capabilities whenever such commands exist.
- FR-021: Installed skills shall use command help surfaces (`dadaia --help`, `dadaia <group> --help`, and `dadaia <group> <command> --help`) for self-discovery before resorting to non-canonical probing.
- FR-022: If no official CLI command covers a needed capability, a skill may create an ephemeral Python script only under `<workspace-root>/.dadaia/tmp/python/`.
- FR-023: Any structured fallback output needed by a skill shall be written under `<workspace-root>/.dadaia/tmp/json/`.
- FR-024: Skills shall not bypass an existing official CLI capability by directly reading `spec_contexts.json`, `primary_context.json`, package internals, or other managed metadata paths.
- FR-025: Guidance and installed assets shall instruct agents to prefer CLI error output and help surfaces as the first recovery mechanism after a failed command.
- FR-026: The system shall provide an installed slash command named `/dadaia-academy` in the workspace agent environment.
- FR-027: The `/dadaia-academy` command shall operate as an agent command and shall not extend the frozen top-level surface of the `dadaia` binary.
- FR-028: The `/dadaia-academy` command shall use `dadaia academy list` for course discovery and read course files from `.dadaia/academy/<slug>/` as primary context.
- FR-029: The `/dadaia-academy` command shall not write to `academy.json` directly; it shall instruct the user to use the CLI for CRUD operations.
- FR-030: Guidance for the academy command shall preserve the file structure from the knowledge_basis module (README, EXAMPLE, EXERCISES, REFERENCES, numbered content files).

### Agents
- FR-031: The system shall provide 5 SDD pipeline agent files in `dadaia_workspace/public/agents/`: `software-architect.md`, `product-auditor-agent.md`, `product-engineer.md`, `software-engineer.md`, `qa-engineer.md`. Domain agents (`devops-engineer.md`, `game-developer.md`) are also present and defined in their own feature specs.
- FR-032: Agent files shall include enough metadata to project Claude Code sub-agent frontmatter (`name`, `description`, `model`, and `tools`) and runtime-native formats where supported.
- FR-033: Each agent's system prompt shall explicitly define its allowed write paths and prohibited paths.
- FR-034: `dadaia public install --target claude|all` shall copy/project `dadaia_workspace/public/agents/` to `<workspace-root>/.claude/agents/`; other runtimes receive native projections only when supported.

### `dadaia-grill-me` Skill
- FR-035: The system shall provide a skill named `dadaia-grill-me` at `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`.
- FR-036: The `dadaia-grill-me` skill shall instruct the agent to ask incisive questions that expose missing behavior contracts, conflicting requirements, ambiguous state machine transitions, and weak acceptance criteria.
- FR-037: The skill shall produce structured output: question → finding → recommendation.
- FR-038: `dadaia public install --target agents|all` shall copy the `dadaia-grill-me` skill to `<workspace-root>/.agents/skills/dadaia-grill-me/SKILL.md`, and runtime-specific skill directories when supported.

### `dadaia-workspace-dev-guardrail` Rule
- FR-039: The system shall provide an always-on rule named `dadaia-workspace-dev-guardrail` at `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`.
- FR-040: The `dadaia-workspace-dev-guardrail` rule shall instruct the agent to identify lib-originated assets by verifying whether the asset's relative path exists under `dadaia_workspace/public/` (resolved via the installed package path).
- FR-041: The `dadaia-workspace-dev-guardrail` rule shall instruct the agent to never directly edit a lib-originated asset in `.agents/`, `.claude/`, `.codex/` or `.opencode/`. Edits must be made in `dadaia_workspace/public/<relative-path>` first, then applied via `dadaia public stage` and `dadaia public install`.
- FR-042: If lib drift is detected, the rule shall require the agent to report it and recommend `dadaia public install --force` before proceeding.
- FR-043: Project-specific assets in runtime projections — those with no counterpart in the staged manifest — are exempt from this rule and may be edited freely.

### `dadaia-workspace-doctor` Skill and Command
- FR-044: The system shall provide a skill named `dadaia-workspace-doctor` at `dadaia_workspace/public/skills/dadaia-workspace-doctor/SKILL.md`.
- FR-045: The `dadaia-workspace-doctor` skill shall implement a three-phase protocol: Phase 1 (lib vs installed drift detection), Phase 2 (JSON state schema migration), Phase 3 (report).
- FR-046: In Phase 1, the doctor flow shall compare package source, `.dadaia/agentic/`, and runtime projections, classifying each as `ok`, `missing`, `drift`, `partial`, or `unsupported`. The `partial` status was added by the `multi-agent-orchestration` feature to honor best-effort capability mappings (e.g., OpenCode running `parallel_group` sequentially). It shall never mutate runtime projection files.
- FR-047: In Phase 2, the skill shall read each `*.json` in `.dadaia/states/`, cross-reference it with the corresponding frozen dataclasses in `core/models/` and the canonical JSON example in `specs/memory/architecture.md`, and repair mismatches atomically.
- FR-048: The system shall provide a slash command `/dadaia-workspace-doctor` at `dadaia_workspace/public/commands/dadaia-workspace-doctor.md` as a thin entry point for the skill. Accepts optional scope arguments: `lib` (Phase 1 only) or `state` (Phase 2 only).
- FR-049: `dadaia public install` shall project the `dadaia-workspace-doctor` skill and command to supported runtime destinations.

### `workflows/` — Novo Tipo Universal de Asset

> Adicionado por `specs/features/multi-agent-orchestration/SPEC.md`. Define `workflows/` como tipo de asset versionado no pacote, ao lado de `agents/`, `skills/`, `rules/`, `commands/`, `scripts/`.

- **FR-050:** The system shall recognize `workflows/` as a versioned asset type with source of truth at `dadaia_workspace/public/workflows/<slug>.workflow.md`. Each file is Markdown with YAML frontmatter conforming to schema version `"1"` as declared in `specs/features/multi-agent-orchestration/SPEC.md`.
- **FR-051:** `dadaia public stage` shall include `public/workflows/` in `_COPY_DIRS` and produce sha256 hashes for each workflow file in `.dadaia/agentic/manifest.json`.
- **FR-052:** `dadaia public install --target all|claude|opencode|codex|agents` shall project `<workspace-root>/.dadaia/agentic/workflows/` to: `.agents/workflows/` (universal reference), `.claude/workflows/`, `.opencode/workflows/`, `.codex/workflows/`. The files installed in Codex/OpenCode are reference documents; runtime execution semantics are governed by `AgentDispatcher` capabilities.
- **FR-053:** `dadaia public doctor` shall classify each projected workflow per runtime as `ok`, `partial` (best-effort), `unsupported` (e.g., Codex with `parallel_group`), `missing`, or `drift`.
- **FR-054:** Workflows that fail schema validation at `dadaia public stage` time shall abort the staging operation with a clear error orientado a recuperação (per RF-QA-007). Validation rules are defined in `specs/features/multi-agent-orchestration/SPEC.md` FR-ORCH-005.

---

## Requisitos Não-Funcionais

- NFR-001: [Governança] The rule set shall prioritize consistency enforcement over token minimization for this product's own development workflow.
- NFR-002: [Portabilidade] Installed assets shall work in workspace-local runtime projection directories without requiring direct edits to `.github/` files.
- NFR-003: [Manutenibilidade] Installed assets shall remain semantically aligned with the versioned source in `dadaia_workspace/public/`.
- NFR-004: [Descoberta] Skills shall rely on stable JSON contracts instead of parsing human-formatted CLI tables.
- NFR-005: [Autorrecuperação] Installed skills shall prefer help-first discovery and CLI error recovery over direct inspection of internal files whenever an official command exists.

---

## Estrutura de Arquivos

```
<repo-root>/
  dadaia_workspace/
    public/
      rules/
        dadaia-workspace-dev-guardrail.md
      templates/
        repo-AGENTS.md
      skills/
        dadaia-workspace-spec-navigator/
          SKILL.md
        dadaia-workspace-spec-reviewer/
          SKILL.md
        dadaia-grill-me/
          SKILL.md
        dadaia-workspace-doctor/
          SKILL.md
      agents/
        software-architect.md
        product-auditor-agent.md
        product-engineer.md
        software-engineer.md
        qa-engineer.md
        devops-engineer.md
        game-developer.md
      commands/
        dadaia-workspace-refine-specs.md
        dadaia-academy.md
        dadaia-workspace-doctor.md
        spec-context.md
      workflows/                                    ← NOVO tipo de asset
        spec-refinement.workflow.md
        tdd-cycle.workflow.md
```

---

## Fora de Escopo (v1.0)

- Geração automática de assets para agentes fora do ecossistema suportado pelo workspace
- Edição automática de `.github/` a partir do pacote
- Histórico de execuções da revisão de specs por sessão
- Skills especializadas de geração da academy além do command inicial `/dadaia-academy`

---

## Questões Abertas

*Nenhuma bloqueante após a definição do modelo `dadaia_workspace/public/` → `.dadaia/agentic/` → runtime projections.*
