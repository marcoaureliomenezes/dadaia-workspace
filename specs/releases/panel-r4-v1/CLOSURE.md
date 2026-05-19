# Closure: Release — panel-r4-v1

> **Status:** Aprovado
> **Release ID:** panel-r4-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-19

---

## Summary

The operator's complaint — *"this is not the reality"* — concretely meant two
defects on the `dadaia panel` Agents tab: (1) `Sessions / Cost / Last seen` were
hard zeros across every card, and (2) all 16 cards rendered with a flat
1px `#dddddd` border and no at-a-glance signal of orchestration tier. Disk-level
inspection of `~/.dadaia/state/telemetry/telemetry.sqlite` pinpointed the root
cause: 50 sessions rows existed with healthy event ingestion (13,152 events,
$4,870.74 cumulative cost) but `sessions.agent_name` was `NULL` for every single
row — so the downstream `tel_by_id[agent_id]` lookup in `/api/agents` always
missed and fell back to the hardcoded zero-state.

**FR1 (reader fix)** patched
`dadaia_workspace/features/telemetry/reader/claude.py` to extract `agent_name`
from `tool_use.input.subagent_type` on dispatched-subagent Task tool
invocations, propagate the persona via a `session_id → agent_name` map to all
subsequent events in the same session, and persist via `UPDATE … WHERE session_id = ?`
on the DAO. A one-shot idempotent backfill at
`scripts/backfill_telemetry_agent_name.py` re-scanned the source jsonl files and
populated **28 of the 50** sessions (the remaining 22 are legitimately NULL — they
are top-level main-Claude sessions with no dispatched subagent event).

**FR2 (tier field)** added `tier:` frontmatter to all 16 public agent markdowns
(T1 orchestrators × 2, T2 curator × 1, T3 leaf specialists × 13) per the
authoritative mapping in `specs/memory/product/agent-orchestration.html`. The
agent reader was extended to parse `tier: int`, with softening: missing → defaults
to 3 with stderr warning; invalid → `MissingTierError`. `/api/agents` now
includes `tier` per agent in every response.

**FR3 (visual identity)** bumped `.agent-card` to a 2px default border with a
4px left accent color-coded by tier (Mint/Sage/Warm palette tokens × 3 tiers = 9
hex values), all verified WCAG 2.2 AA contrast in the design-specialist report.
The frontend wires `data-tier="${agent.tier}"` on each rendered card.

