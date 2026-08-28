---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: No-lock enforcement — origin-classified LAW, path/phase/mode gates, phase from the RELEASE.jsonl fold, git hooks pared to the publication boundary.
summary: The merged Python PreToolUse gate enforces root whitelist, venv and cache posture, path class, phase and caller mode; the git chokepoints enforce only the publication boundary, with a range-scoped privacy denylist scan at push.
tags:
- sdd
- gate
- hooks
- enforcement
- no-locks
- privacy
---

## Purpose

The gate constrains unsafe writes without serializing agents. No lease, mutex, lock file,
incumbent pointer, acquisition, adoption, steal or wait path exists.

## PreToolUse

`dadaia_workspace.hooks.pre_gate` reads each tool payload once and evaluates three policies in
order, first block wins:

1. **Root whitelist** — blocks file-tool creation of forbidden workspace-root entries.
2. **Venv + cache guard** (Bash only) — venv-rooting blocks leading invocations of `dadaia`,
   `python -m dadaia_workspace` or `pip` outside `.dadaia/.venv/bin/`; the cache guard blocks
   `pytest` without `-p no:cacheprovider`, `ruff check`/`ruff format` without `--no-cache`, and
   `mypy` without a `--cache-dir` redirect. Both match fixed leading tokens only, with no shell
   parsing, and every block message carries the corrected command.
3. **SDD gate** — context-relative path class, phase, and the caller's own mode.

### Path classes

| Class | Behavior |
|---|---|
| LAW | Projected law files — fail-closed, human-only in an instantiated workspace |
| ADDITIVE | `specs/bugs`, `specs/backlog`, `specs/audits` and workspace reports/handoffs/tmp, writable in any mode |
| MEMORY | Writable only in `DEFINITION` or `CLOSURE` |
| FROZEN | `specs/{backlog,bugs,audits}/_archive/` plus the legacy root `specs/_archive/`, matched before the ADDITIVE prefixes; entered only by `git mv` |
| PROTECTED | Session identity records, fail-closed |
| MUTATING | Everything else, writable unless this session resolves to READ mode; `specs/releases/**` throughout, `_ideas/` and `releases/_archive/` included |

**LAW is decided by origin on a static fail-closed floor.** A path is LAW when its basename is
`DADAIA.md`, `AGENTS.md` or `CLAUDE.md` **and** it sits at the workspace root or in a fixed
harness projection directory (`.claude/rules`, `.codex`, `.kimi-code`, `.agents`); both sets
come from `core/workspace_layout.py`. `classify_path` performs zero I/O on that decision, and
`.dadaia/agentic/manifest.json` classifies UNGATED. A path under `repos/<slug>/` matches
neither origin, so a repo's own domain-scoped `AGENTS.md`/`CLAUDE.md` is MUTATING.

**MEMORY covers dotfiles**: the classifier matches the bare prefix `specs/memory/`, with no
carve-out. The gate reads no SDD artifact and has no SPEC-override channel.

**Phase comes from the `RELEASE.jsonl` fold and nothing else.** The gate locates the live
release as the single directory under `specs/releases/` carrying a `RELEASE.jsonl`, parses it
with the same stdlib parser the doctor uses, and takes the last `phase` record
([[sdd-bug-backlog-governance]]). Resolution is fail-closed: zero live releases, more than one,
an unreadable file, or no `phase` record all yield an empty phase and deny a MEMORY write. The
hook never imports the composition root.

Mode resolves from the environment, then this session's own record, then `IMPLEMENTATION`. A
READ session blocks only its own mutating writes.

## Attribution and presence

The gate carries no resolution ladder of its own: it calls
`core.specs_resolver.resolve_context()` ([[context-management]]) passing the write target as
caller-supplied input, keeping attribution path-first.

A mutating write best-effort upserts `.dadaia/states/presence/<context>/<session-id>.json`.
Another live record causes one throttled warning and never changes the verdict; presence I/O
failure is swallowed. The PostToolUse reconciler reports out-of-scope dirty paths, refreshes
presence and never blocks.

## Git chokepoints

- `pre-commit-presence-gate.sh` is advisory-only and **always exits 0**; it may warn about
  another live session and warns about nothing else.
