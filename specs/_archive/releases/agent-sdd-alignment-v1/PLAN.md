# Plan: Release — agent-sdd-alignment-v1

> **Status:** Aprovado
> **Release ID:** agent-sdd-alignment-v1
> **Owner:** product-engineer
> **Estimativa total:** ~3 sessões de implementação curtas (≤2h cada)

---

## Estratégia geral

Trabalho dividido em **5 fases sequenciais**, agrupadas por write-set para minimizar
conflito e permitir paralelismo dentro de cada fase. Fases 1–3 são puramente edits em
arquivos texto (agentes + doctor.py + tests + CI). Fase 4 é propagação via
`dadaia public stage && install`. Fase 5 é verificação end-to-end.

Cada commit segue convencional commits + protocolo `dadaia-task-manager`
(`chore(tasks): start <id>` antes de tocar produção; commit final inclui marker `[x]`).

---

## Fase 1 — software-architect alignment

**Write set:** `dadaia_workspace/public/agents/software-architect.md` (sozinho).
**Paralelismo:** N/A (1 arquivo).

**Edits surgical (3 sites):**
1. L86–92 ONBOARD — substituir `memory/architecture.md` por trio
   `memory/architecture.html` + `memory/product/index.html` + `memory/tech-stack.html`;
   nota sobre `memory/product/<slug>.html` on demand.
2. L158 REVIEW step 2 — mesma substituição; manter `foundation/SPEC.md` como "if present".
3. L258 template Architecture Status — `architecture.md` → `architecture.html`.

**Verificação:** `grep "memory/.*\.md" software-architect.md` vazio; `grep "memory/.*\.html"` ≥3 hits.

---

## Fase 2 — Implementer agents alignment

**Write set:** 4 arquivos, paralelizáveis (write-sets disjuntos):
- `dadaia_workspace/public/agents/software-engineer.md`
- `dadaia_workspace/public/agents/qa-engineer.md`
- `dadaia_workspace/public/agents/devops-engineer.md`
- `dadaia_workspace/public/agents/frontend-engineer.md`
- (backend-engineer.md confirmado limpo; nada a fazer)

### Bloco padronizado "Resolving the active release"

Inserir uma vez por agente. Conteúdo: ler `specs/releases/ACTIVE.md` (2 linhas
`release:` / `phase:`), localizar `specs/releases/<id>/{SPEC,TASKS}.md`. Bloco "Legacy
compat" cita fallback `features/<feature>/...` com `SDD_LEGACY_FEATURES=1`.

**Pontos de inserção e patches:**

| Agente | Insert antes de | Linhas a patchar |
|--------|-----------------|------------------|
| software-engineer.md | "## TDD — non-negotiable" (L106) | L109, L144 → `specs/releases/<active>/{SPEC,TASKS}.md` |
| qa-engineer.md | "## Test quality audit" (L231) | L179, L320–322 → idem; `memory/architecture.md` → `.html`; remover `(optional)` |
| devops-engineer.md | dentro de "## Workspace Protocol" pós "### Context discovery" | L434, L622 → `specs/releases/<release-id>/`; L617 já válido |
| frontend-engineer.md | "## TDD — non-negotiable" (L124) | L127, L187 → idem software-engineer |

**Verificação:** `grep "features/<feature>/" dadaia_workspace/public/agents/{software,qa,devops,frontend,backend}-engineer.md` → 0 hits fora de "Legacy compat".

---

## Fase 3 — Doctor checks (ACTIVE.md format + backlog schema)

**Write set:**
- `dadaia_workspace/features/specs/doctor.py`
- `tests/unit/features/specs/test_doctor.py`

Paralelizável **dentro** do arquivo (doctor.py): edits são em métodos diferentes.

### Edit A — Hardening de `_read_active_md`

Atualmente (linhas 192–200) aceita `release: ` com valor vazio. Patch:

```python
# Antes
if line.startswith("release:"):
    release = line.split(":", 1)[1].strip()

# Depois
if line.startswith("release:"):
    value = line.split(":", 1)[1].strip()
    release = value if value else None
```

Mesmo tratamento para `phase:`. A função já retorna error message
`"ACTIVE.md missing 'release:' or 'phase:' line"` quando `release is None or phase is None`,
então strings vazias passam a ser tratadas como missing.

### Edit B — Novo check `_check_backlog_schema` (código SPEC-DOC-012)

Adicionar método novo em `SpecsDoctor` que parse `specs/backlog/candidates.md`. Regex:
`^- \S.*? — .+? \(owner: [a-z-]+, contexto: .+?\)\s*$`. **Apenas** bullets dentro da seção
`## Candidatas ativas` (matched por header `re.match(r"^##\s+Candidatas", line)`) são
validados. Bullets em `## Convenções`, `## Histórico` ou qualquer outra seção, e linhas
que não começam com `- `, são puladas. Falhas geram SPEC-DOC-012 **WARNING** (não
bloqueia CI; guidance, não hard contract). Backlog ausente: noop. Registrar no método
`check()` via `issues.extend(self._check_backlog_schema())`.

### Edit C — Tests

