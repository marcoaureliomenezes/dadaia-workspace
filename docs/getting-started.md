# Getting started

From a bare machine to a first candidate. Every step names what it creates on disk;
the terms are defined in [concepts](concepts.md) and in [`CONTEXT.md`](../CONTEXT.md).

## Install

<!-- derived-from: pypi-distribution sha256:ab76c52ed560 -->
<!-- derived-from: workspace-init sha256:0c2017836e6f -->

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
it prints `upgraded A -> B`, or `already at A` when the workspace is current.

## Level 1 — the workspace

<!-- derived-from: workspace-init sha256:0c2017836e6f -->

`uvx dadaia-workspace init <dir> --harness claude|codex|kimi-code|cursor|devin|copilot
[--repo <url>] [--associated-repo <url>]… [--skip-assets]` is the only verb that works
on an empty directory. `<dir>` is created if absent, refused with one `fix:` line if it
holds a foreign tree, never resolved from the cwd. It lays down:

- `.dadaia/.venv`, every `.dadaia/` zone whose creator is init or install, and
  `.agents/skills`; the harness's own directory comes from its projection. The tree is
  a view of `dadaia_workspace/core/workspace_layout.py`.
- `.dadaia/states/spec_contexts.json` and `.dadaia/states/server_registry.json` as
  empty documents, never overwriting existing data, and
  `.dadaia/states/harness_profile.json`, the harness roster; a re-init with another
  harness merges into it, never narrowing it.
- Unless `--skip-assets`, the staged and installed public assets — the one writer of
  every hook wiring. With `--skip-assets` the output warns that the workspace is
  ungated until `.dadaia/.venv/bin/dadaia public install` runs.

`init` deletes no projection; `.dadaia/.venv/bin/dadaia harness add <name>` adds a
harness later and `.dadaia/.venv/bin/dadaia harness list` reads the roster.

## Level 2 — the project

<!-- derived-from: spec-context-project sha256:4984ba691799 -->
<!-- derived-from: context-management sha256:d40d5eeb1115 -->

A context — a Spec Context Project — is the unit of work: one canonical `specs/` tree
owned by one main repository, optionally spanning associated repositories that live and
die with it. Specs, bind, memory, releases and backlog resolve only from the main repo.
`init --repo <url>` creates the first one; every later one is one step:

```bash
.dadaia/.venv/bin/dadaia context create --main-repo <url> [--associated-repo <url>]
.dadaia/.venv/bin/dadaia context show <ctx> --json   # the repo set
```

`context create` clones (or adopts) every repo, installs the pre-push hook, makes the
context ALIVE and binds this session; on failure nothing is left behind. The name
defaults to the main repo's slug. `bind` writes exactly one record,
`.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`), and acquires
nothing; `.dadaia/.venv/bin/dadaia context bind <ctx> --print-env` emits
`DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for an `eval $(…)` shell, and a session
without a harness-native id carries the binding in `DADAIA_CONTEXT`. The bind's scope
is the context's main repo plus its associated repos; a bound session's MUTATING write
into a repo another context owns is refused with the bind that would allow it. After a
bind, the ctx-inject hook injects the context header, `ARCHITECTURE.md`'s
`## Tech Stack` section and the memory catalog digest once.

## Level 3 — the specs

<!-- derived-from: spec-context-project sha256:4984ba691799 -->

```bash
.dadaia/.venv/bin/dadaia specs init --context <ctx> [--replace-foreign]
```

`specs init` brings the main repo's `specs/` to the canon and never commits: an absent
tree is scaffolded, a dadaia tree is upgraded and its missing files filled, and a
foreign `specs/` is moved to `specs-bkp/` (`git mv`, staged) after consent —
`--replace-foreign` gives it without asking.

## Check compliance — `doctor`

<!-- derived-from: workspace-doctor sha256:6af42080bf04 -->

```bash
.dadaia/.venv/bin/dadaia doctor --context <ctx> [--json] [--fix] [--redact]
```

`doctor` is the one instance validator, and three sections run in fixed order:
`workspace` (the root, the harness dirs, the `.dadaia/` zones, every ALIVE repo tree,
the installed git hook), `specs` (the rules over one `specs/` tree) and `ledgers` (the
backlog document, the ADR ledger and the ledger scripts' own `check`).

The `specs` and `ledgers` tree resolves from `--context`, `--specs-dir` or the bound
context; with none, those sections are empty and `workspace` still runs. With no
instance around — CI over a checkout — `.dadaia/.venv/bin/dadaia doctor --specs-dir specs --source-root .`
runs the two tree sections.

Every printed finding is one `<CODE> <verdict> <message>` line, every error-class
finding carries one `fix: <command>` line, and any error-class finding exits 1. There
is no score: the findings and the exit code are the run. `--json` mirrors it,
`--redact` masks every foreign context name and repo slug, and `--fix` is the reaper —
it moves slop to `.dadaia/reaped/<YYYYMMDD>/` under a 7-day hold and deletes only what
a TTL expired.

## Run the first candidate

<!-- derived-from: release-lifecycle sha256:1151a261d24f -->
<!-- derived-from: backlog-ledger sha256:46382434daf2 -->
<!-- derived-from: bug-ledger sha256:9534ded07707 -->

A candidate is one closed-scope cycle inside the live release. Nothing drives it: the
documents are the state, the ledger scripts move the records, and the markers in
`TASKS.md` are the trace.

1. **Demand enters the backlog.** Only the operator creates demand;
   `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new <slug>` appends
   one `active[]` entry born `idea`, and every later status (`candidate`, `picked`)
   binds `intents[]` that resolve to a code, doc or CLI anchor.
2. **Birth the release.**
   `python3 .agents/skills/dd-release-implementation/scripts/release.py new <M.m.p>`
   writes a `SPEC.md` stub and `_RELEASE.json` in `DEFINITION` under
   `specs/releases/<M.m.p>/`, all or nothing, refusing a second live release.
3. **Define the candidate.** The picked set, the mandatory grill, then `SPEC.md`,
   `PLAN.md` and `TASKS.md` at the release root, in one definition commit on
   `feature/<M.m.p>`.
4. **Open implementation.** `release.py phase IMPLEMENTATION --sha <sha>` requires all
   three files `**Status:** Approved` and stamps `defined`.
5. **Implement one task at a time.** Reserve it `[-]` in its own commit, work
   test-first, run the local CI preflight, and mark `[x]` only after the reviewer's
   `APPROVED` on the same commit.
6. **Close the candidate.** `release.py phase CLOSURE --sha <sha>` requires no `[ ]`
   or `[-]` marker and stamps `implemented`. Then, in order: memory reconciliation, the
   closure `log` entries, the disposition sweep (`backlog.py exit`,
   `audit.py disposition`/`close`, `bugs.py archive`), artifact GC, and the
   `feature -> develop` PR merged green.
7. **Continue or promote.** Continue: `release.py new` with the same id stacks the next
   candidate, reopening `DEFINITION`. Promote: merge `develop` into `main`, then merge
   the release PR release-please opens there — it owns the version, the CHANGELOG
   section and the tag, and the publish jobs run on it.

A bug needs none of this: register, lineage, RED test, root-cause fix, GREEN, `resolve`
with evidence, one commit — on the live feature branch, in any phase.
