# SPEC — Release: 0.5.0, candidate 14 — one owner per fact; Wave 1 law, skills and dev loop

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-11
**Origin:** backlog:dd-ask-me-owned-questioning-skill,architecture-adr-section-generated,public-law-language-neutral,test-suite-diet,programmatic-dates-in-skills,impacted-test-selection,law-one-home-residual,bug-batch-cause-trigger-and-attempt-cap,define-backlog-merge-runs-verify,hotfix-specs-revert-commit-shape,harness-specific-surface-minimized,adr-0122-zero-backlog-destined-to-this-release,job-gate-runs-the-law-deletion-check,merge-entry-times-survive-rebase,hypothesis-cache-stays-out-of-repo-trees,task-gate-drops-deleted-paths-itself,architecture-principles-measured-by-re-pointed,fix-reader-rebuild-under-c,task-gate-declared-owner-tests,pr-merge-method-pinned,phase-implementation-has-a-place,stage-gate-keeps-only-the-red-check,verdict-author-unbound,judge-config-outside-the-script-dir,gate-reuses-a-green-result-for-the-same-tree,process-proportional-to-change-size,bug-status-deferred-banned,quality-scorecard-ruler,task-lines-carry-seam-and-adr-clause,skill-scripts-one-kernel; bugs:worktree-new-crashes-on-an-unreadable-release-state,release-check-admits-a-dag-that-phase-refuses,release-new-orphans-a-drafted-next-rc,verify-line-shlex-mangles-windows-paths,context-repo-refusals-carry-no-fix-line,codex-persona-frontmatter-drops-on-crlf,doctor-misses-worktrees-of-a-repo-that-left-its-context,job-gate-red-on-untracked-bytecode,cross-os-ci-masks-utf8,cli-refusals-print-no-fix-line,context-alive-crashes-on-a-non-git-repo-dir,skill-git-runners-read-the-callers-git-env,ledger-replace-destroys-a-symlinked-ledger,frontmatter-parsers-disagree-on-crlf-and-bom,slug-grammar-four-patterns-disagree

