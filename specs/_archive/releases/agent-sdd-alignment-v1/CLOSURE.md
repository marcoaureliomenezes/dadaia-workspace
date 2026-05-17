# Closure: Release — agent-sdd-alignment-v1

> **Status:** Aprovado
> **Release ID:** agent-sdd-alignment-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-16 (retroactive)
> **Spec:** `specs/releases/agent-sdd-alignment-v1/SPEC.md`
> **Plan:** `specs/releases/agent-sdd-alignment-v1/PLAN.md`
> **Tasks:** `specs/releases/agent-sdd-alignment-v1/TASKS.md`

---

## Summary

Release `agent-sdd-alignment-v1` fechou o gap cognitivo entre o modelo SDD release-based
(implantado em `sdd-release-lifecycle-v1`) e os 6 agentes especialistas não-game-engine
(`software-architect`, `software-engineer`, `qa-engineer`, `devops-engineer`,
`frontend-engineer`, `backend-engineer`), além de 4 skills e 4 workflows
(`dadaia-task-manager`, `dadaia-release-closure`, `architect-code-audit`, `dadaia-grill-me`;
`spec-refinement`, `cross-cutting-feature`, `architecture-review`, `game-spec-definition`).
Cada agente/skill/workflow recebeu **surgical patch** mantendo voz e estrutura, substituindo
referências legacy (`specs/memory/architecture.md`, `specs/features/<feat>/{SPEC,TASKS}.md`,
`specs/memory/product.html`) pelos paths release-based (`specs/memory/architecture.html`,
`specs/memory/product/index.html`, `specs/memory/tech-stack.html`,
`specs/releases/<active>/{SPEC,TASKS}.md`) e adicionando bloco "Resolving the active release"
nos agentes implementers. Compat legacy (`SDD_LEGACY_FEATURES=1`) preservada para outros repos
ainda não migrados.

Endurecimento estrutural do doctor (`SPEC-DOC-003` estendido com validação de valores não-vazios
em ACTIVE.md; `SPEC-DOC-012` novo para schema do `backlog/candidates.md`). Novo subcomando
`dadaia specs init <name>` (E3) com `scaffolder.py` + 3 templates atualizados + adição de
`"none"` em `CANONICAL_PHASES`. Migration playbook (E4) em `docs/sdd-migration-playbook.md`.
CI hook `specs-doctor` em `.github/workflows/ci.yml` para regressão automatizada.

39 tasks executadas em 8 fases (Phase 1–5 + E1/E2/E3/E4). Todas marcadas `[x]` no
TASKS.md.

---

## Drifts

### lifecycle-drift — retroactive closure

**Description:** Release implementação-completa (todas as 39 tasks `[x]`, `dadaia specs doctor`
green, `pytest tests/unit/features/specs/` green, `dadaia public doctor` ok em todos os targets,
CI verde), mas `ACTIVE.md` foi flipado direto para `release: sdd-hotfix-track-v1 / phase: SPEC`
sem passar por `CLOSURE` desta release. Quando `sdd-hotfix-track-v1` foi encerrado em
2026-05-16 (sua própria CLOSURE.md gravada e archive concluído), `ACTIVE.md` voltou para
`release: none / phase: none` — e esta release ficou "pendurada" em `specs/releases/` sem
CLOSURE.md, violando memory atomicity (lifecycle gate v3 exige passagem por `phase: CLOSURE`
antes de archive). Retroactive closure executada em 2026-05-16, mesmo dia em que o operador
desbloqueou o pipeline para `dadaia-workspace-panel-v1`.

**Resolution:** `ACTIVE.md` flipado para `release: agent-sdd-alignment-v1 / phase: CLOSURE`
antes de qualquer escrita em `specs/memory/*` ou em CLOSURE.md desta release. Memory updates
(catalog index + novo feature card `agent-sdd-alignment.html`) executados nessa janela. Após
gravação completa do CLOSURE.md + memory updates + archive (`git mv` para
`_archive/releases/agent-sdd-alignment-v1`), `ACTIVE.md` volta a `release: none / phase: none`
e libera flip para `dadaia-workspace-panel-v1`.

**Impact:** zero em produção — a release já estava implementada e em uso. Drift puramente de
audit-trail: o histórico passa a refletir corretamente que esta release foi promovida a
CLOSURE em sequência, não saltada. CLOSURE evidence (this file) e memory updates landamemória.

