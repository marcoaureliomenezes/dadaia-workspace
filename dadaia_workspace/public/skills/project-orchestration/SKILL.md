---
name: project-orchestration
description: >
  Reference for project-manager and project-auditor agents. Provides agent inventory,
  workflow inventory, dispatch protocol, mediation patterns, escalation triggers,
  and forbidden actions. Load when dispatching agents or arbitrating conflicts.
applyTo: ".dadaia/reports/**"
---

# project-orchestration — Agent Dispatch & Mediation

## Agent Inventory

All 20 agents active in this workspace (post `agents-r3-v1`: 2 dispatchers T1 +
1 curator T2 + 17 leaf specialists T3). Column "Dispatches to" lists agents this
agent commonly calls as sub-agents. Column "Do NOT call when" lists conditions
that make the agent unsuitable.

| Agent | Primary Mission | Dispatches to | Do NOT call when |
|---|---|---|---|
| `product-engineer` | Own spec lifecycle; write SPEC, PLAN, TASKS, CLOSURE; guardian of `specs/` | software-architect, project-manager | Implementation is already DONE; task is code-level only |
| `software-architect` | Architecture decisions, ADRs, pattern selection, cross-repo dependency mapping | software-engineer-python, software-engineer-node, backend-engineer | Task is pure feature impl without architectural trade-off |
| `software-engineer-python` | Python implementation (CLI, lib, tooling); unit + integration tests; deploy trigger | qa-engineer | Task is Node tooling, Go backend, frontend, game code, data pipeline, BI, or AI entities |
| `software-engineer-node` | Server-side Node/TS tooling (CLIs, harnesses, opencode glue); unit + integration tests | qa-engineer | Task is Python implementation, browser-bound frontend, Go backend, game code, data pipeline, BI, or AI entities |
| `frontend-engineer` | Browser HTML/CSS/TS/React, design-system token consumption | design-specialist, qa-engineer | Task is backend, CLI, or server-side only |
| `backend-engineer` | Go HTTP services, production DB integrations, high-perf infra | software-engineer-python, software-engineer-node | Task is Python/Node tooling or scripting |
| `data-engineer` | Data pipelines (Spark, Airflow, Kafka), Delta/Iceberg/Parquet, DABs, ETL/ELT | software-engineer-python (for tooling glue) | Task is BI dashboards, browser UI, or non-data backend |
| `data-analyst` | BI dashboards, data visualisation, KPI specs; paired with `design-specialist` for visual review | — | Task is data-pipeline authorship (data-engineer territory) or production code |
| `ai-engineer` | AI entities (skills, rules, workflows, commands, agents, hooks); prompt-efficiency analysis | — | Task is Python or Node implementation, specs, or game code |
| `qa-engineer` | E2E test strategy, acceptance criteria, E2E test files | — | Unit or integration tests only; those belong to software-engineer-python / software-engineer-node |
| `devops-engineer` | GitHub Actions YAML, CI/CD pipelines, container orchestration | software-engineer-python | No CI change is in scope |
| `security-reviewer` | OWASP audit, CVE scanning, STRIDE threat model, IaC security review | software-engineer-python, software-engineer-node, devops-engineer | No security-relevant change; pure docs task |
| `code-reviewer` | PR architecture review, SOLID/pattern audit, complexity report | — | No PR or branch diff to review |
| `researcher` | External-source investigation against whitelisted sources | — | Task can be answered by reading local specs/code |
| `project-manager` | Cross-agent dispatch, workflow orchestration, conflict mediation | any agent | Single-agent task; no cross-domain coordination needed |
| `project-auditor` | Memory↔implementation drift, compliance scoring, dead-code detection | project-manager | Active release is mid-implementation (wait for CLOSURE phase) |
| `design-specialist` | UX/UI review, WCAG audit, design spec authoring, visual hierarchy analysis | frontend-engineer | Task is purely functional with no UI surface |
| `game-developer` | Unreal Engine C++, Blueprints, game mechanics, physics, AI | game-tester | Task lives outside `repos/tauan-games/` |
| `game-designer` | Game assets, maps, audio, material pipelines, HDA scripts | game-developer | Task is code-level game logic |
| `game-tester` | UE5 automation scripts, game test reports | — | Task is not game-related |

---

## Workflow Inventory

7 canonical workflows (post-`agents-r2-v1` trim; 8 deprecated workflows moved to
`specs/_archive/legacy-workflows/` and replaced by PM Playbooks below). Each row
names the trigger event, the entry agent, and key intermediate stages.

