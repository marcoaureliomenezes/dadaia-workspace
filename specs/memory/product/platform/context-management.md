---
slug: context-management
title: context-management
category: product
tldr: ALIVE/DEAD registry of one main repo plus N associated repos, one resolution authority, lean bind-driven injection, advisory presence, redactable output.
summary: Manages Spec Context Projects and their repositories through a v3 registry, a single resolution authority, a single repo accessor, bind-driven memory injection, expiring presence records, and workspace export/import.
tags:
- context
- lifecycle
- session
- no-locks
- privacy
---

## Purpose

A Spec Context Project binds one canonical `specs/` tree to one main repository plus any
number of associated repositories. The registry stores name, main repo slug and URL, the
ordered associated-repo collection (slug + url), state, branch and lifecycle timestamps.
The main repo is unique and is the only specs, bind, memory, release and backlog target;
an associated repo is a working checkout and nothing more. There is no global primary
context.

Every consumer resolves "this context's repos" through **one accessor** — main first, then
the associated repos in order. The registry schema is v3, reached by a backup-first,
idempotent migration that writes the v2 file verbatim beside it first; a v3 record with an
empty associated collection behaves exactly as its v2 form, and the read path tolerates a
v2 file.

## Lifecycle

| Verb | Behavior |
|---|---|
| `context create` | registers a DEAD context, optionally with associated repos declared up front; back-fills `repo_url` from the repos catalog when `--url` is omitted |
| `context alive` | clones or keeps every repo of the set under `repos/`, restores the recorded branch, merges missing scaffold without overwriting, marks ALIVE. An associated repo is cloned clean — no scaffold, no bind, its own `specs/` never read |
| `context dead` | requires a clean, pushed state across the whole set, naming the offending repo otherwise; scans newly committed material for secrets with `--commit`; records the branch and removes the local repos |
| `context repo add\|remove\|list` | manages the associated collection idempotently; `remove` mutates the registry only and states what it leaves on disk |
| `context update --url` | repairs the remote URL; alive/dead backfill an absent URL from the origin |

**A repo slug is owned by exactly one context.** `repos/<slug>` is a shared namespace and
`dead` destroys every entry of the set it walks, so both seams that introduce a slug from
an argument — `create` and `repo add` — consult one ownership predicate and refuse a slug
another context owns, naming the owner. The v2→v3 migration is additive and imports
whatever the old registry said, so historical collisions are covered by detection instead:
the workspace doctor's registry-wide `INV-6` reports every slug with more than one owner
and never chooses a winner ([[workspace-doctor]]).

Concurrent alive/dead races are not serialized; operations are idempotent where possible
and surface ordinary filesystem/git conflicts.

## Usage

`context show` renders main and associated repos — slug, url, on-disk, live branch — in
table and `--json` form; `context list` carries the associated count in the table and the
full list in `--json`. One live branch-resolution implementation serves both, so they
cannot disagree on `current_branch`; the stored snapshot is exposed under its own field
name. The panel's context card lists main and associated alike.

`dadaia repos list` reads the static catalog at `.dadaia/agentic/data/repos.xlsx`
(projected from `dadaia_workspace/public/data/repos.xlsx`) and shows slug, URL and
description, so a context can be created from a short slug.

## Resolution

`core.specs_resolver.resolve_context()` is the single authority answering "which context
is this?"; the CLI seam, `container`, the SDD gate and ctx-inject all call it.

| Rung | Input | Meaning |
|---|---|---|
| 0 | caller-supplied | the `--context` flag, or the context derived from an explicit write target under `repos/<slug>/` |
| 1 | `DADAIA_CONTEXT` | the environment binding |
| 2 | this session's own live record | keyed by the harness-native session id |
| 3 | the repo containing the cwd | `repos/<slug>/…` |

