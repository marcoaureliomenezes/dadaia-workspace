# Bug-history forensic — the last 100 reported bugs

**Scope.** The 100 most recent `reported` events in `specs/bugs/bugs.jsonl` (by `ts`), from
2026-07-26 to 2026-08-26 — 31 days, **3.2 bugs reported per day**. Ledger at HEAD of
`feature/0.4.5`: 503 reported / 474 resolved / 13 superseded / 12 deferred / 4 rejected.
Every number below is reproducible from the commands in the Appendix; scratch scripts live
in `.dadaia/tmp/claude-code/20260826/` (workspace root). Read-only research: no tracked
file other than this one was touched.

**Method.** For each bug the *resolution commit* is the first commit across all refs
(including the 50 `archive/*` tags, merges excluded) whose diff adds the bug's `resolved`
ledger line. Granularity: `exact` = that commit adds one resolved line and touches something
outside `specs/`; `squash` = the commit adds more than one bug line (a release ship);
`ledger` = only `specs/` touched (the fix landed in some other, unattributable commit);
`open` = no resolved event. Fix shape was classified by reading the diff for the 26 `exact`
commits and the `evidence` field of the resolved event for the rest (the evidence fields
are unusually explicit: "+54/-54", "deleted", "one guard", "negation line added").
Two extra shapes were needed beyond the requested six: `TEST-ONLY` (the defect and the fix
both live in `tests/`) and `LEDGER` (a re-affirmation event with no fix at all).

## 1. Per-bug table

