---
title: "foreign-name scan layer derived from repos/ directories only: a DEAD or relocated context contributes no term"
status: candidate
opened: 2026-08-14
description: >-
  Materializes a LOW from the APPROVED v0.9.0 ship security review — a structural
  coverage gap in FR3 term source 3, not a defect against the SPEC as written.
  _foreign_repo_slugs (cli/commands/ci.py:226-241) enumerates <workspace>/repos/
  subdirectory names only; the registry .dadaia/states/spec_contexts.json is never
  read. A Spec Context that is registered but whose repo directory is absent — a
  DEAD or relocated context — therefore contributes no term and is invisible to
  the push-range scan. The gate's foreign-name protection silently SHRINKS exactly
  when an operator archives or removes a repo directory — which is when the name
  becomes MORE sensitive, not less. Demonstrated by the reviewer: re-running the
  shipped matcher over the same 71 ship blobs with the wider registry set (11
  terms vs the gate's 6) produced 2 hits the gate would not produce, both from a
  DEAD context's name (verified pre-existing since v0.1.x, identical at base and
  tip, 0 occurrences in added lines — evidence of the gap, not a leak of that
  delta). Fix per the reviewer: widen the layer to {registry names} ∪ {registry
  repo_slugs} ∪ {repos/ directory names} − {own context name, own slug}, read
  through a container seam exactly as the denylist and baseline are read today.
  Sequencing caution: the layer becomes strictly larger, so land it AFTER (or
  with) prior-published-term-amnesty, with a latent-blocker enumeration first —
  the reviewer's 2 wider-set hits are themselves prior-published content that
  would become one-time blockers. At delivery, the gate atom's term-layers
  description moves from directory-derived to registry-derived (a DEAD context
  keeps protecting its name).
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/cli/commands/ci.py#_foreign_repo_slugs
    change: >-
      Derive the foreign-name set from the union of registry names, registry
      repo_slugs, and repos/ directory names, minus the pushing repo's own context
      name and slug; DEAD contexts contribute their terms. Read the registry
      through a container seam mirroring load_denylist_terms /
      load_denylist_baseline_patterns.
  - subject:
      kind: code
      ref: tests/integration/test_repo_self_scan.py#_NO_FOREIGN_SLUGS
    change: >-
      Keep the sentinel's deterministic empty-slug set (its documented determinism
      filter is unchanged by this entry), and run a one-off wider-set enumeration
      when landing the change to surface pre-existing latent blockers before they
      block a real push.
---

# registry-derived foreign-name set

## Description

See frontmatter. Source — the APPROVED pre-push security handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`,
LOW finding "Coverage gap in FR3 term source 3" with the four-way verification
that the 2 wider-set hits are historical content, plus the fix and sequencing
recommendation. Routed to the PM in `decisions_required` (restated by the
reconciliation handoff `2026-08-14T231057Z-…-main-reconciliation`); this entry is
that routing.

The 2 hits live in `specs/bugs/bugs.jsonl`, resurfacing only because that file
republishes itself wholly on every append — the cost driver tracked separately as
the idea `bugs-jsonl-whole-blob-per-append`.

## Motivation

The scan exists because context names leaked twice; the current layer forgets a
name at exactly the lifecycle moment (context death/archival) the leak risk
peaks. P2: it is a real coverage hole in the shipped privacy control, but gated
behind the amnesty item to avoid converting historical content into new
one-time blockers.

## Acceptance criteria

- A DEAD registry context's name and slug refuse a push that introduces them in
  new content (unit + integration over a real registry fixture); the pushing
  repo's own name/slug never enter the set.
- Registry read goes through the container seam; the CLI still never imports
  infrastructure directly (import-linter contracts kept).
- Pre-landing enumeration of latent blockers executed and dispositioned
  (amnesty in place, or explicit accept list recorded at pick time).
- Self-scan sentinel determinism unchanged.

## Ownership

`software-engineer` implements; `security-reviewer` verifies the widened layer in
the covering push review. Sequenced with `prior-published-term-amnesty`.
