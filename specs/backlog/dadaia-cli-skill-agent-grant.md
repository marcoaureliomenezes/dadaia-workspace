---
title: "dadaia-cli skill granted to no agent while its description claims all agents may use it"
status: candidate
opened: 2026-08-15
description: >-
  F-1 (v0.10.0 SPEC §4 item 7, verified): the dadaia-cli skill's description claims
  "all agents may use it" while it appears in NO agent's frontmatter `skills:` list —
  under frontmatter-scoped grants it is reachable only by the top-level session, so
  every dispatched sub-agent that needs CLI literacy is working from a skill it cannot
  activate. Pre-existing, independent of the v0.10.0 family. Fix: decide the intended
  reachability and make grant and description agree — either grant dadaia-cli to the
  agents whose protocols invoke the CLI (with reasoned per-agent selection, not a
  blanket grant), or narrow the description to the top-level-session reality.
intents:
  - subject:
      kind: doc
      ref: memory/product/agents/agentic-entities.md#Registry
    change: >-
      The registry/frontmatter skill grants and the dadaia-cli skill description agree:
      each agent whose protocol requires CLI invocation carries the grant, or the
      description stops claiming universal reachability; the derivation surface records
      the decided reachability so grant/description drift is checkable.
---

# dadaia-cli skill — grant/description mismatch (F-1)

## Description

See frontmatter. Source: v0.10.0 SPEC §4 item 7 (design-report Part A finding F-1),
routed to `project-manager` as a new entry — pre-approved intake, SPEC §4.7.

## Acceptance criteria

- `grep -l "dadaia-cli"` over `public/agents/*.md` frontmatter matches exactly the
  decided grant set (possibly empty), and the skill's description states that set
  truthfully.
- A reachability note records the decision (who gets CLI literacy and why).

## Provenance

Pre-approved intake P-3 (operator ratification at v0.10.0 approval, SPEC §4.7 — "new PM
entry"). Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation — intake report #2
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`ai-engineer` (agent frontmatter + skill description). Priority P3.
