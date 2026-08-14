# Closure: Release — v0.8.0 — Audit disposition

**Status:** Aprovado
**Release ID:** v0.8.0
**Owner:** product-engineer
**Closed:** 2026-08-14
**Branch:** `feature/v0.8.0` (cut from `develop` at `d3e05d19`; branch contract: `dadaia-gitflow`)
**Source SPEC:** `specs/releases/v0.8.0/SPEC.md` · **Source PLAN:** `specs/releases/v0.8.0/PLAN.md`

---

## Summary

v0.8.0 is a **record release**: its deliverable is a decision written down, not behaviour
changed. Two audits had been sitting loose in `specs/audits/` without a disposition —
`2026-07-15-consumer-dadaia-integration.md` (12 findings, named remediation release v0.2.5,
which shipped without a finding-by-finding disposition) and
`2026-07-18-architecture-resilience-review.md` (W1–W6, whose audited object, the lifecycle
workflow engine, was demolished in v0.3.0). Under law §5 an undispositioned audit outranks
*every* backlog entry at *every* future pick, so the two of them were silently blocking the
queue. This release gives all 18 findings an explicit, evidenced disposition and archives
both audits naming v0.8.0 as the disposing release.

The consumer-integration audit closes 8 `fixed` · 1 `superseded` · 1 `rejected` · 2
`deferred`; the resilience review closes 5 `rejected` (moot by the v0.3.0 demolition) · 1
`superseded`. Nothing was dropped: the two `deferred` findings are carried in full as
acceptance criteria of the live backlog candidate `consumer-side-validation-round`, the
`superseded` consumer finding points at an open registered bug, and the `superseded`
resilience finding points at the backlog candidate `thin-wrapper-projected-scripts`,
rewritten against HEAD with the corrected direction.

