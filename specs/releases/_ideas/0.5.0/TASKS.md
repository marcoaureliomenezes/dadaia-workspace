# TASKS — Release 0.5.0 — governance, lineage and audits

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/_ideas/0.5.0/SPEC.md`
**Source PLAN:** `specs/releases/_ideas/0.5.0/PLAN.md`
**Location:** `specs/releases/_ideas/0.5.0/` — a future-release Draft. **No task below is
reservable while this file lives here.** Reservation begins at promotion (T-050-01).
**Branch (at promotion):** `feature/0.5.0`, cut from `main` at the shipped `v0.4.5`
(SPEC AS-5 — this supersedes the `feature/0.4.6` cut named in `specs/releases/v0.4.5/TASKS.md`
T-045-41; that file is not edited by this Draft).
**Segments:** `S1 … S4` — internal work boundaries on `feature/0.5.0`, each closed by a
`qa-engineer` review **committed on the branch**: no merge, no PR, no `rc` burned (SPEC D-J).
**Candidates:** `rc-1 … rc-N`. `rc-1` burns when the whole scope is implemented, validated,
gate-green and QA-closed, and is merged into `develop`; `rc-2 … rc-N` are adjustment rounds on
that same scope found by testing the merged `develop`; the **final `rc`** carries memory →
closure → archive and ships. If nothing is found, the final `rc` **is** `rc-1`.

This file is the single marker surface for all of it (SPEC D-E); the blocks below are the
segments and the lane. The live release carries no `segment:` line.

## Task status markers

- `[ ]` OPEN · `[-]` IN PROGRESS · `[x]` DONE

## Segment and candidate map

**Ids are in execution order** — nothing below runs out of numeric sequence.

| Block | Tasks | Contents | Gate |
|---|---|---|---|
| W0 | T-050-01 … 03 | promotion + definition commit + definition PR + baseline captures | definition PR merged into `develop`; APPROVED verdict on its head sha |
| `S1` | T-050-04 … 15 | the v6 canon and the historical ledger rewrite (FR1–FR6) | `qa-engineer` review **committed** + the `software-architect` **AR-1** ruling |
| `S2` | T-050-16 … 22 | lineage, commit shapes, hooks de-slop, the validated map (FR7–FR12) | `qa-engineer` review committed |
| `S3` | T-050-23 … 27 | the audit canon and its dry run (FR13–FR16) | `qa-engineer` review committed + the dry-run artifact satisfying A16.2 |
| `S4` | T-050-28 … 33 | memory two-tier, principles, ADRs (FR17–FR21) | `qa-engineer` review committed + **operator** ADR decisions (FR20) |
| scope complete | T-050-34 … 36 | invariants measured → six-axis review → security review + QA release verdict | the trio APPROVED on the same commit |
| `rc-1` | T-050-37 | PR `feature/0.5.0` → `develop` | merged, CI green |
| `rc-2 … rc-N` | T-050-38 | adjustment rounds on this scope | one QA close + one merge per round |
| final `rc` | T-050-39 … 43 | memory → closure record → archive → version bump + merge → ship | full trio still green, then the PR to `main` |

Order across the lane is fixed: **review → closure → archive → ship**. The six-axis review
runs on a **thawed** tree, before `rc-1` and again over any later `rc` delta — always before
the archive move.

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]**, **[shell]** or
  **[operator]** is executed by the dispatcher, `software-engineer`, `ai-engineer`,
  `qa-engineer`, `project-auditor` or the operator. `product-engineer` authors text only.
- **Shell-less reservation obligation.** When the dispatcher relays work for a shell-less
  sub-agent it commits that sub-agent's `[ ]`→`[-]` flip **before** relaying the next item —
  never batched. Applies to T-050-28, T-050-32, T-050-39 and T-050-40.
- **Reservation is observable.** Flip `[ ]`→`[-]` and commit `chore(tasks): start <id>` before
  the work (`dadaia-task-manager`). **One `[-]` at a time — this release declares no parallel
  pair.**
- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN**, on the executed path.
- **The D15 posture is an acceptance.** No task may add a blocking CLI exit or a hook block.
  A diff that adds a branch, a flag, a second code path, a cross-feature reach-in or a new
  side effect is rejected, whatever the test result. Every review verdict states the
  **bug-surface delta** of the feature it touched, with bug-history evidence.
- **Retirement needs its replacement first** — `expand → switch → contract` (SPEC D-F). No
  reader, writer, file or rule is deleted before its replacement exists and is green.
- **Nothing derived is written by hand.** Every sha in every record comes from the FR3
  derivation, through the one resolver seam (FR8).
- **Nothing inferred is presented as declared.** Provenance markers are mandatory (SPEC D-A).
- **Test intent at birth.** `Intent: CONTRACT — 0.5.0 <A-id>` or `Intent: SENTINEL — <seam>`.
  **Zero new `tests/e2e/**`** without a named `qa-engineer` exception in that segment's QA
  artifact.
- **Never prune to go green.** A deletion, skip or disable is a `qa-engineer` verdict with
  evidence, executed by `software-engineer`.
- **Lane discipline.** `ai-engineer` performs every skill/persona/rule/projected-asset edit;
  `software-engineer` every production-code, CI-YAML and test edit; `project-manager` any
  backlog-file mechanics; `project-auditor` only `specs/audits/**`; `product-engineer` only
  release specs and memory; the **operator** alone flips an ADR to `accepted` and alone runs
  the destructive deletion.
- **No new scope in an `rc`.** An `rc-N ≥ 2` carries only fixes and adjustments **on this
  release's scope** (SPEC A22.8).
- **A completed task group is one commit** — stage exactly the task's write set, never `-A`.
- **No home-absolute path, operator email literal, IP, hostname, private name or denylisted
  term** enters any authored file, including migration reports, QA artifacts and the audit
  folder. Self-scan before every commit.
- **Measurements** (V1–V19, SPEC §6) are captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.

## Acceptance and evidence map

| Task | FR | Acceptance ids | Evidence |
|---|---|---|---|
| T-050-01 | — | — | promotion commit sha; six subsections purged from `## ACTIVE`; `RELEASE.jsonl`/`ACTIVE.md` set to DEFINITION |
| T-050-02 | — | SPEC §7 | definition PR merged; APPROVED verdict on the head sha; the `defined` milestone |
| T-050-03 | — | AS-9 | V1, V2, V6, V11, V12 baseline captures |
| T-050-04 | FR2/FR3 | A2.5 | the `software-architect` **AR-1** ruling, verbatim |
| T-050-05 | FR1 | A1.1–A1.4 | scaffold fixture; TREE-8 WARN fixture + exit-code fixture; `--recipe` output; double-`upgrade` byte comparison |
| T-050-06 | FR1 | A1.5, A1.6 | this repo migrated; `specs doctor` 0 errors; the `gate_policy.py` diff |
| T-050-07 | FR2 | A2.1, A2.2 | `bug-record-v1.schema.json`; immutability + in-place-rewrite contract tests |
| T-050-08 | FR2 | A2.3, A2.4 | WARN-with-unchanged-exit fixture; the event reader deleted after the switch |
| T-050-09 | FR3 | A3.4 (unit) | the derivation function + its fixture-repo tests, including the double-run |
| T-050-10 | FR3 | A3.1–A3.8 | V4, V5; the migration report; the no-fabrication scan; `archive.jsonl` byte-identical |
| T-050-11 | FR4 | A4.1, A4.2, A4.4, A4.5 | `RELEASE.jsonl`; gate fixture with no `ACTIVE.md`; milestone immutability test |
| T-050-12 | FR4 | A4.3, A4.6 | V7; `releases_histo.jsonl`; every sha `git cat-file -e` green |
| T-050-13 | FR5 | A5.1–A5.4 | `backlog_histo.jsonl`; BL-DUP deleted; the exit fixture |
| T-050-14 | FR6 | A6.1–A6.5 | V8; the pushed tag; the deletion commit with the FROZEN repoint |
| T-050-15 | all `S1` | A1–A6 ids | `qa-engineer` artifact committed |
| T-050-16 | FR7 | A7.1–A7.5 | `dd-diagnose` + `LINEAGE.md`; the coverage table; zero `cli/`+`hooks/` diff |
| T-050-17 | FR8 | A8.1–A8.4 | the duplicate scan; the resolver contract test on ≥ 20 records |
| T-050-18 | FR9 | A9.1–A9.5 | V9, V10; the executed-path pre-commit fixture; zero-hit greps |
| T-050-19 | FR10 | A10.1–A10.5 | V17; five mutation fixtures; `rules-skills-map.json` retired |
| T-050-20 | FR11 | A11.1–A11.4 | V12 with per-section attribution; `public doctor` green |
| T-050-21 | FR12 | A12.1–A12.5 | V11; zero-hit grep for `dd-bug-fix`; the coverage table |
| T-050-22 | all `S2` | A7–A12 ids | `qa-engineer` artifact committed |
| T-050-23 | FR13 | A13.1–A13.4 | the finding schema; the persona-allowlist refusal fixture |
| T-050-24 | FR14 | A14.1–A14.5 | the rewritten skill + 4 siblings; the executable window recipe |
| T-050-25 | FR15 | A15.1–A15.3 | zero-hit grep on the regex path; two doctor fixtures |
| T-050-26 | FR16 | A16.1–A16.6 | V16; the committed audit folder; the four chains named with evidence |
| T-050-27 | all `S3` | A13–A16 ids | `qa-engineer` artifact committed |
| T-050-28 | FR17 | A17.1–A17.5 | the two-part memory trio; the coverage table |
| T-050-29 | FR18 | A18.1–A18.4 | V13, V14; the contract test on the contract count |
| T-050-30 | FR19 | A19.1–A19.4 | `specs/ADRs/` + the proposed inventory ADRs; the numbering test |
| T-050-31 | FR20 | A20.1–A20.3 | one `docs(adr): accept …` commit per accepted ADR, carrying its Part-1 hunk |
| T-050-32 | FR21 | A21.1–A21.3 | V15; the coverage table; the duplicate scan |
| T-050-33 | all `S4` | A17–A21 ids | `qa-engineer` artifact committed |
| T-050-34 | FR22 | A22.1–A22.7 | V18, V19; gate output; per-FR LOC direction |
| T-050-35 | all | A22.1–A22.6 | `code-reviewer` APPROVED on a **thawed** tree, with the bug-surface verdict per feature |
| T-050-36 | all | — | `security-reviewer` APPROVED + `qa-engineer` release verdict, same sha |
| T-050-37 | — | — | **`rc-1`**: PR merged; CI green; verdict handoff for the PR head sha |
| T-050-38 | — | A22.8 | **`rc-2 … rc-N`**: per round — the finding on `develop`, its fix, QA close, delta reviews, merge |
| T-050-39 | all | SPEC §5 | memory diff in the Part 1 / Part 2 shape; `specs doctor` 0 errors |
| T-050-40 | all picked | A22.7 + closure obligations | the closure record; sweeps complete; the `rc` ledger |
| T-050-41 | — | — | `git mv` into `specs/releases/_archive/0.5.0/` |
| T-050-42 | — | — | `0.5.0` bump; final-`rc` PR merged; CI green; the `implemented` milestone |
| T-050-43 | — | AS-6 | PR to `main` merged; the `shipped` milestone with its sha; branch deleted and the next cut |

---

## W0 — promotion and definition

- [ ] **T-050-01 — [git] Promotion + definition commit**

**Owner role:** dispatcher (+ `project-manager` for the backlog mechanics) · **Commit:**
`docs(specs): 0.5.0 definition — governance, lineage and audits (Aprovado)`

**Preconditions:** `v0.4.5` archived and shipped; `feature/0.5.0` cut from `main` at that
commit (AS-5); SPEC, PLAN and TASKS reviewed and carrying `**Status:** Aprovado`.

**Write set (staging only — content authored by `product-engineer` / `project-manager`):**
`specs/releases/_ideas/0.5.0/` → `specs/releases/0.5.0/` (a `git mv`),
`specs/releases/ACTIVE.md`, `specs/backlog/BACKLOG.md` (purge-on-pick: the six `## ACTIVE`
subsections `specs-canon-v6`, `entity-behavior-map`, `bug-lineage-and-commit-discipline`,
`audit-canon-v1`, `memory-two-tier-principles`, `dd-diagnose` removed and their
`CONSUMED · 0.5.0` records added).

**Description:** The pick and the SPEC ride **one** commit (`DADAIA.md` §5). Re-read every
write-set path in this file against the tree **before** editing — `v0.4.5` moved files, and a
stale path in a task is how a release drifts. Replace the SPEC's
`**Consumes (declared at promotion, NOT executed by this Draft):**` header with the
machine-readable `**Consumes:**` key in this same commit — that is the moment the declaration
becomes live. `ACTIVE.md` reads `release: 0.5.0` / `phase: DEFINITION`; the phase advances in
T-050-02, not here. **No bug is picked** (AS-4).

**Done criterion:** one commit with exactly those paths; the six subsections gone from
`## ACTIVE`; `backlog doctor` and `specs doctor` clean.

**Parallelism:** none — first task.

---

- [ ] **T-050-02 — [git] Milestone (a): push and open the definition PR → `develop`**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** the phase flip, then git refs

**Preconditions:** T-050-01 `[x]`.

**Write set:** `specs/releases/ACTIVE.md` (`DEFINITION` → `IMPLEMENTATION`), then git refs and
the security handoff.

**Description:** Push `feature/0.5.0` (local CI preflight + name validation), run a diff-based
`security-reviewer` review of the delta, open the PR to `develop` with the APPROVED verdict
covering the PR head sha, watch CI to green, merge. This is the definition PR named by
`DADAIA.md` §4 — it **burns no `rc`**. Record its sha and PR number; they become the
`defined` milestone the moment `RELEASE.jsonl` exists (T-050-11 back-fills it for this
release).

**Done criterion:** definition PR merged; CI green; `ACTIVE.md` reads `IMPLEMENTATION`; the
sha and PR number captured for the `defined` milestone.

**Parallelism:** none.

---

- [ ] **T-050-03 — [shell] Baselines, before anything changes**

**Owner role:** software-engineer (+ `ai-engineer` for V11/V12) · **Commit:** the capture
reference only

**Preconditions:** T-050-02 `[x]`.

**Write set:** none in the repo — captures under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.

**Description:** `git fetch --all --tags` first, then capture **V6** (`git log --all
--no-merges --format=%H -- specs/bugs/ | wc -l` and `git tag -l 'archive/*' | wc -l`) — the
migration's ref scope is a validation, not an assumption (AS-9); **V1**/**V2** (the doctor
suite and the preflight, green); **V11** (AI-surface line count over
`dadaia_workspace/public/{agents,skills,data,entities}/**`); **V12** (the always-on token
count, using the v0.4.5 measurement recipe). Everything downstream is a delta against these.

