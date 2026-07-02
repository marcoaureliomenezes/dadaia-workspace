---
release: v0.1.52
phase: IMPLEMENTATION
---

# Active release: v0.1.52 — Panel Plumbing

Sequence position: **R4 of the operator-approved 12-release plan** (grilled 2026-07-02,
`specs/backlog/candidates.md` §Release sequence; operator-elected early position).
Two-part scope with a hard ordering constraint: (1) the Sessions tab becomes an
aggregated-cost-dashboard-only section — the aggregate moves SERVER-side before the
session list dies; (2) telemetry/runtime reliability lands against the post-removal
route surface — every SQLite connection through the pragma'd WAL factory, killing the
concurrent-corruption class. Consumes `panel-sessions-cost-dashboard-only` →
`panel-runtime-reliability`.

Previous: **v0.1.51** — CLOSED and ARCHIVED at `specs/_archive/releases/v0.1.51/`
(merged `5329cd96`; closure `ccc47934`).