No production code was touched, no test was added or removed, no backlog entry and no bug
was picked. The queue is now honest: the next release picks from the backlog without an
undispositioned audit outranking it.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-080-01 | Commit the definition content on `feature/v0.8.0` (trio + both audit disposition sections + governance memory atom) | `c4b91086` |
| T-080-02 | Milestone (a): merge into `develop`, diff-based security review, push | `c223eee3` (merge); pushed tip `b622c17c` |
| T-080-03 | Pre-archive verification — the irreversibility gate (7 checks, APPROVED) | none (evidence only) — handoff `2026-08-14T153358Z-qa-engineer-T-080-03-pre-archive-verification.handoff.json` |
| T-080-04 | `git mv` both audits into `specs/audits/_archive/` under `--dispositioned-v0.8.0` | `8586e07b` |
| T-080-05 | Post-archive verification and evidence capture (APPROVED) | none (evidence only) — handoff `2026-08-14T153655Z-qa-engineer-T-080-05-post-archive-verification.handoff.json` |
| T-080-06 | CLOSURE, memory record, release archive, version-bump decision | `docs(T-080-06): close release v0.8.0` (sha assigned by the dispatcher at commit time) |
| T-080-07 | Milestone (b): ship — merge, security review, push, PR `develop` → `main` | executed **after** this closure; see `## Drifts › ship-task-marker-unflippable-after-archive` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| V1 — Disposition completeness, consumer audit: exactly 12 rows F-01…F-12, every token in {`fixed`,`superseded`,`deferred`,`rejected`}, every evidence cell non-empty (A1.1) | programmatic row extraction of `## Disposition — release v0.8.0` (qa-engineer, T-080-03) | handoff `2026-08-14T153358Z-qa-engineer-T-080-03-pre-archive-verification.handoff.json`, check 1 PASS, `metrics.disposition_rows_verified_file1 = 12`; score 8/1/1/2 matches SPEC FR1 |
| V2 — Disposition completeness, resilience audit: exactly 6 rows W1…W6 + the explicit "§1's 25-row dataset is evidence, not findings" statement and the §4 proposal mapping (A2.1, A2.2) | programmatic row extraction + statement read (qa-engineer, T-080-03) | same handoff, check 2 PASS, `metrics.disposition_rows_verified_file2 = 6`; dataset row count independently re-confirmed at closure = 25 |
| V3 — Historical record untouched: zero deletions/modifications inside the protected original sections of either audit (A1.2, A2.3) | `git show c4b91086 -- <both audit paths>`; `git diff cd66470f^ HEAD -- <both audit paths>` | same handoff, check 4 PASS (LOW note): file 2's diff is 100% additions; file 1's only non-addition is the sanctioned frontmatter marker `status: remediation-required` → `dispositioned` with the original preserved losslessly as `original_status:` — explicitly authorized by FR1 and outside A1.2's protected scope |
| V4 — Inheritance is real: both `deferred` findings and W6 land on live backlog entries (A1.4, A2.5) | file read of both backlog entries (qa-engineer, T-080-03) | same handoff, check 5 PASS — `specs/backlog/consumer-side-validation-round.md` carries findings #3/#6 as acceptance criteria; `specs/backlog/thin-wrapper-projected-scripts.md` carries W6 with the corrected direction. Both remain `status: candidate` by design (SPEC §4.6, PLAN R5) |
| V5 — Supersession is real: the F-10 target bug exists and is open (A1.5) | `grep 'context-alive-sweeps-unrelated-worktree-changes' specs/bugs/bugs.jsonl` | same handoff, check 6 PASS — a single JSONL line, `event: reported`, `ts: 2026-08-13T01:49:49Z`, no terminal event |
| V6 — Archive names the release: both `_archive` paths exist and neither raises SPEC-DOC-036 (A3.1, A3.3) | `dadaia specs doctor` (post-move) | `.dadaia/tmp/qa-engineer/20260814/T-080-05-specs-doctor-after-archive.txt` — the only two SPEC-DOC-036 warnings name the unrelated pre-existing `2026-07-06-full-audit-*--dispositioned-v0.1.61.md` files; neither v0.8.0 archived audit is named |
| V6b — The move preserved history (A3.2) | `git show 8586e07b --stat`; `git log --oneline --follow <both archived paths>` | handoff `2026-08-14T153655Z-qa-engineer-T-080-05-post-archive-verification.handoff.json`, finding 4 — pure renames, 0 body diff; `--follow` resolves back through `c4b91086` into pre-release history |
| V7 — Nothing else regressed: doctor before vs after the archive move (A5.1, A5.2) | `dadaia specs doctor` before (T-080-03) and after (T-080-05); `diff` of the two captures | `.dadaia/tmp/qa-engineer/20260814/T-080-03-specs-doctor-before-archive.txt` vs `...T-080-05-specs-doctor-after-archive.txt` — **byte-identical**, both `0 error(s), 7 warning(s)`, `metrics.diff_before_after_bytes_changed = 0`, `new_warnings_attributable_to_release = 0`. All 7 warnings are pre-existing baseline noise (memory-atom LINT-1 drift/headings on 15 unrelated atoms, 2× SPEC-DOC-027 legacy release-dir names, 2× SPEC-DOC-031 on unrelated v0.7.0 entries, 2× SPEC-DOC-036 on the pre-existing v0.1.61 archived audits) |
| V8 — Memory stays atomic: no changelog/history section, catalog slug set unchanged (A4.2, A4.3) | `dadaia specs doctor` (LINT-1, CAT-1, SPEC-DOC-008) | same T-080-05 handoff, finding 3 PASS — LINT-1 byte-identical before/after, CAT-1 and SPEC-DOC-008 silent on both sides; the FR4 atom edit landed in DEFINITION (`c4b91086`) and changed no slug, so `catalog.json` needed no regeneration |
| V9 — Post-closure prediction, stated before the fact: archiving this release directory adds exactly 3 new SPEC-DOC-031 WARNs and no ERROR | reading `doctor_governance.py:196-278` against `specs/backlog/*.md` statuses at closure | see `## Drifts › spec-doc-031-citation-false-positives` — the three slugs are cited by the archived `SPEC.md` and are the documented ADR-6 false-positive class; the doctor run the dispatcher makes after the move is expected to read `0 error(s), 10 warning(s)` |

