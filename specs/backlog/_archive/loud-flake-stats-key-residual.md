---
title: "The stats-key residual in the loud-flake gate (delivered at HEAD)"
status: delivered
opened: 2026-08-14
release: v0.7.0-followup (T-070-09)
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5) and found
  ALREADY DELIVERED at HEAD during materialization. CLOSURE text: "A structurally
  valid Playwright report lacking stats still exits 0 because // 0 defeats jq -e;
  one-token fix (drop // 0) or a has(\"stats\") precheck, plus correcting the ee02006e
  commit-message claim." Verified 2026-08-14: .github/workflows/ci.yml:367 now runs
  FLAKY=$(jq -er '.stats.flaky' "$REPORT") with an explicit hard-error fallback
  ("malformed or lacks stats — hard error, never a pass"), plus non-numeric and
  missing/empty-report hard errors — delivered by commit 15cb12c4 (T-070-09,
  "Degenerate-report hardening"). The ee02006e commit-message claim is immutable
  history and cannot be corrected; this entry records the correction instead.
intents:
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Flake Policy
    change: >-
      None remaining — the degenerate-report hardening shipped (ci.yml loud-flake
      step: jq -er + hard-error fallback + numeric guard). This entry exists to close
      the CLOSURE's routing claim honestly and to correct, in repository text, the
      ee02006e commit-message claim the CLOSURE flagged.
---

# The stats-key residual in the loud-flake gate

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", third item (destination `backlog/candidates.md`). Materialized terminal:
the defect was fixed at HEAD before this entry existed (evidence:
`.github/workflows/ci.yml:361-374`, commit `15cb12c4`, task T-070-09 finding 1).
