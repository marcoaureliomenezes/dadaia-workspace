---
name: dev-server-registry
description: >
  Use this skill whenever you need to start, stop, or check a local dev server
  for any project in this workspace. The registry at
  .dadaia/states/server_registry.json is the single source of truth for which
  ports are taken by which projects, and you MUST consult it before opening any
  port. Prevents silent port collisions between concurrent agents.
tldr: "Never open a port without dadaia server list/next/register first — the registry is the single source of truth."
---

# Skill: dev-server-registry

## 1. When

- Starting, stopping, or checking a local dev server for any project in this workspace.
- Before opening any port — never start a server without registering it first.

## 2. Steps

1. Inspect current state: `dadaia server list`.
2. Reuse an existing entry for your project instead of starting a second server.
3. Get a safe port: `dadaia server next --project <project-name> --json`.
4. Use the returned port even when `is_base_port: false` — the canonical port was occupied.
5. Never skip step 3 and pick a port manually.
6. Start the server on the returned port.
7. Register it: `dadaia server register --port <N> --project <project-name> --pid <pid> [--description "..."]`.
8. Pass `--pid` when possible — it enables automatic stale detection.
9. Release the port when stopping: `dadaia server release --port <N>`.
10. Release every port for a project at once: `dadaia server release --project <project-name>`.
11. Open `dadaia panel` (Servers tab) to see all registered servers in the browser.
12. On a `PortConflictError`: check `dadaia server list` — another agent may have registered first.
13. Run `dadaia server next` again to get the next available port.
14. Run `dadaia server clean` first if the conflicting entry looks stale, then retry.

## 3. Done when

- Every dev server you started is registered in `server_registry.json`.
- Every server you stop is released.
- No port was opened without first calling `dadaia server next`/`list`.

## 4. References

- `dadaia server list [--json]` — show all registered servers.
- `dadaia server next --project <name>` — get a safe port, does not register.
- `dadaia server register --port N --project <name>` — register a port.
- `dadaia server release --port N` / `--project <name>` — release a port or all of a project's.
- `dadaia server show --project <name>` — show URL for a project.
- `dadaia server clean [--dry-run]` — remove stale entries.
- `dadaia panel` — browser view of registered servers (Servers tab).
