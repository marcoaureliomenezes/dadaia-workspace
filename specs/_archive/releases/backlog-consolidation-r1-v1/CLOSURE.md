# Closure: Release — backlog-consolidation-r1-v1

> **Status:** Aprovado
> **Release ID:** backlog-consolidation-r1-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-23

## Summary

Esta release consolidou o backlog Tier A em 9 tarefas distribuídas por 7 fases. O foco foi triplo: (1) hardening do CLI e da infra de operação do workspace com 4 bug-fixes em `dadaia context deactivate`; (2) criação de uma infra formal de bug reporting capaz de detectar, persistir e surfaçar bugs automaticamente ao operador no momento de planning; (3) qualidade do DEV workspace com `[warn] git-dirty` no doctor, extensão da guardrail de self-reference e adição do 21º agente universal `data-architect`.

Todos os 9 tasks foram concluídos com commits rastreados. `dadaia public doctor` retorna all `[ok]` após propagação completa. A suite pytest tem 19 falhas pré-existentes (não relacionadas a esta release — stale skill lists, model mapping de fixtures, schema v1.0/v1.1) e zero regressões novas introduzidas.

Os itens Tier B (workflows de ciclo de vida, migration waves de agentes, especificações arquiteturais) permanecem no backlog como candidatos para próximas releases.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-BCR-01 | Remover `codex-runtime-stage-gap-v1` de `backlog/candidates.md` (stale) | `ac8bc9e` |
| T-BCR-02 | Estender `dadaia-workspace-dev-guardrail.md` com seção `## 6. DEV Workspace Self-Reference` | `d00c892` |
| T-BCR-03 | Criar `data-architect.md` como 21º agente universal | `d0d74c4` |
| T-BCR-04 | Corrigir 4 bugs em `dadaia context deactivate` | `3c0c1aa` |
| T-BCR-05 | Adicionar `[warn] git-dirty` ao `FileSystemPublicAssetManager.doctor()` | `f35a49e` |
| T-BCR-06 | Implementar infra de bug reporting: CLI exception handler + doctor persistence | `fac0a53` |
| T-BCR-07 | Integrar leitura de `reported.json` em `dadaia specs` ao criar/abrir release | `9f235cf` |
| T-BCR-08 | Testes de regressão para todos os FRs (suite completa + smoke test de upstream tracking) | `387da34`, `154b136` |
| T-BCR-09 | Propagação completa (`dadaia public stage && install --force && doctor`) + validação final | `4932129` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Doctor all `[ok]` pós-propagação | `dadaia public doctor` | Saída com zero `[drift]`/`[missing]` — ver seção de saída abaixo |
| Pytest sem novas regressões | `poetry run pytest tests/ -q` | 1878 passed, 19 pre-existing failures, 0 new — ver análise de falhas |
| Guardrail seção 6 presente | `grep "DEV Workspace Self-Reference" .claude/rules/dadaia-workspace-dev-guardrail.md` | Seção com 4 invariantes presentes |
| data-architect projetado | `dadaia public doctor \| grep data-architect` | `[ok] stage:agents/data-architect.md`, `[ok] claude:agents/data-architect.md`, etc. |
| Bug reporter write entry | `poetry run pytest tests/unit/cli/test_bug_reporter.py -q` | 11 passed |
| Specs bug integration | `poetry run pytest tests/unit/cli/test_specs_bug_integration.py -q` | 14 passed |
| Deactivate bug fixes | `poetry run pytest tests/unit/infrastructure/test_git_subprocess.py -q` | 7 passed |
| git-dirty doctor check | `poetry run pytest tests/unit/infrastructure/test_public_assets.py::TestDoctorGitDirtyCheck -q` | 5 passed |
| Upstream tracking smoke test | `poetry run pytest tests/integration/test_cli_context.py::test_push_uses_set_upstream_when_no_tracking` | 1 passed |

