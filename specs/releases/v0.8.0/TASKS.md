# TASKS — Release v0.8.0 — Audit disposition

**Status:** Aprovado
**Release ID:** v0.8.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.8.0/SPEC.md`
**Source PLAN:** `specs/releases/v0.8.0/PLAN.md`
**Branch:** `feature/v0.8.0` (cut from `develop` at `d3e05d19`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release (no `alpha-N`; no implementation increment to close)

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **No production code.** No task in this release may modify a file under
  `dadaia_workspace/`. A task that finds itself needing to is a scope error: stop and
  raise it with the operator.
- **`product-engineer` has no shell.** Every task marked **[git]** is executed by the
  dispatcher or `software-engineer`. `product-engineer` authors text only.
- **The archive is irreversible.** `specs/audits/_archive/` is FROZEN (law §3). T-080-04
  may not start until T-080-03 is `[x]`. A table archived incomplete cannot be repaired
  in place — it would require a new disposing release.
- **Additive-only on the audit files.** Never rewrite, reorder or "clean up" the original
  audit text. The disposition is a new section plus frontmatter markers. `git diff` on
  those two files must show additions only inside the original sections.
- **Strictly serial.** No sanctioned parallel pair. Never two `[-]` in this file.
- **A group of completed work is one commit** — not one commit per file.
- **Reservation is observable.** Flip `[ ]` → `[-]` and commit `chore(tasks): start <id>`
  before the work, per `dadaia-task-manager`.

---

- [x] **T-080-01 — [git] Commit the definition content on `feature/v0.8.0`**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-080-01): v0.8.0 definition — audit dispositions, trio, governance memory`

**Preconditions:** `SPEC.md`, `PLAN.md` and `TASKS.md` all carry `**Status:** Aprovado`
(operator). Working tree on `feature/v0.8.0`.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`,
`specs/releases/v0.8.0/SPEC.md`,
`specs/releases/v0.8.0/PLAN.md`,
`specs/releases/v0.8.0/TASKS.md`,
`specs/audits/2026-07-15-consumer-dadaia-integration.md`,
`specs/audits/2026-07-18-architecture-resilience-review.md`,
`specs/memory/product/sdd/sdd-bug-backlog-governance.md`.

**Description:** Stage exactly these seven paths — never `-A` over the shared tree — and
commit. Also set `ACTIVE.md` phase from `DEFINITION` to `IMPLEMENTATION` in the same commit
(the trio is approved; implementers are unblocked).

**Done criterion:** one commit containing exactly those paths; `git status` clean for them;
`ACTIVE.md` reads `release: v0.8.0` / `phase: IMPLEMENTATION`.

**Parallelism:** none — first task.

---

- [x] **T-080-02 — [git] Milestone (a): merge, security review, push**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-080-01 `[x]`. All three of SPEC/PLAN/TASKS `Aprovado`.

**Write set:** git refs only (`develop`), plus the security-reviewer handoff under
`.dadaia/handoff/dadaia-workspace/`.

**Description:** Per `dadaia-gitflow` milestone (a), in this order: merge
`feature/v0.8.0` into local `develop`; run a **diff-based** `security-reviewer` review of
`origin/develop..develop`; push `develop`. The push gate requires an APPROVED
`security-reviewer` handoff keyed to the pushed tip, plus the CI preflight.

**Done criterion:** `develop` pushed; APPROVED handoff exists covering the pushed delta;
CI green.

**Parallelism:** none.

---

- [x] **T-080-03 — Pre-archive verification (the irreversibility gate)**

**Owner role:** qa-engineer · **Commit:** none (evidence only; handoff/report)

**Preconditions:** T-080-02 `[x]`. **Must complete before T-080-04 starts.**

**Write set:** read-only over `specs/`; output to
`.dadaia/handoff/dadaia-workspace/` (and `.dadaia/tmp/qa-engineer/<YYYYMMDD>/` for captures).

**Description:** Verify, against `specs/releases/v0.8.0/SPEC.md` FR1/FR2 row by row:

1. `specs/audits/2026-07-15-consumer-dadaia-integration.md` carries a
   `## Disposition — release v0.8.0` section with **exactly 12 rows** (F-01…F-12), one per
   audit finding, each token in {`fixed`, `superseded`, `deferred`, `rejected`} and each
   evidence cell non-empty (A1.1).
2. `specs/audits/2026-07-18-architecture-resilience-review.md` carries the same section with
   **exactly 6 rows** (W1…W6) plus the explicit statement that §1's 25-row dataset is
   evidence, not findings (A2.1, A2.2).
3. Both files carry a disposing-release pointer matching SPEC-DOC-036 — frontmatter
   `disposing_release: v0.8.0` and a `**Disposition:** v0.8.0 …` line (A1.3, A2.4).
4. `git diff` on both files shows **additions only** inside the original sections — zero
   deletions or modifications of pre-existing audit text (A1.2, A2.3).
