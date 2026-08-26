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

---

## 0. Terms, defined once (this release will be read by people new to the repo)

| Term | Meaning here |
|---|---|
| **Arm A / Arm B** | The two lanes every demand takes (`DADAIA.md` §1). Arm A = feature work: backlog → release definition → implementation → audit. Arm B = a bug (the tool broke a contract it already promises), fixed on the spot, never through a release. |
| **rc-N** | "Release candidate N" — a **state of the specs**, never a branch name. Each `rc` burns exactly one `feature/{M.m.p}` → `develop` merge. |
| **Segment (`S1 … S4`)** | A work boundary inside one release, closed by a QA review committed on the branch. It burns no `rc` and opens no PR. |
| **Puxadinho** | Brazilian Portuguese for a lean-to shack bolted onto a house. Here: a fix that adds a branch, a flag, a special case, a second code path, a cross-feature reach-in or a new side effect instead of fixing the structure. Refused by the operator's standing order, whatever the tests say. |
| **Seam** | A place where a test or a replacement can be inserted without editing the module under test. "Fix at the seam" = change one boundary, not N call sites. |
| **FR23** | Requirement 23 of release v0.4.4: the evidence gate on a bug's `resolved` record — the red-loop command, the regression-test seam, and the diff direction. Already law; cited here as history, not re-implemented. |
| **The gate** | One PreToolUse hook (`dadaia_workspace.hooks.pre_gate`) that classifies each file write by path class × presence × phase × mode. It never reads task markers. |
| **Provenance marker** | SPEC D-A: a closed-vocabulary field recording *how* a value was obtained — `registration_granularity` and `resolution_granularity` (`exact\|release-squash\|ledger-only`), one per derived sha, and `lineage_source` (`declared\|text-reference\|null`) on `caused_by`. There is no field called `commit_granularity`. |
| **Pillar 1 / 2 / 3** | The three halves-and-a-half of one audit: bug history, spec compliance, memory/constitution drift. They always run together (ruling D6). |
| **Histo** · **live photo** | A *histo* is an append-only `*_histo.jsonl` beside an area's `_archive/` holding that area's exits (`bugs_histo`, `backlog_histo`, `releases_histo`). A *live photo* is the document that keeps only the current state — `BACKLOG.md` after FR5 carries `## ACTIVE` and nothing else; what left lives in the histo and in git. |
| **Thawed tree** | The working tree before the release directory is `git mv`'d into `_archive/` (which makes it FROZEN). The six-axis review runs on the thawed tree because a reviewer must be able to request a change. |
| **Presence** · **verdict gate** | Presence: the advisory record a MUTATING write leaves naming its session — it never blocks (NO-LOCKS), it surfaces a race. Verdict gate: the required CI job refusing a PR without an APPROVED `security-reviewer` handoff covering the PR head sha, on both edges. |
| **Purge-on-pick** | Removing a picked backlog slug's `## ACTIVE` subsection in the **same commit** that creates the release SPEC — `project-manager`'s step, never `product-engineer`'s. |
| **One-axis law** | The release id **is** the package version: one lineage, no second numbering. "Operator law O5" is the operator ruling that a version may be **minted without being published**. |
| **TREE-5 / TREE-8** | `specs doctor` structural rules. TREE-5 is the existing scoped-`AGENTS.md` hash-projection regime; **TREE-8** is new in FR1 — "nothing beyond canon", WARN-only. |

---

## 1. Strategy

One ordering principle: **build the record, fill it from history, then teach the readers.**

This release is the inverse of `v0.4.5`: that one was a demolition whose danger was deleting a
net; this one **adds a canon**, and a governance release is exactly the shape that grows the
surface it governs. Three constraints hold it:

1. **Nothing here becomes a blocker.** Ruling D15 is an acceptance criterion, not a
   preference: skills instruct, audits measure, hooks and the CLI act only at the publication
   boundary. This release adds zero blocking validations and **removes two** (FR9).
2. **Nothing here is written by hand that git already knows.** Every sha is derived
   (FR3/FR8); every stored sha is a cache of that derivation with one reader.
