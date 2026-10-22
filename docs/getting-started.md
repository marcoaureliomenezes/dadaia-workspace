# Getting started

From a bare machine to a first candidate. Every step names what it creates on disk;
the terms are defined in [concepts](concepts.md) and in the glossary [`CONTEXT.md`](../CONTEXT.md), which defines terms only.

## Install

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
it prints `upgraded A -> B`, `repaired -> B` when the venv's build could not be read, or
`already at A` when the workspace is current. A venv whose python cannot start is refused
with a fix that deletes `.dadaia/.venv` and reruns the init line. The upgrade
never writes a project repo: `.dadaia/.venv/bin/dadaia specs init --context <ctx>` then
refreshes each project's specs law.

## Level 1 — the workspace

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

To move a workspace, `.dadaia/.venv/bin/dadaia export` writes
`.dadaia/dist/spec-contexts.json` (every context, its repo urls and the harness roster),
and `export --hard` writes `.dadaia/dist/workspace-export.tar.gz`, that JSON plus a
secret-scanned bundle of each open lane and `wt-rc` tree and each paused one; export only
reads the registry. `uvx dadaia-workspace init <dir> --from <artifact>` (never with
`--repo`) installs every harness the artifact names, registers its contexts DEAD, lists a
context with no remote as not replicated, places the bundles in `.dadaia/dist/` and prints
`context alive <ctx>` for each context that was ALIVE; then `worktree resume` restores each
bundled tree.

## Level 2 — the project

A context — a Spec Context Project — is the unit of work: one canonical `specs/` tree
owned by one main repository, optionally spanning associated repositories that live and
die with it. Specs, bind, memory, releases and backlog resolve only from the main repo.
`init --repo <url>` creates the first one; every later one is one step:

```bash
.dadaia/.venv/bin/dadaia context create --main-repo <url> [--associated-repo <url>]
.dadaia/.venv/bin/dadaia context show <ctx> --json   # the repo set
```

`context create` clones (or adopts) every repo, installs the pre-push and reference-transaction hooks and makes
the context ALIVE — it never binds; on failure nothing is left behind. The name
defaults to the main repo's slug. `bind` writes exactly one record,
`.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`, `bind_id`, `last_seen_at`), and acquires
nothing; the session id comes from the environment only, and a session without a
harness-native id exports `DADAIA_SESSION_ID` before it binds. The bind's scope
is the context's main repo plus its associated repos; a MUTATING file-tool write into a
repo outside it is refused with the bind that would allow it, unless the write lands in a
worktree git linked from a repo of this workspace, and agents write a repo only inside its
worktrees. After a bind, the ctx-inject hook injects the context header,
`constitution.md`, `ARCHITECTURE.md`'s `## Tech Stack` section, the memory catalog digest
and the open worktrees once.

## Level 3 — the specs

```bash
.dadaia/.venv/bin/dadaia specs init --context <ctx> [--replace-foreign]
```

`specs init` (3a) brings the main repo's `specs/` to the canon: an
absent tree is scaffolded, a dadaia tree is upgraded and its missing files filled, and a
foreign `specs/` is moved to `specs-bkp/` (`git mv`) after consent —
`--replace-foreign` gives it without asking. On a repo with no work branch it first cuts the
local one (from `origin/<work>`, else the integration branch) and commits only the scaffold (the move included) on it; it never pushes. The
`dd-audit-project` first pass (3b) fills memory in the `wt-backlog-first-pass` lane and is done when memory holds real content (`.dadaia/.venv/bin/dadaia doctor --context <ctx>` exit 0), never by a
stamp. `context baseline <ctx>` (3c) publishes the principal, integration and work
branches; a re-run is a no-op.

