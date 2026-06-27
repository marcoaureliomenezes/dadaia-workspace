---
release: none
phase: none
---

# Active release: none

**v0.1.31** — *make the dadaia-workflows actually run on a real Layer-2 worker* — is
**CLOSED and ARCHIVED** at `specs/_archive/releases/v0.1.31/` (CLOSURE.md). The
dadaia-workflows now run on a real Layer-2 worker end to end: a live real-worker e2e drove
a real `pi` (gpt-5.5, OpenAI Codex subscription) through `release_scope → spec_create` past
step 1 under the **review-only** typed gate. All tasks `[x]` (T-31-C-03 descoped — pi alone
satisfies the deliverable); code/security/qa reviews APPROVE; `specs doctor` 0 errors.

Both HIGH bugs Closed with evidence (`pi-headless-command-trailing-dash-breaks-layer2`,
`lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate`). Two follow-ups left Open:
`lifecycle-prompt-names-two-schemas-confusing-real-workers` (the C-02 residual — the prompt
names two schemas, so real workers label the result inconsistently; the extractor was
hardened to tolerate it) and `subagent-handoff-resolves-dadaia-inside-repo-cwd` (escalated to
MEDIUM — subagents running with cwd=repo write `.dadaia/` into the repo, breaking the
mypy-cache redirect).

Branch `feature/v0.1.31` is **NOT pushed / NOT merged** (operator constraint — no push). It
stacks on `feature/v0.1.30` (also unpushed). Ship path when ready: re-stamp a
`security-reviewer` APPROVE on the final HEAD sha, push, watch CI until every job is green
(incl. the GH-only `e2e-panel` job), PR → squash-merge to `main`. Note the two stacked
unpushed releases (v0.1.30 then v0.1.31) — sequence the merges or rebase accordingly.

No release is currently active. Open the next release with `dadaia release new` when work is
picked.

Pre-existing drift (not in scope): `specs/releases/v0.1.23/` remains unarchived on `main`
(an `Aprovado` SPEC with no CLOSURE) — a future cleanup.
