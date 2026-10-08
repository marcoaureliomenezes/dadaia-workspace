# PLAN — Release: 0.5.0, candidate 11

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

The SPEC defines the product contract. This PLAN records the inspected present state, the dependency graph, exact job write ownership and the transition from the current stage-shaped release dialect to the jobs-and-tasks dialect. Paths are relative to the repository root.

## As-is review

Order per row is DELETE → REBUILD → UPDATE → KEEP → ADD. The detailed evidence is in `.dadaia/handoff/dadaia-workspace/2026-10-08T183940Z-dd-software-engineer-rc11-as-is.handoff.json`.

| unit | today | bugs | verdict | why |
|---|---|---:|---|---|
| `specs/constitution.md`, root/public/scoped law and release skills | heavy release ceremony is repeated across generated and canonical sources | many downstream law records | REBUILD | Job 1 installs Features × Futures and the light path in the source files, then reprojects |
| `_release_schema.py`, worktree scripts | release-shaped names and five task-id readers; no plain worktree | 24 relevant records | REBUILD | one parser accepts `J<n>.T<k>` plus legacy ids; one-segment change worktrees base on the configured live work branch, otherwise the checked-out branch |
| task/stage merge gates | task, stage and job each run checks; a deleted freeze previously coupled tests to stage ids | 5 freeze bugs plus merge-gate history | REBUILD | task merge checks hygiene and implementation/test separation; job merge runs tracked `verify:` once and retains the bound independent verdict |
| freeze, own-judge and closure git-window paths | deleted at `adec87277`, `165cce183`, `91e1d1991` | 9 | KEEP | these are validated deletions; do not rebuild them |
| verdict binding | `reviewed_sha`, `diff_sha256` and patch-series equivalence bind a job review | 4 | KEEP | this remains the evidence boundary; there is no live `ci_run` schema field |
| CI and repo `verify:` | three local levels and a full matrix on pushes | 12 | REBUILD | pushes use one Linux path; PRs keep the matrix; fast verify keeps lint, mypy, guards and unit tests |
| venv guard and law-deletion citation gate | pre-tool shell policing plus ADR-citation enforcement at push | 13 | DELETE | retain the workspace venv, canonical-specs, branch and denylist checks |
| bug and audit ledgers | git-derived fix reader, balance prose and `deferred`; 13 deferred audit findings | 24 plus 13 rows | REBUILD | store the resolve sha, remove derived ceremony, reopen deferred findings and keep an audit open while any finding is open |
| release state and candidate documents | 11 new-log kinds, rigid SPEC body, stages and contracts | 32 | REBUILD | four new-log kinds; seven-section default; PLAN DAG and exact W sets; jobs and tasks only |
| derived-document and behavior-map hashes | section hashes and `hash_tuple` create re-record churn | 3 direct | DELETE | retain registry, grants, ownership and source/projection checks |
| memory closure | entry-exists check already landed; memory remains in doctor scripts | 3-chain | UPDATE | remove the memory checker from `LEDGER_SCRIPTS`; closure still runs drift, writes one memory entry and generates the catalog |

## Authorities and transition

- `_release_schema.py` becomes the sole task-id and job-file parser. It reads `J<n>.T<k>` and historical `J<n>.S<m>.T<k>` ids; no writer emits the historical form after Job 1.
- A plain worktree records its base. With a live release it uses that release's configured gitflow `work_branch`; with no live release it uses the repository's currently checked-out branch. Merge returns to the recorded base and runs its tracked `verify:` once when present.
- The current phase transition requires `## DAG`, `### Hot files`, `## Stage` and `- Contract:`. This PLAN and the job files therefore contain explicitly temporary compatibility metadata while already using current ids. Job 1 owns `_release_phase.py` and every existing phase-shape assertion in `test_release__release_script.py`: it first commits the transition RED, then J1.T2 installs the parser and phase reader while J1.T3–J1.T4 change their disjoint source/law envelopes. Only after T2–T4 have merged onto the Job 1 branch does the main thread open J1.T5 from that updated branch to remove `### Hot files` from this PLAN and the wrappers from `job2.md`, `job3.md` and `job4.md`. Job 1's wrapper remains immutable history and is accepted only through legacy reading. No tool is bypassed and no implementation precedes its RED dispatch.
- Every implementation task has two main-thread dispatches: the first owns all test-path changes and commits the failing acceptance tests; a fresh second dispatch owns production/source changes and may not touch a declared or fallback test path. Review rework follows the same split when it adds or changes behavior.
- Job review retains `reviewed_sha` plus `diff_sha256`; merge recomputes the digest. The work branch's tracked `verify:` is the only verify authority.

