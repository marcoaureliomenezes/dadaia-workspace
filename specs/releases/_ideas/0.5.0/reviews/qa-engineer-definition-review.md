# QA Engineer — Definition Review — Release 0.5.0

**Reviewer:** qa-engineer · **Reviewed:** SPEC.md (1364 lines), PLAN.md (277 lines),
TASKS.md (1177 lines) at `specs/releases/_ideas/0.5.0/` · **Read also:**
`dadaia-test-stewardship` SKILL.md, `specs/memory/quality-assurance.md`, the grill handoff
`2026-08-26T120000Z-…adr-grill.handoff.json` (D1–D15).

---

## Axis 1 — Validations V1..V19

Most Vs (V1–V3, V7–V19) are commands with a checkable output (exit code, grep zero-hit,
line count, `git cat-file -e`). Two are **not fully falsifiable as written**:

- **V4/A3.2 (registration granularity).** SPEC §1.2's own ground truth states "124 [distinct
  registration commits], of which **79 register exactly one bug**" — a pure single-bug-per-commit
  count. FR3's `commit_granularity` marker `exact` requires **both** single-bug **and**
  "touches at least one file outside `specs/`" (SPEC §3/FR3 step 4). Nothing in §1.2 reports how
  many of those 79 single-bug registration commits also touch non-`specs/` files. A3.2 pins
  "**≥79 marked exact**" as if it were the same number as the measured "79 single-bug" — it is
  not provably the same set. **GAP.** Recommend: either restate A3.2/V4 as "≥79 single-bug
  registration commits" (the number actually measured) and drop the unverified equivalence to
  `exact`, or have the implementer independently measure the code-touching subset before
  pinning a threshold on `marked exact`.
- **V4/A3.3 (resolution granularity — the more serious one).** §1.2 measures "**155** resolved
  bugs whose first resolving commit is a release-level squash" by **commit-message pattern**
  (`chore: ship …`, `feat(v0.x) …`, `fix: 0.3.0 …` — SPEC line 74/79). FR3's mechanical
  `release-squash` marker is defined purely structurally: "the commit adds **more than one**
  bug's line" (SPEC §3/FR3 step 4, line 402). These are two different criteria. Since 117
  distinct resolution commits include 70 single-bug ones, the remaining 47 commits resolve
  470−70 = **400** bugs between them — under the *structural* definition, roughly 400 resolved
  records would be marked `release-squash`, not 155. A3.3 pins "**≥155 marked release-squash**"
  against the narrative-measured number while the algorithm computes the structural one. **GAP,
  MEDIUM.** Recommend product-engineer reconcile the two definitions in FR3 before
  implementation (either redefine "release-squash" narratively — matched by commit-message
  pattern — or explicitly re-measure and re-pin V4/A3.3 against the structural count so the
  acceptance is checkable against what the algorithm will actually produce).
- V6 (ref scope ≥295, `archive/*` tags =50) and V5 (idempotence) are cleanly falsifiable and
  correctly pinned — confirmed against the live repo (`git log --all --no-merges -- specs/bugs/`
  reachability and `git tag -l 'archive/*'` are exactly what V6 asks for).
- V13 ("import-linter contract count") is correctly grounded: `grep -c '^\[importlinter:contract'
  setup.cfg` = **9** on this repo today, matching SPEC's "nine at HEAD" claim (verified).

## Axis 2 — Test plan per FR

Intent/size and RED-first are stated as **standing rules** (§3 of SPEC, §1/§6 of PLAN) rather
than restated per-FR — acceptable, since `dadaia-test-stewardship` already governs intent
declaration and this avoids duplication (D-A/D15 posture). Per-FR specifics checked:

- **FR10 (behavior-map enforcer).** Five RED directions are enumerated explicitly (skill with no
  row / scoped `AGENTS.md` with no row / `DADAIA.md` section with no owner / row naming a
  nonexistent member / stale hash tuple) and each gets a named mutation fixture (A10.2). **PASS**
  — each direction is independently testable.
- **FR2 (schema-derived record model).** A2.2 is a genuine contract test (immutable-core write
  refused through the service seam; governance rewrite leaves every other byte identical) —
  checkable, seam-correct (service seam, not the JSONL file directly). **PASS.**
- **FR15 (doctor FINDINGS fold).** A15.2 gives two concrete fixtures (archived audit with one
  `open` record → error; live fully-terminal audit → archive-due WARN). **PASS**, though no
  explicit RED-before-GREEN sequencing note beyond the standing rule — acceptable given §3.
