# Spec: Release — agent-monitoring-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** agent-monitoring-v1
> **Phase:** SPEC
> **Owner:** product-engineer
> **Created:** 2026-05-17
> **Source candidate:** `specs/backlog/candidates.md` § Histórico (promovido a partir de `dadaia-workspace-panel-r2-agents`)
> **Pipeline (3-phase):** PE Discovery → 4× Phase-2 specialist reports (architect, frontend, devops, SE) → PE Reconciliation → this SPEC
> **Discovery inputs:**
> - PE Discovery: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T052532Z-agent-monitoring-discovery.html`
> - Architect: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-17T052932Z-agent-monitoring-architecture.html`
> - Frontend: `.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-17T053015Z-agent-monitoring-design.html`
> - Devops: `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-17T053054Z-agent-monitoring-security.html`
> - Software-engineer: `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T053301Z-agent-monitoring-feasibility.html`
> - PE Reconciliation: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T053947Z-agent-monitoring-reconciliation.html`
> **Parallel candidate:** `dadaia-workspace-brand-identity-v1` (consumer of brand tokens; falls back to current panel tokens if not yet landed)

---

## Visão e lema operador

> "Users will use the dadaia-workspace in its own environment.
> The dadaia-workspace panel must be secure. And the workspace resilient."

O dadaia-workspace panel é hoje uma superfície read-only de 3 abas (Servers, Memories,
Agents & Workflows com placeholder). Esta release evolui a aba placeholder em **duas
abas reais e observáveis (Agents e Workflows)**, alimentadas por um novo módulo de
telemetria que consome **apenas arquivos locais do operador** (Claude Code jsonl + Codex
sqlite) — zero APIs remotas, zero dependências Node, zero `ccusage`. O panel continua
read-only, bind `127.0.0.1`, e nunca serve conteúdo bruto de mensagens.

A release entrega 4 abas finais (Servers, Memories, Agents, Workflows), com tokens
visuais consumindo a paleta da `dadaia-workspace-brand-identity-v1` quando essa
release tiver pousado, e fallback aos tokens atuais caso contrário.

---

## Decisões travadas (resumo)

| ID | Tópico | Decisão | Fonte autoritativa |
|----|--------|---------|--------------------|
| D-AM-01 | Reader | Python stdlib only. Zero npm. Zero `ccusage` | Plan + SE |
| D-AM-02 | Bind | `127.0.0.1:4999` mantido | Plan + devops |
| D-AM-03 | Transcripts | NUNCA expostos. Allowlist no reader (não denylist) | Phase-1 + T1 devops |
| D-AM-04 | Brand identity | Spec separada e paralela | Phase-1 lock |
| D-AM-05 | Abas | 4: Servers, Memories, Agents, Workflows | Phase-1 + frontend D-01 |
| D-AM-06 | Auth | Bearer token, `secrets.token_urlsafe(32)`, `~/.dadaia/state/panel.token` chmod 600 | Devops § 3 |
| D-AM-07 | Pricing | Módulo Python `features/telemetry/pricing.py` com `effective_from` versionado | Architect D10 + SE D4 |
| D-AM-08 | Schema migration | `PRAGMA user_version` + migrações lineares Python | Architect + SE D5 |
| D-AM-09 | Workflows source | `.claude/skills/` + `.agents/skills/` (frontmatter `name`+`description`) | Architect D12 |
| D-AM-10 | Módulo top-level | `features/telemetry/` peer de `features/panel/` | Architect D1 |
| D-AM-11 | Ingestão | Lazy on-request + cache 30s. Sem daemon, cron, watcher | Architect D5 |
| D-AM-12 | Retenção | 180d raw + agregados perpétuos (default) | Phase-1 default-2 |
| D-AM-13 | Schema corrigido | `usage` em `event.message.usage.*`; `model` em `event.message.model`; identidade via evento `type=agent-name` (`agentName`); `is_subagent` derivado de `isSidechain` + `slug` | SE empírico (R1+R2 reconciliation) |
| D-AM-14 | opencode | Deferido para v1.1 | Architect D13 |
| D-AM-15 | Persistência | SQLite local com WAL em `~/.dadaia/state/telemetry/telemetry.sqlite` chmod 600 | Architect D4 + devops § 5 |
| D-AM-16 | Codex cost | `tokens_used` agregado → `cost_micro_usd` NULL; UI mostra "custo indisponível" | SE Seção 6 (R9) |
| D-AM-17 | a11y prereq | T-AM-01 corrige `role=tablist`/`role=tabpanel`/keyboard nav antes de tocar novas abas | Frontend D-08 + Seção 5.1 |

### Decisões aprovadas em 2026-05-17 (operator final lock)

As 5 decisões abaixo eram defaults pendentes de aprovação durante Phase-1/Phase-2 e ficaram
travadas como finais com a aprovação geral do operador em 2026-05-17. Substituem qualquer
"default-N pending" residual nos discovery/reconciliation reports.

| ID | Tópico | Decisão final |
|----|--------|---------------|
| D-AM-18 | **Retention** | 180 dias raw + agregados perpétuos. Compactação por janela diária após 30d. Implementação: cron interna lazy-on-request (sem daemon) que ao detectar evento > 30d move-o para tabela `events_daily` (sum-by-day) e remove da `events` após cópia idempotente. Eventos > 180d são apagados de `events` mas mantidos em agregados perpétuos. |
| D-AM-19 | **T7 (forged events)** | Mark + UI warning. Eventos cujos tokens violam bounds (`MAX_TOKEN_COUNT_PER_EVENT = 2_000_000` ou negativos) entram em `events.suspect=1`. UI renderiza badge `<span class="badge badge-pending">suspect</span>` no card de agente quando `agent.suspect_count > 0`. NÃO descartar silenciosamente — operador inspeciona. |
| D-AM-20 | **Alert policy** | Numbers-only na v1. Sem thresholds, sem notificações push, sem cost-per-day alerts. Operador inspeciona visualmente via aba Agents. Threshold alerts ficam deferidos para release sucessora (já listado em Out of scope). |
| D-AM-21 | **Pricing staleness banner** | Exibir banner amarelo (`background: var(--color-warning-bg)`) na aba Agents se qualquer entrada de `pricing.py` usada nos cálculos da janela tem `effective_from > 90 dias atrás` sem nova versão registrada. Fórmula `pricing_age_days = (today - max(effective_from das entradas usadas)).days` é re-checada a cada page load da aba Agents (não cacheada). Mensagem: "Preços com >90 dias sem revisão — custos podem estar defasados." |
| D-AM-22 | **Brand identity cadence** | Paralelo. `dadaia-workspace-brand-identity-v1` pode pousar antes, depois ou simultaneamente a `agent-monitoring-v1`. Esta SPEC usa fallback aos tokens atuais (`--color-accent: #7ec8e3`, demais valores presentes em PANEL_CSS hoje) quando brand identity ainda não pousou. Quando pousar, os tokens são lidos automaticamente do PANEL_CSS atualizado — zero coupling de cronograma. |