### stale-tasks-in-meta-release (transcrito da SPEC §"Drifts conhecidos" #1)

**Description:** `sdd-release-lifecycle-v1/TASKS.md` tinha 11 tasks marcadas `[ ]` que já
estavam implementadas (T-5.2/T-5.3/T-5.4/T-5.5/T-5.6 da CLI `dadaia specs doctor` + T-V.1 a
T-V.6 do end-to-end verification). Evidência: `dadaia_workspace/cli/commands/specs.py` existe;
`dadaia_workspace/features/specs/doctor.py` retorna `[]` em `specs/`;
`tests/unit/features/specs/test_doctor.py` tinha 22 testes green no CI no momento da SPEC.

**Resolution:** Esta release não tocou o `TASKS.md` da meta-release (decisão D8 da SPEC).
A meta-release `sdd-release-lifecycle-v1` ainda está em `IMPLEMENTATION` e essa pendência
permanece para a sua própria CLOSURE futura. Documentação preservada nesta seção para que o
encerramento daquela release não perca o pointer.

**Impact:** zero operacional — funcionalidade está em uso e coberta por testes verdes. Drift
puramente de marker state na TASKS.md da meta-release.

### game-agents-still-on-legacy-paths (transcrito da SPEC §"Drifts conhecidos" #2)

**Description:** Agentes `game-developer` e `game-designer` continuam referenciando
`specs/features/<jogo>/{SPEC,TASKS}.md`. Workflow `game-spec-definition.workflow.md`
recebeu patch de path apenas (T-E2.4); os agentes em si ficaram fora de escopo (decisão D1
da SPEC).

**Resolution:** Tracked em `backlog/candidates.md` como `game-agents-split`. Futura release
patcha os 3 agentes de jogo seguindo mesmo padrão surgical desta.

**Impact:** zero — repos `redacted-slug/` ainda não migraram para release-based; agentes ainda
funcionais no caminho legacy.

### other-readiness-audit-items (transcrito da SPEC §"Drifts conhecidos" #3)

