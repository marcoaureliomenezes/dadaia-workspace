---
slug: context-management
title: context-management
tldr: ALIVE/DEAD registry of a main repo plus associated repos; create clones, hooks and ALIVEs in one step; only context bind binds, naming the session's scope.
summary: Spec Context Projects and their repos through one registry and the context verbs — create as onboarding level 2, alive, dead, baseline, the repo set; one resolution authority whose Bind carries the session's scope; bind-driven injection of the tech stack, catalog and help digests; redaction at the render boundary.
tags: [context, lifecycle, session, privacy]
sources:
  - dadaia_workspace/hooks/ctx_inject.py
  - dadaia_workspace/hooks/_common.py
  - dadaia_workspace/core/invocation.py
  - dadaia_workspace/core/session_store.py
  - dadaia_workspace/core/record_liveness.py
  - dadaia_workspace/features/spec_context/injection_policy.py
  - dadaia_workspace/features/spec_context/markers.py
  - dadaia_workspace/features/spec_context/service.py
  - dadaia_workspace/infrastructure/json_context_store.py
  - dadaia_workspace/cli/commands/context.py
---

## Registry

- `.dadaia/states/spec_contexts.json` stores per context its name, state, main repo slug and URL, ordered associated repos (slug + URL), branch and lifecycle timestamps; schema 2 and 3 files read alike, a schema 1 file is refused with `dadaia migrate` as the fix ([[specs-migration]]).
- The main repo is where `specs/` lives and the only specs, bind, memory, release and backlog target; associated repos are working checkouts.
- `dadaia context create [<name>] --main-repo <url> [--associated-repo <url>]...` is onboarding level 2 in one transactional step: clone every repo into `repos/<slug>/`, install the pre-push hook in each, register the context ALIVE with its branch and print the derived next step; it binds no session — only `context bind` does ([[workspace-init]]).
- One slug rule serves the context name and every repo slug: a URL's last path segment minus `.git`, every character outside `[A-Za-z0-9_-]` replaced by `-` (`my.repo.git` -> `my-repo`); the name defaults to the main repo's slug.
- The record is validated before any clone; a `repos/<slug>` already holding a checkout whose `origin` is that URL is adopted without cloning, any other occupant exits 1 and registers nothing.
- Any failure removes every directory the call created and writes no record, so the corrected command re-runs with the same slug; `create` writes nothing inside a repo but the hook, so the working tree stays clean and HEAD equals the remote's.
- A `create` refusal's `fix:` line reproduces the invocation with every `--associated-repo` kept: a failed clone's URL becomes `<clone-url>`, a taken name becomes `<another-name>`, and a slug another context owns points to `context list` instead.
- The hook installer copies `pre-push-ci-gate.sh` into `.git/hooks/pre-push` only where no hook exists; an operator's own hook is never overwritten, and [[workspace-doctor]]'s `HOOKS-DRIFT-1` names it; `dadaia ci install-hook [--repo <path>] [--force]` is its other caller ([[sdd-gate-v3]]).
- `dadaia context alive <name>` clones every missing repo of the set and installs the hook where absent in each, main and associated alike; it writes no specs, commits nothing and restores the main repo's recorded branch. It is idempotent on an ALIVE context; a DEAD context (after `dadaia import`) becomes ALIVE ([[context-portability]]).
- `dadaia context dead <name> [--commit]` preflights the whole set before touching any repo: untracked files refuse without `--commit`, and with it a secret scan blocks on any hit; a repo with local commits and no remote refuses. Then tracked changes are committed and pushed, the branch recorded and every repo removed; a refused push removes nothing and prints git's own error.
- `alive` and `dead` back-fill every repo's empty URL from its checkout's `origin`; `dead` refuses to remove a repo still URL-less (`fix: git -C repos/<slug> remote add origin <clone-url>`); `alive` refuses a URL-less missing main repo with `fix: <cli> context delete <name> && <cli> context create <name> --main-repo <clone-url>`, and a URL-less missing associated repo with `fix: <cli> context repo remove <name> <slug> && <cli> context repo add <name> <slug> --url <clone-url>`.
- `dadaia context baseline <name> --yes [--push]` births an unborn main repo: it refuses a clean one, scans for secrets, commits the working tree on the first release's `feature/{M.m.p}` branch and, with `--push`, publishes it; a repo with history and a clean tree only pushes, a dirty one is refused — its changes are an ordinary commit.
- `dadaia context delete <name>` removes a DEAD context.
- `dadaia context repo add <ctx> <slug> [--url <url>]` and `dadaia context repo remove <ctx> <slug>` write the registry only, cloning and deleting nothing: re-adding the same slug and URL is a no-op, the same slug with another URL is refused (remove, then add), and a slug with neither a URL nor a `repos/<slug>` git checkout is refused, as by `dadaia import`; `dadaia context show <ctx> --json` is the one reader of the repo set.
- A repo slug belongs to one context: `create`, `repo add` and `dadaia import` pass one validation (name and slugs allowlisted, name new, every slug free); `INV-6` reports any multi-owner slug already on disk ([[workspace-doctor]]).

