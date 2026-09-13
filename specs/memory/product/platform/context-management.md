---
slug: context-management
title: context-management
tldr: ALIVE/DEAD registry of one main repo plus N associated repos, one Invocation per process, a Bind carrying scope, bind-driven injection, advisory presence.
summary: Contexts (Spec Context Projects) and their repositories through a v3 registry, one resolution authority whose Bind carries the session's scope, one repo accessor, bind-driven injection and expiring presence records.
tags: [context, lifecycle, session, no-locks, privacy]
---

## Registry

- The registry stores per context its name, main repo slug and URL, the ordered associated repos, state, branch and lifecycle timestamps.
- The main repo is unique and the only specs, bind, memory, release and backlog target; associated repos are working checkouts, reached after it through the one repos accessor.
- `context create` registers a DEAD context, back-filling `repo_url` from the repos catalog.
- `context alive` clones or keeps every repo under `repos/`, restores the branch and folds the canon scaffold over `specs/` without overwriting an existing file; an associated repo is cloned clean and unbound.
- `context dead` requires a clean, pushed state across the set, naming the offender otherwise, scans committed material with `--commit`, records the branch and removes the local repos.
- `context repo add|remove|list` is idempotent, and `context update --url` repairs the remote URL.
- A repo slug is owned by exactly one context: `create` and `repo add` refuse a slug another context owns through one ownership predicate, because `dead` destroys every entry it walks.
- The v2→v3 migration is backup-first and additive, so historical collisions are detected instead — `INV-6` reports every multi-owner slug and never picks a winner ([[workspace-doctor]]).

## Resolution

- `core.invocation.resolve()` answers workspace root, session, context, repo slug, specs dir and the session's own `Bind` in one call; the CLI seam, `container`, the gate and ctx-inject each build one `Invocation` and re-derive nothing — no mode, release or phase is resolved anywhere.
- `Bind` is the context the session named plus every repo slug that context owns (`all_repos()`: main plus associated) — its scope; `resolve_bind` reads `DADAIA_CONTEXT` then this session's live record and never the cwd, so sitting inside a repo is not a bind and an unbound `Bind` owns nothing.
- Rung 0 is caller-supplied (`--context`, or a write target under `repos/<slug>/`), rung 1 `DADAIA_CONTEXT`, rung 2 this session's record keyed by its harness-native id, rung 3 the repo containing the cwd.
- The workspace root is walked from an explicit `target_path` when one is given and only from the cwd otherwise, so every rung in a call shares one root.
- Rungs 0 and 3 resolve a slug and recover the context name through the registry, falling back to the slug when unregistered.
- Every rung fails soft, and when all are exhausted `resolve_specs_dir` raises rather than guessing.
- One harness session runs per checked-out tree; a parallel session gets its own linked worktree before launch (ADR 0002, `DADAIA.md` §3.3).
- `core.session_store` is the sole reader, writer and toucher of `.dadaia/sessions/`; `core.record_liveness.is_stale` is the one staleness predicate.
- `DADAIA_CONTEXT` is the only environment variable in resolution; the other `DADAIA_*` variables are hook transport or the `DADAIA_SESSION_ID` identity override.

## Binding and injection

- `dadaia context bind <context> [--print-env]` is one verb with one argument: it writes one artifact — the caller-owned `.dadaia/sessions/<session-id>.json` carrying context, runtime, pid and `bound_at` — acquiring nothing and requiring no live release; `--print-env` emits `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for the `eval $(…)` flow.
- That record is reachable at rung 2 only when keyed by the session's own harness-native id; lacking one, `bind` warns that the `DADAIA_CONTEXT` export is the binding.
- The injection carries state, never law: the tech-stack digest plus the product catalog digest, the ALIVE-context list going only to an unbound session.
- Every emission also attaches the derived CLI help digest (`.dadaia/agentic/help-digest.md`, built by `public install`/`reconcile`/`dadaia help tree --digest`) bind-independent; the hook only reads the file, never builds it.
- The catalog persists ten keys per atom (`slug title tldr summary path area tags depends_on rank token_estimate`); the injected digest keeps exactly `slug`, `title`, `tldr` and `path` (`hooks/ctx_inject.py::_DIGEST_FIELDS`) — `summary` stays behind.
- Specs, bind, memory, releases and backlog resolve only from the main repo, so each doctor and the gate see exactly one `specs/` tree per context.
- The bind's scope is the only thing it constrains: a bound session's MUTATING write under a `repos/<slug>/` another context owns is refused with `fix: … context bind <owner>`; ADDITIVE paths, workspace-root paths, unregistered slugs and an unbound session are never scope-judged ([[sdd-gate-v3]]).

## Presence, redaction, export

- Mutating file-tool activity best-effort records advisory presence; a live peer warns, never denies, and records expire by heartbeat age.
- `presence.gc()` is the only reaper of presence records, throttle markers, the injection sentinel and the directories they empty; the workspace reaper runs it — `doctor --fix` and, on one throttle, the PostToolUse hook through `doctor.reap(own_session_id=…)` — so a live session's own record is never touched ([[workspace-doctor]]).
- `context list`, `context show` and `dadaia doctor` accept `--redact`, presence block included, turning every foreign context name and repo slug into a stable `[REDACTED-CONTEXT-<n>]` placeholder at the render boundary.
- `dadaia export` refreshes each ALIVE repo's checked-out branch, then writes one file, `.dadaia/dist/spec-contexts.json` (`spec-contexts-export-v1`: per context slug, name, state, repo URL, branch, associated repos, last sync); anything else in `dist/` is `WS-dist-slop` ([[workspace-doctor]]).
- `dadaia import <file>` accepts only that schema version, registers each unknown name DEAD with its branch and associated repos, prints `skipped (exists)` for a known name and names `dadaia context alive <name>` as the restore step.

## Runtime state

`.dadaia/states/spec_contexts.json`; `.dadaia/sessions/`; `.dadaia/states/presence/`; `.dadaia/dist/spec-contexts.json`; `repos/<slug>/`, where only the main repo carries canonical specs.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]], [[QUALITY]].
