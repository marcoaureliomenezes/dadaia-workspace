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

**Ids are in execution order** — nothing below runs out of numeric sequence. Tasks added by
the 2026-08-26 review fold carry a **letter suffix** (`T-050-03A`) and run immediately after
the numbered task they follow; existing ids are never renumbered, because five review
documents, the SPEC's §9 fold table and the backlog entries all cite them by number.

| Block | Tasks | Contents | Gate |
|---|---|---|---|
| W0 | T-050-01 … 03, **03A** | promotion + definition commit + definition PR + baseline captures + the reviewer-persona allowlist widening | definition PR merged into `develop`; APPROVED verdict on its head sha |
| `S1` | T-050-04 … 15 (+ **06A**, **13A**) | the v6 canon, its two boundaries, and the historical ledger rewrite (FR1–FR6) | `qa-engineer` review **committed** + the `software-architect` **AR-1** confirmation |
| `S2` | T-050-16 … 22 (+ **21A**) | lineage, commit shapes, hooks de-slop, the validated map, and FR4's contract step (FR7–FR12, FR4) | `qa-engineer` review committed |
| `S3` | T-050-23 … 27 (+ **25A**) | the audit canon, its dry run, and the retirement of every `CLOSURE.md` parser (FR13–FR16) | `qa-engineer` review committed + the dry-run artifact satisfying A16.2 |
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
- **Nothing inferred is presented as declared.** Provenance markers are mandatory (SPEC D-A),
  and they are named `registration_granularity` / `resolution_granularity` — never
  `commit_granularity`, which is not a field.
- **Every verdict lands at the exact path and shape the CI gate keys on.** A
  `security-reviewer` verdict is a handoff at
  `specs/releases/<release-id>/verdicts/<sha>.handoff.json` carrying
  `agent: "security-reviewer"`, `verdict: "APPROVED"` and a **40-hex** `metrics.commit_sha`
  — a branch name or a short sha is silently skipped by the gate. Applies to T-050-02,
  T-050-36, T-050-37, T-050-42 and T-050-43.
- **The memory window is recorded, never toggled (AS-12).** `specs/memory/**` is writable in
  `DEFINITION`/`CLOSURE` only. `S4` opens with a `phase: CLOSURE` record appended to
  `RELEASE.jsonl` (T-050-28) and closes with a `phase: IMPLEMENTATION` record (T-050-33).
  Both are ledger facts an audit can read. **No task silently flips a phase around itself.**
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
| **T-050-03A** | — | AI-1 (§9.4) | four reviewer personas widened to `specs/releases/**/reviews/**`; one refusal fixture each |
| T-050-04 | FR2/FR3 | A2.5, A3.10, A13.4 | the `software-architect` **AR-1** confirmation of §2 F6/AR-1, verbatim |
| T-050-05 | FR1 | A1.1–A1.4 | scaffold fixture; TREE-8 WARN fixture + exit-code fixture; `--recipe` output; double-`upgrade` byte comparison |
| T-050-06 | FR1 | A1.5, A1.6, A1.9 | this repo migrated; `specs doctor` 0 errors; V3; the `hooks/sdd_gate.py` diff |
| **T-050-06A** | FR1 | A1.7, A1.8 | **V20**, **V21**; `.gitignore` inverted; the verdict gate proven against a v6 fixture tree |
| T-050-07 | FR2 | A2.1, A2.2, A2.6, A2.9 | `bug-record-v1.schema.json`; immutability + write-once + in-place-rewrite + redaction + atomic-write tests |
| T-050-08 | FR2 | A2.3, A2.4, A2.7, A2.8 | WARN-with-unchanged-exit fixture; `bugs archive` idempotence; the doctor's core-vs-derived WARN; the event reader deleted after the switch |
| T-050-09 | FR3 | A3.4, A3.10 (unit) | the pure derivation function over `GitHistoryReader` + its fixture tests, including the double-run |
| T-050-10 | FR3 | A3.1–A3.9 | V4, V5, **V22**, **V23**; the migration report; the no-fabrication scan; `archive.jsonl` byte-identical |
| T-050-11 | FR4 | A4.1, A4.2, A4.6 | `RELEASE.jsonl` written **and read in parallel with `ACTIVE.md`**; milestone immutability test; `core/release_events.py` |
| T-050-12 | FR4 | A4.3, A4.6 | V7 across **both** archive layouts; `releases_histo.jsonl`; every sha `git cat-file -e` green |
| T-050-13 | FR5 | A5.1–A5.4 | `backlog_histo.jsonl`; BL-DUP deleted from `features/backlog/doctor.py`; the exit fixture |
| **T-050-13A** | FR5 | A5.5 | the 18 `consumed_backlog.json` sidecars relocated; BL-STALE still fires on a relocated record |
| T-050-14 | FR6 | A6.1–A6.6 | V8 from a throwaway clone; the pushed tag; the relocated `verdicts/**`; the deletion commit with the enumerated FROZEN repoint |
| T-050-15 | all `S1` | A1–A6 ids | `qa-engineer` artifact committed |
| T-050-16 | FR7 | A7.1–A7.5 | `dd-diagnose` + `LINEAGE.md`; the coverage table; zero `cli/`+`hooks/` diff |
| T-050-17 | FR8 | A8.1–A8.4 | the duplicate scan; the resolver contract test on ≥ 20 records |
| T-050-18 | FR9 | A9.1–A9.6 | V9, V10; the executed-path pre-commit fixture; the pre-push **runner-refusal** fixture; the two hook tests' stewardship verdict; zero-hit greps |
| T-050-19 | FR10 | A10.1–A10.6 | V17; five mutation fixtures; **nine checks proven ported**; glob-based discovery; `rules-skills-map.json` retired |
| T-050-20 | FR11 | A11.1–A11.4 | V12 with anchor cost separated per section; the §3 ADDITIVE-row rewrite; `public doctor` green |
| T-050-21 | FR12 | A12.1–A12.5 | V11; zero-hit grep for `dd-bug-fix`; the coverage table incl. the `dd-architecture-survey` pointer |
| **T-050-21A** | FR4 | A4.4 (partly), A4.5, A4.7 | `ACTIVE.md` **deleted**; all 28 consumers + 26 test files repointed; zero-hit grep; the no-`ACTIVE.md` gate fixture |
| T-050-22 | all `S2` | A7–A12 ids, A4.5/A4.7 | `qa-engineer` artifact committed; zero new `tests/e2e/**` exceptions confirmed or named |
| T-050-23 | FR13 | A13.1–A13.4 | the finding schema; the generic `JsonlRecordStore`; the FROZEN refusal fixture |
| T-050-24 | FR14 | A14.1–A14.6 | the rewritten skill + 4 siblings; the executable window recipe; the one-rewrite pillar-1 fixture |
| T-050-25 | FR15 | A15.1–A15.3 | zero-hit grep on the regex path; two doctor fixtures |
| **T-050-25A** | FR15/FR4 | A4.4 | every surviving `CLOSURE.md` parser deleted; `RELEASE_ARTIFACTS` and `AUDIT_DIR_NAME_RE` collapsed; zero-hit grep |
| T-050-26 | FR16 | A16.1–A16.6 | V16, **V24**; the committed audit folder; the four chains named **by their pinned bug ids** |
| T-050-27 | all `S3` | A13–A16 ids | `qa-engineer` artifact committed; A16.2 evidenced; zero e2e exceptions confirmed |
| T-050-28 | FR17 | A17.1–A17.5 | the `phase: CLOSURE` record opening the memory window; the two-part memory trio; the coverage table |
| T-050-29 | FR18 | A18.1–A18.4 | V13, V14; the contract test on the contract count |
| T-050-30 | FR19 | A19.1–A19.4 | `specs/ADRs/` + the proposed inventory ADRs; the numbering test |
| T-050-31 | FR20 | A20.1–A20.3 | one `docs(adr): accept …` commit per accepted ADR, carrying its Part-1 hunk |
| T-050-32 | FR21 | A21.1–A21.3 | V15; the coverage table; the duplicate scan |
| T-050-33 | all `S4` | A17–A21 ids | `qa-engineer` artifact committed; the `phase: IMPLEMENTATION` record closing the memory window; zero e2e exceptions confirmed |
| T-050-34 | FR22 | A22.1–A22.7 | V18, V19; gate output; per-FR LOC direction; the xdist CI-matrix note |
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
T-050-02, not here (`ACTIVE.md` is still the phase source until T-050-21A retires it).
**No bug is picked** (AS-4) — and there is no `status: picked` to write on any record either,
since the pick **is** this commit (FR2, FR8 shape 5).

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
`security-reviewer` review of the delta, open the PR to `develop` with the APPROVED verdict at
**`specs/releases/0.5.0/verdicts/<40-hex-sha>.handoff.json`** (`agent: "security-reviewer"`,
`verdict: "APPROVED"`, a **40-hex** `metrics.commit_sha` — a short sha or branch name is
skipped by the gate), watch CI to green, merge. This is the definition PR named by
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

