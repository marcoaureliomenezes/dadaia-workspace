# Concepts

Seven terms, one section each. The canonical sense of every term used across this
repository is defined once in [`CONTEXT.md`](../CONTEXT.md); the law that binds them
is `dadaia_workspace/public/data/AGENTS.md`, and the walkthrough is
[getting started](getting-started.md).

## Context

<!-- derived-from: spec-context-project sha256:4984ba691799 -->
<!-- derived-from: context-management sha256:3f48eef447f1 -->

A *context* — a Spec Context Project — is one canonical `specs/` tree owned by one
main repository, the unit for memory, backlog, bugs, releases, reports and handoffs.
A product spanning several repositories is still one context: its associated
repositories own production source only and live and die with it. The **main repo** is
the repo where `specs/` lives and the only specs, bind, memory, release and backlog
target; an associated repo's own `specs/` is never read. The registry holds each
context ALIVE or DEAD, and a repo slug belongs to one context.

One resolution per call answers workspace root, session, context, repo slug, specs dir
and the session's `Bind`: rung 0 is caller-supplied (`--context`, or a write target
under `repos/<slug>/`), rung 1 `DADAIA_CONTEXT`, rung 2 this session's record, rung 3
the repo containing the cwd. The `Bind` — the named context plus every repo slug it
owns — is read from `DADAIA_CONTEXT` then the session record, never the cwd, so an
unbound session owns nothing and is never scope-judged. A bind is also what triggers
memory injection into the session.

## Release and candidate

<!-- derived-from: release-lifecycle sha256:ebb8441fde08 -->

Exactly one *release* is live, `specs/releases/<M.m.p>/`, with open scope; it grows by
*candidates*, each a closed-scope cycle whose `SPEC.md`, `PLAN.md` and `TASKS.md` sit
flat at the release root and are replaced by the next candidate's, the closed trio
staying in git. `_RELEASE.json` is the one mutable state document: `phase` is
`DEFINITION`, `IMPLEMENTATION`, `CLOSURE` or `ARCHIVED`, the `phase` verbs stamp the
`defined` and `implemented` milestones, and `log` is the append-only closure narrative.
Every SPEC carries an `**Origin:**` line. Release ids are bare SemVer; the live version
is the last published one plus one patch and moves only at an operator-approved deploy.

## The flow

<!-- derived-from: release-lifecycle sha256:ebb8441fde08 -->
<!-- derived-from: bug-ledger sha256:eeebe84481a4 -->
<!-- derived-from: audits-canon sha256:20bf48c21012 -->

Every demand takes one of two arms. **Arm A**, a feature, leaves through a candidate:
the picked backlog and bug set, the as-is review (one As-is verdict — DELETE, REBUILD,
UPDATE, KEEP, then ADD — per touched unit, landing as PLAN §1), the mandatory grill, the
SPEC with its `Replaces`, PLAN and TASKS, one reserved task at a time, then closure — memory reconciliation, the closure `log`
entries, the disposition sweep (`backlog.py exit`, `audit.py disposition`/`close`,
`bugs.py archive`), artifact GC, the work -> integration merge (the constitution's `gitflow:`) and the operator's
promote-or-continue choice. **Arm B**, a bug, is fixed on the live work branch in
any phase with no SPEC, PLAN or TASKS: register, lineage, RED test, root-cause fix,
GREEN, `resolve` with evidence, one commit; a unit fixed twice before is rebuilt, not
patched a third time. No engine drives either arm: the documents
carry the ordered work, and the ledger scripts move the records.

## The gate

<!-- derived-from: sdd-gate-v3 sha256:7a6e11d84264 -->

The *gate* is one PreToolUse pre-gate evaluating root whitelist, venv guard and SDD
gate in that order — first block wins, and a policy that raises is ALLOW. It blocks
exactly three things: a new workspace-root entry outside the root law and
`.dadaia/states/instance_exceptions.txt`; a leading `dadaia`, `pip` or
`python -m dadaia_workspace` outside `.dadaia/.venv/bin/`; a PROTECTED write, or a
bound session's MUTATING write into a `repos/<slug>/` outside its scope. Paths fall in
three classes: ADDITIVE (`specs/bugs/`, `specs/backlog/`, `specs/audits/` and the
`.dadaia/` scratch zones, always writable), PROTECTED (`.dadaia/sessions/` and the
projected law) and MUTATING (everything else). No lease, lock or wait path exists and
no `_RELEASE.json` is read. Every BLOCK, here and at every other enforcement point,
carries exactly one `fix:` line, and a contract test feeds each fix back through the
gate — a refusal whose fix is itself refused (a Stall) cannot ship.

## Memory

<!-- derived-from: context-management sha256:3f48eef447f1 -->
<!-- derived-from: workspace-doctor sha256:3fa0c321c7b0 -->
<!-- derived-from: release-lifecycle sha256:ebb8441fde08 -->
<!-- derived-from: audits-canon sha256:20bf48c21012 -->

*Memory* is current product truth: the atoms under `specs/memory/product/**`, plus
`ARCHITECTURE.md` (its `## Tech Stack` section included) and `QUALITY.md`, whose
canonical statements change only in the commit carrying an accepted decision. A bound
session receives its onboarding next step while one remains, the Tech Stack section and
the catalog digest (`slug`, `title`, `tldr`, `path` per atom). At each candidate's closure, `memory.py drift` lists the
atoms whose sources changed, each is reconciled — delete, update, then add — and
`RELEASE-TREE-MEMORY` keeps the release red until the reconciliation is logged.
`.dadaia/.venv/bin/dadaia doctor`'s `specs` section polices the tree: `CAT-1` (catalog equals atom
files), `LINT-1` (frontmatter, headings, wikilinks, `sources` globs, history lines) and
the warnings `MEM-DRIFT-1` (features package map vs the live tree) and `MEM-DRIFT-2`
(a cited verb or path that does not exist).

## Bugs and backlog

<!-- derived-from: bug-ledger sha256:eeebe84481a4 -->
<!-- derived-from: backlog-ledger sha256:46382434daf2 -->

Both are records with one shape and one writer script. `specs/bugs/BUGS.jsonl` holds
one record per bug, appended once and keyed by `id`, carrying no git-derived fact;
`status` is `open | resolved | superseded | deferred | rejected`, a terminal status is
reached only through its transition, and registration is ask-first: the agent proposes
and `bugs.py append` runs only after the operator confirms. `specs/backlog/BACKLOG.json`'s
`active[]` is the operator's demand queue: an entry is born `idea` by `backlog.py new`,
moves through `candidate` and `picked`, and exits exactly once, at the closure
disposition sweep, by `backlog.py exit`, which appends one histo record carrying the
removed entry. One terminal vocabulary serves every histo: `delivered resolved
superseded deferred rejected`.

## Audits

<!-- derived-from: audits-canon sha256:20bf48c21012 -->

An *audit* is the only full-tree inspection lane, every other quality boundary being
diff-scoped: a committed folder `specs/audits/<YYYYMMDD>-<slug>/` holding `AUDIT.md` —
scope, the `[from-sha, HEAD]` window, method per pillar, the eight forensic metrics,
summary — and `FINDINGS.jsonl`. Three pillars always run together over the window
since the newest archived audit: bug history, spec compliance and memory drift. One
audit is suggested every five releases, never mandatory, and generates at most one
remediation release (a zero-finding audit closes with none): `audit.py disposition` rewrites a finding's disposition, release
and reason in place, and `audit.py close` refuses while any finding is undispositioned,
appends the one `audits_histo.jsonl` record and deletes the folder.
