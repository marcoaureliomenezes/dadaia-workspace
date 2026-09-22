---
slug: context-management
title: context-management
tldr: ALIVE/DEAD registry of one main repo plus N associated repos, one Invocation per process, a Bind carrying scope, bind-driven injection.
summary: Contexts (Spec Context Projects) and their repositories through a v3 registry, one resolution authority whose Bind carries the session's scope, one repo accessor, bind-driven injection.
tags: [context, lifecycle, session, no-locks, privacy]
sources:
  - dadaia_workspace/hooks/ctx_inject.py
  - dadaia_workspace/hooks/_common.py
  - dadaia_workspace/core/invocation.py
  - dadaia_workspace/core/session_store.py
  - dadaia_workspace/core/record_liveness.py
  - dadaia_workspace/features/spec_context/injection_policy.py
  - dadaia_workspace/features/spec_context/markers.py
  - dadaia_workspace/infrastructure/json_context_store.py
  - dadaia_workspace/cli/commands/context.py
---

## Registry

- The registry stores per context its name, main repo slug and URL, the ordered associated repos, state, branch and lifecycle timestamps.
- The main repo is unique and the only specs, bind, memory, release and backlog target; associated repos are working checkouts, reached after it through the one repos accessor.
- `context create` registers a DEAD context, back-filling `repo_url` from the repos catalog.
- `context alive` clones or keeps every repo under `repos/`, restores the branch and folds the canon scaffold over `specs/` without overwriting an existing file; an associated repo is cloned clean and unbound.
- `context dead` requires a clean, pushed state across the set, naming the offender otherwise, scans committed material with `--commit`, records the branch and removes the local repos.
- `context repo add|remove` is idempotent; `context show --json` is the one reader of the repo set (`context repo list` and `context update --url` died at 0.4.7 c8 — a URL is repaired by `alive`, which back-fills from origin, or by delete + `create`).
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

## Redaction, export

- A MUTATING write records nothing; races between sessions surface through git, never through a warning or a block (ADR 0016).
- `context list`, `context show` and `dadaia doctor` accept `--redact`, turning every foreign context name and repo slug into a stable `[REDACTED-CONTEXT-<n>]` placeholder at the render boundary.
- `dadaia export` refreshes each ALIVE repo's checked-out branch, then writes one file, `.dadaia/dist/spec-contexts.json` (`spec-contexts-export-v1`: per context slug, name, state, repo URL, branch, associated repos, last sync); anything else in `dist/` is `WS-dist-slop` ([[workspace-doctor]]).
- `dadaia import <file>` accepts only that schema version, registers each unknown name DEAD with its branch and associated repos, prints `skipped (exists)` for a known name and names `dadaia context alive <name>` as the restore step.

## Freeze

- The context surface is frozen (0.4.7 c6, FR6): no new context verb, no new state file, no new session field; a single-repo context is the degenerate case of multi-repo.
- User-facing vocabulary: **main repo** (where `specs/` lives) and **associated repos** — `context create --main-repo <slug> [--associated-repos a,b]`, `context show --json` keys `main_repo`/`associated_repos`; internal identifiers and the state schema keep their names.

## Bug history (audit 2026-09-20, 0.4.7 c6 FR6)

Window: every `BUGS.jsonl` record whose surface is `spec_context` or whose id/title names
context, bind, presence, heartbeat or ctx — 89 of 514 records (17 CRITICAL, 33 HIGH, 37 MEDIUM,
11 LOW); 63 of them opened in July 2026, 12 in August, 12 in September; 0 open today.

### Weak points, by family (structural reading)

1. **Context resolution had many deciders (38 records).** `specs doctor`, `bugs append`,
   `context show`, `context heartbeat`, `ctx_inject`, the lifecycle runner and the PI adapter
   each resolved "which context am I in" on their own: persisted bind ignored
   (`specs-doctor-ignores-persisted-context-bind`, `bugs-append-ignores-persisted-bind`,
   `context-heartbeat-ignores-persisted-bind`), first-ALIVE fallback stealing the caller's
   context (`first-alive-fallback-violates-caller-owned-context-contract`,
   `ctx-inject-newest-bind-epoch-steals-other-sessions-context`,
   `pi-headless-loads-foreign-context-files`), a context name that differed from its repo slug
   breaking 9 modules (`lifecycle-*-context-created-with-repo-slug-differs-from-name`).
   Fix chain: eight per-verb patches (June–July) were symptom patches; the structural fix was ADR
   0003's one executed-path resolver (`DADAIA_CONTEXT` -> session binding -> repo of cwd,
   `core/invocation.resolve`) in v0.1.72; no resolution bug after 2026-07-26 except
   `sdd-gate-resolves-context-from-cwd-not-written-path` (2026-08-28), fixed at the same seam.
