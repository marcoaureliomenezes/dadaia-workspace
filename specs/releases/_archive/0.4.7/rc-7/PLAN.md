# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Design (codebase-design vocabulary)

Every `specs/` ledger has three modules that each know its schema: a CLI verb that writes
(`cli/commands/bugs.py` 440 LOC, `newartifacts.py` 556 LOC over `features/{bugs,backlog}` and
`features/specs/{candidate,doctor_release,catalog}`), a doctor rule that validates
(`features/specs/ledgers.py`, 309 LOC of re-implemented schema), and a skill that instructs.
Three interfaces for one fact: the depth is negative — a caller must learn Typer options, the
container, context resolution and the venv guard to append one JSON line, and the three copies
drift against each other.

Candidate 7 replaces that with **one module per ledger**: a stdlib script whose interface is
`<script>.py <subcommand> --specs <path>`. Its implementation is the schema, the invariants and
the atomic write; `check` is the same implementation read-only. One writer, one validator.

- **Seam moved.** The ledger seam moves from *the container-composed CLI verb* to *the script's
  argv*. Its adapters collapse from three (Typer option surface, service/store layering, doctor
  rule table) to one. `--specs <path>` replaces the whole context-resolution stack: the
  parameter IS the context (`registry.py --registry` precedent, `tests/unit/skills/
  test_cli_library_registry_script.py` is the tested shape).
- **Depth raised, deletion test applied.** Delete `features/bugs/service.py`,
  `features/backlog/{document,classifier,preview}.py`, `features/specs/ledgers.py`,
  `cli/commands/{bugs,audit,memory}.py` and `newartifacts.py`: complexity does not reappear at
  N callers — the callers are the five scripts and the doctor. What stays is what the doctor
  *reads* for cross-checks (`SPEC-DOC-*`, `RELEASE-TREE-*`, `BL-*`, `subject_registry`,
  `doctor_release`) — reader-only, no schema copy.
- **Replace, don't layer.** No verb keeps a shim, no alias, no deprecation branch. A retired
  group leaves `main.py`'s `add_typer` list in the same commit as its script lands green.
- **Schemas: copy at stage, not symlink, not import.** The script reads
  `scripts/schemas/<name>.schema.json` next to itself; `public stage` copies the shipped
  `public/schemas/**` file in. A symlink dies on Windows and in a zip-installed skill; an import
  is the exact coupling FR1 forbids. The copy is hash-checked by the FR4 hash tuple, so drift is
  a red test, not a silent fork.
- **The doctor is a caller, not a validator.** `ledgers` runs `check --specs <dir> --json` as a
  subprocess through `infrastructure/subprocess_runner.py` — `features` must not import
  `subprocess` (setup.cfg contract, line 42), so the adapter is where the delegation lives and
  `features/specs/ledgers.py` is deleted, not rewritten.

## Order of work (tracer bullets)

Each task leaves `dadaia ci preflight` green; each retires its CLI group only after its script
is green, so the repo's own ledgers are writable at every commit.

1. **T-047-63 (FR1)** — the contract first: `check`-only `bugs.py`, the schema copy rule at
   stage, and the contract test. No verb retires; the tracer proves the shape end to end.
2. **T-047-64 (FR2 bugs)** — the widest ledger (9 verbs, the `update` governance seam, the
   `_run_transition` model-method dispatch) moves and `dadaia bugs` retires.
3. **T-047-65 (FR2 backlog)**, **T-047-66 (FR2 release)** — release last of the two: `archive`
   is the all-or-nothing transaction and depends on the bugs script for its `bugs archive` sweep.
4. **T-047-67 (FR2 audit + memory)** — the two small ledgers, one task, disjoint files.
5. **T-047-68 (FR3)** — the doctor delegates; `ledgers.py` and every stale `fix:` die together.
6. **T-047-69 (FR4)** ratchets, hash tuple, reachability lint, import-linter. **T-047-70 (FR5)**
   closure.

## Verification

- `dadaia ci preflight` green after every task; full suite at closure.
- New `tests/unit/skills/test_<skill>_<ledger>_script.py` per ledger, subprocess-driven over a
  tmp `specs/` tree (the `registry.py` precedent, SMALL).
- `tests/contract/test_public_scripts_thin_wrapper.py` re-pointed (see Risks); amended
  `test_every_block_carries_a_fix.py`, `test_behavior_map.py`, `test_docs_derived_from_memory.py`,
  `test_cli_help_quality.py`, `test_cli_output_stability.py`, `test_specs_cli_complexity_ratchet.py`,
  `test_slop_ratchets.py`, the doctor golden fixtures.
- AC2.2: `grep -rn 'dadaia \(bugs\|backlog\|release\|audit\|memory\)' dadaia_workspace` returns 0
  (136 hits today). AC3.1: `dadaia doctor --specs-dir specs` exit 0 here; a corrupted tmp ledger
  yields one `LEDGER-*` line whose `fix:` names the script.
