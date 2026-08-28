---
slug: context-management
title: context-management
category: product
tldr: ALIVE/DEAD registry of one main repo plus N associated repos, one resolution authority, bind-driven injection, advisory presence, redactable output.
summary: Manages Spec Context Projects and their repositories through a v3 registry, a single resolution authority, a single repo accessor, bind-driven memory injection, expiring presence records, and workspace export/import.
tags:
- context
- lifecycle
- session
- no-locks
- privacy
---

## Registry

A Spec Context Project binds one canonical `specs/` tree to one main repository plus any number of
associated repositories. The registry stores name, main repo slug and URL, the ordered
associated-repo collection, state, branch and lifecycle timestamps. The main repo is unique and is
the only specs, bind, memory, release and backlog target; an associated repo is a working checkout
and nothing more. There is no global primary context, and every consumer reaches "this context's
repos" through **one accessor** — main first, then the associated repos in order. The schema is v3,
reached by a backup-first idempotent migration that writes the v2 file verbatim beside it; the read
path tolerates a v2 file.

`context create` registers a DEAD context, back-filling `repo_url` from the repos catalog.
`context alive` clones or keeps every repo of the set under `repos/`, restores the recorded branch
and merges missing scaffold without overwriting — an associated repo is cloned clean, with no
scaffold, no bind and its own `specs/` never read. `context dead` requires a clean, pushed state
across the whole set, naming the offending repo otherwise, scans newly committed material for
secrets with `--commit`, records the branch and removes the local repos. `context repo
add|remove|list` manages the associated collection idempotently; `context update --url` repairs the
remote URL.

**A repo slug is owned by exactly one context.** `repos/<slug>` is a shared namespace and `dead`
destroys every entry of the set it walks, so `create` and `repo add` both consult one ownership
predicate and refuse a slug another context owns, naming the owner. The v2→v3 migration is additive,
so historical collisions are covered by detection instead — the doctor's `INV-6` reports every slug
with more than one owner and never chooses a winner ([[workspace-doctor]]). Concurrent alive/dead
races are not serialized; operations are idempotent where possible and surface ordinary
filesystem/git conflicts.

## Resolution

`core.specs_resolver.resolve_context()` is the single authority answering "which context is this?";
the CLI seam, `container`, the SDD gate and ctx-inject all call it. Rung 0 is caller-supplied (the
`--context` flag, or an explicit write target under `repos/<slug>/`); rung 1 is `DADAIA_CONTEXT`;
rung 2 is this session's own live record, keyed by the harness-native session id; rung 3 is the repo
containing the cwd. Rung 0 is why a write into `repos/x/` is attributed to `x` even under
`DADAIA_CONTEXT=y`. Rungs 0 and 3 resolve a slug and recover the context NAME through the registry,
falling back to the slug when unregistered. Every rung fails soft; when all are exhausted
`resolve_specs_dir` raises rather than guessing. `DADAIA_CONTEXT` is the only environment variable
participating in resolution; `DADAIA_MODE` carries mode, and `WORKSPACE_ROOT`, `DADAIA_RUNTIME`,
`DADAIA_HOOK_OUTPUT`, `DADAIA_HOOK_EVENT` are hook transport.

## Binding and injection

`dadaia context bind <context> --mode …` writes exactly one artifact: the caller-owned record at
`.dadaia/sessions/<session-id>.json`, carrying context, mode and `bound_at`. It writes no
context-global pointer and acquires nothing, and is reachable at rung 2 only when keyed by the
session's own harness-native id; with neither a native id nor `DADAIA_CONTEXT`, `bind` warns that
the export is the binding and `--print-env` emits the export line.

`bound_at` newer than this session's injection sentinel is the sole injection trigger, so a re-bind
— including one to the same context — reaches a live session. **The injection carries state, never a
restatement of the law**: the prefix is the tech-stack digest plus the product catalog digest, with
the ALIVE-context list emitted only to an unbound session. The generator persists the one-line
`tldr` only for atoms in the injected tier (selected by `category`) and drops it for the rest, while
`product/index.md` renders from the full set; `slug`, `title` and `path` survive on every entry.
Specs, bind, memory, releases and backlog resolve only from the main repo, so `specs doctor`,
`backlog doctor` and the SDD gate each see exactly one `specs/` tree per context. READ mode is
opt-in self-protection — it blocks this session's mutating file-tool writes, leaves additive paths
writable, and cannot be imposed on another session.

## Presence, redaction, export

Mutating file-tool activity best-effort records advisory presence; a live peer produces a warning,
never a denial, and records expire by heartbeat age. `context list`, `context show` and
`dadaia doctor` accept `--redact` in table and `--json` form, including the `presence` block: every
context name and repo slug other than the caller's resolved context becomes a stable
`[REDACTED-CONTEXT-<n>]` placeholder, ordinal by first appearance, at the render boundary only
([[quality-assurance]]). `dadaia export` packages the workspace's durable state as a tarball under
`.dadaia/dist/`, excluding `.env`, caches and cloned `repos/`; `dadaia import <archive>` restores
contexts as they were, re-cloning repos through `context alive` and copying associated-repo records
structurally so no field is dropped.

## Runtime state

`.dadaia/states/spec_contexts.json` (registry) and `spec_contexts.v2.bak.json` (pre-migration, byte
verbatim); `.dadaia/sessions/`; `.dadaia/states/presence/`;
`.dadaia/tmp/ctx-inject-fired-<session-id>`; `repos/<slug>/` — ALIVE checkout, only the main repo's
tree carrying canonical specs, and no `.dadaia/` inside any repository.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]],
[[quality-assurance]].
