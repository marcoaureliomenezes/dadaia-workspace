---
name: codex-push-policy-blocks-required-release-preflight
status: Open
severity: HIGH
reported: 2026-06-18
surface: Codex command policy / release-definition preflight
session_id: null
release: v0.1.15
---

**Symptom:** A release-definition workflow precondition required clean worktrees
to be committed and pushed before any release artifacts were edited. Local
checkpoint commits could be created, but `git push` from Codex was rejected with
`approval required by policy, but AskForApproval is set to Never`. The session
could not satisfy the precondition or proceed to release definition.

**Repro:**
1. In a Codex session with approvals disabled, create or inherit a local
   checkpoint commit that must be pushed before release definition.
2. Run `git push -u origin <current-branch>` from the repo.
3. Observe the harness command-policy rejection before git executes.

**Expected:** dadaia-workspace should provide a deterministic way to satisfy or
record a "commit + push before release definition" preflight under Codex. Either
the generated Codex command policy should support the approved push path, or the
workflow should offer a first-class blocked/preflight handoff that lets the
operator complete the push and resume without ambiguity.

**Notes:** This is not a git remote failure and not an SDD lease conflict. It is
a mismatch between a required release-definition ritual and the available Codex
command policy surface in a no-approval session.