- `pre-push-ci-gate.sh` refuses exactly three things: an invalid branch name, a denylist hit,
  and an unresolvable runner. It reads no security handoff.
- The CI preflight is an always-on rule (`dadaia ci preflight` before every push), not a hook
  step; its advertised check list and CI's gating list are pinned as one set by a parity test.

Branch policy at the push boundary is inverted: `refs/heads/feature/{M.m.p}` is the only
pushable ref, and `develop` or `main` is refused with the PR path named. Three branch-name
patterns exist — `^main$`, `^develop$`, `^feature/\d+\.\d+\.\d+$` — with one source in the
package and a cross-referenced POSIX-ERE translation in CI. A refspec aiming a local ref at a
different remote ref is refused. Parsing is fail-closed: an unparseable stdin line refuses the
whole push naming `git push --no-verify` as the one traceable bypass, while empty stdin is the
distinct "nothing to gate" allow. Both shas per line are shape-validated (40- or 64-character
hex, or the all-zero deletion sentinel) before reaching a git argv, revision arguments carry
`--`, and deletions publish no object and are not scanned.

**The security verdict is a pull-request gate, not a push-time check.** A CI job on both edges
requires an APPROVED `security-reviewer` handoff whose `metrics.commit_sha` is the PR head sha,
or an ancestor whose only intervening diff is committed verdict evidence. The evidence is
committed at `specs/releases/<release-id>/verdicts/<sha>.handoff.json`, the release id is
constrained to the release-id canon before it reaches a path, and the coverage diff is read
through a checked exit status so an unreadable diff fails closed. A separate dual
qa-plus-security closure gate reads `release_id` and context at a different moment and is the
only mechanical check of the qa-engineer verdict.

After a confirmed merge the ship flow runs `dadaia ci gc-push-verdicts --sha <sha>`, which
deletes exactly the verdict handoffs covering those shas. One line — reviewing agent, verdict,
covered sha, timestamp — is appended to the append-only
`.dadaia/logs/push-verdict-gc-ledger.jsonl` **before** each delete; a failed append leaves the
handoff in place. The verb is idempotent and exits 0 when nothing matches.

`secret-scan.yml` (gitleaks) triggers on a `main` push and a `main` pull request, so it runs
once per release on the ship PR. Everything reaching `develop` earlier is covered by the
privacy denylist scan only — a foreign-name/home-path detector, not a secret scanner. That is a
recorded, accepted gap.

### Push-range denylist scan

For every non-deletion ref the scan reads the **new objects the push would publish**, before
any network I/O. The range is `git rev-list --objects <local-sha> --not <remote-sha>` when the
remote sha resolves locally, and `--not --remotes` otherwise. Blob entries **and**
commit/annotated-tag objects are read through a batched `git cat-file` conversation over fixed
500-sha chunks, decoded as UTF-8, de-duplicated by object sha and streamed into the matcher.
The working tree and existing history are out of scope; whole-tree scanning stays in the audit
lane. A commit **body** is scanned; `author`/`committer` headers are out of scope by design.

**Prior-published-term amnesty.** Where the range has a resolvable base, each scanned object
also carries the prior published text of its own path, and a hit is suppressed **iff the exact
matched value was already published at that same path**. The same value in a new path still
refuses; a new value in an edited path still refuses. Suppression is decided per layer in that
layer's own semantics — operator denylist by case-insensitive literal substring, a baseline
pattern by re-running the same anchored pattern over the prior text and comparing matched
values, a foreign name by its own `\bname\b` search. An object reachable at more than one path
in the range, an oversized object, and the `--not --remotes` fallback shape carry no prior text
and are never amnestied.

Term sources are additive and the scan is never a no-op:

