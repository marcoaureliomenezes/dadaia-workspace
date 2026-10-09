# Optional: plug your own CI into the repo's verify: lines

Optional depth behind `dd-gitflow-default`. Nothing here is required: the branch contract runs on local git and the repo's tracked `verify:` line alone.
Addressed to an operator who also runs a pipeline of their own.

- Point the pipeline at the same lines the worktree gates run, so one command is the one judge, locally and in the pipeline.
- Two checks turn the branch contract into a machine boundary, each a pre-push hook: a branch-name guard (any ref outside the `gitflow:` names of `specs/constitution.md`: numeric version, no `v`, no suffix) and a direct-push refusal (any push to a branch the skill's §2a table marks not pushable, the message naming the review path instead).
- A check that rejects a change from a source branch outside the skill's §2a table, and the deletion of a stale work branch after a deploy, are the same table read by your own host.
- Keep the branch-name guard and the denylist scan in one job, so a single failure names the rule that fired.
