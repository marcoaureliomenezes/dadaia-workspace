# Plan: Release — sdd-hotfix-track-v1

> **Status:** Aprovado
> **Release ID:** sdd-hotfix-track-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Refactored:** 2026-05-16 (operator simplification — see SPEC §"Drifts conhecidos")
> **Spec:** `specs/releases/sdd-hotfix-track-v1/SPEC.md`

---

## Estratégia

Implementação declarativa nesta sessão (SPEC + PLAN + TASKS); executiva na próxima
(software-engineer + devops-engineer aplicam as tasks). O plano agrupa as mudanças por
camada (doctor, agentes, templates, CI, constitution) e ordena por dependência leve —
doctor primeiro (regex SemVer + backlog dual-section validation), depois consumers
(templates, agentes, workflow), depois CI e constitution.

A simplificação adotada na refatoração eliminou o catch-22 do design anterior: como o
**gate não muda** (hotfix é uma release normal sob `specs/releases/`), não há sequência
rígida "doctor primeiro, depois gate, depois consumers". Cada camada é praticamente
independente.

---

## Camadas e sequenciamento

### Camada 1 — Doctor: SemVer regex + backlog dual-section

1. `dadaia_workspace/features/specs/doctor.py`:
   - Adicionar `RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")` (D3)
   - Adicionar `RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)` e `RELEASE_SEMVER_HARD = date(2026, 7, 1)`
   - Adicionar `BACKLOG_HOTFIX_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}T\d{6}Z) (LOW|MEDIUM|HIGH|CRITICAL) ([\w\-/]+) — .+ \(post-mortem: .+\)$")`
   - Adicionar `BACKLOG_CANDIDATE_RE` (regex existente, formalizado)
   - Novo check `SPEC-DOC-016` (WARNING→ERROR): folder name em `specs/releases/<id>/` casa
     `RELEASE_SEMVER_RE` quando `Created:` ≥ `RELEASE_SEMVER_CUTOFF`; severidade WARNING
     até `RELEASE_SEMVER_HARD`, depois ERROR. Vintage (`Created:` ≤ 2026-05-17) skipped
   - Estender `SPEC-DOC-012` (existente, valida candidates.md) para validar **duas**
     seções com regex próprios: `## Candidatas ativas` (formato atual) e `## Hotfixes pendentes`
     (novo formato D22). WARNING quando bullet em `## Hotfixes pendentes` tem timestamp
     mais antigo que 72h e não foi movido para `## Histórico` (D23)
   - Tests em `tests/unit/features/specs/test_doctor.py`: 2 positivos + 2 negativos por
     check novo/estendido (8 testes mínimo)

### Camada 2 — Templates + scaffolder

Independente de Camada 1; pode rodar em paralelo.

1. Criar `dadaia_workspace/public/templates/release_hotfix.md.j2` (D24): SPEC template
   enxuto com 6 seções obrigatórias — Incident summary, Affected memory features, Root
   cause, Fix scope, Rollback plan, Acceptance + smoke test. Header inclui `**Patches release:**`
2. Criar `dadaia_workspace/public/templates/closure_hotfix.md.j2` (D25): CLOSURE template
   com bloco `## Validations` contendo placeholder para evidence triple (description,
   command, evidence) verificando que o bug não existe em produção
3. Adicionar `scaffold_hotfix_release(specs_dir, version_id, patches_release_id, severity, templates_dir)`
   em `dadaia_workspace/features/specs/scaffolder.py`. Cria `specs/releases/<version_id>/SPEC.md`
   + `TASKS.md` (stub) usando templates novos. Valida `RELEASE_SEMVER_RE.match(version_id)`
   e `version_id` tem PATCH≥1
4. CLI command `dadaia specs hotfix open <version-id> --patches <release-id> [--severity <S>]`
   em `dadaia_workspace/cli/commands/specs.py`. Pré-condição: existe entrada em
   `## Hotfixes pendentes` no backlog que justifica a promoção (validação humana, comando
   apenas avisa)
5. Tests `tests/unit/features/specs/test_scaffolder.py`: happy path + idempotência +
   version-id inválido rejeitado + PATCH=0 rejeitado

### Camada 3 — Agentes (surgical edits)

Independente das outras camadas.

1. `dadaia_workspace/public/agents/product-engineer.md`:
   - Nova seção "Hotfix release lifecycle" após "Mandatory workflow — release lifecycle"
   - Descreve fluxo condensado: SPEC + TASKS obrigatórios; PLAN opcional (SPEC declara
     em "Fix scope"); CLOSURE com smoke evidence obrigatório (D25)
   - Regra dura: hotfix release só sai de bullet em `## Hotfixes pendentes` do backlog (D4)
   - Folder name é `v<M>.<m>.<p>` com PATCH≥1 (D3)

