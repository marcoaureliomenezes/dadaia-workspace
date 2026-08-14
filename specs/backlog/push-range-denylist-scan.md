---
title: "Push-range denylist scan at the push gate — close the specs/ privacy blind spot"
status: candidate
opened: 2026-08-12
description: >-
  Renamed from whole-tree-denylist-push-scan on 2026-08-14 (grill ADR #3: the literal
  whole-tree scope is born unsatisfiable over the already-published term; scope is now
  the NEW objects of the pushed range). Two consecutive releases (v0.6.0 and v0.7.0)
  leaked the same class of consumer-project name into pushed history through the same
  channel: QA validates on the live instance, a doctor/presence line names a foreign
  context, the author transcribes it into a specs/ document. check_public_privacy()
  only scans dadaia_workspace/public/**, so nothing mechanical sees specs/ — both
  incidents were caught only by the manual security diff review and remediated by
  history rewrites. Per the root-cause doctrine, two identical incidents in
  consecutive releases means the structural fix is owed: the pre-push gate scans every
  NEW object of the pushed range (git rev-list --objects origin/develop..develop)
  against the operator privacy denylist plus local repos/ slugs, failing closed with
  the offending path:line. Grill 2026-08-14 settled the whole contract — ADRs
  #3/#3b/#4/#5, recorded in the body. Whole-tree scanning survives only in the audit
  lane (project-auditor dispatch), mirroring §6's diff-based-push / full-scan-audit
  split.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#push_gate_decision
    change: >-
      Range-scoped denylist scan wired into the push gate: decode each NEW blob of
      git rev-list --objects origin/develop..develop, match the 18-term denylist +
      repos/ slugs + absolute-path patterns, refuse with path and masked term.
      Tag pushes are covered (grill ADR #4): tags remain exempt from the security
      REVIEW (law §3 intact), but the scan runs over the new objects a tag publishes
      (rev-list --objects <tag> --not --remotes) — today service.py:344 filters tags
      before any policy, so a tag push would publish unscanned objects. Fail-open
      only on unreadable binary blobs, never on matches. New objects carrying a
      denylisted term ALWAYS block — no sanctioned-terms amnesty list (ADR #3b).
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Satisfiable Diagnostics
    change: >-
      The refusal must be satisfiable: name the offending blob/line, the redaction
      law, and the sanctioned remediation (edit + history rewrite before push). The
      SPEC must document the FROZEN↔scan invariant (ADR #3b): specs/_archive/ is
      FROZEN (never edited) and git mv creates no new blob, so tainted archived files
      can never enter a scanned range — the already-published term is amnestied by
      construction, not by exception list. Absorbed FR (ADR #5): redact foreign Spec
      Context names at QA authoring time (doctrine line and/or doctor --redact mode)
      — closes the leak's entry path while the scan closes the exit path.
---

# Push-range denylist scan at the push gate

## Description

See frontmatter. Incident record: v0.6.0 definition push (SPEC named a consumer repo),
v0.7.0 ship push (ALPHA-1-QA transcribed a foreign presence record) — both REJECTED by
the security diff review, both remediated by cherry-pick+amend history rewrites. The
class survives manual review only as long as the reviewer keeps catching it.

## Grill decisions (2026-08-14 refinement report — settled, do not re-litigate)

- **ADR #3 — scope:** new objects of the pushed range
  (`git rev-list --objects origin/develop..develop`); whole-tree stays in the audit
  lane. Entry renamed accordingly.
- **ADR #3b — no amnesty list:** new objects with a denylisted term always block; the
  edge case is void by construction (FROZEN `_archive/` + `git mv` ⇒ no new blob).
  The SPEC documents this FROZEN↔scan invariant.
- **ADR #4 — tags covered:** review-exempt, scan-covered
  (`rev-list --objects <tag> --not --remotes`); closes the `service.py:344` bypass.
- **ADR #5 — absorbed FR:** redaction of foreign context names at QA authoring time
  ships inside this release (see backlog entry
  `redact-foreign-context-names-at-qa-authoring`).

## Acceptance criteria

A push (branch or tag) whose new objects contain a denylist term is refused locally
before any network I/O; the message names the path and masks the term; no amnesty
list exists and the FROZEN↔scan invariant is documented in the SPEC; the
redaction-at-authoring FR ships in the same release; suite green; the scan adds < 2s
to the gate.
