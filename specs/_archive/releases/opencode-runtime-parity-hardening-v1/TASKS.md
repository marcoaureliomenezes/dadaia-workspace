# Tasks: Release — opencode-runtime-parity-hardening-v1

> **Status:** Aprovado
> **Release ID:** opencode-runtime-parity-hardening-v1
> **Owner:** product-engineer
> **Created:** 2026-05-29
> **Aprovado em:** 2026-05-29 (operador)
> **SPEC:** `specs/releases/opencode-runtime-parity-hardening-v1/SPEC.md` (Aprovado)
> **PLAN:** `specs/releases/opencode-runtime-parity-hardening-v1/PLAN.md` (Aprovado)
> **Total tasks:** 18 (T-OC-01..06 + T-RN-01..03 + T-AC-01..08 + T-INT-01)

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. Maximum **one `[-]` per agent
at a time** unless a phase declares parallel-safe (disjoint write sets).
Gate-protocol: flip `[ ]` → `[-]` and commit (`chore(tasks): start <id>`) before
touching any production file; flip `[-]` → `[x]` and commit with final work.

---

## Sequência entre tracks

```
Track A (T-OC-*)         Track B (T-RN-*)       Track C (T-AC-*)
sw-eng-py + ai-eng       sw-eng-py               ai-engineer + sw-eng-py
       |                      |                        |
 T-OC-01 (bloqueante)   T-RN-01 feature         T-AC-01..06 (6 agents)
 T-OC-02 color          T-RN-02 CLI              T-AC-07 propagação
 T-OC-03 permission     T-RN-03 testes           T-AC-08 testes
 T-OC-04 sdd-gate.ts
 T-OC-05 ctx-inject
 T-OC-06 regressão ←── dep T-AC-07
       └──────────────────────┴────────────────────────┘
                              T-INT-01 (dep T-OC-06 + T-AC-07)
```

**Regras críticas:** T-OC-03 e T-OC-04 só iniciam após T-OC-01 [x] com findings em SPEC/PLAN.
T-OC-06 só inicia após T-AC-07 [x]. T-INT-01 só inicia após T-OC-06 [x] e T-AC-07 [x].
Tracks A, B, C são independentes entre si (exceto T-OC-06 → T-AC-07).

---

## Track A — OpenCode Runtime Parity Hardening

### T-OC-01 — Investigação bloqueante (permission per-agent + hook event name)

- [x] **T-OC-01** — Blocking investigation: OpenCode 1.14.x `permission:` per-agent support and hook event name
- **Owner:** `software-engineer-python`
- **Write-set:** `specs/releases/opencode-runtime-parity-hardening-v1/SPEC.md` (update FR-OC-2/FR-OC-3 findings), `specs/releases/opencode-runtime-parity-hardening-v1/PLAN.md` (update §Fase A1)
- **Maps-to:** FR-OC-2 pré-requisito, FR-OC-3 pré-requisito; desbloqueia AC-OC-2, AC-OC-3
- **Precondições:** nenhuma — primeira task do Track A
- **Done criterion:** (1) verificar nos docs oficiais OpenCode 1.14.x se `permission:` é aceito por-agent em `.opencode/agents/<name>.md`; (2) confirmar nome do evento de intercepção de tool use em plugins (candidato: `tool.execute.before`); (3) registrar respostas em SPEC/PLAN antes que T-OC-03 ou T-OC-04 sejam reservadas; AC-OC-2 e AC-OC-3 atualizados com valores confirmados.

---

### T-OC-02 — Color strip na projeção OpenCode

- [x] **T-OC-02** — Add `color:` field strip to `_prepare_agent_for_opencode` (FR-OC-1)
- **Owner:** `software-engineer-python`
- **Write-set:** `dadaia_workspace/infrastructure/public_assets.py`, `tests/` (novo caso em `TestPrepareAgentForOpencode`)
- **Maps-to:** FR-OC-1; satisfaz AC-OC-1
- **Precondições:** nenhuma — independente de T-OC-01
- **Done criterion:** `_FRONTMATTER_COLOR_RE = re.compile(r"^color:[^\n]*\n", re.MULTILINE)` adicionado (~linha 30 de `public_assets.py`); `sub("", content)` chamado após o strip de `tools:`; caso de teste verifica ausência de `color:` na projeção OpenCode e presença na projeção Claude Code (parity check); `poetry run pytest` verde.

---

### T-OC-03 — Permission por-agent na projeção OpenCode

