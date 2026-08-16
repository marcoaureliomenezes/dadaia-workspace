---
title: "Retire the dead hotfix-release surface (verb, templates, doctor nag)"
status: candidate
opened: 2026-08-12
description: >-
  v0.6.0 revoked the hotfix-release lifecycle (operator ruling D4): bug fixes run on
  hotfix branches with a PATCH mint and no ceremony. The revoked lifecycle's surface
  still ships as dead code and must be removed: the CLI verb, the two Jinja templates,
  and the specs-doctor check that nags for the revoked backlog intake section.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/cli/commands/specs.py#hotfix_app
    change: >-
      Remove the `dadaia specs hotfix open` verb (the hotfix_app sub-app) and its tests —
      never invoked under the v0.6.0 law; product-engineer.md names it dead surface.
  - subject:
      kind: code
      ref: dadaia_workspace/features/specs/doctor_governance.py#GovernanceValidator
    change: >-
      Retire the SPEC-DOC-023 check that requires a '## Hotfixes pendentes' intake
      section in specs/backlog/candidates.md — the intake it polices was revoked with
      the hotfix-release lifecycle.
  - subject:
      kind: catalog
      ref: specs-doctor
    change: >-
      Remove public/templates/release_hotfix.md.j2 and closure_hotfix.md.j2 from the
      shipped template set (manifest + goldens follow); the doctor's template-facing
      checks drop with SPEC-DOC-023.
---

# Retire the dead hotfix-release surface

## Description

See frontmatter. Found by the v0.6.0 six-axis code review (finding 4): the docs now
honestly call this surface dead; this entry is the queued removal those docs cite.

## Acceptance criteria

Verb, templates and SPEC-DOC-023 gone; no doc references them as live; goldens/manifest
regenerated; full suite green.