---

## Schema SQLite (DDL inline, comentado, corrigido por SE)

```sql
-- ~/.dadaia/state/telemetry/telemetry.sqlite — chmod 600, owner=uid do operador
-- Connection PRAGMAs: journal_mode=WAL, synchronous=NORMAL, foreign_keys=ON
-- Schema versioned via PRAGMA user_version (D-AM-08).

PRAGMA user_version = 5;

-- =========================================================================
-- reader_state — checkpoint por arquivo fonte (jsonl ou sqlite Codex).
-- Idempotência: re-leitura completa é no-op (D7 architect / D1 SE).
-- =========================================================================
CREATE TABLE IF NOT EXISTS reader_state (
    file_path     TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,                -- 'claude_jsonl' | 'codex_sqlite'
    byte_offset   INTEGER NOT NULL DEFAULT 0,   -- jsonl only
    last_mtime    REAL    NOT NULL DEFAULT 0.0,
    last_inode    INTEGER NOT NULL DEFAULT 0,   -- detect file rotation (devops T7)
    error_count   INTEGER NOT NULL DEFAULT 0,
    last_ingest_at TEXT   NOT NULL
);

-- =========================================================================
-- sessions — uma linha por sessionId (Claude Code) ou thread_id (Codex).
-- Identidade do agente: ai_title é label legível; agent_name vem do evento
-- type=agent-name (campo agentName, SE empírico — NÃO 'subagent_type').
-- =========================================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id     TEXT PRIMARY KEY,           -- sessionId or thread_id
    provider       TEXT NOT NULL,              -- 'claude' | 'codex'
    agent_name     TEXT,                       -- from type=agent-name event (or null)
    ai_title       TEXT,                       -- from type=ai-title event
    entrypoint     TEXT,                       -- 'cli' | 'vscode' | 'web' | null
    cwd            TEXT,
    git_branch     TEXT,
    is_sidechain   INTEGER NOT NULL DEFAULT 0, -- 1 if sub-agent (Claude jsonl)
    sub_slug       TEXT,                       -- 'slug' field when isSidechain=1
    first_event_at TEXT NOT NULL,
    last_event_at  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'closed'   -- 'open' | 'closed'
);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_name);
CREATE INDEX IF NOT EXISTS idx_sessions_provider_first ON sessions(provider, first_event_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_cwd ON sessions(cwd);

-- =========================================================================
-- agents — catálogo distinto de agentes observados ("claude (main)",
-- "codex (main)", "software-architect", ...). Nome canônico:
--   - se sessão tem agent_name (do evento type=agent-name) → usa esse valor
--   - se is_sidechain=1 e há sub_slug → usa sub_slug
--   - caso contrário → "<provider> (main)"
-- =========================================================================
CREATE TABLE IF NOT EXISTS agents (
    name           TEXT PRIMARY KEY,
    provider       TEXT NOT NULL,
    is_subagent    INTEGER NOT NULL DEFAULT 0,  -- derived from isSidechain or sub_slug
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL
);

-- =========================================================================
-- events — append-only, uma linha por evento 'assistant' com usage.
-- Localização do usage: event.message.usage.* (SE empírico, R1 reconciliation).
-- Localização do model: event.message.model.
-- Custo pré-calculado denormalizado para SUM() rápido; cost_micro_usd NULL
-- quando modelo desconhecido ou provider=codex sem token split (R9).
-- =========================================================================
CREATE TABLE IF NOT EXISTS events (
    event_id            TEXT PRIMARY KEY,        -- sha1(sessionId||uuid)[:20] — idempotente
    session_id          TEXT NOT NULL,
    agent_name          TEXT NOT NULL,
    model               TEXT NOT NULL,
    occurred_at         TEXT NOT NULL,
    tokens_input        INTEGER NOT NULL DEFAULT 0,
    tokens_cache_read   INTEGER NOT NULL DEFAULT 0,
    tokens_cache_create INTEGER NOT NULL DEFAULT 0,
    tokens_output       INTEGER NOT NULL DEFAULT 0,
    cost_micro_usd      INTEGER,                 -- NULL = unknown model or aggregated codex
    pricing_version     TEXT,                    -- effective_from of pricing row used
    suspect             INTEGER NOT NULL DEFAULT 0,  -- devops T7: bounds-check failed
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (agent_name) REFERENCES agents(name)
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_agent_time ON events(agent_name, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at DESC);

-- =========================================================================
-- workflows — discovered from .claude/skills/ + .agents/skills/ SKILL.md
-- frontmatter (architect D12). Refreshed on same lazy-on-request cycle.
-- =========================================================================
CREATE TABLE IF NOT EXISTS workflows (
    name           TEXT PRIMARY KEY,
    source_path    TEXT NOT NULL,
    description    TEXT,
    apply_to       TEXT,
    discovered_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL
);

-- many-to-many: substring match against known agent names (best effort, v1)
CREATE TABLE IF NOT EXISTS workflow_agents (
    workflow_name  TEXT NOT NULL,
    agent_name     TEXT NOT NULL,
    PRIMARY KEY (workflow_name, agent_name),
    FOREIGN KEY (workflow_name) REFERENCES workflows(name) ON DELETE CASCADE,
    FOREIGN KEY (agent_name)    REFERENCES agents(name)
);

-- =========================================================================
-- INTENTIONALLY ABSENT
-- =========================================================================
-- NO 'contexts' table — Spec Contexts owned by SpecContextService;
-- cwd→context resolved at QUERY time (architect D9), bucket 'unassigned'
-- for cwd not matching any registered context (R16 consensus).
-- NO 'event_content', no 'prompt', no 'response', no 'snapshot' columns.
-- Privacy invariant: panel NEVER serves content (Phase-1 default #5; T1 devops).
```