- [ ] **T-050-03A — Widen the four reviewer personas to `specs/releases/**/reviews/**`**

**Owner role:** ai-engineer · **Commit:** `feat(T-050-03A): reviewer personas may write
release review artifacts`

**Preconditions:** T-050-03 `[x]`. **This task must land before T-050-04**, whose very first
act is `software-architect` writing into `reviews/`.

**Write set:** `dadaia_workspace/public/agents/software-architect.md`,
`dadaia_workspace/public/agents/qa-engineer.md`,
`dadaia_workspace/public/agents/code-reviewer.md`,
`dadaia_workspace/public/agents/security-reviewer.md` (frontmatter `write_allowlist` only),
`tests/contract/**`, then one projection cycle.

**Description:** This release's own segment closes, code review and release verdicts are
artifacts under `specs/releases/0.5.0/reviews/**`, but at HEAD `software-architect`,
`code-reviewer` and `security-reviewer` carry **no** `specs/` allowlist and `qa-engineer`
carries only `specs/releases/**/ALPHA-*-QA.md`. Add the single generic glob
`specs/releases/**/reviews/**` to each — generic enough to survive future releases, far
narrower than a blanket `specs/**`. **State the honest posture in the same edit:**
`write_allowlist` is parsed at *projection* time and is persona documentation, not a
write-time control (nothing refuses a persona's file-tool write to an ADDITIVE path). It is
declared so the fleet's declared scope matches what the release actually asks of it — the
drift class `ai-engineer` exists to prevent.

**Done criterion:** each of the four personas declares `specs/releases/**/reviews/**` and
nothing wider; a fixture per persona asserts the parsed allowlist admits that glob and does
not admit `specs/memory/**`; `dadaia public doctor` green.

**Parallelism:** none.

---

## Segment `S1` — the v6 canon and the historical ledger rewrite

- [ ] **T-050-04 — AR-1: the record model and the v5 boundary adapter, ruled**

**Owner role:** software-architect · **Commit:** `docs(T-050-04): AR-1 ruling — bug record
model and the v5 adapter boundary`

**Preconditions:** T-050-03 `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S1-AR1-ruling.md`.

**Description:** **AR-1 was already answered by the 2026-08-26 definition review**, so this
task is a short confirmation, not an open question. The three answers now in the SPEC:
(a) the v5→v6 adapter lives in `dadaia_workspace/features/bugs/migrate_v5.py`, imported by
nothing else and deletable with the migration (A2.5); (b) the record-update seam is admissible
only as a **generic** `infrastructure/jsonl_record_store.py` — `JsonlRecordStore` keyed by
`id`, parse/serialise injected through a `core.protocols` record protocol, one instance per
feature model, the legacy hourly-file reader deleted in the same task (A2.5, A13.4); (c) the
FR3 derivation is a **pure core function** over `(sha, parents, date, touched_paths,
added_lines)`, with git behind a `core.protocols.GitHistoryReader` implemented in
`infrastructure/git_subprocess.py` and injected by the container — no `subprocess` in
`features/**`, no new accepted edge (A3.10). Confirm all three against the tree as it stands
at this moment, or record an overturn **with its reason** and re-read the affected acceptance
ids before implementation.

**Done criterion:** a five-line confirmation (or a reasoned overturn) recorded verbatim,
before T-050-07 starts.

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
`QUALITY.md`; **`specs/assets/**` retired into `specs/memory/ARCHITECTURE.md`** with every
`../assets/` link in memory rewritten to the diagram's new home;
**`specs/backlog/remote-bugs/**` deleted** — the folder whose own gitignore stanza is one of
the nine recurrences; `specs/releases/README.md`, `specs/bugs/README.md`,
`specs/audits/README.md` retire in their owning FRs),
`dadaia_workspace/features/specs/memory_lint.py`, `tests/**`.

**Description:** Perform the case-only renames with an explicit **two-step `git mv`** so a
case-insensitive filesystem cannot silently no-op them. Retire `specs/assets/` and
`specs/backlog/remote-bugs/` — both exist at HEAD and both are named by the canon as
non-conformant, so neither may be left for "some later task". Repoint the memory lint and
every in-repo reference. **The gate is not touched here:** the FROZEN class is repointed in
T-050-14 and the phase read (`hooks/sdd_gate.py#_active_field`) retires in T-050-21A — this
task must leave no window where either points at nothing.

**Done criterion:** A1.5, A1.6, A1.9; `dadaia specs doctor` **0 errors**; **V3** captured with
no TREE-8 WARN on this release's own directory; zero `specs/assets/` and zero
`specs/backlog/remote-bugs/` paths remain.

**Parallelism:** none.

---

- [ ] **T-050-06A — FR1: the two boundaries a canon change breaks**

**Owner role:** software-engineer · **Commit:** `fix(T-050-06A): track every canon path and
resolve verdict evidence from the canon`

**Preconditions:** T-050-06 `[x]`.

**Write set:** `.gitignore`, `.github/scripts/pr-verdict-check.sh`, `.github/workflows/ci.yml`,
`dadaia_workspace/core/specs_version.py`, `tests/contract/**`.

**Description:** Two boundaries read the canon from outside `specs/`, and a canon change that
leaves either behind is this workspace's most-repeated bug shape.

**(a) `.gitignore` (A1.7 / V21).** Verified today with `git check-ignore -q`:
`specs/audits/<slug>/FINDINGS.jsonl`, `specs/ADRs/0001-x.md`, `specs/ADRs/AGENTS.md` and
`specs/backlog/_archive/backlog_histo.jsonl` are **IGNORED** — three of this release's own
governance artifacts would be born untracked, unreviewable, and invisible to the range-scoped
denylist scan. Apply the **proven inversion** already used for `specs/releases/**`
(`!/specs/audits/**`, `!/specs/ADRs/**`, `!/specs/bugs/_archive/**`,
`!/specs/backlog/_archive/**`, `!/specs/releases/_archive/**`, denying only `local-notes.md`
and `tmp/`), and delete the three stanzas T-050-06/FR6 orphan (`specs/assets/`,
`specs/backlog/remote-bugs/`, root `specs/_archive/`). State the widening as the deliberate
privacy decision it is in the file's own comment.

**(b) The CI verdict-evidence contract (A1.8 / V20).** The gate globs
`specs/releases/*/verdicts/` and `specs/_archive/releases/*/verdicts/`; after FR6 the evidence
lives at `specs/releases/_archive/<id>/verdicts/` — one level deeper, matched by neither (`*`
does not cross `/`) — and its `_RELEASE_ID_RE` demands a `v` prefix that bare-semver ids do
not carry. Left alone, the final-`rc` PR and the ship PR both fail a **required** check and
the release cannot ship. **Derive the evidence roots and the id pattern from
`core/specs_version.py`** — the canon — instead of hard-coding globs, so the next canon move
cannot break it again. Keep every refusal **fail-closed**: `_archive`, `_ideas` and any
traversal shape still refused before interpolation; a missing qualifying handoff still fails.
This is the **third** firing of
`verdict-gate-cannot-resolve-evidence-after-release-archive` (HIGH, T-044-50, after the
`ACTIVE.md`-pointer variant); both prior fixes patched the resolution shape rather than
deriving it. **Archiving after the ship PR is not the fix and is refused** — it contradicts
`DADAIA.md` §6's finalization order (SPEC AS-15).

