# SPEC — Release: 0.5.0, candidate 11 — light by default

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-08
**Origin:** operator-demand

---

## Bug window review

`bugs.py window --specs specs` reports 78 fixes found in `0.5.0/rc-10`. The review applies the operator's maturity rule: one KEEP removes a fix from the first-level window; a REBUILD leaves after its replacement merges with a test and the next candidate produces no bug from it. A deleted unit is a validated REBUILD. Every rc-10 fix appears exactly once.

| verdict | disposition | fixes |
|---|---|---|
| KEEP | The fix remains the simplest tested behaviour; it leaves the first-level window. | `agentic-projections-agent-writable`, `approval-precondition-four-versions`, `declared-bom-strip-depends-on-locale-decoding`, `declared-echo-rereads-the-law`, `default-tests-globs-under-match-dotnet-android`, `grill-skill-contradicts-adr-0165`, `guards-check-not-required-by-live-protection`, `import-raises-keyerror-on-a-record-missing-a-field`, `law-cites-commands-that-fail-from-root`, `law-cites-dead-sections-and-retired-terms`, `public-install-never-restages-after-an-upgrade`, `public-law-teaches-the-private-pipeline`, `push-before-review-forbidden-and-required`, `read-only-reviewer-named-audit-writer`, `review-assert-guard-has-no-base-range`, `root-enforcement-section-states-false-blocks`, `skill-git-output-decodes-with-the-locale`, `skills-ask-grantees-for-writes-they-cannot-do`, `software-engineer-persona-self-contradicts`, `spec-navigator-subagent-rebinds-parent`, `subprocess-text-encoding-has-no-guard`, `tests-line-predicate-lives-in-two-readers`, `verdict-ttl-shorter-than-merge-window` |
| REBUILD — deletion | The landed freeze, memory-window and own-judge deletions already validate their rows. Planned deletions become validated only at their rc-11 job closure. The regression test is kept where the surviving contract still has a seam. | `backlog-skill-asks-a-merge-the-writer-cannot-do`, `bug-resolution-law-prescribes-rewriting-asserts`, `check-stray-laundered-by-rebase`, `freeze-adversary-row-asserts-not-none`, `freeze-cannot-see-a-red-amendment-stage`, `freeze-deadlocks-a-repo-without-a-tests-line`, `freeze-has-no-lane-for-an-approved-amendment`, `freeze-reads-only-numbered-job-ids`, `gate-runs-the-judged-trees-own-ci-script`, `hook-unreadable-fix-line-crashes-installer`, `memory-window-bound-shallow-clone-named-as-rebase`, `own-judge-check-hands-the-verify-argv-to-git-as-paths`, `pillar-bugs-metric-reads-retired-event-stream`, `push-refusal-advertises-no-verify`, `rc-closes-with-an-open-bug`, `rebase-orphans-bug-fix-links-cited-by-sha`, `release-check-parses-the-gitflow-in-the-skill`, `reports-validate-documents-exit-codes-it-never-returns`, `root-allows-git-and-gitignore-though-root-is-never-a-repo`, `skill-script-root-walks-ignore-the-fence`, `task-fix-over-a-bug-fix-records-no-lineage`, `trio-status-canon-judged-outside-the-define-merge-gate`, `worktree-removal-leaves-empty-parent-and-remote-branch` |
| REBUILD — rc-11 | The unit changes fundamentally in this candidate; its existing regression tests remain as contract evidence unless the unit is deleted. | `bug-balance-cuts-a-non-utc-closure-day-to-local`, `bug-fix-links-a-task-id-across-rcs`, `bugs-check-reads-no-jb-task-ids`, `canonical-shape-guard-refuses-the-bugs-section`, `default-tests-globs-over-match-source`, `git-errors-replace-has-no-row`, `manager-orchestration-skill-allows-job-dispatch`, `memory-written-before-closure-phase`, `onboarding-writes-no-tests-line`, `quality-bugs-review-names-release-ids`, `release-check-fallback-fix-line-drops-specs`, `release-check-reads-status-of-backlog-exits`, `release-check-reds-every-change-after-the-closure-memory-entry`, `release-check-reds-main-after-an-operational-lane-commit`, `release-check-skips-a-rebased-away-until`, `release-definition-law-claims-a-deleted-stage-one-check`, `release-ship-requires-a-pr-number`, `test-path-convention-is-python-only`, `unit-fast-cross-lacks-the-dadaia-launcher-on-windows`, `venv-guard-misses-prefixed-and-absolute-dadaia` |
| REBUILD — rc-12 Job 1 | The script reports later rework, but rc-11 does not change the owning unit. The next candidate's first job must rebuild it with its tests; this is scope, not backlog intake. | `context-show-live-branch-test-rmtree-readonly-git-on-windows`, `coverage-line-test-spawns-bare-python-on-windows`, `fix-line-run-tests-spawn-wsl-bash-on-windows`, `fix-line-tests-expect-posix-bin-paths-on-windows`, `hook-wrapper-tests-run-an-unrunnable-fixture-python-on-windows`, `job-merge-accepts-any-ci-run-url`, `job-merge-requires-a-remote-ci-run`, `merge-gate-accepts-verdict-written-by-the-merger`, `orphan-worktree-line-absent-from-the-bind-block-on-windows`, `root-gate-blocks-editing-an-existing-entry`, `shipped-law-hardcodes-the-posix-venv-path`, `worktree-script-run-fails-winerror-193-on-windows` |

