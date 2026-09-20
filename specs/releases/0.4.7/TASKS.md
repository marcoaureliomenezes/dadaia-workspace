# TASKS — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Candidate 7 — ledger verbs to skill scripts

- [x] T-047-63 — FR1: the script contract. `dd-bug-resolution/scripts/bugs.py` lands
  `check`-only as the tracer: stdlib only, `#!/usr/bin/env python3`, exec bit, `--specs <path>`
  defaulting to the nearest `specs/` at or above cwd whose parent holds `.git` (else exit 1 with
  one `fix:` line), `--json`, one `<CODE> error <message>` line per finding, exit 1 on any. It
  reads `scripts/schemas/bug-record-v1.schema.json` beside itself — `public stage` copies the
  shipped `public/schemas/**` file in (copy, not symlink, not import: PLAN decision). Re-point
  `tests/contract/test_public_scripts_thin_wrapper.py`: keep `_THIN_WRAPPER_SCRIPTS` for
  `public/scripts/` mirrors, add the owner-script table for `public/skills/*/scripts/` (<= 150
  lines, stdlib imports only, exec bit, `--help` exit 0, `check` present). No CLI verb retires.
  Seam: the script's argv — `--specs` replaces context resolution.
  RED: `tests/unit/skills/test_bug_resolution_bugs_script.py` running `check` as a subprocess
  over a tmp `specs/bugs/BUGS.jsonl` (clean -> exit 0; a record missing an immutable-core field
  -> exit 1, one line); plus the owner-script contract cases.
  Write set: `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`,
  `dadaia_workspace/infrastructure/{public_assets,projection_rules}.py`,
  `tests/unit/skills/**`, `tests/contract/test_public_scripts_thin_wrapper.py`.

- [x] T-047-64 — FR2: the bugs ledger moves. `bugs.py` gains `append resolve defer reject
  supersede update archive status stats`; every write runs `check` on the result before an
  atomic replace. Carry the two governance refusals verbatim (PLAN): `update --set status=…`
  refused naming the transition subcommand, `update --set caused_by=…` refused naming `resolve
  --caused-by`, which validates against the ledger or the literal `none`. `dadaia bugs` retires:
  drop `add_typer` from `cli/main.py`, delete `cli/commands/bugs.py` and `features/bugs/`,
  regenerate `docs/cli.md`. `dd-bug-registration` cites `bugs.py append`, `dd-bug-resolution`
  cites `resolve`, `LINEAGE.md` cites `status`; `scaffold/bugs/AGENTS.md`, `templates/
  specs-AGENTS.md`, `dd-cli-library`, `dd-audit-project/PILLAR-BUGS.md`, `dd-code-review`,
  `dd-architecture-survey`, `dd-gitflow-default`, `agents/dd-code-reviewer.md` follow.
  Depends on T-047-63. Seam: the bug record's transition methods, now inside the script.
  RED: extend the T-047-63 test with one case per subcommand, incl. both `update` refusals and a
  concurrent-write retry; a `test_cli_help_quality.py` case asserting no `bugs` group.
  Write set: `public/skills/dd-bug-{resolution,registration}/**`, `cli/main.py`,
  `cli/commands/bugs.py` (deleted), `features/bugs/**` (deleted), `container.py`, `setup.cfg`,
  `docs/cli.md`, `public/{scaffold,templates,skills,agents}/**`, `tests/**`.