| # | bug_id | sev | surface | reported | fix sha | gran | days | +/- code | shape | prior≤14d (same surface) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | a2-release-missing-spec-gate-lacks-resume-remedy | HIGH | bugs | 07-26 | 63903a71 | squash | 0.0 | - | STRUCTURAL | a2-bugs-append-context-resol(+0.0d) |
| 1 | a3-context-create-accepts-unusable-name | HIGH | spec-context | 07-26 | cb426924 | exact | 0.0 | +15/-0 | GUARD | a1-context-specs-resolution-(+0.0d) |
| 2 | kimi-hooks-noexec-home-reported-as-repairable-dr | HIGH | public-assets | 07-26 | 099f485d | exact | 0.0 | +14/-1 | BRANCH | tasks-implementability-revie(+0.8d) |
| 3 | claude-install-destroys-operator-settings | CRIT | public-assets | 07-27 | d8a039a2 | exact | 0.0 | +214/-32 | STRUCTURAL | kimi-hooks-noexec-home-repor(+0.2d) |
| 4 | claude-install-prunes-operator-authored-files | HIGH | public-assets | 07-27 | 42ac6092 | squash | 14.8 | - | STRUCTURAL | claude-install-destroys-oper(+0.0d) |
| 5 | claude-doctor-blind-to-unmanaged-projection-file | HIGH | public-assets | 07-27 | dad5afd8 | squash | 15.2 | - | GUARD | claude-install-destroys-oper(+0.0d) |
| 6 | init-skip-assets-writes-gateless-claude-settings | MEDI | workspace | 07-27 | dad5afd8 | squash | 15.2 | - | STRUCTURAL | venv-missing-dadaia-entrypoi(+1.3d) |
| 7 | rule-corpus-reachability-unchecked-on-claude-pat | LOW | public-assets | 07-27 | 42ac6092 | squash | 14.8 | - | STRUCTURAL | claude-install-destroys-oper(+0.0d) |
| 8 | public-privacy-consumer-leak-in-public-repo | HIGH | public-assets | 08-06 | e567a533 | ledger | 0.0 | - | RELOCATE | claude-install-destroys-oper(+10.6d) |
| 9 | public-doctor-exits-zero-despite-error | HIGH | public-assets | 08-06 | ec301ae3 | squash | 0.3 | - | STRUCTURAL | claude-install-destroys-oper(+10.6d) |
| 10 | retired-lib-asset-leaves-orphan-projection | HIGH | public-assets | 08-06 | ec301ae3 | squash | 0.2 | - | STRUCTURAL | public-privacy-consumer-leak(+0.1d) |
| 11 | bugs-append-accepts-second-terminal-event | MEDI | bugs | 08-07 | dad5afd8 | squash | 4.0 | - | STRUCTURAL | a2-bugs-append-context-resol(+11.6d) |
| 12 | agents-tab-model-picker-ignores-harness-runtime | HIGH | panel | 08-10 | baaee583 | ledger | 0.2 | - | BRANCH | - |
| 13 | bugs-append-allows-terminal-event-without-report | MEDI | specs-doctor | 08-10 | dad5afd8 | squash | 0.3 | - | STRUCTURAL | - |
| 14 | specs-doctor-spec-doc-033-unsatisfiable-on-histo | MEDI | specs-doctor | 08-11 | 54d982ad | squash | 0.7 | - | BRANCH | bugs-append-allows-terminal-(+0.0d) |
| 15 | workspace-venv-non-editable-install-serves-stale | HIGH | workspace | 08-11 | 54d982ad | squash | 0.0 | - | RELOCATE | init-skip-assets-writes-gate(+0.4d) |
| 16 | release-workflow-coverage-file-in-checkout | LOW | workflow-engine | 08-11 | d533fbcf | exact | 0.8 | +0/-0 | GUARD | - |
| 17 | closure-catalog-references-missing-memory-atom | LOW | bugs | 08-11 | 2ffc7d57 | squash | 0.0 | - | LEDGER | bugs-append-accepts-second-t(+0.7d) |
| 18 | blocked-close-leaves-closure-artifact | LOW | workflow-engine | 08-11 | - | open | - | - | OPEN | - |
| 19 | codex-lifecycle-timeout-not-enforced-041 | LOW | workflow-engine | 08-11 | - | open | - | - | OPEN | - |
| 20 | lifecycle-release-define-stalls-before-worker | LOW | workflow-engine | 08-11 | - | open | - | - | OPEN | - |
| 21 | gate-self-blocks-lease-holder-own-session | LOW | sessions | 08-11 | - | open | - | - | OPEN | - |
| 22 | spec-doc-029-false-forgery-harness-uuid-vs-sessi | LOW | specs-doctor | 08-11 | - | open | - | - | OPEN | specs-doctor-spec-doc-033-un(+0.0d) |
| 23 | import-linter-contracts-red-but-not-ci-enforced | LOW | workflow-engine | 08-11 | 54d982ad | squash | 0.0 | - | UNKNOWN | - |
| 24 | context-dead-nonwritable-guard-rejects-standard- | LOW | spec-context | 08-11 | 54d982ad | squash | 0.0 | - | UNKNOWN | - |
| 25 | context-dead-plain-git-push-fails-mismatched-ups | LOW | spec-context | 08-11 | 54d982ad | squash | 0.0 | - | UNKNOWN | context-dead-nonwritable-gua(+0.0d) |
| 26 | memory-heading-allowlist-not-consumer-extensible | LOW | specs-doctor | 08-11 | 54d982ad | squash | 0.0 | - | UNKNOWN | specs-doctor-spec-doc-033-un(+0.0d) |
| 27 | backlog-subjects-readme-uses-unsupported-positio | LOW | backlog | 08-11 | 54d982ad | squash | 0.0 | - | UNKNOWN | - |
| 28 | dadaia-cli-skill-command-drift | LOW | cli | 08-11 | 54d982ad | squash | 0.0 | - | UNKNOWN | - |
| 29 | gitignore-alpha-qa-review-untrackable | MEDI | lifecycle | 08-12 | 232c1405 | exact | 0.6 | +0/-0 | LIST-ADD | - |
| 30 | test-suite-real-venv-and-ci-longpole | MEDI | panel | 08-12 | d2b69b94 | exact | 0.0 | +0/-0 | GUARD | agents-tab-model-picker-igno(+1.7d) |
| 31 | panel-e2e-artifacts-no-consumer | LOW | panel | 08-12 | 63d1e245 | exact | 0.0 | +0/-0 | STRUCTURAL | agents-tab-model-picker-igno(+1.7d) |
| 32 | panel-e2e-readiness-flaky-under-xdist-load | MEDI | panel | 08-12 | 947b9587 | exact | 0.0 | +0/-0 | TEST-ONLY | test-suite-real-venv-and-ci-(+0.1d) |
| 33 | panel-command-readiness-flaky-under-xdist-load | LOW | panel | 08-12 | 931ad0e7 | exact | 0.0 | +0/-0 | TEST-ONLY | panel-e2e-readiness-flaky-un(+0.1d) |
| 34 | context-alive-sweeps-unrelated-worktree-changes | MEDI | spec-context | 08-13 | 7054ee69 | exact | 1.6 | +76/-32 | STRUCTURAL | context-dead-nonwritable-gua(+1.1d) |
| 35 | init-venv-bootstrap-inherits-degraded-base-pytho | HIGH | workspace | 08-14 | b622c17c | ledger | 0.0 | - | BRANCH | workspace-venv-non-editable-(+3.0d) |
| 36 | specs-resolver-context-tests-flaky-under-xdist-f | LOW | spec-context | 08-14 | c973b4f8 | ledger | 0.9 | - | TEST-ONLY | context-alive-sweeps-unrelat(+0.1d) |
| 37 | mypy-strict-cache-dir-created-without-cache-dir- | LOW | workflow-engine | 08-14 | 0dc527a0 | ledger | 0.8 | - | RELOCATE | release-workflow-coverage-fi(+2.3d) |
| 38 | gitignore-code-review-artifact-untrackable | HIGH | lifecycle | 08-16 | 08a9c109 | squash | 0.0 | - | LIST-ADD | gitignore-alpha-qa-review-un(+4.2d) |
| 39 | memory-token-estimate-normalizer-dead-code | LOW | memory | 08-16 | 7971eefb | exact | 0.8 | +0/-38 | STRUCTURAL | - |
| 40 | push-gate-refuses-its-own-privacy-baseline-fixtu | HIGH | git-chokepoints | 08-16 | 08a9c109 | squash | 0.7 | - | RELOCATE | - |
| 41 | memory-catalog-regenerator-orphaned-factory | LOW | memory | 08-17 | 9a09b551 | exact | 0.0 | +0/-22 | STRUCTURAL | memory-token-estimate-normal(+0.0d) |
| 42 | specs-doctor-segment-router-silent-skip | MEDI | specs-doctor | 08-17 | 3084f832 | squash | 0.1 | - | GUARD | specs-doctor-spec-doc-033-un(+5.6d) |
| 43 | privacy-baseline-noreply-local-part-not-carved-o | HIGH | git-chokepoints | 08-17 | 07c78366 | exact | 0.0 | +4/-3 | LIST-ADD | push-gate-refuses-its-own-pr(+0.1d) |
| 44 | install-target-doctor-goldens-stale-after-v043-s | MEDI | public-assets | 08-17 | 3084f832 | squash | 0.0 | - | RELOCATE | memory-heading-allowlist-not(+5.7d) |
| 45 | skill-orphans-unwired-agent-frontmatter | LOW | public-assets | 08-17 | 3084f832 | squash | 0.0 | - | LIST-ADD | install-target-doctor-golden(+0.1d) |
| 46 | repo-self-scan-hits-alpha2-qa-historical-literal | LOW | lifecycle | 08-17 | 3084f832 | squash | 0.0 | - | RELOCATE | gitignore-code-review-artifa(+1.0d) |
| 47 | ruff-0-16-2-markdown-python-fence-format-drift | MEDI | other | 08-17 | 3084f832 | squash | 0.0 | - | LIST-ADD | - |
| 48 | t043-33-absolute-path-leaked-into-tasks-md | MEDI | lifecycle | 08-17 | 3084f832 | squash | 0.0 | - | RELOCATE | repo-self-scan-hits-alpha2-q(+0.1d) |
| 49 | self-scan-baseline-drift-t04343-evidence-prose | LOW | lifecycle | 08-18 | 3084f832 | squash | 0.0 | - | RELOCATE | t043-33-absolute-path-leaked(+0.1d) |
| 50 | ancestor-walk-workspace-root-silent-mistarget | HIGH | reports | 08-18 | 3084f832 | squash | 0.0 | - | UNKNOWN | - |
| 51 | self-scan-baseline-drift-pre-pr-review-secrets-p | LOW | lifecycle | 08-18 | 3084f832 | squash | 0.0 | - | RELOCATE | self-scan-baseline-drift-t04(+0.1d) |
| 52 | post-gate-reconciler-tests-order-dependent-flake | MEDI | certification | 08-18 | 3084f832 | squash | 0.0 | - | TEST-ONLY | - |
| 53 | v043-gc-suite-windows-platform-fixtures | HIGH | hooks | 08-18 | 00c2cf5d | exact | 0.0 | +0/-0 | TEST-ONLY | - |
| 54 | reconciliation-merge-body-scan-unamendable-main- | HIGH | git-chokepoints | 08-18 | 2295bde5 | exact | 0.0 | +5/-4 | LIST-ADD | push-gate-refuses-its-own-pr(+0.6d) |
| 55 | minted-version-skips-published-lineage | MEDI | other | 08-18 | 3347d801 | exact | 0.0 | +0/-0 | RELOCATE | ruff-0-16-2-markdown-python-(+0.7d) |
| 56 | upgrade-never-refreshes-uncustomised-scoped-law- | MEDI | public-assets | 08-18 | d1da6c84 | exact | 0.3 | +109/-0 | LIST-ADD | skill-orphans-unwired-agent-(+0.9d) |
| 57 | specs-upgrade-emits-atoms-violating-frontmatter- | HIGH | specs-doctor | 08-18 | 0f63df07 | exact | 0.0 | +165/-46 | STRUCTURAL | specs-doctor-segment-router-(+1.0d) |
| 58 | specs-upgrade-blames-itself-for-a-preexisting-er | MEDI | specs-doctor | 08-18 | 1f27eb6f | ledger | 0.0 | - | BRANCH | specs-upgrade-emits-atoms-vi(+0.3d) |
| 59 | prepush-gate-omits-import-boundary-contracts-ci- | MEDI | git-chokepoints | 08-18 | 68658783 | squash | 4.9 | - | UNKNOWN | reconciliation-merge-body-sc(+0.8d) |
| 60 | symlinked-specs-root-is-followed-by-migration-an | LOW | specs-doctor | 08-19 | 68658783 | squash | 5.2 | - | GUARD | specs-upgrade-emits-atoms-vi(+0.3d) |
| 61 | atomic-writer-drift-guard-is-brittle-and-covers- | LOW | specs-doctor | 08-19 | 68658783 | squash | 5.2 | - | GUARD | specs-upgrade-emits-atoms-vi(+0.3d) |
| 62 | read-only-atom-honouring-is-advisory-and-root-by | LOW | specs-doctor | 08-19 | 68658783 | squash | 5.5 | - | RELOCATE | specs-upgrade-emits-atoms-vi(+0.3d) |
| 63 | tmp-gc-tests-age-files-by-the-real-clock-against | HIGH | tests | 08-19 | 28574746 | ledger | 0.0 | - | TEST-ONLY | import-linter-contracts-red-(+7.0d) |
| 64 | no-ratchet-against-frozen-clock-tests-that-age-f | LOW | tests | 08-19 | 68658783 | squash | 5.2 | - | GUARD | tmp-gc-tests-age-files-by-th(+0.0d) |
| 65 | mode-preservation-test-asserts-posix-bits-on-eve | MEDI | specs-doctor | 08-19 | 7b17cc13 | ledger | 0.0 | - | TEST-ONLY | specs-upgrade-blames-itself-(+0.0d) |
| 66 | crlf-fixture-makes-a-windows-assertion-pass-for- | LOW | specs-doctor | 08-19 | 68658783 | squash | 5.2 | - | TEST-ONLY | specs-upgrade-blames-itself-(+0.0d) |
| 67 | migration-normalises-crlf-atoms-to-lf-contradict | LOW | specs-doctor | 08-19 | 68658783 | squash | 5.2 | - | RELOCATE | specs-upgrade-blames-itself-(+0.0d) |
| 68 | backlog-doctor-rejects-deferred-status-documente | LOW | backlog | 08-23 | 68658783 | squash | 0.6 | - | RELOCATE | backlog-subjects-readme-uses(+11.7d) |
| 69 | context-list-current-branch-stale-for-alive-repo | LOW | spec-context | 08-23 | - | open | - | - | OPEN | specs-resolver-context-tests(+8.0d) |
| 70 | sdd-artifact-linter-mutates-task-markers | HIGH | lifecycle | 08-23 | 68658783 | squash | 0.2 | - | GUARD | self-scan-baseline-drift-t04(+5.6d) |
| 71 | backlog-doctor-silent-on-duplicate-top-level-sec | MEDI | backlog | 08-23 | 68658783 | squash | 0.5 | - | GUARD | backlog-subjects-readme-uses(+11.7d) |
| 72 | dadaia-md-projected-twice-into-claude-code-conte | MEDI | public-assets | 08-23 | 68658783 | squash | 0.2 | - | STRUCTURAL | upgrade-never-refreshes-uncu(+4.8d) |
| 73 | codex-live-probe-gate-checks-presence-not-usabil | MEDI | certification | 08-23 | e74e9911 | exact | 0.0 | +55/-10 | BRANCH | post-gate-reconciler-tests-o(+5.7d) |
| 74 | certify-skip-detail-leaks-full-codex-output | LOW | certification | 08-23 | 7681d4f3 | exact | 1.6 | +38/-21 | GUARD | codex-live-probe-gate-checks(+0.0d) |
| 75 | codex-probe-unit-fixture-carries-real-session-uu | LOW | certification | 08-23 | 5c9be8ed | exact | 1.6 | +0/-0 | TEST-ONLY | codex-live-probe-gate-checks(+0.0d) |
| 76 | repo-agents-md-law-gate-contradicts-template | MEDI | spec-context | 08-23 | 6dcf278f | squash | 1.5 | - | STRUCTURAL | specs-resolver-context-tests(+8.2d) |
| 77 | new-branch-push-loses-prior-published-denylist-a | HIGH | hooks | 08-23 | 68658783 | squash | 0.0 | - | BRANCH | v043-gc-suite-windows-platfo(+5.7d) |
| 78 | t044-04-renumber-stale-DADAIAmd-section-citation | MEDI | public-assets | 08-23 | 68658783 | squash | 0.0 | - | RELOCATE | upgrade-never-refreshes-uncu(+4.9d) |
| 79 | v0.4.4-reviews-dir-untrackable-gitignore-recurre | MEDI | other | 08-23 | 68658783 | squash | 0.0 | - | LIST-ADD | minted-version-skips-publish(+5.4d) |
| 80 | dadaia-task-manager-stale-workspace-protocol-cit | LOW | public-assets | 08-23 | db9d0c20 | exact | 1.5 | +1/-1 | RELOCATE | t044-04-renumber-stale-DADAI(+0.0d) |
| 81 | test-public-assets-stale-grill-me-name | LOW | public-assets | 08-24 | 68658783 | squash | 0.0 | - | TEST-ONLY | t044-04-renumber-stale-DADAI(+0.1d) |
| 82 | test-public-pipeline-stale-skill-roster | LOW | public-assets | 08-24 | 68658783 | squash | 0.0 | - | TEST-ONLY | t044-04-renumber-stale-DADAI(+0.1d) |
| 83 | sdd-gate-blocks-fresh-repo-root-agents-md | MEDI | spec-context | 08-24 | 6dcf278f | squash | 1.4 | - | STRUCTURAL | specs-resolver-context-tests(+8.3d) |
| 84 | skill-orphan-checker-misses-disable-model-invoca | LOW | tests | 08-24 | 68658783 | squash | 0.0 | - | BRANCH | tmp-gc-tests-age-files-by-th(+5.0d) |
| 85 | s2-qa-close-review-leaks-home-abs-path | LOW | lifecycle | 08-24 | 68658783 | squash | 0.0 | - | RELOCATE | sdd-artifact-linter-mutates-(+0.2d) |
| 86 | self-scan-baseline-drift-t04427-test-fixture-ema | LOW | tests | 08-24 | 68658783 | squash | 0.0 | - | TEST-ONLY | skill-orphan-checker-misses-(+0.1d) |
| 87 | self-scan-baseline-drift-s4-qa-close-review-pros | LOW | lifecycle | 08-24 | 68658783 | squash | 0.0 | - | RELOCATE | s2-qa-close-review-leaks-hom(+0.1d) |
| 88 | two-atomic-writers-leak-temp-file-on-injected-os | LOW | public-assets | 08-24 | - | open | - | - | OPEN | dadaia-md-projected-twice-in(+0.1d) |
| 89 | bug-event-field-with-unicode-line-separator-sile | MEDI | bugs | 08-24 | 2b9b30c1 | exact | 1.9 | +46/-5 | STRUCTURAL | closure-catalog-references-m(+12.7d) |
| 90 | context-repo-add-accepts-foreign-context-slug | HIGH | spec-context | 08-24 | 68658783 | squash | 0.0 | - | GUARD | specs-resolver-context-tests(+9.0d) |
| 91 | context-create-accepts-slug-owned-by-another-con | HIGH | spec-context | 08-24 | 68658783 | squash | 0.0 | - | GUARD | context-repo-add-accepts-for(+0.0d) |
| 92 | gitignore-verdict-evidence-untrackable-fourth-re | MEDI | other | 08-24 | 68658783 | squash | 0.0 | - | STRUCTURAL | v0.4.4-reviews-dir-untrackab(+0.8d) |
| 93 | citation-enforcer-resolves-projected-instance-pa | HIGH | tests | 08-24 | 68658783 | squash | 0.0 | - | TEST-ONLY | no-ratchet-against-frozen-cl(+0.5d) |
| 94 | citation-mutation-fixtures-never-turn-red-on-win | HIGH | tests | 08-24 | 68658783 | squash | 0.0 | - | TEST-ONLY | citation-enforcer-resolves-p(+0.0d) |
| 95 | windows-xdist-workers-crash-on-unit-fast-tier | LOW | tests | 08-24 | - | open | - | - | OPEN | citation-enforcer-resolves-p(+0.0d) |
| 96 | verdict-gate-cannot-resolve-evidence-after-relea | HIGH | tests | 08-24 | 68658783 | squash | 0.0 | - | STRUCTURAL | citation-mutation-fixtures-n(+0.0d) |
| 97 | frozen-clock-ratchet-scans-tests-tmp-scratch-dir | LOW | tests | 08-25 | 0d9d49bb | exact | 0.0 | +0/-0 | BRANCH | verdict-gate-cannot-resolve-(+0.6d) |
| 98 | dadaia-reconcile-quarantines-sanctioned-referenc | MEDI | certification | 08-26 | 92b8b3d6 | exact | 0.0 | +54/-54 | STRUCTURAL | certify-skip-detail-leaks-fu(+1.1d) |
| 99 | dadaia-agents-md-canonical-table-omits-sanctione | LOW | public-assets | 08-26 | 43e020e9 | exact | 0.0 | +4/-3 | LIST-ADD | dadaia-task-manager-stale-wo(+1.2d) |