Adicionar em `tests/unit/features/specs/test_doctor.py`:

1. `test_active_md_empty_release_value_is_error` — escrever `release: \nphase: TASKS`
   → espera SPEC-DOC-003 com severity ERROR
2. `test_active_md_empty_phase_value_is_error` — espera SPEC-DOC-003
3. `test_backlog_well_formed_passes` — bullet correto não gera issue
4. `test_backlog_historico_section_skipped` — bullet no histórico com formato livre
   passa
5. `test_backlog_malformed_bullet_warns` — bullet errado gera SPEC-DOC-012 WARNING

Cada teste usa o fixture `tmp_path` que já existe (`make_specs_dir(...)` pattern).

### Verificação

```bash
pytest tests/unit/features/specs/test_doctor.py -v
# expected: 27+ tests pass (22 antigos + 5 novos)

# Rodar doctor no próprio workspace:
python -c "from dadaia_workspace.features.specs.doctor import SpecsDoctor; \
  from pathlib import Path; \
  issues = SpecsDoctor(Path('specs')).check(); \
  print(f'{len(issues)} issues'); \
  [print(f'  {i.severity.value} {i.code}: {i.description[:70]}') for i in issues]"
# expected: 0 errors. Pode ter 0–1 WARNING em backlog se algum bullet histórico-recente
# não estiver no formato (verificar manualmente).
```

---

## Fase 4 — CI hook

**Write set:** `.github/workflows/ci.yml`.

Job `specs-doctor` no padrão dos demais: checkout + setup-python 3.12 + `pipx install poetry==1.8.3` + cache compartilhado (`poetry-${{ runner.os }}-${{ hashFiles('poetry.lock') }}`) + `poetry install --with dev` + `poetry run dadaia specs doctor --specs-dir specs`. Timeout 3min. `--specs-dir specs` explícito (não depende de `primary_context.json` em CI). Fail-fast: ERROR → exit 1; WARNING não bloqueia.

**Verificação:** YAML válido + job aparece em `gh workflow view CI` após push.

---

## Fase 5 — Propagação + verificação end-to-end

**Write set:** projeções `.agents/`, `.claude/`, `.codex/`, `.opencode/` (via dadaia CLI).
**Importante**: agora propaga também skills (E1) e workflows (E2) editados nas Fases 6.

### Comandos

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

`dadaia public doctor` deve retornar `[ok]` para todos os agentes, skills e workflows
editados. Se algum target estiver em drift por edição manual prévia, decidir com operador
antes de usar `--force`.

### Smoke tests end-to-end

| Teste | Comando | Esperado |
|-------|---------|----------|
| Doctor 0 errors | `dadaia specs doctor` | exit 0 |
| Tests green | `pytest tests/unit/features/specs/` | 27+ green |
| Public doctor | `dadaia public doctor` | `[ok]` em todos os 4 targets |
| Agents grep | `grep "memory/architecture.md\|features/<feature>/SPEC.md" dadaia_workspace/public/agents/{software-architect,software-engineer,qa-engineer,devops-engineer,frontend-engineer,backend-engineer}.md` | apenas hits dentro de blocos "Legacy compat" |

---

## Fase 6 — Skills + Workflows alignment (E1+E2)

**Write set:** 8 arquivos disjuntos sob `dadaia_workspace/public/{skills,workflows}/` —
totalmente paralelos. Mesma política dos agentes: **surgical patch**, preservar voz/estrutura.

- **E1 (4 skills, 1 site cada — ver SPEC §Delta E1):** `dadaia-task-manager/SKILL.md` L32
  (primary release-based + nota legacy `SDD_LEGACY_FEATURES=1`); `dadaia-release-closure/SKILL.md`
  L71 (`memory/product.html` singular → catálogo `memory/product/index.html` + per-feature);
  `architect-code-audit/SKILL.md` L27 (`memory/architecture.md` → `.html`);
  `dadaia-grill-me/SKILL.md` L196 (exemplo de path → `specs/releases/<release-id>/SPEC.md`).
- **E2 (4 workflows — ver SPEC §Delta E2):** `spec-refinement` L14+L92 (input renomeado
  para `release_id` + path `specs/releases/{release_id}/SPEC.md`); `cross-cutting-feature`
  L14 (description release-based); `architecture-review` L20 (description release-based);
  `game-spec-definition` L104 (path-only patch; semântica game-agents-split fica no backlog).

**Verificação:** `grep -E "features/<feat>/|memory/architecture\.md|memory/product\.html\b" dadaia_workspace/public/{skills,workflows}/**/*.md` → 0 hits fora de "Legacy compat".

---

## Fase 7 — Scaffold CLI `dadaia specs init` (E3)

**Write set:** `dadaia_workspace/features/specs/scaffolder.py` (novo);
`dadaia_workspace/cli/commands/specs.py` (extensão subcomando `init`);
`dadaia_workspace/features/specs/doctor.py` (2 edits); 3 templates
`public/templates/memory-{architecture,tech-stack,product-index}.html.j2`;
`tests/unit/features/specs/test_scaffolder.py` (novo).

