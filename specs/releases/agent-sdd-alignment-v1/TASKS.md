# Tasks: Release — agent-sdd-alignment-v1

> **Status:** Aprovado
> **Release ID:** agent-sdd-alignment-v1
> **Owner:** product-engineer

---

## Convenções

| Marker | Estado |
|--------|--------|
| `[ ]` | OPEN |
| `[-]` | IN PROGRESS |
| `[x]` | DONE |

Apenas uma task `[-]` por vez (regra invariante do `dadaia-task-manager`).

Cada task tem o cabeçalho `[parallel: yes/no]` indicando se pode rodar concorrente com
outra `[-]` da mesma fase em sessões separadas (write-set disjunto).

---

## Phase 1 — software-architect alignment

- [x] T-1.1 `[parallel: no]` Editar `dadaia_workspace/public/agents/software-architect.md` ONBOARD workflow (L86–92): substituir `memory/architecture.md` por `memory/architecture.html`, `memory/product/index.html` e `memory/tech-stack.html`; adicionar nota sobre carregar `memory/product/<slug>.html` sob demanda. **Owner:** product-engineer. **Critério:** `grep "memory/architecture.html" software-architect.md` → ≥1 hit.

- [x] T-1.2 `[parallel: no]` Editar `dadaia_workspace/public/agents/software-architect.md` REVIEW workflow (L158): mesma substituição da T-1.1 + remover `foundation/SPEC.md` como obrigatório (manter "if present"). **Critério:** `grep "memory/architecture.md" software-architect.md` → 0 hits.

- [x] T-1.3 `[parallel: no]` Editar `dadaia_workspace/public/agents/software-architect.md` Report Template (L258): `architecture.md + foundation/SPEC.md` → `architecture.html + foundation/SPEC.md`. **Critério:** template `Architecture Status` referencia `architecture.html`.

---

## Phase 2 — Implementer agents alignment (paralelizáveis entre si)

- [x] T-2.1 `[parallel: yes]` Editar `dadaia_workspace/public/agents/software-engineer.md`: (a) inserir bloco "Resolving the active release" antes da seção "## TDD — non-negotiable" (L106); (b) atualizar L109 e L144 para referenciar `specs/releases/<active>/{SPEC,TASKS}.md`. **Critério:** grep `releases/<active>` → ≥2 hits; grep `features/<feature>` → 0 hits fora do bloco "Legacy compat".

- [x] T-2.2 `[parallel: yes]` Editar `dadaia_workspace/public/agents/qa-engineer.md`: (a) inserir bloco "Resolving the active release" antes da seção "## Test quality audit"; (b) atualizar Spec gate (L320–322) — substituir `memory/architecture.md` por `memory/architecture.html`, remover `(optional)`, e substituir `features/<feature>/{SPEC,TASKS}.md` por `releases/<active>/{SPEC,TASKS}.md`. **Critério:** grep `features/<feature>` → 0 hits fora de "Legacy compat".

- [x] T-2.3 `[parallel: yes]` Editar `dadaia_workspace/public/agents/devops-engineer.md`: (a) inserir bloco "Resolving the active release" dentro de "## Workspace Protocol" após "### Context discovery"; (b) atualizar L617 (manter `repos/<slug>/specs/constitution.md`, ok) + L622 (exemplo `specs/features/deploy-pipeline/` → `specs/releases/<release-id>/`); (c) atualizar L434 (corpo do exemplo "spec conflict") para path de release. **Critério:** grep `specs/features/` → 0 hits fora de "Legacy compat".

- [x] T-2.4 `[parallel: yes]` Editar `dadaia_workspace/public/agents/frontend-engineer.md`: (a) inserir bloco "Resolving the active release" antes da seção "## TDD — non-negotiable" (L124); (b) atualizar L127 e L187 referenciando `specs/releases/<active>/{SPEC,TASKS}.md`. **Critério:** mesmo padrão que T-2.1.

- [x] T-2.5 `[parallel: yes]` Verificar `dadaia_workspace/public/agents/backend-engineer.md` está limpo (sem `features/<feature>` ou `memory/.*\.md`). **Critério:** `grep -E "features/<feature>|memory/.*\.md" backend-engineer.md` → 0 hits. Se passar, marcar `[x]` imediatamente sem edit; se falhar, abrir sub-task de correção.

---

## Phase 3 — Doctor checks (ACTIVE.md hardening + backlog schema)

- [x] T-3.1 `[parallel: no]` Editar `dadaia_workspace/features/specs/doctor.py` `_read_active_md` (linhas 192–200): tratar empty values (`release: ` e `phase: ` com espaços apenas) como `None`. **Critério:** `_read_active_md` retorna tupla `(None, None, error_message)` quando valores são whitespace-only.