## DAG

| job | waits on | why |
|---|---|---|
| Job 1 | — | dependency kernel, transition parser, all AGENTS/SKILL law, worktrees, CI, hooks and push gate land first |
| Job 2 | Job 1 | imports the one task-id parser; deletes bug/audit derived state together with `_release_tree.py` and the existing release tests that consume it |
| Job 3 | Job 1 | consumes the new task/job parser and document dialect; its dedicated lean-state test file does not share Job 2's consumer tests |
| Job 4 | Job 1 | Job 1 temporarily re-records `behavior-map.json` so its verify remains green; Job 4 then deletes the hash fields and validators |
| Reconciliation | Jobs 2, 3, 4 | one summary, product-memory pass, catalog generation, projection and final checks |

Job 1 has its own dependency DAG because the bootstrap changes the dialect used by later jobs:

| Job 1 act | waits on | why |
|---|---|---|
| J1.T1 | — | commits every acceptance row RED before implementation |
| J1.T2 | J1.T1 | installs the parser, phase bridge and worktree kernel |
| J1.T3 | J1.T1 | changes its disjoint hook/push/CI envelope |
| J1.T4 | J1.T1 | changes its disjoint law/ecosystem envelope |
| J1.T5 | J1.T2, J1.T3, J1.T4 | final metadata rewrite; it is opened from the updated Job 1 branch only after all three task merges |
| Job 1 gate/review | J1.T5 | verifies and reviews the exact post-transition job head |

The intentional cross-job rewrites are ordered by Job 1: it updates the current phase assertions before Job 2 later removes the balance assertions from `test_release__release_script.py`; it temporarily writes `dadaia_workspace/public/entities/behavior-map.json` before Job 4 removes `hash_tuple`; and it updates the entity-derivation assertion for venv-guard removal before Job 4 removes hash validation from that test. After Job 1, Jobs 2, 3 and 4 have pairwise-disjoint W sets and run in one parallel wave. Job 2 owns `_release_tree.py`, including both balance-consumer deletion and summary-origin tracing; Job 3 does not rewrite that consumer.

### Hot files

This subsection is compatibility metadata for the current `release.py phase IMPLEMENTATION` check and J1.T5 removes it after the lean phase/parser bridge and every parallel Job 1 source task have merged.

- `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` and `_release_phase.py`: Job 1 establishes the parser and executable phase bridge; Jobs 2 and 3 consume them without writing them.
- `dadaia_workspace/public/entities/behavior-map.json`: Job 1 temporarily re-records current skill hashes so its verify is green; Job 4, ordered after it, deletes `hash_tuple`.
- `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py`: Job 1 migrates phase-shape assertions; Job 2 later deletes balance/quality assertions and tests `_release_tree.py` summary tracing.
- `tests/infrastructure/test_entity_doctor__agentic_entities_derivation.py`: Job 1 removes the venv-guard expectation; Job 4 later removes hash expectations.
- `specs/releases/0.5.0/rc-11/PLAN.md` and `tasks/job2.md` through `job4.md`: J1.T5 solely owns the compatibility metadata removal. The main thread opens T5 after merging T2–T4, so its task worktree starts at the final source/law head; its task merge runs the tracked `verify-task:` over those four document paths before the Job 1 gate.

## Write ownership

The complete per-task paths live in `tasks/job1.md` through `tasks/job4.md`. No glob is a write grant. Generated runtime projections (`.agents/`, `.claude/`, `.codex/`, `.kimi-code/`) are never in W; public sources are staged and installed after their owning job merges.

- Job 1 owns the dependency parser and phase bridge, worktree scripts, CI configuration, hook/push deletion, `public/entities/registry.json`, every AGENTS.md/SKILL.md source authorized by SPEC AC7.3, their installed repository counterparts, supporting release/worktree prose, shipped-template history and its temporary behavior-map re-record.
- Job 2 owns bug/audit code and schemas, ledger migration, the bug-schema contract test, `LINEAGE.md`, `FINDINGS-FORMAT.md`, `_release_tree.py` and its existing balance/deferred consumer tests. It does not edit AGENTS.md or SKILL.md.
- Job 3 owns the remaining release writers/schema, `RELEASE-EVENTS.md`, the release doctor if its rigid duplicate is present, and a dedicated lean-state acceptance test. It does not edit bug/audit files, `_release_tree.py`, AGENTS.md or SKILL.md.
- Job 4 owns only derived-hash code/data/docs and its tests. Product memory (`specs/memory/ARCHITECTURE.md`, `QUALITY.md`, `product/agents/agentic-entities.md`, catalog) is reserved for the dd-product-engineer reconciliation pass.

