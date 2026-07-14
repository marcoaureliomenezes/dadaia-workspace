---
name: dadaia-workspace-manager
description: >
  Use this skill whenever asked to manage the dadaia workspace: import/export,
  initialize, manage spec context projects (create/alive/dead/delete/bind),
  inspect workspace state, or run doctor. Teaches the full dadaia CLI and prohibits
  raw file or git operations for workspace management. Invoke before acting on any
  request that involves contexts, repos on disk, or workspace state.
---

# dadaia-workspace-manager

## Prohibitions - Read Before Acting

NEVER do these things for workspace management because they corrupt state:

| What you might reach for | Use this instead |
|---|---|
| Edit `.dadaia/states/spec_contexts.json` directly | `dadaia context` subcommands |
| Manually choose a working context for an agent | `dadaia context bind <name>` (persists context + mode in the session record; default mode `read`) |
| `git clone <url> repos/<slug>/` | `dadaia context alive <name>` |
| `tar xzf <archive>` to import a workspace | `dadaia import <archive>` |
| `rm -rf repos/<slug>/` | `dadaia context dead <name>` |
| `git checkout <branch>` inside `repos/<slug>/` | `dadaia context alive <name>` checks out the stored branch automatically |

## Core Concepts

**Workspace root** - directory containing `.dadaia/`. All `dadaia` commands
auto-resolve it by searching cwd and parent directories. You never need to pass
`--workspace` in normal use.

**SpecContextProject** - record tracking a git repository:

| Field | Meaning |
|---|---|
| `name` | Human identifier used in all CLI commands |
| `state` | `alive` when the repo is on disk at `repos/<slug>/`; `dead` when it is not |
| `repo_slug` | Directory name under `repos/` |
| `repo_url` | Git clone URL |
| `current_branch` | Branch stored when the context is made dead and checked out on the next alive |

**Bound context** - the context selected for the current agent session by
`dadaia context bind <name> [--mode <read|implementation|review>] [--release <id>]`.
The command **persists** the bound context, mode, and session id in the session record
— the SDD gate resolves each session's own mode strictly self-scoped (env → the
session's own record → IMPLEMENTATION default), so bind never needs a shell `eval` and a
foreign session's bind can never change your mode (NO-LOCKS DOCTRINE, v0.1.76). Bind
also stamps a bind-epoch marker (`.dadaia/states/bind_epoch/<ctx>`) — the SOLE trigger
for context-memory injection: an unbound session gets generic preflight only (no
first-ALIVE injection fallback), and bind is never a precondition for ADDITIVE work.
Pass `--print-env` to
additionally emit `export DADAIA_CONTEXT=… DADAIA_SESSION_ID=…` lines for legacy
`eval $(…)` callers. Spec navigation, gates, and workflow commands use this
session-bound state or explicit `--context` flags.

**Repos on disk** - `repos/<slug>/` exists only when a context is `alive`.
Making a context dead git-syncs and removes it. Making it alive clones it back
on the stored branch.

## CLI Reference

### Workspace lifecycle

```bash
dadaia init                           # bootstrap .dadaia/, install agent assets
dadaia export                         # pack durable state -> .dadaia/dist/workspace-<ts>.tar.gz
dadaia export --exclude-mnt           # exclude mnt/ (VPS without live containers)
dadaia export --list                  # preview manifest without creating file
dadaia import <archive.tar.gz>        # full restore from export artifact
dadaia import <archive> --skip-mnt    # restore without extracting mnt/ (local machine)
dadaia import <archive> --dry-run     # preview what would happen; no disk changes
dadaia doctor                         # check workspace invariants
dadaia doctor --fix                   # auto-repair fixable issues
```

### Context management

```bash
dadaia context list                          # table: name, state, repo slug, branch
dadaia context show <name>                   # show specific context
dadaia context show --json                   # JSON state for all contexts
dadaia context create <name> --repo <slug>   # register new context (state: dead)
dadaia context alive <name>                  # clone repo, checkout stored branch; transition to alive
dadaia context dead <name>                   # git sync + push + remove repo; transition to dead
dadaia context delete <name>                 # delete context record (must be dead first)
.dadaia/.venv/bin/dadaia context bind <name>                                          # default: read (observe)
.dadaia/.venv/bin/dadaia context bind <name> --mode implementation --release <release-id>
.dadaia/.venv/bin/dadaia context bind <name> --mode review --release <release-id>
# add --print-env only for legacy `eval $(…)` shells — bind persists the mode itself
```

