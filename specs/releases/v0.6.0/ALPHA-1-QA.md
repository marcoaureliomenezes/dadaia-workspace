# ALPHA-1 QA Review — v0.6.0 Gitflow standardization

**Task:** T-060-06 · **Reviewer:** qa-engineer · **Date:** 2026-08-12
**Scope:** validate SPEC §7 acceptance criteria and TASKS T-060-06 items 1–7 on the
**live instance** (`<workspace-root>`), not from the diff.

## Verdict: REJECTED

Two real, reproducible defects block acceptance. Both are process/coverage gaps, not
design flaws — the underlying mechanism (branch policy, diff-keyed security verdict,
`pr-source-guard`) works correctly everywhere it was exercised. The full quality ladder
is **not** green (Done criterion for T-060-04) and `dadaia public doctor` does **not**
exit 0 (Done criterion for T-060-03 / SPEC §7 item 1). Per T-060-06's own Done
criterion, T-060-03 and T-060-04 are returned to `[-]` (see TASKS.md); T-060-06 itself
is complete — this review is its deliverable.

---

## Item 1 — Four `DADAIA.md` projections + `dadaia-gitflow` presence

**PASS.**

```
$ sha256sum <workspace-root>/DADAIA.md .claude/rules/DADAIA.md \
    .codex/DADAIA.md .kimi-code/DADAIA.md \
    repos/dadaia-workspace/dadaia_workspace/public/data/DADAIA.md
ee6623fb5546e1e58f3a744e9ea1eae23bdf7b4a1c5c8e4331454ab97a69a1e2  DADAIA.md
ee6623fb5546e1e58f3a744e9ea1eae23bdf7b4a1c5c8e4331454ab97a69a1e2  .claude/rules/DADAIA.md
ee6623fb5546e1e58f3a744e9ea1eae23bdf7b4a1c5c8e4331454ab97a69a1e2  .codex/DADAIA.md
ee6623fb5546e1e58f3a744e9ea1eae23bdf7b4a1c5c8e4331454ab97a69a1e2  .kimi-code/DADAIA.md
ee6623fb5546e1e58f3a744e9ea1eae23bdf7b4a1c5c8e4331454ab97a69a1e2  .../public/data/DADAIA.md

$ stat -c '%a %n' DADAIA.md .claude/rules/DADAIA.md .codex/DADAIA.md .kimi-code/DADAIA.md
444 DADAIA.md
444 .claude/rules/DADAIA.md
444 .codex/DADAIA.md
444 .kimi-code/DADAIA.md
```

All five bytes identical; all four projections `0444`.