## Schedule and estimate

The clean unchanged-main rerun supplied by the main thread is the baseline proof: `scripts/ci.py stage` exited 0 with lint, strict mypy, guards and planted guards all PASS; unit reported 1298 passed in 22.29 seconds. A prior stage invocation took 76 seconds but failed only because the inspection had created ignored bytecode under `public/`; 76 seconds is retained as a prior end-to-end timing, not labeled a clean result. Each range below includes implementation uncertainty; gate/review rows include repeated focused checks plus one full tracked verify and reviewer turnaround.

| act | waits on | elapsed | uncertainty / contingency |
|---|---|---:|---|
| J1.T1 transition RED | — | 0.6–0.9 h | existing cross-contract tests make deletion triage the main variance |
| J1.T2 parser/worktree/phase implementation | J1.T1 | 0.7–1.1 h | parser compatibility and recorded-base merge are the risk |
| J1.T3 hook/push/CI implementation | J1.T1 | 0.5–0.8 h | CI selector and deletion sweep may expose one extra contract row |
| J1.T4 law/ecosystem implementation | J1.T1 | 0.8–1.2 h | 15-rule ecosystem/cross-citation sweep is the upper-bound driver |
| J1.T5 final compatibility metadata | J1.T2–J1.T4 | 0.2–0.4 h | includes opening from the updated job branch, four document edits, commit and task-merge `verify-task:`; it is not opened early and needs no rebase contingency |
| Job 1 gate + review | J1.T5 | 0.4–0.6 h | includes public stage/install/doctor and one rework allowance over the post-transition head |
| J2.T1 bug/audit/consumer RED | Job 1 | 0.6–0.9 h | balance/deferred tombstone triage spans existing release tests |
| J2.T2 bug/audit/consumer implementation | J2.T1 | 1.2–1.8 h | one-time finding migration and `_release_tree.py` are the risk |
| Job 2 gate + review | J2.T2 | 0.4–0.6 h | one rework allowance |
| J3.T1 lean-release RED | Job 1 | 0.5–0.8 h | dedicated owner file avoids Job 2 test overlap |
| J3.T2 lean-release implementation | J3.T1 | 1.0–1.5 h | history-compatible log/schema reads are the risk |
| Job 3 gate + review | J3.T2 | 0.4–0.6 h | one rework allowance |
| J4.T1 structural-derivation RED | Job 1 | 0.4–0.7 h | deletion-test inventory is the variance |
| J4.T2 structural-derivation implementation | J4.T1 | 1.0–1.5 h | docs marker removal and structural validator retention are the risk |
| Job 4 gate + review | J4.T2 | 0.4–0.6 h | includes public doctor and one rework allowance |
| Reconciliation + final review | Jobs 2–4 | 0.5–0.9 h | memory worklist or projection drift consumes the contingency |

J1.T2–J1.T4 run in parallel after J1.T1; J1.T5 then runs alone before the gate. Job 1 elapsed is therefore `J1.T1 + max(T2,T3,T4) + T5 + gate/review` = 2.0–3.1 hours, while its aggregate effort is `T1 + T2 + T3 + T4 + T5 + gate/review` = 3.2–5.0 agent-hours. Jobs 2–4 then run in parallel; their elapsed and aggregate ranges are respectively 2.2–3.3, 1.9–2.9 and 1.8–2.8 hours because each job's two tasks and gate are sequential. The critical path is `Job 1 elapsed + max(Jobs 2–4 elapsed) + reconciliation` = 4.7–7.3 wall-clock hours. Aggregate effort is `Job 1 aggregate + Job 2 + Job 3 + Job 4 + reconciliation` = 9.6–14.9 agent-hours. The 7.8-hour cap retains 0.5 hour of upper-bound contingency; a new semantic edge, a Job 1 estimate above 3.5 hours or work outside the listed W sets returns this Draft to the main thread for an explicit scope decision. Q19's private `~/.claude` work is excluded from both estimates.

## Verification and closure

Each RED task runs its named focused tests with `--runxfail` or the repository's equivalent proof of the intended failure. Each implementation task runs the same focused tests green. Each job runs tracked `verify:` once, public-source jobs additionally run public stage/install/doctor, and one independent reviewer returns APPROVED for the exact job digest. Reconciliation runs release check, bug check, audit check, public doctor and the repository verify command; then the product engineer prunes memory to current truth, writes one memory log entry and generates the catalog. No implementation or approval has occurred while this PLAN is Draft.