## Check compliance — `doctor`

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
finding carries one fix line (its forms are the root `AGENTS.md` map's *What is enforced*
section), and any error-class finding exits 1. There
is no score: the findings and the exit code are the run. `--json` mirrors it,
`--redact` masks every foreign context name and repo slug, and `--fix` is the reaper —
it moves slop to `.dadaia/reaped/<YYYYMMDD>/` under a 7-day hold; a TTL expiry acts by
zone class, an OUTPUT entry held, an EPHEMERAL one deleted.

## Run the first candidate

A candidate is one closed-scope cycle inside the live release. Nothing drives it: the
documents are the state, the ledger scripts move the records, and the job files and
task commits are the trace.

After `context baseline`, each step writes inside a worktree that then merges into its
parent, all under `worktrees/<repo>/<M.m.p>/`: a `wt-backlog-<slug>` lane for step 1;
the candidate's `rc-<N>/wt-rc`, its integration branch, for steps 2, 3, 4 and 6; a job's
`rc-<N>/job-<n>/wt-main` and its `wt-task-<kkk>` trees from step 5. `.dadaia/.venv/bin/dadaia worktree <verb>`
runs every worktree verb: `new`, `merge`, `sync`, `clean`, `hash`, `list`, `pause`, `resume`.

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
   `PLAN.md` (opening with that table as §1, then the job DAG with waves and exact `W:` sets) and
   one job file per job, `tasks/job<n>.md`, in that `rc-<N>/`, as the first commits of
   the `wt-rc`, cut from the work branch (`<work>M.m.p`; the names are the
   `gitflow:` block of `specs/constitution.md`).
4. **Open implementation.** `release.py phase IMPLEMENTATION` requires
   `SPEC.md` and `PLAN.md` `**Status:** Approved`, PLAN's `## DAG` with wave and exact
   `W:` sets, and lean job files containing task id, AC and exact `W:`, then stamps `defined`.
5. **Run the jobs.** Each job opens its `wt-main` by `.dadaia/.venv/bin/dadaia worktree new`
   once the `wt-rc` reads `IMPLEMENTATION`. Each behavior gets two task worktrees: the
   first commits its acceptance test RED; a fresh second task implements without
   touching a test path. Task merge into `wt-main` checks hygiene and that separation.
   Job merge into `wt-rc` runs the tracked `verify:` once and requires the reviewer's
   one `APPROVED`, bound to the exact diff. When a lane lands meanwhile,
   `.dadaia/.venv/bin/dadaia worktree sync <wt-rc path>` rebases the rc and its trees,
   parents first.
6. **Close the candidate.** The Reconciliation, as the last commits of the `wt-rc`:
   `release.py phase CLOSURE` (no `wt/*` tree or branch open but the `wt-rc`), the
   closure `log` entries, the disposition sweep (`backlog.py exit`, `audit.py
   disposition`/`close`, `bugs.py archive`), artifact GC, and last the memory
   reconciliation with its derived docs; after CLOSURE a hotfix lane still reaches it by
   `worktree sync`, in code only the `wt-rc` holds only a block-list bug lands, on the `wt-rc` itself, and any other work opens the next candidate. Then the `wt-rc` merges into the work branch through the job gate plus
   the ledger checks, and the work -> integration PR merges green.
7. **Continue or promote.** Continue: `release.py new` with the same id stacks the next
   candidate, reopening `DEFINITION`. Promote: merge the integration branch into the
   principal by PR — that merge is the deploy. The old work tip is tagged
   `archive/<work-branch>` and the work branch is renamed to the next release id
   (`git branch -m`, then `git push -u`), never cut anew; `release.py ship`,
   in a backlog lane on that branch, then records the promote and moves the release
   folder to `_archive/`.

A bug is registered once the operator confirms it; a bug in code the work branch holds is fixed in
a `wt-hotfix-<bug-id>` lane — lineage, a RED new case, root-cause fix, GREEN, then `resolve` with the
implementation sha. Any other bug becomes explicit candidate scope; ship refuses it while
open unless the operator authorizes that exact id and the authorization is recorded.
