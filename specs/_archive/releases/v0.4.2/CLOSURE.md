# Closure: Release — v0.4.2 (residual-convergence)

> **Status:** Aprovado
> **Release ID:** v0.4.2
> **Owner:** product-engineer
> **Closed:** 2026-08-16
> **Branch:** `feature/0.4.2` (cut from `develop` at `36412845`)
> **Range:** `741f2294..078925e8` (definition merge → memory window)

## Summary

The operator asked for one thing: *"na próxima rodada não quero ver essa desgraça de erros e
bugs residuais."* Three consecutive releases had each shipped clean and each produced a longer
residual list than the one before. This release read those fourteen residuals as **three
root-cause classes** and fixed each at the class, not at the instance.

**Class 1 — a fact with more than one writer.** The backlog grammar now has exactly one owner:
the writer moved into the feature that owns the parser, takes its insertion point from the
parser's own fence-aware structure, deletes three private regexes, and re-parses its own output
before reporting success. The push gate's masker consumes the detector's own compiled matchers,
so under-masking is impossible by construction rather than by convention. `token_estimate`
stopped being stored in 29 atoms and became a computed value — the drift check that existed only
because the value was hand-maintained was deleted with it. Four skill and persona surfaces
stopped describing a backlog shape retired two releases ago.

**Class 2 — a process order that froze the artifact before it was reviewed.** Three prior
releases archived the release directory *before* the pre-PR six-axis review ran, so the
reviewer's first reader hit a FROZEN closure and every finding cost a reopen — three paid
reopens. This release makes review-before-archive canon **and is its first executor**: the code
review ran at T-042-18, on a thawed tree, before any `git mv`. It returned REQUEST-CHANGES with
two HIGH findings — one of them a genuine push-blocking regression this release had introduced,
found before it reached `develop`. Both were fixed in place, re-reviewed, and APPROVED. **Zero
reopens.** The canon paid for itself on its first execution, against a three-for-three prior
failure rate.

**Class 3 — a review pipeline that manufactured intake volume.** Reviews still record
everything; the routing now distinguishes record-only observations (which terminate in this
document) from actionable defects (which reach the operator). This closure is the proof: **26
observations recorded across the release, 15 record-only, 11 actionable — and exactly one item
reaches the operator's intake desk.** That is the volume reduction the operator asked for,
achieved by fixing the routing rather than by suppressing findings.

Riding with the classes: an amnesty that leaked across paths through a shared blob now fails
closed range-wide; three silent scan-path degradations became typed or counted; the self-scan
sentinel now sees archive-authored blobs; the privacy baseline covers all three declared-support
platforms; the parser stopped being quadratic; a dead CLI verb and two templates are gone; the
CHANGELOG states one version axis; and SPEC-DOC-031 went from nine warnings to zero by keying on
consumption evidence instead of substring conversation.

