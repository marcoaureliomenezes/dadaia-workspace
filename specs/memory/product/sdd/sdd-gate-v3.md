---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "No-lock SDD enforcement: path/mode gates, advisory presence, and a develop-only, denylist-scanned, security-gated push boundary."
summary: >-
  The merged Python PreToolUse gate enforces root whitelist, workspace venv usage,
  path class, phase, and the caller's own mode. It never waits for or blocks on another
  session. Presence is advisory. Git pre-commit warns only; pre-push enforces the CI
  preflight, develop-only branch policy, a range-scoped denylist scan of the new objects
  the push would publish, and a security verdict covering the develop delta.
tags:
- sdd
- gate
- hooks
- enforcement
- no-locks
- privacy
token_estimate: 1320
last_updated: '2026-08-14'
release_origin: v0.3.0
---

## Purpose

The gate constrains unsafe writes without serializing agents. Races are accepted and
surfaced; no lease, mutex, lock file, incumbent pointer, acquisition, adoption, steal,
or wait path exists in the SDD concurrency design.

## PreToolUse

`dadaia_workspace.hooks.pre_gate` reads each tool payload once and evaluates three
policies in order, first block wins:

1. **root whitelist** blocks file-tool creation of forbidden workspace-root entries;
2. **venv guard** blocks leading Bash invocations of `dadaia`, `python -m
   dadaia_workspace`, or `pip` outside `.dadaia/.venv/bin/`;
3. **SDD gate** evaluates context-relative path class, phase, and caller-owned mode.

Path classes:

| Class | Behavior |
|---|---|
| ADDITIVE | `specs/bugs`, `specs/backlog`, `specs/audits`, and workspace reports/handoffs/tmp are writable. |
| MEMORY | Writable only in `DEFINITION` or `CLOSURE`. |
| FROZEN | Archived specs are never writable — archive by `git mv`. |
| PROTECTED | Session identity records and projected law files are fail-closed. |
| MUTATING | Writable unless this session explicitly resolves to READ mode. |

Mode resolution is environment, then this session's own record, then
`IMPLEMENTATION`. There is no context-global mode or foreign-session fallback. A READ
session blocks only its own mutating writes; it does not affect another session.

## Context Attribution

The gate does not carry a resolution ladder of its own. It calls the shared authority
`core.specs_resolver.resolve_context()` ([[context-management]]) and passes the write's
target path as the caller-supplied input, which keeps attribution **path-first**: a
write under `repos/<slug>/` is attributed to that slug's context even when
`DADAIA_CONTEXT` names another. A write under no repo falls through the remaining law
rungs — the environment, then this session's own live record, then the repo containing
the working directory — so a demonstrably bound session's out-of-repo write belongs to
its own context. The slug reaching the classifier is mapped back to the context NAME
through the registry.

## Presence

A mutating write best-effort upserts
`.dadaia/states/presence/<context>/<session-id>.json`. Another live presence record
causes one throttled warning and never changes the verdict. Presence I/O failure is
swallowed. Stale records are removed opportunistically and by doctor.

The PostToolUse reconciler reports out-of-scope dirty paths and refreshes advisory
presence. It never blocks.

## Git Chokepoints

- `pre-commit-presence-gate.sh` may warn about another live session but always permits
  the commit on concurrency grounds.
- `pre-push-ci-gate.sh` runs the local CI preflight and then applies branch policy, the
  range-scoped denylist scan, and the security verdict, in that order.

Branch policy at the push boundary: `refs/heads/develop` is the only pushable ref. A push
of `main` is refused and named as PR-only from `develop`; a push of a `feature/*` or
`hotfix/*` ref is refused as local-only; a ref outside the four permitted patterns
(`main`, `develop`, `feature/vM.m.p`, `hotfix/vM.m.p` with PATCH ≥ 1) is refused by the
branch-name validator; a local ref that is not a branch head gets its own diagnosis. The
remote side is policed too — a refspec aiming local `develop` at another remote ref is
refused, so only `refs/heads/develop → refs/heads/develop` passes. Parsing is fail-closed:
any unparseable stdin line refuses the whole push and the message names `git push
--no-verify` as the one traceable bypass, while empty stdin remains the distinct
"nothing to gate" allow. Branch deletions are neither scanned nor verdict-checked. Tag
pushes keep their carve-out from the *security verdict* — which is what release
publication depends on — but they are covered by the denylist scan.

Security verdict: an APPROVED `security-reviewer` handoff whose `metrics.commit_sha`
equals the pushed `develop` tip, i.e. a verdict covering the `origin/develop..develop`
delta. Every refusal names the rule that fired, the permitted value, and the corrective
action, so each one is clearable by an action the product accepts.

The push rules are a quality gate, not a concurrency lock. Commits are never blocked for
missing review evidence; pushes are.

