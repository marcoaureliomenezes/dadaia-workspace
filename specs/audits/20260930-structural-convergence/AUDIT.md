# Audit 20260930-structural-convergence

- **Timestamp:** 2026-09-30T01:40Z.
- **Window:** `[fe04319a, 3a279529]` on `feature/0.5.0`: 2654 commits (2530 non-merge), 240 ledger commits.
  The newest `audits_histo.jsonl` record (`20260830-design-bug-surface-audit`) carries no sha, so the start is
  the commit that appended it (`git log -S`, ship 0.4.5, PR #240).
- **Agents:** `dd-code-reviewer` ×3 (audit lens, read-only; one per pillar); `dd-product-engineer` (synthesis,
  FINDINGS, `audited` stamps).
- **Scope:** context `dadaia-workspace`. Covers 223 `BUGS.jsonl` records in the window, the specs tree, ADRs 0001–0120,
  23 active backlog entries, and the memory tree.
- **Origin:** the operator, 2026-09-30: "devemos fazer um audit completo que virará uma release governada registrada,
  devemos estar atentos bugs que podem virar superseded … o problema arquitetural de se resolver bug a bug sem
  olhar o todo".
- **Findings:** 150 in `FINDINGS.jsonl`, all `open`. Ids are `20260930-structural-convergence-Fnnn`, cited below as `Fnnn`.

| Pillar | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| bugs | 0 | 8 | 31 | 12 | 51 |
| specs | 0 | 6 | 35 | 20 | 61 |
| memory | 0 | 16 | 15 | 7 | 38 |

## Pillar 1 — bugs

In the window: 223 records (189 resolved, 33 open, 1 rejected), none stamped before this audit.

| # | Metric | Measured | Baseline | Target | F |
|---|---|---|---|---|---|
| 1 | Registrations per session | unmeasurable: no `governance_events` source exists; proxy 2.53 per ledger commit, max 20 | n/a | a real source or a redefinition | F001 |
| 2 | Evidence-triple coverage | 189/189, presence only | 38% | 100% verified | F002 |
| 3 | Fix-shape neg/(neu+pos) | 1.70; net-positive 21% | 0.42 | ≥1.5, net-positive ≤10% | F003 |
| 4 | Same-surface re-bug 3d/14d | 71% / 82% | 69% / 86% | ≤30% / ≤50% | F004 |
| 5 | Hand-kept-list touches | 36% (shipped-hashes 50, _golden 38) | 19% | ≤10% | F005 |
| 6 | Test-layer bug share | 6.3% | 32% | ≤10% | F006 |
| 7 | Scanner-vs-prose recurrence | 3 | 0 | 0 | F007 |
| 8 | Sweep closures as resolved | 0; 12 closed <60 s, 51 <10 min | 0 | 0, and no no-red-loop closures | F008 |

- 37 of 189 resolutions are fix-induced; 29 of 155 since 2026-09-22 (F009).
- Cross-cutting cause: "one question, N deciders". All 75 `sa-*` collapses are resolved, yet 3 open bugs regress them. Each one regresses at the point where its collapse stopped: the package/stdlib-script seam or an env override (F010).
- Ledger integrity:
  - the surface enum is not enforced at append (F011);
  - `caused_by` has 2 cycles and 3 dangling ids (F012);
  - 3 open records carry `caused_by: null` although their own text names the `sa-` record they regress (F013).
- Clusters by structural cause (the rule counts are ±10%, for ranking only):
  - Still producing: SCOPE 90, ROOT 62, FIXTEXT 55 (41 since 09-22, the hottest), PRIVACY 38, PROJ 71, LEDGER 80, SPECS 32.
  - Slowing: TESTS 68 (22% fix-induced, the highest), GIT 33, CTXLIFE 30.
  - Stopped: ENGINE 134. Its chain (4 deep) ended only when 0.4.7 c5 deleted the engine. This is the evidence that deletion, not patching, ends a family.

## Pillar 2 — specs

- Commit shapes (§3a), candidate-4 sub-window of 510 commits:
  - Shape 3 (HIGH, F055): 18 of 114 fixes are not self-contained, and 9 RED commits are split from their fix. The cause is that dd-bug-resolution teaches RED first while §3a demands one commit: two rules answer the same question.
  - Shape 1 is clean in c4 (7 off-set across the window, F053).
  - Shape 2: `5f6bb714` mixes decisions.jsonl with ARCHITECTURE.md (F054).
  - Shape 5: `1528a8e0` defines with PLAN+TASKS only (F056).
  - 1317 commits match no shape, e.g. marker flips and memory/law writes (F057).
- Canon: the doctor reports 0 findings in both the specs and ledgers sections. Findings:
  - no sha in histo (F052);
  - archived releases 0.4.5–0.4.7 still keep their directories, which contradicts LINEAGE: two answers (F058);
  - releases_histo keeps sha/PR in prose only (F059);
  - backlog cites `reports/` paths that are never committed (F060);
  - the backlog exit vocabulary has no Arm B token (F063).
- Release 0.5.0 (`IMPLEMENTATION`, candidate 4, 45/46 `[x]`):
  - `implemented` predates `defined`, and the log opens "Release 0.4.8 born" (F061);
  - the SPEC's out-of-scope section contradicts ADRs 0101/0102 (F062).
- Candidate-4 close is blocked by:
  - T-050-62 Measure is not run (F064);
  - the last closure review is REJECTED 67/100 with no later APPROVED verdict (F065);
  - the closure steps were not run, and the HIGH bug reopened by `3a279529` has no vehicle (F066);
  - there are 10 prunable `wt/*` branches, and ADR 0117's migration must precede ADR 0112's refusal (F068).
- The ADR 0102 publish gate stands at 33 open bugs and 23 active entries (F067).
- `removals-shipped-without-recorded-authority` is re-filed here from the ledger (F069).

| C | ADRs | Conflict | Sev | F |
|---|---|---|---|---|
| C1 | 0072 / 0105 | 0072 refusal contradicted by code (fix reverted); its measured_by is indifferent to the bug | HIGH | F070 |
| C2 | 0103 / 0105 | bound session writes `repos/<r>/` vs "`repos/<r>` receives only merges"; 0103 not amended | HIGH | F071 |
| C3 | 0105 / 0106 / map §3 | every write in a worktree vs "audits need no worktree" vs ADDITIVE always-writable | HIGH | F072 |
| C4 | 0018 / 0109, 0106 | worktree.py merge runs checks vs no script calls another | MEDIUM | F073 |
| C5 | 0096, 0103 / backlog | gate never parses Bash vs `gate-judges-bash-writes` | MEDIUM | F074 |
| C6 | 0067 / 0096 | no venv → every wrapper fails open → core protection is zero | HIGH | F075 |
| C7 | 0092 / 0059 | `.dadaiaignore` reaches harness dirs vs ledger-owned entries only | MEDIUM | F076 |
| C8 | 0053 / 0101 / 0102 | three accepted texts read opposite on c5/c6/c7 scope | MEDIUM | F077 |
| C9 | 0089 / SPEC | ≥80/100 gate vs the operator relaxing it to a recommendation; 50 vs 78 ids | MEDIUM | F078 |
| C10 | 0088 / gate | the fenced-roots env var disables enforcement | MEDIUM | F079 |
| C11 | 0118 / 0096, 0103 | a third fail-open path; never stated in one place | LOW | F080 |
| C12 | 0112, 0106 | accepted ADRs defer their own mechanism to open grill items | MEDIUM | F081 |
| C13 | 0114 / DEC-11 | implemented "through DEC-11", shape undecided | MEDIUM | F082 |
| C14 | 0097 / 0107 | worktree letter past `z` undefined | LOW | F083 |
| C15 | 0027 | frozen surface holds; title still says create "binds" | LOW | F084 |
| C16 | 0104 / instance | 10 worktree dirs gone under a TTL zone; guard unverified | MEDIUM | F085 |

- `measured_by` that measures nothing:
  - dead verb `dadaia bugs status`: 5 ADRs (F086);
  - missing test files: 6 ADRs (F087);
  - prose or manual: 5 ADRs (F088);
  - "the delivering candidate adds": 21 ADRs (F089);
  - 0072 passes with the bug present (F070).

## Pillar 3 — memory

- Part-1 checks:
  - Passing checks: lint-imports (6 contracts kept), ruff C901/PLR1702, the ratchets, stewardship, docs-derived, doctor MEM-DRIFT/LINT-1, and `memory.py check`.
  - Stale `Measured by`: P-12, P-14, P-15, P-18 and P-32 point at deleted tests or a retired rule (F125–F129). P-33 has selector drift (F131). P-27 has no mechanism left: the pyramid is unmeasured and was deleted without an ADR (HIGH, F130).
  - P-31 is inconclusive in the sandbox (F136).
  - §4 dead-code and §5 constitution sweep were not run (F137).
  - 23 of 31 principles carry `ADR: none` (F138).
- Canonical hunks without an accepted ADR in the same commit:
  - HIGH: `b84d62f4`, `cddb8ba5`, `6a1e3b59`, `21a4e479`, `65f247c7`, `d655ccea`, `96fc5742` (F139–F145);
  - 3 unscoreable squashes (F146);
  - 1 shape-only mismatch (F147);
  - the structural cause is that no lane exists for a statement-true reconciliation of non-principle sections (F148).
- Drift, where the memory disagrees with the code or an accepted ADR:
  - specs pattern version is 7, truth 8, in ARCHITECTURE, specs-migration and public-asset-distribution (F114–F116);
  - `is_live`/`ttl_seconds` (F117);
  - ctx-inject "never law" vs ADR 0103 (F118);
  - reaper age by newest mtime vs ADR 0104 lstat (F119);
  - hook timeouts stated nowhere (F120);
  - wall-clock "no pinned number" vs ADR 0119 (F121);
  - dead flow omits the ADR 0120 archive tag (F122);
  - `packaging` missing from the runtime deps (F113);
  - seven vs six contracts (F123);
  - eight vs seven stems (F124).
- `capabilities` and `server-registry` have no reconcile entry in the whole window (F132). All 28 atoms have drifted since the last closure pass at `61e39efc` (F133).
- Hygiene: gitleaks has no manifest counterpart (F134); 6 `__pycache__`-only package dirs (F135).

## Remediation shape

Sequence, per the operator's ruling of 2026-09-30:
1. Structure first: c5 (M2) and c6 (M1) are built, and the bugs whose surface they delete close with them.
2. Then the collapses (M3–M5) and the independent bugs.
3. Every step is gated on net-negative production code and on no bug caused by the prior fix.

### Structural moves

| Move | One decider | Closes | Deletes | Needs first | F |
|---|---|---|---|---|---|
| M1 c6 | `scope(target) -> (repo, kind)`; bind reduced to context; `repos/<r>` only merges | SCOPE; 4 open bugs; scope fix lines | `sdd_gate.py:55-56` unbound ALLOW, `gate_policy` `bound_*` + `_scope_block`, `SPECS_ADDITIVE_GLOBS`, session-id in the write decision | DEC-11 (ADR 0114); C1–C3; Q3–Q8 | F014 |
| M2 c5 + one deleter | one two-level root classifier read by gate, doctor, reaper; `sweep.hold` the only deleter | ROOT; 5 open bugs | `instance_exceptions.txt`, ledger-derived PROTECTED (`sdd_gate.py:45-48`), direct deletes in `doctor.fix` | Q10 (C6, C7) | F015 |
| M3 scripts share readers | one owner per grammar/ledger/registry | LEDGER, SPECS, PRIVACY; 9 open bugs | `_backlog_exit` Origin regex, second task regex, `splitlines` readers, `_ledger._terms` cwd walk, stored `diff_direction`, ship readiness logic | new ADR: the stdlib-script seam | F016 |
| M4 one renderer | `core/cli_line` renders every BLOCK, refusal, help example | FIXTEXT; 6 open bugs | hand-spelled fix/help strings, `DADAIA_BIN`, the ledger fallback, venv_guard pip arm | ADR for the pip-arm deletion | F017 |
| M5 one child env | `tests/fixtures/harness_env.py`; live tests opt-in | TESTS; 4 open bugs | ad-hoc child envs, live Codex probe in the default suite | — | F018 |

- M2 is c5 plus a sweep.hold collapse that ADR 0092 excludes (the tmp/TTL zones). It is one move, but only part of it is covered by c5's ADRs.
- c6 must carry the study `worktree-harness-mechanics-study` (ADR 0100) into its SPEC. The scratch copy is ephemeral. Its conclusions:
  - git is the registry, and the `--lock --reason dadaia:…` is the owner marker, so no JSON state is needed and ADR 0027 holds;
  - a named `wt/` branch is cut from the work branch, never a detached HEAD;
  - a worktree is destroyed only after a verified ff-merge: never by TTL or count, never `--force`, never `branch -D`;
  - removal is refused while non-disposable ignored files exist;
  - the doctor reports and never prunes;
  - no worktree lives under a TTL-swept dir (the 10 prunable `wt/*` here are live evidence);
  - hooks resolve from the workspace root, and `GIT_*` env is scrubbed before tool-driven git.

### Bug dispositions (33 open, all proposals)

| Disposition | Move | Bugs (F) |
|---|---|---|
| supersede-by-redesign (4) | M1 | `unbound-native-session-writes-freely-into-repos` F019 (only if c6 deletes the unbound ALLOW), `additive-globs-hand-kept-beside-the-canon` F022 |
| | M2 | `instance-exceptions-file-writable-by-agents` F020, `gate-protects-nothing-without-install-ledger` F021 (harness-interior protection survives) |
| fix-by-collapse (16) | M1 | `fenced-roots-env-disables-the-gate` F023 |
| | M2 | `bug-proposal-handoff-reaped-without-a-hold` F025 |
| | M3 | `corrupt-context-registry-crashes-doctor-and-next-step` F024, `release-ship-accepts-what-release-check-refuses` F029, `task-line-grammar-accepts-a-malformed-open-marker` F030, `spec-origin-line-has-two-readers` F032, `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger` F033, `bugs-check-trusts-evidence-fields-unverified` F034, `privacy-denylist-has-two-loaders` F036, `list-form-privacy-denylist-errors-without-migration` F037 |
| | M4 | `implementer-persona-states-a-second-task-marker-lifecycle` F031, `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids` F035, `help-examples-spell-the-blocked-bare-cli` F039, `fix-lines-are-not-one-runnable-command` F040, `dadaia-bin-still-honoured-after-adr-0045` F041 |
| | M5 | `test-suite-writes-outside-tmp` F049 |
| fix-local (11) | M1 | `corrupt-session-record-never-collected` F027 |
| | M2 | `context-dead-ignores-the-hold-refusal` F026 |
| | M3 | `secret-scan-misses-github-pat-and-anthropic-keys` F038 |
| | M4 | `pip-guard-fix-routes-project-installs-into-the-tool-venv` F042 |
| | M5 | `ci-preflight-writes-coverage-into-the-repo` F048, `default-suite-calls-a-real-model-through-codex` F050, `hook-entrypoints-invisible-to-coverage` F051 |
| | independent | `onboarding-next-step-names-another-context` F028, `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree` F043, `upgrade-leaves-reconcile-scratch-behind` F044, `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original` F045 |
| defer (1) | M2 | `missing-venv-hook-disarms-the-gate-invisibly` F046 — waits on Q10(a) |
| reject (1) | ADR repairs | `removals-shipped-without-recorded-authority` F047, re-filed as F069 |

### Backlog dispositions (23 active, all proposals)

- **IN (10):**
  - M1: `bind-scope-durable-on-every-harness` F094, `ctx-inject-on-cursor-copilot` F095, `canonical-worktrees` F106 (its description is stale and cites the superseded 0098), `worktree-harness-mechanics-study` F107 (exits `delivered` via the c6 Origin), `operator-protected-path-class` F108 (DEC-11, a prerequisite of M1).
  - M2: `dadaiaignore-and-root-core-canon` F105.
  - M3: `ledger-schema-one-engine` F103.
  - M5: `preflight-ci-parity-derived` F104, `test-intent-docstring-backfill` F112.
  - No move: `docs-site-zensical-pages` F109 is the only purely additive entry (Q9).
- **EXIT rejected (6):** `gitflow-trunk-based-model` F090, `consumer-gitflow-server-side-enforcement` F091,
  `associated-repo-gitflow-override` F092, `gate-judges-bash-writes` F093, `clone-detection` F110 (needs 0102 amended),
  `launch-operator-acts` F111.
- **EXIT superseded (2):** `task-line-grammar-one-reader` F102 (a duplicate of an open bug); `guidance-messages-name-the-right-target` F098, which splits into three parts: an open bug, a line c5 delivers, and an Arm B part.
- **EXIT via Arm B (5):** `doctor-context-ignores-other-contexts` F096, `release-memory-idempotent` F097,
  `consumer-guidance-names-no-library-toolchain` F099, `init-announces-codex-trust` F100 (rejected if 0.4.7 NEW-FR-12
  no longer stands), `tests-agents-scaffold-without-placeholders` F101. The exit token itself is open (Q12, F063).

### Memory pass worklist (dd-product-engineer, at the remediation closure)

1. Statement-true fixes now:
   - the specs version 7→8 (F114–F116);
   - `packaging` (F113);
   - the contract and stem counts (F123, F124);
   - the stale `Measured by` lines (F125–F131);
   - the hook timeouts (F120);
   - the ADR 0119 budget (F121). This one is canonical and needs an ADR-paired commit.
2. Rewrite once with c5: F149. With c6: F150, folding in F117, F118, F119 and F122. Never patch these before the redesign lands.
3. Reconcile `capabilities` and `server-registry` (F132). Run the full closure pass over the 28 atoms since `61e39efc` (F133).
4. Re-run P-31 in CI (F136). The next audit runs §4/§5 (F137). Name the reconciliation lane once instead of backfilling ADRs (F148).

### ADR repairs (to be recorded in the remediation release; none is recorded here)

- Status hygiene:
  - 0053 → superseded (F077);
  - 0101 → superseded by 0102 (F077);
  - 0103 → amended by 0105 (F071).
  - 0072 → superseded by 0105 (F070): conflicts with 0105's own text, see Contradictions.
- Amendments:
  - 0089 (Q2, F078);
  - 0106 and 0109 (Q4, F073);
  - 0102: clone detection and c7 (Q9, F077);
  - 0097 and 0107: letters past `z` (F083);
  - 0027 title (F084).
- New decisions:
  - the stdlib-script seam (M3);
  - the venv_guard pip-arm deletion (F042);
  - the memory reconciliation lane (F148);
  - shape 3 (Q13, F055);
  - the backlog Arm B exit token (Q12, F063);
  - 0.5.0 removals authority (F069);
  - the three fail-open paths stated in one place (F080);
  - 0067 vs 0096 (Q10a, F075);
  - 0092 vs 0059 (Q10b, F076);
  - DEC-11 shape (Q11, F082).
- `measured_by` repairs: F086–F089, F070.

## Decisions

- **Made (operator, 2026-09-30):** this audit becomes a governed, registered remediation release. The order is structure first: c5 and c6 are built, the bugs they supersede close with them, then the independent bugs. Every step is gated on net-negative production code and on no fix-induced bug.
- **Made (this audit):** `audited=20260930-structural-convergence` is stamped on all 223 window records. No other ledger write.
- **Pending (operator); nothing below is decided:**
  1. Q1, the vehicle: is the remediation candidate 5 of 0.5.0 or a new release? Does c4 close with the HIGH `unbound-native-session-writes-freely-into-repos` open, or wait for c6? What is the build order of c5 vs c6?
  2. Q2, ADR 0089: amend "≥80/100" to a recommendation, or re-run the rubric to ≥80?
  3. Q3, R2-1 (C2/C3): after 0105, which writes stay direct in `repos/<r>`? Only `specs/audits/**`, or every ADDITIVE ledger?
  4. Q4, R2-5 (C4): are ledger checks and tests skill steps, not `worktree.py`? If so, amend 0106/0109.
  5. Q5, R2-6: accept the review lock's fix line (`reports validate <handoff>`), knowing it proves procedure, not honesty?
  6. Q6, R2-7: the five hygiene layers (0112 waits on them).
  7. Q7, R2-8 (C16): the triage table for the 10 `wt/*` branches here, archive-tagged before any discard.
  8. Q8, bundle yes/no: R2-2, R2-3, R2-4, R2-9, R2-10, R2-11.
  9. Q9, ADR 0102 scope: do c7 and clone detection stay in a structural release? Do the launch acts leave the backlog?
  10. Q10, c5: (a) missing venv fails closed, or fails open loudly with init as the fix? (b) does `.dadaiaignore` reach harness-dir interiors?
  11. Q11, DEC-11: (a) a gate-read glob, or (b) per-harness config plus a git backstop? As a section of `.dadaiaignore`, or its own file?
  12. Q12: which backlog exit token does an idea converted to an Arm B bug take?
  13. Q13: shape 3 as one self-contained commit, or a named two-commit RED + fix shape?
  14. Every bug and backlog disposition above, plus every ADR repair. Only the remediation release dispositions them, via `audit.py disposition`.

## Contradictions between the pillar outputs

- ADR 0105's consequences read "ADR 0072's unbound refusal stands". Pillar 2 (C1) nevertheless proposes 0072 → superseded by 0105, while pillar 1 follows 0105's text. Pending operator.
- The severity of `missing-venv-hook-disarms-the-gate-invisibly` disagrees across three places: the ledger says MEDIUM, pillar 1 says DEFER, and pillar 2 C6 says HIGH ("core protection is zero").
- Pillar 1 marks the handoff-reap fix "Not c5 (ADR 0092 excludes the tmp/TTL zones)", yet folds it into M2 labelled c5.
- Pillar 1's cluster open counts sum to 32 against 33 open bugs. The disposition table has 4 TESTS rows, but the cluster table says 3 (±10% rule).
- Pillar 2's text says 20 ADRs measure nothing pending a candidate; its own list holds 21.
- Pillar 2 lists `guidance-messages-name-the-right-target` as "EXIT" (three parts) in prose but `EXIT(superseded)` in data. `superseded` expects a release id that a duplicate of an open bug does not have.
- Pillar 1 re-files `removals-shipped-without-recorded-authority` as a pillar-2 finding, but pillar 2 did not carry it. The synthesis added F069.
