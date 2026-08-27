---
slug: context-management
title: context-management
category: product
tldr: ALIVE/DEAD registry of one main repo plus N associated repos, one resolution authority, one repo accessor, lean bind-driven injection, advisory presence.
summary: >-
  Manages Spec Context Projects and their repositories — one unique main repo plus an
  ordered collection of associated repos, resolved everywhere through a single accessor,
  with a backup-first idempotent registry migration to schema v3. ALIVE/DEAD, the surface
  verbs, export/import and the panel all cover the full set; a single branch-resolution
  implementation serves both `list` and `show`, so they cannot disagree. A single
  resolution function
  answers "which context is this?" for every verb, hook and gate; bind persists context
  and mode only for the caller, never acquires a lock, and drives an injection that
  carries memory rather than a restatement of the law, its catalog half curated at
  generation so every atom stays one self-pull away. A registry-wide doctor invariant
  reports a repo slug owned by more than one context without ever choosing a winner. Concurrent work is allowed and
  surfaced through expiring presence records. `list` and `show` accept `--redact` to mask
  foreign context names in table and JSON output.
tags:
- context
- lifecycle
- session
- no-locks
- privacy
last_updated: '2026-08-27'
release_origin: v0.4.5
---

## Purpose

A Spec Context Project binds one canonical `specs/` tree to **one main repository, plus
any number of associated repositories**. The workspace registry stores name, main repo
slug, main repo URL, the ordered associated-repo collection (slug + url each), state,
branch, and lifecycle timestamps. The main repo is unique and is the only specs, bind,
memory, release and backlog target; an associated repo is a working checkout the context
owns and nothing more. There is no global primary context.

Every consumer that needs "this context's repos" resolves through **one accessor** —
main first, then the associated repos in order. The lifecycle verbs, the display verbs,
export and the panel all use it; no second repo-resolution path exists. The registry
schema is v3, reached by a backup-first, idempotent migration that writes the v2 file
verbatim beside it before touching anything and is a proven no-op on re-run; a v3 record
with an empty associated collection behaves exactly as its v2 form did, and the read path
tolerates a v2 file rather than gating on a version it could not repair.

## Lifecycle

- `context create` registers a DEAD context, optionally with associated repos declared
  up front.
- `context alive` clones or keeps **every** repo of the set under `repos/`, idempotently,
  restores the recorded branch, merges missing scaffold files without overwriting existing
  files, and marks the context ALIVE. An associated repo is cloned **clean**: it receives
  no scaffold, no bind, and its own `specs/` — if it has one — is never read by the
  context.
- `context dead` requires a reviewable clean transition across the whole set, refusing
  and naming the offending repo when **any** of them is dirty or unpushed, scans newly
  committed material for secrets when `--commit` is used, records the branch, and removes
  the local repos.
- `context repo add|remove|list` manages the associated collection. Each verb is
  idempotent and fails loudly on an unknown context or slug; `remove` mutates the registry
  only and states what it leaves on disk rather than deleting a checkout silently.
- `context update --url` repairs the remote URL. Alive/dead also backfill an absent URL
  from the repository origin when available.

**A repo slug is owned by exactly one context.** `repos/<slug>` is a namespace every
context shares and `dead` destroys every entry of the set it walks, so both seams that can
introduce a slug from an argument — `create` for the main repo and `repo add` for an
associated one — consult one ownership predicate and refuse a slug another context already
owns, naming the owner. The four other registry writes carry an existing slug forward and
cannot break the invariant.

Enforcement by construction covers new writes; **historical state is covered by
detection**. The v2→v3 migration is purely additive and imports whatever the old registry
said, so a registry that collided before the two seams existed keeps its collision. The
workspace doctor's registry-wide `INV-6` check reads the folded registry and reports every
slug with more than one owner, main or associated ([[workspace-doctor]]). It reports and
stops: which owner should lose the slug is a disposition only the operator holds, and the
verbs to act on it already exist, so no automatic choice is made on the destructive side of
the invariant. With that lane decided, the class has no undecided lane left — two write
seams guarded, historical state surfaced, `dead` untouched.

Concurrent alive/dead races are not serialized. Operations are idempotent where
possible and surface ordinary filesystem/Git conflicts instead of waiting on a lock.

## Usage

`context show` renders main and associated repos — slug, url, on-disk, live branch — in
both table and `--json` form; `context list` carries the associated count in the table and
the full list in `--json`. **`list` and `show` can never disagree on `current_branch`**:
one live branch-resolution implementation serves both, and the stored snapshot, where it
is still meaningful, is exposed under its own distinct field name rather than as
`current_branch`. Export and import round-trip the associated repos (url and branch)
through a structural record copy that cannot silently drop a field it does not know about,
and import's own `alive` re-clones the whole set. The panel's context card lists main and
associated alike, and the CI foreign-slug derivation covers the full set.

## Resolution

`core.specs_resolver.resolve_context()` is the single authority that answers "which
context is this?". Every consumer — the CLI seam, `container`, the SDD gate and the
ctx-inject hook — calls that one function, and the law it implements is its docstring:

| Rung | Input | Meaning |
|---|---|---|
| 0 | caller-supplied | the `--context` flag, or the context derived from an explicit write **target** under `repos/<slug>/` |
| 1 | `DADAIA_CONTEXT` | the environment binding |
| 2 | this session's own **live** record | keyed by the harness-native session id |
| 3 | the repo containing the cwd | `repos/<slug>/…` |