Sources: the 0.5.0 scope grill of 2026-10-11 (report https://claude.ai/artifact/GGEzLQDmquUfrUhacFgmmK; "Confirmo, pode seguir (Recommended)"); each Origin entry's "Scope grill 2026-10-11" paragraph in `BACKLOG.json`; the duplicated-decider inventory at `dd10eb7de` (27 groups, about 110 copy sites, 12 diverged). Operator, 2026-10-11: "Eu so quero que vocÊ converja para 0 bugs ... qual é o problema core de tantos bugs ficarem aparecendo o tempo todo?"; "Isso é obvio né. Agora vc me fala desse problema arquitetural??? é esse o bug porra"; on the owner: "A: script da skill dona (Recommended)" (ADR 0246).

Placement (main-thread inference, review MEDIUM): `skill-scripts-one-kernel` was destined to Wave 2. Its move into rc-14 is the main thread's reading of "totalmente agora ... é para ser feito exatamente nessa release" and "é esse o bug porra". The operator's Option A ruling confirmed it afterwards.

---

## Bug window review

rc-13 ran from `7a1ae384a` (2026-10-10) to its implementation at `d68a7c42f`. Three fixes closed in that window; one rc-13 verdict is carried.

| verdict | disposition | fixes |
|---|---|---|
| KEEP | `git show 44a9f58c8`: +34/−92, itself the REBUILD its `caused_by` required; no assert edited, no branch, no reach; no record names it in `caused_by`. | `agent-model-templates-pin-superseded-sonnet-and-haiku` |
| REBUILD — FR14 | `git show d68a7c42f`: the second fix in one day on `_release_phase._refuse_open_worktrees` (after `f1d59e9e6`). The unit computes the next candidate a second time; `_release_schema.next_candidate`'s copy fails as `release-new-orphans-a-drafted-next-rc`. | `release-closure-refuses-the-next-candidates-define-tree` |
| KEEP | `git show d7503ff81`: a specs revert, no code. Its cause, guard v33, is deleted (FR9); its commit shape is FR6. | `rc13-define-cites-an-unread-prefix-family` |
| REBUILD — FR14 (carried) | `2a8b5637f` added a second `_RELEASE.json` parser in `_worktree_new.py`; `worktree-new-crashes-on-an-unreadable-release-state` is that parser failing. | `worktree-new-opens-a-job-outside-implementation` |

Bugs law §2: Job 1 executes both REBUILD rows.

## 1. Problem

The root cause of the bug stream: one fact is decided in several places. The inventory counts 27 facts with two or more deciders and 12 that already diverged. Four divergences replay as bugs (FR11 to FR13). The projection makes the copies itself: `public_assets.py` `_SKILL_SCRIPT_SHARED` and `_SKILL_SCRIPT_SCHEMAS` copy `_ledger`, `_specs`, `_privacy`, the baseline and the schemas into each skill (3,869 lines in 31 files), and `slop.py` v37/v38 rows sanction twins.

The structural-audit bugs of 2026-09-27/28 (`sa-package-defines-a-fact-twice`, `sa-seven-workspace-root-rules`, `sa-live-release-resolved-by-two-readers`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts`, `sa-frontmatter-split-five-ways`) closed while the copies stayed. Their premise, "the stdlib-only skill scripts and the package cannot share code", is false: ADR 0157 already has `privacy_check.py` import the skill's `_ledger.py`, and ADR 0135 makes the skill script the owner and the package its importer.

The Wave 1 law has its own defects: a grill record that expires, ADRs without a threshold or rejected options, an `ADR:` status label that drifted, shipped law naming this library's Python internals and ADR numbers, dates the model types, a guard that reads `specs/` prose, and no way to run only the tests a change reaches.

Fifteen confirmed bugs are open.

## 2. Measurable Goals

- G1. Zero copies: for each inventory group the PLAN names one `git grep`, and each returns only the owner's definition.
- G2. `bugs.py status` lists none of the fifteen Origin bugs as open at closure.
- G3. `git grep -n 'noqa: E402' -- dadaia_workspace` returns nothing; each skill entry point keeps one bootstrap `sys.path` line.
- G4. radon reports no D–F function under `dadaia_workspace/public/skills/*/scripts` (constitution §5).
- G5. Every ADR proposed after rc-14 carries `options` and a self-contained `ruling.words`; no `ADR:` label carries a status token after the Reconciliation.
- G6. The FR4 grep over `public/` returns only the workspace's own operation; `git grep -n -- '--ts' dadaia_workspace/public/skills` returns nothing.

## 3. Requirements

### Wave 1 law, skills and dev loop

#### FR1 — dd-grill-me complete, name kept (`dd-ask-me-owned-questioning-skill`; "Tudo, sem rename (Recommended)")

- AC1.1 (no test — reviewer sweep): `references/` holds one file per stage: backlog (a decision at all: problem measured, feature or bug, scope); release (before the SPEC); adr (FR2's threshold and the question bank: reversibility, drivers, a quality-attribute scenario whose response measure becomes `measured_by`, the surface's bug history, coupling, reuse, rollback, cost, security, what it deletes, the accepted drawback); plan (contradicts an accepted ADR, or carries a decision past the threshold). `SKILL.md` keeps one question at a time, 3 closed options with trade-offs, one recommended, free text through the tool.
- AC1.2 (no test — reviewer sweep): Three triggers, one line each: before `backlog.py new`; `dd-release-definition` §3 before the SPEC or an ADR; after the PLAN, only past the threshold.
- AC1.3 (no test — reviewer sweep): Every answer lands in a durable record in the same turn (backlog description, ADR `options` and `ruling.words`, or the SPEC); the handoff stays ephemeral; `grep -rn 'whole frontier\|grill-<slug>.md' dadaia_workspace/public` returns nothing (ADR 0165).
- AC1.4 (integration): The report is the harness artifact first, else HTML styled by one CSS file under `scripts/`; `public install` projects `references/` and the CSS.

#### FR2 — the ADR law and the ledger decisions (`law-one-home-residual`)

Operator: "Triagem + gerada (Recommended)", "ADR que supersede (Recommended)", "Ratificar os 4 (Recommended)". The clause "an ADR is born only in `dd-release-definition`" is dropped (main thread: an unruled agent default; the threshold serves "Se tudo é ADR nada é ADR"). Part (c), ADR 0193's `amends: null`, goes to the Wave 4 triage.

- AC2.1 (no test — reviewer sweep): The scaffold ADR law states the three-leg threshold in one line: one-way door, architecturally significant, at least two genuine options.
- AC2.2 (unit, RED first): `decision-record-v1` carries `options` (at least two of `name`, `tradeoff`, `rejected_because`), required for ids after 0245; every existing record still validates.
- AC2.3 (no test — law line): `ruling.words` carries the question and the chosen option, never only an answer id.
- AC2.4 (no test — ledger): The operator rules ADRs 0243, 0244, 0245 and 0246 before approval. ADR 0242 was accepted at `366cda255`.
- AC2.5 (no test — reviewer sweep): `git grep -n found_in -- dadaia_workspace tests` returns nothing.

#### FR3 — status only in the ledger (`architecture-adr-section-generated`, Wave 1 part)

- AC3.1 (unit): The memory-lint `ADR:` exemption is deleted; `test_memory_lint.py` stays green unedited.
- AC3.2 (no test — reviewer sweep): The status token leaves the `ADR:` grammar (the label cites the id only), the ADR law's label clauses and `PILLAR-MEMORY.md`. Job 3's guard tolerates old labels; the Reconciliation strips the 15 status tokens and points P-01, P-09, P-14 and P-15 at ADR 0243. The entry stays active for Wave 4.

#### FR4 — the shipped surface is language-neutral (`public-law-language-neutral`)

- AC4.1 (no test — reviewer sweep; grep and count in the commit body): `public/` names no package path of this library, no ADR number of this repo and no Python-only tooling, except `.dadaia/.venv` and `uvx dadaia-workspace`. Each finding is deleted, rewritten, or moved to `repos/dadaia-workspace/AGENTS.md`; `scripts/pre-push-ci-gate.sh` waits for Wave 3.

#### FR5 — harness-specific surface minimized (`harness-specific-surface-minimized`)

No harness is removed: the goal is cheap switching.

- AC5.1 (reviewer sweep; integration for the registry): One law line states that common behaviour lives in skills and `AGENTS.md` and each harness gets only what it cannot do without. `entities/registry.json` stops restating `implementations`; the entity doctor derives coverage from the harness records and the hook table, and the registry names only `gaps`.

#### FR6 — a specs-revert hotfix shape (`hotfix-specs-revert-commit-shape`)

- AC6.1 (no test — reviewer sweep): `dd-gitflow-default` §3a has one row for a hotfix reverting `specs/` text: the tree, the paths, the revert message with its `block:` item.

#### FR7 — bug batch trigger and attempt cap (`bug-batch-cause-trigger-and-attempt-cap`)

- AC7.1 (no test — reviewer sweep): One line in `dd-bug-resolution`: batch on the rc window or 20 registrations, whichever first; bugs sharing a cause are fixed together (ADR 0123's home).
- AC7.2 (no test — reviewer sweep): One line: two fix attempts per bug, then a fresh session with a written diagnosis.

#### FR8 — dates come from the clock (`programmatic-dates-in-skills`)

- AC8.1 (integration, RED first): `bugs.py` and `backlog.py` reject `--ts` and stamp from the clock.
- AC8.2 (integration, pin — passes on arrival): `verdict.py`'s file-name stamp and `produced_at` are one clock read.
- AC8.3 (no test — reviewer sweep): Every other skill-written date names its source; the model-written handoff takes its stamp from a clock command.

#### FR9 — dev loop: the diet, v33, CI (`test-suite-diet`, `define-backlog-merge-runs-verify`; bugs `job-gate-red-on-untracked-bytecode`, `cross-os-ci-masks-utf8`)

- AC9.1 (no test — reviewer sweep): The closed DELETE list leaves where it still exists (PLAN §1); each commit names the check that still catches what it caught.
- AC9.2 (integration): `scripts/ci.py` keeps only the job level.
- AC9.3 (no RED — guard run): v33 is deleted (31 orphan families, all noise); `scripts/guards/run.py` and `--planted` exit 0.
- AC9.4 (unit, RED first): The bytecode assertion judges tracked files (`git ls-files`): an ignored `.pyc` under `public/` stays green, a tracked one fails.
- AC9.5 (CI): `PYTHONUTF8` and `PYTHONIOENCODING` leave `ci.yml` (six hits to zero) with every leg green; an exposed encoding defect is proposed as a bug, never re-masked (ADR 0220 P5).

#### FR10 — impacted tests as a developer read (`impacted-test-selection`; "Mapa de impacto como leitura (Recommended)")

- AC10.1 (integration, RED first): `python scripts/ci.py --changed` lists and runs the tests that import, transitively, a changed module, and names each changed file it cannot map.
- AC10.2 (no test — reviewer sweep): No gate calls it; CI keeps the full suite.

### One owner per fact (`skill-scripts-one-kernel`, ADR 0246)

Every FR below deletes the copies of its group; the owner's existing tests stay green unedited.

#### FR11 — the kernel owner, `dd-bug-resolution/scripts` (bugs `skill-git-runners-read-the-callers-git-env`, `ledger-replace-destroys-a-symlinked-ledger`)

- AC11.1 (integration, RED first): `public install` projects no shared copy: each fact module and schema exists once under `skills/`; `_SKILL_SCRIPT_SHARED`, `_SKILL_SCRIPT_SCHEMAS`, their test staging and the v37/v38 rows are deleted; `load_owner` lives in core.
- AC11.2 (unit, RED first): Two repos A and B with `GIT_DIR=B/.git` set: every skill runner and `infrastructure/git_subprocess` answer for A, through the one `git()`.
- AC11.3 (unit, RED first): A symlinked ledger: `_ledger.replace` refuses as `core.atomic_write` does, through one writer; the bare `os.replace` sites in `features/workspace/service.py` and `features/spec_context/sweep.py` leave.
- AC11.4 (no test — reviewer `git grep` per group): One definition each for the commit loop, `_validated`, `finding()`, `histo_findings`, the JSONL reader, `serialize`, `_values`, the workspace-root walk (venv owner first), the clock, each ledger's status vocabulary (read from its schema) and the skill-side platform constant.

#### FR12 — one frontmatter grammar (bugs `frontmatter-parsers-disagree-on-crlf-and-bom`, `codex-persona-frontmatter-drops-on-crlf`)

- AC12.1 (no test — measurement first): The one stdlib parser is measured against every frontmatter the package parses (the constitution's `gitflow: {...}` flow mapping included); a miss returns to the main thread before code.
- AC12.2 (unit, RED first): A constitution with a leading BOM keeps its `gitflow` block; the same file through core, Codex projection and memory schema yields the same fields on LF and CRLF, quotes removed. The Codex and `_memory_schema` regexes leave.

#### FR13 — one slug grammar, owned by the backlog schema (bug `slug-grammar-four-patterns-disagree`)

- AC13.1 (unit, RED first): `a--b` is accepted or refused alike by backlog, the schema, `verdict.py` and the worktree name parser, all reading the one owner.

#### FR14 — the release ledger owner, `_release_schema` (bugs `worktree-new-crashes-on-an-unreadable-release-state`, `release-check-admits-a-dag-that-phase-refuses`, `release-new-orphans-a-drafted-next-rc`)

- AC14.1 (integration, RED first): A missing, malformed or non-object `_RELEASE.json` refuses job admission with `Error:` and one `fix:` line; no branch or worktree; one parser, the raw read in `_worktree_new.py` deleted.
- AC14.2 (integration, RED first): A DAG that differs from its `tasks/job<n>.md` fails `release.py check` with `phase`'s message; one comparison.
- AC14.3 (unit, RED first): With rc-1 live and a drafted `rc-2/SPEC.md`, `release.py new` adopts rc-2; the closure fence reads the same decider; `test_the_closure_spares_only_the_next_candidates_define_tree` stays unedited.
- AC14.4 (no test — reviewer `git grep`): One definition each for the task-id, sha, semver/candidate and phase grammars; the package reads them through the owner.

#### FR15 — the gitflow owner (bugs `verify-line-shlex-mangles-windows-paths`, `doctor-misses-worktrees-of-a-repo-that-left-its-context`)

- AC15.1 (unit, RED first): On Windows `python scripts\ci.py job` runs as `['python', 'scripts\\ci.py', 'job']`; one splitter serves `verify:` and `tests:` (ADR 0220 P3).
- AC15.2 (integration, RED first): A worktree of a repo that left its context is a doctor finding with one fix line (ADR 0112); one row filter serves doctor and `ctx_inject`.
- AC15.3 (no test — reviewer `git grep`): One definition each for the worktree path, list, dirty check, verdict reader and venv CLI path.

#### FR16 — core owners (package side)

- AC16.1 (unit, RED first): A naive timestamp reads the same in `session_store` and `ctx_inject` (one rule).
- AC16.2 (no test — reviewer `git grep`): `os.name` and `sys.platform` appear only in `core/platform.py`; the context-name pattern has one definition.

#### FR17 — a refusal carries its fix (bugs `cli-refusals-print-no-fix-line`, `context-repo-refusals-carry-no-fix-line`, `context-alive-crashes-on-a-non-git-repo-dir`)

Operator: "Registrar e corrigir no Job 5 (Recommended)", "Registrar, Job 5 (Recommended)".

- AC17.1 (unit, then integration; RED first): The raised error carries its fix, as `SchemaVersionError` does (`core/exceptions.py:87-93`); `fail` prints a caller fix only when the error has none. Each measured site prints `Error:` and one `fix:` line (ADR 0073): context registry (`repo add` ×3, `repo remove`, `create`'s conflict whose `context.py:168` fix clears nothing); git failures of `alive`, `baseline`, `dead`; `import` ×3; `reports validate` ×2; `init`'s venv failure; `specs` upgrade ×2; the unresolved `specs_dir`.
- AC17.2 (integration, RED first): Adding the context's own main repo exits 0 as a no-op.
- AC17.3 (integration, RED first): `context alive` on a non-git `repos/<slug>` refuses with one `fix:` line; the installer's off-repo condition is one domain refusal every caller consumes.

## 4. Exits at closure

These entries need no rc-14 work; each exits once at closure with the reason from its paragraph.

| slug | disposition | reason |
|---|---|---|
| `adr-0122-zero-backlog-destined-to-this-release` | delivered | ADR 0242 accepted at `366cda255`; promote readouts ride `promote-gate-050` |
| `define-backlog-merge-runs-verify` | superseded | "Consertar a raiz (Recommended)": v33 deleted (FR9) |
| `job-gate-runs-the-law-deletion-check` | superseded | obsolete by ADR 0230 |
| `merge-entry-times-survive-rebase` | superseded | obsolete by `e8c2683ca` |
| `hypothesis-cache-stays-out-of-repo-trees` | superseded | obsolete by ADR 0231 |
| `task-gate-drops-deleted-paths-itself` | superseded | ADRs 0231/0232/0236; dead code deleted (FR9) |
| `architecture-principles-measured-by-re-pointed` | superseded | delivered (`75150722f`, `6c9ea5f6d`); residue in ADR 0243 |
| `fix-reader-rebuild-under-c` | superseded | obsolete by `392769e97` |
| `task-gate-declared-owner-tests` | superseded | ADRs 0231/0232/0236 |
| `pr-merge-method-pinned` | superseded | delivered: `allow_rebase_merge` false |
| `phase-implementation-has-a-place` | superseded | delivered (`2a8b5637f`) |
| `stage-gate-keeps-only-the-red-check` | superseded | ADRs 0231/0232/0236 |
| `verdict-author-unbound` | superseded | "Disciplina + auditoria (Recommended)"; ADR 0218 |
| `judge-config-outside-the-script-dir` | superseded | 2026-10-08 "Apagar; o revisor cobre (Recommended)" |
| `gate-reuses-a-green-result-for-the-same-tree` | superseded | 2026-10-08 "somente job e tasks são suficientes" |
| `process-proportional-to-change-size` | superseded | 2026-10-08 "devemos ser por default leves", "Worktree livre" |
| `bug-status-deferred-banned` | superseded | delivered (ADRs 0223/0227) |
| `quality-scorecard-ruler` | superseded | the score-9 ruling, ADR 0239 |
| `task-lines-carry-seam-and-adr-clause` | superseded | job file slimmed (2026-10-08 questions 12, 15) |

The entries with work exit `delivered`, except `architecture-adr-section-generated` (active for Wave 4). `law-one-home-residual`: (a) by FR2, its location clause dropped; (b) and (c) carried by the Wave 4 triage.

## 5. Not in rc-14

- **Wave 3:** the D–F functions of `cli/` and `features/`; `spec-context-branch-field-deleted`, `worktree-layout-per-context`, `context-dead-snapshots-open-worktrees`, `context-show-derives-worktrees`, `export-soft-and-hard`, `init-from-export`, `multi-platform-by-construction-migration` (its two bugs are FR15 and FR9 here), `bug-stats-hotspots-and-age`, `audit-project-scorecard-cycle`, `repo-ci-sast-gates`.
- **Wave 4:** `architecture-adr-section-generated` (triage, generated section, ADR 0193's `amends`), `docs-site-zensical-pages`, `launch-operator-acts`, `eval-codex-lane-in-library-ci`, `promote-gate-050` (050 checks, D1–D10, findings, rc-13 residuals).
- **Not destined** (ADR 0242): `evals-benchmark-lanes`, `release-approve-requires-evals-gate`, `windows-smoke-t1-at-release`.
- **Left out:** the `dd-ask-me` rename; the `behavior-map.json` deletion (unruled); gate-side test selection.

## 6. Constraints and risks

### Replaces

- Projected copies of shared modules and schemas, their copy tables and allowance rows, become one owner per fact, loaded by core (FR11, ADR 0246).
- Second deciders (git runners, atomic writers, frontmatter and slug parsers, release readers, DAG and next-candidate computations, declared-line splitters, row filters, task-id, sha and timestamp rules) leave (FR11 to FR16).
- Per-site remedies become an error that carries its fix; the own-main refusal becomes a no-op (FR17).
- The grill handoff as record, any decision as an ADR, id-only rulings, the `ADR:` status token, shipped library facts, `--ts`, v33, `ci.py` task and stage code, the working-tree bytecode check, the CI UTF-8 masks and hand-written registry `implementations` leave (FR1 to FR9).

### Governance sequencing

1. ADRs 0243 to 0246 are proposed here; under rule M2 the main thread sets the fields at acceptance (0244 supersedes 0205 and amends 0187; 0245 amends 0165; 0246 amends 0135).
2. The rulings land before approval; the label strip belongs to the Reconciliation.

### Delivery constraints

- Bugs law §2: Job 1 executes the REBUILD rows; the PLAN reconciles that with the owner DAG.
- Tidy First: an owner moves before its behaviour changes; every bug fix lands its RED test first.
- One canon bump across the law and kernel jobs; shipped law reaches this instance only by projection.

### Risks

| risk | control |
|---|---|
| The one frontmatter parser misses a package shape | AC12.1 measures first and returns to the main thread |
| Five skills depend on `dd-bug-resolution` | ADR 0246 accepts it; projection always ships it |
| Unmasked CI legs expose encoding defects | each proposed as a bug, never re-masked |

## 7. Open questions

None.