Legend: `+/- code` = insertions/deletions under `dadaia_workspace/` for `exact` commits only
(squash commits carry a whole release and are meaningless per bug). `prior≤14d` = the
nearest earlier bug on the same normalized surface whose resolution predates this report by
≤14 days (the surface normalizer maps free-text `component`/`surface` to 18 buckets; see
`analyze.py`). `UNKNOWN` = closed by a "need met by shipped work" sweep with no diff to read.

## 2. Loop detection

**Same-surface re-bug within 14 days.** 82 of 100 bugs have at least one earlier bug (out of
all 503) on the same normalized surface resolved ≤14 days before their report; 496 such
(earlier, later) pairs exist, 330 of them with both ends inside the last 100. This metric is
**saturated**: at 3.2 bugs/day on 18 surfaces, almost every bug has a recent predecessor, so
the 14-day/surface window does not discriminate between good and bad fixes. Two tighter
views were therefore computed:

| window | key | ADDITIVE prior (GUARD+LIST-ADD+BRANCH) | STRUCTURAL prior | RELOCATE/TEST-ONLY prior | all |
|---|---|---|---|---|---|
| 3 d | surface | 19/31 = 61% | 10/21 = **48%** | 19/31 = 61% | 51/92 = 55% |
| 7 d | surface | 22/31 = 71% | 12/21 = 57% | 24/31 = 77% | 62/92 = 67% |
| 14 d | surface | 22/31 = 71% | 15/21 = 71% | 24/31 = 77% | 67/92 = 73% |
| 14 d | fine component (path in `component`) | 5/31 = 16% | 3/21 = 14% | 6/31 = 19% | 14/92 = 15% |

