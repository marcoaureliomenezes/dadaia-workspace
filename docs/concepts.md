# Concepts

Seven terms, one section each. The canonical sense of every term used across this
repository is defined once in [`CONTEXT.md`](../CONTEXT.md); the law that binds them
is `dadaia_workspace/public/data/AGENTS.md`, and the walkthrough is
[getting started](getting-started.md).

## Context

<!-- derived-from: spec-context-project sha256:9690f09f679b -->
<!-- derived-from: context-management sha256:e084ff04890d -->

A *context* — a Spec Context Project — is one canonical `specs/` tree owned by one
main repository, the unit for memory, backlog, bugs, releases, reports and handoffs.
A product spanning several repositories is still one context: its associated
repositories own production source only and live and die with it. The **main repo** is
the repo where `specs/` lives and the only specs, bind, memory, release and backlog
target; an associated repo's own `specs/` is never read. The registry holds each
context ALIVE or DEAD, and a repo slug belongs to one context.

One resolution per call answers workspace root, session, context, repo slug, specs dir
and the session's `Bind`: rung 0 is caller-supplied (`--context`, or a write target
`scope()` maps to a repo), rung 1 `DADAIA_CONTEXT`, rung 2 this session's record, rung 3
the repo containing the cwd. The `Bind` — the named context plus every repo slug it
owns — is read from the session's own record when it has an id, else `DADAIA_CONTEXT`,
never the cwd, so an unbound session owns nothing. A bind is also what triggers
memory injection into the session.

## Release and candidate

<!-- derived-from: release-lifecycle sha256:7b50f03ee3e9 -->

Exactly one *release* is live, `specs/releases/<M.m.p>/`, with open scope; it grows by
*candidates*, each a closed-scope cycle whose `SPEC.md`, `PLAN.md` and job files `tasks/<job>.md` sit
in `rc-<N>/`, the live one being the highest; only `_RELEASE.json` sits at the release root. `_RELEASE.json` is the one mutable state document: `phase` is
`DEFINITION`, `IMPLEMENTATION` or `CLOSURE`, the `phase` verbs stamp the `defined` and
`implemented` milestones, `ship` records the merged promote PR and archives the release folder, and `log` is the append-only closure narrative.
Every SPEC's first `**Origin:**` line is `operator-demand` or
`backlog:<ids>; bugs:<ids>; findings:<ids>`, each kind at most once; `release.py check` judges it. Release ids are bare SemVer; the live version
moves only at an operator-approved deploy.

## The flow

<!-- derived-from: release-lifecycle sha256:7b50f03ee3e9 -->
<!-- derived-from: bug-ledger sha256:a3df43b6e94e -->
<!-- derived-from: audits-canon sha256:611e3746cfd5 -->

