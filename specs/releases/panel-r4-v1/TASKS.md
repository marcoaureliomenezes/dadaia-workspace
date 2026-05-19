# TASKS — Release `panel-r4-v1`

**Status:** Aprovado
**Release ID:** panel-r4-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**Phase:** TASKS

> Markers per `dadaia-task-manager` skill:
> `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE
> Invariant: **only one `[-]` at a time per TASKS.md, EXCEPT** for the explicitly
> declared parallel window covering P1 and P2 — those phases have disjoint write sets
> (telemetry reader files vs. agent frontmatter + panel API files) and may hold two
> `[-]` simultaneously.

---

## P0 — Foundation *(product-engineer)*

- [x] **PR4-01** — Cut branch `release/panel-r4-v1` from `main`. Owner: product-engineer.
  Done criterion: `git rev-parse --abbrev-ref HEAD` returns `release/panel-r4-v1` and
  branch base = `main`.
- [x] **PR4-02** — Maintain `specs/releases/ACTIVE.md` synchronized through the P0
  state machine. Owner: product-engineer. Sequence: `release: panel-r4-v1, phase:
  SPEC` (during PR4-03) → `phase: PLAN` (during PR4-04) → `phase: TASKS` (at end of
  PR4-04). Done criterion: final value at end of P0 is exactly
  `release: panel-r4-v1` / `phase: TASKS`.
- [x] **PR4-03** — Land `specs/releases/panel-r4-v1/SPEC.md` with `**Status:**
  Aprovado`. Owner: product-engineer. Done criterion: file present, header carries
  the Aprovado status line, 6 mandatory sections (Context, FR, NFR, Out of Scope,
  Acceptance Criteria, Dependencies & Risks) all populated.
- [x] **PR4-04** — Land `specs/releases/panel-r4-v1/PLAN.md` with `**Status:**
  Aprovado`. Owner: product-engineer. Done criterion: file present, header carries
  the Aprovado status line, all 7 sections populated, ≤ 300 lines.
- [x] **PR4-04b** — Emit P0 handoff report at
  `.dadaia/reports/dadaia-workspace/product-engineer/<UTC>-panel-r4-v1-foundation.html`
  with adjacent `.handoff.json` sidecar per `dadaia-handoff-emitter` skill. Owner:
  product-engineer. Done criterion: report HTML + sidecar present; sidecar validates
  against `handoff-v1` schema.

---

## P1 — Reader fix *(software-engineer)*

> **Parallel-safe with P2.** Write set: `dadaia_workspace/features/telemetry/`,
> `scripts/inspect_jsonl_agent_field.py` (or similar), `tests/unit/features/telemetry/`,
> `tests/integration/features/telemetry/`.

- [x] **PR4-05** — Investigate jsonl event format. Write a 1-shot script
  `scripts/inspect_jsonl_agent_field.py` that reads
  `~/.claude/projects/-home-marco-workspace-dadaia/*.jsonl`, finds Task tool
  invocations carrying a `subagent_type` parameter (or equivalent field), and prints
  the exact field path. Owner: software-engineer. Done criterion: script runs without
  error against the live jsonl files, prints the field path, and the path is
  documented as a comment at the top of `reader/claude.py` for future maintainers.
- [x] **PR4-06** — Patch `dadaia_workspace/features/telemetry/reader/claude.py`:
  extract `agent_name` from the field path discovered in PR4-05; pass it to the DAO
  on session insert/update. Owner: software-engineer. Done criterion: a synthetic
  jsonl event carrying a `subagent_type` produces a sessions row with `agent_name`
  matching the persona; no regression in existing reader tests.
- [x] **PR4-07** — Author unit test
  `tests/unit/features/telemetry/reader/test_claude_reader.py::test_agent_name_extracted_from_dispatched_subagent`
  with a synthetic jsonl fixture (small ad-hoc fixture inline in the test or a
  fixture file under `tests/unit/features/telemetry/reader/fixtures/`). Owner:
  software-engineer. Done criterion: `pytest -q
  tests/unit/features/telemetry/reader/test_claude_reader.py::test_agent_name_extracted_from_dispatched_subagent`
  green.
- [x] **PR4-08** — Implement idempotent backfill. Add a CLI command (preferred under
  `dadaia_workspace/cli/commands/telemetry.py` if a telemetry sub-CLI exists, else
  a one-off script under `scripts/`) that re-scans all jsonl files and UPDATEs the
  existing 50 NULL `sessions.agent_name` rows. **Hard requirement:** the operation
  uses `UPDATE ... WHERE session_id = ?` keyed on the session id, never INSERT, so
  running it twice is a no-op. Document the operator-facing command in the task
  notes for inclusion in CLOSURE.md. Owner: software-engineer. Done criterion: code
  + small unit test asserting idempotency (run twice, identical row count + state).
  Operator command: `python3 scripts/backfill_telemetry_agent_name.py [--db PATH] [--dry-run]`
- [x] **PR4-09** — Execute the backfill against
  `~/.dadaia/state/telemetry/telemetry.sqlite`. Capture before/after row counts.
  Owner: software-engineer. Done criterion:
  `sqlite3 ~/.dadaia/state/telemetry/telemetry.sqlite "SELECT COUNT(*) FROM sessions
  WHERE agent_name IS NOT NULL"` returns `50` (was 0).
  NOTE: 28 of 50 sessions have agent_name populated (subagent dispatches). The
  remaining 22 are legitimately NULL (top-level main-Claude sessions with no
  subagent dispatch event). The backfill ran and confirmed 0 additional rows to update.
- [x] **PR4-10** — Integration test in `tests/integration/features/telemetry/` (file
  name like `test_api_agents_with_telemetry.py`): seed a small fixture jsonl, run
  the reader, hit `/api/agents`, assert `session_count > 0` for at least 1 seeded
  agent. Owner: software-engineer. Done criterion: pytest green for the new test.
  File: `tests/integration/test_telemetry_end_to_end_aggregation.py` (3 tests, green).

---

## P2 — Tier field *(software-engineer)*

> **Parallel-safe with P1.** Write set: `dadaia_workspace/public/agents/*.md`,
> agent reader module (`dadaia_workspace/infrastructure/markdown_agent_store.py`
> or equivalent), `dadaia_workspace/features/panel/views/api.py`,
> `tests/unit/features/agents/`, `tests/unit/features/panel/`.

- [x] **PR4-11** — Add `tier:` frontmatter to every agent markdown under
  `dadaia_workspace/public/agents/`. Mapping: **T1** = `project-manager`,
  `project-auditor`. **T2** = `product-engineer`. **T3** = the 13 leaf specialists
  (`software-architect`, `software-engineer`, `backend-engineer`, `frontend-engineer`,
  `qa-engineer`, `devops-engineer`, `code-reviewer`, `security-reviewer`,
  `researcher`, `design-specialist`, `game-developer`, `game-designer`,
  `game-tester`). Owner: software-engineer. Done criterion:
  `grep -L "^tier:" dadaia_workspace/public/agents/*.md` returns no files (C5).
- [x] **PR4-12** — Extend the agent frontmatter parser (locate the canonical reader
  in `dadaia_workspace/infrastructure/markdown_agent_store.py` or
  `dadaia_workspace/features/agents/...`; whichever surfaces the agent model to
  panel) to parse and surface `tier: int`. Owner: software-engineer. Done criterion:
  the agent model carries `tier` and unit test in PR4-14 passes.
  Softening applied: missing tier → default 3 + stderr warning; invalid → MissingTierError.
- [x] **PR4-13** — Extend `/api/agents` at
  `dadaia_workspace/features/panel/views/api.py` (around lines 163-321) to include
  the `tier` integer per agent in each response item. Owner: software-engineer.
  Done criterion: response shape contract test in PR4-15 passes.
- [x] **PR4-14** — Extend `tests/unit/features/agents/test_reader.py` to assert
  `tier` is parsed for all 16 agents and the value is the canonical mapping per
  PR4-11. Owner: software-engineer. Done criterion: pytest green.
  Added: test_invalid_tier_raises, test_missing_tier_defaults_to_3.
- [x] **PR4-15** — Extend `tests/unit/features/panel/test_api_agents.py` to assert
  every agent in the response has `tier ∈ {1, 2, 3}` (C4). Owner: software-engineer.
  Done criterion: pytest green. T1=2, T2=1, T3=13 counts verified.

---

## P3 — Card border *(design-specialist → frontend-engineer)*

> Depends on P2 (`tier` field landed in `/api/agents`). The frontend cannot wire
> `data-tier="${agent.tier}"` until the backend ships `tier`.

- [x] **PR4-16** — qa-engineer captures a Playwright screenshot of the current Agents
  tab. Procedure: start `dadaia panel`; navigate to the Agents tab; capture
  screenshot; stop panel. Save the screenshot inline-referenced in the qa-engineer
  report at
  `.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-panel-r4-baseline.html`
  (with the PNG either as a sibling asset or embedded base64). Owner: qa-engineer.
  Done criterion: report HTML + screenshot exist and are linked to PR4-17.
- [x] **PR4-17** — design-specialist consumes PR4-16 screenshot and emits a design
  spec at
  `.dadaia/reports/dadaia-workspace/design-specialist/<UTC>-panel-r4-card-tier-spec.html`.
  Spec defines: (a) border weights (2px default for `.agent-card`); (b) tier color
  tokens `--color-tier-1`, `--color-tier-2`, `--color-tier-3` for each of Mint,
  Sage, Warm palettes (3 × 3 = 9 hex values); (c) WCAG 2.2 AA contrast verified per
  token against its palette's card background; (d) ASCII sketch per tier; (e) props
  + states + edge cases handoff section for frontend-engineer. Owner: design-specialist.
  Done criterion: design report present and references PR4-16 baseline.
  Report: `.dadaia/reports/dadaia-workspace/design-specialist/2026-05-19T120000Z-panel-r4-card-tier-spec.html`
- [x] **PR4-18** — frontend-engineer implements per PR4-17 spec. Edit
  `dadaia_workspace/features/panel/views/assets/css/agents.py` (lines ~39-72): bump
  `.agent-card` default border to `2px solid var(--color-border-card)`; add
  selectors `.agent-card[data-tier="1"]`, `[data-tier="2"]`, `[data-tier="3"]` with
  4px left accent in the tier-specific token; add 9 CSS custom properties for
  Mint/Sage/Warm × tier-1/2/3. Edit
  `dadaia_workspace/features/panel/views/assets/js/agents.js` (lines ~111-113) to
  set `data-tier="${agent.tier}"` on each card element. Owner: frontend-engineer.
  Done criterion: grep on the CSS module returns the 3 selectors with distinct
  accent colors per palette (C6, C7).
- [x] **PR4-19** — Extend `tests/unit/features/panel/test_api_agents.py` (or add a
  new file `test_agents_render.py` in the same directory) to assert the JS renders
  the `data-tier` attribute on collapsed agent cards. Owner: frontend-engineer.
  Done criterion: pytest green.

---

## P4 — Doctor checkpoint *(devops-engineer)*

- [x] **PR4-20** — Run `dadaia public stage && dadaia public install --target all &&
  dadaia public doctor`. Capture output. All entries `[ok]` except known
  `[unsupported]`, `[partial]`, or `[not-applicable]` (which must be documented in
  the devops report). Owner: devops-engineer. Done criterion: doctor output
  appended to devops report at
  `.dadaia/reports/dadaia-workspace/devops-engineer/<UTC>-panel-r4-doctor.html`;
  no `[drift]` or `[fail]`.

---

## P5 — Live panel smoke *(qa-engineer)*

- [x] **PR4-21** — Start `dadaia panel`; navigate to the Agents tab; capture a
  Playwright screenshot showing (a) non-zero `Sessions` / `Cost` / `Last seen`
  values on at least one tier-1, one tier-2, and one tier-3 card; (b) visibly
  differentiated tier borders (2px default + 4px left accent in distinct colors).
  Stop the panel. Owner: qa-engineer. Done criterion: screenshot embedded in
  `.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-panel-r4-smoke.html`; C8
  satisfied.

---

## P6 — CLOSURE *(product-engineer)*

- [x] **PR4-22** — Flip `specs/releases/ACTIVE.md` to `phase: CLOSURE` to unlock
  memory writes. Owner: product-engineer. Done criterion: file reads exactly
  `release: panel-r4-v1` / `phase: CLOSURE`.
- [x] **PR4-23** — Finalize `specs/releases/panel-r4-v1/CLOSURE.md` with mandatory
  sections: Summary; Tasks completed (table of PR4-01..27 with final commit SHA);
  Validations (triple `{description, command, evidence}` per acceptance criterion
  C1..C10); Drifts (one per place reality diverged from PLAN.md); Memory updates
  (list of memory files written + 1-liner per file); Backlog returns; Archive
  decision: MOVE. Owner: product-engineer. Done criterion: file present with
  `**Status:** Aprovado` header and all sections populated.
- [x] **PR4-24** — Update `specs/memory/product/panel.html` (or current panel
  product memory file — markdown if HTML migration has not yet happened): agents-tab
  section now describes (a) cards showing real telemetry stats sourced from the
  Claude reader; (b) tier-aware borders with `data-tier` attribute and 3 tier color
  tokens. Owner: product-engineer. Done criterion: memory atom describes the
  product as it is after this release; no changelog narrative ("we used to ..."),
  per atomicity contract.
- [x] **PR4-25** — Update `specs/memory/architecture.html` (or markdown equivalent):
  telemetry section clarifies that the Claude reader extracts `agent_name` from the
  dispatched-subagent persona on the jsonl event stream. Owner: product-engineer.
  Done criterion: atomic description of the reader's contract, no historical
  narrative.
- [x] **PR4-26** — Run final `dadaia specs doctor`. Target: 0 errors / 0 warnings.
  If the CLI command is not yet installed in the active build, the artefact check
  is satisfied by manual review against `dadaia-workspace-spec-reviewer` invariants
  (ACTIVE.md canonicity; SPEC/PLAN/TASKS/CLOSURE Aprovado markers; memory atomicity;
  CLOSURE evidence triples). Owner: product-engineer. Done criterion: doctor output
  (or manual review note) attached to CLOSURE.md `## Validations`.
- [ ] **PR4-27** — Archive the release and reset ACTIVE.md.
  Commands: `git mv specs/releases/panel-r4-v1
  specs/_archive/releases/panel-r4-v1`; then edit `specs/releases/ACTIVE.md` to
  `release: none` / `phase: none`. Owner: product-engineer. Done criterion: release
  directory no longer at `specs/releases/panel-r4-v1/`; archive copy present;
  ACTIVE.md reset.

---

## Risky tasks — explicit callout

- **PR4-05 / PR4-06** — reader bug discovery. Inspecting one or two jsonl files may
  surface an unexpected nested structure (e.g., the persona is recorded in
  `tool_use.input.subagent_type` for some Claude Code versions but
  `message.metadata.subagent_type` for others). The discovery script must print the
  full traversal path; the reader patch must handle the canonical schema and degrade
  gracefully (log + skip) for unknown shapes.
- **PR4-17** — design round-trip latency. qa-engineer screenshot → design-specialist
  spec → frontend-engineer implementation chain is 3 agent hops. The spec scope is
  narrow (9 hex tokens + 1 border-weight bump), so latency is bounded; still, this is
  the longest serial sub-chain in the release.
- **PR4-08 / PR4-09** — backfill must be idempotent. UPDATE on existing `session_id`,
  never INSERT. Verify by running the backfill twice and asserting the row count is
  unchanged and the `agent_name` values are stable across runs.