**Measured honestly (per the code review's own note, RO-14):** production Python is **net +169**,
not net-negative. R5's promised deletions are all real — `new_artifacts.py` −136,
`scaffolder.py` −132, `cli/commands/specs.py` −112, **−380 combined** — but they are outweighed
by `document.py` +240 (of which ~136 is the FR1 relocation), `git_objects.py` +96 and
`doctor_governance.py` +65. Netting the relocation out, genuinely new production logic is roughly
+305 against −380 deleted. Public assets are net −63. The release deletes what it promised to
delete; it does not claim a net-negative line count.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-042-01 | Definition content committed; phase → IMPLEMENTATION; 13 ACTIVE subsections purged on pick | `01a938dd` |
| T-042-02 | Milestone (a): V12 captured, merge, diff security review APPROVED, `develop` pushed, hooks armed | `741f2294` (merge) · `fc548e46` |
| T-042-03 | FR12 — the revoked hotfix-release surface deleted (verb, scaffolder, 2 templates, golden regenerated) | `782883d3` |
| T-042-04 | FR1 — one backlog grammar; writer moved, write-then-verify, three private regexes deleted | `7d6e926e` |
| T-042-05 | FR11 — bisect fence filter + `CSafeLoader` selection | `72b12894` |
| T-042-06 | FR14 — SPEC-DOC-031 keys on consumption-asserting evidence | `b449085f` |
| T-042-07 | FR2 code half — catalog computes `token_estimate`; drift check retired | `4cd582b8` |
| T-042-08 | FR4 — masker consumes the detector's matchers; refusals carry no raw path | `d1d5c902` |
| T-042-09 | FR7 — a multi-path blob receives no amnesty (fail-closed) | `49bb84bb` |
| T-042-10 | FR8 — a scan-path degradation is typed or counted, never silent | `ebda21ef` |
| T-042-11 | FR10 — privacy baseline v5 covers macOS and Windows home paths | `d7f8c273` |
| T-042-12 | FR9 — the self-scan sentinel sees archive-authored blobs | `9edc6aaa` |
| T-042-13 | FR3 code half — YAML error formatter exported; DEAD markers repointed | `baccd820` |
| T-042-14 | FR3 skills + FR5 — shipped sweep + review-before-archive canon stated | `009692f4` (+ QA-1 fix `978bb850`) |
| T-042-15 | FR6 — record-only terminates in CLOSURE; only defects reach intake | `6f6cb543` |
| T-042-16 | FR13 — CHANGELOG version-axis preamble, V13 measured | `8a59e9ff` (markers normalized `44ec8efb`) |
| T-042-17 | `qa-engineer` alpha-1 review — REQUEST_CHANGES → **APPROVED** | `a42c4514` → `978bb850`/`34e71ca7` → `c8847288` |
| T-042-18 | `code-reviewer` six-axis pre-PR review **before archive** — REQUEST-CHANGES → **APPROVE** | `934e6cf3` → `7e2ac0b4`/`759eb598`/`85ac7ab7` → `e8808bf5` |
| T-042-19 | Memory window — five atoms, diagram, `token_estimate` strip (29 atoms), schema, catalog | `078925e8` |
| T-042-20 | This closure: CLOSURE.md, disposition sweep, CR-5/CR-6, archive, version confirmation | this commit (reservation `27200b8c`) |
| T-042-21 | **[ ] OPEN** — milestone (b) ship: merge, diff security review, push, PR → `main`, CI green | rides the dispatcher's milestone-(b) evidence |

**On T-042-21.** It is `[ ]` in `TASKS.md` and stays `[ ]` at closure — mirrored honestly. Under
the canon this release ships, that open marker is **not** a review gap: the six-axis review is
already `[x]` and APPROVED (T-042-18, on a thawed tree), and `qa-engineer` closed `alpha-1`
(T-042-17). What remains is mechanical ship — merge to `develop`, the diff-based security review
of `origin/develop..develop`, the push, the PR to `main` and CI. There is no
"`[ ]` by design" review row in this release's TASKS, unlike the flat-release shape
`flat-release-ship-task-evidence` was raised against; the ship row carries the dispatcher's
milestone-(b) evidence and closes when CI is green.

## Validations

| id | Description | Command | Evidence |
|----|-------------|---------|----------|
| V1 | Full preflight green at every gate boundary | `dadaia ci preflight` | **5/5 PASS** (ruff format, ruff check, mypy --strict, lint-imports, pytest) at the alpha-1 tree, at `c8847288` (QA + CR round 1) and at `85ac7ab7` (CR round 2) |
| V1a | Suite — **alpha-1 tree**, full selection | `python -m pytest -q -p no:cacheprovider -m 'not quarantine' -n auto` | `2298 passed, 3 skipped` (3 skips environment-gated: 2× Windows-only, 1× no non-loopback IPv4) — QA's own re-run at `a42c4514`/`c8847288` |
| V1b | Suite — **CR remediation tip**, full selection | same | `2302 passed, 3 skipped` at `85ac7ab7` (+4 net: CR-0/CR-1/CR-2/CR-3 regression tests) |
| V1c | Suite — **memory commit**, non-e2e selection | same, non-e2e selection | `2247 passed, 2 skipped, 0 failed` at `078925e8` — a narrower selection than V1a/V1b, not a regression |
| V2 | Backlog document validity | `dadaia backlog doctor --specs-dir specs --source-root .` | `backlog doctor: clean.` at QA (`c8847288`) and CR round 2 (`85ac7ab7`) |
| V3 | Specs governance + SPEC-DOC-031 before/after | `dadaia specs doctor` | `0 error(s), 5 warning(s)` — identical 5 pre-existing at every run. **SPEC-DOC-031: 9 → 0** (capture at `b449085f`; reconfirmed `0` independently by QA and by CR at `c8847288` and `85ac7ab7`) |
| V4 | Projection integrity | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | all `[ok]`, including `[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution`; verified at `009692f4`/`6f6cb543`, re-verified after `978bb850` and at `85ac7ab7` |
| V5 | Import boundaries, no new edge (A1.6) | `lint-imports --config setup.cfg --no-cache` + `git diff setup.cfg` | 9/9 contracts kept, 0 broken; `setup.cfg` **zero-diff** over the full range `741f2294..85ac7ab7` (CR-verified by diff) |
| V6 | FR12 zero-hit grep (standing exclusions) | `rg -n 'hotfix_app\|hotfix_open\|scaffold_hotfix_release\|_HOTFIX_TASKS_STUB\|release_hotfix\.md\.j2\|closure_hotfix\.md\.j2\|Hotfixes pendentes'` | 2 hits at `a42c4514` (QA-1) → **0 hits** at `978bb850`, re-verified under both the standing scope and a narrower `dadaia_workspace/ tests/` scope |
| V7 | FR1 zero-hit grep for private grammar regexes | `rg -n '\^###\|\^##\[ \\t\]\+LEDGER' dadaia_workspace` | zero hits outside `features/backlog/document.py`, which **is** the owner |
| V8 | FR2 zero-hit after the closure half (A2.3) | `rg -n 'token_estimate' specs/memory dadaia_workspace/public/schemas` | zero hits at `078925e8` — 29 atoms stripped, key removed from the schema's `properties`, `catalog.json` regenerated; `specs doctor` memory errors `0` |
| V9 | Self-scan sentinel incl. archive-authored blobs | `pytest tests/integration/test_repo_self_scan.py` | 5 passed (A9.1 planted-authored fails, A9.2 `git mv` stays excluded, A9.3 missing `HEAD^` degrades); `_TESTS_SCOPE_BASELINE` grew by **exactly 2 rows**, both FR10's, diff-verified |
| V10 | Parser budget | `pytest -k backlog_document_budget` | 1 passed — 565-subsection ~140 KB synthetic document, measured **0.14 s** against a 1.0 s ceiling |
| V11 | CLI redaction unchanged (A4.3) | `pytest tests/**/test_*redact*` + `git diff dadaia_workspace/core/redaction.py` | 15 passed unmodified; `core/redaction.py` **and** `cli/redact.py` zero-diff over the full range, re-checked after the CR remediation |
| V12 | Open bugs (OD-3 / pick-time claim) | `dadaia bugs status` | `[ok] 0 open bug(s)` at T-042-02 (confirming SPEC §7's zero-open-bugs pick claim) and again at `85ac7ab7` after `gitignore-code-review-artifact-untrackable` was resolved. **1 open at closure** — `memory-token-estimate-normalizer-dead-code` (LOW), registered `0be80513` after the memory commit; see `## Dispositions` |
| V13 | Published version lineage (OD-3, A13.1) | package-index listing for `dadaia-workspace` | **13 versions published, `0.1.0`–`0.4.1`**; `0.4.2` unpublished at measurement. Captured 2026-08-16T17:32:59Z → `.dadaia/tmp/software-engineer/20260816/t-042-16-pypi-versions.json` |
| V14 | Push-gate behaviour end to end | the real pre-push gate | Milestone (a): gate exit 0, `develop` pushed, APPROVED handoff `2026-08-16T155627Z-security-reviewer-v0.4.2-definition-push`. Milestone (b) **pending T-042-21** |
| V15 | `qa-engineer` alpha-1 verdict | — | **APPROVED**, 90/90 acceptance ids · `specs/releases/v0.4.2/ALPHA-1-QA.md` · handoffs `…180500Z-qa-engineer-v0.4.2-alpha1` (REQUEST_CHANGES) and `…180823Z-qa-engineer-v0.4.2-alpha1-reverify` (APPROVED) |
| V16 | `code-reviewer` pre-PR six-axis verdict (before archive) | — | **APPROVE** on `85ac7ab7` · `specs/releases/v0.4.2/PRE-PR-REVIEW.md` · handoffs `…191500Z-code-reviewer-v0.4.2-prearchive` (REQUEST-CHANGES) and `…193000Z-code-reviewer-v0.4.2-prearchive-rereview` (APPROVED) |

## Drifts

### t-042-09-rev-list-to-ls-tree-correction

**Description:** PLAN §4 framed FR7 as reading multi-path reachability off
`_rev_list_candidates` — "`_rev_list_candidates` already yields every `(sha, path)` pair". That
framing was empirically false: `git rev-list --objects` performs its own object-visit dedup and
reports only the first tree entry per object, so a `_multi_path_shas` built on it can **never**
detect a multi-path blob. The plan's primitive could not answer the plan's question.

**Resolution:** root-caused with three throwaway git repositories before any code changed, then
the detection primitive was switched to `git ls-tree -r --full-tree`, which enumerates every
tree *entry* rather than every distinct object. Disclosed in the commit message in its own
words, independently re-derived by QA from the diff rather than taken on trust, and later
widened again by CR-3 (below). Trade-off: one bounded extra subprocess, guarded by an empty-set
early return.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the multi-path amnesty semantics
are stated as shipped, so the atom's "a new path still refuses" sentence is true again.

### t-042-12-sentinel-self-catch

**Description:** The FR9 positive fixture, written inline, would have been **invisible to the
sentinel it was testing** — masked by an earlier hit in the same object under the
one-hit-per-object refusal shape — and would simultaneously have forced a
`_TESTS_SCOPE_BASELINE` row that A9.4 explicitly forbids this FR to add. The test module caught
itself: `test_no_hit_outside_the_shrink_only_baseline` tripped on this very file.

**Resolution:** fixed at the root rather than by adding a baseline row — the literal is composed
at runtime (`_archive_fixture_literal()`) so the module's own tracked source never contains the
substring contiguously. A9.4 then held by construction: FR9 added **zero** baseline rows, diff-
verified by QA and again by the code reviewer.

**Memory updates:** none — the fix is a test-authoring technique, not product truth.

### qa-request-changes-cycle-alpha-1

**Description:** The `alpha-1` QA review returned **REQUEST_CHANGES** at `a42c4514`. 14 of 15
FRs and 88 of 90 acceptance ids held, but **A12.1 failed on the literal tree**:
`public/agents/product-engineer.md` still named the two retired template filenames inside its
"Hotfix release lifecycle — REVOKED" historical section, and FR12's acceptance text carries no
historical-comment carve-out (unlike A3.1's explicit one). A second, non-blocking LOW (QA-2)
noted four new tests referencing their acceptance ids in prose without the canonical `Intent:`
tag.

**Resolution:** QA-1 remediated by `ai-engineer` at `978bb850` — the revocation fact preserved,
the literal retired filenames dropped, re-projected and byte-verified. QA-2 remediated by
`software-engineer` at `34e71ca7` — all four tests now carry
`Intent: CONTRACT — v0.4.2 <A-id>` in the release's own precedent shape. Both independently
re-verified in a targeted light pass; verdict flipped to **APPROVED** at `c8847288` with the
original REQUEST_CHANGES evidence preserved verbatim as the historical record.

**Memory updates:** none.

### code-review-request-changes-cycle-the-r3-dogfood

**Description:** The six-axis pre-PR review ran **before** the archive move — the ordering FR5
makes canon and this release is the first to execute — and returned **REQUEST-CHANGES** at
`934e6cf3`: 2 HIGH, 2 MEDIUM, 2 LOW actionable, 9 record-only.

- **CR-0 (HIGH)** — the artifact the new canon requires was **gitignored**: `.gitignore`'s
  `/specs/releases/*/*` deny rule with a literal allowlist denied both candidate filenames, so
  the review had to be committed with `git add -f`. A recurrence of an already-registered and
  already-"fixed" class (`gitignore-alpha-qa-review-untrackable`, fixed by adding one literal).
- **CR-1 (HIGH)** — a **regression this release introduced**: FR8's row-shape narrowing
  classified `git cat-file --batch-check`'s missing row by field count, so a new path containing
  two or more spaces raised a typed error, which the gate converts into a **blocked push**
  explaining itself as internal git inconsistency on a healthy repository. Reproduced end to end.
- **CR-2 (MEDIUM)** — `windows-users-path`'s trailing lookahead fired only before a backslash or
  end-of-line, so the commonest leak shape (an inline path in prose) never fired; the fixture
  had been written on the one form that worked.
- **CR-3 (MEDIUM)** — FR7's multi-path scope was the tip tree where SPEC/A7.1 say the pushed
  range; load-bearing, because T-042-19 was about to write the semantics into memory.
- **CR-4 (LOW)** — the artifact filename did not match the one TASKS declares.
- **CR-5 (LOW)** — BACKLOG.md #24's partial-pick note cited an archive path that did not yet
  exist.

**Resolution:** all four blocking/MEDIUM findings fixed **on the thawed tree** across
`7e2ac0b4`, `759eb598`, `85ac7ab7` — and fixed at the class, not the instance: CR-0 added the
`.gitignore` negation *plus a contract test* pinning the artifact's visibility (the previous
instance had a comment and no test, which is exactly why the class reappeared); CR-1 and CR-3
each shipped their reproduction as a permanent regression test; CR-2 widened the lookahead to
parity with its two peers *and* gave the fixture the prose form so the gap is provable. CR-4 was
a `git mv` with the review content diff-verified at 98% similarity — another agent's review text
left intact. Re-review returned **APPROVE** on `85ac7ab7` at `e8808bf5`. CR-5 was accepted as
correctly deferred to this task and is executed below.

**This is the R3 dogfood result.** Two HIGH findings — one of them a real push-blocking
regression — were found, fixed and re-approved **without reopening a single archived artifact**,
against three consecutive prior releases that each paid a reopen for reviewing after the freeze.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` records the CR-3 range-wide
semantics verbatim ("reachable at more than one path anywhere in the pushed range"), the CR-1
suffix classification of the missing row, and the CR-2 baseline-v5 pattern set;
`specs/memory/product/sdd/sdd-bug-backlog-governance.md` records the review-before-archive order.

### t-042-19-memory-window-scope-fallout

**Description:** The `token_estimate` strip was declared as a mechanical single-key removal over
memory atoms. It reached further than the write set anticipated in three places: (1) five
scaffold/template files and two test modules asserted the key and broke the tree until updated;
(2) `specs/memory/AGENTS.md` is glob-matched by `specs/memory/**/*.md` and its prose literally
named the field, breaking the A2.3/V8 zero-hit grep — it required the documented three-copy
manual sync (canonical, `public/data/`, `public/scaffold/`), since that file is deliberately not
a `dadaia public install` projection target; (3) `product/index.md`, declared "no change" in
SPEC §5, **embeds each atom's `tldr`**, and two of those embedded rows asserted retired facts
(the two-axis version split and the pre-FR7 amnesty wording).

**Resolution:** all three folded into the single T-042-19 commit. The index rows were corrected
to match the new frontmatter so a regeneration reproduces them byte-identically — SPEC §5's "no
change" was true of catalog *membership*, not of generated content, and leaving the rows would
have left memory asserting a retired fact in a generated file. The doctor-decomposition diagram
refresh likewise reached past its named target: three further nodes were stale against the live
modules (a removed governance method, a retired coherence check and its import note, a retired
`pid_probe` attribute), all corrected in the same touch. Two `architecture.md` statements
adjacent to the FR3/FR4 write set were false at HEAD and corrected with them.

**Memory updates:** `specs/memory/architecture.md`,
`specs/assets/architecture/doctor-decomposition.md`, `specs/memory/product/index.md`,
`specs/memory/product/catalog.json`, `specs/memory/AGENTS.md` (+ its two canonical copies), and
the 29 stripped atoms — full list under `## Memory updates`.

### batched-completion-marker-normalization

**Description:** The `[-]`→`[x]` **completion** flips for T-042-03…16 were normalized in one
commit (`44ec8efb`) rather than inside each task's own commit.

**Resolution:** accepted, recorded, not silently passed over (RO-8). The obligation FR5 actually
ships concerns the **reservation** flip, and that was honoured individually: all 17
`chore(tasks): start …` commits are present, so the marker trace A5.3 depends on is complete and
observable in history. The code reviewer verified this independently. Recorded here so a future
auditor reading the completion flips as one commit does not read it as a lost trace.

**Memory updates:** none.

### t-042-16-changelog-backfill-gap-discovered

**Description:** FR13's measurement (V13) was scoped to reconciling the never-published
`[0.5.0]`–`[0.9.0]` headings. Reading the real published list surfaced a **wider** discrepancy
the SPEC had not anticipated: **10 published versions carry no CHANGELOG section at all**
(`0.1.2`, `0.1.5`, `0.1.6`, `0.2.0`–`0.2.3`, `0.3.0`, `0.4.0`, `0.4.1`) and **3 existing
`[0.1.x]` headings** (`[0.1.24]`, `[0.1.7]`, `[0.1.3]`) correspond to no published version.

**Resolution:** deliberately **not** actioned inside this release — A13.2 forbids adding,
renaming or renumbering headings, so reconciling it here would have broken the release's own
acceptance. The preamble volunteers the gap in its own "Known, separate gap" paragraph rather
than silently widening scope, the implementer disclosed it in `decisions_required`, and it is
routed below as this release's **single** intake candidate. Backfilling ten historical sections
is an operator decision about shape and depth, not a mechanical fix.

**Memory updates:** `specs/memory/product/distribution/pypi-distribution.md` — the ADR-2
two-axis claim retired; one axis, the PyPI lineage, with the package/release-id identity
recorded.

## Memory updates

Written during this CLOSURE phase, all inside the single T-042-19 commit `078925e8`:

- `specs/memory/product/sdd/sdd-gate-v3.md` — the shipped gate semantics as they now are:
  range-wide multi-path amnesty denial (unioned over every commit in the range, tree- **and**
  commit-order independent, adapter-only); the per-layer suppression predicate as an exact
  three-row table; the oversized-CURRENT-object never-amnestied boundary; the missing-row suffix
  classification (paths with embedded spaces are ordinary absence); the intentional early close
  as the only swallowed read outcome; baseline v5 with the three declared-platform home
  patterns, their literal-anchored carve-outs and the deliberate `/root` exclusion; the
  registry-degradation stderr note; the masker consuming the detector's own compiled matchers
  and `GitObjectReadError`'s structured path masked at one render boundary; the FROZEN invariant
  generalized to content-addressing; the sentinel's sha-absent-from-`HEAD^` archive coverage.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — §Release And Audit gains the intake
  signal-class routing (FR6); §Merge Cadence gains the review-before-archive order and the
  shell-less-dispatcher reservation obligation (FR5).
- `specs/memory/product/sdd/specs-doctor.md` — SPEC-DOC-031's evidence surface restated as
  consumption-asserting (FR14).
- `specs/memory/product/distribution/pypi-distribution.md` — ADR-2's two-axis split retired; one
  axis, the PyPI lineage; the package/release-id identity recorded (FR13).
- `specs/memory/architecture.md` — doctor-decomposition reference refreshed; the `core/redaction`
  consumer statement corrected (one consumer, `cli/redact.py`, plus the gate's deliberately
  separate detector-derived predicate); the frontmatter-schema sentence restated so it stays
  true after the `token_estimate` removal.
- `specs/assets/architecture/doctor-decomposition.md` — `check_backlog_schema()` removed plus
  three further stale nodes; the live `doctor_governance → features.backlog.document` boundary
  edge added.
- `specs/memory/product/index.md` — two generated `tldr` rows re-synced to the new frontmatter
  (catalog membership unchanged; a regeneration reproduces them byte-identically).
- `specs/memory/product/catalog.json` — regenerated with computed estimates.
- **Every `specs/memory/**/*.md` atom (29)** — the `token_estimate:` frontmatter key removed
  (FR2 memory half), with `memory-frontmatter-v1.schema.json` dropping it from `properties` in
  the same commit.
- `specs/memory/AGENTS.md` (+ `public/data/memory-AGENTS.md`, `public/scaffold/memory/AGENTS.md`)
  — the frontmatter field description updated via the documented three-copy manual sync.
- `specs/memory/tech-stack.md` — **no change**: no dependency added or removed.
- `specs/memory/quality-assurance.md` — **no change**: the stewardship doctrine was applied, not
  amended.

## Dispositions

**No bug and no audit was picked into this release.** The pick claim was measured, not asserted:
V12 (`dadaia bugs status`) returned `[ok] 0 open bug(s)` at T-042-02, before the definition push
(OD-3 / risk R11). Every audit was already archived and dispositioned under
`specs/audits/_archive/`. Pick-time priority (`DADAIA.md` §5) was satisfied with nothing
outranking the backlog set.

The **13 fully-consumed entries** left `## ACTIVE` at the definition commit `01a938dd`
(purge-on-pick, provenance recorded in SPEC §7); this sweep writes their `## LEDGER` lines.
Nothing is deleted.

| Record | Kind | Terminal disposition | Evidence |
|--------|------|-----------------------|----------|
| `specs/backlog/BACKLOG.md` (`backlog-grammar-single-writer-seam` #38) | backlog | `DELIVERED · v0.4.2` | FR1 · T-042-04 `7d6e926e` |
| `specs/backlog/BACKLOG.md` (`denylist-masking-predicate-parity` #39) | backlog | `DELIVERED · v0.4.2` | FR4 · T-042-08 `d1d5c902` |
| `specs/backlog/BACKLOG.md` (`derived-values-computed-not-stored` #43) | backlog | `DELIVERED · v0.4.2` | FR2 · T-042-07 `4cd582b8` + T-042-19 `078925e8` |
| `specs/backlog/BACKLOG.md` (`knowledge-duplication-doc-pass` #44) | backlog | `DELIVERED · v0.4.2` | FR3 · T-042-13 `baccd820` + T-042-14 `009692f4` |
| `specs/backlog/BACKLOG.md` (`flat-release-ship-task-evidence`) | backlog | `DELIVERED · v0.4.2` | FR5 · T-042-14 `009692f4`; dogfooded by this release's own task order |
| `specs/backlog/BACKLOG.md` (`intake-signal-calibration`) | backlog | `DELIVERED · v0.4.2` | FR6 · T-042-15 `6f6cb543`; proven by this document's two routing sections |
| `specs/backlog/BACKLOG.md` (`amnesty-multi-path-blob-fail-closed` #40) | backlog | `DELIVERED · v0.4.2` | FR7 · T-042-09 `49bb84bb`, widened range-wide at `759eb598` (CR-3) |
| `specs/backlog/BACKLOG.md` (`git-batch-epipe-swallow-width` #41) | backlog | `DELIVERED · v0.4.2` | FR8 · T-042-10 `ebda21ef`, CR-1 correction at `759eb598` |
| `specs/backlog/BACKLOG.md` (`self-scan-sentinel-archive-authored-blobs` #45) | backlog | `DELIVERED · v0.4.2` | FR9 · T-042-12 `9edc6aaa` |
| `specs/backlog/BACKLOG.md` (`document-parser-fence-filter-complexity` #42) | backlog | `DELIVERED · v0.4.2` | FR11 · T-042-05 `72b12894` |
| `specs/backlog/BACKLOG.md` (`retire-dead-hotfix-surface` #4) | backlog | `DELIVERED · v0.4.2` | FR12 · T-042-03 `782883d3` + `978bb850` |
| `specs/backlog/BACKLOG.md` (`changelog-version-axis-reconciliation` #11) | backlog | `DELIVERED · v0.4.2` | FR13 · T-042-16 `8a59e9ff` + the `[0.4.2]` section at ship |
| `specs/backlog/BACKLOG.md` (`spec-doc-031-citation-classes` #10) | backlog | `DELIVERED · v0.4.2` | FR14 · T-042-06 `b449085f`; SPEC-DOC-031 9 → 0 |
| `specs/backlog/BACKLOG.md` (`baseline-carve-out-review-cadence` #24) | backlog | **stays `ACTIVE`** — partial pick | FR10 delivered the cross-platform half (T-042-11 `d7f8c273`, CR-2 fix `85ac7ab7`); the residual is rewritten in this commit |
| `specs/bugs/bugs.jsonl` (`gitignore-code-review-artifact-untrackable`) | bug | `Closed` | Registered HIGH by `code-reviewer` at `975ee8f4` during T-042-18; `resolved` event at `7e2ac0b4` with reproducing contract test, `.gitignore` negation and the CR-4 rename as evidence; `dadaia bugs status` → `[ok] 0 open bug(s)` at `85ac7ab7` |
| `specs/bugs/bugs.jsonl` (`memory-token-estimate-normalizer-dead-code`) | bug | **`Open`** — Arm B lane, LOW | Registered `0be80513` by `software-engineer` during T-042-19. `container.py:_normalize_memory_token_estimates` became a permanent no-op once the key was stripped and the schema forbade re-adding it. **Not** an intake candidate — a registered bug is Arm B and never becomes backlog demand |

**Entry #24 — the partial pick, rewritten (CR-5 + CR-6).** Per `dd-release-definition` §5's
full-slug rule, #24 was **not** declared in `**Consumes:**` and stays `ACTIVE`. Its Description
is rewritten in this same commit to state the accurate present state:

- **Delivered by this release** (past tense now true, and it is stated as delivered rather than
  as a promise): FR10's cross-platform half — `/Users/<name>` and `C:\Users\<name>` patterns with
  paired fixtures, baseline bumped to `version: 5`, `/root` evaluated and deliberately excluded
  (grill D10), and the CR-2 prose-form parity fix.
- **Citation (CR-5):** the entry cites `specs/_archive/releases/v0.4.2/SPEC.md`. That path is
  **created by this very commit's `git mv`**. Repointing it at the live path would have made it
  wrong the moment the archive lands, which is why the code reviewer accepted the deferral as
  the only correct sequencing. The dispatcher's `[git]` half **must verify the path resolves
  after the move** and repoint it in the same commit if it does not — verify, do not assume;
  nothing else in the release re-reads that string.
- **CR-6 folded, no new entry (FR15.3 / ADR #15):** the trailing-period carve-out escape in
  `windows-users-path` (the Windows name charset includes `.`, so a placeholder path ending a
  sentence swallows the period and defeats the `^`-anchored `exclude_regex`) is added to #24's
  existing residual. It is pre-existing (dating from T-042-11, not from the CR-2 remediation —
  the reviewer verified the pre-fix form false-positives identically), it **over**-fires on
  placeholder documentation so it costs friction and never privacy, and #24 already names
  exactly this class ("carve-outs are literal-by-literal"). **No backlog entry is materialized
  by this closure.**

**Lane note.** This closure edits `specs/backlog/BACKLOG.md` only where T-042-20's write set
declares it: the 13 LEDGER lines, #24's residual rewrite, the purge-on-pick notice's tense
(its LEDGER lines now exist), and the pick-precedence notice's zero-open-bugs claim, which V12
has made stale. Any further curation is `project-manager`'s.

## Test dispositions

No demotion, no quarantine, no SCAFFOLD expiry in this release. Every deletion is a recorded
supersession whose subject ceased to exist; **zero new e2e tests** were added
(`git diff --stat -- tests/e2e/` empty, independently confirmed by QA), so the LARGE census this
release inherits did not grow. 32 new test functions, all covered by a module- or section-level
`Intent:` declaration.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| supersession (declared in TASKS) | the 2 hotfix cases in `tests/unit/features/specs/test_scaffolder.py` | none needed — the behaviour was **removed**, not moved (`scaffold_hotfix_release` no longer exists) | T-042-03 `782883d3`; QA deletion-class audit, criterion (a) |
| supersession (traceable to FR2/A2.4) | the drift-check test in `tests/unit/test_lint_memory_atoms.py` | none needed — the drift check itself is deleted; with no stored copy there is nothing to drift | T-042-07 `4cd582b8`; QA traced it to the write set and SPEC text, "no ambiguity" |
| relocation (FR1/D1 move) | 6 `backlog_new` tests in `tests/unit/features/spec_artifacts/test_new_artifacts.py` | 5 relocate **byte-identically** into `tests/unit/features/backlog/test_document.py` (matching function names confirmed in the diff); the 6th, a combined `backlog_new`+`release_new` parametrized matrix, split cleanly into `test_invalid_release_id_matrix` (kept) and two `backlog_new` slices in the new home. **Zero coverage lost** | T-042-04 `7d6e926e`; QA independently traced every one |
| remediation (QA-2) | — | 4 tests gained the canonical `Intent: CONTRACT — v0.4.2 <A-id>` tag (`test_baseline_never_flags_placeholder_home_paths_on_any_declared_platform`, `test_baseline_v5_header_and_single_line_patterns`, `test_malformed_registry_produces_exactly_one_stderr_note`, `test_healthy_registry_produces_no_degradation_note`) | `34e71ca7`; re-verified 4 passed, tag shape matches this release's precedent |
| addition (CR remediation) | — | 2 new regression tests shipped **with** the fixes: the CR-1 two-space-path repro and the CR-3 intermediate-commit multi-path repro, each carrying an `Intent:` declaration; plus the CR-0 contract-test row (`specs/releases/v9.9.9/PRE-PR-REVIEW.md`) and the CR-2 prose-form fixture line | `759eb598`, `7e2ac0b4`, `85ac7ab7` |

## Record-only observations

Per FR6/R4 these terminate **here**. Each was recorded in its author's own findings array or
handoff — never-silent holds, zero observations lost — but none carries a fix surface worth
operator adjudication, so **none enters a PM intake report**. **15 record-only observations.**

| # | Source | Observation | Why record-only |
|---|--------|-------------|-----------------|
| RO-1 | `code-reviewer` `191500Z` | `backlog_new`'s write-then-verify raises *after* the file is already mutated; no rollback. | Deliberately declined — SPEC §4 non-goal 1 (D2) rejects `atomic_write_text`; the message opens with "wrote `<name>` but a re-parse …", so the operator is told the file changed. Honest as shipped. |
| RO-2 | `code-reviewer` `191500Z` | The slug-uniqueness check now depends on a successful parse, so an unterminated fence could hide an existing slug. | Fails **closed**: the same shadow hides the freshly-written slug, so write-then-verify raises. |
| RO-3 | `code-reviewer` `191500Z` | `fenced_ranges` / `top_level_heading_starts` promoted to `__all__` with no consumer outside their own module. | Public surface widened without an external consumer — mild tension with R5, justified by intent-revealing docstrings. Awareness-only. |
| RO-4 | `code-reviewer` `191500Z` | `catalog.json` at the reviewed commit differed from the computed values on **24 of 26 atoms** — worst `sdd-gate-v3` 1600→3814 (**138 %**), `context-management` 470→1021 (117 %). | The declared FR2 intermediate state, already fixed at HEAD by T-042-19's regeneration. Recorded because it **substantiates FR2's own premise**: the SPEC cited 37 % and 42 %; reality was worse. |
| RO-5 | `code-reviewer` `191500Z` | `estimate_tokens` is duplicated verbatim in `public/scripts/generate-memory-catalog.py` — a Class-1 second writer. | Structurally unavoidable (the projected script is importless), explicitly out of scope (SPEC §4 non-goal 6), pinned to byte-identical output by a contract test, and already owned by ACTIVE entry #6 `thin-wrapper-projected-scripts`. |
| RO-6 | `code-reviewer` `191500Z` | `_dispositions_tokens` is not fence-aware; a `## Dispositions` heading quoted inside a fence would read as structure. | No archived document has that shape, and SPEC-DOC-031 is WARN by design (R3 accepts false negatives). |
| RO-7 | `code-reviewer` `191500Z` | `git_objects.py` writes `proc.returncode not in (0,)` where `!= 0` reads plainly. | Cosmetic. |
| RO-8 | `code-reviewer` `191500Z` | The `[-]`→`[x]` completion flips for T-042-03…16 were normalized in one commit (`44ec8efb`). | The FR5 obligation concerns the **reservation** flip, honoured individually across all 17 `chore(tasks): start …` commits; A5.3's marker trace is complete. Also recorded as a drift above. |
| RO-9 | `code-reviewer` `191500Z` | Test **size** is declared by directory placement plus module/section `Intent:` headers rather than a per-test size token. | All 32 new tests fall under a declaration; none is undeclared. Consistent with the TASKS standing rule, which specifies the `Intent:` format only. |
| RO-10 | `product-engineer` `200500Z` | `cli/redact.py`'s module docstring still asserts the push gate shares this primitive — false since FR4, which made the gate consume the detector's matchers instead. | Comment-only, zero behavioural effect; the correct fact is already stated in `architecture.md`. The file is a **deliberate zero-diff surface this release** (A4.3), so touching it here would have broken an acceptance criterion. Awareness-only; corrected by whoever next legitimately edits the file. |
| RO-11 | `software-engineer` `192405Z` | `specs/memory/AGENTS.md` is not a product atom but is glob-matched by `specs/memory/**/*.md`, and its prose named the field — requiring the documented three-copy manual sync. | Documented and evidenced in the commit; the file is deliberately not a `public install` projection target. No action. |
| RO-12 | gate runs, all tasks | `lint-memory-atoms` heading-allowlist warnings on memory atoms — 12 per-atom heading warnings (count relayed from the T-042-19 gate run), which `specs doctor` collapses into a single LINT-1 aggregate WARN line. | **Pre-existing**, unchanged by this release, and unchanged in count across every gate run. The hardcoded allowlist is a known library limitation accepted since v0.3.0. |
| RO-13 | gate runs, all tasks | The other 4 pre-existing `specs doctor` warnings: SPEC-DOC-027 ×2 (legacy release-dir names), SPEC-DOC-036 ×2 (pre-v0.4.2 archived audits). | Pre-existing and byte-identical at every run in this release (`0 error(s), 5 warning(s)` throughout); none names a T-042-* symbol or path. |
| RO-14 | `code-reviewer` `191500Z` | Production Python is **net +169**, not net-negative; the reviewer asked the closure to state the measured number rather than claim a net-negative release. | Explicitly "not a finding" — SPEC §2's deletion list is delivered item by item. Honoured in the Summary above with the full breakdown. |
| RO-15 | `product-engineer` `200500Z` | The doctor-decomposition diagram's introspection drift-guard pins **class** names only; the method rows are accurate by inspection today and should be re-checked at the next structural release. | Forward-looking note about a guard's coverage boundary, not a defect. No fix surface today. |

## Intake candidates

Actionable residuals only. This closure creates **no** backlog entry (FR15.3 / ADR #15) — each
item below is *listed* for `project-manager` to compile into its next operator-facing intake
report.

### To be adjudicated

1. **CHANGELOG backfill gap (from T-042-16 / FR13).** The V13 measurement against the package
   index surfaced that **10 published versions carry no CHANGELOG section at all** (`0.1.2`,
   `0.1.5`, `0.1.6`, `0.2.0`–`0.2.3`, `0.3.0`, `0.4.0`, `0.4.1`) and **3 existing `[0.1.x]`
   headings** (`[0.1.24]`, `[0.1.7]`, `[0.1.3]`) match no published version. Out of FR13's scope
   by construction — A13.2 forbids adding, renaming or renumbering headings, so acting on it
   inside this release would have failed the release's own acceptance. Disclosed in the
   CHANGELOG preamble's own "Known, separate gap" paragraph and in the implementer's
   `decisions_required`. **Needs an operator decision on shape before it can be a task:**
   reconstruct all ten sections from git history, or write a single "pre-0.4.2 sections are
   incomplete" statement, or leave the lineage as-is and only reconcile the three phantom
   headings. Evidence: `.dadaia/tmp/software-engineer/20260816/t-042-16-pypi-versions.json`,
   captured 2026-08-16T17:32:59Z.

### Pre-approved intake

None. No operator-ratified deferral was taken during this release beyond the SPEC §4 non-goals,
all of which are already owned by ACTIVE entries (#6 `thin-wrapper-projected-scripts`, #2
`test-suite-remediation-stewardship`, #24 `baseline-carve-out-review-cadence`) or are recorded
declines (D2, D4, D7, D10).

### Not intake — routed elsewhere

- `memory-token-estimate-normalizer-dead-code` (LOW, **Open**) is in the **bug lane**, not
  intake. A registered bug is Arm B and is fixed on the spot on `hotfix/{M.m.p}`; it never
  becomes backlog demand. See `## Dispositions`.
- **CR-6** folds into ACTIVE entry #24's residual — no new entry, per FR15.3.

### A6.3 reconciliation — zero observations lost

| Source | Actionable | Record-only |
|---|---:|---:|
| `qa-engineer` (both passes) | 2 (QA-1, QA-2) | 0 |
| `code-reviewer` (both rounds) | 7 (CR-0…CR-6) | 9 (RO-1…RO-9) |
| `software-engineer` (implementation + memory) | 2 (CHANGELOG gap; the dead-code bug) | 2 (RO-11, RO-14 measurement basis) |
| `product-engineer` (memory window) | 0 | 2 (RO-10, RO-15) |
| gate runs (both doctors, all tasks) | 0 | 2 (RO-12, RO-13) |
| **Total** | **11** | **15** |

**26 observations, 26 accounted for.** Of the 11 actionable: **9 closed inside this cycle**
(QA-1, QA-2, CR-0, CR-1, CR-2, CR-3, CR-4 fixed and re-verified; CR-5 and CR-6 executed by this
closure), **1 routed to the bug lane** (open, LOW), **1 routed to intake** (the CHANGELOG
backfill gap). The 15 record-only terminate in the section above. Zero lost, and exactly **one**
item reaches the operator — which is the calibration FR6 exists to produce, measured on the
release that ships it.

## Open decisions restated (OD-1…OD-4)

Recorded, not blocking; none changed this release's scope. Restated for the operator's ruling:

- **OD-1 — De-personalise the git commit identity used in this workspace?** Standing operator
  question, restated at intake #3. Both v0.12.0 security reviews dispositioned the existing
  identity as pre-existing published metadata (1,063 of 1,203 commits), not a leak. It is a
  policy call. **Still open**, unrelated to this scope; it also stands in `BACKLOG.md`'s
  standing-questions block so it resurfaces at every pick.
- **OD-2 — Is `deferred` terminal for bug
  `panel-telemetry-sqlite-corrupts-under-concurrent-access`, or does it return to the queue?**
  **Still undecided.** Entry #12 (the dangling-pointer repair) was not picked and proceeds
  either way. Keeps surfacing at every pick until ruled.
- **OD-3 — The published lineage and the open-bug count must be measured, not asserted
  (`product-engineer` has no shell).** **Discharged by measurement.** V13 read the package index
  at implementation time (13 versions, `0.1.0`–`0.4.1`, evidence captured); V12 ran
  `dadaia bugs status` before the definition push and returned `[ok] 0 open bug(s)`, confirming
  SPEC §7's pick claim. The FR13 preamble states measured fact with its evidence path. The
  underlying constraint (a shell-less author needs a named task step for every measurement)
  worked and should stay the pattern.
- **OD-4 — Should `token_estimate` remain in `catalog.json` at all?** **Kept, computed.** It is
  the only cost signal an agent has when choosing atoms, and RO-4's measurement (24 of 26 atoms
  wrong by up to 138 % while it was hand-stored) shows the value was worth computing rather than
  dropping. Revisit only if it goes unused.

## Version confirmation

- **`pyproject.toml` reads `0.4.2`** — verified in this closure; it already read `0.4.2` at the
  branch cut, so no bump is owed (A13.3).
- **One axis (ADR R2).** The release id **is** the minted package version: release `v0.4.2` mints
  package `0.4.2`. ADR-2's two-axis split is retired in code, in the CHANGELOG preamble and in
  the `pypi-distribution` memory atom (A13.4).
- **PyPI lineage.** 13 versions published, `0.1.0` through **`0.4.1`** (the latest published);
  `0.4.2` is unpublished until this release ships. Measured 2026-08-16T17:32:59Z; evidence
  `.dadaia/tmp/software-engineer/20260816/t-042-16-pypi-versions.json`.
- **Owed to the dispatcher's `[git]` half:** the `## [0.4.2]` `CHANGELOG.md` section, placed
  above the T-042-16 preamble's explanation, as the first section written under the new
  one-section-per-published-version rule. The archived release directory must be `v0.4.2`
  (A13.3).

## Archive decision

**MOVE.**

The dispatcher's `[git]` half executes, in this same commit:

```bash
git mv specs/releases/v0.4.2 specs/_archive/releases/v0.4.2
```

then sets `specs/releases/ACTIVE.md` to `release: none` / `phase: none`, adds the
`## [0.4.2]` CHANGELOG section, and — **CR-5, a verification and not an assumption** — confirms
that `specs/backlog/BACKLOG.md` entry #24's citation of
`specs/_archive/releases/v0.4.2/SPEC.md` resolves after the move, repointing it in the same
commit if it does not.

**Standing note for the next closer (`dd-release-closure`).** SPEC-DOC-031 counts only
*archived*-document assertions, so this closure's own archive move adds one WARN per
non-terminal `ACTIVE` slug that the just-archived SPEC or this CLOSURE names — here, `#24`
`baseline-carve-out-review-cadence`, which stays ACTIVE by design as a partial pick. Measure the
SPEC-DOC-031 count **after** this archive move, never before; the pre-move count is 0.
