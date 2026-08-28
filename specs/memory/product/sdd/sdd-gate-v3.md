---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: No-lock enforcement — origin-classified LAW, path/phase/mode gates, phase read from RELEASE.json, git hooks pared to the publication boundary.
summary: The merged Python PreToolUse gate enforces root whitelist, venv and cache posture, path class, phase and caller mode; the git chokepoints enforce only the publication boundary, with a range-scoped privacy denylist scan at push.
tags:
- sdd
- gate
- hooks
- enforcement
- no-locks
- privacy
---

## PreToolUse

The gate constrains unsafe writes without serializing agents: no lease, mutex, lock file, incumbent
pointer, acquisition, adoption, steal or wait path exists. `dadaia_workspace.hooks.pre_gate` reads
each payload once and evaluates three policies in order, first block wins, every block message
carrying the corrected command: the **root whitelist** (file-tool creation of forbidden
workspace-root entries), the **venv + cache guard** (Bash only — leading `dadaia`,
`python -m dadaia_workspace` or `pip` outside `.dadaia/.venv/bin/`, and `pytest`/`ruff`/`mypy`
invocations that would write a cache in-tree, matched on fixed leading tokens with no shell
parsing), and the **SDD gate** (context-relative path class, phase, caller mode).

| Class | Behavior |
|---|---|
| LAW | Projected law files — fail-closed, human-only in an instantiated workspace |
| ADDITIVE | `specs/bugs`, `specs/backlog`, `specs/audits`, workspace reports/handoffs/tmp — writable in any mode |
| MEMORY | Writable only in `DEFINITION` or `CLOSURE` |
| FROZEN | `specs/{backlog,bugs,audits}/_archive/` plus legacy root `specs/_archive/`, matched before the ADDITIVE prefixes; entered only by `git mv` |
| PROTECTED | Session identity records, fail-closed |
| MUTATING | Everything else, writable unless this session resolves to READ mode; `specs/releases/**` throughout |

**LAW is decided by origin on a static fail-closed floor**: basename `DADAIA.md`, `AGENTS.md` or
`CLAUDE.md` **and** a location at the workspace root or in a fixed harness projection directory,
both sets from `core/workspace_layout.py`, with zero I/O on that decision. A path under
`repos/<slug>/` matches neither origin, so a repo's own domain-scoped `AGENTS.md`/`CLAUDE.md` is
MUTATING. MEMORY matches the bare prefix `specs/memory/` with no dotfile carve-out.

**Phase comes from `RELEASE.json` and nothing else**: the live release is the single directory under
`specs/releases/` carrying a `RELEASE.json`, and its top-level `phase` field is read directly
([[sdd-bug-backlog-governance]]). Resolution is fail-closed — zero live releases, more than one, an
unreadable file, or no `phase` all yield an empty phase and deny a MEMORY write. Mode resolves from
the environment, then this session's own record, then `IMPLEMENTATION`; a READ session blocks only
its own mutating writes. The hook never imports the composition root, has no SPEC-override channel,
and reads no approval status or task marker. It calls
`core.specs_resolver.resolve_context()` ([[context-management]]) with the write target as
caller-supplied input, keeping attribution path-first, and best-effort upserts a presence record —
another live record causes one throttled warning and never changes the verdict. The PostToolUse
reconciler reports out-of-scope dirty paths, refreshes presence and never blocks; `bound_at` against
this session's injection sentinel is the only trigger for context-memory injection.

## Git chokepoints

`pre-commit-presence-gate.sh` is advisory-only and always exits 0, warning about another live
session and nothing else. `pre-push-ci-gate.sh` refuses exactly three things: an invalid branch
name, a denylist hit, and an unresolvable runner — it reads no security handoff. The CI preflight is
an always-on rule (`dadaia ci preflight` before every push), not a hook step.