## Drifts

### closure-phase-not-committed-to-active-md

**Description:** The `dadaia-release-closure` protocol says to set `ACTIVE.md` `phase: CLOSURE`
before writing CLOSURE.md. Committing that value here would have produced a **SPEC-DOC-024
ERROR**: with `phase=CLOSURE`, the validator requires every marker in the active TASKS.md to
be `[x]`, and T-080-07 (ship) is `[ ]` *by design* until after this closure
(`doctor_release.py:394-409`). The phase's only mechanical function — authorizing a
`specs/memory/**` write — was not needed, because this release's single memory edit (FR4)
landed in the DEFINITION phase at `c4b91086` and CLOSURE only *records* it.

**Resolution:** The CLOSURE phase was traversed logically, not as a committed `ACTIVE.md`
value: `ACTIVE.md` moves in one write from `phase: IMPLEMENTATION` to the terminal
`release: none` / `phase: none`. No memory file was written in this phase, so no gate
authorization was bypassed. The trade-off is a lost intermediate audit trail in `ACTIVE.md`
for the closure window; the trail exists in this file and in the single T-080-06 commit.

**Memory updates:** none required — the finalization-order rule (memory → CLOSURE → archive)
in `specs/memory/product/sdd/sdd-bug-backlog-governance.md › ## Merge Cadence` is unchanged
and remains true; the ordering held, with the memory step already satisfied from DEFINITION.

### ship-task-marker-unflippable-after-archive

**Description:** T-080-07 (ship) has T-080-06 as a precondition, and T-080-06 archives the
release directory. `specs/_archive/` is FROZEN (law §3), so once the `git mv` runs, T-080-07's
`[ ]` marker can never be flipped to `[x]` — the task that closes the release is structurally
unable to record its own completion. This is a defect of the flat record-release task shape,
not of this release's execution.

**Resolution:** T-080-07 is archived as `[ ]` and **must not** be edited afterwards (the gate
blocks it, and editing archived content would be a worse lie than leaving it open). Its
completion evidence lives where it actually is: the milestone (b) merge commit, the
`security-reviewer` handoff for the shipped delta, the PR `develop` → `main`, and CI. Routed
to the PM as a process observation (see `## Backlog returns`).

**Memory updates:** none — this is a task-template shape issue, not current product truth.

### spec-doc-031-citation-false-positives

**Description:** Found at closure, before the move: `SPEC-DOC-031` scans every archived
release's `SPEC.md` and `CLOSURE.md` line by line for backlog slugs and warns when a matched
slug's entry is non-terminal, excluding only lines inside a `## Backlog returns` section
(`doctor_governance.py:196-224`). This release's SPEC.md *cites* three `candidate` entries
without consuming any of them: `consumer-side-validation-round` (FR1, the inheritor of the
two `deferred` findings), `thin-wrapper-projected-scripts` (FR2, the inheritor of W6), and
`push-range-denylist-scan` (§4 non-goal 2, an explicit *out-of-scope* citation). Archiving
this directory therefore raises three new WARNs that assert consumption which demonstrably
did not happen — the ADR-6 false-positive class the check itself documents.

**Resolution:** Accepted and predicted rather than papered over. The correct fix is *not* to
flip those three entries (SPEC §4.6 and PLAN R5 forbid it — this release picked nothing), and
*not* to strip the citations from an `Aprovado` SPEC (that would destroy the evidence the
disposition rests on). The prediction is recorded as V9 so the post-archive doctor delta is
explained in advance: `0 error(s), 10 warning(s)`, +3 WARN, 0 ERROR, all three of the
documented false-positive class. Routed to the PM as a candidate refinement of the check.

**Memory updates:** none — `specs/memory/product/sdd/specs-doctor.md` describes the validator
families, not per-check false-positive taxonomy, and remains true.

### hotfix-v0.5.1-inside-the-release-window

