# TASKS — Release 0.5.1 — Deepening simplification K1–K11

**Status:** Aprovado
**Release ID:** 0.5.1
**Owner:** product-engineer
**Source SPEC:** `specs/releases/0.5.1/SPEC.md`
**Source PLAN:** `specs/releases/0.5.1/PLAN.md`
**Branch:** `feature/0.5.1`, cut from `main` at the shipped `0.5.0`.
**Segments:** `alpha-1 … alpha-4` — work boundaries on `feature/0.5.1`, each closed by a
`qa-engineer` stewardship verdict **committed on the branch**: no PR, no merge, no `rc` burned.
**Candidates:** `rc-1 … rc-N`; the final `rc` carries memory → closure → archive and ships.

## Task status markers

- `[ ]` OPEN · `[-]` IN PROGRESS · `[x]` DONE

## Segment map

| Block | Tasks | Contents | Gate |
|---|---|---|---|
| W0 | T-051-02 | baselines before anything changes | numbers captured |
| `alpha-1` | T-051-01, 03, 04, 05, 06 | CONTEXT.md · K1 `Invocation` · K9 deletion half · ADR proposals | `qa-engineer` verdict committed |
| `alpha-2` | T-051-07 … 10 | K2 presence GC · K7 chokepoints split · K5 bug transitions | `qa-engineer` verdict committed |
| `alpha-3` | T-051-11 … 14 | K3 projection rules · K4 canon table (+R7) · K6 handoff | `qa-engineer` verdict committed |
| `alpha-4` | T-051-15 … 20 | K8 telemetry · K10 migration purge · K11 ruling · 2 standalone bugs | `qa-engineer` verdict committed |
| scope complete | T-051-21, 22 | invariants measured → trio review | all three APPROVE the same commit |
| `rc-1` | T-051-23 | PR `feature/0.5.1` → `develop` | merged, every CI job green |
| `rc-2 … rc-N` | T-051-24 | adjustment rounds on this scope | one QA close + one merge per round |
| final `rc` | T-051-25 … 28 | memory → closure narrative → archive → ship | trio still green, then the PR to `main` |

## Standing rules for this release

- **Reservation is observable.** Flip `[ ]`→`[-]` and commit `chore(tasks): start <id>` before the
  work (`dadaia-task-manager`).
- **Parallel `[-]` is allowed only inside `alpha-2`, `alpha-3` and `alpha-4`**, whose task write
  sets this file declares disjoint. `alpha-1` is strictly serial: 01 → 03 → 04 → 05.
- **Stage exactly the task's write set, never `git add -A`** — concurrent worktrees share one git
  index (open bugs 9, 10). Re-check `git status` before every commit.
- **Green at every commit:** `dadaia ci preflight`, `dadaia specs doctor`, `dadaia backlog doctor`,
  `dadaia public doctor`, `lint-imports`. No `--no-verify`, ever.
- **RED before GREEN** on the executed path for every bug fix.
- **Replace, don't layer.** The table-driven test at the new interface is written and green
  **before** the mirrored files are deleted, in the same task.
- **Every task is net-negative in production LOC and deletes at least one decider** (R3). A diff
  that only adds is rejected at review.
- **No puxadinho:** no branch, flag, special case, second code path, cross-feature reach-in or new
  side effect added to make a symptom go away. Every review verdict states the bug-surface delta
  of the touched feature, with bug-history evidence.
- **Naming comes from `CONTEXT.md`** — a module named before T-051-01 lands is renamed, not
  grandfathered.
- **No agent flips an ADR to `accepted`** — the operator alone (`DADAIA.md` §6.5).
- **`product-engineer` has no shell.** Every `[shell]`/`[git]`/`[operator]` step is run by the
  dispatcher, `software-engineer`, `qa-engineer`, `software-architect` or the operator.
