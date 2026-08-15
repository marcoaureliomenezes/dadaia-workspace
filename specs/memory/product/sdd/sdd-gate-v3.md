---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "No-lock SDD enforcement: path/mode gates, advisory presence, and a develop-only, denylist-scanned push boundary that never re-refuses a path's published value."
summary: >-
  The merged Python PreToolUse gate enforces root whitelist, workspace venv usage,
  path class, phase, and the caller's own mode. It never waits for or blocks on another
  session. Presence is advisory. Git pre-commit warns only; pre-push enforces the CI
  preflight, develop-only branch policy, a range-scoped denylist scan of the new objects
  the push would publish, and a security verdict covering the develop delta. The scan
  reads a chunk-bounded batched git conversation, suppresses a hit whose matched value
  the same path already published, derives its foreign-name layer from the context
  registry, partially scans and honestly reports oversized blobs, and masks private
  path segments in everything it prints.
tags:
- sdd
- gate
- hooks
- enforcement
- no-locks
- privacy
token_estimate: 1600
last_updated: '2026-08-15'
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
"nothing to gate" allow. Both shas on a line are shape-validated — 40- or 64-character
hex, or the all-zero deletion sentinel — before they can reach a git argv, so an
option-shaped ref value is a malformed line rather than a successful empty range that
silently skips the scan for that ref. Downstream, revision arguments carry an explicit
`--` end-of-options marker and a sha is prefix-checked before interpolation, so no
supplied value is parsed as a git option. Branch deletions are neither scanned nor verdict-checked. Tag
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
remote-tracking ref can neither over- nor under-scan. Only blob entries are read — through a
batched `git cat-file` conversation rather than one subprocess per object, which is what
keeps a full-history fallback range affordable, and run over **fixed-size chunks of shas**
(500) rather than one buffer per range, so the peak resident set is a constant of the chunk
size and the per-object cap instead of growing with the range. Each blob is decoded as UTF-8
and de-duplicated by object sha across the whole push, then streamed into the matcher rather
than materialised as a list. A deletion ref
publishes no object and is not scanned. The working tree and existing history are out of
scope by design — whole-tree scanning stays in the audit lane.

#### Prior-published-term amnesty

A new blob is not the same thing as a new publication. Where the range has a resolvable
base, every scanned object also carries the **prior published text of its own path**,
resolved at that base inside the same chunk loop through two extra batched calls per chunk —
never one per blob — and the matcher suppresses a candidate hit **iff the exact matched value
occurs, case-insensitively, in that prior text**. Three consequences define the semantics:

- editing a file that already published the matched value at the same path never refuses, so
  the gate never demands a rewrite of content the operator already published;
- the same value introduced into a **new path** still refuses — the amnesty binds to the
  path, not to the value;
- a **new value** in an edited path still refuses, even when a different value of the same
  pattern was already there, because the predicate keys on the matched value itself and never
  on the pattern id or the term layer. That distinction is the whole difference between an
  amnesty and a smuggling path.

In the `--not --remotes` fallback shape there is no single published base, so no object
carries prior text and **no hit is ever suppressed** — a deliberate conservative boundary.
The prior text serves the predicate and is discarded; only the masked term ever leaves the
matcher. The suppression rule is expressed once and applies uniformly to all three term
layers, and the matcher gains no parameter and no new input source to obtain it: the prior
side arrives on the scanned object itself, so the decision logic stays a pure function of the
objects and terms it already receives.

Term sources are additive, and the scan is never a no-op:

