---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: No-lock enforcement — origin-classified LAW, path/phase/mode gates, phase read from _RELEASE.json, git hooks pared to the publication boundary.
summary: The merged PreToolUse gate enforces root whitelist, venv and cache posture, path class, phase and caller mode; the git chokepoints enforce the publication boundary and the denylist scan.
tags: [sdd, gate, hooks, enforcement, no-locks, privacy]
---

## PreToolUse

- No lease, mutex, lock file, acquisition or wait path exists.
- `hooks/pre_gate.py` reads each payload once and evaluates three policies in order — root whitelist (the root law sets plus the instance exception globs, both from `core/workspace_layout.py`, [[workspace-doctor]]), venv + cache guard, SDD gate — first block wins, each block message carrying the corrected command.
- The venv + cache guard is Bash-only on fixed leading tokens: `dadaia`, `python -m dadaia_workspace` or `pip` outside `.dadaia/.venv/bin/`, and a `pytest`/`ruff`/`mypy` run writing a cache in-tree.

| Class | Behavior |
|---|---|
| LAW | Projected law files — fail-closed, human-only |
| ADDITIVE | `specs/{bugs,backlog,audits}`, `.dadaia/{handoff,tmp,mcps,.cache}` — the registry's output and ephemeral zones — any mode |
| MEMORY | Writable only in `DEFINITION` or `CLOSURE` |
| PROTECTED | Session identity records, fail-closed |
| MUTATING | Everything else, unless this session resolves READ; `specs/releases/**` throughout |

- LAW is origin-decided with zero I/O: basename `DADAIA.md`, `AGENTS.md` or `CLAUDE.md` plus a root or harness-projection location, both sets from `core/workspace_layout.py`.
- A path under `repos/<slug>/` matches neither origin, so a repo's scoped `AGENTS.md` is MUTATING; MEMORY matches the bare prefix `specs/memory/` with no dotfile carve-out.
- Phase comes from `_RELEASE.json` alone — the single directory under `specs/releases/` carrying one — fail-closed: zero or several live releases, an unreadable file or a missing `phase` denies the write.
- Mode resolves from the environment, then this session's record, then `IMPLEMENTATION`; a READ session blocks only its own mutating writes.
- The gate builds one `core.invocation.Invocation` per payload and reads context, mode, release and phase off it; it re-derives no fact and never imports the container ([[context-management]]).
- It best-effort upserts a presence record, another live record warning once without changing the verdict.
- The PostToolUse hook renews this session's presence and `last_seen_at`, runs `presence.gc` on one throttle and never blocks; `bound_at` against the injection sentinel is the only injection trigger ([[context-management]]).

## Git chokepoints

- `pre-commit-presence-gate.sh` is advisory-only, always exits 0, and only warns about another live session.
- `pre-push-ci-gate.sh` refuses exactly three things — an invalid branch name, a denylist hit, an unresolvable runner — and reads no security handoff.
- `refs/heads/feature/{M.m.p}` is the only pushable ref; the patterns `^main$`, `^develop$`, `^feature/\d+\.\d+\.\d+$` have one source in the package plus a POSIX-ERE translation in CI.
- A refspec aiming a local ref at a different remote ref is refused; an unparseable stdin line refuses the push naming `git push --no-verify` as the one bypass, empty stdin being the nothing-to-gate allow.
- The security verdict is a pull-request gate: a CI job on both edges requires an APPROVED `security-reviewer` handoff whose `metrics.commit_sha` is the PR head sha, or an ancestor whose only intervening diff is the verdict evidence at `specs/releases/<release-id>/verdicts/<sha>.handoff.json`.
- The dual qa-plus-security closure gate is the only mechanical check of the qa-engineer verdict.
- `features/chokepoints` is four modules — `branch_policy`, `pre_commit`, `push_gate`, `verdict` — and `verdict.covering_verdict(paths, head_sha)` is the single verdict reader the push gate, `specs doctor` and the PR check all call.
- A consumed verdict is deleted by hand after the merge; no GC verb exists.
- `secret-scan.yml` (gitleaks) runs once per release on the ship PR; earlier material is covered only by the denylist scan, an accepted gap.

### Push-range denylist scan

- The scan reads only the objects the push would publish, over `git rev-list --objects <local> --not <remote>` with a `--not --remotes` fallback, before any network I/O; working tree, history and author/committer headers are out of scope.
- It runs last, after branch policy, and is the only policy running on a tag ref.
- Terms come from three additive sources: the operator denylist (`$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, never committed, shared with the bug ledger's masking loader), the packaged structural baseline v8, and the foreign names — registry context names, repo slugs and `repos/` directory names, minus both identities of the pushed repository.
- Amnesty suppresses a hit iff the range has a resolvable base and the exact value was already published at that same path; a new path, a multi-path object, an oversized object and the `--not --remotes` fallback are never amnestied.
- The gate never reports coverage it did not achieve: a git failure, unresolvable prior side, desynchronised stream or absent prior blob refuses; a non-UTF-8 blob is skipped and counted, and a blob over the 5 MB cap is scanned to the cap.
- The refusal names ref, blob path with the match line, short object sha, the term masked to `first…last`, the source layer and the remediation — never the matched line or the unmasked term.

## Dependencies

[[context-management]], [[workspace-doctor]], [[architecture]], [[agent-monitoring]].
