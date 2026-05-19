# Refinamento de Specs — sdd-hotfix-track-v1 Discovery
> Gerado em: 2026-05-16T21:53:56Z
> Escopo: nova release `sdd-hotfix-track-v1` (candidato top da backlog L22)
> Problemas encontrados: 13 questões abertas + 3 inconsistências arquiteturais | Resolvidos: 16 | Abertos: 0

---

## Modo de operação desta sessão

O operador instruiu (system-reminder durante a sessão): _"work without stopping for
clarifying questions. When you'd normally pause to check, make the reasonable call and
continue; they'll redirect if needed."_

Logo, a Fase 1 do `dadaia-grill-me` (uma pergunta por turno) **não foi executada como
interview live**. Em vez disso, cada uma das 16 perguntas/inconsistências foi resolvida
sintetizando: (a) a recomendação do especialista no report origem, (b) a recomendação
default pré-declarada no prompt do operador, (c) o status quo de invariantes do gate v3 +
doctor. Resoluções listadas explicitamente abaixo com origem e justificativa.

Onde a recomendação default do prompt do operador conflitava com a recomendação do
especialista, segui o **operador** (prompt outranks specialist recommendation per
session protocol).

---

## Sumário de Problemas

| # | Tipo | Specs/files envolvidos | Resolução |
|---|------|-----------------------|-----------|
| 1 | Question (devops Q10 + architect §6) | gate v3 path-construction bug for `specs/hotfix/` | **IN scope** — D7/D8/D9 da SPEC. Devops recomenda; operador concorda no prompt |
| 2 | Question (architect §5) | ACTIVE.md format dual-pointer | **Option β** com 4 keys (2 opcionais). D5 da SPEC |
| 3 | Inconsistência (architect §13) | bug-fix-fastlane existing workflow vs hotfix-track | **KEEP both**. D10 — critério mecânico em SPEC §"Quando usar..." |
| 4 | Question (architect §3 + §4) | folder layout + hotfix data model | **Option A + single-file rico**. D1+D2 — `specs/hotfix/<v-id>/HOTFIX.md` + TASKS.md |
| 5 | Question (architect Q2) | SemVer axis (per-product vs per-release-line) | **Per-product**. D15 — dadaia-workspace ganha versão; releases declaram MAJOR/MINOR/PATCH no header |
| 6 | Question (operator default) | Migração 10 releases legados | **Vintage bucket out-of-scope**. D14 — cutoff por `Created:` ≤ 2026-05-17 |
| 7 | Question (architect Q5) | Status ladder de HOTFIX.md | **Hotfix-specific**: `Aberto → Aplicado → Encerrado`. D4. TASKS.md mantém canonical para preservar check 4 |
| 8 | Inconsistência (architect §13) | Constitution L148 contradiz `_archive/releases/` | **Fix in-scope**. D17 + T8 — redação reescrita |
| 9 | Inconsistência (architect §13) | dadaia-workspace-panel-v1 PLAN.md L76-78 "PATCH" colloquial | **Out of scope**. D18 — backlog item `panel-patch-terminology` criado |
| 10 | Question (devops top rec) | CI workflow strategy | **Extend ci.yml**, não cria hotfix.yml. D19 |
| 11 | Question (devops Q4) | Hotfix exige PLAN.md? | **Não**. D2 — single-file `HOTFIX.md` + `TASKS.md` apenas |
| 12 | Question (devops Q5, architect Q4) | Hotfix CLOSURE updates memory? | **Opcional**. D16 — analogous ao "## Memory updates: none" das releases |
| 13 | Question (devops Q9) | Onde começa MAJOR.MINOR baseline? | **D15**: `v0.5.0` como baseline retrospectivo do dadaia-workspace (declarado neste SPEC) |
| 14 | Question (devops Q7 + architect §10) | Hotfixes archive mixed ou separate? | **Separate**: `specs/_archive/hotfixes/<id>/` mirror simétrico de `_archive/releases/`. D1 |
| 15 | Question (architect Q1) | Hotfix-id format: `v1.2.1` ou `<slug>-v1.2.1`? | **Bare SemVer**: `v<M>.<m>.<p>`. D3 — scope dado pelo path `specs/hotfix/` |
| 16 | Question (architect Q6) | Cross-repo hotfix support? | **Não**. D21 — cada repo seu hotfix; cross-repo via `dadaia orchestrate run` (fora de escopo) |

---

## Backlog Priorizado (pós-refinamento)

