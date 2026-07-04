---
slug: dadaia-workflows
title: dadaia-workflows
category: product
tldr: The 7 governed Layer-2 workflows, all operator-invocable since v0.1.56 via ~12 CLI verbs; every model step gets fragment + persona.
summary: >-
  The roster and invocability truth of the dadaia-workflows: 7 workflows defined in
  the governed catalog (release_definition, implementation, backlog_definition,
  closure, audit, research, bug_report), now ALL operator-invocable (v0.1.56),
  surfaced by these CLI verbs: release define, backlog define, pipeline, implement,
  review qa|security|code, close, audit, research, bug_report, implement-review
  (~12 verbs on 7 workflows — implement-review is a verb on the implementation
  workflow, not a new workflow). audit/research/bug_report gained container builders
  + CLI verbs, born resolver-governed on the shared policy seam (no second raw
  id:effort path). Every model-driven step prompt on every verb carries its fragment
  AND its persona. Engine mechanics live in lifecycle-foundation.
tags:
- sdd
- workflows
- lifecycle
- layer-2
token_estimate: 750
last_updated: '2026-07-04'
release_origin: v0.1.56
---

## Purpose

A **dadaia-workflow** is a Python body that drives Layer-2 workers through steps: it
imports the step's **fragment** (the single-step instruction: inputs, task, output
contract), injects the role's **persona** (the operative "who you are" directive),
selects dynamic context, calls a discrete `(harness, model)` worker, and advances
**Python-validated gates** — the model recommends, Python decides the legality of the
transition. This atom is the single source of the ROSTER and of INVOCABILITY; the
engine mechanics (pipeline, gates, run store, data plane) are [[lifecycle-foundation]].

**The 7 workflows of the governed catalog** (defined in
`features/lifecycle/governed_catalog.py` — `governed_workflow_catalog()`; re-exported for
presentation on the stable public path `features/workflows/dadaia_catalog.py`):

| Workflow | Body | Availability | CLI verb |
|----------|------|--------------|----------|
| `release_definition` | `workflows/release_definition.py` | available | `dadaia lifecycle release define` |
| `backlog_definition` | `workflows/backlog_definition.py` | available | `dadaia lifecycle backlog define` |
| `implementation` | `pipeline.py` / `phase_workflow.py` | available | `dadaia lifecycle pipeline` (+ single-step verbs `implement`, `review qa\|security\|code`, and the `implement-review` loop verb) |
| `closure` | step `close` + `closure_removal_gate` | available | `dadaia lifecycle close` |
| `audit` | `workflows/audit.py` (real, fragment+gate) | available | `dadaia lifecycle audit` |
| `research` | `workflows/research.py` (real, fragment+gate) | available | `dadaia lifecycle research` |
| `bug_report` | `workflows/bug_report.py` (real, fragment+gate) | available | `dadaia lifecycle bug_report` |

**All 7 workflows are invocable (v0.1.56).** They are surfaced by these CLI verbs:
`release define`, `backlog define`, `pipeline`, `implement`,
`review qa|security|code`, `close`, `audit`, `research`, `bug_report`,
`implement-review` — ~12 verbs on 7 workflows. Keep the two counts distinct: the
**workflow** count is 7; the **verb** roster is larger because `implementation`
carries several verbs. `implement-review` is a **verb on the `implementation`
workflow** (the digest-injecting, runner-gated implement/review loop), **not** a new
workflow. `audit`/`research`/`bug_report` gained container builders + CLI verbs in
v0.1.56, each **born resolver-governed** on the shared policy seam (no second raw
`<id>:<effort>` path). The governed catalog was already AVAILABLE for all 7; v0.1.56
closed the invocability gap.

## Usage flow

1. An entry harness (or the operator) invokes a verb:
   `dadaia lifecycle <verb> --release-id <id> --harness {pi|codex|fake} [--model …]`.
2. The policy resolver freezes the per-step `(harness, profile, model)` snapshot before
   step 1 ([[lifecycle-foundation]] — control plane).
3. For each model-driven step, the prompt is assembled as **persona (role directive) +
   fragment bundle + dynamic context + output contract** — persona injection applies
   to ALL verbs (a shared helper threaded through the 5 workflow bodies AND the CLI's
   `_run_phase_step`), not just the pipeline.
4. The worker replies with the `schema: agent-run-result-v1` payload; the typed gate
   decides the advance (gate mechanics: [[lifecycle-foundation]] §"Gating note").
5. Steps communicate via the workflow-step handoff ledger ([[lifecycle-foundation]]
   §"Workflow-step handoff data plane"); a missing required upstream BLOCKS.

## Typical trigger

Release or backlog-item definition in a Codex/PI entry harness (where
dadaia-workflows are the preferred execution path); the implementation→review
pipeline in a release; the close at the end.

## Differentiator

Workflow authority stays in Python (step order, gates, ledger), not in free-form agent
text — a worker cannot "approve itself" outside the contract. Fragment and persona
separate the step's WHAT from the role's WHO, each with a single home
(`public/lifecycle_fragments/`, `public/personas/`).

## Runtime state touched

- `.dadaia/states/lifecycle/<run_id>.json` — run records (policy snapshot + step
  ledger).
- `.dadaia/runs/lifecycle/<run_id>/steps/*.step-payload.json` — immutable payloads.
- `.dadaia/states/workflow_model_policy.json` — policy overlay (panel/CLI).
- The context's `specs/` — the artifacts each workflow produces (SPEC/PLAN/TASKS,
  backlog item, CLOSURE), under the normal SDD gate.

## Dependencies

- [[lifecycle-foundation]] — the engine (pipeline, gates, run store, data plane,
  model/harness governance).
- [[agent-orchestration]] — the Layer-2 persona surface.
- [[tech-stack]] — the harness/model roster the verbs accept.
- [[sdd-gate-v3]] — the gate and chokepoints the workers' writes fall under.
- [[panel]] — the operator surface (diagram-cards + model pickers) over the same
  governed catalog.
