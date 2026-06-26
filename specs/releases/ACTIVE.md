---
release: none
phase: ARCHIVED
---

No active release. **v0.1.26 (R2 — `backlog_definition` workflow body +
removal-on-release)** is CLOSED — CLOSURE.md written + memory atoms updated; pending the
coordinator's `git mv` to `specs/_archive/releases/v0.1.26/`. With R1 (v0.1.25) + R2
(v0.1.26) both shipped, the epic `FEAT-BACKLOG-DEFINITION-WORKFLOW-01` is dispositioned
`DELIVERED — v0.1.26`.

**Next step:** the R2 residual —
`specs/backlog/wire-consumed-ledger-producer-at-release-definition.md`
(`FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01`, HIGH): wire the `consumed_backlog` ledger
**producer** (`consume_at_release_definition`) into the real release-definition surface so
removal-on-release fires end-to-end (the closure consumer is already wired into
`dadaia lifecycle close`). Then: `workflow-model-governance-panel-control-plane`.
