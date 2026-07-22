# bug-hotfix-doctrine

This rule is always active, for every Layer-1 entry harness and every agent.

## The law — bugs are fixed on the spot, NEVER via a release

Creating a release (SPEC/PLAN/TASKS, grill, task markers, reviewer fan-out — any
release protocol) to fix a bug is **forbidden**. The release-per-bug pattern is
recognized slop: each remediation release historically introduced new bugs,
burned tokens, and trapped operator and agents in an unproductive loop.
Releases exist exclusively for feature work picked from backlog.

When a bug is identified — reported by the operator, by a consumer-side
validation agent, or self-found — the responsible agent executes this flow
**immediately**, in order, with no ceremony in between:

1. **Register** the bug: `dadaia bugs append --event reported ...` (see the
   `bug-registration-guardrail` rule for the event contract and redaction).
2. **Root-cause** it: reproduce against the real tool on the executed path;
   never patch a symptom or add a workaround.
3. **RED** — write the test that reproduces the bug and watch it fail.
4. **Fix** the root cause.
5. **GREEN** — prove the new test passes and the full suite stays green.
6. **Close** the bug: append the `resolved` event carrying the resolution
   evidence (reproducing test, fix, suite result).
7. **Commit** the fix (see the commit gate below) — a solved bug never leaves
   a dirty worktree.
8. **Deliver**: build a new wheel and hand it to the operator's consumer-side
   validator for end-to-end workspace validation.

## Commit gate — a solved bug is ALWAYS committed

A bug is not solved at GREEN — it is solved when the fix is **committed**. The
turn that closes a bug MUST leave a clean worktree: stage and commit every file
the fix touched — source, tests, ledger events, regenerated projections — with
a conventional `fix(...)` message naming the bug id. **No dirty worktree is
allowed after a solved bug**, on any Layer-1 entry harness (Claude Code, Codex,
PI, Kimi Code), in any repo the fix touched.

This is the bug-flow counterpart of the commit gates the ordered workflows
already own: release-definition commits its definition artifacts
(`definition_commit_gate`), closure commits its artifacts, and implementation
preflight BLOCKS on a dirty tree. The bug flow has no Python committer, so this
gate is discipline every agent enforces on itself:

- Commit **before the turn ends** — never "commit later", never hand a dirty
  tree to the next session, workflow, or preflight.
- Commit **only what the fix touched** — never `git add -A` over a tree that
  may carry another session's in-progress work (NO-LOCKS doctrine: the tree is
  shared; your commit must not sweep up foreign changes).
- No new blocking machinery: the pre-commit gate stays WARN-only and the
  pre-push security/CI gates are unchanged — this rule makes "solved bug ⇒
  committed tree" part of the definition of done.

## Approval

The fix is approved only when the operator and the consumer-side validation
agent, after validating the whole workspace, agree it is ok. Internal gates
(`certify` included) passing is never, by itself, validation — a green internal
gate that diverges from real consumer-workspace behavior is itself a bug.

## What stays from the old protocols

- The bugs ledger (ADDITIVE, always writable) — registration is still mandatory
  before the turn ends.
- TDD discipline (RED → fix → GREEN) — mandatory, on the executed path.
- The pre-push security-verdict and CI gates — pushes still obey them; the
  doctrine removes release *ceremony*, not quality *gates*.

## Scope

This doctrine governs **bug fixing**. Feature work — new capability picked from
backlog — still matures through releases per the `release-governance` rule.
When in doubt whether something is a bug or a feature: if the tool violates its
own existing contract, it is a bug — fix it on the spot.
