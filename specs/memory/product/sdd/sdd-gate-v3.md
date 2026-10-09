---
slug: sdd-gate-v3
title: sdd-gate-v3
tldr: No-lock enforcement combines root-entry hygiene and SDD write policy before tools, then applies branch, specs-canon and privacy checks at push.
summary: The two-policy pre-tool gate, path classes and bind scope, fail-open boundaries, one-fix refusal shape and range-scoped git publication chokepoint.
tags: [gate, hooks, scope, privacy, git]
sources:
  - dadaia_workspace/hooks/pre_gate.py
  - dadaia_workspace/hooks/root_whitelist.py
  - dadaia_workspace/hooks/sdd_gate.py
  - dadaia_workspace/cli/commands/ci.py
  - dadaia_workspace/features/chokepoints/**
  - dadaia_workspace/infrastructure/data/privacy_baseline.json
  - dadaia_workspace/infrastructure/git_objects.py
---

## Pre-tool gate

- One entrypoint reads a payload once and evaluates root-whitelist then SDD gate; first block wins. A policy exception or unreadable payload fails open.
- Root-whitelist blocks only a file-tool write that creates a new path the workspace layout classifies as slop. Editing an existing path is not a root-entry creation.
- The SDD gate classifies writes as ADDITIVE, PROTECTED or MUTATING. ADDITIVE zones accept their declared outputs; PROTECTED paths refuse; MUTATING repository writes are scope-checked and repository checkouts accept only the audit exception.
- A bind's scope is its context's main and associated repositories. An identified but unbound session owns none. Worktree paths inherit the owning repository's scope.
- The gate reads no release phase or SDD artifact and acquires no lock. A permitted write records advisory presence only where the harness has a post-tool lane.
- Missing workspace venv wrappers warn and allow; the gate does not police which Python or CLI executable a shell command invokes.

## Fix contract

- Every BLOCK contains exactly one `fix: <command>` or `fix: Operator action: <one act>`.
- CLI fixes are rendered by the shared command-line builder, with real values and no placeholder or command chain.
- Root slop points to the agent's dated scratch directory; protected projection and law paths point to the owning install or operator action; an out-of-scope repository points to the owning context bind; merge-only repository writes point to the canonical worktree list.

## Push chokepoint

- The installed pre-push hook invokes `dadaia ci push-gate-check` and reads git's ref lines before network I/O.
- First refusal wins: malformed input; branch policy; specs canon over the net pushed tree; privacy scan over newly published objects.
- Pushable branches are the live work branch, release job branches and backlog branches. Principal and integration branches advance by their governed PR paths, apart from empty bootstrap births.
- The privacy scan combines the operator denylist with the packaged structural baseline, checks paths and text after control-character normalization, scans tags, and never prints an unmasked secret.
- Already-published bytes can be amnestied only at the same path with a resolvable base. An unreadable range or git-object failure refuses rather than claiming coverage.
- Security review is the reviewer's security lens on each PR head; consumer repositories receive no library CI workflow.

## Dependencies

[[context-management]], [[workspace-doctor]], [[worktrees]], [[agentic-entities]], [[public-asset-distribution]], [[ARCHITECTURE]].