- **FR18 (`Measured by:` inventory).** "Every principle has a measure" is tested two ways: A18.1
  is a real **regression** contract test (adding a 10th import-linter contract without a
  principle goes RED — durable, re-run every commit). A18.2 ("every `Measured by:` command
  executed once, output captured") is a **one-time capture (V14)**, not a standing regression
  test — a principle's `Measured by:` check silently going stale later is caught only at the
  next audit (FR14 pillar 3), never at commit time. This matches D15's posture (audits measure,
  hooks don't gate) so it is **not a gap**, but the QA close (T-050-33) must say so explicitly
  rather than imply V14 is a permanent gate — currently T-050-33's description does state this
  correctly ("a `Measured by:` line pointing at a check nobody ran is decoration").

## Axis 3 — Segment closes

All four segments (S1/S2/S3/S4) have a `qa-engineer` close task (T-050-15/22/27/33) with a
concrete, cited acceptance-id list and a stated `APPROVE` criterion committed on the branch.
`rc` lane is defined (PLAN §0/§3, SPEC D-J) with a clear rule for `rc-N ≥ 2` (must trace to a
defect found on `develop`, on this scope only).

**FR16's dry-run acceptance (A16.2) — chain-naming precision, checked against the actual
`bugs.jsonl` on this repo:**

| Chain | Named with bug slug(s) in SPEC §1.1? | Verified |
|---|---|---|
| gitignore class | **Yes** — 8 explicit slugs listed (though the prose says "four recurrences" while 8 are listed — an internal miscount in the SPEC's own evidence table, worth a copy-fix) | checkable |
| certify probe (37-min re-bug) | **No** — only "named as firing 1 of the v0.4.4 FR23 evidence gate," no bug_id | **not** independently checkable by slug |
| frozen-clock → guard → guard's bug (3 hops) | **No** — described narratively, no bug_id for any of the three hops; the `frozen-clock-guard-tz-boundary-031` id used in FR2/FR7 examples does **not** exist in `specs/bugs/bugs.jsonl` (confirmed by grep — it is an illustrative example, not the real chain) | **not** checkable by slug |
| bug-event ledger family | **Partial** — `bug-event-field-with-unicode-line-separator-silently-drops-the-event` exists and is confirmed in the ledger; "the ESC/CWE-117 finding" names no bug_id or finding id | partially checkable |

**GAP, MEDIUM-HIGH.** A16.2 requires FR16 to "name, with evidence, at least the four documented
chains of §1.1," but three of the four chains give `project-auditor` no citable bug_id to search
for — only prose. This makes the acceptance harder to fail-safe: a dry run could plausibly claim
to have "found" the certify-probe or frozen-clock chain against the wrong bug records, and no
reviewer could check it against a stable identifier. **Recommend:** before FR16 lands (ideally
before T-050-01), `product-engineer` amends SPEC §1.1 to cite the real bug_id(s) for the
certify-probe bug, the frozen-clock bug and its guard bug (and the guard's own bug — three
ids), and the actual finding id if "ESC/CWE-117" is not itself a `bugs.jsonl` record.

## Axis 4 — Test-suite impact (existing tests that die or break)

Checked directly against the tree (grep), not assumed:

- **26 test files reference `ACTIVE.md`**, 4 reference `CLOSURE.md`/`CLOSURE-TEMPLATE`. FR4/FR12
  retire both. TASKS names no explicit qa-engineer demotion/deletion verdict for these — T-050-11
  and T-050-21's write sets say `tests/**`, which is broad enough to *permit* editing them, but
  the coverage-table discipline (D-F, R-4) does not explicitly require enumerating which of the
  26 die vs. get rewritten. **Recommend:** T-050-11/T-050-21's *Description* name the census (26
  `ACTIVE.md`-referencing files, 4 `CLOSURE.md`-referencing files) so the S1/S2 QA close can
  verify none were silently orphaned instead of demoted.
- **`tests/integration/test_precommit_backlog_scoping.py`** directly imports and exercises
  `_run_backlog_doctor_gate` from `dadaia_workspace/cli/commands/ci.py` (module docstring:
  "Integration tests for the W1-4 pre-commit backlog-gate scoping"). FR9/T-050-18 **deletes**
  `_run_backlog_doctor_gate` — this test will fail to import. **Its own file is not in T-050-18's
  write set**, which lists only `pre-commit-presence-gate.sh`, `pre-push-ci-gate.sh`,
  `cli/commands/ci.py`, and `tests/contract/**` — this file lives under `tests/integration/`.
  **CONCRETE GAP.** Same for `tests/e2e/features/test_backlog_precommit.py`, the CLI's
  git-hook-path E2E companion cited in that integration test's own docstring — also outside
  `tests/contract/**`. **Recommend:** T-050-18's write set explicitly add
  `tests/integration/test_precommit_backlog_scoping.py` and `tests/e2e/features/test_backlog_precommit.py`,
  and its Description state the deletion/rewrite verdict (this is a `qa-engineer` verdict per
  test-stewardship §E — the implementer must not silently delete or skip these to go green).
- **`tests/contract/test_rules_skills_map.py`** retires into `test_behavior_map.py` (T-050-19,
  named correctly). Three *other* files also reference `rules_skills_map`/`rules-skills-map.json`:
  `tests/helpers/scan_population.py`, `tests/contract/test_frozen_clock_aging_ratchet.py`,
  `tests/contract/test_public_scripts_thin_wrapper.py`. T-050-19's write set (`tests/**`) is
  broad enough to cover them but none is named — same class of risk as above, lower severity
  since `tests/**` at least is the declared write set (unlike the FR9 case).
- **8 files reference `BugEvent`**, impacted by FR2's `BugEvent` → `BugRecord` rename — covered
  by T-050-08's `tests/**` write set; no specific gap found.
- SPEC-DOC-036/038 golden fixtures (`tests/unit/features/specs/test_doctor_golden.py`,
  `_golden/doctor_golden_v0155.json`, `test_doctor_taxonomy_disposition.py`) are impacted by
  FR15's regex-path deletion — T-050-25's write set (`doctor_closure_audit.py`, `tests/**`)
  covers this generically; acceptable.

**LARGE-tier estimate vs. the census ratchet (100).** SPEC §3 standing rule already forbids
**any** new `tests/e2e/**` file without a named `qa-engineer` exception recorded in the
segment's QA artifact (good — directly enforces the census ratchet without a new mechanism).
No segment's task currently pre-declares an expected exception, which is consistent with "the
release adds no LARGE tests" being the default — fine as written, but the S1–S4 QA close
templates should explicitly confirm **zero** exceptions were granted (or name them) rather than
leave it implicit.

## Axis 5 — Migration safety

| Requirement | Covered by | Verdict |
|---|---|---|
| Idempotence | T-050-09 (fixture repo double-run), T-050-10/V5 (real ledger double-run, byte-diff) | PASS |
| Dry-run mode | T-050-09 explicitly forbids running the algorithm on the real ledger before it is proven on a synthetic fixture repo | PASS |
| Byte-frozen legacy archive assertion | A3.6/V test: `git diff --stat` empty for `specs/bugs/_archive/archive.jsonl` before/after | PASS |
| Rollback via pushed tag | FR6/T-050-14: `archive/specs-archive-<date>` tag created **and pushed** before the destructive deletion, reachability demonstrated (A6.4/V8) before deletion runs, operator present | PASS — this is the strongest-gated step in the release |

No migration-safety gap found; this is the best-covered axis of the release.

## Axis 6 — Path drift

Checked every write-set path named across TASKS.md's `S1`–`S3` tasks (FR1–FR16) against HEAD
with direct filesystem checks (not inference). **All existing paths verified present**:
`dadaia_workspace/features/specs/{doctor,doctor_structural,doctor_closure_audit,doctor_release,
doctor_governance,scaffolder,catalog}.py`, `features/bugs/service.py`,
`core/models/bugs.py`, `infrastructure/jsonl_bug_store.py`, `features/spec_context/gate_policy.py`,
`hooks/sdd_gate.py`, `cli/commands/{bugs,ci,specs}.py`, `public/schemas/bugs/bug-event-v1.schema.json`,
`public/scripts/{pre-commit-presence-gate,pre-push-ci-gate}.sh`,
`public/entities/rules-skills-map.json`, `public/skills/dd-bug-fix/`,
`public/skills/dd-release-implement/{CLOSURE-CHECKS,CLOSURE-TEMPLATE}.md`,
`public/skills/dd-audit-project/{RUBRIC,TOOLING}.md`, `public/agents/project-auditor.md`,
`specs/{audits,releases,bugs}/README.md`, `specs/backlog/remote-bugs`, `specs/assets`,
`tests/contract/test_rules_skills_map.py`, `specs/memory/{architecture,quality-assurance,
tech-stack}.md`, `specs/bugs/{bugs.jsonl,_archive/archive.jsonl}`, `specs/backlog/BACKLOG.md`,
`specs/_archive`, `specs/releases/ACTIVE.md`, `setup.cfg`. **No drift found** (unlike v0.4.5,
which had several) — this is a well-grounded write-set for a Draft of this size.

## Axis 7 — Windows/xdist

Open bug `windows-xdist-workers-crash-on-unit-fast-tier` (LOW, still `reported`, not resolved —
confirmed by last-event scan of `bugs.jsonl`) is **not mentioned anywhere in SPEC or TASKS**.
AS-4 correctly handles the bug's *migration* (stays open, not picked, not fabricated as
`caused_by: none`), but the release adds a nontrivial number of new `unit`/`contract` tests
(FR2, FR3's fixture-repo test with real subprocess `git` calls, FR9's hook fixtures, FR10's five
mutation fixtures, FR18's contract-count test, FR19's monotonic-numbering test) with **no
stated tier-placement guidance** relative to the open crash. T-050-09 in particular spins up a
synthetic git fixture repo with subprocess calls — exactly the shape of test most likely to add
memory/IO pressure on the crash-prone windows-latest unit-fast tier if placed under
`tests/unit/**`. **GAP, LOW** (matches the bug's own severity). **Recommend:** T-050-09's
Description state the tier placement explicitly (`tests/contract/` or `tests/integration/`, not
`tests/unit/`, given the subprocess/git cost) and T-050-34 (FR22 invariants capture) or the S1
QA close note whether the new fixture-repo test's addition correlates with any recurrence of
the windows-xdist crash during CI development of the segment.

## Bug-surface direction, stated explicitly

Every FR carries its own direction claim (net-additive/net-negative) with bug-history evidence,
and §3/A22.3/A22.4 require the release to report the per-FR net honestly rather than hide an
addition inside a total — this is itself the correct structural answer to the standing
architecture-review order, and is the one property this Draft is most disciplined about. The
release as a whole is **declared net-additive in production LOC** (a canon is being built) and
**net-negative** in specific engines it names separately (FR9 hooks, FR12 AI-surface, FR15
regex-parsing, FR21 constitution). This is an honest accounting posture, not a "tests green"
verdict, and satisfies FR24/DADAIA.md §7's bug-surface-delta requirement **for the definition
stage** — the actual delta can only be verified at each segment's QA close once real diffs
exist.

---

## Verdict: **REWORK**

The three concrete, evidence-backed gaps below are what block APPROVE-FOR-FOLD; the rest of
the Draft (migration safety, path grounding, segment structure, bug-surface accounting) is
well-built and should not be re-litigated.

### Ordered amendments for `product-engineer`

1. **(Axis 3, MEDIUM-HIGH)** Amend SPEC §1.1 to cite real `bugs.jsonl` bug_ids for the
   certify-probe chain, the frozen-clock chain's three hops, and the bug-event-ledger family's
   second symptom (or its finding id) — three of the four chains FR16/A16.2 must rediscover are
   currently unnamed by slug and therefore not independently checkable.
2. **(Axis 1, MEDIUM)** Reconcile FR3's structural `release-squash` granularity marker
   ("commit adds more than one bug's line") against §1.2's narrative measurement of "155
   resolutions inside release squashes" (measured by commit-message pattern) — these are
   different criteria that will likely diverge by roughly 2.5x on the real ledger; re-pin
   A3.3/V4 against whichever definition the implemented algorithm actually produces.
3. **(Axis 1, LOW-MEDIUM)** Either drop the "≥79 marked exact" equivalence in A3.2/V4 for
   registration commits (the measured number is "79 single-bug," not "79 code-touching
   single-bug"), or have the migration task independently measure the code-touching subset
   before pinning it.
4. **(Axis 4, LOW)** Add `tests/integration/test_precommit_backlog_scoping.py` and
   `tests/e2e/features/test_backlog_precommit.py` to T-050-18's write set with an explicit
   deletion/rewrite instruction — both directly exercise the code FR9 deletes and are outside
   its stated `tests/contract/**` scope.
5. **(Axis 7, LOW)** T-050-09's Description should state the tier placement of the new
   fixture-repo derivation test explicitly, given the open `windows-xdist-workers-crash-on-unit-fast-tier`
   bug and that test's subprocess/git cost profile.

None of these require re-litigating a D1–D15 ruling or an AS-1…AS-11 assumption; all five are
authoring-precision fixes inside the Draft `product-engineer` already owns.

## Security/privacy leakage note

No home-absolute path, IP, hostname, operator email or denylisted term was transcribed into
this review — every path cited is workspace-relative and every command run was read-only
(`git log`, `grep`, `find`, `python3 -c` reading `bugs.jsonl`). This review itself introduces no
new leakage surface. Two structural points worth security-reviewer's attention at
implementation time, already named correctly by the Draft itself: FR3's migration report and
FR16's audit folder are **committed forever inside `specs/`** and must carry no path/IP/hostname
(T-050-36 already assigns this to `security-reviewer` — no gap here, flagging for continuity).
