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
**and refreshes the context's incumbent pointer** (`sessions/runtime/<ctx>.ptr`) — the
bind binds the CONTEXT, so the SDD gate resolves the bound mode for the running harness
session through the incumbent pointer, no shell `eval` needed. Bind also stamps a
bind-epoch marker (`.dadaia/states/bind_epoch/<ctx>`) — the SOLE trigger for
context-memory injection: an unbound session gets generic preflight only (no
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

Implementation/review binds acquire the single per-context release **lease** (v0.1.6
model: one MUTATING lease per context, coordinated by project-manager — see constitution
§8/§9). `read` (and its legacy alias `spec`) binds are **non-acquiring**: they never
block, never take a lease, and the gate blocks MUTATING file-tool writes from a
READ-bound session before any lease call (additive paths stay writable). The lease
record is `{context, release, session_id, mode, pid, acquired_at, heartbeat, ttl}`,
where `pid` is the **long-lived harness pid** (hook payload pid when present, else the
hook's parent process); liveness is **TTL + pid veto**: stale means
`now − heartbeat > LEASE_TTL_SECONDS` (`= 120`, OQ-1 operator decision 2026-06-06)
**and** the recorded holder pid is not demonstrably alive. The heartbeat renews on every
PostToolUse hook firing (match-all on both harnesses; harness-native session id from the
hook stdin payload), so a holder running long reads/tests stays live — and a single tool
call outliving the TTL is still protected by the pid veto.

### Liveness & recovery (reclaim-iff-stale / yield-iff-live-foreign)

The gate never freezes the flow, and the operator is **never** asked to rebind,
relaunch, or steal a lock. Behaviour on acquire:

- **Your own session (even relaunched)** → RENEW. Stable identity via
  `.dadaia/sessions/runtime/<ctx>.ptr` means a relaunched/continuing session resolves to
  the same identity, so you never block yourself.
- **Stale or absent lease** (no heartbeat within ~120s **and** holder pid not alive) →
  reclaimed automatically on the next write (fail-open). A finished or dead holder frees
  the lease by itself. A holder whose pid is still running is **never** stolen, however
  old its heartbeat.
- **Live foreign lease** (a genuinely different concurrent session) → the gate **yields**:
  this session does not mutate (informative `LockHeldError`, additive writes still allowed),
  and acquires automatically once the other session goes idle / expires. This is the
  exactly-one-mutating-session invariant (§8) — not a freeze, and it requires no manual step.

There is no per-session "implementation lock" vs "review lock" pair — v0.1.6 collapsed
that into one release lease keyed to the coordinator session. `dadaia lock steal` exists
only as an administrative/observability escape; it is **never** part of the normal flow,
because reclaim-iff-stale already frees an abandoned lease without it.

### Supporting commands

```bash
dadaia repos list                    # show known repos catalog
dadaia public stage                  # project lib assets into .dadaia/agentic/
dadaia public install --target all   # deploy assets to .agents/, .claude/, .codex/, .opencode/
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
| LEASE | The per-context release lease record is consistent with context state; a stale lease (heartbeat aged past ~120s AND holder pid not alive — a running pid vetoes reclaim) auto-reclaims, no manual action. `dadaia lock steal` exists only as an admin/observability escape — never a routine unblock step | Auto (reclaim-iff-stale) |
