# Closure: Release — agent-monitoring-v1

> **Status:** Aprovado
> **Release ID:** agent-monitoring-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-17
> **Spec:** `specs/releases/agent-monitoring-v1/SPEC.md`
> **Plan:** `specs/releases/agent-monitoring-v1/PLAN.md`
> **Tasks:** `specs/releases/agent-monitoring-v1/TASKS.md`

---

## Summary

Release `agent-monitoring-v1` materializa duas novas superfícies do panel —
**Agents** e **Workflows** — alimentadas por um módulo de telemetria local
(`features/telemetry/`) que consome **apenas arquivos do operador** (Claude Code
jsonl em `~/.claude/projects/` + Codex sqlite). Zero APIs remotas, zero
dependências Node, zero `ccusage`. Panel continua read-only, bind
`127.0.0.1:4999`, e **nunca serve conteúdo bruto de mensagens** (T1 CRITICAL do
devops report endereçado via allowlist gate hardcoded no reader).

A release entrega 4 abas finais (Servers, Memories, Agents, Workflows). O
catálogo visual consome tokens da `dadaia-workspace-brand-identity-v1` quando
essa release tiver pousado (fallback aos tokens atuais quando não — D-AM-22
operator lock).

Cinco entregáveis atômicos consolidados em 22 tasks (T-AM-01..22) executadas em
5 waves paralelizáveis:

1. **A11y prereq** (T-AM-01) — `role=tablist/tab/tabpanel`, keyboard nav
   ArrowLeft/Right/Home/End/Enter/Space nos 3 tabs existentes antes de qualquer
   nova aba (frontend D-08 + Seção 5.1).
2. **Telemetry core** (T-AM-02..09) — package `features/telemetry/` peer de
   `features/panel/`, SQLite com WAL+foreign_keys+`PRAGMA user_version`
   migrações lineares (5 migrações iniciais), DAO repository, allowlist gate
   CRITICAL, Claude jsonl reader incremental (byte-offset checkpoint + inode
   detection), Codex sqlite reader read-only mode com degradação para
   `tokens_used`-aggregated (D-AM-16), workflows reader parseando frontmatter
   YAML stdlib-only de `.claude/skills/*/SKILL.md` + `.agents/skills/*/SKILL.md`.
3. **Pricing module** (T-AM-10) — `features/telemetry/pricing.py` com
   `PRICING_TABLE` versionado por `effective_from` (Claude opus-4-7 / sonnet-4-6
   / haiku-3-5 baseline rows); `compute_cost` retorna micro-USD ou None;
   `pricing_age_days` alimenta banner de staleness na UI.
4. **Aggregator + service** (T-AM-11..12) — queries com cwd→spec_context
   resolvido em query time via `SpecContextService.list_all()` (architect D9),
   bucket "unassigned" para cwd fora dos contextos. TelemetryService DI:
   `refresh()` lazy on-request, cache 30s, lock via `fcntl.flock` em
   `~/.dadaia/state/telemetry/telemetry.lock`, guard `os.getuid() != 0`
   (devops T6), boot em modo "no-telemetry" se `PRAGMA integrity_check` falhar
   (devops T10 → endpoints 503 com mensagem).
5. **Endpoints + frontend + hardening** (T-AM-13..22) — Bearer token via
   `secrets.token_urlsafe(32)` persistido em `~/.dadaia/state/panel.token`
   chmod 600; CSP `default-src 'self'` + nosniff via helper privado
   `_security_headers(content_type)`; 3 novos endpoints (`/api/agents`,
   `/api/agents/{id}/sessions`, `/api/workflows`) com sincronização
   `_NOT_FOUND_BODY` (architect HIGH finding). Views: Agents card-grid com
   breakdown por Spec Context + drill-down lazy de sessões + sessionId
   truncado a 8 chars (devops T9 anti-enumeração); Workflows card-grid com
   chips clicáveis que navegam para Agents com filtro `#agents?filter=<name>`;
   4ª tab Workflows. Hardening: `0o700` para `~/.dadaia/state/telemetry/`,
   `0o600` para SQLite + token; tests de contraste WCAG AA; ad-hoc validation
   log para acceptance.

Janela de telemetria default: **180d raw + agregados perpétuos** com
compactação por janela diária após 30d (D-AM-18); eventos > 180d removidos de
`events` mas mantidos em `events_daily`. **Mark+UI warning** para eventos
suspect (`MAX_TOKEN_COUNT_PER_EVENT = 2_000_000` ou negativos — D-AM-19); UI
renderiza badge `<span class="badge badge-pending">suspect</span>` no card de
agente. **Numbers-only na v1** (D-AM-20) — sem thresholds, sem push, sem
cost-per-day alerts; operador inspeciona visualmente.

