# Getting started

From a bare machine to a first candidate. Every step names what it creates on disk;
the terms are defined in [concepts](concepts.md) and in [`CONTEXT.md`](../CONTEXT.md).

## Install

<!-- derived-from: pypi-distribution sha256:c627d9e5be4d -->
<!-- derived-from: workspace-init sha256:ca5c835e94af -->

```bash
python -m venv .venv && .venv/bin/pip install dadaia-workspace
```

`pip install dadaia-workspace` installs the library and one CLI under two
console-script names, `dadaia` and `dadaia-workspace`; `uvx dadaia-workspace init
<dir> --harness <name> --repo <url>` runs the next step without an install. The wheel
ships `dadaia_workspace/` with the full public asset tree, so the next step works
offline from a bare install. The workspace you create keeps its own virtualenv at
`.dadaia/.venv`, which `dadaia init` provisions.

## Provision the workspace — `dadaia init`

<!-- derived-from: workspace-init sha256:ca5c835e94af -->

```bash
dadaia init <dir> --harness claude|codex|kimi-code|cursor|devin|copilot [--repo <url>] [--skip-assets]
```

`init` is the only verb that works on an empty directory. `<dir>` is required —
created if absent, refused with one `fix:` line if it holds a foreign tree, never
resolved from the cwd — and a re-run is idempotent. It lays down:

- `.dadaia/.venv`, every `.dadaia/` zone whose creator is init or install, and
  `.agents/skills`; the harness's own directory comes from its projection. The tree is
  a view of `dadaia_workspace/core/workspace_layout.py`.
- `.dadaia/states/spec_contexts.json` and `.dadaia/states/server_registry.json` as
  empty documents, never overwriting existing data, and
  `.dadaia/states/harness_profile.json`, the harness roster; a re-init with another
  harness merges into it, never narrowing it.
- Unless `--skip-assets`, the staged and installed public assets — the one writer of
  every hook wiring. With `--skip-assets` the output warns that the workspace is
  ungated until `dadaia public install` runs.

With `--repo <url>`, `init` clones the repo into `repos/<slug>/` and composes the
context verbs — `create --main-repo <slug>`, `alive`, the session bind, printing the
`--print-env` line — then installs the pre-push hook. A re-run with the same URL reuses
the context, and a failed clone prints the same command as its `fix:`. Without
`--repo`, `init` closes with three lines: sessions launch at the root, the harness's
law-loading note, and the `dadaia context create <name> --main-repo <slug>` that makes
the first project. `init` deletes no projection; `dadaia harness add <name>` adds a
harness later and `dadaia harness list` reads the roster.

## Bind a context — `dadaia context bind`

<!-- derived-from: spec-context-project sha256:15dae861d543 -->
<!-- derived-from: context-management sha256:0227a5e43894 -->

A context — a Spec Context Project — is the unit of work: one canonical `specs/` tree
owned by one main repository, optionally spanning associated repositories that live and
die with it. Specs, bind, memory, releases and backlog resolve only from the main repo.

```bash
dadaia context create <ctx> --main-repo <slug> # registers it DEAD
dadaia context alive <ctx>                     # clones the repos, folds the canon scaffold over specs/
dadaia context bind <ctx>                      # this session's scope
dadaia context show <ctx> --json               # the repo set
```

`dadaia context alive` clones every missing repo; the main repo alone gets the canon
scaffold folded over `specs/`, never overwriting a file. `bind` writes exactly one
record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`), and
acquires nothing; `--print-env` emits `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for an
`eval $(…)` shell, and a session without a harness-native id carries the binding in
`DADAIA_CONTEXT`. The bind's scope is the context's main repo plus its associated
repos; a bound session's MUTATING write into a repo another context owns is refused
with the bind that would allow it. After a bind, the ctx-inject hook injects the context
header, `ARCHITECTURE.md`'s `## Tech Stack` section and the memory catalog digest once.

## Check compliance — `dadaia doctor`

<!-- derived-from: workspace-doctor sha256:ef9c81d0d181 -->

```bash
dadaia doctor --context <ctx> [--json] [--fix] [--redact]
```

`doctor` is the one instance validator, and three sections run in fixed order:
`workspace` (the root, the harness dirs, the `.dadaia/` zones, every ALIVE repo tree,
the installed git hook), `specs` (the rules over one `specs/` tree) and `ledgers` (the
backlog document, the ADR ledger and the ledger scripts' own `check`).

The `specs` and `ledgers` tree resolves from `--context`, `--specs-dir` or the bound
context; with none, those sections are empty and `workspace` still runs. With no
instance around — CI over a checkout — `dadaia doctor --specs-dir specs --source-root .`
runs the two tree sections.

Every printed finding is one `<CODE> <verdict> <message>` line, every error-class
finding carries one `fix: <command>` line, and any error-class finding exits 1. There
is no score: the findings and the exit code are the run. `--json` mirrors it,
`--redact` masks every foreign context name and repo slug, and `--fix` is the reaper —
it moves slop to `.dadaia/reaped/<YYYYMMDD>/` under a 7-day hold and deletes only what
a TTL expired.

## Run the first candidate

<!-- derived-from: release-lifecycle sha256:09607348cc88 -->
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
