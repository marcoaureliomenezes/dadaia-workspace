---
name: dadaia-workspace-manager
description: >
  Use this skill whenever asked to manage the dadaia workspace: import/export,
  initialize, manage spec context projects (create/activate/deactivate/promote/delete),
  inspect workspace state, or run doctor. Teaches the full dadaia CLI and prohibits
  raw file or git operations for workspace management. Invoke before acting on any
  request that involves contexts, repos on disk, or workspace state.
---

# dadaia-workspace-manager

## Prohibitions — Read Before Acting

NEVER do these things for workspace management — they corrupt state:

| What you might reach for | Use this instead |
|---|---|
| Edit `.dadaia/states/spec_contexts.json` directly | `dadaia context` subcommands |
| Edit `primary_context.json` directly | `dadaia context promote <name>` |
| `git clone <url> repos/<slug>/` | `dadaia context activate <name>` |
| `tar xzf <archive>` to import a workspace | `dadaia import <archive>` |
| `rm -rf repos/<slug>/` | `dadaia context deactivate <name>` |
| `git checkout <branch>` inside `repos/<slug>/` | `dadaia context activate <name>` — it reads `current_branch` and checks out automatically |

## Core Concepts

**Workspace root** — directory containing `.dadaia/`. All `dadaia` commands auto-resolve it by searching cwd and parent directories. You never need to pass `--workspace` in normal use.

**SpecContextProject** — record tracking a git repository:

| Field | Meaning |
|---|---|
| `name` | Human identifier used in all CLI commands |
| `state` | `ativo` (repo on disk at `repos/<slug>/`) or `inativo` (not on disk) |
| `repo_slug` | Directory name under `repos/` |
| `repo_url` | GitHub clone URL |
| `is_primary` | Marks the context whose `specs/` guides AI agents |
| `current_branch` | Branch stored at deactivate, checked out on next activate |

**primary_context.json** — written by `dadaia context promote`; read by spec-navigator skills to locate the active project's specs.

**Repos on disk** — `repos/<slug>/` exists only when a context is `ativo`. Deactivating git-syncs and removes it. Re-activating clones it back on the correct branch.

## CLI Reference

### Workspace lifecycle

```bash
dadaia init                           # bootstrap .dadaia/, install agent assets into .claude/ etc.
dadaia export                         # pack durable state → .dadaia/dist/workspace-<ts>.tar.gz
dadaia export --exclude-mnt           # exclude mnt/ (VPS without live containers)
dadaia export --list                  # preview manifest without creating file
dadaia import <archive.tar.gz>        # full restore from export artifact
dadaia import <archive> --skip-mnt   # restore without extracting mnt/ (local machine)
dadaia import <archive> --skip-activate  # extract + init only; skip cloning repos
dadaia import <archive> --dry-run    # preview what would happen; no disk changes
dadaia doctor                         # check 6 workspace invariants
dadaia doctor --fix                   # auto-repair all fixable issues
```

### Context management

```bash
dadaia context list                          # table: name, state, primary flag, repo slug
dadaia context show                          # show primary context details
dadaia context show <name>                   # show specific context
dadaia context show --json                   # JSON (includes current_branch, repo_url)
dadaia context create <name> --repo <slug>   # register new context (state: inativo)
dadaia context activate <name>               # clone repo, checkout stored branch, auto-promote if first
dadaia context deactivate <name>             # git sync + push + remove repo; stores current_branch
dadaia context promote <name>                # set is_primary=true, write primary_context.json
dadaia context delete <name>                 # delete context record (must be inativo first)
dadaia context use <name>                    # eval $(dadaia context use <name>) — session isolation
```

### Supporting commands

```bash
dadaia repos list                     # show known repos catalog (repos.xlsx)
dadaia public stage                   # project lib assets into .dadaia/agentic/
dadaia public install --target all   # deploy assets to .agents/, .claude/, .codex/, .opencode/
dadaia public install --target claude # deploy to .claude/ only
dadaia public doctor                  # audit asset drift (ok / missing / drift)
dadaia academy list                   # list courses
dadaia academy create <slug> <name>   # create course
```

## Import Flow

This is the canonical procedure. Do not improvise with raw bash.

**On the VPS:**
```bash
dadaia export --exclude-mnt
# outputs: ✓ .dadaia/dist/workspace-<timestamp>.tar.gz

scp workspace-<ts>.tar.gz <local-user>@<local-host>:~/
```

**On the local machine:**
```bash
# Prerequisites: Python 3.12+, git
git clone https://github.com/marcoaureliomenezes/dadaia-workspace.git
pip install -e dadaia-workspace/ --break-system-packages

mkdir -p ~/workspace && cd ~/workspace
dadaia import ~/workspace-<ts>.tar.gz --skip-mnt
```

`dadaia import` handles automatically, in order:
1. Validates the archive and reads `export-manifest.json`
2. Extracts `.dadaia/states/`, `.dadaia/academy/`, CLAUDE.md, AGENTS.md, `.claude/`, `.agents/`, `.codex/`, `.opencode/`
3. Patches absolute paths in `spec_contexts.json` (old workspace root → new)
4. Resets all contexts to `inativo` / `is_primary=false` (repos not cloned yet)
5. Preserves `current_branch` on each context (used in step 6)
6. Runs `dadaia init` — creates `.venv`, deploys agent assets
7. For each context that was `ativo` in the manifest: `dadaia context activate <name>` (clones + checks out stored branch)
8. Promotes the primary context: `dadaia context promote <name>`
9. Reports restored contexts, any errors, and next steps (add secrets, run `dadaia doctor`)

**After import — always verify:**
```bash
dadaia context list    # all contexts visible
dadaia doctor          # should report "All invariants OK"
```

## Context Lifecycle

```
create (inativo)
  └─ activate → ativo (repo cloned at repos/<slug>/, branch checked out)
       ├─ promote → is_primary=true (primary_context.json written)
       └─ deactivate → inativo (git sync + push + rmtree, current_branch stored)
            └─ delete → context record removed
```

**Switch primary context** (correct procedure):
```bash
dadaia context activate <other-name>   # clone if needed
dadaia context promote <other-name>    # writes new primary_context.json
```
Never run `dadaia context deactivate` during a switch — it removes the repo from disk.

## Doctor Invariants

`dadaia doctor` checks six invariants. Run after any manual intervention or import.

| Code | Check | Auto-fixable |
|---|---|---|
| INV-1 | At most one context has `is_primary=true` | Yes |
| INV-2 | `is_primary=true` only on `ativo` context | Yes |
| INV-3 | `primary_context.json` matches the `is_primary` context | Yes |
| INV-4 | `ativo` context has repo on disk at `repos/<slug>/` | No (run `dadaia context activate`) |
| INV-5 | `inativo` context does NOT have repo on disk | Yes |
| INV-6 | `primary_context.json` present but no `is_primary` context | Yes |
