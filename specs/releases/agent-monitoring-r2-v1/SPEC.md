# SPEC: agent-monitoring-r2-v1

**Status:** Draft
**Release ID:** agent-monitoring-r2-v1
**Owner:** product-engineer
**Created:** 2026-05-29

---

## Objective

Extend the existing agent-monitoring feature with three complementary capabilities:
(1) a **context-window-fill gauge** that shows per-session utilization of the model's
context window as a percentage, (2) **threshold alerts** for rolling-24h per-agent cost
and for sessions crossing the red context-fill threshold, and (3) a **pricing table
refresh + retroactive recompute** mechanism that corrects stale cost data for new and
updated models.

The primary operator need is visibility: the current Sessions tab already shows
`context_size_tokens` as a raw number, but gives no signal of how close a session is to
exhausting its model's context window. Opus 4-8 sessions with 1M-token contexts are
especially invisible — the raw token count is meaningless without knowing the denominator.

---

## Concurrency note — disjoint from go-open-source

`go-open-source` is currently ACTIVE (phase: IMPLEMENTATION). Its write surface covers
`public/` assets, root docs (LICENSE, CONTRIBUTING.md, AGENTS.md), CI/CD
(`.github/workflows/release.yml`), and `.gitignore`. It does NOT touch
`dadaia_workspace/features/telemetry/`, `dadaia_workspace/features/panel/`, or
`tests/unit/features/telemetry/`.

This release's write surface is entirely within those telemetry/panel paths plus
`dadaia_workspace/cli/commands/`. File-level overlap: **zero**. Both releases can be
planned and implemented in parallel or in either order without merge conflict risk.
Confirmed by researcher discovery report
`.dadaia/reports/dadaia-workspace/researcher/2026-05-29T000000Z-agent-monitoring-r2-discovery.html`
§4 (Concurrency-Safety, §4.3 Collision Analysis verdict: FULLY DISJOINT).

---

## Background — current state of agent-monitoring

Architecture (from discovery report §1):

```
reader (claude.py + codex.py) → store (SQLite WAL) → aggregator (queries.py)
  → service (lazy on-request, 30s cache, fcntl lock) → panel (views/)
```

Data already captured per event: `tokens_input`, `tokens_cache_read`,
`tokens_cache_create`, `tokens_output`, `model`, `cost_micro_usd` (nullable),
`pricing_version`. The aggregator already computes
`context_size_tokens = tokens_input + tokens_cache_create + tokens_cache_read`
from the most recent event in a session. What is missing is the denominator
(`context_window_max`) to derive a utilization percentage, and a correct pricing entry
for `claude-opus-4-8` (currently absent).

Current pricing table (`pricing.py`) lists three models with `effective_from = 2025-01-01`:
`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-3-5`. It is stale: it is missing
`claude-opus-4-8` entirely and assumes 200K context for all models. A gauge using a 200K
denominator for an opus-4-8 session with a 1M-context window would report >100%.

---

## Track 1 — Context-window-fill gauge

### Problem

Sessions in the panel Sessions tab display `context_size_tokens` as a raw number but
provide no signal of proximity to the model's context limit. For a 200K-token model this
is tolerable; for a 1M-token model (claude-opus-4-8 extended-context variant) it is
unreadable. The operator has no way to act on context pressure without computing the
percentage manually.

### Scope

Add a per-session context-window utilization gauge to the panel Sessions tab, with a
per-agent rollup on the Agents tab. Utilization is defined as:

```
utilization_percent = (context_size_tokens / effective_window) * 100
```

where `effective_window` is the per-session resolved denominator (see effective-window
resolution below). The base window for each model is stored in a new date-versioned lookup
table — `CONTEXT_WINDOW_MAX` in `pricing.py` — mirroring the existing `PRICING_TABLE`
pattern (append-only, keyed by model string, each entry carries an `effective_from` date).
For ambiguous models (see discovery note below), `effective_window` may be promoted beyond
the base table value via the high-water-mark heuristic.