2. `dadaia_workspace/public/agents/qa-engineer.md`:
   - Subseção "Hotfix candidate filing" descrevendo stub HTML (timestamp, affected
     release, failing scenario, suggested PATCH bump)
   - Output path: `.dadaia/reports/<context>/qa-engineer/<ts>-hotfix-candidate.html`

3. `dadaia_workspace/public/agents/devops-engineer.md`:
   - Branch governance: push em `hotfix/v<M>.<m>.<p>` só aceita bump PATCH; CI rejeita
     MAJOR/MINOR em branch que começa com `hotfix/`

### Camada 4 — Constitution edit

1. `specs/constitution.md` L148: substituir bullet "Versão atômica" por:
   > **Versão atômica**: specs ativas em `specs/releases/<v-id>/` representam apenas o
   > estado atual; specs encerradas vão para `specs/_archive/releases/<v-id>/`. Hotfix
   > releases (PATCH≥1) seguem o mesmo caminho. Não há rascunhos órfãos fora dessas
   > trilhas.
2. Requer explicit operator confirmation per product-engineer agent contract

### Camada 5 — Workflow

1. Criar `dadaia_workspace/public/workflows/hotfix-release.workflow.md` (4 stages):
   - `file_hotfix_candidate` (qa-engineer ou operador): bullet em `## Hotfixes pendentes`
   - `promote_to_release` (product-engineer): atribui `v<M>.<m>.<p+1>`, move bullet para
     `## Histórico`, cria `specs/releases/<v-id>/`, atualiza `ACTIVE.md`
   - `apply_fix` (implementer): TASKS com marker `[-]`, fluxo padrão
   - `close_with_smoke` (product-engineer): CLOSURE.md com smoke evidence (D25), memory
     update opcional (D16), `git mv` para `_archive/releases/`
2. `bug-fix-fastlane.workflow.md` ganha adendo no header (D10): comentário curto
   instruindo que fixes que toquem `specs/memory/product/*` devem migrar para hotfix
   release (filing em `## Hotfixes pendentes`)

### Camada 6 — CI

1. `.github/workflows/ci.yml` (D19): `on.push.branches` ganha `'hotfix/v*'`
2. Job adicional simples que valida formato SemVer do branch name (`hotfix/v<M>.<m>.<p>`)
   antes de continuar — rejeita `hotfix/v1.0` ou `hotfix/v1.0.0-beta`
3. Job `specs-doctor` continua chamando `dadaia specs doctor --specs-dir specs` — já cobre
   novos checks

### Camada 7 — Smoke-test end-to-end

1. Criar hotfix release sintética `v0.0.1` em branch local (não merge) usando
   `dadaia specs hotfix open v0.0.1 --patches agent-sdd-alignment-v1 --severity LOW`
2. Verificar:
   - Doctor green com release sintética presente
   - Gate trata `specs/releases/v0.0.1/TASKS.md` como qualquer outra TASKS
   - Backlog dual-section validation funciona (criar bullet de teste em `## Hotfixes pendentes`)
   - SemVer regex rejeita folder mal-formado (`specs/releases/v9.bad/`)
3. Tear down: `git restore .`

---

## Sequência de tasks (precondições)

Cada task em `TASKS.md` é paralelizável quando write-set é disjunto.

```
T1 (doctor: SemVer regex + backlog dual-section)
└── T7 (CI ci.yml) ──── T8 (smoke-test)
T2 (templates + scaffolder + CLI) ──── T8 (smoke-test)
T3 (agentes 3 patches) ──── T6 (workflow hotfix-release)
T4 (constitution L148 edit)
T5 (bug-fix-fastlane header adendo)
T9 (dadaia public stage && install --target all) ← depende T1..T6
T_CLOSE (CLOSURE desta release) ← depende T9 + operator approval
```

Tasks T1, T2, T3, T4, T5 podem rodar em paralelo em branches separadas (write-sets disjuntos):
- T1: `dadaia_workspace/features/specs/doctor.py`, `tests/`
- T2: `dadaia_workspace/public/templates/*.j2`, `dadaia_workspace/features/specs/scaffolder.py`, `dadaia_workspace/cli/commands/specs.py`
- T3: `dadaia_workspace/public/agents/{product,qa,devops}-engineer.md`
- T4: `specs/constitution.md`
- T5: `dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md`

T6 depende de T3 (workflow referencia agentes patchados). T7 depende de T1 (CI roda doctor
estendido). T8 (smoke-test) depende de T1 + T2. T9 depende de tudo. T_CLOSE é operator-gated.

---

## Riscos do PLAN (que não cabiam no SPEC)

