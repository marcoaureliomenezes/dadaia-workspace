---
slug: context-management
title: context-management
tldr: ALIVE/DEAD registry of one main repo plus N associated repos; one resolution per call; a bind names the session's scope and drives memory injection.
summary: Spec Context Projects and their repos through one registry and the context verbs; one resolution authority whose Bind carries the session's scope; bind-driven injection of the tech stack, catalog and help digests; redaction at the render boundary.
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
- `dadaia context create <name> --main-repo <slug> [--url <url>] [--associated-repos a,b]` registers a DEAD context; a repo with neither a URL (`--url`, `slug=URL`) nor a `repos/<slug>` git checkout is refused, as by `repo add` and `dadaia import`.
- `dadaia context alive <name>` clones every missing repo of the set; the main repo alone gets the canon scaffold folded over `specs/` (never overwriting a file), its scaffold commit and branch restore; associated repos are cloned clean. It is idempotent on an ALIVE context.
- `dadaia context dead <name> [--commit]` preflights the whole set before touching any repo: untracked files refuse without `--commit`, and with it a secret scan blocks on any hit; a repo with local commits and no remote refuses. Then tracked changes are committed and pushed, the branch recorded and every repo removed.
- `alive` and `dead` back-fill every repo's empty URL from its checkout's `origin`; `dead` refuses to remove a repo still URL-less (`fix: git -C repos/<slug> remote add origin <clone-url>`), and `alive` refuses a URL-less missing repo with the `repo remove`+`repo add --url` fix.
- `dadaia context baseline <name> --yes [--push]` makes the first commit of an unborn repo; `dadaia context delete <name>` removes a DEAD context.
- `dadaia context repo add|remove <ctx> <slug>` is idempotent; `dadaia context show <ctx> --json` is the one reader of the repo set.
- A repo slug belongs to one context: `create`, `repo add` and `dadaia import` pass one ownership check; `INV-6` reports any multi-owner slug already on disk ([[workspace-doctor]]).

## Resolution

- `resolve` in `dadaia_workspace/core/invocation.py` answers workspace root, session, context, repo slug, specs dir and the session's `Bind` in one call; the CLI, the container, the gate and ctx-inject each resolve once.
- Rung 0 is caller-supplied (`--context`, or a write target under `repos/<slug>/`), rung 1 `DADAIA_CONTEXT`, rung 2 this session's live record keyed by its harness-native id, rung 3 the repo containing the cwd. Every rung fails soft; with all exhausted, specs-dir resolution raises instead of guessing.
- The workspace root is walked from an explicit target path when one is given, else from the cwd, so every rung shares one root.
- `Bind` is the named context plus every repo slug it owns (main plus associated); `resolve_bind` reads `DADAIA_CONTEXT` then the session record, never the cwd, and an unbound `Bind` owns nothing.
- `dadaia_workspace/core/session_store.py` alone reads and writes `.dadaia/sessions/`; `is_stale` in `dadaia_workspace/core/record_liveness.py` is the one staleness predicate.
- One harness session runs per checked-out tree; a parallel session uses its own linked worktree.

## Binding and injection

- `dadaia context bind <name> [--print-env]` writes one record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`), acquiring nothing; `--print-env` emits `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for `eval $(…)`.
- The ctx-inject hook injects state, never law: a bound session gets its context header, `ARCHITECTURE.md`'s `## Tech Stack` section and the catalog digest (`slug`, `title`, `tldr`, `path` per atom); an unbound session gets `[no bound context]` and the ALIVE-context list.
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