5. The inheritors exist and carry what was handed to them:
   `specs/backlog/consumer-side-validation-round.md` (findings #3/#6 as acceptance criteria),
   `specs/backlog/thin-wrapper-projected-scripts.md` (W6, corrected direction) — A1.4, A2.5.
6. `context-alive-sweeps-unrelated-worktree-changes` is present and **open** in
   `specs/bugs/bugs.jsonl` (A1.5) — the F-10 supersession target.
7. `dadaia specs doctor` run and stdout captured (the **before** half of V7/A5.1).

**Done criterion:** a handoff with verdict APPROVED enumerating all seven checks; any
failure blocks T-080-04 and returns the defect to `product-engineer` for repair (still
editable at this point).

**Parallelism:** none.

---

- [ ] **T-080-04 — [git] Archive both audits under the `--dispositioned-v0.8.0` name**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-080-04): archive both audits dispositioned by v0.8.0`

**Preconditions:** T-080-03 `[x]` with an APPROVED verdict. **Irreversible step.**

**Write set:** path moves only —

```bash
git mv specs/audits/2026-07-15-consumer-dadaia-integration.md \
       specs/audits/_archive/2026-07-15-consumer-dadaia-integration--dispositioned-v0.8.0.md
git mv specs/audits/2026-07-18-architecture-resilience-review.md \
       specs/audits/_archive/2026-07-18-architecture-resilience-review--dispositioned-v0.8.0.md
```

**Description:** Move with `git mv` (never delete + recreate — history must follow, A3.2).
No content edit in this task: the files are final as of T-080-03. Commit the two moves as
one commit.

**Done criterion:** both `_archive` paths exist; neither audit remains loose in
`specs/audits/`; `git log --follow` resolves each pre-move path (A3.1, A3.2).

**Parallelism:** none.

---

- [ ] **T-080-05 — Post-archive verification and evidence capture**

**Owner role:** qa-engineer · **Commit:** none (evidence only; handoff)

**Preconditions:** T-080-04 `[x]`.

**Write set:** read-only over `specs/`; output to `.dadaia/handoff/dadaia-workspace/` and
`.dadaia/tmp/qa-engineer/<YYYYMMDD>/`.

**Description:** Run `dadaia specs doctor` and capture stdout (the **after** half of
V7/A5.1). Assert: no SPEC-DOC-036 issue for either archived file (A3.3); no new
ERROR/WARNING attributable to this release when diffed against the T-080-03 capture (A5.2);
memory checks (LINT-1, CAT-1, SPEC-DOC-008) unchanged (A4.3).

**Done criterion:** both stdout captures handed to `product-engineer` for CLOSURE, with the
before/after diff summarized in the handoff.

**Parallelism:** none.

---

- [ ] **T-080-06 — CLOSURE, memory record, release archive, version bump**

**Owner role:** product-engineer (text) + software-engineer/dispatcher (**[git]** steps)
· **Commit:** `docs(T-080-06): close release v0.8.0`

**Preconditions:** T-080-05 `[x]`. `ACTIVE.md` phase set to `CLOSURE` before writing.

**Write set:** `specs/releases/v0.8.0/CLOSURE.md` (new), `specs/releases/ACTIVE.md`,
`pyproject.toml` (version), `CHANGELOG.md`, plus the release-directory move.

**Description:** In the finalization order **memory → CLOSURE → archive**:

1. Memory was already written in DEFINITION (FR4) — CLOSURE *records* it; re-verify the
   atom still matches A4.1/A4.2 and list it under `## Memory updates`.
2. Write `CLOSURE.md` per `dadaia-release-closure`: summary, tasks + commit SHAs,
   validations V1–V8 with evidence, drifts, memory updates, and a `## Dispositions` table
   whose rows are the **two audits** (kind `audit`, terminal status
   `ARCHIVED — dispositioned v0.8.0`), plus the explicit statement that **no backlog entry
   and no bug was picked** by this release, so no backlog/bug status is flipped (A5.3).
   Record as closure observations: the stale live release dirs `specs/releases/v0.2.6/` and
   `specs/releases/v0.2.9/`, and the dangling `panel-runtime-reliability` pointer in the bug
   ledger — both routed to the PM, neither fixed here.
3. **[git]** `git mv specs/releases/v0.8.0 specs/_archive/releases/v0.8.0`; set `ACTIVE.md`
   to the next release or `release: none` / `phase: none`.
4. **[git]** Bump `pyproject.toml` version and add the `CHANGELOG.md` entry per the gitflow
   contract.

**Done criterion:** `CLOSURE.md` complete under `specs/_archive/releases/v0.8.0/`;
`ACTIVE.md` no longer points at `v0.8.0`; `dadaia specs doctor` green.

**Parallelism:** none.

---

- [ ] **T-080-07 — [git] Milestone (b): ship**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit + PR

**Preconditions:** T-080-06 `[x]`.

**Write set:** git refs only, plus the security-reviewer handoff.

**Description:** Per `dadaia-gitflow` milestone (b), in order: merge `feature/v0.8.0` into
local `develop`; diff-based `security-reviewer` review of `origin/develop..develop`; push
`develop`; open PR `develop` → `main`; watch CI until every job is green; merge.

**Done criterion:** PR merged to `main`; CI green; `feature/v0.8.0` no longer needed.

**Parallelism:** none — last task.
