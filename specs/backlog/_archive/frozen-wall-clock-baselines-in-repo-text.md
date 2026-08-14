---
title: "Embed the frozen wall-clock baselines in repository text (delivered at HEAD)"
status: delivered
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5) and found
  ALREADY DELIVERED at HEAD during materialization. CLOSURE text: "Embed the frozen
  wall-clock baselines in repository text so the 1.5x timeout-minutes ratchet can be
  re-derived from the repo alone at audit time (QA finding F3)." Verified 2026-08-14:
  specs/memory/quality-assurance.md ("Test Health", lines 147-151) now embeds the
  frozen baselines (pre-push preflight quick 2:38, preflight full ~5:30, panel E2E
  1:10, full local suite 4:37 under -n auto) and states that each CI pytest job's
  timeout-minutes ceiling is set against them — the ratchet is re-derivable from the
  repo alone.
intents:
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#CI
    change: >-
      None remaining — the baselines are embedded in QA memory and the CI
      timeout-minutes ceilings reference them. This entry exists to close the
      CLOSURE's routing claim honestly.
---

# Embed the frozen wall-clock baselines in repository text

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", ideas item 3 (destination `backlog/ideas.md`). Materialized terminal:
delivered before this entry existed (evidence:
`specs/memory/quality-assurance.md:147-151`).