```
dadaia public doctor output (truncated to last non-ok lines):
[unsupported] opencode:hooks
[partial] opencode:workflows/audit-cycle.workflow.md (parallel_group sequentially)
[not-applicable] codex:workflows/audit-cycle.workflow.md (no workflow runtime)
# All other entries: [ok]
```

## Drifts

### test-suite-pre-existing-failures

**Description:** A suite pytest tinha 19 falhas pré-existentes que não foram introduzidas por esta release. Incluem: `EXPECTED_SKILLS` stale (skills removidas em releases anteriores); SHA mismatch em `test_all_projected_pairs_share_single_sha256` (CLAUDE.md é escrito como stub, não como cópia do source); model mapping `claude-sonnet-4-5` sem entry em Codex mapping (fixture de teste usa modelo antigo); incompatibilidade de schema handoff v1.0 vs v1.1; workflow stage ordering em orchestration pipeline. Adicionalmente, `test_r3_new_personas_have_expected_models`, `test_minimal_valid_handoff_returns_empty`, `test_full_valid_handoff_returns_empty` já eram pre-existing antes desta release.

**Resolution:** Corrigidas apenas as falhas causadas diretamente por T-BCR-03 (`EXPECTED_AGENTS` não incluía `data-architect` — fix: `154b136`). As 19 restantes são trade-off aceito: corrigir todas exigiria um escopo maior do que Tier A autoriza. Registradas para próxima rodada de planning.

**Memory updates:** Nenhuma — falhas pre-existing não alteram a arquitetura documentada.

### context-gate-cross-repo-fix

**Description:** SDD spec-gate lê `primary_context.json` do contexto PRIMÁRIO para determinar a fase ativa, não o contexto do arquivo que está sendo escrito. Quando o primary context era `dd-chain-explorer` (fase=TASKS), qualquer tentativa de escrever em `specs/memory/*.html` do dadaia-workspace (fase=CLOSURE) era bloqueada. Isso impediu a atualização de `memory/product/public-asset-distribution.html` no momento correto.

**Resolution:** Memory HTML update foi documentada como bloqueada no CLOSURE.md e o backlog recebeu a candidata `context-gate-cross-repo-fix-v1`. A seção de "Memory updates" abaixo reflete o estado real.

**Memory updates:** Nenhum arquivo de memória foi atualizado nesta release (gate bloqueou durante os tentativas anteriores).

## Memory updates

- `specs/memory/product/index.html` — não atualizado: gate bloqueado por cross-context issue (ver drift acima). Nota para próxima release: adicionar `data-architect` ao catálogo de agentes e `bug-reporter` à lista de features de infra.
- `specs/memory/architecture.html` — não atualizado: mesma razão. Nenhuma mudança arquitetural estrutural nesta release que requeira update urgente.
- `specs/memory/tech-stack.html` — não atualizado: sem mudança de dependências ou runtime stack.

## Backlog returns

- `backlog/candidates.md` ← `context-gate-cross-repo-fix-v1` — gate SDD lê primary_context.json para determinar fase, não o contexto do arquivo sendo escrito; cross-context writes falham quando primary context não é o dadaia-workspace (owner: software-engineer-python)
- `backlog/candidates.md` ← Tier B items permanecem: `agents-md-hierarchical-v1`, `data-pipeline-cycle-workflow-v1`, `dashboard-publication-workflow-v1`, `ai-entity-refinement-workflow-v1`, `ai-engineer-recursive-bootstrap-v1`, `agent-monitoring-*`, `reports-*`, `panel-workflow-run-dispatcher`, `hotfix-release-workflow`, `vintage-bucket-doc`, `release-pipeline`, `multi-bot-context-isolation`, `security`.

## Archive decision

**MOVE** — release directory será movida para `specs/_archive/releases/backlog-consolidation-r1-v1/` via `git mv`. ACTIVE.md será atualizado para `release: none`.
