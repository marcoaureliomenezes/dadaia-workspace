---
title: "MEMORY path class vs dotfiles / SPEC-assigned memory writes"
status: candidate
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "Decide whether
  specs/memory/.heading-allowlist (and dotfiles under specs/memory/ generally) belongs
  to the MEMORY class, and whether a SPEC may legitimately assign a memory-class path
  to a non-CLOSURE task." Verified at HEAD 2026-08-14: the gate classifies every path
  under specs/memory/ as MEMORY by prefix (features/spec_context/gate_policy.py:56
  _MEMORY_PREFIX, :218-219), with writability restricted to DEFINITION/CLOSURE phases
  (:89 _MEMORY_WRITE_PHASES) — dotfiles included, undecided by doctrine.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/spec_context/gate_policy.py#classify_path
    change: >-
      Decide and encode: (a) whether dotfiles under specs/memory/ (e.g.
      .heading-allowlist) are MEMORY-class or a carve-out; (b) whether a SPEC may
      assign a memory-class write to a non-CLOSURE/DEFINITION task, and how the gate
      should treat that assignment. The decision lands as code + a documented rule,
      not as an ad-hoc exception.
---

# MEMORY path class vs dotfiles / SPEC-assigned memory writes

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", sixth item (destination `backlog/candidates.md`), referencing the drift
noted in that CLOSURE.

## Acceptance criteria

Both questions answered by an explicit rule (law or gate code + test); the
.heading-allowlist write path is legal-by-rule rather than legal-by-accident; gate
tests pin the decided behavior.
