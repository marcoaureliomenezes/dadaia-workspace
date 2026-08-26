# QA Engineer — Test-Minimization Review — Release 0.5.0

**Scope.** Operator demand: cleaner architecture, fewer tests, minimization that keeps
coverage and value, no more unmarked temporary tests, no tests that ossify the
architecture — quantitative, not opinion. Reviewed: `specs/releases/_ideas/0.5.0/{SPEC,PLAN,
TASKS}.md` at `10320654` (`Em revisão`). Evidence: `reviews/test-minimization-literature.md`,
`reviews/architecture-metrics-baseline.md` §6, `reviews/bug-history-forensic-100.md` §4/§5,
`dadaia-test-stewardship` SKILL.md + `PARAMETERS.md`, `specs/memory/quality-assurance.md`.
Counts below are re-measured on the working tree (`grep`, `find`) where marked *(measured)*,
otherwise cited from the evidence files with their own provenance. This is a **distinct**
axis from `reviews/qa-engineer-definition-review.md` (content/acceptance review, already
folded, §9.1.3/§9.2) — that review does not cover test-count minimization at all.

---

## Headline finding, stated first

**PLAN.md §"Test stewardship" states outright: "the release is net-additive in tests by
nature."** No item in SPEC §6 Validations (V1–V24) measures the test suite's own size —
V10/V11/V12/V19 measure production LOC, AI-surface lines and always-on tokens, never test
file/function count. The operator's explicit demand ("MENOS testes") has **no metric tracking
it anywhere in this Draft.** This is the single most consequential gap (Amendment 1, below):
everything else in this review is secondary to closing it.

---

## 1. Inventory — tests this SPEC retires or must retire

| Test surface | Baseline | 0.5.0 as written | Disposition owner named? |
|---|---|---|---|
| Event-fold + coherence machine (`BugEvent` state machine, terminal/non-terminal kinds) | 8 files reference `BugEvent` (measured) | T-050-08 deletes the fold; write set `tests/**` generic — **no file-level census**, unlike FR4's | **No** — gap |
| `ACTIVE.md`/`CLOSURE.md` parsers + readers | 26 files ref `ACTIVE.md`, 4 ref `CLOSURE.md`/`CLOSURE-TEMPLATE` (measured, matches definition-review QA-6, already applied) | T-050-21A: "enumerate them, and rewrite or delete each under a recorded `qa-engineer` verdict" | **Yes**, but verdict deferred to segment close — see Amendment 2 |
| `test_precommit_backlog_scoping.py` (imports `_run_backlog_doctor_gate`, deleted by FR9) | 1 integration file | T-050-18 write set names it; verdict deferred to `qa-engineer` at task time | **Named, verdict deferred** — see Amendment 3 |
| `tests/e2e/features/test_backlog_precommit.py` (git-hook-path companion) | 1 e2e file — LARGE tier | Same as above | **Named, verdict deferred** |
| SPEC-DOC-036/038 regex golden fixtures (`test_doctor_golden.py`, `_golden/doctor_golden_v0155.json`, `test_doctor_taxonomy_disposition.py`) | 3 files (measured, prior definition review) | T-050-25/25A delete the regex path and every surviving `CLOSURE.md` parser; write set `tests/**` generic | **No** — same gap as row 1 |
| `test_rules_skills_map.py` (9 checks) | 1 file, 2 registered bug histories attached | T-050-19: retires wholesale into `test_behavior_map.py`, name-diff with zero-hit residue required | **Yes** — the strongest-specified retirement in the release |
| BL-DUP rule + its tests | in `features/specs/doctor_governance.py` and its test file(s) | T-050-13: "**deleted**, not disabled — with one line per exit in an append-only file, a duplicate ledger line is structurally impossible" | **Yes** — best-in-class: the invariant became unnecessary, not merely unwatched |
| `consumed_backlog.json` sidecar-absence fixtures | implicit in BL-STALE tests | T-050-13A relocates 18 sidecars; behavior preserved, not reduced | n/a (relocation, not a deletion) |

**Recommended additions QA would add, not currently in TASKS:**

1. **T-050-08's write set should carry the same census discipline as T-050-21A** — name the
   `BugEvent`-referencing files (8, measured) and require a per-file disposition, not a bare
   `tests/**`. The event-fold deletion is the release's largest single production-code
   deletion (SPEC §8, FR2 "net-negative") and currently has the weakest test-side accounting
   of any FR in the release.
