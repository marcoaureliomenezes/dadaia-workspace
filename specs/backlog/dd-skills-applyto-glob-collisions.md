---
title: "dd- skill family: applyTo glob collisions blur the one-skill-per-stage activation boundary"
status: candidate
opened: 2026-08-15
description: >-
  The seven dd-* lifecycle skills' `applyTo` frontmatter globs collide pairwise — e.g.
  two skills both claim specs/backlog/** — so the one-skill-per-stage boundary the
  family was built on is not expressed in the activation surface: a harness resolving
  which skill governs a path can activate the wrong stage's skill or two at once.
  Verified live at HEAD 57dc4937 in all seven canonical SKILL.md frontmatters. Fix:
  partition the globs so each lifecycle stage owns a disjoint activation surface (or
  document an explicit precedence rule where genuine overlap is intended), and add a
  projection-time collision check so a future skill cannot silently reintroduce the
  ambiguity.
intents:
  - subject:
      kind: catalog
      ref: agentic-entities
    change: >-
      The dd- family's applyTo globs become pairwise disjoint (or carry a documented
      precedence rule); the agentic-entities derivation/lint surface gains a check that
      flags colliding applyTo globs across projected skills.
---

# dd- family applyTo glob collisions

## Description

See frontmatter. Source: code-review pre-PR handoff
`.dadaia/handoff/dadaia-workspace/2026-08-15T145731Z-code-reviewer-v0.10.0-prepr.handoff.json`
(LOW, un-absorbed by the pre-ship remediation commit `1cddb6fb`).

## Motivation

The dd- family's core design claim is one skill per lifecycle stage. An activation
surface that contradicts the design claim is drift at birth — cheap to fix now, costly
after more skills join the family.

## Acceptance criteria

- Pairwise glob comparison across all dd-* SKILL.md frontmatters yields zero undocumented
  collisions.
- Where overlap is intentional, the precedence is stated in the colliding skills.
- A mechanical check (projection lint or test) fails on a newly introduced collision.

## Provenance

Intake report #2 item 2-1 — APPROVED. Trace: operator-delegated adjudication, 2026-08-15
(goal directive), verdicts per PM recommendation
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`ai-engineer` (AI-surface lane); rides the next AI-surface window together with
`dd-release-definition-orchestration-pointer-loop`. Priority P3.