The live panel smoke at the end of P5 confirmed the end-to-end pipeline: cards
visibly show non-zero stats (project-manager 12 sess / $48.71 / today;
product-engineer 1 sess / $91.22 / today; multiple leaf specialists with real
session counts) and visually distinct tier borders (orchestrator T1 accent vs.
curator T2 accent vs. leaf T3 accent). The operator's complaint is resolved.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| PR4-01 | Cut branch `release/panel-r4-v1` from `main` | `2b69b04` |
| PR4-02 | Maintain ACTIVE.md sync through P0 state machine | `cbc55f6` |
| PR4-03 | Land SPEC.md Aprovado | `dd419fe` |
| PR4-04 | Land PLAN.md Aprovado | `5e94976` |
| PR4-04b | Emit P0 foundation handoff report + sidecar | `83496bf` |
| PR4-05 | Investigate jsonl format; discovery script + reader docstring | `1e27a9e` |
| PR4-06 | Patch reader/claude.py to extract `agent_name` from subagent_type | `2918e4c` |
| PR4-07 | Unit test: `test_agent_name_extracted_from_dispatched_subagent` | `2918e4c` |
| PR4-08 | Idempotent backfill script `scripts/backfill_telemetry_agent_name.py` | `002eb74` |
| PR4-09 | Execute backfill against live telemetry.sqlite | `1eff540` |
| PR4-10 | Integration test for end-to-end aggregation pipeline | `03fa734` |
| PR4-11 | Add `tier:` frontmatter to all 16 public agent markdowns | `680134e` |
| PR4-12 | Soften MissingTierError (missing → default 3 + stderr warning) | `c7ff278` |
| PR4-13 | Extend `/api/agents` to include `tier` integer per agent | `b6511d2` |
| PR4-14 | Update tier tests (invalid raises; missing defaults to 3) | `216cab1` |
| PR4-15 | Assert tier ∈ {1,2,3} for all agents in `/api/agents` response | `ac96e25` |
| PR4-16 | qa-engineer baseline screenshot of Agents tab | `39aefc6` |
| PR4-17 | design-specialist tier card spec (9 hex tokens, WCAG verified) | `d74fdd3` |
| PR4-18 | Frontend tier-aware card borders (CSS selectors + 9 tokens) | `583f0d9` |
| PR4-19 | JS wires `data-tier="${agent.tier}"` on each card | `583f0d9` |
| PR4-20 | devops `dadaia public stage/install/doctor` checkpoint | `eda4a79` |
| PR4-21 | qa-engineer live panel smoke screenshot (Agents tab final) | `82f59e5` |
| PR4-22 | Flip ACTIVE.md to phase: CLOSURE | `bcb3480` |
| PR4-23 | Finalize CLOSURE.md | _this commit_ |
| PR4-24 | Update `specs/memory/product/panel.html` (agents-tab + tiers) | _next commit_ |
| PR4-25 | Update `specs/memory/architecture.html` (telemetry reader contract) | _next commit_ |
| PR4-26 | Run final `dadaia specs doctor` 0/0 | _next commit_ |
| PR4-27 | `git mv` to `_archive/releases/` and reset ACTIVE.md | _next commit_ |

---

