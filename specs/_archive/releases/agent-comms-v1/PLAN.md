# Plan: Release — agent-comms-v1

> **Status:** Aprovado
> **Release ID:** agent-comms-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Spec:** `specs/releases/agent-comms-v1/SPEC.md`

---

## Resumo executivo

Esta release entrega o contrato `handoff-v1` em **5 waves** (13 tasks). Wave 0 é foundation
totalmente paralelizável (schema, models, protocol, `_COPY_DIRS` patch). Wave 1 monta
validator + service + CLI sob TDD. Wave 2 cria skill + patches dos 3 pilotos + E2E. Wave 3 é
a migração documental de `z_bug_specs.md` (patches **antes** dos deletes — mitigação de AR1).
Wave 4 é a closure pelo PE. Toda execução acontece em sessão futura após panel-v1 arquivar;
nesta sessão apenas SPEC+PLAN+TASKS são aprovados e `ACTIVE.md` permanece intocado.

---

## Waves

| Wave | Tema | Tasks | Paraleliza | Dep externa |
|------|------|-------|------------|-------------|
| 0 | Foundation (schema, models, protocol, assets-patch) | T-AC-01, T-AC-02, T-AC-03, T-AC-04 | T-AC-01 ⊥ T-AC-02 ⊥ T-AC-04; T-AC-03 dep T-AC-02 | — |
| 1 | Validator + Service + CLI | T-AC-05, T-AC-06, T-AC-07 | T-AC-05 ⊥ T-AC-06 (após Wave 0); T-AC-07 dep T-AC-05+T-AC-06 | Wave 0 [x] |
| 2 | Skill + Pilots + Integration/E2E | T-AC-08, T-AC-09, T-AC-10 | T-AC-08 dep T-AC-07; T-AC-09 dep T-AC-04 (paralelo a T-AC-08); T-AC-10 dep T-AC-08+T-AC-09 | Wave 1 [x] |
| 3 | z_bug migration (patches → propagate → mv) | T-AC-11, T-AC-12 | Serial estrita | Wave 2 [x] (skill patched antes); operador OK |
| 4 | Closure | T-AC-13 (CLOSURE) | — | Wave 3 [x] + operator approval |

```
Wave 0:  T-AC-01  T-AC-02  T-AC-04          (paralelo)
                 ↓
              T-AC-03                        (dep T-AC-02)
                 ↓
Wave 1:   T-AC-05         T-AC-06            (paralelo, dep Wave 0)
                 ↓
              T-AC-07                        (dep T-AC-05+T-AC-06)
                 ↓
Wave 2:   T-AC-08         T-AC-09            (paralelo, dep diferentes em Wave 0/1)
                 ↓
              T-AC-10                        (dep T-AC-08+T-AC-09)
                 ↓
Wave 3:   T-AC-11 → T-AC-12                  (serial: patches → mv)
                 ↓
Wave 4:   T-AC-13 (CLOSURE)                  (dep T-AC-12 + operator)
```

Effort total estimado pelo SE: **~11.25 h (~1.5 working days)**. Wave 0 paralelizada: ~9.5 h
wall-clock.

---

## Critical files

### NEW files (canonical absolute paths)

| Path | Layer | Wave |
|------|-------|------|
| `dadaia_workspace/public/schemas/handoff-v1.schema.json` | public asset | 0 |
| `dadaia_workspace/core/models/handoff.py` | core | 0 |
| `dadaia_workspace/core/protocols/handoff_validator.py` | core | 0 |
| `dadaia_workspace/infrastructure/stdlib_handoff_validator.py` | infrastructure | 1 |
| `dadaia_workspace/features/reports_validation/__init__.py` | features | 1 |
| `dadaia_workspace/features/reports_validation/service.py` | features | 1 |
| `dadaia_workspace/cli/commands/reports.py` | cli | 1 |
| `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md` | public asset | 2 |
| `tests/unit/test_handoff_models.py` | tests | 0 |
| `tests/unit/test_stdlib_handoff_validator.py` | tests | 1 |
| `tests/unit/test_reports_validation_service.py` | tests | 1 |
| `tests/integration/test_cli_reports.py` | tests | 2 |
| `tests/e2e/features/test_handoff_pipeline.py` | tests | 2 |
| `specs/_archive/legacy-bug-specs/z_bug_specs-specs-2026-05-08.md` | archive (via git mv) | 3 |
| `specs/_archive/legacy-bug-specs/z_bug_specs-root-2026-05-08.md` | archive (via git mv) | 3 |
| `specs/releases/agent-comms-v1/CLOSURE.md` | release | 4 |

### MODIFIED files