Rungs 1–3 are the law's three rungs in the law's order. Rung 0 is the caller's explicit
input, which is why a write into `repos/x/` is attributed to `x` even while
`DADAIA_CONTEXT=y` — the gate keeps path-first attribution by passing the write target.
Rungs 0 and 3 resolve a repo slug and then recover the context NAME through the
registry — the same inverse lookup covers an **associated** slug, so a walk from inside an
associated checkout resolves the owning context rather than inventing a second one.
The lookup falls back to the slug when it is unregistered. Every rung fails soft;
resolution returns nothing only when all four are exhausted, and `resolve_specs_dir`
then raises rather than guessing from the cwd.

`DADAIA_CONTEXT` is the only environment variable that participates in resolution.
`DADAIA_MODE` carries mode, and `WORKSPACE_ROOT` / `DADAIA_RUNTIME` /
`DADAIA_HOOK_OUTPUT` / `DADAIA_HOOK_EVENT` are hook transport; none of them resolves a
context.

## Binding

`dadaia context bind <context> --mode READ|IMPLEMENTATION|...` writes exactly one
artifact: the caller-owned record at `.dadaia/sessions/<session-id>.json`, carrying the
context, the mode and a `bound_at` timestamp. It writes no context-global incumbent
pointer and acquires nothing.

That record is reachable at rung 2 only when it is keyed by the session's own
harness-native id. When the shell has neither a harness-native session id nor
`DADAIA_CONTEXT`, `bind` prints a loud warning saying the binding is reachable only if
`DADAIA_CONTEXT=<context>` is exported — for a plain shell, and for a harness that
exposes no session id of its own, the environment variable **is** the binding (rung 1).
`bind --print-env` emits that export line.

The record's `bound_at` is also the sole context-memory injection trigger: ctx-inject
re-injects when this session's own `bound_at` is newer than its injection sentinel, so a
re-bind — including a re-bind to the same context — delivers the changed mode or release
to a live session.

**The injection carries state, never a restatement of the law.** A bound session's prefix
is the lean memory bootstrap — the tech-stack digest plus the product catalog digest — and
nothing else: no dispatcher preflight (the law states the flow once, and a session already
carrying the law does not need it a second time per prompt) and no ALIVE-context list,
which is useful only to a session that is **unbound** and is therefore emitted only there.

The catalog half is **curated at generation, not at injection**. The catalog generator
persists the one-line `tldr` only for atoms in the injected tier — selected by the atom's
existing `category` frontmatter field, today `core` — and drops it from the persisted file
for the rest; the in-memory catalog and the rendered `product/index.md` are fed the full,
uncurated set, so `index.md` still carries every atom's `tldr` as a one-step lookup. The
hook's digest logic is unchanged and simply emits the fields present. **Every catalog entry
stays reachable**: `slug`, `title` and `path` survive on every entry, so any atom is one
self-pull away — the policy changes what is *injected*, never what *exists*. The policy
lives in the generator, and both writers of `catalog.json` apply it identically, pinned by a
contract over their written output. The measured prefix on a real bound session is **877.8
tokens** against a ≤0.7k target, down from 1,505.6; the remaining floor is the bounded
tech-stack digest (~564 tokens, outside this lever) plus ~314 tokens of catalog structure
that cannot shrink without dropping an entry's `path`.

**One place of control.** Specs, bind, memory, releases and backlog resolve only from the
main repo. A bind to a context with associated repos injects the **main** repo's memory
alone, and `specs doctor`, `backlog doctor` and the SDD gate each see exactly one `specs/`
tree per context even when an associated repo carries a `specs/` directory of its own.

READ is opt-in self-protection: it blocks this session's mutating file-tool writes while
leaving additive intake paths writable. It cannot impose READ mode on another session.

## Redacted Output

`context list` and `context show` accept `--redact` in both their table and `--json`
forms, including the `presence` block. Every context name and repo slug other than the
caller's resolved context is replaced by a stable `[REDACTED-CONTEXT-<n>]` placeholder,
ordinal by first appearance within one invocation, so the same foreign context carries
the same placeholder everywhere it appears in that output. The caller's own context stays
visible. Redaction applies at the render boundary only — the registry and services keep
returning true names, the default output is unchanged, and the redacted `--json` remains
valid JSON with the same key set, so a machine consumer's parsing contract does not
change. The purpose is authoring hygiene: output pasted into a document must not carry a
foreign Spec Context name ([[quality-assurance]]).

## Presence

Mutating file-tool activity best-effort records advisory presence under
`.dadaia/states/presence/<context>/<session-id>.json`. Live peer presence produces a
warning, never a denial. Records expire by heartbeat age and are garbage-collected by
the gate and workspace doctor.

## Runtime State

- `.dadaia/states/spec_contexts.json` - context registry.
- `.dadaia/sessions/` - caller-owned binding records (context, mode, `bound_at`).
- `.dadaia/states/presence/` - advisory live-session records.
- `.dadaia/tmp/ctx-inject-fired-<session-id>` - per-session injection sentinel.
- `repos/<slug>/` - ALIVE repository checkout; the main repo's tree carries the canonical
  specs, an associated repo's does not.
- `.dadaia/states/spec_contexts.v2.bak.json` - the pre-migration registry, written
  verbatim before the v3 stamp.

No `.dadaia/` directory may exist inside a repository.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]],
[[quality-assurance]].