**Done criterion:** A1.7, A1.8; **V21** (every canon path reports *not ignored*) and **V20**
(the gate resolves and refuses correctly against a v6 fixture tree with live, `_ideas/` and
`specs/releases/_archive/<id>/verdicts/` members) captured. Both run **now**, not at
T-050-41.

**Parallelism:** none.

---

- [ ] **T-050-07 — FR2 (expand): the bug record model**

**Owner role:** software-engineer · **Commit:** `feat(T-050-07): one record per bug —
bug-record-v1 with immutable core and mutable governance`

**Preconditions:** T-050-06 `[x]`; the AR-1 ruling recorded.

**Write set:** `dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json` (new),
`dadaia_workspace/core/models/bugs.py`,
`dadaia_workspace/infrastructure/jsonl_record_store.py` (**new** — generic, replaces
`jsonl_bug_store.py` per the AR-1 confirmation), `dadaia_workspace/core/protocols/` (the
record protocol, sibling of `git_object_reader.py`), `tests/**`.

**Description:** Author the record model exactly as SPEC FR2 states it, with the **three**
categories — immutable core, **write-once/absent-until-set** (`root_cause`, `solution`,
`superseded_by`, `migration_note`), mutable governance — documented **per property in the
schema**, not in prose elsewhere. `status` has **no `picked` value**. Add the in-place
record-update seam: one line rewritten, every other byte identical, through the existing
`dadaia_workspace/core/atomic_write.py` (temp file + `os.replace`) with a **re-read
immediately before the rewrite** — the append stream's `O_APPEND` made concurrent writes
race-benign and a record model does not inherit that for free. Route **both** write paths
through the schema-derived `redact` seam installed one day earlier (`eb03d01b` / `0cb08157`,
`v0.4.5` T-045-19): the four new free-text fields must be scrubbed with **no hand-kept list
anywhere**, which is the defect that already fired twice (T-043-23 → T-044-62). **Nothing is
deleted in this task** — `bug-event-v1.schema.json` and the event reader stay until T-050-08
(D-F).

**Done criterion:** A2.1, A2.2 (a/b/c), A2.6, A2.9; the immutability, write-once,
in-place-rewrite, redaction (new schema property scrubbed with no code edited) and
stale-rewrite-refused contract tests green.

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
delete the event fold and its terminal/non-terminal state machine **and the legacy
hourly-file reader** (`_BUG_LOG_RE`, `_sorted_files`, `ROWS_PER_FILE`, the v3→v4
consolidation) — dead under canon v6. The coherence checker becomes a **WARN** surfaced by
`dadaia bugs status` and the doctor with the **exit code unchanged** — proven by a fixture,
because a coherence check that blocks is a new blocker (D15). The `picked` and `archived`
event kinds disappear entirely: `picked` is not a status (the pick is the definition commit),
and archiving is the verb below. Add **`dadaia bugs archive`** (A2.8): terminal records older
than 90 days move to `specs/bugs/_archive/bugs_histo.jsonl` through the same store seam,
re-running is a no-op, and the doctor's overdue signal is a **WARN** with an unchanged exit
code. Add the **A2.7 detector**: a `specs doctor` WARN comparing each record's immutable core
against FR3's first-add derivation, because seam-level immutability is detection, not
prevention, and the SPEC now says so.

**Done criterion:** A2.3, A2.4, A2.7, A2.8; the CLI-output-stability fixtures green untouched
for every input that succeeds today; the double-run `bugs archive` byte comparison green.

**Parallelism:** none.

---

- [ ] **T-050-09 — FR3 (build): the commit derivation, unit-tested on a fixture repo**

**Owner role:** software-engineer · **Commit:** `feat(T-050-09): derive registration and
resolution commits in one pass over the ledger history`

**Preconditions:** T-050-08 `[x]`.

**Write set:** `dadaia_workspace/features/bugs/migrate_v5.py` (**new** — the migration module
and its v5 adapter), `dadaia_workspace/core/protocols/` (`GitHistoryReader`),
`dadaia_workspace/infrastructure/git_subprocess.py` (`log_added_lines(pathspec)`), `tests/**`.

**Description:** Implement SPEC FR3's algorithm and nothing else, as a **pure core function**
over an iterator of `(sha, parents, date, touched_paths, added_lines)` — git access is behind
`GitHistoryReader`, so `features/**` imports neither `infrastructure` nor `subprocess` and
`lint-imports` gains no accepted edge (A3.10). The reader runs `git log --all --no-merges
--reverse --date-order -- specs/bugs/`; the function does one chronological pass, added lines
only, parsed through the migration-owned v5 adapter, **first add wins**, with
`registration_granularity` / `resolution_granularity` computed from (number of bug lines added
in that commit, whether the commit touches any non-`specs/` file). Ties across equal dates
break by topological order then sha, and the tie-break used is recorded.

Most cases are covered by unit tests over an **in-memory history fixture** — a list of
tuples — because the function is pure: a single-bug registration; a 3-bug squash; a
ledger-only resolution; a line re-added by a later squash; a bug whose line is never added.
The one test that still needs a **synthetic git repository** (proving `log_added_lines`
itself) is placed in **`tests/contract/`, never `tests/unit/`** — its subprocess and I/O cost
is exactly the profile that aggravates the still-open
`windows-xdist-workers-crash-on-unit-fast-tier`, and the crash-prone tier is the `unit-fast`
one. **Do not run the migration on the real ledger in this task.**

**Done criterion:** every fixture case produces the expected sha and marker; running the
derivation twice yields identical output; the git-touching test sits under `tests/contract/`
and the CI matrix is watched for any xdist recurrence during this task (reported in T-050-34).

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

