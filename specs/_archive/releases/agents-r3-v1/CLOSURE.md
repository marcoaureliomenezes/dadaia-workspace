# Closure: Release — agents-r3-v1

> **Status:** Aprovado
> **Release ID:** agents-r3-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-19
> **Phase:** CLOSURE → ARCHIVED (P6, R3-28..30)
> **SPEC:** `specs/releases/agents-r3-v1/SPEC.md` (Aprovado)
> **PLAN:** `specs/releases/agents-r3-v1/PLAN.md` (Aprovado)
> **TASKS:** `specs/releases/agents-r3-v1/TASKS.md` (Aprovado)

## Summary

agents-r3-v1 restructured the agent topology from **16 → 20 agents** in a single
coherent release. The over-generic `software-engineer` persona was retired (archived
under `specs/_archive/legacy-agents/2026-05-19T174108Z/`) and replaced by two focused
specialists: `software-engineer-python` (Python lib, scripts, pytest, FastAPI/Flask,
Docker, AWS Lambda) and `software-engineer-node` (Node 20 LTS+, TypeScript/JavaScript
server-side, security-conscious, no browser surface).

Three brand-new specialist domains landed: `data-engineer` (SQL+NoSQL, Spark/Airflow/
Kafka, Databricks DABs/Delta Tables/notebooks; primary scope `dd-chain-explorer`),
`data-analyst` (BI specialist consuming Databricks Genie + Dashboards via DABs, with
Playwright dashboard evaluation; pairs with `design-specialist` for visual polish), and
`ai-engineer` (exclusive owner of the lib's AI-entity markdown surface — `public/skills`,
`rules`, `workflows`, `commands`, `agents`, `hooks`; opus-tier model for meta-analysis of
prompt efficiency, cost, and persona authoring depth).

Topology rewires followed: `project-manager` and `project-auditor` dispatch/evidence
lists learned the 5 new leaf names; the Decision Authority Matrix in
`project-orchestration/SKILL.md` gained 5 new rows (Python / Node / Data engineering /
BI / AI entities); the `cross-cutting-feature` and `hotfix-release` workflows were
rewired off bare `software-engineer` references; test fixtures (`test_reader.py`,
`test_api_agents.py`, path-scope gate tests) were updated for the 20-agent topology;
the canonical `data/AGENTS.md` was rewritten to a 20-agent inventory under the ≤280-line
+ forbidden-strings invariants from agents-r2-v1; `scripts/check_agent_topology.py` was
authored as a 5-invariant drift guard. No new workflows for data/BI/AI flows were
introduced (rewire-only per operator decision Q3); the first recursive
`ai-engineer`-led authoring pass is deferred to a follow-up release per Q4.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| R3-01 | Cut branch `release/agents-r3-v1` from `main` post panel-r5-v1 archive | `3af7a10` |
| R3-02 | `specs/releases/ACTIVE.md` → `release: agents-r3-v1` through SPEC/PLAN/TASKS phases | `800025e` |
| R3-03 | Author SPEC.md as Aprovado | `800025e` |
| R3-04 | Author PLAN.md as Aprovado | `800025e` |
| R3-05 | Author TASKS.md as Aprovado | `800025e` |
| R3-06 | Author `software-engineer-python.md` persona | `0bb8e95` |
| R3-07 | Author `software-engineer-node.md` persona | `feb09da` |
| R3-08 | Author `data-engineer.md` persona | `645d92b` |
| R3-09 | Author `data-analyst.md` persona | `d081e3d` |
| R3-10 | Author `ai-engineer.md` persona (model: claude-opus-4-7) | `729f383` |
| R3-11 | Archive `software-engineer.md` to `_archive/legacy-agents/2026-05-19T174108Z/` | `f3fed30` |
| R3-12 | Update `project-manager.md` dispatch list (5 new leaves) | `26ae89b` |
| R3-13 | Update `project-auditor.md` evidence list (data-engineer + ai-engineer surfaces) | `ba95a36` |
| R3-14 | Replace DAM Python/Node row with 5 new rows (Python / Node / Data / BI / AI) | `4f0a1e6` |
| R3-15 | Audit `cross-cutting-feature.workflow.md` for bare-SE references (route by task scope) | `0f7af3a` |
| R3-16 | Rewire `hotfix-release.workflow.md` (route table for 5 implementer agents) | `45259f7` |
| R3-17 | Update `tests/unit/features/agents/test_reader.py` (count 16 → 20 + 5 new persona shape assertions) | `fc08406` |
| R3-18 | Update `tests/unit/features/panel/test_api_agents.py` (card count 20 + T3=17 tier rollup) | `bf5a05e` |
| R3-19 | Fixture stubs for 5 new personas — NO-OP (tests drive off `_PUBLIC_AGENTS_DIR`; closed with note) | `2bc6cb3` |
| R3-20 | Path-scope gate unit tests for SE-python / SE-node / AI allowlists (24 passed) | `f19c61e` |
| R3-21 | Rewrite `dadaia_workspace/public/data/AGENTS.md` for 20-agent inventory (T1=2/T2=1/T3=17, ≤280 lines) | `9c4ffa0` |
| R3-22 | Author `scripts/check_agent_topology.py` drift guard (5 invariants) | `7b019a5` |
| R3-22-followup | Bare SE prose cleanup across skills/rules/data + 7 leaf personas; auditor names all 17 leaves | `708a33f` |
| R3-23 | `dadaia public stage` + `install --target all` propagation (5 new + 0 stale) | `b8ccee4` |
| R3-24 | Clean stale `software-engineer` projection across `.agents/`/`.claude/`/`.codex/`/`.opencode/` + repo-level sync | `50d189d` |
| R3-25 | `dadaia public doctor` green (all `[ok]`, zero drift) | `b8ccee4` |
| R3-26 | `dadaia specs doctor` pre-CLOSURE green (0 errors / 0 warnings) | `b8ccee4` |
| R3-27 | Full `pytest -q tests/` sweep (1546 passed, 1 pre-existing failure deferred — DRIFT-4) + `spec_write` stage extension | `32ca93f` |
| R3-28 | Author CLOSURE.md with evidence triples (this file) | _this commit_ |
| R3-29 | Update 3 memory atoms (agent-orchestration, architecture, product/index) for 20-agent topology | _R3-29 commit_ |
| R3-30 | Update backlog candidate + archive release + reset ACTIVE.md | _R3-30 commit_ |