**Done criterion:** V1, V2, V6, V11, V12 captured with their exact commands recorded; the
ledger-commit count is **≥ 295** and the `archive/*` tag count is recorded beside it.

**Parallelism:** none.

---

## Segment `S1` — the v6 canon and the historical ledger rewrite

- [ ] **T-050-04 — AR-1: the record model and the v5 boundary adapter, ruled**

**Owner role:** software-architect · **Commit:** `docs(T-050-04): AR-1 ruling — bug record
model and the v5 adapter boundary`

**Preconditions:** T-050-03 `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S1-AR1-ruling.md`.

**Description:** Rule, before any code moves, on: (a) where the v5→v6 decoding lives so that
**no historical shape leaks into the bugs feature** (SPEC A2.5) — the intended answer is one
boundary adapter owned by the migration, deletable when the migration retires; (b) whether the
FR2 record-update seam in `dadaia_workspace/infrastructure/jsonl_bug_store.py` may serve bugs,
findings **and** the backlog histo without becoming a cross-cutting helper that hides coupling
(SPEC A13.4); (c) the layer placement of the FR3 derivation, which must read git without
`features/**` importing `infrastructure` or `subprocess` directly. If the ruling overturns any
of these, the alternative and its reason are recorded here and the affected acceptance ids are
re-read before implementation.