**NO-LOCKS DOCTRINE (v0.1.76).** Binds never acquire anything blocking. Every MUTATING
write upserts an **advisory presence record** for the session at
`.dadaia/states/presence/<ctx>/<session_id>.json` — this never fails or blocks (presence
I/O errors are swallowed and the write proceeds). `read` (and its legacy alias `spec`)
binds are **self-scoped only**: a READ-bound session blocks its **own** MUTATING writes
as opt-in self-protection, and a foreign session's bind can never change your mode
(additive paths always stay writable). The presence record is
`{session_id, runtime, pid, started_at, last_seen_at}`, where `pid` is the **long-lived
harness pid** (hook payload pid when present, else the hook's parent process). The
heartbeat (`last_seen_at`) renews on every PostToolUse hook firing (match-all on both
harnesses; harness-native session id from the hook stdin payload). Presence with a
`last_seen_at` older than `PRESENCE_TTL_SECONDS` (`= 120`, tunable retained with renamed
"presence TTL" semantics) is stale and GC'd by doctor (PRESENCE-GC) or opportunistically
on upsert.

### Liveness & advisory warnings (races accepted, never blocked)

The gate never freezes the flow, and the operator is **never** asked to rebind,
relaunch, or steal anything — there is nothing to steal. Behaviour on write:

- **Your own session (even relaunched)** → presence record is renewed. Stable identity
  via `.dadaia/sessions/runtime/<ctx>.ptr` means a relaunched/continuing session
  resolves to the same identity.
- **Stale or absent presence for other sessions** → GC'd; no advisory warning.
- **Live foreign presence** (a genuinely different concurrent session) → the write is
  **allowed**, and the gate surfaces one throttled advisory warning naming the other
  session (session id, runtime, heartbeat age). Both sessions' MUTATING writes proceed
  concurrently — this is the doctrine trade-off: a rare, surfaced race is preferred over
  a blocked user.

There is no per-session "implementation lock" vs "review lock" pair, no exclusivity
invariant, and no lease to steal. `dadaia lock steal` is **deleted** — there is nothing
left for it to do.

### Supporting commands

```bash
dadaia repos list                    # show known repos catalog
dadaia public stage                  # project lib assets into .dadaia/agentic/
dadaia public install --target all   # deploy assets to .agents/, .claude/, .codex/, .pi/
dadaia public install --target claude # deploy to .claude/ only
dadaia public doctor                 # audit asset drift
dadaia academy list                  # list courses
dadaia academy create <slug> <name>  # create course
```

## Import Flow

This is the canonical procedure. Do not improvise with raw bash.

**On the source machine:**

```bash
dadaia export --exclude-mnt
# outputs: .dadaia/dist/workspace-<timestamp>.tar.gz

scp workspace-<ts>.tar.gz <local-user>@<local-host>:~/
```

**On the destination machine:**

```bash
# Prerequisites: Python 3.12+, git
git clone <dadaia-workspace-repo-url>
pip install -e dadaia-workspace/ --break-system-packages

mkdir -p ~/workspace && cd ~/workspace
dadaia import ~/workspace-<ts>.tar.gz --skip-mnt
```

`dadaia import` handles automatically, in order:

1. Validates the archive and reads `export-manifest.json`
2. Extracts durable `.dadaia/` state and projected runtime assets
3. Patches absolute paths in workspace state where needed
4. Restores contexts as dead until repos are explicitly made alive
5. Preserves `current_branch` on each context
6. Runs `dadaia init` and deploys agent assets
7. For each context restored as alive in the manifest: `dadaia context alive <name>`
8. Reports restored contexts, any errors, and next steps such as adding secrets and running `dadaia doctor`

**After import - always verify:**

```bash
dadaia context list
dadaia doctor
```

## Context Lifecycle

```text
create (dead)
  -> alive (repo cloned at repos/<slug>/, branch checked out)
       -> bind (session selects context for read, implementation, or review work)
       -> dead (git sync + push + rmtree, current_branch stored)
            -> delete (context record removed)
```

**Switch work to another context**:

```bash
dadaia context alive <other-name>       # clone if needed
dadaia context bind <other-name>        # persists the binding; default mode read
```

Never run `dadaia context dead` during a switch unless you intentionally want to
remove that repo from disk.

## Doctor Invariants

`dadaia doctor` checks workspace consistency. Run after import or manual repair.

| Code | Check | Auto-fixable |
|---|---|---|
| INV-4 | `alive` context has repo on disk at `repos/<slug>/` | No (run `dadaia context alive <name>`) |
| INV-5 | `dead` context does not have repo on disk | Yes |
| PRESENCE-GC | Stale presence records (heartbeat aged past ~120s) are garbage-collected; presence is advisory-only and never blocks a write | Auto (GC on doctor + opportunistic sweep) |