**Description:** **First verify the precondition (V23):** the `v0.4.5` T-045-20 fix for
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` is on this branch —
a record carrying U+2028 round-trips byte-identically and `bugs status` reports `skipped: 0`.
Migrating 490 records through a reader that silently drops lines is the build-on-a-stale-layer
shape this release exists to end (AS-14). Then run the migration.

Populate `cause` **only** where the v5 `evidence_diff` / `notes` text literally states one;
populate `caused_by` **only** where a record's text names another existing bug id, marked
`lineage_source: "text-reference"`; everything else stays `null` — historical `caused_by` is
never `"none"` (AS-2). **Every copied free-text value goes through the FR2 redaction seam**
with the operator's denylist terms loaded — write-time scrubbing began only on `eb03d01b`, so
the whole 1 005-event history predates it. `specs/bugs/_archive/archive.jsonl` is **not
touched** (AS-3). Run the migration a second time and prove byte-identical output (V5).

**The rename voids the push-scan amnesty, so scan before you push (V22).** `bugs.jsonl` →
`BUGS.jsonl` gives the new path no prior text, so the range-scoped scan suppresses nothing and
re-flags every historical value: the first push is expected to be refused wholesale. Run
`dadaia ci push-gate-check` over the migration range **before** pushing and remediate each hit
**at the source record**. **Never `--no-verify`, never a scan exclusion.**

Capture **V4**. A count below a `≥` **threshold** means the ref scope was wrong (re-check V6).
A **marker distribution** that differs from §1.2's narrative numbers is **a fact to record,
not a target to chase** — §1.2 counts different units (commit-message pattern, single-bug
commits) than the structural markers the algorithm computes; expect roughly 400
`release-squash` against §1.2's 155, and report it.

**Done criterion:** A3.1–A3.9; V4, V5, V22 and V23 captured; the report's **headline counts**
recorded in `RELEASE.jsonl` as a `note` record and in the closure record (the raw capture
under `.dadaia/tmp/**` is GC'd at 3 days and may not be the sole home of the evidence); the
report carries counts only, never values; this task is a **separate commit** from T-050-07.

**Parallelism:** none.

---

- [ ] **T-050-11 — FR4: `RELEASE.jsonl` replaces `ACTIVE.md`**

**Owner role:** software-engineer · **Commit:** `feat(T-050-11): RELEASE.jsonl milestones
replace ACTIVE.md`

**Preconditions:** T-050-10 `[x]`.

**Write set:** `dadaia_workspace/public/schemas/releases/release-event-v1.schema.json` (new),
`dadaia_workspace/core/release_events.py` (**new** — the stdlib-only fold),
`dadaia_workspace/features/specs/doctor_release.py`, `dadaia_workspace/container.py`,
`dadaia_workspace/hooks/sdd_gate.py` (calls the fold; `_active_field` still present),
`specs/releases/0.5.0/RELEASE.jsonl` (new — back-filled with this release's own `phase` and
`defined` records from T-050-01/02), `specs/releases/README.md` (retires), `tests/**`.

**Description:** This is the **expand** half only. Write and read `RELEASE.jsonl` **alongside**
`ACTIVE.md`; `ACTIVE.md` is **not deleted here** — the contract step is **T-050-21A**, in `S2`,
after FR11/FR12 have repointed the personas, skills and law file that cite it. Deleting it now
would leave the always-on law naming a missing file for an entire segment (SPEC A4.5).

Seven event kinds only — `phase`, `defined`, `implemented`, `shipped`, `audited`, `rc`,
`note` — and the envelope is `{ts, event, agent, data}` with `additionalProperties: false`:
**no `session_id`**, because a harness session id lives in `.dadaia/sessions/` (PROTECTED) and
committing it would link every governance milestone to a local identifier forever. The fold
lives in `core/release_events.py` as a tri-state resolver in the shape of today's
`_active_field`, called directly by `hooks/sdd_gate.py` (**hooks never import the
container**), by `container.py` and by the doctor: one reader, one fold, three callers. The
three sha-bearing milestones are immutable; a contract test refuses a rewrite. `implemented`
is written at the **final-`rc` QA close sha**, not at the PR merge (D3).

**Done criterion:** A4.1, A4.2, A4.6; both files live and agreeing; `ACTIVE.md` still present.

**Parallelism:** none.

---

- [ ] **T-050-12 — FR4: back-fill the archived releases' milestone shas**

**Owner role:** software-engineer · **Commit:** `feat(T-050-12): back-fill archived release
milestones into releases_histo.jsonl`

**Preconditions:** T-050-11 `[x]`. **Must complete before T-050-14** — it reads the archive
that task deletes.

**Write set:** `specs/releases/_archive/releases_histo.jsonl` (new), the back-fill report under
`.dadaia/tmp/software-engineer/<YYYYMMDD>/`.

**Description:** Scan **both** archive layouts — `specs/_archive/releases/<id>/` (93
directories, of which **four are not versions** and are named and excluded:
`ctx-inject-v2-drift-fix-v1`, `memory-markdown-source-v1`, `multiharness-engine-v0116`,
`pi-fourth-harness-v1`) **and** `specs/_archive/<id>/` (30 entries, `v0.1.47` … `v0.2.3`),
which the first Draft did not scan at all. For each, read its `CLOSURE.md` tables and emit one
milestone block: `defined` / `implemented` / `shipped` with `sha` and `pr` **where the table
gives them** and `null` where it does not — never a guess (SPEC D-G, A4.3). Verify every
non-null sha with `git cat-file -e`. **V7's denominator is the number of directories the scan
actually visited across both layouts**, reported with the four exclusions named.

**Done criterion:** A4.3, A4.6; V7 captured with its denominator stated; the found/null split
recorded per release; the headline counts carried into `RELEASE.jsonl` as a `note` record so
the evidence outlives the 3-day `.dadaia/tmp/**` GC.

**Parallelism:** none.

---

- [ ] **T-050-13 — FR5: `BACKLOG.md` becomes a live photo**

**Owner role:** software-engineer (+ `project-manager` for the entry text) · **Commit:**
`refactor(T-050-13): live-photo BACKLOG.md with backlog_histo.jsonl`

**Preconditions:** T-050-12 `[x]`.

**Write set:** `specs/backlog/BACKLOG.md` (the `## LEDGER` section retires),
`specs/backlog/_archive/backlog_histo.jsonl` (new),
`dadaia_workspace/features/backlog/doctor.py` (**BL-DUP deleted — it lives here, not in
`features/specs/doctor_governance.py`**), `dadaia_workspace/features/backlog/document.py` and
`dadaia_workspace/features/backlog/ledger.py` (the in-file `## LEDGER` parsers retire),
`dadaia_workspace/public/scaffold/backlog/**`, `tests/**`.

**Description:** Migrate every `## LEDGER` line into a histo record carrying the full entry
snapshot where the entry text is recoverable and `entry_md: null` + a note where it is not;
report the counts. `BL-DUP` is **deleted**, not disabled — with one line per exit in an
append-only file, a duplicate ledger line is structurally impossible. Legacy
`specs/backlog/_archive/*.md` stay byte-identical.

**Done criterion:** A5.1–A5.4; `backlog doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-13A — FR5: relocate the 18 `consumed_backlog.json` sidecars before FR6**

**Owner role:** software-engineer · **Commit:** `fix(T-050-13A): keep BL-STALE's data feed
across the archive deletion`

**Preconditions:** T-050-13 `[x]`. **Must complete before T-050-14** — it reads what that task
deletes.

**Write set:** `specs/backlog/_archive/consumed_backlog_histo.jsonl` (new),
`dadaia_workspace/features/backlog/ledger.py`, `tests/**`.

**Description:** `features/backlog/ledger.py` reads
`specs/_archive/<release-id>/consumed_backlog.json` and documents that an absent ledger
degrades to `{}` — "BL-STALE is a no-op, never a false ERROR". **18 such files live under the
root archive FR6 deletes**, and nothing in the first Draft named them: deleting the tree would
make a live doctor rule go permanently quiet **without ever failing**, which is precisely the
"documented convention with no data behind it" shape FR13 condemns. Relocate all 18 into
`specs/backlog/_archive/consumed_backlog_histo.jsonl`, one record per release carrying its
release id and consumed slugs, and repoint `ledger.py` at it. Keep the degrade-to-`{}`
behaviour for a genuinely absent record; what is removed is the accidental permanent absence.
The reviewer's alternative — "retire BL-STALE instead" — is **refused**: deleting a rule to
avoid moving its data is the symptom patch this release exists to stop.

**Done criterion:** A5.5; 18 records asserted; a fixture proves BL-STALE still fires on a
stale `ACTIVE` item using a relocated record; `backlog doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-14 — [operator] FR6: tag, then delete root `specs/_archive/`**

**Owner role:** **operator** (executes) + dispatcher (prepares and verifies) · **Commit:**
`chore(T-050-14): delete root specs/_archive after tagging (operator ruling 2026-08-23)`

**Preconditions:** T-050-13A `[x]`; **T-050-10, T-050-12 and T-050-13A complete and
committed** — nothing this task deletes may still be needed.

**Write set:** `specs/_archive/**` (deleted, **after** the historical `verdicts/**` are
relocated to `specs/releases/_archive/<id>/verdicts/`),
`dadaia_workspace/features/spec_context/gate_policy.py` (FROZEN: `_FROZEN_PREFIX =
"specs/_archive/"` **deleted**, `specs/releases/_archive/` **added** — the other three
per-area prefixes already exist), `tests/**`.

**Description:** **Destructive, operator-present, one commit.**

1. **Relocate the evidence, don't just the data.** Root `specs/_archive/releases/*/verdicts/**`
   holds **every past security approval**. Move each beside its release in the per-area
   archive and re-run **V20** against the relocated path — the CI gate must resolve there or
   the next PR cannot pass a required check (A6.2, T-050-06A).
2. **Tag, push, and prove reachability from the remote.** Create and push
   `archive/specs-archive-<YYYYMMDD>` at the commit immediately preceding the deletion; then
   `git ls-remote --tags origin` must list it, and `git show <tag>:specs/_archive/releases/
   v0.4.4/CLOSURE.md | head` must succeed **from a throwaway clone**, not from this working
   copy (**V8**). A local `git show` proves nothing about a tag that never left the machine,
   and the whole recovery story for an irreversible deletion rests on that premise.
3. **If the tag push is refused by the denylist scan:** stop, redact at the source object,
   re-tag, push again (A6.6). **Never `--no-verify`, never disable the scan, never force.**
   The deletion does not proceed until the tag is on the remote and proven from it.
4. **Only then delete**, repointing FROZEN in the **same** commit — one prefix out, one in,
   with **one fixture per path** of the enumerated post-v6 set (`specs/releases/_archive/`,
   `specs/bugs/_archive/`, `specs/backlog/_archive/`, `specs/audits/_archive/`). Omitting
   `specs/releases/_archive/` would leave every archived release **MUTATING** — a net
   integrity loss versus today. `specs/releases/_ideas/` stays **MUTATING deliberately**;
   state it.

**No `archive/*` tag is deleted by this release** — the 50 existing tags are the only path to
**220 of the 295** ledger commits (AS-9).

**Done criterion:** A6.1–A6.6; V8 captured from the throwaway clone; V20 re-run green against
the relocated verdicts; the tag pushed and proven before anything is removed.

**Parallelism:** none.

---

- [ ] **T-050-15 — `S1` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-15): S1 QA close`

**Preconditions:** T-050-04 … 14 (incl. 06A, 13A) all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S1-qa-close.md`.

**Description:** Evidence every `S1` acceptance id. Four questions this segment must answer
plainly: (1) do the migration report's **threshold** counts meet their `≥` bars, and is the
**marker distribution** reported as a measured fact rather than forced toward §1.2's
differently-counted numbers? (2) is there any record whose `cause` or `caused_by` was not
literally present in its source text (A3.5)? (3) did **V20** and **V21** run at T-050-06A —
i.e. is every canon path tracked and does the verdict gate resolve archived evidence — since
discovering either at the ship PR means the release cannot ship; (4) was **V23** verified
before the migration ran? State the bug-surface delta of the bugs feature with its bug
history: the event fold amplified the U+2028 loss across a bug's several lines, this segment
deletes the fold, and the underlying `splitlines()` defect is `v0.4.5` T-045-20's fix, not
this release's claim. Confirm **zero** new `tests/e2e/**` files were added, or name each
exception granted.

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
deleted), `tests/contract/**`,
**`tests/integration/test_precommit_backlog_scoping.py`**,
**`tests/e2e/features/test_backlog_precommit.py`**, then one projection cycle.

**Description:** Pre-commit becomes advisory-only: presence WARN, **always exit 0**. **In that
script only**, the `backlog doctor` block and the fail-closed runner resolution are deleted —
CI already runs the unscoped sweep.

**`pre-push-ci-gate.sh` keeps its fail-closed runner.** The two scripts share the same
`resolve_runner` text and D9 attaches the deletion to the *pre-commit* bullet; a fail-open
pre-push runner means a machine without the venv pushing with **no branch policy and no
denylist scan**, silently — the exact boundary D9 preserves. Pre-push therefore refuses
**three** things and nothing else: an invalid branch name, a denylist hit, and an unresolvable
runner. Only the `ci preflight --quick` invocation leaves it, becoming an always-on rule
(landed in `DADAIA.md` by T-050-20). The security-verdict CI gate on PRs is **untouched**.

Assert the **executed path**, never the script's text: a fixture stages a set `backlog doctor`
rejects and proves pre-commit exits 0; one proves a failing preflight no longer blocks a push;
one proves an **unresolvable runner still refuses** the push.

**The two tests this deletion breaks are in the write set, with a verdict.**
`tests/integration/test_precommit_backlog_scoping.py` imports `_run_backlog_doctor_gate`
directly and will fail to import; `tests/e2e/features/test_backlog_precommit.py` is its
git-hook-path E2E companion. Both are outside `tests/contract/**` and were unnamed in the
first Draft. Per test-stewardship, **`qa-engineer` records the per-file verdict — delete or
rewrite — with its evidence, and `software-engineer` executes it.** The implementer never
deletes or skips either to go green. Capture **V9** and **V10**, and record the secret-scan
coverage limit (A9.6) as a known accepted gap with its intake candidate.

**Done criterion:** A9.1–A9.6; V9 and V10 captured; V10 **negative**; zero-hit greps for both
deleted helpers; the two hook tests carry a recorded `qa-engineer` verdict.

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
`tests/contract/test_rules_skills_map.py`, which retires),
`tests/helpers/scan_population.py`, `tests/contract/test_frozen_clock_aging_ratchet.py`,
`tests/contract/test_public_scripts_thin_wrapper.py` (the three other files referencing
`rules_skills_map`, named rather than left to a broad `tests/**`), `tests/**`.

**Description:** One row per core skill and per scoped `AGENTS.md`, with a recorded hash
tuple. **Cardinality as D14 states it:** every member maps to **exactly one** section; every
section has **at least one** owner. Demanding exactly one owner per section would go RED on
the map's own existing rows, where more than one skill legitimately owns §7 Quality.

**Discovery is structural, never a hand list.** Glob the generators — every `AGENTS.md` and
`*-AGENTS.md` source under `public/{data,scaffold,templates}/` — as the enforcer already globs
`public/skills/*/SKILL.md`. The first Draft's hand-written roster already omitted three
sources that ship today: `public/data/dadaia-AGENTS.md`, `public/data/states-AGENTS.md`,
`public/data/tmp-AGENTS.md`. A hand list is precisely the defect D14 exists to catch.

**Extend the existing enforcer; do not add a second map** — a second map is the exact
puxadinho this release is built to make visible. Five RED conditions, five mutation fixtures,
each proven to fail before and pass after its correction. The test message must say **what to
re-read**, not merely that a hash changed.

**Nothing hard-won is lost on the retirement (A10.6).** `test_rules_skills_map.py` carries
**nine** checks at HEAD — the schema check, six map modes, the FR27 citation checks and the
FR28 bidirectional model-invocation grant — two of them carrying their own registered bug
histories (`citation-enforcer-resolves-projected-instance-paths-against-the-checkout`,
`citation-mutation-fixtures-never-turn-red-on-windows`). **Before deleting the old file**,
produce a **name-diff with a zero-hit residue** plus a one-line note per check recording the
behaviour it still asserts. Byte-for-byte equality is not the criterion and cannot be met by
an extended enforcer; *no behaviour dropped* is.

**Done criterion:** A10.1–A10.6; V17 captured; the nine-check name-diff recorded with a
zero-hit residue; zero-hit grep for `rules-skills-map.json` outside history.

**Parallelism:** none.

---

- [ ] **T-050-20 — FR11: `DADAIA.md` — anchors, the D15 posture, three short sections**

**Owner role:** ai-engineer · **Commit:** `feat(T-050-20): DADAIA.md behavior anchors and the
enforcement-posture section`

**Preconditions:** T-050-19 `[x]`. **This is the only task in the release whose write set
contains `DADAIA.md`** (SPEC D-B).

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (**source only** — the projected law is
PROTECTED), then one projection cycle.

**Description:** Add stable per-behavior anchors for the map to point at — **as zero-cost
comment markup (`<!-- behavior: bugs -->`), never titled subsections.** Six to eight new
headings would read as prose to every agent that loads this file every session and would
materially change the V12 delta; a comment is invisible to a reader and exactly as greppable
for the enforcer. Then the D15 enforcement-posture section verbatim in intent, the short
bug-lineage/commit-shape section (FR7/FR8), the short audits section (FR13/FR14), the short
memory two-tier + ADR section (FR17/FR19), the always-on preflight rule (FR9), and **one
rewritten row in §3's path-class table**: the ADDITIVE row becomes *"Always writable; the
record contract — immutable core, write-once, mutable governance — is audited, not gated"*,
because a mutable-field record breaks the assumption the old wording encoded. No new path
class, no second classifier.

**Every section is a pointer, never a restatement** — the FR8 duplicate scan is re-run over
the result, **including against the scoped `AGENTS.md` files** FR12 authors in this same
segment. Re-capture **V12** with **anchor cost attributed separately from section-body cost**,
so an anchor can never hide inside a section's number: a governance release is exactly the
shape that quietly spends the token budget the last two releases fought for.

**Done criterion:** A11.1–A11.4; V12 re-captured with per-section attribution and anchors
separated; the projected law byte-identical to source.

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
`specs/AGENTS.md`, `specs/backlog/AGENTS.md` **(new)**, `specs/releases/AGENTS.md` **(new)**,
`specs/memory/AGENTS.md`, then one projection cycle and the FR10 hash-tuple re-recording.
*(Verified at HEAD: `specs/AGENTS.md` and `specs/memory/AGENTS.md` exist;
`specs/backlog/AGENTS.md` and `specs/releases/AGENTS.md` do not and are created here —
`specs/bugs/AGENTS.md` is created by T-050-16 and `specs/audits/AGENTS.md` by T-050-23.)*

**Description:** Rename, rebuild and rewrite as SPEC FR12 states. `RC-FLOW.md` **carries
forward the operative `dd-architecture-survey` pointer** the `entity-behavior-map` entry
requires — a pointer dropped in a rebuild is a law relocated into nothing, the exact R-4 risk
this segment names. Every deleted file's content gets a named surviving home in a coverage
table. Re-record each affected hash tuple with a named reviewer — that re-recording is the
joint review FR10 exists to force, and skipping it is how
`dadaia-task-manager-stale-workspace-protocol-citation` happened. Capture **V11**.

**Done criterion:** A12.1–A12.5; V11 captured and `S2`'s AI-surface net **negative**;
`dadaia public doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-21A — FR4 (contract): delete `ACTIVE.md`, all 28 consumers repointed**