| Ordem | Item | Depende de | Razão |
|-------|------|-----------|-------|
| 1 | `sdd-hotfix-track-v1` (esta) | nada | Top backlog candidate; especialistas já alinhados |
| 2 | `panel-patch-terminology` (novo) | sdd-hotfix-track-v1 ARCHIVED | Reconcilia uso colloquial após PATCH ter semântica nova |
| 3 | `hotfix-track-workflow` (novo) | T6 (agentes patchados) | Workflow concreto consume agentes alinhados |
| 4 | `vintage-bucket-doc` (novo) | sdd-hotfix-track-v1 ARCHIVED | Documenta política Vintage para outros operadores |
| 5 | `agent-sdd-alignment-v1 CLOSURE` | operator decision | Independente — coexiste em `phase: TASKS` com esta |

---

## Detalhes por Problema

### Problema #1 — Gate v3 path-construction bug

**Tipo:** Question + Bug (devops Q10, architect §6.3)
**Specs/files:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh` L151-182
**Descrição:** Rule C grep constructs `$PRIMARY_SPECS/releases/$ACTIVE_RELEASE/TASKS.md`.
Se ACTIVE.md aponta para hotfix (slug `v1.2.1`) sob `specs/hotfix/`, o path resolvido
é `$PRIMARY_SPECS/releases/v1.2.1/TASKS.md` (errado) e o gate fail-open.
**Resposta default operador:** "IN scope — gate deve ser hotfix-aware ou o feature todo é unsafe"
**Resolução:** D5 + D7 + D8 + D9; tasks T1+T2+T4 cobrem implementação. Gate ganha priority-0
em `hotfix/<ACTIVE_HOTFIX>/TASKS.md` antes do release search.

### Problema #2 — ACTIVE.md format dual pointer

**Tipo:** Question (architect §5)
**Specs/files:** `specs/releases/ACTIVE.md` schema, `doctor.py::_read_active_md` L189-206
**Descrição:** Architect recomenda Option β (4 keys, 2 opcionais).
**Resolução:** D5 — schema FROZEN em `release: / phase: / hotfix: / hotfix_phase:`. Ambos
últimos opcionais; quando presentes, ambos devem ser não-vazios. Backward-compat com 10
releases legadas garantida (linhas ausentes = behavior idêntico ao atual).

### Problema #3 — bug-fix-fastlane existing workflow

**Tipo:** Inconsistência arquitetural (architect §13)
**Specs/files:** `dadaia_workspace/public/workflows/bug-fix-fastlane.workflow.md`
**Descrição:** Workflow existente roda fluxo hotfix-like sem tocar `specs/`. Operador
deve decidir: deprecate / keep / merge.
**Resposta default operador:** "keep both"
**Resolução:** D10 — KEEP fastlane (correções triviais ≤30 LOC, sem memory). Critério
mecânico tabular em SPEC §"Quando usar hotfix-track vs bug-fix-fastlane" determina escolha.

### Problema #4 — Folder layout + data model

**Tipo:** Question (architect §3 + §4)
**Specs/files:** `specs/hotfix/` (não existe ainda)
**Descrição:** Architect §3 recomenda Option A (parallel); §4 oferece 3 variantes (single,
minimal-triple, full). Operador no prompt sugere single-file `HOTFIX.md` com evidence-triple
em CLOSURE.
**Resolução:** D1 (Option A) + D2 (single-file `HOTFIX.md` rich + TASKS.md). HOTFIX.md
serve SPEC+CLOSURE merged. `## Validation` section carrega evidence triples (espelha
SPEC-DOC-006 do doctor).

### Problema #5 — SemVer axis

**Tipo:** Question (architect Q2)
**Descrição:** Per-release-line (`agent-sdd-alignment-v1.0.0`) vs per-product (`dadaia-workspace-v0.5.0`)
**Resposta default operador:** "per-product (single workspace = one version line)"
**Resolução:** D15. Dadaia-workspace ganha SemVer próprio; cada release declara contribuição
no header `**SemVer:**` (informativo, não enforced).

### Problema #6 — Migração 10 releases legados

**Tipo:** Question (devops §6, architect §10)
**Resposta default operador:** "out of scope — declare Vintage naming bucket"
**Resolução:** D14. Cutoff por `Created:` ≤ 2026-05-17; SPEC-DOC-016 skips Vintage. Sem
rename, sem mapping table.

### Problema #7 — Status ladder

**Tipo:** Question (architect Q5)
**Resposta default operador:** "hotfix-specific ladder. Friction of 'Em revisão' is wrong for a 2-hour incident"
**Resolução:** D4. `CANONICAL_HOTFIX_STATUS = {Aberto, Aplicado, Encerrado}` usado apenas
em HOTFIX.md. TASKS.md hotfix mantém canonical (Aprovado) — preserva SPEC-DOC-004 sem fork.