**Context window sizes (initial table):**

| Model | Base context window |
|---|---|
| `claude-opus-4-7` | 200 000 tokens |
| `claude-sonnet-4-6` | 200 000 tokens |
| `claude-haiku-3-5` | 200 000 tokens |
| `claude-opus-4-8` | 200 000 tokens (base tier; see effective-window heuristic below) |

> **Discovery note (2026-05-29) — opus-4-8 model string resolution:** A live Claude Code
> session transcript was probed to verify the model string for the 1M-context opus-4-8
> variant. Finding: the JSONL `message.model` field is exactly `claude-opus-4-8` — there
> is NO `1m`, `context-1m`, or any other suffix. The `betas` field is absent. There is no
> context-window field in the message. Verified message keys: `content`, `diagnostics`,
> `id`, `model`, `role`, `stop_details`, `stop_reason`, `stop_sequence`, `type`, `usage`.
>
> Consequence: the 200K-context and 1M-context variants of `claude-opus-4-8` are
> **byte-identical** in the `model` field. A naïve `CONTEXT_WINDOW_MAX[model]` lookup
> cannot distinguish them. A session observed at 379 068 tokens (input + cache_creation +
> cache_read) — which exceeds 200K — proves the session is running under the 1M context
> window; the token count is the only available signal.

**Effective-window resolution (replaces naïve lookup for ambiguous models):**

The gauge denominator is derived via a two-step algorithm:

1. **Base window** = `CONTEXT_WINDOW_MAX[model]` (default `200_000` for `claude-opus-4-8`).
   The table retains both tier values as sentinel constants:
   `CONTEXT_WINDOW_TIERS = [200_000, 1_000_000]` (ordered ascending).
2. **High-water-mark promotion:** if, at any point during a session, the observed
   `context_size_tokens` (= `tokens_input + tokens_cache_create + tokens_cache_read`)
   exceeds the current base tier, the session's `effective_window` is promoted to the
   next tier in `CONTEXT_WINDOW_TIERS` (i.e., 1 000 000). The resolved effective window
   is **persisted per session** (see data path changes below) so the denominator is
   stable and never reverts.
3. The gauge utilization % = `context_size_tokens / effective_window` for that session.
   This value must never exceed 100% for any session/model.

This heuristic is correct by construction: a session that exceeds 200K tokens cannot be
running under a 200K context window; promoting it to 1M is the only coherent interpretation
available from the JSONL data.