**Owner role:** software-engineer (code, tests) + ai-engineer (personas, skills, law) ·
**Commit:** `refactor(T-050-21A): retire ACTIVE.md — the phase is the RELEASE.jsonl fold`

**Preconditions:** T-050-21 `[x]`; T-050-11 `[x]` (the parallel writer has been green for a
segment).

**Write set:** `specs/releases/ACTIVE.md` (**deleted**),
`dadaia_workspace/hooks/sdd_gate.py` (`_active_field` and its regex **deleted**),
`dadaia_workspace/container.py`, `dadaia_workspace/core/exceptions.py`,
`dadaia_workspace/features/specs/{doctor,doctor_common,doctor_release,doctor_structural,scaffolder}.py`,
`dadaia_workspace/features/reports/next.py`,
`dadaia_workspace/features/spec_context/gate_policy.py`,
`dadaia_workspace/cli/commands/specs.py` (the `specs release` / `specs segment` verbs),
`dadaia_workspace/public/agents/**` (the six personas citing it),
`dadaia_workspace/public/skills/**` (the five skills citing it),
`dadaia_workspace/public/scaffold/AGENTS.md`,
`dadaia_workspace/public/templates/specs-AGENTS.md`,
`dadaia_workspace/public/data/DADAIA.md` **— by exception, and only for the `ACTIVE.md`
citation**: T-050-20 owns that file (D-B Tier 1), so this edit is sequenced strictly after it
and states that in the commit body, `tests/**`, then one projection cycle.