Reading: a `STRUCTURAL` fix buys the surface ~3 days of quiet more often than an additive
fix (48% vs 61% re-bugged within 3 days), but at 14 days every shape converges to ~70%.
The shape of the fix is **not** what predicts the next bug; the surface is. The bugs keep
coming because the surface keeps being touched, not because individual fixes are bad.

**Top chains (fine-component key, ≤14 days, followers inside the 100):**

| # | earlier bug (shape of its fix) | followers |
|---|---|---|
| 1 | `specs-upgrade-emits-atoms-violating-frontmatter-schema` (STRUCTURAL) | `specs-upgrade-blames-itself…`, `symlinked-specs-root…`, `read-only-atom-honouring…`, `migration-normalises-crlf…` (4) |
| 2 | `push-gate-refuses-its-own-privacy-baseline-fixtures` (RELOCATE) | `self-scan-baseline-drift-t04343…`, `reconciliation-merge-body-scan…`, `self-scan-baseline-drift-s4-qa-close…` (3) |
| 3 | `tmp-gc-tests-age-files-by-the-real-clock…` (TEST-ONLY) | `no-ratchet-against-frozen-clock…` (GUARD), `mode-preservation-test-asserts-posix-bits…`, `crlf-fixture-makes-a-windows-assertion…` (3) |
| 4 | `kimi-hooks-noexec-home-reported-as-repairable-drift` (BRANCH) | `claude-install-destroys-operator-settings` (CRITICAL), `claude-doctor-blind-to-unmanaged-projection-files` (2) |
| 5 | `codex-live-probe-gate-checks-presence-not-usability` (BRANCH) | `certify-skip-detail-leaks-full-codex-output`, `codex-probe-unit-fixture-carries-real-session-uuid` (2) |
| 6 | `self-scan-baseline-drift-t04343-evidence-prose` (RELOCATE) | `reconciliation-merge-body-scan…` (LIST-ADD), `self-scan-baseline-drift-s4-qa-close…` (2) |
| 7 | `claude-install-destroys-operator-settings` (STRUCTURAL) | `claude-doctor-blind-to-unmanaged-projection-files` (1) |
| 8 | `context-repo-add-accepts-foreign-context-slug` (GUARD) | `context-create-accepts-slug-owned-by-another-context` (GUARD, +1 day — the same missing invariant re-added at a second seam) (1) |
| 9 | `citation-enforcer-resolves-projected-instance-paths…` (TEST-ONLY) | `citation-mutation-fixtures-never-turn-red-on-windows` (1) |
| 10 | `memory-token-estimate-normalizer-dead-code` (STRUCTURAL) | `memory-catalog-regenerator-orphaned-factory` (deletion exposing the next dead function) (1) |