- **A completed task group is one commit**, `conventional-commit(task-id): description`.
- **No home-absolute path, email literal, IP, hostname, private name or denylisted term** enters
  any authored file. Self-scan before every commit.

---

## W0

- [x] **T-051-02** — Baselines, before anything changes · owner: software-engineer · write set: none in-repo (captures under `.dadaia/tmp/software-engineer/<YYYYMMDD>/`) · acceptance: A-0.1, A-0.2, A-0.5 baselines exist as measured numbers, never estimates
  - captures: `git ls-files 'dadaia_workspace/**/*.py' | xargs wc -l` (production LOC/modules); decider counts per SPEC §1 by `rg` with the exact patterns recorded; `pytest --collect-only -q` per tier + file/function counts; `lint-imports` edge count and `_RECORDED_IGNORE_EDGE_CAP`; `radon cc -s -j dadaia_workspace` ceiling; `dadaia bugs stats`
  - deletes: none
  - parallelism: none — runs first

---

## `alpha-1` — vocabulary, the one value, the free deletion (strictly serial)

- [x] **T-051-01** — `CONTEXT.md`: the 16 overloaded terms resolved · owner: product-engineer · write set: `CONTEXT.md` (repo root, new) · acceptance: A-11.1
  - content: one canonical meaning + an **Avoid** list per term, exactly as ruled in R4 — context, session, bind, invocation, root, gate, chokepoint, verdict, projection, harness, drift, record, histo, terminal, canon, handoff, doctor, store/registry/service
  - deletes: none (the only additive task in the release; ~1 file, no production LOC)
  - parallelism: none — naming gate for every later task

- [x] **T-051-03** — K1: `core.invocation` — one value resolved once per process · owner: software-engineer · write set: `dadaia_workspace/core/invocation.py` (new), `dadaia_workspace/core/specs_resolver.py`, `dadaia_workspace/core/session_env.py`, `dadaia_workspace/features/spec_context/session_identity.py`, `dadaia_workspace/cli/_specs_resolution.py`, `dadaia_workspace/cli/commands/context.py`, `dadaia_workspace/cli/commands/reports.py`, `dadaia_workspace/container.py`, `dadaia_workspace/hooks/{sdd_gate,sdd_post_gate,ctx_inject,pre_gate,root_whitelist}.py`, `tests/unit/core/test_invocation.py` (new) + the 14 mirrored test files, `tests/contract/test_core_file_io_purity.py` · acceptance: A-1.1 … A-1.5, A-0.2 (8→1, 3→1, 4→1)
  - deletes: 8 context ladders · 3 sid ladders · 5 `_resolve_workspace` copies · `context._load_session` · `_session_is_stale` · `container.resolve_context` (0 callers) · `container._context_specs_dir` root fallback · `reports.py:709` env read · 5 copies of the name-allowlist regex — ~350 LOC
  - tests: 14 mirrored files → one table-driven `test_invocation.py` over `(env, cwd, payload, records)`; written and green **before** any ladder is deleted
  - bug: `sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-worktree-outside-repos` — RED case first, resolved with lineage
  - preconditions: T-051-01 `[x]`
  - parallelism: none — shares `container.py` with T-051-04

- [x] **T-051-04** — K9 deletion half: purge the composition root · owner: software-engineer · write set: `dadaia_workspace/container.py`, `dadaia_workspace/features/repos/**` (deleted), `dadaia_workspace/infrastructure/` single-consumer modules that move inside their feature, `pyproject.toml`, `poetry.lock`, the matching `tests/unit/**` files · acceptance: A-9.1, A-9.2, A-9.4
  - deletes: `_workspace_python_bin` · `_repo_hygiene_sweeper` · `_definition_committer` · `_closure_committer` (a `git add -A` committer) · `_memory_lint_gate` (dead since `b94aede3`) · `features/repos` + `ExcelReader` + the `openpyxl` dependency — ~500 LOC
  - keeps: `TelemetryRefreshLock`, `FilePermissionSetter`, `ShutdownHandler` — the three real seams
  - out of scope: retiring the ~17 one-adapter protocol files — gated on the operator accepting T-051-05's ADR
  - preconditions: T-051-03 `[x]` (shared file)
  - parallelism: none