- [x] **T-OC-03** — Implement (or document-only) `permission:` per-agent in OpenCode projection (FR-OC-2)
- **Owner:** `software-engineer-python`
- **Write-set:** `dadaia_workspace/infrastructure/public_assets.py` (se suportado), `tests/`
- **Maps-to:** FR-OC-2; satisfaz AC-OC-2
- **Precondições:** T-OC-01 [x] e findings registrados em SPEC/PLAN
- **Done criterion:** se `permission:` por-agent suportado → transform em `_prepare_agent_for_opencode`; tools sem equivalente OpenCode geram `# [opencode-unsupported]: <tool>`; se não suportado → comentário `# [opencode-confirmed]: permission: per-agent not supported in OpenCode <version>` + AC-OC-2 atualizado; `poetry run pytest` verde.

---

### T-OC-04 — SDD gate plugin para OpenCode (`sdd-gate.ts`)

- [x] **T-OC-04** — Author `.opencode/plugins/sdd-gate.ts` SDD gate plugin (FR-OC-3)
- **Owner:** `ai-engineer`
- **Write-set:** `.opencode/plugins/sdd-gate.ts` (novo arquivo)
- **Maps-to:** FR-OC-3; satisfaz AC-OC-3
- **Precondições:** T-OC-01 [x] e nome do evento confirmado em SPEC/PLAN
- **Done criterion:** plugin TypeScript separado de `ctx-inject.ts`; intercepta escritas equivalentes (`write_file`, `edit_file`, `apply_patch`); invoca `.dadaia/scripts/sdd-spec-gate.sh` com contrato JSON de stdin idêntico ao gate atual; bloqueia em `{"decision":"block",...}`; fail-open em erros internos; comentário no topo cita evento verificado, versão OpenCode e URL do doc.

---

### T-OC-05 — Auditoria de `ctx-inject.ts`

- [x] **T-OC-05** — Audit `ctx-inject.ts` against OpenCode 1.14.x official docs (FR-OC-4)
- **Owner:** `ai-engineer`
- **Write-set:** `.opencode/plugins/ctx-inject.ts` (comentários inline ou correção)
- **Maps-to:** FR-OC-4; satisfaz AC-OC-4
- **Precondições:** nenhuma — pode correr em paralelo com T-OC-03/04 após T-OC-01
- **Done criterion:** se `chat.message` válido → comentário `# verified: chat.message valid in OpenCode <version> — <url>` no topo; se inválido → plugin corrigido para evento correto com comentário citando docs URL; "documentar sem corrigir" só se OpenCode não oferece alternativa.

---

### T-OC-06 — Testes de regressão cross-runtime

- [x] **T-OC-06** — Cross-runtime regression tests (FR-OC-6) — only after T-AC-07 done
- **Owner:** `software-engineer-python`
- **Write-set:** `tests/`
- **Maps-to:** FR-OC-6; satisfaz AC-OC-5, AC-ALL (NFR-1, NFR-3)
- **Precondições:** T-AC-07 [x] (Track C propagação completa); T-OC-02 [x]; T-OC-03 [x]; T-OC-04 [x]
- **Done criterion:** testes verificam ausência de `color:` em `.opencode/agents/` (todos 21 agents); presença de `color:` em `.claude/agents/`; presença/ausência de `permission:` conforme resultado de T-OC-01/03; presença de `.opencode/plugins/sdd-gate.ts`; `dadaia public doctor` `[ok]` via subprocess; `poetry run pytest` verde.

---

## Track B — `dadaia reports next` CLI

**Nota NFR-5:** antes de reservar T-RN-01, executar `poetry run pytest --cov=dadaia_workspace --cov-report=term-missing -q` e registrar o percentual da camada `features/` no commit de abertura. Floor constitucional: **80%**.

### T-RN-01 — Feature layer: lógica de negócio de `reports next`

- [x] **T-RN-01** — Implement `reports next` business logic in `features/` layer (FR-RN-1)
- **Owner:** `software-engineer-python`
- **Write-set:** `dadaia_workspace/features/reports_validation/` ou `dadaia_workspace/features/reports_next/`
- **Maps-to:** FR-RN-1; satisfaz AC-RN-1, AC-RN-2 (lógica)
- **Precondições:** registrar baseline NFR-5 antes de iniciar; independente de Tracks A e C
- **Done criterion:** lógica em `features/` (não inline na CLI); resolve contexto via `primary_context.json` ou `DADAIA_CONTEXT`; extrai sequência de agents de PLAN.md via contrato FR-RN-1 (`(owner: <agent>)`, `**Owner:** <agent>`, `owner: <agent>`); verifica `.handoff.json` com `release_id` ativo por agent; edge cases (sem release → exit 3; todos completos → mensagem; PLAN sem owners → exit 3); sem import de `infrastructure/` direto; `poetry run pytest` verde; cobertura `features/` ≥ 80%.