## Validations

Each row matches one acceptance criterion from SPEC §3. Evidence is a commit SHA, a
stdout snippet (in inline code), or a path to a report HTML under `.dadaia/reports/`.

| Criterion | Command | Evidence | Status |
|-----------|---------|----------|--------|
| C1 — 20 agents in `public/agents/` | `ls dadaia_workspace/public/agents/*.md \| wc -l` → `20` | `f3fed30` (R3-11 archive commit) | PASS |
| C2 — Frontmatter parse green (20 agents) | `pytest -q tests/unit/features/agents/test_reader.py` | `fc08406` (R3-17) | PASS |
| C3 — Panel API exposes 20 tier-aware agents | `pytest -q tests/unit/features/panel/test_api_agents.py` (T1=2/T2=1/T3=17) | `bf5a05e` (R3-18) | PASS |
| C4 — Path-scope gate honours new allowlists | `pytest -q tests/unit/gate/test_path_scope.py` → 24 passed | `f19c61e` (R3-20) | PASS |
| C5 — DAM has 5 new rows | `grep -cE 'Python implementation\|Node implementation\|Data engineering\|BI / dashboards\|AI entities' dadaia_workspace/public/skills/project-orchestration/SKILL.md` → 5 | `4f0a1e6` (R3-14) | PASS |
| C6 — Zero bare `software-engineer` references | `grep -rnE '\bsoftware-engineer\b' dadaia_workspace/public/{agents,skills,workflows,commands,rules,data}/ \| grep -v 'software-engineer-python\|software-engineer-node\|legacy software-engineer\|legacy \`software-engineer\`'` → only intentional historical mentions remain | `708a33f` (R3-22-followup) | PASS |
| C7 — `data/AGENTS.md` 20 rows + ≤280 lines + clean | `wc -l dadaia_workspace/public/data/AGENTS.md` → 280; forbidden-strings grep exits 1 | `9c4ffa0` (R3-21) | PASS |
| C8 — Topology guard script exits 0 | `.dadaia/.venv/bin/python scripts/check_agent_topology.py` → `AGENT TOPOLOGY OK`, exit 0 | `7b019a5` + `0f8c2b0` (R3-22 + R3-22-followup) | PASS |
| C9 — `dadaia public doctor` + `dadaia specs doctor` green | both commands exit 0; `0 errors / 0 warnings` | `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-19T192945Z-agents-r3-v1-p5-doctor-checkpoint.html` | PASS |
| C10 — Full pytest sweep green (modulo deferred drift) | `.dadaia/.venv/bin/pytest -q tests/` → 1546 passed, 1 pre-existing fail (DRIFT-4) | `.dadaia/reports/dadaia-workspace/devops-engineer/2026-05-19T192945Z-agents-r3-v1-p5-doctor-checkpoint.html` | PASS (with deferred drift) |

