# Tasks: Release — agent-comms-v1

> **Status:** Aprovado
> **Release ID:** agent-comms-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Plan:** `specs/releases/agent-comms-v1/PLAN.md`

Implementer: software-engineer (executa T-AC-01 a T-AC-12) + product-engineer (executa T-AC-13).

Esta release está **enfileirada** (queued): `specs/releases/ACTIVE.md` continua apontando
para `dadaia-workspace-panel-v1`. Nenhuma task abaixo pode ser reservada (`[ ]` → `[-]`)
antes de:

1. `dadaia-workspace-panel-v1` arquivar em `_archive/releases/`.
2. Operador editar `ACTIVE.md` para apontar para `agent-comms-v1` (phase `TASKS`).

Cada task tem precondições explícitas. Marcas: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Gate v3 libera production write quando alguma TASKS.md tem `[-]`. Tasks são paralelizáveis
quando write-sets são disjuntos (ver wave matrix).

Gate-protocol reminder: antes de tocar qualquer arquivo de produção, mude o marker da task
de `[ ]` para `[-]` e commit (`chore(tasks): start <id>`). Ao concluir, mude para `[x]` e
commit junto com o trabalho final. Nunca dois `[-]` simultâneos.

---

## Wave matrix

| Wave | Tasks | Paralelizáveis | Dep externa |
|------|-------|----------------|-------------|
| 0 | T-AC-01, T-AC-02, T-AC-03, T-AC-04 | T-AC-01 ⊥ T-AC-02 ⊥ T-AC-04; T-AC-03 dep T-AC-02 | — (após ACTIVE.md flip) |
| 1 | T-AC-05, T-AC-06, T-AC-07 | T-AC-05 ⊥ T-AC-06; T-AC-07 dep ambos | Wave 0 [x] |
| 2 | T-AC-08, T-AC-09, T-AC-10 | T-AC-09 ⊥ T-AC-08; T-AC-10 dep ambos | Wave 1 [x] |
| 3 | T-AC-11, T-AC-12 | Serial: T-AC-12 dep T-AC-11 | Wave 2 [x] (skill já patcheada para emit) |
| 4 | T-AC-13 (CLOSURE) | — | Wave 3 [x] + operator approval |

```
Wave 0:  T-AC-01  T-AC-02  T-AC-04     →  T-AC-03 (dep T-AC-02)
Wave 1:  T-AC-05  T-AC-06               →  T-AC-07 (dep both)
Wave 2:  T-AC-08  T-AC-09               →  T-AC-10 (dep both)
Wave 3:  T-AC-11                        →  T-AC-12 (dep T-AC-11)
Wave 4:  T-AC-13 (CLOSURE — operator-gated)
```

---

## Tasks

### T-AC-01 — Canonical schema `handoff-v1.schema.json`

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 0
- **Precondições:** ACTIVE.md flipped para `agent-comms-v1`
- **Paraleliza com:** T-AC-02, T-AC-04
- **Files NEW:**
  - `dadaia_workspace/public/schemas/handoff-v1.schema.json`
- **Mudanças:** JSON Schema Draft 2020-12 com `$schema = "https://json-schema.org/draft/2020-12/schema"`. Campos obrigatórios: `schema_version`, `agent`, `context`, `produced_at`, `artifact{type,path,content_hash}`. Opcionais: `release_id`, `findings[]` (enum severity), `decisions_required[]`, `next_handoff`. `additionalProperties: false`. `artifact.path` pattern `^[a-zA-Z0-9_./{}-]+$` (Q7).
- **Aceite:** `jq '."$schema"' dadaia_workspace/public/schemas/handoff-v1.schema.json` retorna URL Draft 2020-12; `python -c "import json; json.load(open('dadaia_workspace/public/schemas/handoff-v1.schema.json'))"` exit 0.
- **Est. effort:** 30 min

---

### T-AC-02 — `HandoffDocument` dataclass + sub-models

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 0
- **Precondições:** ACTIVE.md flipped
- **Paraleliza com:** T-AC-01, T-AC-04
- **Files NEW:**
  - `dadaia_workspace/core/models/handoff.py`
  - `tests/unit/test_handoff_models.py`
