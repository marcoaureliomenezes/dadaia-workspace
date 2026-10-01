# SPEC — Release: 0.5.0, candidate 7 (W3: one grammar owner; W4: one text renderer)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-01
**Origin:** backlog:ledger-schema-one-engine,structural-convergence-f053-f054-f057,consumer-guidance-names-no-library-toolchain,seventh-fail-open-path-law-line
- Sources:
  - the W3 and W4 rows and the W3 risk seeds of rc-6's SPEC §Carried;
  - rc-6's closure log (2026-10-01T05:12:50Z), its step-7b review of bdf3b602 and the PR #276 head review;
  - operator order, 2026-09-30: "cria todas as rc … vc ja sabe o que vai nelas. Depois so revisaremos";
  - the batch grill of 2026-10-01 (`2026-10-01T010500Z-main-thread-grill-rc7-rc9-batch.md`): D1–D6 accepted as recommended.
- The Origin line holds the `backlog:` clause alone: today SPEC-DOC-048 and `_backlog_exit` refuse a multi-clause line, so bugs and findings are in §Origin map, and AC3.2 rewrites the line in the D5 form at closure.
- The clause is the pick `backlog.py exit` reads: this candidate's deliveries only. `task-line-grammar-one-reader` exits `to-bug`, which reads no Origin (AC3.12). No bug is registered.
- Live status at 44d023e6: every carried id is non-terminal — 18 bugs open; the 4 picked entries and `task-line-grammar-one-reader` active; 29 findings open, F053, F054, F057, F080 deferred to 0.5.0.

## Objective

- Give every text grammar one parser and one owner (ADR 0135, as 0157 and 0162 amend it): the Origin line, the task line, the Status token, each JSONL ledger record, the privacy denylist and the context registry.
- Give every printed command one renderer and one contract harness: fix lines, `--help` examples and shipped-text commands (ADR 0045).
- Close the lineage, commit-shape and archive gaps on those grammars, the `to-bug` exit (0137) and 0127's release traceability; state the seventh fail-open path.

## Terms

- `CONTEXT.md` holds the terms. **W3** and **W4** are this candidate; **DEL** and **FR** keep rc-5's meaning.
- **Grammar**: a text shape more than one module reads (ADR 0135). A JSON Schema validates its records; the grammar's owner owns that check (AC3.6).
- **Grammar owner**: the one module that parses a grammar. Every other reader consults it.
- **Pinned pair**: one grammar or renderer kept twice across the package/script seam (`core` may not import `public/`), one contract test asserting equal output (ADR 0159).
- **Text renderer**: the one builder of a printed command, not the Rich console printer.

## Bug history read

- Fix lines: 17 records, 4 open, plus rc-6's foreign-owned expiry bug. ADR 0045's builder covered the CLI spelling only, not placeholders, prose, no-op commands or `_specs.py`; three contract files judge one invariant.
- Unicode line breaks: 5 records, the fifth open. Each fix patched its own reader; `_release_new.py:63` and `doctor_adr.py:30` still use `splitlines()`.
- Denylist: 19 records. `sa-denylist-file-has-three-shapes` collapsed the shapes and migrated no old file (F037).
- Task line: rc-5 added a third reader (`_worktree_end._MARK`); `_release_plan` reads `W:` with a fourth regex. Same cause: no owner.
- Registry: rc-6 moved `invocation`'s read into `core/context_registry.py` (a34f3b73); `JsonContextStore` still parses with its own rule.

## Decisions

- These ADRs decide: 0018, 0019, 0045, 0106, 0111, 0119, 0122, 0123, 0126, 0127, 0135, 0136, 0137, 0140, 0141, 0142, 0146, 0150, 0152.
- The batch-grill rulings (operator, 2026-10-01: "Aceito D1–D6 (Recomendado)") are proposed one record each; only the operator's ruling accepts them (0151 M4).

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
| Closure memory pass | — | — | atoms `bug-ledger`, `backlog-ledger`, `release-lifecycle`, `audits-canon`, `worktrees`, `context-management`, `workspace-doctor`, `sdd-gate-v3`, `ci-preflight`, each rewritten once where changed |

## Gate — rc-5's G1–G6, applied to W3 and W4