**Description:** This is FR4's **contract** step, and it lands in `S2` rather than `S1` on
purpose: 28 consumers in `dadaia_workspace/` read or write `ACTIVE.md`, and the personas,
skills and law file among them are owned by FR11/FR12 in this segment. Deleting the file in
`S1` would leave the always-on law naming a file that does not exist for a whole segment — an
`expand → switch → contract` violation by this release's own D-F.

Repoint every consumer at `core/release_events.py`'s fold, then delete the file with **no
fallback branch left behind** — a fixture with **no `ACTIVE.md` present** proves the gate
resolves the MEMORY phase from the fold alone. On the test side, **26 test files reference
`ACTIVE.md` and 4 reference `CLOSURE.md`/`CLOSURE-TEMPLATE`**: enumerate them, and rewrite or
delete each under a recorded `qa-engineer` verdict — none is silently orphaned.

**Done criterion:** A4.5, A4.7; a **zero-hit grep** for `ACTIVE.md` outside `_archive/` and
git history; the no-`ACTIVE.md` gate fixture green; the 26 + 4 census enumerated with a
per-file disposition; `dadaia public doctor` green.

**Parallelism:** none.

---

- [ ] **T-050-22 — `S2` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-22): S2 QA close`

**Preconditions:** T-050-16 … 21A all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S2-qa-close.md`.

