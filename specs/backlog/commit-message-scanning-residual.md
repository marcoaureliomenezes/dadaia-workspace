---
title: "commit-message scanning: the residual channel the v0.9.0 blob-only scan leaves open — sized at 59 KB by the first squash-merge"
status: candidate
opened: 2026-08-14
description: >-
  The one known hole left in the channel v0.9.0 closed, recorded deliberately at
  SPEC §4.2 (operator-ratified non-goal, "defer to backlog at closure") and routed
  by the CLOSURE. rev-list --objects lists commits WITHOUT a path and the shipped
  scanner reads blobs only, so a commit message (or annotated tag body) naming a
  private project is published with no refusal. The ship reviews sharpened the
  sizing decisively: the v0.9.0 main-reconciliation range published 0 bytes of
  scannable blob content and 59,263 characters (1,229 lines) of unscannable
  commit-message content — the GitHub squash-merge workflow concatenates every
  commit message of a PR into ONE commit object, so the residual is not "a subject
  line might name a client" but the entire authored narrative of a release in a
  single object the gate structurally cannot see. Scope per the reviewer: scan the
  range's COMMIT OBJECTS (message bodies), including the squash-merge shape and
  annotated tag bodies; for a reconciliation merge the commit objects are the only
  scan target since no blob is published. Both v0.9.0 ranges' bodies were verified
  clean by hand (27 + 2 commits; only the Co-Authored-By tooling trailer matched)
  — the manual check this entry mechanizes.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/container.py#build_git_object_reader
    change: >-
      Extend the reader seam (or build a sibling at the same composition root) to
      yield the commit objects of the pushed range — message bodies, and annotated
      tag bodies for tag refs — through the same batched conversation and
      typed-error contract, so the matcher can scan them like blobs.
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#push_gate_decision
    change: >-
      Feed range commit messages through the same three term layers with the same
      masked, satisfiable refusal shape; the healing action differs (reword/amend
      before push — for local unpublished commits this demands no published-history
      rewrite, same guarantee as the blob scope).
  - subject:
      kind: doc
      ref: memory/product/sdd/sdd-gate-v3.md#Non-Goals
    change: >-
      Retire the blob-only limitation from the gate atom's stated non-goals:
      coverage becomes blob + commit-object; record the squash-merge sizing
      evidence as the motivation.
---

# commit-message scanning — the residual channel

## Description

See frontmatter. Sources, deduplicated into this single entry:

- `specs/_archive/releases/v0.9.0/CLOSURE.md` §"Backlog returns" — the routed
  return ("the one known hole left in the channel this release closed"), owed by
  T-090-12 per SPEC §4.2/§"non-goals".
- Security-reviewer ship handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`
  — INFO "Commit messages remain out of scan scope": 27 bodies verified clean by
  hand for that range; asks the next release to confirm this entry exists so the
  residual does not expire with v0.9.0.
- Security-reviewer reconciliation handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T231057Z-security-reviewer-v0.9.0-main-reconciliation.handoff.json`
  — INFO findings 2 and 3: the 59 KB / 1,229-line squash message fully enumerated
  by hand (103 email occurrences, 1 distinct tooling-trailer value, 0 denylist / 0
  foreign-name / 0 path / 0 secret hits), and the explicit scoping guidance
  ("scope it to include the squash-merge shape explicitly … the scan target for a
  reconciliation merge is the commit objects alone"). Also the methodological
  caution worth carrying into implementation: scan_objects returns at most one Hit
  per object by design, so per-object enumeration semantics need stating for a
  1,229-line message object.

## Motivation

Every push cycle now ends with a security reviewer hand-scanning commit bodies —
the exact class of manual control v0.9.0 was built to mechanize. Under the
squash-merge workflow the channel is the largest single unscanned text the repo
publishes, and after v0.9.0 it is the ONLY unscanned channel on the push path.

## Acceptance criteria

- A denylist term in a range commit message refuses the push with the masked,
  satisfiable diagnostic naming the commit (not a blob path); clean messages pass.
- Squash-merge shape covered: a reconciliation range publishing zero blobs still
  scans its commit objects.
- Annotated tag bodies covered; lightweight tags and deletions unchanged.
- Fail-closed posture and the security-verdict carve-outs unchanged; performance
  stays within the existing budget posture (commit objects are small).

## Ownership

`software-engineer` implements; `security-reviewer` verifies the channel closed in
the covering push review.
