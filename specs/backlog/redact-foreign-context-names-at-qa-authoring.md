---
title: "Redact foreign Spec Context names at QA authoring time"
status: candidate
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5). CLOSURE text:
  "Both privacy incidents entered through verbatim dadaia doctor output transcribed
  into an ALPHA-1-QA.md; a doctrine line (or a doctor --redact output mode) closes the
  entry path at the source, complementing the whole-tree scan." ABSORBED: per grill
  ADR #5, this item is absorbed as an FR of the push-range-denylist-scan release
  (defence in depth — redaction-at-authoring closes the leak's ENTRY path; the range
  scan closes the EXIT path). NOT pickable in isolation; it ships inside that release.
intents:
  - subject:
      kind: catalog
      ref: workspace-doctor
    change: >-
      Doctor/presence output gains a redaction posture for foreign Spec Context names
      when transcribed into authored documents (doctrine line and/or a --redact output
      mode), so QA evidence can be pasted without carrying foreign context names into
      pushed history. Delivered as an FR of the push-range-denylist-scan release, not
      as a standalone pick.
---

# Redact foreign Spec Context names at QA authoring time

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", fifth item (destination `backlog/candidates.md`).

**Absorvido como FR na release push-range-denylist-scan (grill ADR #5) — não pickável
isoladamente.**

## Acceptance criteria

Inherited by the push-range-denylist-scan SPEC as an FR; this entry is marked delivered
when that release ships the redaction FR.
