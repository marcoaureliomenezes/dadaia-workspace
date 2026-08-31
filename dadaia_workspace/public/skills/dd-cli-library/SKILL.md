---
name: dd-cli-library
description: >
  Operate the dadaia-workspace CLI: bind a context, check state, author
  backlog/release artifacts, register a bug, manage dev servers, discover any
  command. Use whenever a task needs the CLI; the non-obvious idioms live here, the
  authoritative surface is --help.
---

# dd-cli-library

Cache of expensive lookups, not a transcription of the live command tree — when a
line here and `--help` disagree, `--help` wins.

## Core idioms

1. Call the venv binary always: `.dadaia/.venv/bin/dadaia` (absolute path) — never
   system Python/pip.
2. `dadaia --help` lists the groups; `dadaia <group> --help` the subcommands; add
   `--json` to read commands for machine-readable output.
3. Run `dadaia capabilities --json` first in any new or upgraded session.
4. Bind the session: `dadaia context bind <ctx> --mode implementation --release
   <id>`; a plain shell (or kimi-code) exports `DADAIA_CONTEXT=<ctx>` instead — the
   env var IS the binding there. ADDITIVE work (bugs/backlog/audits/reports) needs
   no bind.
5. Before implementing: `dadaia specs doctor --context <ctx> --json` clean, then
   reserve the task (`dadaia-task-manager`).
6. Pass explicit `--context`/`--release-id` on every command.
7. Converge a runtime: resolve `provider.distribution_version` from
   `dadaia capabilities --json`, then `dadaia reconcile --expect-version "$v"
   --json`, then `dadaia certify --json` — a failed certify check is a release
   blocker.
8. On a failing command: preserve the evidence trail (command, exit code, output);
   classify and register a genuine bug (`dd-bug-registration`) before any
   workaround.
9. `dadaia panel` (default port 4999) is the human view.

## Workspace state is CLI-owned

- Never edit `.dadaia/states/*.json`, never `git clone` into `repos/`, never
  `rm -rf repos/<slug>/`, never `tar xzf` an import — `dadaia context alive|dead`
  and `dadaia import|export` own those.
- Lifecycle: `create (dead) → alive → bind → dead → delete`; `context dead` removes
  the repo from disk — never run it casually mid-switch.
- Import flow: export on source, move the archive, `dadaia import <archive>`, verify
  with `dadaia context list` + `dadaia doctor`.
- NO-LOCKS: binds acquire nothing; MUTATING writes leave advisory presence; a live
  foreign presence is one throttled warning, never a block.

## Dev-server law

- Never open a port without the registry: `dadaia server list` → `dadaia server
  next --project <name> --json` → start → `dadaia server register --port N
  --project <name>`.
- Use the returned port even when `is_base_port: false`; release on stop; on
  `PortConflictError`: `server list`, `server clean` if stale, `server next` again.

## Reachability

Granted to every persona whose `tools:` include `Bash`; the shell-less roles
(`product-engineer`, `software-architect`) are ungranted and receive CLI work by
dispatch. The table is derived at projection time by
`dadaia_workspace/public/scripts/lint-dadaia-cli-reachability.py`.

## Done when

- The command run matches live `--help`, not a remembered table.
- `specs doctor` clean before any implementation write; `certify --json` green
  before promoting a runtime; every dev server started is registered.

## References

- `dd-bug-registration` — classify-first, redaction, `dadaia bugs append`.
- `dadaia-handoff-emitter` — emit/validate the final handoff.
- `DADAIA.md` §2 — SDD stages are agent-dispatched, not a CLI verb group.
