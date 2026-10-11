# SPEC — Release: 0.5.0, candidate 14 — Wave 1: law, skills, personas, dev loop, every confirmed bug

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-11
**Origin:** backlog:dd-ask-me-owned-questioning-skill,architecture-adr-section-generated,public-law-language-neutral,test-suite-diet,programmatic-dates-in-skills,impacted-test-selection,law-one-home-residual,bug-batch-cause-trigger-and-attempt-cap,define-backlog-merge-runs-verify,hotfix-specs-revert-commit-shape,harness-specific-surface-minimized,adr-0122-zero-backlog-destined-to-this-release,job-gate-runs-the-law-deletion-check,merge-entry-times-survive-rebase,hypothesis-cache-stays-out-of-repo-trees,task-gate-drops-deleted-paths-itself,architecture-principles-measured-by-re-pointed,fix-reader-rebuild-under-c,task-gate-declared-owner-tests,pr-merge-method-pinned,phase-implementation-has-a-place,stage-gate-keeps-only-the-red-check,verdict-author-unbound,judge-config-outside-the-script-dir,gate-reuses-a-green-result-for-the-same-tree,process-proportional-to-change-size,bug-status-deferred-banned,quality-scorecard-ruler,task-lines-carry-seam-and-adr-clause; bugs:worktree-new-crashes-on-an-unreadable-release-state,release-check-admits-a-dag-that-phase-refuses,release-new-orphans-a-drafted-next-rc,verify-line-shlex-mangles-windows-paths,context-repo-refusals-carry-no-fix-line,codex-persona-frontmatter-drops-on-crlf,doctor-misses-worktrees-of-a-repo-that-left-its-context,job-gate-red-on-untracked-bytecode,cross-os-ci-masks-utf8,cli-refusals-print-no-fix-line,context-alive-crashes-on-a-non-git-repo-dir

Source: the 0.5.0 scope grill of 2026-10-11 (24 questions, 28 decisions), report https://claude.ai/artifact/GGEzLQDmquUfrUhacFgmmK. The operator confirmed the shared understanding: "Confirmo, pode seguir (Recommended)". Each Origin entry's "Scope grill 2026-10-11" paragraph in `BACKLOG.json` holds its verbatim ruling, scope and wave.

The wave rule (operator, 2026-10-11): rc-14 is Wave 1. Wave 1 is ordered by leverage on all later work. It covers law, skills, personas and the dev loop, plus every confirmed bug (bugs law §2).

---

## Bug window review

rc-13 ran from its birth (`7a1ae384a`, 2026-10-10) to its implementation at `d68a7c42f` (2026-10-11T00:58:51Z) and its closure. Three fixes closed in that window. One REBUILD verdict carried from rc-13's table is still owed.

| verdict | disposition | fixes |
|---|---|---|
| KEEP | `git show 44a9f58c8`: +34/−92, itself the REBUILD its `caused_by` required; no assert edited, no branch, no reach. No record names it in `caused_by`. FR16's parser predates it (`a4f58278b`). | `agent-model-templates-pin-superseded-sonnet-and-haiku` |
| REBUILD — FR13 | `git show d68a7c42f`: +6/−5, the second fix in one day on `_release_phase._refuse_open_worktrees` (after `f1d59e9e6`). The unit computes the next candidate number a second time; `_release_schema.next_candidate`'s copy fails as `release-new-orphans-a-drafted-next-rc`. The REBUILD leaves one decider; `test_the_closure_spares_only_the_next_candidates_define_tree` stays unedited. | `release-closure-refuses-the-next-candidates-define-tree` |
| KEEP | `git show d7503ff81`: a specs revert, no code, `block: (1)`. Its cause, guard v33, is deleted (FR9); its missing commit shape is FR6. | `rc13-define-cites-an-unread-prefix-family` |
| REBUILD — FR11 (carried) | Carried from rc-13: `2a8b5637f` added a second `_RELEASE.json` parser in `_worktree_new.py`; `worktree-new-crashes-on-an-unreadable-release-state` is that parser failing. | `worktree-new-opens-a-job-outside-implementation` |

Job 1 executes both REBUILD rows.

## 1. Problem

The law, the skills and the dev loop are the base every later wave builds on, and they carry six defects:

