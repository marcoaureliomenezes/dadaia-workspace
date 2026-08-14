---
title: "Flat release's ship task cannot record its own completion (TASKS template shape defect)"
status: idea
opened: 2026-08-14
description: >-
  v0.8.0 CLOSURE backlog return, materialized 2026-08-14. In a flat (no-segment)
  release, the closure/archive task freezes the release directory (git mv to
  specs/_archive/) before the ship task can flip its own marker: v0.8.0's T-080-07
  (ship) archived as "[ ]" because T-080-06 (closure + archive) ran first and the
  archived TASKS.md is FROZEN — the ship marker can never be flipped afterwards.
  The release TASKS template needs a form of ship evidence that lives outside the
  archived directory: either make ship the last task BEFORE archive, or state in
  the template that the ship task's evidence is the merge/PR itself and that its
  marker is expected to archive open.
---

# Flat release ship-task evidence outside the archived directory

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.8.0/CLOSURE.md` §"Drifts"
and §"Backlog returns", sixth item (destination `backlog/ideas.md`).

Observed shape, v0.8.0: finalization order is memory update → CLOSURE → archive
(DADAIA.md §5), and the archive move was executed by the closure task (T-080-06).
The ship task (T-080-07: merge to local develop, diff security review, push, PR)
runs *after* the directory is frozen, so its `[ ]` marker is permanently
unflippable — the marker trace asserts unfinished work that in fact completed,
with the real evidence living in git (merge commit, push, PR #189).

## Motivation

The `[ ]/[-]/[x]` markers are the auditable trace of who took what (DADAIA.md §5).
A template whose last task structurally archives open produces one guaranteed
false-open marker per flat release — noise in exactly the artifact that exists for
audit. Candidate resolutions (template-level, product-engineer surface):

1. Reorder: ship becomes the last task before the closure/archive task.
2. Declare: the template states ship evidence = the merge/PR + push record, and
   the ship marker is expected to archive `[ ]` (a documented, non-defect open).

## Acceptance criteria

(To be bound at candidate promotion — the release TASKS template and/or
`dadaia specs release` scaffolding reflect one of the two resolutions, and the
next flat release archives with zero unexplained open markers.)
