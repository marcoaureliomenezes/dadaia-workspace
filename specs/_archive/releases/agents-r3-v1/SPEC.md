# Spec: Release — agents-r3-v1

> **Status:** Aprovado
> **Approved:** 2026-05-19
> **Approved-by:** operator (design pre-approved in dispatch brief + plan
> `/home/marco/.claude/plans/i-inspect-the-agents-glistening-sparrow.md`)
> **Release ID:** agents-r3-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Phase:** SPEC
> **Branch:** `release/agents-r3-v1` (cut from `main` at the panel-r5-v1 archive tip)
> **Predecessor:** `panel-r5-v1` (CLOSED + ARCHIVED) — last release in the `panel-rN-v1`
> series; immediate ancestor in the `agents-rN-v1` series is `agents-r2-v1` (CLOSED).
> **Discovery inputs:**
> - Operator dispatch brief + operator-approved plan
>   `/home/marco/.claude/plans/i-inspect-the-agents-glistening-sparrow.md` (this SPEC
>   quotes the operator's scope verbatim where appropriate).
> - Atomic memory (post panel-r5-v1 CLOSURE):
>   `specs/memory/architecture.html`, `specs/memory/product/index.html`,
>   `specs/memory/product/agent-orchestration.html`, `specs/memory/tech-stack.html`.
> - Constitution: `specs/constitution.md` Pilar 2 (orquestração multi-agente).
> - Source files exercised by this release:
>   - `dadaia_workspace/public/agents/software-engineer.md` (to be retired)
>   - `dadaia_workspace/public/agents/project-manager.md` (dispatch list)
>   - `dadaia_workspace/public/agents/project-auditor.md` (evidence list)
>   - `dadaia_workspace/public/skills/project-orchestration/SKILL.md` (Decision
>     Authority Matrix, lines ~99–117)
>   - `dadaia_workspace/public/workflows/{cross-cutting-feature,hotfix-release}.workflow.md`
>   - `tests/unit/features/agents/test_reader.py`
>   - `tests/unit/features/panel/test_api_agents.py`
>   - `dadaia_workspace/public/data/AGENTS.md`

---

## 1. Objective

The operator's proposal, quoted verbatim from the approved plan §"Context":

> The operator wants the next release to restructure the agent topology — `software-engineer`
> has become too generic, and several specialist domains (data, BI, AI orchestration) are
> missing. Five new leaf specialists land in one coherent release:
>
> 1. **`software-engineer-python`** — Python lib, scripts, pytest, packaging, Docker,
>    AWS Lambda, FastAPI/Flask.
> 2. **`software-engineer-node`** — Node 20 LTS+, TypeScript/JavaScript runtime, npm/npx,
>    server-side only. Pragmatic ("no `is_even` deps"), security-conscious. Stays clear of
>    `frontend-engineer`'s browser surface.
> 3. **`data-engineer`** — SQL + NoSQL, OLTP/OLAP, Spark/Airflow/Kafka, Databricks (DABs,
>    Delta Tables, notebooks, workflows), file/table formats (CSV/AVRO/JSON/Parquet/Delta/
>    Iceberg), distributed systems. Primary scope today: `redacted-slug-explorer`. Available for
>    data-heavy tasks across any project.
> 4. **`data-analyst`** — BI specialist, Databricks Genie + Dashboards via DABs, data viz
>    + storytelling, Playwright dashboard evaluation. Consumes `design-specialist` reviews
>    for dashboard polish (same pattern as `frontend-engineer` ↔ `design-specialist`).
> 5. **`ai-engineer`** — Exclusive owner of all AI-entity markdown files in the lib. Knows
>    context engineering, prompt design, skill/rule/workflow/hook efficiency analysis,
>    claude-code + codex + opencode runtime fundamentals. Generates feedback reports on
>    prompt efficiency, cost vs output. Never touches Python/Node implementation. Tightly
>    coordinated with `software-engineer-python` (and the rest) — owns the persona surface,
>    not the runtime.
>
> Net effect: **16 → 20 agents.** `software-engineer` is retired (its skills + scope split
> into Python and Node). Two existing dispatchers (`project-manager`, `project-auditor`)
> must learn the new leaf names. The Decision Authority Matrix gains rows for Python/Node
> split + data + BI + AI domains.

This release is **additive (5 new personas) + retirement (1 old persona) + topology rewire
(dispatchers, matrix, 2 workflows) + parity fixups (tests, AGENTS.md, optional script)**.
No new workflows are introduced (per operator decision Q3 — rewire-only).

---

## 2. Functional Requirements

### FR1 — Five new agent personas authored

Author five new `.md` files under `dadaia_workspace/public/agents/`, each conforming to
the canonical agent frontmatter schema (`tier`, `model`, `tools`, `skills`, `maxTurns`,
`input_contract` with `requires_inputs` + `produces_outputs`, `paths.write_allowlist`,
plus the body sections: Scope, Forbidden actions, Workflow protocol, Skills surface,
Report contract). All five are **Tier 3 leaf specialists** (no Agent tool, no dispatch
authority). Model assignments:

| Agent file | Model | Rationale |
|---|---|---|
| `software-engineer-python.md` | `claude-sonnet-4-6` | Implementation work, parity with parent SE |
| `software-engineer-node.md` | `claude-sonnet-4-6` | Implementation work, parity with parent SE |
| `data-engineer.md` | `claude-sonnet-4-6` | Implementation + pipeline analysis |
| `data-analyst.md` | `claude-sonnet-4-6` | Dashboard build + analysis |
| `ai-engineer.md` | **`claude-opus-4-7`** | Meta-analysis of agents/skills/rules/workflows/hooks; cost/efficiency reasoning; persona authoring needs depth |

Each persona body MUST contain:

- Explicit **scope** — what the agent writes.
- Explicit **forbidden actions** — what the agent must refuse, with the standard
  `[SCOPE ERROR]` template (mirrors `game-developer-scope` rule pattern).
- **Workflow protocol** — input contract (release id, task id, paths to touch),
  TDD/`dadaia-task-manager` reservation flow, and exit criteria.
- **Skills surface** — declared `skills:` list in frontmatter; body cross-refs.
- **Report contract** — handoff sidecar via `dadaia-handoff-emitter`.

### FR2 — `software-engineer` retired

`dadaia_workspace/public/agents/software-engineer.md` is archived via `git mv` to
`specs/_archive/legacy-agents/<UTC>/software-engineer.md`. No replacement file remains
in `public/agents/`. The agent's scope (Python lib + Node tooling) is fully covered by
FR1's two specialist Python/Node personas.

### FR3 — `project-manager` dispatch list updated

`dadaia_workspace/public/agents/project-manager.md` — the "Dispatches:" line (currently
line ~231–233 referencing `software-engineer`) drops `software-engineer` and lists the
five new agents in the appropriate dispatch group. Any prose mentions of
"`software-engineer`" in the PM body are rewritten to "`software-engineer-python` /
`software-engineer-node`" or to a generic phrase, whichever preserves intent. Acceptance
grep: `grep -nE '\bsoftware-engineer\b' dadaia_workspace/public/agents/project-manager.md`
returns ZERO unsuffixed matches (only `-python`/`-node` are allowed).

### FR4 — `project-auditor` evidence list updated

`dadaia_workspace/public/agents/project-auditor.md` — extend the evidence/escalation
inventory to include `data-engineer` (data-drift evidence in audit-cycle) and
`ai-engineer` (prompt-efficiency evidence). Update any "PM-auditor inlined scope" prose
where `software-engineer` is bare-mentioned. Same zero-bare-mention grep acceptance as
FR3 applies to the auditor file.

### FR5 — Decision Authority Matrix gains 5 rows

`dadaia_workspace/public/skills/project-orchestration/SKILL.md` — the single
`Python/Node implementation` row currently at line ~108 is replaced with **five new
rows** in the order shown below (operator-confirmed wording):

| Domain | Primary Authority | May Object | Tie-breaker |
|---|---|---|---|
| Python implementation | `software-engineer-python` | `software-architect` | `software-architect` |
| Node implementation (server-side) | `software-engineer-node` | `software-architect`, `security-reviewer` | `software-architect` |
| Data engineering / pipelines / DABs | `data-engineer` | `software-architect` | `software-architect` |
| BI / dashboards / data viz | `data-analyst` | `design-specialist` (visual), `data-engineer` (source) | `design-specialist` (visual), `data-engineer` (data) |
| AI entities / skills / rules / workflows / hooks / personas | `ai-engineer` | `product-engineer` | `product-engineer` |

The leaf-agents-inventory table (line ~22 of the same SKILL.md) is also updated to drop
`software-engineer` and add the five new rows.

### FR6 — Workflow rewiring (rewire-only, no new files)

The 7 surviving workflows in `dadaia_workspace/public/workflows/` are audited; **two**
require edits:

- `cross-cutting-feature.workflow.md` — current body has no bare `software-engineer`
  reference (grep verified). FR6.1 is a **no-op audit**: confirm via grep and document
  in the closure. If a bare reference does emerge during P3 reading, rewrite it to
  pair `frontend-engineer` + `backend-engineer` (already the standard pair) or to
  `software-engineer-python`/`-node` if the spawned task is non-browser.
- `hotfix-release.workflow.md` — currently has two bare `software-engineer` references
  (`default: software-engineer` line ~22; description line ~23 enumerates implementer
  agents). FR6.2: change `default` to a guard string that the dispatcher must override
  (e.g. `default: ""` with a required-input gate) OR pick `software-engineer-python` as
  the conservative default. Update the `description` enum to include
  `software-engineer-python`, `software-engineer-node`, `data-engineer`, `data-analyst`,
  `ai-engineer`, and drop the bare `software-engineer` name.

The other 5 workflows (`audit-cycle`, `code-review-fan-out`, `game-dev-cycle`,
`onboarding-new-repo`, `spec-refinement`) are verified clean and left untouched.

Acceptance: `grep -rn '\bsoftware-engineer\b' dadaia_workspace/public/workflows/`
returns ZERO matches (only suffixed forms allowed).

### FR7 — Test fixtures updated for 20 agents

- `tests/unit/features/agents/test_reader.py` — update count assertion (currently 16) to
  20; extend frontmatter-parse coverage to the five new persona files; assert each new
  persona has `tier == 3`, a `paths.write_allowlist`, and a `model` value.
- `tests/unit/features/agents/fixtures/` — add minimal fixture files for the five new
  agent shapes (one per agent) if a test needs an isolated fixture rather than reading
  the live `public/agents/` tree.
- `tests/unit/features/panel/test_api_agents.py` — update the `/api/agents` card-count
  assertion from 16 to 20; update tier-count assertions to T1=2, T2=1, T3=17.
- Workflow-count test (if any) stays at 7 — no new workflows per operator decision Q3.

### FR8 — `dadaia_workspace/public/data/AGENTS.md` rewritten for 20 agents

The lib's source `data/AGENTS.md` (≤ 280-line invariant carried over from agents-r2-v1)
is rewritten to reflect 20 agents. The forbidden-strings invariant (no Hostinger /
redacted-infra / redacted-infra / Traefik / VPS prose) MUST remain clean. The agent inventory table
in this file lists all 20 agents with their model + tier + one-line scope.

Acceptance:

- `wc -l dadaia_workspace/public/data/AGENTS.md` ≤ 280.
- `grep -iE 'Hostinger|redacted-infra|redacted-infra|Traefik' dadaia_workspace/public/data/AGENTS.md`
  exit 1 (no match).
- Agent-inventory section contains exactly 20 rows.

### FR9 — Optional topology guard script

`scripts/check_agent_topology.py` (optional but recommended): asserts (a) exactly 20
files in `dadaia_workspace/public/agents/`; (b) every agent named in the PM dispatch
list exists in the persona directory; (c) every agent named in the auditor evidence
list exists; (d) the Decision Authority Matrix in `project-orchestration/SKILL.md`
references no orphaned agent name. Exit non-zero on drift. Script is referenced from
the CLOSURE validations table.

### FR10 — Three memory atoms updated in CLOSURE

During CLOSURE phase (P6) only, `product-engineer` updates:

- `specs/memory/product/agent-orchestration.html` — 16 → 20 agent count, new tier-3
  names, Python/Node split rationale paragraph, AI-entity surface authority paragraph,
  data/BI surfaces.
- `specs/memory/architecture.html` — agent-topology layer updated for the 20-agent
  split; Decision Authority Matrix domain rows refreshed.
- `specs/memory/product/index.html` — feature catalog gains data + BI + AI capability
  bullets.

These edits are CLOSURE-phase only (gate-locked). No memory edits are permitted during
SPEC/PLAN/TASKS/IMPLEMENTATION phases.

---

## 3. Acceptance Criteria

Each criterion is machine-verifiable. The CLOSURE Validations table records the command
and its evidence (commit SHA, stdout snippet, or report path).

- **C1 — Count assertion.** `ls dadaia_workspace/public/agents/*.md | wc -l` → `20`.
- **C2 — No bare SE references.**
  `grep -rn '\bsoftware-engineer\b' dadaia_workspace/public/{agents,skills,workflows,commands,rules} \
    | grep -v 'software-engineer-python\|software-engineer-node\|legacy\|archived'`
  returns ZERO lines (exit 1).
- **C3 — Frontmatter parse green.** `pytest -q tests/unit/features/agents/` exits 0;
  all 20 agents parse with `tier`, `paths.write_allowlist`, `model`, `skills`.
- **C4 — Panel API count.** `pytest -q tests/unit/features/panel/test_api_agents.py`
  exits 0; `/api/agents` returns 20 agents with `tier ∈ {1,2,3}` and tier counts
  `T1=2, T2=1, T3=17`.
- **C5 — Path-scope gate honours new allowlists.** A unit test simulating `ai-engineer`
  attempting to write `dadaia_workspace/cli/main.py` is BLOCKED with
  `[PATH SCOPE ERROR]`; a complement test verifies `software-engineer-python` IS
  allowed at the same path.
- **C6 — Decision Authority Matrix delta.** The matrix in
  `dadaia_workspace/public/skills/project-orchestration/SKILL.md` has the **five new
  rows** named in FR5 in the listed order, and the single legacy Python/Node row is
  gone (`grep -c 'Python/Node implementation' SKILL.md` → `0`).
- **C7 — `dadaia public doctor` green.** All `[ok]`, zero drift; stale
  `software-engineer` projection files cleaned from `.agents/`, `.claude/`, `.codex/`,
  `.opencode/`.
- **C8 — `dadaia specs doctor` green.** `0 errors / 0 warnings` against the current
  workspace state, including memory atom updates landed in P6.
- **C9 — Live panel smoke.** Launching the panel renders 20 agent cards with correct
  tier accents (T1 red, T2 amber, T3 neutral). Evidence: screenshot under
  `specs/assets/panel-r5-archive-tip-or-later/agents-r3-v1-panel.png` referenced from
  the CLOSURE.md.
- **C10 — Operator review of personas.** Each of the five new persona files is read
  end-to-end by the operator; tone, scope, and forbidden-actions block match the plan.
  Evidence: explicit operator OK recorded in CLOSURE.md alongside C1–C9.

---

## 4. Out of Scope

The following items are explicitly deferred to backlog. Mentioning them in the closure
backlog-returns section is mandatory.

- **New workflows for data/BI/AI flows.** `data-pipeline-cycle.workflow.md`,
  `dashboard-publication.workflow.md`, `ai-entity-refinement.workflow.md` — these
  declarative workflows wait for a concrete operator demand to drive them. r3 is
  rewire-only per Q3.
- **Recursive `ai-engineer` bootstrap.** `ai-engineer` does NOT author any persona /
  skill / rule / workflow in this release. Persona is authored by `product-engineer`
  (per Q4); `ai-engineer`'s first real run on its own surface is deferred to a
  follow-up release once the persona is battle-tested.
- **`product-engineer` migration off persona authoring.** While Q2 grants `ai-engineer`
  exclusive write authority over `public/agents/**`, the **first** authoring pass for
  the 5 new files is done by `product-engineer` in P1 (Q4 explicit). The transition of
  ongoing persona maintenance into `ai-engineer`'s hands happens in a later release.
- **`codex-agent-orchestration-parity-v1` count update.** The backlog candidate entry
  locking "16 canonical agents" is left alone during r3. Its update from 16 → 20 is
  recorded as a backlog-return note in this release's CLOSURE so the next planning
  round catches it.

---

## 5. Boundaries — write_allowlist per new persona

Operator-approved write-allowlist boundaries (verbatim from the plan):

| Agent | `paths.write_allowlist` | Notes |
|---|---|---|
| `software-engineer-python` | `dadaia_workspace/features/**`, `dadaia_workspace/infrastructure/**`, `dadaia_workspace/cli/**`, `dadaia_workspace/core/**`, `dadaia_workspace/container.py`, `dadaia_workspace/__init__.py`, `scripts/**`, `tests/**`, `repos/**` (Python projects only), `.dadaia/reports/<ctx>/software-engineer-python/**` | Explicitly EXCLUDES `dadaia_workspace/public/**` (ai-engineer territory). |
| `software-engineer-node` | Node sub-trees under `dadaia_workspace/` (if any emerge), `repos/**` (Node projects), `tests/**`, `.dadaia/reports/<ctx>/software-engineer-node/**` | Cannot touch browser surfaces (frontend-engineer territory: `*.tsx`, browser `*.ts`/`*.js`, CSS, HTML). Cannot touch `public/**`. |
| `data-engineer` | `repos/redacted-slug-explorer/**`, `**/*.sql`, `**/databricks/**`, `**/dabs/**` (excluding dashboards subtree), `**/notebooks/**`, `tests/**`, `.dadaia/reports/<ctx>/data-engineer/**` | Primary scope `redacted-slug-explorer`; available cross-project. |
| `data-analyst` | `repos/**/dashboards/**`, `repos/**/genie/**`, `repos/**/bi/**`, `**/dabs/dashboards/**`, `.dadaia/reports/<ctx>/data-analyst/**` | Builds dashboards via DABs; cannot write pipelines. |
| `ai-engineer` | `dadaia_workspace/public/skills/**`, `dadaia_workspace/public/rules/**`, `dadaia_workspace/public/workflows/**`, `dadaia_workspace/public/commands/**`, `dadaia_workspace/public/agents/**`, `dadaia_workspace/public/hooks/**` (if introduced), `.dadaia/reports/<ctx>/ai-engineer/**` | Cannot write Python/Node code, specs, or tests. Reads everywhere; writes only AI-entity surface. |

Updated boundary for the existing curator:

| Agent | `paths.write_allowlist` | Notes |
|---|---|---|
| `product-engineer` (updated) | `specs/**` (except `_archive/`), `.dadaia/reports/<ctx>/product-engineer/**` | LOSES de facto authority over `public/agents/*.md` (now `ai-engineer`'s, per Q2). Keeps SPEC/PLAN/TASKS/CLOSURE + memory atoms. |

Note: `product-engineer`'s persona file IS edited mechanically in P1 to reflect this
narrower allowlist; the substantive transition (PE stops authoring personas day-to-day)
is gated to a future release per Q4.

---

## 6. Dependencies and Risks

**Dependencies:**

- panel-r5-v1 is CLOSED and ARCHIVED before this branch is cut (operator confirmed in
  dispatch brief; ACTIVE.md already reflects `release: agents-r3-v1, phase: SPEC` on
  branch `release/agents-r3-v1`).
- agents-r2-v1's path-scope gate (`sdd-spec-gate.sh` step 6) is in place and enforces
  `paths.write_allowlist`. The 5 new personas inherit enforcement automatically; no
  gate changes are required in r3.
- panel-r4-v1's tier-aware UI rendering covers any 20-agent count automatically (all 5
  new agents are Tier 3 → neutral accent). No panel rendering changes required.

**Risks + mitigations:**

| Risk | Mitigation |
|---|---|
| Drift between agent personas, PM dispatch list, auditor evidence list, tests, and `data/AGENTS.md` | FR9 optional `scripts/check_agent_topology.py` + P5 doctor checkpoint catch missed updates. |
| Stale projection of `software-engineer.md` in `.agents/`, `.claude/`, `.codex/`, `.opencode/` after retirement | P5 R4 cleanup pattern (from agents-r2-v1 P8) — `dadaia public stage && install --target all --force && doctor`. |
| `ai-engineer`'s opus model assignment increases token cost vs sonnet | Acceptable trade-off for meta-analysis depth (operator-confirmed). Cost is bounded because ai-engineer is invoked rarely — only for AI-entity surface edits. |
| `cross-cutting-feature.workflow.md` may already be clean (no bare SE) | FR6.1 framed as audit; if grep confirms clean, the task is a documentation acknowledgement, not a file edit. |
| Recursive scope confusion: `ai-engineer` would author personas including its own | Q4 explicitly assigns P1 authoring to `product-engineer`. ai-engineer's first authoring pass deferred to a follow-up release. |

---

**Status:** Aprovado
