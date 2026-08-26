# PLAN — Release 0.5.0 — governance, lineage and audits

**Status:** Em revisão
**Release ID:** 0.5.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/_ideas/0.5.0/SPEC.md`
**Location:** `specs/releases/_ideas/0.5.0/` — a future-release Draft; promoted by `git mv`
to `specs/releases/0.5.0/` when `v0.4.5` archives (operator ruling D6 of 2026-08-23).
**Branch (at promotion):** `feature/0.5.0`, cut from `main` at the shipped `v0.4.5`
(SPEC AS-5; branch model: `DADAIA.md` §4, operations: `dd-gitflow-default`).
**Segments:** `S1 … S4` — internal work boundaries, each closed by a `qa-engineer` review
**committed on the branch**, no merge, no PR (SPEC D-J).
**Candidates:** `rc-1 … rc-N`. `rc-1` burns when the **whole** scope is implemented,
gate-green and QA-closed, and is merged into `develop`; `rc-2 … rc-N` are adjustment rounds
on that same scope; the final `rc` carries memory → closure → archive and ships. If nothing
is found, the final `rc` **is** `rc-1`.
**Folded three times (SPEC §9):** nine reviews, 55 + 10 + 22 = **87 dispositions**, none
dropped. Fold 3 is quantitative — every claim carries `baseline → projected`.

---

## 0. Terms, defined once (this release will be read by people new to the repo)

| Term | Meaning here |
|---|---|
| **Arm A / Arm B** | The two lanes every demand takes (`DADAIA.md` §1). Arm A = feature work: backlog → release definition → implementation → audit. Arm B = a bug (the tool broke a contract it already promises), fixed on the spot, never through a release. |
| **rc-N** · **Segment** | `rc-N` = "release candidate N", a **state of the specs**, never a branch name; each `rc` burns exactly one `feature/{M.m.p}` → `develop` merge. A **segment** (`S1 … S4`) is a work boundary *inside* one release, closed by a QA review committed on the branch — it burns no `rc` and opens no PR. |
| **Puxadinho** | Brazilian Portuguese for a lean-to shack bolted onto a house. Here: a fix that adds a branch, a flag, a special case, a second code path, a cross-feature reach-in or a new side effect instead of fixing the structure. Refused by the operator's standing order, whatever the tests say. |
| **Seam** · **FR23** · **the gate** | *Seam*: a place where a test or a replacement can be inserted without editing the module under test — "fix at the seam" = change one boundary, not N call sites; a **write seam** is the one code path through which an artifact may be written (SPEC AS-16). *FR23*: requirement 23 of release v0.4.4, the evidence gate on a `resolved` record — its **three fields** (`evidence_loop`/`_seam`/`_diff`) exist in the v5 schema and are **restored** into the v6 record (SPEC FR2). *The gate*: the one PreToolUse hook (`pre_gate`) classifying each file write by path class × presence × phase × mode; it never reads task markers. |
| **Provenance marker** | SPEC D-A: a closed-vocabulary field recording *how* a value was obtained — `registration_granularity` and `resolution_granularity` (`exact\|release-squash\|ledger-only`), one per derived sha, and `lineage_source` (`declared\|text-reference\|null`) on `caused_by`. There is no field called `commit_granularity`. |
| **`surface` enum** | SPEC FR2: `surface` stops being free text and becomes a closed enum whose **single source** is the feature-package list the import-linter independence contract uses (SPEC A2.12 ↔ A18.5). Free text moves to `component`. Without it, recurrence is not computable — 100 bugs used **86** distinct component strings. |
| **Pillar 1 / 2 / 3** | The three halves-and-a-half of one audit: bug history, spec compliance, memory/constitution drift. They always run together (ruling D6). |
| **Histo** · **live photo** | A *histo* is an append-only `*_histo.jsonl` beside an area's `_archive/` holding that area's exits (`bugs_histo`, `backlog_histo`, `releases_histo`). A *live photo* is the document that keeps only the current state — `BACKLOG.md` after FR5 carries `## ACTIVE` and nothing else; what left lives in the histo and in git. |
| **Thawed tree** · **Presence** · **verdict gate** | *Thawed tree*: the working tree before the release directory is `git mv`'d into `_archive/` (which makes it FROZEN) — the six-axis review runs there because a reviewer must be able to request a change. *Presence*: the advisory record a MUTATING write leaves naming its session; it never blocks (NO-LOCKS), it surfaces a race. *Verdict gate*: the required CI job refusing a PR without an APPROVED `security-reviewer` handoff covering the PR head sha, on both edges. |
| **Purge-on-pick** · **one-axis law** | *Purge-on-pick*: removing a picked backlog slug's `## ACTIVE` subsection in the **same commit** that creates the release SPEC — `project-manager`'s step, never `product-engineer`'s. *One-axis law*: the release id **is** the package version, one lineage, no second numbering; "operator law O5" is the ruling that a version may be **minted without being published**. |
| **TREE-5 / TREE-8** | `specs doctor` structural rules. TREE-5 is the existing scoped-`AGENTS.md` hash-projection regime; **TREE-8** is new in FR1 — "nothing beyond canon", WARN-only. |
| **Ratchet** | A measured value pinned in a test and allowed to move in one direction only (the law `test_module_size_ceiling.py` and `test_import_linter_ignore_cap.py` already use). A **test-suite ratchet** measures the suite itself and lives in `tests/contract/`; a **product check** is a doctor rule, CI job or hook exit that can fail a consumer's tree. SPEC A18.3 governs the second kind only. |
| **Review ids** | `SA-*`/`SA-R*`/`SA-Q*` = `software-architect` (folds 1/2/3) · `A-*`, `SEC-R*`, `S-*`, `N-*` = `security-reviewer` · `QA-*`/`QA-Q*` = `qa-engineer` · `AI-*` = `ai-engineer` · `CR-*` = `code-reviewer` · `AR-*` = an architecture ruling requested by a task · `BL-CONFLICT` = a backlog cross-ownership adjudication. All resolve in `reviews/`; SPEC §9 is their index. |

