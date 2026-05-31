# Closure: Release — spec-context-session-locks-v1

> **Status:** Aprovado
> **Release ID:** spec-context-session-locks-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-31

## Summary

Esta release entregou o **MAJOR break v2.0.0** do `dadaia-workspace`: a substituição completa
do modelo `ATIVO/INATIVO` + `is_primary` / `primary_context.json` por `ALIVE/DEAD` + session
binding, com três camadas de locking e um gate ciente de sessão. O objetivo central era fechar
a superfície de race condition multi-agente que se tornava crítica à medida que Claude Code,
Codex e OpenCode passaram a correr em paralelo no mesmo workspace.

O núcleo da release é a tríade de mecanismos que fecham as races R-1..R-10 (R-2 eliminado por
design, R-6 deferido): (1) Lock 1 — fcntl workspace-wide ao redor de toda mutação em
`spec_contexts.json`; (2) Lock 2 — fcntl por context ao redor de git clone e rmtree; (3) Lock 3
— arquivo JSON por-release `implementation/<ctx>__<release>.json` com heartbeat TTL de 300 s,
PID liveness check, reclaim auditado e exclusão mútua Impl-XOR-Review para habilitar o
Kanban de Review/Quality do panel. Sessões obtêm identidade via `eval $(dadaia context bind ...)`
que exporta `DADAIA_SESSION_ID`, `DADAIA_CONTEXT` e `DADAIA_MODE`; o hook PreToolUse RULE E
valida identidade e lock ownership antes de permitir qualquer write em produção; o novo hook
PostToolUse `sdd-post-gate.sh` renova `last_seen_at` atomicamente a cada tool call.

