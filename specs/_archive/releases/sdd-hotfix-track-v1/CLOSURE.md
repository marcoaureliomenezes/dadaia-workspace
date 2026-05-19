# Closure: Release — sdd-hotfix-track-v1

> **Status:** Aprovado
> **Release ID:** sdd-hotfix-track-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-16
> **Spec:** `specs/releases/sdd-hotfix-track-v1/SPEC.md`
> **Plan:** `specs/releases/sdd-hotfix-track-v1/PLAN.md`
> **Tasks:** `specs/releases/sdd-hotfix-track-v1/TASKS.md`

---

## Summary

Release `sdd-hotfix-track-v1` introduziu **versionamento SemVer (`vMAJOR.MINOR.PATCH`)** no
Spec Context Project `dadaia-workspace` e formalizou a **diferenciação de hotfix release** por
PATCH≥1 — sem criar trilha paralela. Toda release passa a viver sob
`specs/releases/v<M>.<m>.<p>/` (feature: `PATCH=0`; hotfix: `PATCH≥1`), com fluxo condensado para
hotfix (SPEC + TASKS obrigatórios, PLAN opcional, CLOSURE com smoke evidence obrigatório).
A origem do hotfix é fixada: ele só entra em release se foi reportado na nova seção
`## Hotfixes pendentes` de `specs/backlog/candidates.md`.

Nove tasks (T1–T9) foram executadas em três waves (paralelas onde write-sets disjuntos
permitiam). O gate v3 **não foi alterado** — hotfix é uma release como qualquer outra do
ponto de vista do gate. Os deltas mecânicos vivem em doctor (SPEC-DOC-016 + SPEC-DOC-012
estendido), templates (`release_hotfix.md.j2`, `closure_hotfix.md.j2`) + scaffolder + CLI
(`dadaia specs hotfix open`), agentes (product/qa/devops), constitution (L148),
workflow (novo `hotfix-release.workflow.md` + adendo em `bug-fix-fastlane.workflow.md`),
CI (branch trigger `hotfix/v*` + validação SemVer) e propagação via `dadaia public install`.

---

## Drifts

### refactor-mid-flight (operator simplification)

**Description:** Cinco minutos após o rascunho inicial do SPEC (design com folder paralelo
`specs/hotfix/<hotfix-id>/`, single-file `HOTFIX.md`, status ladder hotfix-específico
`Aberto→Aplicado→Encerrado`, ACTIVE.md dual-pointer e gate v3 modificado, totalizando 21
decisões e 12 tasks), o operador rejeitou a complexidade e impôs simplificação radical:
**hotfix é uma release como qualquer outra**, diferenciada apenas pelo PATCH≥1 no folder
name.

**Resolution:** SPEC + PLAN + TASKS reescritos em-place. Decisões reduzidas de 21 para 15
(D7/D8/D9/D12 parcial/D20 canceladas; D22/D23/D24/D25 introduzidas). Tasks reduzidas de 12
para 9 + T_CLOSE. Reversões detalhadas em
`.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md`
seção "Refactor amendment". Nenhuma criação de `specs/hotfix/` ocorreu — design rejeitado
nunca tocou o disco.

**Impact:** zero — refactor aconteceu antes de qualquer task de implementação. O gate v3
permanece intocado (D6); o catch-22 do design anterior (gate precisa entender 2 trilhas)
foi eliminado por construção.

---

## Validations

