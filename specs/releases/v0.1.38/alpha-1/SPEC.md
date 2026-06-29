# SPEC: v0.1.38 alpha-1 - pi-agent-fourth-harness WS-PI-5

**Status:** Aprovado
**Release ID:** v0.1.38
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29
**Consumes:** pi-agent-fourth-harness

---

## 1. Scope

Complete the final residual of the `pi-agent-fourth-harness` epic: WS-PI-5, "Absorb and
retire `dadaia-pi-workspace`."

The previous PI releases already delivered the PI Layer-2 adapter, result extraction,
`.pi/` projection, Ring-1 PI extension, and PI telemetry. The live backlog item now carries
only one remaining intent:

> DEAD-mark the standalone `dadaia-pi-workspace` context with a deprecation pointer to the
> epic; never delete the repo.

## 2. Requirements

| ID | Requirement | Acceptance |
|----|-------------|------------|
| R1 | Preserve a deprecation pointer in the standalone repo before retiring it. | `dadaia-pi-workspace` has a committed `README.md` explaining that PI now lives in `dadaia-workspace` and pointing to the epic. |
| R2 | Mark the standalone context DEAD using workspace tooling. | `dadaia context show dadaia-pi-workspace --json` reports `"state": "dead"`. |
| R3 | Do not delete repo history. | No manual deletion is performed; the local checkout is removed only by `dadaia context dead`, leaving the remote repo as history/evidence. |
| R4 | Consume the backlog item. | `specs/backlog/pi-agent-fourth-harness.md` records a terminal consumed/delivered disposition for v0.1.38, and the release declares `**Consumes:** pi-agent-fourth-harness`. |
| R5 | Keep workspace and SDD health green. | `dadaia specs doctor`, `dadaia public doctor`, repo hygiene scan, and relevant context-state checks pass. |

## 3. Picked Inputs

| Artifact | Role |
|----------|------|
| `specs/backlog/pi-agent-fourth-harness.md` | Consumed backlog item, residual WS-PI-5 only. |
| `specs/bugs/context-dead-nonwritable-guard-rejects-standard-git-objects.md` | Picked blocking bug discovered during real WS-PI-5 execution. |
| `repos/dadaia-pi-workspace/README.md` | Deprecation pointer to commit in the standalone repo before DEAD-marking. |
| `.dadaia/states/spec_contexts.json` via `dadaia context` CLI | Context state authority for ALIVE/DEAD. |

## 4. Out Of Scope

- Any new PI adapter/runtime feature.
- Any new `.pi/` projection behavior.
- Any deletion of the standalone remote repository or history.
- Any manual edit to `.dadaia/states/spec_contexts.json`.

## 5. Risks

- `dadaia context dead --commit` syncs and removes the local repo. Mitigation: inspect the
  standalone repo status first; only the deprecation `README.md` should be untracked.
- Context DEAD may be blocked by live leases or repo sync errors. Mitigation: use the
  workspace CLI only and record any blocker as a bug before continuing.
