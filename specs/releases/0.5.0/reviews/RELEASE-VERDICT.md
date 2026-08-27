# RELEASE-VERDICT — release 0.5.0

**Task:** T-050-36 (QA half) · **Reviewer:** qa-engineer · **Branch:** `feature/0.5.0`
**HEAD reviewed:** `343acc38` (post T-050-34 `afbd94fa`; includes four further commits that
landed while this verdict was being written — `b9ffaf77` full-history fix, `c01fe20f`
FR23-firing docs, `b0c1997d` audit dispositions, `d981855c` backlog-histo redaction fix —
plus this session's own bug-registration commit `343acc38`, isolated shape 1)
**Precondition note:** T-050-36's TASKS.md precondition reads "T-050-35 `[x]`". At the time
of writing, **T-050-35 (the six-axis code review) has not landed** —
`specs/releases/0.5.0/reviews/T-050-35-code-review.md` does not exist and TASKS.md still
carries `[ ]` for it. Per dispatch, this verdict proceeds and is marked
**conditional on T-050-35** rather than blocked on it.
**Security-reviewer half:** not authored here — this document carries the `qa-engineer`
half only, per dispatch. The combined "three `APPROVE`s on one sha" (TASKS.md done
criterion) still requires the security-reviewer's own verdict on this same file.

---

## Part 1 — the A22.9 demotion/deletion map

### 1.1 The gap, restated precisely

| Metric | T-050-03 (before) | T-050-34 (after, authoritative) | Delta |
|---|---:|---:|---:|
| Test functions | 1 825 | **1 899** | **+74** |
| Collected items | 2 881 | **2 972** | **+91** |
| Test files | 396 | 408 | +12 |

A22.9 gates on **after ≤ before**. The release's own declared per-FR `Tests: +N/-M`
roll-up (SPEC §9.4 fold 4, hand-summed) is **+61/-35 = +26**, i.e. a *paper* prediction of
1825+26 = 1851 against T-050-03's real baseline. The **measured** after-count (1899) is
**48 above that paper prediction** and **74 above the raw gate**. Per A22.9's own text,
this divergence is "a defect of the accounting, not of the measurement."

**Re-verified independently** (not merely re-read from T-050-34), by diffing
`tests/**` across the whole release range (`git diff --name-status 02eef219..HEAD --
tests`, at this verdict's HEAD `343acc38`):

| Change class | Files | Function delta |
|---|---:|---:|
| Added (`A`) | 29 | **+123** |
| Deleted (`D`) | 16 | **-74** |
| Modified (`M`) net | 63 | **+26** |
| Renamed (`R059`, `test_rules_skills_map.py` -> `test_behavior_map.py`) | 1 | **+4** |
| **Grand net** | 109 | **+79** |

(This independent re-derivation reads **+79**, T-050-34's own capture read **+74** — a
5-function discrepancy attributable to the different HEAD each was taken at, four
non-test commits and one test-touching commit having landed on the branch between the
two captures; T-050-34's `1899/408/2972` figures remain the **authoritative, task-scoped**
numbers this map closes against, per that task's own done criterion. A **fresh**
`--collect-only` at this verdict's own HEAD reads **1 909 functions / 409 files / 2 979
items** — **+10 functions / +1 file** further drift since T-050-34, from concurrent
work outside this task's write set. Neither T-050-34 nor this map re-opens that drift;
it is named here so the number is not silently stale at closure.)

### 1.2 Method

Every added/renamed test file (29 + 1 = 30 files, +127 functions gross) was read in full
(module docstring + every `def test_` signature) and checked against
`dadaia-test-stewardship` §B (admission filter) and §E (deletion criteria): cross-tier
duplication (same assertion at two tiers with no declared split), tautology, reflex
snapshot, tombstone (asserting the absence of something this release removed), and
change-detector shape (mirrors the implementation rather than a behavior).

### 1.3 Findings, file:line

**No deletion or demotion candidate found among the release's own new test population.**
Every new/renamed file:

- carries an explicit `Intent: CONTRACT` (or, for three files, `Intent: SCAFFOLD` with a
  concrete `expires:` — see below) module-docstring header naming an AC/task id;
- targets genuinely new or genuinely changed production surface this release adds
  (FR2's `BugRecord`/`JsonlRecordStore`, FR3's `core.bug_provenance`, FR4's
  `RELEASE.jsonl` fold, FR13's `FindingRecord`, FR19's ADR canon, T-050-06A's
  per-area-archive verdict-gate arm, FR1's `specs.py` complexity ratchet, FR15's
  audit-findings fold) — none of it re-tests surface an existing test already covers;
- where two files test related ground, the split is **explicit and cross-referenced in
  the docstring**, not accidental duplication. Two examples, verified by reading both
  files named in each cross-reference:
  - `tests/unit/features/bugs/test_resolved_commit_resolver.py:9-13` names
    `tests/contract/test_resolved_commit_stored_equals_derived.py` as the deliberate
    real-git counterpart ("this file never touches a subprocess or the live
    `specs/bugs/BUGS.jsonl`") — a SENTINEL/unit split per §D, not duplication.
  - `tests/unit/core/test_bug_provenance.py:5-10` states its algorithm-level unit
    coverage is deliberately decoupled from
    `tests/unit/features/bugs/test_migrate_v5_provenance_scaffold.py`'s v5/v6-adapter
    coverage — different subjects, same underlying feature.

**Three files are already correctly declared `Intent: SCAFFOLD`, all `expires: 0.6.0`,
none due yet (V28's own gate: an expiry is a violation only against an *already
archived* release, and 0.6.0 has not happened):**

| File | Fn count | Expires | Retires with |
|---|---:|---|---|
| `tests/unit/features/bugs/test_migrate_v5_provenance_scaffold.py` | 1 | 0.6.0 | `migrate_v5.py` deletion (SPEC FR3, AR-1(a)) |
| `tests/contract/test_specs_cli_complexity_ratchet.py::test_migrate_upgrade_module_is_untouched_by_fr1` | 1 of 2 | 0.6.0 | the hand-kept SHA-256 zero-diff pin (S1 FR23 firing A7) |
| `tests/integration/test_consumed_backlog_relocation.py` | 3 | 0.6.0 | T-050-14's root `specs/_archive/` deletion (still `[ ]`, operator-pending — see §2.3) |

Deleting these **now** would be premature under the SCAFFOLD/expiry discipline itself
(V28 exists to prevent exactly this) — they are correctly time-boxed, not "SCAFFOLD past
its purpose." They stay `KEEP-WITH-REASON` in the map below, flagged for automatic
re-review at 0.6.0's own closure.

**Quarantine lane: empty (0/8 cap).** `grep -rn "pytest.mark.quarantine" tests --include='*.py'`
matches only `tests/conftest.py`'s own enforcement code and
`tests/contract/test_stewardship_mechanics.py`'s fixture string — a live collection
against `-m quarantine` returns **0 collected**. Nothing to quarantine-close.

**Zero new `tests/e2e/**` files across the whole release**
(`git diff --name-status 02eef219..HEAD -- 'tests/e2e/**'` at this verdict's HEAD): the
only e2e change is a **deletion** (`tests/e2e/features/test_backlog_precommit.py`, -2
fn, FR9's removed pre-commit block) and three in-place `M` edits at net-0 function
delta. No LARGE-tier growth to demote.

### 1.4 The map (one row per reviewed entry-class; see §1.3 for file:line detail)

| Test id / class | Functions | Verdict | Reason |
|---|---:|---|---|
| 29 new files, cross-tier-split-verified | +123 | **KEEP** | Passes admission filter; targets genuinely new production surface; no duplicate coverage found (file:line above) |
| 1 renamed file (`test_rules_skills_map.py` -> `test_behavior_map.py`) | +4 (net) | **KEEP** | Declared retirement of the rules-skills-map in favor of `behavior-map.json` (T-050-19); not a duplicate, the old map is gone |
| 63 modified files, net growth | +26 | **KEEP** | Incremental assertions on already-admitted files for new behavior inside existing subjects (e.g. `test_atomic_write.py` +5 for the new record-store compare-then-swap seam) |
| 3 SCAFFOLD files, `expires: 0.6.0` | 5 (already counted in the +123) | **KEEP (time-boxed)** | Not yet due; deleting now violates V28 |
| Quarantine lane | 0 | **N/A** | Empty, nothing to disposition |
| New `tests/e2e/**` | 0 | **N/A** | Zero added this release (only 1 deletion, already counted in the -74) |

**Totals: DEMOTE = 0, DELETE = 0, KEEP = every reviewed entry.**

### 1.5 Residual overshoot — the number the operator must accept

**No legitimate closure was found.** Every function inspected passes the admission
filter and targets real, previously-uncovered behavior; none is a cross-tier duplicate,
tautology, snapshot, tombstone, or change-detector. The overshoot is **not** a
test-quality defect this map can prune away — it is (a) FR2's declared canon-adding
scope genuinely requiring more new coverage than the SPEC's own fold-4 roll-up
attributed to it, and (b) an accounting gap: individual Arm-B bug-fix commits (shape 3,
`dd-gitflow-default` §3a — "code + regression test", one commit, mandatory) are **not
FRs** and so never appear in any FR's `Tests:` line, yet `specs/bugs/BUGS.jsonl` shows
multiple `resolved` bugs timestamped inside this release's window, each plausibly
carrying at least one new regression test. Deleting a bug-fix regression test to close
an accounting gap would itself violate the workspace's own doctrine (a resolved bug's
regression test is a permanent CONTRACT, never prunable under criterion (e) without a
zero-defect flake history).

**Residual overshoot the operator must explicitly accept, per A22.9's own text
("silence is not acceptance"): +74 functions / +91 collected items over the T-050-03
baseline (1825 -> 1899 fn, 2881 -> 2972 items), measured at T-050-34's authoritative
HEAD.** A secondary, non-blocking observation: a **further** +10 functions / +1 file of
drift exists between T-050-34's capture and this verdict's own HEAD, from concurrent
work outside either task's write set — not part of the number above, named so it is not
silently absorbed at closure.

**Alternative disposition, not executed here (out of qa-engineer's write scope):**
`product-engineer` could instead correct SPEC's fold-4 `Tests:` roll-up to state the
real accounting (the per-FR lines undercounted by not attributing Arm-B regression
tests anywhere) — that would resolve the *paper* mismatch without deleting anything,
but does not change A22.9's raw gate math, which compares to the fixed T-050-03
baseline regardless of attribution.

---

## Part 2 — the release QA verdict, A22.1-A22.12 + A16.4

### 2.1 Full suite, run once (this verdict's own execution, not re-read from T-050-34)

```
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q -n auto tests
```

**First run (HEAD `d981855c`, mid-session): 1 failed, 2 977 passed, 4 skipped.**
The one failure —
`tests/contract/test_test_suite_ratchets.py::test_v30_pyramid_shape_reported_from_collect_only`
— raised `subprocess.TimeoutExpired` (its own nested `pytest --collect-only` subprocess
call exceeded its fixed 25 s budget). **Classified, not silently retried:** re-run of
that single test alone passed in 8.35 s, well inside the budget — this is CPU-contention
flake under `-n auto` (sibling xdist workers starving the nested subprocess), same code,
observed pass+fail. Per `dadaia-test-stewardship` §F ("Test observed pass+fail on the
same code -> Mark `quarantine` + register the bug — same act, immediate"), **registered**
as `test-v30-pyramid-shape-collect-only-subprocess-times-out-under-nauto-contention`
(LOW), committed alone in this session's own shape-1 commit `343acc38`.
**Quarantine-marking the test itself is deferred to `software-engineer`, quoting this
verdict's evidence** — qa-engineer rules, it does not edit test files (persona scope).

An **earlier** full-suite run at HEAD `d981855c`'s immediate predecessor (three commits
back, before the concurrent backlog-histo redaction fix landed) read **2 975 passed / 4
skipped**, zero failures — consistent with the flake classification above (the same test
simply did not get unlucky on CPU scheduling that run).

All 4 skips are environment-gated, unchanged from baseline (Windows-only
`icacls`/telemetry-lock tests, no non-loopback IPv4 for a LAN check, an upstream
Codex/ChatGPT entitlement rejection already dispositioned at v0.4.3 A22.4) — none is a
regression.

**Verdict: PASS**, with one newly-registered LOW flake bug and its quarantine-marking
handed to `software-engineer`.

### 2.2 A22.1-A22.12 + A16.4, checked against T-050-34's capture and independently spot-verified

| # | Invariant | T-050-34 verdict | Independent spot-check this session | Verdict |
|---|---|---|---|---|
| A22.1 | `ci preflight`/`doctor`/`specs doctor`(0 err)/`backlog doctor`/`public doctor` | PASS (tolerated-error only) | `doctor`: 0 err. `specs doctor`: 1 `[ERR]` (SPEC-DOC-024, the release's own `TASKS.md` legitimately `Em revisão` during IMPLEMENTATION — the same tolerated error), 493 `[WARN]` (dominated by 483 pre-existing SPEC-DOC-033 legacy-record gaps, WARN-only by design). `backlog doctor`: clean. `public doctor`: 0 drift/missing/fail, 1 pre-existing info. **`ci preflight` at this verdict's own HEAD: `ruff format --check` FAILS** — but the sole offender is `tests/contract/test_bug_record_schema.py`, an **untracked** file from a concurrent session's in-flight `test_bug_record.py` -> contract-tier move (visible in `git status --short`: ` M tests/unit/core/models/test_bug_record.py`, ` M tests/unit/core/models/test_findings.py`, `?? tests/contract/test_bug_record_schema.py`). This is WIP outside any committed task's scope, not a defect of the committed tree this verdict evaluates — but `ci preflight` **must** be re-run clean once that WIP lands or is reverted, before any push | **PASS on the committed tree; a concurrent WIP file currently fails `ci preflight` and must be resolved before push** |
| A22.2 | `lint-imports` green, no new accepted edge | PASS | Not independently re-run (T-050-34's `9 kept / 0 broken, 329 files/1532 deps` accepted as current) | PASS |
| A22.3 | Net LOC accounting per FR, honest | 1 genuine mismatch found (FR15 declared ~-200, measured +42/+236 depending on scope) | Accepted as T-050-34's own finding, routed to closure record per that task's own text — not re-derived here (out of QA's LOC-accounting scope) | **PASS with 1 named finding** (FR15 divergence — a closure/operator disposition item, not a QA blocker) |
| A22.4 | AI-surface net negative, S2 total reported | S2 re-verdict (see below) found a wording mismatch, not a numeric defect | `S2-qa-close.md` re-verdict already carries this as its own APPROVE-CONDITIONAL item (A12.5 wording vs measured +544/+203/-1 at three different scope readings) — carried forward, not re-litigated here | **PASS, 1 named wording condition already open (§2.4)** |
| A22.5 | Complexity ceilings unchanged/lowered | PASS (unchanged, no unsafe ratchet applied) | Not re-run (radon/ruff both stable per T-050-34's own finding + registered bug) | PASS |
| A22.6/V18 | 2 blocks removed, pre-push fail-closed survives | PASS (3/3 hook tests, 8/8 CLI-stability) | Both files present in this session's own full-suite green run (§2.1) | PASS |
| A22.7 | Every picked entry dispositioned | Not this task's direct scope | `FINDINGS.jsonl` (37 records): 9 `fixed`, 32 `open`, `release: null`/`reason: null` on every open one (A16.5 shape correct) — dispositioning is ongoing, not yet complete, consistent with the release still being mid-scope-complete | **Reported, not gated: 32 open findings remain undispositioned — a closure precondition (A22.7), not a T-050-36 blocker** |
| A22.8 | Every `rc` holds A22.1-A22.8 | N/A pre-`rc-1` | N/A | N/A (checked at each future `rc`) |
| A22.9 | Test suite net non-positive | **FAIL, overshoot recorded** | Confirmed independently (§1) — no closure found, +74 fn residual | **FAIL, operator acceptance required (§1.5)** |
| A22.10 | Suite marking/structure ratchets (V26-V30) | PASS | `Intent:` coverage: **115/409** declared this session (V27's own recorded floor is `>=108`, a **per-segment ratchet**, not "396/396" — SPEC A22.10 explicitly allows this alternative wording and V27's own committed floor comment states it plainly); still far from full coverage but the ratchet floor holds and is not violated | PASS (ratchet holds; full coverage remains a known, disclosed, multi-release debt — not a regression) |
| A22.11/V31 | Mutation floor on `core/`, ratchet up only | BLOCKED this pass (jsonschema import gap), floor carried forward at 89.87%, bug registered | Confirmed: `mutation-baseline-core-models-scope-now-imports-jsonschema-isolated-venv-cannot-collect` still `open`; a **second**, related mutation-baseline bug also landed concurrently this session (`mutation-baseline-core-models-scope-omits-public-schemas-fixture-directory`) — both name the same isolated-venv scope gap from two angles | **PASS (floor never lowered; 2 open bugs tracked, non-blocking per A22.11's own null-with-reason clause)** |
| V32 | Independence contract 24/24 | PASS | Not re-run (stable, no feature-package change since) | PASS |
| A22.12/V35 | Ruff ceiling ratchets to reality | PASS (no unsafe ratchet applied, 63 kept, bug registered for the radon/ruff C901 discrepancy) | Not re-run (T-050-34's finding is definitive: the literal ratchet attempt broke `ruff check` outright) | PASS |
| A16.4 | Pillar-3 re-run appended to `FINDINGS.jsonl` | Confirmed present (`7c682559`, pre-dating T-050-34's own capture session) | Confirmed still present in `FINDINGS.jsonl` (37 records, unchanged shape) | PASS |

### 2.3 Operator-gated items carried forward, unresolved at this verdict

| Item | State | What blocks it |
|---|---|---|
| **T-050-31** | `[ ]`, not started | Operator-only ADR-acceptance sitting (D12/D13 forbid any agent from flipping a `Status:` to `accepted`). All 28 ADRs remain `proposed`. Expected state per S4's own close, not a defect. |
| **T-050-14** | `[ ]`, not started | Operator-present, destructive: tag `specs/_archive/`, prove reachability from a throwaway clone, then delete the root archive. `specs doctor`'s TREE-8 warning (1 occurrence) is this task's own open marker. |
| **Push-scan objects** | **11 objects** carrying a denylisted term at this verdict's HEAD (`dadaia ci push-gate-check` over `refs/heads/feature/0.5.0`), **up from 8** at S3 close (finding `20260827-canon-v6-first-audit-F037`, then classified "pre-existing, email-address baseline/operator-denylist hits, none inside `specs/audits/`"). The **+3 growth since S3 is unclassified by this verdict** — every object must be re-walked (baseline-vs-new) and remediated at the source record (or the amnesty explicitly re-confirmed) before `T-050-37`'s push; `git push --no-verify` is never the answer (DADAIA.md §7). |
| **A12.5 wording** | Open, routed to `product-engineer`/operator (S2 re-verdict) | "AI-surface LOC net for S2 is negative" is true only under the narrowest single-FR (FR12 alone, -1) reading; the whole-S2 total is +544, the A22.4-named FR7+FR11+FR12 scope is +203. A spec-wording decision, not further engineering. |

### 2.4 Bug surface (FR24 axis)

`dadaia bugs status`: **10 open bugs**, 0 CRITICAL, 0 HIGH (both HIGH findings the audit
surfaced — the record-store append-clobber race and the `--full-history` walk gap — are
now **resolved**, `b9ffaf77`/prior commits, confirmed absent from the open list this
session), 8 MEDIUM, 2 LOW (including this session's own new LOW flake registration).
**None of the 10 open bugs is AS-4 or AS-5.** AS-4 names exactly one bug by SPEC
ruling — `windows-xdist-workers-crash-on-unit-fast-tier` — **not picked, carried forward
open** (still present in the open list, unchanged since T-050-34's own report: no CI ran
this release window to observe a recurrence, by construction, since `feature/0.5.0`
remains unpushed). **AS-5 is a branch-naming ruling** ("the branch is `feature/0.5.0`"),
not a bug id — nothing in the open list corresponds to it.

**Bug-surface direction, per touched feature (evidence from `specs/bugs/BUGS.jsonl` /
`FINDINGS.jsonl`), a summary — the full per-feature verdict is `code-reviewer`'s T-050-35
responsibility, not duplicated here:** this session's own two actions were both
surface-reducing (a registered flake, correctly quarantine-routed rather than silently
retried; the earlier `d981855c` fix closed `backlog-histo-writer-skips-write-time-denylist-redaction`
in the same commit as its regression test, per shape 3). The release as a whole reduced
the bug surface of the bugs feature structurally (one record model replacing an
event-sourced ledger, per S1-AR1's ruling) while surfacing — correctly, via FR16's own
audit dry run — 2 real pre-existing HIGH defects now resolved, and adding 2 new MEDIUM
findings in the mutation-baseline tooling's own venv-scope assumption (itself a
by-product of FR2's new `core/models/` surface, not a regression in shipped behavior).

### 2.5 Security/privacy leakage note (FR24)

- No home-absolute paths, IPs, hostnames, secrets, or tokens were introduced by this
  session's own writes (`specs/bugs/BUGS.jsonl` append, this file) — both spot-checked.
- **This verdict itself surfaces, rather than introduces, a leakage-adjacent finding**:
  the push-scan object count (§2.3) grew from 8 to 11 since S3 close and is
  **unclassified** — until every object is confirmed pre-existing/baseline (as the
  original 8 were) or remediated at the source, this is an open privacy-surface
  question, named here for `security-reviewer`'s T-050-36 half and for whoever executes
  `T-050-37`'s push.
- No new dependency, no auth/access-control surface, and no generated file was touched
  by this qa-engineer session's own writes.
- Consumer-specific data: none observed in any artifact this session read or wrote.

---

## Verdict: **APPROVE-CONDITIONAL**

Conditions, named individually (none is waived by this document alone):

1. **`T-050-35`, the six-axis code review, has not landed.** This verdict's `APPROVE`
   is conditional on that review also landing `APPROVE` on the **same** sha this
   document reviews (or a later sha this verdict is explicitly re-run against).
2. **Operator's explicit, numbered acceptance of the A22.9 overshoot: +74 test
   functions / +91 collected items over the T-050-03 baseline** (§1.5) — this map found
   no legitimate closure; silence is not acceptance per A22.9's own text.
3. **`T-050-31`** — the operator's ADR-acceptance sitting (28 ADRs remain `proposed`).
4. **`T-050-14`** — the operator-present tag-then-delete of root `specs/_archive/`.
5. **The push-scan object growth (8 -> 11 since S3)** must be classified and, where
   not pre-existing baseline, remediated at the source record before `T-050-37`'s push
   — never `--no-verify`.

**Not a condition, but recorded for closure:** the A12.5 wording mismatch (§2.3) is a
`product-engineer`/operator spec-wording call, independent of this verdict's own
APPROVE-CONDITIONAL.

**Evidence paths (this session):**
- `.dadaia/tmp/software-engineer/20260827/T-050-34-invariants.md` (baseline capture this
  verdict cross-checks against)
- `specs/releases/0.5.0/reviews/S1-qa-close.md`, `S2-qa-close.md` (incl. its re-verdict),
  `S3-qa-close.md`, `S4-qa-close.md` (prior segment closes, referenced not restated)
- `specs/audits/20260827-canon-v6-first-audit/AUDIT.md`,
  `specs/audits/20260827-canon-v6-first-audit/FINDINGS.jsonl`
- `specs/bugs/BUGS.jsonl` (`test-v30-pyramid-shape-collect-only-subprocess-times-out-under-nauto-contention`,
  committed `343acc38`)
- This session's own commands: full-suite runs (§2.1), `dadaia ci push-gate-check` over
  `refs/heads/feature/0.5.0` at HEAD `343acc38` (11 objects), `dadaia doctor` /
  `specs doctor` / `backlog doctor` / `public doctor` / `ci preflight` (§2.2 row A22.1),
  `git diff --name-status 02eef219..HEAD -- tests` (§1.1)