- G1 Principles, never a line-count limit (ADR 0142):
  - Every unit walks DELETE → REBUILD → UPDATE → KEEP → ADD, and an ADD names what it could not delete or rebuild.
  - No question gets a second decider, and no rule contradicts another.
  - Readout at `<start>` and `<end>`, by the commands rc-8 §G1 also uses: production lines `git ls-files -z 'dadaia_workspace/*.py' | xargs -0 cat | wc -l`, test functions `git grep -hE '^\s*(async\s+)?def test_' -- 'tests/*.py' | wc -l`, test lines `git ls-files -z 'tests/*.py' | xargs -0 cat | wc -l`. At 44d023e6: 24,965 / 1,193 / 44,164.
- G2 `bugs.py status` lists no open record whose `caused_by` names a record or a commit of W3 or W4.
- G3 Every still-open bug is re-run at `<end>`; one that no longer reproduces is resolved citing the commit that removed its cause; the count is logged.
- G4 CI is green on the three OSes; `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0; no job's wall-clock grows past its rc-6 closure duration (run 36813899731); the ADR 0119 breach stays with rc-8 W5 (operator 2026-10-01: "Sim, base rc-6 (Recomendado)").
- G5 A test a DEL leaves dead leaves in the same commit; a new test states its intent and passes `dd-test-stewardship`'s admission; a new test file enters only when no file owns the behavior (0146 (5)).
- G6 At closure, the audit's open findings and `active[]` are re-audited against the merged waves, rc-8's SPEC is re-scoped before its PLAN, and one `dispositions` entry logs open before, resolved with a commit, open after.

## W3 — one grammar owner: acceptance

- AC3.1 One parser per grammar (0135; 0159, 0162):
  - The PLAN §1.1 Authorities table has one row per grammar of §Objective, one per JSONL ledger (bugs, backlog histo, ADRs, audit findings and histo, releases histo).
  - Each row names one owner that every other reader `consults`; the Status token is a pinned pair, `core/spec_status` ↔ `_release_schema.extract_status`.
  - Measure: 0135's contract test, in the file the PLAN finds owning it, fails when a package module parses a grammar outside its owner or pinned twin, and pins each owner script's location.
- AC3.2 Origin line (DEL `spec-origin-line-has-two-readers`; 0127; 0161):
  - `release.py` owns the 0161 parser. `doctor_release` (SPEC-DOC-048) and `_backlog_exit` import it.
  - Only the first Origin line counts. In the bug's repro, `backlog.py exit <id> --disposition delivered` is refused.
  - `release.py check` lists each carried id and reports one whose record does not point back: an entry's `delivered` exit, a bug's `resolved_release` or rejection, a finding's disposition `release`.
  - At closure, after the disposition sweep, this SPEC's Origin line is rewritten into the 0161 form with the §Origin map's ids, and `release.py check` traces it clean.
  - Command: `pytest tests/contract/test_release_script.py tests/unit/skills/test_release_implementation_release_script.py`.
- AC3.3 Task line (DEL `task-line-grammar-accepts-a-malformed-open-marker`; 0111):
  - The grammar, the marker and the `W:` field, lives once, in `_release_schema`.
  - `- [ ]**T-1**`, `+ [ ] T-1` and `* [-] T-1` all read as open to `release.py phase CLOSURE`, the doctor and `worktree.py merge`'s marker replay. The replay keeps "the most advanced state wins".
  - `_release_plan`'s overlap check reads `W:` through the owner. rc-6's T-050-117 line (the reviewer's `W:` conflict) parses to the paths it writes; a backticked path inside parentheses is named, not written.
  - `git grep -nE '_TASK_BLOCK_RE|_MARK = re' -- dadaia_workspace` prints nothing.
  - Command: `pytest tests/unit/skills/test_release_implementation_release_script.py tests/integration/test_worktree_lifecycle.py`.
- AC3.4 One readiness authority (DEL `release-ship-accepts-what-release-check-refuses`; FR `release-check-accepts-done-tasks-in-definition`):
  - In the ship bug's repro, `release.py ship` exits 1 with `check`'s refusal and fix, the release directory untouched.
  - `release.py check` judges every phase: under DEFINITION, a `[-]` or `[x]` marker, or a closure log entry after the live candidate's birth note, is a finding; `_release_tree._directory_findings`'s phase guard leaves.
  - Command: `pytest tests/unit/skills/test_release_implementation_release_script.py`.
- AC3.5 One JSONL reader (DEL `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger`):
  - Every ledger reader, script or package, splits on `\n` only, through one reader; none uses `splitlines()`.
  - In the bug's repro, `release.py new --origin bugs:ls-probe` seeds the SPEC, and `doctor_adr` reads a decisions record holding U+2028.
- AC3.6 One ledger schema engine (FR `ledger-schema-one-engine`; F103; 0018):
  - The doctor's ledgers section runs each script's `check` and builds no `jsonschema` validator for a ledger schema.
  - Command: `pytest tests/integration/test_backlog_doctor.py` plus the bug-ledger doctor case the PLAN names.
- AC3.7 Evidence fields (DEL `bugs-check-trusts-evidence-fields-unverified`; F002; 0160):
  - `diff_direction` leaves `bug-record-v1` and, once, every record. `bugs.py check` and `stats` derive it from the `evidence_diff` prefix, so `BUGS.jsonl` lines 653–654 read as one direction; `dd-bug-resolution` SKILL.md and `PILLAR-BUGS.md` follow.
  - `bugs.py resolve` refuses an `--evidence-seam` whose file or `def <name>` does not exist. `check` never re-judges a resolved seam: the 15 historic seams and rc-6's moved seam and pre-rebase SHAs stay as written.
  - Command: `pytest tests/unit/skills/test_bug_resolution_bugs_script.py`.
- AC3.8 Lineage (F012, F013):
  - `bugs.py check` refuses a `caused_by` cycle and a `caused_by` that names no record.
  - The 2 cycles, 3 dangling targets and 3 null `caused_by` of F012 and F013 are set by the `bugs.py` governance verb, never by hand; `check` exits 0.
- AC3.9 One context-registry parse (DEL `corrupt-context-registry-crashes-doctor-and-next-step`; F024; 0162):
  - `core/context_registry.py` is the one parse: `JsonContextStore` and the doctor's `_contexts()` read through it; `invocation._registry_contexts`'s fail-soft `or []` is deleted.
  - A top level that is not a `{"contexts": [...]}` object, `{}` included, is unreadable, never empty.
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
  - `backlog.py check` accepts `to-bug` in the history, and `specs/backlog/AGENTS.md` lists four dispositions.
  - The backlog kind's allowed set admits `specs/bugs/BUGS.jsonl`, so the registration and the exit share one worktree.
  - `release.py check` reports a `to-bug` target that was later rejected; `task-line-grammar-one-reader` exits by it (§Origin map).
- AC3.13 Commit shapes (F053, F054, F057; FR `gitflow-shape2-omits-backlog-histo`; 0106, 0136):
  - `dd-gitflow-default` §3a's staged-set column becomes "the kind's allowed set" (`_worktree_kinds.KINDS`): a backlog exit stages `BACKLOG.json` with its `_archive/backlog_histo.jsonl`, and shape 2's ADR message is the ADRs law's `docs(adr): propose|accept <slug>`.
  - The "alone" clauses and "+ picked bugs" leave, there and in `dd-release-definition` §4; each closure commit form (`chore(tasks)`, `docs(memory)`, `docs(specs)`, `chore(release)`) gets a row.
  - Check: `git grep -c 'picked bugs' -- dadaia_workspace/public` prints nothing; `tests/contract/test_law_states_what_the_code_does.py` asserts §3a's sets equal `KINDS`.
- AC3.14 Archive and milestones (F058, F059, F061):
  - `LINEAGE.md` states ADR 0152 (1): the release folder survives under `_archive/<v>/`.
  - A shipped sha and PR live in one structured field, which `release.py check` verifies for each release archived from 0.5.0 on.
  - Each candidate's `defined` and `implemented` stamps stay readable after the next one is born (shape: the PLAN, in `RELEASE-EVENTS.md`).
  - The 0.5.0 log gains one appended note on the 0.4.8 → 0.5.0 rename; no entry is rewritten.
- AC3.15 Audit close (F052): `audit.py close` refuses to run without `--sha`, and `LINEAGE.md` says how to recover a missing sha (`git log -S <audit-id> -- specs/audits`).
- AC3.16 Ratchet carry-overs (c4 AC6.3, AC6.6):
  - A destructive file call outside `features/spec_context/sweep.py` fails V38 or an import-linter contract; the PLAN measures today's sites first.
  - `_allowance_violations` asserts that the V38 and V39 closure allowances are subsets of their birth allowances. V37 is rc-9's (AC7.4), cited here as it stands.
- AC3.17 Law: `CONTEXT.md` gains **Grammar**, **Grammar owner** and **Pinned pair**; the scaffold `specs/releases/AGENTS.md` §2 states the 0161 Origin grammar once.
- AC3.18 Core-floor refusal messages (PR #276 review):
  - The message for each floor entry lives beside `CORE_FLOOR` in `core/workspace_layout.py`, and `gate_policy.evaluate` keys none on a string literal.
  - `classify_path`'s docstring states `_protection`'s order: projected → floor → glob.
  - Command: `pytest tests/unit/features/spec_context/test_gate_policy.py`.

## W4 — one text renderer: acceptance

- AC4.1 One renderer, one harness (F017; 0045, 0158, 0159):
  - `test_every_block_carries_a_fix.py`, `test_fix_lines_use_the_builder.py` and `test_fix_line_runs_in_every_shell.py` become one harness over every site, rc-6's DEC-11, missing-venv and root-whitelist refusals included; each case is re-homed by name, the PLAN listing them before and after (G5).
  - Per site it asserts exactly one fix line, in a 0158 form (a command whose argv0 exists, or `Operator action:`), no `<…>` placeholder, and a command the pre-gate allows when fed back as Bash.
  - It holds 0159's pinned-pair case: one argv through `cli_line` and `_specs.py` renders one line.
  - The root map §3 states the two forms (0158). The harness adds no wall-clock beyond the three files it replaces (G4).
- AC4.2 `DADAIA_BIN` is gone (DEL `dadaia-bin-still-honoured-after-adr-0045`): `git grep -n DADAIA_BIN -- dadaia_workspace` prints nothing. The three sites are `public/scripts/pre-push-ci-gate.sh`, `hooks/venv_guard.py` and `features/ci_preflight/service.py`.
- AC4.3 `--help` examples (DEL `help-examples-spell-the-blocked-bare-cli`):
  - Every `Run:` or example line in `--help` renders the venv CLI path through the renderer.
  - Command: `pytest tests/contract/test_cli_help_quality.py`, walking the whole command tree.
- AC4.4 Fix lines run as printed (DEL `fix-lines-are-not-one-runnable-command`; FR `doctor-tmp-expiry-foreign-owned-entry-never-clears`; 0158):
  - Each site the record names prints real values or 0158's `Operator action:` form: the session-record BLOCK (today `context bind '<ctx>'`); the pre-push refusal (the real work branch); the root-whitelist BLOCK, with a fix that clears it and names where the file belongs (F098's message is rc-8's AC6.4); `doctor --context nosuch` (one fix line); the onboarding first-pass Next; the gate scope BLOCK; the `backlog exit` hint (a disposition the entry can take).
  - `sweep.guarded`'s skip line for an expired entry it cannot delete names the owner and one fix line in a 0158 form with the real path; once the entry is gone, `doctor --fix` clears the finding.
  - Correlate: `_specs._bound_tree` stops routing `--specs` to `repos/<r>/specs` (unwritable outside `specs/audits/`, rc-5 AC1.1); it names the open worktree of the ledger's kind, else `worktree.py new <r> --kind <kind>`.
  - Correlate: `_backlog_exit`'s `--release` fix names the release it found.
  - Command: the AC4.1 harness.
- AC4.5 Ledger fixes (DEL `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids`):
  - Each ledger script's `check` emits its own fix, naming its governance verb.
  - `infrastructure/ledger_scripts.py`'s hand-edit fallback is deleted.
  - An invalid line gets one fix, not one per field.
  - In the bug's repro, the fix runs a `bugs.py` verb.
- AC4.6 One task-marker lifecycle and one closure ladder (DEL `implementer-persona-states-a-second-task-marker-lifecycle`; FR `rc-flow-asks-compliance-line-doctor-never-prints`; 0126, 0141):
  - The scaffold `specs/releases/AGENTS.md` §3 states the lifecycle once (`[ ]→[-]` at the start, `[-]→[x]` in the impl commit, reviewed at the worktree merge); `dd-software-engineer`, `dd-manager-orchestration` and `RC-FLOW.md` cite it.
  - `RC-FLOW.md` loses "marker stays `[-]`", "no per-task reviewer gate" and the "two simultaneous `[-]`" recovery (0141).
  - `RC-FLOW.md` step 8 asks only for what the doctor prints, its findings and exit code; `grep -c compliance` on it prints 0.
  - Measured by `tests/contract/test_law_states_what_the_code_does.py`.
- AC4.7 Consumer guidance (FR `consumer-guidance-names-no-library-toolchain`; F099):
  - The installed pre-push hook names no `dadaia ci preflight`, `docs/getting-started.md` no release-please; the harness runs the consumer refusals in a consumer-repo fixture.
  - The entry's `gh pr create` evidence is gone (`git grep` empty at c19383a7).
- AC4.8 Shipped text (F007):
  - The harness scans the command lines of `public/**/*.md` for a bare `dadaia`, `$DADAIA_BIN`, or a verb or flag the live command tree lacks, replacing the bare-CLI guard deleted with its test.
- AC4.9 The seventh fail-open path in law (FR `seventh-fail-open-path-law-line`; F080; rc-6 step-7b review):
  - The root map §3 (`public/data/AGENTS.md`) fail-open bullet adds the seventh path: an unreadable context registry judges nothing below `repos/` and `worktrees/` (`{"*"}`). Its first bullet states the root-whitelist scope the code judges: the root, `.dadaia/`, the closed-canon zones, the first level of `repos/` and `worktrees/`.
  - `README.md` and `docs/concepts.md` point to the root map §3 and restate no path.
  - `docs/getting-started.md` Level 1 lets "absent" govern both `.dadaiaignore` and `prompt.md`; the doctor paragraphs of README, getting-started and quickstart say a TTL expiry acts by zone class (OUTPUT held, EPHEMERAL deleted).
  - Command: `pytest tests/contract/test_law_states_what_the_code_does.py`, asserting the seven paths in that one place.

## Replaces

- `doctor_release._ORIGIN_RE` and `_backlog_exit`'s Origin regex.
- `_TASK_BLOCK_RE`'s marker reading, `_worktree_end._MARK` and `_release_plan`'s `W:` regex.
- `ship`'s own readiness judgement, and `check`'s DEFINITION skip.
- The `splitlines()` ledger reads (`_release_new.py:63`, `doctor_adr.py:30`).
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
- The six-path fail-open list and its README and concepts restatements.

## Risks

| Weakness | Mitigation |
|---|---|
| 0135: an owner on a hot path crashing or moving. | Owners stay off the pre-gate path; the package imports its own `public/skills` copy; a crash fails soft into one finding (F024); AC3.1 pins each location. |
| A pinned pair drifts (0159, 0162). | Its one contract test fails on any difference (AC3.1, AC4.1). |
| 0137: a registration without its exit; a target rejected later. | One backlog worktree holds both; `release.py check` reports a rejected target (AC3.12). |
| The 0160 strip rewrites every `BUGS.jsonl` line; a parallel `bug` worktree's union merge (0111) doubles a record. | The strip runs with no `bug` worktree open; `bugs.py check` refuses a duplicate id at merge. |
| The 0161 grammar breaks closed SPECs. | A one-clause line is its one-clause case; no second grammar exists. |
| The widened secret patterns hit published history. | Published history is never rescanned (§2a). |
| The root map passes its soft budget (8,304 B of 8,192, ADR 0143). | AC4.1 and AC4.9 edit existing bullets. |
| ADRs 0157, 0158, 0159, 0161 and 0162 amend an accepted record while proposed, so LEDGER-ADR-SCHEMA (M2) is red until ruled. | No push of the work branch before the rulings; a rejected record leaves the rule. |

## Carried to candidates 8+ (ADR 0140; specified by their own SPECs)

- The rows of rc-6's §Carried for W5, W6, W7 and the Promote PR are unchanged.
- rc-6's closure carries to rc-8 (W5, W6) stand as logged in `_RELEASE.json`.

## Open questions for the operator

- None. OQ1 (G4's wall-clock base) answered by the operator on 2026-10-01: rc-6's closure durations; see G4.