**Done criterion:** a ruling recorded verbatim, before T-050-07 starts.

**Parallelism:** none.

---

- [ ] **T-050-05 — FR1: the v6 canon in the scaffold and the doctor**

**Owner role:** software-engineer · **Commit:** `feat(T-050-05): specs pattern v6 — canon
tree, TREE-8 and specs doctor --recipe`

**Preconditions:** T-050-04 `[x]`.

**Write set:** `dadaia_workspace/features/specs/scaffolder.py`,
`dadaia_workspace/features/specs/doctor.py`,
`dadaia_workspace/features/specs/doctor_structural.py`,
`dadaia_workspace/cli/commands/specs.py`, `dadaia_workspace/public/scaffold/**` (the v6 tree;
`backlog/README.md`, `bugs/README.md`, `releases/README.md`, `audits/README.md` and
`assets/.gitkeep` retire; per-area `AGENTS.md` and `ADRs/` added), `tests/**`.

**Description:** `specs_pattern_version` 5 → 6. The scaffold emits the canon root exactly
(`backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md`,
`AGENTS.md`), `BUGS.jsonl`, a `RELEASE.jsonl`-ready `releases/` with `_ideas/` and `_archive/`,
scoped `AGENTS.md` per area, **zero** `README.md` and **zero** `assets/`. The doctor gains
TREE-8 "nothing beyond canon" and `--recipe`; `specs upgrade` automates the safe renames.
**Compliance is WARN-only** — a fixture asserts the exit code is unchanged, because a canon
that blocks is the slop this release exists to remove (D15).

**Done criterion:** A1.1–A1.4; the double-`upgrade` byte comparison green.

**Parallelism:** none.

---

- [ ] **T-050-06 — FR1: migrate this repository's own `specs/` to v6**

**Owner role:** software-engineer · **Commit:** `refactor(T-050-06): migrate specs/ to canon
v6`

**Preconditions:** T-050-05 `[x]`.

**Write set:** `specs/**` (the renames: `specs/memory/architecture.md` → `ARCHITECTURE.md`,
`specs/memory/tech-stack.md` → `TECHSTACK.md`, `specs/memory/quality-assurance.md` →
`QUALITY.md`; `specs/releases/README.md`, `specs/bugs/README.md`, `specs/audits/README.md`
retire in their owning FRs), `dadaia_workspace/features/spec_context/gate_policy.py`,
`dadaia_workspace/features/specs/memory_lint.py`, `tests/**`.

**Description:** Perform the case-only renames with an explicit **two-step `git mv`** so a
case-insensitive filesystem cannot silently no-op them. Repoint the memory lint and every
in-repo reference. The gate's FROZEN class is repointed in T-050-14, not here — this task must
not leave a window where FROZEN points at nothing.

**Done criterion:** A1.5, A1.6; `dadaia specs doctor` **0 errors**; the `gate_policy.py` diff
flat or net-negative.

**Parallelism:** none.

---

- [ ] **T-050-07 — FR2 (expand): the bug record model**

**Owner role:** software-engineer · **Commit:** `feat(T-050-07): one record per bug —
bug-record-v1 with immutable core and mutable governance`

**Preconditions:** T-050-06 `[x]`; the AR-1 ruling recorded.

**Write set:** `dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json` (new),
`dadaia_workspace/core/models/bugs.py`,
`dadaia_workspace/infrastructure/jsonl_bug_store.py`, `tests/**`.

**Description:** Author the record model exactly as SPEC FR2 states it, with the
mutable/immutable split documented **per property in the schema**, not in prose elsewhere. Add
the in-place record-update seam (one line rewritten, every other byte identical). **Nothing is
deleted in this task** — `bug-event-v1.schema.json` and the event reader stay until T-050-08
(D-F).

**Done criterion:** A2.1, A2.2; the immutability and in-place-rewrite contract tests green.

**Parallelism:** none.

---

- [ ] **T-050-08 — FR2 (switch + contract): every consumer reads records; the event fold dies**

**Owner role:** software-engineer · **Commit:** `refactor(T-050-08): route bugs through the
record model and delete the event fold`

**Preconditions:** T-050-07 `[x]`.

**Write set:** `dadaia_workspace/features/bugs/service.py`,
`dadaia_workspace/cli/commands/bugs.py`,
`dadaia_workspace/public/schemas/bugs/bug-event-v1.schema.json` (deleted),
`dadaia_workspace/features/specs/doctor.py` (the bug lane), `tests/**`.

**Description:** Switch `bugs status`/`bugs stats`/the doctor lane to the record reader, then
delete the event fold and its terminal/non-terminal state machine. The coherence checker
becomes a **WARN** surfaced by `dadaia bugs status` and the doctor with the **exit code
unchanged** — proven by a fixture, because a coherence check that blocks is a new blocker
(D15). The `picked` and `archived` event kinds disappear as `status` values.

**Done criterion:** A2.3, A2.4; the CLI-output-stability fixtures green untouched for every
input that succeeds today.

**Parallelism:** none.

---

- [ ] **T-050-09 — FR3 (build): the commit derivation, unit-tested on a fixture repo**

**Owner role:** software-engineer · **Commit:** `feat(T-050-09): derive registration and
resolution commits in one pass over the ledger history`

**Preconditions:** T-050-08 `[x]`.

**Write set:** the migration module (placement per the AR-1 ruling; default
`dadaia_workspace/features/bugs/`), `tests/**`.

