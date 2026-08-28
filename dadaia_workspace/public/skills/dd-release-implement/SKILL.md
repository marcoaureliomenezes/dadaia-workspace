---
name: dd-release-implement
description: >
  Use when: implementing a release from the first task reservation through the
  final-rc ship — the whole implement-to-close arc under the v2/rc segment model.
  Short SKILL-plus-disclosed-siblings shape (T-050-21, FR12): RC-FLOW.md (state
  ladder + gate cadence), RELEASE-EVENTS.md (RELEASE.json state+log contract),
  MEMORY-UPDATE.md (closure memory protocol). CLOSURE.md/CLOSURE-TEMPLATE.md
  retired — the closure narrative now lives in RELEASE.json's log.
tldr: "Reserve -> TDD -> segment close -> rc rounds -> final-rc trio -> memory -> closure narrative -> archive -> ship."
applyTo: "specs/releases/*/TASKS.md"
---

# dd-release-implement

> Not hook-enforced. No engine advances gates, drives closure, or reads `TASKS.md` — implementers, reviewers, `product-engineer` uphold it directly.

## 1. When

- Any implementer (`software-engineer`, `ai-engineer`, `qa-engineer`) working a task inside an `Aprovado` release.
- `product-engineer` at the final-rc closure.
- From the first reservation through the ship PR and the post-deploy branch cut.

## 2. Steps

1. Resolve the active release by reading `RELEASE.json`'s `phase` field directly — no fold, no `ACTIVE.md`.
2. Locate `TASKS.md` at `releases/<release-id>/<segment>/TASKS.md` when `segment` is present.
3. Locate `TASKS.md` at `releases/<release-id>/TASKS.md` otherwise.
4. Full navigation protocol: `dadaia-workspace-spec-navigator`.
5. Read `RC-FLOW.md` for the state ladder, gate cadence, and 14-step arc before acting past reservation.
6. Update `RELEASE.json` per `RELEASE-EVENTS.md`'s shape and `log` conventions.
7. At final-rc step 8, run `MEMORY-UPDATE.md`'s full protocol before touching any memory atom.
8. Declare test intent at birth; pass the admission filter (`dadaia-test-stewardship` §A/§B) before a test enters the suite.
9. Handle demotion and quarantine/SCAFFOLD expiry at closure time only (`RC-FLOW.md` step 9).

## 3. Done when

- Release + segment resolved by reading `RELEASE.json` directly.
- Task reserved (`[-]`) with an isolated `chore(tasks): start <id>` commit.
- Current step (`RC-FLOW.md`) identified before attempting its unlock action.
- CI green before any push; trio `APPROVE`d before any final-rc unlock action.
- At final rc: memory update -> closure narrative -> disposition sweep -> artifact GC -> archive, one commit, in that order.

## 4. References

- `RC-FLOW.md` — gate cadence table, 14-step arc, out-of-scope list, segments rule.
- `RELEASE-EVENTS.md` — `RELEASE.json` shape, milestone ownership, `log` conventions.
- `MEMORY-UPDATE.md` — closure memory protocol.
- `dadaia-task-manager` — reservation/marker discipline.
- `dadaia-test-stewardship` §A/§B — test admission filter.
- `DADAIA.md` §3 — git chokepoints, the only mechanical backstop.