---

## 1. Strategy

One ordering principle: **build the record, fill it from history, then teach the readers.**

This release is the inverse of `v0.4.5`: that one was a demolition whose danger was deleting a
net; this one **adds a canon**, and a governance release is exactly the shape that grows the
surface it governs. Five constraints hold it — three of principle, two of arithmetic:

1. **Nothing here becomes a blocker.** D15 is an acceptance, not a preference: skills
   instruct, audits measure, hooks and the CLI act only at the publication boundary. Zero
   blocking validations added; **two removed** (FR9).
2. **Nothing here is written by hand that git already knows.** Every sha is derived
   (FR3/FR8), every stored sha is a cache with one reader, and the derivation lives in
   `core/` — not in the module that is meant to be deletable.
3. **Nothing here is asserted that no check measures.** A principle without a `Measured by:`
   is not admitted, FR18 writes no new product check, and a principle must be **true when
   accepted** — hence the independence contract is completed (20/24 → 24/24) *before*
   promotion.
4. **Four numbers are gates** (fold 3): test functions **≤ 1 859** (A22.9/V25), always-on
   tokens **≤ 22 011** (A11.3/V34), `#upgrade` **CC ≤ 26** / `#doctor` **CC ≤ 30** with
   `max-complexity` **63 → 61** (A1.4/A22.12/V35), `BUGS.jsonl` write seams **3 → 1**
   on the executed path (AS-16/A2.13).
5. **What is not fixed is deferred out loud** — AS-17's three public-assets engines, the
   `specs upgrade` automation, `reconcile`'s three edges and four more, each with a named
   intake target. SPEC §1.6 states where the loop still lives, in the reviewer's numbers.

