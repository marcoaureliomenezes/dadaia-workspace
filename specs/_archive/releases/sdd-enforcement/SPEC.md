# Spec: Feature — SDD Enforcement (sdd-spec-gate v2)

> **Status:** Em revisão
> **Versão:** 0.1
> **Autor:** Marco Menezes
> **Refinamento:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-15T000709Z-refine-specs-fase7.md`
> **Depende de:** `task-state-tracking` (mesma rodada)

---

## Contexto

O hook atual `sdd-spec-gate.sh` (v1) tem dois defeitos críticos identificados em auditoria de governança:

1. **Escopo estreito**: protege apenas paths VPS (`services/`, `docker/`, `scripts/`). Qualquer escrita em `repos/<slug>/` passa sem gate — o SDD nunca disparou durante o desenvolvimento da própria `dadaia-workspace`.
2. **Granularidade trivial**: a verificação atual é "existe algum SPEC.md aprovado em `specs_dir`?". Como toda evolução tem ao menos um SPEC aprovado, o gate é trivialmente satisfeito e perde valor.

Esta feature endereça os dois defeitos publicando a v2 do gate, que adiciona:
- proteção do `repos/<primary_slug>/` derivado do `primary_context.json`;
- verificação de pelo menos uma task com marker `[-]` (IN PROGRESS) em `TASKS.md` — granularidade real;
- mensagens orientadas por intenção que dizem ao agente exatamente o que falta;
- fail-open conservador fora dos paths de produção (mantém ergonomia para docs/configs).

A v2 é distribuída via `dadaia public stage && dadaia public install` (script já é lib-originated).

---

## Glossário

| Termo | Definição |
|---|---|
| **primary slug** | Valor de `repo_slug` em `<workspace_root>/.dadaia/states/primary_context.json`. |
| **production path** | Path coberto por qualquer cláusula do `case` do gate (paths VPS + `repos/<primary_slug>/`). |
| **active task** | Linha em `TASKS.md` com marker `[-]` (IN PROGRESS). Definida por `task-state-tracking/SPEC.md`. |
| **gate v2** | Versão deste hook publicada por esta evolução. Substitui a v1 inteiramente. |

---

## Usuários e Goals

### US-SDD-001: Bloquear escritas em produção sem task IN PROGRESS

- **Como** agente de implementação
- **Quero** ser bloqueado se tentar editar um arquivo de produção sem ter declarado uma task `[-]`
- **Para** garantir que toda mudança em produção tem rastreabilidade em TASKS.md

**Critérios de Aceite:**
- Dado um workspace com `primary_context.json` válido e nenhuma task `[-]`, quando o agente tenta `Write` em `repos/<primary_slug>/qualquer-arquivo`, então o gate retorna `{"decision":"block","reason":...}` com mensagem orientada.
- Dado o mesmo workspace mas com pelo menos uma task `[-]` em qualquer `TASKS.md` sob `<primary_specs_dir>`, quando o agente tenta `Write` no mesmo arquivo, então o gate libera (exit 0 silencioso).
- Dado um arquivo fora de produção (ex: `<workspace_root>/README.md`), quando o agente tenta `Write`, então o gate libera independente do estado de tasks.

### US-SDD-002: Mensagem orientada por intenção

- **Como** agente bloqueado pelo gate
- **Quero** uma mensagem clara dizendo qual condição não foi satisfeita
- **Para** poder agir corretamente sem entrar em loop

**Critérios de Aceite:**
- Mensagem cita o `file_path`, o `primary_slug`, o `specs_dir`, e o próximo passo concreto.
- Quando bloqueado por falta de `primary_context.json`: mensagem orienta `dadaia context activate <nome>` ou passar `--context`.
- Quando bloqueado por ausência de task `[-]`: mensagem orienta editar `TASKS.md` e mudar `[ ]` → `[-]` antes de retomar (consumo da skill `dadaia-task-manager`).

### US-SDD-003: Fail-open para edições não-produção

- **Como** operador editando um arquivo de docs
- **Quero** poder editar livremente arquivos fora do escopo do gate
- **Para** evitar fricção em mudanças triviais

**Critérios de Aceite:**
- Edições em `<workspace_root>/CLAUDE.md`, `AGENTS.md`, `README.md`, `.gitignore`, `pyproject.toml` (do workspace, não do primary_slug) não disparam o gate.
- Edições em `<workspace_root>/repos/<não-primary-slug>/` não disparam o gate.

---

## Requisitos Funcionais

- **FR-SDD-001:** Gate v2 shall be implemented as `dadaia_workspace/public/scripts/sdd-spec-gate.sh`. The script is lib-originated (manifest-tracked) and projected to runtimes by `dadaia public install`.
- **FR-SDD-002:** Gate v2 shall resolve `WORKSPACE_ROOT` via `$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)` — never via `$HOME` fallback. (Closes BUG-002 in spec.)
- **FR-SDD-003:** Gate v2 shall read `primary_slug` from `<WORKSPACE_ROOT>/.dadaia/states/primary_context.json`. If file is missing or malformed, gate shall treat the workspace as "no primary" and skip the new `repos/<primary_slug>/` clause (fail-open).
- **FR-SDD-004:** Gate v2 shall recognize as "production paths" any file matching at least one of:
  - `$WS/services/*`
  - `$WS/docker/redacted-infra/*`
  - `$WS/docker/redacted-infra/*`
  - `$WS/scripts/*`
  - `$WS/repos/<primary_slug>/*` (NEW in v2)
- **FR-SDD-005:** For paths matching FR-SDD-004, gate v2 shall require **at least one active task** (`[-]` marker) discoverable in `<primary_specs_dir>/TASKS.md` OR `<primary_specs_dir>/features/*/TASKS.md`. The semantics of `[-]` are defined by `task-state-tracking/SPEC.md`.
- **FR-SDD-006:** Gate v2 shall NOT inspect file_path coverage against the active task content in v0.1 — the existence of any `[-]` is sufficient. Path-aware coverage is deferred (see "Fora de Escopo").
- **FR-SDD-007:** Gate v2 shall emit RFC-style decision JSON on block: `{"decision":"block","reason":"<orientado por intenção>"}` and exit 0 (Claude Code / Codex hooks contract).
- **FR-SDD-008:** Gate v2 shall emit nothing on pass (exit 0 with empty stdout).
- **FR-SDD-009:** Gate v2 shall NOT crash on any internal error. All exceptions in subshells / python heredocs must end in a `exit 0` (fail-open) with optional `_log` to `/tmp/sdd-gate.log`.
- **FR-SDD-010:** Tool match list shall remain: `Write | write_file | Edit | edit_file | MultiEdit | apply_patch`. Read/Glob/Grep are never gated.

---

## Requisitos Não-Funcionais

- **NFR-SDD-001 [Honestidade]:** Mensagens de bloqueio nunca mentem sobre o motivo. Se o gate falha-aberto por erro interno, **não** bloqueia disfarçadamente.
- **NFR-SDD-002 [Performance]:** Gate v2 shall complete in <100ms p99 on a workspace with ≤20 TASKS.md files. Implementação: usa `find` + `grep -l` com early-exit, evita parse completo.
- **NFR-SDD-003 [Portabilidade]:** Script depende apenas de `bash`, `python3` (presente no workspace venv), `find`, `grep`, `mktemp`. Sem `jq`, sem ferramentas externas.

---

## Decisões Arquiteturais

### ADR-SDD-001: Verificação binária `[-]` em vez de coverage de path

Verificar se uma task `[-]` cobre exatamente o `file_path` exigiria parser semântico em `TASKS.md` (correspondência file_path ↔ texto da task). Em v0.1 é decisão consciente de pragmatismo: a presença de qualquer `[-]` é forte sinal de que o agente declarou intent. Coverage de path é deferida para v0.2 quando houver dados sobre falsos positivos/negativos da v0.1.

### ADR-SDD-002: Primary slug é a única expansão de escopo

A pergunta grill-me oferecia três níveis: primary, todos ativos, ou primary + states + specs. O operador escolheu o mais conservador. Isto reduz falsos positivos em multi-context paralelo e mantém ergonomia.

### ADR-SDD-003: v2 substitui v1 integralmente

Não há flag de compatibilidade. O upgrade é via `dadaia public install --target all --force`. O hook v1 nunca foi correto (paths errados); não há valor em mantê-lo.

---

## Estrutura de Arquivos

```
dadaia_workspace/
  public/
    scripts/
      sdd-spec-gate.sh       ← v2 (substitui inteiramente)
