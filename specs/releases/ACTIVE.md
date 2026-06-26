---
release: v0.1.27
phase: IMPLEMENTATION
segment: alpha-1
---

Active release: **v0.1.27 — wire the consumed_backlog PRODUCER at release-definition**
(the v0.1.26 R2 residual, `FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01`, HIGH). R2 shipped
the full removal-on-release mechanism + the closure-side `remove` invocation, but left
the producer unwired: nothing writes `consumed_backlog.json` in production, so
`remove_at_closure` no-ops and the BL-STALE loop never fires end-to-end.

**Operator-resolved design decision (2026-06-26):** a release declares its consumed
backlog items via a machine-readable `**Consumes:** slug1, slug2` line in the release
SPEC. At `dadaia lifecycle release define`, a guarded `post_step` parses that line, binds
each slug's intents through the R1 registry → the verified shipped-anchor set, and calls
`BacklogRemovalLifecycle.consume(...)` to write the ledger — symmetric with the
`dadaia lifecycle close` removal already wired in R2.

Source backlog: `specs/backlog/wire-consumed-ledger-producer-at-release-definition.md`.
Then: `workflow-model-governance-panel-control-plane`.
