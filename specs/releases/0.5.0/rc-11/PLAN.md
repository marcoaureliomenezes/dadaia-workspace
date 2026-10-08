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
- The current phase transition requires `## DAG`, `### Hot files`, `## Stage` and `- Contract:`. This PLAN and the job files therefore contain explicitly temporary compatibility metadata while already using current ids. Job 1 first commits RED tests, then installs the new parser and phase bridge, then removes `### Hot files` from this PLAN and the wrappers from `job2.md`, `job3.md` and `job4.md`. Job 1's wrapper remains immutable history and is accepted only through legacy reading. No tool is bypassed and no implementation precedes its RED dispatch.
- Every implementation task has two main-thread dispatches: the first owns all test-path changes and commits the failing acceptance tests; a fresh second dispatch owns production/source changes and may not touch a declared or fallback test path. Review rework follows the same split when it adds or changes behavior.
- Job review retains `reviewed_sha` plus `diff_sha256`; merge recomputes the digest. The work branch's tracked `verify:` is the only verify authority.

## DAG

| job | waits on | why |
|---|---|---|
| Job 1 | — | dependency kernel, transition parser, all AGENTS/SKILL law, worktrees, CI, hooks and push gate land first |
| Job 2 | Job 1 | imports the one task-id parser and executes under the lean task/job law |
| Job 3 | Job 1 | consumes the new task/job parser and document dialect |
| Job 4 | Job 1 | Job 1 temporarily re-records `behavior-map.json` so its verify remains green; Job 4 then deletes the hash fields and validators |
| Reconciliation | Jobs 2, 3, 4 | one summary, product-memory pass, catalog generation, projection and final checks |

The only intentional cross-job rewrites are ordered: Job 1 temporarily writes `dadaia_workspace/public/entities/behavior-map.json`, then Job 4 removes its `hash_tuple` values; Job 1 migrates the compatibility wrappers in the three downstream job files before those jobs open. Jobs 2, 3 and 4 otherwise have pairwise-disjoint W sets and run in one parallel wave.

### Hot files

This subsection is compatibility metadata for the current `release.py phase IMPLEMENTATION` check and J1.T4 removes it after the lean phase/parser bridge lands.

- `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py`: Job 1 establishes the parser; Jobs 2 and 3 import it without writing it.
- `dadaia_workspace/public/entities/behavior-map.json`: Job 1 temporarily re-records current skill hashes so its verify is green; Job 4, ordered after it, deletes `hash_tuple`.
- `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py` and `test_release.py`: Job 1 writes transition RED rows; Job 3, ordered after Job 1, writes release-model RED rows.
- `specs/releases/0.5.0/rc-11/PLAN.md` and `tasks/job2.md` through `job4.md`: Job 1 removes only the compatibility metadata after its replacement parser and phase rules are green.

## Write ownership

The complete per-task paths live in `tasks/job1.md` through `tasks/job4.md`. No glob is a write grant. Generated runtime projections (`.agents/`, `.claude/`, `.codex/`, `.kimi-code/`) are never in W; public sources are staged and installed after their owning job merges.

- Job 1 owns the dependency parser, worktree scripts, CI configuration, hook/push deletion, every AGENTS.md/SKILL.md source authorized by SPEC AC7.3, their installed repository counterparts, supporting release/worktree prose, shipped-template history and its temporary behavior-map re-record.
- Job 2 owns only bug/audit code, schemas, ledger migration and their tests. It does not edit law.
- Job 3 owns only release scripts/schema, the release doctor if its rigid duplicate is present, and release tests. It does not edit bug/audit or law files.
- Job 4 owns only derived-hash code/data/docs and its tests. Product memory (`specs/memory/ARCHITECTURE.md`, `QUALITY.md`, `product/agents/agentic-entities.md`, catalog) is reserved for the dd-product-engineer reconciliation pass.

## Schedule and estimate

The 76-second clean baseline (`scripts/ci.py stage`: lint, strict mypy, guards, planted guards and 1297 passing fast tests after removal of an inspection-created ignored bytecode cache) is the measured check cost. Estimates include two dispatches and one review per job; they are ranges, not commitments.

| wave | work | elapsed estimate | aggregate effort |
|---|---|---:|---:|
| 1 | Job 1 | 2.5–3.5 h | 2.5–3.5 h |
| 2 | Jobs 2, 3 and 4 in parallel | 2–3 h | 5.5–8.5 h |
| 3 | Reconciliation and final review | 0.5–1 h | 0.5–1 h |

Expected critical path is roughly 5–7.5 wall-clock hours; expected aggregate effort is roughly 8.5–13 agent-hours. The upper wall-clock bound leaves about 18 minutes inside the 7.8-hour cap. Scope or estimates may be revised only while the candidate is Draft, before approval. Once implementation launches, agents follow the approved ACs and report any actual overrun in the release narrative without dropping scope, reopening the grill or changing status unilaterally. Q19's private `~/.claude` work is excluded from both estimates.

## Verification and closure

Each RED task runs its named focused tests with `--runxfail` or the repository's equivalent proof of the intended failure. Each implementation task runs the same focused tests green. Each job runs tracked `verify:` once, public-source jobs additionally run public stage/install/doctor, and one independent reviewer returns APPROVED for the exact job digest. Reconciliation runs release check, bug check, audit check, public doctor and the repository verify command; then the product engineer prunes memory to current truth, writes one memory log entry and generates the catalog. No implementation or approval has occurred while this PLAN is Draft.
