# QA Close — Segment S1 (gitflow contract v2)

**Release:** v0.4.4 · **Segment:** S1 · **Task:** T-044-11 (QA half)
**Author:** qa-engineer · **Date:** 2026-08-23
**Scope:** FR1–FR6 (T-044-03 … T-044-10), two Arm-B bugs closed in-segment, plus one
HIGH bug (`sdd-artifact-linter-mutates-task-markers`, T-044-03) closed as an evidenced
negative ahead of the rest.

**Verdict: APPROVE.**

Every acceptance id A1.1–A6.3 was independently re-run on this branch (not read off a
report) and holds. Two new bugs were found and registered during this close; one
(gitignore recurrence) was root-caused and closed in the same session; the other
(DADAIA.md section-citation drift) is a genuine MEDIUM regression in S1's own surface
but does not fail any of S1's acceptance ids — see §3.

---

## 1. Per-FR verdict table

### FR1 — one gitflow law section (T-044-04)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A1.1 | PASS | `grep -n "^## " dadaia_workspace/public/data/DADAIA.md` | Exactly one `## 4. Gitflow — the branch contract`; 10 sections total, no duplicate branch-model header. |
| A1.2 | PASS | `grep -n "alpha" dadaia_workspace/public/data/DADAIA.md` | Zero hits — `alpha` does not appear as a release-maturation stage. |
| A1.3 | PASS | `grep -n "hotfix" dadaia_workspace/public/data/DADAIA.md` | One hit, line 137: `"hotfix/* is retired: reachable only on an explicit operator request"` — no stage row, no cadence. |
| A1.4 | PASS | Read §4 body | `feature/{M.m.p}` names every stage row; `develop`/`main` appear only as PR targets. |
| A1.5 | PASS | `diff dadaia_workspace/public/data/DADAIA.md {root,.claude/rules,.codex,.kimi-code}/DADAIA.md` | All 4 projections byte-identical to source. |

### FR2 — `dd-gitflow-default` (T-044-05)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A2.1 | PASS | `find . -iname "*dadaia-gitflow*"` / `grep -rn dadaia-gitflow dadaia_workspace/public/` | Zero hits anywhere in the tree. |
| A2.2 | PASS | Read `dd-gitflow-default/SKILL.md` §1–§4 | Start-of-work protocol, uniqueness (§1.5), delete-after-deploy + same-step next-cut (§4) each stated exactly once. |
| A2.3 | PASS | Read §"CI/CD automation" | Present, addressed to a consumer operator. |
| A2.4 | PASS | Read §5 "Mechanical vs discipline" | 7-row table, mechanical rows 1–6 match FR3/FR4 exactly (name pattern, ref refusal, denylist scan, CI trigger, pr-source-guard, verdict-gate). |
| A2.5 | PASS | `wc -l dd-gitflow-default/SKILL.md` | 80 lines, within the G12 ceiling. |