22 tasks executadas em 9 waves por 4 specialists:
`frontend-engineer-p1` (T-AM-01), `software-engineer-p2..p7` (T-AM-02..15),
`frontend-engineer-p8` (T-AM-16..18), `software-engineer-p9` (T-AM-19..21),
`product-engineer claude-main` (T-AM-22 acceptance + this CLOSURE).

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-AM-01 | A11y prereq — role=tablist/tabpanel + keyboard nav | `6e88331` |
| T-AM-02 | `features/telemetry/` package skeleton | `9242552` |
| T-AM-03 | `store/schema.py` — 5 migrations + PRAGMA user_version | `9242552` |
| T-AM-04 | `store/dao.py` — repository pattern with dataclasses | `9242552` |
| T-AM-05 | `reader/allowlist.py` — T1 CRITICAL allowlist gate | `f2c2ad9` |
| T-AM-06 | `reader/claude.py` — incremental tail with byte-offset checkpoint | `f2c2ad9` |
| T-AM-07 | `reader/codex.py` — sqlite read-only mode + tokens_used aggregation | `028c388` |
| T-AM-08 | `budget.py` — named constants for read budget | `028c388` |
| T-AM-09 | `reader/workflows.py` — SKILL.md frontmatter parser (stdlib YAML) | `028c388` |
| T-AM-10 | `pricing.py` — versioned PRICING_TABLE + compute_cost | `c926bf8` |
| T-AM-11 | `aggregator/queries.py` — cwd→context query-time lookup | `d119264` |
| T-AM-12 | `service.py` — TelemetryService DI orchestration + lock + uid guard | `d119264` |
| T-AM-13 | `panel/auth.py` — Bearer token with chmod 600 | `e67ce0a` |
| T-AM-14 | `panel/handler.py` — CSP + nosniff via `_security_headers` | `e67ce0a` |
| T-AM-15 | `panel/handler.py` — `/api/agents`, `/api/agents/{id}/sessions`, `/api/workflows` + `_NOT_FOUND_BODY` sync | `e67ce0a` |
| T-AM-16 | `views/agents.py` — card grid + breakdown + drill-down + staleness banner | `541223e` |
| T-AM-17 | `views/workflows.py` — card grid + clickable chips with `#agents?filter=` | `541223e` |
| T-AM-18 | `views/index.py` — 4th nav-tab Workflows + JS hash routing | `541223e` |
| T-AM-19 | Brand tokens audit + contrast assertions | `5255941` |
| T-AM-20 | Hardening — `0o700/0o600` perms + `shred -u` recovery doc | `5255941` |
| T-AM-21 | Boot in no-telemetry mode on SQLite corruption (devops T10) | `5255941` |
| T-AM-22 | Acceptance pass + ad-hoc validation log | `c3cb893` |

---

## Drifts

### Drift #1 — Brand identity ainda não pousou em CLOSURE time

**Description:** SPEC § Visão e D-AM-22 assumem que `dadaia-workspace-brand-identity-v1`
pode pousar antes, simultânea ou depois desta release. Em CLOSURE time
(2026-05-17), `dadaia-workspace-brand-identity-v1` ainda está em
`specs/releases/dadaia-workspace-brand-identity-v1/` com `Status: Em revisão`
(não aprovada). T-AM-19 implementou os tokens (`--color-cost`,
`--color-warning-bg`, `--color-alert`, `--color-accent-secondary`,
`--color-accent` atualizado para `#9cddc8`) com fallback aos valores anteriores
quando brand identity não pousou — release ships either way per D-AM-22.

**Resolution:** PANEL_CSS já contém os novos tokens; quando
`dadaia-workspace-brand-identity-v1` aprovar o CLOSURE, a memory de
`brand-identity.html` documentará o consumo desses tokens pelo panel
(coupling de cronograma zero — release agnóstica de ordem).

**Memory updates:** `brand-identity.html` permanece referência canônica da
paleta; `panel.html` documenta os novos tokens consumidos com fallback
explícito.

### Drift #2 — opencode telemetry deferido para v1.1

**Description:** SPEC D-AM-14 declara opencode telemetry deferido para v1.1.
Architect D13 confirmou que não há schema estável para opencode em 2026-05; v1
cobre apenas Claude Code jsonl + Codex sqlite. Reader factory tem placeholder
para opencode (interface `Reader` + factory dispatch), mas implementação fica
em backlog.

