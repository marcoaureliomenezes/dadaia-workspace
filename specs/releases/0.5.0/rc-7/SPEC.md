# SPEC — Release: 0.5.0, candidate 7 (W3: one grammar owner; W4: one text renderer)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-01
**Origin:** backlog:ledger-schema-one-engine,structural-convergence-f053-f054-f057,consumer-guidance-names-no-library-toolchain,seventh-fail-open-path-law-line
- Sources: rc-6's §Carried W3/W4 rows and risk seeds, its closure log and reviews (step 7b, PR #276); operator order 2026-09-30 ("cria todas as rc … Depois so revisaremos"); the 2026-10-01 batch grill, D1–D6.
- The line holds the `backlog:` clause alone (today's tools refuse a multi-clause line); bugs and findings are in §Origin map; AC3.2 rewrites it. `task-line-grammar-one-reader` exits `to-bug`, which reads no Origin. No bug is registered.
- At 44d023e6 every carried id is non-terminal: 18 bugs open, 5 entries active, 29 findings open, F053, F054, F057, F080 deferred.

## Objective

- Give every text grammar one parser and one owner (ADR 0135, as 0157 and 0162 amend it): the Origin line, the task line, the Status token, each JSONL ledger record, the privacy denylist and the context registry.
- Give every printed command one renderer and one contract harness: fix lines, `--help` examples and shipped-text commands (ADR 0045).
- Close the lineage, commit-shape and archive gaps on those grammars, the `to-bug` exit (0137) and 0127's release traceability; state the seventh fail-open path.

## Terms

- `CONTEXT.md` holds the terms. **W3** and **W4** are this candidate; **DEL** and **FR** keep rc-5's meaning.
- **Grammar**: a text shape more than one module reads (ADR 0135). A JSON Schema validates its records; the grammar's owner owns that check (AC3.6).
- **Grammar owner**: the one module that parses a grammar. Every other reader consults it.
- **Pinned pair**: one grammar or renderer kept on both sides of the package/script seam, one contract test asserting equal output (ADR 0159).
- **Text renderer**: the one builder of a printed command, not the Rich console printer.

## Bug history read

- Fix lines: 17 records, 4 open. ADR 0045's builder covered the CLI spelling only, not placeholders, prose or `_specs.py`; three contract files judge one invariant.
- Unicode line breaks: 5 records, the fifth open; each fix patched its own reader.
- Denylist: 19 records; `sa-denylist-file-has-three-shapes` migrated no old file (F037).
- Task line: four readers (`_worktree_end._MARK` from rc-5, `_release_plan`'s `W:`); registry: rc-6 left `JsonContextStore`'s own parse. Same cause: no owner.

## Decisions

- These ADRs decide: 0018, 0019, 0045, 0106, 0111, 0119, 0122, 0123, 0126, 0127, 0135, 0136, 0137, 0140, 0141, 0142, 0146, 0150, 0152.
- Accepted, one record per ruling (operator, 2026-10-01: "Aceito D1–D6 (Recomendado); Aceito 0157–0162 (Recomendado)"); 0158 also narrows 0018's "every fix line names a script or verb".

| D | ruling | ADR |
|---|---|---|
| D1 | one denylist loader, the stdlib `_ledger.py`; root from `--specs` | 0157, amends 0135 |
| D2 | a fix line: a runnable command or `Operator action: <one act>`, no placeholder | 0158, amends 0045 |
| D3 | the renderer is a pinned pair, `core/cli_line.py` ↔ `_specs.py` | 0159, amends 0045 |
| D4 | `diff_direction` derived, `evidence_seam` judged at `resolve` only; narrows the bug's `expected` | 0160 |
| D5 | the Origin line is `backlog:<ids>; bugs:<ids>; findings:<ids>`, parsed only by `release.py` | 0161, amends 0019 |
| D6 | the registry parse in `core`; the Status token a pinned pair | 0162, amends 0135 |

- No new record: the doctor delegating to each script's `check` is 0018's; shape 5's "+ picked bugs" leaves by 0106 and 0127; the backlog kind admitting `BUGS.jsonl` is 0137's "one worktree".

## Origin map — candidate 7

Each finding that cites a bug or an entry shares its destination; findings are `20260930-structural-convergence-F<nnn>`.

| Where | Bugs | Backlog | Findings, carry-overs |
|---|---|---|---|
| W3 | DEL `spec-origin-line-has-two-readers`, `task-line-grammar-accepts-a-malformed-open-marker`, `privacy-denylist-has-two-loaders`, `release-ship-accepts-what-release-check-refuses`, `bugs-check-trusts-evidence-fields-unverified`, `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger`, `corrupt-context-registry-crashes-doctor-and-next-step`; FR `list-form-privacy-denylist-errors-without-migration`, `secret-scan-misses-github-pat-and-anthropic-keys`, `release-check-accepts-done-tasks-in-definition`, `gitflow-shape2-omits-backlog-histo` | FR `ledger-schema-one-engine`, `structural-convergence-f053-f054-f057`, each exits `delivered`; `task-line-grammar-one-reader` exits `to-bug` → `task-line-grammar-accepts-a-malformed-open-marker` | F002, F010, F012, F013, F016, F024, F029, F030, F032–F034, F036–F038, F052–F054, F057–F059, F061, F063, F102, F103; c4 AC6.3, AC6.6 (V38) |
| W4 | DEL `dadaia-bin-still-honoured-after-adr-0045`, `help-examples-spell-the-blocked-bare-cli`, `fix-lines-are-not-one-runnable-command`, `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids`, `implementer-persona-states-a-second-task-marker-lifecycle`; FR `doctor-tmp-expiry-foreign-owned-entry-never-clears`, `rc-flow-asks-compliance-line-doctor-never-prints` | FR `consumer-guidance-names-no-library-toolchain`, `seventh-fail-open-path-law-line`, each exits `delivered` | F007, F017, F031, F035, F039–F041, F080, F099 |
| Closure memory pass | — | — | `bug-ledger`, `backlog-ledger`, `release-lifecycle`, `audits-canon`, `worktrees`, `context-management`, `workspace-doctor`, `sdd-gate-v3`, `ci-preflight` |

## Gate — rc-5's G1–G6, applied to W3 and W4

- G1 Principles, never a line-count limit (ADR 0142):
  - Every unit walks DELETE → REBUILD → UPDATE → KEEP → ADD, and an ADD names what it could not delete or rebuild.
  - No question gets a second decider, and no rule contradicts another.
  - Readout at `<start>` and `<end>`, by the commands rc-8 §G1 also uses: production lines `git ls-files -z 'dadaia_workspace/*.py' | xargs -0 cat | wc -l`, test functions `git grep -hE '^\s*(async\s+)?def test_' -- 'tests/*.py' | wc -l`, test lines `git ls-files -z 'tests/*.py' | xargs -0 cat | wc -l`. At 44d023e6: 24,965 / 1,193 / 44,164.
- G2 `bugs.py status` lists no open record whose `caused_by` names a record or a commit of W3 or W4.
- G3 Every still-open bug is re-run at `<end>`; one that no longer reproduces is resolved citing the commit that removed its cause; the count is logged.
- G4 CI is green on the three OSes; `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0; no job's wall-clock grows past its rc-6 closure duration (run 36813899731); the ADR 0119 breach stays with rc-8 W5 (operator 2026-10-01: "Sim, base rc-6 (Recomendado)"). The closure log states the timing tolerance it applied.
- G5 A test a DEL leaves dead leaves in the same commit; a new test states its intent and passes `dd-test-stewardship`'s admission; a new test file enters only when no file owns the behavior (0146 (5)).
- G6 At closure, open findings and `active[]` are re-audited against the merged waves, rc-8's SPEC is re-scoped before its PLAN, and one `dispositions` entry logs open before, resolved with a commit, open after.

## W3 — one grammar owner: acceptance

- AC3.1 One parser per grammar (0135; 0159, 0162):
  - The PLAN §1.1 Authorities table has one row per grammar of §Objective, one per JSONL ledger (bugs, backlog histo, ADRs, audit findings and histo, releases histo) and one for `BACKLOG.json`.
  - Each row names one owner that every other reader `consults`; the Status token is a pinned pair, `core/spec_status` ↔ `_release_schema.extract_status`.
  - Measure: 0135's contract test, in the file the PLAN finds owning it, fails when a package module parses a grammar outside its owner or pinned twin, and pins each owner script's location.
  - It encodes the layer rule the pairs rest on: no `core` module loads a `public/` file; no `public/skills` script imports `dadaia_workspace`. `infrastructure` loads an owner script (0157) by path from the package's own copy; a stdlib script is no package module, so no import-linter contract changes.
- AC3.2 Origin line (DEL `spec-origin-line-has-two-readers`; 0127; 0161):
  - `release.py` owns the 0161 parser, and `release.py check` is the one judge of an Origin line: presence, grammar, id existence and tracing. `_backlog_exit` imports the parser. SPEC-DOC-048 leaves the doctor, which reports Origin through its ledgers section (AC3.6), so no fact is reported twice.
  - Only the first Origin line counts. In the bug's repro, `backlog.py exit <id> --disposition delivered` is refused.
  - `release.py check` lists each carried id and whether its record points back: an entry's `delivered` exit, a bug's `resolved_release` or rejection, a finding's disposition `release`. A missing pointer is a finding only once the live candidate's `dispositions` log entry exists, and at `ship`; before, it is listed.
  - In the closure touch, this SPEC's Origin line is rewritten in the 0161 form, the §Origin map drops the ids now on it, and `release.py check` traces it clean.
  - Command: `pytest tests/contract/test_release_script.py tests/unit/skills/test_release_implementation_release_script.py`.
- AC3.3 Task line (DEL `task-line-grammar-accepts-a-malformed-open-marker`; 0111):
  - The grammar, the marker and the `W:` field, lives once, in `_release_schema`.
  - `- [ ]**T-1**`, `+ [ ] T-1` and `* [-] T-1` all read as open to `release.py phase CLOSURE`, the doctor and `worktree.py merge`'s marker replay. The replay keeps "the most advanced state wins".
  - `_release_plan`'s overlap check reads `W:` through it; rc-6's T-050-117 line parses to the paths it writes (a backticked path in parentheses is named, not written).
  - `git grep -nE '_TASK_BLOCK_RE|_MARK = re' -- dadaia_workspace` prints nothing.
  - Command: `pytest tests/unit/skills/test_release_implementation_release_script.py tests/integration/test_worktree_lifecycle.py`.
- AC3.4 One readiness authority (DEL `release-ship-accepts-what-release-check-refuses`; FR `release-check-accepts-done-tasks-in-definition`):
  - In the ship bug's repro, `ship` exits 1 with `check`'s refusal and fix, the directory untouched.
  - `release.py check` judges every phase: under DEFINITION, a `[-]` or `[x]` marker, or a closure log entry after the live candidate's birth note, is a finding; `_release_tree._directory_findings`'s phase guard leaves.
  - Command: `pytest tests/unit/skills/test_release_implementation_release_script.py`.
- AC3.5 One JSONL reader (DEL `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger`):
  - One JSONL reader, in `_ledger.py`, splits on `\n` only. The script stores read through it; the package loads it by 0157's path. `infrastructure/jsonl_record_store.py`, read by no production module, is deleted. No ledger is read with `splitlines()`, `doctor_release._json_records` included.
  - In the bug's repro, `release.py new --origin bugs:ls-probe` seeds the SPEC, and `doctor_adr` reads a decisions record holding U+2028.
- AC3.6 One ledger schema engine (FR `ledger-schema-one-engine`; F103; 0018):
  - The doctor's ledgers section runs each script's `check` and builds no `jsonschema` validator for a ledger schema.
  - Command: `pytest tests/integration/test_backlog_doctor.py` plus the bug-ledger doctor case the PLAN names.
- AC3.7 Evidence fields (DEL `bugs-check-trusts-evidence-fields-unverified`; F002; 0160):
  - `diff_direction` leaves `bug-record-v1` and, once, every record: `_bugs_store.commit` (bugs.py's one write path) writes the strip from a command quoted in the commit body, in one shape-3 commit of a `bug` worktree with the schema drop; no new verb, no hand edit. `check` and `stats` derive it from the `evidence_diff` prefix (lines 653–654 read as one); SKILL.md and `PILLAR-BUGS.md` follow.
  - `bugs.py resolve` refuses an `--evidence-seam` whose file or `def <name>` does not exist. `check` never re-judges a resolved seam: the 15 historic seams and rc-6's moved seam and pre-rebase SHAs stay as written.
  - Command: `pytest tests/unit/skills/test_bug_resolution_bugs_script.py`.
- AC3.8 Lineage (F012, F013):
  - `bugs.py check` refuses a `caused_by` cycle and a `caused_by` that names no record.
  - The 2 cycles, 3 dangling targets and 3 null `caused_by` of F012 and F013 are set by the `bugs.py` governance verb, never by hand; `check` exits 0.
- AC3.9 One context-registry parse (DEL `corrupt-context-registry-crashes-doctor-and-next-step`; F024; 0162):
  - `core/context_registry.py` is the one parse: `JsonContextStore` and the doctor's `_contexts()` read through it; `invocation._registry_contexts`'s fail-soft `or []` is deleted.
  - An absent file is the empty registry at every reader (the resolver's sentinel). A file not parsing to a `{"contexts": [...]}` object, `{}` included, is unreadable, never empty, and every doctor `--fix` lane then acts on nothing.
  - Truncated registry: SessionStart, `doctor`, `context list`, `show` and `create` each print REG-SCHEMA with one fix line, no traceback, never "create a context"; the layout check keeps `{"*"}`.
  - Command: the owner test the PLAN names, one case per reader.
- AC3.10 One denylist loader (DEL `privacy-denylist-has-two-loaders`, FR `list-form-privacy-denylist-errors-without-migration`; 0157):
  - A ledger verb run from outside the workspace, with `--specs` pointing into it, loads the same terms as pre-push.
  - Re-running `init` converts a list-form file to the object form once, `sweep.hold` holding the original; then `public doctor` and a push pass.
  - Command: `pytest tests/unit/features/chokepoints/test_push_denylist_scan.py` plus the `test_cli_init.py` upgrade case.
- AC3.11 Secret registry (FR `secret-scan-misses-github-pat-and-anthropic-keys`):
  - `infrastructure/data/privacy_baseline.json` matches `github_pat_` plus 40 characters and `sk-ant-…` keys in an assignment, a header and YAML; `ghp_` still matches.
  - Fixtures compose the secrets at runtime (`dd-release-implementation` §2a).
- AC3.12 The `to-bug` exit (0137; F063, F102):
  - `backlog.py exit <slug> --disposition to-bug --reason <bug-id>` exits when the id names a `BUGS.jsonl` record, read by importing `bugs.py`'s reader; an unknown id is refused.
  - `backlog.py check` accepts `to-bug`; `specs/backlog/AGENTS.md` lists four dispositions; the backlog kind admits `specs/bugs/BUGS.jsonl`, so registration and exit share one worktree.
  - `release.py check` reports a `to-bug` target that was later rejected; `task-line-grammar-one-reader` exits by it (§Origin map).
- AC3.13 Commit shapes (F053, F054, F057; FR `gitflow-shape2-omits-backlog-histo`; 0106, 0136):
  - `dd-gitflow-default` §3a's staged set becomes "the kind's allowed set" (`KINDS`): a backlog exit stages `BACKLOG.json` with its histo; shape 2's ADR message is `docs(adr): propose|accept <slug>`.
  - The "alone" clauses and "+ picked bugs" leave, there and in `dd-release-definition` §4; each closure commit form (`chore(tasks)`, `docs(memory)`, `docs(specs)`, `chore(release)`) gets a row.
  - Check: `git grep -c 'picked bugs' -- dadaia_workspace/public` prints nothing; `tests/contract/test_law_states_what_the_code_does.py` asserts §3a's sets equal `KINDS`.
- AC3.14 Archive and milestones (F058, F059, F061):
  - `LINEAGE.md` states ADR 0152 (1): the release folder survives under `_archive/<v>/`.
  - A shipped sha and PR live in one structured field, which `release.py check` verifies for each release archived from 0.5.0 on.
  - Each candidate's `defined` and `implemented` stamps survive the next one's birth (shape: the PLAN, in `RELEASE-EVENTS.md`); earlier 0.5.0 stamps, overwritten in the one slot, are recovered from the log.
  - The 0.5.0 log gains one appended note on the 0.4.8 → 0.5.0 rename; no entry is rewritten.
- AC3.15 Audit close (F052): `audit.py close` refuses to run without `--sha`, and `LINEAGE.md` says how to recover a missing sha (`git log -S <audit-id> -- specs/audits`).
- AC3.16 Ratchet carry-overs (c4 AC6.3, AC6.6):
  - A destructive file call outside `features/spec_context/sweep.py` fails V38 or an import-linter contract; the PLAN measures today's sites first.
  - `_allowance_violations` asserts that the V38 and V39 closure allowances are subsets of their birth allowances. V37 is rc-9's (AC7.4).
- AC3.17 Law: `CONTEXT.md` gains **Grammar**, **Grammar owner** and **Pinned pair**; the scaffold `specs/releases/AGENTS.md` §2 states the 0161 Origin grammar once.
- AC3.18 Core-floor refusal messages (PR #276 review):
  - The message for each floor entry lives beside `CORE_FLOOR` in `core/workspace_layout.py`, and `gate_policy.evaluate` keys none on a string literal.
  - `classify_path`'s docstring states `_protection`'s order: projected → floor → glob.
  - Command: `pytest tests/unit/features/spec_context/test_gate_policy.py`.

## W4 — one text renderer: acceptance

- AC4.1 One renderer, one harness (F017; 0045, 0158, 0159):
  - `test_every_block_carries_a_fix.py`, `test_fix_lines_use_the_builder.py` and `test_fix_line_runs_in_every_shell.py` become one harness over every site, rc-6's refusals included; each case is re-homed by name (G5).
  - Per site it asserts exactly one fix line, in a 0158 form (a command whose argv0 exists, or `Operator action:`), no `<…>` placeholder, and a command the pre-gate allows when fed back as Bash.
  - It holds 0159's pinned-pair case: one argv through `cli_line` and `_specs.py` renders one line.
  - The `push-refspec` case keeps its name and its bug id `every-block-fix-push-refspec-flaky-under-xdist`; the fix stays rc-8 W5's unless the rebuild removes the shared state, which G3 then resolves citing that commit.
  - The root map §3 states the two forms (0158). The harness adds no wall-clock beyond the three files it replaces (G4).
- AC4.2 `DADAIA_BIN` is gone (DEL `dadaia-bin-still-honoured-after-adr-0045`): `git grep -n DADAIA_BIN -- dadaia_workspace` prints nothing.
- AC4.3 `--help` examples (DEL `help-examples-spell-the-blocked-bare-cli`):
  - Every `Run:` or example line in `--help` renders the venv CLI path through the renderer.
  - Command: `pytest tests/contract/test_cli_help_quality.py` over the whole command tree.
- AC4.4 Fix lines run as printed (DEL `fix-lines-are-not-one-runnable-command`; FR `doctor-tmp-expiry-foreign-owned-entry-never-clears`; 0158):
  - Each site the record names, in its 0158 form with real values:
    - command: the session-record BLOCK (`context bind` with the resolved context); the pre-push refusal (the live work branch); the root-whitelist BLOCK (`mkdir -p` of the real `.dadaia/tmp/<agent>/<YYYYMMDD>/`; F098's message is rc-8's AC6.4); `doctor --context nosuch` (`context list`); the gate scope BLOCK (`context bind <owner>`); the `backlog exit` hint (a disposition the entry can take);
    - `Operator action:`: the id-less session relaunch, and the onboarding first-pass Next.
  - `sweep.guarded`'s skip line for an expired entry it cannot delete names the owner and `Operator action: remove <real path>`; once the entry is gone, `doctor --fix` clears the finding.
  - Correlate: `_specs._bound_tree` stops routing `--specs` to `repos/<r>/specs` (unwritable outside `specs/audits/`, rc-5 AC1.1); it names the open worktree of the ledger's kind, else `worktree.py new <r> --kind <kind>`.
  - Correlate: `_backlog_exit`'s `--release` fix names the release it found.
  - Command: the AC4.1 harness.
- AC4.5 Ledger fixes (DEL `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids`):
  - Each ledger script's `check` emits its own fix naming its governance verb, one per invalid line; `ledger_scripts.py`'s hand-edit fallback is deleted. In the bug's repro the fix runs a `bugs.py` verb.
- AC4.6 One task-marker lifecycle and one closure ladder (DEL `implementer-persona-states-a-second-task-marker-lifecycle`; FR `rc-flow-asks-compliance-line-doctor-never-prints`; 0126, 0141):
  - The scaffold `specs/releases/AGENTS.md` §3 states the lifecycle once (`[ ]→[-]` at the start, `[-]→[x]` in the impl commit, reviewed at the worktree merge); `dd-software-engineer`, `dd-manager-orchestration` and `RC-FLOW.md` cite it.
  - `RC-FLOW.md` loses "marker stays `[-]`", "no per-task reviewer gate" and the "two simultaneous `[-]`" recovery (0141).
  - RC-FLOW step 8 asks only for the doctor's findings and exit code.
  - Measured by `tests/contract/test_law_states_what_the_code_does.py`, by code-derived facts as AC3.13: the transitions the law states equal the marker states and order `_release_schema` defines; no sentence is pinned (S3d).
- AC4.7 Consumer guidance (FR `consumer-guidance-names-no-library-toolchain`; F099):
  - The installed pre-push hook names no `dadaia ci preflight`, `docs/getting-started.md` no release-please; the harness runs the consumer refusals in a consumer-repo fixture.
- AC4.8 Shipped text (F007):
  - The harness scans the command lines of `public/**/*.md` for a bare `dadaia`, `$DADAIA_BIN`, or a verb or flag the live command tree lacks, replacing the bare-CLI guard deleted with its test.
- AC4.9 The seventh fail-open path in law (FR `seventh-fail-open-path-law-line`; F080; rc-6 step-7b review):
  - The root map §3 (`public/data/AGENTS.md`) adds the seventh path: an unreadable registry judges nothing below `repos/` and `worktrees/` (`{"*"}`); its first bullet states the judged scope: the root, `.dadaia/`, the closed-canon zones, the first level of `repos/` and `worktrees/`.
  - `docs/getting-started.md` Level 1 lets "absent" govern both `.dadaiaignore` and `prompt.md`; the doctor paragraphs of README, getting-started and quickstart say a TTL expiry acts by zone class (OUTPUT held, EPHEMERAL deleted).
  - Command: `pytest tests/contract/test_law_states_what_the_code_does.py`: one row per fail-open path drives the code to ALLOW (or `{"*"}`), and the root map's list is set-equal to the rows' keys. No sentence is pinned (S3d, rc-8 W5).

## Replaces

- SPEC-DOC-048 (`doctor_release._ORIGIN_RE`, `check_spec_origin`, `_known_backlog_ids`) and `_backlog_exit`'s Origin regex.
- `_TASK_BLOCK_RE`'s marker reading, `_worktree_end._MARK` and `_release_plan`'s `W:` regex.
- `ship`'s own readiness judgement, and `check`'s DEFINITION skip.
- The `splitlines()` ledger reads (`_release_new.py:63`, `doctor_adr.py:30`, `doctor_release._json_records`) and `infrastructure/jsonl_record_store.py`.
- The doctor's `jsonschema` ledger validation.
- `invocation._registry_contexts`'s `[]`, `JsonContextStore`'s own parse and the doctor's store read (0162).
- The second denylist loader and its cwd walk (0157).
- The stored `diff_direction` (0160).
- §3a's "alone" clauses, `chore(adrs)` and "+ picked bugs".
- `LINEAGE.md`'s "no per-release `_RELEASE.json` survives archiving".
- `gate_policy`'s string-literal floor keys.
- `DADAIA_BIN` at three sites.
- Hand-spelled `--help` examples.
- `ledger_scripts._finding`'s hand-edit fallback.
- `_bound_tree`'s `repos/<r>/specs` routing.
- `sweep.guarded`'s fixless skip line.
- The three fix-line contract files.
- The second marker lifecycle, and RC-FLOW's compliance line.
- The hook's `ci preflight` advice and the release-please step.
- The six-path fail-open list.

## Risks

| Weakness | Mitigation |
|---|---|
| 0135: an owner on a hot path crashing or moving. | Owners stay off the pre-gate path, loaded from the package's own copy; a crash fails soft into one finding (F024); AC3.1 pins each location. |
| A pinned pair drifts (0159, 0162). | Its one contract test fails on any difference (AC3.1, AC4.1). |
| 0137: a registration without its exit; a target rejected later. | One backlog worktree holds both; `release.py check` reports a rejected target (AC3.12). |
| The 0160 strip rewrites every `BUGS.jsonl` line; a parallel `bug` worktree's union merge (0111) doubles a record. | The strip runs with no `bug` worktree open; `bugs.py check` refuses a duplicate id at merge. |
| The 0161 grammar breaks closed SPECs. | A one-clause line is its one-clause case; no second grammar exists. |
| The widened secret patterns hit published history. | Published history is never rescanned (§2a). |
| The root map passes its soft budget (8,304 B of 8,192, ADR 0143). | AC4.1 and AC4.9 edit existing bullets. |

## Carried to candidates 8+ (ADR 0140; specified by their own SPECs)

- rc-6's §Carried rows for W5–W7 and the Promote PR, and its closure carries to rc-8, stand as logged.

## Open questions for the operator

- None (OQ1 answered; see G4).
