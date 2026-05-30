# Closure: Release — spec-context-tree-v2

> **Status:** Aprovado
> **Release ID:** spec-context-tree-v2
> **Owner:** product-engineer
> **Closed:** 2026-05-30

## Summary

Esta release entregou o **canonical `specs/` tree v2** como novo baseline do scaffold de consumer repos (`dadaia_workspace/public/scaffold/`). O scaffold anterior estava desatualizado em relação ao modelo SDD em produção: ainda carregava `foundation/`, root `SPEC.md`, arquivos de memory em Markdown, e ausência dos diretórios `backlog/`, `bugs/` e `releases/`. Um workspace recém-scaffoldado falhava no `dadaia specs doctor` — o que invalidava o onboarding de novos consumer repos.

O coração da release foi o alinhamento do scaffold com o modelo que o próprio repo dadaia-workspace já usava. Foundation foi removida, root SPEC.md foi depreciada, memory HTML tornou-se obrigatória com o catalog folder (`memory/product/index.html`), e os três diretórios de lifecycle (`backlog/`, `bugs/`, `releases/`) foram adicionados com READMEs e `.gitkeep`. O `specs/AGENTS.md` template foi introduzido como contrato SDD legível para o operador do consumer repo.

Sete invariantes TREE-1 a TREE-7 foram adicionados ao `dadaia specs doctor`, com políticas distintas de auto-fix (`--fix`) para os casos tratáveis (TREE-3 regenera `product/index.html`, TREE-4 recria diretórios ausentes) e warn-only com migration guard para os casos que exigem decisão humana (TREE-1, TREE-2). O gate `sdd-spec-gate.sh` teve o fallback legacy de root-`TASKS.md` removido (T-8a), completando a primeira metade da migração gate v3 — a gate agora busca tasks exclusivamente em `releases/<active>/TASKS.md`. Três novos CLIs (`dadaia release new`, `dadaia backlog new`, `dadaia bug new`) e `dadaia migrate tree-v2` fecham o ciclo de onboarding e migração sem edição manual de frontmatter.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-1 | Remove `foundation/` from scaffold; service.py:119 fallback cleanup; `dadaia migrate tree-v2` for foundation | `138c911` |
| T-2 | Scaffold memory as HTML (architecture.html + tech-stack.html); drop markdown memory files | `138c911` |
| T-4 | Scaffold `backlog/`, `bugs/`, `releases/` with README.md and `.gitkeep` | `138c911` |
| T-5 | New template `specs/AGENTS.md` (SDD workflow contract) | `138c911` |
| T-6 | Deprecate root `specs/SPEC.md`; remove from scaffold; `dadaia migrate tree-v2` for root SPEC.md | `138c911` |
| T-8a | Gate cleanup: remove legacy root-TASKS.md fallback path | `138c911` |
| T-3 | Mandatory `memory/product/index.html`; `dadaia memory product add <slug>` CLI | `77aadaa` |
| T-7 | New CLI: `dadaia release new`, `dadaia backlog new`, `dadaia bug new` | `77aadaa` |
| T-9 | Doctor TREE-1..7 invariants + `--fix` auto-fix (TREE-3/4) + migration guard (TREE-1/2) | `fae7fdb` |
| T-QA | Full test suite green; AC-O-1 onboarding E2E; QA gate APPROVED | `ef672d4` |
| T-DEVOPS | `dadaia public stage && dadaia public install --target all`; `dadaia public doctor` exits 0 | `aa8788c` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green — zero regressions | `poetry run pytest` | 2078 passed, 0 failed, 1 skipped, 1 xpassed, 89.48% coverage |
| SDD tree structural health of dadaia-workspace repo | `dadaia specs doctor` | exit 0 (1 warn-only: repo's own `specs/AGENTS.md` absent — see Drifts) |
| Runtime projection parity after propagation | `dadaia public doctor` | exit 0, 0 drift, 0 missing, 221 [ok] |
| TREE invariants unit coverage (54 test fns, ≥2 refs per TREE-* invariant) | `pytest tests/unit/features/specs/test_doctor.py` | 54 test fns / 77 TREE refs; AC-T9-15 fresh-scaffold exit 0; AC-T9-16 repo-self exit 0 |
| Onboarding E2E (AC-O-1): scaffold → v2 tree → 0 TREE-* issues | `pytest tests/integration/test_onboarding_tree_v2_e2e.py` | copytree-from-scaffold → v2 tree → 0 TREE-* issues; QA sidecar `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T170000Z-spec-context-tree-v2-qa.handoff.json` |
| Propagation parity (devops) | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | devops sidecar `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-30T000000Z-spec-context-tree-v2-devops.handoff.json` |

## Drifts

### repo-own-agents-md-absent

**Description:** O invariante TREE-5 emite um warning para `specs/AGENTS.md` ausente. O repo dadaia-workspace em si não tem esse arquivo em `specs/` — apenas o scaffold e os consumer repos terão. R1 deliberadamente tinha como alvo o consumer scaffold (`public/scaffold/`), não a árvore interna do lib. O `dadaia specs doctor` emite 1 TREE-5 warning (exit 0, não-bloqueante).

**Resolution:** Benign — exit 0, não bloqueia CI. Segue-up opcional: adotar o `specs/AGENTS.md` na própria árvore do lib em release futura se o operador considerar útil. Não requer mudança em memory.

**Memory updates:** none.

### panel-integration-tests-couple-to-gitignored-staging

**Description:** Descoberta durante T-9 (commit `4120b88`): 11 testes de integração do panel dependiam do staging gitignored `.dadaia/agentic/` (deletado pelo cleanup do go-open-source) e assertavam um agent id retirado (`software-engineer`). O scaffold não causou esse drift — o problema pré-existia, mas foi exposto pelos novos testes de T-9 que fazem staging hermético via `tmp_path`.

**Resolution:** Corrigido com fixtures de staging herméticas via `tmp_path` e atualização dos agent ids para `software-engineer-python`. Bug registrado em `specs/bugs/panel-integration-tests-couple-to-gitignored-staging.md` via `dadaia bug new` (dogfood do novo CLI). Não causado por R1.

**Memory updates:** none — bug de fixture, sem mudança funcional visível na feature.

### preexisting-untracked-drafts

**Description:** A working tree carrega itens pré-existentes não relacionados a R1: `specs/_archive/releases/orchestration-consolidation-v1/{PLAN,TASKS}.md` modificados e diretórios draft `design-first-gate-v1/` e `agent-monitoring-r2-v1/` não commitados. R1 não tocou nenhum desses caminhos.

**Resolution:** Deixados intactos por R1. Flagged para triage do operador em sessão futura. Não afetam a validade do CLOSURE.

**Memory updates:** none.

## Memory updates

- `specs/memory/product/specs-doctor.html` — adicionados os sete invariantes TREE-1..7 e a capacidade `--fix` com políticas por invariante (auto-fix TREE-3/4; warn-only TREE-1/2/5; no-fix TREE-6/7); contagem de checks atualizada de 12 para 19 (12 SPEC-DOC + 7 TREE); migration guard documentado para TREE-1/2.
- `specs/memory/product/sdd-gate-v3.html` — T-8a: gate agora busca tasks exclusivamente em `releases/<active>/TASKS.md`; fallback legacy de root-`TASKS.md` removido. Diagrama de sequência atualizado para refletir o caminho único.
- `specs/memory/product/context-management.html` — documentado o canonical specs/ tree v2: `foundation/` + root `SPEC.md` depreciados; `backlog/`, `bugs/`, `releases/` adicionados; memory HTML obrigatória com folder catalog `memory/product/index.html`; novos CLIs `dadaia release new`, `dadaia backlog new`, `dadaia bug new`, `dadaia memory product add`, `dadaia migrate tree-v2`; invariantes TREE-1..7 com policies de fix.
- `specs/memory/product/index.html` — `meta` atualizado para closure: spec-context-tree-v2 / 2026-05-30. Catálogo sem alteração de ordem ou entradas.

## Backlog returns

- `backlog/ideas.md` ← Adotar `specs/AGENTS.md` no próprio repo dadaia-workspace (TREE-5 warn é benign; follow-up opcional).
- `backlog/candidates.md` ← **spec-context-session-locks-v1 (R2)** desbloqueada: R1 phase ARCHIVED libera R2 para entrar em IMPLEMENTATION. R2 completa a gate v3 com per-release context resolution (T-13) que depende de T-8a já shipped.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/spec-context-tree-v2/` via `git mv`. ACTIVE.md will be updated to point to `spec-context-session-locks-v1` or `release: none` if not yet opened.