- The grill's record is a handoff that expires after a day. 28 accepted ADR rulings cite answer ids that can no longer be read.
- Any decision can become an ADR, and none records the options it rejected.
- The `ADR:` label on principles restates ledger status and has drifted.
- The shipped law tells users in any language about this library's Python internals and ADR numbers.
- Skills let the model type dates.
- A specs-only definition can turn a code guard red. The developer has no way to run only the tests a change reaches.

Eleven confirmed bugs are open. Ship refuses an open bug the operator has not authorized.

## 2. Measurable Goals

- G1. A grill decision can be read without a handoff. Every ADR proposed after rc-14 carries `options` and a self-contained `ruling.words`.
- G2. Status has one home: after the Reconciliation, no `ADR:` label in `specs/memory` or the scaffold carries a status token.
- G3. `bugs.py status` lists none of the eleven Origin bugs as open at rc-14's closure.
- G4. The FR4 grep over `dadaia_workspace/public/` returns only the workspace's own operation.
- G5. `git grep -n -- '--ts' dadaia_workspace/public/skills` returns nothing.
- G6. A specs-only change cannot turn the repo guards red through prose. `scripts/ci.py --changed` runs only the tests the diff reaches.

## 3. Requirements

### FR1 — dd-grill-me complete, name kept (`dd-ask-me-owned-questioning-skill`)

Operator: "Tudo, sem rename (Recommended)": the name `dd-grill-me` stays.

- AC1.1 (no test — reviewer source sweep): `dd-grill-me` ships `references/` with one file per stage:
  - backlog: is it a decision at all (problem measured, feature or bug, scope);
  - release: before the SPEC;
  - adr: FR2's threshold and the question bank (reversibility, decision drivers, a quality-attribute scenario whose response measure becomes `measured_by`, the surface's bug history, ownership and coupling, reuse, failure and rollback, cost, security, what it lets us delete, the accepted drawback, open issues);
  - plan: does the PLAN contradict an accepted ADR, or carry a technical decision past the threshold.

  `SKILL.md` keeps the common core: one question at a time, 3 closed options each with its trade-off, one recommended, and free text through the tool's own open answer.
- AC1.2 (no test — reviewer source sweep): There are three triggers, each one line in its skill:
  - `dd-backlog-definition`, before `backlog.py new`;
  - `dd-release-definition` §3, before the SPEC or any ADR;
  - after the PLAN, only for a technical decision past the threshold.
- AC1.3 (no test — reviewer source sweep): Every answer lands in a durable record in the same turn: the entry description at `backlog.py new`, an ADR's `options` and `ruling.words`, or the SPEC. The handoff stays ephemeral. ADR 0165's own check holds: `grep -rn 'whole frontier\|grill-<slug>.md' dadaia_workspace/public` returns nothing.
- AC1.4 (integration): The report uses the harness's artifact first. Without one, it is an HTML report styled by one CSS file under the skill's `scripts/`. `public install` projects `references/` and the CSS file.

### FR2 — the ADR law and three ledger decisions (`law-one-home-residual`)

Operator: "Triagem + gerada (Recommended)", "ADR que supersede (Recommended)", "Ratificar os 4 (Recommended)".

Scope note (main thread, 2026-10-11): the entry's clause "an ADR is born only in `dd-release-definition`; `decisions.jsonl` leaves the backlog kind's allowed set and its gitflow row" is dropped. It was an unruled agent default, and the three-leg threshold already serves the operator's "Se tudo é ADR nada é ADR". FR2 does not depend on that clause: `options` and a self-contained `ruling.words` stay. Part (c), ADR 0193's `amends: null`, goes to the Wave 4 ledger triage (§5).

- AC2.1 (no test — reviewer source sweep): The scaffold ADR law (projected to `specs/ADRs/AGENTS.md`) states the three-leg threshold in one line: a one-way door, architecturally significant, at least two genuine options. A decision that fails a leg lives in its scoped law line or the SPEC (ADR 0245 (1)).
- AC2.2 (unit, RED first): `decision-record-v1` carries `options`: at least two entries of `name`, `tradeoff` and `rejected_because`. Doctor `LEDGER-ADR-SCHEMA` refuses a record proposed after ADR 0245's acceptance if it has no `options`. Every record already in the ledger still validates.
- AC2.3 (no test — law line and schema description): `ruling.words` carries the question and the chosen option in the operator's words, never only an answer id.
- AC2.4 (no test — ledger): The operator rules ADRs 0243 (P-01, P-09, P-14, P-15 ratified), 0244 (no `found_in`; archiving needs no ADR) and 0245 (this FR and FR3) before this SPEC is Approved. ADR 0242 was accepted in this define tree at `366cda255`.
- AC2.5 (no test — reviewer source sweep): `git grep -n found_in -- dadaia_workspace tests` returns nothing.

