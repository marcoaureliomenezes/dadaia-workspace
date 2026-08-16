---
title: "Consumer-side validation round — prove the assembled consumer journey on a real workspace"
status: candidate
opened: 2026-08-14
description: >-
  Created by grill ADR #1 (2026-08-14 refinement report) as the inheritor of the two
  external findings of the consumer audit (2026-07-15) that this repo cannot close from
  the provider side alone. Both findings were dispositioned `deferred` — `rejected`
  would contradict the §6 approval law ("a candidate is approved when the operator and
  the consumer-side validation agent agree, after validating a real workspace"), and
  leaving them pending would block every future pick under §5 precedence. The audit
  archives citing this entry. The work: run a full consumer-side validation round on a
  real (disposable) consumer workspace against the current provider surface, with the
  two inherited findings as its acceptance criteria.
intents:
  - subject:
      kind: catalog
      ref: consumer-agent-support
    change: >-
      A consumer-side validation round on a real disposable workspace certifies the
      assembled consumer journey through supported interfaces only, closing the two
      inherited audit findings: (1) the consumer prompt/tests must consume the
      installed version-matched skill/capability surface and exercise canonical
      workflow verbs — no preserved references to removed lifecycle commands; (2) the
      consumer owning repository must be governance-coherent — one-task-at-a-time
      markers, valid memory/schema state, immutable release evidence.
---

# Consumer-side validation round

## Description

See frontmatter. Provenance: `specs/audits/2026-07-15-consumer-dadaia-integration.md`,
findings #3 and #6 (both HIGH), dispositioned `deferred` by the operator in the
2026-08-14 grill (ADR #1) and inherited here as acceptance criteria:

- **#3 — "Consumer prompt and tests preserve removed lifecycle commands."** Required
  disposition: consume the installed version-matched skill/capability surface and test
  canonical workflow verbs.
- **#6 — "The Consumer owning repository is governance-incoherent."** Required
  disposition: restore one-task-at-a-time markers, valid memory/schema state, and
  immutable release evidence before certification.

Both live outside this repository's write surface — they can only be proven closed by a
validation round executed on the consumer side, which is exactly the §6 approval model.

## Acceptance criteria

A real (disposable) consumer workspace is validated end-to-end through supported
interfaces; finding #3 and finding #6 are each proven closed with automated,
consumer-side evidence; the round's report/handoff is emitted; no provider-side gate is
weakened to make the round pass.