**Description:** While v0.8.0 was in flight, bug
`init-venv-bootstrap-inherits-degraded-base-python` (HIGH) was fixed Arm B on
`hotfix/v0.5.1` and merged into `develop`, bumping the package version 0.5.0 → 0.5.1 and
adding a `CHANGELOG.md` entry. It shares a push range with this release
(`ff1d96df..b622c17c`, reviewed and APPROVED full-range by `security-reviewer` at
`2026-08-14T151941Z`), which makes it look adjacent to v0.8.0 in git history.

**Resolution:** Recorded here as a **period event outside this release's scope**, not a
v0.8.0 deliverable. It is Arm B in full (law §1): its record is the bug ledger's `resolved`
event plus the `CHANGELOG.md` [0.5.1] entry — no SPEC, PLAN, TASKS or
`specs/releases/<id>/` directory, per law §5 (Hotfixes). v0.8.0 shipped zero lines of
production code; every line of production code in the shared push range belongs to the
hotfix.

**Memory updates:** none — the hotfix doctrine already in
`specs/memory/product/sdd/sdd-bug-backlog-governance.md › ## Bugs` describes exactly this
flow and needed no change.

## Memory updates

No memory file was written during the CLOSURE phase. This release's single memory delta (FR4)
was authored and committed in the **DEFINITION** phase, and CLOSURE re-verified it against
A4.1/A4.2 post-archive and found it still true.

- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — written in DEFINITION at
  `c4b91086`. `## Release And Audit` states the three A4.1 facts: (i) one audit generates
  exactly one remediation release, (ii) that release dispositions every finding as
  `fixed`/`superseded`/`deferred`/`rejected`, (iii) the archived audit carries a
  disposing-release pointer naming that release, with SPEC-DOC-036/SPEC-DOC-038 named as the
  backstops. `## Runtime State` carries
  `specs/audits/_archive/<audit>--dispositioned-<release-id>`. Re-verified at closure against
  the two files now on disk — both match that shape exactly, so the atom describes the product
  as it is now. No changelog/history/version section was added (A4.2).
- `specs/memory/product/index.md`, `specs/memory/product/catalog.json` — no change: no feature
  was added, removed or re-ranked; the atom's slug is unchanged (A4.3, CAT-1 silent).
- `specs/memory/architecture.md` — no change: no layer, module or dependency contract moved.
- `specs/memory/tech-stack.md` — no change: no dependency, command or Python version moved.
- `specs/memory/quality-assurance.md` — no change: no test, tier or gate moved.

## Dispositions

