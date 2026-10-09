---
name: dd-cli-library
description: >
  Operate the dadaia-workspace CLI: bind a context, check state, manage dev servers, discover any
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
5. Bind: `.dadaia/AGENTS.md` §2.
6. Workspace compliance: `.dadaia/.venv/bin/dadaia doctor --context <ctx> [--json]` — clean before any implementation write; `--fix` semantics: `.dadaia/AGENTS.md` §5.
7. Pass an explicit `--context` on every command that takes it.
8. Converge a runtime: `v=$(.dadaia/.venv/bin/dadaia capabilities --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["provider"]["distribution_version"])')`, then `.dadaia/.venv/bin/dadaia reconcile --expect-version "$v" --json`, then `.dadaia/.venv/bin/dadaia certify --json` — a failed certify check is a release blocker.
9. On a failing command: preserve the evidence trail (command, exit code, output); propose a genuine bug (`dd-bug-registration` §2) before any workaround.

## Workspace state is CLI-owned

- `.dadaia/states/`, `repos/` clones and `.dadaia/dist/` change only through `context create`, `alive`, `dead` and `import`/`export`.
- Onboarding levels: the root `AGENTS.md` map §7; retire with `context dead` → `context delete`.
- Every other verb (`context baseline`, `context repo add|remove`, `export`/`import`): its `--help`.

## Dev servers

- The registry (`.dadaia/states/server_registry.json`) is the one record of who holds
  which local port; every verb is `python3 .agents/skills/dd-cli-library/scripts/registry.py <verb>` (the
  script walks up from cwd to the nearest `.dadaia/states/spec_contexts.json`; `--registry <path>` overrides).
- Open a port in this order: `list` → `next --project <name> --json` → start the server on
  loopback → `register --port N --project <name> [--pid <pid>] [--ttl <hours>]` — idempotent
  for the same project; a port held by another project exits 1 naming the owner.
- Work ends with the port released (`release --port N`, or `--project <name>` for all);
  on a conflict `list --status all`, `clean` (stale = TTL expired or pid gone), then `next`.
- `scan [--json]` lists listeners no entry covers (Linux `ss`; empty elsewhere).

## Done when

- Each command run was checked against its live `--help` this session.
- `.dadaia/.venv/bin/dadaia doctor` clean before any implementation write; `certify --json` green before promoting a runtime; every dev server started is registered.

## References

- `dd-bug-registration` — the ask-first proposal a genuine bug takes before `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append`.
- `dd-handoff-emitter` — emit/validate the final handoff.
