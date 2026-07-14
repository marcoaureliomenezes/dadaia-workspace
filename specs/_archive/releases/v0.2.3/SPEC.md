# SPEC: v0.2.3 - Four-workflow consolidation

**Status:** Aprovado

## Problem

The lifecycle product exposes seven governed workflows and several overlapping
execution verbs. Research, bug reporting, closure, standalone reviews, pipeline,
and retry verbs duplicate orchestration boundaries, fragment composition, state
transitions, and handoff behavior. The resulting surface is difficult to reason
about and has failed real operator validation.

## Required outcome

The governed catalog and operator-facing workflow execution surface contain
exactly four workflows:

1. `backlog_definition`
2. `release_definition`
3. `implementation_reviews`
4. `audit`

Diagnostics such as status, preflight, hygiene, policy inspection, and handoff
doctor remain utilities, never additional workflows.

## Functional requirements

- `backlog_definition` absorbs demand research and bug intake needed to author
  one consistent backlog item.
- `release_definition` produces and reviews SPEC, PLAN, and TASKS, ending at
  the implementation-ready gate.
- `implementation_reviews` owns implementation, self-verification, QA,
  security review, code review, bounded correction, and closure.
- `audit` scopes, inspects, dispositions findings, and validates workflow/handoff
  coherence without silently deleting evidence.
- Every model step receives exactly one persona plus its main fragment, shared
  fragments, bounded dynamic context, and one output contract.
- Each step emits one immutable run-scoped payload. Python validates the payload
  before transition; required upstream payloads are consumed by exact run, step,
  and attempt identity.
- Removed workflow IDs and execution verbs must not remain callable or visible
  in the panel/catalog.
- The panel gains a `Games` tab that can run Snake and Tetris for phantom-release
  implementation quality validation.

## Validation requirements

- Focused unit, integration, CLI, handoff-ledger, and panel tests cover the four
  workflows as complete sequences, not disconnected helpers.
- Four phantom releases execute the four workflows from start to audit.
- Codex Layer 2 implements and reviews Snake cycles; PI Layer 2 implements and
  reviews Tetris cycles.
- Any defect found during a workflow run is registered, fixed, and the affected
  workflow is restarted from its first step.
- Games are playable from the panel and verified at desktop and mobile sizes.

## Non-goals

- Adding a fifth workflow.
- Preserving deprecated workflow execution aliases.
- Treating maintenance/diagnostic commands as workflows.
- Shipping the games as a product commitment outside this validation release.
