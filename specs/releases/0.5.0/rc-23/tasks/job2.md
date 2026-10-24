# Job 2 — the ADR proposal (FR7)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`. Design: PLAN section 1 (R15) and section 3 (the operator question). Wave 1; the only job whose work is already committed.

The record is ADR 0281, `status: proposed`, appended in the `wt-rc` define step by the commit `docs(adr): propose multi-harness-eval-deploy-gate` (shape 2 of `dd-gitflow-default` section 3a), before the PLAN commit. The title, the six-clause decision and the relations are SPEC FR7's text; the record adds the context, the consequences and four options.

Two facts the record carries that the SPEC does not state:

- `supersedes` and `amends` are `null` in the proposal. `doctor` (`LEDGER-ADR-SCHEMA`, `dadaia_workspace/features/specs/doctor_adr.py:184-189`) refuses a proposed record that names an accepted one ("only a ruled record changes a ruled one"). The consequences text names the relations (supersedes 0269 and 0277, amends 0217, mechanizes 0178 (1) and (5), subsumes 0225), and the operator's acceptance commit writes the fields: `supersedes` `0269,0277`, `amends` `0217`, and a separate `docs(adr): reject` for 0225.
- `measured_by` is `null` until acceptance; the check it names then is the `Eval gate` rows of `tests/e2e/test_evals_gate.py` (Job 7) and the `no-model-api-in-ci` planted rows (Job 6).

| task | who | AC | `W:` | waits on | tests | outcome |
|---|---|---|---|---|---|---|
| J2.T1 | sr | AC7.1 | `specs/ADRs/decisions.jsonl` | - | `doctor` `LEDGER-ADR-SCHEMA` reports no finding for the record (run on the define tree: zero hits) | done in the define step: record 0281 proposed; acceptance is the operator's and is not a task (PLAN section 3) |

**Definition of done.** `git show --stat` of the define commit found by `git log --grep "propose multi-harness-eval-deploy-gate"` lists only `specs/ADRs/decisions.jsonl` with one inserted line; `doctor --specs-dir specs` prints no `LEDGER-ADR-SCHEMA` line.