2. **T-050-25/25A should do the same** for the 3 SPEC-DOC-036/038 golden-fixture files.
3. **T-050-18's qa-engineer verdict on the two orphaned hook tests should be pre-committed to
   DELETE, not left open for "rewrite or delete."** Pre-commit becomes advisory-only under
   FR9 — the E2E test's entire premise (pre-commit *blocking* a bad stage) is gone. The three
   new contract fixtures T-050-18 already writes (pre-commit exits 0; preflight non-blocking;
   unresolvable-runner still refuses) supersede what the LARGE-tier E2E file asserted, at a
   cheaper tier. Rewriting it at E2E tier would be a change-detector test of the new
   advisory behavior — exactly the class §B of `dadaia-test-stewardship` prohibits. **QA
   verdict, stated now: delete both files; the three new contract fixtures are their
   replacement, cited in T-050-18's commit message per the stewardship separation of
   powers.**

**Before/after, as the SPEC stands:** not computable — no FR states an exact test-file or
test-function delta (Amendment 1). **Before/after with this review's recommended deletions
applied:** at minimum **1 E2E file removed with no replacement at that tier**
(`test_backlog_precommit.py`), on top of what TASKS already retires (`test_rules_skills_map.py`
whole-file, BL-DUP's tests, the regex-parsing goldens).

---

## 2. Structure-sensitive tests — the ossification list

*(measured directly: `grep -rnE "^\s*from dadaia_workspace… import …_[A-Za-z]" tests
--include=test_*.py`, then hand-filtered to true private-symbol imports, excluding module
aliasing false positives such as `import registry as _registry`.)*

Representative file:line evidence (24 true private-symbol imports across 22 files measured
this way — close to, not identical to, the baseline's own 24/14 heuristic; the two counting
methods diverge on whether repeated `from dadaia_workspace.hooks import _common` across 6
files counts once per file or once per statement — both readings agree the order of
magnitude and both are ≥ 20):

| File:line | Private symbol | 0.5.0-relevant? |
|---|---|---|
| `tests/integration/test_precommit_backlog_scoping.py:23` | `_run_backlog_doctor_gate` | **Yes — dies with FR9** (§1 above) |
| `tests/unit/hooks/test_common.py:18` (+5 siblings) | `dadaia_workspace.hooks._common` | No — `hooks/` untouched |
| `tests/unit/features/panel/test_static.py:16,97` | `_MIME_BY_EXT`, `_ASSETS` | No — `panel/` untouched |
| `tests/unit/infrastructure/test_agents_index.py:10` | `_parse_write_allowlist` | No |
| `tests/unit/features/spec_context/test_doctor_gc.py:261` | `_resolve_mode` (`sdd_gate.py`) | Adjacent — `sdd_gate.py` touched by FR4/FR11, symbol unrelated to `_active_field` |

**Only 1 of ~22–24 structure-sensitive tests dies as a side effect of 0.5.0's own scope**
(the FR9 deletion, §1). The other ~21–23 are pre-existing debt this release neither adds to
nor reduces — they remain the exact Hyrum's-Law liability the operator named ("tests that
ossify the architecture"), untouched.

**Proposed ratchet (not for 0.5.0's own scope — see Amendment 4 for placement):** a contract
test greping `tests/**` for `from dadaia_workspace… import … _name` outside an explicit
inline-commented allowlist (documented-contract reason required), pinned at the measured
count and ratcheting only downward — same law as the LARGE census and the complexity
ceilings already use. **Where it lives:** `tests/contract/test_module_size_ceiling.py`'s
sibling pattern (measure-then-pin-then-ratchet) is the existing home for exactly this shape;
a new `tests/contract/test_no_private_symbol_imports.py` follows it. This is new-check work
and **conflicts with FR18's A18.3 ("zero new checks")** if attempted inside 0.5.0 — it is
correctly a **companion-release candidate**, not a blocker here, but 0.5.0's own QUALITY.md
mandatory rewrite (§5, closure obligation) is the right place to **record the 22–24 baseline**
so the next release's principle has a number to ratchet from instead of re-measuring cold.

---

## 3. Temporary tests — the marking rule

TASKS.md §"Standing rules" already states: *"Test intent at birth, per
`dadaia-test-stewardship`."* This governs **every new test 0.5.0 writes** — correctly. It
does **nothing** for the pre-existing gap: **302 of 396 files (76%) carry no `Intent:` header
and are SCAFFOLD by the taxonomy's own default** *(measured, baseline §6)*, and
`check_test_intent_declared.py` gates only `tests/e2e/**` — 302 undeclared SCAFFOLD files sit
outside `tests/unit`, `tests/contract`, `tests/integration` with no mechanism that will ever
expire them.

**0.5.0 does not touch this.** No FR, no task, extends the intent gate beyond `tests/e2e/**`,
and no closure obligation in §5 requires the 302-file backlog to shrink. The release's own
"Test dispositions" closure obligation (§5) covers demotion/quarantine/SCAFFOLD-expiry for
**tests this release itself touches**, not a sweep of the inherited debt.

**Recommend:** state explicitly in T-050-33's `S4` close (or a new closure-obligation line)
that the 302-file gap is **measured and recorded, not silently left implicit** — a single
`grep -rlE "^\s*Intent:" tests --include=test_*.py | wc -l` line in the closure record costs
nothing and turns an invisible debt into a numbered one the next release can ratchet against,
exactly the discipline FR18/FR19 apply to everything else this release inventories.

---

## 4. Test-layer bug surface — the 21 guard-breeds-guard bugs

*(from `bug-history-forensic-100.md` §4 P4: 21/100 bugs live in the test/ratchet layer
itself — TEST-ONLY 14 + 3 guard-chains + Windows-only 5.)*

| Shape | Chain | Does 0.5.0 remove the generator? |
|---|---|---|
| Frozen-clock ratchet chain | `no-ratchet-against-frozen-clock…` (ratchet added as fix) → `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` (mis-scan, fixed by exclusion BRANCH) → `windows-xdist-workers-crash-on-unit-fast-tier` (**open**) | **No.** T-050-09/T-050-34 only *place new tests away from* the crash-prone tier and *report* recurrence — the ratchet itself is untouched. Generator survives. |
| Citation-enforcer chain | `citation-enforcer-resolves-projected-instance-paths-against-the-checkout` → `citation-mutation-fixtures-never-turn-red-on-windows` | **Partially.** T-050-19 deletes the whole enforcer file the bugs lived in, but **replaces it with 5 new mutation fixtures** — the same shape class (`RED`-direction mutation fixtures) that produced the Windows bug. Risk carried forward, not removed. |
| Atomic-writer drift guard | `atomic-writer-drift-guard-is-brittle…` (+279 test lines replacing an 18-line guard) | **No** — `core/atomic_write.py` is reused as-is by FR2/A2.9; the brittle-guard bug is untouched, and FR2 adds a **second** call site (record rewrite) through the same guard, widening its blast radius without revisiting the guard's own bug history. |
| Panel/specs-resolver timeout chain | `panel-e2e-readiness-flaky…` → `panel-command-readiness-flaky…` → `specs-resolver-context-tests-flaky…` (10→30s twice) | **Out of scope**, correctly — `panel/` untouched by 0.5.0. |
| TEST-ONLY 14 (undifferentiated) | — | No FR names or addresses this bucket generically. |

**Verdict on this axis:** 0.5.0 avoids *aggravating* the one open item (windows-xdist) via
correct tier placement (already applied per definition-review QA-5), but **removes the
generator of zero of the four named guard-breeds-guard chains** and **recreates one
(mutation fixtures) in a new file**. This matches the standing order's own bar imperfectly:
"reduce implementation complexity... never bolt a puxadinho onto an existing feature." A
new mutation-fixture file is not a puxadinho by that definition (it replaces, not adds to,
the old enforcer) — but it does not resolve the Windows-fragility class either. **Recommend
(Amendment 5):** T-050-19's five mutation fixtures each get an explicit cross-platform CI
run (not merely "watched," which is FR22's posture for the xdist bug) before `S2` closes,
citing the two prior bug ids by id in the task's done-criterion, the same discipline A16.2
already requires of the audit.

---

## 5. Pyramid & tiers

*(measured, `architecture-metrics-baseline.md` §6, `pytest --collect-only -q`.)*

| Tier | Files | Functions | Share of 1,859 |
|---|---:|---:|---:|
| unit | 244 dirs / 56 marked | 1,376 | 74.0% |
| integration | 84 dirs / 34 marked | 241 | 13.0% |
| contract | 53 dirs / 31 marked | 200 | 10.8% |
| e2e (LARGE) | 15 dirs / 5 marked | 42 | 2.2% |

Shape is already close to Google's 80/15/5 target the literature review names (§1.4); the
gap is at the **contract** tier (10.8% vs an implied ~5% if contract nests under "small").
Not a defect 0.5.0 needs to fix — flagged only because no FR states the target shape or
checks drift against it (literature Part 3 rule 9: "drift > 5pp fails the closure size
accounting"). **0.5.0 adds no such check and adds it correctly nowhere (A18.3 discipline)**
— recommend recording the measured shape in T-050-34's V19 capture as a baseline line, not
a new gate.

**LARGE-cap contradiction — confirmed, unresolved by 0.5.0.** Three numbers for one
parameter: `PARAMETERS.md` says cap **30** (current ~84); `tests/AGENTS.md` says **30**;
`specs/memory/quality-assurance.md` says the census **is 100** (54 pytest e2e + 46
Playwright) and **that number is the ceiling**. Measured today: 42 `tests/e2e/**` functions,
15 `e2e`-marked. **No FR touches `PARAMETERS.md` or resolves this**, and FR18/T-050-29
explicitly promotes "the LARGE-test census ceiling" to a Part-1 principle **without
reconciling which of the three numbers it promotes** — A18.1's contract test only checks
the import-linter count agrees with `setup.cfg`, nothing checks the census number agrees
across its three homes. **This is the exact "Sensitive-Equality smell in the doctrine
itself" the literature review already named** (Amendment 6, below).

**e2e under-marking, confirmed, unaddressed.** 42 functions live under `tests/e2e/**`; only
15 carry the `e2e` pytest marker (27 are `integration`-marked or unmarked). This means the
LARGE-tier count any tier-based selector (`-m e2e`) reports is **wrong by 2.8x** relative to
directory placement. No FR corrects the marker/directory mismatch. **Recommend (Amendment
7):** T-050-19 or T-050-34 adds a one-line note in the closure record naming this drift as
measured (not fabricated), leaving the fix itself to a companion release per A18.3's
zero-new-checks discipline.

---

## 6. Value measurement — mutation floor

`mutmut==3.7.0` is pinned (memory), cadence 1×/release off the push path,
`run_mutation_baseline.sh` exists. **Venv check this session:** no `mutmut`/`pip` binary
reachable from this read-only session — treated as **unverified, not absent** (a value
nobody assessed is `null`, never a default). FR14/T-050-24's "mutation" measures are audit
findings on bug records, unrelated to mutation testing. **0.5.0 schedules no mutation
baseline pass anywhere in TASKS**, though the stewardship cadence implies one is due.

**Recommend (Amendment 8):** add `V-MUT` to T-050-34 (already runs V18/V19): one
`run_mutation_baseline.sh` pass over `core/` — the package gaining the most new pure-function
surface (FR2's record model, FR3's derivation) — floor = measured baseline, ratchet up only.
Zero-kill tests outside a named SENTINEL enter the closure curation table (§H). Measurement,
not a new gate; compliant with A18.3.

---

## 7. Per-FR test net — ADDS vs DELETES

| FR | Adds (named in TASKS) | Deletes (named in TASKS) | Net | Flag |
|---|---|---|---|---|
| FR1 | TREE-8, `--recipe`, double-`upgrade` compare, V20 7-arm + V21 ignore fixtures, semver-regex inversion (2 files) | none named | **ADD only** | **Yes** — 3 tasks, no offsetting reduction; name what the 4 retired scaffold `README.md`s' own tests supersede |
| FR2 | A2.1–A2.9 contract tests (immutability, redaction, archive idempotence, atomic-write refusal) | Event fold + state machine + legacy reader (8 `BugEvent` files exist; **none named for deletion**) | **Unclear — census gap** | **Yes** — see §1 Rec. 1; net unverifiable without the census |
| FR3 | Fixture-repo unit tests + 1 contract-tier git test | none (`migrate_v5.py` framed "deletable after," not deleted here) | **ADD only, justified** | No — recommend `Intent: SCAFFOLD — expires: <deleting release>` (Amendment 10) |
| FR4 | RELEASE.jsonl fold + sha-immutability contract tests | 26+4 `ACTIVE.md`/`CLOSURE.md` census, verdict deferred | **Best-specified reduction lever** | No |
| FR5 | backlog_histo + 18-record relocation fixtures | BL-DUP rule + tests — structurally impossible, deleted not disabled | **Net negative (best-in-class)** | No — model for other FRs |
| FR6 | 4 FROZEN-path fixtures + V8 clone-reachability | old single-root fixture (unnamed) | **Small ADD** | No |
| FR9 | 3 new contract fixtures | `_run_backlog_doctor_gate`/`_staged_backlog_paths` + 2 orphaned tests, verdict deferred (this review pre-commits to DELETE, §1) | **Net negative once the DELETE verdict lands** | No |
| FR10 | 5 mutation fixtures | `test_rules_skills_map.py` whole file (9 checks) | **Roughly flat, count-wise** | **Yes — see §4.** New fixtures repeat a Windows-fragile shape. |
| FR13 | New finding-record schema fixture + FROZEN-for-auditor fixture | none | **ADD** | No — legitimate new artifact class |
| FR15 | none named beyond fold test | SPEC-DOC-036/038 regex path + every surviving `CLOSURE.md` parser, "LOC delta negative" stated explicitly | **Net negative (best-in-class)** | No — cite as the model |
| FR18 | 1 contract-count test (traceability, meta-check) | none | **Small ADD, justified** | No — A18.3-compliant, cheap |
| FR19 | 1 monotonic-numbering test | none | **Small ADD** | No |

**Two clean models the release already contains** (FR5, FR15): delete a check because the
invariant became structurally impossible, or because the artifact it parsed no longer
exists — never disable, never bypass. **Recommend every future FR in this release's own
`rc` rounds be measured against this same bar** before any is accepted as "done."

---

## 8. Verdict

**As defined, 0.5.0 does not demonstrate it makes the suite smaller — it explicitly disclaims
the goal ("net-additive in tests by nature", PLAN §"Test stewardship") and provides no
metric that would let a reviewer check the claim either way.** The release **does** contain
genuine, well-specified reductions (FR5's BL-DUP, FR15's dead-parser sweep, FR4's 30-file
census with a verdict requirement) that, if the deferred qa-engineer verdicts are resolved
toward DELETE rather than REWRITE wherever coverage is already superseded (§1), could make
the release net-negative in test count. **Nothing in the Draft currently forces that
outcome or would even detect it.**

This closes a measurement gap the same way FR18/FR19 already close it for principles and
ADRs — none reopens a D1–D15 ruling, an AS-1…AS-15 assumption, or an already-folded pass-1/
pass-2 disposition; all are additions to existing write sets, done criteria, or the closure
record, in the same register as this review's predecessor (`qa-engineer-definition-review.md`).

### Ranked amendments for `product-engineer` (12)

1. **(§0/CRITICAL)** Add `V-TESTCOUNT`: `pytest --collect-only -q` before (baseline captured)
   and after (`T-050-34`), per tier, alongside V18/V19 — measurement, compliant with D15/A18.3.
2. **(§1/HIGH)** T-050-08 enumerates the 8 `BugEvent`-referencing files, per-file disposition.
3. **(§1/HIGH)** T-050-25/25A enumerates the 3 SPEC-DOC-036/038 golden-fixture files.
4. **(§1/MEDIUM)** T-050-18's hook-test verdict pre-committed to DELETE, not left open.
5. **(§3/LOW)** T-050-33 records the measured 302/396 undeclared-SCAFFOLD count.
6. **(§4/MEDIUM)** T-050-19 names the two prior Windows bug ids and requires a cross-platform
   CI run of the five new mutation fixtures before `S2` closes.
7. **(§5/MEDIUM)** QUALITY.md's mandatory rewrite reconciles the LARGE-cap 3-number
   contradiction (30/30/100) into one source — documentary, A18.3-compliant.
8. **(§5/LOW)** Record the e2e directory-vs-marker mismatch (42 vs 15) as known drift.
9. **(§6/MEDIUM)** Add `V-MUT` to T-050-34: one mutation-baseline pass over `core/`.
10. **(§7/LOW)** T-050-09's tests carry `Intent: SCAFFOLD — expires: <release>`.
11. **(§7/LOW)** FR1's tasks name at least one existing test file each retires/supersedes.
12. **(follow-up)** File the private-import ratchet (§2) and intent-header extension (§3) as
    backlog candidates for a companion test-minimization release.

## Security/privacy leakage note

No home-absolute path, IP, hostname, operator email or denylisted term is transcribed into
this review; every command run was read-only. No `mutmut`/`pip` binary was found in this
session — reported as unverified, never fabricated. Amendments 9/12 route new measurement
capture through `.dadaia/tmp/<agent>/<YYYYMMDD>/`, per the release's own redaction discipline.
