release: v0.4.3
segment: none
phase: IMPLEMENTATION

Release v0.4.3 — "claims-made-true / backlog-zero".

Segment tracking (ADR D1 — **ratified** by the dispatcher, 2026-08-17). This release is
**segmented** (ADR R1: `alpha-1` … `alpha-6` → `rc-1`, order amended by ADR R10), but it
keeps **one** authoritative document set at `specs/releases/v0.4.3/` and expresses the
segment cadence as per-segment blocks inside `TASKS.md`. The `segment:` pointer therefore
stays `none`: the shipped schema-v2 routing binds a non-`none` `segment:` value to a
per-segment document directory (`releases/<id>/<segment>/{SPEC,PLAN,TASKS}.md`), and this
release deliberately does not duplicate its document set six times. The live segment is
named in `TASKS.md` §Segment map and advanced by the QA gate tasks
(`T-043-12/23/31/37/45/49`).

Segment order (R10): `alpha-1` AI surface · `alpha-2` gate + primitives (+ the Arm-B
rider) · `alpha-3` suite + complexity · `alpha-4` Codex · `alpha-5` event-driven GC ·
`alpha-6` consumer round + CHANGELOG (**last**, so it certifies the assembled surface
including GC) · `rc-1` review → memory → closure → archive → ship.

Phase ladder for this release:
DEFINITION (now) → IMPLEMENTATION (from T-043-01) → CLOSURE (T-043-50/51) → ARCHIVED.
