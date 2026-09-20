# Concepts

Seven terms, one paragraph each. The canonical sense of every term used across this
repository is defined once in [`CONTEXT.md`](../CONTEXT.md); the law that binds them
is `dadaia_workspace/public/data/AGENTS.md`, and the walkthrough is
[getting started](getting-started.md).

## Context

<!-- derived-from: spec-context-project sha256:b39739176d42 -->
<!-- derived-from: context-management sha256:9166a06fab52 -->

A *context* — a Spec Context Project — is one canonical `specs/` tree owned by one
main repository, the unit for memory, backlog, bugs, releases, reports and handoffs.
A product spanning several repositories is still one context: it may carry associated
repositories, which live and die with it and own production source only. The registry
holds each context ALIVE or DEAD; `dadaia context bind` writes one session record and
resolution answers workspace root, session, context, repo slug, specs dir and the
session's scope in one call, from `DADAIA_CONTEXT`, then this session's record, then
the repo containing the cwd — never from the cwd alone, so sitting inside a repository
is not a binding. The vocabulary is the paradigm's: the **main repo** is the repo where
`specs/` lives, the **associated repos** are the others the context owns; the surface is
frozen — no new context verb, no new state file, no new session field — and a
single-repo context is the degenerate case of multi-repo.

## Release and candidate

<!-- derived-from: sdd-bug-backlog-governance sha256:5268cc21ea84 -->

Exactly one *release* is live at a time, named last-published-PyPI + 1 patch, with
OPEN scope; it grows by *candidates*, each a closed-scope SDD cycle whose SPEC, PLAN
and TASKS sit flat at the release root while `rc-N/` folders hold the archived trios
of completed candidates. `_RELEASE.json` is the state document: `phase` is one of
`DEFINITION`, `IMPLEMENTATION`, `CLOSURE`, `ARCHIVED`, the three milestones
(`defined`, `implemented`, `shipped`) move only by verb, and `log` is the one
append-only narrative array. The version increments only at an operator-approved
deploy.

## The flow

<!-- derived-from: sdd-bug-backlog-governance sha256:5268cc21ea84 -->
<!-- derived-from: audits-canon sha256:c97a3c4e65b1 -->

Every demand takes one of two arms. **Arm A**, a feature, enters through the backlog
and leaves through a candidate: operator demand, curation into `active[]`, a picked
entry, the approved trio, one reserved task at a time, the closure sweep that exits
the entry with a disposition. **Arm B**, a bug, is fixed on the spot on the live
feature branch — register, root-cause, RED test, fix, GREEN, `resolved` with evidence,
one commit — with no SPEC, PLAN, TASKS, pick line or release directory, in any phase.
There is no workflow engine on either arm: the documents carry the ordered work, and
the verbs move the records.

## The gate

<!-- derived-from: sdd-gate-v3 sha256:a3fcecc38fa6 -->

The *gate* is a PreToolUse chain of three policies evaluated in fixed order — root
whitelist, venv guard, SDD gate — first block wins, and a policy that raises is ALLOW.
It blocks exactly three things: a new workspace-root entry, a leading `dadaia`, `pip`
or `python -m dadaia_workspace` token run outside the workspace virtualenv, and a
PROTECTED write or a bound session's write under a repository outside its scope.
Paths fall in three classes, no fourth: ADDITIVE (always writable), MUTATING
(everything else, scope-judged) and PROTECTED (session records and the projected
`AGENTS.md` set, fail-closed). No lease, mutex or wait path exists
and no phase is ever consulted. Every refusal, here and at every other enforcement
point, carries exactly one `fix:` line naming one runnable command — a refusal whose
fix is itself refused (a Stall) is unrepresentable, and a contract test proves it by
feeding each fix back through the gate.

## Memory

<!-- derived-from: context-management sha256:9166a06fab52 -->
<!-- derived-from: workspace-doctor sha256:f17e827caadc -->

*Memory* is current product truth, never history: one Markdown atom per subject under
`specs/memory/product/**`, plus `ARCHITECTURE.md`, `QUALITY.md` and `TECHSTACK.md`,
each of the three split into an ADR-gated Part 1 of principles (every one carrying a
`Measured by:` command) and a Part 2 of implementation. Frontmatter carries five
fields (`slug`, `title`, `tldr`, `summary`, `tags`), the catalog persists ten keys per
atom, and the digest injected at bind keeps exactly `slug`, `title`, `tldr` and `path`
— `summary` stays behind. `dadaia doctor`'s `specs` section polices it: atoms present
and Markdown, catalog slugs equal to the atom files, frontmatter and wikilinks linted,
and memory drift — the features package map against the live tree, a `dadaia <verb>`
or path an atom cites that no longer exists — reported as a warning, never a red build.

## Bugs and backlog

<!-- derived-from: sdd-bug-backlog-governance sha256:5268cc21ea84 -->

Both are records with one shape and one owning verb. `specs/bugs/BUGS.jsonl` holds one
record per bug, appended once and keyed by `id`, with no git-derived cache — git is the
only authority for git facts; `status` is `open | resolved | superseded | deferred |
rejected`, a terminal status is reachable only through a transition carrying its
evidence, and registration is ask-first: the agent proposes and `dadaia bugs append`
runs only after the operator confirms. `specs/backlog/BACKLOG.json`'s `active[]` is the
operator's demand queue, curated by `project-manager` and exited exactly once by
`dadaia backlog exit`, which appends one histo record carrying the removed entry.

## Audits

<!-- derived-from: audits-canon sha256:c97a3c4e65b1 -->

An *audit* is the only full-tree inspection lane, every other quality boundary being
diff-scoped, and it is a committed spec artifact rather than a report: a folder under
`specs/audits/` holding `AUDIT.md` — scope, the `[from-sha, to-sha]` window, method
per pillar, metrics as `baseline → measured`, score and summary — and `FINDINGS.jsonl`,
one appended record per finding. Three pillars always run together over the window
since the newest archived audit: bug history, spec compliance and memory drift. One
audit is suggested every five releases, never mandatory, and generates exactly one
remediation release: `dadaia audit disposition` rewrites a finding's disposition,
release and reason in place, and `dadaia audit close` refuses while any finding is
`open`, appends the one `audits_histo.jsonl` record and deletes the directory.