On the coarse surface key the biggest chains are all in `specs-doctor` (the pair
`bugs-append-allows-terminal-event-without-reported` → 12 followers, `spec-doc-033-unsatisfiable`
→ 11) and `public-assets` (`claude-install-prunes…` → 9, `claude-doctor-blind…` → 9,
`install-target-doctor-goldens-stale…` → 9): those two surfaces alone carry 31 of the 100.

**Text lineage.** 18 bugs name another bug slug in their `notes`/`symptom`/`repro` (23
pairs). The named predecessor's fix shape: RELOCATE 8, TEST-ONLY 5, STRUCTURAL 5, LIST-ADD 1,
GUARD 2, LEDGER 2, open/pre-window 2. The densest lineage cluster is the privacy self-scan
family: `self-scan-baseline-drift-t04427…` cites three earlier scan bugs, `…s4-qa-close…` two,
and the evidence of the latter literally says "Third recurrence of the review-artifact-vs-
privacy-scan class".

## 3. Aggregates

**Fix-shape distribution** (83 classifiable; 8 open, 8 `UNKNOWN` sweep-closures, 1 `LEDGER`):

| shape | n | % of classifiable | mean/median code insertions (exact commits only, n) |
|---|---|---|---|
| STRUCTURAL | 21 | 25.3% | 69.4 / 50 (n=8) |
| RELOCATE | 17 | 20.5% | 0.5 / 0.5 (n=2) |
| TEST-ONLY | 14 | 16.9% | 0 / 0 (n=4) |
| GUARD | 13 | 15.7% | 13.2 / 7.5 (n=4) |
| BRANCH | 9 | 10.8% | 23 / 14 (n=3) |
| LIST-ADD | 9 | 10.8% | 24.4 / 4 (n=5) |

