---
slug: sdd-gate-v3
title: sdd-gate-v3
tldr: No-lock enforcement — three gate blocks (root entry, non-venv command, PROTECTED or out-of-scope write), one fix line per BLOCK, chokepoints at the push.
summary: The merged PreToolUse gate blocks exactly three things and reads no SDD artifact; every refusal anywhere carries one executable fix line; the git chokepoints enforce the publication boundary and the full denylist scan over every pushed path.
tags: [sdd, gate, hooks, enforcement, no-locks, privacy]
---

## PreToolUse

- No lease, mutex, lock file, acquisition or wait path exists; the gate knows no session mode and reads no `_RELEASE.json`, so no phase is ever consulted.
- `hooks/pre_gate.py` reads each payload once and evaluates three policies in order — root whitelist, venv guard, SDD gate — first block wins; a policy that raises is ALLOW.
- The gate blocks exactly three things: a new workspace-root entry (root whitelist — the root law sets plus the instance exception globs, both from `core/workspace_layout.py`, [[workspace-doctor]]); a leading `dadaia`, `pip` or `python -m dadaia_workspace` token outside `.dadaia/.venv/bin/` (venv guard, Bash only, its one rule); a PROTECTED write or a bound session's MUTATING write under a `repos/<slug>/` outside its scope (SDD gate).

| Class | Behavior |
|---|---|
| ADDITIVE | `specs/{bugs,backlog,audits}` at the root or context-relative, `.dadaia/{handoff,tmp,reaped,mcps,.cache}` — the registry's output and ephemeral zones — always writable, bound or not |
| MUTATING | Everything else, `specs/memory/` and `specs/releases/**` included in every phase; scope-judged under `repos/<slug>/` |
| PROTECTED | `.dadaia/sessions/` and the projected law files — fail-closed |

- Three classes, no fourth: a workspace-root path matching no ADDITIVE or PROTECTED prefix is MUTATING; the projected-law origin is decided with zero I/O — basename `DADAIA.md`, `AGENTS.md` or `CLAUDE.md` at the root or a harness-projection dir, both sets from `core/workspace_layout.py` — so a repo's scoped `AGENTS.md` is MUTATING.
- Scope is the bound context's main repo plus its associated repos: `hooks/sdd_gate.py` resolves one `core.invocation.Invocation` per write target and passes its `Bind` (context name + `all_repos()` slugs) and the target's owner to `gate_policy.evaluate` as plain data; the policy module imports nothing from `core.invocation` ([[context-management]]).
- Only `repos/<slug>/` is scope-judged; an unbound session, a slug no context registers and a workspace-root path are never scope-blocked — the gate cannot attribute them and fails open.
- Every BLOCK from every enforcement point — the three gate blocks, `ci push-gate-check`, the release verbs, every error-class doctor rule through its mandatory `fix_help` — carries exactly one `fix: <command>` line naming one executable command, venv-rooted when it is `dadaia`; `tests/contract/test_every_block_carries_a_fix.py` drives each refusal through its public seam and feeds the line back through `pre_gate.evaluate_payload` asserting ALLOW, so a BLOCK whose fix is itself blocked (a Stall) is unrepresentable.
- The fix lines: root entry → append the name to `.dadaia/states/instance_exceptions.txt`; session record → `context bind <ctx>`; projected law → `public stage && public install`; out-of-scope write → `context bind <owner>`; venv → the same command venv-rooted.
- A MUTATING write records nothing about its session; races between sessions surface through git (ADR 0016).
- The PostToolUse hook touches `last_seen_at` and, on one throttle, runs the workspace reaper (`doctor.reap`, which owns marker GC); it never blocks; `bound_at` against the injection sentinel is the only injection trigger ([[context-management]], [[workspace-doctor]]).

## Git chokepoints

- `pre-push-ci-gate.sh` delegates to `ci push-gate-check`, whose refusals are a direct `develop`/`main` push or invalid branch name, a mismatched refspec, an unparseable stdin line, a non-canon `specs/` path, a denylist hit and a git read failure — each one `fix:` line — and it reads no security handoff.
- `refs/heads/feature/{M.m.p}` is the only pushable ref; the patterns `^main$`, `^develop$`, `^feature/\d+\.\d+\.\d+$` have one source in the package plus a POSIX-ERE translation in CI.
- A refspec aiming a local ref at a different remote ref is refused; an unparseable stdin line refuses the push naming `git push --no-verify` as the one bypass, empty stdin being the nothing-to-gate allow.
- The installed hook `.git/hooks/pre-push` is `core/workspace_layout.INSTALLED_GIT_HOOKS`, written by `dadaia ci install-hook` and byte-compared per ALIVE repo by `dadaia doctor` (`HOOKS-DRIFT-1`, [[workspace-doctor]]).
- The security review is a pull-request gate: CI's `security-review` job (the official `anthropics/claude-code-security-review` Action, `CLAUDE_API_KEY` secret) reviews the diff on both edges and is required by the branch ruleset; no verdict file exists in the tree (ADR 0016).
- `features/chokepoints` is three modules — `branch_policy`, `denylist_scan`, `push_gate`.
- `secret-scan.yml` (gitleaks) runs on every PR to `develop` and `main` and is a required status check on `develop`'s branch protection.

### Push-range denylist scan

- The push is the publication boundary: the repository is public, so every tracked path is scanned with the full layer set — no tolerated-pairs list and no path-scoped `exclude_regex` exist, and a test fixture needing a secret shape composes it at runtime from parts (`tests/helpers/privacy_fixtures.py`), never as a tracked literal.
- The scan reads only the objects the push would publish, over `git rev-list --objects <local> --not <remote>` with a `--not --remotes` fallback, before any network I/O; working tree, history and author/committer headers are out of scope.
- It runs last, after branch policy, and is the only policy running on a tag ref.
- Terms come from three additive sources: the operator denylist (`$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, never committed, shared with the bug store's masking loader), the packaged structural baseline (`infrastructure/data/privacy_baseline.json`, its `version` bumped on every change), and the foreign names — registry context names, repo slugs and `repos/` directory names, minus both identities of the pushed repository.
- Amnesty suppresses a hit iff the range has a resolvable base and the exact value was already published at that same path; a new path, a multi-path object, an oversized object and the `--not --remotes` fallback are never amnestied.
- The gate never reports coverage it did not achieve: a git failure, unresolvable prior side, desynchronised stream or absent prior blob refuses; a non-UTF-8 blob is skipped and counted, and a blob over the 5 MB cap is scanned to the cap.
- The refusal names ref, blob path with the match line, short object sha, the term masked to `first…last`, the source layer and the remediation — never the matched line or the unmasked term.

## Dependencies

[[context-management]], [[workspace-doctor]], [[ARCHITECTURE]].
