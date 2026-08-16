---
title: "memory-ctx phantom prefix in _CODEX_SKILL_REF_PREFIXES"
status: candidate
opened: 2026-08-15
description: >-
  v0.10.0 SPEC §4 item 8 (verified in-release): the _CODEX_SKILL_REF_PREFIXES tuple in
  runtime_transforms/codex_assets.py names "memory-ctx", a skill that does not exist in
  public/skills/ — the only memory-ctx asset lives at public/runtime/codex/memory-ctx/
  (a Codex runtime adapter, not a grantable public skill), so the persona skill-ref
  filter whitelists a prefix no persona frontmatter can legitimately carry. Pre-existing;
  v0.10.0's FR13 changed only the two entries its rename required and routed this as a
  PM observation. Fix: remove the phantom prefix (or re-point it at the real asset
  surface if Codex personas are ever meant to reference the runtime adapter), and bind
  the tuple to the actual public/skills/ inventory with a test so a future rename or
  removal cannot leave another dead prefix behind.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py#_CODEX_SKILL_REF_PREFIXES
    change: >-
      Every prefix in the tuple corresponds to at least one skill that exists in
      public/skills/ (or an explicitly documented runtime-asset exception); a unit test
      derives the expectation from the inventory so drift fails loud.
---

# memory-ctx phantom prefix in `_CODEX_SKILL_REF_PREFIXES`

## Description

See frontmatter. Source: v0.10.0 SPEC §4 item 8, routed to the PM as an observation —
pre-approved intake, SPEC §4.8. Consumer of the tuple:
`infrastructure/codex_doctor.py` (skill-ref validation at line ~269).

## Acceptance criteria

- No prefix in `_CODEX_SKILL_REF_PREFIXES` is dead against the `public/skills/`
  inventory (documented exceptions listed inline).
- A test binds the tuple to the inventory; removing or renaming a skill family breaks
  the test until the tuple follows.

## Provenance

Pre-approved intake P-4 (operator ratification at v0.10.0 approval, SPEC §4.8 — "new PM
entry"). Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation — intake report #2
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`software-engineer` (a constant and a test); Arm-B-adjacent, rides any window touching
`codex_assets.py`. Priority P3.
