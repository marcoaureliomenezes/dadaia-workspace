# Closure: Release — token-cost-bigbang-v1

> **Status:** Aprovado
> **Release ID:** token-cost-bigbang-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-20
> **Branch merged:** `release/token-cost-bigbang-v1` → `main`

---

## Summary

Big-bang release que executa o plano vinculante dos dois audits binding em
`.dadaia/reports/dadaia-workspace/audit/` (token-cost audit v2 + execution backlog).
Reduz cost per-invocation da topologia de 20 agentes e restaura reasoning bandwidth
perdido para system-prompt bloat. O release entrega quatro contratos arquiteturais
novos canonizados na constituição como ADRs X1..X7 (`AGENTS.md` provider-agnostic;
skill scoping Tier-A/B; agent size budget; default model Sonnet 4.6; schema
`handoff-v1.1`; dispatch-to-researcher canônico; plugin-scope policy). North-star
targets (audit §0) cobrem daily spend ~$58 → $15–20, system-prompt floor 160 K → 80 K,
`cache_read / msg` ~159 K → ≤ 80 K — todas com gates de validação P3 (T-50..T-54) na
janela de 7 dias pós-CLOSURE controlada pelo operador.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-20 | Schema `handoff-v1.schema.json` → v1.1 | (commit registrado em P2-B) |
| T-21 | `dadaia reports validate` accepts v1.1, rejects v1.0 | (commit registrado em P2-B) |
| T-22 | `dadaia reports lint <dir>` novo comando | (commit registrado em P2-B) |
| T-30 | 7 agentes Opus → Sonnet 4.6; researcher confirmado Haiku 4.5 | (commit registrado em P2-C) |
| T-31 | `description:` ≤ 200 chars em todos os 20 agentes | (commit registrado em P2-C) |
| T-32 | Template extraction para `docs/agent-knowledge/<agent>/templates/` | (commit registrado em P2-C) |
| T-33 | `workspace-protocol.md` rule criada e fatorada dos agent bodies | (commit registrado em P2-C) |
| T-34 | 22 Tier-B skills migradas para `docs/agent-knowledge/`; 11 Tier-A retidas | (commit registrado em P2-C) |
| T-35 | Legacy `software-engineer` sweep; lint rule em `dadaia public doctor` | (commit registrado em P2-C) |
| T-36 | Sidecar-first emission em todos os 20 agentes (handoff-v1.1) | (commit registrado em P2-C) |
| T-37 | Dispatch-to-researcher playbook em `project-orchestration` SKILL.md | (commit registrado em P2-C) |
| T-38 | `project-manager` codifica HTML/sidecar prompt antes de emitir | (commit registrado em P2-C) |
| T-39 | `plugin-scope.md` rule + allow-list lines (ADR-X7 enforcement) | (commit registrado em P2-C) |
| T-40 | 7 workflows com `consumes: [sidecar-path]`; 4 read-heavy com researcher stage | (commit registrado em P2-D) |
| T-41 | `dadaia public install`: `CLAUDE.md` = 1-line stub; `AGENTS.md` canonical | (commit registrado em P2-D) |
| T-42 | `dadaia public doctor` green (165+ entries, zero drift/missing/error) | (commit registrado em P2-D) |
| T-43 | Constitution amended ADRs X1..X7; memory atoms atualizados atomicamente | (este CLOSURE) |

---

## Validations

Acceptance criteria (SPEC §5) como evidence triples `{description, command, evidence}`.

### AC-1: All SPEC/PLAN/TASKS/CLOSURE with Status: Aprovado

| | |
|---|---|
| **Description** | Os 4 artefatos do release ladder carregam o marker exato `**Status:** Aprovado`. |
| **Command** | `grep "Status:" specs/releases/token-cost-bigbang-v1/{SPEC,PLAN,TASKS,CLOSURE}.md` |
| **Evidence** | `SPEC.md: **Status:** Aprovado` / `PLAN.md: **Status:** Aprovado` / `TASKS.md: **Status:** Aprovado` / `CLOSURE.md: **Status:** Aprovado` |

### AC-2: Constitution amended with ADRs X1–X7

