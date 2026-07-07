---
name: visual-review-protocol
description: >
  Use this skill when running a visual review of a UI change — the
  screenshot-evidence loop, viewport/responsive matrix, regression comparison,
  and the APPROVED/REQUEST_CHANGES verdict criteria design-specialist applies
  as the UI gate. Shipped by the frontend-design plugin pack; owned by
  design-specialist.
---

# Skill: visual-review-protocol

The visual-review protocol for the `frontend-design` pack. `design-specialist` uses it as the
UI approval gate: reviewing a `frontend-engineer` implementation handoff against the design
spec, on `qa-engineer` screenshot evidence, and returning a verdict. The *bar* being applied
(tokens, accessibility, responsive rules) is the shared checklist in
`browser-frontend-implementation`; this skill owns the review **procedure** — evidence,
matrix, comparison, verdict.

## When to use

- A UI implementation handoff awaits visual review before its task can leave `[-]`.
- A regression sweep after a shared-token or design-system change.
- Re-review after a `REQUEST_CHANGES` rework (always against the new commit).

## 1. Evidence first — no review without pixels

- Review **screenshot/browser evidence produced by `qa-engineer`**, plus a live dev-server
  pass when interaction states matter. Never review from the diff alone — code that "reads
  right" can render wrong.
- Evidence must name the commit sha it captures; stale evidence means re-capture, not
  guesswork.
- Missing or partial evidence is itself a `REQUEST_CHANGES` finding ("evidence gap"), not a
  reason to approve on faith.
- On the Codex runtime, session context (active release/task, latest design and QA screenshot
  reports, dev-server state) is injected by the existing runtime adapters — `design-ctx` for
  this role, `frontend-ctx` for the implementer. Consult the adapter at session start; it owns
  context-gathering and its own emit format — this skill owns only the review procedure.

## 2. Viewport / responsive matrix

Review every view in the change at minimum:

| Class | Check |
|---|---|
| Small (mobile) | Layout reflows per spec; no horizontal scroll; touch targets adequate. |
| Medium (tablet) | Breakpoint transitions match the spec'd behavior, not accidental. |
| Large (desktop) | Max-width behavior, alignment to the grid, no stretched artifacts. |
| States | hover/focus/active/disabled + loading/empty/error for each interactive element. |
| Modes | Dark/light and reduced-motion where the design system defines them. |

The matrix scales with risk: a copy change needs one viewport; a layout change needs all.

## 3. Regression comparison

- Compare against the **previous approved state** (prior screenshots/report), not memory.
- Sweep sibling surfaces that consume the same tokens/components as the change — shared-token
  edits regress at a distance.
- Any unexplained visual delta outside the task's declared scope is a finding, even if it
  "looks fine": undeclared change is drift.

## 4. Findings and verdict

Each finding is concrete and per-element: **element → expected (spec/token) → observed
(evidence) → severity**. "Looks off" is not a finding.

| Verdict | Criteria |
|---|---|
| `APPROVED` | Token fidelity holds (no off-token values); accessibility gates pass on evidence (contrast, focus visibility, keyboard path); responsive matrix clean; no unexplained regressions. |
| `REQUEST_CHANGES` | Any token violation, failed accessibility gate, broken state/viewport, unexplained regression, or evidence gap — each returned as a per-element finding. |

- The verdict handoff names the exact commit sha reviewed and carries `verdict` +
  `verdict_reason`.
- Rework re-enters at step 1 against the new commit — never "approve the delta" on stale
  evidence.
- A spec gap discovered during review (the implementation is faithful but the design is
  wrong) is routed back to the design spec via PM, not blamed on the implementer.

## Guardrails

| Rule | Detail |
|---|---|
| Shared bar | The checklist being enforced lives in `browser-frontend-implementation` — reference it, never fork a private review bar. |
| Evidence ownership | Screenshot/E2E evidence belongs to `qa-engineer`; you consume it, you do not produce or edit the E2E suite. |
| Gate, not implementer | You return findings; the rework belongs to `frontend-engineer` via PM. |
| No scope creep | Review the task's declared write set; new feature requests are product intent for `product-engineer`. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the review. |
