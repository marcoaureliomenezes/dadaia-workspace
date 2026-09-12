# TASKS — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Candidate 1 — records tell the truth

- [x] T-047-01 — FR1: `validate_release_tree` in `features/specs` over
  `core/release_state`; contract test `tests/contract/test_release_tree_canon.py`
  runs it on the real `specs/` tree and on a fixture reproducing the pre-Wave-0
  0.4.6 document (RED first). Write set: `dadaia_workspace/features/specs/**`,
  `dadaia_workspace/core/release_state.py`, `tests/**`.
  Blocked by: none. Delivers: the operator runs the test and sees the archived
  state validated for the first time.
- [x] T-047-02 — FR5: generalize `features/specs/rules.py` to `Rule(code, section,
  check, fix)`; `features/spec_context/doctor.py` and `features/backlog/doctor.py`
  contribute their rules; `cli/commands/doctor.py` collects, runs, renders
  `<CODE> <verdict> <message>`, `compliance(<section>)` lines, total, `--json`,
  exit 1 on error class; delete `specs doctor` and `backlog doctor` commands and
  move `--specs-dir`/`--context` to `doctor`. Write set: `dadaia_workspace/cli/**`,
  `dadaia_workspace/features/specs/**`, `dadaia_workspace/features/spec_context/
  doctor.py`, `dadaia_workspace/features/backlog/doctor.py`, `tests/**`.
  Blocked by: T-047-01. Delivers: `dadaia doctor` reports workspace, specs and
  ledgers with three scores and one total.
- [x] T-047-03 — FR7: `core/models/histo.py` (`HistoRecord`, terminal vocabulary
  constant), `public/schemas/histo-record-v1.schema.json`; per-ledger schema
  subsets; `ledgers` section validates `decisions.jsonl`, `BACKLOG.json`,
  `BUGS.jsonl`, `_RELEASE.json` (T-047-01) and the three histories (FR6);
  `test_adr_canon.py` uses the schema validator, `_record_violations` deleted.
  Write set: `dadaia_workspace/core/models/**`, `dadaia_workspace/public/schemas/**`,
  `dadaia_workspace/features/specs/**`, `dadaia_workspace/features/backlog/**`,
  `dadaia_workspace/features/bugs/**`, `tests/**`. Blocked by: T-047-02.
  Delivers: an invalid committed record of any ledger fails `dadaia doctor`.
- [ ] T-047-04 — FR7 migrations, one commit per file with counts:
  `backlog_histo.jsonl` (136), `audits_histo.jsonl` (23), `releases_histo.jsonl`
  (179 events → one record per release). Write set: `specs/**/_archive/*.jsonl`.
  Blocked by: T-047-03. Delivers: `dadaia doctor` ledgers 100 % on the real tree.
- [ ] T-047-05 — FR7 contract: delete `consumed_backlog_histo.jsonl`,
  `features/backlog/ledger.py`, `ConsumedBacklogHistoRecord`, its store builder,
  BL-STALE (a), SPEC-DOC-031, the provisional `CONSUMED` token and their tests;
  canon rows updated. Write set: `dadaia_workspace/**`, `specs/backlog/**`,
  `tests/**`. Blocked by: T-047-04. Delivers: a picked item stays `picked` and
  exits once at closure; no code path writes `CONSUMED`.
- [ ] T-047-06 — FR2: `release new` writes SPEC stub + `_RELEASE.json` in one
  transaction; refuses a second live release with `fix:`. Write set:
  `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/cli/commands/
  newartifacts.py`, `tests/**`. Blocked by: T-047-01. Delivers: after `release
  new` the gate and `context show` resolve the release.
- [ ] T-047-07 — FR4: `release-state-v1` drops `segment`/`audited`, enumerates
  `log.kind`; `PHASES` = four; `rc-archive` parks in DEFINITION and calls the
  shared validator; archived documents carrying `audited`/`segment` migrated
  (one commit). Write set: `dadaia_workspace/public/schemas/releases/**`,
  `dadaia_workspace/core/release_state.py`, `dadaia_workspace/features/specs/
  candidate.py`, `specs/releases/**`, `tests/**`. Blocked by: T-047-06.
  Delivers: the validator refuses any phase or kind outside the enum.