1. the **operator denylist** when present — literal, case-insensitive substrings loaded
   from `$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, which are
   operator-private by design and never enter the repository;
2. the **packaged structural baseline** (version 4) — IPv4/IPv6 literals, internal
   hostnames, absolute home paths, email addresses, and secret-looking tokens — with its
   `exclude_regex` carve-outs honored. The carve-out set is: loopback and documentation
   address ranges; `example.*` hosts and the noreply mail domains; RFC-2606 reserved-TLD
   email domains at any subdomain depth; the product's **own synthetic git commit identity**
   host `workspace.local`, as an exact literal in both the internal-hostname pattern and as
   an email domain, because it is a fixture host the product itself injects rather than an
   operator's network; and the stdlib `Path.home` / `pathlib.Path.home` call forms, which the
   internal-hostname pattern would otherwise read as a `.home` hostname. Every carve-out is
   anchored to an exact literal: any other `.local` host, any other subdomain of the
   carved-out host, and any real `.home` hostname still match;
3. the **foreign names** — every Spec Context identity the workspace knows: the registry's
   context names unioned with its repo slugs unioned with the directory names under
   `repos/`, minus **both** identities of the repository being pushed (its context name and
   its repo slug are separate fields and may differ, so subtracting only one would make the
   gate refuse every push of its own repository). Deriving the layer from the registry rather
   than from directories alone is what keeps a DEAD or relocated context protecting its name
   at exactly the lifecycle moment that name becomes more sensitive, not less. The registry
   reaches the CLI through a container seam, and a missing, empty or malformed registry
   degrades to the directory-derived set rather than killing the push hook. Terms match on
   word boundaries so a short name never fires inside a longer word, and
   **case-insensitively**, so a name written with different capitalisation is still caught.
   The whole matcher is case-insensitive on every layer.

With no operator denylist present, layers 2 and 3 still run; the gate names on stderr the
mode it ran in — `operator denylist + baseline` or `baseline only (no operator
denylist)`. The scan runs after branch policy and before the security-verdict lookup, so
a leaking push is refused for the leak rather than for a missing handoff; on a tag ref it
is the only policy that runs.

The boundary between fail-closed and fail-open is explicit:

| Situation | Verdict |
|---|---|
| A term matches and the same path did not already publish that value | refuse |
| `git rev-list` or an object read fails | refuse, naming the git failure |
| The prior-side lookup fails | refuse — an amnesty is never granted from a base the adapter could not read |
| The path is absent at the base, or its prior blob is over the cap or undecodable | no prior content, so every hit on it refuses; absence is explicit and is never an empty string |
| The batch stream desynchronises, or a header field will not parse | abort with the reader's own typed error — no fabricated object is ever yielded, so nothing invented can reach a skip count |
| A blob is not valid UTF-8 | skip that blob, count it, and report the count on the allow and refuse paths alike |
| A blob exceeds the 5 MB per-object cap | scan its first 5 MB and report it as an oversized note; the remainder is never fetched |
| No object source wired into the decision function | refuse at the CLI boundary — the source is a required parameter, so an unwired production path is a defect, not a bypass |

The cap is a partial-coverage fail-open, not a blind spot, and it is reported as one. An
over-cap blob is read through a separate bounded per-object stream that is closed once the
cap's worth of bytes is in hand, so git stops producing and the remainder is genuinely never
fetched, and that prefix is matched like any other content — an oversized text blob whose
first 5 MB carries a term refuses the push. The two skip classes stay separately counted and
separately worded: the binary count covers genuinely undecodable blobs only, while oversized
blobs are carried as structured notes bearing the path, the total size and the scanned bytes,
and rendered as what they are — first 5 MB scanned, remainder **not** scanned, verify by
hand — on the allow path and the refuse path alike. An oversized blob whose prefix is not
valid UTF-8 falls back to the binary count and its wording.

There is no sanctioned-terms or amnesty list anywhere in the product: the amnesty derives
from published git state, and a value the same path never published always blocks. The edge
case that would have demanded such a list — a term already published inside
`specs/_archive/` — is void by construction:

> **FROZEN↔scan invariant.** `specs/_archive/` is FROZEN (`DADAIA.md` §3): it is never
> edited, and it is entered only by `git mv`. A rename creates no new blob — git reuses the
> existing blob object. A tainted archived file therefore can never appear as a *new* object
> of any future pushed range, and the already-published term is amnestied by construction
> rather than by exception list. The invariant holds exactly as long as `_archive/` stays
> FROZEN; if a future release ever edits an archived file, the scan will — correctly —
> refuse the push.

That invariant covers **renames of existing blobs**, and only those. A document *authored*
into `specs/_archive/` — a `CLOSURE.md` written at close time, a QA artifact created in
place — is an ordinary new blob: its content has never been published, the archive path
grants it nothing, and the scan reads it like any other new object. This is correct
behaviour, and it is the reason archive-time documents follow the redaction-at-authoring
doctrine the quality-assurance atom records: a closure that transcribes a diagnostic literal
refuses its own push. The blob-reuse guarantee is a property of `git mv`, not of the directory.

The refusal is satisfiable and masked. Per offending object it names the ref
(`<local-ref> → <remote-ref>`), the blob path with the 1-based line number of the first
match, the short object sha, the term masked to `first…last`, and the source layer
(operator denylist, baseline pattern id, or foreign name). It then names the law it
enforces and the remediation: edit the file, rewrite the offending commits (`--amend`,
interactive rebase, cherry-pick) so no pushed object carries the term, and push again —
the range scope means already-published history never needs a rewrite. The message never
prints the matched line and never prints the term unmasked; at most ten offending objects
are listed, followed by a count of the remainder. `git push --no-verify` remains the
single traceable bypass and is named in the message.

The masking is stated over a class, not a call site: **every operator-facing string the gate
emits that names a blob path masks that path's private-name-bearing segments** — today the
denylist refusal and the oversized note, and any future channel by inheritance. The path is
split on `/` and only the segments matching a term source are replaced, through the same
stdlib-pure primitive in `core/redaction.py` that the `--redact` operator surface consumes
([[architecture]]); the line number, the short sha and every non-matching segment are left
alone, so the operator can still find the file, and a path that matches nothing renders
byte-identically to an unmasked one.

Measured cost on this repository's own content, on the shipped code. The fallback shape —
the whole reachable history a fresh clone presents, 9,095 blobs and 130.29 MB — reads in
1.26 s and matches in 53.87 s: **0.42 s/MB end to end at a 285.5 MiB peak resident set**,
with matching accounting for ~98% of the total. The ordinary resolvable-base range is the
one operators actually meet and is three orders of magnitude cheaper: a 70-blob push costs
~48 ms, about 12 ms of which is the prior-side lookup's two extra batched calls per chunk.
**These are the product's figures; the 2.978 s benchmark recorded in the archived v0.9.0
closure was measured on a synthetic corpus roughly two orders of magnitude smaller than real
content and is superseded, as is the ~1.3 s/MB reading taken before the chunked reader
shipped.** Match throughput is the dominant term and is deliberately left unoptimised: the
shape that pays it is rare and one-time per remote, and replacing the matching engine is its
own engineering effort with its own correctness surface.

Decision logic stays pure: git object listing and prior-side resolution reach it through a
port the CLI injects, never a subprocess inside the decision module ([[architecture]]). The
adapter's parse boundary is typed in both directions — a truncated stream, a non-numeric size
field or a desynchronised header raises the reader's own error rather than letting a raw
parse exception escape or, worse, letting the reader keep parsing content bytes as headers.

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
