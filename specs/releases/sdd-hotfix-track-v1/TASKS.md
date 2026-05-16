# Tasks: Release — sdd-hotfix-track-v1

> **Status:** Aprovado
> **Release ID:** sdd-hotfix-track-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Refactored:** 2026-05-16 (operator simplification — see SPEC §"Drifts conhecidos")
> **Plan:** `specs/releases/sdd-hotfix-track-v1/PLAN.md`

Implementer: software-engineer (executa T1, T2, T3, T4, T5, T6, T8) + devops-engineer
(executa T7, T9) + product-engineer (executa T_CLOSE).

Cada task tem precondições explícitas. Marcas: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Gate v3 libera production write quando alguma TASKS.md tem `[-]`. Tasks são paralelizáveis
quando write-sets são disjuntos.

---

## T1 — doctor.py: SemVer regex (SPEC-DOC-016) + backlog dual-section (SPEC-DOC-012 estendido)

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Precondições:** nenhuma
- **Paraleliza com:** T2, T3, T4, T5
- **Files modified:**
  - `dadaia_workspace/features/specs/doctor.py`
  - `tests/unit/features/specs/test_doctor.py`
- **Mudanças:**
  - Adicionar `RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")` (D3)
  - Adicionar `RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)`, `RELEASE_SEMVER_HARD = date(2026, 7, 1)`
  - Adicionar `BACKLOG_HOTFIX_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}T\d{6}Z) (LOW|MEDIUM|HIGH|CRITICAL) ([\w\-/]+) — .+ \(post-mortem: .+\)$")` (D22)
  - Novo `_check_release_semver_naming` (SPEC-DOC-016, WARNING→ERROR): walk `specs/releases/*/`;
    aplica `RELEASE_SEMVER_RE` quando `Created:` ≥ `RELEASE_SEMVER_CUTOFF`. Vintage skip
    (`Created:` ≤ 2026-05-17). WARNING até `RELEASE_SEMVER_HARD`, ERROR após
  - Estender `_check_backlog_format` (SPEC-DOC-012): validar **duas** seções de
    `specs/backlog/candidates.md` — `## Candidatas ativas` (regex existente) e
    `## Hotfixes pendentes` (novo `BACKLOG_HOTFIX_RE`); WARNING quando bullet em
    `## Hotfixes pendentes` tem timestamp > 72h sem ter sido movido (D23)
  - Adicionar todos a `check()` em ordem
- **Tests:**
  - 2 positivos + 2 negativos para SPEC-DOC-016
  - 2 positivos + 2 negativos para SPEC-DOC-012 estendido
  - 1 teste positivo para 72h cutoff (timestamp -75h → WARNING)
  - 1 teste negativo (timestamp -10h → ok)
- **Aceite:** `pytest tests/unit/features/specs/test_doctor.py -q` green; `dadaia specs doctor --specs-dir specs` 0 errors em `dadaia-workspace`

---

## T2 — Templates (release_hotfix.md.j2, closure_hotfix.md.j2) + scaffolder + CLI command

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Precondições:** nenhuma (templates standalone)
- **Paraleliza com:** T1, T3, T4, T5
- **Files created:**
  - `dadaia_workspace/public/templates/release_hotfix.md.j2`
  - `dadaia_workspace/public/templates/closure_hotfix.md.j2`
- **Files modified:**
  - `dadaia_workspace/features/specs/scaffolder.py`
  - `dadaia_workspace/cli/commands/specs.py`
  - `tests/unit/features/specs/test_scaffolder.py`
- **Mudanças:**
  - `release_hotfix.md.j2` (D24): SPEC template enxuto (≤100 linhas) com header
    (`**Status:** Draft`, `**Release ID:** v<M>.<m>.<p>`, `**Patches release:**`, `**Severity:**`,
    `**Created:**`) + 6 seções obrigatórias: `## Incident summary`, `## Affected memory features`,
    `## Root cause`, `## Fix scope` (declara se requer PLAN), `## Rollback plan`,
    `## Acceptance + smoke test`
  - `closure_hotfix.md.j2` (D25): header + `## Drifts`, `## Validations` (tabela 3-col
    com placeholder para evidence triple: description, command, evidence), `## Memory updates`
    (default "Nenhum")
  - `scaffold_hotfix_release(specs_dir, version_id, patches_release_id, severity, templates_dir, force=False)`
    em scaffolder.py: valida `RELEASE_SEMVER_RE.match(version_id)`, valida PATCH≥1,
    valida `patches_release_id` resolve sob `releases/` ou `_archive/releases/`. Cria
    `specs/releases/<version_id>/SPEC.md` (renderizado) + `TASKS.md` (stub com 0 tasks)
  - CLI command `dadaia specs hotfix open <version-id> --patches <release-id> [--severity LOW|MEDIUM|HIGH|CRITICAL]`
    em `cli/commands/specs.py`. Imprime warning se não houver bullet correspondente em
    `## Hotfixes pendentes` (auditoria humana per D4)