Branch policy at the push boundary is inverted: `refs/heads/feature/{M.m.p}` is the only pushable
ref, and `develop` or `main` is refused with the PR path named. Three branch-name patterns exist —
`^main$`, `^develop$`, `^feature/\d+\.\d+\.\d+$` — with one source in the package and a
cross-referenced POSIX-ERE translation in CI; a refspec aiming a local ref at a different remote ref
is refused. Parsing is fail-closed: an unparseable stdin line refuses the whole push naming
`git push --no-verify` as the one traceable bypass, while empty stdin is the distinct "nothing to
gate" allow.

**The security verdict is a pull-request gate, not a push-time check.** A CI job on both edges
requires an APPROVED `security-reviewer` handoff whose `metrics.commit_sha` is the PR head sha, or
an ancestor whose only intervening diff is committed verdict evidence, read from
`specs/releases/<release-id>/verdicts/<sha>.handoff.json`; an unreadable coverage diff fails closed.
A separate dual qa-plus-security closure gate is the only mechanical check of the qa-engineer
verdict. After a confirmed merge, `dadaia ci gc-push-verdicts --sha <sha>` deletes exactly the
covering verdict handoffs, appending one ledger line before each delete. `secret-scan.yml`
(gitleaks) runs once per release on the ship PR; everything reaching `develop` earlier is covered by
the privacy denylist scan only — a foreign-name/home-path detector, not a secret scanner, a recorded
and accepted gap.

### Push-range denylist scan

The scan reads the **new objects the push would publish** — blobs and commit/annotated-tag bodies
over `git rev-list --objects <local-sha> --not <remote-sha>` (or `--not --remotes` when the remote
sha does not resolve locally) — before any network I/O. The working tree, existing history and
`author`/`committer` headers are out of scope; whole-tree scanning stays in the audit lane. It runs
after branch policy, last; on a tag ref it is the only policy that runs.

Three additive term sources make it never a no-op: the **operator denylist** (literal,
case-insensitive substrings from `$DADAIA_PRIVACY_DENYLIST` or
`.dadaia/states/privacy_denylist.json`, operator-private and never committed — one seam consumed
twice, since the bug ledger masks on the same terms at write time); the **packaged structural
baseline**, version 8 (IP literals, internal hostnames, absolute home paths with `/root`
deliberately uncovered, email addresses and secret-looking tokens, every carve-out carrying a
rationale `public doctor` enforces); and the **foreign names** (registry context names ∪ repo slugs
∪ the directory names under `repos/`, minus both identities of the repository being pushed).

**Prior-published-term amnesty**: where the range has a resolvable base, a hit is suppressed **iff
the exact matched value was already published at that same path** — the same value in a new path
still refuses, and an object reachable at more than one path, an oversized object and the
`--not --remotes` fallback carry no prior text and are never amnestied. The **FROZEN↔scan
invariant** follows from content-addressing: a `git mv` into `_archive/` publishes no new object,
while a document *authored* into an archive is scanned and a rename voids the amnesty.

One rule decides every case: **the gate never reports coverage it did not achieve.** Any git
failure, unresolvable prior side, desynchronised stream or unwired object source refuses; an absent
or oversized prior blob means every hit refuses; a non-UTF-8 blob is skipped and counted; a blob over
the 5 MB cap is scanned to the cap with an oversized note. The refusal is satisfiable and masked —
ref, blob path with the first match's line number, short object sha, the term masked to
`first…last`, the source layer and the remediation, never the matched line or the unmasked term —
and every operator-facing string naming a blob path masks that path's private-name-bearing segments
with the detector's own matchers. Decision logic stays pure: object listing and prior-side
resolution arrive through an injected port.

## Runtime state

`specs/releases/<release-id>/RELEASE.json` (read-only, the phase source);
`.dadaia/states/presence/<context>/<session-id>.json`; `.dadaia/sessions/<session-id>.json`;
`.dadaia/tmp/ctx-inject-fired-<session-id>`;
`.dadaia/logs/{hook-latency,reconciler-events,push-verdict-gc-ledger}.jsonl`, each rotated at write
time by its own writer ([[agent-monitoring]]). Legacy `ctx_locks/` and `sessions/runtime/` are
retired residue that doctor reports and removes.

## Dependencies

[[context-management]], [[workspace-doctor]], [[architecture]].