---

### T-RN-02 — CLI subcomando `dadaia reports next`

- [x] **T-RN-02** — Add `dadaia reports next` CLI subcommand (FR-RN-1)
- **Owner:** `software-engineer-python`
- **Write-set:** `dadaia_workspace/cli/commands/reports.py`
- **Maps-to:** FR-RN-1; satisfaz AC-RN-1, AC-RN-2 (saída)
- **Precondições:** T-RN-01 [x]
- **Done criterion:** subcomando `next` com opções `--context <ctx>`, `--json`; output texto e JSON conforme SPEC §FR-RN-1; exit codes 0/3; delega para serviço de T-RN-01; `dadaia reports next --help` exit 0.

---

### T-RN-03 — Testes unitários para `reports next`

- [x] **T-RN-03** — Unit tests for `reports next` (FR-RN-2)
- **Owner:** `software-engineer-python`
- **Write-set:** `tests/`
- **Maps-to:** FR-RN-2; satisfaz AC-RN-1, AC-RN-2, AC-ALL (NFR-1, NFR-5)
- **Precondições:** T-RN-01 [x]
- **Done criterion:** 5 casos mínimos (sem release ativa; PLAN sem owners; todos completos; próximo agent correto; `--json` válido); cobertura `features/` ≥ 80%; `poetry run pytest` verde.

---

## Track C — agent-comms waves 2-7

**Owner edição/propagação:** `ai-engineer` (write-surface exclusiva em `dadaia_workspace/public/agents/**`)
**Owner testes:** `software-engineer-python`
Referência de padrão: `dadaia_workspace/public/agents/data-analyst.md`.

### T-AC-01 — `qa-engineer` (piloto)

- [ ] **T-AC-01** — Add `dadaia-handoff-emitter` to `qa-engineer.md` (FR-AC-1, wave 2 pilot)
- **Owner:** `ai-engineer`
- **Write-set:** `dadaia_workspace/public/agents/qa-engineer.md`
- **Maps-to:** FR-AC-1; contribui para AC-AC-1
- **Precondições:** nenhuma — independente de Tracks A e B
- **Done criterion:** `dadaia-handoff-emitter` em `skills:` frontmatter; parágrafo de instrução no body; sem duplicação; `poetry run pytest` verde (parse tests).

### T-AC-02 — `devops-engineer`

- [ ] **T-AC-02** — Add `dadaia-handoff-emitter` to `devops-engineer.md` (FR-AC-1, wave 3)
- **Owner:** `ai-engineer`
- **Write-set:** `dadaia_workspace/public/agents/devops-engineer.md`
- **Maps-to:** FR-AC-1; contribui para AC-AC-1
- **Precondições:** T-AC-01 [x] (padrão validado no piloto)
- **Done criterion:** idem T-AC-01 para `devops-engineer.md`.

### T-AC-03 — `backend-engineer`

- [ ] **T-AC-03** — Add `dadaia-handoff-emitter` to `backend-engineer.md` (FR-AC-1, wave 4)
- **Owner:** `ai-engineer`
- **Write-set:** `dadaia_workspace/public/agents/backend-engineer.md`
- **Maps-to:** FR-AC-1; contribui para AC-AC-1
- **Precondições:** T-AC-01 [x]
- **Done criterion:** idem T-AC-01 para `backend-engineer.md`.

### T-AC-04 — `game-designer`

- [ ] **T-AC-04** — Add `dadaia-handoff-emitter` to `game-designer.md` (FR-AC-1, wave 5)
- **Owner:** `ai-engineer`
- **Write-set:** `dadaia_workspace/public/agents/game-designer.md`
- **Maps-to:** FR-AC-1; contribui para AC-AC-1
- **Precondições:** T-AC-01 [x]
- **Done criterion:** idem T-AC-01 para `game-designer.md`; write_allowlist com `<ctx>` — gate resolve via `PRIMARY_SLUG` (SPEC §Track C).

### T-AC-05 — `game-developer`

- [ ] **T-AC-05** — Add `dadaia-handoff-emitter` to `game-developer.md` (FR-AC-1, wave 6)
- **Owner:** `ai-engineer`
- **Write-set:** `dadaia_workspace/public/agents/game-developer.md`
- **Maps-to:** FR-AC-1; contribui para AC-AC-1
- **Precondições:** T-AC-01 [x]
- **Done criterion:** idem T-AC-04 para `game-developer.md`.