- **Mudanças:** dataclass `frozen=True` com `HandoffDocument`, `ArtifactRef`, `Finding`, `NextHandoff` (A7). Classmethod `HandoffDocument.from_dict(data: dict) -> HandoffDocument`. 6 testes unit (minimal parse, full parse, frozen, type round-trip, severity round-trip, next_handoff optional).
- **Aceite:** `pytest tests/unit/test_handoff_models.py -q` green; coverage ≥ 100% no novo módulo.
- **Est. effort:** 45 min

---

### T-AC-03 — `ValidatorPort` Protocol + exceptions

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 0
- **Precondições:** T-AC-02 [x] (importa `HandoffDocument` em type hints opcionais)
- **Paraleliza com:** T-AC-01, T-AC-04 (em paralelo a T-AC-02)
- **Files NEW:**
  - `dadaia_workspace/core/protocols/handoff_validator.py`
- **Files MODIFIED:**
  - `dadaia_workspace/core/exceptions.py` (append `HandoffSchemaError`, `HandoffValidationError`)
- **Mudanças:** `typing.Protocol` com `validate(doc: dict) -> Sequence[HandoffValidationError]` (A8). 2 exceptions de domínio appended em `core/exceptions.py`. Sem testes diretos — Protocol é interface (cobertura via consumers em T-AC-05/T-AC-06).
- **Aceite:** `python -c "from dadaia_workspace.core.protocols.handoff_validator import ValidatorPort"` exit 0; `pytest tests/ -q` continua green (smoke).
- **Est. effort:** 20 min

---

### T-AC-04 — Patch `_COPY_DIRS` em `public_assets.py`

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 0
- **Precondições:** ACTIVE.md flipped
- **Paraleliza com:** T-AC-01, T-AC-02
- **Files MODIFIED:**
  - `dadaia_workspace/infrastructure/public_assets.py` (single-line: L35 adicionar `"schemas"` à tupla `_COPY_DIRS`)
- **Mudanças:** A6 — adicionar `"schemas"` em `_COPY_DIRS`. **NÃO** adicionar em `_CLAUDE_DIRS`, `_OPENCODE_DIRS` (A1). Esta task **deve preceder** o staging em T-AC-05/T-AC-08 (AR4 mitigation).
- **Aceite:** `grep '"schemas"' dadaia_workspace/infrastructure/public_assets.py` 1+ match; `pytest tests/unit/infrastructure/test_public_assets.py -q` green; após `dadaia public stage`, `.dadaia/agentic/schemas/handoff-v1.schema.json` existe (se T-AC-01 já mergeada).
- **Est. effort:** 10 min

---

### T-AC-05 — `StdlibHandoffValidator` adapter + tests

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 1
- **Precondições:** T-AC-01 [x], T-AC-03 [x], T-AC-04 [x]
- **Paraleliza com:** T-AC-06
- **Files NEW:**
  - `dadaia_workspace/infrastructure/stdlib_handoff_validator.py`
  - `tests/unit/test_stdlib_handoff_validator.py`
- **Mudanças:** ~85 LoC stdlib-only (A4). Whitelist explícita `SUPPORTED_KEYWORDS`; raise `HandoffSchemaError` em `__init__` se schema usa keyword fora do whitelist. Validate via `re` para `pattern`, `datetime.fromisoformat` para `format: date-time`. 10 tests: minimal valid, full valid, missing required, wrong type, invalid datetime, invalid enum, additionalProperties rejected, unsupported keyword raises HandoffSchemaError, schema file missing raises, error message includes field path.
- **Aceite:** `pytest tests/unit/test_stdlib_handoff_validator.py -q` 10/10 green; coverage do módulo ≥ 90%; `grep -E "^import (jsonschema|pydantic)" dadaia_workspace/infrastructure/stdlib_handoff_validator.py` vazio (NFR3).
- **Est. effort:** 2 h

---

### T-AC-06 — `ReportsValidationService` + `FakeHandoffValidator` + tests

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 1
- **Precondições:** T-AC-02 [x], T-AC-03 [x]
- **Paraleliza com:** T-AC-05
- **Files NEW:**
  - `dadaia_workspace/features/reports_validation/__init__.py`
  - `dadaia_workspace/features/reports_validation/service.py`
  - `tests/unit/test_reports_validation_service.py`