- **Tests:** happy path; idempotência; PATCH=0 rejeitado; SemVer regex inválido rejeitado; patches-release-id inválido rejeitado
- **Aceite:** `dadaia specs hotfix open v0.0.1 --patches agent-sdd-alignment-v1 --severity LOW` cria árvore esperada

---

## T3 — Agentes: 3 surgical patches (product/qa/devops)

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Precondições:** nenhuma
- **Paraleliza com:** T1, T2, T4, T5
- **Files modified:**
  - `dadaia_workspace/public/agents/product-engineer.md`
  - `dadaia_workspace/public/agents/qa-engineer.md`
  - `dadaia_workspace/public/agents/devops-engineer.md`
- **Mudanças (surgical, voz preservada):**
  - product-engineer.md: nova subseção "Hotfix release lifecycle" após release-lifecycle
    descrevendo fluxo condensado (SPEC + TASKS obrigatórios; PLAN opcional; CLOSURE com
    smoke evidence). Regra dura: hotfix só sai de `## Hotfixes pendentes` (D4). Folder
    name é `v<M>.<m>.<p>` com PATCH≥1 (D3). Status ladder canonical (não há ladder
    hotfix-específico) (D2)
  - qa-engineer.md: subseção "Hotfix candidate filing" descrevendo stub HTML (timestamp,
    affected release, failing scenario, suggested PATCH bump) em
    `.dadaia/reports/<context>/qa-engineer/<ts>-hotfix-candidate.html`
  - devops-engineer.md: nota em "Branch governance" sobre push em `hotfix/v<M>.<m>.<p>`
    aceitar apenas bump PATCH; CI rejeita MAJOR/MINOR
- **Aceite:** `grep "Hotfix release lifecycle" dadaia_workspace/public/agents/product-engineer.md` retorna 1+ hit; idem para qa/devops

---

## T4 — Constitution L148 edit (D17)

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Precondições:** **explicit operator confirmation** (constitution edit per product-engineer agent contract)
- **Paraleliza com:** T1, T2, T3, T5
- **Files modified:** `specs/constitution.md`
- **Mudanças:** L148, substituir bullet "Versão atômica" por:
  ```
  - **Versão atômica**: specs ativas em `specs/releases/<v-id>/` representam apenas o estado atual; specs encerradas vão para `specs/_archive/releases/<v-id>/`. Hotfix releases (PATCH≥1) seguem o mesmo caminho. Não há rascunhos órfãos fora dessas trilhas.
  ```
- **Aceite:** `grep -A1 "Versão atômica" specs/constitution.md` mostra nova redação; `dadaia specs doctor` green

---

## T5 — bug-fix-fastlane: adendo de enforcement no header (D10)

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Precondições:** nenhuma
- **Paraleliza com:** T1, T2, T3, T4
- **Files modified:** `dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md`
- **Mudanças:** adicionar comentário no header indicando que fixes que requerem update
  em `specs/memory/product/*.html` devem migrar para hotfix release (filing em
  `specs/backlog/candidates.md` seção `## Hotfixes pendentes`). Sem outras alterações
- **Aceite:** `grep "Hotfixes pendentes" dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md` retorna 1 hit

---

## T6 — Workflow hotfix-release.workflow.md (criação)

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Precondições:** T3 [x] (referencia agentes patchados)
- **Paraleliza com:** T7, T8
- **Files created:** `dadaia_workspace/public/workflows/hotfix-release.workflow.md`
- **Mudanças:** YAML frontmatter + 4 stages:
  - `file_hotfix_candidate` (qa-engineer ou operador): bullet em `## Hotfixes pendentes`
  - `promote_to_release` (product-engineer): atribui `v<M>.<m>.<p+1>`, move bullet para
    `## Histórico`, cria `specs/releases/<v-id>/`, atualiza `ACTIVE.md`
  - `apply_fix` (implementer): TASKS marker `[-]`, fluxo padrão
  - `close_with_smoke` (product-engineer): CLOSURE.md com smoke evidence; memory update
    opcional; `git mv` para `_archive/releases/`
  - Cada stage com `expected_output` path
