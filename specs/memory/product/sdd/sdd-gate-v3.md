---
slug: sdd-gate-v3
title: sdd-gate-v3
tldr: No-lock enforcement — root-entry hygiene and SDD write policy before tools; branch, canon and privacy checks at push; a ref gate on raw ref moves.
summary: The two-policy pre-tool gate, path classes and bind scope, fail-open boundaries, one-fix refusal shape, range-scoped git publication chokepoint with its remedy verb, and the reference-transaction ref gate.
tags: [gate, hooks, scope, privacy, git]
sources:
  - dadaia_workspace/hooks/pre_gate.py
  - dadaia_workspace/hooks/root_whitelist.py
  - dadaia_workspace/hooks/sdd_gate.py
  - dadaia_workspace/hooks/translate.py
  - dadaia_workspace/hooks/ref_transaction.py
  - dadaia_workspace/cli/commands/ci.py
  - dadaia_workspace/features/chokepoints/**
  - dadaia_workspace/public/skills/dd-bug-resolution/scripts/privacy_baseline.json
  - dadaia_workspace/infrastructure/git_objects.py
---

## Pre-tool gate

- One entrypoint reads a payload once and evaluates root-whitelist then SDD gate; first block wins. A policy exception or unreadable payload fails open.
- Root-whitelist blocks only a file-tool write that creates a new path the workspace layout classifies as slop. Editing an existing path is not a root-entry creation.
- The SDD gate classifies writes as ADDITIVE, PROTECTED or MUTATING. ADDITIVE zones accept their declared outputs; PROTECTED paths refuse; MUTATING repository writes are scope-checked and repository checkouts accept only the audit exception.
- A bind's scope is its context's main and associated repositories. An identified but unbound session owns none. Worktree paths inherit the owning repository's scope.
- The gate reads no release phase or SDD artifact and acquires no lock. A permitted write records advisory presence only where the harness has a post-tool lane.
- The gate judges file-tool writes only: Claude Code, Codex and Kimi Code register it on their file-editing tools alone, never on the shell tool, and it does not police which Python or CLI executable a shell command invokes. Missing workspace venv wrappers warn and allow.

## Fix contract

- Every BLOCK contains exactly one fix line, in one of three forms: `fix: <command>`, `fix: Agent action: <one act>` for an act an agent performs that no single command does, or `fix: Operator action: <one act>` only for an act the law reserves to the operator (an ADR acceptance, a secret, a `.dadaiaignore` or PROTECTED edit, a named ruling, an act outside agent reach).
- CLI fixes are rendered by the shared command-line builder through the kernel's one spelling, with real values and no placeholder or command chain; a word the host shell cannot spell turns the line into an `Agent action:` naming that word ([[cross-platform-portability]]).
- Root slop points to the agent's dated scratch directory; law and projection paths point to `public install`; the operator's files (`.dadaiaignore`, the privacy denylist) and `[protected]` globs to the command creating the draft directory `.dadaia/tmp`; other state files to the `Agent action:` to use their owning verb or script; an out-of-scope repository points to the owning context bind; merge-only repository writes point to the canonical worktree list.

## Push chokepoint

- The installed pre-push hook invokes `dadaia ci push-gate-check` through the first workspace venv `dadaia` found walking up from the repo root's parent, never the repo's own `.venv`, refusing with the reinstall act when none is found, and reads git's ref lines before network I/O.
- First refusal wins: malformed input; branch policy; specs canon over the net pushed tree; privacy scan over newly published objects.
- Pushable branches are the live work branch and the `wt-rc`, `wt-main` and backlog-lane branches ([[worktrees]]). Principal and integration branches advance by their governed PR paths, apart from empty bootstrap births. With several local work branches the gate warns with that refusal's message and its fix as a hint, and judges the higher, kept one as the work branch.
- The privacy scan combines the operator denylist with the packaged structural baseline, checks paths and text after control-character normalization, scans tags, and never prints an unmasked secret. A baseline pattern may name file paths whose content it skips, never their path: the IPv4 pattern skips generated lock files, whose four-part versions read as addresses.
- Already-published bytes can be amnestied only at the same path with a resolvable base. An unreadable range or git-object failure refuses rather than claiming coverage.
- A denylist or canon refusal's fix is the remedy verb `dadaia ci push-gate-check --repo <repo> --rewrite-from <oldest unpublished commit>`, with `--message <text>` appended when a listed hit sits in a commit message (a tag or detached HEAD gets an `Agent action:` to push a branch; a branch not checked out, its `git switch` first). The verb re-commits HEAD's unpublished range from that commit as one commit holding the tracked working tree, its git calls carrying `DADAIA_WT=1`; it refuses a commit origin holds or HEAD's history lacks, runs only while the push gate lists a denylist or canon finding in that range, only when the working tree differs from HEAD by edits or deletions of listed paths, and takes `--message` only when a commit message is listed. Origin's history is never rewritten.
- The installed reference-transaction hook is a shell shim that judges raw ref moves when git prepares them: a move carrying `DADAIA_WT=1` passes at once; otherwise the first workspace venv interpreter found walking up from the repo root's parent runs `dadaia_workspace.hooks.ref_transaction` from the installed package, and only that module's refusal blocks; the repo's own `.venv` is never searched. The module resolves a zero old sha on a branch line to the ref's current value through one `git rev-parse`, since ref packing hands a zero old sha for refs that exist, so only a missing `wt/*` ref is a creation: it is refused with the `worktree new` fix of `dadaia worktree`, or the reinstall act when that venv holds no runnable `dadaia`; a `wt/*` update and `git pack-refs` pass; any other branch update to a sha other than origin's goes to `dadaia ci ref-gate-check` with its resolved old sha, and only its `[ref-gate] BLOCKED` line blocks. With no interpreter found, an unrunnable CLI or a faulting module the hook warns and lets the update through, an unmarked `wt/*` creation included; the pre-push gate stays the fail-closed chokepoint.
- `dadaia ci ref-gate-check` reads `<old> <new> <ref>` lines on stdin and refuses moving a work-branch ref to a sha other than the one origin holds for it, with `[ref-gate] BLOCKED` and one `Agent action:` to open a tree with the `new` verb of `dadaia worktree` and land the change through its merge; creating a missing work-branch ref at any other sha is refused with the `git branch <work> origin/<work>` fix; a deletion, any other ref, a ref origin does not hold, and a move whose old sha is an ancestor of the new one with every changed path (renames off) under `specs/audits/**` pass; a failed or faulting ancestry or diff read refuses.
- Security review is the reviewer's security lens on each PR head; consumer repositories receive no library CI workflow.

## Dependencies

[[context-management]], [[workspace-doctor]], [[worktrees]], [[agentic-entities]], [[public-asset-distribution]], [[ARCHITECTURE]].
