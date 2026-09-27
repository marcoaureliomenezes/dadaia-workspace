# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 4 — "systemic ambiguity remediation" (CRITICAL). SPEC FR1–FR9 (FR9 = test strategy); DEC-1..DEC-13 as recommended
(DEC-11 deferred); the grill decisions of 2026-09-26/27, cited as ADR ids `(00NN)` as in the SPEC. Evidence: `reports/main-thread/20260927-050-c4-evidence/` (`EV/`).
Paths are relative to `dadaia_workspace/` (`f/` = `features/`, `i/` = `infrastructure/`, skill scripts as
`<skill>/<file>`) unless they start with `tests/`, `specs/`, `.github/`.

## 1. As-is review

Read-only at `38b51b4b` (`EV/c4/asis-{A,B}.json`), test audits at `2c1faf65`/`8ba986e7` (`EV/c4/tests-audit-*.json`); re-measured when
`release.py new` opens the candidate after candidate 3 closes (every † unit). Ledger: 49 open —
the 48 `sa-*` bugs below plus `pre-push-gate-never-runs-under-core-hookspath` (HIGH, 0057, 0085);
`sa-pre-push-and-publish-scan-disagree-on-secret-shapes` was resolved in candidate 3 (T-050-22, `-83`
lines) and leaves this table. Every authority unit carries ≥ 2 prior bugs → REBUILD, not patch.
Rows are grouped per package and verdict; `″` = as the row above; the first row of each package names
its bug and the count of ledger bugs on its units.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `f/spec_context/sweep.py` move | A same-day re-reap of one origin deletes the earlier hold before its… | 4 (`sa-reaper-destroys-its-own-hold-before-ttl`) | REBUILD | Carries the destroy-before-TTL defect plus 3 prior reaper fixes;… |
| `f/spec_context/doctor.py` _reaped_destination; `public/skills/dd-cli-library/SKILL.md` step-6; `cli/commands/doctor.py` expired_only option | ″ | ″ | UPDATE | Bucket becomes <YYYYMMDDTHHMMSSZ> (with -N on collision) so each reap… |
| `f/spec_context/sweep.py` remove | ″ | ″ | KEEP | Still the EXDEV fallback's origin removal and the TTL delete… |
| `f/spec_context/service.py` dead | context dead deletes a repo irreversibly with rmtree instead of… | 8 (`sa-context-dead-removes-repos-outside-the-reaper`) | REBUILD | 24 ledger bugs on service.py and 5 prior dead() fixes (unborn clone,… |
| `f/spec_context/service.py` DeadUnpushedCommitsError; `i/git_subprocess.py` GitCli.unpushed; `f/spec_context/doctor.py` _reap_dead_repo +1 | ″ | ″ | UPDATE | Docstring shrinks to the real rule. |
| `f/spec_context/service.py` create rollback… | ″ | ″ | KEEP | Removes only what the same call just cloned; the one legitimate raw… |
| `i/projection_rules.py` prune_stale_codex_tomls; `i/install_helpers.py` remove_retired_core_rules; `i/install_helpers.py`… +2 | public install unlinks .codex/agents/*.toml not in the current… | 5 (`sa-public-install-unlinks-operator-files-outside-its-ledger`) | DELETE | Second prune path beside the ledger reconciler; judges by glob, not… |
| `i/public_assets.py` install (prune calls) | ″ | ″ | UPDATE | Four call sites and imports removed. |
| `hooks/root_whitelist.py` _operator_exception; `hooks/root_whitelist.py` main (back-compat wrapper); `f/spec_context/doctor.py` _excepted +1 | The gate ALLOWs an existing non-whitelisted root entry that the… | 10 (`sa-gate-allows-root-entries-the-reaper-moves`) | DELETE | Second glob matcher with a different rule than doctor._excepted. |
| `hooks/root_whitelist.py` _root_block_reason; `f/spec_context/doctor.py` _scan_root | ″ | ″ | REBUILD | 4 fix commits and 4 ledger bugs (misses nested writes, message… |
| `f/spec_context/gate_policy.py` classify (root arm); `f/spec_context/doctor.py` _scan_dadaia_top; `public/data/AGENTS.md` §4 root line +1 | ″ | ″ | UPDATE | Root specs/ arm deleted; .dadaia/<non-zone> and .dadaia/states/<new>… |
| hooks/sdd_post_gate.py | ″ | ″ | KEEP | Calls doctor.reap; becomes correct once gate and doctor share verdict. |
| `core/workspace_layout.py` verdict | — | ″ | ADD | No existing unit is shared by gate and doctor; the classifier bodies… |
| `f/spec_context/doctor.py` _scan_harness_dirs; `f/spec_context/doctor.py` _active_harnesses | doctor --fix and the PostToolUse reaper move… | 4 (`sa-doctor-reaps-harness-owned-entries`) | DELETE | The walker judges entries a harness writes without passing the gate;… |
| .dadaia/states/instance_exceptions.txt (instance) | ″ | ″ | UPDATE | Operator removes dm-chain-*, settings.local.json, worktrees globs… |
| core/harness_registry.py; f/spec_context/gate_policy.py / hooks/sdd_gate.py | ″ | ″ | KEEP | DEC-2 (b) not taken; no per-harness native canon. |
| `i/workspace_guardrail.py` _consumer_repos_for_root; `i/workspace_guardrail.py` _classify_consumer_agents; `i/workspace_guardrail.py` _doctor_consumer_pair_lines +2 | public install copies the root map into repos/<slug>/AGENTS.md and… | 8 (`sa-public-install-writes-the-root-map-into-product-repos`) | DELETE | Consumer fan-out discovery. |
| `i/workspace_guardrail.py` _install_guardrail_pair… | ″ | ″ | REBUILD | 5 fix commits; a second writer of repo law. Shrinks to the… |
| `i/workspace_guardrail.py` _agents_md_source; `i/public_assets.py` install (consumer fan-out + scope); `f/specs/canon.py` REPO_LAW +1 | ″ | ″ | UPDATE | templates/AGENTS.md precedence removed. |
| `cli/commands/public.py` install --only; `i/projection_rules.py` InstallPlan.only + branches | `public install --only X` prunes every other family (settings.json… | 4 (`sa-scoped-public-install-prunes-the-gate-wiring`) | DELETE | Unused scoping flag (no doc or skill uses it). |
| `i/public_assets.py` install (full= predicate); `i/public_assets.py` stage | ″ | ″ | UPDATE | full= collapses to `plan.harness is None` once only and scope (WP-07)… |
| `i/public_assets_common.py` is_ignored_public_asset | ″ | ″ | KEEP | The one asset filter. |
| `dd-bug-resolution/_bugs_store.py` append_raw | `backlog.py exit` and `bugs.py archive` say 'nothing was written'… | 5 (`sa-ledger-verbs-append-histo-before-validating-the-pair`) | DELETE | Unchecked writer. |
| `dd-backlog-definition/_backlog_store.py` append_histo | ″ | ″ | REBUILD | Fragment check is the second validator; rebuilt as a pair write… |
| `dd-backlog-definition/backlog.py` _exit; `dd-backlog-definition/_backlog_write.py` new; `dd-bug-resolution/bugs.py` _archive +1 | ″ | ″ | UPDATE | Builds candidate pair, checks, then writes. |
| `cli/commands/doctor.py` _build_redactor +… | public doctor prints the raw private denylist term the pre-push masks. | 5 (`sa-private-match-rendering-has-three-renderers`) | DELETE | Third redactor builder. |
| `f/chokepoints/denylist_scan.py` _mask; `i/privacy_check.py` public-privacy findings; `cli/commands/context.py` _build_context_redactor +2 | ″ | ″ | UPDATE | Moves to core/redaction.mask. |
| `hooks/venv_guard.py` tool-name read | Cursor rides beforeShellExecution, so file writes are never judged. | 6 (`sa-gate-blind-on-cursor-copilot-devin`) | DELETE | Duplicate of _common.tool_name. |
| `i/runtime_transforms/hook_wrappers.py` _translator; `i/runtime_transforms/hook_wrappers.py` HOOK_DIALECTS…; `hooks/_common.py` tool_name +4 | ″ | ″ | UPDATE | Deny-only output. |
| `i/runtime_transforms/codex_assets.py`… | Codex runs `sed -i` and `find … -exec` unsandboxed and without a… | 4 (`sa-codex-policy-allows-write-capable-commands`) | REBUILD | 3 prior bugs on the same rules file (undocumented allowed command,… |
| `public/entities/registry.json` codex-command-policy…; .codex/rules/dadaia-command-policy.rules (instance) | ″ | ″ | UPDATE | True statement. |
| `f/migrate/upgrade.py`… | specs upgrade writes through symlinks outside the tree (CWE-59) while… | 6 (`sa-specs-upgrade-writes-through-symlinks`) | DELETE | Duplicate of the doctor's fixed-section repair. |
| `f/migrate/upgrade.py` upgrade | ″ | ″ | REBUILD | 3 fix commits; becomes version hop + stamp + the repair set, called… |
| `core/atomic_write.py` atomic_write; `f/specs/doctor_memory.py` fix_fixed_section; f/specs/doctor_structural.py (TREE-5 fix) +1 | ″ | ″ | UPDATE | Refuses a symlinked destination (the one policy). |
| `core/invocation.py` _workspace_root (WORKSPACE_ROOT…; `cli/commands/migrate.py`…; `f/specs/memory_lint.py` main cwd default | WORKSPACE_ROOT in the environment turns the whole gate into ALLOW. | 8 (`sa-seven-workspace-root-rules`) | DELETE | Env override with a generic name. |
| `f/migrate/state_v2.py` plan_migration; `dd-cli-library/registry.py` _default_registry; `core/workspace_resolver.py` resolve (--workspace) +2 | ″ | ″ | UPDATE | Missing registry is an error. |
| `core/invocation.py` resolve_bind | With a native session id, DADAIA_CONTEXT overrides the registry and… | 11 (`sa-bind-has-two-stores`) | REBUILD | 12 prior bind bugs across heartbeat, ctx-inject, show, aliases — the… |
| `f/workspace/onboarding.py` _unbound; `hooks/ctx_inject.py` main header/injection; f/spec_context/injection_policy.py +3 | ″ | ″ | UPDATE | Asks resolve_bind. |
| `hooks/venv_guard.py` _VENV_BIN/fix | Fix lines cite a bare `dadaia` the gate blocks. | 10 (`sa-fix-lines-not-built-by-cli-line`) | REBUILD | 4 fix commits; fixes become absolute. |
| core/cli_line.py; `f/chokepoints/push_gate.py` object-read refusal; `f/spec_context/gate_policy.py` projected-law deny fix +6 | ″ | ″ | UPDATE | Gains shell_line only if no existing builder covers pip/python. |
| `cli/commands/init.py` _refuse; `cli/commands/reports.py` err_console + exit codes | Rich wraps fix lines at 80 columns in non-TTY output. | 7 (`sa-rich-printer-wraps-fix-lines`) | DELETE | Second printer. |
| `cli/commands/public.py` doctor output | ″ | ″ | REBUILD | 6 fix commits; plain echo, exit semantics. |
| `cli/main.py` _safe_app; cli/commands/specs.py + migrate.py refusals; cli/commands/context.py resolution errors +1 | ″ | ″ | UPDATE | Calls _fail. |
| cli/_fail.py | ″ | ″ | KEEP | Already the intended authority; becomes the only one. |
| `core/doctor_rules.py` with_fix; `f/spec_context/doctor.py` ContextDoctor.check…; `f/spec_context/doctor.py` WS-INVARIANT/WS-ENTRY rules +1 | CTX-URL-1, INV-4, INV-6, VENV-1 and the missing install ledger print… | 5 (`sa-unfixable-doctor-findings-say-doctor-fix`) | UPDATE | Default applies only when fixable. |
| `f/specs/doctor_governance.py` SPEC-DOC-035; `f/specs/doctor_structural.py` TREE-7; `f/specs/doctor_memory.py` SPEC-DOC-002L | A legacy file yields TREE-8 plus a second placement rule whose fix… | 5 (`sa-placement-rules-contradict-tree8`) | DELETE | Second placement authority. |
| f/specs/rules.py (rule rows) | ″ | ″ | UPDATE | Rows removed. |
| `f/specs/canon.py` TREE-8 fix | ″ | ″ | KEEP | The authority. |
| `f/migrate/state_v2.py` _detect_schema_version | An int 3 / '4' / '0' registry loops list→migrate→list or converts… | 4 (`sa-registry-schema-version-has-three-grammars`) | DELETE | Second grammar. |
| `i/json_context_store.py` _load | ″ | ″ | REBUILD | 3 fix commits; gains the one parser. |
| `f/migrate/state_v2.py` plan_migration/migrate rows; core/invocation.py / cli/commands/context.py /…; f/spec_context/doctor.py | ″ | ″ | UPDATE | Rewrites only ativo/inativo rows; preserves alive/dead rows whole. |
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
| .github/workflows/release.yml | release.yml stops redeclaring the test matrix. | 7 (`sa-doctor-job-not-a-required-check`) | REBUILD | 6 prior CI bugs; reuse ci.yml |
| f/ci_preflight/service.py checks_for; branch protection (out of repo); tests/contract/test_ci_preflight_ci_gating_parity.py | subset without doctor/coverage/hygiene | ″ | UPDATE | +12; the one local list |
| core/invocation.py… | A context name stops standing in for its repo slug. | 7 (`sa-context-repo-mapping-falls-back-to-the-name`) | REBUILD | 6 prior bugs on this mapping |
| core/handoff_index.py:548 self_pull resolution; i/json_context_store.py _context_registered; cli/commands/specs.py init --context | repos/<context> | ″ | UPDATE | consult resolve_context_specs_dir |
| cli/main.py, capabilities, reconcile, python_env,… | --version, capabilities, reconcile, export and the install ledger… | 6 (`sa-editable-install-reports-a-frozen-version`) | UPDATE | call provider_version |
| `infrastructure/python_env.py` distribution-version read → `provider_version()` | six readers, dist-info only | ″ | REBUILD | AC8.2 admits three ADDs: the one reader is an existing read rebuilt in place (dist-info, editable → source pyproject), not a new unit |
| scripts/_backlog_subjects.py --resolve; core/models/backlog.py SubjectKind.PANEL | The backlog script stops declaring a subject RESOLVED from the… | 7 (`sa-subjects-resolve-is-circular`) | DELETE | 6 prior bugs; resolves against itself |
| f/backlog/subject_registry.py bind | no 'dadaia ' normalization | ″ | UPDATE | +2 |
| i/runtime_config.py _python_bin | Claude hooks stop resolving a Python interpreter on their own. | 8 (`sa-hook-parity-claims-false-and-interpreter-rules-diverge`) | DELETE | 7 prior bugs on interpreter resolution |
| i/runtime_transforms/hook_wrappers.py | wrappers per harness | ″ | REBUILD | one wrapper, one missing-venv posture |
| specs/memory/product/agents/agentic-entities.md +… | parity claim | ″ | UPDATE | declare the gap per harness (DEC-9 b) |
| i/install_helpers.py _ACTIVITY_CLASSES | ADDITIVE stops meaning two things (a path class and an actor class). | 5 (`sa-reviewer-persona-body-contradicts-its-tools`) | REBUILD | 4 prior bugs; rename to read_only |
| public/agents/dd-code-reviewer.md; i/runtime_transforms/codex_assets.py:217; public/agents/dd-software-engineer.md,… | body contradicts tools | ″ | UPDATE | -10 |
| i/public_assets.py render_registry_tables; f/specs/canon.py:154 copy; f/specs/doctor_structural.py:228 TREE-5 +1 | specs init stops writing law with unrendered placeholders. | 6 (`sa-specs-init-writes-unrendered-law`) | UPDATE | move to core/workspace_layout |
| f/spec_context/gate_policy.py classify_path | PROTECTED stops being decided by a file basename. | 6 (`sa-gate-path-classes-diverge-from-the-law`) | REBUILD | 5 prior bugs on classification |
| core/workspace_layout.py; f/specs/doctor_structural.py:210; public/data/AGENTS.md, dadaia-AGENTS.md,… | owns zones and canon | ″ | UPDATE | exposes protected/additive views |
| pyproject.toml [tool.ruff]/[tool.mypy] cache; i/runtime_config.py harness env block; f/spec_context/markers.py:59,72 +1 | Tool caches stop resolving relative to the cwd (nested .dadaia/ from… | 6 (`sa-tool-caches-land-outside-the-cache-zone`) | UPDATE | 5 prior cache bugs; absolute via env |
| public/skills/dd-gitflow-default/SKILL.md:45; AGENTS.md (repo) :17-18 | The work-branch name stops being computed from the last tag. | 7 (`sa-live-work-branch-named-three-ways`) | DELETE | contradicts P-30 |
| f/spec_context/service.py _work_branch | tag+1 | ″ | REBUILD | c3-overlap; 6 prior version bugs |
| cli/commands/ci.py branch naming; release-please-config.json | tag+1 | ″ | UPDATE | c3-overlap |
| f/specs/canon.py:114 | specs init stops suggesting literal branch names. | 4 (`sa-principal-branch-defaults-to-main-and-cut-point-diverges`) | DELETE | always overwritten |
| cli/commands/specs.py _gitflow | detection + literals | ″ | REBUILD | 3 prior bugs; one detector |
| public/skills/dd-gitflow-default/SKILL.md §2a/§11; f/spec_context/service.py baseline | cut from principal | ″ | UPDATE | ADR 0035 |
| f/specs/doctor_closure_audit.py SPEC-DOC-036/038; i/jsonl_record_store.py write half; f/specs/doctor.py findings_store_factory | The doctor stops recommending audit close on its own reading of… | 6 (`sa-audit-close-archives-without-validating`) | DELETE | 5 prior audit bugs |
| scripts/_audit_verbs.py close | writes before checking | ″ | UPDATE | +3; check first, deferred/rejected when nothing resolved |
| i/runtime_transforms/codex_assets.py build_agents_index; i/codex_doctor.py check_codex_rule_corpus_reachable; i/public_assets.py stage/doctor index lines | Stage stops writing agents.index.json. | 5 (`sa-staged-assets-without-consumers`) | DELETE | deletion test passes |
| i/install_helpers.py model fallback | silent default | ″ | UPDATE | fail closed |
| f/spec_context/markers.py reap_markers; core/kernel_tunables.py SENTINEL_GC_TTL_SECONDS; core/handoff_index.py timestamp family | Markers and handoffs stop having a second expiry clock beside the… | 4 (`sa-expiry-has-two-clocks`) | DELETE | 3 prior TTL bugs |
| f/spec_context/sweep.py | the one chokepoint | ″ | KEEP | authority |
| core/handoff_index.py:507 conditional | The validator stops branching on schema_version. | 5 (`sa-handoff-self-pull-requirement-diverges`) | DELETE | schema carries it |
| public/schemas/handoff-v1.schema.json | three versions | ″ | UPDATE | 4 prior handoff bugs; one version |
| cli/commands/specs.py --target; f/migrate/upgrade.py old-layout guard | specs upgrade stops accepting a target it cannot migrate to. | 4 (`sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges`) | DELETE | 3 prior upgrade bugs |
| public/skills/dd-spec-navigator/SKILL.md:52,… | Part 1/Part 2 | ″ | UPDATE | CONTEXT.md:182 already forbids the term |
| core/models/histo.py vocabularies | core stops holding ledger vocabularies no library code reads. | 6 (`sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts`) | DELETE | 5 prior ledger-write bugs |
| tests/contract/test_required_evidence_has_one_home.py | pins core, exempts public/skills | ″ | REBUILD | its authority choice contradicts WP-48; must point at the script |
| scripts/_*_store.py _replace x4; dd-cli-library/registry.py save; scripts/_bugs_check.py +1 | identical, leak tmp | ″ | UPDATE | +3 each; clone of one another by design (self-contained scripts) |
| public/data/AGENTS.md:37 venv rule; core/invocation.py docstring, hooks/ctx_inject.py,…; setup.cfg importlinter +3 | Docstrings stop restating the resolution law. | 7 (`sa-text-restates-rules-the-code-contradicts`) | UPDATE | 'a Bash command that STARTS with' |

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

### FR1 — wave 0 (data loss, leaks, gate holes; 14 bugs)

Order: WP-02 first (every other deleter consults `sweep`), `release-as` with it (AC1.6); the install and
ledger deleters; the gate; WP-32 and the hooks-path bug together (the gate must run where git runs it,
and the checks that carry it must be required). WP-32 does not depend on FR5/FR6: it pins the `ci.yml`
job list; the ratchets later land inside an already-listed job (AC6.7 → AC1.7). † = anchors re-measured.

| row | RED seam | deletes: code · tests · fakes | Δprod | Δtest |
|---|---|---|---|---|
| WP-02 | `doctor --fix` twice, frozen clock: two byte-intact holds | `move`→`remove` · `test_a_second_reap…replaces_the_earlier_hold`, 2 HOLLOW, 1 DUP · undo `044d1d0b` | −4 | +40 |
| WP-03 † | real-git `context dead`: refuses an unpushed non-HEAD branch and a linked worktree; else holds under `.dadaia/reaped/` | raw `rmtree` · `test_dead_succeeds_on_non_writable_files`, 2 DUP, 2 HOLLOW; 7 REWRITE · undo `934377e8` | +3 | +78 |
| WP-04 | `public install` on a codex ws: `.codex/agents/my-agent.toml` byte-intact | 4 removers · 2 LOSER | −86 | +5 |
| WP-05 | one table fed to `pre_gate` and the doctor: ALLOW ⇔ not SLOP | 4 matchers · 7 LOSER | −30 | +75 |
| WP-06 | `doctor --fix` moves nothing under harness dirs; moved ⊆ ledger | `_scan_harness_dirs`, `_active_harnesses` · 3 LOSER | −45 | +2 |
| WP-07 † | create → install → `specs init`: repo `AGENTS.md` = template; an operator edit survives | fan-out, scope flags · 6 LOSER | −230 | −119 |
| WP-08 | `install --only` exit 2; every ledgered shipped path survives | `--only` · 2 LOSER | −40 | +14 |
| WP-09 | 4 scripts × invalid line: a refusal leaves both sha256 unchanged | `append_raw` | −10 | +80 |
| WP-11 † | `public doctor` with denylist `zorblax` prints `z…x`; `doctor --redact` = `context list --redact` | doctor redactor · 7 LOSER, 2 DUP | −30 | +25 |
| WP-12 | vendor-documented payloads through each rendered wrapper get Claude's verdict; no explicit allow | explicit allow, own reads · 2 LOSER, 2 HOLLOW · undo `fb95c427` | +10 | +60 |
| WP-13 | parsed `.rules`: no write/exec prefix allowed | `find`, bare `sed` · 1 DUP, 1 HOLLOW | −3 | +37 |
| WP-14 | `specs upgrade` and `doctor --fix` refuse a symlinked QUALITY.md; outside md5 unchanged | upgrade's writers · 1 LOSER, 1 HOLLOW · undo `0fee8cdd` | −30 | +65 |
| hooksPath | real `git init` + `core.hooksPath`: gate installed at `--git-path hooks`; foreign `pre-push` refused with its line; doctor never healthy; push with a denylisted term refused | `.git/hooks` literal · 2 HOLLOW, 2 REWRITE | +5 | +70 |
| WP-32 | `ci.yml` job names = the in-repo required-checks file; `release.yml` consumes `ci.yml` | release matrix · 1 LOSER, 1 HOLLOW | −75 | +71 |
| **wave 0** | | | **−565** | **+503** |

Statement ids:
- WP-02: `sa-reaper-destroys-its-own-hold-before-ttl#B1`, `sa-reaper-destroys-its-own-hold-before-ttl#B2`, `sa-reaper-destroys-its-own-hold-before-ttl#B3`, `sa-reaper-destroys-its-own-hold-before-ttl#B4`, `sa-reaper-destroys-its-own-hold-before-ttl#B5`, `sa-reaper-destroys-its-own-hold-before-ttl#B6`, `sa-reaper-destroys-its-own-hold-before-ttl#B7`, `sa-reaper-destroys-its-own-hold-before-ttl#B8`
- WP-03: `sa-context-dead-removes-repos-outside-the-reaper#C1`, `sa-context-dead-removes-repos-outside-the-reaper#C2`, `sa-context-dead-removes-repos-outside-the-reaper#C3`, `sa-context-dead-removes-repos-outside-the-reaper#C4`, `sa-context-dead-removes-repos-outside-the-reaper#C5`, `sa-context-dead-removes-repos-outside-the-reaper#C6`, `sa-context-dead-removes-repos-outside-the-reaper#C7`, `sa-context-dead-removes-repos-outside-the-reaper#C8`
- WP-04: `sa-public-install-unlinks-operator-files-outside-its-ledger#D1`, `sa-public-install-unlinks-operator-files-outside-its-ledger#D2`, `sa-public-install-unlinks-operator-files-outside-its-ledger#D3`, `sa-public-install-unlinks-operator-files-outside-its-ledger#D4`, `sa-public-install-unlinks-operator-files-outside-its-ledger#D5`, `sa-public-install-unlinks-operator-files-outside-its-ledger#D6`
- WP-05: `sa-gate-allows-root-entries-the-reaper-moves#E1`, `sa-gate-allows-root-entries-the-reaper-moves#E2`, `sa-gate-allows-root-entries-the-reaper-moves#E3`, `sa-gate-allows-root-entries-the-reaper-moves#E4`, `sa-gate-allows-root-entries-the-reaper-moves#E5`, `sa-gate-allows-root-entries-the-reaper-moves#E6`, `sa-gate-allows-root-entries-the-reaper-moves#E7`, `sa-gate-allows-root-entries-the-reaper-moves#E8`, `sa-gate-allows-root-entries-the-reaper-moves#E9`
- WP-06: `sa-doctor-reaps-harness-owned-entries#H1`, `sa-doctor-reaps-harness-owned-entries#H2`, `sa-doctor-reaps-harness-owned-entries#H3`, `sa-doctor-reaps-harness-owned-entries#H4`, `sa-doctor-reaps-harness-owned-entries#H5`
- WP-07: `sa-public-install-writes-the-root-map-into-product-repos#K1`, `sa-public-install-writes-the-root-map-into-product-repos#K2`, `sa-public-install-writes-the-root-map-into-product-repos#K3`, `sa-public-install-writes-the-root-map-into-product-repos#K4`, `sa-public-install-writes-the-root-map-into-product-repos#K5`, `sa-public-install-writes-the-root-map-into-product-repos#K6`
- WP-08: `sa-scoped-public-install-prunes-the-gate-wiring#L1`, `sa-scoped-public-install-prunes-the-gate-wiring#L2`, `sa-scoped-public-install-prunes-the-gate-wiring#L3`, `sa-scoped-public-install-prunes-the-gate-wiring#L4`
- WP-09: `sa-ledger-verbs-append-histo-before-validating-the-pair#J1`, `sa-ledger-verbs-append-histo-before-validating-the-pair#J2`, `sa-ledger-verbs-append-histo-before-validating-the-pair#J3`, `sa-ledger-verbs-append-histo-before-validating-the-pair#J4`, `sa-ledger-verbs-append-histo-before-validating-the-pair#J5`
- WP-11: `sa-private-match-rendering-has-three-renderers#B1`, `sa-private-match-rendering-has-three-renderers#B2`, `sa-private-match-rendering-has-three-renderers#B3`, `sa-private-match-rendering-has-three-renderers#B4`, `sa-private-match-rendering-has-three-renderers#B5`, `sa-private-match-rendering-has-three-renderers#B6`, `sa-private-match-rendering-has-three-renderers#B7`
- WP-12: `sa-gate-blind-on-cursor-copilot-devin#B1`, `sa-gate-blind-on-cursor-copilot-devin#B2`, `sa-gate-blind-on-cursor-copilot-devin#B3`, `sa-gate-blind-on-cursor-copilot-devin#B4`, `sa-gate-blind-on-cursor-copilot-devin#B5`, `sa-gate-blind-on-cursor-copilot-devin#B6`, `sa-gate-blind-on-cursor-copilot-devin#B7`, `sa-gate-blind-on-cursor-copilot-devin#B8`
- WP-13: `sa-codex-policy-allows-write-capable-commands#B1`, `sa-codex-policy-allows-write-capable-commands#B2`, `sa-codex-policy-allows-write-capable-commands#B3`, `sa-codex-policy-allows-write-capable-commands#B4`
- WP-14: `sa-specs-upgrade-writes-through-symlinks#B1`, `sa-specs-upgrade-writes-through-symlinks#B2`, `sa-specs-upgrade-writes-through-symlinks#B3`, `sa-specs-upgrade-writes-through-symlinks#B4`, `sa-specs-upgrade-writes-through-symlinks#B5`
- hooksPath: `pre-push-gate-never-runs-under-core-hookspath#B1`, `pre-push-gate-never-runs-under-core-hookspath#B2`, `pre-push-gate-never-runs-under-core-hookspath#B3`, `pre-push-gate-never-runs-under-core-hookspath#B4`
- WP-32: `sa-doctor-job-not-a-required-check#B1`, `sa-doctor-job-not-a-required-check#B2`, `sa-doctor-job-not-a-required-check#B3`, `sa-doctor-job-not-a-required-check#B4`, `sa-doctor-job-not-a-required-check#B5`

### FR5 + FR6 — the never-again mechanism (after wave 0)

- **Generic (FR5, every consumer).** `_refuse_missing_as_is_table` also finds `### … Authorities`
  under §1 and refuses, one `fix:` each: missing table; an empty `authority`; one `question` with two
  authorities. Structure only (ADR 0041). The fix names the skeleton `_release_new.py` seeds. Fixture
  pair: a two-authority PLAN is refused; its twin passes. Skills (`dd-release-definition` §2,
  `dd-code-review` S10 HIGH + the architecture lens, `dd-audit-project` fixed hunt) change under
  `dd-ai-eng-knowhow` AUTHORING and the AI-surface lens, then `public stage`/`install`/`doctor`.
  `CONTEXT.md` gets the four terms. ~+18 production.
- **Library (FR6, tests only, AC6.8).** V37 (AST over modules, skill scripts, hooks: duplicate top-level
  UPPER constants and functions), V38 (destructive calls outside `sweep.py`) + import-linter `shutil`
  contract, V39 (every doctor code has a fix-clears case or a `report-only` key), `test_zone_registry`
  widening. One allowance shape: `{"file:symbol": "<open bug id>" | "parity:<test>"}`; an unlisted hit
  fails, a vanished key fails stale, a value naming a closed bug fails. Born at today's counts, keyed to
  the wave 1–3 bugs. `test_required_evidence_has_one_home.py` folds into V37 (deleted). ~+160 test lines.

### FR9 — test harness (after FR5/FR6, before waves 1–3)

- **Real-git fixture** (AC9.4) — one `tmp_git_repo` fixture (bare origin, branches, linked worktrees)
  replaces `FakeGitClient` and the 4 `ObjectSource` fakes (22 users). `FakeContextStore` stays only
  behind `_store_contract.py` plus a save/update parity test against `JsonContextStore`. ~−500 tests.
- **Hook harness + WP-15** (AC9.5) — the `WORKSPACE_ROOT` injection and `_POLICY_DRIVER` exist to feed the
  rung WP-15 deletes; they leave in WP-15's commit. Hooks spawn as `hook_wrappers.py` renders them, cwd
  in the tmp workspace, through `pre_gate`. The ~60 tests that go red are adjudicated by §2.4.
- **`DADAIA_FENCED_ROOTS` — declared product feature (operator decision (b), 0088)**: no dadaia process
  acts on a fenced root. `core/workspace_resolver` `FENCE_ENV` + `_fenced()` stay; the suite (`tests/conftest.py`)
  and every mutating probe set it (the 2026-09-26 probe incident). One law line in `.dadaia/AGENTS.md`
  (source `pub/data/dadaia-AGENTS.md`, resolution order), one behaviour statement (AC9.12 `#S11`, 0088),
  `test_workspace_not_found_error.py` cites it. Δprod ≈ +3 (law); Δtest ≈ +10.
- **No shared cross-check helper**; each package's RED is its own table.

### FR2 — wave 1 (stalls, loops, fixes that never clear)

| row | RED seam | deletes: code · tests · fakes | Δprod | Δtest |
|---|---|---|---|---|
| WP-15 † | hook subprocess with `WORKSPACE_ROOT=<empty>`: a write to `.dadaia/sessions/x.json` BLOCKed; AST: one root walk | env step, 5 walks · 1 LOSER, 1 HOLLOW, 18 REWRITE (the harness) | −25 | +108 |
| WP-16 † | native id × env × record × ghost: gate, `ctx_inject`, onboarding, `context show` agree; native id + no bind refused in `repos/<slug>/` | env-first · 2 LOSER, 1 HOLLOW | −5 | +115 |
| WP-17 † | every BLOCK/refusal/finding fix runs verbatim from the root and `repos/alpha`, exit 0 | bare/`&&` lines · `_EXECUTABLE_TOKENS`, 2 LOSER · undo `75b92f25` | 0 | +140 |
| WP-18 † | walk `_cli_tree`: `Error:` + `fix:`, exit 1 (Click usage 2), unwrapped at a 61-char root | `_refuse`, `err_console` · 3 LOSER, 1 DUP, 1 HOLLOW · undo `b50f0c97` | −50 | +75 |
| WP-19 | run each printed fix, re-run the doctor: finding gone; no unfixable says `doctor --fix` | `rule_fix` default · 2 HOLLOW | +2 | +100 |
| WP-20 | off-canon files: one finding each; its fix → zero | SPEC-DOC-035, TREE-7, -002L · 10 LOSER · undo `9ebefd5f` | −115 | −40 |
| WP-21 † | version table: store readable ⇔ migrate no-op | `_detect_schema_version` · 1 DUP · undo `f9774c2d` | −18 | +100 |
| WP-22 | doctor × `bugs.py check` parity; AST: no `core.models.bugs` | `core/models/bugs.py`, SPEC-DOC-033 · `test_bug_record.py` (23), 7 LOSER · undo `0fee8cdd` | −640 | −670 |
| WP-23 | secret matrix: seam refuses ⇔ push refuses; `BUGS.jsonl` byte-intact | 3 `redact` copies (ADD `_shared/_privacy.py`) · 4 LOSER | −60 | +10 |
| WP-24 | `postponed`/`Deferred` agree; `new --origin` → `exit delivered`, no hand edit | BL-STALE, whitelist · 4 LOSER, 2 HOLLOW, 1 DUP · undo `68658783` | −80 | −40 |
| WP-25 | `new`→IMPLEMENTATION→CLOSURE→`ship`→`new` by verbs, doctor clean; `* [ ]` refuses CLOSURE | ARCHIVED, second regex (ADD `ship`) · 14 LOSER, 2 HOLLOW · undo `b50f0c97` | −40 | −70 |
| WP-26 | parity table of both status readers; SPEC-DOC-004 fixed in place | window, append · 5 REWRITE · undo `b50f0c97` | −5 | +60 |
| WP-27 | `measured_by: npx vitest run` clean; a duplicate `0049` flagged | the pattern · 2 LOSER, 4 DUP · undo `64e4885c` | −15 | −10 |
| WP-28 † | pre-push reads the pushed commit: malformed + stray → BLOCKED; one fix everywhere | SPECS-VERSION · 3 LOSER | −34 | +145 |
| WP-29 | generate, check, LINT-1 give one verdict; tags `["a, b", c]` refused | CAT-1, atomicity · 6 LOSER · undo `b50f0c97` | −155 | −10 |
| **wave 1** | | | **−1240** | **+13** |

Statement ids:
- WP-15: `sa-seven-workspace-root-rules#S1`, `sa-seven-workspace-root-rules#S2`, `sa-seven-workspace-root-rules#S3`, `sa-seven-workspace-root-rules#S4`, `sa-seven-workspace-root-rules#S5`, `sa-seven-workspace-root-rules#S6`, `sa-seven-workspace-root-rules#S7`, `sa-seven-workspace-root-rules#S8`, `sa-seven-workspace-root-rules#S9`, `sa-seven-workspace-root-rules#S10`
- WP-16: `sa-bind-has-two-stores#S1`, `sa-bind-has-two-stores#S2`, `sa-bind-has-two-stores#S3`, `sa-bind-has-two-stores#S4`, `sa-bind-has-two-stores#S5`, `sa-bind-has-two-stores#S6`, `sa-bind-has-two-stores#S7`, `sa-bind-has-two-stores#S8`, `sa-bind-has-two-stores#S9`, `sa-bind-has-two-stores#S10`, `sa-bind-has-two-stores#S11`
- WP-17: `sa-fix-lines-not-built-by-cli-line#S1`, `sa-fix-lines-not-built-by-cli-line#S2`, `sa-fix-lines-not-built-by-cli-line#S3`, `sa-fix-lines-not-built-by-cli-line#S4`, `sa-fix-lines-not-built-by-cli-line#S5`, `sa-fix-lines-not-built-by-cli-line#S6`, `sa-fix-lines-not-built-by-cli-line#S7`, `sa-fix-lines-not-built-by-cli-line#S8`
- WP-18: `sa-rich-printer-wraps-fix-lines#S1`, `sa-rich-printer-wraps-fix-lines#S2`, `sa-rich-printer-wraps-fix-lines#S3`, `sa-rich-printer-wraps-fix-lines#S4`, `sa-rich-printer-wraps-fix-lines#S5`, `sa-rich-printer-wraps-fix-lines#S6`
- WP-19: `sa-unfixable-doctor-findings-say-doctor-fix#S1`, `sa-unfixable-doctor-findings-say-doctor-fix#S2`, `sa-unfixable-doctor-findings-say-doctor-fix#S3`, `sa-unfixable-doctor-findings-say-doctor-fix#S4`, `sa-unfixable-doctor-findings-say-doctor-fix#S5`, `sa-unfixable-doctor-findings-say-doctor-fix#S6`
- WP-20: `sa-placement-rules-contradict-tree8#B1`, `sa-placement-rules-contradict-tree8#B2`, `sa-placement-rules-contradict-tree8#B3`, `sa-placement-rules-contradict-tree8#B4`, `sa-placement-rules-contradict-tree8#B5`, `sa-placement-rules-contradict-tree8#B6`
- WP-21: `sa-registry-schema-version-has-three-grammars#B1`, `sa-registry-schema-version-has-three-grammars#B2`, `sa-registry-schema-version-has-three-grammars#B3`, `sa-registry-schema-version-has-three-grammars#B4`, `sa-registry-schema-version-has-three-grammars#B5`, `sa-registry-schema-version-has-three-grammars#B6`, `sa-registry-schema-version-has-three-grammars#B7`
- WP-22: `sa-spec-doc-033-duplicates-bugs-check#B1`, `sa-spec-doc-033-duplicates-bugs-check#B2`, `sa-spec-doc-033-duplicates-bugs-check#B3`, `sa-spec-doc-033-duplicates-bugs-check#B4`, `sa-spec-doc-033-duplicates-bugs-check#B5`, `sa-spec-doc-033-duplicates-bugs-check#B6`, `sa-spec-doc-033-duplicates-bugs-check#B7`, `sa-spec-doc-033-duplicates-bugs-check#B8`
- WP-23: `sa-ledger-write-seam-redacts-less-than-push-refuses#B1`, `sa-ledger-write-seam-redacts-less-than-push-refuses#B2`, `sa-ledger-write-seam-redacts-less-than-push-refuses#B3`, `sa-ledger-write-seam-redacts-less-than-push-refuses#B4`, `sa-ledger-write-seam-redacts-less-than-push-refuses#B5`, `sa-ledger-write-seam-redacts-less-than-push-refuses#B6`
- WP-24: `sa-backlog-status-has-no-single-authority#B1`, `sa-backlog-status-has-no-single-authority#B2`, `sa-backlog-status-has-no-single-authority#B3`, `sa-backlog-status-has-no-single-authority#B4`, `sa-backlog-status-has-no-single-authority#B5`, `sa-backlog-status-has-no-single-authority#B6`, `sa-backlog-status-has-no-single-authority#B7`, `sa-backlog-status-has-no-single-authority#B8`
- WP-25: `sa-promote-has-no-verb#B25-1`, `sa-promote-has-no-verb#B25-2`, `sa-promote-has-no-verb#B25-3`, `sa-promote-has-no-verb#B25-4`, `sa-promote-has-no-verb#B25-5`, `sa-promote-has-no-verb#B25-6`, `sa-promote-has-no-verb#B25-7`, `sa-promote-has-no-verb#B25-8`
- WP-26: `sa-status-line-has-two-parsers#B26-1`, `sa-status-line-has-two-parsers#B26-2`, `sa-status-line-has-two-parsers#B26-3`, `sa-status-line-has-two-parsers#B26-4`
- WP-27: `sa-adr-measured-by-pattern-refuses-real-checks#B27-1`, `sa-adr-measured-by-pattern-refuses-real-checks#B27-2`, `sa-adr-measured-by-pattern-refuses-real-checks#B27-3`, `sa-adr-measured-by-pattern-refuses-real-checks#B27-4`
- WP-28: `sa-specs-tree-state-read-five-ways#B28-1`, `sa-specs-tree-state-read-five-ways#B28-2`, `sa-specs-tree-state-read-five-ways#B28-3`, `sa-specs-tree-state-read-five-ways#B28-4`, `sa-specs-tree-state-read-five-ways#B28-5`, `sa-specs-tree-state-read-five-ways#B28-6`, `sa-specs-tree-state-read-five-ways#B28-7`
- WP-29: `sa-memory-atom-has-two-grammars#B29-1`, `sa-memory-atom-has-two-grammars#B29-2`, `sa-memory-atom-has-two-grammars#B29-3`, `sa-memory-atom-has-two-grammars#B29-4`, `sa-memory-atom-has-two-grammars#B29-5`, `sa-memory-atom-has-two-grammars#B29-6`

### FR3 — wave 2 (consolidations)

| row | RED seam | deletes | Δprod | Δtest |
|---|---|---|---|---|
| WP-30 | phase `closure`: one finding with a runnable fix; `next/` not live; `new` refuses while `check` is red | `release_tree` rules, rc-N · 14 LOSER, 4 DUP, 3 HOLLOW · undo `987e76d4` | −105 | −100 |
| WP-31 | `certify` reports workspace slop; every recipe line passes the wheel's `--help` | `_OWNED_DOCTOR_SECTIONS` · 2 LOSER | −126 | +116 |
| WP-33 | `specs init --context alpah` refused, nothing written; self-pull resolves via the registry | name fallback · 3 LOSER | −10 | +101 |
| WP-34 | editable 0.4.7 over dist-info 0.1.4: three verbs say 0.4.7 | 5 readers · 1 DUP | −8 | +91 |
| WP-35 | `cli:dadaia context bind` accepted; no surface says RESOLVED | `--resolve`, PANEL · 3 LOSER | −25 | +39 |
| WP-36 | no venv: every wrapper exits 0 + one warning | `_python_bin` · 4 REWRITE | −20 | +147 |
| WP-37 | a persona body never needs a missing tool | `_ACTIVITY_CLASSES` · 2 REWRITE | −7 | +48 |
| WP-38 | `specs init`: `| Area | Members |` present, the marker absent | raw copy · 1 LOSER, 2 DUP | +4 | +33 |
| **wave 2** | | | **−297** | **+475** |

Statement ids:
- WP-30: `sa-release-json-validated-three-times#B1`, `sa-release-json-validated-three-times#B2`, `sa-release-json-validated-three-times#B3`, `sa-release-json-validated-three-times#B4`, `sa-release-json-validated-three-times#B5`, `sa-release-json-validated-three-times#B6`, `sa-release-json-validated-three-times#B7`
- WP-31: `sa-reconcile-certify-skip-the-workspace-walk#B1`, `sa-reconcile-certify-skip-the-workspace-walk#B2`, `sa-reconcile-certify-skip-the-workspace-walk#B3`, `sa-reconcile-certify-skip-the-workspace-walk#B4`, `sa-reconcile-certify-skip-the-workspace-walk#B5`
- WP-33: `sa-context-repo-mapping-falls-back-to-the-name#B1`, `sa-context-repo-mapping-falls-back-to-the-name#B2`, `sa-context-repo-mapping-falls-back-to-the-name#B3`, `sa-context-repo-mapping-falls-back-to-the-name#B4`, `sa-context-repo-mapping-falls-back-to-the-name#B5`
- WP-34: `sa-editable-install-reports-a-frozen-version#B1`, `sa-editable-install-reports-a-frozen-version#B2`, `sa-editable-install-reports-a-frozen-version#B3`, `sa-editable-install-reports-a-frozen-version#B4`
- WP-35: `sa-subjects-resolve-is-circular#B1`, `sa-subjects-resolve-is-circular#B2`, `sa-subjects-resolve-is-circular#B3`, `sa-subjects-resolve-is-circular#B4`, `sa-subjects-resolve-is-circular#B5`
- WP-36: `sa-hook-parity-claims-false-and-interpreter-rules-diverge#B1`, `sa-hook-parity-claims-false-and-interpreter-rules-diverge#B2`, `sa-hook-parity-claims-false-and-interpreter-rules-diverge#B3`, `sa-hook-parity-claims-false-and-interpreter-rules-diverge#B4`, `sa-hook-parity-claims-false-and-interpreter-rules-diverge#B5`, `sa-hook-parity-claims-false-and-interpreter-rules-diverge#B6`
- WP-37: `sa-reviewer-persona-body-contradicts-its-tools#B1`, `sa-reviewer-persona-body-contradicts-its-tools#B2`, `sa-reviewer-persona-body-contradicts-its-tools#B3`, `sa-reviewer-persona-body-contradicts-its-tools#B4`
- WP-38: `sa-specs-init-writes-unrendered-law#B38-1`, `sa-specs-init-writes-unrendered-law#B38-2`, `sa-specs-init-writes-unrendered-law#B38-3`, `sa-specs-init-writes-unrendered-law#B38-4`, `sa-specs-init-writes-unrendered-law#B38-5`

### FR4 — wave 3 (design debt)

| row | RED seam | deletes | Δprod | Δtest |
|---|---|---|---|---|
| WP-39 | hook: `.claude/settings.json` BLOCK; a tmp probe `AGENTS.md` ALLOW | basename rule, prefixes · 3 LOSER, 3 DUP | +5 | −5 |
| WP-40 | ruff/mypy from a worktree and `repos/demo/pkg/sub`: no nested `.dadaia/`; caches in `.dadaia/tmp/<tool>-cache` (0080) | `.cache` zone, relative paths · 1 LOSER · undo `64e4885c` | 0 | +30 |
| WP-41 † | tag v0.4.7 + live 0.5.0: baseline, gate and `work_name` say `feature/0.5.0` | tag+1 · 1 LOSER · undo `ffb30aa0` | −3 | +37 |
| WP-42 † | origin/HEAD=develop, master present: principal master | literal default · 1 HOLLOW | +2 | +44 |
| WP-43 | `BANANA`: `audit.py close` refuses, dir kept | SPEC-DOC-036/038, write half · 13 LOSER, 1 HOLLOW · undo `27ed26fb` | −182 | −340 |
| WP-44 | no `agents.index.json`: `public doctor` exit 0 | index builder, corpus check · 5 LOSER, 1 DUP | −151 | −100 |
| WP-45 | marker at 86401 s, handoff at 1 d + 1 s: reaped by the zone walk | `reap_markers`, `expires_at` · 4 LOSER | −67 | +10 |
| WP-46 | a v1.1 handoff without `self_pull` is INVALID | v1/v1.1 · 4 LOSER | −4 | +5 |
| WP-47 | `--target` gone; a two-tier tree refused unstamped | `--target`, old guard · 1 LOSER · undo `07eb6349` | −20 | +10 |
| WP-48 | failing `os.replace` leaves no `.tmp`; a bad histo line flagged | `histo.py` sets · 3 LOSER | −5 | +45 |
| WP-49 | `os.name` ratchet; import-linter flags `core.invocation` in `harness.py` | false text | −20 | +80 |
| FR-8 | a consumer's own `--surface` accepted; no library fact projected | the `surface` library arm · 1 LOSER | −40 | +45 |
| **wave 3** | | | **−485** | **−139** |

Statement ids:
- WP-39: `sa-gate-path-classes-diverge-from-the-law#B39-1`, `sa-gate-path-classes-diverge-from-the-law#B39-2`, `sa-gate-path-classes-diverge-from-the-law#B39-3`, `sa-gate-path-classes-diverge-from-the-law#B39-4`, `sa-gate-path-classes-diverge-from-the-law#B39-5`, `sa-gate-path-classes-diverge-from-the-law#B39-6`, `sa-gate-path-classes-diverge-from-the-law#B39-7`
- WP-40: `sa-tool-caches-land-outside-the-cache-zone#B40-1`, `sa-tool-caches-land-outside-the-cache-zone#B40-2`, `sa-tool-caches-land-outside-the-cache-zone#B40-3`, `sa-tool-caches-land-outside-the-cache-zone#B40-4`
- WP-41: `sa-live-work-branch-named-three-ways#B41-1`, `sa-live-work-branch-named-three-ways#B41-2`, `sa-live-work-branch-named-three-ways#B41-3`, `sa-live-work-branch-named-three-ways#B41-4`, `sa-live-work-branch-named-three-ways#B41-5`
- WP-42: `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-1`, `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-2`, `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-3`, `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-4`, `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-5`, `sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-6`
- WP-43: `sa-audit-close-archives-without-validating#B43-1`, `sa-audit-close-archives-without-validating#B43-2`, `sa-audit-close-archives-without-validating#B43-3`, `sa-audit-close-archives-without-validating#B43-4`, `sa-audit-close-archives-without-validating#B43-5`, `sa-audit-close-archives-without-validating#B43-6`
- WP-44: `sa-staged-assets-without-consumers#44.1`, `sa-staged-assets-without-consumers#44.2`, `sa-staged-assets-without-consumers#44.3`, `sa-staged-assets-without-consumers#44.4`, `sa-staged-assets-without-consumers#44.5`
- WP-45: `sa-expiry-has-two-clocks#45.1`, `sa-expiry-has-two-clocks#45.2`, `sa-expiry-has-two-clocks#45.3`
- WP-46: `sa-handoff-self-pull-requirement-diverges#46.1`, `sa-handoff-self-pull-requirement-diverges#46.2`, `sa-handoff-self-pull-requirement-diverges#46.3`, `sa-handoff-self-pull-requirement-diverges#46.4`
- WP-47: `sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.1`, `sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.2`, `sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.3`, `sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.4`
- WP-48: `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.1`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.2`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.3`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.4`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.5`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.6`
- WP-49: `sa-text-restates-rules-the-code-contradicts#49.1`, `sa-text-restates-rules-the-code-contradicts#49.2`, `sa-text-restates-rules-the-code-contradicts#49.3`, `sa-text-restates-rules-the-code-contradicts#49.4`, `sa-text-restates-rules-the-code-contradicts#49.5`, `sa-text-restates-rules-the-code-contradicts#49.6`
- FR-8: `sa-consumer-law-carries-library-facts#FR8.1`, `sa-consumer-law-carries-library-facts#FR8.2`, `sa-consumer-law-carries-library-facts#FR8.3`, `sa-consumer-law-carries-library-facts#FR8.4`

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
- **Candidate-3 overlap** (WP-03, 07, 11, 15, 16, 17, 18, 21, 28, 41, 42): each starts after candidate 3's
  closure merge; anchors re-measured at `release.py new`; candidate 3's overshoot is reported against
  these rows' ceilings.
- **Load flakiness in the local preflight.** The real-git fixture and hook spawns raise wall time; a
  timing failure under load is a flake → `quarantine` + a registered bug, never a raised timeout; no
  `sleep`/barrier; an unregistered pass-on-retry is a failure.
- **AC9.5 turns ~60 hook tests red** on the real root rung; they are adjudicated in WP-15's task, never
  skipped.
- **Gate-not-enforced harnesses** cap D8/D9; the ≥ 80 score is measured, not assumed.
- **V35 skill-corpus ceiling (2863 lines, down-only).** FR5 grows four skills; the growth is paid by the
  skill-text deletions of WP-02, WP-24, WP-25, WP-49 and FR-8 within the candidate, else V35 fails.
- **Test budget** (AC9.9): +522 before pruning; the pruning pass is sized in §2 and measured at closure.

## 5. Contradictions routed to the main thread (planned as stated here)

1. SPEC AC9.1 lands behaviour rows in `QUALITY.md` "before the first fix"; ruling R1 lands them at the
   closure memory pass for resolved bugs. Planned per R1.
2. (Resolved in SPEC v2: waves 14/15/8/12.) SPEC's bug table kept `sa-doctor-job-not-a-required-check` in wave 2 (its wave-0 row reuses number
   32 for the hooks-path bug); ruling R2 moves WP-32 to wave 0. Planned per R2; the SPEC wave counts
   (13/15/9/12) need the move.
3. As-is WP-48 REBUILDs `test_required_evidence_has_one_home.py`; AC6.2 folds it into V37. Planned as
   delete.
4. WP-39: as-is +5, audit +30; the SPEC cap is +5. Over it the task stops.
5. WP-12 (+12) and WP-19 (+7) now equal their SPEC ceilings (AC1.1, AC2.1): no margin.
6. As-is names WP-39..48 with pre-registration slugs; the registered ids are used.