## 1. Problem

The default development path grew into release, candidate, job, stage and task rituals whose repeated gates, parsers, ledgers and generated narratives cost more than the product changes they protect. rc-10 made that cost visible. The product needs a small safe core in which ceremony is opt-in, tests are written before implementation, one review judges one job, and persisted records contain product facts rather than duplicated code facts.

The governing product philosophy is Features × Futures: a feature or fix spends future options when it adds coupling, so delivery alternates with work that restores options. The bug window review is the concrete recovery mechanism.

## 2. Measurable Goals

- G1. The PLAN estimates the complete candidate at no more than 7.8 wall-clock hours on its critical path from explicit task durations and dependencies, cites measured baseline timings, states uncertainty and contingency, and discloses aggregate agent-hours; any larger cluster is removed before approval rather than assigned a fictional estimate.
- G2. A normal change can use one plain worktree, one repository `verify:` run and one review, without creating a release, candidate, job or task record.
- G3. After the Job 1 bootstrap, a release candidate uses jobs and tasks only: no stage command, stage contract, stage gate, task gate or mandatory bug-batch job remains.
- G4. The release, bug, audit and memory ledgers retain only facts that are not derived from git or source; each retained fact has one parser and one writer.
- G5. Push CI on `wt/**` and `feature/**` completes its Linux path once; pull requests retain the full Linux, Windows and macOS matrix.
- G6. Every AGENTS.md and SKILL.md source changed by this candidate is named in this SPEC, making approval the operator's authorization for those edits.

## 3. Non-goals

- Reimplementing the already-landed hotfix deletions of the test freeze, memory git-window check or own-judge refusal; rc-11 only reconciles remaining law and tests.
- Implementing the operator's private `~/.claude` cleanup in this repository. It is separate operator tooling: keep gate 2 in the commit hook, make mutation and test-audit optional reviewer tools, reduce the pre-review checklist from 13 items to 5, and retire the private architecture and test-stack rules.
- Completing the REBUILD fixes assigned above to rc-12 Job 1.
- Adding stored maturity, carry, balance or derived-git fields to any ledger.
- Removing the mandatory independent reviewer verdict from a job merge, or its `reviewed_sha` and `diff_sha256` binding.

## 4. Requirements

### FR1 — Features × Futures and bounded candidates

- AC1.1 (no test — operator approval gate): When a candidate is proposed, the PLAN must estimate a critical path of at most 7.8 wall-clock hours from each task's duration and the DAG dependencies, disclose aggregate agent-hours, cite the measured gate/runtime baselines used, and state uncertainty plus contingency before the SPEC may become Approved.
- AC1.2 (no test — reviewer source sweep): The constitution must state Features × Futures as an accepted product principle, and the public root map must explain in 3–5 lines that features and fixes spend options, coupling is cost, delivery alternates with option-restoring work, and the bug window review restores futures.
- AC1.3 (no test — reviewer source sweep): When the public corpus is reviewed, the retired private architecture-review rule must have no projected or source reference.

### FR2 — light worktrees and test-first separation

