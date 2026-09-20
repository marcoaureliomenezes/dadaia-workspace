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

1. `dadaia --help` lists the groups; `dadaia <group> --help` the subcommands; add
   `--json` to read commands for machine-readable output.
2. Run `dadaia capabilities --json` first in any new or upgraded session.
3. Bind the session: `dadaia context bind <ctx>` — `--print-env` emits
   `DADAIA_CONTEXT`/`DADAIA_SESSION_ID` for `eval $(…)`; the bind sets the write
   scope to the context's main repo plus its associated repos (`DADAIA.md` §3.3).
4. Workspace compliance: `dadaia doctor --context <ctx> [--json]` — clean before any
   implementation write; `--fix` MOVES slop to `.dadaia/reaped/` (7-day hold) and
   nothing is deleted before its own TTL; `--fix --expired-only` reaps without
   touching slop (`DADAIA.md` §8.5).
5. Pass explicit `--context`/`--release-id` on every command.
6. Converge a runtime: resolve `provider.distribution_version` from
   `dadaia capabilities --json`, then `dadaia reconcile --expect-version "$v"
   --json`, then `dadaia certify --json` — a failed certify check is a release
   blocker.
7. On a failing command: preserve the evidence trail (command, exit code, output);
   classify and register a genuine bug (`dd-bug-registration`) before any
   workaround.

## Workspace state is CLI-owned

- Never edit `.dadaia/states/*.json`, never `git clone` into `repos/`, never
  `rm -rf repos/<slug>/`, never hand-write `.dadaia/dist/` — `dadaia context
  alive|dead` and `dadaia import|export` own those.
- Lifecycle: `create --main-repo <slug> [--associated-repos a,b]` → alive → bind → dead
  → delete; `context dead` removes the repo from disk — never run it mid-switch.
- Portability: `dadaia export` writes `.dadaia/dist/spec-contexts.json` (overwritten
  each run); on the destination `dadaia import <file>` registers each unknown context
  DEAD, then `dadaia context alive <slug>` clones it; verify with `dadaia context list`.

## Dev-server law

- The registry (`.dadaia/states/server_registry.json`) is the one record of who holds
  which local port; every verb is `python3 <skill-dir>/scripts/registry.py <verb>` (the
  script walks up from cwd to the nearest `.dadaia/`; `--registry <path>` overrides).
- Open a port in this order: `list` → `next --project <name> --json` → start the server on
  loopback → `register --port N --project <name> [--pid <pid>] [--ttl <hours>]` — idempotent
  for the same project; a port held by another project exits 1 naming the owner.
- Work ends with the port released (`release --port N`, or `--project <name>` for all);
  on a conflict `list --status all`, `clean` (stale = TTL expired or pid gone), then `next`.
- `scan [--json]` lists listeners no entry covers (Linux `ss`; empty elsewhere).

## Done when

- The command run matches live `--help`, not a remembered table.
- `dadaia doctor` clean before any implementation write; `certify --json` green
  before promoting a runtime; every dev server started is registered.

## References

- `dd-bug-registration` — the ask-first proposal a genuine bug takes before `dadaia bugs append`.
- `dd-handoff-emitter` — emit/validate the final handoff.
- `DADAIA.md` §2 — SDD stages are agent-dispatched, not a CLI verb group.