### Push-Range Denylist Scan

The push boundary inspects content, not only refs. For every non-deletion ref, tag or
branch, the **new objects the push would publish** are scanned before any network I/O.
The range is computed from the `remote_sha` git itself supplies on the pre-push stdin
line: `git rev-list --objects <local-sha> --not <remote-sha>` when that sha resolves
locally, and `--not --remotes` when it is zero or unresolvable, so a stale or ahead
remote-tracking ref can neither over- nor under-scan. Only blob entries are read, each
decoded as UTF-8 and de-duplicated by object sha across the whole push. A deletion ref
publishes no object and is not scanned. The working tree and existing history are out of
scope by design — whole-tree scanning stays in the audit lane.

Term sources are additive, and the scan is never a no-op:

1. the **operator denylist** when present — literal, case-insensitive substrings loaded
   from `$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, which are
   operator-private by design and never enter the repository;
2. the **packaged structural baseline** (version 2) — IPv4/IPv6 literals, internal
   hostnames, absolute home paths, email addresses, and secret-looking tokens — with its
   `exclude_regex` carve-outs honored, including loopback and documentation address
   ranges, `example.*` hosts, and RFC-2606 reserved-TLD email domains at any subdomain
   depth;
3. the **foreign repo slugs** — the directory names under `repos/`, excluding the slug of
   the repository being pushed, matched on word boundaries so a short slug never fires
   inside a longer word.

With no operator denylist present, layers 2 and 3 still run; the gate names on stderr the
mode it ran in — `operator denylist + baseline` or `baseline only (no operator
denylist)`. The scan runs after branch policy and before the security-verdict lookup, so
a leaking push is refused for the leak rather than for a missing handoff; on a tag ref it
is the only policy that runs.

The boundary between fail-closed and fail-open is explicit:

| Situation | Verdict |
|---|---|
| A term matches | refuse |
| `git rev-list` or an object read fails | refuse, naming the git failure |
| A blob is not valid UTF-8 | skip that blob, count it, and report the count on the allow and refuse paths alike |
| No object source wired into the decision function | refuse at the CLI boundary — the source is a required parameter, so an unwired production path is a defect, not a bypass |

There is no sanctioned-terms or amnesty list anywhere in the product: a new object
carrying a denylisted term always blocks. The edge case that would have demanded one —
a term already published inside `specs/_archive/` — is void by construction:

> **FROZEN↔scan invariant.** `specs/_archive/` is FROZEN (`DADAIA.md` §3): it is never
> edited, and it is entered only by `git mv`. A rename creates no new blob — git reuses the
> existing blob object. A tainted archived file therefore can never appear as a *new* object
> of any future pushed range, and the already-published term is amnestied by construction
> rather than by exception list. The invariant holds exactly as long as `_archive/` stays
> FROZEN; if a future release ever edits an archived file, the scan will — correctly —
> refuse the push.

The refusal is satisfiable and masked. Per offending object it names the ref
(`<local-ref> → <remote-ref>`), the blob path with the 1-based line number of the first
match, the short object sha, the term masked to `first…last`, and the source layer
(operator denylist, baseline pattern id, or foreign slug). It then names the law it
enforces and the remediation: edit the file, rewrite the offending commits (`--amend`,
interactive rebase, cherry-pick) so no pushed object carries the term, and push again —
the range scope means already-published history never needs a rewrite. The message never
prints the matched line and never prints the term unmasked; at most ten offending objects
are listed, followed by a count of the remainder. `git push --no-verify` remains the
single traceable bypass and is named in the message.

Decision logic stays pure: git object listing reaches it through a port the CLI injects,
never a subprocess inside the decision module ([[architecture]]).

## Context Injection

`dadaia context bind` writes the caller's session record. That record's `bound_at`
timestamp, compared against this session's injection sentinel, is the only trigger for
context-memory injection — so a re-bind reaches a live session. An unbound session gets
generic preflight only. A foreign session's bind cannot alter this session's context or
mode.

## Non-Goals

The hook does not read approval status, task markers, or task write sets. It constrains
**what** may be written, never **how** the change was produced — the ordered SDD
sequence is carried by the specs documents and upheld by the agents. It also does not
parse arbitrary shell strings; git chokepoints provide the independent commit/push
boundary.

## Runtime State

- `.dadaia/states/presence/<context>/<session-id>.json`
- `.dadaia/sessions/<session-id>.json`
- `.dadaia/tmp/ctx-inject-fired-<session-id>`
- `.dadaia/logs/hook-latency.jsonl`
- `.dadaia/logs/reconciler-events.jsonl`

Legacy `.dadaia/states/ctx_locks/` and `.dadaia/sessions/runtime/` are retired residue;
doctor reports and removes them.

## Dependencies

[[context-management]], [[workspace-doctor]], [[architecture]].