- [x] T-3.2 `[parallel: no]` Adicionar método `_check_backlog_schema` em `dadaia_workspace/features/specs/doctor.py` (código SPEC-DOC-012, severity WARNING). Skipa seções `## Histórico*` e linhas sem `- `. Regex documentado em PLAN.md Fase 3 Edit B. Registrar no `check()` via `issues.extend(self._check_backlog_schema())`. **Critério:** método existe; `check()` o invoca.

- [x] T-3.3 `[parallel: yes com 3.4/3.5]` Adicionar testes em `tests/unit/features/specs/test_doctor.py`: `test_active_md_empty_release_value_is_error`, `test_active_md_empty_phase_value_is_error`. Cada um escreve ACTIVE.md malformado em `tmp_path` e espera issue SPEC-DOC-003 ERROR. **Critério:** 2 testes novos verdes.

- [x] T-3.4 `[parallel: yes com 3.3/3.5]` Adicionar testes positivos em `tests/unit/features/specs/test_doctor.py`: `test_backlog_well_formed_passes`, `test_backlog_historico_section_skipped`. **Critério:** 2 testes novos verdes; nenhum issue gerado.

- [x] T-3.5 `[parallel: yes com 3.3/3.4]` Adicionar teste negativo em `tests/unit/features/specs/test_doctor.py`: `test_backlog_malformed_bullet_warns`. **Critério:** 1 teste novo verde gerando SPEC-DOC-012 WARNING.

- [x] T-3.6 `[parallel: no]` Rodar `pytest tests/unit/features/specs/test_doctor.py -v` e confirmar 27+ testes verdes. **Critério:** exit 0; saída lista os 5 testes novos por nome.

- [x] T-3.7 `[parallel: no]` Rodar `dadaia specs doctor --specs-dir specs` no próprio workspace. **Critério:** exit 0 (warnings em backlog atuais aceitáveis; fixar `candidates.md` se houver falha de schema flagrante para evitar ruído).

---

## Phase 4 — CI hook

- [x] T-4.1 `[parallel: no]` Editar `.github/workflows/ci.yml`: adicionar job `specs-doctor` no padrão dos jobs `lint/typecheck/test`. Comando: `poetry run dadaia specs doctor --specs-dir specs`. Timeout 3min. Reusa cache Poetry. **Critério:** YAML válido (sem indentação quebrada); job aparece em `gh workflow view CI` após push.

---

## Phase 5 — Propagação e verificação end-to-end

- [-] T-5.1 `[parallel: no]` Rodar `dadaia public stage && dadaia public install --target all`. Cobre agentes (Fases 1–2), skills E1 + workflows E2 (Fase 6), templates atualizados (Fase 7). **Critério:** sem erro; mensagens de install para cada arquivo editado em agents/, skills/, workflows/ e templates/.

- [ ] T-5.2 `[parallel: no]` Rodar `dadaia public doctor`. **Critério:** `[ok]` em todos os targets para agentes, skills, workflows e templates editados. Se drift, escalar antes de `--force`.

- [ ] T-5.3 `[parallel: no]` Verificação final agents: `grep -rn "memory/architecture\.md\|features/<feature>/SPEC\|features/<feature>/TASKS" dadaia_workspace/public/agents/{software-architect,software-engineer,qa-engineer,devops-engineer,frontend-engineer,backend-engineer}.md`. **Critério:** hits aparecem **apenas** dentro de blocos "Legacy compat".

- [ ] T-5.4 `[parallel: no]` Verificação final skills+workflows: `grep -rnE "features/<feat>/|memory/architecture\.md|memory/product\.html\b" dadaia_workspace/public/{skills,workflows}/**/*.md`. **Critério:** 0 hits fora de blocos "Legacy compat".

- [ ] T-5.5 `[parallel: no]` Rodar `dadaia specs doctor` final no workspace + `pytest tests/unit/features/specs/`. **Critério:** doctor exit 0; pytest 30+ verde (22 originais + 5 doctor novos + 3+ scaffolder).

---

## Phase 6 — Skills + Workflows alignment (E1 + E2, paralelizáveis entre si)

### E1 — Skills (4 patches surgical, write-sets disjuntos)

- [x] T-E1.1 `[parallel: yes]` Editar `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md` L32: substituir "raiz `specs/TASKS.md` ou `specs/features/<feat>/TASKS.md`" por primary `specs/releases/<active>/TASKS.md` (resolver via `releases/ACTIVE.md`) + nota "Legacy compat: se `releases/ACTIVE.md` ausente, cair em `features/<feat>/TASKS.md` com `SDD_LEGACY_FEATURES=1`". **Critério:** grep `specs/releases/<active>/TASKS.md` → ≥1 hit; nota legacy presente.

