# PLAN — Release v0.8.0 — Audit disposition

**Status:** Aprovado
**Release ID:** v0.8.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.8.0/SPEC.md`
**Grill:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`
**Branch:** `feature/v0.8.0` (cut from `develop` at `d3e05d19`; branch contract: `dadaia-gitflow`)

---

## 1. Strategy

This is a **record release**: its deliverable is a decision written down, not behavior
changed. No file under `dadaia_workspace/` is touched. That shapes every choice below.

Three properties drive the ordering:

1. **The content is authored in DEFINITION; implementation is git plus verification.**
   The disposition tables, the memory correction and this trio are `product-engineer`
   output, written before approval. What remains for implementers is: commit, verify
   completeness, move, verify again, close. There is no code task and no test task,
   because there is no behavior delta to prove.
2. **The archive move is irreversible in place.** `specs/audits/_archive/` is FROZEN
   (law §3): after the `git mv`, the file cannot be edited to repair a missing row. So
   completeness verification is a *separate task that precedes the move*, owned by a
   different role than the author, and its output is evidence for CLOSURE.
3. **Additive-only edits to historical records.** `specs/audits/README.md` says an audit
   is immutable once committed. The disposition is therefore appended (plus frontmatter
   markers), never woven into the findings text — which also makes A1.2/A2.3 verifiable
   with a plain `git diff` (additions only, zero deletions in the original sections).

The release ships **flat** — no `alpha-N` / `rc-N` segment. Segmentation exists to close
increments of implementation with a QA review; there is no implementation increment here.
The trio review still happens at milestone (a), and the security review runs at both merge
milestones, unchanged.

---

## 2. Layers affected

| Layer | What moves |
|---|---|
| Audit records (`specs/audits/`) | two files gain a disposition section + frontmatter markers, then move to `_archive/` under the `--dispositioned-v0.8.0` name |
| Memory (`specs/memory/`) | `product/sdd/sdd-bug-backlog-governance.md` — `## Release And Audit` + `## Runtime State`; DEFINITION-phase write (FR4) |
| Release ledger (`specs/releases/`) | `ACTIVE.md` (`release: v0.8.0`, phase transitions); `v0.8.0/{SPEC,PLAN,TASKS,CLOSURE}.md` |
| Package version | `pyproject.toml` + `CHANGELOG.md` at ship, per the gitflow contract |
| Production code | **none** |
| Tests | **none** — no behavior delta; the enforcement this release depends on (SPEC-DOC-036) already exists and is already tested |

---

## 3. Execution order

```
T-080-01  commit definition content on feature/v0.8.0
   │        (trio + 2 audit disposition edits + memory atom)
   ▼
T-080-02  milestone (a): merge → develop · security review of origin/develop..develop · push
   │
   ▼
T-080-03  pre-archive verification  ← the irreversibility gate (18/18 rows, tokens, pointers)
   │
   ▼
T-080-04  git mv both audits into _archive/ under --dispositioned-v0.8.0 · commit
   │
   ▼
T-080-05  post-archive verification: specs doctor, SPEC-DOC-036 clean, evidence captured
   │
   ▼
T-080-06  CLOSURE.md · dispositions table · ACTIVE.md → ARCHIVED · release dir → _archive
   │        version bump + CHANGELOG entry
   ▼
T-080-07  milestone (b): merge → develop · security review · push · PR develop→main · CI green
```

Strictly serial. No sanctioned parallel pair: every task either consumes the previous
task's git state or gates the next task's irreversible step. Never two `[-]`.

---

## 4. Phases

### Phase 0 — DEFINITION (product-engineer, done at authoring)

Author `SPEC.md`, `PLAN.md`, `TASKS.md`; write both disposition sections into the audit
files; correct the governance memory atom; point `ACTIVE.md` at `v0.8.0` / `DEFINITION`.
Nothing is committed by the author — `product-engineer` has no shell.

### Phase 1 — Approval and milestone (a)

Operator approves the trio (`Draft` → `Aprovado`, three files). `ACTIVE.md` phase then
advances to `IMPLEMENTATION`. The definition content is committed (T-080-01) and milestone
(a) fires (T-080-02): merge into local `develop`, diff-based security review of
`origin/develop..develop`, push `develop` — in that order, per `dadaia-gitflow`.