- AC2.1 (integration): When `worktree.py new <repo> <name>` is invoked outside a release job, a one-segment lowercase kebab name outside the reserved `backlog`, `hotfix` and `<M.m.p>-rc<N>` namespaces must create `worktrees/<repo>/<name>` on `wt/<name>` carrying neither a SPEC nor a bug record. It must base on the gitflow work branch when a live release exists, otherwise on the currently checked-out branch; merge must return to that recorded base, run its tracked `verify:` once when declared and allow it when absent.
- AC2.2 (no test — dispatch and handoff evidence): When a release task is implemented, the main thread must dispatch `dd-software-engineer` once to commit failing acceptance tests and a fresh second time to implement them.
- AC2.3 (integration): When an implementation commit in the second dispatch touches a test path declared by the repository, or in the built-in fallback `tests/`, `test_*`, `*_test.*`, `*.spec.*`, task merge must refuse it; when no matching test path exists it must not refuse for this reason.
- AC2.4 (integration): When a task merges, it must run git hygiene plus AC2.3 only; when a job merges, it must run the work branch's tracked `verify:` once and require one APPROVED reviewer verdict bound by `reviewed_sha` and `diff_sha256`.
- AC2.5 (no test — mandatory reviewer verdict): The reviewer must refuse a diff that weakens the repository verify command, tests or guards. The work branch remains the sole authority for `verify:`; removing retired task/stage levels must not repeal that rule.

### FR3 — jobs, tasks and candidate documents

- AC3.1 (unit): When the dependency kernel parses an id, it must accept current `J<n>.T<k>` ids and historical `J<n>.S<m>.T<k>` ids; five other task-id parsers must be deleted.
- AC3.2 (integration): After the rc-11 Job 1 bootstrap lands on the work branch, `worktree.py stage`, `verify-stage:`, `verify-task:`, stage headings and `Contract:` lines must have no active writer, parser, command or gate.
- AC3.3 (unit): When release validation reads a job file, it must accept tasks carrying id, AC and exact `W:` set without stage material.
- AC3.4 (unit): When validation reads a PLAN, it must require the as-is review plus a DAG naming each job's complete `W:` set and wave, and refuse two jobs in one wave whose `W:` sets overlap.
- AC3.5 (unit): When a SPEC is created, its template must contain exactly the seven default sections used here; validation must prescribe only canonical Status and the `Bug window review` heading, retain Origin as a plain line, and allow user-added sections.

### FR4 — bugs and audits without derived ceremony

- AC4.1 (unit): When bug-window maturity is read, it must be derived from the prior SPEC table with no ledger field: one KEEP exits the first-level window; a REBUILD exits after a tested replacement and a following candidate with no child bug.
- AC4.2 (integration): `release.py ship` must refuse every open bug by default; after the operator authorizes an id in chat, `--allow-open <id>` must require one flag per open bug plus a `kind: note` entry containing the authorization verbatim, leave the bug open and carry it into the next candidate's scope.
- AC4.3 (unit): After rc-11 lands, the mandatory bug-batch job, QUALITY `## Bugs`, `bugs.py balance`, `_bugs_balance.py`, `_bugs_quality.py` and the release-check balance finding must be absent.
- AC4.4 (unit): When `bugs.py resolve` closes a bug, it must write cause, solution, caused_by and the fix sha; `caused_by` may be `none` only when blame offers no candidate. `evidence_loop`, `evidence_seam`, `--lineage-reason` and the five-regex fix reader must be absent.
- AC4.5 (unit): When bug history is archived, it must require no accepted ADR gate.
- AC4.6 (integration): After ADRs 0223 and 0227 are accepted together, `deferred` must be absent from bug status, audit finding disposition and audit closure; existing deferred bug and finding records must migrate once, and an audit with an open finding must stay open.

### FR5 — lean release state and memory

- AC5.1 (unit): When a new `_RELEASE.json` log entry is written, it must use `milestone`, `note`, `summary` or the closure-only `memory` entry required by AC5.3. A closure summary must contain delivered, carried and backlog exits; Origin trace must read that summary.
- AC5.2 (unit): When legacy log kinds outside AC5.1 are read, they must remain valid history, but no writer may emit them for rc-11 or later candidates.
- AC5.3 (integration): Closure must run `release.py drift` and append exactly one memory entry. `release.py check` must verify only that the entry exists after implementation, without reading git; the already-landed removal of `_release_tree.py`'s git window and `principal_flag` must not be reimplemented. The catalog is generated at closure.
- AC5.4 (no test — closure memory review): When an atom is touched by this candidate, memory must reference the code without repeating it and must be pruned to current product truth.

### FR6 — CI weight

- AC6.1 (integration): A push to `wt/**` or `feature/**` must run Linux jobs only, with coverage measured once inside unit plus integration.
- AC6.2 (integration): A pull request must run the complete Linux, Windows and macOS matrix.
- AC6.3 (integration): This repository's `verify:` must be the fast check — lint, mypy, guards and unit tests. Its numeric target and measured baseline belong only to the PLAN; no release law may promise a fixed wall time.

### FR7 — AI-entity source and derivation cleanup