### FR3 — status only in the ledger (`architecture-adr-section-generated`, Wave 1 part)

- AC3.1 (unit): Memory lint's `ADR:` exemption (`_ADR_LINE_RE`) is deleted. `tests/features/specs/test_memory_lint.py` stays green and gains no row.
- AC3.2 (no test — reviewer source sweep): Several pieces leave:
  - the status token in the scaffold memory law's `ADR:` grammar (a label cites the id only);
  - the ADR law's label clauses (§5, §5.1);
  - `PILLAR-MEMORY.md`'s label-status clause.

  The missing-`Measured by:` finding and the pairing rule stay. Job 3's guard tolerates the old labels; the Reconciliation strips their status tokens and points P-01, P-09, P-14 and P-15 at ADR 0243. The triage and the generated section are Wave 4 work, so this entry stays active after rc-14.

### FR4 — the shipped surface is language-neutral (`public-law-language-neutral`, whole entry)

- AC4.1 (no test — reviewer source sweep; the grep and its count go in the commit body): `dadaia_workspace/public/` names no package path of this library, no ADR number of this repo, and no Python-only project tooling. The workspace's own operation is the exception: `.dadaia/.venv` and `uvx dadaia-workspace`. Each finding is deleted, rewritten language-neutral, or moved to `repos/dadaia-workspace/AGENTS.md`. Nothing moves to private. Two kinds of file stay as they are: those the entry leaves to another owner, and `scripts/pre-push-ci-gate.sh`, which Wave 3 deletes.

### FR5 — harness-specific surface minimized (`harness-specific-surface-minimized`)

Operator: "minimizamos a superficie do que é especifico de cada harness (sub-agents e hooks principalmente)".

No harness is removed: the goal is cheap harness switching, not fewer harnesses.

- AC5.1 (reviewer sweep for the law line; integration for the registry): One law line, in one home, states the strategy: common behaviour lives in skills and `AGENTS.md`; each harness gets only the surface it cannot do without. `entities/registry.json` stops restating `implementations`: the entity doctor derives coverage from the harness records and the hook table, and the registry names only `gaps` (Job 9, Wave 2).

### FR6 — a commit shape for a specs revert hotfix (`hotfix-specs-revert-commit-shape`)

- AC6.1 (no test — reviewer source sweep): `dd-gitflow-default` §3a has one row for a hotfix that reverts `specs/` text. The row names the hotfix tree, the reverted `specs/` paths and the message of a revert that carries its `block:` item.

### FR7 — the bug batch trigger and the attempt cap (`bug-batch-cause-trigger-and-attempt-cap`)

- AC7.1 (no test — reviewer source sweep): One line in `dd-bug-resolution` sets the batch trigger: the rc bug window or 20 registrations, whichever comes first. Open bugs that share a cause are fixed together, which is where ADR 0123 lives.
- AC7.2 (no test — reviewer source sweep): One line sets the cap: two fix attempts on one bug, then a fresh session with a written diagnosis.

### FR8 — dates come from the clock (`programmatic-dates-in-skills`)

- AC8.1 (integration, RED first): `bugs.py` and `backlog.py` reject `--ts` as an unknown option and stamp from the clock.
- AC8.2 (integration, pin — passes on arrival): `verdict.py`'s handoff file-name stamp and `produced_at` are one clock read. The model-written handoff gets its stamp from the clock command AC8.3's law line names.
- AC8.3 (no test — reviewer source sweep): Every other date a skill writes names its source: `date -u`, git or gh.

### FR9 — the test suite diet and the v33 root (`test-suite-diet`, carrying `define-backlog-merge-runs-verify`)