- [x] T-E1.2 `[parallel: yes]` Editar `dadaia_workspace/public/skills/dadaia-release-closure/SKILL.md` L71 (bullets "Memory updates"): substituir `specs/memory/product.html` (singular inexistente) por catálogo folder `specs/memory/product/index.html` + per-feature `specs/memory/product/<slug>.html`. **Critério:** grep `memory/product\.html\b` → 0 hits; grep `memory/product/index\.html` → ≥1 hit.

- [x] T-E1.3 `[parallel: yes]` Editar `dadaia_workspace/public/skills/architect-code-audit/SKILL.md` L27 (Phase 0 — Context Loading): `specs/memory/architecture.md` → `specs/memory/architecture.html`. **Critério:** grep `memory/architecture\.md` → 0 hits.

- [x] T-E1.4 `[parallel: yes]` Editar `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` L196 (tabela "Edições Pendentes"): exemplo `specs/features/platform/snapshots/SPEC.md` → `specs/releases/<release-id>/SPEC.md`. **Critério:** grep `features/platform/snapshots` → 0 hits.

### E2 — Workflows (4 patches, write-sets disjuntos)

- [x] T-E2.1 `[parallel: yes]` Editar `dadaia_workspace/public/workflows/spec-refinement.workflow.md` L14 + L92: renomear input `topic` → `release_id` (description: "Release ID under `specs/releases/`"); `path: "specs/features/{topic}/SPEC.md"` → `path: "specs/releases/{release_id}/SPEC.md"`. **Critério:** grep `features/{topic}` → 0 hits; grep `releases/{release_id}/SPEC.md` → ≥1 hit.

- [x] T-E2.2 `[parallel: yes]` Editar `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md` L14: ajustar description do input para "Release ID under `specs/releases/`" preservando compat retroativa (alias para nome antigo se houver chamadas). **Critério:** description menciona `specs/releases/`.

- [x] T-E2.3 `[parallel: yes]` Editar `dadaia_workspace/public/workflows/architecture-review.workflow.md` L20: description do input — "When scope=feature, the release id under `specs/releases/`". **Critério:** description menciona `specs/releases/`.

- [x] T-E2.4 `[parallel: yes]` Editar `dadaia_workspace/public/workflows/game-spec-definition.workflow.md` L104 (path-only patch): `specs/features/<jogo>/SPEC.md` → `specs/releases/{release_id}/SPEC.md`. Semântica de game scope continua tracked em backlog `game-agents-split`. **Critério:** grep `features/<jogo>` → 0 hits.

---

## Phase 7 — Scaffold CLI `dadaia specs init` (E3)

- [x] T-E3.1 `[parallel: no]` Atualizar 3 templates `dadaia_workspace/public/templates/memory-{architecture,tech-stack,product-index}.html.j2` com placeholders `{{ project_name }}`, `{{ today }}`, `{{ last_release_id }}` (default `"none"`), `{{ architecture_overview }}`, `{{ layers_html }}` (default `<p>Sem camadas registradas.</p>`) e catálogo vazio. Defaults devem ser opcionais (renders existentes não quebram). **Critério:** renderizar cada template com dict vazio não levanta `jinja2.UndefinedError`.

- [x] T-E3.2 `[parallel: no]` Criar módulo `dadaia_workspace/features/specs/scaffolder.py` com função pura `scaffold(specs_dir: Path, project_name: str, force: bool, templates_dir: Path) -> list[str]`. Cria 8 outputs canônicos + 3 `.gitkeep` (lista em SPEC §Delta E3). Idempotente: arquivo existente → `[skip] <path>`; `force=True` → `[overwrite] <path>`. Sem `force`, retorno é determinístico. **Critério:** módulo existe; função tem assinatura especificada; mypy passa.

- [x] T-E3.3 `[parallel: no]` Wiring CLI em `dadaia_workspace/cli/commands/specs.py`: adicionar subcomando `init` ao grupo `specs`. Args: `--specs-dir <path>` (default `./specs/`), `--name <project-name>` (default = parent dir name), `--force` (default false). Output: lista linhas `[created] / [skip] / [overwrite] <path>`. **Critério:** `dadaia specs init --help` mostra os 3 flags; subcomando aparece em `dadaia specs --help`.

- [x] T-E3.4 `[parallel: yes com T-E3.5]` Editar `dadaia_workspace/features/specs/doctor.py`: (a) adicionar `"none"` em `CANONICAL_PHASES`; (b) short-circuit em todos os `_check_*` que dependem de release ativa quando `release == "none"` (estende tratamento existente das linhas 414/434). **Critério:** `dadaia specs doctor --specs-dir <repo-com-release-none>` exit 0; nenhum issue release-scoped reportado.