3. **Nothing here is asserted that no check measures.** A memory principle without a
   `Measured by:` line is not admitted (FR17/FR18), and FR18 is forbidden from writing any new
   check — it may only promote checks that already exist.

The segment order is a constraint chain, not a preference:

- **`S1` first — the canon and the ledger rewrite.** Every other segment reads the shapes it
  creates: `BUGS.jsonl`'s record model (FR2), the derived commit map (FR3), `RELEASE.jsonl`'s
  `audited` milestone (FR4) which *defines* the audit window that `S2`'s FR7 and `S3`'s FR14
  both consume. `S1` also contains the release's only destructive step (FR6), which must run
  after the two back-fills have read the archive and before anything else depends on the tree.
- **`S2` second — lineage, commit shapes, hooks, the map.** These are procedure and tests over
  `S1`'s data. FR9's deletion lands here rather than in `S1` because de-slopping the hooks
  while the migration is running would change the tree's commit behaviour mid-migration.
- **`S3` third — the audit canon, and the dry run that proves it.** FR16 is deliberately last
  of the executable work: it audits `S1` and `S2`'s own commits (SPEC A8.4, A16.3). An audit
  written but never run is a green internal gate that has never met a consumer.
- **`S4` last — memory and ADRs.** Part 1 principles must name checks that exist *at the end*
  of the release, and the operator's ADR sitting (FR20) needs the final text.

**Then, and only then, the `rc` lane.** A segment never reaches `develop` on its own: the four
close on the branch and the release integrates **once**, whole, as `rc-1`.

Five properties are non-negotiable throughout:

1. **RED before GREEN**, on the executed path.
2. **Green at every commit** — `dadaia ci preflight`, `backlog doctor`, `specs doctor`,
   `public doctor`; no `--no-verify`.
3. **No puxadinho.** Every review verdict states the bug-surface delta of the feature it
   touched, with bug-history evidence. "Tests green" is not a verdict.
4. **`expand → switch → contract` for every retirement** (SPEC D-F): add the new path, switch
   every consumer, only then delete the old — each step independently green.
5. **No number is estimated.** Every figure is captured by a shell task (SPEC §6, V1–V19).

---

## 2. Layers affected

