# Getting started

From a bare machine to a first candidate. Every step names what it creates on disk;
the terms are defined in [concepts](concepts.md) and in [`CONTEXT.md`](../CONTEXT.md).

## Install

<!-- derived-from: pypi-distribution sha256:1b31683b6fb3 -->
<!-- derived-from: workspace-init sha256:4f0ceaccc6c8 -->

```bash
uvx dadaia-workspace init <dir> --harness claude --repo <url>
```

Onboarding has three levels — workspace, project, specs — and the first two are this
one line (needs uv; `pip install dadaia-workspace` into any venv gives the same `init`,
under two console-script names, `dadaia` and `dadaia-workspace`). The wheel ships
`dadaia_workspace/` with the full public asset tree; `init` resolves the workspace
venv's dependencies from PyPI, so it needs network access. From then on every command
runs through the workspace's own CLI, `.dadaia/.venv/bin/dadaia`, which `init` prints
by its absolute path.

**Upgrade:** re-run the same `uvx dadaia-workspace init <dir> --harness <name>` line;
it prints `upgraded A -> B`, or `already at A` when the workspace is current. The upgrade
never writes a project repo: `.dadaia/.venv/bin/dadaia specs init --context <ctx>` then
refreshes each project's specs law.

## Level 1 — the workspace

<!-- derived-from: workspace-init sha256:4f0ceaccc6c8 -->

`uvx dadaia-workspace init <dir> --harness claude|codex|kimi-code|cursor|devin|copilot
[--repo <url>] [--associated-repo <url>]… [--skip-assets]` is the only verb that works
on an empty directory. `<dir>` is created if absent, refused with one `fix:` line if it
holds a foreign tree, never resolved from the cwd; every `fix:` line repeats the
invocation's `--repo` and `--associated-repo` flags. It lays down:

- `.dadaia/.venv`, every `.dadaia/` zone whose creator is init or install, and
  `.agents/skills`; the harness's own directory comes from its projection. The tree is
  a view of `dadaia_workspace/core/workspace_layout.py`.
- `.dadaia/states/spec_contexts.json` and `.dadaia/states/server_registry.json` as
  empty documents, never overwriting existing data, and
  `.dadaia/states/harness_profile.json`, the harness roster; a re-init with another
  harness merges into it, never narrowing it.
- An absent root `.dadaiaignore`, seeded from the legacy
  `states/instance_exceptions.txt` or a comment-only template, and an absent `prompt.md`,
  empty; each is the operator's file from then on.
- Unless `--skip-assets`, the staged and installed public assets — the one writer of
  every hook wiring. With `--skip-assets` the output warns that the workspace is
  ungated until `.dadaia/.venv/bin/dadaia public install` runs.

`init` deletes no projection; `.dadaia/.venv/bin/dadaia harness add <name>` adds a
harness later and `.dadaia/.venv/bin/dadaia harness list` reads the roster.

## Level 2 — the project

<!-- derived-from: spec-context-project sha256:9690f09f679b -->
<!-- derived-from: context-management sha256:2d908837d9f6 -->

A context — a Spec Context Project — is the unit of work: one canonical `specs/` tree
owned by one main repository, optionally spanning associated repositories that live and
die with it. Specs, bind, memory, releases and backlog resolve only from the main repo.
`init --repo <url>` creates the first one; every later one is one step:

```bash
.dadaia/.venv/bin/dadaia context create --main-repo <url> [--associated-repo <url>]
.dadaia/.venv/bin/dadaia context show <ctx> --json   # the repo set
```

`context create` clones (or adopts) every repo, installs the pre-push hook and makes
the context ALIVE — it never binds; on failure nothing is left behind. The name
defaults to the main repo's slug. `bind` writes exactly one record,
`.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`), and acquires
nothing; the session id comes from the environment only, and a session without a
harness-native id exports `DADAIA_SESSION_ID` before it binds. The bind's scope
is the context's main repo plus its associated repos; a MUTATING file-tool write into a
repo outside it is refused with the bind that would allow it, and agents write a repo
only inside its worktrees. After a bind, the ctx-inject hook injects the context header,
`constitution.md`, `ARCHITECTURE.md`'s `## Tech Stack` section, the memory catalog digest
and the open worktrees once.

## Level 3 — the specs

<!-- derived-from: spec-context-project sha256:9690f09f679b -->

```bash
.dadaia/.venv/bin/dadaia specs init --context <ctx> [--replace-foreign]
```

`specs init` (3a) brings the main repo's `specs/` to the canon and never commits: an
absent tree is scaffolded, a dadaia tree is upgraded and its missing files filled, and a
foreign `specs/` is moved to `specs-bkp/` (`git mv`, staged) after consent —
`--replace-foreign` gives it without asking. The `dd-audit-project` first pass (3b) fills
memory and is done when memory holds real content (`.dadaia/.venv/bin/dadaia doctor --context <ctx>` exit 0), never by a
stamp. `context baseline <ctx>` (3c) publishes the principal, integration and work
branches; a re-run is a no-op.