This release picked **no backlog entry and no bug** (SPEC "Consumes" header and §4 non-goals
4/5/6). No backlog status and no bug status is therefore flipped by this closure — the sweep
is complete precisely because there is nothing of those two kinds to sweep. The rows below
are the two **audits** this release dispositioned.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/audits/_archive/2026-07-15-consumer-dadaia-integration--dispositioned-v0.8.0.md` | audit | `ARCHIVED — dispositioned v0.8.0` | 12/12 findings dispositioned (8 `fixed`, 1 `superseded`, 1 `rejected`, 2 `deferred`); frontmatter `disposing_release: v0.8.0` + `**Disposition:** v0.8.0` line; verified T-080-03 check 1/3, moved at `8586e07b`, SPEC-DOC-036 clean post-move (V6) |
| `specs/audits/_archive/2026-07-18-architecture-resilience-review--dispositioned-v0.8.0.md` | audit | `ARCHIVED — dispositioned v0.8.0` | 6/6 findings dispositioned (5 `rejected` moot-by-removal, 1 `superseded`); `**Disposition:** v0.8.0` + `**Disposing release:** v0.8.0` lines; §1's 25-row dataset declared evidence, not findings; verified T-080-03 check 2/3, moved at `8586e07b`, SPEC-DOC-036 clean post-move (V6) |

Explicit non-flips, stated so a later reader does not mistake them for an incomplete sweep:

- `specs/backlog/consumer-side-validation-round.md` — stays `candidate`. It **inherited** the
  two `deferred` consumer findings (F-03, F-06); it was not consumed by this release.
- `specs/backlog/thin-wrapper-projected-scripts.md` — stays `candidate`. It **inherited** W6;
  it was not consumed by this release.
- `specs/backlog/push-range-denylist-scan.md` — stays `candidate`. Cited only as an explicit
  out-of-scope item (SPEC §4 non-goal 2).
- Bug `context-alive-sweeps-unrelated-worktree-changes` — stays **open**. F-10 is `superseded`
  *by* it; the bug is fixed Arm B on `hotfix/{M.m.p}`, outside this release (SPEC §4 non-goal
  5). A `superseded` disposition points at a carrier, it does not import the work.
- Bug `panel-telemetry-sqlite-corrupts-under-concurrent-access` — untouched, still `deferred`
  pending the operator's decision (SPEC §4 non-goal 4). No `bugs append` event was emitted by
  this release.

## Test dispositions

None. This release changed no test and no production code (SPEC §4 non-goal 1, PLAN §2), so
there is no demotion map, no quarantine expiry and no SCAFFOLD expiry to record. No pytest leg
is claimed as evidence for this release's scope (PLAN §5) — the pre-push CI preflight that ran
at each push is the branch contract, not this release's validation.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| — | none | none — zero test delta in this release | `git show 8586e07b --stat`, `c4b91086` (documentation-only deltas) |

## Backlog returns

`specs/backlog/**` belongs to `project-manager` (law §5); this release authors nothing there.
The items below are **routed in writing** for the PM to materialize or reject. Nothing here is
picked, and no status anywhere is flipped by this closure.

- `backlog/candidates.md` ← **Stale live release directories.** `specs/releases/v0.2.6/` and
  `specs/releases/v0.2.9/` still sit in the live tree with a full SPEC/PLAN/TASKS/CLOSURE set
  and were never archived. Observed during definition (SPEC §4 non-goal 7), untouched here.
  After this release the live `specs/releases/` should hold only `README.md`, `.gitkeep` and
  `ACTIVE.md` — it will hold those two directories instead. Needs a PM decision:
  `git mv` both into `specs/_archive/releases/`, or record why they stay.
- `backlog/candidates.md` ← **Dangling `panel-runtime-reliability` pointer** in the bug ledger,
  noted by the deep triage and explicitly not repaired here (SPEC §4 non-goal 4). Needs a PM
  decision on whether the pointer is repaired or the referenced record is created.
- `backlog/candidates.md` ← **Operator decision pending on bug
  `panel-telemetry-sqlite-corrupts-under-concurrent-access`**: is the `deferred` state accepted
  as terminal, or does it return to the queue? Blocking nothing today, but the bug ledger
  carries an undecided item that will keep surfacing at every pick.
- `backlog/candidates.md` ← **SPEC-DOC-031 citation false positives** (found at this closure,
  detailed in `## Drifts`). The check treats *any* slug mention in an archived `SPEC.md` /
  `CLOSURE.md` outside a `## Backlog returns` section as evidence of consumption, so an
  inheritance citation and an explicit *out-of-scope* citation both raise a WARN asserting
  something that did not happen. Candidate refinement: also exclude out-of-scope/non-goal
  sections, or key the check on a machine-readable consumed set
  (`consumed_backlog.json`) instead of free-text slug matching.
- `backlog/candidates.md` ← **The two LOW security findings of the v0.5.1 hotfix review were
  declared routed to the backlog but no entry exists.** The APPROVED handoff
  `2026-08-14T151941Z-security-reviewer-v0.8.0-plus-hotfix-full-range.handoff.json` closes with
  "Two LOW findings (CWE-426 absolute-path filter; missing subprocess timeout/stdin isolation)
  are defence-in-depth and are routed to the backlog, not to this push" — a grep of
  `specs/backlog/` for `CWE-426`, `isabs`, `python_env` and `subprocess timeout` returns zero
  files. The routing was asserted and never materialized. Belongs to the hotfix's Arm B lane,
  surfaced here because this closure is where it was caught.
- `backlog/ideas.md` ← **A flat release's ship task cannot record its own completion.**
  T-080-07 archives as `[ ]` because T-080-06 froze the directory before it could run (see
  `## Drifts`). Candidate fix for the release TASKS template: make ship the *last* task before
  archive, or state in the template that the ship task's evidence is the merge/PR and its
  marker is expected to archive open.
- `backlog/ideas.md` ← **CHANGELOG version-axis incoherence.** `CHANGELOG.md` carries a dated
  `## [0.5.1] — 2026-08-14` above `## [Unreleased] — spec release v0.7.0`,
  `## [Unreleased] — spec release v0.6.0`, `## [Unreleased] — spec release v0.5.0` and
  `## [0.5.0] — Unreleased`: the hotfix minted a PATCH on top of a version whose own section
  still reads *Unreleased*, so the file no longer says truthfully what a given package version
  contains. Pre-existing, not caused by this release; flagged because the version-bump decision
  below rests on the same axis.
- `backlog/ideas.md` ← **The resilience audit's own title is internally inconsistent** — it
  reads "the 21-bug retrospective" while its §1 dataset has 25 rows (counted at closure; the
  SPEC's "25-row" statement is the correct one). The file is now FROZEN in `_archive/`, so
  this is a note for readers, never an edit.

## Version bump decision

**Decision: no `pyproject.toml` bump and no new `CHANGELOG.md` entry for v0.8.0.** T-080-06's
description asks for a bump "per the gitflow contract"; read against the contract itself, the
correct execution of that instruction here is to mint nothing. Justification, on the record:

1. **The gitflow contract binds the bump to a hotfix merge, not to a release closure.** Law §5
   (Hotfixes): "At merge to `develop`, the same commit bumps `pyproject.toml`'s version and adds
   the `CHANGELOG.md` entry." §5 (Releases) prescribes no package bump — it prescribes the
   milestone merges, the security review, the push and the PR.
2. **The two version axes are distinct and documented.** `specs/memory/product/distribution/pypi-distribution.md`
   (ADR-2) records the split: SDD release ids version the SDD process, the `0.x` package version
   versions the shipped library. `v0.8.0` is a specs identity, not a package version; renumbering
   the package to match would break a documented, deliberately never-renumbered convention.
3. **This release contains zero shipped bytes.** SPEC §4 non-goal 1 and PLAN §2: no file under
   `dadaia_workspace/` was modified. A bump would publish a wheel byte-identical in code to
   0.5.1 — a version number asserting a change that does not exist.
4. **The period's only production code already minted its version.** `0.5.1` was minted by the
   `init-venv-bootstrap-inherits-degraded-base-python` hotfix, correctly, at its merge into
   `develop`. It already covers every line of production code in the shared push range.
5. **A CHANGELOG entry would deepen an existing incoherence, not resolve one.** The file already
   carries three stacked `[Unreleased] — spec release vX` sections beneath a dated `[0.5.1]`
   (see `## Backlog returns`). Adding a fourth for a release with no package-visible delta adds
   noise to a section that already needs reconciliation. v0.8.0's record is this `CLOSURE.md`
   plus the two archived audits.

**Operator override path, if wanted:** the only defensible entry would be a governance note,
not a version — e.g. a `### Governance` bullet under the existing `[Unreleased]` heading reading
"spec release v0.8.0 — both open audits (2026-07-15 consumer integration, 2026-07-18
architecture resilience) fully dispositioned and archived; no package delta". `pyproject.toml`
stays at `0.5.1` in either case. `pyproject.toml` was **not** modified by this closure.

## Archive decision

**MOVE** — `specs/releases/v0.8.0/` moves to `specs/_archive/releases/v0.8.0/` via `git mv`,
executed by the dispatcher (`product-engineer` has no shell). `ACTIVE.md` is set in the same
commit to `release: none` / `phase: none`: no release follows immediately, and the next pick is
the PM's, now unblocked — with both audits dispositioned, no undispositioned audit outranks the
backlog at the next pick (law §5).

The archived directory carries T-080-07 as `[ ]` by design (see `## Drifts`); after the move,
nothing under `specs/_archive/` is edited again.