Evidence triples (description, command, evidence) para cada task entregue.

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T1 | doctor.py SemVer regex (SPEC-DOC-016) + backlog dual-section (SPEC-DOC-012 estendido) | `pytest tests/unit/features/specs/test_doctor.py -q` green; `dadaia specs doctor --specs-dir specs` 0 errors em `dadaia-workspace` | Testes adicionados (2 pos + 2 neg SPEC-DOC-016; 2 pos + 2 neg SPEC-DOC-012 estendido; 1 pos + 1 neg 72h cutoff); doctor green pós-merge |
| T2 | Templates (`release_hotfix.md.j2`, `closure_hotfix.md.j2`) + scaffolder + CLI command | `dadaia specs hotfix open v0.0.1 --patches agent-sdd-alignment-v1 --severity LOW` cria árvore esperada | Comando rodou em smoke-test (T8) criando `specs/releases/v0.0.1/{SPEC,TASKS}.md`; rejeição correta de PATCH=0 e SemVer inválido |
| T3 | Agentes 3 patches surgical (product/qa/devops) | `grep "Hotfix release lifecycle" dadaia_workspace/public/agents/product-engineer.md` retorna 1+ hit; idem para qa-engineer "Hotfix candidate filing" e devops-engineer "Branch governance" hotfix note | Greps confirmaram presença das 3 subseções; voz dos agentes preservada |
| T4 | Constitution L148 edit (D17) | `grep -A1 "Versão atômica" specs/constitution.md` mostra nova redação; `dadaia specs doctor` green | L148 reescrita inclui hotfix releases (PATCH≥1) seguindo mesmo caminho de archive; operator confirmation registrada |
| T5 | bug-fix-fastlane: adendo de enforcement no header (D10) | `grep "Hotfixes pendentes" dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md` retorna 1 hit | Comentário no header instrui migração para hotfix release quando memory deve ser tocado |
| T6 | Workflow `hotfix-release.workflow.md` (criação) | YAML parse válido; `grep "name: hotfix-release" dadaia_workspace/public/workflows/hotfix-release.workflow.md` 1 hit | 4 stages criados (file_hotfix_candidate → promote_to_release → apply_fix → close_with_smoke); cada stage com expected_output |
| T7 | CI: `ci.yml` branch trigger + SemVer branch validation (D19) | push em `hotfix/v0.0.1` triggera CI; push em `hotfix/v0.0` rejeitado | `on.push.branches` ganhou `'hotfix/v*'`; job de validação rejeita MAJOR/MINOR/pré-release |
| T8 | Smoke-test end-to-end (doctor + scaffolder + backlog) | Matriz de 12 checks de PLAN §"Verificação end-to-end" pass; `git status` clean após `git restore .` | Todos os 12 checks pass: doctor SemVer, hotfix-pendentes regex, 72h WARNING, scaffolder happy/idempotent/PATCH=0/SemVer inválido, gate aceita hotfix release, CI green/rejeita malformado, constitution L148 atualizado, `dadaia public doctor` ok |
| T9 | `dadaia public stage && install --target all` | `dadaia public doctor` retorna `[ok]` em todos targets; `dadaia specs doctor` green | Projeções atualizadas em `.agents/`, `.claude/agents/`, `.codex/`, `.opencode/`; manifest.json refresh; sem drift |

---

## Memory updates

- `specs/memory/product/sdd-hotfix-track.html` — **criado** (novo feature card). Documenta:
  layout SemVer único em `specs/releases/`, regra D4 (origem obrigatória via
  `## Hotfixes pendentes`), fluxo condensado (SPEC + TASKS obrigatórios, PLAN opcional,
  CLOSURE com smoke evidence), comando `dadaia specs hotfix open`, doctor SPEC-DOC-016 +
  SPEC-DOC-012 estendido, gate inalterado (D6).
- `specs/memory/product/index.html` — **atualizado**: nova entry no catálogo apontando para
  `sdd-hotfix-track.html`. Reordenação reflete relevância no dia-a-dia
  (ordem mantida; entry adicionada antes de `academy.html` por proximidade conceitual com
  `sdd-gate-v3.html` e `specs-doctor.html`).
- Nenhum dos outros HTMLs de memory (`workspace-init`, `context-management`,
  `agent-orchestration`, `public-asset-distribution`, `workspace-doctor`, `specs-doctor`,
  `sdd-gate-v3`, `academy`, `workspace-portability`, `repos-catalog`, `server-registry`)
  foi tocado — esta release adicionou capability nova, não alterou comportamento das
  existentes.

---

## Backlog returns

Adicionados a `specs/backlog/candidates.md § Candidatas ativas` (D18 / SPEC §"Backlog gerado"):

- `panel-patch-terminology` — Reconciliar uso colloquial de "PATCH" em
  `dadaia-workspace-panel-v1/PLAN.md` L76-78 com SemVer PATCH agora reservado para hotfix
  release (owner: product-engineer)
- `hotfix-release-workflow` — Já criado em T6, mas backlog item registra futuras iterações
  (e.g., dry-run mode, automatic version bump) (owner: product-engineer)
- `vintage-bucket-doc` — Documentar Vintage bucket em `docs/sdd-migration-playbook.md` com
  lista das 10 releases pré-SemVer (owner: software-engineer)

Adicionada nova seção `## Hotfixes pendentes` (vazia inicialmente) — referenciada pela
nova extensão SPEC-DOC-012 implementada em T1.

Entry `sdd-hotfix-track` movida de `## Candidatas ativas` para `## Histórico` com data
2026-05-16 e release-id `sdd-hotfix-track-v1`.

---

## Archive decision

**MOVE** — diretório `specs/releases/sdd-hotfix-track-v1/` será relocado para
`specs/_archive/releases/sdd-hotfix-track-v1/` via `git mv` após este CLOSURE ser
gravado e os memory updates concluídos. `ACTIVE.md` transita para
`release: none / phase: none` indicando ausência de release ativa pós-archival.