**Edit A — Templates:** placeholders `{{ project_name }}`, `{{ today }}`,
`{{ last_release_id }}` (default `"none"`), `{{ architecture_overview }}` (placeholder),
`{{ layers_html }}` (default `<p>Sem camadas registradas.</p>`), catálogo vazio. Defaults
opcionais — renders existentes continuam funcionando.

**Edit B — `scaffolder.py`:** função pura
`scaffold(specs_dir, project_name, force, templates_dir) -> list[str]`. Idempotente
(arquivo pré-existente → `[skip] <path>`); `force=True` → `[overwrite] <path>`. Saídas
listadas em SPEC §Delta E3 (8 arquivos + 3 `.gitkeep`).

**Edit C — CLI:** `dadaia specs init [--specs-dir <path>] [--name <project-name>] [--force]`.
Defaults: `--specs-dir=./specs/`, `--name=<parent dir name>`. Imprime `[created] / [skip] / [overwrite]`.

**Edit D — Doctor:** (1) adicionar `"none"` em `CANONICAL_PHASES`; (2) short-circuit em
checks release-scoped quando `release: none` (extends linhas 414/434 existentes).

**Edit E — Tests:** 3+ testes em `test_scaffolder.py`: happy path, idempotency, `--force`.
Bonus: render template com defaults não levanta `UndefinedError`.

**Smoke test do operador:**
```bash
dadaia specs init --specs-dir /tmp/sdd-init-smoke --name testing
dadaia specs doctor --specs-dir /tmp/sdd-init-smoke   # exit 0
```

---

## Fase 8 — Migration playbook (E4)

**Write set:** `docs/sdd-migration-playbook.md` (novo, ≤ 200 linhas). Operator-facing,
estilo `docs/sdd_patterns.md`. **Não** propagado via `dadaia public` (decisão D12).

**6 seções canônicas:** (1) **Preconditions** — `dadaia` CLI + contexto ativo; (2) **Scaffold** —
`dadaia specs init --specs-dir <repo>/specs --name <repo>`; (3) **Triage** — listar features
existentes; classificar em backlog (`ideas.md`/`candidates.md`) ou release nova; (4) **Migrar
memory** — preencher `memory/{architecture,tech-stack}.html` + `memory/product/index.html`
e per-feature `<slug>.html`; (5) **Ativar primeira release** — criar
`releases/<id>/{SPEC,PLAN,TASKS}.md` via `product-engineer`; atualizar `ACTIVE.md`;
(6) **Verificar** — `dadaia specs doctor` → 0 errors; `dadaia context activate <repo>`.

Referenciar `sdd-release-lifecycle-v1/SPEC.md` Phase 6 como exemplo trabalhado.

**Verificação:** `wc -l docs/sdd-migration-playbook.md` ≤ 200; manual review pelo operador.

---

## Sequenciamento e paralelismo

| Fase | Pode rodar em paralelo com | Motivo |
|------|---------------------------|--------|
| 1 | 3, 6, 8 | Write-sets disjuntos |
| 2 | 3, 6, 8 | Idem |
| 3 | 1, 2, 6, 8 | Idem |
| 4 | 1, 2, 3, 6, 8 | `.github/workflows/ci.yml` único |
| 6 | 1, 2, 3, 4, 8 | Skills/workflows disjuntos de tudo |
| 7 | 8 | scaffolder + doctor + tests; bloqueia Fase 5 (propagação cobre templates) |
| 8 | 1–7 | `docs/` independente |
| 5 | depende de 1–4 e 6–7 | Propagação cobre agentes, skills, workflows, templates |

Dentro de Fase 2, os 4 agentes podem ser editados em paralelo. Dentro de Fase 6, os 8
arquivos (4 skills + 4 workflows) são totalmente paralelos. Fase 7 tem edits A/B/C/D
parcialmente paralelos: Edit A (templates) independente; B+C (scaffolder + CLI) acoplados;
D (doctor) independente; E (tests) depende de B+D.

---

## Riscos operacionais e mitigações

| Risco | Mitigação |
|-------|-----------|
| Patch de agente quebrar voz/tom existente | Surgical edit revisado pelo operador no PR; sem reescrita |
| Doctor pegar muitos warnings novos em backlog atual | Verificar manualmente após Edit B; se bullets atuais não casam, fixar `candidates.md` (ou seja, esta release pode adicionar 1 commit de cleanup do backlog atual) |
| CI job falhar por `poetry install` lento | Cache compartilhado com outros jobs; timeout=3min é suficiente baseado no histórico (~1min em médias) |
| `dadaia public install` sobrescrever projeções customizadas | Usar default (não `--force`) primeiro; se drift, escalar ao operador |

---

## Critérios de pronto da PLAN

- [x] PLAN ≤ 300 linhas (limit do doctor SPEC-DOC-005)
- [x] Fases sequenciais bem-definidas
- [x] Paralelismo declarado por fase
- [x] Cada edit referenciado por arquivo + linha aproximada
- [x] Cada fase tem critério de verificação explícito
- [x] Compat legacy preservada (não quebra outros repos)
