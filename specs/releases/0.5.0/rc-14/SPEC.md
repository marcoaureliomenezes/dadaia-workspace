# SPEC — Release: 0.5.0, candidate 14 — Wave 1: law, skills, personas, dev loop, every confirmed bug

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-11
**Origin:** backlog:dd-ask-me-owned-questioning-skill,architecture-adr-section-generated,public-law-language-neutral,test-suite-diet,programmatic-dates-in-skills,impacted-test-selection,law-one-home-residual,bug-batch-cause-trigger-and-attempt-cap,define-backlog-merge-runs-verify,hotfix-specs-revert-commit-shape,harness-specific-surface-minimized,adr-0122-zero-backlog-destined-to-this-release,job-gate-runs-the-law-deletion-check,merge-entry-times-survive-rebase,hypothesis-cache-stays-out-of-repo-trees,task-gate-drops-deleted-paths-itself,architecture-principles-measured-by-re-pointed,fix-reader-rebuild-under-c,task-gate-declared-owner-tests,pr-merge-method-pinned,phase-implementation-has-a-place,stage-gate-keeps-only-the-red-check,verdict-author-unbound,judge-config-outside-the-script-dir,gate-reuses-a-green-result-for-the-same-tree,process-proportional-to-change-size,bug-status-deferred-banned,quality-scorecard-ruler,task-lines-carry-seam-and-adr-clause; bugs:worktree-new-crashes-on-an-unreadable-release-state,release-check-admits-a-dag-that-phase-refuses,release-new-orphans-a-drafted-next-rc,verify-line-shlex-mangles-windows-paths,context-repo-refusals-carry-no-fix-line,codex-persona-frontmatter-drops-on-crlf,doctor-misses-worktrees-of-a-repo-that-left-its-context,job-gate-red-on-untracked-bytecode,cross-os-ci-masks-utf8

The source is the 0.5.0 scope grill of 2026-10-11, run entry by entry: 24 questions, 28 decisions, frontier empty, report https://claude.ai/artifact/GGEzLQDmquUfrUhacFgmmK. The operator confirmed the shared understanding: "Confirmo, pode seguir (Recommended)". Each Origin entry's "Scope grill 2026-10-11" paragraph in `BACKLOG.json` records its verbatim ruling, scope and wave. This SPEC restates only what binds rc-14.

The wave rule (operator, 2026-10-11): rc-14 is Wave 1. Wave 1 is ordered by leverage on all later work. It covers law, skills, personas and the dev loop, plus every confirmed bug (bugs law §2).

---

## Bug window review

rc-13 ran from its birth (`7a1ae384a`, 2026-10-10) to its implementation at `d68a7c42f` (2026-10-11T00:58:51Z) and its closure. Three fixes closed in that window. One REBUILD verdict carried from rc-13's table is still owed.

| verdict | disposition | fixes |
|---|---|---|
| KEEP | `git show 44a9f58c8`: +34/−92 in `model_registry.py`. This is itself the REBUILD that its `caused_by` required. It edited no assert, added no branch and reached into no other feature. No record since names it in `caused_by` or correlates with it. The Codex CRLF bug (FR16) is in a parser last changed 2026-09-28 (`a4f58278b`), which is outside this fix. | `agent-model-templates-pin-superseded-sonnet-and-haiku` |
| REBUILD — FR13 | `git show d68a7c42f`: +6/−5. This is the second fix in one day on `_release_phase._refuse_open_worktrees`. The first, `f1d59e9e6`, added the define-tree exception, and this one fixed its candidate parse: two fixes on one unit. The unit computes "the next candidate number" a second time. `_release_schema.next_candidate` computes it for `release.py new`, and the open bug `release-new-orphans-a-drafted-next-rc` is the failure of that second computation. The REBUILD leaves one decider of the next candidate, consulted by both verbs. Its test `test_the_closure_spares_only_the_next_candidates_define_tree` stays unedited. | `release-closure-refuses-the-next-candidates-define-tree` |
| KEEP | `git show d7503ff81`: a revert of the culprit specs commit, with no code and a `block: (1)` body. The structural cause is guard v33 reading `specs/` prose, and FR9 removes it at the root. The missing commit-shape row is FR6. | `rc13-define-cites-an-unread-prefix-family` |
| REBUILD — FR11 (carried) | rc-13's table carried the verdict on `2a8b5637f`. That fix added a second parser of `_RELEASE.json` inside `_worktree_new.py`, and `worktree-new-crashes-on-an-unreadable-release-state` is that parser failing. FR11 executes the verdict. | `worktree-new-opens-a-job-outside-implementation` |

