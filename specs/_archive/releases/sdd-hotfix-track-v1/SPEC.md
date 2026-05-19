# Spec: Release — sdd-hotfix-track-v1

> **Status:** Aprovado
> **Release ID:** sdd-hotfix-track-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Refactored:** 2026-05-16 (operator simplification adopted mid-flight — see "Drifts conhecidos")
> **Source SPEC:** none (candidata `sdd-hotfix-track` em `specs/backlog/candidates.md` L22)
> **Discovery reports:** `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-16T214611Z-hotfix-track.md`; `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T214645Z-hotfix-track.md`; `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md` (Refactor amendment incluído)

---

## Objetivo

Adotar **versionamento SemVer** (`vMAJOR.MINOR.PATCH`) no Spec Context Project
`dadaia-workspace` e diferenciar **release de feature** (`PATCH=0`) de **release de hotfix**
(`PATCH≥1`) **pelo número da versão**, sem criar nenhum diretório paralelo. Toda release —
feature ou hotfix — vive sob `specs/releases/v<M>.<m>.<p>/` e segue o gate e o doctor
existentes. A diferença está apenas no **fluxo condensado** que um hotfix usa, e na
**origem obrigatória** do hotfix: ele só pode entrar em release se foi reportado em
`specs/backlog/candidates.md` na seção `## Hotfixes pendentes`.

Esta release entrega três coisas:

1. **SemVer único em `specs/releases/`**: o nome do diretório é a versão (`v<M>.<m>.<p>`).
   Feature releases têm `PATCH=0`; hotfix releases bumpam o PATCH da feature release mais
   recente.
2. **Backlog com duas seções distintas**: `## Candidatas ativas` (features/evoluções) e
   `## Hotfixes pendentes` (incidentes). Hotfix obrigatoriamente entra por essa segunda
   seção — não há atalho. O fluxo previne PATCH ad-hoc sem auditoria.
3. **Fluxo condensado para hotfix release**: SPEC + TASKS obrigatórios; PLAN opcional
   (decisão da própria SPEC); CLOSURE com smoke evidence obrigatório; memory updates
   opcionais.

A simplificação anula a complexidade do design anterior (folder paralelo
`specs/hotfix/`, single-file `HOTFIX.md`, dual-pointer ACTIVE.md, gate v3 modificado)
porque a diferenciação por número de versão é suficiente para todos os casos — sem novo
schema, sem novo status ladder, sem deadlocks.

---

## Contexto

`dadaia-workspace` opera hoje sob `sdd-release-lifecycle-v1` + `agent-sdd-alignment-v1`:
`specs/releases/<id>/` (SPEC+PLAN+TASKS+CLOSURE), `specs/releases/ACTIVE.md` single-pointer
(`release:`/`phase:`), gate v3 com 3 regras (A memory-atômico, B archive read-only, C marker
`[-]` em produção), doctor com 12 checks em CI. Drifts conhecidos: releases legadas não-SemVer
(devops §2.3, architect §1), branches git já SemVer (`hotfix/v1.2.1-...`),
`bug-fix-fastlane.workflow.md` bypassa `specs/` (architect §1), `constitution.md` L148 contradiz
`_archive/releases/` ativo (architect §13).

