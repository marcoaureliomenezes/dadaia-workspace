---
title: "doctor/lint warning for an installed tests/AGENTS.md still carrying <PLACEHOLDER> tokens"
status: idea
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "A doctor/lint warning
  for an installed tests/AGENTS.md that still contains <[A-Z_]+> placeholders (code
  review r1 finding 8, half-implemented: the fill-me banner shipped, the check did
  not)." Verified at HEAD 2026-08-14: placeholder checks exist only for memory atoms
  (MEM-PLACEHOLDER-1, features/specs/doctor.py:119) — no check covers an installed
  tests/AGENTS.md.
---

# doctor/lint warning for tests/AGENTS.md placeholders

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", ideas item 1 (destination `backlog/ideas.md`; per-file materialization —
the ideas.md file was never created; the BACKLOG.md consolidation ratified by grill
ADR #14 supersedes that split).