### T-AC-06 — `game-tester`

- [ ] **T-AC-06** — Add `dadaia-handoff-emitter` to `game-tester.md` (FR-AC-1, wave 7)
- **Owner:** `ai-engineer`
- **Write-set:** `dadaia_workspace/public/agents/game-tester.md`
- **Maps-to:** FR-AC-1; contribui para AC-AC-1
- **Precondições:** T-AC-01 [x]
- **Done criterion:** `dadaia-handoff-emitter` em `skills:` frontmatter + parágrafo de invocação no body; **não duplicar** bloco de sidecar-first section já existente no body de `game-tester` (linhas ~163-174).

### T-AC-07 — Propagação `dadaia public stage && install --target all`

- [x] **T-AC-07** — Propagate agent changes (`dadaia public stage && install --target all`) (FR-AC-2)
- **Owner:** `ai-engineer`
- **Write-set:** `.dadaia/agentic/` (staging), `.claude/agents/`, `.opencode/agents/`, `.codex/`, `.agents/` (projeções geradas)
- **Maps-to:** FR-AC-2; satisfaz AC-AC-2 (parcial); desbloqueia T-OC-06
- **Precondições:** T-AC-01 [x], T-AC-02 [x], T-AC-03 [x], T-AC-04 [x], T-AC-05 [x], T-AC-06 [x]
- **Done criterion:** `dadaia public stage && dadaia public install --target all` sem erros; `dadaia public doctor` `[ok]` para os 6 agents migrados; gate de desbloqueio para T-OC-06.

### T-AC-08 — Testes de regressão para os 6 agents migrados

- [x] **T-AC-08** — Regression tests for 6 migrated agents in source and projections (FR-AC-3)
- **Owner:** `software-engineer-python`
- **Write-set:** `tests/`
- **Maps-to:** FR-AC-3; satisfaz AC-ALL (NFR-1)
- **Precondições:** T-AC-07 [x]
- **Done criterion:** testes verificam presença de `dadaia-handoff-emitter` em `skills:` nos 6 agents source e nas projeções correspondentes; `poetry run pytest` verde.

---

## Gate de integração final

### T-INT-01 — Doctor completo: todos os 21 agents `[ok]`

- [x] **T-INT-01** — `dadaia public doctor` green for all 21 agents (AC-AC-2 gate final)
- **Owner:** `software-engineer-python`
- **Write-set:** nenhum (read-only)
- **Maps-to:** AC-AC-2, AC-OC-5, AC-ALL (NFR-2); libera CLOSURE
- **Precondições:** T-OC-06 [x] + T-AC-07 [x]
- **Done criterion:** `dadaia public doctor` retorna `[ok]` para todos os 21 agents em todos os runtimes suportados; nenhum `[drift]` ou `[missing]`; comando e saída registrados como evidência para CLOSURE §Validations.

---

## Resumo e traceabilidade

| Track | Tasks | Count |
|-------|-------|-------|
| A — OpenCode Hardening | T-OC-01..06 | 6 |
| B — reports next CLI | T-RN-01..03 | 3 |
| C — agent-comms waves 2-7 | T-AC-01..08 | 8 |
| Integration gate | T-INT-01 | 1 |
| **Total** | | **18** |

| FR/NFR | Task(s) | AC satisfeito |
|--------|---------|---------------|
| FR-OC-1 | T-OC-02 | AC-OC-1 |
| FR-OC-2 | T-OC-01, T-OC-03 | AC-OC-2 |
| FR-OC-3 | T-OC-01, T-OC-04 | AC-OC-3 |
| FR-OC-4 | T-OC-05 | AC-OC-4 |
| FR-OC-5 | T-INT-01 | AC-OC-5 |
| FR-OC-6 | T-OC-06 | AC-OC-1, AC-OC-5 (regressão) |
| FR-RN-1 | T-RN-01, T-RN-02 | AC-RN-1, AC-RN-2 |
| FR-RN-2 | T-RN-03 | AC-RN-1, AC-RN-2 |
| FR-AC-1 | T-AC-01..06 | AC-AC-1 |
| FR-AC-2 | T-AC-07 | AC-AC-2 (parcial) |
| FR-AC-3 | T-AC-08 | AC-ALL |
| NFR-1 | T-OC-06, T-RN-03, T-AC-08, T-INT-01 | AC-ALL |
| NFR-2 | T-AC-07, T-INT-01 | AC-AC-2 |
| NFR-3 | T-OC-06 | parity check |
| NFR-5 | T-RN-01 (baseline), T-RN-03 | AC-ALL |
