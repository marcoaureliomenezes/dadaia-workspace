# Spec: Feature — Dev Workspace Governance

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/features/agent-rules-skills/SPEC.md`, `specs/memory/architecture.md`
> **Consolidado por:** `specs/features/universal-agentic-assets/SPEC.md`

---

## Contexto

O dadaia-workspace é desenvolvido dentro de um dadaia-workspace — o "paradoxo do bootstrap" (análogo ao Java escrito em Java). O diretório `/home/ubuntu/workspace` é simultaneamente:

- O **workspace de DEV** onde o operador trabalha no produto
- Um **workspace runtime** operado pela própria lib que está sendo desenvolvida

Isso cria dois pontos de falha específicos que precisam de governança explícita:

**Ponto 1 — projeções runtime com assets de duas origens:**
O workspace de DEV contém assets lib-originated em `.agents/`, `.claude/`, `.codex/` e `.opencode/` (fonte canônica em `dadaia_workspace/public/`, staged em `.dadaia/agentic/`) e assets projeto-específicos. Editar diretamente um asset lib-originated em qualquer projeção runtime cria drift silencioso — a lib evolui mas o workspace fica com versão stale do asset.

**Ponto 2 — `.dadaia/states/*.json` pode ficar inconsistente:**
Quando a lib evolui e o schema dos Python models muda (ex: campo renomeado, campo novo, campo removido), os JSON de estado do workspace ficam com schema antigo. A estratégia escolhida é estados plain-JSON auto-reparáveis por agente de AI, sem migrations ou versioning explícito. Não se usa SQLite nem migration scripts — essa abordagem gera slope code e tornou-se inviável em experimentos anteriores.

---

## Glossário

| Termo | Definição |
|---|---|
| **Asset lib-originated** | Arquivo em `.agents/`, `.claude/`, `.codex/` ou `.opencode/` cujo path relativo é gerado a partir de `dadaia_workspace/public/` via `.dadaia/agentic/` |
| **Asset projeto-específico** | Arquivo em projeção runtime que não existe no manifest staged — gerenciado pelo operador |
| **Schema drift** | Divergência entre campos em um `.dadaia/states/*.json` e os frozen dataclasses em `core/models/` |
| **Lib drift** | Divergência de conteúdo entre package source, `.dadaia/agentic/` e projeções runtime |
| **Dev guardrail** | Rule sempre ativa que proíbe edição direta de assets lib-originated em runtime projections |
| **Doctor** | Skill + command de diagnóstico e reparo operacional do workspace |

---

## Usuários e Goals

### US-001: Guardrail contra edição direta de assets lib-originated

- **Como** agente de IA trabalhando no workspace de DEV
- **Quero** ser impedido de editar diretamente assets lib-originated em `.agents/`, `.claude/`, `.codex/` ou `.opencode/`
- **Para** que a fonte canônica da lib nunca seja bypassada por edições locais silenciosas

**Critérios de Aceite:**
- Dado um pedido para editar um arquivo lib-originated em runtime projections, quando esse arquivo existe no manifest staged, então o agente recusa a edição direta e instrui: editar em `dadaia_workspace/public/<path>`, executar `dadaia public stage` e `dadaia public install`
- Dado um pedido para editar um asset projeto-específico (não presente no manifest staged), quando o agente verifica, então a edição direta é permitida

### US-002: Detecção de lib drift no workspace

- **Como** engenheiro de DEV
- **Quero** saber quais assets staged ou projetados estão divergindo da versão canônica na lib
- **Para** executar `dadaia public install` e sincronizar antes de trabalhar

**Critérios de Aceite:**
- Dado que `dadaia public doctor` ou a skill `dadaia-workspace-doctor` é invocada, quando ela executa a Fase 1, então ela compara package source, `.dadaia/agentic/` e projeções runtime e produz status `ok`, `missing`, `drift` ou `unsupported`
- Dado drift detectado, quando a fase conclui, então a skill exibe o diff e recomenda `dadaia public stage` ou `dadaia public install --force` sem escrever nas projeções runtime

### US-003: Reparo de JSON state com schema stale

- **Como** engenheiro de DEV com workspace quebrado após evolução da lib
- **Quero** reparar automaticamente os arquivos JSON em `.dadaia/states/`
- **Para** restaurar consistência sem recriar o workspace do zero

**Critérios de Aceite:**
- Dado um `spec_contexts.json` com schema stale (ex: campo `primary_repo_slug` onde o model atual espera `repo_slug`), quando a Fase 2 do doctor executa, então o agente lê o JSON, lê os frozen dataclasses correspondentes, identifica os mismatches e propõe as correções mínimas
- Dado um mismatch com default óbvio (ex: campo booleano ausente), quando o agente infere o valor padrão, então ele aplica sem perguntar ao operador
- Dado um mismatch sem default claro, quando o agente não consegue inferir, então ele pergunta ao operador antes de escrever
- Dado qualquer escrita de reparo, quando o agente grava o JSON, então ele usa escrita atômica (`.tmp` → `os.replace()`)
- Dado que o reparo falha, quando o JSON fica inalterado, então o workspace não perde dados

### US-004: Diagnóstico e reparo por escopo

- **Como** engenheiro de DEV
- **Quero** executar diagnóstico parcial (só lib drift, ou só JSON repair)
- **Para** focar no problema específico sem executar o fluxo completo

**Critérios de Aceite:**
- Dado `/dadaia-workspace-doctor lib`, quando o command executa, então só a Fase 1 (package vs staging vs runtime projections) é executada
- Dado `/dadaia-workspace-doctor state`, quando o command executa, então só a Fase 2 (JSON migration) é executada
- Dado `/dadaia-workspace-doctor` sem argumento, quando o command executa, então todas as fases são executadas em sequência

---

## Requisitos Funcionais

### Dev Guardrail Rule
- FR-001: The system shall provide an always-on rule named `dadaia-workspace-dev-guardrail` in `dadaia_workspace/public/rules/`.
- FR-002: The `dadaia-workspace-dev-guardrail` rule shall instruct the agent to identify lib-originated assets by checking whether the asset's relative path exists in `dadaia_workspace/public/` (located via `python -c "import dadaia_workspace; print(dadaia_workspace.__file__)"` and resolving to the package root).
- FR-003: The `dadaia-workspace-dev-guardrail` rule shall instruct the agent to never directly edit a lib-originated asset in `.agents/`, `.claude/`, `.codex/` or `.opencode/`. The only allowed path is: edit in `dadaia_workspace/public/<relative-path>` → run `dadaia public stage` → run `dadaia public install`.
- FR-004: If lib drift is detected during any task, the rule shall instruct the agent to report the drift and recommend `dadaia public install --force` before continuing.
- FR-005: Project-specific assets — files in runtime projections with no counterpart in the staged manifest — may be freely edited directly.

### Doctor Skill — Phase 0: Workspace Identification
- FR-006: The system shall provide a skill named `dadaia-workspace-doctor` in `dadaia_workspace/public/skills/dadaia-workspace-doctor/SKILL.md`.
- FR-007: Phase 0 of the skill shall locate the installed `dadaia_workspace` package path using `python -c "import dadaia_workspace; import pathlib; print(pathlib.Path(dadaia_workspace.__file__).parent)"`.
- FR-008: Phase 0 shall list and read all `*.json` files in `<workspace-root>/.dadaia/states/` before proceeding.

### Doctor Skill — Phase 1: Lib vs Installed Drift
- FR-009: Phase 1 shall iterate all files under `<lib-root>/public/`, compare them with `.dadaia/agentic/`, and compare supported runtime projections.
- FR-010: For each asset, Phase 1 shall report one of four statuses: `ok` (identical), `drift` (exists but differs), `missing` (not installed), or `unsupported` (runtime lacks the capability).
- FR-011: For assets with `drift` status, Phase 1 shall display a concise diff.
- FR-012: Phase 1 shall never write to runtime projections. All remediation is performed by the operator via `dadaia public stage` and `dadaia public install [--force]`.

### Doctor Skill — Phase 2: JSON State Migration
- FR-013: Phase 2 shall read each `*.json` in `.dadaia/states/` and identify its corresponding Python frozen dataclass(es) in `core/models/`.
- FR-014: Phase 2 shall cross-reference the JSON contents with: (1) the frozen dataclass fields and types, and (2) the canonical JSON example in `specs/memory/architecture.md`.
- FR-015: For each schema mismatch, Phase 2 shall classify it as: `renamed_field`, `missing_field`, `stale_field`, or `type_mismatch`.
- FR-016: For `missing_field` with an inferable default (boolean → false, empty list → [], ISO timestamp → current time), Phase 2 shall apply the default without prompting the operator.
- FR-017: For `missing_field` without an inferable default, Phase 2 shall ask the operator before writing.
- FR-018: For `renamed_field`, Phase 2 shall infer the rename from context (e.g., `primary_repo_slug` → `repo_slug` based on dataclass field name) and propose the change for operator confirmation.
- FR-019: For `stale_field` (present in JSON, absent in dataclass), Phase 2 shall propose removal with operator confirmation before deleting.
- FR-020: All JSON writes shall be atomic: write to `<file>.tmp` then `os.replace()`.
- FR-021: If any write operation fails, Phase 2 shall leave the original JSON file unmodified.
- FR-022: Phase 2 shall never remove or modify files in `repos/` — repo lifecycle is managed exclusively by `activate`/`deactivate`.

### Doctor Skill — Phase 3: Report
- FR-023: Phase 3 shall produce a summary: assets with drift / assets ok / JSON files repaired / actions requiring manual intervention.

### Doctor Command
- FR-024: The system shall provide an installed slash command `/dadaia-workspace-doctor` in `dadaia_workspace/public/commands/dadaia-workspace-doctor.md`.
- FR-025: `/dadaia-workspace-doctor` without arguments shall execute all phases (0 → 1 → 2 → 3).
- FR-026: `/dadaia-workspace-doctor lib` shall execute only Phase 0 and Phase 1 (lib vs installed drift).
- FR-027: `/dadaia-workspace-doctor state` shall execute only Phase 0 and Phase 2 (JSON state migration).

---

## Requisitos Não-Funcionais

- NFR-001: [Integridade] Phase 2 repair shall never cause data loss. If a write fails, the original JSON must be intact.
- NFR-002: [Segurança] The doctor skill shall never write to runtime projections. Only the operator, via `dadaia public install`, may modify lib-originated assets.
- NFR-003: [Diagnóstico] Phase 1 and Phase 2 shall always report their findings before applying any change, allowing the operator to review.
- NFR-004: [Leveza] JSON state files shall remain human-readable plain text. No embedded versioning, migration logs, or schema metadata shall be added to state files.
- NFR-005: [Manutenibilidade] The migration logic in Phase 2 is driven by reading current Python models and spec examples — no separate migration scripts or migration tables are maintained.

---

## Fora de Escopo (v1.0)

- Spec↔Python implementation drift detection — responsabilidade do `product-auditor-agent`
- JSON Schema files (.json schema spec files) para validação automática — não necessário
- Reparo automático de JSON malformado (sintaxe inválida) — reportar; requer intervenção manual
- Histórico de migrações anteriores por arquivo JSON

---

## Questões Abertas

*Nenhuma bloqueante.*
