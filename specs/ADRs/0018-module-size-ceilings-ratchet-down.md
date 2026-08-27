# ADR 0018 — Module-size ceilings ratchet down

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Two god modules — a 2,830-line specs doctor and a 1,279-line panel API view — were the
erosion a previous release decomposed. The layering contracts constrain *edges*, not line
counts, so nothing structurally prevented the split modules from re-growing back into a
monolith one reasonable edit at a time. The ceiling is a ratchet in the measure-then-pin
tradition this repository already uses: pin what is true now, welcome any lowering, and make
a raise cost a same-commit justification.

## Decision
We will hold the decomposed modules under line-count ceilings that only decrease —
`features/specs/doctor*.py` ≤ 700 lines, `features/panel/views/api*.py` ≤ 450 lines, and the
deleted `api.py` monolith stays deleted so it cannot re-form.

## Consequences
+ Re-growth becomes a visible, justified event rather than the default outcome of many small
  additions.
+ Lowering a ceiling after a further split is a one-constant change that locks the gain in.
− Line count is a crude proxy: a legitimately large module needs an explicit raise with a
  reason, and a file can stay under the ceiling while still being poorly factored.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_module_size_ceiling.py`.