**Gauge color thresholds** (default; mirrors operator's existing statusline):

| Utilization % | Color |
|---|---|
| < 60% | Green |
| 60% – 84% | Yellow |
| >= 85% | Red |

**Gauge placement:**
- Sessions tab: per-row gauge widget next to the existing Context (tokens) column.
- Agents tab: per-agent rollup showing the highest utilization among that agent's
  open sessions.

**Data path changes:**

1. `pricing.py` — add `CONTEXT_WINDOW_MAX: dict[str, list[ContextWindowEntry]]`
   (date-versioned, append-only). Add helper `context_window_max_for(model, when)`.
   Add `CONTEXT_WINDOW_TIERS: list[int]` (ordered ascending, e.g. `[200_000, 1_000_000]`)
   used by the effective-window promotion logic.
2. `store/models.py` — add `context_window_max: int | None` (base window from table) and
   `effective_window: int | None` (resolved per-session, updated on promotion) to `Event`
   dataclass.
3. `store/schema.py` — migration 7: `ALTER TABLE events ADD COLUMN context_window_max INTEGER`;
   add `effective_window INTEGER` column (persisted so the denominator is stable per session).
4. `reader/claude.py` — at ingest: populate `Event.context_window_max` from the table;
   apply high-water-mark promotion to set `Event.effective_window` (promote if
   `context_size_tokens > current_base_window`; persist the promoted value).
5. `aggregator/models.py` — add `context_window_utilization_percent: float | None`
   to `SessionRow`; add `max_context_utilization_percent: float | None` to `AgentSummary`.
6. `aggregator/queries.py` — compute utilization using `effective_window` (not raw
   `context_window_max`) in `list_sessions()` and `list_agents()`.
7. `features/panel/views/sessions.py` — render gauge widget with threshold colors.
8. `features/panel/views/agents.py` — render per-agent rollup gauge.
9. `tests/unit/features/telemetry/test_context_window_gauge.py` — NEW unit test.

### Acceptance criteria — Track 1

- **AC-T1-01** — `pricing.py` exports `CONTEXT_WINDOW_MAX` with at least 4 entries
  (the four base-tier models listed above) and `CONTEXT_WINDOW_TIERS = [200_000, 1_000_000]`.
  `context_window_max_for("claude-opus-4-8", date.today())` returns `200_000` (base tier).
- **AC-T1-02** — `Event.context_window_max` is populated for every ingested Claude Code
  event where the model string appears in `CONTEXT_WINDOW_MAX`; it is `None` for unknown
  models and for Codex events.
- **AC-T1-03** — For a synthetic 200K-model session with `context_size_tokens = 120_000`,
  `SessionRow.context_window_utilization_percent` is `60.0` and the gauge renders yellow.
- **AC-T1-04 (critical invariant — model-string ambiguity)** — An `opus-4-8` session
  whose observed `context_size_tokens` exceeds 200 000 (e.g. 379 068, as observed in a
  live session) has its `effective_window` promoted to 1 000 000, and the gauge reports
  approximately 38% (NOT > 100%). This is the correctness invariant the effective-window
  heuristic is designed to enforce.
- **AC-T1-05** — A fresh `opus-4-8` session at `context_size_tokens = 120_000` (below
  200K) resolves to the 200K base tier, `effective_window = 200_000`, and the gauge reads
  60% (yellow). If that same session later receives an event where `context_size_tokens`
  crosses 200 000, the `effective_window` is promoted to 1 000 000 and all subsequent
  gauge readings re-baseline below 100%; the gauge never displays > 100%.
- **AC-T1-06** — The gauge never displays a utilization value > 100% for any
  session/model combination. If `context_size_tokens / effective_window` would produce a
  value > 1.0 due to a data anomaly, the implementer must clamp the stored value to
  `100.0` and log a warning.
- **AC-T1-07** — When `context_window_max` is `None` (Codex or unknown model), the gauge
  widget is absent (no empty bar, no zero %).
- **AC-T1-08** — Schema migration 7 applies cleanly to an existing schema-version-6
  database; existing rows receive `context_window_max = NULL` and `effective_window = NULL`
  (backfill on next ingest cycle via reader).
- **AC-T1-09** — Agents tab renders a rollup gauge for each agent showing the maximum
  utilization across their open sessions; the color threshold logic is the same as the
  Sessions tab gauge.
- **AC-T1-10** — Unit tests cover: correct percentage for 200K model below threshold,
  effective-window promotion when `context_size_tokens` exceeds 200K on an `opus-4-8`
  session (result ~38% for 379K tokens), `None` propagation for unknown model, threshold
  boundary values (59.9% green, 60.0% yellow, 85.0% red), and the > 100% clamp invariant.

---

## Track 2 — Threshold alerts

### Problem

The operator has no proactive signal when per-agent daily cost exceeds a budget, or when
a session crosses the red context-fill threshold (>=85%). Currently these conditions
require manual visual inspection of the panel.

### Scope

Add rolling-24h per-agent cost alerts and context-fill threshold alerts. New components:

**Alert model:**
- `Alert` dataclass: `alert_id`, `agent_name`, `alert_type` (`cost_daily` | `context_fill`),
  `severity` (`warning` | `critical`), `value` (float), `threshold` (float),
  `triggered_at` (str ISO-8601), `session_id` (str | None).
- Stored in a new `alerts` table (schema migration 7 or 8, to be decided by implementer).

**Threshold configuration:**
- Default thresholds stored in `.dadaia/config/telemetry-thresholds.toml` (created on
  first use by `TelemetryService` if absent):
  - `[cost]` `daily_usd_warning = 5.0`, `daily_usd_critical = 20.0`
  - `[context]` `fill_red_pct = 85.0`
- Threshold file is read on each refresh cycle; no daemon, no file-watch.

**Alert generation:**
- `TelemetryService.check_thresholds()` runs at end of each refresh cycle.
- Generates `cost_daily` alerts when rolling-24h cost per agent exceeds configured threshold.
- Generates `context_fill` alerts when a session's `context_window_utilization_percent
  >= fill_red_pct` (requires Track 1 gauge to be implemented first; Track 2 depends on
  Track 1).
- Alerts are deduplicated by `alert_id = sha1(agent_name + alert_type + day_bucket)[:16]`.

**Panel surface:**
- A new `Alerts` section or badge indicator on the Agents tab panel page surfaces active
  alerts. Exact placement (inline badge vs. separate section) is a frontend decision.
- `GET /api/alerts` endpoint (authenticated Bearer) returns current active alerts as JSON.
- Stale alerts (older than 48h) are pruned on each refresh cycle.

**Staleness detection:**
- Existing `pricing_age_days` banner logic is unchanged; alerts complement it.

### Acceptance criteria — Track 2

- **AC-T2-01** — When rolling-24h cost for an agent exceeds `daily_usd_warning`,
  a `cost_daily` / `warning` alert is generated and persisted in the `alerts` table.
- **AC-T2-02** — When `context_window_utilization_percent >= 85.0` for any open session,
  a `context_fill` / `warning` alert is generated referencing that `session_id`.
- **AC-T2-03** — `GET /api/alerts` returns a JSON list of active alerts with fields:
  `alert_id`, `agent_name`, `alert_type`, `severity`, `value`, `threshold`,
  `triggered_at`, `session_id`.
- **AC-T2-04** — Alert deduplication: calling `check_thresholds()` twice in the same
  refresh cycle does not produce duplicate rows in `alerts`.
- **AC-T2-05** — Alerts older than 48h are absent from `GET /api/alerts` response.
- **AC-T2-06** — Default threshold file is created by `TelemetryService` when absent;
  its format validates against a documented schema (inline docstring or TOML comment).
- **AC-T2-07** — Unit tests cover: cost threshold breach, cost below threshold (no alert),
  context-fill threshold breach, deduplication, and 48h pruning.

---

## Track 3 — Pricing table refresh + recompute

### Problem

`pricing.py` is stale: it is missing `claude-opus-4-8` and assumes 200K context for all
models. Historical events for any opus-4-8 session have `cost_micro_usd = NULL` and
`context_window_max = NULL` because the model string is absent from both lookup tables.
When the pricing table is updated (new models added, prices corrected), the existing
backfill in `service.py` only handles rows where `cost_micro_usd IS NULL`. Rows that
were computed with a previous (wrong) price entry are not retroactively corrected.

### Scope

1. **Refresh the pricing table** — add `claude-opus-4-8` with correct input/output/cache
   prices (effective_from = current date). Confirm and preserve existing three model
   entries. There is a single pricing entry for this model string (OQ-07 RESOLVED: the
   200K and 1M-context variants share the same `claude-opus-4-8` model string; no
   `claude-opus-4-8-1m` entry is created). The implementer must look up the current
   Anthropic pricing page for the token cost values before implementing.

2. **Recompute mechanism** — detect when `PRICING_TABLE` has changed since the last
   refresh cycle via a stable digest (`pricing_table_digest()` function in `pricing.py`
   that returns a SHA256 of the sorted serialized table). On digest mismatch, trigger
   a full-recompute pass (`dao.recompute_all_costs()`) that updates
   `cost_micro_usd` and `pricing_version` for all events where the model is now in the
   pricing table (including rows that previously had a non-NULL but potentially stale cost).

3. **Graceful handling of edge cases:**
   - Codex events: `cost_micro_usd` stays `NULL` (Codex tokens are pre-aggregated;
     cache split unavailable).
   - Unknown models: `cost_micro_usd` stays `NULL`.
   - Suspect events (`suspect = 1`): recompute runs but does not clear the suspect flag.

4. **Trigger** — recompute runs in the refresh cycle backfill step (default), reusing the
   existing mechanism. An explicit CLI command `dadaia telemetry recompute-costs` is also
   provided for manual invocation.

### Files changed

- `pricing.py` — add models, add `pricing_table_digest()`, add `CONTEXT_WINDOW_MAX`
  (shared with Track 1).
- `service.py` — detect digest drift in refresh cycle; call `dao.recompute_all_costs()`.
- `store/dao.py` — add `recompute_all_costs()` method.
- `dadaia_workspace/cli/commands/telemetry.py` — add `recompute-costs` subcommand.
- `tests/unit/features/telemetry/test_pricing_recompute.py` — NEW unit test.

### Acceptance criteria — Track 3

- **AC-T3-01** — `pricing.py` contains at least 4 distinct model keys after this release;
  `compute_cost("claude-opus-4-8", input_tok=1000, ...)` returns a non-None value.
- **AC-T3-02** — `pricing_table_digest()` returns a stable hex string; adding a new entry
  changes the digest; removing and re-adding the same entry restores the original digest.
- **AC-T3-03** — When a refresh cycle detects a digest change, `dao.recompute_all_costs()`
  is called exactly once per cycle (not once per event).
- **AC-T3-04** — After recompute, events previously priced with an old `pricing_version`
  that is superseded have their `cost_micro_usd` and `pricing_version` updated to the
  current values.
- **AC-T3-05** — Codex events (`provider = 'codex'`) are unchanged by recompute
  (`cost_micro_usd` remains `NULL`).
- **AC-T3-06** — `dadaia telemetry recompute-costs` exits 0 and prints a summary line
  `Recomputed N events.` (N >= 0).
- **AC-T3-07** — Unit tests cover: digest stability, digest change detection,
  recompute call on change, Codex exemption, and unknown-model exemption.

---

## Architecture deltas

| Component | Change | Notes |
|---|---|---|
| `pricing.py` | Add `CONTEXT_WINDOW_MAX` table + `CONTEXT_WINDOW_TIERS` + `context_window_max_for()` + `pricing_table_digest()` + new model entries | Single file — all pricing/capability constants live here |
| `store/models.py` | Add `Event.context_window_max: int \| None` (base) and `Event.effective_window: int \| None` (promoted, persisted) | Additive fields |
| `store/schema.py` | Migration 7 (or split 7+8): add `events.context_window_max` + `events.effective_window` columns + `alerts` table | Sequential; existing schema v6 DBs auto-migrate |
| `store/dao.py` | Add `recompute_all_costs()` + alert CRUD methods | Additive |
| `aggregator/models.py` | Add `SessionRow.context_window_utilization_percent` + `AgentSummary.max_context_utilization_percent` | Additive DTOs |
| `aggregator/queries.py` | Extend `list_sessions()` + `list_agents()` to compute utilization | Query extension |
| `service.py` | Add `check_thresholds()` call in refresh cycle + digest-drift detection for recompute | Extend refresh pipeline |
| `features/panel/views/sessions.py` | Render gauge widget with color thresholds | UI extension |
| `features/panel/views/agents.py` | Render per-agent rollup gauge + alert badges | UI extension |
| `features/panel/views/api.py` | Add `GET /api/alerts` endpoint | New route |
| `dadaia_workspace/cli/commands/telemetry.py` | Add `recompute-costs` subcommand | New CLI command |

No new Python library dependencies are introduced. All additions use stdlib only (sqlite3,
hashlib, toml is stdlib in Python 3.11+; tomllib in Python 3.11+ or tomli backport — check
constitution lock before using). If `tomllib` is not available under the locked Python
version, fall back to a minimal TOML-like parser or use JSON for threshold configuration.

> Note on TOML: Python 3.11+ includes `tomllib` (stdlib, read-only). Since the
> constitution requires Python 3.12+, `tomllib` is available. Writing the threshold file
> requires a serialization approach (e.g., write as TOML string manually or use
> `tomllib` for reading + a small write helper). Implementer to confirm.

---

## Tech-stack deltas

None. All changes stay within the existing approved stack (Python 3.12+, stdlib sqlite3,
Typer CLI, pytest). `tomllib` (stdlib since 3.11, therefore available in 3.12+) is used
for reading `.dadaia/config/telemetry-thresholds.toml`; this does not require a
`pyproject.toml` dependency addition.

---

## Security / operations deltas

- `GET /api/alerts` follows the same Bearer-token authentication as `/api/agents` and
  `/api/sessions`. No new auth surface.
- `.dadaia/config/telemetry-thresholds.toml` is operator-local config; no secrets or
  credentials are stored there. File is created with standard permissions (no explicit
  chmod needed beyond the directory-level 0o700 already applied to `.dadaia/`).
- Pricing recompute is bounded: it scans only the `events` table, which already exists.
  No new I/O surface.

---

## Memory files affected at closure

- `specs/memory/product/agent-monitoring.html` — update to reflect gauge, alerts,
  recompute mechanism, and corrected pricing table; update runtime state, dependencies,
  and flow sections.
- `specs/memory/product/index.html` — update `agent-monitoring` catalog entry description
  to mention gauge and alerts.
- `specs/memory/architecture.html` — minor update if schema migration number changes
  (currently v6; will become v7 or v8 after this release).
- `specs/memory/tech-stack.html` — no change expected (no new dependencies).

---

## Out of scope

| Item | Reason |
|---|---|
| **Candidate C — multi-host aggregation** | HIGH effort; requires an unresolved architectural decision (HTTP push vs. rsync snapshots vs. central DB). Deserves a dedicated grill-me session and its own release. Deferred. |
| **Candidate B — opencode reader** | Soft-blocked: the opencode.json schema is flagged as pending stability confirmation (go-open-source OQ-01 is resolved for that release's scope, but the opencode reader's full column contract — `agent_role`, `agent_tier` — needs independent validation). Deferred to a follow-up release. |
| **Candidate D — frontmatter-completo** | Orthogonal to the token-visibility theme of this release. No urgency; deferred to backlog. |
| **Gauge on Codex sessions** | Codex reader provides only pre-aggregated `tokens_used` with no model-level context-window mapping; gauge is `None` for Codex events. Accepted limitation. |
| **UI design beyond threshold colors** | Gauge widget visual design (bar shape, animation) is delegated to frontend-engineer + design-specialist within the color-threshold contract above. |
| **Push notifications / webhooks** | Alerts are panel-surface only (pull model). No push, no email, no Telegram integration in this release. |
| **Manual threshold UI** | Thresholds are configured via file only in this release. No in-panel settings UI. |

---

## Open questions

The following questions have operator-approved defaults and do not block SPEC approval.
They are recorded here for transparency; the defaults should be used unless the operator
overrides before PLAN authoring.

| OQ | Question | Default |
|---|---|---|
| OQ-01 | Context-window-max sourcing: hardcoded date-versioned table vs. runtime Anthropic API | **Hardcoded + date-versioned table** (mirrors `PRICING_TABLE` pattern; no API dependency; operator updates on model release) |
| OQ-02 | Gauge color thresholds | **Green < 60%, Yellow 60–84%, Red >= 85%** (mirrors operator's existing statusline) |
| OQ-03 | Pricing-recompute trigger: refresh-cycle backfill vs. explicit CLI command only | **Both** — refresh-cycle runs when digest drifts (automatic); CLI command available for manual invocation |
| OQ-04 | Gauge placement in panel | **Both tabs** — Sessions tab per-row gauge + Agents tab per-agent rollup |
| OQ-05 | TOML vs JSON for threshold config file | **TOML** (tomllib, stdlib Python 3.12+; human-readable comments are valuable for operator) — implementer to confirm write strategy |
| OQ-06 | Schema migration number for alerts table | Implementer decides whether alerts table lands in migration 7 (with context_window_max column) or migration 8 (separate); record in PLAN |
| OQ-07 | Exact model string for opus-4-8 1M-context variant | **RESOLVED (discovery 2026-05-29):** The JSONL `message.model` field is exactly `claude-opus-4-8` for both the 200K and 1M context variants — there is no suffix (`1m`, `context-1m`, etc.) and no `betas` field. The 200K-vs-1M distinction is not available from the model string. The **effective-window heuristic** (high-water-mark promotion when `context_size_tokens > 200_000`) is the authoritative design decision. No separate table entry for `claude-opus-4-8-1m` will be created. |

---

## Dependencies and risks

**Dependencies:**
- Track 2 (alerts) depends on Track 1 (gauge) for context-fill alert generation.
  Track 2 can be partially implemented (cost alerts) before Track 1 is complete, but
  context-fill alerts require Track 1 gauge data to be in the store.
- Track 3 (pricing recompute) is independent of Tracks 1 and 2. It may proceed in
  parallel or first.

**Risks:**
- **Schema migration on live DB** — Migration 7 (ADD COLUMN) is low-risk for SQLite.
  If the operator has a large `events` table, the ALTER TABLE is O(1) for adding a
  nullable column in SQLite (no table rewrite). Recompute is O(events) and may take
  several seconds on large tables. Mitigation: run recompute in background thread or
  bound to a MAX_RECOMPUTE_PER_CYCLE limit.
- **Opus-4-8 model string — RESOLVED (discovery 2026-05-29)** — A live Claude Code
  session was probed. The JSONL `message.model` field is `claude-opus-4-8` with no
  variant suffix for either context tier. The 200K-vs-1M distinction is not present in
  the model string. The effective-window heuristic (see Track 1 Scope) is the adopted
  design: `CONTEXT_WINDOW_MAX["claude-opus-4-8"] = 200_000` is the base entry; promotion
  to 1M occurs at ingest when `context_size_tokens > 200_000`. No separate
  `claude-opus-4-8-1m` entry is needed. This risk is closed; no further verification is
  required by the implementer.
- **Pricing staleness correction** — Recompute overwrites previously computed costs.
  If pricing data was wrong and then corrected, historical cost summaries change. The
  operator is aware and accepts this trade-off (this is the whole point of Track 3).

---

## Suggested implementer surfaces

This section is informational only — PLAN/TASKS will formalize assignments.

| Surface | Suggested owner |
|---|---|
| `pricing.py`, `store/`, `aggregator/`, `service.py`, `dao.py`, `reader/claude.py` | `software-engineer-python` |
| `features/panel/views/sessions.py`, `features/panel/views/agents.py`, `features/panel/views/api.py`, gauge widget HTML/CSS | `frontend-engineer` + `design-specialist` |
| `dadaia_workspace/cli/commands/telemetry.py` | `software-engineer-python` |
| Unit tests (`tests/unit/features/telemetry/`) | `software-engineer-python` (unit); `qa-engineer` (E2E validation) |

---

## Acceptance criteria summary

**Track 1 (gauge):** AC-T1-01 through AC-T1-10 (listed above under Track 1).
Note: AC-T1-04 is the critical invariant for the effective-window heuristic (opus-4-8
379K session → 38% gauge, not > 100%). AC-T1-05 and AC-T1-06 are the never->100% and
promotion re-baseline invariants. These three ACs are non-negotiable for correctness.

**Track 2 (alerts):** AC-T2-01 through AC-T2-07 (listed above under Track 2).

**Track 3 (pricing):** AC-T3-01 through AC-T3-07 (listed above under Track 3).

**Cross-cutting:**
- `dadaia specs doctor` exits 0 after all changes.
- `pytest tests/unit/features/telemetry/` passes with all new tests.
- No new Python library dependencies in `pyproject.toml`.