---

## Contratos de endpoint (do frontend report, com correções)

Todos os endpoints exigem header `Authorization: Bearer <token>`. Sem header válido → 401 sem body.

### GET `/api/agents`

Lista de agentes com métricas agregadas. **Nenhum campo de conteúdo de mensagem.**

```json
{
  "generated_at": "2026-05-17T05:28:00Z",
  "window_days": 180,
  "pricing_age_days": 94,
  "pricing_model_date": "2026-02-12",
  "agents": [
    {
      "agent_id": "software-architect",
      "display_name": "software-architect",
      "providers": ["claude"],
      "dominant_model": "claude-opus-4-7",
      "is_subagent": true,
      "session_count": 24,
      "total_cost_usd": 1.84,
      "cost_known": true,
      "last_activity_at": "2026-05-17T02:11:00Z",
      "token_totals": { "input": 284310, "cache_creation": 44120, "cache_read": 198450, "output": 21380 },
      "context_breakdown": [
        { "context_slug": "dadaia-workspace", "context_name": "dadaia-workspace",
          "session_count": 12, "cost_usd": 0.97, "cost_fraction": 0.527 },
        { "context_slug": null, "context_name": "unassigned",
          "session_count": 5, "cost_usd": 0.33, "cost_fraction": 0.179 }
      ],
      "recent_sessions": [
        { "session_id_prefix": "a1b2c3d4", "date": "2026-05-17", "cost_usd": 0.14,
          "entrypoint": "cli", "git_branch": "main", "context_slug": "dadaia-workspace",
          "token_counts": { "input": 12441, "cache_creation": 0, "cache_read": 8201, "output": 934 } }
      ]
    }
  ]
}
```