- **Files MODIFIED:**
  - `tests/fakes.py` (append `FakeHandoffValidator`)
- **Mudanças:** `ReportsValidationService.__init__(validator: ValidatorPort, reports_root: Path)`. Métodos: `validate_file(path)`, `validate_all(context=None)`, `check_hash(handoff_path)`. Dataclass `ValidationResult`. **Não importa** `StdlibHandoffValidator` direto (constitution L67). 8 tests cobrindo happy path, malformed JSON, schema violation propagation, validate_all discovery, context filter, hash matches/mismatch/missing.
- **Aceite:** `pytest tests/unit/test_reports_validation_service.py -q` 8/8 green; coverage do módulo ≥ 80% (NFR8); `grep "from dadaia_workspace.infrastructure" dadaia_workspace/features/reports_validation/service.py` vazio (constitution L67 enforcement).
- **Est. effort:** 1.5 h

---

### T-AC-07 — Container wiring + CLI Typer app + main.py registration

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 1
- **Precondições:** T-AC-05 [x], T-AC-06 [x]
- **Paraleliza com:** nenhuma (Wave 1 join point)
- **Files NEW:**
  - `dadaia_workspace/cli/commands/reports.py`
- **Files MODIFIED:**
  - `dadaia_workspace/container.py` (append `build_reports_validation_service(workspace_root)`)
  - `dadaia_workspace/cli/main.py` (1 line: `app.add_typer(reports.app, name="reports")`)
- **Mudanças:** A9 — composição com `StdlibHandoffValidator(schema_path)` lido de `workspace_root/.dadaia/agentic/schemas/`. CLI `reports validate` Typer app com args `[PATHS...]`, `--all`, `--release`, `--strict/--no-strict`, `--json`. Exit codes: 0 valid, 1 strict violation, 2 file not found, 3 bad invocation.
- **Aceite:** `dadaia --help | grep -i reports` mostra `reports  Inspect and validate agent handoff reports.`; `dadaia reports --help` mostra `validate`; smoke run `dadaia reports validate --help` exit 0.
- **Est. effort:** 1 h

---

### T-AC-08 — Integration tests CLI `dadaia reports validate`

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 2
- **Precondições:** T-AC-04 [x], T-AC-07 [x]
- **Paraleliza com:** T-AC-09
- **Files NEW:**
  - `tests/integration/test_cli_reports.py`
- **Mudanças:** 10 tests cobrindo happy path, schema violation exit codes (strict on/off), file not found, `--all`, `--json` output structure, `--release` filter, schema staged after `public install`, schema **NOT** in `.claude/schemas/` (A1 enforcement), workspace not initialized error.
- **Aceite:** `pytest tests/integration/test_cli_reports.py -q` 10/10 green; após este task, executar `dadaia public stage && dadaia public install --target all --force && dadaia public doctor` retorna `[ok]` em todas as projeções (incluindo `stage:schemas/handoff-v1.schema.json`).
- **Est. effort:** 1.5 h

---

### T-AC-09 — Skill `dadaia-handoff-emitter` + 3 pilot agent patches

- [x] **Status:** DONE
- **Owner:** software-engineer (coordena com PE em body changes — ADR-006)
- **Wave:** 2
- **Precondições:** T-AC-04 [x]
- **Paraleliza com:** T-AC-08
- **Files NEW:**
  - `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`
- **Files MODIFIED:**
  - `dadaia_workspace/public/agents/product-engineer.md`
  - `dadaia_workspace/public/agents/software-architect.md`
  - `dadaia_workspace/public/agents/software-engineer.md`
- **Mudanças:** A5 — SKILL.md com 3-step protocol (sha256sum, assemble JSON, Write sidecar). Referencia schema por path lógico (`.dadaia/agentic/schemas/handoff-v1.schema.json`), **não** duplica conteúdo (A10). Para cada um dos 3 pilotos: adicionar `dadaia-handoff-emitter` à lista `skills:` (frontmatter YAML — SE owns) + 1 parágrafo no body (PE owns per ADR-006) instruindo invocação após cada report HTML. Após edits: `dadaia public stage && dadaia public install --target all --force`; `dadaia public doctor` `[ok]`.
- **Aceite:** `for a in product-engineer software-architect software-engineer; do grep -c "dadaia-handoff-emitter" "dadaia_workspace/public/agents/$a.md"; done` cada linha ≥ 1; `ls .agents/skills/dadaia-handoff-emitter/SKILL.md` existe; `dadaia public doctor` `[ok]`.
- **Est. effort:** 45 min

