---
slug: sdd-gate-v3
title: sdd-gate-v3
tldr: No-lock enforcement — three gate blocks (root entry, non-venv command, PROTECTED or out-of-scope write), one fix line each, a gitflow push chokepoint.
summary: The merged PreToolUse gate blocks exactly three things and reads no SDD artifact; every refusal anywhere carries one executable fix line; the pre-push chokepoint enforces the branch contract read from the project gitflow, the specs canon and one secret registry over every pushed object, with one rewrite formula as its fix, and no CI job calls a model API — the security review is the reviewer's lens before each pull request.
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
- Every BLOCK — the three gate blocks, `dadaia ci push-gate-check`, the ledger scripts, every error-class doctor rule — carries exactly one `fix: <command>` line; every one naming the workspace CLI is built by `fix_line` in `dadaia_workspace/core/cli_line.py` (the absolute venv CLI path, POSIX `shlex` quoting, the Windows form under Windows), and a contract test fails any other module spelling that CLI in a fix position; `tests/contract/test_every_block_carries_a_fix.py` feeds each fix back through the gate and asserts ALLOW, so a BLOCK whose fix is itself blocked (a Stall) cannot ship.
- The fix lines: root entry → append the name to `.dadaia/states/instance_exceptions.txt`; session record → `<cli> context bind <ctx>`; projected law → `<cli> public stage && <cli> public install`; out-of-scope write → `<cli> context bind <owner>`; venv → the agent's own arguments after the builder-spelled CLI.
- The gate returns a decision and its message per write target: a BLOCK's message is its reason, an ALLOW's is empty; there is no advisory channel.
- A BLOCK is one envelope carrying `"decision": "block"` plus Claude Code's `permissionDecision: "deny"`; an ALLOW is an explicit envelope with no permission verdict and no `systemMessage`.
- A MUTATING write records nothing about its session; races between sessions surface through git.
- The PostToolUse hook refreshes the session record's `last_seen_at` and, on a throttle, runs the workspace reaper; it always exits zero ([[workspace-doctor]]).

## Git chokepoints

- `.git/hooks/pre-push` delegates to `dadaia ci push-gate-check`; `dadaia context create` and `context alive` install it in every repo of the set where no hook exists, and `dadaia ci install-hook [--repo <path>] [--force]` installs it into the cwd's repo or the named one, exiting 1 on an existing hook unless `--force` ([[context-management]]); `dadaia doctor` byte-compares the installed hook per ALIVE repo (`HOOKS-DRIFT-1`, one per-repo `fix:` line).
- The branch contract is the project gitflow — the `gitflow: {principal, integration, work}` block of `specs/constitution.md` frontmatter ([[specs-migration]]), read once per push from committed data only: the constitution at HEAD, else the newest one on a local branch or an `origin` remote-tracking ref, else — an associated repo — its owning context's main repo; absent or malformed it is the default (`main`, `develop`, `feature/`) with one stderr warning, never a block.
- Policy order, first refusal wins: branch policy; the `specs/` canon over every `specs/` path the range touches; the denylist scan. An unparseable stdin line refuses, naming `git push --no-verify` as the one bypass; empty stdin allows; `git push origin HEAD` is judged as the checked-out branch.
- Branch policy judges each ref by the remote branch it lands on: a work branch (`<work prefix><M.m.p>`) pushed from the same-named local head passes; the principal or integration branch passes only as a bootstrap birth — a zero remote sha and either an origin holding neither role branch or a ref with no unpublished commit — from any source; every other ref is refused.
- Every branch refusal names the gitflow's own branches: a principal or integration push → `gh pr create --base <branch> --head <integration or work>`; a ref outside the gitflow → switch to (or cut) the live work branch, the last tag + 1 patch; a birth carrying new objects to an origin holding a role branch → birth it at the other role's published tip; a mismatched refspec → rename the local branch.
- A specs-canon or denylist refusal carries one rewrite formula for every unpublished range, a root-reaching one included: `git -C <repo> reset --soft <oldest unpublished commit of the refused ref>`, remove what is listed, `git commit --amend`, push (a branch HEAD is not on is switched to first); a tag or a detached HEAD gets operator-action text; origin's history is never rewritten.
- "Already published" is one rule, `unpublished` (the commits of a ref no `origin` ref holds), shared by births, the rewrite fix and every "unpushed" check.
- The security review is the `dd-code-reviewer` security lens on the PR head, run by the main thread before each pull request; no workflow calls a model API. `secret-scan.yml` runs gitleaks on every PR to `develop` and `main`.
- CI's `pr-source-guard` reads the gitflow of the base branch's committed constitution through the same reader and admits into the principal only the integration branch and `release-please--branches--<principal>`, into the integration branch only work branches and Dependabot update branches; the workflow's push triggers stay literal and a contract test pins them equal to the library's own gitflow. `.github/dependabot.yml` targets the integration branch, so dependency updates reach the principal with the next promote.
- No pre-commit hook enforces the gitflow and no CI workflow is written into a consumer repo.

### Push-range denylist scan

- The push is the publication boundary: every tracked path is scanned with the full layer set, no path is exempt, and a fixture needing a secret shape composes it at runtime (`tests/helpers/privacy_fixtures.py`).
- It reads only the objects the push would publish (`git rev-list --objects <local> --not <remote>`, `--not --remotes` fallback), tags included, before any network I/O; working tree, history and author headers are out of scope.
- Terms come from ONE secret registry: the operator denylist (`$DADAIA_PRIVACY_DENYLIST` or `.dadaia/states/privacy_denylist.json`, never committed) plus the packaged structural baseline (`dadaia_workspace/infrastructure/data/privacy_baseline.json`); `context baseline` and `context dead --commit` run this same matcher in-process over the files they are about to commit ([[context-management]]), so no second secret engine exists; no context name, repo slug or `repos/` directory name is a term source, and the scan reads neither the context registry nor `repos/` — a private name is protected only by listing it in the operator denylist.
- Text is matched after control-character normalization; every pattern also runs against each pushed path, so a key or keystore file (`.pem`, `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`, `.der`) refuses by its name, binary or not, while a public certificate (`.crt`, `.cer`) passes.
- The secret-token pattern refuses an assignment of a secret-named key (password, secret, API key, access token, private key, bearer, AWS secret key; key optionally quoted) to a whole literal — quoted with 8+ characters, or unquoted to the end of the line with an optional `#` comment — plus the vendor token shapes (AWS, GitHub, GitLab, Stripe, OpenAI-style, Slack); references, templates and code expressions pass, and `tests/unit/test_one_secret_matcher.py`'s matrix is that contract.
- Each run prints its scan mode on stderr; with no operator denylist it is `baseline only`, naming both denylist locations.
- A hit is amnestied only when the range has a resolvable base and the exact value was already published at the same path; a new path, a multi-path object, an oversized object and the fallback range are never amnestied.
- The gate never reports coverage it did not achieve: a git failure or an unresolvable prior side refuses; a non-UTF-8 blob is skipped and counted, a blob over 5 MB is scanned to the cap.
- The refusal names ref, path and line, short object sha, the term masked to `first…last` and the source layer — never the matched line or the unmasked term.

## Dependencies

[[context-management]], [[workspace-doctor]], [[release-lifecycle]], [[ARCHITECTURE]].
