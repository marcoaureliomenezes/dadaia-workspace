---
slug: context-management
title: context-management
category: product
tldr: ALIVE/DEAD registry of one main repo plus N associated repos, one Invocation resolved per process, bind-driven injection, advisory presence, redactable output.
summary: Spec Context Projects and their repositories through a v3 registry, one resolution authority, one repo accessor, bind-driven injection and expiring presence records.
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

- `core.invocation.resolve()` answers workspace root, session, context, repo slug, specs dir, mode, release and phase in one call; the CLI seam, `container`, the gate and ctx-inject each build one `Invocation` and re-derive nothing.
- Rung 0 is caller-supplied (`--context`, or a write target under `repos/<slug>/`), rung 1 `DADAIA_CONTEXT`, rung 2 this session's record keyed by its harness-native id, rung 3 the repo containing the cwd.
- The workspace root is walked from an explicit `target_path` when one is given and only from the cwd otherwise, so every rung in a call shares one root.
- Rungs 0 and 3 resolve a slug and recover the context name through the registry, falling back to the slug when unregistered.
- Every rung fails soft, and when all are exhausted `resolve_specs_dir` raises rather than guessing.
- One harness session runs per checked-out tree; a parallel session gets its own linked worktree before launch (ADR 0002, `DADAIA.md` §3.3).
- `core.session_store` is the sole reader, writer and toucher of `.dadaia/sessions/`; `core.record_liveness.is_stale` is the one staleness predicate.
- `DADAIA_CONTEXT` is the only environment variable in resolution; `DADAIA_MODE` carries mode and the other `DADAIA_*` variables are hook transport.

## Binding and injection

- `dadaia context bind <context> --mode …` writes one artifact — the caller-owned `.dadaia/sessions/<session-id>.json` carrying context, mode and `bound_at` — acquiring nothing.
- That record is reachable at rung 2 only when keyed by the session's own harness-native id; lacking one, `bind` warns that the `DADAIA_CONTEXT` export is the binding.
- The injection carries state, never law: the tech-stack digest plus the product catalog digest, the ALIVE-context list going only to an unbound session.
- Every emission also attaches the derived CLI help digest (`.dadaia/agentic/help-digest.md`, built by `public install`/`reconcile`/`dadaia help tree --digest`) bind-independent; the hook only reads the file, never builds it.
- The catalog generator persists `tldr` only for atoms in the injected tier, selected by `category`; `slug`, `title` and `path` survive on every entry.
- Specs, bind, memory, releases and backlog resolve only from the main repo, so each doctor and the gate see exactly one `specs/` tree per context.
- READ mode is opt-in self-protection: it blocks this session's mutating writes, leaves additive paths writable, and is never imposed on another session.

## Presence, redaction, export

- Mutating file-tool activity best-effort records advisory presence; a live peer warns, never denies, and records expire by heartbeat age.
- `presence.gc()` is the only reaper — presence records, throttle and sentinel markers, and the directories they empty — called by `doctor --fix` and the PostToolUse reconciler on one throttle; a live session's own record is never touched.
- `context list`, `context show` and `dadaia doctor` accept `--redact`, presence block included, turning every foreign context name and repo slug into a stable `[REDACTED-CONTEXT-<n>]` placeholder at the render boundary.
- `dadaia export` tars durable workspace state under `.dadaia/dist/`, excluding `.env`, caches and cloned `repos/`.
- `dadaia import <archive>` restores contexts as they were, re-cloning through `context alive`.

## Runtime state

`.dadaia/states/spec_contexts.json` and `spec_contexts.v2.bak.json` (pre-migration, byte verbatim); `.dadaia/sessions/`; `.dadaia/states/presence/`; `repos/<slug>/`, where only the main repo carries canonical specs.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]], [[quality-assurance]].