## Drifts

For every divergence between PLAN.md expectations and reality during implementation:

### DRIFT-1 — spec-refinement workflow grew a `spec_write` stage post-r5

**Description:** `tests/e2e/features/test_orchestration_pipeline.py::test_full_pipeline_run_to_completion` was failing pre-r3. Root cause: the post-panel-r5 `spec-refinement.workflow.md` adds a `spec_write` stage after `synthesis` (PE leaf invoked by PM after specialists report). The test only advanced through `synthesis`, leaving the run paused at `spec_write`.

**Resolution:** Test was extended in R3-27 to advance through the `spec_write` stage; the test now reaches `RUN_COMPLETED`. Commit `8ef2639` carries the extension.

**Memory updates:** None required. The workflow change was already reflected in `specs/memory/product/agent-orchestration.html` §flow (sequence diagram already shows PM → spec_write → PE).

**Confidence:** HIGH — root cause confirmed via event log inspection.

### DRIFT-2 — 13 stale-count tests outside R3-17/R3-18 scope

**Description:** During the P5 pytest sweep, 13 tests in `tests/integration/test_public_pipeline.py` and `tests/integration/test_public_assets.py` failed against the 20-agent topology because they hardcoded `agents=16` or enumerated the 16 legacy persona names. These were outside the R3-17/R3-18 SPEC declaration (which named only the unit-level reader + panel-API tests).

**Resolution:** All 13 fixed in the P5 commit batch (`32ca93f` — `test(public): R3-27 — fix hardcoded counts for 20-agent topology + workflow/skill drift`). Suite is now green for the 20-agent topology.

**Memory updates:** None required. Test-only drift.

**Recommendation:** Future agent-count-changing releases must include `tests/integration/test_public_pipeline.py` and `tests/integration/test_public_assets.py` in their P4 update list. Returned to backlog as `infra-install-source-repo-target-v1`'s sibling action.

### DRIFT-3 — `design-specialist.md` frontmatter referenced a non-existent skill

**Description:** During R3-28 closure preparation, the `design-specialist.md` frontmatter was found to declare `skills: [frontend-design]`. No corresponding skill directory exists in `dadaia_workspace/public/skills/`. This dangling reference predates r3 and was never caught by any doctor check.

**Resolution:** The `frontend-design` skill reference was removed from `design-specialist.md` frontmatter in the P5 cleanup batch. The skill is documented as a backlog candidate (`codex-design-frontend-projection-pilot-v1` already exists in `candidates.md` line 23 and is the canonical home for restoring this skill).

**Memory updates:** None — `specs/memory/product/agent-orchestration.html` already states 16/20-agent topology with no per-skill enumeration.

**Recommendation (added to backlog):** Extend `scripts/check_agent_topology.py` with an `I6` invariant validating that every `skills:` reference in agent frontmatter resolves to a real skill directory under `dadaia_workspace/public/skills/`. Filed as `agent-topology-guard-i6-skill-link-validation-v1`.

### DRIFT-4 — `dadaia reports validate` exit-code semantics misaligned with test_10

**Description:** `tests/integration/test_cli_reports.py::test_10_workspace_not_initialized_exits_3` expects exit 3 when the workspace is not initialized; the CLI raises `WorkspaceNotInitializedError` which currently propagates to exit 1. This is pre-existing CLI behaviour not introduced by r3, and the test failure was the only red line in the otherwise-green 1546-test sweep.

**Resolution:** Deferred to backlog. Two paths viable: (a) align CLI exit semantics with test expectation (exit 3 for un-init), or (b) update the test to assert exit 1. Filed as `cli-reports-exit-code-alignment-v1`.

**Memory updates:** None.

### DRIFT-5 — `dadaia public install --target all` does not propagate to source repo's own projection

**Description:** During R3-23/R3-24 propagation, it became clear that `dadaia public install --target all` walks consumer-repos under `repos/<slug>/` carrying `.dadaia/agentic/` markers but skips the source repo's own repo-level projections at `repos/dadaia-workspace/.claude/agents/` etc. (the source repo auto-skips via `package_version` to avoid recursive self-installation). The 5 new persona files + the archived `software-engineer.md` deletion were therefore not visible inside the source repo's repo-level `.claude/`/`.codex/`/`.opencode/`/`.agents/` until manually synced.

