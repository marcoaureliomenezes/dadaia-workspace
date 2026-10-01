---
slug: context-management
title: context-management
tldr: ALIVE/DEAD registry of a main repo plus associated repos; create clones, hooks and ALIVEs; only context bind binds, by env session id, naming the scope.
summary: Spec Context Projects and their repos through one registry and the context verbs — create as onboarding level 2, alive, dead, the anchor-first append-only publish of the main repo (baseline), the repo set; one resolution authority whose Bind carries the session's scope and whose scope() maps a path to its repo and zone; bind-driven injection of the constitution, tech stack, catalog, open worktrees and help digests; redaction at the render boundary.
tags: [context, lifecycle, session, privacy]
sources:
  - dadaia_workspace/hooks/ctx_inject.py
  - dadaia_workspace/hooks/_common.py
  - dadaia_workspace/core/invocation.py
  - dadaia_workspace/core/context_registry.py
  - dadaia_workspace/core/session_store.py
  - dadaia_workspace/features/spec_context/injection_policy.py
  - dadaia_workspace/features/spec_context/service.py
  - dadaia_workspace/infrastructure/json_context_store.py
  - dadaia_workspace/cli/commands/context.py
---

## Registry

- `.dadaia/states/spec_contexts.json` stores per context its name, state, main repo slug and URL, ordered associated repos (slug + URL), branch and lifecycle timestamps; schema 2 and 3 files read alike, a schema 1 file is refused with `dadaia migrate` as the fix ([[specs-migration]]).
- The main repo is where `specs/` lives and the only specs, bind, memory, release and backlog target; associated repos are working checkouts.
- `dadaia_workspace/core/context_registry.py` reads the registry's entries and their repo slugs for the resolution authority, the layout check and the doctor; `JsonContextStore` reads and writes the same file for the context verbs; an unreadable file resolves no context and admits every name to the layout check ([[workspace-doctor]]).
- `dadaia context create [<name>] --main-repo <url> [--associated-repo <url>]...` is onboarding level 2 in one transactional step: clone every repo into `repos/<slug>/`, install the pre-push hook in each, register the context ALIVE with its branch and print the derived next step; it binds no session — only `context bind` does ([[workspace-init]]).
- One slug rule serves the context name and every repo slug: a URL's last path segment minus `.git`, every character outside `[A-Za-z0-9_-]` replaced by `-` (`my.repo.git` -> `my-repo`); the name defaults to the main repo's slug.
- The record is validated before any clone; a `repos/<slug>` already holding a checkout whose `origin` is that URL is adopted without cloning, any other occupant exits 1 and registers nothing.
- Any failure removes every directory the call created and writes no record, so the corrected command re-runs with the same slug; `create` writes nothing inside a repo but the hook, so the working tree stays clean and HEAD equals the remote's.
- A `create` refusal's `fix:` line reproduces the invocation with every `--associated-repo` kept: a failed clone's URL becomes `<clone-url>`, a taken name becomes `<another-name>`, and a slug another context owns points to `context list` instead.
- The hook installer copies `pre-push-ci-gate.sh` into the `pre-push` hook under `git rev-parse --git-path hooks` where no hook exists, and refreshes one byte-identical to a hook the library shipped (`shipped-hashes.json`; a re-init upgrade refreshes every ALIVE repo, [[workspace-init]]); an operator's own hook is never overwritten, and [[workspace-doctor]]'s `HOOKS-DRIFT-1` names it; `dadaia ci install-hook [--repo <path>] [--force]` is its other caller ([[sdd-gate-v3]]).
- `dadaia context alive <name>` clones every missing repo of the set and installs the hook in each, main and associated alike; a failed clone names `git ls-remote <url>` as its fix; it writes no specs, commits nothing and restores the main repo's recorded branch. It is idempotent on an ALIVE context; a DEAD context (after `dadaia import`) becomes ALIVE ([[context-portability]]).
- `dadaia context dead <name> [--commit]` preflights the whole set before touching any repo, and any refusal touches none: untracked files refuse without `--commit`, and with it the pre-push secret matcher runs in-process over them ([[sdd-gate-v3]]; a hit names `git -C <repo> stash push -u -- <files>`); an unborn repo holding files, a repo with local commits and no remote, a repo with changes to commit and no git identity, and a repo with changes to sync on a branch that is not a work branch of its gitflow (`fix: git -C <repo> checkout -b <work pattern>`) each refuse.
- A repo holding an open `wt/*` worktree (read from `worktree.py`'s rows, [[worktrees]]), a linked worktree, or a local branch carrying commits neither origin nor HEAD holds refuses the whole `dead` with one fix line: the worktree's own `merge` or `clean`, or the push of that branch as tag `archive/<branch>/<sha7>`.
- Then each repo's changes are committed and pushed, the branch recorded and every repo held in `.dadaia/reaped/`; a hold refused (outside the workspace, or holding a linked worktree) exits 1 with that refusal and the context stays ALIVE; the commit never stages an unmerged entry — git's conflict refusal surfaces and no conflict marker is published; a refused push removes nothing and prints git's full output.
- `alive` and `dead` back-fill every repo's empty URL from its checkout's `origin`; `dead` refuses to remove a repo still URL-less (`fix: git -C repos/<slug> remote add origin <clone-url>`); `alive` refuses a URL-less missing repo, main or associated, with `fix: git clone <clone-url> <repos/slug path>` — a checkout placed there is adopted and its origin back-filled.
- `dadaia context baseline <name> [--message <text>]` is onboarding level 3c, the project publication ([[workspace-init]]): invoking it is consent, and it publishes the main repo only — an associated repo publishes by plain `git push` under the pre-push gate.
- Before any write it refuses, one fix line each: no checkout (`<cli> context alive <name>`), no git identity (`git config`), no committable `specs/constitution.md` (`<cli> specs init --context <name>`), a secret in an untracked onboarding file (the publish again, once removed).
- It is append-only and anchor-first: fetch; commit the onboarding paths (`specs/`, `specs-bkp/`, root `AGENTS.md`) off every branch — a detached HEAD, or the unborn clone's first commit — as the onboarding anchor; read the gitflow from that anchor ([[sdd-gate-v3]]); bring the work branch to the anchor, merging an existing local one into it; merge origin's first held of work, integration, principal (unrelated histories only when every root holds only onboarding paths); one atomic `push -u` of the work branch and the missing role branches.
- Births: an empty origin gets the principal and integration branches at the anchor; an origin holding only the principal gets the integration branch at `origin/<principal>`; each is pushed by refspec, no local head created, moved or reset. The anchor never lands on the principal or any other existing branch, and nothing is ever force-checked-out, reset, rebased, force-pushed or deleted.
- An origin lacking the principal is refused after the anchor with `<cli> specs init --context <name> --principal <head>` (the one candidate head, else a `<principal>` placeholder over the listed ones); a fetch, merge or push failure carries git's full output and names the anchor sha HEAD holds; work outside the onboarding paths is never committed, and git refuses a switch or merge it collides with.
- It prints the work branch it published, or `already published — nothing to do` (exit 0, nothing committed or pushed) when the project is published — `origin/<integration>` exists and `specs/constitution.md` is on origin — and HEAD has no unpublished commit.
- `dadaia context delete <name>` removes a DEAD context.
- `dadaia context repo add <ctx> <slug> [--url <url>]` and `dadaia context repo remove <ctx> <slug>` write the registry only, cloning and deleting nothing: re-adding the same slug and URL is a no-op, the same slug with another URL is refused (remove, then add), and a slug with neither a URL nor a `repos/<slug>` git checkout is refused, as by `dadaia import`; `dadaia context show <ctx> --json` is the one reader of the repo set.
- A repo slug belongs to one context: `create`, `repo add` and `dadaia import` pass one validation (name and slugs allowlisted, name new, every slug free); `INV-6` reports any multi-owner slug already on disk ([[workspace-doctor]]).

## Resolution

- `resolve` in `dadaia_workspace/core/invocation.py` answers workspace root, session, context, repo slug, specs dir and the session's `Bind` in one call; the CLI, the container, the gate and ctx-inject each resolve once.
- Rung 0 is caller-supplied (`--context`, or a write target `scope()` gives a repo), rung 1 `DADAIA_CONTEXT`, rung 2 this session's live record keyed by its session id, rung 3 the repo containing the cwd. Every rung fails soft; with all exhausted, specs-dir resolution raises instead of guessing.
- The workspace root is walked from an explicit target path when one is given; otherwise it is the workspace owning the running CLI's venv (`<root>/.dadaia/.venv`), so a fix line runs from any cwd, else the walk from the cwd; every rung shares one root, and a root listed in `DADAIA_FENCED_ROOTS` is never one a process acts on — the gate still protects it ([[sdd-gate-v3]]).
- `scope(root, path)` in `dadaia_workspace/core/invocation.py` is the one path-to-repo decider: `(repo, zone)`, zone `worktree` for `worktrees/<r>/**`, `audit` for `repos/<r>/specs/audits/**`, `repo` for the rest of `repos/<r>/`, else `root`; a slug outside the name grammar is `root`.
- `repo_owner` maps any path `scope()` gives a repo to its owning context, repo slug and main repo slug; the pre-push gate reads an associated repo's gitflow through it ([[sdd-gate-v3]]).
- A context's specs tree is `repos/<main-slug>/specs` whether or not it exists; a context without one has its `specs` onboarding step pending, never redirected to another tree.
- The session id comes from the environment only: `DADAIA_SESSION_ID`, else a harness-native id variable (`CLAUDE_CODE_SESSION_ID`, `CODEX_SESSION_ID`, `CODEX_THREAD_ID`), sanitized; a hook payload's id is never read, so the gate, the hooks and `bind` see one id.
- `Bind` is the named context plus every repo slug it owns (main plus associated); `resolve_bind` reads the session's own live record when it has an id, else `DADAIA_CONTEXT`, never the cwd, and an unbound `Bind` owns nothing.
- `dadaia_workspace/core/session_store.py` alone reads and writes `.dadaia/sessions/`; its `is_live` is the one liveness rule: `last_seen_at` younger than the one-day TTL constant, no creation fallback; the post-gate and ctx-inject renew `last_seen_at`.
- A stale record is deleted by the reaper; an unreadable one is never stale — [[workspace-doctor]] reports it as slop and `--fix` holds it.
- Agents change a repo inside its worktrees under `worktrees/<repo>/`, one session per tree ([[worktrees]]).

## Binding and injection

- `dadaia context bind <name>` writes one record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid, `bound_at`), under the environment's session id, acquiring nothing and minting no id; a shell with no session id exits 1 with `fix: Operator action: export DADAIA_SESSION_ID=<any-stable-id> before opening the session`.
- The ctx-inject hook runs one onboarding call site for bound and unbound sessions alike: a bound session gets its context header, the derived onboarding next step focused on its context while one remains, the context's `specs/constitution.md`, `ARCHITECTURE.md`'s `## Tech Stack` section, the catalog digest (`slug`, `title`, `tldr`, `path` per atom) and its open worktrees in the doctor's rendering; an unbound session gets `[no bound context]`, the same derived step ([[workspace-init]]) and the ALIVE-context list.
- The same hook serves every harness; each speaks its vendor's envelope, built by the one owner `dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py` `envelope` from `DADAIA_HOOK_OUTPUT` (Codex's native `hookSpecificOutput.additionalContext`, Cursor's `additional_context`, Copilot's `additionalContext`), else plain text; the missing-venv message of each ctx-inject wrapper is rendered through the same envelope ([[agentic-entities]]).
- Every emission also carries `.dadaia/agentic/help-digest.md`, which the hook reads and never builds.
- Injection fires once per session — a new session start always injects, whatever an earlier session stamped, and a resume continues — again after a later bind or a compaction, and stays silent on repeat prompts; its sentinel and compact markers live in `.dadaia/tmp/` and are reaped by mtime.
- A MUTATING write into a repo outside the bind's scope is refused with a `fix:` naming the owner's bind, for a bound session and for an unbound one carrying an id ([[sdd-gate-v3]]).

## Redaction

- `dadaia context list`, `dadaia context show` and `dadaia doctor` accept `--redact`, masking every foreign context name and repo slug as a stable placeholder at render time.
- Moving the context set between workspaces is [[context-portability]].

## Runtime state

`.dadaia/states/spec_contexts.json`; `.dadaia/sessions/`; `.dadaia/tmp/ctx-*` markers; `repos/<slug>/`, where only the main repo carries `specs/`.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]], [[context-portability]], [[worktrees]], [[agentic-entities]], [[QUALITY]].
