# TASKS: v0.1.21 — WS-PI-4: PI Layer-1 Ring-1 SDD-gate extension

**Status:** Aprovado
**Release ID:** v0.1.21

## DEFINITION (memory + specs)

- [x] T-21-01 — Author SPEC/PLAN/TASKS (Status: Aprovado).
- [x] T-21-02 — Constitution §4/§8 PI rows: PI gains Layer-1 Ring-1 extension (post-trust caveat).
- [x] T-21-03 — Memory honesty: architecture.md Layer-1 parity PI row; multi-platform-parity; lifecycle-foundation (WS-PI-4 no longer deferred); sdd-gate-v3 if applicable. Regenerate catalog.

## IMPLEMENTATION (assets/code/tests)

- [x] T-21-04 — Author `public/pi/extensions/dadaia-sdd-gate.ts` (tool_call → pre_gate; write→Write/edit→Edit; fail-open; venv resolve; node child_process).
- [x] T-21-05 — Wire projection: `_PI_DIRS` += "extensions"; `public/pi/settings.json` += extensions list. `public stage && install --target pi && doctor`.
- [x] T-21-06 — Test: projection + content contract for `.pi/extensions/dadaia-sdd-gate.ts` (exists, settings lists it, invariants present, no leak).
- [x] T-21-07 — Test: `pre_gate` enforces the mapped payload (Write→FROZEN/PROTECTED blocked; ADDITIVE allowed).

## CLOSURE

- [x] T-21-08 — preflight green; review ladder (QA + code-review + security) APPROVED on closing tip.
- [x] T-21-09 — CLOSURE.md (incl. trusted-run verification recipe); archive; gated push; CI watched green; drift re-check.
