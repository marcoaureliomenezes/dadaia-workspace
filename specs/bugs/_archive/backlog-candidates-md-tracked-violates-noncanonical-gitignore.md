---
name: backlog-candidates-md-tracked-violates-noncanonical-gitignore
status: Closed
severity: LOW
reported: 2026-06-24
surface: repo hygiene — specs/backlog/candidates.md vs .gitignore /specs/* policy
session_id: null
---

**Symptom:** `tests/contract/test_source_repo_hygiene.py::test_noncanonical_specs_content_stays_gitignored`
fails: `specs/backlog/candidates.md` is git-**tracked**, so `git check-ignore` reports it as
not-ignored, violating the contract "only canonical lifecycle artifacts are opted back into version
control." Pre-existing on `feature/v0.1.15` (reproduced with all v0.1.16 changes stashed) — the file
was committed in `824c290` and re-touched in the v0.1.15 closure `ca5ba47`, despite `.gitignore:98`
(`/specs/*`) intending non-canonical backlog scratch content to stay local.

**Repro:**
1. `git ls-files specs/backlog/candidates.md` → shows the path (tracked).
2. `dadaia ci preflight` (or `pytest tests/contract/test_source_repo_hygiene.py`) → 1 failed.

**Expected:** `specs/backlog/candidates.md` (the spec-reviewer's non-canonical "unresolved gaps"
scratch file) is gitignored and not tracked; the hygiene contract passes.

**Resolution:** `git rm --cached specs/backlog/candidates.md` (untracked; file kept on disk). It now
matches `.gitignore:98 /specs/*` and both hygiene contracts pass. Fixed within release
`multiharness-engine-v0116` because the pre-existing failure blocked that release's pre-push CI gate.

**Notes:** No operator-local paths/secrets. The `/specs/*` ignore with `!`-negation exceptions
(canonical SPEC/PLAN/TASKS/CLOSURE/bugs/audits) is the intended policy; `candidates.md` simply lacked
a negation and should never have been tracked.
