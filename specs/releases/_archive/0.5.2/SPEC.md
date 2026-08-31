# SPEC — Release: 0.5.2

**Status:** Aprovado
**Release ID:** 0.5.2
**Owner:** product-engineer
**Opened:** 2026-08-31

> Approval provenance: operator `/goal` order 2026-08-31 — "define a release and implement
> fully the 32 findings found" — names the scope and authorizes definition+implementation
> directly. The `dd-grill-me` pre-SPEC session is satisfied by that direct order (recorded
> deviation); this is the `20260827-canon-v6-first-audit` remediation release (§6.8: one
> audit → one remediation release).

---

## 1. Problem and context

- `specs/audits/20260827-canon-v6-first-audit/FINDINGS.jsonl` holds 41 findings; 32 remain `disposition: open`.
- §6.7: undispositioned audits outrank fresh backlog — they block the pick lane.
- Re-measurement at HEAD (17390c19): 14 of the 32 were already remediated by the 0.5.0/0.5.1 arc, 11 need evidence-carrying terminal dispositions (history-immutable / pass-records / structurally-superseded), 7 need real implementation.

## 2. Objective

Disposition all 32 open findings of `20260827-canon-v6-first-audit` — implementing every live defect, evidencing every already-fixed one — leaving the audit fully dispositioned and archived.

## 3. Scope

### 3a. Implementation (live defects)

| Finding | Work |
|---|---|
| F010 | `core/bug_provenance.py` — a conformant shape-1 registration (BUGS.jsonl alone) must derive `exact` registration granularity, not `ledger-only`; TDD |
| F015+F036 | pre-commit advisory (WARN-only, NO-LOCKS): staged set mixing `BUGS.jsonl` with other `specs/**` paths gets one warn line naming FR8 isolation; TDD |
| F016 | `dd-gitflow-default` §4 gains shape 6 — the ordinary task commit (`conventional-commit(task-id)`), closing the 39% classification gap; lib edit + reprojection |
| F001+F003 | ledger lineage corrections via `dadaia bugs update` (`caused_by` is mutable-governance): certify-skip-detail → parent probe-gate bug; frozen-clock-ratchet → parent no-ratchet bug |
| F033 | one-shot `vulture` dead-code measurement in an isolated venv (no new project dependency); result recorded in the disposition |
| F041 | `specs/memory/QUALITY.md` P-21 Measured-by selector tightened to the three timeout assertions (CLOSURE-phase memory edit) |

### 3b. Evidence dispositions (no code)

- Already fixed by 0.5.0/0.5.1 (cite evidence): F002, F006, F009, F013, F017, F018, F020, F021, F022, F037.
- Superseded by canonical restructure: F005 (metric 8 re-based commit-derived), F008 (granularity machinery), F019 (release-state-v1), F028/F029/F039 (ADR canon v2, decisions.jsonl, operator-accepted 0001–0003).
- Rejected with reason: F007, F014, F023 (immutable history), F011 (immutable-core `surface`, closed enum), F035 (inherent to append-model, NO-LOCKS), F012, F025, F032 (pass observations — no defect).

### 3c. Closure

- Rewrite all 32 records' `disposition/release/reason` in place (mutable-governance), `release: "0.5.2"`.
- Audit fully dispositioned: summary appended to `specs/audits/_archive/audits_histo.jsonl`; directory removed per DADAIA.md §6.8 (history stays in git).
- Closure narrative in `RELEASE.json` `log`; memory update (F041) in CLOSURE phase.

### 3d. Bugs picked (Arm-B rider, bug-always-solved)

- `backlog-new-append-reported-as-created` (open, LOW) — fixed in-release, commit shape 3.

## 4. Out of scope

- The 17 findings of `20260830-design-bug-surface-audit` (its own remediation release, later).
- The 6 design-audit backlog entries (PM intake pending). **Consumes:** line intentionally absent — no backlog item consumed.
- Publication (PyPI/tag) and the ship PR ceremony — operator-gated.

## 5. Dependencies and risks

- Ledger corrections ride `dadaia bugs update` (refuse-stale seam) — rerun on race.
- Reprojection after the lib skill edit must leave `dadaia public doctor` `[ok] public-privacy`.
- Law contradiction found during definition (audits AGENTS.md "never delete" vs DADAIA.md §6.8 "directory is deleted"; stale projected releases/AGENTS.md) — registered as bugs, fixed on the branch (Arm B), not release material.