---

### T-AC-10 — E2E tests handoff pipeline

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Wave:** 2
- **Precondições:** T-AC-08 [x], T-AC-09 [x]
- **Paraleliza com:** nenhuma (Wave 2 join point)
- **Files NEW:**
  - `tests/e2e/features/test_handoff_pipeline.py`
- **Mudanças:** 4 tests E2E via subprocess CLI: full handoff emit-and-validate; invalid handoff fails strict; schema projection idempotente (run twice, diff zero); doctor reports schema ok after install. Bootstrap workspace via `tmp_path` em cada teste.
- **Aceite:** `pytest tests/e2e/features/test_handoff_pipeline.py -q` 4/4 green; full suite `pytest tests/ -q` green; coverage `pytest --cov=dadaia_workspace.features.reports_validation --cov-fail-under=80` exit 0 (NFR8).
- **Est. effort:** 1 h

---

### T-AC-11 — z_bug consumers patches + backlog appends + constitution L106

- [x] **Status:** DONE
- **Owner:** software-engineer (coordena com PE em constitution edit — ADR-007)
- **Wave:** 3
- **Precondições:** T-AC-09 [x] (skill já patcheada antes que pilotos emitam handoff referenciando consumers atualizados)
- **Paraleliza com:** nenhuma (Wave 3 serial)
- **Files MODIFIED:**
  - `dadaia_workspace/public/skills/dadaia-workspace-spec-reviewer/SKILL.md` (L3, L22, L63: trocar `z_bug_specs.md` por `specs/backlog/candidates.md`)
  - `dadaia_workspace/public/commands/dadaia-workspace-refine-specs.md` (L2, L21, L28)
  - `dadaia_workspace/public/templates/repo-AGENTS.md` (L20)
  - `specs/backlog/candidates.md` (append BUG-003 em `## Hotfixes pendentes`; append `cli-asset-granular` em `## Candidatas ativas`)
  - `specs/constitution.md` (L106: enumerar 10 asset types — FR6, requires explicit operator confirmation per ADR-007; aprovação desta SPEC = consent)
- **Mudanças:** patches dos 3 consumers de `z_bug_specs.md` per Discovery §4.3. 2 bullets novos no backlog (PE Discovery §4.2). Patch constitution L106 (FR6 + ADR-007). Após edits: `dadaia public stage && dadaia public install --target all --force && dadaia public doctor`. **Doctor verde é precondição absoluta de T-AC-12.**
- **Aceite:** `grep -c "specs/backlog/candidates.md" dadaia_workspace/public/skills/dadaia-workspace-spec-reviewer/SKILL.md` ≥ 1; `grep -E "rules, skills, commands, scripts, agents, templates, workflows, plugins, data" specs/constitution.md` ≥ 1; `dadaia public doctor` `[ok]`; `dadaia specs doctor` 0 errors.
- **Est. effort:** 45 min

---

### T-AC-12 — z_bug archive (git mv) + sdd-spec-gate.sh patch

- [-] **Status:** IN PROGRESS
- **Owner:** software-engineer
- **Wave:** 3
- **Precondições:** T-AC-11 [x] + `dadaia public doctor` verde verificado (R2 mitigation)
- **Paraleliza com:** nenhuma (Wave 3 serial — **delete só após patches**)
- **Files MOVED (via `git mv`):**
  - `z_bug_specs.md` → `specs/_archive/legacy-bug-specs/z_bug_specs-root-2026-05-08.md`
  - `specs/z_bug_specs.md` → `specs/_archive/legacy-bug-specs/z_bug_specs-specs-2026-05-08.md`