| | |
|---|---|
| **Description** | `specs/constitution.md` carrega seção `## Architectural Decision Records` com 7 ADRs (X1..X7), cada um com Decisão / Justificativa / Consequências. |
| **Command** | `grep "### ADR-X" specs/constitution.md \| wc -l` |
| **Evidence** | 7 ADR headers presentes em `specs/constitution.md` (ADR-X1, ADR-X2, ADR-X3, ADR-X4, ADR-X5, ADR-X6, ADR-X7) — validável via grep acima. |

### AC-3: `dadaia public doctor` all green after install

| | |
|---|---|
| **Description** | Após `dadaia public stage && dadaia public install --target all`, doctor reporta zero `[missing]`, `[drift]`, `[error]`. |
| **Command** | `dadaia public stage && dadaia public install --target all && dadaia public doctor` |
| **Evidence** | T-42 DONE: 165+ entries processados; zero `[missing]`, `[drift]`, `[error]`; root:AGENTS.md `[ok]`; root:CLAUDE.md `[ok]` (stub verificado byte-identical). |

### AC-4: `dadaia reports validate` accepts v1.1, rejects v1.0

| | |
|---|---|
| **Description** | Validator distingue versões e falha non-zero em v1.0 incompleto. |
| **Command** | `dadaia reports validate <v1.0-sidecar-path>` |
| **Evidence** | T-21 DONE: exits non-zero com mensagem `ERROR: Missing required field 'findings[]'` para v1.0 incompleto; aceita v1.1 com warning quando `detail_md` ausente. |

### AC-5: `dadaia reports lint` clean

| | |
|---|---|
| **Description** | Lint flagga orphan HTMLs, oversized HTMLs (> 30 KB) e missing schema fields. |
| **Command** | `dadaia reports lint .dadaia/reports/` |
| **Evidence** | T-22 DONE: comando implementado; detecta orphans e oversized. Lint run pós-release está em T-53 (P3) — janela 7 dias pós-CLOSURE. |

### AC-6: 7-day post-release daily cost ≤ $25 (P3)

| | |
|---|---|
| **Description** | Daily spend ccusage média sobre janela de 7 dias pós-CLOSURE ≤ $25. |
| **Command** | `npx ccusage@latest claude daily \| tail -7` |
| **Evidence** | **Pendente** — P3 task T-50, owner operador, janela 7 dias pós-CLOSURE. |

### AC-7: cache_read / msg ≤ 80 K (P3)

| | |
|---|---|
| **Description** | Per-session `cache_read / msg` falsifica audit §8 P-02 baseline ~159 K. |
| **Command** | per-session cache_read/msg script per audit §1 |
| **Evidence** | **Pendente** — P3 task T-51, owner operador. |

### AC-8: 5 spot-check dispatches sidecar-only (P3)

| | |
|---|---|
| **Description** | 5 dispatches consecutivos sem HTML surpresa; researcher fan-out visível em ≥ 2. |
| **Command** | Manual dispatch observation (operador + project-auditor) |
| **Evidence** | **Pendente** — P3 task T-52, owner operador + project-auditor. |

---

## Summary of changes

### P2-B — Schema + validator (devops-engineer)
- `handoff-v1.schema.json` → v1.1: `scope`, `metrics`, `findings[].detail_md`, `findings[].fix_recommendation` obrigatórios; `artifact.path` opcional
- `dadaia reports validate` distingue v1.0 vs v1.1 com warnings/errors apropriados
- `dadaia reports lint <dir>` novo comando detecta orphans, oversized, missing fields

### P2-C — Agent rewrites (ai-engineer)
- 7 agentes Opus → Sonnet 4.6 (`project-manager`, `project-auditor`, `product-engineer`, `software-architect`, `ai-engineer`, `game-designer`, `game-tester`); `researcher` confirmado Haiku 4.5
- `description:` ≤ 200 chars em todos os 20 agentes (ADR-X3)
- Template extraction para `docs/agent-knowledge/<agent>/templates/` em agentes > 350 linhas
- `workspace-protocol.md` rule criada e fatorada dos agent bodies (ADR-X3)
- 22 skills Tier-B migradas para `docs/agent-knowledge/<agent>/<topic>.md`; 11 Tier-A retidas em `public/skills/` (ADR-X2)
- Legacy `subagent_type: software-engineer` eliminado; lint rule ativo em `dadaia public doctor`
- Sidecar-first emission em todos os 20 agentes (handoff-v1.1) (ADR-X5)
- Dispatch-to-researcher playbook em `project-orchestration` SKILL.md (ADR-X6)
- `project-manager` codifica HTML/sidecar prompt + multi-HTML split rule antes de emitir
- `plugin-scope.md` enforcement para `frontend-design` (ADR-X7); allow-list lines em `frontend-engineer.md` e `design-specialist.md`

