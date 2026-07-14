# TASKS: v0.2.3 - Four-workflow consolidation

**Status:** Aprovado

- [x] **T01 - Consolidate the governed workflow and CLI surface.** Reduce the
  catalog to four workflows; merge research/bug intake, implementation/reviews,
  and closure responsibilities; remove deprecated execution verbs and update
  fragments/personas/policy. **Write set:** `dadaia_workspace/features/lifecycle/**`,
  `dadaia_workspace/cli/commands/lifecycle.py`, `dadaia_workspace/container.py`,
  `dadaia_workspace/public/lifecycle_fragments/**`, `dadaia_workspace/public/data/AGENTS.md`,
  `tests/**`.
- [x] **T02 - Simplify and harden workflow handoffs.** Enforce one immutable
  payload per attempted model step, exact edge consumption, bounded retries, and
  coherent terminal retention. **Write set:** lifecycle handoff models, schemas,
  services, doctors, retention, and focused tests.
- [x] **T03 - Align panel, public assets, and memory to four workflows.** Remove
  stale workflow cards/docs and update projections plus product memory. **Write
  set:** panel workflow views/assets, public workflow assets, memory atoms, tests.
- [x] **T04 - Add the phantom Games tab.** Implement playable Snake and Tetris
  with isolated state and responsive panel integration. **Write set:** panel
  views/assets/routes and focused tests.
- [x] **T05 - Run four Codex/PI phantom release journeys.** Execute backlog
  definition, release definition, implementation plus reviews, and audit from
  the CLI for four disposable releases; fix and restart any failing workflow.
  **Write set:** phantom release/backlog/audit artifacts and workflow bug fixes.
- [x] **T06 - Final verification and closure.** Run full CI, workflow/handoff
  doctors, panel browser checks, disposition all findings, update current memory,
  and close/archive the release. **Write set:** verification evidence, memory,
  `CLOSURE.md`, `ACTIVE.md`.
