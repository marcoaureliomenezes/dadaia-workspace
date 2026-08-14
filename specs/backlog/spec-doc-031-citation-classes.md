---
title: "SPEC-DOC-031: distinguish consumption citations from reference citations in archived SPEC/CLOSURE"
status: candidate
opened: 2026-08-14
description: >-
  v0.8.0 CLOSURE backlog return, materialized 2026-08-14. SPEC-DOC-031 scans every
  archived release's SPEC.md and CLOSURE.md line by line for backlog slugs and WARNs
  when a matched slug's entry is non-terminal, excluding only lines inside a
  "## Backlog returns" section (doctor_governance.py:196-224). Any other mention —
  a legitimate inheritance citation (an entry named as inheritor of deferred/
  superseded findings) or an explicit non-goal/out-of-scope citation — raises a WARN
  asserting consumption that demonstrably did not happen. Concrete case: archiving
  v0.8.0 raised exactly 3 such WARNs (consumer-side-validation-round,
  thin-wrapper-projected-scripts, push-range-denylist-scan), all predicted as
  false positives by that CLOSURE (V9). Proposed refinement: also exclude
  out-of-scope/non-goal sections, or key the check on a machine-readable consumed
  set (consumed_backlog.json) instead of free-text slug matching.
intents:
  - subject:
      kind: doc
      ref: memory/product/sdd/specs-doctor.md#Validator Families
    change: >-
      Refine _archive_consumption_hits / check_consumed_backlog_disposition so a
      slug mention only counts as consumption evidence when it is one: either
      restrict matching to consumption-asserting contexts (and exclude non-goal /
      out-of-scope / inheritance sections the way "## Backlog returns" is already
      excluded), or key SPEC-DOC-031 on a machine-readable consumed set
      (consumed_backlog.json) instead of free-text slug matching. The v0.8.0 archive
      must stop producing its 3 documented false-positive WARNs without flipping the
      three cited entries and without editing the FROZEN archive.
---

# SPEC-DOC-031: citation-consumption vs citation-reference

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.8.0/CLOSURE.md` §"Drifts"
(`spec-doc-031-citation-false-positives`) and §"Backlog returns", fourth item
(destination `backlog/candidates.md`).

The v0.8.0 case, on the record: its SPEC cites three `candidate` entries without
consuming any of them — `consumer-side-validation-round` (FR1, inheritor of two
`deferred` consumer-audit findings), `thin-wrapper-projected-scripts` (FR2,
inheritor of W6), and `push-range-denylist-scan` (§4 non-goal 2, an explicit
out-of-scope citation). The correct fix was *not* to flip those entries (the
release picked nothing) and *not* to strip citations from an `Aprovado` SPEC
(that would destroy disposition evidence) — so the +3 WARN delta was predicted
(V9: `0 error(s), 10 warning(s)`) and accepted. This is the ADR-6 false-positive
class the check itself documents (`doctor_governance.py:74`: "SPEC-DOC-031 stays
WARN (never ERR) for this reason").

## Motivation

A WARN that asserts something which demonstrably did not happen trains readers to
ignore WARNs. The check's value (catching consumed-but-unsanitized backlog) is
real; its evidence test (any free-text slug mention outside one excluded section)
is too coarse now that CLOSUREs legitimately cite entries as inheritors and SPECs
legitimately cite entries as non-goals.

## Acceptance criteria

- `dadaia specs doctor` over the current tree reports zero SPEC-DOC-031 WARNs for
  the three v0.8.0 citations, with the three entries still `candidate` and the
  archive untouched.
- A true positive (an archived CLOSURE asserting consumption of a still-live
  entry) still WARNs — covered by a regression test for both citation classes.
- The chosen mechanism (section-class exclusion or consumed_backlog.json keying)
  is recorded in the check's docstring and, if the machine-readable set is chosen,
  wired at release closure.
