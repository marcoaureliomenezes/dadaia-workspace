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

All 16 agents active in this workspace. Column "Dispatches to" lists agents this agent
commonly calls as sub-agents. Column "Do NOT call when" lists conditions that make the
agent unsuitable.

| Agent | Primary Mission | Dispatches to | Do NOT call when |
|---|---|---|---|
| `product-engineer` | Own spec lifecycle; write SPEC, PLAN, TASKS, CLOSURE; guardian of `specs/` | software-architect, project-manager | Implementation is already DONE; task is code-level only |
| `software-architect` | Architecture decisions, ADRs, pattern selection, cross-repo dependency mapping | software-engineer, backend-engineer | Task is pure feature impl without architectural trade-off |
| `software-engineer` | Python/Node.js implementation, unit tests, integration tests, deploy trigger | qa-engineer | Task involves Go backend, game code, or frontend |
| `frontend-engineer` | Browser HTML/CSS/TS/React, design-system token consumption | design-specialist, qa-engineer | Task is backend, CLI, or server-side only |
| `backend-engineer` | Go HTTP services, production DB integrations, high-perf infra | software-engineer | Task is Python tooling or Node.js scripts |
| `qa-engineer` | E2E test strategy, acceptance criteria, E2E test files | — | Unit or integration tests only; those belong to software-engineer |
| `devops-engineer` | GitHub Actions YAML, CI/CD pipelines, container orchestration | software-engineer | No CI change is in scope |
| `security-reviewer` | OWASP audit, CVE scanning, STRIDE threat model, IaC security review | software-engineer, devops-engineer | No security-relevant change; pure docs task |
| `code-reviewer` | PR architecture review, SOLID/pattern audit, complexity report | — | No PR or branch diff to review |
| `project-manager` | Cross-agent dispatch, workflow orchestration, conflict mediation | any agent | Single-agent task; no cross-domain coordination needed |
| `project-auditor` | Memory↔implementation drift, compliance scoring, dead-code detection | project-manager | Active release is mid-implementation (wait for CLOSURE phase) |
| `design-specialist` | UX/UI review, WCAG audit, design spec authoring, visual hierarchy analysis | frontend-engineer | Task is purely functional with no UI surface |
| `game-developer` | Unreal Engine C++, Blueprints, game mechanics, physics, AI | game-tester | Task lives outside `repos/tauan-games/` |
| `game-designer` | Game assets, maps, audio, material pipelines, HDA scripts | game-developer | Task is code-level game logic |
| `game-tester` | UE5 automation scripts, game test reports | — | Task is not game-related |
| `software-architect` (ADR mode) | Architecture Decision Records, cross-cutting concerns | product-engineer | Micro-level impl decisions already settled |

---

## Workflow Inventory

15 canonical workflows. Each row names the trigger event, the entry agent, and key
intermediate stages.

| # | Workflow | Trigger | Entry Agent | Key Stages |
|---|---|---|---|---|
| W-01 | Feature delivery | Product decision: new feature needed | product-engineer | SPEC → PLAN → TASKS → software-engineer impl → qa-engineer E2E → CLOSURE |
| W-02 | Bug fix | Defect reported (user or monitor) | project-manager | triage → software-engineer patch → qa-engineer regression → deploy |
| W-03 | Security patch | CVE or security-reviewer finding | security-reviewer | severity assessment → software-engineer fix → devops-engineer redeploy → security-reviewer verify |
| W-04 | Architecture evolution | ADR proposal or tech-debt spike | software-architect | ADR draft → product-engineer approval → software-engineer migration → closure |
| W-05 | Dependency upgrade | `pip-audit` / `npm audit` HIGH+ | software-engineer | audit → upgrade → test → deploy |
| W-06 | CI/CD pipeline change | Build failure or new automation needed | devops-engineer | YAML edit → test run → software-engineer validate |
| W-07 | Design review | New UI surface or redesign request | design-specialist | UX audit → design spec → frontend-engineer impl → qa-engineer E2E |
| W-08 | PR code review | PR opened on monitored repo | code-reviewer | diff fetch → 6-axis review → report → approve/request-changes |
| W-09 | Compliance drift audit | Release CLOSURE phase or scheduled audit | project-auditor | memory inventory → diff walk → scoring → report → project-manager |
| W-10 | Game feature | New game mechanic or asset | game-developer / game-designer | spec → impl → game-tester report |
| W-11 | Release closure | All TASKS.md tasks `[x]` | product-engineer | CLOSURE.md authoring → memory update → ACTIVE.md archive |
| W-12 | Escalation / operator decision | 3+ unresolved agent conflicts | project-manager | positions documented → synthesis → `dadaia-grill-me` |
| W-13 | Secrets leak response | Secret detected in repo | security-reviewer | rotate credential → force-push or BFG → audit trail |
| W-14 | Infrastructure incident | Service down or Traefik failure | devops-engineer | root-cause → fix → verify → post-mortem |
| W-15 | Memory atom update | product-engineer CLOSURE phase | product-engineer | HTML memory edit → `dadaia specs doctor` → commit |

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
| Architecture, ADRs, patterns | **software-architect** | software-engineer, backend-engineer | software-architect |
| Python/Node implementation | **software-engineer** | software-architect | software-architect |
| Go backend, prod DB | **backend-engineer** | software-engineer, software-architect | software-architect |
| Browser UI, design tokens | **frontend-engineer** | design-specialist | design-specialist |
| Security posture | **security-reviewer** | software-engineer, devops-engineer | security-reviewer |
| CI/CD, pipelines | **devops-engineer** | software-engineer | devops-engineer |
| E2E acceptance criteria | **qa-engineer** | software-engineer | qa-engineer |
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
