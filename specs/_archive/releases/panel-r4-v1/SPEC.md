# SPEC — Release `panel-r4-v1`

**Status:** Aprovado
**Release ID:** panel-r4-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**Phase:** SPEC

---

## 1. Context

The operator inspected the agents tab in `dadaia panel` and reported two distinct
complaints, each backed by direct evidence:

1. **Card visual identity is too weak** — the current `.agent-card` rule uses a 1px
   `#dddddd` border with no tier differentiation, so the catalog reads as a flat list
   instead of an orchestration topology. There is no at-a-glance way to distinguish
   orchestrators from leaf specialists.
2. **Sessions / Cost / Last seen are all zero or "Never"** — quoting the operator:
   *"this is not the reality."*

Disk-level inspection of the live telemetry store at
`~/.dadaia/state/telemetry/telemetry.sqlite` (run 2026-05-19) confirms the second
complaint has a precise, mechanical root cause:

| Table | Row count | Notes |
|-------|-----------|-------|
| `sessions` | **50** | **All 50 rows have `agent_name = NULL`** |
| `events`   | **13,152** | Total cost **$4,870.74 USD**; last event **2026-05-19T04:58Z** (very recent) |

The data IS being ingested. The events table is healthy and current. The bug is that the
**Claude jsonl reader at `dadaia_workspace/features/telemetry/reader/claude.py` never
populates the `sessions.agent_name` column**. Downstream `/api/agents` does a
`tel_by_id[agent_id]` lookup, finds zero matches (because every session row is bucketed
under the single `None` agent), and falls back to `_empty_telemetry_sub()` — which is
the hard-coded zero state the operator sees in the panel.

Once the reader is patched and the existing 50 NULL rows are backfilled from the source
jsonl files, the cards will immediately show real session counts, real costs, and real
"Last seen" timestamps. No UI work is required to enable this — the API path and the
JS render path already consume the data correctly when it is non-NULL.

The UI work in this release is strictly the visual identity fix described in §2 (FR3).

This release is intentionally small, focused, and parallelisable across two engineers.

---

## 2. Functional Requirements (FR)

### FR1 — Reader populates `sessions.agent_name`

The Claude jsonl reader extracts the dispatched-subagent persona from the jsonl event
stream and writes it into the `sessions.agent_name` column at insert/update time.

- **Source path:** the dispatched-subagent persona appears in Claude Code's jsonl event
  stream — most likely on `tool_use` events where `name == "Task"` with a `subagent_type`
  parameter, or on a `user_metadata.subagent` field. Investigation (task PR4-05) confirms
  the exact path before implementation.
- **Fallback strategy:** if the persona is only recorded on the dispatch event (not on
  every subsequent event in the session), the reader assigns the captured `agent_name`
  to every event sharing the same `session_id`.
- **Backfill:** the existing 50 NULL `sessions.agent_name` rows are backfilled in a
  one-time operation that re-scans the source jsonl files. The operation is idempotent
  (running it twice is a no-op) and is documented in CLOSURE.md.
- **Coverage:** `tests/unit/features/telemetry/reader/test_claude_reader.py` adds a case
  `test_agent_name_extracted_from_dispatched_subagent` with a synthetic jsonl fixture
  asserting the reader yields the correct `agent_name` for a dispatched subagent event.

### FR2 — `/api/agents` returns `tier` per agent

Every agent in the `/api/agents` response carries a `tier` integer field with value in
`{1, 2, 3}`.

- **Source of truth:** a new `tier:` frontmatter key on every
  `dadaia_workspace/public/agents/<name>.md` file. Keeping the topology decision in the
  markdown layer means `product-engineer` owns it; the runtime simply parses what the
  spec says.
- **Authoritative mapping** (per `specs/memory/product/agent-orchestration.html`):
  - **T1 (orchestrators):** `project-manager`, `project-auditor`.
  - **T2 (curator):** `product-engineer`.
  - **T3 (leaf specialists):** the 13 others — `software-architect`,
    `software-engineer`, `backend-engineer`, `frontend-engineer`, `qa-engineer`,
    `devops-engineer`, `code-reviewer`, `security-reviewer`, `researcher`,
    `design-specialist`, `game-developer`, `game-designer`, `game-tester`.
- **Runtime path:** the agent markdown reader parses the `tier:` key from frontmatter
  and surfaces it on the agent model. `/api/agents` includes it on each response item.
- **Coverage:** `tests/unit/features/agents/test_reader.py` asserts `tier` is parsed for
  all 16 agents; `tests/unit/features/panel/test_api_agents.py` asserts every agent in
  the response has `tier ∈ {1, 2, 3}`.

### FR3 — Agent card visual identity

The `.agent-card` CSS rule is bumped to a 2px default border, and a 4px left accent in
tier-specific color tokens makes the topology readable at a glance.

- **Default border:** `border: 2px solid var(--color-border-card)` (up from 1px).
- **Tier-aware variants:** each rendered card carries `data-tier="${agent.tier}"`. CSS
  selectors `.agent-card[data-tier="1"]`, `[="2"]`, `[="3"]` set a 4px left accent in
  tier-specific color tokens.
- **Tokens:** three new CSS custom properties `--color-tier-1`, `--color-tier-2`,
  `--color-tier-3` defined for each of the three theme palettes (Mint / Sage / Warm).
  All 9 hex values verified for WCAG 2.2 AA contrast against the card background in
  their respective palette.
- **JS wiring:** the panel render path at
  `dadaia_workspace/features/panel/views/assets/js/agents.js` sets
  `data-tier="${agent.tier}"` on each card element when building the catalog.
