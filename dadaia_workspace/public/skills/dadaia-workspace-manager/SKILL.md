---
name: dadaia-workspace-manager
description: >
  Use this skill whenever asked to manage the dadaia workspace: import/export,
  initialize, manage spec context projects (create/alive/dead/delete/bind),
  inspect workspace state, or run doctor. Teaches the full dadaia CLI and prohibits
  raw file or git operations for workspace management. Invoke before acting on any
  request that involves contexts, repos on disk, or workspace state.
tldr: "Manage the workspace only through dadaia CLI commands; never raw file/git ops on state or repos."
---

# dadaia-workspace-manager

## 1. When

- Import/export, initialize, or run doctor on the workspace.
- Manage spec context projects: create/alive/dead/delete/bind.
- Inspect workspace state before acting on any request touching contexts, repos on disk, or workspace state.

## 2. Steps

1. Never edit `.dadaia/states/spec_contexts.json` directly — use `dadaia context` subcommands.
2. Never manually choose a working context for an agent — use `dadaia context bind <name>`.
3. Never `git clone <url> repos/<slug>/` — use `dadaia context alive <name>`.
4. Never `tar xzf <archive>` to import a workspace — use `dadaia import <archive>`.
5. Never `rm -rf repos/<slug>/` — use `dadaia context dead <name>`.
6. Never `git checkout <branch>` inside `repos/<slug>/` — `dadaia context alive <name>` checks out the stored branch.
7. Never pass `--workspace` in normal use — every `dadaia` command auto-resolves the root from cwd/parents.
8. Bind a context: `dadaia context bind <name> [--mode <read|implementation|review>] [--release <id>]`.
9. Expect bind to persist context, mode, and session id in the session record (self-scoped mode resolution).
10. Export `DADAIA_CONTEXT=<ctx>` as the binding in a plain shell or kimi-code (no harness session id).
11. Bootstrap: `dadaia init`.
12. Export: `dadaia export` (`--exclude-mnt` on a VPS without live containers, `--list` to preview).
13. Import: `dadaia import <archive.tar.gz>` (`--skip-mnt` local machine, `--dry-run` to preview).
14. Check invariants: `dadaia doctor` (`--fix` to auto-repair).
15. List contexts: `dadaia context list` / `dadaia context show <name>` / `dadaia context show --json`.
16. Register a new context: `dadaia context create <name> --repo <slug>` (state: dead).
17. Bring it up: `dadaia context alive <name>` (clones, checks out stored branch).
18. Retire it: `dadaia context dead <name>` (git sync + push + remove repo).
19. Remove the record: `dadaia context delete <name>` (must be dead first).
20. Never run `dadaia context dead` during a context switch unless intentionally removing that repo from disk.
21. Follow the import flow exactly: export on source, `scp` the archive, clone the repo, create the venv, `pip install -e`.
22. Let `dadaia import` handle validation, extraction, path patching, dead-context restore, branch preservation, init, alive-restore, and reporting.
23. After import, always verify: `dadaia context list` then `dadaia doctor`.

## 3. Done when

- Every workspace-management action ran through a `dadaia` subcommand, never raw file/git ops.
- `dadaia doctor` reports clean after any import or manual repair.
- The bound context's mode and session id are visible in `dadaia context show --json`.

## 4. References

- Core concepts: workspace root (auto-resolved), `SpecContextProject` fields (`name`, `state`, `repo_slug`, `repo_url`, `current_branch`).
- NO-LOCKS DOCTRINE (v0.1.76): binds never acquire anything blocking; every MUTATING write upserts an advisory presence record.
- Presence record shape: `{session_id, runtime, pid, started_at, last_seen_at}`; stale past `PRESENCE_TTL_SECONDS` (120) is GC'd.
- Liveness: your own session renews presence; stale foreign presence is GC'd silently.
- Liveness (continued): live foreign presence surfaces one throttled warning, write still proceeds.
- No per-session "implementation lock" vs "review lock" pair exists — nothing to steal, nothing to rebind.
- Context lifecycle: `create (dead) -> alive -> bind -> dead -> delete`.
- Doctor invariants: INV-4 (alive has repo on disk, not auto-fixable), INV-5 (dead has no repo, auto-fixable), PRESENCE-GC (auto).
- Supporting commands: `dadaia repos list`, `dadaia public stage/install/doctor`, `dadaia academy list/create`.
