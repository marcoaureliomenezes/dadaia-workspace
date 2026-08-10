---
name: clean-architecture-remediation
status: OPEN
created: 2026-08-06
origin: operator goal 2026-08-06 (bug-ledger deep audit; report 2026-08-06T210000Z-bug-ledger-architecture-audit.html)
owner: project-manager (curates)
intents:
  - subject: { kind: doc, ref: "memory/architecture.md#Overview" }
    change: "CONSUMED — v0.3.0: operator chose DEMOLISH; the engine was deleted entirely (−61,883 lines)"
  - subject: { kind: doc, ref: "memory/architecture.md#Overview" }
    change: "SUPERSEDED — v0.3.0: the retry/bounded-revision machinery died with the engine demolition"
  - subject: { kind: doc, ref: "memory/architecture.md#Primary Subsystems" }
    change: "CONSUMED — v0.3.0: public_assets de-flagged into InstallPlan + flag-free step pipeline (16→1 private bools)"
  - subject: { kind: code, ref: "dadaia_workspace/core/specs_resolver.py#resolve_bound_context_name" }
    change: "one resolution rung: finish what v0.1.77 started, delete the accreted ladder + 5 env-vars"
  - subject: { kind: doc, ref: "memory/quality-assurance.md#Root Cause, Always" }
    change: "conduct law: additive-only fixes require explicit justification; family recurrence REOPENS the original bug"
---

# Backlog — clean-architecture remediation (bug-ledger audit disposition)

## Evidence base (full detail in the audit report + dataset)

- Report: `.dadaia/reports/dadaia-workspace/project-auditor/2026-08-06T210000Z-bug-ledger-architecture-audit.html`
- Dataset: `.dadaia/tmp/project-auditor/20260806/bug_audit_data.json`
- Headline numbers: 416 bugs; lifecycle cluster 200 (48%); median reported→resolved
  **25 min**; median resolved→same-family-re-report **0.48 day** (239 measured
  recurrences); fix-ratio 96% in `features/lifecycle/`, 95% in `hooks/`; every sampled
  bug-fix was net-ADDITIVE; every surface DELETION (v0.1.53 purge, v0.1.57 dedup,
  v0.1.75 test rearchitecture, v0.1.76 NO-LOCKS) went quiet afterward.

**The empirical law this backlog operationalizes: deleted surface stops producing
bugs; surface added by a fix produces the next bug in under a day.**

## Item 1 — DECISION: fate of dadaia-workflows (blocks items 2)

The subsystem is fully present on main (~20,700 production LOC; 493 test functions =
29.5% of the suite; 289 of 416 bugs). Options, both mapped:

- **Demolish** (operator's stated preference; precedent: NO-LOCKS v0.1.76): removal
  surface is fully mapped in the audit census §6 — container (~20 import sites), CLI
  (4 verbs, 1,378 LOC), panel views (968 LOC), 5 internal doctors, adapters (~2,950
  LOC), 7 import-linter entries, certification checks, fragments+personas assets,
  DADAIA.md §1 rewrite, 25 memory atoms, 12 skills. One dedicated demolition release.
- **Freeze**: mark the 4 verbs experimental/unsupported, stop accepting bugs against
  them (auto-defer), no further fixes. Cheaper, but keeps 29.5% of the suite paying
  rent on a frozen subsystem.

Not an option per the data: continuing to fix (the 96%-fix-ratio loop).

## Item 2 — retry-machinery demolition (only if Item 1 = freeze/keep)

`_fragment_gate.py` (1,226 LOC, 47 retry/revision mentions) + `pipeline.py` (1,289,
47): four generations of mechanism-fixing-mechanism (blind retry → revision brief →
bounded digest → digest compaction). Replace with: single attempt, fail-loud with the
worker's full diagnostic, operator-driven resume. Delete the bounded-revision loop.

## Item 3 — de-flag `public_assets.py`

18 boolean parameters + 21 compat/legacy/fallback mentions in one 1,498-line class —
the same accretion signature lifecycle had before it exploded. Direction: split
install() into flag-free sequential steps; each step takes data, not booleans;
`force`/`scope`/`only`/`overlay` become explicit step selection at the CLI boundary.

## Item 4 — one context-resolution rung

`specs_resolver.py` grew 5.2× (71→368) one rung per bug; `ctx_inject.py` 3.1× with 5
env-var reads. v0.1.77 declared "one resolution path for every verb" and both files
kept growing after it. Finish it: a single resolution function, delete the ladder,
collapse the env-vars to `DADAIA_CONTEXT` alone.

## Item 5 — conduct law (DADAIA.md §6 amendment)

Two sentences of law, enforced as review discipline:

1. A bug fix that only ADDS code (no deletion, no consolidation) carries an explicit
   justification of why removal was impossible — reviewers reject additive-by-default.
2. A recurrence in the same family REOPENS the original bug (new `reported` event
   referencing it) instead of minting a fresh id — the 387 "resolved" ledger stops
   overstating closure.

## Item 6 — deferred-debt triage

12 deferred bugs, 4 older than 50 days (memory-heading-allowlist, context-dead
non-writable guard, spec-doc-029 false forgery, context-dead plain-git-push) +
gate-self-blocks-lease-holder (41d — likely obsolete post-NO-LOCKS: verify and close
or reopen). Each gets a terminal disposition with a reason.

## Interactions

- The in-flight verifier-integrity release (typed DoctorReport, install ledger,
  attesting checks, workspace_layout authority) already disposes recurrence chains #5
  and #7 by deletion — do not duplicate.
- Item 1's demolition release, if chosen, subsumes Item 2 and most of the lifecycle
  open/deferred bugs (supersession events, per release-governance).

## Acceptance (audit-disposition law)

Every audit finding above reaches a disposition (fixed/superseded/deferred-with-reason)
in the first release picked from this entry; the audit archives only when that release
is approved and referenced.
