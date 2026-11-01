# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Design (codebase-design vocabulary)

The audit's structural reading holds for every FR: the release state has one
parser (`core/release_state.py`) and three writers with no reader of archives; the
histories have three shapes and no reader; the doctors are three shallow modules
each measuring a slice. Candidate 1 deepens three seams and deletes the layers
around them.

- **Seam 1 — `validate_release_tree`** (FR1). One function in `features/specs`
  over the existing parser; `rc-archive`, `release archive`, the doctor and one
  contract test are its four adapters. The manual promote lane fails the deletion
  test (its checks reappear in every skill that describes it) and is deleted; the
  verb replaces it (replace, don't layer).
- **Seam 2 — the rule registry** (FR5/FR6). `features/specs/rules.py::RULES`
  already is the one ordered table for the specs doctor; it generalizes to a
  `Rule(code, section, check, fix)` record that `features/spec_context/doctor.py`
  (workspace) and `features/backlog/doctor.py` (ledgers) also contribute to.
  `cli/commands/doctor.py` is the one caller: collect, run, render, score. Two CLI
  commands and their option parsing are deleted. Interface shrinks (one command,
  one grammar, one JSON); implementation concentrates.
- **Seam 3 — `histo-record-v1`** (FR7). One model in `core/models`, one schema,
  one terminal vocabulary constant; three per-file writers become adapters of one
  shape. `features/backlog/ledger.py` and `ConsumedBacklogHistoRecord` have one
  hypothetical consumer and no producer: deleted with their tests.
- **Release verbs** (FR2/FR3/FR4): `release new` and `release archive` are two
  deep verbs with zero optional behavior; `release archive` composes FR2 and
  `bugs archive` inside one transaction (stage in a temp dir, validate, then
  move). Git stays outside the CLI: the verb prints the `next:` lines.
- **Deletions counted against growth:** `specs doctor` + `backlog doctor`
  commands, `ledger.py` + model + store + 2 test files, `_superseded/` lane,
  `segment`/`audited`/`DISCOVERY`/`SPEC`/`PLAN`/`TASKS` phase values, the alias
  table, the tldr category filter, `_record_violations`, `memory-AGENTS.md` twin,
  the provisional `CONSUMED` path and SPEC-DOC-031. Additions: one validator, one
  verb, one field (`closed_at`), one schema, one section grammar.

## Order of work (tracer bullets)

1. FR1 validator + contract test against the real tree (RED on a fixture of the
   pre-Wave-0 0.4.6 document) — first observable slice: the doctor-of-today
   still passes, the test fails.
2. FR5 registry generalization + `dadaia doctor` sections and score lines; delete
   the two commands; the FR1 validator becomes the `specs` section's release
   rule. Slice: one command reports what three did.
3. FR7 model + schema + vocabulary; `ledgers` section validates all five ledgers
   (FR6); migrations one file per commit; delete consumed-histo lane and the
   provisional CONSUMED path.
4. FR2/FR3/FR4: `release new` atomic; `release archive`; schema and phase
   shrink; `closed_at` + back-fill + threshold; `rc-archive` shares validator and
   archive call.
5. FR8 ADR ledger (schema-validate in test, `measured_by` pattern, in-place
   superseded, law text); operator decision on 0004/0010 recorded.
6. FR9 memory hygiene.
7. FR10 law/skills/scaffolds/behavior-map; re-project; `dadaia doctor` green.
8. FR11 closure: memory atoms, CHANGELOG, preflight, CLOSURE.

## Verification

- Full preflight (`ruff format --check`, `ruff check`, `mypy --strict`,
  `lint-imports`, `pytest`) green.
- `dadaia doctor` on this instance: `compliance(total)` 100 %, exit 0; before
  step 3 lands it must report the pre-repair fixtures as findings (kept as unit
  fixtures, not live data).
- The `release archive` transaction is exercised on a fixture tree (unit) and
  refused on a tree with an open task; the first real run happens at this
  release's ship.
- `git diff --stat main...HEAD` for the candidate: production lines net-negative
  or justified per FR against the deletion test in the closure `summary` log.
