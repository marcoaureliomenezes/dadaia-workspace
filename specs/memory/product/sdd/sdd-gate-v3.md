---
slug: sdd-gate-v3
title: sdd-gate-v3
tldr: No-lock enforcement — three gate blocks (root entry, non-venv command, PROTECTED or out-of-scope write), one fix line per BLOCK, chokepoints at the push.
summary: The merged PreToolUse gate blocks exactly three things and reads no SDD artifact; every refusal anywhere carries one executable fix line; the pre-push chokepoint enforces the branch contract, the specs canon and the denylist scan over every pushed object, and no CI job calls a model API — the security review is the reviewer's lens before each pull request.
tags: [sdd, gate, hooks, enforcement, no-locks, privacy]
sources:
  - .github/dependabot.yml
  - .github/workflows/ci.yml
  - dadaia_workspace/hooks/__init__.py
  - dadaia_workspace/hooks/pre_gate.py
  - dadaia_workspace/hooks/sdd_gate.py
  - dadaia_workspace/hooks/sdd_post_gate.py
  - dadaia_workspace/hooks/root_whitelist.py
  - dadaia_workspace/hooks/venv_guard.py
  - dadaia_workspace/features/spec_context/gate_policy.py
  - dadaia_workspace/features/chokepoints/**
  - dadaia_workspace/infrastructure/data/privacy_baseline.json
  - dadaia_workspace/cli/commands/ci.py
---

## PreToolUse

- No lease, lock file or wait path exists; the gate knows no session mode and reads no `_RELEASE.json`.
- One pre-gate reads each payload once and evaluates root whitelist, venv guard and SDD gate in that order, first block wins; a policy that raises is ALLOW.
- It blocks exactly three things: a new workspace-root entry outside the root law and `.dadaia/states/instance_exceptions.txt` ([[workspace-doctor]]); a leading `dadaia`, `pip` or `python -m dadaia_workspace` outside `.dadaia/.venv/bin/` (Bash only); a PROTECTED write, or a bound session's MUTATING write into a `repos/<slug>/` outside its scope.

| Class | Behavior |
|---|---|
| ADDITIVE | `specs/bugs/`, `specs/backlog/`, `specs/audits/` at the root or inside a repo, and `.dadaia/{handoff,tmp,reaped,mcps,.cache}/` — always writable, bound or not |
| MUTATING | everything else, `specs/memory/` and `specs/releases/` included; scope-judged under `repos/<slug>/` |
| PROTECTED | `.dadaia/sessions/` and the projected law — `AGENTS.md` at the workspace root or under `.dadaia/` |

- A repo's own `AGENTS.md` is MUTATING; nothing at the root escapes classification.
- Scope is the bound context's main repo plus its associated repos ([[context-management]]); an unbound session, a slug no context registers and a workspace-root path are never scope-blocked.
- Every BLOCK — the three gate blocks, `dadaia ci push-gate-check`, the ledger scripts, every error-class doctor rule — carries exactly one `fix: <command>` line, venv-rooted when it is `dadaia`; `tests/contract/test_every_block_carries_a_fix.py` feeds each fix back through the gate and asserts ALLOW, so a BLOCK whose fix is itself blocked (a Stall) cannot ship.
- The fix lines: root entry → append the name to `.dadaia/states/instance_exceptions.txt`; session record → `dadaia context bind <ctx>`; projected law → `dadaia public stage && dadaia public install`; out-of-scope write → `dadaia context bind <owner>`; venv → the same command venv-rooted.
- The gate returns a decision and its message per write target: a BLOCK's message is its reason, an ALLOW's is empty; there is no advisory channel.
- A BLOCK is one envelope carrying `"decision": "block"` plus Claude Code's `permissionDecision: "deny"`; an ALLOW is an explicit envelope with no permission verdict and no `systemMessage`.
- A MUTATING write records nothing about its session; races between sessions surface through git.
- The PostToolUse hook refreshes the session record's `last_seen_at` and, on a throttle, runs the workspace reaper; it always exits zero ([[workspace-doctor]]).

## Git chokepoints

- `.git/hooks/pre-push` delegates to `dadaia ci push-gate-check`; `dadaia context create` and `context alive` install it in every repo of the set where no hook exists, and `dadaia ci install-hook [--repo <path>] [--force]` installs it into the cwd's repo or the named one, exiting 1 on an existing hook unless `--force` ([[context-management]]); `dadaia doctor` byte-compares the installed hook per ALIVE repo (`HOOKS-DRIFT-1`, one per-repo `fix:` line).
- Policy order, first refusal wins: branch policy — only `refs/heads/feature/<M.m.p>` pushed to the same remote name, `develop` and `main` refused; the `specs/` canon over every `specs/` path the range touches; the denylist scan. An unparseable stdin line refuses, naming `git push --no-verify` as the one bypass; empty stdin allows.
- The security review is the `dd-code-reviewer` security lens on the PR head, run by the main thread before each pull request; no workflow calls a model API. `secret-scan.yml` runs gitleaks on every PR to `develop` and `main`.
- CI's `pr-source-guard` admits into `main` only `develop` and the release-please release PR, and into `develop` only `feature/{M.m.p}` and Dependabot update branches; `.github/dependabot.yml` targets `develop`, so dependency updates reach `main` with the next promote.

### Push-range denylist scan

- The push is the publication boundary: every tracked path is scanned with the full layer set, no path is exempt, and a fixture needing a secret shape composes it at runtime (`tests/helpers/privacy_fixtures.py`).
- It reads only the objects the push would publish (`git rev-list --objects <local> --not <remote>`, `--not --remotes` fallback), tags included, before any network I/O; working tree, history and author headers are out of scope.
- Terms come from the operator denylist (`$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, never committed), the packaged structural baseline (`dadaia_workspace/infrastructure/data/privacy_baseline.json`) and the foreign names — registry context names, repo slugs and `repos/` directory names, minus the pushed repository's own.
- A hit is amnestied only when the range has a resolvable base and the exact value was already published at the same path; a new path, a multi-path object, an oversized object and the fallback range are never amnestied.
- The gate never reports coverage it did not achieve: a git failure or an unresolvable prior side refuses; a non-UTF-8 blob is skipped and counted, a blob over 5 MB is scanned to the cap.
- The refusal names ref, path and line, short object sha, the term masked to `first…last` and the source layer — never the matched line or the unmasked term.

## Dependencies

[[context-management]], [[workspace-doctor]], [[release-lifecycle]], [[ARCHITECTURE]].