2. **Session identity minted per invocation (11 records, 3 causal chains).**
   `bind-session-id-divergence` -> `bind-alias-dual-record`; `context-bind-session-id-mismatch`
   -> `context-heartbeat-requires-env-after-persisted-bind`; `bind-mode-session-record-keyed-by-
   cli-sid` -> `specs-doctor-ignores-persisted-context-bind`. Every fix that added a second
   record or an alias bred the next bug; the structural fix was one session-id resolution order
   (`DADAIA_SESSION_ID` -> harness id -> payload) and one record per session; the heartbeat verb
   and presence died in 0.4.7 c5, removing the last consumer of the divergence.
3. **Locks, leases and presence (9 records, 5 CRITICAL).** `rebind-does-not-adopt-same-process-
   lease`, `layer1-rebind-adopts-lease-to-synthetic-session-self-block`, `release-for-session-
   misses-unindexed-cross-context-lease`, `doctor-ptr-gc-deletes-valid-lock-free-bind`,
   `no-locks-doctrine-retains-blocking-context-locks`. Each lease fix moved the deadlock; the
   structural fix was deletion: NO-LOCKS (v0.1.75), then advisory presence, then presence itself
   (0.4.7 c5, ADR 0016: one session per checked-out tree). Nothing of the family survives.
4. **Doctor as a second authority over the root and the zones (14 records).** ROOT-1/ROOT-3/
   ROOT-4 contradictions with the law (`doctor-root-whitelist-contradicts-root-law`,
   `doctor-flags-allowed-claude-bridge`, `doctor-root1-flags-env-that-dadaia-md-9-declares-
   canonical`), exit 0 with issues, --fix aborting a pass, walking a symlinked zone into a repo.
   Structural fix: one registry (`workspace_layout.DADAIA_ZONES`, root whitelist as the single
   constant the hook identity-asserts), rendered into `.dadaia/AGENTS.md`; the September doctor
   records are all fail-open/robustness fixes at that one seam, not new authorities.
5. **`alive`/`dead`/`baseline` git side effects (9 records).** Auto-commit needing identity,
   sweeping unrelated worktree changes, refusing the scaffold it just wrote, copying a scaffold
   image past the canon fold (`context-alive-copies-scaffold-image-bypassing-canon-fold` ->
   `scaffold-copytree-route-carries-orphaned-releases-active-md`). The verbs that mutate git
   (`baseline`, `update`, `repo`, `create`, `delete`) are the stale-verb set candidate 7 retires
   into skill scripts; the structural fix is fewer verbs with git effects, not more guards.
6. **Slug ownership (3 records, one chain).** `context-create-accepts-slug-owned-by-another-
   context` -> `context-repo-add-accepts-foreign-context-slug` -> `context-alive-sweeps-
   unrelated-worktree-changes`: ownership was checked per verb. Structural fix landed 2026-08-24
   in the service (one ownership check); FR5's vocabulary (main repo = where `specs/` lives)
   names the invariant those bugs violated.

### Symptom patches, named

`bugs-append-ledger-ignores-context-flag`, `context-show-noarg-ignores-bound-session`,
`context-show-json-traceback-unbound`, `context-list-json-documented-but-unsupported` and
`context-heartbeat-*` each fixed one verb's resolution; they were superseded by the single
resolver and by the death of the verbs. `bind-alias-dual-record` added a second record to fix a
mismatch and is the clearest puxadinho in the ledger.

### Structural fixes still owed (candidate 7 / 8 scope)

- Retire the git-mutating context verbs (`baseline`, `update`, `repo`, `create`, `delete`) into
  the one skill script with one ownership check (c7).
- `init <dir> --harness <name> --repo <url>` creates the first context (done, 0.4.7 c8: `features/workspace/bootstrap.py`
  composes `create`/`alive`/binding); single-repo is the degenerate multi-repo case and has no verb of its own.
- The surface is frozen: no new context verb, no new state file, no new session field.

Bug ids judged: all 89 listed in the audit dataset (`0.4.7 c6 closure log`).

## Runtime state

`.dadaia/states/spec_contexts.json`; `.dadaia/sessions/`; `.dadaia/dist/spec-contexts.json`; `repos/<slug>/`, where only the main repo carries canonical specs.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]], [[QUALITY]].
