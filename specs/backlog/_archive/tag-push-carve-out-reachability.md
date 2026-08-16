---
title: "Tag-push carve-out — require pushed tags to point at commits reachable from remote develop/main"
status: idea
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "Tag-push carve-out
  (carried forward from v0.6.0, restated by both security reviews): require a pushed
  tag to point at a commit already reachable from remote develop/main, designed
  together with the whole-tree denylist scan." ABSORBED: grill ADR #4 settled the
  design — tags remain exempt from security review (law §3 intact) but the denylist
  scan covers the new objects a tag publishes (rev-list --objects <tag> --not
  --remotes), closing the unscanned-object hole that motivated this item
  (chokepoints/service.py:344 filters tags before any policy). Ships inside the
  push-range-denylist-scan release; NOT pickable in isolation. A strict
  reachability requirement beyond the scan remains a future idea if ever needed.
---

# Tag-push carve-out — reachability requirement

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", ideas item 4 (destination `backlog/ideas.md`).

**Absorvido na release push-range-denylist-scan (grill ADR #4: tags cobertas pelo
scan) — não pickável isoladamente.**
