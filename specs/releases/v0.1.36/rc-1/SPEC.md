# SPEC: v0.1.36 rc-1 - PI Layer-2 Release-Definition Ship Gate

**Status:** Aprovado
**Release ID:** v0.1.36
**Segment:** rc-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Objective

Ship the already-closed `v0.1.36/alpha-1` PI Layer-2 release-definition hardening as a
release candidate. This segment does not add product scope; it validates the alpha output,
keeps the active release model coherent, and records the ship decision.

## Scope

In scope:

- Re-run deterministic rc gates over the committed alpha changes.
- Verify the `v0.1.36/alpha-1` CLOSURE evidence includes real PI Layer-2 command, create,
  and review-gate validation.
- Keep all `v0.1.36` alpha bug dispositions intact.
- Write an `rc-1` CLOSURE with validation results and ship disposition.

Out of scope:

- New PI feature work.
- Consuming additional backlog.
- Re-running full live PI e2e unless deterministic gates or alpha evidence are
  insufficient; the alpha closure already includes the opt-in real PI review-gate proof.
- Renaming this release to a different SemVer.

## Requirements

| ID | Requirement | Evidence |
|----|-------------|----------|
| R1 | `rc-1` MUST be scoped to release-candidate validation of `v0.1.36/alpha-1`, not new feature work. | This SPEC, PLAN, and TASKS. |
| R2 | Deterministic tests for the PI adapter, release-definition workflow, lifecycle run model, and PI live-test skip behavior MUST pass. | rc validation command output. |
| R3 | Specs doctor MUST report zero errors. | `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`. |
| R4 | Public projection doctor MUST remain green for privacy/model/workflow policy. | `dadaia public doctor`. |
| R5 | Repo hygiene MUST remain clean; no generated live-test release artifacts may remain in the repo. | repo hygiene scan + `git status`. |

## Traceability

- Builds on: `specs/releases/v0.1.36/alpha-1/CLOSURE.md`
- Commits under validation:
  - `2ce13f11 fix: harden pi layer2 release definition`
  - `dd7ca936 fix: make release artifact hashes python authoritative`
