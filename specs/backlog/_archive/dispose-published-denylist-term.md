---
title: "Dispose of the already-published denylist term in the two archived backlog files (void by construction)"
status: rejected
opened: 2026-08-14
rejected_reason: >-
  Dissolved by grill ADR #3b (2026-08-14): with the denylist scan scoped to NEW
  objects of the pushed range (git rev-list --objects origin/develop..develop), the
  already-published term is amnestied for free — specs/_archive/ is FROZEN (never
  edited) and git mv creates no new blob, so the tainted archived files can never
  enter a scanned range. No amnesty list, no history rewrite, no disposition action
  remains. The FROZEN↔scan invariant is documented in the push-range-denylist-scan
  SPEC instead.
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5). CLOSURE
  text: "Dispose of the already-published denylist term in the two archived backlog
  files (now reachable from both main and develop) — an operator decision carried
  forward from v0.6.0." The operator decision arrived in the 2026-08-14 grill and
  voided the question by construction (ADR #3b) — see rejected_reason.
intents:
  - subject:
      kind: cli
      ref: ci push-gate-check
    change: >-
      None — void by construction under the range-scoped scan (ADR #3/#3b). The
      surviving obligation (document the FROZEN↔scan invariant) belongs to the
      push-range-denylist-scan SPEC, not to this entry.
---

# Dispose of the already-published denylist term

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", ideas item 6 (destination `backlog/ideas.md`). Materialized terminal
(`rejected`) so the carried-forward v0.6.0 operator decision has a recorded answer and
is never re-litigated.