- AC7.1 (unit): After rc-11 lands, `derived-from` hashes and behavior-map `hash_tuple` fields, their validators and their tests must be absent; derivation must still enforce the registry, grants, source/projection relationships and public privacy.
- AC7.2 (integration): Public assets must be authored at source, then stage, install and public doctor must finish clean.
- AC7.3 (no test — reviewer source sweep): The complete authorized AGENTS.md/SKILL.md source write set is the following list; adding another such source requires returning this Draft to the operator:
  - `AGENTS.md`
  - `specs/AGENTS.md`
  - `specs/audits/AGENTS.md`
  - `specs/bugs/AGENTS.md`
  - `specs/memory/AGENTS.md`
  - `specs/releases/AGENTS.md`
  - `dadaia_workspace/public/data/AGENTS.md`
  - `dadaia_workspace/public/data/worktrees-AGENTS.md`
  - `dadaia_workspace/public/scaffold/audits/AGENTS.md`
  - `dadaia_workspace/public/scaffold/bugs/AGENTS.md`
  - `dadaia_workspace/public/scaffold/memory/AGENTS.md`
  - `dadaia_workspace/public/scaffold/releases/AGENTS.md`
  - `dadaia_workspace/public/templates/repo-AGENTS.md`
  - `dadaia_workspace/public/templates/specs-AGENTS.md`
  - `dadaia_workspace/public/skills/dd-ai-eng-knowhow/SKILL.md`
  - `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`
  - `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md`
  - `dadaia_workspace/public/skills/dd-code-review/SKILL.md`
  - `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`
  - `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md`
  - `dadaia_workspace/public/skills/dd-release-definition/SKILL.md`
  - `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`
  - `dadaia_workspace/public/skills/dd-spec-navigator/SKILL.md`
- AC7.4 (unit): When the public context map describes worktrees after rc-11, `dadaia_workspace/public/data/CONTEXT-MAP.md` must describe the plain path and the surviving job/task gates without the retired three-level model.
- AC7.5 (unit and reviewer source sweep): The complete additional AI-entity ecosystem source write set is `dadaia_workspace/public/entities/registry.json` and these disclosed siblings: `dadaia_workspace/public/skills/dd-audit-project/FINDINGS-FORMAT.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-SPECS.md`, `dadaia_workspace/public/skills/dd-bug-resolution/LINEAGE.md`, `dadaia_workspace/public/skills/dd-gitflow-default/CICD-AUTOMATION.md`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, and `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`. Their owning jobs must update the corresponding behavioral contract tests, including `tests/core/test_atomic_write__core_file_io_purity.py`, `tests/core/test_handoff_index__handoff_schema_contract.py`, and `tests/infrastructure/test_public_assets__public_scripts_thin_wrapper.py`; adding another AI-entity source or disclosed sibling requires returning this Draft to the operator. Generated runtime projections remain outside every task write set and are changed only by stage/install from these sources.

### FR8 — hook and push-gate deletion

- AC8.1 (unit): After rc-11 lands, the venv guard behaviour and ADR 0134 implementation must be absent while the workspace venv and CLI invocation guidance remain.
- AC8.2 (unit): After rc-11 lands, the law-deletion ADR citation check in `push_gate`, its `git_objects.py` support and `doctor_adr.py` support must be absent while denylist, branch and canonical-specs checks remain.
- AC8.3 (unit): After rc-11 lands, the memory checker must be absent from `LEDGER_SCRIPTS`; catalog generation remains a closure act.

## 5. Constraints and risks

### Replaces

- The mandatory release → candidate → job → stage → task path becomes a light plain-worktree path plus an opt-in release path of jobs and tasks.
- Stage contracts and task/stage verify levels become task test-separation plus one job `verify:` run.
- The test freeze and its `tests:` onboarding law become two-dispatch TDD and a merge refusal on implementation commits that touch tests.
- The mandatory same-rc bug batch becomes default ship refusal with an explicit per-bug operator-authorized carry path.
- Bug balance and fix-reader derived state become the SPEC bug-window table.
- Git-revalidated memory windows become drift plus one closure memory record.
- Expanded closure narration becomes one summary and one memory entry.
- Hash-stamped AI derivation becomes structural source/projection validation.
- The three-part pre-tool gate becomes root whitelist plus SDD scope gate; the venv guard is deleted.
- The push-gate law-deletion citation becomes reviewer-governed law change.
- The release-shaped worktree name parser becomes a kernel that also accepts plain change worktrees.

### Governance scope and sequencing