- Live instance: `public stage` -> `public install --target all` -> `public doctor` ok ->
  `dadaia doctor --fix` exit 0, scripts executable under `.agents/skills/*/scripts/`.

## Risks

Bug families these surfaces carry — 125 `BUGS.jsonl` ids match `doctor-fix|backlog|bugs-|
release-|audit`; `doctor` names 102 titles, `release` 56, `specs` 44 records, `backlog` 18,
`bugs` 18. Two families are structural and this shape ends them:

- **The dangling-`fix:` family** — `backlog-doctor-fix-names-missing-update-verb` (three `fix:`
  lines naming a deleted verb) and `recipe-f15-cites-nonexistent-memory-list` (`dadaia memory
  list` never existed). Cause: the validator names a remedy owned by a different module. With
  the validator BEING the writer, a `fix:` names a subcommand of the same file — a broken fix is
  a red `--help` test, not a released defect.
- **The three-copies-drift family** — every `LEDGER-<NAME>-SCHEMA` rule in `ledgers.py`
  duplicating a writer's invariant, plus `backlog-subject-registry-lacks-top-level-doctor-cli-
  anchor` and `backlog-resume-contradiction-loop-after-fixing-a-preexisting-item` (author and
  gate prescribing each other). One writer that runs its own `check` before replacing the file
  makes writer-vs-validator disagreement unrepresentable.
- **Counter-risk to watch:** this candidate DELETES far more than it adds, but each script is a
  new file. Any script that grows a second code path for a caller (a `--legacy`, a `--no-check`)
  is the puxadinho this rule forbids — refuse it, shrink the subcommand set instead.

Mechanical risks:

- **Ratchets going up.** `_V35_DIR_CEILING = 18` / `_V35_LINE_CEILING = 2881` count skill
  Markdown only, so `.py` scripts are outside it — but every skill gaining a script also gains
  prose. Pay for it by deleting the CLI recipes those skills no longer need. `_V33_CEILING = 37`
  (orphan codes) and `_V32_CEILING = 765` move DOWN as verbs die; `test_specs_cli_complexity_
  ratchet.py` and `test_module_size_ceiling.py` must be re-pinned downward, never up.
- **Tests pinning the CLI tree.** `docs/cli.md` is `dadaia help tree`'s committed output and
  `test_docs_derived_from_memory.py` fails on any drift; `test_cli_help_quality.py` and
  `test_cli_output_stability.py` pin per-group help text. Regenerate `docs/cli.md` in the same
  commit that removes a group, or the retirement is red at push.
- **`test_public_scripts_thin_wrapper.py` asserts the opposite doctrine today** — logic in the
  package, projected script thin (v0.4.3 FR16). FR1 inverts it for skill scripts. Re-point the
  file: keep `_THIN_WRAPPER_SCRIPTS` for `public/scripts/` mirrors, add the owner-script table
  for `public/skills/*/scripts/`. Do not create a second file.
- **`bugs update` is the governance-write seam.** It refuses `status` (naming the transition
  verbs) and `caused_by` (one writer: `resolve --caused-by`, validated against the ledger). Both
  refusals live in `BugRecord.apply_governance_update`; the script must carry them or the
  lineage contract silently opens.
- **`release archive` is all-or-nothing** — writes `shipped` + ARCHIVED, moves the tree, births
  the next release, appends the histo record and sweeps `bugs archive`, printing git lines it
  never runs. FR1's "run `check` then replace atomically" is per-file; a multi-file transaction
  needs staging + rename, and the `bugs archive` sweep is a cross-script call FR1 forbids —
  make it a numbered step in `dd-gitflow-default`/RC-FLOW, not an import.
- **Doctor-as-subprocess.** The interpreter must be the venv `sys.executable`, never `python3`
  (the venv guard and `init-venv-never-installs-dadaia-workspace` history); resolve the script
  from the installed `.agents/skills/` tree, not a repo-relative path, or a consumer instance
  finds nothing. Windows has no exec bit — invoke `[sys.executable, script]`, never the script
  alone (`v043-gc-suite-windows-platform-fixtures`, `citation-mutation-fixtures-never-turn-red-
  on-windows`).
- **import-linter contracts** name `features.backlog` and `features.bugs` in the mutual-
  independence contract (setup.cfg:122); deleting the packages leaves a contract naming a
  missing module — update setup.cfg in the same task that deletes.
- **Stall risk:** `specs/bugs/`, `specs/backlog/` and `specs/audits/` are ADDITIVE, so scripts
  write there unblocked; `specs/releases/**` is MUTATING — `release.py` run from an out-of-scope
  bind is blocked with a `fix:` naming `dadaia context bind`, which must survive the retirement.
