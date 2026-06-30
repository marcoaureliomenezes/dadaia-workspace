---
name: context-dead-plain-git-push-fails-mismatched-upstream
status: Closed
severity: MEDIUM
reported: 2026-06-14
session_id: null
surface: dadaia context dead (git sync push)
---

**Symptom:** `dadaia context dead <ctx>` fails during git sync when the local
branch tracks an upstream branch with a different name. The service runs plain
`git push`, which respects `push.default=simple` and exits with:

```text
fatal: The upstream branch of your current branch does not match
the name of your current branch.
```

This was observed with local branch `hotfix/v0.6.4-development` tracking
`origin/development`. The commit had already been pushed explicitly with
`git push origin HEAD:development`, but `context dead` retried plain `git push`
and blocked the DEAD transition.

**Expected:** `dead()` should push to the configured upstream explicitly, or
recognize that the local commit is already contained in the tracked upstream.
The context lifecycle should not depend on a caller's local `push.default`
configuration when the upstream is known.

**Workaround:** set repo-local `push.default=upstream` before retrying
`context dead`, or rename/rebind the branch so the local and upstream branch
names match.