**Query params opcionais:** `limit` (int, default 50), `context` (string slug), `days` (int, default 180).

**`cost_known=false`** quando todos os eventos do agente são `provider=codex` sem split (D-AM-16). UI mostra "tokens totais — custo indisponível" sem falhar.

**`session_id_prefix`** = primeiros 8 chars do sessionId (devops T9 — anti-enumeração via screenshot).

### GET `/api/agents/{agent_id}/sessions`

Paginação de sessões. Mesmo shape que `recent_sessions` acima + total.

### GET `/api/workflows`

```json
{
  "generated_at": "2026-05-17T05:28:00Z",
  "source_hint": ".claude/skills/, .agents/skills/",
  "workflows": [
    { "workflow_id": "discovery-pipeline", "display_name": "discovery-pipeline",
      "description": "Orchestrates 4-agent parallel discovery pattern.",
      "source": ".claude/skills/", "agent_ids": ["product-engineer", "software-architect"] }
  ]
}
```

**Sem `/api/transcripts/`, sem `/api/sessions/{id}/content`** — proibidos por D-AM-03.

---

## Auth model (Bearer token, devops § 3)

- Em startup, se `~/.dadaia/state/panel.token` não existe: gerar com `secrets.token_urlsafe(32)`, persistir, `os.chmod(path, 0o600)`.
- Em cada request, validar `Authorization: Bearer <token>` antes do dispatch de rota.
- Sem header válido → `401 Unauthorized` sem body.
- O comando `dadaia panel start` imprime a URL com `?token=<value>` para o primeiro load do navegador; o token migra para session cookie via JS após o primeiro fetch.
- **Threat aceito:** processo rodando como uid do operador pode ler `panel.token` direto. Já tem acesso ao filesystem todo — risco marginal nulo (devops § 3 "what this does NOT protect against").

---

## Tabela de preços (estrutura, SE Seção 4)

Módulo: `dadaia_workspace/features/telemetry/pricing.py`. Stdlib only.

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class ModelPricing:
    """Prices per million tokens (USD/MTok)."""
    input_per_mtok: float
    output_per_mtok: float
    cache_creation_per_mtok: float
    cache_read_per_mtok: float
    effective_from: date

# Versioned table — key: model_id; value: list ordered by effective_from (newest last).
PRICING_TABLE: dict[str, list[ModelPricing]] = {
    "claude-opus-4-7":   [ModelPricing(15.00, 75.00, 18.75, 1.50, date(2025, 1, 1))],
    "claude-sonnet-4-6": [ModelPricing( 3.00, 15.00,  3.75, 0.30, date(2025, 1, 1))],
    "claude-haiku-3-5":  [ModelPricing( 0.80,  4.00,  1.00, 0.08, date(2025, 1, 1))],
    # Unknown models: compute_cost returns None → cost_micro_usd NULL.
}

def compute_cost(usage: dict, model: str, when: date) -> int | None:
    """Returns cost in micro-USD (10^-6 USD) for the event, or None if model unknown."""
