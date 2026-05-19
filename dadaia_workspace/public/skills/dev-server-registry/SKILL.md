---
name: dev-server-registry
description: >
  Use this skill whenever you need to start, stop, or check a local dev server
  for any project in this workspace. The registry at
  .dadaia/states/server_registry.json is the single source of truth for which
  ports are taken by which projects, and you MUST consult it before opening any
  port. Prevents silent port collisions between concurrent agents.
---

# Skill: dev-server-registry

Use this skill whenever you need to start, stop, or check a local dev server for any project in this workspace.

## Invariant

**Never start a server without registering its port first.** The registry at `.dadaia/states/server_registry.json` is the single source of truth.

## Protocol (4 steps)

### Step 1 — Inspect current state

```bash
dadaia server list
```

Shows all active servers across all projects. If your project already has an entry, use that port — do not start a second server.

### Step 2 — Get a safe port

```bash
dadaia server next --project <project-name> --json
```

Returns `{"port": N, "url": "http://localhost:N", "is_base_port": true|false}`.

- If `is_base_port: false`, the canonical port was occupied; use the returned port instead.
- Do NOT skip this step and pick a port manually.

### Step 3 — Start the server and register

Start the server on the port returned by `next`, then register:

```bash
dadaia server register --port <N> --project <project-name> --pid <pid> [--description "Vite dev server"]
```

`--pid` is optional but strongly recommended — enables automatic stale detection.

### Step 4 — Release when done

When stopping the server:

```bash
dadaia server release --port <N>
```

Or to release all ports for a project at once:

```bash
dadaia server release --project <project-name>
```

## Dashboard

To see all active servers in the browser (bookmarkable URL `http://localhost:4999`):

```bash
dadaia server dashboard
```

## Conflict handling

If `register` returns a `PortConflictError`:
1. Check `dadaia server list` — another agent may have registered first.
2. Run `dadaia server next` again to get the next available port.
3. If the conflict entry looks stale: `dadaia server clean` first, then retry.

## Quick reference

| Command | Purpose |
|---|---|
| `dadaia server list [--json]` | Show all registered servers |
| `dadaia server next --project <name>` | Get safe port (does not register) |
| `dadaia server register --port N --project <name>` | Register a port |
| `dadaia server release --port N` | Release a port |
| `dadaia server show --project <name>` | Show URL for a project |
| `dadaia server clean [--dry-run]` | Remove stale entries |
| `dadaia server dashboard` | Open browser index at http://localhost:4999 |
