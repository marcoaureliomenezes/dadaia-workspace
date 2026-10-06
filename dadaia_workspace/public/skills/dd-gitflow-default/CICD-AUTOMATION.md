# Optional: plug your own CI into the repo's verify: lines

Optional depth behind `dd-gitflow-default`. Nothing here is required: the branch contract runs on local git and the repo's own `verify:`, `verify-stage:` and `verify-task:` lines alone.
Addressed to an operator who also runs a pipeline of their own.

- Point the pipeline at the same lines the worktree gates run, so one command is the one judge, locally and in the pipeline.
- Two checks turn the branch contract into a machine boundary, each a pre-push hook: a branch-name guard (any ref outside the `gitflow:` names of `specs/constitution.md` — `<work>M.m.p`: numeric, no `v`, no suffix) and a direct-push refusal (any push to the integration or principal branch, the message naming the review path instead).
- A check that rejects a change from a source branch outside the skill's §2a table, and the deletion of a stale work branch after a deploy, are the same table read by your own host.
- Keep the branch-name guard and the denylist scan in one job, so a single failure names the rule that fired.
