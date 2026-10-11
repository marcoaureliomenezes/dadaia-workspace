# Job 2 — ADR law: threshold, options, self-contained ruling, status only in the ledger (FR2, FR3)

**Status:** Draft

Wave 1. The only job that edits canon-fingerprinted law (`scaffold/*/AGENTS.md`): the canon pin and the shipped-hash history change together in T6, last; no other job of this candidate touches the canon (ADR 0246 changes no law text). ADRs 0243 to 0245 are accepted by the operator before the Reconciliation (SPEC governance); the code and law here do not depend on the acceptance commit.

- Status-token transition (PLAN notes): the guard accepts `ADR: NNNN` or `ADR: none` followed by anything, so the 15 `(accepted)`/`(proposed)` labels still in `specs/memory` keep the job gate green; the Reconciliation strips them in 0245's acceptance commit. The `adr-exists` check stays.
- `decision-record-v1` stays the one validator (`doctor_adr` over `_ledger.validate`): `options` is optional in general and required, by schema, for ids above `0245`, so every record already in the ledger validates (ADR 0246 is a legitimate exception recorded in its own text).
- Mirrors `specs/{ADRs,memory,releases}/AGENTS.md` are refreshed by `dadaia specs upgrade --specs-dir specs` run in the job tree, never by hand; the commit body names it.
- Test-side first: T1. Then T2, T3, T4, T5 in parallel; T6 last.
- Commit bodies carry `git grep -n -E 'ADR: [0-9]{4} \((proposed|accepted)' -- dadaia_workspace scripts tests` (target 0) and `git grep -c 'ADR [0-9]\{4\}' -- dadaia_workspace/public/scaffold` (target 0).
- Pre-review checklist: one validator (no second schema reader); no cross-component import; sweep lines above; no platform fact; net lines ≤ 0 except the schema's `options` (est. +25).

Tasks: 6 (0 jr, 6 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J2.T1 | sr | AC2.2 | `tests/features/specs/test_doctor_adr.py` | RED, unit: a record with id `0247`, status `proposed` and no `options` is refused by `LEDGER-ADR-SCHEMA`; one with two `options` (`name`, `tradeoff`, `rejected_because`) passes; a record with id `0246` and no `options` still passes. Owner `test_doctor_adr.py` |
| J2.T2 | sr | AC2.2, AC2.3 | `dadaia_workspace/public/schemas/ADRs/decision-record-v1.schema.json` | add `options` (array, at least two objects, three required strings each), required by an `if` on the id pattern for ids above `0246`; `ruling.description` states that `words` carries the question and the chosen option in the operator's words and drops the ADR number and the answer-id clause. Owner T1 |
| J2.T3 | sr | AC2.1, AC2.3, AC3.2 | `dadaia_workspace/public/scaffold/ADRs/AGENTS.md` | the three-leg threshold in one line (a one-way door, architecturally significant, at least two genuine options; a decision failing a leg lives in its scoped law line or the SPEC); the `options` field in §1; §2: the ruling's `words` are the question and the chosen option, never only an answer id; delete the grill-answer-id clause, the `ADR:` line of §5 and the §5.1 label clauses (the pairing rule stays), and the ADR-number cites. Net lines ≤ 0. No test; reviewer sweep |
| J2.T4 | sr | AC3.2 | `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-MEMORY.md` | the memory law's principle line becomes `Measured by:` / `Rationale:` with an optional `ADR: NNNN` or `ADR: none` that carries no status; delete the label clause of pillar 3 (the missing-`Measured by:` finding stays); delete the ADR-number cites of the releases scaffold. No test; reviewer sweep |
| J2.T5 | sr | AC3.2 | `scripts/guards/repo.py` | `_ADR_LINE` accepts `ADR: none` or `ADR: ` plus four digits, then any text (trailing text tolerated until the Reconciliation); the `adr-line` message and plants follow; the `adr-exists` plant edits the stable prefix. Owner `python scripts/guards/run.py` and `--planted` exit 0 |
| J2.T6 | sr | AC2.1, AC3.2 | `specs/ADRs/AGENTS.md`, `specs/memory/AGENTS.md`, `specs/releases/AGENTS.md`, `dadaia_workspace/core/specs_version.py`, `dadaia_workspace/public/templates/shipped-hashes.json` | refresh the three mirrors with `dadaia specs upgrade --specs-dir specs` in the job tree; re-pin `CANON_AT[12]` (canon 12 is unpublished: `test_a_canon_change_bumps_the_stamp` computes the digest) and append the new digests of the edited scaffold laws to `shipped-hashes.json` (`test_shipped_history_records_every_current_scaffold_law`). Last task. After T3, T4 |