Job 1 executes both REBUILD rows.

## 1. Problem

The law, the skills and the dev loop are the base every later wave builds on, and they carry six defects:

- The grill's record is a handoff that expires after a day. 28 accepted ADR rulings cite answer ids that can no longer be read.
- Any decision can become an ADR, and none records the options it rejected.
- The `ADR:` label on principles duplicates ledger status and has drifted.
- The shipped law tells users in any language about this library's Python internals and ADR numbers.
- Skills let the model type dates.
- A specs-only definition can turn a code guard red. The developer has no way to run only the tests a change reaches.

Nine confirmed bugs are open. A ship refuses any open bug that the operator has not authorized.

## 2. Measurable Goals

- G1. A grill decision can be read without a handoff. Every ADR proposed after rc-14 carries `options` and a self-contained `ruling.words`.
- G2. Status has one home: after ADR 0245's acceptance, no `ADR:` line remains under a principle in `specs/memory` or the scaffold.
- G3. `bugs.py status` lists none of the nine Origin bugs as open at rc-14's closure.
- G4. The FR4 grep over `dadaia_workspace/public/` returns only the workspace's own operation.
- G5. `git grep -n -- '--ts' dadaia_workspace/public/skills` returns nothing.
- G6. A specs-only change cannot turn the repo guards red through prose. `scripts/ci.py --changed` runs only the tests the diff reaches.

## 3. Requirements

### FR1 — dd-grill-me complete, name kept (`dd-ask-me-owned-questioning-skill`)

Operator: "Tudo, sem rename (Recommended)". The skill keeps the name `dd-grill-me`, so the rename and its blast radius are out of scope.

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
  - the `ADR:` grammar in the scaffold memory law;
  - the ADR law's `ADR:` line and its §5.1 label clauses;
  - `PILLAR-MEMORY.md`'s label clause.

  The missing-`Measured by:` finding and the pairing rule stay. The `ADR:` lines in `specs/memory` leave in ADR 0245's acceptance commit. The triage and the generated section are Wave 4 work, so this entry stays active after rc-14.

### FR4 — the shipped surface is language-neutral (`public-law-language-neutral`, whole entry)

- AC4.1 (no test — reviewer source sweep; the grep and its count go in the commit body): `dadaia_workspace/public/` names no package path of this library, no ADR number of this repo, and no Python-only project tooling. The workspace's own operation is the exception: `.dadaia/.venv` and `uvx dadaia-workspace`. Each finding is deleted, rewritten language-neutral, or moved to `repos/dadaia-workspace/AGENTS.md`. Nothing moves to private. Two kinds of file stay as they are: those the entry leaves to another owner, and `scripts/pre-push-ci-gate.sh`, which Wave 3 deletes.

### FR5 — harness-specific surface minimized (`harness-specific-surface-minimized`)

Operator: "minimizamos a superficie do que é especifico de cada harness (sub-agents e hooks principalmente)".

- AC5.1 (no test — reviewer source sweep): One law line, in one home, states the strategy: common behaviour lives in skills and `AGENTS.md`, and each harness gets only the surface it cannot do without.
- AC5.2 (no test — PLAN §1): The as-is review lists every harness-specific asset the library ships, each with a verdict. Every DELETE row lands in rc-14. Any other row goes to the operator at PLAN approval.

### FR6 — a commit shape for a specs revert hotfix (`hotfix-specs-revert-commit-shape`)

- AC6.1 (no test — reviewer source sweep): `dd-gitflow-default` §3a has one row for a hotfix that reverts `specs/` text. The row names the hotfix tree, the reverted `specs/` paths and the message of a revert that carries its `block:` item.

### FR7 — the bug batch trigger and the attempt cap (`bug-batch-cause-trigger-and-attempt-cap`)

- AC7.1 (no test — reviewer source sweep): One line in `dd-bug-resolution` sets the batch trigger: the rc bug window or 20 registrations, whichever comes first. Open bugs that share a cause are fixed together, which is where ADR 0123 lives.
- AC7.2 (no test — reviewer source sweep): One line sets the cap: two fix attempts on one bug, then a fresh session with a written diagnosis.

### FR8 — dates come from the clock (`programmatic-dates-in-skills`)

- AC8.1 (integration, RED first): `bugs.py` and `backlog.py` reject `--ts` as an unknown option and stamp from the clock.
- AC8.2 (integration, RED first): A handoff's file-name stamp and its `produced_at` come from one clock read, never from text the model typed.
- AC8.3 (no test — reviewer source sweep): Every other date a skill writes names its source: `date -u`, git or gh.

### FR9 — the test suite diet and the v33 root (`test-suite-diet`, carrying `define-backlog-merge-runs-verify`)