The numbered set below is the exact governance scope approved with this SPEC; it is not an ADR-status authority. The canonical **Status:** field is the sole authority for SPEC approval, and ADR acceptance and rulings live only in `decisions.jsonl`. The G0 sequence is the main thread's Features × Futures ADR record and the dd-product-engineer's authorized constitution amendment in one define-tree governance commit, followed by a separate approval-status commit for SPEC and PLAN. Q21 instead follows the reconciliation sequence below.

1. Supersede ADR 0134 by deleting the venv guard behaviour, while retaining the workspace venv as the CLI runtime.
2. Amend ADR 0151 by deleting M3 only; retain operator-only acceptance, ruling evidence, ruled lineage and the release canon.
3. Amend ADRs 0190 and 0211 by deleting task and stage gate levels; retain one review per job and the task as dispatch unit.
4. Amend ADR 0206 with AC4.2 and delete the mandatory bug batch.
5. Amend ADR 0207 only for the retired `verify-task:`/`verify-stage:` levels; preserve the work branch's `verify:` authority.
6. Accept a new successor ADR that supersedes accepted ADR 0208 and deletes the bug-balance surface; ADR 0208 remains immutable history and is never withdrawn or rewritten.
7. Accept a new successor ADR that supersedes accepted ADR 0209's freeze with the two-dispatch TDD separation; amend ADR 0216 to delete its freeze and balance halves while preserving the mandatory reviewer verdict.
8. Accept proposed ADRs 0223 and 0227 together with AC4.6 and their one-time migrations.
9. Reject proposed ADRs 0224 and 0226: the freeze and own-judge refusal they extend are retired.
10. Accept a new ADR for the Features × Futures constitution principle.
11. Accept one new Q21 ADR authorizing both canonical-memory changes: delete QUALITY P-29 and replace ARCHITECTURE P-17 with structural registry, grant, ownership and source/projection checks that carry no content hash or `hash_tuple`. The new record has no `supersedes` or `amends` target: ADR 0012 is rejected and must not be superseded, while P-17 names no prior ADR. The accepted Q21 ADR is the sole decision cited by both changed principles in their shared commit.

At Reconciliation, after the operator's concrete Q21 ruling, the main thread transcribes the accepted Q21 ADR and the dd-product-engineer authors the authorized QUALITY P-29 deletion and ARCHITECTURE P-17 replacement. The record and both memory changes land together in one reconciliation commit. No implementation task owns the constitution, `decisions.jsonl`, ARCHITECTURE or QUALITY changes.

### Delivery constraints

- The PLAN's estimated critical path is bounded at 7.8 hours and must also disclose aggregate agent-hours, measured baseline inputs, uncertainty and contingency. If the estimate does not fit, the SPEC stays Draft and the operator chooses the subset; estimates must not be compressed to manufacture compliance.
- The candidate has exactly four implementation jobs. Job 1 contains the dependency kernel, removes merge-time weight and lands every authorized AGENTS.md/SKILL.md source plus CI, worktree, hook and push-gate changes; it lands before another job. The PLAN owns every later semantic dependency and may claim parallel execution only for jobs whose complete consumers, tests and write sets are independent. No fifth implementation job or changed edge is added silently.
- Job 1 is the sole bootstrap artifact allowed to use the current stageful grammar because the current validator cannot accept its own replacement. After Job 1 merges, every subsequently opened job/task file uses the stage-free grammar; this transition does not preserve a stage writer.
- Every production behaviour follows test-first separation; each job receives one reviewer verdict.
- `J<n>.S<m>.T<k>` remains readable only for historical records. No writer emits it after rc-11.
- Private `~/.claude` changes carry operator authorization from Q19 but are not repository implementation and do not count toward this candidate's tests.

### Risks

| risk | control |
|---|---|
| Broad deletion silently removes a safety property. | Each removed gate maps to an AC and an independent reviewer checks verify, tests, guards and security. |
| Historical candidates stop parsing. | AC3.1 pins backward-compatible task-id reads and AC5.2 pins legacy log reads. |
| An authorized open bug becomes invisible. | AC4.2 requires one flag per id, verbatim authorization and closure-summary carry. |
| Parallel jobs collide on central public law. | All AGENTS.md/SKILL.md sources land in Job 1; the PLAN overlap check refuses same-wave collisions. |
| Audit/bug migrations lose records. | Migration is one-time, byte-preserving apart from the explicit status/disposition change, and ledger checks run before and after. |

## 6. Open questions

None. The PLAN is the sole authority for task, gate/review, dependency, reconciliation, critical-path and aggregate-effort arithmetic. Any new edge or write outside the listed sets requires the PLAN to be recalculated, and an upper path beyond the 7.8-hour cap requires an explicit operator choice of the requirement cluster that moves to rc-12.
