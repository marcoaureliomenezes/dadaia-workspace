---
slug: agent-evals
title: agent-evals
tldr: The library's own agent evals — two graded tasks run on the candidate wheel and a PyPI baseline by one dispatch-or-schedule workflow.
summary: evals/ holds a cold-onboarding task and a block-list-bug task, each graded by a script on the state the agent leaves; .github/workflows/eval.yml runs each three times on a baseline release and on the candidate wheel built from its own checkout, scans every upload for the model secret, and blocks when the candidate drops where the baseline passed.
tags: [evals, ci, release-gate, distribution]
sources:
  - evals/**
  - .github/workflows/eval.yml
---

## Behavior

- `evals/tasks/t1-cold-onboarding/` asks an agent to onboard `file:///srv/demo.git` into a new workspace for Claude Code through to its specs initialized; its grader passes only with one ALIVE context on that URL and `dadaia doctor` clean.
- `evals/tasks/t2-block-list-bug/` asks an agent to register and fix a block-list bug on the demo project's work branch; its grader passes only when a `BUGS.jsonl` record lands before the fix commit, the tests fail on the pre-fix sha and pass on the fix, the suite is green, and no `assert` line is removed under `tests/`.
- Each task is a harbor task folder — `instruction.md`, `task.toml`, an `environment/` Dockerfile and a `tests/` grader writing a 0 or 1 reward; a grader reads only fields the baseline release and the candidate share.
- `.github/workflows/eval.yml` runs on `workflow_dispatch` or a weekly `schedule`, on a GitHub-hosted runner, in the `evals` environment: it builds the candidate wheel from its own checkout, runs both tasks three times on `dadaia-workspace==<baseline>` (the `baseline` input, whose default the workflow file names) and three times on the wheel, then compares.
- `evals/scripts/compare.py` blocks (exit 1) when a task passing at least 2 of 3 on the baseline passes at most 1 of 3 on the candidate, or when T1 passes below 3 of 3 on the candidate; a missing trial is a fail, and the table lists the trials found per side.
- `evals/scripts/scan.py` exits 1 when any file under the uploaded paths holds the model secret's value or an Anthropic token shape; it runs before the upload and the job summary, and a hit uploads nothing.
- The model secret is read only at the job level of the one job that needs it; the `no-model-api-in-ci` guard (`scripts/guards/repo.py`) judges every line of the workflow, and no other workflow calls a model ([[pypi-distribution]], [[QUALITY]] P-33).
- No context carries an evals repo, and the shipped law states no rule about a user's CI.

## Dependencies

[[pypi-distribution]], [[QUALITY]], [[consumer-agent-support]].