Rung 0 is why a write into `repos/x/` is attributed to `x` even under
`DADAIA_CONTEXT=y` — the gate passes the write target and keeps attribution path-first.
Rungs 0 and 3 resolve a slug and recover the context NAME through the registry, and the
same inverse lookup covers an associated slug, falling back to the slug when it is
unregistered. Every rung fails soft; when all are exhausted `resolve_specs_dir` raises
rather than guessing from the cwd.

`DADAIA_CONTEXT` is the only environment variable participating in resolution.
`DADAIA_MODE` carries mode; `WORKSPACE_ROOT`, `DADAIA_RUNTIME`, `DADAIA_HOOK_OUTPUT` and
`DADAIA_HOOK_EVENT` are hook transport.

## Binding and injection

`dadaia context bind <context> --mode READ|IMPLEMENTATION|…` writes exactly one artifact:
the caller-owned record at `.dadaia/sessions/<session-id>.json`, carrying context, mode
and `bound_at`. It writes no context-global pointer and acquires nothing. That record is
reachable at rung 2 only when keyed by the session's own harness-native id; with neither a
native id nor `DADAIA_CONTEXT`, `bind` warns that the export is the binding, and
`bind --print-env` emits the export line.

`bound_at` newer than this session's injection sentinel is the sole injection trigger, so
a re-bind — including one to the same context — reaches a live session. **The injection
carries state, never a restatement of the law**: the prefix is the tech-stack digest plus
the product catalog digest, with the ALIVE-context list emitted only to an unbound
session. The catalog half is curated at generation: the generator persists the one-line
`tldr` only for atoms in the injected tier (selected by the atom's `category` field) and
drops it from the persisted file for the rest, while `product/index.md` is rendered from
the full set. `slug`, `title` and `path` survive on every entry, so every atom stays one
self-pull away. Both writers of `catalog.json` apply the policy identically, pinned by a
contract over their written output.

Specs, bind, memory, releases and backlog resolve only from the main repo: a bind injects
the main repo's memory alone, and `specs doctor`, `backlog doctor` and the SDD gate each
see exactly one `specs/` tree per context. READ mode is opt-in self-protection — it blocks
this session's mutating file-tool writes, leaves additive paths writable, and cannot be
imposed on another session.

## Redacted output

`context list` and `context show` accept `--redact` in table and `--json` form, including
the `presence` block. Every context name and repo slug other than the caller's resolved
context becomes a stable `[REDACTED-CONTEXT-<n>]` placeholder, ordinal by first appearance
within one invocation. Redaction applies at the render boundary only: services keep
returning true names, default output is unchanged, and the redacted `--json` keeps the
same key set ([[quality-assurance]]).

## Presence

Mutating file-tool activity best-effort records advisory presence under
`.dadaia/states/presence/<context>/<session-id>.json`. A live peer produces a warning,
never a denial. Records expire by heartbeat age and are collected by the gate and the
workspace doctor.

## Export and import

`dadaia export [--output DIR] [--include-reports] [--exclude-mnt] [--list]` packages the
workspace's durable state — state files, academy, rules, skills — as
`.dadaia/dist/workspace-<timestamp>.tar.gz`. `.env`, caches and cloned `repos/` are
excluded; HTML reports are opt-in. `dadaia import <archive> [--workspace DEST]
[--skip-mnt] [--skip-activate] [--dry-run]` extracts, patches absolute paths, restores
contexts as they were and re-runs workspace init unless `--skip-activate`. Associated and
main repos are re-cloned by `context alive` after import; export/import round-trip the
associated repos through a structural record copy that cannot silently drop a field.

## Runtime state

- `.dadaia/states/spec_contexts.json` — context registry;
  `.dadaia/states/spec_contexts.v2.bak.json` — the pre-migration file, written verbatim.
- `.dadaia/sessions/` — caller-owned binding records.
- `.dadaia/states/presence/` — advisory live-session records.
- `.dadaia/tmp/ctx-inject-fired-<session-id>` — per-session injection sentinel.
- `repos/<slug>/` — ALIVE checkout; only the main repo's tree carries canonical specs.

No `.dadaia/` directory may exist inside a repository.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]],
[[quality-assurance]].