- **Coverage:** `tests/unit/features/panel/test_api_agents.py` (or a sibling test file)
  asserts the rendered JS produces the `data-tier` attribute on collapsed cards.

---

## 3. Non-Functional Requirements (NFR)

### NFR1 — Telemetry refresh stays within the existing 30-second cache TTL

The reader fix and backfill operate inside the existing telemetry refresh pipeline. No
new daemon, no new background process, no change to the 30-second cache window that
`/api/agents` already respects.

### NFR2 — Card render budget unchanged

The card-render path remains under 1 frame for the canonical 16-card catalog. Adding a
`data-tier` attribute and three CSS selectors imposes no measurable cost.

### NFR3 — Accessibility — WCAG 2.2 AA contrast in all 3 palettes

All 9 tier color tokens (3 tiers × 3 palettes) meet WCAG 2.2 AA contrast against their
respective card background. The design-specialist verifies and documents the contrast
ratios in the design report consumed by frontend-engineer.

---

## 4. Out of Scope

- **Aggregator rework / subagent cost re-attribution** — currently dispatched-subagent
  costs accrue against the parent session. Re-attribution to the child agent is a
  separate concern, deferred to a future release.
- **Codex parity rebuild** — `codex-agent-orchestration-parity-v1` (per
  `specs/backlog/candidates.md:22`) is a separate release and is not touched here.
- **Dark mode permutations** — existing backlog item, unchanged.
- **Any other backlog item** that is not explicitly listed in §2.

---

## 5. Acceptance Criteria

Each criterion is verifiable by a single command or assertion. CLOSURE.md will reference
the criterion ID in its `## Validations` triples.

- **C1 (FR1)** — `SELECT COUNT(*) FROM sessions WHERE agent_name IS NOT NULL` against
  `~/.dadaia/state/telemetry/telemetry.sqlite` returns `≥ 50` after the backfill.
- **C2 (FR1)** — `pytest -q tests/unit/features/telemetry/reader/test_claude_reader.py::test_agent_name_extracted_from_dispatched_subagent`
  is green.
- **C3 (FR1)** — `/api/agents` returns at least 5 agents with `session_count > 0` after
  the backfill. Captured as either an integration test or an HTTP smoke (curl + jq).
- **C4 (FR2)** — Every agent in the `/api/agents` response carries
  `tier ∈ {1, 2, 3}`. Asserted in
  `tests/unit/features/panel/test_api_agents.py`.
- **C5 (FR2)** —
  `grep -L "^tier:" dadaia_workspace/public/agents/*.md` returns no files (i.e. every
  agent markdown carries a `tier:` frontmatter key).
- **C6 (FR3)** — The `.agent-card` CSS rule has `border: 2px solid ...` (not 1px).
  Verifiable by `grep -E 'border:\s*2px solid' dadaia_workspace/features/panel/views/assets/css/agents.py`.
- **C7 (FR3)** — Selectors `.agent-card[data-tier="1"]`, `[="2"]`, `[="3"]` are present
  in the CSS module with distinct accent colors per palette.
- **C8 (FR3)** — Live panel screenshot (qa-engineer, P5) shows visibly differentiated
  tier borders for at least one agent of each tier. Screenshot embedded in CLOSURE.md
  evidence.
- **C9** — Full `pytest -q tests/` is green (modulo the existing known coverage
  threshold). No new failures introduced by this release.
- **C10** — `dadaia public doctor` is clean; `dadaia specs doctor` reports 0 errors /
  0 warnings. (Note: if `dadaia specs doctor` is not yet installed in the active CLI
  build, this gate is deferred to the release that ships it; the artefact check is
  satisfied by manual review against `dadaia-workspace-spec-reviewer` invariants.)

---

## 6. Dependencies and Risks

### Dependencies

- The Claude jsonl source files at `~/.claude/projects/-home-marco-workspace-dadaia/`
  must be readable by the backfill script. (Verified: they are.)
- The telemetry SQLite schema already has the `sessions.agent_name TEXT` column — the
  bug is purely in the reader, not the schema. (Verified.)

### Risks

- **R1 — jsonl event format brittleness.** The exact field path for the dispatched
  subagent persona is inferred from inspection of one or two jsonl files. If Claude
  Code emits the persona under a different key in older or newer event formats, the
  reader regex may miss it. **Mitigation:** PR4-05 starts with a discovery script that
  prints the field path before implementation, and the unit test in PR4-07 pins the
  contract.
- **R2 — Design round-trip latency.** P3 requires a qa-engineer screenshot →
  design-specialist spec → frontend-engineer implementation chain, which adds two
  agent hops vs. a direct CSS edit. **Mitigation:** the design spec scope is narrow
  (3 tokens × 3 palettes + 1 border-weight bump), so the round trip is small.
- **R3 — Backfill non-idempotency.** If the backfill re-creates rather than updates
  rows, repeated runs could double-count. **Mitigation:** PR4-08 mandates idempotency
  (UPDATE on existing `session_id`, not INSERT); PR4-09 verifies row count is exactly
  50 after the first run and unchanged after a second run.

### Memory atoms affected at closure

- `specs/memory/product/panel.html` — agents-tab section: cards now show real
  telemetry and carry `data-tier`; the 3 tier colors are documented.
- `specs/memory/architecture.html` — telemetry section: the Claude reader extracts
  `agent_name` from the dispatched-subagent persona.

Memory atom names are forward-looking — the workspace memory layer is currently
markdown (`specs/memory/*.md`); migration to HTML may happen as part of this release's
CLOSURE phase if the canonical templates land in time, otherwise it is deferred. The
content updates above apply to whichever format is current at CLOSURE.