## Check compliance — `doctor`

<!-- derived-from: workspace-doctor sha256:8b2f7d91f08a -->

```bash
.dadaia/.venv/bin/dadaia doctor --context <ctx> [--json] [--fix] [--redact]
```

`doctor` is the one instance validator, and three sections run in fixed order:
`workspace` (the root, the harness dirs, the `.dadaia/` zones, every ALIVE repo tree —
only the scoped context's when the run is scoped — the installed git hook), `specs` (the rules over one `specs/` tree) and `ledgers` (the
backlog document, the ADR ledger and the ledger scripts' own `check`).

The `specs` and `ledgers` tree resolves from `--context`, `--specs-dir` or the bound
context; with none, those sections are empty and `workspace` still runs. With no
instance around — CI over a checkout — `.dadaia/.venv/bin/dadaia doctor --specs-dir specs`
runs the two tree sections; any other run outside a workspace exits 1 with the one
workspace-not-found error.

Every printed finding is one `<CODE> <verdict> <message>` line, every error-class
finding carries one fix line (a command, or
`Operator action: <one act>`), and any error-class finding exits 1. There
is no score: the findings and the exit code are the run. `--json` mirrors it,
`--redact` masks every foreign context name and repo slug, and `--fix` is the reaper —
it moves slop to `.dadaia/reaped/<YYYYMMDD>/` under a 7-day hold; a TTL expiry acts by
zone class, an OUTPUT entry held, an EPHEMERAL one deleted.

## Run the first candidate

<!-- derived-from: release-lifecycle sha256:f91b7bdd7b3c -->
<!-- derived-from: backlog-ledger sha256:0e13883cee01 -->
<!-- derived-from: bug-ledger sha256:03704577cc85 -->

A candidate is one closed-scope cycle inside the live release. Nothing drives it: the
documents are the state, the ledger scripts move the records, and the job files and
task commits are the trace.

After `context baseline`, each step writes inside a worktree that then merges: a
`backlog/<slug>` one for step 1, the candidate's `define` one for steps 2 and 3, a job's
or a task's from step 5.

1. **Demand enters the backlog.** Only the operator creates demand;
   `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new <slug> --relates <slugs>|none`
   appends one `active[]` entry born `idea`, and every later status binds `intents[]` that resolve to a code, catalog, doc or invariant anchor.
2. **Birth the release.**
   `python3 .agents/skills/dd-release-implementation/scripts/release.py new <M.m.p>`
   writes a `SPEC.md` stub in `specs/releases/<M.m.p>/rc-<N>/` and `_RELEASE.json` in
   `DEFINITION` at the release root, all or nothing, refusing a second live release.
3. **Define the candidate.** The picked set; the as-is review — one row per unit the
   set touches, `unit | today | bugs | verdict | why`, the As-is verdict DELETE,
   REBUILD, UPDATE or KEEP, then ADD only for what no unit can carry; the mandatory
   grill; then `SPEC.md` (its `Replaces` naming what DELETE/REBUILD rows remove),
   `PLAN.md` (opening with that table as §1, then the DAG of jobs and the hot files) and
   one job file per job, `tasks/<job>.md`, in that `rc-<N>/`, in one
   definition commit on the work branch (`<work>M.m.p`; the names are the
   `gitflow:` block of `specs/constitution.md`).
4. **Open implementation.** `release.py phase IMPLEMENTATION --sha <sha>` requires
   `SPEC.md` and `PLAN.md` `**Status:** Approved`, PLAN's `## DAG` and `### Hot files`
   sections and well-formed job files, and stamps `defined`.
5. **Run the jobs.** Each job opens its worktree by `worktree.py new`; each stage's
   tasks run in parallel task worktrees, stage 1 writing every acceptance test RED;
   a task lands on its job branch by `worktree.py merge` after its task gate, a stage
   closes by `worktree.py stage`, and the job lands on the work branch after its CI
   run and the reviewer's one `APPROVED`.
6. **Close the candidate.** The Reconciliation job, in its `reconcile` worktree:
   `release.py phase CLOSURE --sha <sha>` (no other open `wt/*` worktree), memory
   reconciliation with its derived docs, the closure `log` entries, the disposition
   sweep (`backlog.py exit`, `audit.py disposition`/`close`, `bugs.py archive`),
   artifact GC; then the work -> integration PR merged green.
7. **Continue or promote.** Continue: `release.py new` with the same id stacks the next
   candidate, reopening `DEFINITION`. Promote: merge the integration branch into the
   principal by PR — that merge is the deploy; `release.py ship --sha <sha> --pr <n>`
   then records the merged promote PR and moves the release folder to `_archive/`.

A bug is registered once the operator confirms it; a block-list bug is fixed at once as
a hotfix job — lineage, a RED new case, root-cause fix, GREEN, `resolve` with its red
loop, one commit — and any other by the next candidate's Job 1.