Additive shapes (GUARD + LIST-ADD + BRANCH) = 31 = **37% of classifiable fixes**; text/test
moves (RELOCATE + TEST-ONLY) = 31 = 37%; STRUCTURAL = 25%. The 8 STRUCTURAL exact commits
are the largest diffs (mean +69 code LOC) because 5 of the 8 are collapses that replace a
duplicated authority (`workspace_layout`, `commit_paths`, retired-frontmatter migration,
`merge_claude_settings`, control-char strip at the redact seam); the two pure deletions are
−38 and −22 LOC with 0 insertions.

**Re-bug rate by prior shape** — see §2 table. Headline: ADDITIVE 71% vs STRUCTURAL 71% at
14 d; 61% vs 48% at 3 d; 16% vs 14% on the fine key. No shape is protective at 14 days.

**Top 8 surfaces** (bug count; bugs with a same-surface predecessor ≤14 d; dominant shapes):

| surface | n | re-bug | shapes |
|---|---|---|---|
| public-assets (install/doctor/projection/law text) | 18 | 18 | STRUCTURAL 6, RELOCATE 4, LIST-ADD 3 |
| specs-doctor (doctor + migration/upgrade) | 13 | 12 | GUARD 3, STRUCTURAL 2, BRANCH 2 |
| spec-context (create/alive/dead/gate policy) | 10 | 9 | GUARD 3, STRUCTURAL 3 |
| lifecycle (release artifacts, .gitignore, review prose) | 9 | 8 | RELOCATE 6, LIST-ADD 2 |
| tests (ratchets, checkers, platform asserts) | 9 | 9 | TEST-ONLY 4, BRANCH 2, GUARD 1 |
| workflow-engine (demolished; 3 open superseded) | 6 | 1 | OPEN 3 |
| panel (e2e readiness/artifacts) | 5 | 4 | TEST-ONLY 2 |
| certification (codex probe) | 5 | 4 | TEST-ONLY 2, BRANCH 1, GUARD 1 |

**Severity mix:** LOW 45, MEDIUM 28, HIGH 26, CRITICAL 1. 45% of the ledger's last month is
LOW — mostly scanner/ratchet/prose hits and test-fixture corrections.

