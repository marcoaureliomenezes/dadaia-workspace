# Spec: Feature — Universal Agentic Assets

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/SPEC.md`, `specs/memory/architecture.md`, `specs/foundation/SPEC.md`
> **Consolida:** `agent-rules-skills`, `agents`, `cross-tool-parity`, `multi-tool-sdd-enforcement`, `dev-workspace-governance`, `spec-context-agent-command`

---

## Contexto

O dadaia-workspace deve operar como produto multi-agent-runtime para Claude Code, OpenCode e Codex. As specs anteriores ainda descreviam `.claude/` como destino principal e tratavam OpenCode/Codex como compatibilidade parcial. Esta feature define o contrato canônico: assets são versionados no pacote, staged pela CLI e projetados para cada runtime conforme suas capacidades nativas.

Fonte canônica:
- `dadaia_workspace/public/`

Estado local gerado:
- `<workspace-root>/.dadaia/agentic/`

Destino universal:
- `<workspace-root>/.agents/skills/`
- `<workspace-root>/AGENTS.md`

Projeções runtime-specific:
- Claude Code: `.claude/rules/`, `.claude/agents/`, `.claude/commands/`, `.claude/skills/`, `.claude/settings.json`
- OpenCode: `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/`, `opencode.json` (regras via `AGENTS.md`)
- Codex: `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/`, skills compartilhadas em `.agents/skills/`

### Matriz de distribuição por tipo de asset e runtime

| Asset type | Source (`public/`) | `.agents/` | `.claude/` | `.opencode/` | `.codex/` | Root |
|---|---|---|---|---|---|---|
| **agents** | `agents/` | — | `agents/` | `agents/` | — (via AGENTS.md) | — |
| **commands** | `commands/` | — | `commands/` | `commands/` | — (via AGENTS.md) | — |
| **rules** | `rules/` | — | `rules/` | — (via AGENTS.md) | `rules/` | — |
| **skills** | `skills/` | `skills/` | `skills/` | `skills/` | `skills/` (via `.agents/`) | — |
| **hooks** | `scripts/` | — | `settings.json` | — (unsupported) | `hooks.json` | — |
| **scripts** | `scripts/` | — | — | — | — | `.dadaia/scripts/` |
| **instructions** | `data/AGENTS.md` | — | — | — | — | `AGENTS.md` |

---

## Decisões Arquiteturais

### ADR-UAA-001: `dadaia_workspace/public/` permanece canônico

Não haverá rename amplo para `.agents/` dentro do pacote. O pacote Python continua versionando todos os assets em `dadaia_workspace/public/` para preservar a arquitetura existente e evitar migração ruidosa.

### ADR-UAA-002: `.dadaia/agentic/` é staging gerado

`.dadaia/agentic/` é recriável e pertence à CLI. O staging é extraído do pacote instalado, preferencialmente por editable install em desenvolvimento. Nenhum runtime deve ser tratado como fonte canônica.

### ADR-UAA-003: Projeções respeitam capacidades reais

Claude Code, OpenCode e Codex recebem artefatos nativos. Quando uma capacidade não existir em um runtime, o sistema registra `unsupported` no doctor em vez de simular paridade falsa.

### ADR-UAA-004: OpenCode não tem hook parity

OpenCode deve usar comandos, config, permissões e instruções. A spec não deve prometer hooks equivalentes a Claude Code/Codex para OpenCode.

### ADR-UAA-005: Codex usa `AGENTS.md`, hooks, rules e skills universais

Codex recebe instruções universais via `AGENTS.md`, configuração em `.codex/config.toml`, hooks em `.codex/hooks.json`, rules em `.codex/rules/` e skills compartilhadas em `.agents/skills/`.

---

## Usuários e Goals

### US-UAA-001: Staging reproduzível dos assets do pacote

- **Como** mantenedor do produto
- **Quero** gerar `.dadaia/agentic/` a partir de `dadaia_workspace/public/`
- **Para** validar exatamente quais assets serão projetados nos runtimes

**Critérios de Aceite:**
- Dado um editable install do pacote, quando executo `dadaia public stage`, então `.dadaia/agentic/` espelha `dadaia_workspace/public/`.
- Dado o staging concluído, então `.dadaia/agentic/manifest.json` contém `schema_version`, `package_version`, `generated_at` e hashes de assets.

### US-UAA-002: Instalação multi-runtime

- **Como** operador do workspace
- **Quero** executar `dadaia public install --target all`
- **Para** preparar Claude Code, OpenCode e Codex sem configurar cada ferramenta manualmente

**Critérios de Aceite:**
- Dado um workspace inicializado, quando executo `dadaia public install --target all`, então o sistema gera `.agents/skills/`, `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md`.
- Dado que `.dadaia/agentic/` está ausente, quando executo `install`, então o sistema executa staging antes da projeção.
- Dado um arquivo existente customizado, quando executo `install` sem `--force`, então o arquivo não é sobrescrito.
- Dado `--force`, quando executo `install`, então assets lib-originated podem ser sobrescritos pela versão staged.

### US-UAA-003: Doctor de package, staging e runtime

- **Como** operador ou agente
- **Quero** diagnosticar drift entre pacote, staging e projeções
- **Para** saber se o workspace reflete a versão instalada do produto

**Critérios de Aceite:**
- Dado assets íntegros, quando executo `dadaia public doctor`, então o status é `ok`.
- Dado asset ausente em staging ou runtime, então o status é `missing`.
- Dado asset divergente em staging ou runtime, então o status é `drift`.
- Dado uma capacidade não suportada por runtime, então o status é `unsupported`.

---

## Requisitos Funcionais

### Source e Staging

- FR-UAA-001: The versioned source of truth for all agentic assets shall be `dadaia_workspace/public/`.
- FR-UAA-002: The CLI shall provide `dadaia public stage`.
- FR-UAA-003: `dadaia public stage` shall extract package assets into `<workspace-root>/.dadaia/agentic/`.
- FR-UAA-004: `stage` shall write `.dadaia/agentic/manifest.json` with `schema_version`, `package_version`, `generated_at`, and content hashes for staged assets.
- FR-UAA-005: `.dadaia/agentic/` shall be generated state and may be deleted/recreated without losing canonical data.

### Install

- FR-UAA-006: The CLI shall provide `dadaia public install --target all|claude|codex|opencode|agents [--force]`.
- FR-UAA-007: `install` shall read from `.dadaia/agentic/`, generating it first when missing.
- FR-UAA-008: `install --target agents` shall install universal skills into `<workspace-root>/.agents/skills/`.
- FR-UAA-009: `install --target claude` shall project assets into `.claude/rules/`, `.claude/agents/`, `.claude/commands/`, `.claude/skills/`, and `.claude/settings.json`.
- FR-UAA-010: `install --target opencode` shall project assets into `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/`, and `opencode.json`.
- FR-UAA-011: `install --target codex` shall project assets into `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/`, and shared `.agents/skills/`.
- FR-UAA-012: `install --target all` shall run the `agents`, `claude`, `codex`, and `opencode` projections.
- FR-UAA-013: `install` shall create `AGENTS.md` in the workspace root from the staged universal template.
- FR-UAA-014: `install` shall not overwrite existing files unless `--force` is provided.
- FR-UAA-015: Runtime directories shall never be treated as canonical authoring locations.
- FR-UAA-026: The generated `.claude/settings.json` hook entries shall conform to the current Claude Code hook schema: each event key maps to an array of `{matcher: string, hooks: [{type, command}]}` objects. The `matcher` field shall be an empty string to match all tools.
- FR-UAA-027: `install --target opencode` shall not project a `rules/` directory into `.opencode/`; SDD rules reach OpenCode exclusively via `AGENTS.md`, which is loaded through `opencode.json` instructions.

### Doctor

- FR-UAA-016: The CLI shall provide `dadaia public doctor`.
- FR-UAA-017: `doctor` shall compare package source, `.dadaia/agentic/`, and runtime projections.
- FR-UAA-018: `doctor` shall classify each checked asset as `ok`, `missing`, `drift`, or `unsupported`.
- FR-UAA-019: `doctor` shall not mutate files.
- FR-UAA-020: `doctor` shall report unsupported runtime capabilities explicitly instead of requiring parity.

### Runtime Semantics

- FR-UAA-021: `AGENTS.md` shall be the universal instruction document for runtimes that read workspace-root instructions.
- FR-UAA-022: Universal skills shall be installed in `.agents/skills/`.
- FR-UAA-023: Hooks are supported for Claude Code and Codex only where their runtime hook model supports them.
- FR-UAA-024: OpenCode shall use commands, config, permissions, and instructions rather than hook parity.
- FR-UAA-025: The 4 specialized agent personas shall remain canonical in `dadaia_workspace/public/agents/` and be projected into runtime-native formats when supported.

---

## Requisitos Não-Funcionais

- NFR-UAA-001: [Reprodutibilidade] Staging must be deterministic for a given package version and workspace path.
- NFR-UAA-002: [Integridade] Existing user files must not be overwritten without `--force`.
- NFR-UAA-003: [Diagnóstico] Doctor output must be clear enough for an AI agent to decide whether to run `stage`, `install`, or request operator input.
- NFR-UAA-004: [Portabilidade] The flow must work with an editable install and the real `dadaia` CLI.
- NFR-UAA-005: [Honestidade de plataforma] Specs and generated assets must not claim unsupported parity for hooks, commands, skills, or agents.

---

## Critérios de Aceite

Acceptance command shape:

```bash
python -m pip install -e .
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

Required validations:
- Fresh workspace scaffold includes `.dadaia/agentic/`, `.agents/skills/`, `.codex/`, `.opencode/`, and `.claude/`.
- Staging mirrors `dadaia_workspace/public/`.
- Universal skills are installed into `.agents/skills/`.
- Claude, OpenCode, and Codex projections are generated without claiming unsupported parity.
- Drift is detected when a projected asset differs from staged/package source.
- Existing user files are not overwritten unless `--force` is used.

---

## Fora de Escopo

- Migrar o source package de `dadaia_workspace/public/` para outro diretório.
- Implementar capabilities inexistentes em runtimes via shims falsos.
- Usar runtime projection directories como source of truth.

---

## Questões Abertas

*Nenhuma bloqueante.*
