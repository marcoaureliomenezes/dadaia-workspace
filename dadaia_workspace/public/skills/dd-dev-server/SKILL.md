---
name: dd-dev-server
description: >
  Reserve, register, list, release and clean dev-server ports through the workspace
  registry (`.dadaia/states/server_registry.json`) with one stdlib script. Use before
  opening any local port, when a port conflict appears, and when a dev server stops.
---

# dd-dev-server

The registry is the one record of who holds which local port (`AGENTS.md` §8.4). Every
verb is `python3 <skill-dir>/scripts/registry.py <verb>`; the script finds the registry by
walking up from cwd to the nearest `.dadaia/` (`--registry <path>` overrides).

## Opening a port

1. `registry.py list` — see what is held; `--status all` includes stale entries.
2. `registry.py next --project <name> --json` — the deterministic port for the project
   (its base port, or the next free one in `[--min-port, --max-port]`).
3. Start the server on that port, bound to loopback.
4. `registry.py register --port <n> --project <name> [--pid <pid>] [--url <url>]
   [--ttl <hours>] [--description <text>]` — idempotent for the same project; a port
   held by another project exits 1 naming the owner.

**Done when** `registry.py list --project <name>` shows the port as `active`.

## Closing and cleaning

- Server stopped → `registry.py release --port <n>` (or `--project <name>` for all).
- Conflict on register → `registry.py list --status all`, then `release` the stale port
  or `clean` (`--dry-run` previews; stale = TTL expired or pid gone).
- Orphans → `registry.py scan [--json]` lists listeners no entry covers (Linux `ss`;
  empty elsewhere); a `lan_exposed` listener is the operator's call.

**Done when** `registry.py list --status all --project <name>` is empty after the work.

## Contract

- JSON shape: `{"version":"1","range":{"min_port","max_port"},"entries":[…]}`; entries
  carry `port project url status pid reserved_at expires_at description`.
- Exit codes: 0 on success, 1 on a refused verb; `--json` output is stable for scripts.