### P2-D — Workflows + projection (devops-engineer)
- 7 workflows com `consumes: [sidecar-path]`; 4 read-heavy (`audit-cycle`, `code-review-fan-out`, `cross-cutting-feature`, `spec-refinement`) com stage `researcher` injetado (ADR-X6)
- `dadaia public install` re-arquitetado: `CLAUDE.md` = 1-line stub (`# See AGENTS.md for workspace rules and agent personas.`); `AGENTS.md` = canonical (ADR-X1)
- Skills em `.agents/skills/` com symlinks para `.claude/skills/`, `.codex/skills/`, `.opencode/skills/`
- `dadaia public doctor` green (165+ entries, zero drift/missing/error)

### CLOSURE — Constitution + memory (product-engineer)
- `specs/constitution.md` emendado com seção `## Architectural Decision Records` contendo ADRs X1..X7
- Memory atoms atualizados atomicamente:
  - `specs/memory/architecture.html` — agent topology layer atualizado com model defaults, skill catalogue Tier-A/B, sidecar-first emission, dispatch-to-researcher pattern; rules folder layer atualizado com `workspace-protocol.md` + `plugin-scope.md`
  - `specs/memory/tech-stack.html` — novas sections `model-assignments`, `plugin-inventory`, `schema-handoff`
  - `specs/memory/product/agent-orchestration.html` — novas sections `emission-contract` (ADR-X5), `dispatch-researcher` (ADR-X6), `plugin-scope` (ADR-X7)
  - `specs/memory/product/index.html` — vision/users/catalog refresh refletindo Sonnet default + Haiku researcher + Opus override

---

## Drifts

Nenhum drift estrutural a documentar nesta release. Todos os deltas foram entregues
conforme PLAN.md e o backlog binding em
`.dadaia/reports/dadaia-workspace/audit/2026-05-19T2200Z-token-cost-backlog.html`.

A única observação operacional: P3 acceptance gates (T-50..T-54) são post-CLOSURE por
construção — exigem janela de 7 dias de observação real. Resultados serão capturados em
relatórios de telemetria pelo operador e project-auditor; se qualquer gate falhar,
abrir nova release de correção (não re-editar este CLOSURE).

---

## Memory updates

- `specs/memory/architecture.html` — agent topology layer ganhou model defaults, skill catalogue, sidecar-first emission, dispatch-to-researcher; rules folder layer ganhou `workspace-protocol.md` + `plugin-scope.md`
- `specs/memory/tech-stack.html` — novas sections `model-assignments` + `plugin-inventory` + `schema-handoff`
- `specs/memory/product/agent-orchestration.html` — novas sections `emission-contract` + `dispatch-researcher` + `plugin-scope`
- `specs/memory/product/index.html` — vision/users refresh + catalog entry de `agent-orchestration` atualizada com os 4 ADRs canônicos da release

---

## Backlog returns

- `backlog/candidates.md ## Próxima release (queued)` ← `codex-agent-orchestration-parity-v1` (paused 2026-05-20, pre-empted por esta release; SPEC Draft preservado em `specs/releases/codex-agent-orchestration-parity-v1/SPEC.md`; resume após CLOSURE)
- `backlog/ideas.md` ← workflows novos para domínios data-engineering / BI / AI-entity authoring (rewire-only nesta release; workflows ficam em backlog até demanda concreta do operador)

---

## Archive decision

**MOVE** — release directory será movido para `specs/_archive/releases/token-cost-bigbang-v1/` via cópia explícita (passo 6 abaixo). `ACTIVE.md` será atualizado para `release: none, phase: DISCOVERY` com history annotation registrando o close.

---

**Status:** Aprovado