**Description:** OpenCode hooks (item #5 do readiness audit), game agents alignment (#6),
`primary_context` choice/multi-context (#7), closing `sdd-release-lifecycle-v1` (#8). Listados
em "Fora de escopo" desta SPEC.

**Resolution:** Item #5 (OpenCode hooks) e #7 (primary_context choice) seguem tracked em
"Fora de escopo" — sem entry no backlog ainda; serão promovidos quando o operador decidir
priorizar. Item #6 → backlog `game-agents-split` (já presente). Item #8 (closing
`sdd-release-lifecycle-v1`) depende do operador encerrar aquela release.

**Impact:** zero — itens conhecidos e tracked.

### migration-playbook-not-propagated (transcrito da SPEC §"Drifts conhecidos" #4)

**Description:** `docs/sdd-migration-playbook.md` (E4) vive em `docs/`, não em `public/data/`.
Operadores de outros repos leem direto do dadaia-workspace ao migrar — não há projeção para
`.agents/`, `.claude/`, `.codex/`, `.opencode/`.

**Resolution:** Decisão D12 da SPEC. Se no futuro for desejável projeção, estende-se
`_VALID_TARGETS` em `dadaia_workspace/features/public/install.py` para incluir arquivos
`data/*.md` arbitrários — fora de escopo desta release.

**Impact:** zero — playbook é operator-facing e lido manualmente; padrão `docs/sdd_patterns.md`.

---

## Validations

Evidence triples (description, command, evidence) para todas as 39 tasks. Agrupado por phase
para legibilidade. Cada bloco usa o critério literal da TASKS.md como evidence assertion.

### Phase 1 — software-architect alignment

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-1.1 | ONBOARD workflow do software-architect referencia `memory/architecture.html`, `memory/product/index.html`, `memory/tech-stack.html` | `grep "memory/architecture.html" dadaia_workspace/public/agents/software-architect.md` | ≥1 hit (critério T-1.1) |
| T-1.2 | REVIEW workflow do software-architect substitui `memory/architecture.md` e marca `foundation/SPEC.md` opcional | `grep "memory/architecture.md" dadaia_workspace/public/agents/software-architect.md` | 0 hits (critério T-1.2) |
| T-1.3 | Report Template (Architecture Status) referencia `architecture.html` | inspeção visual da seção Report Template | template `Architecture Status` referencia `architecture.html` (critério T-1.3) |

### Phase 2 — Implementer agents alignment

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-2.1 | `software-engineer.md` ganha bloco "Resolving the active release" + L109/L144 apontam para `specs/releases/<active>/{SPEC,TASKS}.md` | `grep "releases/<active>" dadaia_workspace/public/agents/software-engineer.md`; `grep "features/<feature>" dadaia_workspace/public/agents/software-engineer.md` | ≥2 hits no primeiro grep; 0 hits no segundo fora de "Legacy compat" (critério T-2.1) |
| T-2.2 | `qa-engineer.md` ganha bloco "Resolving the active release" + Spec gate (L320–322) atualizado para release-based | `grep "features/<feature>" dadaia_workspace/public/agents/qa-engineer.md` | 0 hits fora de "Legacy compat" (critério T-2.2) |
| T-2.3 | `devops-engineer.md` Workspace Protocol atualizado para release-based (L617/L622/L434) | `grep "specs/features/" dadaia_workspace/public/agents/devops-engineer.md` | 0 hits fora de "Legacy compat" (critério T-2.3) |
| T-2.4 | `frontend-engineer.md` ganha bloco "Resolving the active release" + L127/L187 apontam para release-based | grep mesmo padrão de T-2.1 aplicado a frontend-engineer.md | ≥2 hits + 0 hits legacy (critério T-2.4) |
| T-2.5 | `backend-engineer.md` confirmado limpo | `grep -E "features/<feature>\|memory/.*\.md" dadaia_workspace/public/agents/backend-engineer.md` | 0 hits (critério T-2.5) |

### Phase 3 — Doctor checks (ACTIVE.md hardening + backlog schema)

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-3.1 | `_read_active_md` trata empty values como `None` | leitura de `dadaia_workspace/features/specs/doctor.py` linhas 192–200 + execução de testes T-3.3 | `_read_active_md` retorna `(None, None, error_message)` quando whitespace-only (critério T-3.1) |
| T-3.2 | `_check_backlog_schema` adicionado (SPEC-DOC-012 WARNING) | leitura de `doctor.py` + `grep "_check_backlog_schema" dadaia_workspace/features/specs/doctor.py` | método existe; `check()` o invoca (critério T-3.2) |
| T-3.3 | Testes negativos ACTIVE.md (empty release / empty phase) | `pytest tests/unit/features/specs/test_doctor.py -k "active_md_empty" -v` | 2 testes novos verdes gerando SPEC-DOC-003 ERROR (critério T-3.3) |
| T-3.4 | Testes positivos backlog (well-formed + Histórico skip) | `pytest tests/unit/features/specs/test_doctor.py -k "backlog" -v` | 2 testes novos verdes sem issues (critério T-3.4) |
| T-3.5 | Teste negativo backlog (malformed bullet) | `pytest tests/unit/features/specs/test_doctor.py -k "backlog_malformed" -v` | 1 teste verde gerando SPEC-DOC-012 WARNING (critério T-3.5) |
| T-3.6 | `pytest tests/unit/features/specs/test_doctor.py -v` 27+ verdes | `pytest tests/unit/features/specs/test_doctor.py -v` | exit 0 com os 5 testes novos listados (critério T-3.6) |
| T-3.7 | `dadaia specs doctor --specs-dir specs` no próprio workspace | `dadaia specs doctor --specs-dir specs` | exit 0 (critério T-3.7) |

### Phase 4 — CI hook

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-4.1 | `.github/workflows/ci.yml` ganha job `specs-doctor` rodando `poetry run dadaia specs doctor --specs-dir specs` | `gh workflow view CI` ou leitura visual de `.github/workflows/ci.yml` | YAML válido; job aparece em CI (critério T-4.1) |

### Phase 5 — Propagação e verificação end-to-end

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-5.1 | `dadaia public stage && dadaia public install --target all` propaga sem erro | `dadaia public stage && dadaia public install --target all` | mensagens de install para cada arquivo editado (critério T-5.1) |
| T-5.2 | `dadaia public doctor` retorna `[ok]` em todos os targets | `dadaia public doctor` | `[ok]` em agents/skills/workflows/templates (critério T-5.2) |
| T-5.3 | Verificação final agents: nenhum hit legacy fora de "Legacy compat" | `grep -rn "memory/architecture\.md\|features/<feature>/SPEC\|features/<feature>/TASKS" dadaia_workspace/public/agents/{software-architect,software-engineer,qa-engineer,devops-engineer,frontend-engineer,backend-engineer}.md` | hits aparecem apenas dentro de blocos "Legacy compat" (critério T-5.3) |
| T-5.4 | Verificação final skills+workflows: 0 hits legacy fora de "Legacy compat" | `grep -rnE "features/<feat>/\|memory/architecture\.md\|memory/product\.html\b" dadaia_workspace/public/{skills,workflows}/**/*.md` | 0 hits fora de "Legacy compat" (critério T-5.4) |
| T-5.5 | Doctor + pytest finais | `dadaia specs doctor && pytest tests/unit/features/specs/` | doctor exit 0; pytest ≥30 verdes (critério T-5.5) |

### Phase 6 — Skills + Workflows alignment (E1 + E2)

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-E1.1 | `dadaia-task-manager/SKILL.md` L32 reescrito para release-based + nota Legacy compat | `grep "specs/releases/<active>/TASKS.md" dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md` | ≥1 hit; nota legacy presente (critério T-E1.1) |
| T-E1.2 | `dadaia-release-closure/SKILL.md` L71 substitui `memory/product.html` por catálogo folder | `grep "memory/product\.html\b" dadaia_workspace/public/skills/dadaia-release-closure/SKILL.md`; `grep "memory/product/index\.html"` | 0 hits no primeiro; ≥1 hit no segundo (critério T-E1.2) |
| T-E1.3 | `architect-code-audit/SKILL.md` L27 `memory/architecture.md` → `memory/architecture.html` | `grep "memory/architecture\.md" dadaia_workspace/public/skills/architect-code-audit/SKILL.md` | 0 hits (critério T-E1.3) |
| T-E1.4 | `dadaia-grill-me/SKILL.md` L196 exemplo atualizado para path de release | `grep "features/platform/snapshots" dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` | 0 hits (critério T-E1.4) |
| T-E2.1 | `spec-refinement.workflow.md` L14+L92 input `topic` → `release_id`; path → `specs/releases/{release_id}/SPEC.md` | `grep "features/{topic}"` workflow; `grep "releases/{release_id}/SPEC.md"` workflow | 0 hits no primeiro; ≥1 hit no segundo (critério T-E2.1) |
| T-E2.2 | `cross-cutting-feature.workflow.md` L14 description menciona `specs/releases/` | inspeção visual do header do workflow | description menciona `specs/releases/` (critério T-E2.2) |
| T-E2.3 | `architecture-review.workflow.md` L20 description menciona release id sob `specs/releases/` | inspeção visual do header do workflow | description menciona `specs/releases/` (critério T-E2.3) |
| T-E2.4 | `game-spec-definition.workflow.md` L104 path-only patch para release-based | `grep "features/<jogo>" dadaia_workspace/public/workflows/game-spec-definition.workflow.md` | 0 hits (critério T-E2.4) |

### Phase 7 — Scaffold CLI `dadaia specs init` (E3)

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-E3.1 | 3 templates `memory-{architecture,tech-stack,product-index}.html.j2` aceitam render com dict vazio | render dos templates em pytest com dict vazio | sem `jinja2.UndefinedError` (critério T-E3.1) |
| T-E3.2 | Módulo `scaffolder.py` com função pura `scaffold(...)` | leitura de `dadaia_workspace/features/specs/scaffolder.py`; `mypy dadaia_workspace/features/specs/scaffolder.py` | módulo existe; assinatura especificada; mypy passa (critério T-E3.2) |
| T-E3.3 | CLI wiring `dadaia specs init` com `--specs-dir`/`--name`/`--force` | `dadaia specs init --help`; `dadaia specs --help` | os 3 flags aparecem; subcomando aparece no grupo specs (critério T-E3.3) |
| T-E3.4 | `CANONICAL_PHASES` inclui `"none"` + short-circuit em release `none` | `dadaia specs doctor --specs-dir <repo-com-release-none>` | exit 0; nenhum issue release-scoped (critério T-E3.4) |
| T-E3.5 | `test_scaffolder.py` com happy/idempotency/force (3+ testes verdes) | `pytest tests/unit/features/specs/test_scaffolder.py -v` | 3+ testes verdes (critério T-E3.5) |
| T-E3.6 | `pytest tests/unit/features/specs/` ≥30 verdes total | `pytest tests/unit/features/specs/` | exit 0; ≥30 testes (critério T-E3.6) |
| T-E3.7 | Smoke test end-to-end de `dadaia specs init` + `doctor` | `dadaia specs init --specs-dir /tmp/sdd-init-smoke --name testing && dadaia specs doctor --specs-dir /tmp/sdd-init-smoke` | init imprime ≥11 linhas `[created]`; doctor exit 0 (critério T-E3.7) |

### Phase 8 — Migration playbook (E4)

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| T-E4.1 | `docs/sdd-migration-playbook.md` criado com 6 seções canônicas | `grep -E "^## " docs/sdd-migration-playbook.md` | arquivo existe; tem 6 headers `## ` (critério T-E4.1) |
| T-E4.2 | Playbook referencia `sdd-release-lifecycle-v1/SPEC.md` Phase 6 como case study | `grep "sdd-release-lifecycle-v1" docs/sdd-migration-playbook.md` | ≥1 referência inline (critério T-E4.2) |
| T-E4.3 | `wc -l docs/sdd-migration-playbook.md` ≤ 200 | `wc -l docs/sdd-migration-playbook.md` | retorna ≤ 200 (critério T-E4.3) |

---

## Memory updates

- `specs/memory/product/agent-sdd-alignment.html` — **criado** (novo feature card). Documenta:
  alinhamento dos 6 agentes especialistas + 4 skills + 4 workflows com modelo SDD release-based;
  bloco "Resolving the active release" como padrão; endurecimento de `_read_active_md`
  (SPEC-DOC-003 estendido); novo check `_check_backlog_schema` (SPEC-DOC-012); novo subcomando
  `dadaia specs init <name>` com scaffolder + templates atualizados (`"none"` em
  `CANONICAL_PHASES`); migration playbook em `docs/sdd-migration-playbook.md`; CI hook
  `specs-doctor`. Compat legacy via `SDD_LEGACY_FEATURES=1` preservada.
- `specs/memory/product/index.html` — **atualizado**: nova entry no catálogo apontando para
  `agent-sdd-alignment.html`, inserida entre `sdd-hotfix-track.html` e `academy.html`
  (proximidade conceitual com `sdd-gate-v3.html` / `specs-doctor.html` / `sdd-hotfix-track.html`).
  Meta `Última atualização` agora referencia `Closure: agent-sdd-alignment-v1`.
- Nenhum dos outros HTMLs de memory (`workspace-init`, `context-management`,
  `agent-orchestration`, `public-asset-distribution`, `workspace-doctor`, `specs-doctor`,
  `sdd-gate-v3`, `sdd-hotfix-track`, `academy`, `workspace-portability`, `repos-catalog`,
  `server-registry`) foi tocado — esta release alinhou definições agentic com modelo já
  documentado, não introduziu nova capability de produto.
- `specs/memory/architecture.html` e `specs/memory/tech-stack.html` permanecem intocados —
  esta release não muda arquitetura nem stack; apenas reescreve referências cognitivas dos
  agentes.

---

## Backlog returns

- `agent-sdd-alignment` **não** estava em `specs/backlog/candidates.md § Candidatas ativas` (a
  release nasceu de revisão pós-`sdd-release-lifecycle-v1`, não de promoção do backlog). Sem
  movimentação para `## Histórico` necessária.
- Nenhum item novo retornando ao backlog nesta closure — os 4 drifts não-resolvidos (stale
  tasks da meta-release, game-agents-split, readiness audit items #5/#7/#8, playbook não
  propagado) já estão tracked nas seções "Fora de escopo" desta SPEC e nos respectivos itens
  pré-existentes do `candidates.md` (notavelmente `game-agents-split`).

---

## Archive decision

**MOVE** — diretório `specs/releases/agent-sdd-alignment-v1/` será relocado para
`specs/_archive/releases/agent-sdd-alignment-v1/` via `git mv` após este CLOSURE.md ser
gravado, memory updates concluídos e `ACTIVE.md` retornar para `release: none / phase: none`.
A retroatividade desta closure (2026-05-16) é registrada na seção `## Drifts` acima como
`lifecycle-drift`. Pós-archive, `ACTIVE.md` libera para flip a `dadaia-workspace-panel-v1`.