- [x] T-E3.5 `[parallel: yes com T-E3.4]` Criar `tests/unit/features/specs/test_scaffolder.py` com 3+ testes: (1) `test_scaffold_happy_path` — `tmp_path` vazio gera toda a árvore; (2) `test_scaffold_is_idempotent` — segunda execução retorna `[skip]` em todos os outputs; (3) `test_scaffold_force_overwrites` — `force=True` reescreve. Bonus opcional: `test_templates_render_with_defaults` — render sem dict não falha. **Critério:** 3+ testes verdes.

- [x] T-E3.6 `[parallel: no]` Rodar `pytest tests/unit/features/specs/` → todos verdes (22 originais + 5 doctor novos da Fase 3 + 3+ scaffolder). **Critério:** exit 0; ≥30 testes.

- [x] T-E3.7 `[parallel: no]` Smoke test end-to-end: `dadaia specs init --specs-dir /tmp/sdd-init-smoke --name testing && dadaia specs doctor --specs-dir /tmp/sdd-init-smoke`. **Critério:** init imprime ≥11 linhas `[created]`; doctor exit 0; árvore inspecionada manualmente.

---

## Phase 8 — Migration playbook (E4)

- [x] T-E4.1 `[parallel: no]` Criar `docs/sdd-migration-playbook.md` (operator-facing, estilo `docs/sdd_patterns.md`, ≤ 200 linhas). 6 seções canônicas conforme SPEC §Delta E4: Preconditions, Scaffold, Triage, Migrar memory, Ativar primeira release, Verificar com doctor + ativar context. **Critério:** arquivo existe; tem 6 headers `## ` correspondentes às seções.

- [x] T-E4.2 `[parallel: no]` Revisar o playbook cross-referenciando contra `sdd-release-lifecycle-v1/SPEC.md` Phase 6 (a migração real do dadaia-workspace serve como exemplo trabalhado). Ajustar passos divergentes. **Critério:** ≥1 referência inline a `sdd-release-lifecycle-v1/SPEC.md` Phase 6 como case study.

- [x] T-E4.3 `[parallel: no]` Verificar `wc -l docs/sdd-migration-playbook.md` ≤ 200. **Critério:** comando retorna ≤ 200.

---

## Parallelism notes

- **Phase 1** (3 tasks): T-1.1/T-1.2/T-1.3 mesmo arquivo, sequenciais (write-set único)
- **Phase 2** (5 tasks): T-2.1/T-2.2/T-2.3/T-2.4/T-2.5 paralelas — arquivos disjuntos
- **Phase 3** (7 tasks): T-3.1 + T-3.2 sequenciais; T-3.3/T-3.4/T-3.5 paralelas; T-3.6/T-3.7 sequenciais e bloqueiam Phase 4
- **Phase 4** (1 task): bloqueia Phase 5
- **Phase 5** (5 tasks): sequenciais — propagação → doctor → grep agents → grep skills/workflows → verificação total
- **Phase 6** (8 tasks): T-E1.1/E1.2/E1.3/E1.4 e T-E2.1/E2.2/E2.3/E2.4 **totalmente paralelas** — 8 arquivos disjuntos sob `public/{skills,workflows}/`
- **Phase 7** (7 tasks): T-E3.1 (templates) e T-E3.4 (doctor) independentes; T-E3.2 (scaffolder) → T-E3.3 (CLI wiring) sequenciais; T-E3.5 (tests) paralela com T-E3.4; T-E3.6 + T-E3.7 sequenciais finais
- **Phase 8** (3 tasks): single file — sequenciais

Phases 1, 2, 3, 6, 8 podem rodar em paralelo entre si (write-sets disjuntos: agentes × doctor.py × tests × skills/workflows × docs). Phase 4 depende de Phase 3. Phase 7 independente de tudo exceto Phase 5 (que cobre propagação dos templates). Phase 5 depende de 1+2+3+6+7.

---

## Definition of Done (release completa, antes de CLOSURE)

- Todos os 39 tasks marcados `[x]` (18 originais + 1 T-5.4 novo grep skills+workflows + 4 E1 + 4 E2 + 7 E3 + 3 E4)
- `dadaia specs doctor` no workspace → 0 errors
- `pytest tests/unit/features/specs/` → all green (≥30 testes)
- `dadaia public doctor` → `[ok]` todos (agents + skills + workflows + templates)
- CI verde no PR final
- Operador aprovou os patches dos 6 agentes + 4 skills + 4 workflows (revisão visual)
- `dadaia specs init` smoke-tested em `/tmp/sdd-init-smoke` com sucesso
- `docs/sdd-migration-playbook.md` existe e tem ≤ 200 linhas

CLOSURE (não nesta sessão): operador decide flipar para CLOSURE depois de adicionar
backlog adicional. Quando promover: writes em `specs/memory/*` só serão permitidos durante
phase=CLOSURE; esta release **não** atualiza memory (decisão D9 da SPEC), então CLOSURE.md
documentará isso explicitamente na seção `## Memory updates`.
