# PLAN — Release v0.1.81 — Deprecation strips & doctor cleanup

**Status:** Aprovado

T-1 FR1 strip (TDD: flip the AC-6 tolerance test to RED-as-unknown-key first, then
strip) → T-2 FR2 doctor invariant (TDD: RED fixture of an artifact-empty archived
release dir) → T-3 validation + ship gates. Small, disjoint surfaces. The operator's
date-gate waiver is recorded in the SPEC header and travels into CLOSURE + the
backlog entry's disposition.
