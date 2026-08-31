---
name: dd-architecture-survey
description: >
  Survey a codebase for deepening opportunities, oriented by the measured bug history.
  Produces architecture cards plus exactly ONE top candidate routed to dd-grill-me.
disable-model-invocation: true
---

# dd-architecture-survey

The permanent architecture review as a procedure, not an exhortation. Speaks the
`dadaia-codebase-design` vocabulary (seam, deep module, deletion test). A survey, not
a rescue: it finds and argues candidates; it never edits code.

## 1. When

- The operator or `project-manager` invokes it explicitly.
- At the close of each candidate or release (the `dd-release-implement` cadence).

## 2. Scope before you scan — YAGNI

Deepening pays off by making FUTURE changes easier, so weight the survey toward where
change actually happens:

1. If the operator named a direction (a module, subsystem, pain point), take it and
   skip the inference below.
2. Otherwise, measure — never impressionistic:
   - `dadaia bugs stats` and `dadaia bugs status --all`, aggregated per
     surface/component: re-bug rate, fix-induced `caused_by` edges,
     resolved-without-evidence count.
   - `git log --oneline --since=<window> -- <path>` churn per touched path; join the
     two — the loop lives where re-bugs and churn coincide.
   - The prior survey/audit's dispositions (`specs/audits/_archive/audits_histo.jsonl`)
     — a candidate that recurs across surveys is structural by definition.

## 3. Explore — note where you feel friction

Read the repo's `CONTEXT.md` and the ADRs in the area first. Then walk the hot paths
organically (a sub-agent walks well) and note friction rather than applying rigid
heuristics:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — an interface nearly as complex as the implementation?
- Where were pure functions extracted just for testability while the real bugs hide in
  how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts are untested, or untestable through their current interface?

Apply the **deletion test** to anything suspected shallow: would deleting it
concentrate complexity (a real module) or just move it (a pass-through)?

## 4. Output — architecture cards

One card per candidate, in the shared vocabulary:

- **files** — the cluster's paths.
- **problem** — the duplicated decider / policy-in-transport / missing owner, named.
- **deepening** — what deep module would absorb it (interface sketched in one line).
- **before/after** — one-line sketch of the fold's shape (what gets DELETED).
- **confidence** — `Strong` / `Worth exploring` / `Speculative`.

Then exactly **ONE top candidate**, argued from the cards. When a candidate contradicts
an accepted ADR, surface it only if the friction justifies reopening the decision, and
mark the conflict on the card.

Emission is handoff-first (`dadaia-handoff-emitter`): cards travel in the handoff; the
visual HTML report is added only when the operator asks or the next hop is human —
then follow [`HTML-REPORT.md`](HTML-REPORT.md).

## 5. After the pick — the grilling loop

The top candidate goes to a `dd-grill-me` session before anything is picked — the
survey never decides. During that session, keep the domain model current via
`dd-domain-modeling`:

- A deepened module named after a concept missing from `CONTEXT.md` → add the term.
- The operator rejects a candidate with a load-bearing reason → offer an ADR so future
  surveys don't re-suggest it (skip ephemeral or self-evident reasons).
- Alternative interfaces worth exploring → `dadaia-codebase-design`'s design-it-twice
  pattern.

## 6. Boundaries (ADDITIVE)

- Writes a report (`.dadaia/reports/...`) and/or handoff (`.dadaia/handoff/...`) only.
- A candidate reaches the backlog only through the operator-gated intake.

## 7. Done when

- Cards cover every surface whose re-bug × churn signal is non-trivial in the window.
- One top candidate is named with its evidence; the handoff's next hop is the grill.

## 8. References

- `dadaia-codebase-design` — the vocabulary, the deletion test, design-it-twice.
- `dd-domain-modeling` — glossary/ADR side effects during the grilling loop.
- `dd-grill-me` — the mandatory next hop for the top candidate.
- `dd-audit-project` — the three-pillar audit this survey feeds and complements.
- [`HTML-REPORT.md`](HTML-REPORT.md) — report-mode scaffold, card layout, diagram patterns.
