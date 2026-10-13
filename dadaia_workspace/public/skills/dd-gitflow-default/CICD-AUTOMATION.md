# Optional: plug your own CI into the repo's verify: lines

Optional depth behind `dd-gitflow-default`. Nothing here is required: the branch contract runs on local git and the repo's tracked `verify:` line alone.
Addressed to an operator who also runs a pipeline of their own.

- Point the pipeline at the same lines the worktree gates run, so one command is the one judge, locally and in the pipeline.
- The shipped pre-push hook already refuses a non-canon branch name and a direct push to a non-pushable branch (a pipeline feeds the pre-push ref lines to `.dadaia/.venv/bin/dadaia ci push-gate-check` on stdin).
- A check that rejects a change from a source branch outside the skill's §2a table, and the deletion of a stale work branch after a deploy, are the same table read by your own host.