- AC9.1 (no test — reviewer source sweep): The entry's closed DELETE list leaves where it still exists (PLAN §1 measures it: the honesty-residue test and four source-text or vacuous test blocks; the meta-test duplicates and mutation wiring are already gone). Each deletion commit names the check that still catches what it caught.
- AC9.2 (integration): `scripts/ci.py` keeps only the job level. The dead task and stage code leaves, and `python scripts/ci.py job` keeps its steps.
- AC9.3 (no RED — guard run): v33 is deleted, as the operator allowed if it never caught real slop: PLAN §1 measured 31 orphan families, all noise (`ADR`, `SHA`, `UTF`). `scripts/guards/run.py` and `--planted` exit 0 without v33, its plants and its guard test. No new gate.

### FR10 — impacted tests as a developer read (`impacted-test-selection`)

Operator: "Mapa de impacto como leitura (Recommended)".

- AC10.1 (integration, RED first): `python scripts/ci.py --changed` lists and runs the test files that import, transitively, a module the diff changes. It names each changed file the import graph cannot map.
- AC10.2 (no test — reviewer source sweep): No gate calls it, whether job verify, merge, pre-push or CI. CI keeps the full suite.

### FR11 — `worktree-new-crashes-on-an-unreadable-release-state` (MEDIUM; REBUILD of `_worktree_new.py`'s phase admission)

- AC11.1 (integration, RED first): A missing, malformed or non-object `_RELEASE.json` refuses job admission with exit 1, `Error:` and exactly one `fix:` line. No branch or worktree is created. Valid phases and the define, reconcile and hotfix trees are unchanged.
- AC11.2 (no test — reviewer): The phase is read through the release ledger's existing reader. The raw read in `_worktree_new.py` leaves, and no new parser is added.

### FR12 — `release-check-admits-a-dag-that-phase-refuses` (MEDIUM)

- AC12.1 (integration, RED first): A PLAN whose DAG jobs differ from its `tasks/job<n>.md` files fails `release.py check` with the same message `release.py phase IMPLEMENTATION` prints. Both verbs call one comparison.

### FR13 — `release-new-orphans-a-drafted-next-rc` (MEDIUM; REBUILD of the next-candidate computation)

- AC13.1 (unit, RED first): With rc-1 live and a drafted `rc-2/SPEC.md`, `release.py new` adopts rc-2 and keeps the draft. It never creates rc-3.
- AC13.2 (unit): The closure fence and `release.py new` take the next candidate number from one decider. The closure test named in the Bug window review stays green unedited.

### FR14 — `verify-line-shlex-mangles-windows-paths` (MEDIUM)

- AC14.1 (unit, RED first): On Windows, the declared line `python scripts\ci.py job` runs as `['python', 'scripts\\ci.py', 'job']`. POSIX splitting is unchanged. One splitter serves `verify:` and `tests:` (ADR 0220 P3).

### FR15 — `cli-refusals-print-no-fix-line`, `context-repo-refusals-carry-no-fix-line`, `context-alive-crashes-on-a-non-git-repo-dir` (MEDIUM; REBUILD of the refusal path)

Operator: "Registrar e corrigir no Job 5 (Recommended)", "Registrar, Job 5 (Recommended)". The structural cause: `cli/_fail.fail` prints only `Error:`, and the remedy lives in each raiser's prose or a per-site f-string.

- AC15.1 (unit, then integration; RED first): The raised error carries its fix, as `SchemaVersionError` does (`core/exceptions.py:87-93`); `fail` prints a caller fix only when the error has none. Each measured site then prints `Error:` and exactly one `fix:` line (ADR 0073), one case per repro:
  - context registry: `repo add` (invalid slug, different URL, foreign slug), `repo remove` of an unregistered slug, and `create`'s conflict, whose `fix: dadaia context list` (`context.py:168`) clears nothing;
  - git failures of `context alive`, `baseline`, `dead`: the verb's retry line;
  - `import` of a missing, non-JSON or non-export file; `reports validate` bare or on a missing file;
  - `init`'s venv failure; `specs` upgrade's two-tier refusal and its unlabeled `Operator action:`; the unresolved `specs_dir`.
- AC15.2 (integration, RED first): Adding the context's own main repo exits 0 as a no-op. The operator ruled that this refusal becomes idempotent.
- AC15.3 (integration, RED first): `context alive` on a `repos/<slug>` that is not a git repository refuses with `Error:` and one `fix:` line, never a traceback. The hook installer's off-repo condition is one domain refusal carrying its fix, consumed unchanged by every caller (`create`, `alive`, `ci install-hook`, hook refresh).

