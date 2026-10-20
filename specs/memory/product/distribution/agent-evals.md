---
slug: agent-evals
title: agent-evals
tldr: The library's own agent evals — three graded tasks run on the candidate wheel alone by one dispatch-or-schedule workflow.
summary: evals/ holds a cold-onboarding task, a block-list-bug task and a discovery task, each graded by a script on the state the agent leaves; .github/workflows/eval.yml runs each three times on the candidate wheel built from its own checkout, never on a published release, scans every upload for the model secret, and blocks when a gated task falls below its floor.
tags: [evals, ci, release-gate, distribution]
sources:
  - evals/**
  - .github/workflows/eval.yml
---

## Behavior

- `evals/tasks/t1-cold-onboarding/` asks an agent to onboard `file:///srv/demo.git` into a new workspace for Claude Code through to its specs initialized; its grader passes only with one ALIVE context on that URL and `dadaia doctor` clean; when doctor exits non-zero the grader reports its findings instead of crashing.
- `evals/tasks/t2-block-list-bug/` asks an agent to register and fix a block-list bug on the demo project's work branch; its grader passes only when a `BUGS.jsonl` record lands before the fix commit, the tests fail on the pre-fix sha and pass on the fix, the suite is green, and every assertion node under `tests/` at the base (an `assert`, or an `assert*`, `raises` or `warns` call) is still present and unedited at HEAD, wherever it moved, so a removed or edited assert fails in any form.
- `evals/tasks/t3-discovery/` gives an agent a goal and one work item, naming no command, install path or doc URL: `/workspace` itself is the workspace folder; try `dadaia-workspace` on the Git project at `file:///srv/demo.git`, keep using it to organise the work, and the operator wants a `subtract` function with tests for `calc.py`. Its image puts no `dadaia` on `PATH`: it builds a wheelhouse of the run's `requirements.txt`, its dependencies and `uv`, and points pip and uv at that wheelhouse alone (`PIP_NO_INDEX`, `UV_OFFLINE`), so whatever route the agent finds installs the run's build, never what an index serves. Its grader passes only with one ALIVE context on that URL, its specs initialized, `dadaia doctor` with no error for it, and a backlog, in the main repo or one of its worktrees, that passes `backlog.py check` and holds an active entry.
- Each task is a harbor task folder — `instruction.md`, `task.toml`, an `environment/` Dockerfile and a `tests/` grader writing a 0 or 1 reward; T1 and T2 install the run's `requirements.txt` into the image and link `dadaia` onto `PATH`.
- `.github/workflows/eval.yml` runs on `workflow_dispatch` or a weekly `schedule`, on a GitHub-hosted runner, in the `evals` environment: it builds the candidate wheel from its own checkout (the dispatched ref, or `main` on the schedule), writes it and a `requirements.txt` naming it by path into each task's `environment/lib/`, never committed, runs every task three times on it, then compares.
- `evals/scripts/compare.py <candidate jobs>` blocks (exit 1) when the candidate is below its floor on a gated task (`t1-cold-onboarding` 3 of 3, `t2-block-list-bug` 2 of 3, `t3-discovery` 2 of 3); a missing trial is a fail, and the table lists the trials found per task.
- `evals/scripts/scan.py` exits 1 when any file under the uploaded paths holds the model secret's value or an Anthropic token shape; it runs before the upload and the job summary, and a hit uploads nothing.
- The model secret is read only at the job level of the one job that needs it; the `no-model-api-in-ci` guard (`scripts/guards/repo.py`) judges every line of the workflow, and no other workflow calls a model ([[pypi-distribution]], [[QUALITY]] P-33).
- No context carries an evals repo, and the shipped law states no rule about a user's CI.

## Dependencies

[[pypi-distribution]], [[QUALITY]], [[consumer-agent-support]].