## Validations

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| V1 | C1 — `sessions.agent_name` non-null count after backfill | `sqlite3 ~/.dadaia/state/telemetry/telemetry.sqlite "SELECT COUNT(*) FROM sessions WHERE agent_name IS NOT NULL"` | `28` of `50` (22 legitimately NULL top-level main-Claude rows; commit `1eff540`) |
| V2 | C2 — Reader unit test green | `pytest -q tests/unit/features/telemetry/reader/test_claude_reader.py` | green at commit `2918e4c` |
| V3 | C3 — `/api/agents` returns ≥5 agents with `session_count > 0` | live panel smoke via Playwright | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-19T071230Z-PR4-21-panel-smoke.html` shows project-manager 12 sess/$48.71/today, product-engineer 1 sess/$91.22/today, and multiple leaf specialists non-zero |
| V4 | C4 — Every agent in `/api/agents` carries `tier ∈ {1,2,3}` | `pytest -q tests/unit/features/panel/test_api_agents.py::TestTierFieldInResponse` | 28 cases green at commit `ac96e25` (T1=2, T2=1, T3=13 counts) |
| V5 | C5 — Every agent markdown carries `tier:` frontmatter | `grep -L "^tier:" dadaia_workspace/public/agents/*.md` | empty stdout at commit `680134e` |
| V6 | C6 — `.agent-card` CSS has 2px default border | `grep -E 'border:\s*2px solid' dadaia_workspace/features/panel/views/assets/css/agents.py` | match at commit `583f0d9` (`border: 2px solid var(--color-border-card, #dddddd)`) |
| V7 | C7 — Selectors `[data-tier="1\|2\|3"]` present in CSS with 9 hex tokens | `grep -c 'agent-card\[data-tier=' dadaia_workspace/features/panel/views/assets/css/agents.py` | 3 selectors + 9 hex tokens (3 palettes × 3 tiers) at commit `583f0d9` per design spec at `.dadaia/reports/dadaia-workspace/design-specialist/2026-05-19T120000Z-panel-r4-card-tier-spec.html` |
| V8 | C8 — Live screenshot shows visibly differentiated tier borders | qa-engineer Playwright capture | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-19T071230Z-PR4-21-agents-tab-final.png` (referenced in PR4-21 report) |
| V9 | C9 — Full pytest sweep no new failures | `pytest -q tests/` | `1348 passed, 2 failed` per PR4-21 smoke report; both failures pre-existing on `main` (`test_install_overwrites_existing_files_with_force`, `test_10_workspace_not_initialized_exits_3`); neither in this release's write set |
| V10 | C10 — `dadaia public doctor` clean + `dadaia specs doctor` 0/0 | `dadaia public doctor` + `dadaia specs doctor` | `dadaia public doctor` 256 [ok] / 0 [drift] / 0 [fail] per devops report at `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-19T070247Z-P4-doctor-checkpoint.html`; `dadaia specs doctor` result appended below at PR4-26 |

---

## Drifts

No new architectural or product drifts were introduced by this release.

The 2 pre-existing pytest failures on `main` are pre-existing drift unrelated
to `panel-r4-v1`'s write set and are tracked separately:

- `test_install_overwrites_existing_files_with_force` (`tests/unit/...`) —
  pre-existing failure on `main`; not touched by this release.
- `test_10_workspace_not_initialized_exits_3` (`tests/unit/...`) —
  pre-existing failure on `main`; not touched by this release.

Both should be triaged in a separate hotfix or release; they are documented
here only to scope V9 evidence honestly.

---

## Memory updates

- `specs/memory/product/panel.html` — agents-tab section updated: cards now
  describe real telemetry (sessions / cost / last-seen) sourced from the Claude
  reader's `agent_name` extraction, each card carries `data-tier="1|2|3"` and a
  tier sub-label (T1 Orchestrator / T2 Curator / T3 Leaf), and borders are 2px
  default + 4px left accent color-coded by tier with 9 tokens defined across the
  three palettes (Mint / Sage / Warm), WCAG 2.2 AA contrast verified.
- `specs/memory/architecture.html` — telemetry section clarifies that the Claude
  jsonl reader extracts `agent_name` from `tool_use.input.subagent_type` in
  dispatched-subagent Task tool invocations and propagates the persona via a
  `session_id → agent_name` map to all subsequent events in the same session;
  one-shot idempotent backfill at `scripts/backfill_telemetry_agent_name.py`
  is documented as the historic-data recovery path.
- `specs/memory/tech-stack.html` — no change: release did not touch dependencies.

---

## Backlog returns

- `backlog/ideas.md` ← **qa-engineer stop-conditions documentation for
  dev-server-registry skill.** The qa-engineer Playwright baseline-screenshot
  dispatch (PR4-16) ended mid-task and the main session captured the final live
  screenshot (PR4-21) directly. The pattern surfaced a gap: qa-engineer
  sub-sessions that boot a `dadaia panel` dev server should have an explicit
  stop-condition contract (max-frames captured, max-elapsed-seconds, idle-after-N
  in `dadaia server list`) so they complete cleanly within their time budget
  instead of leaving the session orphaned. Owner: software-engineer or
  product-engineer (skill author).
- `backlog/ideas.md` ← **panel active-state hover conflict with tier accent.**
  design-specialist surfaced a visual-precedence question during PR4-17: when a
  card is in active/hover state, the tier accent and active-state shift can
  visually compete. The release chose tier accent as primary precedence (always
  visible) and active-state as secondary (subordinate shift). If user testing
  shows the hover is too muted, a follow-up release can rebalance. Owner:
  design-specialist or frontend-engineer.
- `backlog/candidates.md` ← already present: `codex-design-frontend-projection-pilot-v1`.
  The untracked file at `specs/backlog/codex-design-frontend-projection-pilot-v1.md`
  is the draft body of that backlog entry and was authored by a prior session.
  It is preserved as the candidate's draft body for the next planning round and
  will not be moved into this release's archive.

---

## Archive decision

**MOVE** — PR4-27 will `git mv specs/releases/panel-r4-v1
specs/_archive/releases/panel-r4-v1`. After the move, ACTIVE.md will be reset to
`release: none` / `phase: none` so the workspace is ready for the next planning
round.