```

- **Atualização:** PR adicionando entrada com novo `effective_from` (não substitui a anterior). Eventos históricos continuam usando o preço vigente na época, preservando reproducibilidade.
- **`pricing_age_days`** (na response): `date.today() - max(effective_from das entradas usadas)`. Banner WCAG-compatível na UI quando `> 90`.

---

## Threat matrix resumida (top 5 do devops report)

| # | Threat | Severity | Mitigação |
|---|--------|----------|-----------|
| T1 | **Sensitive content leak via new endpoint** — jsonl tem input verbatim do operador, potencialmente segredos | CRITICAL | **Allowlist no reader**: apenas campos aprovados entram em SQLite e em qualquer response. Unit test asserta ausência de `content`, `text`, `messages`, `snapshot`, `thinking`, `prompt`, `response` em todas as APIs. |
| T2 | **SQLite legível por outro user do SO** | HIGH | `os.chmod(path, 0o600)` imediato após criação. Dir parent `0o700`. Reader recusa criação com permissions abertas. |
| T3 | **Malware local enumera sessionIds e custos** (panel sem auth) | HIGH | **Bearer token** (D-AM-06) + sessionId truncado a 8 chars + `...` em todas as views de lista. |
| T4 | **DoS via jsonl gigante** | HIGH | Read budget: 4 MB/file/ciclo, max 64 KB/linha (skip+log), checkpoint byte-offset, buffer máx 10k eventos/ciclo. Constantes nomeadas em `features/telemetry/budget.py`. |
| T6 | **Reader rodando como root** lê `~/.claude/projects/` de todos os usuários | MEDIUM | Guard `os.getuid() != 0` em `TelemetryService.__init__`; recusa start. |

**Headers de segurança** (T8): CSP `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'` em respostas HTML; `X-Content-Type-Options: nosniff` em respostas JSON. Implementação via helper privado `_security_headers(content_type)` em `handler.py`.

---

## Out of scope (deferido)

- **Multi-host** — release v1 atende apenas instância local; sem agregação entre hosts.
- **Admin API** — sem write endpoints; sem edição de configuração de telemetria via HTTP.
- **Real-time push** — sem SSE, sem WebSocket; UI usa fetch lazy on tab activation (frontend D-05).
- **opencode telemetry** — defer para v1.1 (architect D13).
- **Anthropic Admin API integration** — não está disponível; tabela de preços local é a fonte canônica.
- **Recompute** quando pricing.py muda — denormalização aceita; recompute fica como tarefa v1.1 opcional.
- **Threshold alerts / cost-per-day notifications** — default v1: só números; operador pode pedir em release sucessora.
- **Frontmatter completo de skills** (autores, tags, parâmetros) — v1 lê apenas `name`, `description`, `applyTo`.
- **Edição de pricing via UI ou JSON externo** — manter PR-gated (D-AM-07).
- **Backup automático do SQLite** — operador faz `sqlite3 ... .dump` manual (documentado).
- **Implementação da brand identity** — entregue por `dadaia-workspace-brand-identity-v1`.

---

## Acceptance criteria (high level)

1. Panel responde `GET /api/agents` com payload válido contra o schema acima, com 401 quando sem token.
2. Panel responde `GET /api/workflows` similarmente.
3. Aba **Agents** renderiza cards com header (nome + modelo), métricas (sessões, custo, last activity), breakdown por Spec Context (% + barra), drill-down de sessões recentes (lazy via `/api/agents/{id}/sessions`).
4. Aba **Workflows** renderiza cards descritivos com chips de agentes clicáveis que navegam para Agents com filtro `#agents?filter=<agent>`.
5. WCAG 2.1 AA validado: `role=tablist/tab/tabpanel`, keyboard navigation (Left/Right/Home/End/Enter/Space), contraste ≥ 4.5:1 em texto.
6. SQLite criado com `chmod 600`, parent dir `chmod 700`; reader falha em `getuid()==0`.
7. CSP + nosniff headers presentes nas respostas relevantes.
8. Allowlist no reader: teste asserta que NENHUM campo `content`/`text`/`messages`/`snapshot`/`thinking`/`prompt`/`response` aparece em qualquer endpoint da API.
9. Pricing.py com testes para: modelo conhecido em janela vigente, modelo conhecido em janela histórica, modelo desconhecido (`cost=None`), `usage` todo zero (`cost=0.0`), Codex sem split (cost=None com flag `aggregated=true`).
10. Schema migration via `PRAGMA user_version` aplica as 5 migrações iniciais idempotentemente.
11. Performance: cold ingest < 10s nos 49.7 MB observados (34 sessões); query `/api/agents` < 50ms em 415k eventos projetados em 6 meses.
12. `dadaia doctor` passa sem erros para esta release.
13. Operador transiciona `Status: Em revisão → Aprovado` em SPEC.md.