Every demand takes one of two arms. **Arm A**, a feature, leaves through a candidate:
the picked backlog and bug set, the as-is review (one As-is verdict — DELETE, REBUILD,
UPDATE, KEEP, then ADD — per touched unit, landing as PLAN §1), the mandatory grill, the
SPEC with its `Replaces`, a PLAN drawing the DAG of jobs, one job file per job; jobs of stages of parallel tasks, each task in its own
worktree, each job reviewed once; then the Reconciliation job — memory reconciliation, the closure `log`
entries, the disposition sweep (`backlog.py exit`, `audit.py disposition`/`close`,
`bugs.py archive`), artifact GC — the work -> integration merge (the constitution's `gitflow:`) and the operator's
promote-or-continue choice. **Arm B**, a bug, is registered after the operator confirms it; a block-list bug is a hotfix job,
any other is fixed in the candidate's bug batch, before its Reconciliation job: lineage, a RED new case (a fix never rewrites an old assert), root-cause fix,
GREEN, `resolve` with its red loop, one commit; a fix-induced bug is rebuilt, not
patched again. No engine drives either arm: the documents
carry the ordered work, and the ledger scripts move the records.

## The gate

<!-- derived-from: sdd-gate-v3 sha256:11e94d99c0d1 -->

The *gate* is one PreToolUse pre-gate evaluating root whitelist, venv guard and SDD
gate in that order — first block wins. What it blocks, its path classes and every
fail-open path are stated once, in the root `AGENTS.md` §3. No lease, lock or wait path exists and
no `_RELEASE.json` is read. Every BLOCK, here and at every other enforcement point,
carries exactly one `fix:` line, and a contract test feeds each fix back through the
gate — a refusal whose fix is itself refused (a Stall) cannot ship.

## Memory

<!-- derived-from: context-management sha256:e084ff04890d -->
<!-- derived-from: workspace-doctor sha256:84a9bec9fec9 -->
<!-- derived-from: release-lifecycle sha256:7b50f03ee3e9 -->
<!-- derived-from: audits-canon sha256:611e3746cfd5 -->

*Memory* is current product truth: the atoms under `specs/memory/product/**`, plus
`ARCHITECTURE.md` (its `## Tech Stack` section included) and `QUALITY.md`, whose
canonical statements change only in the commit carrying an accepted decision; a
non-principle section may take a truth-only correction whose commit names its code evidence. A bound
session receives its onboarding next step while one remains, `constitution.md`, the Tech Stack
section, the catalog digest (`slug`, `title`, `tldr`, `path` per atom) and its open worktrees. At each candidate's closure, `memory.py drift` lists the
atoms whose sources changed, each is reconciled — delete, update, then add — and
`release.py check` (`LEDGER-RELEASE-SCHEMA`) keeps the release red until the reconciliation is logged.
`.dadaia/.venv/bin/dadaia doctor`'s `ledgers` section runs `LEDGER-MEMORY-SCHEMA` (the generated pair equals the atom
files); its `specs` section runs `LINT-1` (frontmatter, headings, wikilinks, `sources` globs, history lines) and
the warnings `MEM-DRIFT-1` (features package map vs the live tree) and `MEM-DRIFT-2`
(a cited verb or path that does not exist).

## Bugs and backlog

<!-- derived-from: bug-ledger sha256:a3df43b6e94e -->
<!-- derived-from: backlog-ledger sha256:44b145a6a3aa -->

Both are records with one shape and one writer script. `specs/bugs/BUGS.jsonl` holds
one record per bug, appended once and keyed by `id`, carrying no git-derived fact;
`status` is `open | resolved | superseded | deferred | rejected`, a terminal status is
reached only through its transition, and registration is ask-first: the agent proposes
and `bugs.py append` runs only after the operator confirms. `specs/backlog/BACKLOG.json`'s
`active[]` is the operator's demand queue: an entry is born `idea` by `backlog.py new`,
is picked by the `backlog:` clause of a SPEC's first `**Origin:**` line, and exits exactly once by `backlog.py exit`, which
appends one histo record carrying the removed entry: a picked entry at the closure
disposition sweep, a `to-bug` exit with the bug's registration, its reason the bug id. One terminal vocabulary serves
every histo: `delivered resolved superseded deferred rejected to-bug`.

## Audits

<!-- derived-from: audits-canon sha256:611e3746cfd5 -->

An *audit* is the only full-tree inspection lane, every other quality boundary being
diff-scoped: a committed folder `specs/audits/<YYYYMMDD>-<slug>/` holding `AUDIT.md` —
scope, the `[from-sha, HEAD]` window, method per pillar, the eight forensic metrics,
summary — and `FINDINGS.jsonl`. Three pillars always run together over the window
since the newest archived audit: bug history, spec compliance and memory drift. One
audit is suggested every five releases, never mandatory, and generates at most one
remediation release (a zero-finding audit closes with none): `audit.py disposition` rewrites a finding's disposition, release
and reason in place, and `audit.py close` refuses while any finding is undispositioned,
appends the one `audits_histo.jsonl` record and deletes the folder.