**Description:** Evidence A7–A12 **plus A4.5/A4.7** (the contract step lands here). Read the
**coverage tables**, not the diffs alone — the risk here is a law relocated into nothing (the
v0.4.4/v0.4.5 R-4 class), and this segment relocates three: `dd-bug-fix`'s procedure,
`CLOSURE-CHECKS.md`/`CLOSURE-TEMPLATE.md`, and the nine enforcer checks. Confirm
mechanically: (1) this segment added **zero** blocking exits and removed **exactly two**
(pre-commit's `backlog doctor` block and its fail-closed runner) while **pre-push kept its
fail-closed runner** — three fixtures, not two; (2) the nine-check name-diff has a zero-hit
residue; (3) `ACTIVE.md` is gone with a zero-hit grep and the 26 + 4 test census carries a
per-file verdict. State the bug-surface delta of the hook surface with the registered bug that
motivated it (`precommit-backlog-doctor-blocks-unrelated-commits`). Confirm **zero** new
`tests/e2e/**` files, or name each exception granted.

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
`dadaia_workspace/infrastructure/jsonl_record_store.py` (a **second store instance** over the
generic seam — not a second implementation), `dadaia_workspace/core/models/findings.py` (new),
`tests/**`, then one projection cycle **run by `ai-engineer`** (the last write in this task's
set is the persona/scoped law, so `ai-engineer` owns the projection).

**Description:** Author the finding record with the immutable/mutable split documented per
property, and the example record as **valid JSON** so it can seed a fixture against a schema
with `additionalProperties: false`.

**`project-auditor`'s allowlist, decided (S-8).** It gains `specs/audits/**` **and**
`specs/bugs/BUGS.jsonl` — the latter for **governance fields only, written through the FR2
record-store seam**, because pillar 1 must write `audited` and `resolved_commit` and the first
Draft simultaneously forbade it. One writer seam, redacted and atomic; the auditor still never
writes a core field, never writes a fix, and never writes anything else under `specs/`.
**The fixture proves what is mechanically true, not what the allowlist implies:**
`write_allowlist` is parsed at *projection* time and is documentation, and nothing refuses a
persona's file-tool write to an ADDITIVE path — so the fixture asserts that
`specs/audits/_archive/` is **FROZEN** (matched before ADDITIVE) and refused for this persona
as for any other. Reuse the FR2 seam; do **not** re-implement it: bugs, findings and the
backlog histo each get their own store **instance** with their own model, and no module knows
two record shapes.

**Done criterion:** A13.1–A13.4; one store module, three models, three container
registrations, proven by the diff.

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
judgement about what counts, and it filters `resolution_granularity == "exact"` (**never**
`commit_granularity`, which is not a field).

**Pillar 1 gains three cheap measures and one write.** Measures: the
**registration→resolution interval** (`certify-cannot-install-installed-provider` reported
18:41:56Z and resolved 18:41:57Z — the no-red-loop signature, detected by arithmetic instead
of judgement); a **core-field mutation** hunk in `git log -p -- specs/bugs/BUGS.jsonl` as a
**HIGH** finding (the detector that makes A2.2's seam-level rule auditable, since nothing
prevents a file-tool rewrite); and a **cache disagreement** between a stored `resolved_commit`
and the derivation. Write: on each record reviewed, `audited`, `resolved_commit` and
`resolution_granularity` are set in **one atomic in-place rewrite** through the FR2 seam —
one writer, one seam, which is what AS-1(ii) buys and why FR8 has no shape 3b.
**Zero CLI verbs, zero hook changes** in this diff.

**Done criterion:** A14.1–A14.6; the one-rewrite-per-record fixture green.

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

- [ ] **T-050-25A — FR15/FR4: retire every surviving `CLOSURE.md` parser**

**Owner role:** software-engineer · **Commit:** `refactor(T-050-25A): no checker outlives the
file it parses`

**Preconditions:** T-050-25 `[x]`; T-050-21A `[x]` (`CLOSURE.md` and `ACTIVE.md` are both
gone by now).

**Write set:** `dadaia_workspace/features/specs/doctor_closure_audit.py`,
`dadaia_workspace/features/specs/doctor_release.py`,
`dadaia_workspace/features/specs/doctor_governance.py`,
`dadaia_workspace/features/specs/doctor_common.py` (`RELEASE_ARTIFACTS`),
`dadaia_workspace/features/specs/catalog.py`,
`dadaia_workspace/features/specs/memory_lint.py`,
`dadaia_workspace/features/spec_context/gate_policy.py` (the duplicated
`<YYYYMMDD>-<slug>` comment), `tests/**`.

**Description:** FR4 deletes `CLOSURE.md`; T-050-25 retires only its *disposition* regexes.
`CLOSURE.md` still appears in **seven** modules, and a checker that parses a file which no
longer exists is dead code behind a dead artifact — the shape this release exists to stop, and
the one A4.4 deferred to "FR15" without FR15 covering it. Delete the remaining `CLOSURE.md`
checks in `doctor_closure_audit.py`, `doctor_release.py` and `doctor_governance.py`, plus
`RELEASE_ARTIFACTS` in `doctor_common.py`, and collapse `AUDIT_DIR_NAME_RE` into a **single**
home for the `<YYYYMMDD>-<slug>` shape (also replacing the comment that repeats it in
`gate_policy.py`). Deleted, not disabled.

**Done criterion:** A4.4; a **zero-hit grep for `CLOSURE.md` across
`dadaia_workspace/features/**`**; one home for the audit-directory pattern; `specs doctor`
**0 errors**; the LOC delta of this task **negative**.

**Parallelism:** none.

---

- [ ] **T-050-26 — FR16: the first audit, as a dry run over this repository**

**Owner role:** project-auditor · **Commit:** `docs(T-050-26): first audit under canon v6 (dry
run)`

**Preconditions:** T-050-25 `[x]`.

**Write set:** `specs/audits/<YYYYMMDD>-canon-v6-first-audit/AUDIT.md` (new) +
`FINDINGS.jsonl` (new); `specs/releases/0.5.0/RELEASE.jsonl` (the `audited` milestone).

**Preconditions:** T-050-25A `[x]`.

**Description:** Run all three pillars over the window. **This is the release's acceptance,
not a formality:** pillar 1 must name, with evidence, the four documented chains of SPEC §1.1
**by the bug ids §1.1 pins** — the nine-instance gitignore class (≥ 3 ids), the certify chain
(`codex-live-probe-gate-checks-presence-not-usability` →
`certify-skip-detail-leaks-full-codex-output`), the frozen-clock chain
(`no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` →
`frozen-clock-ratchet-scans-tests-tmp-scratch-dir`), and the bug-event ledger family
(`bug-event-field-with-unicode-line-separator-silently-drops-the-event` plus the ESC escaping
finding, cited by its v0.4.4 review artifact since it carries no bug id). **A finding that
claims a chain without naming its ids does not satisfy A16.2** — that is why they are pinned;
SPEC §1.5 is the shape each finding must take. If it cannot, T-050-24 is reworked; the
acceptance is not lowered. Pillar 2 reads **this release's own commits** and reports FR8
conformance. Pillar 3 executes every `Measured by:` check — FR18 authors them in `S4`, so any
principle not yet written is recorded as a gap to re-run at the final `rc`, never as a pass.
Every finding is `disposition: open`, `release: null`; **no backlog entry is created** — the
findings go to the PM's operator-gated intake report.

**Redaction is mechanical here, not a promise (A13.5 / V24).** The auditor writes with file
tools, so no seam can redact for it, and `Measured by:` runs (`lint-imports`, `pytest`, the
ratchets) emit runner-absolute paths routinely. Capture every transcript under
`.dadaia/tmp/**` and **cite it by path** in `evidence` — never paste it — then scan the whole
folder with the same detector a push uses (`dadaia ci push-gate-check` over the range) and
record the zero-hit result before the segment closes. The folder is committed inside `specs/`
forever.

**Done criterion:** A16.1–A16.6; V16 and V24 captured.

**Parallelism:** none.

---

- [ ] **T-050-27 — `S3` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-050-27): S3 QA close`

**Preconditions:** T-050-23 … 26 (incl. 25A) all `[x]`.

**Write set:** `specs/releases/0.5.0/reviews/S3-qa-close.md`.

**Description:** Evidence A13–A16. The single question that decides this segment: **did the
dry run rediscover the loop?** Quote the four chains **and their pinned bug ids** from
`FINDINGS.jsonl`, or reject the segment — a chain named in prose without its ids does not
count. Verify **V24**: the audit folder was scanned by the push detector with a zero-hit
result and every transcript is cited by `.dadaia/tmp/**` path rather than pasted — it is
committed inside `specs/`, so it is public forever. Confirm **zero** new `tests/e2e/**` files,
or name each exception granted.

**Done criterion:** `APPROVE` committed on the branch, with A16.2 explicitly evidenced by id.

**Parallelism:** none.

---

## Segment `S4` — memory two-tier, principles, ADRs

- [ ] **T-050-28 — FR17: split the memory trio into Part 1 and Part 2**

**Owner role:** product-engineer · **Commit:** `docs(T-050-28): memory Part 1 Principles /
Part 2 Implementation`

**Preconditions:** T-050-27 `[x]`; **the `S4` memory window is opened as a recorded release
state (AS-12)** — the first act of this task is appending a `phase: CLOSURE` record to
`specs/releases/0.5.0/RELEASE.jsonl`, with its agent and timestamp, in its own commit.

**Write set:** `specs/releases/0.5.0/RELEASE.jsonl` (the window-opening `phase` record),
`specs/memory/ARCHITECTURE.md`, `specs/memory/QUALITY.md`,
`specs/memory/TECHSTACK.md`, `specs/memory/AGENTS.md`, `specs/memory/product/**` (only the
atoms carrying architecture principles or implementation tours), `tests/contract/**` (the
file-shape test).

**Description:** **Open the window on the record, never by toggling a phase around this
task.** `DADAIA.md` §3 makes `specs/memory/` writable in `DEFINITION`/`CLOSURE` only; the
first Draft's answer — "the dispatcher sets it before relaying and flips it back afterwards",
buried in a precondition — is an unrecorded ritual that makes the gate say yes, which is the
fabricated-evidence shape this release outlaws. Instead the transition is a ledger fact that
pillar 2 can read: `phase: CLOSURE` here, `phase: IMPLEMENTATION` at T-050-33. **The operator
ratifies AS-12 before this task starts**; if refused, the stated fallback applies and
FR17–FR21 move wholesale into the final `rc`'s closure window, at the cost of the `S4` QA
close and the ADR sitting losing their own segment boundary.

Then restructure each of the three files into exactly two top-level parts. Every
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

**Write set:** `specs/releases/0.5.0/reviews/S4-qa-close.md`,
`specs/releases/0.5.0/RELEASE.jsonl` (the window-closing `phase: IMPLEMENTATION` record).

**Description:** Evidence A17–A21. Check the two properties that make this segment worth
anything: (1) **every** Part-1 principle names a measure that was actually executed (V14) —
a `Measured by:` line pointing at a check nobody ran is decoration, which is what this segment
exists to abolish, and **V14 is a one-time capture, not a standing gate**: a `Measured by:`
that goes stale later is caught at the next audit (pillar 3), never at commit time, and the
artifact says so rather than implying a permanent check; (2) **zero** new checks were written
by FR18 (A18.3). Confirm every ADR carries a terminal operator decision, and **zero** new
`tests/e2e/**` files (or name each exception). Then **close the memory window** with the
`phase: IMPLEMENTATION` record (AS-12) — the segment does not close until the ledger says the
window did.

**Done criterion:** `APPROVE` committed on the branch; the window-closing record appended.

**Parallelism:** none.

---

## Scope complete — gates and the trio

- [ ] **T-050-34 — [shell] FR22: the invariants, measured**

**Owner role:** software-engineer · **Commit:** the capture reference only

**Preconditions:** T-050-33 `[x]`; every task above `[x]`.

**Description:** Run `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor` (**0
errors**), `dadaia backlog doctor`, `dadaia public doctor`, `lint-imports`. Capture **V18**
(zero new non-zero exits in the hooks; **exactly two** blocks removed, with the pre-push
fail-closed runner still refusing; the CLI-output-stability fixtures green untouched) and
**V19** (production LOC **per FR** with its declared direction, AI-surface net, complexity
ceilings). A positive net inside an FR that declared itself net-negative is a defect of the
release; the release's overall net-positive production LOC is expected and stated (SPEC
A22.3).

**Also report the xdist observation.** `windows-xdist-workers-crash-on-unit-fast-tier` (LOW)
is open and unpicked (AS-4), and this release adds a nontrivial number of new `unit`/
`contract` tests. State whether any recurrence of that crash appeared on the **CI matrix**
during `S1`–`S4`, naming the runs, and confirm the git-touching derivation test sits in
`tests/contract/` rather than the crash-prone `unit-fast` tier. A recurrence is a bug event
appended to the open record, never a silent retry.

**Done criterion:** A22.1–A22.7; V18 and V19 captured; the xdist CI-matrix note recorded.

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

**Write set:** `specs/releases/0.5.0/reviews/RELEASE-VERDICT.md`, and the verdict handoff at
**`specs/releases/0.5.0/verdicts/<40-hex-sha>.handoff.json`** carrying
`agent: "security-reviewer"`, `verdict: "APPROVED"` and a **40-hex** `metrics.commit_sha` —
the exact path and fields the CI gate keys on; a branch name or a short sha is silently
skipped and the gate then fails closed.

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

**Description:** Push `feature/0.5.0`, open the PR to `develop` with the APPROVED verdict at
`specs/releases/0.5.0/verdicts/<40-hex>.handoff.json` covering the **PR head sha**, watch CI
to green, merge. That merged `develop` **is `rc-1`** (SPEC D-J) — the first and only
integration of the whole scope. Append the `rc` open/close records to `RELEASE.jsonl` (one
kind, the state in `data`).

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

**This is a lane marker, not a unit of work.** It has no fixed write set and no fixed
acceptance beyond A22.8, and it **may close with zero rounds** — say so plainly rather than
leaving a reviewer to infer it.

**Done criterion:** every round has a QA close, a delta review, a merge and a `RELEASE.jsonl`
`rc` open/close pair; the accepted final `rc` is named — or the task closes with **zero
rounds** recorded, in which case the final `rc` **is** `rc-1`.

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
`## Size accounting` (V19, V11, V12, V15); the migration and back-fill reports **by their
headline counts inline** — `.dadaia/tmp/**` is GC'd at 3 days, so a closure record that cites
only a path cites nothing a month later; the FR16 audit by folder with its per-pillar finding
counts; the ADR
ledger with every operator decision; the four coverage tables (FR7, FR12, FR17, FR21); test
dispositions; the `rc` ledger; the artifact GC sweep; **intake candidates** — FR16's findings
and every residual, compiled for the PM's operator-facing report, with **no backlog entry
created by any agent** — including FR9's stated secret-scan coverage limit (A9.6: gitleaks
effectively runs once per release, on the ship PR, so `rc-1` carries the migrated ledger and
the audit folder under the privacy denylist scan only) and any residual from the five
definition reviews; the restated git-identity standing question (which is also why A19.3
claims the ADR **pairing** detection only, never attribution); archive decision `MOVE`.
Six backlog slugs move to `DELIVERED · 0.5.0` through the FR5 mechanism — one record each,
never a duplicate. **No bug is closed by this release** (AS-4).

**Done criterion:** every closure obligation in SPEC §5 discharged.

**Parallelism:** none.

---

- [ ] **T-050-41 — [git] Archive the release**

**Owner role:** dispatcher · **Commit:** `chore(T-050-41): archive 0.5.0`

**Preconditions:** T-050-40 `[x]`.

**Description:** `git mv specs/releases/0.5.0 specs/releases/_archive/0.5.0` — the **per-area**
archive this release created, not the deleted root `_archive/` (FR6). Append a
`phase: ARCHIVED` record to `RELEASE.jsonl` (there is no separate `archive` kind — the phase
record **is** the archive fact). Steps T-050-39 … 41 ride **one** commit, in the order memory
→ closure → sweep → archive, which stays **before** the ship PR per `DADAIA.md` §6.

**The verdicts move with the directory, and the gate must already handle that.** This is the
step that broke the required check twice before; **V20 proved at T-050-06A that the gate
resolves `specs/releases/_archive/0.5.0/verdicts/`**. Re-confirm the gate's resolution against
the moved path here — if it fails, the release stops at this task rather than discovering it
on the ship PR.

**Done criterion:** the release directory is under `specs/releases/_archive/`; the phase fold
reads `ARCHIVED`; the verdict gate resolves this release's evidence at its archived path.

**Parallelism:** none.

---

- [ ] **T-050-42 — [git] Final-`rc` merge: version bump and PR → `develop`**

**Owner role:** dispatcher + software-engineer + security-reviewer

**Preconditions:** T-050-41 `[x]`.

**Write set:** `pyproject.toml` (bump to `0.5.0`), `CHANGELOG.md` (`[0.5.0]`), then git refs.

**Description:** One axis: the release id **is** the package version. MINOR, because the
`specs/` pattern moves 5 → 6 and that is consumer-visible. **`0.5.0` is not `v0.5.0`** — the
archived `v0.5.0` (2026-08-12) belongs to the retired spec-lineage axis and its 46 in-code
citations stay as they are (AS-13).

Write the **`implemented` milestone at the final-`rc` QA-close sha** — D3's own wording — and
only then push, open the PR to `develop` with the APPROVED verdict at
`specs/releases/_archive/0.5.0/verdicts/<40-hex>.handoff.json` covering the PR head sha, watch
CI to green, and merge. The milestone marks the commit that was **worked and closed**, not the
integration artifact that follows it.

**Done criterion:** the `implemented` milestone appended at the QA-close sha **before** the
merge; PR merged; CI green.

**Parallelism:** none.

---

- [ ] **T-050-43 — [git] Ship — merge to `main`**

**Owner role:** dispatcher + security-reviewer + **operator** (the publish decision) ·
**Preconditions:** T-050-42 `[x]`.

**Description:** PR `develop → main` with the APPROVED verdict at
`specs/releases/_archive/0.5.0/verdicts/<40-hex>.handoff.json` covering that PR's head sha;
watch CI to green; merge. Append the `shipped` milestone
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