A candidata `sdd-hotfix-track` é top da backlog (`specs/backlog/candidates.md` L22). O design
anterior desta release introduziu folder `specs/hotfix/` paralelo e gate v3 modificado; o
operador rejeitou essa complexidade e impôs o modelo simplificado descrito aqui (ver "Drifts
conhecidos").

---

## Decisões fixadas (esta release)

Decisões reduzidas de 21 para 15. Cada decisão fecha uma questão dos reports ou um
ajuste pedido pelo operador na refatoração. Reversões registradas em
`.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md`
(seção "Refactor amendment").

| ID | Tema | Decisão |
|----|------|---------|
| D1 | Layout do hotfix | **Hotfix é uma release** em `specs/releases/v<M>.<m>.<p>/`. Não há `specs/hotfix/`. A diferenciação é pelo PATCH do número de versão: PATCH=0 → feature; PATCH≥1 → hotfix |
| D2 | Artefatos do hotfix | **SPEC.md + TASKS.md obrigatórios; PLAN.md opcional**. A própria SPEC declara se PLAN é necessário (ver D24). CLOSURE.md obrigatório com smoke evidence (D25). Status ladder canonical: `Draft → Em revisão → Aprovado` para todos |
| D3 | Nomenclatura do diretório | Folder name é `v<M>.<m>.<p>` puro (regex `^v\d+\.\d+\.\d+$`), aplicado a **todas as releases criadas a partir desta** — não só hotfix. Cutoff em `Created:` ≥ 2026-06-01 |
| D4 | Origem obrigatória do hotfix | Hotfix release **só** pode ser criada a partir de uma entrada promovida da seção `## Hotfixes pendentes` do `specs/backlog/candidates.md`. Sem essa entrada, product-engineer recusa criar a release. Doctor não enforça (auditoria humana), mas product-engineer agent contract bloqueia |
| D5 | ACTIVE.md format | **Single-pointer** mantido (formato atual: `release:` + `phase:` apenas). Quando hotfix vira ativo, ele toma o lugar da release normal em ACTIVE.md. Operador decide se pausa feature in-flight ou interrompe |
| D6 | Gate v3 | **Sem alteração**. Gate já procura `releases/<active>/TASKS.md`; hotfix usa o mesmo path porque hotfix IS a release. (D7/D8/D9 do design original — modificações de gate — cancelados) |
| D10 | bug-fix-fastlane (revisado) | Permanece para fixes **triviais** (≤30 LOC, sem memory). **Enforcement adicionado**: se exigir update em `specs/memory/product/<feature>.html`, fastlane recusa e instrui filing em `## Hotfixes pendentes` |
| D11 | Trigger do hotfix | qa-engineer emite stub em `.dadaia/reports/<context>/qa-engineer/<ts>-hotfix-candidate.html` quando Deploy Validation FAIL; product-engineer transcreve em `## Hotfixes pendentes`. Stub é input recomendado mas não é gate técnico |
| D14/D15 | Vintage bucket + SemVer baseline | Vintage as-is (3 ativas + 7 arquivadas); doctor exclui via cutoff `Created:` ≤ 2026-05-17. Dadaia-workspace ganha SemVer próprio com baseline retrospectivo `v0.5.0` (próxima feature → `v0.6.0`; primeiro hotfix → `v0.5.1`) |
| D16 | Memory em hotfix CLOSURE | Opcional. Mesma pipeline da release CLOSURE; só atualiza se bug alterou comportamento visível |
| D17 | Constitution L148 | L148 reescrita para refletir `_archive/releases/` como destino único; sem menção a `_archive/hotfixes/` |
| D18 | panel-v1 "PATCH" terminology | Out of scope; backlog item `panel-patch-terminology` gerado |
| D19 | CI | Estende `ci.yml` com branch trigger `hotfix/v*`; doctor valida SemVer folder name; sem `hotfix.yml` |
| D21 | Cross-repo hotfix | Não suportado. Cada repo abre seu próprio |
| D22 (NOVO) | Backlog `## Hotfixes pendentes` | Nova seção com regex `- <ts> <severity> <component> — <one-liner> (post-mortem: <link>)`. Doctor SPEC-DOC-012 valida ambas seções |
| D23 (NOVO) | Hotfix promotion protocol | Bullet é **movido** (não copiado) para `## Histórico` com release-id; doctor WARNING se bullet exceder 72h sem promoção |
| D24 (NOVO) | Hotfix SPEC template enxuto | ≤100 linhas, 6 seções obrigatórias: Incident summary, Affected memory features, Root cause, Fix scope (declara se requer PLAN), Rollback plan, Acceptance + smoke test |
| D25 (NOVO) | Hotfix CLOSURE smoke evidence | CLOSURE.md inclui bloco `## Validations` com post-deploy smoke evidence em triple `{description, command, evidence}`. Não-negociável; doctor SPEC-DOC-006 cobre |

---

## Deltas

### Delta de filesystem

- `specs/releases/v<M>.<m>.0/` (feature) e `specs/releases/v<M>.<m>.<p≥1>/` (hotfix) — mesmo
  layout: SPEC.md, PLAN.md (opcional para hotfix), TASKS.md, CLOSURE.md. Hotfix usa
  templates enxutos (D24/D25)
- `specs/backlog/candidates.md` ganha seção `## Hotfixes pendentes` (D22)
- `specs/_archive/releases/` é destino comum (feature E hotfix)
- `specs/constitution.md` L148 reescrita (D17)
- **Nenhum** `specs/hotfix/`, **nenhum** `_archive/hotfixes/`, **nenhum** `HOTFIX.md`

### Delta de gate

**Nenhum.** Gate v3 atual já lida com tudo (D6).

### Delta de doctor

- `RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")`, `RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)`
- `SPEC-DOC-012` estendido: valida ambas seções de `candidates.md` — `## Candidatas ativas`
  (regex atual) e `## Hotfixes pendentes` (`- <ts> <severity> <component> — <one-liner> (post-mortem: <link>)`).
  WARNING se bullet em `## Hotfixes pendentes` > 72h sem mover para `## Histórico` (D23)
- `SPEC-DOC-016` (NOVO, WARNING→ERROR): folder name de releases casa `RELEASE_SEMVER_RE`
  quando `Created:` ≥ cutoff. Vintage (`Created:` ≤ 2026-05-17) excluído

### Deltas restantes

- **Agentes**: `product-engineer.md` ganha subseção "Hotfix release lifecycle" (fluxo
  condensado + regra D4); `qa-engineer.md` ganha "Hotfix candidate filing" (stub HTML em
  Deploy Validation FAIL); `devops-engineer.md` documenta que branch `hotfix/v<M>.<m>.<p>`
  deve casar SemVer e CI rejeita MAJOR/MINOR
- **Templates**: novos `release_hotfix.md.j2` (D24, SPEC enxuto ≤100 linhas, 6 seções) e
  `closure_hotfix.md.j2` (D25, bloco `## Validations` com placeholder para evidence triple).
  Template SPEC de feature inalterado
- **CI** (D19): `.github/workflows/ci.yml` `on.push.branches` ganha `'hotfix/v*'`; sem novo job
- **Constitution** (D17): L148 substituída por:
  > Specs ativas em `specs/releases/<v-id>/` representam apenas o estado atual; specs
  > encerradas vão para `specs/_archive/releases/<v-id>/`. Hotfix releases (PATCH≥1) seguem
  > o mesmo caminho. Não há rascunhos órfãos fora dessas trilhas.
- **Workflow**: `bug-fix-fastlane.workflow.md` ganha adendo no header (D10) instruindo
  migração para hotfix release quando memory deve ser tocado; novo
  `hotfix-release.workflow.md` (criado em sessão seguinte) com 4 stages
  (file_hotfix_candidate → promote_to_release → apply_fix → close_with_smoke)

---

## Fluxo de hotfix release (canonical)

1. **Detecção**: qa-engineer (Deploy Validation FAIL) ou operador identifica incidente
2. **File**: bullet em `specs/backlog/candidates.md` seção `## Hotfixes pendentes`
3. **Promoção**: product-engineer atribui `v<M>.<m>.<p+1>` (bump PATCH da feature release
   atual), move bullet para `## Histórico` com o release-id (D23), cria diretório
   `specs/releases/v<M>.<m>.<p+1>/`, atualiza `ACTIVE.md`
4. **SPEC**: product-engineer escreve SPEC.md usando template enxuto (D24); declara em
   "Fix scope" se PLAN.md é necessário
5. **TASKS**: criada com 1-N tarefas pequenas
6. **PLAN** (opcional): só se SPEC declarou
7. **Implementação**: implementer executa tasks no fluxo padrão (marker `[-]`)
8. **CLOSURE**: smoke evidence em produção obrigatório (D25); memory update opcional (D16);
   `git mv` para `_archive/releases/`

Quando comparado a feature release (8 fases formais), hotfix usa **fluxo condensado** mas
**não bypassa** SPEC: SPEC + TASKS sempre obrigatórios; PLAN é elidido apenas quando
trivial.

---

## Quando usar hotfix-release vs bug-fix-fastlane

| Sintoma observável | Workflow correto |
|---|---|
| Bug pequeno descoberto durante desenvolvimento (não em produção) | tdd-cycle |
| Bug em produção, ≤30 LOC, não toca `specs/memory/`, não impacta funcionalidade documentada | bug-fix-fastlane |
| Incidente em produção, regressão em release arquivada, demanda spec auditável | **hotfix release** (PATCH≥1) |
| Bug em produção que demanda atualizar `specs/memory/product/<feature>.html` | **hotfix release** (D10 — fastlane recusa, instrui filing em backlog) |
| Bug com blast radius > 1 arquivo, múltiplos implementers | **hotfix release** |
| "Fix" que operador quer fazer sem registrar nada | bug-fix-fastlane (mas exige report) |

Critério mecânico: se memory precisa ser atualizado, é hotfix release. Se spec não precisa
existir, é fastlane.

---

## Arquivos de memory afetados

Nenhum nesta sessão. Esta release continua em `phase: TASKS`. Memory updates virão na
CLOSURE — provavelmente novo HTML `specs/memory/product/sdd-hotfix-track.html` documentando
o modelo SemVer + backlog `## Hotfixes pendentes` + fluxo condensado.

---

## Critérios de aceite

- [ ] `specs/releases/sdd-hotfix-track-v1/{SPEC,PLAN,TASKS}.md` com `**Status:** Aprovado`
- [ ] `specs/releases/ACTIVE.md` aponta para `sdd-hotfix-track-v1`, `phase: TASKS` (single-pointer)
- [ ] `dadaia specs doctor` retorna 0 errors, 0 warnings
- [ ] SPEC.md ≤ 250 linhas; PLAN.md ≤ 300 linhas; TASKS.md com 6-9 tasks
- [ ] SPEC.md inclui as 15 decisões ativas (D7/D8/D9/D12 parcial/D20 canceladas)
- [ ] Não há criação de `specs/hotfix/` em momento algum — design rejeitado
- [ ] Gate inalterado (D6); deltas executados em sessão futura

---

## Fora de escopo

Implementação dos deltas (sessão futura, tasks em TASKS.md); migração das 10 releases
legadas (Vintage bucket, D14); terminologia "PATCH" em `dadaia-workspace-panel-v1` (backlog,
D18); cross-repo hotfix (D21); pré-release tags (`v1.0.0-rc1`); PyPI publish (backlog
`release-pipeline`); memory HTMLs (vem na CLOSURE).

---

## Dependências e riscos

| Risco | Mitigação |
|-------|-----------|
| Hotfix abusado como "fast-lane para features pequenas" | Critério mecânico em §"Quando usar..."; D10 força fastlane→hotfix quando memory necessário |
| Hotfix criado sem entrada em `## Hotfixes pendentes` | product-engineer agent contract bloqueia; D23 emite WARNING após 72h |
| SPEC-DOC-016 quebrar Vintage releases | Cutoff `Created:` ≤ 2026-05-17 exclui; ERROR só após 2026-07-01 |
| Backlog regex muito rígido | Severidade WARNING durante 2 semanas após implementação; ERROR depois |
| Feature in-flight vs hotfix chegando | Operador decide pausar/interromper; ACTIVE.md serializa (sem race) |
| Constitution L148 edit | Operator confirmation obrigatório per agent contract |
| Branch `hotfix/v<M>.<m>.<p>` mal-formado | CI rejeita push (D19) |

---

## Drifts conhecidos

**Refatoração mid-flight (2026-05-16):** design original (rascunho fixado 5 minutos antes
da refatoração) introduzia folder `specs/hotfix/<hotfix-id>/` paralelo, single-file
`HOTFIX.md`, status ladder hotfix-específico (`Aberto→Aplicado→Encerrado`), ACTIVE.md
dual-pointer e gate v3 modificado — 21 decisões, 12 tasks. Operador rejeitou e instruiu
simplificação radical: hotfix é **uma release como qualquer outra**, diferenciada apenas
pelo PATCH≥1 no folder name. SPEC + PLAN + TASKS reescritos em-place. Reversões detalhadas
em `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md`
seção "Refactor amendment".

---

## Backlog gerado por esta release

A serem adicionados em `specs/backlog/candidates.md` na CLOSURE (não nesta sessão):

- `panel-patch-terminology` — Reconciliar uso colloquial de "PATCH" em `dadaia-workspace-panel-v1/PLAN.md` L76-78 com SemVer PATCH agora reservado para hotfix release (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` D18)
- `hotfix-release-workflow` — Implementar `dadaia_workspace/public/workflows/hotfix-release.workflow.md` com 4 stages (file_hotfix_candidate → promote_to_release → apply_fix → close_with_smoke) (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` "Delta de workflow")
- `vintage-bucket-doc` — Documentar Vintage bucket em `docs/sdd-migration-playbook.md` com lista das 10 releases pré-SemVer (owner: software-engineer, contexto: SPEC `sdd-hotfix-track-v1` D14)

---

## Referências

- Discovery devops: `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-16T214611Z-hotfix-track.md`
- Discovery architect: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T214645Z-hotfix-track.md`
- Discovery grill report (com Refactor amendment): `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T215356Z-hotfix-discovery.md`
- Constitution: `specs/constitution.md` (L148 alvo de edit)
- Backlog: `specs/backlog/candidates.md` (ganha `## Hotfixes pendentes`)
- Release anterior (data model precedent): `specs/releases/agent-sdd-alignment-v1/SPEC.md`
- Meta-release base: `specs/releases/sdd-release-lifecycle-v1/SPEC.md`
- Gate atual (inalterado, D6): `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
- Doctor atual: `dadaia_workspace/features/specs/doctor.py`
- Workflow legado conservado: `dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md`