1. the **operator denylist** — literal, case-insensitive substrings from
   `$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, operator-private and
   never committed. That loader is one seam consumed twice: the push boundary refuses on these
   terms and the bug ledger masks them at write time ([[sdd-bug-backlog-governance]]).
2. the **packaged structural baseline**, version 8 — IPv4/IPv6 literals, internal hostnames,
   absolute home paths (POSIX `/home/<user>`, macOS `/Users/<name>`, Windows
   `<drive>:\Users\<name>`; `/root` deliberately uncovered), email addresses and secret-looking
   tokens, with `exclude_regex` carve-outs honored. Every pattern is single-line, every
   carve-out carries a rationale enforced by `public doctor`'s baseline-rationale check, and the
   version bumps with the pattern set.
3. the **foreign names** — the registry's context names unioned with its repo slugs and the
   directory names under `repos/`, minus both identities of the repository being pushed. A
   missing, empty or malformed registry degrades to the directory-derived set with exactly one
   stderr note. A name matches as a whole token, case-insensitively.

With no operator denylist present, layers 2 and 3 still run and the gate names its mode on
stderr. The scan runs after branch policy and is the last policy step; on a tag ref it is the
only policy that runs. One rule decides every row: **the gate never reports coverage it did not
achieve.**

| Situation | Verdict |
|---|---|
| A term matches and the same path did not already publish that value | refuse |
| `git rev-list`, an object read, or the prior-side lookup fails | refuse, naming the git failure |
| The path is absent at the base, or its prior blob is over the cap or undecodable | no prior content — every hit refuses; absence is explicit, never an empty string |
| git answers the documented `<base>:<path> missing` | ordinary absence, recognised by the `missing` suffix |
| The batch stream desynchronises or a header will not parse | abort with the reader's typed error; no fabricated object is yielded |
| A blob is not valid UTF-8 | skip, count, and report the count on allow and refuse alike |
| A blob exceeds the 5 MB per-object cap | scan the first 5 MB and report an oversized note |
| A bounded oversized read delivers fewer than the cap's bytes | raise the typed read error |
| A commit or annotated-tag body matches | refuse — path-less objects are never amnestied |
| No object source wired into the decision function | refuse at the CLI boundary |

**FROZEN↔scan invariant.** An `_archive/` subtree is entered only by `git mv`; git is
content-addressed, so relocating an unchanged file publishes no new object and an
already-published term stays amnestied. A document *authored* into an archive is an ordinary new
blob and is scanned, and a rename voids the amnesty; the response is `dadaia ci push-gate-check`
over the range plus remediation at each hit's source record, never `--no-verify` and never an
exclusion. The repository's own self-scan sentinel scans an archive-prefixed path iff its blob
sha is absent from `HEAD^`'s tree, degrading to plain exclusion when `HEAD^` is unavailable.

The refusal is satisfiable and masked. Per offending object it names the ref, the blob path with
the 1-based line number of the first match, the short object sha, the term masked to
`first…last`, the source layer, and the remediation. It never prints the matched line or the
unmasked term, lists at most ten objects plus a remainder count, and names `--no-verify` as the
single traceable bypass. **Every operator-facing string the gate emits that names a blob path
masks that path's private-name-bearing segments**, using the detector's own compiled matchers, so
detector-hit implies masker-hit. The `--redact` CLI surface keeps its own placeholder shape and
its own primitive in `core/redaction.py` ([[architecture]]). A failed object read carries the
offending path as a structured field, never inside its message. Decision logic stays pure: git
object listing and prior-side resolution arrive through a port the CLI injects.

## Context injection

`dadaia context bind` writes the caller's session record; that record's `bound_at` against this
session's injection sentinel is the only trigger for context-memory injection. An unbound session
gets generic preflight only, and a foreign session's bind cannot alter this session's context or
mode.

## Non-goals

The hook reads no approval status, task marker or task write set, and exactly one SDD artifact —
the live release's `RELEASE.jsonl`, for the phase. It constrains what may be written, never how
the change was produced, and parses no arbitrary shell string. No new blocking validation enters
this surface.

## Runtime state

- `specs/releases/<release-id>/RELEASE.jsonl` — read-only, the phase source
- `.dadaia/states/presence/<context>/<session-id>.json`,
  `.dadaia/sessions/<session-id>.json`, `.dadaia/tmp/ctx-inject-fired-<session-id>`
- `.dadaia/logs/{hook-latency,reconciler-events,push-verdict-gc-ledger}.jsonl` — each rotated
  at write time by its own writer ([[agent-monitoring]])
- Legacy `.dadaia/states/ctx_locks/` and `.dadaia/sessions/runtime/` are retired residue that
  doctor reports and removes.

## Dependencies

[[context-management]], [[workspace-doctor]], [[architecture]].