- **Aceite:** YAML parse válido; `grep "name: hotfix-release" dadaia_workspace/public/workflows/hotfix-release.workflow.md` 1 hit

---

## T7 — CI: ci.yml branch trigger + SemVer branch validation

- [x] **Status:** DONE
- **Owner:** devops-engineer
- **Precondições:** T1 [x] (doctor deve aceitar novos formatos antes de CI rodar)
- **Paraleliza com:** T6, T8
- **Files modified:** `.github/workflows/ci.yml`
- **Mudanças:**
  - `on.push.branches`: adicionar `'hotfix/v*'`
  - Job step adicional em `lint` ou novo job pequeno que valida branch name SemVer
    (`hotfix/v<M>.<m>.<p>` com PATCH≥1) — rejeita `hotfix/v1.0` ou `hotfix/v1.0.0-beta`
  - `specs-doctor` job inalterado (cobre novos checks automaticamente)
- **Aceite:** push em `hotfix/v0.0.1` triggera CI; push em `hotfix/v0.0` rejeitado

---

## T8 — Smoke-test end-to-end (doctor + scaffolder + backlog)

- [ ] **Status:** OPEN
- **Owner:** devops-engineer
- **Precondições:** T1 [x], T2 [x]
- **Paraleliza com:** T6, T7 (read-only sobre seus outputs)
- **Files touched (temporário, revertido ao final):**
  - `specs/releases/v0.0.1/SPEC.md`, `TASKS.md` (criados via scaffolder)
  - `specs/backlog/candidates.md` (temp: bullet em `## Hotfixes pendentes`)
- **Mudanças:** executar a matriz de 12 checks de §"Verificação end-to-end" do PLAN
- **Aceite:** todos os 12 checks pass; `git status` clean após `git restore .`

---

## T9 — `dadaia public stage && install --target all`

- [ ] **Status:** OPEN
- **Owner:** devops-engineer
- **Precondições:** T1..T8 todos [x]
- **Paraleliza com:** nenhuma (operação serializada por design)
- **Files modified:** `.agents/skills/...`, `.claude/agents/...`, `.codex/...`, `.opencode/...` (projeções)
- **Mudanças:** `dadaia public stage` → atualiza `.dadaia/agentic/`; `dadaia public install --target all` → propaga; `dadaia public doctor` → entries em `[ok]`
- **Aceite:** `dadaia public doctor` retorna `[ok]` em todos targets; `dadaia specs doctor` green

---

## T_CLOSE — CLOSURE desta release (sdd-hotfix-track-v1)

- [ ] **Status:** OPEN
- **Owner:** product-engineer
- **Precondições:** T9 [x] + explicit operator approval
- **Paraleliza com:** nenhuma
- **Files modified:**
  - `specs/releases/sdd-hotfix-track-v1/CLOSURE.md` (criado)
  - `specs/releases/ACTIVE.md` (phase: CLOSURE temporariamente, depois empty)
  - `specs/memory/product/sdd-hotfix-track.html` (criado — feature card)
  - `specs/memory/product/index.html` (atualizado: nova entry no catálogo)
  - `specs/backlog/candidates.md` (3 novos itens da SPEC §"Backlog gerado" + nova seção `## Hotfixes pendentes` vazia)
  - `specs/_archive/releases/sdd-hotfix-track-v1/` (git mv após CLOSURE)
- **Mudanças:**
  - CLOSURE.md com `## Drifts`, `## Validation` (evidence triples para T1-T9), `## Memory updates`
  - Em CLOSURE: atualizar memory HTMLs
  - Em ARCHIVED: `git mv specs/releases/sdd-hotfix-track-v1 specs/_archive/releases/`
- **Aceite:**
  - `dadaia specs doctor` green
  - `ACTIVE.md` aponta para `release: none / phase: none` (ou próxima release)
  - Entry no histórico de `backlog/candidates.md` movida da seção "Candidatas ativas" para "Histórico"
  - Seção `## Hotfixes pendentes` existe (vazia ou com bullets reais)

---

## Resumo da matriz de paralelismo

```
Wave 0 (paralelo):   T1, T2, T3, T4, T5   (write-sets disjuntos)
Wave 1 (paralelo):   T6 (depende T3), T7 (depende T1), T8 (depende T1+T2)
Wave 2:              T9 (depende T1..T8)
Wave 3:              T_CLOSE (depende T9 + operator)
```

Nesta sessão (criação de SPEC+PLAN+TASKS) nenhuma task acima é executada — todas começam
OPEN. A reserva (`[ ]` → `[-]`) acontece em sessão futura quando o implementer entrar.
