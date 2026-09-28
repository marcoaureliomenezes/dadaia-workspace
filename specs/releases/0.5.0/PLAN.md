# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 4 — "systemic ambiguity remediation" (CRITICAL). SPEC FR1–FR9 (FR9 = test strategy); DEC-1..DEC-13 as recommended
(DEC-11 deferred); the grill decisions of 2026-09-26/27, cited as ADR ids `(00NN)` as in the SPEC. Evidence: `reports/main-thread/20260927-050-c4-evidence/` (`EV/`).
Paths are relative to `dadaia_workspace/` (`f/` = `features/`, `i/` = `infrastructure/`, skill scripts as
`<skill>/<file>`) unless they start with `tests/`, `specs/`, `.github/`.

## 1. As-is review

Read-only at `38b51b4b` (`EV/c4/asis-{A,B}.json`), test audits at `2c1faf65`/`8ba986e7` (`EV/c4/tests-audit-*.json`).
Only open work stays below: a package whose task is `[x]` lives in its commit and its `BUGS.jsonl` resolve
record. Every authority unit carries ≥ 2 prior bugs → REBUILD, not patch; `″` = as the row above.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `core/doctor_rules.py` with_fix; `f/spec_context/doctor.py` ContextDoctor.check…; `f/spec_context/doctor.py` WS-INVARIANT/WS-ENTRY rules +1 | CTX-URL-1, INV-4, INV-6, VENV-1 and the missing install ledger print… | 5 (`sa-unfixable-doctor-findings-say-doctor-fix`) | UPDATE | Default applies only when fixable. |
| `f/specs/doctor_governance.py` SPEC-DOC-035; `f/specs/doctor_structural.py` TREE-7; `f/specs/doctor_memory.py` SPEC-DOC-002L | A legacy file yields TREE-8 plus a second placement rule whose fix… | 5 (`sa-placement-rules-contradict-tree8`) | DELETE | Second placement authority. |
| f/specs/rules.py (rule rows) | ″ | ″ | UPDATE | Rows removed. |
| `f/specs/canon.py` TREE-8 fix | ″ | ″ | KEEP | The authority. |
| core/models/bugs.py; `container.py` bug store factory; `f/specs/doctor_governance.py` SPEC-DOC-033 +… +1 | The doctor validates bug records with its own model and prints an… | 7 (`sa-spec-doc-033-duplicates-bugs-check`) | DELETE | Second validator; its write methods have no caller. 8 fix commits on… |
| `f/specs/doctor_governance.py` SPEC-DOC-041; `f/specs/doctor_release.py` SPEC-DOC-048; public/schemas/bugs/bug-record-v1.schema.json +2 | ″ | ″ | UPDATE | Reads raw JSON or becomes a bugs.py check warning. |
| `dd-bug-resolution/_bugs_write.py` redact; `dd-backlog-definition/_backlog_write.py` redact; `core/models/histo.py` HistoRecord.redact +1 | bugs.py/backlog.py write private data verbatim that the push then… | 5 (`sa-ledger-write-seam-redacts-less-than-push-refuses`) | DELETE | Duplicate scrubber; replaced by refusal via _privacy. |
| `i/public_assets.py` stage; public/scaffold/bugs/AGENTS.md:43 +… | ″ | ″ | UPDATE | Copies _privacy.py and privacy_baseline.json next to ledger scripts. |
| public/skills/_shared/_privacy.py (stdlib, staged… | — | ″ | ADD | Stdlib scripts cannot import the package; one source copied by stage… |
| `f/backlog/doctor.py` BL-SCHEMA status whitelist; `f/backlog/doctor.py` BL-STALE | Doctor and script disagree on live status tokens; the doctor fix is… | 10 (`sa-backlog-status-has-no-single-authority`) | DELETE | Second vocabulary; 7 fix commits on the file. |
| dd-backlog-definition/_backlog_check.py; `dd-backlog-definition/_backlog_exit.py` check_exit; dd-release-implementation/_release_new.py +1 | ″ | ″ | UPDATE | Case decided once. |
| `f/specs/release_tree.py` ARCHIVED rules; `dd-release-implementation/_release_check.py` archive…; `f/specs/doctor_release.py` _TASK_MARKER_RE +… | gitflow step 11 `phase CLOSURE --sha --pr` is refused; shipped is… | 8 (`sa-promote-has-no-verb`) | DELETE | Archive = histo line + git. |
| dd-release-implementation/_release_phase.py | ″ | ″ | REBUILD | 10 ledger bugs on _release*; fixes stop pointing at refusing verbs;… |
| `dd-release-implementation/_release_schema.py`…; public/scaffold/releases/AGENTS.md + RELEASE-EVENTS.md… | ″ | ″ | UPDATE | ARCHIVED removed; regex widened to [-*+]. |
| `dd-release-implementation/release.py` ship | — | ″ | ADD | No verb records the promote; `phase` cannot carry it without a second… |
| core/spec_status.py extract_status | The doctor stops reading **Status:** only inside the first 30 lines. | 5 (`sa-status-line-has-two-parsers`) | REBUILD | 4 prior bugs on status reading; two parsers disagree on… |
| f/specs/rules.py SPEC-DOC-004 fix | appends a line | ″ | UPDATE | in-place replace; append creates the second status line that feeds… |
| scripts/_release_schema.py _STATUS_RE | anchored, whole document | ″ | KEEP | already the anchored rule; becomes the parity target |
| public/schemas/ADRs/decision-record-v1.schema.json…; tests/contract/test_adr_canon.py… | measured_by stops being refused by a prefix pattern; the audit judges… | 3 (`sa-adr-measured-by-pattern-refuses-real-checks`) | DELETE | DEC-8 (a); prose behind a prefix passes, real checks (npx vitest) fail |
| f/specs/doctor_adr.py; public/scaffold/ADRs/AGENTS.md:11,38 | schema only | ″ | UPDATE | receives the numbering rule (moved, not added) |
| f/specs/doctor_coherence.py SPECS-VERSION | The pre-push gate stops trusting the checked-out tree's stamp for the… | 6 (`sa-specs-tree-state-read-five-ways`) | DELETE | second reporter of the same fact |
| core/specs_version.py read_pattern_version; cli/commands/ci.py push_gate_check stamp read | int, malformed collapses to 0 | ″ | REBUILD | 5 prior bugs; five readers, five fixes |
| f/migrate/registry.py upgrade refusal; f/workspace/onboarding.py _specs_fix; f/chokepoints/push_gate.py | own messages | ″ | UPDATE | prints state().fix |
| f/specs/doctor_memory.py check_cat1_catalog_sync; f/specs/doctor_memory.py check_memory_atomicity | The doctor stops re-checking catalog sync with its own logic (CAT-1). | 9 (`sa-memory-atom-has-two-grammars`) | DELETE | -89 lines; memory.py check is the authority |
| scripts/_memory_schema.py parse; f/specs/memory_lint.py LINT-1 | accepts ambiguous inline lists | ″ | REBUILD | 8 prior bugs on the memory grammar; must refuse what it cannot… |
| scripts/_memory_catalog.py:81; i/ledger_scripts.py:130 fix line; public/scaffold/memory/AGENTS.md:34 | writes directory name | ″ | UPDATE | worktree-unstable output |
| f/specs/doctor_common.py resolve_live_release_id; core/workspace_layout.py rc-N rows | The doctor stops validating _RELEASE.json with its own rules. | 9 (`sa-release-json-validated-three-times`) | DELETE | doctor delegates |
| f/specs/release_tree.py | third validator | ″ | REBUILD | 8 prior bugs; keep TRIO/MEMORY only if not duplicated |
| core/specs_version.py RELEASE_SEMVER_RE; f/specs/rules.py SPEC-DOC-003/009 | accepts -suffix | ″ | UPDATE | remove group |
| scripts/_release_check.py / _release_tree.py | authority | ″ | KEEP | gains live_ids as the one live-release rule |
| f/certification/service.py _OWNED_DOCTOR_SECTIONS | certify stops skipping the workspace section. | 8 (`sa-reconcile-certify-skip-the-workspace-walk`) | DELETE | nobody judges the workspace section today |
| public/data/CONSUMER_VALIDATION_RECIPE.md | transcribes commands | ″ | REBUILD | 7 prior recipe bugs; cite certify ids |
| f/reconcile/service.py doctor step | context invariants | ″ | UPDATE | rename to context-invariants (DEC-13 a) |
| scripts/_backlog_subjects.py --resolve; core/models/backlog.py SubjectKind.PANEL | The backlog script stops declaring a subject RESOLVED from the… | 7 (`sa-subjects-resolve-is-circular`) | DELETE | 6 prior bugs; resolves against itself |
| f/backlog/subject_registry.py bind | no 'dadaia ' normalization | ″ | UPDATE | +2 |
| public/skills/dd-gitflow-default/SKILL.md:45; AGENTS.md (repo) :17-18 | The work-branch name stops being computed from the last tag. | 7 (`sa-live-work-branch-named-three-ways`) | DELETE | contradicts P-30 |
| f/spec_context/service.py _work_branch | tag+1 | ″ | REBUILD | c3-overlap; 6 prior version bugs |
| cli/commands/ci.py branch naming; release-please-config.json | tag+1 | ″ | UPDATE | c3-overlap |
| f/specs/canon.py:114 | specs init stops suggesting literal branch names. | 4 (`sa-principal-branch-defaults-to-main-and-cut-point-diverges`) | DELETE | always overwritten |
| cli/commands/specs.py _gitflow | detection + literals | ″ | REBUILD | 3 prior bugs; one detector |
| public/skills/dd-gitflow-default/SKILL.md §2a/§11; f/spec_context/service.py baseline | cut from principal | ″ | UPDATE | ADR 0035 |
| f/specs/doctor_closure_audit.py SPEC-DOC-036/038; i/jsonl_record_store.py write half; f/specs/doctor.py findings_store_factory | The doctor stops recommending audit close on its own reading of… | 6 (`sa-audit-close-archives-without-validating`) | DELETE | 5 prior audit bugs |
| scripts/_audit_verbs.py close | writes before checking | ″ | UPDATE | +3; check first, deferred/rejected when nothing resolved |
| core/models/histo.py vocabularies | core stops holding ledger vocabularies no library code reads. | 6 (`sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts`) | DELETE | 5 prior ledger-write bugs |
| tests/contract/test_required_evidence_has_one_home.py | pins core, exempts public/skills | ″ | REBUILD | its authority choice contradicts WP-48; must point at the script |
| scripts/_*_store.py _replace x4; dd-cli-library/registry.py save; scripts/_bugs_check.py +1 | identical, leak tmp | ″ | UPDATE | +3 each; clone of one another by design (self-contained scripts) |

### 1.1 Authorities

One row per question this candidate touches; one authority each; `consults` call it, `deleted` leave in
the task that resolves the row's bug. The table is the input the architecture lens checks (AC5.4).

| question | authority | consults | deleted |
|---|---|---|---|
| does a reap keep every earlier hold until its TTL | `sweep.move` | doctor `_reaped_destination` (per-reap bucket, `-N` on collision) | `move`'s `remove()`; the one-hold docstring; SKILL `--expired-only` claim |
| who may delete a workspace path | `f/spec_context/sweep.py` | every remover; V38; import-linter `shutil` contract | raw deleters named in the rows below |
| how a dead context's repo leaves disk | `DoctorService._reap_dead_repo` | `SpecContextService.dead`, INV-4/5 | `dead`'s raw `rmtree` |
| does a repo carry unpublished work | `git_objects.unpublished` over every local branch and linked worktree | `dead`, `DeadUnpushedCommitsError` | HEAD-only `GitCli.unpushed` rule |
| who owns an entry under a harness dir | install ledger `_reconcile_install_ledger` | `public install`, the doctor walk | `prune_stale_codex_tomls`, 3 legacy removers, `_RETIRED_CORE_RULES`, `_scan_harness_dirs`, `_active_harnesses` |
| may a root or `.dadaia/` top entry exist | `core/workspace_layout.verdict` | `root_whitelist._root_block_reason`, `gate_policy.classify` root arm, doctor `_scan_root`/`_scan_dadaia_top` | `_operator_exception`, `root_whitelist.main`, `_excepted`, `_migrate_exceptions`, root `specs/` ADDITIVE arm |
| who writes a repo's `AGENTS.md` and `tests/AGENTS.md` | `canon.REPO_LAW` + `scaffold_repo_law` (`specs init`) | `context baseline` publish set | guardrail consumer fan-out (3 helpers + aliases), `--repos-only`/`--workspace-only` |
| what one install writes | `InstallPlan` (no `only`) | rule table, `_reconcile_install_ledger`, `stage` | `--only`, `InstallPlan.only` branches |
| did a refused ledger write touch disk | each script's check of both candidate files before any write | backlog/bugs/audit/release verbs | `_bugs_store.append_raw`; histo-first `append_histo` |
| what is a secret or private term | `i/data/privacy_baseline.json` + operator denylist | pre-push matcher, `dead --commit`, `baseline`, `_shared/_privacy.py` at the ledger seam (byte parity) | `_bugs_write.redact`, `_backlog_write.redact`, `HistoRecord.redact`, `redact_text`, `first_privacy_hit` |
| how a private match is shown | `core/redaction.mask` | `denylist_scan`, `privacy_check` findings (incl. `:318`; 0086), `ContextRedactor` | the `_mask` copy |
| who builds the context redactor | `cli/redact.py` constructor (moved from `context._build_context_redactor`) | `doctor --redact`, `context list --redact` | doctor `_build_redactor`, `_resolve_caller_context_and_slug` |
| is every tool call judged | `hooks/pre_gate` | every rendered wrapper | explicit-allow output, `venv_guard`'s own tool-name read |
| how a harness wires and translates the gate | `HOOK_DIALECTS` | `_common.tool_name`, `resolve_session_id`, Kimi shim, `registry.json`, `agentic-entities.md` | per-wrapper parsing; hand-written parity claims |
| which interpreter runs a hook | the self-locating wrapper | Kimi shim, Claude/Codex hooks | `runtime_config._python_bin` fallback |
| which commands Codex runs unprompted | `_render_codex_command_policy_rules` | registry mandate, `.codex/rules` | `find`, bare `sed` allows |
| how a fixed specs section is written | one symlink-refusing writer (`atomic_write`, `O_NOFOLLOW`) | `doctor --fix`, `specs upgrade` | `restore_fixed_sections`, `_fixed_renders`, `plan_fixed_sections` |
| where the pre-push gate is installed | `git rev-parse --git-path hooks` (one resolver) | installer, doctor HOOKS | hard-coded `<repo>/.git/hooks` |
| the workspace root | `resolve_workspace_root` | invocation, migrate, `state_v2`, `registry.py`, `memory_lint`, `context show` | `WORKSPACE_ROOT` step, `migrate._resolve_workspace_root`, cwd walks |
| is the session bound, and to what | `invocation.resolve_bind` | gate, `ctx_inject`, onboarding, `context show`, `_specs_resolution` | env-first reads; 4 caller rules |
| how a fix line is spelled | `core/cli_line` | `venv_guard`, `push_gate`, `gate_policy`, capabilities, stores | bare `dadaia`, `&&` lines, `_EXECUTABLE_TOKENS` |
| who prints a refusal | `cli/_fail.fail` (exit 1; Click usage keeps 2; 0073) | every command | `init._refuse`, `reports.err_console`, Rich printers, exit 3 |
| what fix an unfixable finding carries | the finding's own `fix_line` | `doctor_rules.with_fix` (fixable only) | `rule_fix`'s `doctor --fix` default |
| where a stray specs file belongs | TREE-8 (`canon.py`) | the doctor | SPEC-DOC-035, TREE-7, SPEC-DOC-002L |
| which registry version is readable | `json_context_store.parse_schema_version` | migrate, invocation, `context`, doctor | `state_v2._detect_schema_version` |
| is a bug record valid | `_bugs_check.py` over `bug-record-v1.schema.json` | doctor LEDGER-BUGS-SCHEMA | `core/models/bugs.py`, SPEC-DOC-033, container bug store, `_resolve_derived_enums` |
| a backlog entry's live status | `backlog.py check` (`_backlog_schema`) | the doctor | BL-SCHEMA whitelist, BL-STALE; `deferred` leaves TERMINAL (0076) |
| what a release picks | the SPEC `**Origin:**` line | `release.py new`, `backlog.py exit` | `picked` requirement, `**Consumes:**` gating |
| how a promote is recorded | `release.py ship` | RC-FLOW, gitflow §11 | ARCHIVED phase, `_archive/<v>/_RELEASE.json`, archive rules |
| is a task open | `_release_schema.UNFINISHED_RE` | doctor SPEC-DOC-024 | `doctor_release._TASK_MARKER_RE` |
| which `**Status:**` line counts | `core/spec_status.extract_status` (anchored, first, no window) | `_release_schema._STATUS_RE` (parity copy), SPEC-DOC-004 fix | 30-line window; append repair; blockquote form (0075) |
| what `measured_by` may name | `doctor_adr` (free text) | the audit | schema pattern |
| the specs-tree state | `core/specs_version.state` | pre-push (from the pushed commit), `specs upgrade`, onboarding, `push_gate` | SPECS-VERSION; malformed → 0 |
| is a memory atom valid | `_memory_schema.parse` | LINT-1, `memory.py catalog generate` | CAT-1, `check_memory_atomicity`, SPEC-DOC-008 |
| is `_RELEASE.json` valid; which release is live | `release.py check` (`live_ids`) | doctor LEDGER-RELEASE-SCHEMA, core phase read | `release_tree` rules, `resolve_live_release_id`, rc-N rows, SemVer suffix; `next/` never live (0077) |
| is an upgraded workspace clean | `dadaia doctor` workspace rules | `certify`, reconcile, the recipe | `_OWNED_DOCTOR_SECTIONS`, transcribed recipe lines |
| which checks gate a merge | `ci.yml` + the versioned required-checks file (0078) | `release.yml` (`workflow_call`), `ci_preflight.checks_for` | `release.yml`'s own matrix |
| which repos belong to a context | the context registry (`repo_slug_for_context`) | handoff self-pull, store, `specs init --context` | name fallback |
| the running version | `provider_version()` | `--version`, capabilities, reconcile, `python_env`, export | five other version reads |
| does a subject ref resolve | doctor `SubjectRegistry` | backlog doctor | `_backlog_subjects --resolve`, `SubjectKind.PANEL` |
| may the reviewer write | persona frontmatter `tools`/`read_only` | render, `codex_assets` | stale body text, `_ACTIVITY_CLASSES`, model fallback |
| the canon table text | `render_registry_tables` (in `core/workspace_layout`) | `stage`, `specs init`, TREE-5 | the unrendered copy |
| a path's class (PROTECTED/ADDITIVE/MUTATING) | `classify_path` in `core/workspace_layout` (literal hook-wiring floor; 0055) | gate, `doctor_structural` | basename `_is_law_path`, hand ADDITIVE prefixes, law duplicates |
| where tool caches live | the zone registry: `.dadaia/tmp/<tool>-cache` (0080) | `pyproject.toml`, harness env block, markers | the `.dadaia/.cache` zone; relative `../../` paths |
| when a zone entry expires | the zone TTL in `workspace_layout`, run by the doctor walk via `sweep` | markers, handoffs | `reap_markers`, `SENTINEL_GC_TTL_SECONDS`, `Handoff.expires_at` family |
| what version a release publishes | release-please (`release-please-config.json`, `release-as`) | `baseline` | tag+1, PyPI+1 minters |
| the live work branch name | `<work prefix>` + the live `_RELEASE.json` id | `baseline`, the gate | tag-derived naming |
| the principal branch | the `specs init` `_gitflow` detector | `baseline` | `canon.py:114` literal default; cut-point stub |
| is an audit closable | `audit.py close` | the doctor | SPEC-DOC-036/038, `JsonlRecordStore` write half, `findings_store_factory` |
| which staged asset is consumed | its real consumer | `public doctor` | `build_agents_index`, `check_codex_rule_corpus_reachable` |
| must a handoff carry `self_pull` | `handoff-v1` schema, v1.2 only | `Handoff.validate`, `reports validate` | v1/v1.1 routing, `handoff_index.py:507` |
| the `specs upgrade` target | `CANONICAL_SPECS_VERSION` | `specs upgrade` (refuses two-tier; 0082) | `--target`, the old-layout guard |
| a ledger's terminal vocabulary | the stdlib scripts' `_*_schema` | the doctor (exact compare; 0083) | `core/models/histo.py` vocabularies |
| how a ledger script writes atomically | `_bugs_store._replace` (`newline=''`, tmp cleanup) | 3 script `_replace` copies (V37 `parity:` keys), `registry.py save` | leaking tmp writers |
| where a rule lives | the code or its test | law text (points at it) | false docstrings, the restated venv rule |
| what consumer law may say | the consumer's own tree | projected skills, templates | library facts; the `surface` library arm |
| where a domain term is defined | `CONTEXT.md` | navigator glossary, maps | `Part 1/Part 2`, "PyPI + 1 patch" |
| does a PLAN give each question one authority | `_release_phase._refuse_missing_as_is_table` | `release.py new` skeleton, S10, the architecture lens | — |
| is a library fact defined twice | V37 in `test_slop_ratchets.py` | Axis 3 verdict | `test_required_evidence_has_one_home.py` |
| does a doctor fix clear its finding | `test_doctor_fix_lines_clear_their_finding.py` cases | V39 (case or `report-only` key) | stale `_EXEMPT` entries |
| which behaviour a test asserts | the statement `<bug-id>#<id>` in `EV/c4/tests-audit-*.json` (enters `QUALITY.md` `### Behavior rows` at closure) | `Intent:` docstrings, the AC9.2 contract test | uncited CONTRACT tests |
| how a test runs a hook | the rendered wrapper spawned as production | every hook test | `WORKSPACE_ROOT` injection, `_POLICY_DRIVER` |
| how a test gets git | the real-git tmp fixture | service/push tests | `FakeGitClient`, 4 `ObjectSource` fakes |
| which roots may a dadaia process act on | `core/workspace_resolver` fence (`DADAIA_FENCED_ROOTS`; 0088) | the suite, every mutating probe, `.dadaia/AGENTS.md` law line | — |

## 2. Strategy per FR

Evidence (committed with the definition): `reports/main-thread/20260927-050-c4-evidence/` (below `EV/`):
as-is `EV/c4/asis-{A,B}.json`, test audits `EV/c4/tests-audit-*.json`, strategy `EV/c4/TESTS-ARCHITECTURE.md`,
the verified hunt `EV/verify/`, grill handoffs `EV/handoffs/`. Every package follows one contract (SPEC
resolution contract; FR9):

1. **Behaviour first.** A package's statements are the only expected values. Their ids are
   `<bug-id>#<id>` exactly as in `EV/c4/tests-audit-*.json`, listed under each wave table; a RED test
   declares `Intent: CONTRACT — <bug-id>#<id>` (AC9.2). The rows enter `QUALITY.md` `## Test
   architecture` → `### Behavior rows` for each RESOLVED bug at the closure memory pass
   (dd-product-engineer), never ahead of the code.
2. **RED at the public seam** (AC9.3) — CLI verb, script subprocess, or the rendered hook wrapper through
   `pre_gate`; an in-process test asserts only the authority function. The RED fails at the definition
   commit for the structural cause (two readers disagree, a deleter runs), never a symptom.
3. **One commit, shape 3:** production + regression test + the `BUGS.jsonl` resolve line,
   `fix(bugs): <id> — <cause>`. The same commit deletes the loser mechanism, its tests and its fakes
   (`git grep -w <symbol> tests/` empty, AC9.6) and REWRITEs tests that reach the authority's answer
   through a loser. The task flip is a separate `chore(tasks)` commit.
4. **Forced-pass commits are undone** where the audit names one: the pre-fix assertion is restored when it
   states the behaviour, deleted when it pinned a loser; a changed assertion cites a statement id (AC9.8).
5. **Cross-check** only while two readers live; it dies in the commit that deletes the loser (AC9.6).
6. **Goldens** (AC9.7): a deleted code's golden rows and `_EXEMPT`/`PLANTS` entries leave with it; a
   surviving row never changes in a commit touching `dadaia_workspace/**`.
7. **Net-positive ceilings** (AC1.1, AC2.1, AC3.1, AC4.1): `context dead` +3, the Cursor/Copilot/Devin
   gate +12, the hooks-path install +5, unfixable findings +7, unrendered law +4, principal detection +2,
   path classes +5. Every other package is net ≤ 0. A value is a ceiling: exceeding it stops the task for
   the architecture lens; the ceiling is never raised.
8. `Δprod` = as-is production + law text; `Δtest` = audit add − delete, before AC9.9's pruning.

### Open packages (RED seam · deletes · Δprod/Δtest)

| row | RED seam | deletes: code · tests · fakes | Δprod | Δtest |
|---|---|---|---|---|
| WP-19 | run each printed fix, re-run the doctor: finding gone; no unfixable says `doctor --fix` | `rule_fix` default · 2 HOLLOW | +2 | +100 |
| WP-20 | off-canon files: one finding each; its fix → zero | SPEC-DOC-035, TREE-7, -002L · 10 LOSER · undo `9ebefd5f` | −115 | −40 |
| WP-22 | doctor × `bugs.py check` parity; AST: no `core.models.bugs` | `core/models/bugs.py`, SPEC-DOC-033 · `test_bug_record.py` (23), 7 LOSER · undo `0fee8cdd` | −640 | −670 |
| WP-23 | secret matrix: seam refuses ⇔ push refuses; `BUGS.jsonl` byte-intact | 3 `redact` copies (ADD `_shared/_privacy.py`) · 4 LOSER | −60 | +10 |
| WP-24 | `postponed`/`Deferred` agree; `new --origin` → `exit delivered`, no hand edit | BL-STALE, whitelist · 4 LOSER, 2 HOLLOW, 1 DUP · undo `68658783` | −80 | −40 |
| WP-25 | `new`→IMPLEMENTATION→CLOSURE→`ship`→`new` by verbs, doctor clean; `* [ ]` refuses CLOSURE | ARCHIVED, second regex (ADD `ship`) · 14 LOSER, 2 HOLLOW · undo `b50f0c97` | −40 | −70 |
| WP-26 | parity table of both status readers; SPEC-DOC-004 fixed in place | window, append · 5 REWRITE · undo `b50f0c97` | −5 | +60 |
| WP-27 | `measured_by: npx vitest run` clean; a duplicate `0049` flagged | the pattern · 2 LOSER, 4 DUP · undo `64e4885c` | −15 | −10 |
| WP-28 † | pre-push reads the pushed commit: malformed + stray → BLOCKED; one fix everywhere | SPECS-VERSION · 3 LOSER | −34 | +145 |
| WP-29 | generate, check, LINT-1 give one verdict; tags `["a, b", c]` refused | CAT-1, atomicity · 6 LOSER · undo `b50f0c97` | −155 | −10 |
| WP-30 | phase `closure`: one finding with a runnable fix; `next/` not live; `new` refuses while `check` is red | `release_tree` rules, rc-N · 14 LOSER, 4 DUP, 3 HOLLOW · undo `987e76d4` | −105 | −100 |
| WP-31 | `certify` reports workspace slop; every recipe line passes the wheel's `--help` | `_OWNED_DOCTOR_SECTIONS` · 2 LOSER | −126 | +116 |
| WP-35 | `cli:dadaia context bind` accepted; no surface says RESOLVED | `--resolve`, PANEL · 3 LOSER | −25 | +39 |
| WP-41 † | tag v0.4.7 + live 0.5.0: baseline, gate and `work_name` say `feature/0.5.0` | tag+1 · 1 LOSER · undo `ffb30aa0` | −3 | +37 |
| WP-42 † | origin/HEAD=develop, master present: principal master | literal default · 1 HOLLOW | +2 | +44 |
| WP-43 | `BANANA`: `audit.py close` refuses, dir kept | SPEC-DOC-036/038, write half · 13 LOSER, 1 HOLLOW · undo `27ed26fb` | −182 | −340 |
| WP-48 | failing `os.replace` leaves no `.tmp`; a bad histo line flagged | `histo.py` sets · 3 LOSER | −5 | +45 |

Statement ids (RED cites them; `EV/c4/tests-audit-*.json`):
- WP-19: `sa-unfixable-doctor-findings-say-doctor-fix#S1..S6`
- WP-20: `sa-placement-rules-contradict-tree8#B1..B6`
- WP-22: `sa-spec-doc-033-duplicates-bugs-check#B1..B8`
- WP-23: `sa-ledger-write-seam-redacts-less-than-push-refuses#B1..B6`
- WP-24: `sa-backlog-status-has-no-single-authority#B1..B8`
- WP-25: `sa-promote-has-no-verb#B25-1..B25-8`
- WP-26: `sa-status-line-has-two-parsers#B26-1..B26-4`
- WP-27: `sa-adr-measured-by-pattern-refuses-real-checks#B27-1..B27-4`
- WP-28: `sa-specs-tree-state-read-five-ways#B28-1..B28-7`
- WP-29: `sa-memory-atom-has-two-grammars#B29-1..B29-6`
- WP-30: `sa-release-json-validated-three-times#B1..B7`
- WP-31: `sa-reconcile-certify-skip-the-workspace-walk#B1..B5`
- WP-35: `sa-subjects-resolve-is-circular#B1..B5`
- WP-41: `sa-live-work-branch-named-three-ways#B41-1..B41-5`
- WP-42: `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-1..B42-6`
- WP-43: `sa-audit-close-archives-without-validating#B43-1..B43-6`
- WP-48: `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.1..48.6`

### FR7, FR8, FR9 AC9.9–9.11 — gate, shrink, test budget

- Closure evidence (engineer): the two AC8.1 measures over the candidate range; the allowance at birth ⊆
  at closure; mutmut on the §1.1 authority functions (AC9.10); the mirrored and cross-checked counts of
  resolved packages against the baseline (AC9.11); the fenced rubric D1–D10 on the wheel built from the
  promote head. Dispositions and the 0.5.0-only override are the product engineer's closure log.
- **Projection, production + law:** waves −2587, mechanism +18, `DADAIA_FENCED_ROOTS` +3 → **−2566**.
- **Projection, tests:** audits +852, fakes and driver −500, mechanism +160, `DADAIA_FENCED_ROOTS` +10 → **+522**
  before pruning. AC9.9 requires ≤ 0 at closure, so the suite-wide pruning pass (DELETE-HOLLOW,
  DELETE-DUP, text pins outside law-file canon, the `WORKSPACE_ROOT`-rung tests) must remove ≥ 522
  lines, run as a reviewer QA-lens verdict the engineer executes; a positive net is a HIGH finding.

## 3. Seams

- Refusal: CLI verb → `cli/_fail.fail`; fix text only from `core/cli_line`.
- Gate: rendered wrapper → `pre_gate` → `classify_path`/`verdict` in `core/workspace_layout`.
- Removal: every remover → `sweep`; the TTL only from `workspace_layout`.
- Git hooks: installer and doctor → one `--git-path hooks` resolver.
- Ledgers: the stdlib scripts are the authority; the doctor imports the packaged script modules (as
  `_bugs_check` today), never a parallel model.
- Secrets: one data file; the library matcher and `_shared/_privacy.py` pinned by byte parity (V37 key).

## 4. Risks

- **Required checks are operator-owned.** WP-32's file is the list (AC1.7); AC6.7 blocks a merge only once GitHub
  branch protection lists every `ci.yml` job, Compliance included (SPEC operator action).
- **Load flakiness in the local preflight.** The real-git fixture and hook spawns raise wall time; a
  timing failure under load is a flake → `quarantine` + a registered bug, never a raised timeout; no
  `sleep`/barrier; an unregistered pass-on-retry is a failure.
- **Gate-not-enforced harnesses** cap D8/D9; the ≥ 80 score is measured, not assumed.
- **V35 skill-corpus ceiling (2863 lines, down-only).** FR5 grows four skills; the growth is paid by the
  skill-text deletions of WP-02, WP-24, WP-25, WP-49 and FR-8 within the candidate, else V35 fails.
- **Test budget** (AC9.9): +522 before pruning; the pruning pass is sized in §2 and measured at closure.

## 5. Contradictions routed to the main thread (planned as stated here)

1. SPEC AC9.1 lands behaviour rows in `QUALITY.md` "before the first fix"; ruling R1 lands them at the
   closure memory pass for resolved bugs. Planned per R1.
2. WP-19 (+7) equals its SPEC ceiling (AC2.1): no margin.