| Path | Layer | Change | Wave |
|------|-------|--------|------|
| `dadaia_workspace/infrastructure/public_assets.py` | infrastructure | L35: add `"schemas"` to `_COPY_DIRS` | 0 |
| `dadaia_workspace/core/exceptions.py` | core | Append `HandoffSchemaError` + `HandoffValidationError` | 0 |
| `dadaia_workspace/container.py` | composition | Add `build_reports_validation_service()` | 1 |
| `dadaia_workspace/cli/main.py` | cli | Register `app.add_typer(reports.app, name="reports")` | 1 |
| `tests/fakes.py` | tests | Add `FakeHandoffValidator` | 1 |
| `dadaia_workspace/public/agents/product-engineer.md` | public asset (PE+SE owners) | YAML: add skill; body: add instruction | 2 |
| `dadaia_workspace/public/agents/software-architect.md` | public asset | Same | 2 |
| `dadaia_workspace/public/agents/software-engineer.md` | public asset | Same | 2 |
| `dadaia_workspace/public/skills/dadaia-workspace-spec-reviewer/SKILL.md` | public asset | 3 line edits (L3, L22, L63) | 3 |
| `dadaia_workspace/public/commands/dadaia-workspace-refine-specs.md` | public asset | 3 line edits (L2, L21, L28) | 3 |
| `dadaia_workspace/public/templates/repo-AGENTS.md` | public asset | 1 line edit (L20) | 3 |
| `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | public asset | L117: remove `*/z_bug_specs.md` from glob | 3 |
| `specs/backlog/candidates.md` | spec | Append BUG-003 bullet + cli-asset-granular bullet | 3 |
| `specs/constitution.md` | spec | L106: enumerate 10 asset types (FR6) | 3 |
| `specs/releases/agent-comms-v1/{SPEC,PLAN,TASKS}.md` | release | Marker transitions during execution | 0–4 |

---

## Verification end-to-end (a executar em IMPLEMENTATION)

| # | Check | Comando | Esperado |
|---|-------|---------|----------|
| 1 | Doctor verde | `dadaia specs doctor` | 0 errors, 0 warnings |
| 2 | Full test suite passa | `pytest tests/ -q` | 0 failed; coverage feature ≥ 80% |
| 3 | `dadaia public install` idempotente | rodar 2x consecutivas | 2ª: `git status --short` vazio |
| 4 | Public doctor verde | `dadaia public doctor` | `[ok]` em todas projeções (incluindo `stage:schemas/handoff-v1.schema.json`) |
| 5 | Schema staged | `ls .dadaia/agentic/schemas/handoff-v1.schema.json` | arquivo existe |
| 6 | Schema **não** em runtime trees | `ls .claude/schemas/ .codex/schemas/ .opencode/schemas/ 2>&1` | "No such file or directory" 3x |
| 7 | Validator aceita fixture válida | `dadaia reports validate <fixture-valid.handoff.json>` | exit 0, "1 valid" |
| 8 | Validator rejeita fixture inválida (strict) | `dadaia reports validate <fixture-invalid.handoff.json> --strict` | exit 1, mensagem indica campo faltante |
| 9 | Validator non-strict emite warning | mesmo arquivo sem `--strict` | exit 0, warning em stderr |
| 10 | `z_bug_specs.md` ausente do live tree | `find . -name "z_bug_specs.md" -not -path "*/_archive/*" -not -path "*/.git/*"` | vazio |
| 11 | Referências stale a `z_bug_specs` | `grep -rn "z_bug_specs" dadaia_workspace/public/ .claude/ .opencode/ .codex/ .agents/ .dadaia/agentic/` | vazio |
| 12 | `sdd-spec-gate.sh:117` sem `z_bug_specs` | `grep "z_bug_specs" dadaia_workspace/public/scripts/sdd-spec-gate.sh` | vazio |
| 13 | Constitution L106 atualizado | `grep -E "rules, skills, commands, scripts, agents, templates, workflows, plugins, data" specs/constitution.md` | 1+ match |
| 14 | ACTIVE.md inalterado | `cat specs/releases/ACTIVE.md` | `release: dadaia-workspace-panel-v1` `phase: TASKS` |
| 15 | 3 pilotos com skill | `for a in product-engineer software-architect software-engineer; do grep -c "dadaia-handoff-emitter" "dadaia_workspace/public/agents/$a.md"; done` | 3 linhas com valor ≥ 1 |

---

## Open questions

Nenhuma. Q1–Q8 foram pré-resolvidas pelo operador no briefing desta Synthesis:

- Q1 (ACTIVE.md): SPEC+PLAN+TASKS aprovados; ACTIVE.md não modificado; release queued.
- Q2 (constitution L106): incluído via FR6 + ADR-007.
- Q3 (ownership `public/agents/*.md`): dual — SE frontmatter, PE body. ADR-006.
- Q4 (validator): stdlib-only.
- Q5 (schema shape): research §4.1 + A7.
- Q6 (workflow seed): sem novo workflow em v1; D4 é one-time; "spec-discovery-chain" → backlog v2.
- Q7 (`artifact.path` regex): loose `^[a-zA-Z0-9_./{}-]+$`.
- Q8 (constitution update procedure): ADR-007.

DN1–DN7 escalados da PE Discovery e Q1–Q3, Q5 do Architect Impact foram fechados via essas
resoluções. Não há item pendente para grill-me adicional.

---

## Rollback path

Se a release quebrar a pipeline de orquestração ou o fluxo de `dadaia public install`,
seguir esta ordem:

1. **Identificar o tipo de falha:**
   - `dadaia public stage` falha → patch `_COPY_DIRS` (T-AC-04) ou schema (T-AC-01) malformado. Revert esses commits.
   - `dadaia reports validate` crash → bug em `StdlibHandoffValidator` ou `ReportsValidationService`. Revert T-AC-05/T-AC-06.
   - Pilotos emitindo handoffs inválidos → skill SKILL.md (T-AC-09) com campos errados. Editar SKILL.md em `public/skills/` + `dadaia public stage && install --target all --force`.
   - Pipeline de orquestração crash (agente não encontrado) → frontmatter YAML dos pilotos corrompido (T-AC-09). Revert 3 edits + reinstall.
   - `refine-specs` lendo arquivo inexistente → delete rodou antes do patch (R2 materializou). Restore archived files com `git mv` reverso, reinstall, refazer migração na ordem correta.

2. **Revert via git:**
   ```bash
   git log --oneline | head -20
   git revert --no-edit <first-bad-commit>..HEAD
   ```

3. **Re-run install para restaurar projeções pre-v1:**
   ```bash
   dadaia public stage
   dadaia public install --target all --force
   dadaia public doctor   # esperado [ok] em todas
   ```

4. **z_bug rollback específico:**
   ```bash
   git mv specs/_archive/legacy-bug-specs/z_bug_specs-specs-2026-05-08.md specs/z_bug_specs.md
   git mv specs/_archive/legacy-bug-specs/z_bug_specs-root-2026-05-08.md z_bug_specs.md
   git checkout <pre-v1-sha> -- dadaia_workspace/public/skills/dadaia-workspace-spec-reviewer/SKILL.md \
                                dadaia_workspace/public/commands/dadaia-workspace-refine-specs.md \
                                dadaia_workspace/public/templates/repo-AGENTS.md \
                                dadaia_workspace/public/scripts/sdd-spec-gate.sh
   dadaia public stage && dadaia public install --target all --force
   ```

5. **Validar pipeline desbloqueado:**
   ```bash
   dadaia orchestrate run spec-refinement --context dadaia-workspace
   # se chega no primeiro gate sem crash, rollback completo
   ```

NFR1 garante que a orquestração **nunca** depende de `*.handoff.json` em v1. Rollback remove
CLI + schema projetado mas não exige migração de consumer — workflows existentes continuam
operando em paths HTML.

---

## Definition of Done (desta sessão)

- SPEC.md, PLAN.md, TASKS.md commited com `**Status:** Aprovado`
- PLAN.md ≤ 300 linhas (este arquivo)
- TASKS.md com 13 tasks (T-AC-01 a T-AC-13) markers `[ ]` + wave matrix
- `ACTIVE.md` **não modificado** (continua `dadaia-workspace-panel-v1` / `TASKS`)
- `dadaia specs doctor` 0 errors / 0 warnings
- Nenhum código de feature/CLI/test tocado nesta sessão (somente specs/)

---

## Referências

- SPEC: `specs/releases/agent-comms-v1/SPEC.md`
- TASKS: `specs/releases/agent-comms-v1/TASKS.md`
- ACTIVE.md (não modificado): `specs/releases/ACTIVE.md`
- Discovery inputs: ver SPEC § Referências
- Architect impact: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T232055Z-agent-comms-impact.html`
- SE recommendation: `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z-agent-comms-implementation.html`
- Constitution alvo: `specs/constitution.md` L106 (FR6)
- Tech-stack referência (não alterado): `specs/constitution.md` L17–28 (NFR3)
- Gate alvo: `dadaia_workspace/public/scripts/sdd-spec-gate.sh` L117 (FR5 / F8)
- Backlog origem: `specs/backlog/candidates.md` L22
- Constitution single-active-release rule: `dadaia_workspace/public/agents/product-engineer.md` L407–423