| # | Workflow file | Trigger | Entry Agent | Key Stages |
|---|---|---|---|---|
| W-01 | `spec-refinement` | New feature scope or spec ambiguity | project-manager | discovery → 5-way parallel specialist review → synthesis → product-engineer SPEC write |
| W-02 | `hotfix-release` | Production defect requiring a versioned patch | project-manager | triage → implement → qa-engineer smoke → CLOSURE |
| W-03 | `code-review-fan-out` | PR opened on monitored repo | code-reviewer | diff fetch → 6-axis review → report → approve/request-changes |
| W-04 | `audit-cycle` | Release CLOSURE phase or scheduled compliance audit | project-auditor | memory inventory → diff walk → scoring → report → project-manager |
| W-05 | `game-dev-cycle` | New game mechanic or asset for `repos/tauan-games/` | game-developer / game-designer | spec → impl → game-tester report |
| W-06 | `cross-cutting-feature` | Full-stack feature requiring frontend + backend shipped together | software-architect (contract) | contract review → parallel FE + BE impl → integration validation |
| W-07 | `onboarding-new-repo` | New repository requires baseline compliance assessment | project-manager | 3-way specialist audit → gap report → SPEC → remediation |

---

## Dispatch Protocol

Use the `Agent` tool to dispatch sub-agents. Never chain more than one level of
sub-agents from a single session (project-manager → agent A is allowed;
project-manager → agent A → agent B from A is forbidden without explicit operator
approval).

### Agent tool call shape

```json
{
  "subagent_type": "<agent-name>",
  "description": "<one-sentence task summary>",
  "prompt": "<full task prompt with input_contract below>"
}
```

### Input contract injection

Every dispatch prompt must include the following block at the top so the
sub-agent can resolve context without additional reads:

```
## Input Contract
- context: <context-name>          # from `dadaia context show --json`
- specs_dir: <absolute-path>       # e.g. /…/dadaia-workspace/specs
- release_id: <release-id>         # e.g. agents-r1-v1
- task_id: <task-id>               # e.g. AGT-18
- report_dir: .dadaia/reports/<context-name>/<agent-name>/
```

### Output path convention

Sub-agent reports always land in:
```
.dadaia/reports/<context-name>/<agent-name>/<ISO-timestamp>-<task-slug>.html
```

After writing the HTML, the sub-agent must emit the `.handoff.json` sidecar
(see `dadaia-handoff-emitter` skill).

---

## Decision Authority Matrix

Extend this template for any cross-domain dispute. The matrix is authoritative
for the dadaia workspace. For game-domain disputes, see `game-agents-coordination`.

| Domain | Primary Authority | May Object (with evidence) | Tie-breaker |
|---|---|---|---|
| Feature scope, SPEC, TASKS | **product-engineer** | all agents | product-engineer (final word) |
| Architecture, ADRs, patterns | **software-architect** | software-engineer-python, software-engineer-node, backend-engineer | software-architect |
| Python implementation | **software-engineer-python** | software-architect, security-reviewer | software-architect |
| Node implementation (server-side) | **software-engineer-node** | software-architect, security-reviewer, frontend-engineer (if browser boundary contested) | software-architect |
| Data engineering / pipelines / DABs / Delta | **data-engineer** | software-architect, backend-engineer (if pipeline feeds Go service) | software-architect |
| BI / dashboards / data viz | **data-analyst** | design-specialist (visual), data-engineer (source-data correctness) | design-specialist on visual; data-engineer on data |
| AI entities (skills, rules, workflows, commands, agents, hooks) | **ai-engineer** | product-engineer (when persona scope conflicts with SPEC authority) | product-engineer |
| Go backend, prod DB | **backend-engineer** | software-engineer-python, software-engineer-node, software-architect | software-architect |
| Browser UI, design tokens | **frontend-engineer** | design-specialist | design-specialist |
| Security posture | **security-reviewer** | software-engineer-python, software-engineer-node, devops-engineer | security-reviewer |
| CI/CD, pipelines | **devops-engineer** | software-engineer-python | devops-engineer |
| E2E acceptance criteria | **qa-engineer** | software-engineer-python, software-engineer-node | qa-engineer |
| UX/UI design spec | **design-specialist** | frontend-engineer | design-specialist |
| Compliance / drift scoring | **project-auditor** | product-engineer | product-engineer |
| Orchestration, mediation | **project-manager** | any | operator via `dadaia-grill-me` |