| Layer | Modules / paths | FRs |
|---|---|---|
| `dadaia_workspace/features/specs` | `doctor.py`, `doctor_common.py`, `doctor_structural.py`, `doctor_closure_audit.py`, `doctor_release.py`, `doctor_governance.py`, `scaffolder.py`, `memory_lint.py` | FR1, FR4, FR15 |
| `dadaia_workspace/features/backlog` | `doctor.py` (BL-DUP deleted), `document.py` + `ledger.py` (the in-file `## LEDGER` retires; the 18 `consumed_backlog.json` sidecars relocate and BL-STALE keeps its feed) | FR5 |
| `dadaia_workspace/features/bugs` | `service.py` — record model, archive verb, the resolver seam; `migrate_v5.py` (**new**, owns the v5 adapter and is deletable with the migration) | FR2, FR3 |
| `dadaia_workspace/core` | `models/{bugs,findings,backlog}.py`; `release_events.py` (**new** — the stdlib-only `RELEASE.jsonl` fold, called by the hook, the container and the doctor); `protocols/` gains a record protocol and `GitHistoryReader`; `atomic_write.py` (reused, not re-implemented; the record rewrite is **refuse-stale + retry**, one race semantics); `specs_version.py` (the canon the CI gate derives from — `RELEASE_SEMVER_RE` flips to **bare** semver with the `v` prefix optional for read-only archive lookups, moving its three production consumers `specs/scaffolder.py`, `specs/doctor_release.py` ×2, `spec_artifacts/new_artifacts.py` and its identity contract test in the same task); `protocols/bug_store.py` **retires** with `jsonl_bug_store.py` | FR1, FR2, FR3, FR4, FR13 |
| `dadaia_workspace/infrastructure` | `jsonl_record_store.py` — a **generic** `JsonlRecordStore` keyed by `id`, parse/serialise injected; one instance per feature model, no module knowing two shapes. `git_subprocess.py` gains `log_added_lines(pathspec)` | FR2, FR3, FR5, FR13 |
| `dadaia_workspace/features/spec_context` | `gate_policy.py` — FROZEN: one prefix deleted, `specs/releases/_archive/` added; `_ideas/` stays MUTATING | FR6 |
| `dadaia_workspace/hooks` | `sdd_gate.py` — `_active_field` and its regex retire; the MEMORY phase comes from `core/release_events.py` (hooks never import the container) | FR4 |
| `.github/` | `scripts/pr-verdict-check.sh` + `workflows/ci.yml` — evidence roots and the release-id pattern derived from the canon by a stdlib-only `python3 -c` import on the bare checkout, over **two** roots (live + per-area archive; `_ideas/` refused); still fail-closed, and **any derivation failure exits non-zero — never a fallback glob** | FR1 |
| repo root | `.gitignore` — the proven inversion applied to every new area; three orphaned stanzas deleted | FR1 |
| `dadaia_workspace/cli/commands` | `bugs.py` (record rendering), `ci.py` (`pre_commit_check` loses the backlog-doctor gate), `specs.py` (`--recipe`) | FR1, FR2, FR9 |
| `dadaia_workspace/public/schemas` | `bugs/bug-record-v1.schema.json` (replaces `bug-event-v1`; three field categories per property; the redaction field set derives from it), `audits/finding-record-v1.schema.json`, `releases/release-event-v1.schema.json` (7 kinds, no `session_id`) | FR2, FR4, FR13 |
| `dadaia_workspace/public/scripts` | `pre-commit-presence-gate.sh` (advisory-only), `pre-push-ci-gate.sh` (publication boundary only) | FR9 |
| `dadaia_workspace/public/scaffold` | the v6 tree: per-area `AGENTS.md`, `BUGS.jsonl`, `RELEASE.jsonl`-ready `releases/`, `_ideas/`, `audits/`, `ADRs/`; no `README.md`, no `assets/` | FR1, FR12, FR13, FR19 |
| `dadaia_workspace/public/skills` | **new** `dd-diagnose/` (+`LINEAGE.md`); `dd-bug-fix` → `dd-bug-resolution`; `dd-release-implement` rebuilt (+`RC-FLOW.md`, `RELEASE-EVENTS.md`, `MEMORY-UPDATE.md`; `CLOSURE-TEMPLATE.md`/`CLOSURE-CHECKS.md` die); `dd-backlog-definition`, `dd-bug-registration`, `dd-release-definition`, `dd-gitflow-default`, `dd-audit-project` (rewritten + 4 siblings) | FR7, FR8, FR12, FR14 |
| `dadaia_workspace/public/entities` | `behavior-map.json` (supersedes `rules-skills-map.json`) | FR10 |
| `dadaia_workspace/public/agents` | `project-auditor.md` — allowlist `specs/audits/**`, three-pillar mission, skill listed | FR13, FR14 |
| `dadaia_workspace/public/data` | `DADAIA.md` **source only** — the projected law is PROTECTED; anchors, the D15 posture section, three short sections, the preflight rule | FR11 |
| `tests/contract` | extends `test_rules_skills_map.py` → `test_behavior_map.py`; new hook-posture, record-immutability, migration-idempotence, principle-inventory tests | FR2, FR9, FR10, FR18 |
| `specs/**` (this repo's own) | the v6 migration, `BUGS.jsonl`, `RELEASE.jsonl`, `releases_histo.jsonl`, `backlog_histo.jsonl`, `audits/`, `ADRs/`, the memory trio, `constitution.md` | FR1–FR6, FR13, FR16–FR21 |

**Layer rules hold unchanged:** `features/**` imports neither `cli`, `infrastructure` nor
`hooks`; `core/**` stays stdlib-pure; `lint-imports` green with **no new accepted edge** — FR3
reads git through a `GitHistoryReader` protocol, never `subprocess`. The v5→v6 decoding lives
in one migration-owned adapter (A2.5), so no historical shape leaks into the bugs feature.

---

## 3. Execution order

```
W0   definition commit (SPEC+PLAN+TASKS at _ideas → promotion git mv → backlog purge)
       → push feature/0.5.0 → definition PR → develop   [milestone (a), burns no rc]
       → RELEASE.jsonl `defined` milestone appended with that PR's sha
       → T-050-03A [ai-engineer] widen the four reviewer personas to
         specs/releases/**/reviews/** — S1's very first task needs it

S1   FR1 canon v6 (scaffold + doctor + this repo's migration)
       → FR1 boundaries: .gitignore inversion + the CI verdict-evidence contract (V20/V21)
       → FR2 BUGS.jsonl record model (expand → switch → contract) + bugs archive
       → FR3 historical rewrite: one pass over 295 ledger commits, all refs (V22/V23)
       → FR4 RELEASE.jsonl + milestone shas + releases_histo back-fill (both layouts)
       → FR5 BACKLOG.md live photo + backlog_histo + the 18 sidecars relocated
       → FR6 [operator] tag (proven from the remote), then delete root specs/_archive/
       → QA close S1 (committed on branch)

S2   FR7 dd-diagnose with lineage as phase 0
       → FR8 commit shapes + the one resolver seam
       → FR9 hooks de-slop (the release's clearest deletion)
       → FR10 behavior-map.json + contract tests (RED in five directions, 9 ported)
       → FR11 DADAIA.md: anchors + D15 posture + three short sections + the §3 row
       → FR12 the skill surface rides the canon
       → FR4 contract step: ACTIVE.md deleted, every one of its 28 consumers repointed
       → QA close S2

S3   FR13 audits/ canon + FINDINGS.jsonl → FR14 dd-audit-project three pillars
       → FR15 specs doctor folds FINDINGS.jsonl + retires every CLOSURE.md parser
       → FR16 [project-auditor] the first audit, dry run over this repo
       → QA close S3

S4   [memory window opens — recorded in RELEASE.jsonl, AS-12]
     FR17 memory Part 1 / Part 2 split → FR18 the principle inventory
       → FR19 specs/ADRs canon + the proposed ADRs
       → FR20 [operator] the ADR acceptance sitting
       → FR21 constitution references principles
       → QA close S4  [memory window closes — recorded]

scope complete   FR22 invariants measured → six-axis code review (thawed tree)
                 → security review + QA release verdict (all three on one sha)
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
verdict-gate bugs; both are in FR1's write set, and the gate now derives its evidence roots
from `core/specs_version.py` instead of a hard-coded glob, so the *next* canon move cannot
break it. FR2 lands the model; **FR3 is the release's highest-stakes task**. Its approach is
fixed by measurement: a per-bug `git log -S` pickaxe is O(bugs × history) and returns
ambiguous multi-commit matches, so the migration does **one chronological pass** over the 295
non-merge ledger commits reachable across all refs (`main` exposes 75; the 50 `archive/*` tags
carry the other 220), keys every added line by bug id through the migration-owned v5 adapter,
and takes the **first add** — which a later ship or squash commit re-adding the same line can
never outrank.

The output is data plus a marker, and the markers are **measured, not thresholded**: §1.2's
79 and 155 count different units than the structural definitions the algorithm computes, so
the migration reports the distribution and only the unit-matched `≥` counts gate. Every copied
prose value is re-run through the schema-derived redaction seam, and because the rename voids
the push-scan amnesty the range is scanned **before** the first push, remediated at the source
record — never with `--no-verify`. Idempotence is proven by executing twice and byte-comparing.

FR4's back-fill reads **both** archive layouts before FR6 deletes them; FR5 relocates the 18
`consumed_backlog.json` sidecars so BL-STALE keeps a data feed instead of going quiet. FR6 is
gated on a tag pushed **and proven reachable from the remote**, on the historical `verdicts/**`
being relocated, and on the FROZEN set being repointed in the same commit. Only then is
anything removed, and only with the operator present.

### `S2` — procedure, deletion, and the map

FR7 relocates procedure rather than authoring it twice: what `dd-bug-fix` states as an outcome
becomes a phase with a *Done when*, and `dd-bug-resolution` gets shorter — proven by a coverage
table, not by a line count alone. FR9 is the segment's deletion engine and the one place the
diff must be unambiguously negative: two blocking mechanisms and a fail-closed runner leave,
and the contract test asserts the **executed path** (pre-commit exits 0 on a staged set the
backlog doctor rejects), never the script's text.

FR10 extends the existing enforcer instead of adding a second map — a second map would be the
exact puxadinho this release is built to make visible — each of its five RED conditions gets a
mutation fixture, **all nine existing checks are proven ported before the old file dies**, and
its discovery **globs the generators** rather than trusting a hand list (the first Draft's own
hand list already missed three shipped `AGENTS.md` sources). FR11 is the only writer of
`DADAIA.md` (SPEC D-B): every section it adds is a pointer, its anchors are comment markup
rather than headings, and its always-on token delta is measured with per-section attribution,
because a governance release is precisely the shape that quietly spends the token budget the
previous two releases fought for. `S2` ends with FR4's **contract step**: only once the
personas, skills and law file have been repointed is `ACTIVE.md` deleted — deleting it in `S1`
would leave the always-on law naming a missing file for a whole segment.

### `S3` — the audit canon, proven on this repository

FR13 and FR14 are authoring; FR15 is a deletion (regex-over-prose out, JSONL fold in, and
every surviving `CLOSURE.md` parser retired with its subject). **FR16 is the acceptance:** the
dry run must rediscover, **by the bug ids SPEC §1.1 pins**, the gitignore class (nine
instances), the certify chain, the frozen-clock chain and the bug-event ledger family — a
finding that claims a chain without naming its ids does not count. If it cannot, FR14 is
reworked; the acceptance is not lowered. It also grades this release's own commits against
FR8's shapes.

### `S4` — principles, and the operator's sitting

The segment opens a **recorded memory window** (AS-12), never a phase toggled around a task.
FR17 restructures; FR18 **only promotes what already has a check** and may write none — the
constraint that stops an inventory becoming a second enforcement layer. The import-linter
count is read from `setup.cfg` at implementation time (nine at HEAD), and a contract test
makes a tenth contract without a principle go RED. FR19 authors the ADR canon; FR20 is the
operator's alone; FR21 deletes the constitution's restatements last, against final ids.

---

## 5. Technical risks

Full register in SPEC §6/§8/§9; the seven that shape this plan's order and gates:

| # | Risk | Mitigation |
|---|---|---|
| **R-1** | **The migration is irreversible in perception.** 490 records are rewritten in one pass; a wrong derivation silently becomes "the history". | Idempotence proven by double execution (V5); counts asserted against measured ground truth (V4); the derivation is one pure function over git output and is unit-tested on a fixture repo; the pre-migration ledger stays in git history and in the `archive/*` tags forever. |
| **R-2** | **Migration ambiguity.** Squash-to-main erased per-bug granularity for 155 resolutions; 39 of 117 resolution commits carry no code. | The granularity marker (SPEC D-A) records coarseness instead of hiding it; pillar 1 consumes only `exact` shas as diff-able lineage; A3.5 forbids inventing `cause`/`caused_by`. |
| **R-3** | **Concurrent `v0.4.5` work.** `v0.4.5` is live and touches `specs/bugs/bugs.jsonl`, `BACKLOG.md`, the personas and `DADAIA.md`. | This Draft writes only under `specs/releases/_ideas/0.5.0/`. Promotion is gated on `v0.4.5` being archived; the first task at promotion re-derives the commit map (its counts will have grown) and re-reads every write-set path before any edit. |
| **R-4** | **Canon rename churn.** `bugs.jsonl` → `BUGS.jsonl`, the memory trio's case change, `dd-bug-fix` → `dd-bug-resolution`, `ACTIVE.md`/`CLOSURE.md`/`CLOSURE-TEMPLATE.md` retiring — every reference in 21 skills, 9 personas and the law file can go stale. | `expand → switch → contract` per rename; FR10's enforcer with hash tuples is landed **in the same segment** as FR12's renames, so a stale reference is RED rather than discovered by a human three releases later (the class has already fired twice). Case-only renames use an explicit two-step `git mv` so case-insensitive filesystems do not silently no-op. |
| **R-5** | **A governance release grows the always-on budget.** FR11 adds sections to the law file that every session loads. | Every added section is a pointer; V12 measures the delta with per-section attribution; an increase is reported, never averaged into a total. |
| **R-6** | **The destructive deletion (FR6).** Root `specs/_archive/` holds every archived release's CLOSURE evidence **and every past security verdict**, plus 18 `consumed_backlog.json` sidecars a live doctor rule reads. | Ordered gates: back-fills complete (both layouts) → sidecars relocated → historical `verdicts/**` relocated and the CI gate proven against them (V20) → tag created, pushed and proven reachable **from a throwaway clone** → deletion, one commit, operator present, FROZEN repointed in the same commit. No `archive/*` tag is ever deleted. |
| **R-7** | **A canon change orphans the boundaries that read the canon.** The gitignore class fired nine times and the verdict gate twice on exactly this shape: the tree moved, and a hard-coded path elsewhere did not. | FR1 owns `.gitignore` **and** the CI evidence contract in its own write set, derives both from `core/specs_version.py`, and pins them with contract validations (V20, V21) that run **before** the archive move rather than at ship. |

---

## 6. Validation and review plan

| Boundary | Who | What must be true |
|---|---|---|
| Per task | implementer | RED for the real reason; suite green; preflight green; handoff; marker stays `[-]` |
| End of `S1 … S4` | `qa-engineer` only | every acceptance id of that segment evidenced; the review **committed on the branch**; no push, no PR, no closure |
| `S1` head | `software-architect` | rules on the record model and the boundary adapter (one adapter, no v5 branch in the feature) before FR3 runs |
| `S3` close | `project-auditor` | the FR16 dry-run artifact exists and satisfies A16.2 — the four loop chains, named with evidence |
| `S4` | **operator** | FR20: every inventory ADR carries a terminal operator decision. No agent may flip a status to `accepted` |
| Scope complete | `qa-engineer` + `code-reviewer` + `security-reviewer` | all three `APPROVE` the **same** commit, on a thawed tree; each states the bug-surface delta with evidence |
| `rc-1` | CI + `security-reviewer` | APPROVED verdict covering the PR head sha; CI green; merged |
| `rc-N ≥ 2` | `qa-engineer` + delta reviews | the finding is named, on this scope; one QA close and one merge per round |
| Final `rc` | `product-engineer` + trio | memory → closure record → disposition sweep → artifact GC → archive, one commit, in that order, before the ship PR |

**This trio was reviewed before implementation, by more than the usual fleet — and the reviews
are folded, not filed.** `software-architect` (REWORK), `security-reviewer` (REJECTED),
`qa-engineer` (REWORK), `ai-engineer` (REWORK) and `code-reviewer` (REWORK) each returned an
amendment list; all 55 amendments carry an explicit disposition in **SPEC §9**, and the one
refusal states its reason. A re-review of this revision is required before any `Aprovado`.
The external audience — human and other-vendor — is why §0 defines every term at first use and
why every claim in SPEC §1 carries its measurement and its capture path: a reader who has never
opened this repository must be able to check the numbers.

**Test stewardship.** Intent and size at birth (`dadaia-test-stewardship`); the release is
net-additive in tests by nature (contract tests are the mechanism D15 allows) and every new
test names the acceptance id it pins. No test is deleted, skipped or quarantined except by a
`qa-engineer` verdict with evidence — including the two hook tests FR9's deletion breaks, and
the new fixture-repo test, which is placed in `tests/contract/` rather than the crash-prone
`unit-fast` tier while `windows-xdist-workers-crash-on-unit-fast-tier` stays open.

---

## 7. Definition of done

- Every acceptance id in SPEC §3 evidenced, or dispositioned by an operator ruling in closure.
- **V1–V24** captured; V4/V5/V6/V22/V23, V16, V18 and V20/V21 may not be waived.
- Six backlog slugs terminal in `backlog_histo.jsonl`; zero bugs closed (AS-4); FR16's findings
  compiled for the PM's intake and materialized by nobody; every ADR operator-decided (FR20).
- FR22 holds, including **A22.6: zero new blocking exits, exactly two removed**.
- Memory in the Part 1 / Part 2 shape; closure record written; release archived into
  `specs/releases/_archive/0.5.0/` **after** the trio review and **before** the ship PR.
- `feature/0.5.0` deleted and the next feature branch cut from `main` in the same step.