`dadaia-gitflow` presence: physical copies exist at `.claude/skills/dadaia-gitflow/` and
`.agents/skills/dadaia-gitflow/`. `.codex/skills/` and `.kimi-code/` carry **no** physical
copy — by design, not a gap: `install_universal_skills()` (the codex "skills" install
step) and `_install_claude()` both target a single canonical location
(`.agents/skills/`), and both `.codex/DADAIA.md:300` ("Skills live at `.claude/skills/`,
`.agents/skills/`") and `.kimi-code/AGENTS.md:37` ("Universal skills live in
`.agents/skills/`") explicitly document the reference, consistent with the "one home,
referenced everywhere" law (SPEC §7 item 2 / A2.2). Codex additionally discovers skills
natively from `.agents/skills/` per `runtime_config.py:319`. Treated as satisfying the
done criterion by reference, not by duplication.

---

## Item 2 — Push-gate refusals (installed hook, live)

**PASS.** Captured evidence from the real `git push` attempts
(`/tmp/.../t06004-live-refusal-demo.txt`, produced by T-060-04):

```
=== DEMO 1: git push origin main ===
...
[pre-push] BLOCKED: 'main' is never pushed directly — it advances only via a PR from
'develop' (gitflow law, DADAIA.md §5).
  Fix: merge your work into 'develop', push 'develop', then open the PR develop → main.
exit=1

=== DEMO 2: git push origin feature/v0.6.0 ===
...
[pre-push] BLOCKED: 'feature/v0.6.0' is a feature branch — feature branches are
local-only and are never pushed (gitflow law, DADAIA.md §5). Only 'develop' is pushable.
  Fix: merge the branch into local 'develop', obtain the diff-based security APPROVE,
  then push 'develop'.
exit=1
```

Independent dry-run via `dadaia ci push-gate-check` (no real push executed), four cases:

```
$ printf 'refs/heads/main aaaa...a refs/heads/main 0000...0\n' | dadaia ci push-gate-check
[pre-push] BLOCKED: 'main' is never pushed directly — ... exit=1

$ printf 'refs/heads/feature/v0.6.0 aaaa...a refs/heads/feature/v0.6.0 0000...0\n' | dadaia ci push-gate-check
[pre-push] BLOCKED: 'feature/v0.6.0' is a feature branch — ... exit=1

$ printf 'refs/heads/bugfix/whatever aaaa...a refs/heads/bugfix/whatever 0000...0\n' | dadaia ci push-gate-check
[pre-push] BLOCKED: ref 'refs/heads/bugfix/whatever' is outside the four permitted
branch patterns — main, develop, feature/vM.m.p, hotfix/vM.m.p (gitflow law, DADAIA.md §5).
  Fix: rebuild the work on a permitted branch (git checkout -b feature/vM.m.p or
  hotfix/vM.m.p from develop), merge it into 'develop', and push 'develop'.
exit=1

$ printf 'refs/heads/develop aaaa...a refs/heads/develop 0000...0\n' | dadaia ci push-gate-check
[pre-push] BLOCKED: no security-reviewer APPROVE covers the origin/develop..develop
delta being pushed (refs/heads/develop@aaaaaaaaaaaa).
  APPROVE shas on disk: 02cb44ce..., ... (full ledger listed)
  Fix: dispatch a security-reviewer DIFF review of origin/develop..develop and emit an
  APPROVED handoff with metrics.commit_sha == the pushed develop tip sha, then push again.
exit=1
```

All four refusal messages name the rule, the permitted value, and a corrective action
(A4.2). No real push was executed at any point in this validation.

---

## Item 3 — `pr-source-guard`

**PASS with accepted deviation.** `.github/workflows/ci.yml:405-422` defines the job:

```yaml
pr-source-guard:
  if: github.event_name == 'pull_request' && github.base_ref == 'main'
  steps:
    - name: Refuse PRs to main from any head but develop
      env:
        HEAD_REF: ${{ github.event.pull_request.head.ref }}
      run: |
        if [ "$HEAD_REF" != "develop" ]; then
          echo "::error::Gitflow law (DADAIA.md §5): main accepts PRs from 'develop' only..."
          exit 1
        fi
```

`head.ref` is read via `env:`, never interpolated into the shell string — confirmed by
direct read of the workflow file. The live red-run/green-run URLs (T-060-05 item 3,
SPEC §7 item 3) are **deferred to T-060-08/09** by the workflow's own mechanics: this
job only fires on a real PR event against `main`, and the first legitimate PR to `main`
is the T-060-08 ship milestone. **Accepted deviation**, not a finding — recorded per the
task's own steering instruction and consistent with TASKS' T-060-05 commit note.

---

## Item 4 — Doctors (all must exit 0)

**FAIL** (2 of 3).

```
$ dadaia specs doctor
... 16 atom(s) have warnings ... [ok] overall: 0 error(s), 6 warning(s)
exit=0                                                                    PASS

$ dadaia public doctor
...
[drift] stage:agents/security-reviewer.md
...
[ok] public-privacy
exit=1                                                                    FAIL

$ dadaia doctor
Found 1 issue(s):
  PRESENCE-GC [fixable] — [stale-presence] context 'an-unrelated-consumer-context': advisory presence
  record for session 'session_00f6df24-...' is stale or corrupt — safe to reclaim.
exit=1                                                                    FAIL (unrelated)
```

**Finding A (MEDIUM — blocks acceptance).** `dadaia public doctor` reports
`[drift] stage:agents/security-reviewer.md`. Root cause, confirmed by diff:

```
$ diff dadaia_workspace/public/agents/security-reviewer.md .claude/agents/security-reviewer.md
61,63c63,65
< lacks a matching APPROVED handoff from you, refuses any non-`develop` pushed ref, and
< validates the branch name against the permitted patterns (branch contract:
< `dadaia-gitflow`). There is no lock to hold — you run
---
> lacks a matching APPROVED handoff from you, refuses any pushed ref other than
> `refs/heads/develop`, and validates the branch name against the four permitted
> patterns (the branch contract is `dadaia-gitflow`). There is no lock to hold — you run
```

The committed source (`dadaia_workspace/public/agents/security-reviewer.md`, last
touched by T-060-03's own commit `1e6d0da4`) carries the T-060-03 wording; the installed
`.claude/agents/security-reviewer.md` still carries **pre-T-060-03** wording — the
projection chain (`dadaia public stage` → `dadaia public install --target all`) was
never re-run to completion after that commit landed. `git status --short
dadaia_workspace/public/agents/security-reviewer.md` is clean, so this is not an
artifact of this QA session. **Substance is unaffected**: the installed copy still
correctly states the diff-only `scan_target` and the audit-lane `full`-scan carve-out
(A3.3 content intact) — this is a stale-projection defect, not a content regression. It
directly reproduces as `tests/e2e/features/test_public_pipeline.py` failures (item 5).
Reopens **T-060-03**.

**Finding B (LOW — unrelated to this release, noted per the letter of the done
criterion).** `dadaia doctor` reports one fixable `PRESENCE-GC` issue for context
`an-unrelated-consumer-context` — a stale advisory-presence record from an unrelated project, not touched
by any v0.6.0 write set. `dadaia doctor --fix` would clear it. Reported because the Done
criterion states "all exit 0" without qualification, but this is environmental noise,
not a v0.6.0 defect — no task reopened for this alone.

---

## Item 5 — Quality ladder

```
$ pytest -q -p no:cacheprovider tests/ -n auto --ignore=tests/performance
FAILED tests/e2e/features/test_public_pipeline.py::TestStage::test_stage_dirs_manifest_agents_and_skills
FAILED tests/e2e/features/test_public_pipeline.py::TestInstallAll::test_install_all_populates_claude_agents_skills_no_stale
FAILED tests/e2e/test_push_gate_check.py::test_predicate_keys_on_stdin_sha_not_head
FAILED tests/e2e/test_push_gate_check.py::test_push_without_security_approve_is_blocked
FAILED tests/e2e/test_push_gate_check.py::test_pass_matrix[approve-flows]
5 failed, 2101 passed, 3 skipped, 1 warning in 293.53s        FAIL

$ ruff format --check --no-cache dadaia_workspace/ tests/
645 files already formatted                                   exit=0  PASS

$ ruff check --no-cache dadaia_workspace/ tests/
All checks passed!                                             exit=0  PASS

$ MYPY_CACHE_DIR=/tmp/mypy_qa mypy --strict dadaia_workspace/
Success: no issues found in 261 source files                   exit=0  PASS

$ lint-imports --config setup.cfg --no-cache
Contracts: 9 kept, 0 broken.                                    exit=0  PASS
```

**Finding C (HIGH — blocks acceptance).** Full suite is not green: 5 pre-existing
end-to-end tests were never updated for this release's own behavior change, and neither
file is inside any T-060 task's declared write set.

1. `tests/e2e/features/test_public_pipeline.py::TestStage::test_stage_dirs_manifest_agents_and_skills`
   and `::TestInstallAll::test_install_all_populates_claude_agents_skills_no_stale` — both
   assert an exact `EXPECTED_SKILLS` roster fixture; T-060-01 added `dadaia-gitflow` as a
   new universal skill but the fixture set in this test file was never updated:
   ```
   AssertionError: .agents/skills/ mismatch.
     Missing: []
     Extra:   ['dadaia-gitflow']
   ```
2. `tests/e2e/test_push_gate_check.py::test_predicate_keys_on_stdin_sha_not_head`,
   `::test_push_without_security_approve_is_blocked`,
   `::test_pass_matrix[approve-flows]` — all three push `refs/heads/main` and assert the
   **pre-v0.6.0** refusal behavior (blocked only by a missing/non-matching
   security-reviewer APPROVE). T-060-04's new develop-only ref policy now refuses `main`
   **first**, with a different (more specific, correct) message:
   ```
   AssertionError: gate must key on the pushed sha, not HEAD: [pre-push] BLOCKED:
   'main' is never pushed directly — it advances only via a PR from 'develop'
   (gitflow law, DADAIA.md §5). ...
   assert 1 == 0
   ```
   The underlying *design intent* of these three tests (sha-vs-HEAD keying, no-APPROVE
   refusal, matching-APPROVE pass) is still correct and still needs coverage — but it
   must now target `refs/heads/develop` (the only ref that reaches the security-verdict
   stage), not `refs/heads/main`.

Root cause: T-060-04's write set was scoped to `tests/contract/**` +
`tests/unit/features/chokepoints/**` only, explicitly excluding `tests/e2e/**`; T-060-01
added the new skill without a corresponding e2e-fixture update. Neither task's Done
criterion actually verified the *existing* e2e suite kept passing — only the *new*
contract/unit tests were checked. Reopens **T-060-04** (the skill-roster fixture and the
branch-policy interaction both stem from behavior it introduced).

---

## Item 6 — A2.3 relocation grep (independent re-run)

**PASS.** `grep -rnE "feature/v?\{?[0-9M]|hotfix/v?\{?[0-9M]|only pushable"
dadaia_workspace/public/` — every hit resolves to one of the three permitted homes:

- `dadaia_workspace/public/data/DADAIA.md:183,189,198` — the law itself (one of the two
  canonical homes).
- `dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md:18-20,31-33,42,60` — the skill
  itself (the other canonical home).
- `dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md:67-68` — operational
  reference to the branch names within the milestone-(a) procedure, not a restatement of
  the full branch table.
- `dadaia_workspace/public/agents/product-engineer.md:402` — a one-line reference
  (`... run on hotfix/{M.m.p} (branch contract: dadaia-gitflow)`), immediately following
  the explicit D4-revocation section (line 395: "Hotfix release lifecycle — REVOKED").

No hit duplicates the branch-pattern table or the two-milestone cadence.

---

## Item 7 — Spot-checks

**PASS** on all four.

- `product-engineer.md:395-404` — "Hotfix release lifecycle — REVOKED (operator ruling
  D4, 2026-08-12)"; explicitly states no `release_hotfix.md.j2`/`closure_hotfix.md.j2`,
  no `dadaia specs hotfix open`, no condensed 7-step flow, no hotfix status ladder; no
  `specs/releases/<id>/` directory created for a hotfix.
- `security-reviewer.md:29,70-71` (installed copy, per Finding A above — content, not
  wording, is what's checked) — `scan_target` description: "exactly one target, the diff
  `origin/develop..develop`. `'full'` ... admitted only in the audit lane (project-auditor
  dispatch)." One admitted scan target; `full` appears only in the audit-lane sentence.
- `code-reviewer.md:64,68` — "The PR you gate is `develop` → `main` only — there is no
  `feature/*` → `main` path."
- Constitution §11/§13: `dadaia_workspace/public/scaffold/constitution.md` carries `## 11.
  Checkpoints de Revisão` and `## 13. Propriedade da Memória`. Citations across
  `public/agents/**` (`§6, §7, §9, §11, §13`) all resolve to existing sections —
  resolution (a) (add the sections) was applied.
- `scaffold/releases/README.md:20` states the canon regex `^v\d+\.\d+\.\d+$` and the v2
  `ACTIVE.md` block. `ai-engineer.md:353` inventories exactly the 5
  `dadaia_workspace/public/scripts/` files present on disk (3 shell + 2 Python), matching
  `ls dadaia_workspace/public/scripts/`.

---

## Summary — pass/fail table

| Item | SPEC §7 / TASKS ref | Result |
|---|---|---|
| 1. Four projections + gitflow presence | §7.2, A1.3/A2.1 | PASS |
| 2. Live push refusals (main/feature/bugfix/develop) | §7.3, A4.1/A4.2 | PASS |
| 3. `pr-source-guard` job + env-based `head.ref` | §7.3, A5.1-3 | PASS (red/green URL deferred to T-060-08/09, accepted deviation) |
| 4. Doctors all exit 0 | §7.1, A6.5 | **FAIL** — `public doctor` drift (Finding A); `dadaia doctor` unrelated presence noise (Finding B) |
| 5. Quality ladder | §7.1, A4.3/A4.5 | **FAIL** — 5 pre-existing e2e tests broken by this release's own behavior change (Finding C) |
| 6. A2.3 relocation grep (independent) | §7.2 | PASS |
| 7. Spot-checks (hotfix revocation, scan target, PR base, §11/§13, README regex, scripts inventory) | §7.4/§7.5 | PASS |

**Verdict: REJECTED.** T-060-03 and T-060-04 return to `[-]` (sanctioned concurrent
pair). Fix required before re-review:
1. Re-run the projection chain (`dadaia public stage` → `dadaia public install --target
   all` → `dadaia public doctor`) to clear the `security-reviewer.md` drift.
2. Update `tests/e2e/features/test_public_pipeline.py`'s `EXPECTED_SKILLS` fixture to
   include `dadaia-gitflow`.
3. Update the 3 `tests/e2e/test_push_gate_check.py` tests that assumed `main` was a
   security-verdict-gated pushable ref — retarget them at `refs/heads/develop` (the only
   ref that still reaches that stage) or otherwise reconcile with the new develop-only
   policy.

No source file was modified by this review — findings only, per qa-engineer scope.