Rules:
- An objection without evidence (file:line citation or spec reference) is automatically ignored.
- No agent blocks the domain of another. Objection ≠ veto.
- When primary authority and objector cannot resolve in one exchange, escalate to tie-breaker.

---

## Anti-Deadlock Protocol

Activate when two agents are in unresolved conflict after one round of exchange.

### Step 1 — Positions documented

Each conflicting agent writes its position and trade-offs in its own report
section labeled `## Conflict Position`. Include:
- The specific decision point.
- Preferred resolution and rationale.
- Acknowledged downside of own position.

### Step 2 — Synthesis report

`project-manager` reads both position sections and writes a synthesis report
(HTML under `.dadaia/reports/<context>/project-manager/`) that:
- Summarizes each position neutrally.
- Identifies the actual decision point (often narrower than each agent believes).
- Proposes a resolution aligned with the Decision Authority Matrix.

### Step 3 — Operator escalation

If synthesis does not resolve the conflict or if the dispute crosses authority
boundaries, invoke `dadaia-grill-me` with the operator. Format:

```
dadaia-grill-me: Two agents are blocked on [topic].
Agent A position: [summary].
Agent B position: [summary].
Synthesis attempted: [what project-manager proposed].
Decision needed: [single yes/no or option-A/B question].
```

The operator's answer is final and must be committed to the relevant SPEC or ADR.

---

## Escalation Triggers

Stop orchestrating and surface to the operator immediately when any of these
conditions is met:

1. **3+ unresolved conflicts** — three or more distinct agent disputes are open
   simultaneously with no resolution path visible.
2. **Missing context** — the `specs_dir` does not contain an `ACTIVE.md`, or
   required SPEC/PLAN/TASKS files are absent or lack `**Status:** Aprovado`.
3. **Unknown workflow** — the requested task does not match any row in the
   Workflow Inventory and cannot be decomposed into existing workflows without
   a new SPEC.
4. **Security breach signal** — any agent reports a CRITICAL security finding;
   pause all other work and route to `security-reviewer` immediately.
5. **SCOPE ERROR from sub-agent** — a dispatched agent returns a `[SCOPE ERROR]`
   response. Do not re-dispatch to the wrong agent; escalate to operator to
   clarify task assignment.

---

## Forbidden Actions

The following are hard-prohibited for `project-manager` and `project-auditor`:

| Action | Why Forbidden |
|---|---|
| Edit any file outside `.dadaia/reports/` | Write scope is reports-only for orchestration agents |
| Chain sub-agents beyond one level deep without operator approval | Creates untracked recursive dispatch; breaks observability |
| Mark a TASKS.md item `[x]` without confirming with qa-engineer | Premature closure; may skip E2E validation |
| Dispatch to `game-developer`, `game-designer`, `game-tester` for non-game tasks | Violates domain boundary in `game-developer-scope` rule |
| Edit `specs/` directly | Exclusive domain of `product-engineer` |
| Bypass `sdd-spec-gate` by skipping `[-]` marker before editing production files | Violates `dadaia-task-manager` protocol |
| Start a new release while another is in IMPLEMENTATION phase | Concurrent releases require operator approval |

---

## Quick Reference — dadaia CLI

```bash
dadaia context show --json        # resolve active context + specs_dir
dadaia specs doctor               # validate 11 SDD structural invariants
dadaia public doctor              # verify all public lib projections are [ok]
dadaia public stage               # stage local public/ edits
dadaia public install --target all  # propagate staged edits to all contexts
```

---

## PM Playbooks

> **R3 — PM-only invocation:** These playbooks are dispatched only by
> `project-manager`; no leaf-agent invokes them directly. Leaf agents (e.g.
> `software-engineer-python`, `software-engineer-node`, `qa-engineer`) receive
> task prompts from PM — they never select or trigger a playbook themselves.

Playbooks consolidate the 8 workflow files removed in `agents-r2-v1` (P1).
No corresponding `*.workflow.md` file exists under
`dadaia_workspace/public/workflows/` for any of these playbooks (NFR8:
keeping a stale workflow file would re-introduce the surface that P1 deleted).
Surviving workflow files (`spec-refinement`, `hotfix-release`, etc.) that contain
textual references to former playbook names (e.g. `tdd-cycle`, `bug-fix-fastlane`)
are using them as contextual labels only — they are not acting as live workflow
definitions for the removed patterns (R6 cross-reference verified in AGT-r2-09).

