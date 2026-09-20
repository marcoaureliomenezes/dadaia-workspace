# Getting started

From a bare machine to a first candidate. Every step names what it creates on disk;
the terms are defined in [concepts](concepts.md) and in [`CONTEXT.md`](../CONTEXT.md).

## Install

<!-- derived-from: pypi-distribution sha256:80d67bd879ea -->
<!-- derived-from: workspace-init sha256:5b20a0d9dc80 -->

```bash
python -m venv .venv && .venv/bin/pip install dadaia-workspace
```

`pip install dadaia-workspace` installs the library and its `dadaia` CLI. The wheel
ships `dadaia_workspace/` with the full public asset tree, so the next step works
offline from a bare install. `pyproject.toml`'s `version` is the single source of the
number, and a `v<version>` tag exists only for a published one.

Install into a virtualenv, never into the system interpreter. A workspace keeps its
own at `.dadaia/.venv`: `dadaia init` provisions it, every `dadaia`, `pip` and
`python -m dadaia_workspace` invocation inside the workspace is expected to come from
`.dadaia/.venv/bin/`, and the gate refuses one that does not.

## Provision the workspace — `dadaia init`

<!-- derived-from: workspace-init sha256:5b20a0d9dc80 -->

```bash
dadaia init [--workspace PATH] [--harness claude|codex|kimi-code|all] [--skip-assets]
```

`init` is the only verb that operates on a zero workspace, and re-running it is
idempotent. It creates:

- `.dadaia/.venv` and every zone whose registry creator is `init`, plus the shared
  `.agents/skills` root and the harness directories the selected profile names —
  what it lays down is a view of one registry, `dadaia_workspace/core/workspace_layout.py`.
- `.dadaia/states/spec_contexts.json` and `.dadaia/states/server_registry.json` as
  empty documents, never overwriting existing data, and
  `.dadaia/states/harness_profile.json` through the profile store's one writer.
- Unless `--skip-assets`, the staged and installed public assets — the one writer of
  every hook wiring, and the source of the projected law (`DADAIA.md`, the scoped
  `AGENTS.md` files) and the agent assets of each selected harness. Skipping assets
  leaves the workspace ungated, and the output says so.

`init` deletes no projection and installs no git hook: the chokepoints go in per repo
with `dadaia ci install-hook`.

## Bind a context — `dadaia context bind`

<!-- derived-from: spec-context-project sha256:a80fd443036b -->
<!-- derived-from: context-management sha256:a66534def71e -->

A context — a Spec Context Project — is the unit of work: one canonical `specs/` tree
owned by one main repository, optionally spanning associated repositories that live and
die with it. Specs, bind, memory, releases and backlog resolve only from the main repo.

```bash
dadaia context create <ctx> --repo-url <url>   # registers it DEAD in the registry
dadaia context alive <ctx>                     # clones the repos, folds the canon scaffold over specs/
dadaia context bind <ctx>                      # this session's scope
dadaia context show --json                     # what this session resolved
```

`bind` writes exactly one artifact — the caller-owned
`.dadaia/sessions/<session-id>.json` carrying context, runtime, pid and `bound_at`.
It acquires nothing, requires no live release, and `--print-env` emits
`DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for an `eval $(…)` shell; in a session with
no harness-native id, that exported variable *is* the binding. The bind's scope is
the context's main repo plus its associated repos, and it constrains nothing else.

## Check compliance — `dadaia doctor`

<!-- derived-from: workspace-doctor sha256:d487df63fe2b -->

```bash
dadaia doctor --context <ctx> [--json] [--fix] [--redact]
```

`doctor` is the one validator, and three sections run in fixed order: `workspace`
(the root, the harness dirs, the `.dadaia/` zones, every ALIVE repo tree, the
installed git hooks), `specs` (the rules over one `specs/` tree) and `ledgers`
(`BACKLOG.json` plus schema validation of every committed governance record).

With no instance around the run — CI over a bare checkout — `dadaia doctor
--specs-dir specs` still reads the tree: the `workspace` section is empty and the
other two run; only a run with nothing to read refuses and points at `dadaia init`.

Every finding prints as one `<CODE> <verdict> <message>` line, and every error-class
rule carries a mandatory `fix: <command>` under each of its findings — so an exit-1
run never stalls the flow. There is no score line: the findings and the exit code are
the report. `--json` mirrors the whole run; `--fix` is the reaper — it
MOVES slop to `.dadaia/reaped/<YYYYMMDD>/` under a 7-day hold and deletes only what
its own TTL expired.

## Run the first candidate

<!-- derived-from: sdd-bug-backlog-governance sha256:8c75f3f83bf9 -->

A candidate is one closed-scope SDD cycle inside the live release. Nothing drives it:
the documents are the state, the verbs move the state document, and the markers in
`TASKS.md` are the trace.

1. **Demand enters the backlog.** Only the operator creates demand; `project-manager`
   curates `specs/backlog/BACKLOG.json`'s `active[]` through its intake, and
   `dadaia backlog new` appends the entry. Maturation (`idea → candidate → picked`)
   is hand-written and doctor-validated.
2. **Birth the release.** `dadaia release new <M.m.p>` writes `SPEC.md` and
   `_RELEASE.json` in phase `DEFINITION` under `specs/releases/<M.m.p>/`, in one
   transaction, refusing a second live release.
3. **Define the candidate.** Author `SPEC.md`, `PLAN.md` and `TASKS.md` at the release
   root, each carrying `**Status:** Aprovado`, and flip the picked backlog entry to
   `picked` in the same commit.
4. **Open implementation.** `dadaia release phase IMPLEMENTATION --sha <sha>` requires
   the approved trio and stamps `defined {sha, ts}`.
5. **Implement one task at a time.** Reserve a row `[ ] → [-]`, do the work inside its
   declared write set, then `[-] → [x]` with a `conventional-commit(task-id)` commit.
6. **Close the candidate.** `dadaia release phase CLOSURE --sha <sha>` requires every
   task `[x]` and stamps `implemented {sha, rc: rc + 1, ts}`. Then the memory update,
   the closure `log` entries, the disposition sweep (`dadaia backlog exit`,
   `dadaia audit disposition`), artifact GC, and the `feature → develop` pull request.
7. **Continue or promote.** `dadaia release rc-archive` moves the completed trio into
   the next `rc-N/`, sets `rc = N` and returns the release to `DEFINITION` for another
   candidate; `dadaia release archive <id> --shipped <sha> --pr <n> --next <M.m.p>`
   ships it instead — archiving the directory, birthing the next release, appending
   the `delivered` histo record, and printing the git lines it never runs.

A bug needs none of this: register, root-cause, RED test, fix, GREEN, resolve with
evidence, commit — on the live feature branch, in any phase.
