---
title: "Destination-file symlink hardening for the adjacent repo-AGENTS.md copy"
status: idea
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "Destination-file symlink
  hardening for the adjacent repo-AGENTS.md copy, matching workspace_guardrail.py's
  four refusal sites. The new tests/AGENTS.md seam was hardened at review r2; its
  neighbour still follows the older shape." Verified at HEAD 2026-08-14:
  infrastructure/public_assets.py carries no symlink refusal
  (grep symlink/is_symlink: none) — the neighbour seam is still unhardened.
---

# repo-AGENTS.md destination symlink hardening

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", ideas item 5 (destination `backlog/ideas.md`).