### FR16 — `codex-persona-frontmatter-drops-on-crlf` (MEDIUM)

- AC16.1 (unit, RED first): For the same persona, on LF and CRLF, the Codex projection reads the same fields that `core/frontmatter.py` parses, with quoted values unquoted. The projection's private frontmatter parser leaves.

### FR17 — `doctor-misses-worktrees-of-a-repo-that-left-its-context` (LOW)

- AC17.1 (integration, RED first): A linked worktree under `worktrees/<repo>/` whose repo has left its context is a doctor finding with one fix line (ADR 0112).

### FR18 — `job-gate-red-on-untracked-bytecode` (LOW)

- AC18.1 (unit, RED first): The bytecode assertion judges tracked files (`git ls-files`): an ignored `__pycache__/*.pyc` under `public/` keeps it green, and a tracked one fails it. The shipped contract stays the build exclude.

### FR19 — `cross-os-ci-masks-utf8` (LOW)

- AC19.1 (CI; no unit test, because the contract is the workflow itself): The RED evidence is `grep -n 'PYTHONUTF8\|PYTHONIOENCODING' .github/workflows/ci.yml`, which today finds six hits. GREEN is zero hits with every leg green. An encoding defect that the unmasked legs expose is proposed as a bug and never masked again (ADR 0220 P5).

## 4. Exits at closure

These Origin entries need no rc-14 work. Each exits once, at closure, with the reason recorded in its paragraph.

| slug | disposition | reason |
|---|---|---|
| `adr-0122-zero-backlog-destined-to-this-release` | delivered | ADR 0242, accepted at `366cda255` in this define tree; its promote-time readouts ride `promote-gate-050` |
| `define-backlog-merge-runs-verify` | superseded | "Consertar a raiz (Recommended)": the v33 root fix in FR9, no new gate |
| `job-gate-runs-the-law-deletion-check` | superseded | obsolete by ADR 0230 |
| `merge-entry-times-survive-rebase` | superseded | obsolete by `e8c2683ca` |
| `hypothesis-cache-stays-out-of-repo-trees` | superseded | obsolete by ADR 0231 (redirect `tests/conftest.py:153-169`, tripwire `:513-549`) |
| `task-gate-drops-deleted-paths-itself` | superseded | obsolete by ADRs 0231/0232/0236; dead code deleted in FR9 |
| `architecture-principles-measured-by-re-pointed` | superseded | delivered earlier (`75150722f`, `6c9ea5f6d`); residue in ADR 0243 |
| `fix-reader-rebuild-under-c` | superseded | obsolete by `392769e97` |
| `task-gate-declared-owner-tests` | superseded | obsolete by ADRs 0231/0232/0236 |
| `pr-merge-method-pinned` | superseded | delivered earlier: `allow_rebase_merge` false, main linear |
| `phase-implementation-has-a-place` | superseded | delivered earlier (`2a8b5637f`, `dd-release-definition` SKILL.md:61) |
| `stage-gate-keeps-only-the-red-check` | superseded | obsolete by ADRs 0231/0232/0236 |
| `verdict-author-unbound` | superseded | "Disciplina + auditoria (Recommended)"; ADR 0218, no new hook |
| `judge-config-outside-the-script-dir` | superseded | 2026-10-08 question 16 "Apagar; o revisor cobre (Recommended)" |
| `gate-reuses-a-green-result-for-the-same-tree` | superseded | 2026-10-08 "somente job e tasks são suficientes"; verify once per job (ADR 0231) |
| `process-proportional-to-change-size` | superseded | delivered by 2026-10-08 "devemos ser por default leves" and question 18 "Worktree livre" |
| `bug-status-deferred-banned` | superseded | delivered (ADRs 0223/0227, `392769e97`) |
| `quality-scorecard-ruler` | superseded | the 2026-10-09 score-9 ruling, ADR 0239 |
| `task-lines-carry-seam-and-adr-clause` | superseded | job file slimmed by 2026-10-08 questions 12 and 15; ADRs 0231/0232 |

