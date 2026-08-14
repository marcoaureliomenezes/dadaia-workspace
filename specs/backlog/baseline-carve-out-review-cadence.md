---
title: "privacy-baseline pattern versioning + carve-out review cadence (three reactive exclusions in one release)"
status: candidate
opened: 2026-08-14
description: >-
  v0.9.0 CLOSURE "Backlog returns" item, included at the PE's judgement because
  the drift it generalizes is a class, not a one-off. The RFC-2606 reserved-TLD
  gap was found only by the baseline refusing legitimate synthetic content on its
  first real run — by accident of timing, not by review — and the release then
  added three carve-outs reactively (RFC-2606 emails, the product's own
  workspace.local identity in two patterns, the stdlib Path.home call forms),
  taking privacy_baseline.json from v1 to v4 in one cycle. There is no defined
  moment at which the six patterns and their exclude_regex carve-outs are
  re-examined against the reserved/synthetic-value RFCs. The round-2 code review
  named the underlying treadmill: internal-hostname treats ANY dotted identifier
  chain ending in local|internal|lan|intranet|corp|home as a hostname, so
  `<name>.local`, `<attr>.internal`, `<x>.home` and every future equivalent will each
  demand another literal exclusion — the false-positive class is unbounded while
  carve-outs are literal-by-literal. Candidate shapes from the routing: a periodic
  review lane; a doctor check flagging baseline patterns lacking a documented
  carve-out rationale; and (from the review) a structural fix for the
  dotted-chain class instead of a fourth literal. A constraint to preserve,
  recorded in the CLOSURE accepted-without-action list: baseline patterns must
  stay single-line (the push scan matches line-by-line while the public-privacy
  doctor matches whole text).
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/privacy_check.py#load_baseline_patterns
    change: >-
      Give the baseline a reviewable shape: each pattern carries a documented
      rationale for every exclude_regex carve-out, and a doctor/CI check flags
      patterns lacking one; version history stays in the JSON.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/privacy_check.py#_scan_text_for_baseline
    change: >-
      Structural fix option for the internal-hostname dotted-chain false-positive
      class (require hostname-ish context, or exclude chains whose preceding label
      is a capitalised identifier), replacing the literal-by-literal treadmill;
      paired counter-fixtures keep proving narrowness.
  - subject:
      kind: catalog
      ref: sdd-gate-v3
    change: >-
      Record the cadence as product truth: when the baseline is re-examined, what
      triggers a version bump, and the single-line pattern constraint. If baseline
      v5 is ever opened, evaluate the reviewer suggestion of a per-scan deadline
      that fails CLOSED.
---

# baseline pattern versioning + carve-out review cadence

## Description

See frontmatter. Sources, deduplicated into this single entry:

- `specs/_archive/releases/v0.9.0/CLOSURE.md` §"Backlog returns" — the routed
  return; plus the two accepted-without-action constraints this entry inherits
  (single-line patterns; the ReDoS residual bounded by the 5 MB cap).
- Code-reviewer round-2 handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`
  — INFO "the internal-hostname false-positive class … is unbounded": three
  exclusions added reactively in one release; recommends a structural fix when the
  related amnesty item is picked. The sentinel bounds the class for
  dadaia_workspace/ + specs/, "but the treadmill is a maintenance cost the next
  release will pay again".
- Security-reviewer ship handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`
  — INFO carve-out abuse analysis (each v4 carve-out proven anchored and narrow;
  the per-scan fail-closed deadline suggestion for a future v5); INFO on RFC-2606
  breadth (the carve-out swallows local part and subdomain — a narrowing candidate
  for the cadence to weigh: bare <label>.<reserved-tld> shape).

## Motivation

Every baseline false positive that survives to a real push trains the
`--no-verify` bypass; every reactive carve-out under close pressure is a risk of
over-widening. A defined review moment converts both into scheduled, evidenced
work. Cross-references: `prior-published-term-amnesty` (owns the structural-fix
timing), `denylist-scan-skip-note-oversized-mislabel` (same control surface).

## Acceptance criteria

- A defined cadence exists (release-closure step, doctor check, or audit-lane
  item) and ran at least once, producing a dispositioned review of all six
  patterns and every carve-out.
- Every exclude_regex carries a documented rationale, mechanically checked.
- Decision recorded on the dotted-chain structural fix and on the RFC-2606
  narrowing (adopt or reject with reason).
- Single-line pattern constraint stated mechanically or in the atom.

## Ownership

`software-engineer` (check + baseline shape) with `security-reviewer` as the
review authority for pattern changes; cadence placement is a `product-engineer`
call at pick time.