- **Files MODIFIED:**
  - `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (L117: remover entry `*/z_bug_specs.md` do glob — F8 do Discovery)
- **Mudanças:** `mkdir -p specs/_archive/legacy-bug-specs/` (se não existir); `git mv` dos 2 arquivos; patch L117 do gate; `dadaia public stage && dadaia public install --target all --force`. Verificar: nenhuma referência stale.
- **Aceite:**
  - `find . -name "z_bug_specs.md" -not -path "*/_archive/*" -not -path "*/.git/*"` vazio
  - `grep -rn "z_bug_specs" dadaia_workspace/public/ .claude/ .opencode/ .codex/ .agents/ .dadaia/agentic/` vazio
  - `grep "z_bug_specs" dadaia_workspace/public/scripts/sdd-spec-gate.sh` vazio
  - `dadaia public doctor` `[ok]`
- **Est. effort:** 30 min

---

### T-AC-13 — CLOSURE desta release (`agent-comms-v1`)

- [ ] **Status:** OPEN
- **Owner:** product-engineer
- **Wave:** 4
- **Precondições:** T-AC-12 [x] + explicit operator approval
- **Paraleliza com:** nenhuma
- **Files NEW:**
  - `specs/releases/agent-comms-v1/CLOSURE.md` (com `## Drifts`, `## Validations` triples evidenciando os 15 checks do PLAN, `## Memory updates`)
- **Files MODIFIED:**
  - `specs/releases/ACTIVE.md` (phase: CLOSURE temporariamente; depois zero ou próxima release)
  - `specs/memory/product/agent-comms.html` (NEW — feature card documentando handoff schema + CLI + skill + 3 pilotos)
  - `specs/memory/product/index.html` (append catalog entry)
  - `specs/backlog/candidates.md` (mover entry L22 de `## Candidatas ativas` para `## Histórico` com release-id; append 9 candidatos novos listados em SPEC § Backlog gerado)
- **Files MOVED (via `git mv`):**
  - `specs/releases/agent-comms-v1/` → `specs/_archive/releases/agent-comms-v1/`
- **Mudanças:**
  - CLOSURE.md com Drifts (qualquer divergência do PLAN observada em execução), Validation block com os 15 checks do PLAN como evidence triples (description + command + observed output), Memory updates (lista dos HTMLs criados/atualizados).
  - Memory atomicity: novo HTML `agent-comms.html` documenta o estado atual do contrato handoff (não histórico de mudanças). Index atualizado.
  - Backlog: bullet L22 movido para histórico; 9 candidatas novas appended.
  - `git mv` da release ativa para `_archive/releases/`.
- **Aceite:**
  - `dadaia specs doctor` 0 errors / 0 warnings
  - `cat specs/releases/ACTIVE.md` mostra `release: none` ou próxima release (não `agent-comms-v1`)
  - `specs/_archive/releases/agent-comms-v1/CLOSURE.md` existe com `**Status:** Aprovado`
  - `grep -A2 "## Histórico" specs/backlog/candidates.md | grep agent-comms-v1` retorna match
  - `ls specs/memory/product/agent-comms.html` existe
- **Est. effort:** 30 min

---

## Resumo da matriz de paralelismo

```
Wave 0 (paralelo):   T-AC-01, T-AC-02, T-AC-04            (write-sets disjuntos)
                     T-AC-03 (após T-AC-02)
Wave 1 (paralelo):   T-AC-05 (dep 01+03+04), T-AC-06 (dep 02+03)
                     T-AC-07 (dep 05+06)
Wave 2 (paralelo):   T-AC-08 (dep 04+07), T-AC-09 (dep 04)
                     T-AC-10 (dep 08+09)
Wave 3 (serial):     T-AC-11 → T-AC-12   (patches before delete — R2)
Wave 4 (operator):   T-AC-13 (CLOSURE; dep 12 + operator approval)
```

Effort total: **~11.25 h** (~1.5 working days). Wave 0 paralelizada em 2 sessões: ~9.5 h
wall-clock.

Nesta sessão (criação de SPEC+PLAN+TASKS) **nenhuma task acima é executada** — todas começam
OPEN. A reserva (`[ ]` → `[-]`) acontece em sessão futura após:

1. `dadaia-workspace-panel-v1` arquivar
2. Operador flipar `ACTIVE.md` para `agent-comms-v1` / phase `TASKS`