The segment order is a constraint chain, not a preference. **`S1`** creates the shapes every
other segment reads — the record model (FR2), the derived commit map (FR3) and `RELEASE.jsonl`'s
`audited` milestone (FR4), which *defines* the window FR7 and FR14 consume — and holds the only
destructive step (FR6), after both back-fills have read the archive. **`S2`** is procedure and
tests over `S1`'s data; FR9 lands here, not in `S1`, because de-slopping the hooks mid-migration
would change the tree's commit behaviour, and the ratchets (T-050-18A) land here so every test
`S3`/`S4` add must already comply. **`S3`** is last of the executable work: FR16 audits `S1`/`S2`'s
own commits, because an audit written but never run is a green internal gate that has never met a
consumer. **`S4`** is last of all: Part 1 principles must name checks that exist *at the end* of
the release, and the operator's sitting (FR20) needs the final text.

**Then, and only then, the `rc` lane.** A segment never reaches `develop` on its own: the four
close on the branch and the release integrates **once**, whole, as `rc-1`.

Five properties are non-negotiable throughout: **RED before GREEN** on the executed path;
**green at every commit** (`ci preflight`, `backlog doctor`, `specs doctor`, `public doctor`;
no `--no-verify`); **no puxadinho** — every verdict states the bug-surface delta of the feature
it touched, with bug-history evidence, because "tests green" is not a verdict;
**`expand → switch → contract` for every retirement** (SPEC D-F), each step independently
green; and **no number is estimated** — every figure is captured by a shell task (V1–V35).

---

## 2. Layers affected

