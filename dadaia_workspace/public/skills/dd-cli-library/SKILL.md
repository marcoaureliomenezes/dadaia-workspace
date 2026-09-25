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

1. Open `.dadaia/AGENTS.md` (the area's scoped law) and follow it.
2. Invoke the CLI by its venv path, never a bare `dadaia`: `.dadaia/.venv/bin/dadaia --help` lists the groups, `<group> --help` the subcommands; add `--json` to read commands for machine-readable output.
3. `.dadaia/.venv/bin/dadaia harness list` names this workspace's projected runtimes; `.dadaia/.venv/bin/dadaia harness add <name>` registers one more.
4. Run `.dadaia/.venv/bin/dadaia capabilities --json` first in any new or upgraded session.
5. Bind the session: `.dadaia/.venv/bin/dadaia context bind <ctx>` — `--print-env` emits `DADAIA_CONTEXT`/`DADAIA_SESSION_ID` for `eval $(…)`; the bind sets the write scope to the context's main repo plus its associated repos (`.dadaia/AGENTS.md`).
6. Workspace compliance: `.dadaia/.venv/bin/dadaia doctor --context <ctx> [--json]` — clean before any implementation write; `--fix` MOVES slop to `.dadaia/reaped/` (7-day hold) and nothing is deleted before its own TTL; `--fix --expired-only` reaps without touching slop (`.dadaia/AGENTS.md`).
7. Pass an explicit `--context` on every command that takes it.
8. Converge a runtime: resolve `provider.distribution_version` from `.dadaia/.venv/bin/dadaia capabilities --json`, then `.dadaia/.venv/bin/dadaia reconcile --expect-version "$v" --json`, then `.dadaia/.venv/bin/dadaia certify --json` — a failed certify check is a release blocker.
9. On a failing command: preserve the evidence trail (command, exit code, output); classify and register a genuine bug (`dd-bug-registration`) before any workaround.

## Workspace state is CLI-owned

- Never edit `.dadaia/states/*.json`, never `git clone` into `repos/`, never
  `rm -rf repos/<slug>/`, never hand-write `.dadaia/dist/` — `.dadaia/.venv/bin/dadaia context
  create|alive|dead` and `.dadaia/.venv/bin/dadaia import|export` own those.
- Level 1: `uvx dadaia-workspace init [DIR] [--harness …] [--repo <url>]`; re-run = upgrade. Level 2: `.dadaia/.venv/bin/dadaia context create [<name>] --main-repo <url> [--associated-repo <url>]…`
  clones, hooks, ALIVEs and binds, transactionally. Level 3: `.dadaia/.venv/bin/dadaia specs init --context <ctx>`, then the `dd-audit-project` first pass. Retire: `.dadaia/.venv/bin/dadaia context dead` (removes the repo; never mid-switch) → `.dadaia/.venv/bin/dadaia context delete`.
- A project is published once by `.dadaia/.venv/bin/dadaia context baseline <ctx>` (principal, integration and work branches; a re-run is a no-op); every later write is an ordinary commit.
- The associated set is written by `.dadaia/.venv/bin/dadaia context repo add <ctx> <slug> [--url <url>]` / `.dadaia/.venv/bin/dadaia context repo remove <ctx> <slug>` and READ only by `.dadaia/.venv/bin/dadaia context show <ctx> --json`, whose `associated_repos` carries slug, url, on-disk and branch.
- Portability: `.dadaia/.venv/bin/dadaia export` writes `.dadaia/dist/spec-contexts.json` (overwritten each run); on the destination `.dadaia/.venv/bin/dadaia import <file>` registers each unknown context DEAD, then `.dadaia/.venv/bin/dadaia context alive <slug>` clones it; verify with `.dadaia/.venv/bin/dadaia context list`.

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
- `.dadaia/.venv/bin/dadaia doctor` clean before any implementation write; `certify --json` green before promoting a runtime; every dev server started is registered.

## References

- `dd-bug-registration` — the ask-first proposal a genuine bug takes before `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append`.
- `dd-handoff-emitter` — emit/validate the final handoff.