The entries with work exit `delivered` at closure, except `architecture-adr-section-generated` (FR3), which stays active for Wave 4. `law-one-home-residual` exits `delivered` with this reason: (a) delivered by FR2, with its location clause dropped as an unruled agent default; (b) and (c) carried by `architecture-adr-section-generated`'s Wave 4 triage.

## 5. Not in rc-14

- **Wave 2:** `skill-scripts-one-kernel`, complete. Its two named bugs are fixed here (FR11, FR12). The kernel still owes one `_RELEASE.json` reader, which today means two readers after FR11, and constitution §5 read literally.
- **Wave 3:** `spec-context-branch-field-deleted`, `worktree-layout-per-context`, `context-dead-snapshots-open-worktrees`, `context-show-derives-worktrees` (FR17 fixes only the orphan finding; the one computation stays there), `export-soft-and-hard`, `init-from-export`, `multi-platform-by-construction-migration` (FR14 and FR19 are its bugs; the Python pre-push, P10 rules, the guard line and the P8 amendment stay there), `bug-stats-hotspots-and-age`, `audit-project-scorecard-cycle`, `repo-ci-sast-gates`.
- **Wave 4:** `architecture-adr-section-generated` (triage and generated section; the triage also repairs ADR 0193, which carries `amends: null` though it amends 0152 (2), through a new record the operator accepts), `docs-site-zensical-pages`, `launch-operator-acts`, `eval-codex-lane-in-library-ci` (with the cron deletion), and `promote-gate-050` (the 050 checks, D1–D10, findings dispositions, rc-13 residuals of log entry 188).
- **Not destined to 0.5.0** (ADR 0242): `evals-benchmark-lanes`, `release-approve-requires-evals-gate`, `windows-smoke-t1-at-release`.
- **Out of the picked entries:** the rename to `dd-ask-me` (FR1); the `behavior-map.json` deletion, which is unruled (FR9); the gate-side test selection (FR10).

## 6. Constraints and risks

### Replaces

- The grill handoff as the only record of operator decisions becomes a durable record in the same turn (FR1).
- One generic grill procedure for every stage becomes per-stage references (FR1).
- Any decision as an ADR becomes the three-leg threshold, and an id-only ruling becomes self-contained words (FR2).
- The status token of the `ADR:` label, with its grammar, lint exemption, law clauses and pillar clause, leaves (FR3).
- Library internals, Python-project assumptions and ADR numbers in shipped law are removed (FR4).
- `--ts` on `bugs.py` and `backlog.py`, and handoff dates typed by the model, are removed (FR8).
- The diet's test blocks, `ci.py`'s task and stage code, and guard v33 are removed (FR9).
- `entities/registry.json`'s hand-written `implementations` become derived coverage (FR5).
- The raw `_RELEASE.json` read in `_worktree_new.py` goes (FR11); two DAG deciders and two next-candidate computations become one each (FR12, FR13).
- POSIX `shlex` splitting on Windows is replaced (FR14).
- Per-site remedies and the 12 `Error:`-only refusal sites become an error that carries its fix; the own-main refusal becomes a no-op (FR15).
- The Codex private frontmatter parser (FR16), the working-tree bytecode assertion (FR18) and the CI UTF-8 masks (FR19) go.

### Governance sequencing

1. ADRs 0243, 0244 and 0245 are proposed in this define tree. Under rule M2, each names its targets in `context`, and the main thread sets `supersedes` and `amends` at acceptance: 0244 supersedes 0205 and amends 0187; 0245 amends 0165.
2. The operator's rulings land before the SPEC is approved. The label strip belongs to the Reconciliation, not to an acceptance (FR3).

### Delivery constraints

- Job 1 runs first and executes the two REBUILD verdicts (FR11, FR13).
- Every bug fix lands its RED test first (bugs law §2); DELETE and REBUILD precede ADD.
- Job 2 (FR1) is Wave 2: it waits on Job 3's schema `options` (FR2).
- Shipped law changes only in `dadaia_workspace/public/`; this instance gets it by projection.

### Risks

| risk | control |
|---|---|
| the FR4 sweep grows without bound | the closed list in the FR4 entry; FR5 removes no harness |
| Unmasked CI legs expose many encoding defects | each one is proposed as a bug and fixed at its cause, never re-masked (AC19.1) |

## 7. Open questions

None.