tests/
  integration/
    test_hooks.py            ← estender com casos v2
```

Sem mudanças em Python.

---

## Critérios de Aceite (Spec Aprovada)

- [ ] Script `sdd-spec-gate.sh` v2 atende todos os FR-SDD-001..010.
- [ ] `dadaia public stage && dadaia public install --target all --force` distribui v2.
- [ ] `dadaia public doctor` retorna `[ok]` para `scripts/sdd-spec-gate.sh`.
- [ ] Testes em `tests/integration/test_hooks.py` cobrem: (a) bloqueio quando primary ativo e zero tasks `[-]`, (b) liberação quando primary ativo e ≥1 task `[-]`, (c) fail-open quando sem primary, (d) fail-open para paths fora de produção.
- [ ] Mensagens de bloqueio passam revisão humana de orientação por intenção (RF-QA-007).

---

## Riscos e Mitigações

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| R1 | Gate v2 introduz fricção em PRs onde o agente não conhece a convenção `[-]` | Alta | Skill `dadaia-task-manager` distribuída na mesma rodada documenta o protocolo |
| R2 | Parse de `[-]` falha em formatos exóticos de Markdown | Média | Regex tolerante `^\s*-\s*\[-\]\s*` + fail-open em caso de erro |
| R3 | Performance ruim em workspaces com ≥20 features (≥20 TASKS.md) | Baixa | `grep -l ... | head -1` faz early-exit |
| R4 | Primary é trocado mid-session, gate começa a bloquear sem aviso | Média | Skill orienta operador a trocar primary só com tasks em estado estável |

---

## Fora de Escopo (v0.1)

- Path-aware coverage (validar que a task `[-]` cobre o `file_path`).
- Configuração via `.dadaia/sdd-policy.toml`.
- Gate em paths de `repos/<slug>/` para `slug != primary_slug`.
- Modo strict (sem fail-open).
- Bloqueio retroativo em commits antigos.

---

## Questões Abertas

*Nenhuma.* Todas as decisões resolvidas via grill-me (vide report de refinamento).
