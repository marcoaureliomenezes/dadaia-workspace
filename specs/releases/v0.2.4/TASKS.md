# Tasks: Hotfix Release - v0.2.4

> **Status:** Aprovado
> **Release ID:** v0.2.4
> **Patches release:** v0.2.3
> **Owner:** product-engineer
> **Created:** 2026-07-14

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

## T1 - Suppress hook-runtime bytecode

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Preconditions:** v0.2.3 archived; bug `hook-runtimes-create-repo-bytecode` reported.
- **Files modified:** `dadaia_workspace/infrastructure/runtime_config.py`,
  `dadaia_workspace/features/workspace/service.py`,
  `dadaia_workspace/public/pi/extensions/dadaia-sdd-gate.ts`, focused projection tests.
- **Changes:** add Python `-B` to Claude, Codex, and PI hook launches; add an executed
  repository-hygiene regression; restage projections.
- **Acceptance:** all launch surfaces include `-B`; executed wrapper leaves no bytecode;
  focused tests and public doctor pass.

## T2 - Verify and close

- [-] **Status:** IN PROGRESS
- **Owner:** product-engineer
- **Preconditions:** T1 complete and committed.
- **Files modified:** bug ledger, `CLOSURE.md`, `ACTIVE.md`.
- **Changes:** resolve the bug with evidence, run doctors/hygiene, and archive v0.2.4.
- **Acceptance:** zero open bugs, specs doctor has zero errors, source tree is clean.
