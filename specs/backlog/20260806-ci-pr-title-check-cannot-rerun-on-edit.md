---
name: ci-pr-title-check-cannot-rerun-on-edit
status: idea
opened: 2026-08-06
owner: project-manager (curates)
priority: P3
source: 'found while landing PR #180: the conventional-commit title check failed, the title was corrected, and the check could not re-run — the only way to clear it was a new commit or a manual job re-run.'
---
# BACKLOG — the PR title check cannot re-run when the title is fixed

**Problem.** `.github/workflows/ci.yml` triggers on `pull_request` with no `types:`
declared, which yields the defaults `opened`, `synchronize`, `reopened`. Editing a pull
request's title emits `edited`, which is not in that set. So the one check whose subject
*is* the title — `PR title (conventional commits)` — can never be re-evaluated by fixing
the thing it complains about. Clearing it requires an unrelated commit or a manual job
re-run, which teaches the wrong lesson: that a red check is cleared by pushing noise.

**Why not simply add `edited`.** Adding it to the existing trigger would re-run the entire
matrix — Windows/macOS units, contract coverage, integration, E2E, Playwright — on every
title or description edit. The cure is more expensive than the disease, and would burn CI
minutes on prose changes.

**Direction to evaluate (not a decided design).** Split the title check into its own
workflow file whose trigger is `pull_request: types: [opened, edited, reopened, synchronize]`
and which runs nothing else. The heavy matrix keeps its current trigger untouched. Confirm
whether the branch-protection required-check name survives the move, since renaming or
relocating a required check can silently unblock merges — that risk is the reason this is
an idea rather than a ready item.

**Out of scope.** No change to which checks are required, and no change to the conventional
commit rule itself.