**Resolution:** Documentado em `## Backlog returns` como `agent-monitoring-opencode-v1.1`.
Coupling-clean: quando o reader opencode pousar, basta adicionar entrada no
factory + nova migração SQLite (se necessária).

**Memory updates:** nenhuma (out-of-scope explícito do SPEC).

### Drift #3 — Schema empírico de Claude jsonl divergiu do Architect Phase-2 inicial

**Description:** Architect Phase-2 report assumia `usage` em
`event.message.metadata.usage.*`. SE empirical reconciliation (R1+R2)
identificou que o caminho real é `event.message.usage.*` (sem `metadata`
intermediário); `model` em `event.message.model`; identidade de sub-agente via
evento separado `type=agent-name` (`agentName`), não `subagent_type`. SPEC
D-AM-13 já capturou a correção antes de TASKS aprovar. Schema SQLite
(`PRAGMA user_version = 5`) reflete a forma correta.

**Resolution:** Reader `claude.py` codifica os paths corretos diretamente;
allowlist gate (T-AM-05) bloqueia qualquer outro caminho ao SQLite. Architect
report (`2026-05-17T052932Z-agent-monitoring-architecture.html`) permanece como
referência histórica; a forma canônica vive no SPEC e no reader.

**Memory updates:** documentado em `agent-monitoring.html § Estado runtime tocado`.

### Drift #4 — Pricing reproducibility via denormalização aceita

**Description:** PLAN previa avaliar recompute quando `pricing.py` muda
(release v1 opcional). Decisão final: denormalização em `events.cost_micro_usd`
+ `events.pricing_version` (rótulo de `effective_from`) é a forma canônica;
não há recompute em v1. Preços históricos permanecem reproducíveis por
construção — eventos antigos cite o preço vigente na época. Mudança de
`pricing.py` apenas afeta novos eventos.

**Resolution:** Documentado em SPEC § Tabela de preços último parágrafo.
Backlog: `agent-monitoring-pricing-recompute-v1.1` (opcional, sob demanda).

**Memory updates:** documentado em `agent-monitoring.html § Diferencial`.

---

## Validations

Evidence triples para os 13 critérios de SPEC § Acceptance criteria.

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| 1 | `GET /api/agents` retorna payload válido; 401 sem token | `pytest tests/integration/test_panel_telemetry_endpoints.py::test_agents_endpoint -q` | Commit `e67ce0a`: integration green; payload conforma `AgentSummary` dataclass. |
| 2 | `GET /api/workflows` similar | `pytest tests/integration/test_panel_telemetry_endpoints.py::test_workflows_endpoint -q` | Commit `e67ce0a`: integration green. |
| 3 | Aba Agents — cards com header/metrics/breakdown/drill-down | `pytest tests/unit/features/panel/test_views_agents.py -q` | Commit `541223e`: unit verde para empty list, typical list, `cost_known=false`, staleness banner. |
| 4 | Aba Workflows — cards com chips clicáveis | `pytest tests/unit/features/panel/test_views_workflows.py -q` | Commit `541223e`: unit verde inclusive chip→hash filter. |
| 5 | WCAG 2.1 AA — `role=tablist/tab/tabpanel`, keyboard, contrast ≥4.5:1 | `pytest tests/unit/features/panel/test_views_index.py tests/unit/features/panel/test_panel_css_contrast.py -q` | Commit `6e88331` (a11y prereq) + `5255941` (contrast assertions): todos verdes. |
| 6 | SQLite chmod 600 + parent dir chmod 700 + reader falha em `getuid()==0` | `pytest tests/integration/test_telemetry_permissions.py -q` | Commit `5255941`: integration verifica `os.stat(...).st_mode` para diretório e arquivo. |
| 7 | CSP + nosniff headers presentes nas respostas | `pytest tests/integration/test_panel_handler_headers.py -q` | Commit `e67ce0a`: integration green; helper `_security_headers` produz CSP em HTML e nosniff em JSON. |
| 8 | Allowlist no reader — NENHUM campo proibido em qualquer endpoint | `pytest tests/unit/features/telemetry/test_allowlist.py tests/integration/test_panel_telemetry_endpoints.py::test_no_content_leakage -q` | Commit `f2c2ad9` + `e67ce0a`: testes asseguram ausência de `content`/`text`/`messages`/`snapshot`/`thinking`/`prompt`/`response`. |
| 9 | `pricing.py` — 4 cenários (known/historical/unknown/zero) | `pytest tests/unit/features/telemetry/test_pricing.py -q` | Commit `c926bf8`: 4 parametrized cases verdes. |
| 10 | Schema migration idempotente via `PRAGMA user_version` | `pytest tests/unit/features/telemetry/test_schema.py -q` | Commit `9242552`: in-memory SQLite, apply twice, user_version=5 estável. |
| 11 | Performance: cold ingest < 10s @ 49.7 MB; `/api/agents` < 50ms @ 415k events | Validation log em `T-AM-22` acceptance report | Commit `c3cb893`: ad-hoc validation log captura tempo de cold ingest (real operator workspace) e p95 query. |
| 12 | `dadaia doctor` passa sem erros para esta release | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia doctor` | Pre-CLOSURE baseline green (zero novos erros introduzidos pelas 22 tasks). |
| 13 | Status Em revisão → Aprovado em SPEC.md | inspeção SPEC.md L3 | Status `Aprovado`, `Approved: 2026-05-17`, `Approved-by: operator`. |

---

## Memory updates

- `specs/memory/product/agent-monitoring.html` — **created** (new feature card).
  Documenta a nova capability surface: módulo `features/telemetry/` peer de
  `features/panel/`, SQLite local com WAL em
  `~/.dadaia/state/telemetry/telemetry.sqlite`, schema versionado via
  `PRAGMA user_version`, allowlist gate hardcoded como única porta para SQLite,
  Bearer token em `~/.dadaia/state/panel.token`, endpoints `/api/agents`,
  `/api/agents/{id}/sessions`, `/api/workflows`, abas Agents e Workflows no panel,
  staleness banner pricing, decisões D-AM-01..22 como referência atômica.
- `specs/memory/product/panel.html` — **updated**: catálogo de abas agora é
  Servers / Memories / Agents / Workflows (4 abas, não 3 com placeholder).
  Documenta consumo dos endpoints de telemetria, Bearer token guard, CSP+nosniff
  headers, JS hash routing `#agents?filter=<agent>`.