- [x] **T-051-05** — ADR proposals: P-01/P-08 protocol-per-adapter, P-09 home rename · owner: software-architect · write set: `specs/ADRs/decisions.jsonl` · acceptance: A-9.3
  - content: one record proposing that the ring rule stays and the "every adapter behind a protocol" requirement is dropped from P-01/P-08 as measured, with the container-funnel evidence; the same or a sibling record carrying P-09's home move `core.specs_resolver.resolve_context` → `core.invocation.resolve`
  - status: **`proposed`** — an agent never writes `accepted`
  - deletes: none (governance record; zero production LOC)
  - commit: `BACKLOG.json`/`decisions.jsonl` alone (`dd-gitflow-default` §3a shape 2)
  - parallelism: none

- [ ] **T-051-06** — `alpha-1` QA close · owner: qa-engineer · write set: `specs/releases/0.5.1/RELEASE.json` (`segment`, one `log` entry), the segment's task markers · acceptance: A-0.2, A-0.5, A-0.6 for T-051-01/03/04/05
  - verdict records: decider counts before→after · the `file:line` coverage map for every deleted test file · pyramid shape · bug-surface delta per touched feature with bug-history evidence
  - deletes: none
  - parallelism: none — closes the segment

---

## `alpha-2` — what the sid unblocks, plus K5 (disjoint write sets, parallel)

