---
slug: server-registry
title: server-registry
tldr: Port registry with TTL and PID tracking so parallel agents' dev servers never collide, owned by one stdlib script under the dd-cli-library skill.
summary: A JSON registry of dev-server ports with TTL and PID tracking, an expiry sweeper and a read-only scan against real OS listeners — read and written only by `dd-cli-library/scripts/registry.py`; no CLI verb.
tags: [server, registry, ports, ttl]
---

## Behavior

- `python3 .agents/skills/dd-cli-library/scripts/registry.py {list,next,register,release,clean,scan}` keeps a registry of ports per project so parallel dev servers do not collide and other sessions can discover a project's URL (ADR 0018: a state JSON is owned by a skill script, never a CLI group).
- The 3000-3999 range is enforced only by `next` allocation; `register` accepts any explicit port and is idempotent for the same project; a port held by another project exits 1 naming the owner.
- `clean` (and every mutating verb's sweep) expires entries whose TTL elapsed or whose PID is gone; on a non-POSIX host only the TTL is judged.
- `scan` is read-only: it parses `ss -tlnp`, lists unregistered LISTEN ports above 1024 enriched from `/proc/<pid>/`, and marks `lan_exposed` for `0.0.0.0`/`::` binds; without `/proc` or `ss` it returns an empty list.
- Runtime state is `.dadaia/states/server_registry.json` — `{"version", "range": {"min_port", "max_port"}, "entries": [...]}`; the script finds it by walking up from cwd to the nearest `.dadaia/`, `--registry <path>` overrides.

## Dependencies

[[workspace-init]] seeds the state file. Stdlib only.
