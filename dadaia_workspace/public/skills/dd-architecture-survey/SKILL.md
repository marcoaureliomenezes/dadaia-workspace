---
name: dd-architecture-survey
description: >
  Operationalizes the operator's standing order "permanent architecture review oriented
  by bug history" as a procedure with defined input and output. User-invoked by the
  operator or project-manager, or at the close of each alpha-N/release. Input: the bug
  ledger aggregated per surface/component joined with git churn. Output: architecture
  cards plus exactly ONE top candidate, which goes to dd-grill-me before any pick.
  ADDITIVE only — never edits code, never materializes backlog.
tldr: "bugs stats × git churn → architecture cards → ONE top candidate → grill; report/handoff only."
disable-model-invocation: true
---

# dd-architecture-survey

The permanent architecture review as a procedure, not an exhortation. Speaks the
`dadaia-codebase-design` vocabulary (seam, deep module, deletion test).

## 1. When

- The operator or `project-manager` invokes it explicitly.
- At the close of each `alpha-N` or release (the `dd-release-implement` cadence).

## 2. Input — measured, never impressionistic

1. `dadaia bugs stats` and `dadaia bugs status --all`, aggregated per surface/component:
   re-bug rate, fix-induced `caused_by` edges, resolved-without-evidence count.
2. `git log --oneline --since=<window> -- <path>` churn per touched path; join the two:
   the loop lives where re-bugs and churn coincide.
3. The prior survey/audit's dispositions (`specs/audits/_archive/audits_histo.jsonl`) —
   a candidate that recurs across surveys is structural by definition.

## 3. Output — architecture cards

One card per candidate, in the shared vocabulary:

- **files** — the cluster's paths.
- **problem** — the duplicated decider / policy-in-transport / missing owner, named.
- **deepening** — what deep module would absorb it (interface sketched in one line).
- **before/after** — one-line sketch of the fold's shape (what gets DELETED).
- **confidence** — `Strong` / `Worth exploring` / `Speculative`.

Then exactly **ONE top candidate**, argued from the cards. The top candidate goes to a
`dd-grill-me` session before anything is picked — the survey never decides.

## 4. Boundaries (ADDITIVE)

- Writes a report (`.dadaia/reports/...`) and/or handoff (`.dadaia/handoff/...`) only.
- Never edits code; never writes `BACKLOG.json` — a candidate reaches the backlog only
  through the operator-gated intake.

## 5. Done when

- Cards cover every surface whose re-bug × churn signal is non-trivial in the window.
- One top candidate is named with its evidence; the handoff's next hop is the grill.

## 6. References

- `dadaia-codebase-design` — the vocabulary and the deletion test.
- `dd-grill-me` — the mandatory next hop for the top candidate.
- `dd-audit-project` — the three-pillar audit this survey feeds and complements.