- [ ] **T-051-07** — K2: presence owns liveness and GC end-to-end · owner: software-engineer · write set: `dadaia_workspace/features/spec_context/{presence,doctor,gate_policy}.py`, `dadaia_workspace/hooks/sdd_post_gate.py`, `dadaia_workspace/hooks/ctx_inject.py`, `dadaia_workspace/features/tmp_gc/service.py`, `dadaia_workspace/core/record_liveness.py`, `tests/unit/features/spec_context/test_presence_gc.py` (new) + the four reaper test files · acceptance: A-2.1 … A-2.4, A-0.2 (4→1 GC authorities, 4→1 staleness predicates)
  - deletes: `sdd_post_gate.py:213-537` · `_reap_zombie_lifecycle_runs` (reaper for a demolished engine) · `gate_policy._heartbeat_age_seconds` · `tmp_gc/service._age_seconds` + its marker lane · one of two throttle-marker idioms — ~400 LOC; post-gate ≤ 60 LOC
  - tests: `test_post_gate_reap`, `test_doctor_presence_sweep`, `test_doctor_gc`, the `tmp_gc` marker tests → `test_presence_gc.py`, plus a case pinning that no reaper deletes a live session's own bind record
  - preconditions: T-051-06 `[x]` (needs `Invocation`'s sid)
  - parallelism: parallel with T-051-08, T-051-09 — disjoint write sets

- [ ] **T-051-08** — K7: split `chokepoints.service`; one verdict store · owner: software-engineer · write set: `dadaia_workspace/features/chokepoints/{branch_policy,pre_commit,push_gate,verdict}.py` (new), `dadaia_workspace/features/chokepoints/service.py` (deleted), `dadaia_workspace/features/specs/doctor_release.py`, `dadaia_workspace/cli/commands/ci.py`, `.github/scripts/pr-verdict-check.sh`, `setup.cfg`, `tests/contract/test_import_linter_ignore_cap.py`, the chokepoints test files · acceptance: A-7.1 … A-7.4, A-0.3
  - deletes: `iter_security_approvals` · `gc_consumed_push_verdicts` (hand-reachable only) · `LEDGER_RELPATH` · `_Approval` · `GcOutcome` · the `gc-push-verdicts` CLI verb · legacy `caller_pid`/`pid_probe`/`ancestry` params · the second `_PathMasker` predicate · 2–3 import-linter suppressions — ~300 LOC; cap **18 → 15** in the same commit
  - tests: one test per new module + one `covering_verdict(paths, head_sha)` table test
  - preconditions: T-051-06 `[x]`
  - parallelism: parallel with T-051-07, T-051-09

- [x] **T-051-09** — K5: bug status transitions + one ledger parser + the backlog's four checkers · owner: software-engineer · write set: `dadaia_workspace/core/models/bugs.py`, `dadaia_workspace/features/bugs/service.py`, `dadaia_workspace/cli/commands/bugs.py`, `dadaia_workspace/cli/commands/backlog.py`, `dadaia_workspace/features/specs/{doctor,doctor_governance}.py`, `dadaia_workspace/features/backlog/{document,doctor}.py`, `dadaia_workspace/infrastructure/jsonl_record_store.py`, `dadaia_workspace/public/schemas/{bugs,backlog}/*.json`, the matching test files · acceptance: A-5.1 … A-5.5, A-0.2 (4→1 ledger parsers)
  - deletes: `_iter_native_bug_records` · the inline re-parse loop · the `bugs/*.md` `Status:` regex checker (that file shape died two migrations ago) · `governance_completeness_gaps` · `coherence_violations` · `_print_coherence_warnings` · the SPEC-DOC-033 WARNING branch · status handling in `_parse_set_options` · 3 of the backlog's 4 checkers — ~250 LOC
  - tests: transition table test (verb × missing-field matrix) + one malformed-line test; the completeness-detector and duplicated backlog-checker tests deleted with their subject
  - bugs: `backlog-cli-help-cites-retired-ledger-and-bl-dup` and `backlog-spec-doc-035-flags-agents-md-as-loose-file` fixed with RED cases; `bug-record-write-once-evidence-fields-can-embed-selfscan-triggering-literal-with-no-correction-path` set `superseded_by=deepening-simplification-k1-k11` via `dadaia bugs update --set`, never `--event`
  - preconditions: T-051-06 `[x]`
  - parallelism: parallel with T-051-07, T-051-08

- [ ] **T-051-10** — `alpha-2` QA close · owner: qa-engineer · write set: `specs/releases/0.5.1/RELEASE.json`, the segment's task markers · acceptance: A-0.2, A-0.3, A-0.5, A-0.6 for T-051-07/08/09
  - verdict records: the same five items as T-051-06, plus the ignore-cap move evidenced at 15
  - parallelism: none — closes the segment

---

## `alpha-3` — the three big tables (disjoint write sets, parallel)

- [ ] **T-051-11** — K3: one `ProjectionRule` table; harness as a real seam · owner: software-engineer · write set: `dadaia_workspace/features/public/service.py`, `dadaia_workspace/features/public/harnesses/{claude,codex,kimi}.py` (new), `dadaia_workspace/infrastructure/{public_assets,install_helpers,workspace_guardrail,runtime_config,codex_doctor}.py`, `dadaia_workspace/features/workspace/service.py`, `dadaia_workspace/core/workspace_layout.py`, the public-assets/codex test files · acceptance: A-3.1 … A-3.5, A-0.2 (5 compare semantics → 1, 4 sha sites → 1)
  - deletes: `runtime_expectations` · every `_step_*`/`_install_*` · the `"[ok] "/"[skip] "` transcript protocol and its parsing · `_KIMI_DIRS` · `remove_stale_files` (0 callers) · `_render_codex_pack_agent` (0 callers) · `_doctor_guardrail_pair` duplication · the dcx1/2/4/5/10 regexes (~250 LOC) · 8 `from runtime_config import` stanzas + 4 `noqa: F401` shims · `workspace/service._install_for_harnesses` — ~900 LOC
  - order inside the task: author the rule table → switch `install` → switch `doctor` → switch the ledger, each independently green with `dadaia public doctor` clean between steps
  - tests: `test_public_assets_{install,doctor,profile,kimi,hooks,render}`, `test_install_target_goldens`, `test_consumer_fanout*`, `test_codex_*` (5) → one "rule set per profile" table test + one write/compare pair + per-harness golden renders
  - preconditions: T-051-10 `[x]`
  - parallelism: parallel with T-051-12, T-051-13

- [x] **T-051-12** — K4: one `CANON` table + the R7 law drift · owner: software-engineer · write set: `dadaia_workspace/features/specs/canon/**` (new), `dadaia_workspace/features/specs/{specs_canon,scaffolder,doctor_structural,doctor_closure_audit}.py`, `dadaia_workspace/features/spec_artifacts/**` (deleted), `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md` (re-projected), the scaffold/doctor test files · acceptance: A-4.1 … A-4.5, A-0.2 (3 canon definitions → 1)
  - deletes: the `scaffolder` numbered `_write` blocks (they write `releases_histo.jsonl`, absent from `DADAIA.md` §6.2) · `check_tree4_required_dirs` · `check_tree8_canon_root`'s inline list · `check_archive_dirs_exist` · the whole `features/spec_artifacts` package (it exists only to dodge the cross-feature lint; its two writers become `scaffold_entry`) — ~300 LOC
  - R7: `public/scaffold/releases/AGENTS.md` still describes `RELEASE.jsonl` and a `reviews/` member — canon is `RELEASE.json`, no `reviews/`; fix at the source and re-project (`public stage` → `install --target all` → `doctor`)
  - tests: six scaffold-vs-doctor regressions + `check_tree4/8` units + `spec_artifacts` tests → one property test `scaffold(t) ⇒ doctor(t) == []`
  - preconditions: T-051-10 `[x]`
  - parallelism: parallel with T-051-11, T-051-13

- [x] **T-051-13** — K6: `features/handoff` — one index, one artifact rule, one version router · owner: software-engineer · write set: `dadaia_workspace/features/handoff/**` (new), `dadaia_workspace/core/models/handoff.py` (deleted), `dadaia_workspace/features/reports/{validation,next,retention}.py`, `dadaia_workspace/panel/reports_doctor.py` (deleted), `dadaia_workspace/panel/views/api_reports.py`, `dadaia_workspace/cli/commands/reports.py`, `dadaia_workspace/features/chokepoints/verdict.py` (call site only), `dadaia_workspace/features/specs/doctor_release.py` (call site only), `dadaia_workspace/infrastructure/stdlib_handoff_validator.py`, the 12 reports test files · acceptance: A-6.1 … A-6.4, A-0.2 (10 readers → 1)
  - deletes: `panel/reports_doctor.py` · `_detect_sidecar_version` + `_check_v10_compat` · `_handoff_artifact_paths` · `api_reports._iter_handoffs` + its severity/expiry re-derivations · `ValidatorPort` · `core/models/handoff.HandoffDocument` (0 importers) — ~330 LOC
  - tests: 12 reports test files (**2,162 LOC**) + panel sidecar fixtures → `HandoffIndex` tests; CLI tests become exit-code tests
  - bug: `reports-validate-resolves-self-pull-refs-against-the-checked-out-branch-not-the-reviewed-tree` — RED case first; resolution against the reviewed tree lives in `Handoff.artifact_path()`
  - note: the `verdict.py` / `doctor_release.py` edits are **call-site only**; if T-051-08 is still `[-]`, coordinate the two-line change rather than editing the module's logic
  - preconditions: T-051-10 `[x]`
  - parallelism: parallel with T-051-11, T-051-12

- [ ] **T-051-14** — `alpha-3` QA close · owner: qa-engineer · write set: `specs/releases/0.5.1/RELEASE.json`, the segment's task markers · acceptance: A-0.1, A-0.2, A-0.4, A-0.5, A-0.6 for T-051-11/12/13
  - verdict records: `public doctor` 0 drift · `specs doctor` on a fresh scaffold · the property test's evidence · deletion coverage map · bug-surface delta
  - parallelism: none — closes the segment

---

## `alpha-4` — read-side tail, the ruling, two standalone bugs (disjoint write sets, parallel)

- [ ] **T-051-15** — K8: one telemetry connection owner; table-driven panel routes · owner: software-engineer · write set: `dadaia_workspace/features/telemetry/{service.py,store/**,aggregator/**}`, `dadaia_workspace/features/panel/handler.py`, `dadaia_workspace/panel/views/**` (route table only), `dadaia_workspace/cli/commands/panel.py`, `dadaia_workspace/container.py`, the telemetry/panel test files · acceptance: A-8.1 … A-8.5
  - deletes: `_try_build_telemetry` (moves into the container and shrinks) · one of `store/models.py`/`aggregator/models.py` · the `pricing_module`/`reader_factory` injections · `AuthClass` + `_BEARER_*` (inert since no-auth) · `handler._dispatch_telemetry`'s 100-line ladder + its legacy bypass · the inline `api_agent_sessions` branch · 3 of the 4 route tables — ~550 LOC; handler **735 → ≤ 300**
  - tests: route-table test + `TelemetryStore` lifecycle test including `integrity_check`/`quarantine`
  - bug: `radon-undercounts-nested-class-in-function-complexity-vs-ruff-c901` — the factory it measures is deleted here; set `superseded_by=deepening-simplification-k1-k11` naming the deleting commit
  - preconditions: T-051-14 `[x]`
  - parallelism: parallel with T-051-16 … 19

- [ ] **T-051-16** — K10: delete the pre-v6 migration lineage, the shipped duplicates, and 6 frontmatter parsers · owner: software-engineer · write set: `dadaia_workspace/features/migrate/{bugs_jsonl,bugs_single_file,tree_v2,agent_tier_frontmatter,retired_frontmatter_keys,frontmatter_keys}.py` (deleted), `dadaia_workspace/features/migrate/registry.py`, `dadaia_workspace/features/bugs/migrate_v5.py` (deleted), `dadaia_workspace/public/scripts/generate-memory-catalog.py` (deleted), `dadaia_workspace/core/frontmatter.py` (new), `dadaia_workspace/core/models/adr.py` (deleted), `dadaia_workspace/features/specs/{memory_lint,catalog}.py`, the matching test files · acceptance: A-10.1 … A-10.4, A-0.2 (4 parsers → 1, 7 regex copies → 1)
  - deletes: ~1,700 LOC — six migration modules · `migrate_v5.py` (638 LOC, self-labelled "deletable at 0.6.0") · the duplicate catalog script (~400 LOC) **and** the contract test that exists only to police it · `core/models/adr.py` (0 importers) · 6 of 7 `_FRONTMATTER_RE` copies
  - keeps: the registry's "stamp v6 or refuse (`<6`: upgrade to 0.4.x first)" path
  - bugs: `memory-lint-blames-missing-delimiter-for-a-yaml-parse-error` — RED case, a YAML parse error is diagnosed as a parse error; `memory-trio-missing-required-frontmatter-fields` — the required-field check half only (the trio's own frontmatter is written at T-051-25, memory being writable in CLOSURE alone)
  - preconditions: T-051-14 `[x]`
  - parallelism: parallel with T-051-15, 17, 18, 19

- [ ] **T-051-17** — K11 ruling: the git-index boundary between concurrent sessions · owner: software-architect · write set: `specs/ADRs/decisions.jsonl`, a DRAFT under `.dadaia/reports/dadaia-workspace/software-architect/` · acceptance: A-12.1 (bugs 9/10 carry a stated disposition, never a silent drop)
  - content: the two options — `bind` provisions a per-session worktree, or `pre_commit` refuses when the index holds paths staged by a foreign presence — each with its bug-surface delta, its cost, and the feature it grows; one ADR record appended **`proposed`**
  - deletes: none (ruling only; no code on an agent's authority — both options grow a feature)
  - if the operator accepts inside this release: the accepted option becomes an `rc` task under T-051-24; otherwise bugs 9 and 10 stay `open` with this record as their stated reason
  - preconditions: T-051-14 `[x]`
  - parallelism: parallel with T-051-15, 16, 18, 19

- [ ] **T-051-18** — bug: mutation baseline `core/models` scope omits the public-schemas fixture directory · owner: software-engineer · write set: `tests/scripts/run_mutation_baseline.sh`, the mutation-baseline config/fixture paths, `specs/bugs/BUGS.jsonl` · acceptance: A-12.1, A-12.2 — RED reproduction first, `resolved` with red-loop command, regression seam and diff direction
  - deletes: the scope duplication that caused the omission — the scope list has one home after the fix
  - preconditions: T-051-14 `[x]`
  - parallelism: parallel with T-051-15, 16, 17, 19

- [ ] **T-051-19** — bug: secret-scan workflow never runs on develop PRs, so its required context blocks every merge · owner: software-engineer · write set: `.github/workflows/*.yml`, `specs/bugs/BUGS.jsonl` · acceptance: A-12.1, A-12.2 — the required context is produced on a `develop`-targeted PR, evidenced by a real run
  - deletes: the trigger duplication; one trigger definition covers both edges after the fix
  - preconditions: T-051-14 `[x]`
  - parallelism: parallel with T-051-15, 16, 17, 18

- [ ] **T-051-20** — `alpha-4` QA close · owner: qa-engineer · write set: `specs/releases/0.5.1/RELEASE.json`, the segment's task markers · acceptance: A-0.2, A-0.5, A-0.6, A-12.1 … A-12.3 for T-051-15 … 19
  - verdict records: deletion coverage map · bug-surface delta · every picked bug's terminal token or its stated `open` reason
  - parallelism: none — closes the segment

---

## Scope complete

- [ ] **T-051-21** — Invariants measured · owner: software-engineer · write set: none in-repo (captures under `.dadaia/tmp/software-engineer/<YYYYMMDD>/`) · acceptance: A-0.1 … A-0.5 with `baseline → measured` per line
  - measures: `git diff --stat` production LOC over the release range **and per FR range**; the ten decider counts of A-0.2; `pytest --collect-only -q` before/after; `lint-imports` edges + cap; the four doctors; `dadaia bugs stats`
  - a measured overshoot is recorded as a drift, never renegotiated
  - parallelism: none

- [ ] **T-051-22** — Trio review on one commit, thawed tree · owner: code-reviewer + security-reviewer + qa-engineer · write set: `specs/releases/0.5.1/verdicts/<40-hex-sha>.handoff.json` (security), handoffs for the other two · acceptance: A-0.6 — all three APPROVE the **same** commit; each states the bug-surface delta with bug-history evidence
  - the security verdict carries `agent: "security-reviewer"`, `verdict: "APPROVED"` and a **40-hex** `metrics.commit_sha`; a short sha or branch name is silently skipped by the CI gate
  - parallelism: none

---

## `rc` lane

- [ ] **T-051-23** — `rc-1`: PR `feature/0.5.1` → `develop` · owner: dispatcher (+ security-reviewer) · write set: `specs/releases/0.5.1/RELEASE.json` (`rc: 1`), git refs · acceptance: merged with **every** CI job green, verdict covering the PR head sha
  - watch CI on a loop until all jobs are green; a red job is fixed at its root cause and the watch resumes
  - parallelism: none

- [ ] **T-051-24** — `rc-2 … rc-N`: adjustment rounds · owner: software-engineer + qa-engineer · write set: per round, the fix's own files + `specs/releases/0.5.1/RELEASE.json` · acceptance: fixes on this scope only — never new backlog; one QA close and one merge per round
  - carries the accepted K11 option if, and only if, the operator accepted T-051-17's ADR inside this release
  - parallelism: none

---

## Final `rc` — closure

- [ ] **T-051-25** — Memory update · owner: product-engineer · write set: `specs/memory/ARCHITECTURE.md`, `specs/memory/TECHSTACK.md`, `specs/memory/QUALITY.md`, `specs/memory/product/**`, `specs/releases/0.5.1/RELEASE.json` (`phase: CLOSURE` first) · acceptance: `dadaia specs doctor` reports the memory atoms clean (A-0.4)
  - protocol: `MEMORY-UPDATE.md`; memory describes current state only — no changelog, no history
  - content: P-09's named home → `core.invocation`; Part 2 implementation text for the eleven deepened surfaces; the frontmatter fields the open bug `memory-trio-missing-required-frontmatter-fields` names; atoms for deleted features (`repos`, the pre-v6 migrations) deleted outright; `product/index.md` touched only if catalog order/membership changed
  - preconditions: every task `[x]`; trio APPROVED on one sha
  - parallelism: none

- [ ] **T-051-26** — Closure narrative + disposition sweep + artifact GC · owner: product-engineer · write set: `specs/releases/0.5.1/RELEASE.json` (`log`), `specs/backlog/_archive/backlog_histo.jsonl` (in-place terminal token), `specs/bugs/BUGS.jsonl` · acceptance: A-12.1 … A-12.3; `dadaia bugs stats` and `dadaia backlog doctor` show zero non-terminal picked items
  - `log` entries: `closure-summary`, `closure-size-accounting` (the A-0.1/A-0.2 numbers), `closure-drift`, `closure-dispositions`, `closure-test-dispositions`, `closure-artifact-gc`, `closure-intake-candidates`, `closure-rc-ledger`, `closure-archive-decision` — never a `CLOSURE.md`, never a `RELEASE.jsonl`
  - sweep: `deepening-simplification-k1-k11` rewritten to its terminal token — **one** histo record updated in place, never a second line; the two `superseded` bugs and every `resolved` bug verified terminal; bugs 9/10 left `open` with their stated reason if the K11 ADR was not accepted
  - GC: this release's own `.dadaia/` artifacts only; refuse any target outside `.dadaia/`; never follow a symlinked directory; keep anything a surviving `log` entry references
  - residuals: listed for the PM's operator-facing intake report — `product-engineer` creates no backlog entry
  - parallelism: none

- [ ] **T-051-27** — Archive · owner: product-engineer (authoring) + software-engineer `[git]` · write set: `specs/releases/0.5.1/RELEASE.json` (`phase: ARCHIVED`), `git mv specs/releases/0.5.1/ specs/releases/_archive/0.5.1/` (whole directory, verdicts included, per `DADAIA.md` §6.2 and the operator ruling of 2026-08-28), `specs/releases/_archive/releases_histo.jsonl` (one summary record appended) · acceptance: `specs/releases/0.5.1/` no longer exists live, `_archive/0.5.1/RELEASE.json` carries `phase: ARCHIVED`, the histo record exists, in the same commit as T-051-25/26
  - law drift: `dd-release-implement/RC-FLOW.md` step 12 still says "no per-release archive directory" — fixed at the source (`public/skills/...`) in T-051-12 with the other R7 drift
  - order is fixed: memory → closure narrative → disposition sweep → artifact GC → archive
  - parallelism: none

- [ ] **T-051-28** — Ship PR `develop` → `main`, then cut the next branch · owner: dispatcher (+ security-reviewer) · write set: git refs; the `shipped` milestone recorded in the histo summary · acceptance: PR merged with every CI job green; `feature/0.5.1` deleted and `feature/{next}` cut from `main` in the same step
  - publication stays withheld: no tag, no PyPI, no `release.yml` approval, unless the operator orders otherwise (R9)
  - parallelism: none
