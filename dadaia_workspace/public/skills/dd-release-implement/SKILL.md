---
name: dd-release-implement
description: >
  Implement a release candidate from the first task reservation through the
  promote-or-continue gate. Use when working a task inside an Aprovado candidate, at
  candidate closure, and at the gate (rc-archive or ship + archive + branch cut).
---

# dd-release-implement

> Not hook-enforced. No engine advances gates, drives closure, or reads `TASKS.md` — implementers, reviewers, `product-engineer` uphold it directly.

## 1. When

- Any implementer (`software-engineer`, `ai-engineer`, `qa-engineer`) working a task inside an `Aprovado` candidate.
- `product-engineer` at each candidate's closure.
- From the first reservation through the promote-or-continue gate (and, on promote, the ship + branch cut).

## 2. Steps

1. Resolve the live release by reading `_RELEASE.json`'s `phase` field directly.
2. The live candidate's `TASKS.md` sits at `releases/<v>/TASKS.md` — always flat; `rc-N/` folders are archives, never routed to.
3. Full navigation protocol: `dadaia-workspace-spec-navigator`.
4. Read `RC-FLOW.md` for the candidate arc and gate cadence before acting past reservation.
5. Update `_RELEASE.json` per `RELEASE-EVENTS.md`'s shape and `log` conventions.
6. At candidate step 5, run `MEMORY-UPDATE.md`'s full protocol before touching any memory atom.
7. Declare test intent at birth; pass the admission filter (`dadaia-test-stewardship`, intent and admission) before a test enters the suite.
8. Handle demotion and quarantine/SCAFFOLD expiry at closure time only (`RC-FLOW.md` step 6).

## 3. Done when

- Live release resolved by reading `_RELEASE.json` directly.
- Task reserved (`[-]`) with an isolated `chore(tasks): start <id>` commit.
- Current step (`RC-FLOW.md`) identified before attempting its unlock action.
- CI green before any push; trio `APPROVE`d before the candidate's develop PR.
- At candidate closure: memory update -> closure narrative -> disposition sweep -> artifact GC -> merge -> the promote-or-continue gate.

## 4. References

- `RC-FLOW.md` — gate cadence table, the candidate arc, out-of-scope list.
- `RELEASE-EVENTS.md` — `_RELEASE.json` shape, milestone ownership, `log` conventions.
- `MEMORY-UPDATE.md` — closure memory protocol.
- `dadaia-task-manager` — reservation/marker discipline.
- `dadaia-test-stewardship` (intent and admission) — the test admission filter.
- `DADAIA.md` §3 — git chokepoints, the only mechanical backstop.
