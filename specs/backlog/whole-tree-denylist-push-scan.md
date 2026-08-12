---
title: "Whole-tree denylist scan at the push gate — close the specs/ privacy blind spot"
status: candidate
opened: 2026-08-12
description: >-
  Two consecutive releases (v0.6.0 and v0.7.0) leaked the same class of consumer-project
  name into pushed history through the same channel: QA validates on the live instance,
  a doctor/presence line names a foreign context, the author transcribes it into a
  specs/ document. check_public_privacy() only scans dadaia_workspace/public/**, so
  nothing mechanical sees specs/ — both incidents were caught only by the manual
  security diff review and remediated by history rewrites. Per the root-cause doctrine,
  two identical incidents in consecutive releases means the structural fix is owed: the
  pre-push gate scans every NEW object the push would transmit (rev-list --objects
  origin/develop..develop) against the operator privacy denylist plus local repos/
  slugs, failing closed with the offending path:line. Operator decision pending
  (recorded in the v0.6.0/v0.7.0 security handoffs): confirm the scan scope and any
  sanctioned-term exceptions (the two archived backlog files already published).
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#push_gate_decision
    change: >-
      New-object denylist scan wired into the push gate (or the pre-push script chain):
      decode each new blob, match the 18-term denylist + repos/ slugs + absolute-path
      patterns, refuse with path and masked term. Fail-open only on unreadable binary
      blobs, never on matches.
  - subject:
      kind: doc
      ref: quality-assurance.md#Satisfiable Diagnostics
    change: >-
      The refusal must be satisfiable: name the offending blob/line, the redaction law,
      and the sanctioned remediation (edit + history rewrite before push); document the
      exception list mechanism for already-published terms.
---

# Whole-tree denylist scan at the push gate

## Description

See frontmatter. Incident record: v0.6.0 definition push (SPEC named a consumer repo),
v0.7.0 ship push (ALPHA-1-QA transcribed a foreign presence record) — both REJECTED by
the security diff review, both remediated by cherry-pick+amend history rewrites. The
class survives manual review only as long as the reviewer keeps catching it.

## Acceptance criteria

A push containing a new blob with a denylist term is refused locally before any
network I/O; the message names the path and masks the term; the archived already-public
files are exempted explicitly; suite green; the scan adds < 2s to the gate.
