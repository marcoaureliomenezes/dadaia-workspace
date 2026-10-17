# Job 2 — ADR records carry options; the ADR-label guard tolerates old labels (FR2, FR3)

**Status:** Draft

Wave 1. The code half of the ADR change: the record schema and the guard. It edits no canon-fingerprinted law: every `scaffold/*/AGENTS.md` edit and the canon re-pin live in Job 16, which runs after Job 1 so that ONE bump carries both the ADR law and the five schema-path citations (the canon test is red whenever a fingerprinted law changes without its pin, so the law edits and the pin must share a job; moving the pin alone would leave this job's gate red). ADRs 0243 to 0245 are accepted by the operator in the reconcile tree (SPEC governance); nothing here depends on that.

- Status-token transition (PLAN notes): the guard accepts `ADR: NNNN` or `ADR: none` followed by anything, so the 15 `(accepted)`/`(proposed)` labels still in `specs/memory` keep the job gate green; ADR 0245's acceptance commit in the reconcile tree is the strip. The `adr-exists` check stays.
- `decision-record-v1` stays the one validator (`doctor_adr` over `_ledger.validate`): `options` is optional in general and required, by schema, for ids above `0246` (0246 was accepted without it), so every record already in the ledger validates.
- Test-side first: T1. Then T2, T3 in parallel.
- Commit bodies carry `git grep -n -E 'ADR: [0-9]{4} \((proposed|accepted)' -- scripts tests` (target 0 outside the memory tree the Reconciliation strips).
- Pre-review checklist: one validator (no second schema reader); no cross-component import or cycle; sweep line above; no platform fact; net lines ≤ 0 except the schema's `options` (est. +25).

Tasks: 3 (0 jr, 3 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J2.T1 | sr | AC2.2 | `tests/features/specs/test_doctor_adr.py` | RED, unit: a record with id `0247`, status `proposed` and no `options` is refused by `LEDGER-ADR-SCHEMA`; one with two `options` (`name`, `tradeoff`, `rejected_because`) passes; a record with id `0246` and no `options` still passes. Owner `test_doctor_adr.py` |
| J2.T2 | sr | AC2.2, AC2.3 | `dadaia_workspace/public/schemas/ADRs/decision-record-v1.schema.json` | add `options` (array, at least two objects, three required strings each), required by an `if` on the id pattern for ids above `0246`; `ruling.description` states that `words` carries the question and the chosen option in the operator's words and drops the ADR number and the answer-id clause. Owner T1. After T1 |
| J2.T3 | sr | AC3.2 | `scripts/guards/repo.py` | `_ADR_LINE` accepts `ADR: none` or `ADR: ` plus four digits, then any text (trailing text tolerated until the Reconciliation); the `adr-line` message and plants follow; the `adr-exists` plant edits the stable prefix. Owner `python scripts/guards/run.py` and `--planted` exit 0 |
