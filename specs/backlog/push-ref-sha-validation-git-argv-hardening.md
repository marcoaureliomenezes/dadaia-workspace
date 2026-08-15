---
title: "push-gate stdin sha validation + `--` end-of-options at the git argv boundary (CWE-88/CWE-20)"
status: candidate
opened: 2026-08-14
description: >-
  Materializes a LOW from the APPROVED v0.9.0 ship security review.
  parse_push_stdin builds PushRef with no shape check on either sha;
  _is_resolvable_commit interpolates it into `git cat-file -e {sha}^{commit}` and
  _rev_list_candidates into `git rev-list --objects {local_sha} --not
  {remote_sha}` / `--not --remotes`, with no `--` end-of-options marker anywhere.
  Most option-shaped values fail safe (they error into GitObjectReadError and
  refuse, or over-scan) — but the reviewer measured one class that does NOT: an
  option-shaped local_sha like `--glob=refs/nonexistent` or `--branches=zzz`
  yields a SUCCESSFUL EMPTY rev-list (rc=0, zero output), so the denylist scan
  silently no-ops for that ref instead of failing closed; the security-verdict
  check would then be the only remaining gate, satisfiable by the same actor since
  handoff paths are ADDITIVE. LOW, not a blocker, because the stdin is written by
  git itself on the local machine and reaching it requires the same privilege as
  the sanctioned --no-verify bypass — the gate's threat model is accident, not a
  local adversary. The finding is hardening: the gate's stated posture is
  fail-closed on anything it cannot parse (malformed line COUNTS already refuse),
  and an unvalidated sha is precisely something it cannot parse.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#parse_push_stdin
    change: >-
      Validate both shas against ^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$ (plus the
      all-zero deletion sentinel) and count a violation as a malformed line — the
      fail-closed path already exists and needs no new message.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#_rev_list_candidates
    change: >-
      Append `--` after the revision arguments so no sha can ever be parsed as an
      option, defence in depth behind the parse-time validation.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#_is_resolvable_commit
    change: >-
      Prefix-check the sha before interpolation into `git cat-file -e
      {sha}^{commit}` (same validated shape), closing the remaining argv
      interpolation site.
---

# push-gate sha validation + git argv hardening

## Description

See frontmatter. Source — the APPROVED pre-push security handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`,
LOW finding "CWE-88/CWE-20: pre-push ref shas reach git argv unvalidated"
(`service.py:182`; `git_objects.py:69,77,79`), with the empirical demonstration
of the silent-no-op class reproduced in-repo. Explicitly routed to the PM in
`decisions_required` (both the ship and the reconciliation handoffs); this entry
is that routing.

## Motivation

The only input class that turns the scan from fail-closed into a silent no-op.
Cheap, mechanical, test-pinnable; same Arm-B hardening lane as
`python-env-interpreter-probe-hardening` (#9) and
`commit-paths-index-scope-hardening` (#18) — the natural rider for the next
hotfix/patch window touching the chokepoints or git-subprocess surface.

## Acceptance criteria

- A non-sha-shaped local_sha or remote_sha on the pre-push stdin refuses as a
  malformed line (unit tests, including the measured `--glob=`/`--branches=`
  shapes); the all-zero deletion sentinel still parses.
- `_rev_list_candidates` argv carries `--` after revisions; `_is_resolvable_commit`
  rejects non-sha input before interpolation.
- Existing gate behavior on well-formed pushes byte-identical (contract tests
  green).

## Ownership

`software-engineer` implements; `security-reviewer` verifies the finding closed in
the covering push review.

## Intake adjudication (ADR #15 — report #1)

**APPROVED** — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation. Adjudicated via intake report #1
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T132600Z-intake.html`).
The entry remains a live pickable candidate.