## Resolution

- `resolve` in `dadaia_workspace/core/invocation.py` answers workspace root, session, context, repo slug, specs dir and the session's `Bind` in one call; the CLI, the container, the gate and ctx-inject each resolve once.
- Rung 0 is caller-supplied (`--context`, or a write target under `repos/<slug>/`), rung 1 `DADAIA_CONTEXT`, rung 2 this session's live record keyed by its harness-native id, rung 3 the repo containing the cwd. Every rung fails soft; with all exhausted, specs-dir resolution raises instead of guessing.
- The workspace root is walked from an explicit target path when one is given, else from the cwd, so every rung shares one root.
- A context's specs tree is `repos/<main-slug>/specs` whether or not it exists; a context without one is onboarding level 2, never redirected to another tree.
- `Bind` is the named context plus every repo slug it owns (main plus associated); `resolve_bind` reads `DADAIA_CONTEXT` then the session record, never the cwd, and an unbound `Bind` owns nothing.
- `dadaia_workspace/core/session_store.py` alone reads and writes `.dadaia/sessions/`; `is_stale` in `dadaia_workspace/core/record_liveness.py` is the one staleness predicate.
- One harness session runs per checked-out tree; a parallel session uses its own linked worktree.

## Binding and injection

- `dadaia context bind <name> [--print-env]` writes one record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`), acquiring nothing; `--print-env` emits `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for `eval $(…)`.
- The ctx-inject hook injects state, never law: a bound session gets its context header, the derived onboarding next step focused on its context while one remains, `ARCHITECTURE.md`'s `## Tech Stack` section and the catalog digest (`slug`, `title`, `tldr`, `path` per atom); an unbound session gets `[no bound context]`, the same derived step ([[workspace-init]]) and the ALIVE-context list.
- Every emission also carries `.dadaia/agentic/help-digest.md`, which the hook reads and never builds.
- Injection fires once per session, again after a later bind or a compaction, and stays silent on repeat prompts; its sentinel and compact markers live in `.dadaia/tmp/` and are reaped by mtime.
- A bound session's MUTATING write under a `repos/<slug>/` another context owns is refused with a `fix:` naming the owner's bind ([[sdd-gate-v3]]).

## Redaction

- `dadaia context list`, `dadaia context show` and `dadaia doctor` accept `--redact`, masking every foreign context name and repo slug as a stable placeholder at render time.
- Moving the context set between workspaces is [[context-portability]].

## Runtime state

`.dadaia/states/spec_contexts.json`; `.dadaia/sessions/`; `.dadaia/tmp/ctx-*` markers; `repos/<slug>/`, where only the main repo carries `specs/`.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]], [[context-portability]], [[QUALITY]].
