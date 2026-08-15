---
title: "self-scan sentinel carries only pytest.mark.slow — add the integration marker so future selector changes cannot silently drop it"
status: picked
opened: 2026-08-14
description: >-
  Materializes a LOW from the round-2 code review of v0.9.0.
  tests/integration/test_repo_self_scan.py:85 declares pytestmark with
  pytest.mark.slow only, while six of seven sibling modules in tests/integration/
  declare pytest.mark.integration. Today's gating selector is -m "not quarantine",
  so the sentinel does run (the reviewer confirmed it passes in the
  affected-module run) — the risk is forward-looking: a SENTINEL's entire value is
  that it ALWAYS runs, and any future adoption of -m integration selection would
  silently drop the one test that pins "this repository's own pushable tip scans
  clean". One-line fix; folded into any release or hotfix that touches tests/ or
  the chokepoints surface — kept as its own entry so the routing does not
  evaporate (the lesson of python-env-interpreter-probe-hardening, which needed
  three materialization passes).
intents:
  - subject:
      kind: code
      ref: tests/integration/test_repo_self_scan.py#pytestmark
    change: >-
      Add pytest.mark.integration alongside slow, matching the sibling modules,
      so the sentinel survives any marker-based selector the suite adopts later.
---

# self-scan sentinel: add the integration marker

## Description

See frontmatter. Source — code-reviewer round-2 handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`,
LOW finding "The sentinel test carries only pytest.mark.slow, not the
[integration, slow] pair its siblings use".

Deliberately NOT folded into `test-suite-remediation-stewardship` (#2): that
entry is a large, operator-scoped remediation release with its own measured
baseline; this is a one-line marker fix that should ride the first window
touching the surface, independent of #2's schedule.

## Acceptance criteria

- `pytestmark` carries both `integration` and `slow`; the sentinel is collected
  under `-m integration`, `-m slow`, and the current `-m "not quarantine"`
  selectors.

## Ownership

`software-engineer` executes (test-marker changes are implementer surface;
no stewardship verdict needed — nothing is deleted, skipped, or disabled).

## Intake adjudication (ADR #15 — report #1)

**APPROVED** — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation. Adjudicated via intake report #1
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T132600Z-intake.html`).
The entry remains a live pickable candidate.

## Pick provenance (v0.11.0)

**picked — v0.11.0**, 2026-08-15. Delivered inside **FR3** of release `v0.11.0` "scan-v2"
(acceptance A3.5). Provenance record: `specs/releases/v0.11.0/SPEC.md` §7. This is the
"first window touching the surface" the entry was waiting for: task T-110-12 rewrites
`tests/integration/test_repo_self_scan.py` to extend the sentinel's scope to `tests/**`, so
the marker fix rides that exact write set rather than racing it from a second task.
Deliberately **still not** folded into `test-suite-remediation-stewardship` (#2), which is
not picked. Terminal disposition `DELIVERED — v0.11.0` lands at closure.