### Phase 2 — Verify, then archive

T-080-03 verifies the disposition record is complete *before* anything becomes FROZEN:
12 rows in audit A, 6 in audit B, every row carrying a token from the canonical set and a
non-empty evidence cell; both `deferred` rows naming the inheriting backlog file; both
`superseded` rows naming their inheritor; both files carrying a SPEC-DOC-036-matching
pointer; `git diff` on the two audit files showing additions only inside the original
sections. Only then does T-080-04 move them.

### Phase 3 — Prove and close

T-080-05 re-runs `dadaia specs doctor` and captures stdout as CLOSURE evidence: no
SPEC-DOC-036 issue for either archived file, no new ERROR/WARNING attributable to this
release. T-080-06 writes `CLOSURE.md` (memory was already updated in DEFINITION — CLOSURE
*records* it, per the finalization order memory → CLOSURE → archive), flips `ACTIVE.md` to
`ARCHIVED` and then to the next release (or `release: none`), moves the release directory
to `specs/_archive/releases/v0.8.0/`, and carries the version bump + CHANGELOG entry.
T-080-07 ships: merge, security review, push, PR `develop` → `main`, CI green.

---

## 5. Validation plan

| # | What is validated | How | Evidence for CLOSURE |
|---|---|---|---|
| V1 | Disposition completeness, audit A | 12 rows F-01…F-12, one per audit finding, canonical token + non-empty evidence | verifier note + row count in CLOSURE |
| V2 | Disposition completeness, audit B | 6 rows W1…W6 + the explicit "dataset is evidence, not findings" statement | verifier note + row count |
| V3 | Historical record untouched | `git diff` of both audit files: zero deletions/modifications inside the original sections | diff summary (`--stat` + inspection) in CLOSURE |
| V4 | Inheritance is real | `specs/backlog/consumer-side-validation-round.md` and `specs/backlog/thin-wrapper-projected-scripts.md` exist and carry the inherited findings | path + status quoted in CLOSURE |
| V5 | Supersession is real | `context-alive-sweeps-unrelated-worktree-changes` present and open in `specs/bugs/bugs.jsonl` | `dadaia bugs status` line |
| V6 | Archive names the release | both `_archive` paths exist; `dadaia specs doctor` emits no SPEC-DOC-036 for them | doctor stdout, post-move |
| V7 | Nothing else regressed | `dadaia specs doctor` before and after; diff of the two runs | both stdouts in CLOSURE |
| V8 | Memory stays atomic | no changelog/history section added; `catalog.json` slug set unchanged (CAT-1 silent) | doctor stdout |

No pytest leg is claimed as evidence for this release's own scope: no production code
changes, so the suite proves nothing about it. The pre-push CI preflight still runs at each
push — that is the branch contract, not this release's validation.

---

## 6. Technical risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | A row is archived incomplete; `_archive/` is FROZEN and cannot be repaired in place | T-080-03 gates T-080-04; the verifier is `qa-engineer`, not the author |
| R2 | `git mv` performed as delete + create, losing history | The task names `git mv` literally; V3/A3.2 check `git log --follow` |
| R3 | The disposition wording drifts from the SPEC tables (two copies of the same text) | The SPEC tables are the normative source; T-080-03 compares the archived tables against SPEC FR1/FR2 row by row |
| R4 | A reader later concludes the two `deferred` findings were dropped | The audit's own disposition section names the inheriting backlog entry and quotes the required disposition |
| R5 | The closure sweep flips a backlog entry this release never picked | SPEC §4.6 and A5.3: the `## Dispositions` table states "no backlog entry and no bug picked"; the two inheritor entries stay `candidate` |
| R6 | Milestone (a) pushes before the trio is `Aprovado` | T-080-02 preconditions name all three `Aprovado` markers explicitly |

---

## 7. Rollback

Before T-080-04 the release is pure additive text: reverting the commits restores the
prior state exactly. After T-080-04 the audits are FROZEN in `_archive/`; a correction is
then a *new* record — an amendment noted in `CLOSURE.md` and, if it changes a disposition,
a new disposing release. This asymmetry is the reason T-080-03 exists.
