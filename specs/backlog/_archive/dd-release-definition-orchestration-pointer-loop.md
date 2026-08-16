---
title: "Circular pointer: dd-release-definition ↔ project-orchestration release-definition playbook"
status: candidate
opened: 2026-08-15
description: >-
  dd-release-definition/SKILL.md:103 sends the reader to the project-orchestration
  release-definition playbook for the authority/dispatch view, while v0.10.0 reduced
  that playbook to a pointer back at dd-release-definition — a reference loop with no
  content at either end. One of the two ends must carry the actual statement (the
  playbook keeps its one-line dispatch note but names what it owns, or the skill's
  pointer is dropped). Not in the dispatcher's brief for the intake compilation; added
  by PM verification — a review round's residual is never dropped silently. One-line
  fix; rides with the applyTo-glob entry in the same ai-engineer window.
intents:
  - subject:
      kind: catalog
      ref: agent-orchestration
    change: >-
      The dd-release-definition ↔ project-orchestration cross-references form a DAG
      again: exactly one of the two files carries the release-definition
      authority/dispatch content, the other points at it; no pointer loop remains in
      public/.
---

# dd-release-definition ↔ project-orchestration pointer loop

## Description

See frontmatter. Source: code-review pre-PR handoff
`.dadaia/handoff/dadaia-workspace/2026-08-15T145731Z-code-reviewer-v0.10.0-prepr.handoff.json`
(LOW, un-absorbed by the pre-ship remediation).

## Acceptance criteria

- Following the reference chain from either file terminates at content in one hop.
- A grep of `public/skills/` finds no mutual pointer pair between the two files.

## Provenance

Intake report #2 item 2-3 — APPROVED. Trace: operator-delegated adjudication, 2026-08-15
(goal directive), verdicts per PM recommendation
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`ai-engineer`; P3; rides with `dd-skills-applyto-glob-collisions`.