- `specs/memory/product/index.html` — **updated**: nova entrada `agent-monitoring`
  no catálogo, inserida na posição relevante para o dia-a-dia do operador
  (entre `panel` e features de observabilidade); `Última atualização` reset para
  `2026-05-17 / Closure: agent-monitoring-v1`.
- `specs/memory/architecture.html` — **no change**: nova feature segue layer
  rules existentes (`features/<name>/` peer pattern, DAO em `store/`, reader em
  `reader/`, aggregator em `aggregator/`); zero alteração nas layer-rules.
- `specs/memory/tech-stack.html` — **no change**: zero novas dependências
  externas (stdlib only — `sqlite3`, `secrets`, `fcntl`, `subprocess`, `pathlib`,
  `json`, `dataclasses`, `datetime`); confirmação NFR3.

---

## Backlog returns

Promovido para `## Histórico` em `specs/backlog/candidates.md`:

- `dadaia-workspace-panel-r2-agents → agent-monitoring-v1` (closed 2026-05-17).

Itens descobertos durante implementação que vão para `## Candidatas ativas`:

- `agent-monitoring-opencode-v1.1` — Adicionar reader para opencode quando o
  schema estabilizar (D-AM-14). Owner: software-engineer. Contexto: SPEC
  `agent-monitoring-v1` § Out of scope.
- `agent-monitoring-pricing-recompute-v1.1` — Recompute opcional de
  `cost_micro_usd` quando `pricing.py` muda (Drift #4). Owner: software-engineer.
  Contexto: SPEC `agent-monitoring-v1` § Tabela de preços.
- `agent-monitoring-threshold-alerts-v2` — Threshold alerts e cost-per-day
  notifications (D-AM-20 declarou numbers-only para v1). Owner: product-engineer.
  Contexto: SPEC `agent-monitoring-v1` § Out of scope.
- `agent-monitoring-multi-host-v2` — Agregação cross-host quando o workspace
  rodar em mais de uma máquina (SPEC § Out of scope). Owner: software-architect.
- `agent-monitoring-frontmatter-completo-v2` — Ler frontmatter completo de
  SKILL.md (autores, tags, parâmetros) em vez de só `name`/`description`/`applyTo`.
  Owner: software-engineer.

---

## Archive decision

**MOVE** — directory `specs/releases/agent-monitoring-v1/` é relocado para
`specs/_archive/releases/agent-monitoring-v1/` via `git mv` após este CLOSURE.md,
as atualizações de memory (incluindo criação de `agent-monitoring.html` no
catálogo) pousarem e o backlog ser atualizado. Post-archive, `specs/releases/ACTIVE.md`
é re-apontado para `release: dadaia-workspace-panel-r3-v1 / phase: PLAN` —
continuação da release ativa que originou esta closure como PR3-00 prereq.