- [x] T-047-65 — FR2: the backlog ledger moves. `dd-backlog-definition/scripts/backlog.py` with
  `new exit subjects check` over `backlog/BACKLOG.json` + `_archive/backlog_histo.jsonl`, reading
  `scripts/schemas/{backlog-v1,histo-record-v1}.schema.json`. `exit <slug> --disposition` stays
  once-only and terminal. The CLI-anchor subject registry (`cli/anchors.py`,
  `cli/_backlog_roots.py`, `features/backlog/subject_registry.py`) is the doctor's reader for
  `BL-*` and STAYS — the script's `subjects` reads the same `.dadaia/states/
  backlog_subject_aliases.txt`, it does not re-derive anchors from a retired command tree.
  `dadaia backlog` retires; `features/backlog/{document,classifier,preview}.py` deleted.
  Depends on T-047-63. Seam: the `active[]` write and its histo pair.
  RED: `tests/unit/skills/test_backlog_definition_backlog_script.py` — `new` then `exit` moves
  the entry to the histo exactly once, a second `exit` exits 1 with a `fix:` naming the script.
  Write set: `public/skills/dd-backlog-definition/**`, `cli/main.py`,
  `cli/commands/newartifacts.py`, `features/backlog/**`, `cli/anchors.py`, `container.py`,
  `setup.cfg`, `docs/cli.md`, `public/scaffold/backlog/AGENTS.md`, `tests/**`.

- [ ] T-047-66 — FR2: the release ledger moves. `dd-release-implementation/scripts/release.py`
  with `new phase rc-archive archive fold check` over `releases/<id>/_RELEASE.json`, the trio and
  `releases_histo.jsonl`. `archive` stays all-or-nothing: validate (tree, every task `[x]`,
  phase CLOSURE, `implemented` set), stage every file write, rename into place, append the histo
  record, print the git `next:` lines and run no git. The `bugs archive` sweep becomes a numbered
  step in `RC-FLOW.md` (scripts never call each other), not an import. `dadaia release` retires;
  `features/specs/{candidate,catalog}` release writers deleted, `doctor_release.py` stays a
  reader for `RELEASE-TREE-*`. `dd-release-definition` cites `release.py new`,
  `dd-release-implementation` + `RELEASE-EVENTS.md` + `MEMORY-UPDATE.md` cite `phase|rc-archive|
  archive`, `scaffold/releases/AGENTS.md` follows. Depends on T-047-64 (archive's bugs step).
  Seam: the `_RELEASE.json` milestone writer.
  RED: `tests/unit/skills/test_release_implementation_release_script.py` — `new` refusing a
  second live release with a `fix:`, `archive` on a tree with one `[ ]` task leaving every file
  byte-unchanged (the transaction assertion).
  Write set: `public/skills/dd-release-{definition,implementation}/**`, `cli/main.py`,
  `cli/commands/newartifacts.py` (deleted), `features/specs/{candidate,catalog}.py`,
  `container.py`, `setup.cfg`, `docs/cli.md`, `public/scaffold/releases/AGENTS.md`, `tests/**`.

- [ ] T-047-67 — FR2: audit and memory move. `dd-audit-project/scripts/audit.py` —
  `disposition close check` over `audits/<dir>/FINDINGS.jsonl` + `audits_histo.jsonl`, `close`
  refusing while any finding is `open`. `dd-spec-navigator/scripts/memory.py` — `catalog
  generate`, `product add`, `check` over `memory/product/{index.md,catalog.json}` and the atoms'
  5-field frontmatter (`memory-frontmatter-v1.schema.json`). `dadaia audit` and `dadaia memory`
  retire (`cli/commands/{audit,memory}.py` deleted); `features/specs/catalog.py`'s renderer moves
  into `memory.py` and `public/scripts/lint-memory-atoms.py` keeps its package one-sourcing
  (unchanged by this candidate). `FINDINGS-FORMAT.md`, `dd-audit-project/SKILL.md`,
  `scaffold/{audits,memory}/AGENTS.md`, `dd-spec-navigator/SKILL.md` follow.
  Files are disjoint from T-047-65/66. Depends on T-047-63. Seam: two small ledger writers.
  RED: `tests/unit/skills/test_audit_project_audit_script.py` (`close` exit 1 with an open
  finding) and `test_spec_navigator_memory_script.py` (`catalog generate` byte-reproducing this
  repo's committed `catalog.json`).
  Write set: `public/skills/dd-{audit-project,spec-navigator}/**`, `cli/main.py`,
  `cli/commands/{audit,memory}.py` (deleted), `features/specs/catalog.py`, `container.py`,
  `setup.cfg`, `docs/cli.md`, `public/scaffold/{audits,memory}/AGENTS.md`, `tests/**`.

- [ ] T-047-68 — FR3: the doctor delegates. `cli/commands/doctor.py`'s `ledgers` section runs
  each script's `check --specs <dir> --json` through `infrastructure/subprocess_runner.py`
  (`features` must not import `subprocess` — setup.cfg:42) and re-emits each line as
  `LEDGER-<NAME>-SCHEMA` with a `fix:` naming that script's subcommand. Invoke as
  `[sys.executable, <script>]` resolved from the installed skills tree, never the bare script
  (Windows, no exec bit). `features/specs/ledgers.py` is DELETED, not rewritten; `BL-*`,
  `SPEC-DOC-*`, `RELEASE-TREE-*` stay readers. Sweep every remaining `fix:` line naming a retired
  verb (136 hits at candidate start) and extend
  `tests/contract/test_every_block_carries_a_fix.py` to resolve each fix target on disk.
  Depends on T-047-64..67. Seam: the doctor rule table's one delegation point.
  RED: an integration case over a hand-corrupted ledger in a tmp tree asserting exactly one
  `LEDGER-*` line whose `fix:` names the script; `dadaia doctor --specs-dir specs` exit 0 here.
  Write set: `cli/commands/doctor.py`, `infrastructure/subprocess_runner.py`,
  `features/specs/ledgers.py` (deleted), `features/specs/rules.py`, `setup.cfg`,
  `tests/contract/test_every_block_carries_a_fix.py`, `tests/**`, `tests/**/_golden/**`.

- [ ] T-047-69 — FR4: behavior map, lints, ratchets. `public/entities/behavior-map.json`'s
  `hash_tuple` gains a `scripts` member covering every file under the skill's `scripts/`
  (including the staged `scripts/schemas/*.json`, so a schema fork is red);
  `test_behavior_map.py`'s stale-hash finder extends to it. `lint-dadaia-cli-reachability.py`
  learns the script paths as reachable citation targets. A new ratchet pins the script corpus
  (file count, total lines) downward; V32/V33 and `test_specs_cli_complexity_ratchet.py`,
  `test_module_size_ceiling.py`, `test_test_suite_ratchets.py` re-pinned downward; V35 holds 18
  dirs / 2881 lines by deleting the CLI recipes the skills no longer need — never raised.
  `import-linter` contracts drop the deleted packages. AC2.1 (`dadaia help tree` <= 30 verbs) and
  AC4.1 (`dadaia_workspace/` below 36,315 LOC) measured here. Depends on T-047-68.
  Seam: the entities-derivation contract. RED: `test_behavior_map.py` red on a script edited
  without its hash re-recorded.
  Write set: `public/entities/behavior-map.json`, `public/scripts/lint-dadaia-cli-reachability.py`,
  `public/templates/shipped-hashes.json`, `tests/contract/**`, `setup.cfg`, `pyproject.toml`.

- [ ] T-047-70 — FR5: closure. CHANGELOG "Candidate 7 — ledger verbs to skill scripts";
  `_RELEASE.json` log with the measured LOC delta, the retired verb count and the per-ledger
  script sizes; live instance reflected (`public stage` -> `public install --target all` ->
  `public doctor` ok -> `dadaia doctor --fix` exit 0, scripts executable under
  `.agents/skills/*/scripts/`); preflight; push; CI green; `dd-code-review` three axes and six
  lenses; PR #260 updated. The closure memory pass (atoms `sdd-bug-backlog-governance`,
  `workspace-doctor`, `audits-canon`, `agentic-entities`, `server-registry`,
  ARCHITECTURE/TECHSTACK Part 2) is `dd-project-manager`'s CLOSURE procedure, run after this
  task, never inside it. Depends on T-047-69.
  Write set: `CHANGELOG.md`, `specs/releases/0.4.7/_RELEASE.json`.