| Layer | Modules / paths | FRs |
|---|---|---|
| `dadaia_workspace/features/specs` | `doctor.py`, `doctor_common.py`, `doctor_structural.py`, `doctor_closure_audit.py`, `doctor_release.py`, `doctor_governance.py`, `scaffolder.py`, `memory_lint.py`, `catalog.py` | FR1, FR4, FR15 |
| `dadaia_workspace/features/backlog` | `doctor.py` (BL-DUP deleted), `document.py` + `ledger.py` (the in-file `## LEDGER` retires; the 18 `consumed_backlog.json` sidecars relocate and BL-STALE keeps its feed); the histo store instance registered against `core/models/backlog.py` | FR5 |
| `dadaia_workspace/features/bugs` | `service.py` — record model, the **one** governance write seam (AS-16), archive verb, the resolver; `migrate_v5.py` (**new** — the v5 adapter, the legacy-`surface` mapping table and the one-shot runner, deletable with no permanent consumer) | FR2, FR3 |
| `dadaia_workspace/core` | `models/{bugs,findings,backlog}.py` (**`_OPTIONAL_STR_FIELDS` deleted** — the field set is read from the schema, zero module-level field tuples); **`bug_provenance.py` (new — the pure derivation, permanent, consumed by FR8's resolver and FR14's pillar 1)**; `release_events.py` (**new — read-only fold**, called by the hook, the container and the doctor; appends are file-tool writes by agents); `protocols/` gains a record protocol and `GitHistoryReader`; `atomic_write.py` (reused; the record rewrite is **refuse-stale + retry**, one race semantics); `specs_version.py` (the canon the CI gate derives from — `RELEASE_SEMVER_RE` flips to **bare** semver with `v` optional for read-only archive lookups, moving its three production consumers and its identity contract test in the same task); `protocols/bug_store.py` **retires** with `jsonl_bug_store.py` | FR1–FR4, FR13 |
| `dadaia_workspace/infrastructure` | `jsonl_record_store.py` — a **generic** `JsonlRecordStore` keyed by `id`, parse/serialise injected; **one instance per writer that exists**, none without a caller. `git_subprocess.py` gains `log_added_lines(pathspec)` | FR2, FR3, FR5, FR13 |
| `dadaia_workspace/features/spec_context` | `gate_policy.py` — FROZEN: one prefix deleted, `specs/releases/_archive/` added; `_ideas/` stays MUTATING | FR6 |
| `dadaia_workspace/hooks` | `sdd_gate.py` — `_active_field` and its regex retire; the MEMORY phase comes from `core/release_events.py` (hooks never import the container) | FR4 |
| `.github/` + repo root | `scripts/pr-verdict-check.sh` + `workflows/ci.yml` — evidence roots and the release-id pattern derived from the canon by a stdlib-only `python3 -c` import on the bare checkout, over **two** roots (live + per-area archive; `_ideas/` refused), fail-closed, **any derivation failure exits non-zero — never a fallback glob**; `.gitignore` — the proven inversion per area, three orphaned stanzas deleted; `setup.cfg` — the independence contract completed to **24/24** packages with 3 declared ignores (cap 15 → 17); `pyproject.toml` — `max-complexity` **63 → the observed maximum** | FR1, FR18, FR22 |
| `dadaia_workspace/cli/commands` | `bugs.py` (record rendering; **`bugs update` + `bugs archive` if AS-16(i)**), `ci.py` (`pre_commit_check` loses the backlog-doctor gate), `specs.py` (`--recipe` in its **own** render function; **`release open` and `segment open` deleted** — dead once the phase is a fold) | FR1, FR2, FR4, FR9 |
| `dadaia_workspace/public/schemas` | `bugs/bug-record-v1.schema.json` (replaces `bug-event-v1`; three field categories per property; the **restored FR23 triple**, `diff_direction`, the closed `surface` enum; the redaction field set derives from it), `audits/finding-record-v1.schema.json`, `releases/release-event-v1.schema.json` (7 kinds, no `session_id`) | FR2, FR4, FR13 |
| `dadaia_workspace/public/{scripts,scaffold}` | `pre-commit-presence-gate.sh` (advisory-only), `pre-push-ci-gate.sh` (publication boundary only, **keeping its fail-closed runner**); the v6 scaffold tree: per-area `AGENTS.md`, `BUGS.jsonl`, `RELEASE.jsonl`-ready `releases/`, `_ideas/`, `audits/`, `ADRs/`; no `README.md`, no `assets/` | FR1, FR9, FR12, FR13, FR19 |
| `dadaia_workspace/public/skills` | **new** `dd-diagnose/` (+`LINEAGE.md`); `dd-bug-fix` → `dd-bug-resolution`; `dd-release-implement` rebuilt (+`RC-FLOW.md`, `RELEASE-EVENTS.md`, `MEMORY-UPDATE.md`; `CLOSURE-TEMPLATE.md`/`CLOSURE-CHECKS.md` die); `dd-backlog-definition`, `dd-bug-registration`, `dd-release-definition`, `dd-gitflow-default`, `dd-audit-project` (rewritten + 4 siblings, `PILLAR-BUGS.md` carrying the **eight** forensic metrics); `dadaia-test-stewardship/PARAMETERS.md` — the **only** home of each numeric cap | FR7, FR8, FR12, FR14, FR18 |
| `dadaia_workspace/public/{entities,agents}` | `behavior-map.json` (supersedes `rules-skills-map.json`); `project-auditor.md` — allowlist `specs/audits/**` + `specs/bugs/BUGS.jsonl` (governance fields, through the seam), three-pillar mission, skill listed; the four reviewer personas widened to `reviews/**` (+ `verdicts/**` for `security-reviewer`) | FR10, FR13, FR14 |
| `dadaia_workspace/public/data` | `DADAIA.md` **source only** — the projected law is PROTECTED; anchors (comment markup), the D15 posture section, three short sections, the preflight rule, the §3 ADDITIVE row — **within a +500-token ceiling** | FR11 |
| `tests/` | `test_rules_skills_map.py` → `test_behavior_map.py` (9 checks ported, then deleted); new hook-posture, record-immutability, migration-idempotence, principle-inventory tests; **`test_test_suite_ratchets.py` (new, one file)** — private-symbol imports, `Intent:` coverage, SCAFFOLD expiry, one-number-per-parameter, pyramid shape; `test_import_linter_ignore_cap.py` cap **15 → 17**; `EXPECTED_SKILLS`-style hand rosters retired against FR10's glob (deletion-only, measured at task time) | FR2, FR9, FR10, FR10A, FR18, FR22 |
| `specs/**` (this repo's own) | the v6 migration, `BUGS.jsonl`, `RELEASE.jsonl`, `releases_histo.jsonl`, `backlog_histo.jsonl`, `audits/`, `ADRs/`, the memory trio, `constitution.md`, `tests/AGENTS.md`'s cap reference | FR1–FR6, FR13, FR16–FR21 |

**Layer rules hold unchanged:** `features/**` imports neither `cli`, `infrastructure` nor
`hooks`; `core/**` stays stdlib-pure; `lint-imports` green with **no new accepted edge** — FR3
reads git through a `GitHistoryReader` protocol, never `subprocess`. The v5→v6 decoding lives
in one migration-owned adapter (A2.5), so no historical shape leaks into the bugs feature. The
three `reconcile` edges FR18 makes **visible** are declared ignores, not new edges: they exist
at HEAD and are invisible only because their package is unlisted.

---

## 3. Execution order

```
W0   definition commit (_ideas → promotion git mv → backlog purge) → push → definition PR
     → develop [burns no rc] → RELEASE.jsonl `defined` milestone with that PR's sha
     → T-050-03 baselines: V1/V2/V6/V11/V12 + V25 test count per tier, V26/V27 markers,
       V31 mutmut availability, V32 package inventory, V34/V35 ceilings
     → T-050-03A widen 4 reviewer personas to reviews/** (+ verdicts/** for security)

S1   FR1 canon v6 (scaffold + doctor --recipe ONLY; specs upgrade NOT grown) + its two
       boundaries: .gitignore inversion + CI verdict-evidence contract (V20/V21)
     → FR2 record model — one write seam, FR23 triple restored, surface enum,
       _OPTIONAL_STR_FIELDS deleted (+ bugs archive, + bugs update per AS-16)
     → FR3 core/bug_provenance.py + the rewrite over 295 ledger commits (V22/V23)
     → FR4 RELEASE.jsonl + milestone shas + releases_histo back-fill (both layouts)
     → FR5 BACKLOG.md live photo + backlog_histo + the 18 sidecars relocated
     → FR6 [operator] tag (proven from the remote), delete root specs/_archive/ → QA close

S2   FR7 dd-diagnose, lineage phase 0 capped at 20 records → FR8 shapes + one resolver
     → FR9 hooks de-slop (2 blocks out; both orphaned hook tests DELETED)
     → T-050-18A the test-suite ratchets, one contract file (V26–V30)
     → FR10 behavior-map.json + 5 mutation fixtures proven RED on the CI matrix
     → FR10A the public-assets hand rosters retire with the glob
     → FR11 DADAIA.md anchors + D15 posture + 3 short sections, ≤ +500 tokens
     → FR12 the skill surface rides the canon
     → FR4 contract step: ACTIVE.md deleted, 28 consumers + 26 test files repointed,
       specs release open / specs segment open deleted → QA close S2

S3   FR13 audits/ canon + FINDINGS.jsonl → FR14 three pillars, EIGHT forensic metrics
     → FR15 fold FINDINGS.jsonl + retire every CLOSURE.md parser
     → FR16 [project-auditor] the first audit, dry run over this repo → QA close S3

S4   [memory window opens — recorded in RELEASE.jsonl, AS-12] FR17 Part 1 / Part 2 split
     → FR18 inventory: independence contract 20/24 → 24/24 FIRST, then the principles;
       one number per parameter (LARGE cap = 30, one home)
     → FR19 specs/ADRs + the proposed ADRs → FR20 [operator] the acceptance sitting
     → FR21 constitution references principles → QA close S4 [window closes — recorded]

scope complete   FR22 invariants measured (V18/V19/V25/V30/V31/V32/V35) → pillar-3 re-run
                 appended to FINDINGS.jsonl (A16.4) → six-axis code review (thawed tree)
                 → security + QA verdicts, one sha
rc-1             PR feature/0.5.0 → develop, CI green, merge
rc-2 … rc-N      adjustment rounds on this scope only
final rc         memory → closure record → archive → version bump + merge to develop
                 → ship develop → main; publish decision is the operator's (AS-6)
                 → delete feature/0.5.0 + cut feature/{next} from main, same step
```

---

## 4. Approach per segment

### `S1` — the canon and the ledger rewrite

FR1 lands the shape **and its two boundaries** — a canon change that leaves `.gitignore` and
the CI verdict gate behind is how this workspace produced nine gitignore bugs and two
verdict-gate bugs; both are in FR1's write set, and the gate derives its evidence roots from
`core/specs_version.py` instead of a hard-coded glob. What FR1 does **not** do is grow
`specs upgrade`: that function is chain 1 of the forensic (four followers in eight days) at
CC 26, so the release ships `--recipe` only and the renames are copy-paste steps.

FR2's three new fields are the release's measuring instrument, not decoration — the restored
FR23 triple, `diff_direction` and the closed `surface` enum; without them five of the eight
forensic metrics cannot be computed at all. It also collapses `BUGS.jsonl` from three writers
to one seam (AS-16), the single architecture-fidelity regression fold 3 found.

**FR3 is the highest-stakes task.** A per-bug `git log -S` pickaxe is O(bugs × history) and
returns ambiguous matches, so the migration does **one chronological pass** over the 295
non-merge ledger commits reachable across all refs (`main` exposes 75; the 50 `archive/*` tags
carry the other 220), keys every added line by bug id through the migration-owned v5 adapter,
and takes the **first add**. The pass is a pure function in `core/bug_provenance.py` —
permanent, because FR8's resolver and pillar 1 both consume it; only the adapter, the
legacy-`surface` table and the runner sit in the deletable module. Markers are **measured, not
thresholded**; every copied prose value re-runs through the redaction seam; and because the
rename voids the push-scan amnesty the range is scanned **before** the first push, remediated
at the source record, never with `--no-verify`. FR4's back-fill reads **both** archive layouts
before FR6 deletes them; FR5 relocates the 18 sidecars so BL-STALE keeps a data feed. FR6 is
gated on a tag pushed **and proven reachable from the remote**, on the historical `verdicts/**`
being relocated, and on FROZEN being repointed in the same commit.

### `S2` — procedure, deletion, the map, and the ratchets

FR7 relocates procedure rather than authoring it twice, and **bounds it**: phase 0 reads at
most the 20 most recent same-`surface` records, diffing only `exact` shas — an uncapped read is
100–300 records per fix, which is how a procedure becomes a ritual nobody performs. FR9 is the
segment's deletion engine; its two orphaned tests are **deleted**, verdict pre-committed,
because rewriting a test whose premise was deleted produces a change-detector. T-050-18A turns
the marking mandate into one contract file, landing **before** `S3`/`S4` add tests. FR10 extends
the existing enforcer instead of adding a second map, and its five mutation fixtures are proven
RED **on the cross-platform matrix** — the file being replaced is the home of
`citation-mutation-fixtures-never-turn-red-on-windows`, so an unproven RED direction would
re-create the bug being retired. FR10A then deletes the hand rosters the glob makes redundant:
one of public-assets' four recurrence engines, retired as a deletion. FR11 is the only writer
of `DADAIA.md`, every section it adds is a pointer, and its additions carry a **+500-token
ceiling** — an overshoot is closed by cutting text, in that task. `S2` ends with FR4's
**contract step**.

### `S3` and `S4` — the audit canon, then principles and the operator's sitting

FR13/FR14 are authoring; FR15 is a deletion. **FR16 is the acceptance:** the dry run must
rediscover, **by the bug ids SPEC §1.1 pins**, the four documented chains — and report **all
eight forensic metrics** with `baseline → measured`. A pillar-1 run that names the four chains
but leaves the aggregate rate unmeasured passes the letter of A16.2 and fails its purpose;
A14.7 closes that. If it cannot, FR14 is reworked; the acceptance is not lowered.

`S4` opens a **recorded memory window** (AS-12). FR18 **only promotes what already has a check**
and writes no new product check — but it may not promote a principle that is false: the
independence contract is completed to 24/24 packages, its three invisible edges declared with
the cap moving 15 → 17, and only then is "features are mutually independent" proposed. The
LARGE cap collapses to one number in one home in the same segment. FR19 authors the ADR canon;
FR20 is the operator's alone; FR21 deletes the constitution's restatements last.

---

## 5. Technical risks

Full register in SPEC §6/§8/§9; the nine that shape this plan's order and gates:

| # | Risk | Mitigation |
|---|---|---|
| **R-1** | **The migration is irreversible in perception.** Every record is rewritten in one pass; a wrong derivation silently becomes "the history". | Idempotence proven by double execution (V5); counts asserted against ground truth measured in the same run (V4); the derivation is one pure `core/` function unit-tested on an in-memory fixture; the pre-migration ledger stays in git history and in the `archive/*` tags forever. |
| **R-2** | **Migration ambiguity.** Squash-to-main erased per-bug granularity; 39 of 117 resolution commits carry no code. | The granularity markers record coarseness instead of hiding it; pillar 1 consumes only `exact` shas as diff-able lineage; A3.5 forbids inventing `cause`/`caused_by`; unmapped surfaces become `unknown` and are counted. |
| **R-3** | **Concurrent `v0.4.5` work.** | This Draft writes only under `specs/releases/_ideas/0.5.0/`. Promotion is gated on `v0.4.5` being archived; the first task re-derives the commit map and re-reads every write-set path before any edit. |
| **R-4** | **Canon rename churn** — every reference in 22 skills, 9 personas and the law file can go stale. | `expand → switch → contract` per rename; FR10's enforcer with hash tuples lands **in the same segment** as FR12's renames. Case-only renames use an explicit two-step `git mv`. |
| **R-5** | **A governance release grows the always-on budget.** | Every added section is a pointer; V34 gives the additions a **+500-token ceiling** with per-section attribution and anchors counted separately; an overshoot is cut, not renegotiated. |
| **R-6** | **The destructive deletion (FR6)** — the root archive holds every past security verdict and 18 sidecars a live rule reads. | Ordered gates: back-fills complete → sidecars relocated → historical `verdicts/**` relocated and V20 green → tag pushed and proven from a throwaway clone → deletion, one commit, operator present, FROZEN repointed in the same commit. No `archive/*` tag is ever deleted. |
| **R-7** | **A canon change orphans the boundaries that read the canon.** | FR1 owns `.gitignore` **and** the CI evidence contract, derives both from `core/specs_version.py`, and pins them with V20/V21 **before** the archive move. |
| **R-8** | **The suite grows while the operator asked for it to shrink** (fold 3). A governance release writes contract tests by design, and the first Draft disclaimed the goal outright. | Per-FR `Tests: +N / −M` lines; **V25** measures the total from `--collect-only` before and after; **A22.9** gates it at net non-positive; the named deletions (9 `BugEvent` files, 26+4 `ACTIVE`/`CLOSURE` census, the two hook tests, 9 ported enforcer checks, 3 golden fixtures, BL-DUP's tests) each carry a `qa-engineer` verdict with a coverage map. An overshoot closes with a demotion map or an explicit operator acceptance **carrying the number**. |
| **R-9** | **This release exercises public-assets ten times and reduces one of its four recurrence engines** (forensic: 18 bugs, 18 re-bugged). | Stated, not implied: §1.6 quantifies the exposure; **FR10A** retires the roster engine as a deletion; **AS-17** defers the other three by name with their bug ids and one intake target; T-050-34 reports every bug registered on that surface during `S1`–`S4`. |

---

## 6. Validation and review plan

| Boundary | Who | What must be true |
|---|---|---|
| Per task | implementer | RED for the real reason; suite green; preflight green; handoff; marker stays `[-]` |
| End of `S1 … S4` | `qa-engineer` only | every acceptance id of that segment evidenced; the review **committed on the branch**; no push, no PR, no closure |
| `S1` head | `software-architect` | rules on the record model and the boundary adapter (one adapter, no v5 branch in the feature) before FR3 runs |
| `S2` close | `qa-engineer` | the ratchets are pinned at measured values; the five mutation fixtures proved RED on the matrix; the always-on ceiling held |
| `S3` close | `project-auditor` | the FR16 dry-run artifact satisfies A16.2 (four chains, by id) **and A14.7** (eight metrics) |
| `S4` | **operator** | FR20: every inventory ADR carries a terminal operator decision. No agent may flip a status to `accepted` |
| Scope complete | `qa-engineer` + `code-reviewer` + `security-reviewer` | all three `APPROVE` the **same** commit, on a thawed tree; each states the bug-surface delta with evidence |
| `rc-1` · `rc-N ≥ 2` | CI + `security-reviewer`; then `qa-engineer` + delta reviews | `rc-1`: APPROVED verdict covering the PR head sha, CI green, merged. Each later round: the finding named, on this scope, one QA close and one merge |
| Final `rc` | `product-engineer` + trio | memory → closure record → disposition sweep → artifact GC → archive, one commit, in that order, before the ship PR |

**Reviewed before implementation, and folded rather than filed.** Nine reviews across three
folds; **87 amendments, every one with an explicit disposition** in SPEC §9, and the one
refusal states its reason. A re-review of this revision is required before any `Aprovado`.

**Test stewardship — the release does not grow the suite.** The earlier posture ("net-additive
in tests by nature") is **withdrawn**: it disclaimed the operator's explicit goal and left no
metric that would let a reviewer check it either way. In its place: intent and size at birth,
every new test naming the acceptance id it pins, a per-FR `Tests: +N / −M` declaration, and
**V25**'s `--collect-only` measurement gated at **net non-positive** (A22.9) against the 1 859
baseline. No test is deleted, skipped or quarantined except by a `qa-engineer` verdict carrying
the `file:line` map of the coverage that supersedes it — including the two hook tests FR9
breaks (verdict pre-committed **DELETE**, replaced by three cheaper contract fixtures). Marker
discipline stops being aspirational: `Intent:` coverage, private-symbol imports, SCAFFOLD
expiry, one-number-per-parameter and the pyramid shape are pinned in **one** contract file
(V26–V30), and the mutation floor over `core/` is recorded — or recorded as `null` with its
reason, never fabricated (V31). The fixture-repo test stays in `tests/contract/` while
`windows-xdist-workers-crash-on-unit-fast-tier` is open.

---

## 7. Definition of done

- Every acceptance id in SPEC §3 evidenced, or dispositioned by an operator ruling in closure.
- **V1–V35** captured; V4/V5/V6/V22/V23, V16, V18, V20/V21, **V25** and **V32** are unwaivable.
- Six backlog slugs terminal in `backlog_histo.jsonl`; zero bugs closed (AS-4); FR16's findings
  compiled for the PM's intake and materialized by nobody; every ADR operator-decided (FR20).
- FR22 holds, including **A22.6** (zero new blocking exits, exactly two removed), **A22.9**
  (test suite net non-positive), **A22.10** (marker ratchets), **A22.11** (mutation floor
  recorded) and **A22.12** (`max-complexity` ratcheted to the observed maximum).
- The four operator-gated items are decided: **AS-12**, **AS-16**, **AS-17**, **FR20**; every
  deferral carries a named intake target in the closure record.
- Memory in the Part 1 / Part 2 shape, with the LARGE cap in one home; closure record written;
  release archived into `specs/releases/_archive/0.5.0/` **after** the trio review and
  **before** the ship PR; `feature/0.5.0` deleted and the next branch cut, same step.