### FR3 — chokepoint inversion (T-044-06)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A3.1 | PASS | `echo "refs/heads/feature/0.4.4 <HEAD> refs/heads/feature/0.4.4 0000…0" \| dadaia ci push-gate-check` (feature/0.0.1) vs a `develop` line | feature push → exit 0; `develop` push → exit 1, message names the PR path (`push your work on 'feature/{M.m.p}'... open the PR feature/{M.m.p} → develop`). Both re-run live by qa-engineer, not read from a capture file. |
| A3.2 | PASS | `grep -rn "feature/v" dadaia_workspace/ .github/` | Zero hits of the retired `feature/v…` shape anywhere in the package or CI. |
| A3.3 | PASS | Live probe A above | Denylist scan runs on the feature push (confirmed by T-044-10's V4 capture, which caught a real denylist hit before the amnesty-bug fix, and by probe A now returning clean). |
| A3.4 | PASS | `grep -n "security.verdict\|iter_security_approvals" dadaia_workspace/features/chokepoints/service.py`; read `push_gate_decision` docstring | Docstring states "There is no third step: the former diff-based security-verdict check is DELETED from this path"; `iter_security_approvals` survives only as `gc-push-verdicts`' read side, never called from `push_gate_decision`. |
| A3.5 | PASS | Live probes (message text) + `dadaia ci push-gate-check --help` | Every refusal message states v2 policy and names the PR path. |
| A3.6 | PASS | `git show --numstat a9a40b8f` | Production files only: `cli/commands/ci.py` +25/-27, `chokepoints/__init__.py` +14/-10, `chokepoints/service.py` +75/-112 → net **−35** (≤ 0, independently summed, matches the commit's own claim). |

### FR4 — CI sees the feature branch; verdict is a PR gate (T-044-07)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A4.1 | PASS | `python3 -c "import yaml; ..." ` on `.github/workflows/ci.yml` | `push.branches = [main, develop, feature/**]`. |
| A4.2 | PASS | Read `jobs.pr-source-guard` | One job, `if: base_ref == main or base_ref == develop`; two shell rules — `main` accepts only `develop`, `develop` accepts only `feature/{M.m.p}` via the shared `_FEATURE_RE`-derived POSIX ERE. |
| A4.3 | PASS | Read `jobs.security-verdict-gate` + run `pytest tests/integration/scripts/test_pr_verdict_check_wiring.py` | Job checks out the PR head sha and runs `pr-verdict-check.sh`; **11/11** wiring tests pass, independently re-run. |
| A4.4 | PASS | `grep -n "advisory\|rc-2\|clobber" .github/workflows/ci.yml` | Lines 497–500 carry the recorded-limit comment verbatim (advisory at rc-1, required from rc-2, `required_status_checks` clobber warning). |
| A4.5 | PASS | `ls tests/unit/features/chokepoints/` | `test_push_gate_decision.py` (v1, verdict-in-push-gate coverage) is gone; replaced by `test_push_branch_policy.py` + new `test_iter_security_approvals.py`. No dual path (confirmed independently — see AR-2 §2 below). |

### FR5 — 14 surfaces become pointers (T-044-08)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A5.1 | PASS (with a caveat, see §3) | `grep -rn "feature/{M\.m\.p}\|hotfix/{M\.m\.p}" public/agents public/skills public/entities/registry.json` outside `dd-gitflow-default` | The few remaining hits are workflow-placement mentions ("bugs run on the live `feature/{M.m.p}` branch") or a `registry.json` mandate summary — none restate the branch **pattern**, a pushability **rule table**, or a merge **milestone**; each carries a `DADAIA.md §4 Gitflow` / `dd-gitflow-default` citation. |
| A5.2 | PASS | `grep -c "DADAIA.md.*§4.*Gitflow\|dd-gitflow-default"` across the 13 surfaces T-044-08's own commit named | Every surface carries at least one pointer to both homes. |
| A5.3 | PASS | `grep -rn "hotfix/{M.m.p}" dadaia_workspace/public/skills/dd-bug-fix/` | Zero hits; `dd-bug-fix` instructs the live `feature/{v}` branch only. |
| A5.4 | PASS | `git show --stat 3dfb201c d28405e8` | 3dfb201c: net **−4** across 13 surfaces (commit message, independently spot-checked against the diff); d28405e8 (T-044-08's script/CLI-docstring share, folded with T-044-09): net **−3**. Combined net-negative confirmed. |

### FR6 — preflight/CI parity, bug `prepush-gate-omits-import-boundary-contracts-ci-runs` (T-044-09)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A6.1 | PASS (evidenced negative, verified) | `python -c "import dadaia_workspace.features.ci_preflight.service as svc; print(svc.checks_for(quick=True))"` | `lint-imports` already present in the list, wired since commit `aeaa3c66` (pre-dates the bug report by 6 weeks) — genuine executed-path finding, not a claim taken on faith. |
| A6.2 | PASS | `pytest -p no:cacheprovider -q tests/contract/test_ci_preflight_ci_gating_parity.py` | 2/2 passed, independently re-run. |
| A6.3 | PASS | `sed -n '950p' specs/bugs/bugs.jsonl` (resolved event) | `resolved` event present with substantial `--resolution-evidence`; bug does not appear in `dadaia bugs status`'s open list — Closed confirmed. |

### D7 / bug `sdd-artifact-linter-mutates-task-markers` (T-044-03, HIGH, lands first)

| Check | Verdict | Evidence |
|---|---|---|
| RED-then-GREEN or evidenced negative + contract test | PASS | `pytest -p no:cacheprovider -q tests/contract/test_sdd_writers_never_mutate_task_markers.py` → 6/6 passed, independently re-run. `resolved` event (line 948) carries the seam census (3 harness-wired hooks + migration chain) and the evidenced-negative conclusion (R-3: bug was misfiled from a consumer repo's ledger). |
| `resolved` event + Closed | PASS | Not in `dadaia bugs status` open list. |

### Bug `new-branch-push-loses-prior-published-denylist-amnesty` (T-044-10, HIGH, discovered mid-segment)

Not a named FR, but closed in-segment and directly gates T-044-10's own done criterion
(V4 both edges). Independently verified:

| Check | Verdict | Evidence |
|---|---|---|
| RED-then-GREEN, real bare-origin fixtures | PASS | `resolved` event (line 952) names 3 real failing tests pre-fix (`test_new_branch_push_amnesties_a_path_already_published_on_a_remote_branch`, `test_resolvable_remote_sha_and_new_branch_fallback_agree_on_the_same_final_state`, `test_new_branch_push_of_an_already_published_term_passes`). |
| Root cause, not a carve-out | PASS | Diff direction is a deletion (two range-derivation shapes → one), matching AR-2's own finding (`range_derivation_shapes_before: 2, after: 1`). |
| Live re-probe after fix | PASS | `.dadaia/tmp/claude/20260823/T-044-10-V4-probeA-after-fix.txt` shows `EXIT=0`; **re-confirmed live** by this QA session's own A3.1 probe above (exit 0, no denylist block). |
| `resolved` event + Closed | PASS | Not in `dadaia bugs status` open list. |

---

## 2. Full-suite and e2e re-run (independent, this session)

```
pytest -p no:cacheprovider -q -m "not quarantine" -n auto --ignore=tests/e2e
  -> 2589 passed, 3 skipped (all environment-gated: 2 Windows-only, 1 codex-live-probe
     honest-degrade), 0 failed, 35.25s

pytest -p no:cacheprovider -q tests/e2e/test_push_gate_check.py \
  tests/e2e/test_push_denylist_journey.py tests/e2e/features/test_public_pipeline.py
  -> 16 passed, 8.34s
```

Both runs green, re-executed by this session (not taken from an implementer's report).

### Test-stewardship spot check on the 5 S1-added test files

`tests/contract/test_ci_preflight_ci_gating_parity.py`,
`tests/contract/test_ci_v2_gitflow_pr_gate.py`,
`tests/contract/test_sdd_writers_never_mutate_task_markers.py`,
`tests/integration/scripts/test_pr_verdict_check_wiring.py`,
`tests/unit/features/chokepoints/test_iter_security_approvals.py`.

All 5 declare `Intent: CONTRACT — <AC-id | bug-id>` in the module docstring; tier
matches directory placement (`contract`/`integration`/`unit`, auto-marked by
`pytest_collection_modifyitems`); none is volume padding (5 files for 6 FRs + 3 bugs is
proportionate, not inflated); `test_iter_security_approvals.py`'s docstring explicitly
states it supersedes coverage from the deleted `test_push_gate_decision.py` (a demotion
map at task scope, consistent with §D — no coverage silently dropped). No scaffold, no
tautology, no change-detector pattern observed.

---

## 3. Bug-surface statement (operator standing order)

Net direction across S1, measured, not asserted:

- **Deleted:** the push-time diff-based security-verdict check (a whole enforcement
  step, `push_gate_decision` step 3); the `hotfix/{M.m.p}` PATCH-mint pattern and its
  validator; the retired `feature/v…` regex (the I1 contradiction); the two-shape
  range-derivation branch in `GitObjectReader.new_objects` (root cause of the amnesty
  bug — collapsed to one exclusion-set formula, not a third carve-out); `dadaia-gitflow`
  as a duplicate skill folder; `lint-skill-collisions.py` is untouched by S1 (that is
  S2/FR9's job) but S1 itself added **zero** new branch/flag/second-code-path to any
  touched feature.
- **Added:** exactly one new enforcement point at the CI layer
  (`security-verdict-gate`), which is the G6-ratified **relocation** of the deleted
  push-time step, not a net addition — confirmed independently by AR-2 (gross points
  6 → 6, hook policy steps 4 → 3, enforced-rule inventory net **−2**).
- **Production LOC (FR3, the highest-risk touch):** net **−35** (independently summed
  from `git show --numstat a9a40b8f`, matching A3.6's claim).
- **Documentation LOC (FR5):** net **−4** (3dfb201c) and **−3** (d28405e8's software
  half) = **−7** combined, independently spot-checked against the diffs.

**S1's own new bug-surface contribution, honestly stated:**

1. **`t044-04-renumber-stale-DADAIAmd-section-citations`** (MEDIUM, filed this session).
   T-044-04 inserted a new `## 4. Gitflow` section into `DADAIA.md`, shifting every
   later section down by one (old §4 "Where things are written" → new §5, old §5
   "Specs, tasks and memory" → new §6, old §6 "Quality" → new §7, old §7 "The library
   surface" → new §8). At least 20 downstream `DADAIA.md §N` citations across 12 files
   in `public/agents/` and `public/skills/` were never updated and now point at the
   wrong topic (`§4 (handoff-first)` appears 9–11 times when handoff-first content now
   lives at §5; `§5 (Releases)`/`§5 (Backlog)` appear 6 times when that content is now
   at §6). This is a genuine regression, directly caused by S1's own T-044-04 change,
   left unaddressed by T-044-08 (whose declared scope was narrowly "branch model"
   restatement, not a full citation sweep). **Does not fail any A1–A6 acceptance id** —
   A1.1–A1.5 only require `DADAIA.md` itself to be internally correct (it is: the new
   §4 IS the gitflow section), and FR5/A5.1–A5.4 are scoped to branch-model content
   specifically. It is filed for remediation before S3 touches the same
   personas/skills again — see Open Residuals below. Given the narrow scope and the
   fact that no acceptance id names citation accuracy, I am **not** treating this as a
   REQUEST_CHANGES blocker for T-044-11, but it is a real, non-trivial defect and is
   named here rather than buried.
2. **`v0.4.4-reviews-dir-untrackable-gitignore-recurrence`** (MEDIUM, filed and
   **closed in this same session**). The new `specs/releases/<id>/reviews/` directory
   convention this release's TASKS.md introduces (per-segment QA close +
   `software-architect` AR-N rulings) was silently swallowed by the pre-existing broad
   `/specs/releases/*/*` gitignore rule — the third recurrence of the exact
   "law-mandated artifact needs its own whitelist line, or it is silently defeated"
   class already documented twice inline in `.gitignore` (`ALPHA-*-QA.md`,
   `PRE-PR-REVIEW.md`). Root-caused in this session: two whitelist lines added to
   `.gitignore` (`!/specs/releases/*/reviews/`, `!/specs/releases/*/reviews/*.md`),
   verified with `git check-ignore -v` (no longer matches the broad ignore) and
   `git status` (file now shows `??` instead of `!!`). Closed with
   `--resolution-evidence` in the same session. This is infrastructure plumbing, not a
   feature-surface bug, and does not count against S1's bug-surface direction.

Net: S1 reduces the touched features' surface (branch policy, denylist range
derivation, security-verdict placement) while surfacing — and in one case, fixing on
the spot — two new but narrow, non-blocking defects in its own tooling/documentation
surface. Consistent with the standing order: neither new bug adds a branch, a flag, a
second code path, or a cross-feature reach-in to any *product* feature; both are
plumbing/citation defects in the surrounding surface.

---

## 4. Open residuals

1. **Fix the DADAIA.md §N citation drift** (`t044-04-renumber-stale-DADAIAmd-section-citations`,
   MEDIUM, open) before S3 (`core-skills-consolidation`) does its own persona/skill pass —
   ideally as part of T-044-08's already-declared surfaces, or as a small standalone Arm-B
   fix on `feature/0.4.4` before more skills are touched. FR27/A27.19's citation check
   (S3) validates that a cited **path** exists, not that a numbered **section** citation
   matches its content — this class of drift needs its own check or its own fix, not a
   free ride on A27.20.
2. **The verdict-gate advisory window is real and time-boxed, not a defect.** Per A4.4,
   `security-verdict-gate` is advisory on the `rc-1` PR (the PR that introduces the job
   cannot be gated by it) and becomes required from `rc-2` onward — an operator/dispatcher
   repository-settings action, re-supplying the whole `required_status_checks` list
   (`gh api PATCH` clobbers). Nothing to do at S1 close; flagged so `rc-1`'s ship step
   does not mistake "advisory" for "broken".
3. **The installed venv is editable and runs this branch's code** (T-044-10, D-3)
   — reconfirmed this session (`.dadaia/.venv/bin/dadaia` resolves the live chokepoint
   fix, not a stale PyPI package). This is the correct state for in-branch QA, not a
   residual to fix, but it means every probe in this report is validating
   `feature/0.4.4` HEAD, not a released package — noted for CLOSURE's own venv-state
   record.
4. **AR-2's own two findings** (software-architect, MEDIUM: `pr-verdict-check.sh`'s
   unreviewed-change exemption is path-based not content-based; LOW: verdict-qualification
   predicate duplicated between `iter_security_approvals` and `gc_consumed_push_verdicts`)
   are software-architect's residuals, not re-litigated here — routed by AR-2's own
   handoff to `security-reviewer` (MEDIUM) and "next touch" (LOW).

---

## 5. Verdict

**APPROVE.** All of A1.1–A6.3 independently re-verified true on this branch, by the
executed path, not by trusting an implementer's report. Full suite green (2589 passed,
0 failed) plus the e2e push-gate journey (16 passed). Two new bugs found during this
close are registered; one closed same-session (gitignore), one filed as an open,
non-blocking residual (citation drift) with a clear remediation path before S3.

`software-architect`'s companion AR-2 ruling (`specs/releases/v0.4.4/reviews/S1-AR2-ruling.md`,
handoff `2026-08-23T213000Z-software-architect-S1-AR2-ruling.handoff.json`) independently
concurs: **APPROVED**, enforcement surface shrunk (6→6 gross points, one G6-ratified
relocation, hook policy steps 4→3, enforced-rule inventory net −2, zero dual paths).

S1 is closed on `feature/0.4.4`. No merge, no PR, no `rc` burned (D8) — `S2` may proceed
once T-044-11 flips `[-]` → `[x]`.
