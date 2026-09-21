---
name: dd-release-implementation
description: >
  Implement a release candidate from the first task reservation through the
  promote-or-continue gate. Use when working a task inside an Approved candidate, at
  candidate closure, and at the gate (the next candidate, or promote + branch cut).
---

# dd-release-implementation

> Not hook-enforced. No engine advances gates, drives closure, or reads `TASKS.md` — implementers, the reviewer, `dd-project-manager` uphold it directly.

## 1. When

- `dd-software-engineer` working a task inside an `Approved` candidate.
- `dd-project-manager` at each candidate's closure.
- From the first reservation through the promote-or-continue gate (and, on promote, the ship + branch cut).

## 2. Steps

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Resolve the live release by reading `_RELEASE.json`'s `phase` field directly.
3. The live candidate's `TASKS.md` sits at `releases/<v>/TASKS.md` — always flat; the prior candidate's trio is in git, never on disk.
4. Full navigation protocol: `dd-spec-navigator`.
5. Read `RC-FLOW.md` for the candidate arc and gate cadence before acting past reservation.
6. Update `_RELEASE.json` per `RELEASE-EVENTS.md`'s shape and `log` conventions.
7. At `RC-FLOW.md` step 5, run `MEMORY-UPDATE.md`'s full protocol before touching any memory atom.
8. Declare test intent at birth; pass the admission filter (`dd-test-stewardship`, intent and admission) before a test enters the suite.
9. Before growing any module, run the deletion test and speak the seam vocabulary (`dd-codebase-design`) — a diff that only adds justifies itself against replace-don't-layer.
10. Handle demotion and quarantine/SCAFFOLD expiry at closure time only (`RC-FLOW.md` step 6).

## 2a. Push green

- Every `feature/{M.m.p}` push runs the local CI preflight first: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`.
- The push IS the publication boundary: pre-push scans every object the pushed range introduces or rewrites against the denylist; no path is exempt.
- Published history is the baseline and is never rescanned; a fixture needing a secret shape composes it at runtime, never as a tracked literal.
- Only pushes are review-blocked; commits flow freely, and a full scan lives only in the audit lane.
- Watch every push and PR to green — a red job is fixed at its cause, never waited out.
- A `quarantine`-marked test sits outside the gating selectors, bug-gated; unregistered pass-on-retry is a failure.

## 3. Done when

- Live release resolved by reading `_RELEASE.json` directly.
- Task reserved (`[-]`) with an isolated `chore(tasks): start <id>` commit (`RC-FLOW.md` step 1).
- Current step (`RC-FLOW.md`) identified before attempting its unlock action.
- CI green before any push; trio `APPROVED` before the candidate's develop PR.
- At candidate closure: memory update -> closure narrative -> disposition sweep -> artifact GC -> merge -> the promote-or-continue gate.

## 4. References

- `RC-FLOW.md` — gate cadence table, the candidate arc, out-of-scope list.
- `RELEASE-EVENTS.md` — `_RELEASE.json` shape, milestone ownership, `log` conventions.
- `MEMORY-UPDATE.md` — closure memory protocol.
- `dd-test-stewardship` (intent and admission) — the test admission filter.