### Problema #8 — Constitution L148

**Tipo:** Inconsistência arquitetural (architect §13)
**Specs/files:** `specs/constitution.md` L148
**Descrição:** Bullet "Versão atômica" diz "Não arquive specs descartadas — delete-as",
mas `_archive/releases/` ativo com 7 entries.
**Resposta default operador:** "YES — small edit, can ride along"
**Resolução:** D17 + T8. Edit explícito em TASKS com precondição `operator confirmation`
per product-engineer agent contract para constitution edits.

### Problema #9 — panel-v1 "PATCH" colloquial

**Tipo:** Inconsistência (architect §13)
**Specs/files:** `specs/releases/dadaia-workspace-panel-v1/PLAN.md` L76-78
**Resposta default operador:** "not this release; tag as backlog item"
**Resolução:** D18. Backlog item `panel-patch-terminology` adicionado em SPEC §"Backlog gerado"
(executado em CLOSURE).

### Problema #10 — CI workflow strategy

**Tipo:** Question (devops top rec)
**Resposta default operador:** "extend ci.yml"
**Resolução:** D19. T7 modifica `.github/workflows/ci.yml`; nenhum `hotfix.yml`.

### Problema #11 — PLAN.md no hotfix

**Tipo:** Question (devops Q4)
**Resolução:** D2. Hotfix tem apenas HOTFIX.md + TASKS.md. Se cresce além de 3 tasks,
doctor emite WARNING "consider reclassifying as MINOR release" (mitigation explícita).

### Problema #12 — Memory em hotfix CLOSURE

**Tipo:** Question (devops Q5, architect Q4)
**Resolução:** D16. Opcional. Quando presente, mesma pipeline (templates Jinja2 +
`dadaia public install`). Gate Rule A OR-condition cobre HOTFIX_CLOSURE.

### Problema #13 — MAJOR.MINOR baseline

**Tipo:** Question (devops Q9)
**Descrição:** "v1.0.0 baseline ponto histórico?"
**Resolução:** D15. `v0.5.0` declarado como baseline retrospectivo. Próxima release
feature → `v0.6.0`. Primeiro hotfix possível → `v0.5.1`. Justificativa: dadaia-workspace
não está em 1.0 (CLI ainda evoluindo, API não estável).

### Problema #14 — Archive layout

**Tipo:** Question (devops Q7)
**Resolução:** D1. Separate `_archive/hotfixes/` (mirror simétrico de `_archive/releases/`).
Gate Rule B wildcard `_archive/*` já cobre — zero change na rule.

### Problema #15 — Hotfix-id format

**Tipo:** Question (architect Q1)
**Resolução:** D3. Bare `v<M>.<m>.<p>` com PATCH ≥ 1. Sem slug porque path
`specs/hotfix/` já dá scope. Regex `HOTFIX_ID_RE` em doctor.

### Problema #16 — Cross-repo hotfix

**Tipo:** Question (architect Q6)
**Resolução:** D21. Não suportado nesta release. Cada repo abre o próprio; coordenação
cross-repo via `dadaia orchestrate run` (separate concern).

---

## Edições Pendentes nas Specs

| Arquivo | Seção | O que mudar |
|---------|-------|-------------|
| `specs/releases/sdd-hotfix-track-v1/SPEC.md` | (novo) | Criado nesta sessão (Aprovado) |
| `specs/releases/sdd-hotfix-track-v1/PLAN.md` | (novo) | Criado nesta sessão (Aprovado), 215 linhas |
| `specs/releases/sdd-hotfix-track-v1/TASKS.md` | (novo) | Criado nesta sessão (Aprovado), 12 tasks |
| `specs/releases/ACTIVE.md` | conteúdo | Repointar para `sdd-hotfix-track-v1` / `phase: TASKS` (LAST step) |
| `specs/constitution.md` | L148 | Reescrita declarada em T8 (executada em sessão de IMPLEMENTATION com operator confirmation) |
| `specs/backlog/candidates.md` | "Candidatas ativas" e "Histórico" | Mover `sdd-hotfix-track` para histórico, adicionar 3 novos itens — executado na CLOSURE desta release (T12), não nesta sessão |

---

## Próximos Passos

1. (esta sessão) Repointar `specs/releases/ACTIVE.md` para `sdd-hotfix-track-v1` / phase TASKS
2. (esta sessão) Confirmar `dadaia specs doctor` 0 errors / 0 warnings
3. (próxima sessão) Implementer agents (software-engineer + devops-engineer) executam T1-T11
4. (sessão final) product-engineer executa T12 (CLOSURE + memory update + git mv para archive)

