# Tasks: Release — sdd-release-lifecycle-v1

> **Status:** Aprovado
> **Release ID:** sdd-release-lifecycle-v1
> **Owner:** product-engineer

---

## Convenções

| Marker | Estado |
|--------|--------|
| `[ ]` | OPEN |
| `[-]` | IN PROGRESS |
| `[x]` | DONE |

Apenas uma task `[-]` por vez (regra invariante do `dadaia-task-manager`).

---

## Phase 2 — Refactor product-engineer agent

- [x] T-2.1 Reescrever `dadaia_workspace/public/agents/product-engineer.md` com lifecycle de 8 fases, memory atomicity HTML, active release pointer, SDD HARD STOP, write permissions, e referência à nova skill `dadaia-release-closure`
- [x] T-2.2 Rodar `dadaia public stage && dadaia public install --target all` e verificar `dadaia public doctor` retorna `[ok]` (executado ao final de Phase 3 para batch)

## Phase 3 — Skills release-aware + templates

- [x] T-3.1 Atualizar `dadaia-workspace-spec-navigator/SKILL.md`: ler `memory/*.html`, `releases/ACTIVE.md`, ignorar `_archive/` e `backlog/`
- [x] T-3.2 Atualizar `dadaia-workspace-spec-reviewer/SKILL.md`: checks de atomicidade HTML, ACTIVE, status canônico, evidence triples, broken `<img>`
- [x] T-3.3 Atualizar `dadaia-task-manager/SKILL.md`: TASKS lives em `releases/<active-id>/TASKS.md` (primário) com legacy compat
- [x] T-3.4 Criar nova skill `dadaia-release-closure/SKILL.md` com template e protocolo de CLOSURE
- [x] T-3.5 Criar template `dadaia_workspace/public/templates/memory-product.html.j2`
- [x] T-3.6 Criar template `dadaia_workspace/public/templates/memory-architecture.html.j2`
- [x] T-3.7 Criar template `dadaia_workspace/public/templates/memory-tech-stack.html.j2`
- [x] T-3.8 Propagar (`dadaia public stage && install --target all`) e verificar com `public doctor`

## Phase 4 — Gate v3

- [x] T-4.1 Atualizar `.dadaia/scripts/sdd-spec-gate.sh` para v3: bloquear memory/*.html|md exceto CLOSURE; bloquear `_archive/*`; logar release-id; suporte env `SDD_LEGACY_FEATURES`
- [x] T-4.2 Validar com testes bash inline (4 cenários: memory block sem CLOSURE, memory allow em CLOSURE, archive block, production allow com `[-]`)
- [x] T-5.1 Criar `dadaia_workspace/features/specs/doctor.py` com os 11 checks estruturais

## Phase 5 — CLI dadaia specs doctor

- [ ] T-5.2 Criar `dadaia_workspace/cli/commands/specs.py` (subcommand group `dadaia specs <verb>`)
- [ ] T-5.3 Wire-up em `dadaia_workspace/cli/main.py` (app.add_typer)
- [ ] T-5.4 Criar `tests/unit/features/specs/test_doctor.py` com pelo menos um positivo e um negativo por check
- [ ] T-5.5 Rodar `pytest tests/unit/features/specs/test_doctor.py` → green
- [ ] T-5.6 Rodar `dadaia specs doctor` no próprio workspace → exit 0 ou só warnings legacy

## Phase 6 — Migração dadaia-workspace

- [x] T-6.1 Triagem inicial: classificar cada uma das 23 features em (a) implementada → archive-com-CLOSURE-retroativa; (b) draft sem implementação → backlog candidate + legacy archive; (c) in-flight → nova release Draft
- [x] T-6.2 Para cada feature implementada (7), criar `_archive/releases/<id>/{SPEC,PLAN,TASKS,CLOSURE}.md`. CLOSURE retroativa referencia git log para evidência
- [x] T-6.3 Para cada feature draft sem implementação (15), consolidar bullet em `backlog/candidates.md` e mover SPEC.md para `_archive/legacy-features/<name>/`
- [x] T-6.4 Migrar source SPEC de `sdd-release-lifecycle` para esta meta-release (já feito via `Source SPEC:` reference em SPEC.md). Arquivar a pasta original
- [x] T-6.5 Mover memory markdown legado (`specs/memory/*.md`) para `_archive/legacy-memory/<timestamp>/`
- [x] T-6.6 Renderizar `specs/memory/{product,architecture,tech-stack}.html` a partir dos templates Jinja2 com conteúdo consolidado. ATIVAR phase=CLOSURE em ACTIVE.md antes; reverter para IMPLEMENTATION após
- [x] T-6.7 Atualizar `specs/PLAN.md` e `specs/TASKS.md` raiz se ainda existirem como legacy (movidos para `_archive/legacy-root/`); `security/` e `foundation/` movidos para `_archive/legacy-features/`
- [x] T-6.8 Rodar `dadaia specs doctor` → 0 errors, 0 warnings
- [-] T-6.9 Flipar env `SDD_LEGACY_FEATURES` para `0` no estado do workspace — deferido para a próxima release (quando migração for de fato concluída para outros repos também)

## Verificação end-to-end (após Phase 6)

- [ ] T-V.1 `dadaia specs doctor` → exit 0 em dadaia-workspace
- [ ] T-V.2 Gate v3: 4 testes bash inline passam (block/allow conforme matriz)
- [ ] T-V.3 `dadaia public doctor` → todos `[ok]`
- [ ] T-V.4 `find specs/features -name SPEC.md` → vazio (todas migradas)
- [ ] T-V.5 `find specs/_archive/releases -name CLOSURE.md | wc -l` → ≥ 7
- [ ] T-V.6 Memory HTML abre no browser com Mermaid renderizando

---

## Parallelism notes

Tasks dentro da mesma phase podem ser paralelizadas se não competirem pelo mesmo write
set. Phases são sequenciais (Phase 3 depende de 2, Phase 4 depende de 1, Phase 5 depende
de 2-4 conceitualmente mas pode iniciar em paralelo com 3-4, Phase 6 depende de tudo).

T-3.5/T-3.6/T-3.7 (3 templates) são paralelos entre si — write sets disjuntos.
T-6.2 (archive features implementadas) e T-6.3 (legacy archives) são paralelos.

## Phase 7 — Product Memory Feature Catalog (extensão do dogfood)

- [x] T-7.1 Ampliar gate v3 glob para `memory/product/**/*.html`; atualizar doctor.py + tests
- [x] T-7.2 Atualizar templates: rename `memory-product.html.j2` → `memory-product-index.html.j2`; criar `memory-product-feature.html.j2`
- [x] T-7.3 Migrar `specs/memory/product.html` para `_archive/legacy-memory/2026-05-16T180000Z/`; setar ACTIVE.md phase=CLOSURE
- [x] T-7.4 Criar `specs/memory/product/index.html` + 11 feature HTMLs em ordem de relevância
- [x] T-7.5 Reverter ACTIVE.md para phase=IMPLEMENTATION; atualizar product-engineer.md com Product memory content contract
- [x] T-7.6 Atualizar dadaia-workspace-spec-reviewer/SKILL.md com checks textuais do catálogo
- [x] T-7.7 dadaia public install --force; verificação end-to-end