A migração é coberta pelo comando `dadaia migrate [--dry-run] [--yes]` (idempotente; consent-gated)
e pelo loud guard que intercepta qualquer `dadaia context` em workspace v1 com exit não-zero.
O guard garante que nenhum consumidor atualize para 2.0.0 silenciosamente sem rodar a migração.
Os velhos verbos `activate`, `deactivate`, `promote` e `use` foram removidos; os novos são
`alive`, `dead`, `bind --mode`, `release` e `heartbeat`.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-10a + T-10c | ALIVE/DEAD model + `JsonContextStore v2` + `SchemaVersionError` + `dadaia migrate` + loud guard | `eb3fd64` |
| T-10b + T-10d | `alive()` / `dead()` service + CLI verbs `context alive/dead/bind --mode/release`; velhos verbos → deprecation stubs | `cfa6fc0` |
| T-11 | Three-layer locking (workspace fcntl / per-context fcntl / Lock 3 impl state machine) + Impl-XOR-Review + audit log `lock-events.jsonl` | `c37fa4b` |
| (fix) R-4/R-5 lock race | Lock 2 serializa todas as operações FS por context; deadlock-safe L1>L2 nesting | `552b790` |
| T-12 | Heartbeat + TTL(300 s) + reclaim auditado + doctor LOCK-1..6 | `b94af52` |
| T-13 (se-python) | RULE E gate + `sdd-post-gate.sh` + R-9 + resolução de release por lock file (completa T-8/ADR D-9) | `481af66` |
| T-13-hooks | PostToolUse hooks (Claude/Codex) + OpenCode inline-heartbeat fallback (OQ-3) | `6e90ef7` |
| T-QA | 79 testes de race/lock/heartbeat/gate/doctor; APPROVED; 2258 passed 0 failed 1 skipped 1 xpassed 89.45% cov | `01ccc03` |
| (infra fix) disk-exhaustion | Tests deixaram de criar venvs reais; conftest backstop + `tmp_path_retention_policy=failed` | `53bcd5a` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full suite verde (randomized) | `poetry run pytest` | 2258 passed, 0 failed, 1 skipped, 1 xpassed, 89.45% coverage |
| Cobertura por módulo crítico (AC-COV) | `coverage report` | `json_context_store` 100%, `service` 91%, `locking` 91%, `doctor` 100% |
| Independência de ordem (AC-RACE-6) | `pytest --randomly-seed=last` | green (pytest-randomly) |
| SDD tree health | `dadaia specs doctor` | exit 0 |
| Runtime projection parity (hooks instalados) | `dadaia public doctor` | exit 0, 0 drift/missing, 222 ok; PostToolUse presente em `.claude/settings.json` + `.codex/hooks.json` |
| QA verdict | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-31T000500Z-spec-context-session-locks-v1-qa.handoff.json` | APPROVED, validated |

## Drifts

### r4-r5-lock-race-found-and-fixed

**Description:** T-11 iniciou com o scaffold de `alive()` e o `AGENTS.md` copy fora do Lock 2 enquanto `doctor.fix()` executava `rmtree` sob Lock 1. Isso causou `~3–10%` de flakiness no AC-T11-7 (copytree do destino deletado a meio do copy).

**Resolution:** Todas as operações FS por context foram movidas para dentro do Lock 2; o aninhamento L1>L2 foi documentado como a única direção segura (deadlock-free). AC-T11-7 0/60, AC-T11-8 0/30 após o fix (commit `552b790`).

**Memory updates:** coberto pela descrição do lock architecture em `specs/memory/product/context-management.html` e `specs/memory/architecture.html`.

### disk-exhaustion-venv-in-tests

**Description:** Aproximadamente 20 fixtures de teste criavam venvs reais com `venv.create(with_pip=True)` em `tmp_path`, esgotando `/tmp` com ENOSPC e levando a uma suite de 24 min.

**Resolution:** Corrigido via conftest backstop + `tmp_path_retention_policy=failed`; suite agora ~5 min. Problema pré-existente não causado por R2; corrigido durante R2 (commit `53bcd5a`).

**Memory updates:** nenhum — infra de teste interna, sem mudança funcional visível.

### oq-3-opencode-hooks-plugin-based

**Description:** O hook JSON injection do OpenCode é baseado em plugin TS (`public/plugins/sdd-gate.ts` via `hooks.tool.execute.before`) — não suporta shell-script post-tool como Claude Code e Codex. A especulação original de OQ-3 (shell script direto em `after_tool_call`) não se confirmou.

**Resolution:** Resolvida per SPEC §14 OQ-3: heartbeat inline no path de allow do `sdd-spec-gate.sh` (sem plugin separado). Não é defeito — é a resolução documentada. `dadaia public doctor` reporta `[unsupported]` para o PostToolUse hook no target OpenCode, o que é esperado.

**Memory updates:** `specs/memory/product/sdd-gate-v3.html` — seção de hook runtime documenta o fallback OpenCode.

### r-6-deferred

**Description:** R-6 (gate lê TASKS.md parcialmente durante rewrite atômica — spurious fail-open) é LOW severity: fail-open é safe (permite a write ao invés de bloquear). Deferred per SPEC §4.

**Resolution:** Adicionado a `specs/backlog/candidates.md` com contexto. Não será corrigido em R2.

**Memory updates:** nenhum — comportamento não mudou.

### preexisting-untracked-drafts

**Description:** A working tree carrega itens não relacionados a R2 não commitados: modificações em `_archive/releases/orchestration-consolidation-v1/`, diretórios draft `design-first-gate-v1/` e `agent-monitoring-r2-v1/`, e os rascunhos do operador `memory-context-enforcement-v1` / `memory-structured-source-v1`. Nenhum desses itens foi tocado por R2.

**Resolution:** Deixados intactos. Flagged para triage em sessão futura. Não afetam a validade do CLOSURE.

**Memory updates:** nenhum.

## Memory updates

- `specs/memory/product/context-management.html` — rewrite completo: ALIVE/DEAD state model; remoção de `is_primary` / `primary_context.json`; novos verbos `alive/dead/bind --mode/release/heartbeat`; session files `.dadaia/sessions/<sess_*>.json`; `dadaia migrate` (v1→v2 + loud guard); three-layer locking summary; heartbeat/TTL/reclaim.
- `specs/memory/product/sdd-gate-v3.html` — RULE E (session identity resolution; path-policy matrix por mode; IMPLEMENTATION resolve release from lock file = T-8 completion); `sdd-post-gate.sh` heartbeat hook; R-9 (spec files read-only when impl lock held); fallback OpenCode inline heartbeat.
- `specs/memory/product/workspace-doctor.html` — LOCK-1..6 invariants do `DoctorService`; renomeação INV-4/INV-5 para ALIVE/DEAD; remoção de INV-1/2/3/6 (eram guards de `is_primary`).
- `specs/memory/architecture.html` — estado runtime atualizado: `primary_context.json` removido; novos paths `.dadaia/sessions/`, `.dadaia/locks/implementation/`, `.dadaia/states/ctx_locks/`, `.dadaia/logs/lock-events.jsonl`; diagrama gate v3 atualizado com RULE E e PostToolUse.
- `specs/memory/product/index.html` — `meta` atualizado para closure: spec-context-session-locks-v1 / 2026-05-31; catálogo sem reordenação de entradas.

## Backlog returns

- `backlog/candidates.md` ← **R-6 retry loop** — gate lê TASKS.md parcialmente durante rewrite atômica; LOW severity; fix = short retry loop no hook; deferido de R2 por §12.2.
- `backlog/ideas.md` ← Multi-host lock aggregation (NFS/distributed filesystem) — fora de escopo de R2; futuro `schema_version: "3"` com revision field.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/spec-context-session-locks-v1/` via `git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.
