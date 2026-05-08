# Spec: Feature — Agent Rules, Skills & Public Assets

> **Status:** Aprovado  
> **Versão:** 1.4  
> **Autor:** Marco Menezes  
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`

---

## Contexto

O dadaia-workspace precisa governar dois ambientes ao mesmo tempo:

1. o repositório da biblioteca, que versiona assets de agente diretamente em `dadaia_workspace/public/`;
2. o ambiente do usuário final, que recebe artefatos extraídos para `.claude/` no momento do bootstrap ou de uma instalação explícita.

Esta feature define esse contrato completo para que as regras SDD sejam sempre aplicadas, para que a revisão de spec seja obrigatória e para que a descoberta do contexto ativo seja estável para agentes.

Para assets instalados no workspace, a política operacional é CLI-first: agentes devem descobrir capacidades pela própria CLI oficial e só recorrer a fallback efêmero quando ainda não existir comando canônico para o caso desejado.

---

## Glossário

| Termo | Definição |
|---|---|
| **Packaged source of truth** | Arquivos de rule, skill e workflow versionados neste repositório em `dadaia_workspace/public/` |
| **Installed assets** | Artefatos copiados para o `.claude/` do workspace do usuário |
| **Spec Navigator** | Skill que resolve o contexto ativo via `dadaia context show --json` |
| **Spec Reviewer** | Skill que lê o conjunto de specs e aponta conflitos, lacunas e inconsistências |
| **SDD Enforcer** | Rule sempre ativa que bloqueia implementação sem SPEC aprovada |
| **Spec Governance** | Rule sempre ativa que obriga revisão de consistência sempre que `specs/` for alterado |
| **Academy Command** | Slash command instalado em `.claude/commands/` que opera sobre `.dadaia/academy/` |

---

## Convenção de Nomenclatura (Não-Negociável)

Todos os artefatos usam o prefixo `dadaia-workspace-`.

| Artefato | Nome | Tipo |
|---|---|---|
| Enforcer de SDD | `dadaia-workspace-sdd-enforcer` | Rule |
| Governança de specs | `dadaia-workspace-spec-governance` | Rule |
| Navegador de specs | `dadaia-workspace-spec-navigator` | Skill |
| Revisor de specs | `dadaia-workspace-spec-reviewer` | Skill |

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

### US-004: Distribuição clara entre `public/` e `.claude/`

- **Como** mantenedor do dadoia-workspace
- **Quero** manter `dadaia_workspace/public/` como origem versionada e `.claude/` do workspace como destino de instalação
- **Para** evitar conflito entre desenvolvimento interno e instalação para usuários finais

**Critérios de Aceite:**
- Dado este repositório, quando um artefato é evoluído, então a versão autoritativa existe em `dadaia_workspace/public/`
- Dado este repositório, quando o produto é inspecionado, então `dadaia-workspace/.claude/` não existe como diretório de assets do produto
- Dado o pacote distribuído, quando o usuário executa `dadaia public install` ou `dadaia init`, então os artefatos instalados vêm de `dadaia_workspace/public/`

### US-005: Skills usam CLI e se recuperam por contratos estáveis

- **Como** agente de IA usando assets instalados
- **Quero** usar a CLI oficial como primeira interface e receber orientação suficiente para contornar falhas
- **Para** operar o workspace sem depender de inspeção ad hoc de arquivos internos

**Critérios de Aceite:**
- Dado que existe comando oficial para a capacidade desejada, quando uma skill precisa operar o produto, então ela usa a CLI `dadaia` e suas superfícies de help antes de qualquer fallback
- Dado que a CLI ainda não cobre a capacidade desejada, quando a skill precisa automatizar o caso, então ela usa apenas script efêmero em `.dadaia/tmp/python/` e dados estruturados em `.dadaia/tmp/json/`
- Dado que uma chamada de CLI falha, quando a skill reage ao erro, então ela trata a mensagem de erro e o help do comando como mecanismos primários de autorrecuperação

### US-006: Commands de agente também sustentam a Dadaia Academy

- **Como** usuário do workspace ou agente de IA
- **Quero** um slash command especializado para a Academy
- **Para** gerar e evoluir material didático dentro do runtime do usuário sem mexer na CLI congelada do binário `dadaia`

**Critérios de Aceite:**
- Dado um workspace com assets instalados, quando o agente lista os slash commands disponíveis, então `/dadaia-academy` aparece como command do ambiente de agente
- Dado a invocação de `/dadaia-academy`, quando o workflow cria ou atualiza um curso, então ele grava artefatos apenas dentro de `<workspace-root>/.dadaia/academy/`
- Dado que o workflow da academy precisa de grounding, quando ele gera conteúdo, então usa o material base da academy e as specs relevantes do workspace como referências locais prioritárias

---

## Requisitos Funcionais

### Modelo de Distribuição
- FR-001: The repository shall keep the versioned source of truth for agent assets under `dadaia_workspace/public/`.
- FR-002: A repository-local `.claude/` directory shall not be used as authoring or storage for product agent assets.
- FR-003: The command `dadaia public install` shall install packaged public assets into a target `.claude/` directory.
- FR-004: The command `dadaia init` shall install packaged public assets into the workspace `.claude/` directory unless the user explicitly opts out.

### Rules
- FR-005: The system shall provide an always-on rule named `dadaia-workspace-sdd-enforcer`.
- FR-006: The `dadaia-workspace-sdd-enforcer` rule shall instruct the agent to never implement code without approved `SPEC.md`, `PLAN.md`, and `TASKS.md` when they are required by the workflow.
- FR-007: The system shall provide an always-on rule named `dadaia-workspace-spec-governance`.
- FR-008: The `dadaia-workspace-spec-governance` rule shall instruct the agent that any change in `specs/` requires a consistency review across the whole relevant spec set before completion.
- FR-009: If unresolved inconsistencies remain after a spec refinement pass, the governance rule shall require them to be written to `z_bug_specs.md` before any implementation begins.

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
- FR-024: Skills shall not bypass an existing official CLI capability by directly reading internal SQLite files, package internals, or managed metadata paths.
- FR-025: Guidance and installed assets shall instruct agents to prefer CLI error output and help surfaces as the first recovery mechanism after a failed command.
- FR-026: The system shall provide an installed slash command named `/dadaia-academy` in the workspace agent environment.
- FR-027: The academy command shall operate as an agent command and shall not extend the frozen top-level surface of the `dadaia` binary.
- FR-028: The academy command shall create or update academy artifacts only under `<workspace-root>/.dadaia/academy/`.
- FR-029: The academy command shall use local academy base material and the relevant workspace specs as grounding before generating course content from a custom user prompt.
- FR-030: Guidance for the academy command shall preserve the numbering convention for academy sessions, examples, references, and numbered markdown lesson files.

---

## Requisitos Não-Funcionais

- NFR-001: [Governança] The rule set shall prioritize consistency enforcement over token minimization for this product's own development workflow.
- NFR-002: [Portabilidade] Installed assets shall work in a workspace-local `.claude/` directory without requiring direct edits to `.github/` files.
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
        dadaia-workspace-sdd-enforcer.md
        dadaia-workspace-spec-governance.md
      skills/
        dadaia-workspace-spec-navigator/
          SKILL.md
        dadaia-workspace-spec-reviewer/
          SKILL.md
      commands/
        dadaia-workspace-refine-specs.md
        dadaia-academy.md
```

---

## Fora de Escopo (v1.0)

- Geração automática de assets para agentes fora do ecossistema suportado pelo workspace
- Edição automática de `.github/` a partir do pacote
- Histórico de execuções da revisão de specs por sessão
- Skills especializadas de geração da academy além do command inicial `/dadaia-academy`

---

## Questões Abertas

*Nenhuma bloqueante após a definição do modelo `dadaia_workspace/public/` → `.claude/` do usuário.*