**Resolution:** Manual sync via `50d189d — chore(install): R3-23/R3-24 — sync repo-level projections to 20-agent topology`. Topology guard `scripts/check_agent_topology.py` and `dadaia public doctor` did not catch this drift because both ignore source-repo projection state by design.

**Memory updates:** None — this is an infrastructure drift, not a product/architecture statement.

**Recommendation (added to backlog):** Future infrastructure release should either (a) add `--target source-repo` so the source repo's projections are explicit install targets, or (b) remove repo-level projections from git tracking inside the source repo (treating them as ephemeral artefacts regenerated on demand). Filed as `infra-install-source-repo-target-v1`.

## Memory updates

Explicit list of memory files written during this CLOSURE phase:

- `specs/memory/product/agent-orchestration.html` — 16 → 20 agent count; Python/Node split rationale paragraph; AI-entity surface authority paragraph; data + BI surface paragraphs; Decision Authority Matrix snapshot gains 5 new domain rows; Tier 3 leaf list updated alphabetically (17 names); reports directory list updated.
- `specs/memory/architecture.html` — agent-topology layer row (line ~46) refreshed from 16 → 20 agents; Tier 3 list updated; runtime-state list updated to mention 20 possible report directories.
- `specs/memory/product/index.html` — Users section Tier 3 list updated to 17 leaf specialists; catalog `agent-orchestration` description refreshed to "20 agents in 3 tiers"; new capability bullets added for data engineering, business intelligence, and AI-entity authoring.
- `specs/memory/tech-stack.html` — no change: r3 did not touch dependencies or approved technologies.

No `<h2>Changelog</h2>`, `<h2>History</h2>`, `<h2>Histórico</h2>`, or `<h2>Versions</h2>` sections introduced (memory atomicity invariant). `dadaia specs doctor` runs `0 errors / 0 warnings` after the final memory edit.

## Backlog returns

Items discovered during implementation or surfaced by drifts above. Filed to `specs/backlog/candidates.md` in R3-30:

- `codex-agent-orchestration-parity-v1` — existing candidate; updated from "16 canonical agents" → "20 canonical agents" with note "post-agents-r3-v1 closure".
- `agent-topology-guard-i6-skill-link-validation-v1` (new) — extend `scripts/check_agent_topology.py` with I6 invariant: every `skills:` reference in agent frontmatter must resolve to a real skill directory under `dadaia_workspace/public/skills/`. Source: DRIFT-3.
- `infra-install-source-repo-target-v1` (new) — fix `dadaia public install` to either include the source repo as an explicit install target or remove vestigial source-repo projections from git tracking. Source: DRIFT-5.
- `cli-reports-exit-code-alignment-v1` (new) — align `dadaia reports validate` exit-code semantics with `test_10_workspace_not_initialized_exits_3` expectation (or update the test). Source: DRIFT-4.
- `data-pipeline-cycle-workflow-v1` (new) — declarative workflow for end-to-end data pipeline construction (SQL/NoSQL ingest → Spark/Airflow → Delta/Iceberg → notebook validation). Owned by `data-engineer`. Deferred per Q3 (rewire-only release).
- `dashboard-publication-workflow-v1` (new) — declarative workflow for dashboard authoring → Databricks Dashboards DAB → Playwright evaluation → `design-specialist` visual review → publication. Owned by `data-analyst`. Deferred per Q3.
- `ai-entity-refinement-workflow-v1` (new) — declarative workflow for `ai-engineer`-led skill/rule/workflow/persona refinement (prompt-efficiency audit → cost analysis → rewrite proposal → operator gate → install). Owned by `ai-engineer`. Deferred per Q3.
- `ai-engineer-recursive-bootstrap-v1` (new) — first real `ai-engineer` dispatch on its own surface (skill audit + persona authoring + prompt-efficiency report for a chosen subset of the AI-entity surface). Deferred per Q4 until the `ai-engineer` persona is battle-tested.

## Archive decision

**MOVE.** The release directory `specs/releases/agents-r3-v1/` will be moved to `specs/_archive/releases/agents-r3-v1/` via `git mv` during R3-30. The shell `git mv` operation is delegated to `project-manager` (or the operator) for execution, since `product-engineer` does not invoke `Bash` for archive moves directly per its tool surface. After the move, `specs/releases/ACTIVE.md` is reset to `release: none / phase: none`.

The git history preserves the full release evolution (29 substantive commits + 30 task-marker commits on `release/agents-r3-v1`); the archive directory is the human-browsable snapshot.

---

**Status:** Aprovado