PM identifies the trigger, picks the playbook, dispatches the entry agent with
the input contract above, then mediates if the playbook branches.

### Playbook — architecture-review

**Trigger:** ADR proposal, cross-cutting tech-debt spike, or new pattern adoption.

**Entry:** `software-architect`.

**Steps:**
1. PM dispatches `software-architect` with the architectural question + relevant
   memory atoms (`memory/architecture.html`, `memory/tech-stack.html`).
2. Architect emits ADR report under
   `.dadaia/reports/<context>/software-architect/<UTC>-adr-<slug>.html`.
3. PM forwards ADR to `product-engineer` for SPEC integration (if release-bound)
   or to `backlog/candidates.md` (if speculative).
4. If ADR proposes migration: dispatch the right implementer for the surface —
   `software-engineer-python` for Python migrations, `software-engineer-node` for
   Node tooling migrations, `backend-engineer` for Go surfaces, `data-engineer`
   for data-pipeline migrations — for impl planning; CLOSURE updates
   `memory/architecture.html`.

**Stop conditions:** architect declines (out-of-scope) → backlog. Two valid
options remain → escalate to operator via `dadaia-grill-me`.

### Playbook — tdd-cycle

**Trigger:** feature task with non-trivial logic where red-green-refactor is mandated.

**Entry:** `software-engineer-python` (Python tasks), `software-engineer-node`
(Node tooling tasks), or `backend-engineer` (Go).

**Steps:**
1. PM confirms TASKS.md item is `[-]` and dispatches engineer with TDD intent
   stated in the prompt.
2. Engineer writes failing test first → commit (red).
3. Engineer implements → commit (green).
4. Engineer refactors → commit (refactor).
5. PM dispatches `qa-engineer` for E2E coverage on the new behaviour.

**Stop conditions:** engineer cannot reproduce a red test → spec gap → return to
`product-engineer`. Refactor introduces regression → revert + re-plan.

### Playbook — bug-fix-fastlane

**Trigger:** reproducible defect with narrow blast radius; no SPEC change needed.

**Entry:** `software-engineer-python` (Python surface) or `software-engineer-node`
(Node surface); `backend-engineer` for Go bugs; `frontend-engineer` for browser
bugs.

**Steps:**
1. PM captures the bug report (operator message or `qa-engineer` finding) and
   classifies severity + surface.
2. PM dispatches the surface-appropriate implementer (Python → software-engineer-python,
   Node → software-engineer-node, Go → backend-engineer, browser → frontend-engineer)
   with: reproduction command, expected vs. actual, target file(s).
3. Engineer reproduces locally → writes regression test → patches → commits.
4. PM dispatches `qa-engineer` for verification when patch is non-trivial; skip
   when fix is one-line + has regression test.

**Stop conditions:** root cause crosses sub-domain (e.g. spec drift) → escalate
to `product-engineer`. Fix requires schema change → promote to feature delivery.

### Playbook — game-bugfix

**Trigger:** defect inside `repos/tauan-games/` (any of the 3 active games).

**Entry:** `game-tester` (for triage) → `game-developer` or `game-designer`.

**Steps:**
1. PM dispatches `game-tester` with reproduction notes; tester classifies the
   bug as logic (→ developer) or asset/design (→ designer).
2. If tester emits two sub-reports (cross-domain), PM dispatches both
   `game-developer` and `game-designer` in parallel using disjoint write sets.
3. Each game-* agent patches its sub-domain; commits land in
   `repos/tauan-games/` only.
4. `game-tester` re-runs UE5 automation and emits the verification report.

**Stop conditions:** bug requires engine upgrade → escalate to operator (engine
upgrades are not in-domain for `game-*`). Visual regression unconfirmed → request
new screenshot evidence from tester before re-dispatch.

### Playbook — security-patch

**Trigger:** CVE published against a dependency, `security-reviewer` finding,
or operator-reported leak.

**Entry:** `security-reviewer`.

**Steps:**
1. PM dispatches `security-reviewer` with the advisory ID, affected surface, and
   severity hint.
2. Reviewer emits triage report (severity, blast radius, mitigation options).
3. If patch is code: PM dispatches the surface-appropriate implementer
   (`software-engineer-python` for Python, `software-engineer-node` for Node,
   `backend-engineer` for Go, `frontend-engineer` for browser).
   If patch is CI/CD or infra: PM dispatches `devops-engineer`.