---

## ADRs registrados nesta sessão

- **ADR-hotfix-A**: Folder paralelo `specs/hotfix/` (Option A) — razão: preserva memory atomicity
  (Rule A), simétrico com `_archive/`, zero ambiguidade em doctor whitelist
- **ADR-hotfix-B**: Dual-pointer ACTIVE.md (Option β) — razão: hotfix verdadeiro não pode
  pausar release in-flight; serial activation defeats purpose
- **ADR-hotfix-C**: Hotfix-specific status ladder — razão: 2h incident não comporta 3 status flips
- **ADR-hotfix-D**: Single-file `HOTFIX.md` (SPEC+CLOSURE merged) — razão: data model proporcional
  ao escopo de mudança; CLOSURE em separado é overkill para um arquivo de ≤200 linhas
- **ADR-hotfix-E**: Vintage bucket via cutoff date — razão: rename retroativo destruiria
  links em reports/projeções/git history; benefício cosmético não justifica custo
- **ADR-hotfix-F**: bug-fix-fastlane coexiste com hotfix-track — razão: dois níveis de severidade
  (sem-memory vs com-memory); fastlane preserva fast path para correções triviais
- **ADR-hotfix-G**: Per-product SemVer com baseline `v0.5.0` — razão: produto único, eixo único;
  baseline conservativo reflete maturidade real da CLI (não 1.0)

---

## Notas de execução

- Grill-me não rodou no modo interview (operator session directive). 16 resolutions
  derivadas dos reports + defaults pré-declarados no prompt.
- Nenhuma pergunta ficou pendente. Se operador discordar de alguma das 21 decisões fixadas
  na SPEC, pode redirecionar antes da IMPLEMENTATION começar (próxima sessão).
- Esta release coexistirá em `phase: TASKS` com `agent-sdd-alignment-v1` (também em TASKS).
  Confirmação: ACTIVE.md pode apontar apenas para uma — esta sessão flipa para
  `sdd-hotfix-track-v1`. `agent-sdd-alignment-v1` permanece em sua pasta intocada; o
  operador decide quando promover qualquer das duas para CLOSURE.

---

## Refactor amendment — 2026-05-16 (operator simplification adopted mid-flight)

Cinco minutos após a SPEC + PLAN + TASKS originais serem fixados (21 decisões, 12 tasks),
o operador comunicou a seguinte simplificação radical:

> "Hotfix identificados serão reportados no backlog como hotfixes. Mas eles devem ter um
> padrão diferente de serem gerenciados pelo backlog. Somente hotfixes reportados em
> backlog entram em release/v1.1.{patch} ou seja a cada hotfix cria-se uma release de
> patch. E releases normais e releases de hotfix tem fluxo mais bem definido. Pode
> simplificar e reduzir ambiguidades e deadlocks. Devemos ao maximo evitar deadlocks"

Toda a SPEC + PLAN + TASKS foi reescrita em-place para incorporar o novo modelo. O grill
original (acima) é preservado como contexto histórico de **por que cada decisão original
foi tomada**; este amendment registra **as reversões** e os **novos rumos**.

### Princípio central da simplificação

**Hotfix é uma release como qualquer outra**, vivendo em `specs/releases/v<M>.<m>.<p>/`.
A diferenciação entre feature release e hotfix release é exclusivamente pelo número de
versão: `PATCH=0` é feature; `PATCH≥1` é hotfix. Não há folder paralelo, não há schema
novo no ACTIVE.md, não há ladder de status hotfix-específico, e o gate v3 **não é
alterado**.

### Reversões (decisões originais agora canceladas/revisadas)