| Risco | Mitigação |
|---|---|
| Doctor `SPEC-DOC-012` estendido quebrar parsing existente | Adicionar dual-regex como alternativa; manter regex existente para `## Candidatas ativas`; novo regex só para `## Hotfixes pendentes` |
| `BACKLOG_HOTFIX_RE` muito rígido na adoção inicial | Severity WARNING durante 2 semanas (até 2026-05-30), ERROR depois |
| Scaffolder permitir PATCH=0 acidentalmente em hotfix | Validation explícita no scaffolder + CLI; doctor faz double-check via SemVer regex (não distingue feature/hotfix mas valida formato) |
| Smoke-test commit acidental para main | T8 termina com `git restore .` + `git status` clean verification |
| `dadaia public install --force` sobrescrever projeções customizadas | Documentado em T9: `--force` só após `dadaia public doctor` mostrar entries em drift |
| Constitution edit (T4) interpretado como mudança de produto | T4 é meta-edit; muda apenas redação de uma bullet; operator confirmation explícito |
| Workflow `hotfix-release.workflow.md` colidir com `bug-fix-fastlane` | Tabela em SPEC §"Quando usar..." é canonical; agentes leem na onboard |
| 72h cutoff em `## Hotfixes pendentes` ser arbitrário | Configurável via `doctor` flag (`--hotfix-stale-hours`); default 72h |
| Bullet movido para `## Histórico` quebrar histórico existente | `## Histórico` já existe em candidates.md; mantém formato atual (com data + release-id) |

---

## Verificação end-to-end (a executar em IMPLEMENTATION)

| # | Check | Comando | Esperado |
|---|---|---|---|
| 1 | Doctor valida SemVer regex em releases novas | criar `specs/releases/v0.0.1/`; `dadaia specs doctor` | 0 errors (cutoff exclui) ou 0 warnings após cutoff se SemVer válido |
| 2 | Doctor flagra folder name mal-formado | renomear para `specs/releases/v1-bad/`; doctor | SPEC-DOC-016 ERROR (após cutoff) |
| 3 | Doctor valida `## Hotfixes pendentes` regex | adicionar bullet conforme formato; doctor | 0 errors |
| 4 | Doctor flagra bullet mal-formado em `## Hotfixes pendentes` | bullet sem timestamp; doctor | SPEC-DOC-012 ERROR (após grace period) |
| 5 | Doctor warn em hotfix stale > 72h | bullet com timestamp -75h; doctor | SPEC-DOC-012 WARNING |
| 6 | Scaffolder cria hotfix release | `dadaia specs hotfix open v0.0.1 --patches agent-sdd-alignment-v1 --severity LOW` | árvore criada; idempotente |
| 7 | Scaffolder rejeita PATCH=0 | `dadaia specs hotfix open v0.1.0 --patches X --severity LOW` | error: hotfix requer PATCH≥1 |
| 8 | Gate funciona em hotfix release | `[-]` em `specs/releases/v0.0.1/TASKS.md`; edit production | allowed (sem mudança no gate) |
| 9 | CI passa em branch `hotfix/v0.0.1` | push branch, observa CI | jobs green |
| 10 | CI rejeita branch hotfix com MINOR bump | push `hotfix/v0.1.0` | job rejeita |
| 11 | Constitution L148 atualizado | `grep "Versão atômica" specs/constitution.md` | nova redação aparece |
| 12 | `dadaia public doctor` ok pós-projeção | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | `[ok]` em todos targets |

---

## Out of scope reaffirmados

- Implementação efetiva acontece em IMPLEMENTATION (sessão futura)
- Migração das 10 releases legados (Vintage bucket)
- Workflow `hotfix-release.workflow.md` é criado na próxima sessão (T6), não nesta
- PyPI publish, pre-release tags, multi-repo hotfix orchestration

---

## Definition of Done (desta sessão)

- SPEC.md, PLAN.md, TASKS.md commited com `**Status:** Aprovado`
- `dadaia specs doctor` → 0 errors, 0 warnings
- `specs/releases/ACTIVE.md` aponta para `sdd-hotfix-track-v1`, `phase: TASKS` (single-pointer)
- Grill report atualizado com "Refactor amendment" em `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md`
- PLAN.md ≤ 200 linhas (target); ≤ 300 absoluto

---

## Referências

- SPEC desta release: `specs/releases/sdd-hotfix-track-v1/SPEC.md`
- Discovery reports:
  - `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-16T214611Z-hotfix-track.md`
  - `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T214645Z-hotfix-track.md`
  - `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md` (com Refactor amendment)
- Constitution: `specs/constitution.md` (L148 alvo de T4)
- Gate atual (inalterado): `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
- Doctor atual (alvo de T1): `dadaia_workspace/features/specs/doctor.py`
- Scaffolder (alvo de T2): `dadaia_workspace/features/specs/scaffolder.py`
- Workflow legado (preservado, D10): `dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md`