4. After fix lands, PM re-dispatches `security-reviewer` for verification +
   updated posture report.

**Stop conditions:** CRITICAL severity with active exploit → pause all other
work (escalation trigger #4). Patch requires secret rotation → also invoke the
secrets-leak response steps (rotate credential → force-push or BFG → audit trail).

### Playbook — deploy-validation-only

**Trigger:** deploy already happened; operator wants validation-only sweep
(no code change in scope).

**Entry:** `qa-engineer`.

**Steps:**
1. PM dispatches `qa-engineer` with the deploy target, expected behaviour, and
   smoke-test scope (URL, container name, or panel surface).
2. QA runs the smoke (Playwright, `dadaia panel`, container probe) and captures
   evidence (screenshots, logs, sha256 of critical files).
3. QA emits validation report at
   `.dadaia/reports/<context>/qa-engineer/<UTC>-deploy-validation.html`.
4. PM reads report and either closes the dispatch ([ok]) or opens a bugfix
   fastlane (defect found).

**Stop conditions:** QA finds CRITICAL drift between deployed state and
`memory/*.html` → escalate to `project-auditor` for drift audit.

### Playbook — design-validation

**Trigger:** new UI surface or redesign request; visual/UX evidence needed
before implementation.

**Entry:** `design-specialist` (consumes screenshots from `qa-engineer`).

**Steps:**
1. PM dispatches `qa-engineer` first to capture current-state screenshots via
   Playwright MCP under `.dadaia/reports/<context>/qa-engineer/<UTC>-*.png`.
2. PM dispatches `design-specialist` with the screenshot paths + design brief.
3. Designer emits spec report with tokens, sketches, WCAG audit, and handoff
   block at
   `.dadaia/reports/<context>/design-specialist/<UTC>-design-spec.html`.
4. PM forwards the design report to `frontend-engineer` for implementation.
   FE refuses to implement without a fresh design report (see
   `design-specialist-scope` rule).

**Stop conditions:** design conflict with `memory/product/*.html` semantics →
route to `product-engineer` for spec arbitration.

### Playbook — spec-refinement

**Trigger:** open question on an existing SPEC, ambiguity discovered mid-impl,
or operator request to crystalise a backlog item.

**Entry:** `product-engineer`.

**Steps:**
1. PM dispatches `product-engineer` with the SPEC path (or backlog item) and
   the open question.
2. PE runs `dadaia-grill-me` (skill) on the operator for the irresolvable
   slice; resolves the answerable slice by code inspection.
3. PE emits refine-specs report at
   `.dadaia/reports/<context>/product-engineer/<UTC>-refine-specs.html` and
   updates the SPEC/PLAN/TASKS as required (gate-permitted writes only).
4. PM routes the refined SPEC back to the original workflow (impl, deploy, etc.).

#### scope=game

Replaces the pre-r2 `game-spec-definition` workflow. When the refinement scope
is a game SPEC under `specs/releases/<id>/` whose deliverables live in
`repos/tauan-games/`, the protocol adds two steps:

- PE consults `game-developer` and/or `game-designer` (read-only via report
  reference) for engine-specific constraints before drafting FRs.
- The CLOSURE phase routes memory updates through
  `memory/product/<game-feature-slug>.html` and the relevant
  `memory/architecture.html` UE5/Phaser/Three.js section, not generic memory.

**Stop conditions:** refinement reveals a missing release entirely → PE files
a new candidate in `backlog/candidates.md` and surfaces to operator.

---

## Parallel-researcher fan-out pattern

For evidence-heavy phases (audit, code-review, security-scan), dispatch N `researcher` agents in parallel with tightly-scoped questions. Synthesise from sidecars — not from inline large-file reads.

Pattern:
1. Decompose the investigation into N atomic questions (each scoped to ≤ 5 files or 1 concept).
2. Dispatch N `researcher` agents in parallel (one question each).
3. Each researcher returns a sidecar `*.handoff.json` with `findings[].detail_md`.
4. Synthesising agent reads sidecars only (not HTML) and emits a synthesis sidecar.

Model: `researcher` = Haiku 4.5 (cheap; fast). Escalate to `DADAIA_MODEL_OVERRIDE=sonnet` only if context is too complex for Haiku.