**FR23 triple** (`evidence_loop` + `evidence_seam` + `evidence_diff` all non-empty): **23 of
92 resolved = 25%**. 69 resolutions carry a single free-text `evidence`; the triple only
appears from v0.4.4 onward (19 of the 23 are in the 0.4.4/0.4.5 window).

**Days to resolve** (92 resolved): median **0.01 d** (≈15 min), mean 1.3 d; ≤1 d: 73; 1–7 d:
15; >7 d: 4 (max 15.2 d — the v0.3.0→v0.5.0 install-ledger pair). Bugs are fixed within the
same session almost always; the loop is fast, which is exactly why it compounds.

**Commit granularity:** exact 26, squash 58, ledger-only 8, open 8. **66 of 92 resolutions
(72%) cannot be tied to a per-bug diff** from git alone; the five squash ships carry 50 bugs
(`0.4.4` ship: 26, `0.4.3`: 10, `v0.5.0`: 8, verifier-unification PR: 4, v0.3.0 reconcile: 2).

## 4. Architectural problem classes (evidence = bug slugs)

**P1 — Hand-kept lists as truth (16 bugs).** A list that a human/agent must remember to
extend is the single most common cause. Families: `.gitignore` whitelist ×4
(`gitignore-alpha-qa-review-untrackable`, `gitignore-code-review-artifact-untrackable`,
`v0.4.4-reviews-dir-untrackable-gitignore-recurrence`, `gitignore-verdict-evidence-untrackable-fourth-recurrence`
— three LIST-ADD fixes before the fourth collapsed 65 lines into one negation);
`privacy_baseline.json` exclude regexes ×3 (`push-gate-refuses-its-own-privacy-baseline-fixtures`,
`privacy-baseline-noreply-local-part-not-carved-out`, `reconciliation-merge-body-scan-unamendable-main-squash`);
skill rosters/manifests ×4 (`skill-orphans-unwired-agent-frontmatter`, `test-public-assets-stale-grill-me-name`,
`test-public-pipeline-stale-skill-roster`, `skill-orphan-checker-misses-disable-model-invocation`);
`.dadaia/` layout allowlists ×2 (`dadaia-reconcile-quarantines-sanctioned-references-clone`,
`dadaia-agents-md-canonical-table-omits-sanctioned-references`); `shipped-hashes.json` ×1
(`upgrade-never-refreshes-uncustomised-scoped-law-projection` — a *new* hand-kept list was the fix);
ruff exclude ×1 (`ruff-0-16-2-markdown-python-fence-format-drift`); doctor goldens ×1
(`install-target-doctor-goldens-stale-after-v043-skill-additions`).

**P2 — Two writers / two authorities of one truth (14 bugs).** `a3-context-create-accepts-unusable-name`
(create vs resolver regex), `claude-install-destroys-operator-settings` (installer vs operator
file), `init-skip-assets-writes-gateless-claude-settings` (init vs install writer),
`bugs-append-accepts-second-terminal-event` + `…-allows-terminal-event-without-reported`
(CLI append vs doctor coherence), `agents-tab-model-picker-ignores-harness-runtime`,
`dadaia-md-projected-twice-into-claude-code-context`, `repo-agents-md-law-gate-contradicts-template`
+ `sdd-gate-blocks-fresh-repo-root-agents-md` (gate by name vs by origin),
`dadaia-reconcile-quarantines-sanctioned-references-clone` (two allowlists),
`specs-resolver-context-tests-flaky-under-xdist-full-suite` (env var vs cwd authority),
`public-doctor-exits-zero-despite-error` (severity re-derived in 4 consumers),
`retired-lib-asset-leaves-orphan-projection` (two prune authorities),
`upgrade-never-refreshes-uncustomised-scoped-law-projection` (upgrade vs doctor refresh).
Every STRUCTURAL fix in the window is a collapse of one of these; the collapses are the only
fixes whose evidence says "deleted" rather than "added".

**P3 — Scanner-vs-prose: the privacy gate polices the team's own review text (10 bugs).**
`repo-self-scan-hits-alpha2-qa-historical-literal`, `t043-33-absolute-path-leaked-into-tasks-md`,
`self-scan-baseline-drift-t04343-evidence-prose`, `…-pre-pr-review-secrets-prose`,
`…-t04427-test-fixture-email`, `…-s4-qa-close-review-prose`, `s2-qa-close-review-leaks-home-abs-path`,
plus the three P1 baseline-regex bugs. All ten are LOW/MEDIUM, all fixed by editing prose or
a regex, none by changing where review prose is allowed to live or what the scanner reads.
The fourth recurrence is explicitly acknowledged in the ledger and still produced a RELOCATE.

**P4 — Guard breeds guard: 21 bugs live in the test/ratchet layer itself.** TEST-ONLY 14 +
`no-ratchet-against-frozen-clock…` (a ratchet added as the fix) → `frozen-clock-ratchet-scans-tests-tmp-scratch-dir`
(the ratchet mis-scans, fixed by an exclusion BRANCH) → `windows-xdist-workers-crash-on-unit-fast-tier`
(open); `atomic-writer-drift-guard-is-brittle…` (+279 test lines replacing an 18-line guard);
`citation-enforcer…` → `citation-mutation-fixtures-never-turn-red-on-windows`;
`panel-e2e-readiness-flaky…` → `panel-command-readiness-flaky…` → `specs-resolver-context-tests-flaky…`
(timeouts 10→30 s, twice). Each guard is a new surface with its own platform, clock and
load semantics; 5 of these 21 are Windows-only assertion bugs.