| ID original | Status pós-refactor |
|---|---|
| D1 (`specs/hotfix/<id>/` paralelo) | REVERSO: hotfix vive em `specs/releases/v<M>.<m>.<p>/` |
| D2 (single-file HOTFIX.md) | REVERSO: SPEC.md + TASKS.md canonical; PLAN.md opcional (SPEC declara) |
| D3 (hotfix-id bare `v<M>.<m>.<p>`) | REUTILIZADO mas aplicado a **toda** release nova (não só hotfix) |
| D4 (status ladder `Aberto→Aplicado→Encerrado`) | REVERSO: canonical `Draft → Em revisão → Aprovado` para todos |
| D5 (ACTIVE.md dual-pointer Option β) | REVERSO: single-pointer Option α mantido |
| D6 (CANONICAL_HOTFIX_PHASES) | CANCELADO: sem novo schema de phase |
| D7 (Rule A OR HOTFIX_CLOSURE) | CANCELADO: gate não muda |
| D8 (Rule C priority hotfix path) | CANCELADO: gate não muda |
| D9 (meta-edit `*/HOTFIX.md`) | CANCELADO: arquivos hotfix são SPEC.md/PLAN.md/TASKS.md normais |
| D10 (bug-fix-fastlane keep-both) | REVISADO: fastlane mantida mas com **enforcement**: se memory precisa update, fastlane recusa e instrui filing em `## Hotfixes pendentes` |
| D11 (qa-engineer stub) | MANTIDO mas adaptado: stub gera entrada para `## Hotfixes pendentes`, não para `specs/hotfix/` |
| D12 (SPEC-DOC-013..017) | PARCIALMENTE CANCELADO: apenas SPEC-DOC-016 (SemVer regex) e SPEC-DOC-012 estendido (backlog dual-section) ficam |
| D13 (SemVer enforcement cutoff) | MANTIDO mas simplificado: aplicado a folder name de release, não a hotfix-id |
| D14 (Vintage bucket) | MANTIDO |
| D15 (SemVer per-product baseline v0.5.0) | MANTIDO |
| D16 (memory updates em hotfix CLOSURE opcional) | MANTIDO |
| D17 (constitution L148 rewrite) | MANTIDO mas adaptado: texto novo menciona apenas `_archive/releases/` (não `_archive/hotfixes/`, que não existe mais) |
| D18 (panel-v1 "PATCH" terminology) | MANTIDO |
| D19 (CI ci.yml extend) | MANTIDO mas simplificado: só branch trigger + validação SemVer no branch name |
| D20 (template hotfix.md.j2) | REVISADO: template SPEC enxuto `release_hotfix.md.j2` + CLOSURE template `closure_hotfix.md.j2` (D24, D25 abaixo) |
| D21 (no cross-repo hotfix) | MANTIDO |

### Decisões novas (adicionadas pela refatoração)

- **D22 (NOVO)** — Backlog dual-section: `specs/backlog/candidates.md` ganha seção
  `## Hotfixes pendentes` com regex próprio (`<ts> <severity> <component> — <one-liner> (post-mortem: <link>)`).
  Doctor SPEC-DOC-012 valida ambas seções
- **D23 (NOVO)** — Hotfix promotion protocol: bullet movido (não copiado) para
  `## Histórico` com o release-id atribuído. Doctor WARNING se bullet em
  `## Hotfixes pendentes` exceder 72h sem promoção
- **D24 (NOVO)** — Hotfix SPEC template enxuto (≤100 linhas) com 6 seções obrigatórias:
  Incident summary, Affected memory features, Root cause, Fix scope, Rollback plan,
  Acceptance + smoke test. SPEC declara em "Fix scope" se PLAN.md é necessário
- **D25 (NOVO)** — Hotfix CLOSURE.md com bloco `## Validations` contendo
  post-deploy smoke evidence em triple (description, command, evidence). Não-negociável

### Princípio "evitar deadlocks" — como o novo modelo entrega

1. **Gate inalterado** → nenhuma race condition de path-construction, nenhum risco de
   fail-open em hotfix mal-formado
2. **ACTIVE.md single-pointer** → nenhuma simultaneidade entre release e hotfix; quando
   hotfix chega, operador decide pausar feature in-flight (queue) ou interromper
3. **Origem obrigatória do backlog** → product-engineer não pode criar hotfix ad-hoc;
   filing → promoção é um ponto de decisão humana clara
4. **Status ladder único** → cognitive load mínimo; um único conjunto de regras
5. **Sem novo schema/folder/check** → drift surface reduzida significativamente

### Métricas pós-refactor

- SPEC: 305 → ~225 linhas
- PLAN: 215 → ~195 linhas
- TASKS: 263 → ~210 linhas (12 → 9 tasks + T_CLOSE)
- Decisões: 21 → 15 ativas (6 canceladas/superseded)
- Filesystem paths novos: 0 (vs 2 no modelo original: `specs/hotfix/`, `specs/_archive/hotfixes/`)
- Gate patches: 0 (vs 4 no modelo original)
- Doctor checks novos: 1 + 1 estendido (vs 5 novos no modelo original)

### Operator awareness

O design original já estava aprovado quando a simplificação foi solicitada. A reescrita
em-place mantém `Status: Aprovado` em todos os três artefatos por instrução explícita
do operador. Nenhuma sessão futura precisa re-aprovar — o documento atual é canonical.

