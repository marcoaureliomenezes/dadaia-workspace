# CLOSURE — Release v0.1.79 — Panel agentic-layers reorg

**Shipped:** PR #155, squash-merged to main as `ce4f7ac0` (2026-07-11). All PR checks
green; post-merge main CI green.

## Delivered

7→6 primary tabs in the ratified order (Projects | 1º Agentic Layer | 2º Agentic
Layer | Reports | Academy | Servers); Sessions cost/telemetry dashboard merged into
the 1º Agentic Layer tabpanel (standalone tab removed, all element ids preserved so
`sessions.js` needed zero changes); API surfaces byte-unchanged; CSP inline-script
hashes unchanged and live-recompute-verified; v0.1.59 grep gates green; no lease/lock
wording (v0.1.76 doctrine holds on panel surfaces).

## Review trail (the gates worked)

- QA **REJECTED round 1**: the two agentic-layer tabs were swapped vs the ratified
  order — the implementer had relabeled in place and written the fixtures to match
  the implementation instead of the SPEC. Fixed in `ae3f1a1d` (buttons + panel bodies
  + fixture + Playwright tours re-keyed); QA re-APPROVED with identical suite counts
  (zero regressions).
- Security APPROVED ×2 (initial + per-sha re-key; stale approval removed each time).

## Dispositions

- Backlog `panel-tab-reorg-agentic-layers`: **delivered**, archived.
- No bugs consumed (none open in this domain). Ledger unchanged: 1 open (LOW flake).

## Validations

- Panel unit 266; full suite 2,708 passed; e2e features 45; Playwright panel 59/59
  run locally exactly as CI runs it; mypy --strict clean; doctors green.