- [ ] T-047-08 — FR4 bugs: terminal verbs write `closed_at`; `bugs archive` and
  SPEC-DOC-041 age by `closed_at`; one-time back-fill of the 507 live terminal
  records from the ledger's commit dates (own commit); validator refuses
  `closed_at < ts`. Write set: `dadaia_workspace/core/models/bugs.py`,
  `dadaia_workspace/features/bugs/**`, `dadaia_workspace/public/schemas/bugs/**`,
  `specs/bugs/BUGS.jsonl`, `tests/**`. Blocked by: T-047-03. Delivers: no record
  is archivable by filing date.
- [ ] T-047-09 — FR3: `dadaia release archive <id> --shipped --pr --next`:
  validate (T-047-01 + all `[x]`, CLOSURE, `implemented`), set `shipped` +
  ARCHIVED, move to `_archive/<id>/`, append histo record (T-047-03 shape), birth
  `<next>` (T-047-06), `bugs archive` (T-047-08), all-or-nothing, print `next:`
  git lines; `rc-archive` calls `bugs archive` too. Write set:
  `dadaia_workspace/features/specs/candidate.py`, `dadaia_workspace/cli/commands/
  newartifacts.py`, `tests/**`. Blocked by: T-047-07, T-047-08. Delivers: the
  promote lane is one verb, refused with `fix:` on an open task.
- [ ] T-047-10 — FR8: `_superseded/` lane deleted from canon/law/test; status
  superseded in place; `measured_by` resolvable pattern in schema + test; rulings
  born accepted (law text); DADAIA §6.5 reworded; P-02 → `ADR: none`; ADR
  0005–0009 `measured_by` rewritten to `WS-`/`SPEC-DOC`/pytest refs; 0004/0010
  operator decision recorded. Write set: `dadaia_workspace/public/schemas/ADRs/**`,
  `dadaia_workspace/public/scaffold/ADRs/**`, `dadaia_workspace/public/data/
  DADAIA.md`, `dadaia_workspace/features/specs/canon.py`, `specs/ADRs/**`,
  `specs/memory/ARCHITECTURE.md`, `tests/contract/test_adr_canon.py`.
  Blocked by: T-047-03. Delivers: an ADR with prose `measured_by` cannot be
  accepted.
- [ ] T-047-11 — FR9: delete the wikilink alias table and rewrite the 15 links;
  delete `_TLDR_INJECTED_CATEGORIES`, catalog carries `tldr`; `category` leaves
  the frontmatter schema and the 23 atoms; closure memory log entry `kind: memory`;
  the two stale facts corrected; index heading English. Write set:
  `dadaia_workspace/features/specs/memory_*.py`, `dadaia_workspace/features/specs/
  catalog.py`, `dadaia_workspace/hooks/ctx_inject.py`, `dadaia_workspace/public/
  schemas/memory/**`, `specs/memory/**`, `tests/**`. Blocked by: T-047-02.
  Delivers: the injected digest shows a `tldr` per atom.
- [ ] T-047-12 — FR10: DADAIA §6.2/§6.4/§6.5/§6.6/§6.7/§6.8/§8.5; scaffolds for
  releases/backlog/ADRs/audits; `dd-release-definition`, `dd-release-implementation`
  (RC-FLOW 9–12, RELEASE-EVENTS), `dd-backlog-definition`, `dd-audit-project`,
  `dd-cli-library`, `dd-workspace-doctor`; behavior-map hashes; `CONTEXT.md`
  (Histo record, Compliance section, Doctor section); `public stage` →
  `install --target all` → `public doctor`; grep proves no `specs doctor` /
  `backlog doctor` pointer survives. Write set: `dadaia_workspace/public/**`,
  `CONTEXT.md`, the workspace-instance projections via the CLI,
  `tests/**`. Blocked by: T-047-05, T-047-09, T-047-10, T-047-11. Delivers: law,
  skills and instance say one thing about doctors, histories and release verbs.
- [ ] T-047-13 — FR11 closure: memory atoms (`specs-doctor`, `workspace-doctor`,
  `audits-canon`, `sdd-bug-backlog-governance`, `pypi-distribution`),
  `CHANGELOG.md [0.4.7]` candidate 1, preflight, `dadaia doctor` 100 %, `_RELEASE.json`
  CLOSURE with `summary`/`size`/`dispositions`/`memory` log entries. Write set:
  `specs/memory/**`, `CHANGELOG.md`, `specs/releases/0.4.7/**`,
  `specs/backlog/**`. Blocked by: T-047-12. Delivers: candidate 1 closed, ready
  for the `feature → develop` PR and the promote-or-continue gate.