- AC9.1 (no test — reviewer source sweep): The entry's closed DELETE list leaves wherever it still exists:
  - the vacuous honesty-residue test;
  - the duplicates of the conftest sessionfinish, the stewardship mechanics, gitleaks plus pre-push, and the CI repo-hygiene job;
  - the mutation wiring.

  Each unique guard runs as a script of the one CI guard job. Each deletion commit names the check that still catches what it caught.
- AC9.2 (integration): `scripts/ci.py` keeps only the job level. The dead task and stage code leaves, and `python scripts/ci.py job` keeps its steps.
- AC9.3 (unit, RED first): Guard v33 reads no `specs/` prose, so a SPEC that cites a new id family leaves `scripts/guards/run.py` green. If the as-is review shows from git history that v33 never caught real slop, v33 is deleted instead. No new gate.

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

### FR15 — `context-repo-refusals-carry-no-fix-line` (MEDIUM)

- AC15.1 (integration, RED first): Three refusals each print `Error:` then exactly one `fix:` line naming its own recovery command (ADR 0073): `context repo add` with a different URL, `context repo remove` of an unregistered slug, and `context create`'s associated-repo conflict.
- AC15.2 (integration, RED first): Adding the context's own main repo exits 0 as a no-op. The operator ruled that this refusal becomes idempotent.

### FR16 — `codex-persona-frontmatter-drops-on-crlf` (MEDIUM)

- AC16.1 (unit, RED first): For the same persona, on LF and CRLF, the Codex projection reads the same fields that `core/frontmatter.py` parses, with quoted values unquoted. The projection's private frontmatter parser leaves.

### FR17 — `doctor-misses-worktrees-of-a-repo-that-left-its-context` (LOW)

- AC17.1 (integration, RED first): A linked worktree under `worktrees/<repo>/` whose repo has left its context is a doctor finding with one fix line (ADR 0112).

### FR18 — `job-gate-red-on-untracked-bytecode` (LOW)

- AC18.1 (unit, RED first): An ignored `__pycache__/*.pyc` under `public/` keeps the test green, and a tracked one fails it. The shipped contract stays the build exclude.

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
- The `ADR:` status label on principles, with its grammar, lint exemption, law lines and pillar clause, leaves (FR3).
- ADR 0187 (1)(3) and 0205 as accepted text are superseded by 0244. Their code is already gone (FR2).
- Library internals, Python-project assumptions and ADR numbers in shipped law are removed (FR4).
- `--ts` on `bugs.py` and `backlog.py`, and handoff dates typed by the model, are removed (FR8).
- The honesty-residue test, the duplicate meta-tests, the mutation wiring, `ci.py`'s task and stage code, and v33's reading of `specs/` prose are removed (FR9).
- The raw `_RELEASE.json` read in `_worktree_new.py` is removed (FR11).
- `release.py check`'s DAG check that skips the job files becomes one comparison (FR12).
- Two computations of the next candidate number become one (FR13).
- POSIX `shlex` splitting on Windows is replaced (FR14).
- `Error:`-only context repo refusals and the own-main refusal are replaced (FR15).
- The Codex projection's private frontmatter parser is removed (FR16).
- The working-tree bytecode assertion is replaced (FR18).
- `PYTHONUTF8` and `PYTHONIOENCODING` in CI are removed (FR19).

### Governance sequencing

1. ADRs 0243, 0244 and 0245 are proposed in this define tree. Under rule M2, each names its targets in `context`, and the main thread sets `supersedes` and `amends` at acceptance: 0244 supersedes 0205 and amends 0187; 0245 amends 0165.
2. The operator's rulings land before the SPEC is approved. 0245's acceptance commit deletes the `ADR:` lines of `specs/memory`.

### Delivery constraints

- Job 1 runs first and executes the two REBUILD verdicts (FR11, FR13).
- Every bug fix lands its RED test before the fix (bugs law §2). DELETE and REBUILD tasks come before ADD tasks.
- FR2's schema change lands before FR1's adr reference cites it.
- Shipped law changes only in `dadaia_workspace/public/` and reaches this instance by projection, never by hand edits.

### Risks

| risk | control |
|---|---|
| FR4 and FR5 sweeps grow without bound | the closed list in the FR4 entry; FR5 lands only DELETE rows, and the rest goes to the operator |
| Unmasked CI legs expose many encoding defects | each one is proposed as a bug and fixed at its cause, never re-masked (AC19.1) |
| FR9's v33 change hides real slop | AC9.3 has the as-is review read v33's git history; deletion only on evidence |

## 7. Open questions

None.