**Description:** Implement SPEC FR3's algorithm and nothing else: `git log --all --no-merges
--reverse --date-order -- specs/bugs/`, one chronological pass, added lines only, parsed
through the v5/v6 boundary adapter, **first add wins**, granularity marker computed from
(number of bug lines added in that commit, whether the commit touches any non-`specs/` file).
Ties across equal dates break by topological order then sha, and the tie-break used is
recorded. Test it on a **synthetic fixture repository** with a hand-built history containing:
a single-bug registration; a 3-bug squash; a ledger-only resolution; a line re-added by a later
squash; and a bug whose line is never added. **Do not run it on the real ledger in this task.**

**Done criterion:** every fixture case produces the expected sha and marker; running the
derivation twice on the fixture repo yields identical output.

**Parallelism:** none.

---

- [ ] **T-050-10 — FR3 (run): migrate the 490 historical records**

**Owner role:** software-engineer · **Commit:** `refactor(T-050-10): migrate 490 bug records
to BUGS.jsonl with derived commit provenance`

**Preconditions:** T-050-09 `[x]`; V6 captured (T-050-03).

**Write set:** `specs/bugs/bugs.jsonl` (retired) → `specs/bugs/BUGS.jsonl` (new),
`specs/bugs/_archive/bugs_histo.jsonl` (new, empty), `specs/bugs/README.md` (retires into
`specs/bugs/AGENTS.md`, authored in T-050-16), the migration report under
`.dadaia/tmp/software-engineer/<YYYYMMDD>/`.

**Description:** Run the migration. Populate `cause` **only** where the v5 `evidence_diff` /
`notes` text literally states one; populate `caused_by` **only** where a record's text names
another existing bug id, marked `lineage_source: "text-reference"`; everything else stays
`null` — historical `caused_by` is never `"none"` (AS-2). `specs/bugs/_archive/archive.jsonl`
is **not touched** (AS-3). Then run the migration a second time and prove the output is
byte-identical (V5). Capture **V4** and check every count against SPEC A3.2/A3.3 — a count
below the measured ground truth means the ref scope was wrong, not that the ground truth
moved.

**Done criterion:** A3.1–A3.8; V4 and V5 captured; the report committed by reference; this
task is a **separate commit** from T-050-07's schema change.

**Parallelism:** none.

---

- [ ] **T-050-11 — FR4: `RELEASE.jsonl` replaces `ACTIVE.md`**

**Owner role:** software-engineer · **Commit:** `feat(T-050-11): RELEASE.jsonl milestones
replace ACTIVE.md`

**Preconditions:** T-050-10 `[x]`.

**Write set:** `dadaia_workspace/public/schemas/releases/release-event-v1.schema.json` (new),
`dadaia_workspace/features/specs/doctor_release.py`,
`dadaia_workspace/features/spec_context/gate_policy.py`,
`dadaia_workspace/hooks/sdd_gate.py`, `specs/releases/0.5.0/RELEASE.jsonl` (new — back-filled
with this release's own `created`, `spec_status` and `defined` records from T-050-01/02),
`specs/releases/ACTIVE.md` (deleted at the contract step), `specs/releases/README.md`
(retires), `tests/**`.

**Description:** `expand → switch → contract`: write and read `RELEASE.jsonl` alongside
`ACTIVE.md` for at least one green commit, then delete `ACTIVE.md` with **no fallback branch
left behind** — a fixture with no `ACTIVE.md` present proves the gate resolves the MEMORY
phase from the fold alone. The three sha-bearing milestones are immutable; a contract test
refuses a rewrite.

**Done criterion:** A4.1, A4.2, A4.4, A4.5.

**Parallelism:** none.

---

- [ ] **T-050-12 — FR4: back-fill the archived releases' milestone shas**

**Owner role:** software-engineer · **Commit:** `feat(T-050-12): back-fill archived release
milestones into releases_histo.jsonl`

**Preconditions:** T-050-11 `[x]`. **Must complete before T-050-14** — it reads the archive
that task deletes.

**Write set:** `specs/releases/_archive/releases_histo.jsonl` (new), the back-fill report under
`.dadaia/tmp/software-engineer/<YYYYMMDD>/`.

**Description:** For every release under `specs/_archive/releases/`, read its `CLOSURE.md`
tables and emit one milestone block: `defined` / `implemented` / `shipped` with `sha` and `pr`
**where the table gives them** and `null` where it does not — never a guess (SPEC D-G, A4.3).
Verify every non-null sha with `git cat-file -e`. Capture **V7**.

**Done criterion:** A4.3, A4.6; V7 captured; the found/null split recorded per release.

**Parallelism:** none.

---

- [ ] **T-050-13 — FR5: `BACKLOG.md` becomes a live photo**

**Owner role:** software-engineer (+ `project-manager` for the entry text) · **Commit:**
`refactor(T-050-13): live-photo BACKLOG.md with backlog_histo.jsonl`

**Preconditions:** T-050-12 `[x]`.

**Write set:** `specs/backlog/BACKLOG.md` (the `## LEDGER` section retires),
`specs/backlog/_archive/backlog_histo.jsonl` (new),
`dadaia_workspace/features/specs/doctor_governance.py` (BL-DUP deleted),
`dadaia_workspace/public/scaffold/backlog/**`, `tests/**`.

**Description:** Migrate every `## LEDGER` line into a histo record carrying the full entry
snapshot where the entry text is recoverable and `entry_md: null` + a note where it is not;
report the counts. `BL-DUP` is **deleted**, not disabled — with one line per exit in an
append-only file, a duplicate ledger line is structurally impossible. Legacy
`specs/backlog/_archive/*.md` stay byte-identical.

**Done criterion:** A5.1–A5.4; `backlog doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-14 — [operator] FR6: tag, then delete root `specs/_archive/`**

**Owner role:** **operator** (executes) + dispatcher (prepares and verifies) · **Commit:**
`chore(T-050-14): delete root specs/_archive after tagging (operator ruling 2026-08-23)`

**Preconditions:** T-050-13 `[x]`; **T-050-10 and T-050-12 complete and committed** — nothing
this task deletes may still be needed.

**Write set:** `specs/_archive/**` (deleted),
`dadaia_workspace/features/spec_context/gate_policy.py` (FROZEN repointed to the per-area
`*/_archive/` paths), `dadaia_workspace/hooks/sdd_gate.py`, `tests/**`.

**Description:** **Destructive, operator-present, one commit.** First create **and push**
`archive/specs-archive-<YYYYMMDD>` at the commit immediately preceding the deletion, then
demonstrate `git show <tag>:specs/_archive/releases/v0.4.4/CLOSURE.md | head` succeeds and
capture it (**V8**). Only then delete, repointing FROZEN in the **same** commit so there is
never a window where the class points at nothing. **No `archive/*` tag is deleted by this
release** — the 50 existing tags are the only path to 220 of the 295 ledger commits (AS-9).

**Done criterion:** A6.1–A6.5; V8 captured; the tag pushed and verified before the deletion.

**Parallelism:** none.

---

- [ ] **T-050-15 — `S1` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-15): S1 QA close`

**Preconditions:** T-050-04 … 14 all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S1-qa-close.md`.

**Description:** Evidence every `S1` acceptance id. Two questions this segment must answer
plainly: (1) does the migration report's every count meet or exceed the measured ground truth
of SPEC §1.2, and if any is below, **why** — a low count means a wrong ref scope, not a moved
truth; (2) is there any record whose `cause` or `caused_by` was not literally present in its
source text (A3.5)? State the bug-surface delta of the bugs feature with its bug history — the
event fold produced the U+2028 silent-loss family, and this segment deletes the fold.

**Done criterion:** `APPROVE` committed on the branch; no home-absolute path or denylisted
term in the artifact.

**Parallelism:** none.

---

## Segment `S2` — lineage, commit shapes, hooks, the validated map

- [ ] **T-050-16 — FR7: `dd-diagnose`, with lineage as phase 0**

**Owner role:** ai-engineer · **Commit:** `feat(T-050-16): dd-diagnose — lineage phase 0 plus
the diagnosing method`

**Preconditions:** T-050-15 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-diagnose/SKILL.md` (new),
`dadaia_workspace/public/skills/dd-diagnose/LINEAGE.md` (new), `specs/bugs/AGENTS.md` (new —
the scoped summary), then one projection cycle
(`dadaia public stage && dadaia public install --target all`).

**Description:** Author the seven phases exactly as SPEC FR7 states them, each ending on a
checkable *Done when*. Phase 0 states the window **once** (FR14's pillar 1 cites this text,
never restates it) and instructs the reader to distrust a `release-squash` or `ledger-only` sha
rather than diff it. Produce the coverage table for every block relocated out of
`dd-bug-resolution` (the file itself is edited in T-050-21 — this task does not touch it, per
the single-owner rule SPEC D-B). **Add no CLI verb and no hook**: the diff must touch nothing
under `dadaia_workspace/cli/` or `dadaia_workspace/hooks/`.

**Done criterion:** A7.1–A7.5; `dadaia public doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-17 — FR8: the commit shapes and the one resolver seam**

**Owner role:** ai-engineer (the rules) + software-engineer (the resolver + its test) ·
**Commit:** `feat(T-050-17): commit shapes and one resolver seam for resolved_commit`

**Preconditions:** T-050-16 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`,
`dadaia_workspace/public/skills/dd-bug-registration/SKILL.md`,
`dadaia_workspace/features/bugs/service.py` (the resolver seam), `tests/**`, then one
projection cycle.

**Description:** State the five shapes (SPEC FR8) **exactly once** across the AI surface, with
every other home pointing at that statement; a duplicate-statement scan records its zero-hit
result. Implement the resolver: stored value when present, derived otherwise, one signature,
one caller-facing entry point (AS-1). **No new blocking validation**: `dadaia bugs
append`/`resolve` exit codes are unchanged for every input that succeeds today.

**Done criterion:** A8.1–A8.4; the stored-equals-derived contract test green on ≥ 20
historical records.

**Parallelism:** none.

---

- [ ] **T-050-18 — FR9: de-slop the hooks to the publication boundary**

**Owner role:** software-engineer · **Commit:** `refactor(T-050-18): hooks validate only at
the publication boundary`

**Preconditions:** T-050-17 `[x]`.

**Write set:** `dadaia_workspace/public/scripts/pre-commit-presence-gate.sh`,
`dadaia_workspace/public/scripts/pre-push-ci-gate.sh`,
`dadaia_workspace/cli/commands/ci.py` (`_run_backlog_doctor_gate` and `_staged_backlog_paths`
deleted), `tests/contract/**`, then one projection cycle.

**Description:** Pre-commit becomes advisory-only: presence WARN, **always exit 0**. The
`backlog doctor` block and the fail-closed runner are deleted — CI already runs the unscoped
sweep. Pre-push keeps **only** branch-name policy and the range-scoped denylist scan; the
`ci preflight --quick` invocation leaves the hook and becomes an always-on rule (landed in
`DADAIA.md` by T-050-20). The security-verdict CI gate on PRs is **untouched**. Assert the
**executed path**, never the script's text: a fixture stages a set `backlog doctor` rejects and
proves pre-commit exits 0; another proves a failing preflight no longer blocks a push. Capture
**V9** and **V10**.

**Done criterion:** A9.1–A9.5; V9 and V10 captured; V10 **negative**; zero-hit greps for both
deleted helpers.

**Parallelism:** none.

---

- [ ] **T-050-19 — FR10: `behavior-map.json` and its enforcer**

**Owner role:** ai-engineer (the map) + software-engineer (the contract tests) · **Commit:**
`feat(T-050-19): behavior map — every skill and scoped AGENTS.md maps to one DADAIA.md section`

**Preconditions:** T-050-18 `[x]`.

**Write set:** `dadaia_workspace/public/entities/behavior-map.json` (new),
`dadaia_workspace/public/entities/rules-skills-map.json` (retired),
`dadaia_workspace/public/schemas/rules-skills-map-v1.schema.json` (superseded by the
behavior-map schema), `tests/contract/test_behavior_map.py` (new, extending
`tests/contract/test_rules_skills_map.py`, which retires), `tests/**`.

**Description:** One row per core skill and per scoped `AGENTS.md`, each to exactly one
`DADAIA.md` section, with a recorded hash tuple. **Extend the existing enforcer; do not add a
second map** — a second map is the exact puxadinho this release is built to make visible.
Five RED conditions, five mutation fixtures, each proven to fail before and pass after its
correction. The test message must say **what to re-read**, not merely that a hash changed.

**Done criterion:** A10.1–A10.5; V17 captured; zero-hit grep for `rules-skills-map.json`
outside history.

**Parallelism:** none.

---

- [ ] **T-050-20 — FR11: `DADAIA.md` — anchors, the D15 posture, three short sections**

**Owner role:** ai-engineer · **Commit:** `feat(T-050-20): DADAIA.md behavior anchors and the
enforcement-posture section`

**Preconditions:** T-050-19 `[x]`. **This is the only task in the release whose write set
contains `DADAIA.md`** (SPEC D-B).

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (**source only** — the projected law is
PROTECTED), then one projection cycle.

**Description:** Add stable per-behavior anchors for the map to point at, the D15
enforcement-posture section verbatim in intent, the short bug-lineage/commit-shape section
(FR7/FR8), the short audits section (FR13/FR14), the short memory two-tier + ADR section
(FR17/FR19), and the always-on preflight rule (FR9). **Every section is a pointer, never a
restatement** — the FR8 duplicate scan is re-run over the result. Re-capture **V12** and
attribute the delta per section: a governance release is exactly the shape that quietly spends
the token budget the last two releases fought for.

**Done criterion:** A11.1–A11.4; V12 re-captured with per-section attribution; the projected
law byte-identical to source.

**Parallelism:** none.

---

- [ ] **T-050-21 — FR12: the skill surface rides the canon**

**Owner role:** ai-engineer · **Commit:** one coherent commit per skill family,
`refactor(T-050-21): <skill> aligned to canon v6`

**Preconditions:** T-050-20 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-bug-fix/` → `dd-bug-resolution/` (a `git mv`
plus content), `dadaia_workspace/public/skills/dd-release-implement/SKILL.md` +
`RC-FLOW.md`/`RELEASE-EVENTS.md`/`MEMORY-UPDATE.md` (new) with
`dadaia_workspace/public/skills/dd-release-implement/CLOSURE-CHECKS.md` and
`CLOSURE-TEMPLATE.md` deleted,
`dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`,
`dadaia_workspace/public/skills/dd-release-definition/SKILL.md`,
`specs/AGENTS.md`, `specs/backlog/AGENTS.md`, `specs/releases/AGENTS.md`,
`specs/memory/AGENTS.md`, then one projection cycle and the FR10 hash-tuple re-recording.

**Description:** Rename, rebuild and rewrite as SPEC FR12 states. Every deleted file's content
gets a named surviving home in a coverage table. Re-record each affected hash tuple with a
named reviewer — that re-recording is the joint review FR10 exists to force, and skipping it
is how `dadaia-task-manager-stale-workspace-protocol-citation` happened. Capture **V11**.

**Done criterion:** A12.1–A12.5; V11 captured and `S2`'s AI-surface net **negative**;
`dadaia public doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-22 — `S2` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-22): S2 QA close`

**Preconditions:** T-050-16 … 21 all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S2-qa-close.md`.

**Description:** Evidence A7–A12. Read the **coverage tables**, not the diffs alone — the risk
here is a law relocated into nothing (the v0.4.4/v0.4.5 R-4 class). Confirm mechanically that
this segment added **zero** blocking exits and removed two, and state the bug-surface delta of
the hook surface with the registered bug that motivated it
(`precommit-backlog-doctor-blocks-unrelated-commits`).

**Done criterion:** `APPROVE` committed on the branch.

**Parallelism:** none.

---

## Segment `S3` — the audit canon

- [ ] **T-050-23 — FR13: audits become committed spec artifacts**

**Owner role:** software-engineer (schema, scaffold) + ai-engineer (persona, scoped law) ·
**Commit:** `feat(T-050-23): audits as committed artifacts — AUDIT.md + FINDINGS.jsonl`

**Preconditions:** T-050-22 `[x]`.

**Write set:**
`dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json` (new),
`dadaia_workspace/public/agents/project-auditor.md`,
`dadaia_workspace/public/scaffold/audits/**` (`README.md` retires, `AGENTS.md` added),
`specs/audits/AGENTS.md` (new), `specs/audits/README.md` (deleted),
`dadaia_workspace/infrastructure/jsonl_bug_store.py` (the shared record-update seam, per the
AR-1 ruling), `tests/**`, then one projection cycle.

**Description:** Author the finding record with the immutable/mutable split documented per
property. `project-auditor`'s write allowlist gains `specs/audits/**` and **nothing else** — a
fixture proves a write elsewhere under `specs/` is still refused, because a persona that can
write the whole of `specs/` is not an auditor. Reuse the FR2 record-update seam; do **not**
re-implement it.

**Done criterion:** A13.1–A13.4.

**Parallelism:** none.

---

- [ ] **T-050-24 — FR14: `dd-audit-project` rewritten around three pillars**

**Owner role:** ai-engineer · **Commit:** `refactor(T-050-24): dd-audit-project — three
pillars over a sha window`

**Preconditions:** T-050-23 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`,
`dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md` (new), `PILLAR-SPECS.md`
(new), `PILLAR-MEMORY.md` (new), `FINDINGS-FORMAT.md` (new), with
`dadaia_workspace/public/skills/dd-audit-project/RUBRIC.md` and `TOOLING.md` folded into the
siblings, then one projection cycle and the FR10 hash-tuple re-recording.

**Description:** Rewrite short, with a *Done when* per pillar; lift
`disable-model-invocation` and list the skill in `project-auditor`'s skills — a skill nobody
can invoke is the defect that kept this lane dark. The window computation is stated once and
**cited** from `dd-diagnose/LINEAGE.md`, never restated. Pillar 1's recurrence and
fix-induced definitions must be computable from `BUGS.jsonl` + `git show` with no further
judgement about what counts. **Zero CLI verbs, zero hook changes** in this diff.

**Done criterion:** A14.1–A14.5.

**Parallelism:** none.

---

- [ ] **T-050-25 — FR15: `specs doctor` folds `FINDINGS.jsonl`**

**Owner role:** software-engineer · **Commit:** `refactor(T-050-25): fold FINDINGS.jsonl
instead of regexing audit prose`

**Preconditions:** T-050-24 `[x]`.

**Write set:** `dadaia_workspace/features/specs/doctor_closure_audit.py`, `tests/**`.

**Description:** Delete the regex path of `check_audit_disposition` / SPEC-DOC-036 /
SPEC-DOC-038 and fold the JSONL instead: an `open` record inside an archived audit is an
**error**; a live audit whose records are all terminal with a named release is an
**archive-due WARN**. Deleted, not bypassed.

**Done criterion:** A15.1–A15.3; the zero-hit grep recorded; `specs doctor` **0 errors**.

**Parallelism:** none.

---

- [ ] **T-050-26 — FR16: the first audit, as a dry run over this repository**

**Owner role:** project-auditor · **Commit:** `docs(T-050-26): first audit under canon v6 (dry
run)`

**Preconditions:** T-050-25 `[x]`.

**Write set:** `specs/audits/<YYYYMMDD>-canon-v6-first-audit/AUDIT.md` (new) +
`FINDINGS.jsonl` (new); `specs/releases/0.5.0/RELEASE.jsonl` (the `audited` milestone).

**Description:** Run all three pillars over the window. **This is the release's acceptance,
not a formality:** pillar 1 must name, with evidence, at least the four documented chains of
SPEC §1.1 — the gitignore class, the certify 37-minute re-bug, the frozen-clock 3-hop chain
and the bug-event ledger family. If it cannot, T-050-24 is reworked; the acceptance is not
lowered. Pillar 2 reads **this release's own commits** and reports FR8 conformance. Pillar 3
executes every `Measured by:` check — note that FR18 authors them in `S4`, so any principle not
yet written is recorded as a gap to re-run at the final `rc`, never as a pass. Every finding is
`disposition: open`, `release: null`; **no backlog entry is created** — the findings go to the
PM's operator-gated intake report. Redact absolutely: no path, IP, hostname or private name
enters the artifact.

**Done criterion:** A16.1–A16.6; V16 captured.

**Parallelism:** none.

---

- [ ] **T-050-27 — `S3` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-27): S3 QA close`

**Preconditions:** T-050-23 … 26 all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S3-qa-close.md`.

**Description:** Evidence A13–A16. The single question that decides this segment: **did the
dry run rediscover the loop?** Quote the four chains and their evidence from
`FINDINGS.jsonl`, or reject the segment. Also verify the audit artifact carries no redaction
violation — it is committed inside `specs/`, so it is public forever.

**Done criterion:** `APPROVE` committed on the branch, with A16.2 explicitly evidenced.

**Parallelism:** none.

---

## Segment `S4` — memory two-tier, principles, ADRs

- [ ] **T-050-28 — FR17: split the memory trio into Part 1 and Part 2**

**Owner role:** product-engineer · **Commit:** `docs(T-050-28): memory Part 1 Principles /
Part 2 Implementation`

**Preconditions:** T-050-27 `[x]`; the release phase permits a memory write (`DEFINITION` or
`CLOSURE` — the dispatcher sets it before relaying, and flips it back afterwards).

**Write set:** `specs/memory/ARCHITECTURE.md`, `specs/memory/QUALITY.md`,
`specs/memory/TECHSTACK.md`, `specs/memory/AGENTS.md`, `specs/memory/product/**` (only the
atoms carrying architecture principles or implementation tours), `tests/contract/**` (the
file-shape test).

**Description:** Restructure each of the three files into exactly two top-level parts. Every
prose rule that cannot name an existing measure moves to Part 2 or is deleted, and every move
is recorded in a coverage table — **no law is dropped silently**. `product/` atoms lose any
architecture principle they carried. Memory stays a current-state document: no `Changelog`,
`History`, `Histórico` or `Versions` section.

**Done criterion:** A17.1–A17.5; the coverage table complete; the memory lane of
`specs doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-29 — FR18: the first principle inventory**

**Owner role:** software-architect (the inventory and its measures) + product-engineer (the
authoring) · **Commit:** `docs(T-050-29): promote the measured rules to Part 1 principles`

**Preconditions:** T-050-28 `[x]`.

**Write set:** `specs/memory/ARCHITECTURE.md`, `specs/memory/QUALITY.md`,
`specs/memory/TECHSTACK.md`, `tests/contract/**` (the contract-count test), the V13/V14
captures.

**Description:** One principle per existing mechanical check: **every**
`[importlinter:contract…]` section in `setup.cfg` (count read from the file — nine at HEAD, the
grill counted eight, and the rule is "every contract"), the LOC ceilings and complexity
ratchet, the LARGE-test census and the stewardship pyramid/lifecycle laws, the diagram drift
guard. **Write zero new checks** — if a rule has no existing check it does not become a
principle, and that constraint is what stops this inventory from becoming a second enforcement
layer. Execute every `Measured by:` command once and capture its output (**V14**); a
`Measured by:` that does not run is not admitted.

**Done criterion:** A18.1–A18.4; V13 and V14 captured; the contract-count test RED when a
tenth import-linter contract is added without a principle.

**Parallelism:** none.

---

- [ ] **T-050-30 — FR19: the `specs/ADRs/` canon and the proposed inventory ADRs**

**Owner role:** product-engineer (authoring) + ai-engineer (the scoped `AGENTS.md`) ·
**Commit:** one isolated `docs(adr): propose NNNN-<slug>` **per ADR** (SPEC FR8 shape 2)

**Preconditions:** T-050-29 `[x]`.

**Write set:** `specs/ADRs/AGENTS.md` (new), `specs/ADRs/NNNN-<slug>.md` (one per inventory
principle), `tests/contract/**` (the monotonic-numbering test),
`dadaia_workspace/public/scaffold/ADRs/**`.

**Description:** Author the law, the index and one ADR per inventory principle, each with every
field including **Confirmation** (`Measured by:`) — an ADR with no confirmation cannot be
accepted. Every ADR is authored `Status: proposed`. **An agent that writes `accepted` has
violated the law**; state that where an agent reads it before writing. One decision per file,
never a changelog. Zero CLI verbs, zero doctor rules beyond FR1's folder shape.

**Done criterion:** A19.1–A19.4; one isolated commit per ADR, proven by `git log --stat`.

**Parallelism:** none.

---

- [ ] **T-050-31 — [operator] FR20: the ADR acceptance sitting**

**Owner role:** **operator** (the only permitted actor) · **Commit:** one
`docs(adr): accept NNNN-<slug>` per accepted ADR, each staging the ADR's status flip **plus**
the Part-1 principle hunk it admits

**Preconditions:** T-050-30 `[x]`.

**Write set:** `specs/ADRs/NNNN-<slug>.md` (status flips), `specs/memory/ARCHITECTURE.md` /
`QUALITY.md` / `TECHSTACK.md` (the Part-1 hunks each acceptance admits).

**Description:** The operator reviews the proposed inventory in one sitting and flips each to
`accepted` (with `Accepted by: operator, <date>`) or `rejected` with a reason. **No agent may
perform this step**, and the commit shape is not cosmetic: pillar 3's "Part 1 changed without
an accepted ADR" check reads exactly this pairing. A rejected proposal's principle does not
enter Part 1 and is recorded in the coverage table with its reason.

**Done criterion:** A20.1–A20.3; zero ADRs left `proposed`.

**Parallelism:** none — it gates T-050-32.

---

- [ ] **T-050-32 — FR21: the constitution references principles**

**Owner role:** product-engineer · **Commit:** `docs(T-050-32): constitution references
principles by id`

**Preconditions:** T-050-31 `[x]` — the principle ids must be final.

**Write set:** `specs/constitution.md`.

**Description:** Replace every restated rule with a reference (`see ARCHITECTURE.md P-04`). A
clause with no principle behind it becomes a `proposed` ADR (authored under T-050-30's shape)
or is deleted, with the reason in the coverage table. Re-run the FR8 duplicate scan across
`constitution.md` and the memory trio: **zero** rule text may be duplicated between them.
Capture **V15**.

**Done criterion:** A21.1–A21.3; V15 captured; the delta negative.

**Parallelism:** none.

---

- [ ] **T-050-33 — `S4` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-33): S4 QA close`

**Preconditions:** T-050-28 … 32 all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S4-qa-close.md`.

**Description:** Evidence A17–A21. Check the two properties that make this segment worth
anything: (1) **every** Part-1 principle names a measure that was actually executed (V14) —
a `Measured by:` line pointing at a check nobody ran is decoration, which is what this segment
exists to abolish; (2) **zero** new checks were written by FR18 (A18.3). Also confirm every
ADR carries a terminal operator decision.

**Done criterion:** `APPROVE` committed on the branch.

**Parallelism:** none.

---

## Scope complete — gates and the trio

- [ ] **T-050-34 — [shell] FR22: the invariants, measured**

**Owner role:** software-engineer · **Commit:** the capture reference only

**Preconditions:** T-050-33 `[x]`; every task above `[x]`.

**Description:** Run `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor` (**0
errors**), `dadaia backlog doctor`, `dadaia public doctor`, `lint-imports`. Capture **V18**
(zero new non-zero exits in the hooks; the CLI-output-stability fixtures green untouched) and
**V19** (production LOC **per FR** with its declared direction, AI-surface net, complexity
ceilings). A positive net inside an FR that declared itself net-negative is a defect of the
release; the release's overall net-positive production LOC is expected and stated (SPEC
A22.3).

**Done criterion:** A22.1–A22.7; V18 and V19 captured.

**Parallelism:** none.

---

- [ ] **T-050-35 — Six-axis code review on the thawed tree**

**Owner role:** code-reviewer · **Commit:** `docs(T-050-35): release code review`

**Preconditions:** T-050-34 `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/T-050-35-code-review.md`.

**Description:** Review the whole delta on a **thawed** tree, before any archive move. For
every touched feature, state whether the change **reduced or increased its bug surface**, with
bug-history evidence — "tests green" is not a verdict. Three questions this release must
answer: did the record model leave the bugs feature smaller than the event fold did? Did FR9
delete two blockers without weakening the publication boundary? Is there **any** place where a
second code path was added — a second map, a second symlink check, a second denylist reader, a
second record-update seam — that the single-owner rule (SPEC D-B) was supposed to prevent?

**Done criterion:** `APPROVE` with the bug-surface verdict per touched feature.

**Parallelism:** none.

---

- [ ] **T-050-36 — Security review + the QA release verdict**

**Owner role:** security-reviewer + qa-engineer · **Commit:**
`docs(T-050-36): release verdicts`

**Preconditions:** T-050-35 `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/RELEASE-VERDICT.md`, the verdict handoffs.

**Description:** Diff-based `security-reviewer` review of the whole delta. The surfaces that
matter: FR3's migration report and FR16's audit folder (both committed forever inside `specs/`
— any path, IP, hostname or private name is a leak of the class that recurred three times in
v0.4.4), FR9 (two gates removed — prove the publication boundary is intact and the denylist
scan still runs on the range), FR13 (a persona's write allowlist widened), and FR6 (a
destructive deletion whose only recovery is a tag). Then the `qa-engineer` release verdict
closing the scope. All three verdicts — QA, code, security — must `APPROVE` the **same** commit.

**Done criterion:** three `APPROVE`s on one sha; the verdict handoff keyed to it.

**Parallelism:** none.

---

## `rc-1` — the whole scope integrates once

- [ ] **T-050-37 — [git] `rc-1`: PR `feature/0.5.0` → `develop`**

**Owner role:** dispatcher + security-reviewer · **Preconditions:** T-050-36 `[x]`.

**Description:** Push `feature/0.5.0`, open the PR to `develop` with the APPROVED verdict
covering the **PR head sha**, watch CI to green, merge. That merged `develop` **is `rc-1`**
(SPEC D-J) — the first and only integration of the whole scope. Append the `rc_open`/`rc_close`
records to `RELEASE.jsonl`.

**Done criterion:** PR merged; CI green; APPROVED verdict recorded; `develop` carries the whole
scope.

**Parallelism:** none.

---

## `rc-2 … rc-N` — adjustment rounds on the merged scope

- [ ] **T-050-38 — Adjustment rounds: test `develop`, fix on the branch, merge again**

**Owner role:** qa-engineer + operator (finding) · software-engineer / ai-engineer (fixing) ·
dispatcher + security-reviewer (merging) · **Preconditions:** T-050-37 `[x]`.

**Description:** The merged `develop` is exercised. Each finding **on this release's scope**
becomes a fix worked on `feature/0.5.0`, QA-closed, delta-reviewed and merged again by PR: one
`rc` per merge. **No new backlog enters an `rc`** (A22.8) — a demand outside this scope is
recorded for the PM's intake, never worked here. **This task may close with zero rounds**, in
which case the final `rc` **is** `rc-1`.

**Done criterion:** every round has a QA close, a delta review, a merge and a `RELEASE.jsonl`
`rc_open`/`rc_close` pair; the accepted final `rc` is named.

**Parallelism:** none — one round at a time.

---

## The final `rc` — closure, archive, ship

- [ ] **T-050-39 — Memory window (SPEC §5)**

**Owner role:** product-engineer · **Commit:** `docs(T-050-39): memory after 0.5.0`

**Preconditions:** T-050-38 `[x]` (the final `rc` is accepted); the release phase set to
`CLOSURE`.

**Write set:** the atoms named in SPEC §5 — the **four mandatory rewrites**
(`ARCHITECTURE.md`, `QUALITY.md`, `sdd-bug-backlog-governance.md`, and the **new**
`specs/memory/product/sdd/audit-canon.md`) first, then the rest, one authoring pass per atom;
`specs/memory/product/index.md` + `catalog.json` regenerated.

**Description:** Write into the **new Part 1 / Part 2 shape** this release created. A Part-1
change here requires an accepted ADR in the same commit (FR19's rule now binds the author of
this task too) — if the closure needs a new principle, it needs an operator acceptance first.
Memory describes the product as it now is, with no changelog.

**Done criterion:** `specs doctor` **0 errors**; every atom in SPEC §5 either updated or
explicitly marked "no change" with its reason.

**Parallelism:** none.

---

- [ ] **T-050-40 — The closure record with every sweep**

**Owner role:** product-engineer · **Commit:** `docs(T-050-40): 0.5.0 closure`

**Preconditions:** T-050-39 `[x]`.

**Write set:** `specs/releases/0.5.0/RELEASE.jsonl` (the closure records), the disposition
sweep in `specs/backlog/_archive/backlog_histo.jsonl` and `specs/backlog/BACKLOG.md`,
`specs/audits/<YYYYMMDD>-canon-v6-first-audit/FINDINGS.jsonl` (untouched — its findings stay
`open`, AS-10).

**Description:** `CLOSURE.md` no longer exists (FR4); the closure narrative rides
`RELEASE.jsonl` plus the sections SPEC §5 enumerates. Discharge every closure obligation:
summary; tasks + final shas; validations as `{description, command, evidence}` triples;
`## Size accounting` (V19, V11, V12, V15); the migration report and back-fill report by path
and headline counts; the FR16 audit by folder with its per-pillar finding counts; the ADR
ledger with every operator decision; the four coverage tables (FR7, FR12, FR17, FR21); test
dispositions; the `rc` ledger; the artifact GC sweep; **intake candidates** — FR16's findings
and every residual, compiled for the PM's operator-facing report, with **no backlog entry
created by any agent**; the restated git-identity standing question; archive decision `MOVE`.
Six backlog slugs move to `DELIVERED · 0.5.0` through the FR5 mechanism — one record each,
never a duplicate. **No bug is closed by this release** (AS-4).

**Done criterion:** every closure obligation in SPEC §5 discharged.

**Parallelism:** none.

---

- [ ] **T-050-41 — [git] Archive the release**

**Owner role:** dispatcher · **Commit:** `chore(T-050-41): archive 0.5.0`

**Preconditions:** T-050-40 `[x]`.

**Description:** `git mv specs/releases/0.5.0 specs/releases/_archive/0.5.0` — the **per-area**
archive this release created, not the deleted root `_archive/` (FR6). Append the `archive`
record to `RELEASE.jsonl`. Steps T-050-39 … 41 ride **one** commit, in the order memory →
closure → sweep → archive.

**Done criterion:** the release directory is under `specs/releases/_archive/`; the phase fold
reads `ARCHIVED`.

**Parallelism:** none.

---

- [ ] **T-050-42 — [git] Final-`rc` merge: version bump and PR → `develop`**

**Owner role:** dispatcher + software-engineer + security-reviewer

**Preconditions:** T-050-41 `[x]`.

**Write set:** `pyproject.toml` (bump to `0.5.0`), `CHANGELOG.md` (`[0.5.0]`), then git refs.

**Description:** One axis: the release id **is** the package version. MINOR, because the
`specs/` pattern moves 5 → 6 and that is consumer-visible. Push `feature/0.5.0`, APPROVED
verdict on the PR head sha, PR to `develop`, CI green, merge — this burns the **final `rc`**
and writes the `implemented` milestone with its sha.

**Done criterion:** PR merged; CI green; the `implemented` milestone appended.

**Parallelism:** none.

---

- [ ] **T-050-43 — [git] Ship — merge to `main`**

**Owner role:** dispatcher + security-reviewer + **operator** (the publish decision) ·
**Preconditions:** T-050-42 `[x]`.

**Description:** PR `develop → main`; watch CI to green; merge. Append the `shipped` milestone
with the merge sha, the PR number and the tag if one is created. **The publish decision is the
operator's** (AS-6): `v0.4.5` was minted unpublished by operator law O5, so whether
`release.yml`'s approval gate is approved for `0.5.0` is asked, not assumed, and the answer is
recorded in `RELEASE.jsonl` and in the closure record either way. Then, **in the same step**:
delete `feature/0.5.0` and cut the next feature branch from `main`. Run the reconciliation
merge of `main` into `develop`. Point the release pointer at the next release or `none`.

**Done criterion:** PR merged to `main`; CI green; the `shipped` milestone recorded with its
sha; the publish decision recorded; `feature/0.5.0` gone; exactly one feature branch exists,
cut from `main`; worktree clean.

**Parallelism:** none — last task.