**P5 — Coarse commits hide the fix (66 of 92).** 72% of resolutions are unattributable to a
diff; the FR23 triple is present in 25%. The architecture-review rule ("audit the fix
chain") cannot be executed from git for three quarters of the window — the ledger's
free-text `evidence` is the only record, and 8 bugs were closed by "need met by shipped
work" sweeps with no diff at all.

**P6 — Gate/doctor growth per bug (22 additive fixes).** GUARD 13 + BRANCH 9: `[unsupported]`
branch in kimi doctor, `[foreign]` doctor line, `_foreign_slug_owner` predicate then the same
invariant again at `create` one day later, `is_symlink` guard, missing-segment error,
duplicate-section error, entitlement classifier in the codex probe, healing rule for
SPEC-DOC-033, new-branch amnesty fallback. Individually small (median 7–14 code LOC) —
collectively the doctor/gate surfaces (`public-assets` + `specs-doctor` + `spec-context`) are
41 of the 100 bugs and re-bug at 39/41.

## 5. What 0.5.0 must therefore make measurable

Each metric is computable from `specs/bugs/bugs.jsonl` + git; the 0.5.0 definition review
should check that each is specified with its exact definition and a target.

1. **Per-bug diff attributability** — share of `resolved` events whose first-adding commit
   (all refs, no merges) adds exactly one `resolved` line and touches a non-`specs/` path.
   Baseline 26/92 = 28%. Command: `rebuild_map.py` + `git show --numstat <sha>`.
2. **FR23 triple coverage** — `resolved` events with non-empty `evidence_loop`,
   `evidence_seam`, `evidence_diff`. Baseline 23/92 = 25%. Command:
   `jq -c 'select(.event=="resolved") | [.evidence_loop!=null, .evidence_seam!=null, .evidence_diff!=null]' specs/bugs/bugs.jsonl | sort | uniq -c`.
3. **Fix-shape ratio** — STRUCTURAL / (GUARD + LIST-ADD + BRANCH), read from a mandatory
   machine-readable `evidence_diff.shape` token (the current free text already says
   "net-negative"/"net-neutral"/"net-positive": make the token the field). Baseline 21/31 = 0.68.
4. **Same-surface re-bug rate** at 3 d and 14 d on a **canonical surface id** (a required
   `surface` enum, not free text — 100 bugs used 86 distinct `component` strings). Baseline
   55% (3 d) / 73% (14 d). Command: `analyze.py` with the enum replacing `RULES`.
5. **Hand-kept-list touch count** — commits closing a bug whose diff touches `.gitignore`,
   `privacy_baseline.json`, `shipped-hashes.json`, `*_golden/*.json`, `EXPECTED_SKILLS`, or a
   `frozenset({...})` literal in `dadaia_workspace/`. Baseline 16/83. Command:
   `git show --name-only <sha> | grep -E 'gitignore|privacy_baseline|shipped-hashes|_golden'`.
6. **Test-layer bug share** — bugs whose `component` starts with `tests/` or whose fix is
   TEST-ONLY. Baseline 21/100. Command: `jq -r 'select(.event=="reported") | .component' | grep -c '^tests/'`.
7. **Scanner-vs-prose recurrence** — bugs whose `symptom` matches
   `self-scan|denylist|privacy` and whose fix touches only `specs/**/*.md` or `tests/`.
   Baseline 10/100; target 0 by moving review prose out of the scanned tree or scanning
   only code. Command: `jq -r 'select(.event=="reported") | select(.symptom|test("self-scan|denylist|privacy")) | .bug_id'`.
8. **Sweep closures** — `resolved` events whose `evidence` matches `^Need met` or
   `re-affirmation` with no code-touching commit. Baseline 9/92; target 0 (a sweep closure is
   a `superseded` event naming the release, not a `resolved`).

## Appendix — reproduction

All scripts under `.dadaia/tmp/claude-code/20260826/`, run from the repo root on `feature/0.4.5`.

- Map ledger lines → first adding commit: `python3 rebuild_map.py bug-commit-map-all-refs.json`
  (`git log --all --reverse --no-merges --format=%H|%ct|%s -- specs/bugs/`, then
  `git show --format= --unified=0 <sha> -- specs/bugs/`, parse `+{...}` lines; 1003 keys).
- Per-bug metrics, granularity, priors, lineage: `python3 analyze.py` → `last100.json`
  (surface normalizer = `RULES` list; loop = same surface, `res_ts ≤ rep_ts ≤ res_ts+14d`).
- Evidence dump used for shape reading: `evidence.txt`; exact-commit diffs: `exact_diffs.txt`
  (`git show --format= -U2 <sha> -- dadaia_workspace/ .github/ .gitignore pyproject.toml`).
- Shape assignments (the `SH` dict, one entry per table row) and every aggregate in §2–§3:
  `python3 aggregate.py`; window/fine-key variants and lineage shapes: `python3 windows.py`
  (`rate(key, win)` over `last100_shaped.json`).
- Ledger counts: `jq -r .event specs/bugs/bugs.jsonl | sort | uniq -c`.
